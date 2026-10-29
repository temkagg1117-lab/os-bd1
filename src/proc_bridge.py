#!/usr/bin/env python3
"""proc_bridge.py - bridge between the kernel module's /proc/pid and JSON.

Protocol with the module (see ti_main.c):

    write "<pid>\\n"  to /proc/pid   select the process (EINVAL if the input
                                    is not a decimal number in 1..PID_MAX_LIMIT)
    read             /proc/pid      text report; empty when no such task

The write and the read must not be interleaved with another request, because
the module keeps one global "selected pid". ProcBridge serialises them with a
lock.

Report format that parse_report() understands. One task per line, written as
`key = [value]` pairs, in any order; the first line is the target:

    command = [bash] pid = [1203] ppid = [1190] state = [1]
    command = [sshd] pid = [1190] ppid = [812] state = [1]       <- ancestors
    command = [systemd] pid = [1] ppid = [0] state = [1]
    command = [sleep] pid = [1630] ppid = [1203] state = [1]     <- children

* `ppid` is required for hierarchy; the tree is rebuilt from pid/ppid, so the
  order of the lines does not matter.
* `state` may be the kernel bit value (0 running, 1/2 sleeping, 4 stopped, ...),
  a letter (R S D T Z X) or a word (RUNNING, SLEEPING, ZOMBIE ...).
* `exit_state = [32]` is optional and marks a zombie.
* A line `status = [OK|NOT_FOUND|ERROR|EMPTY]` is optional.
* Only direct children are needed; grandchildren are fetched by asking the
  module about each child (see ProcBridge._expand).
"""
import argparse
import errno
import json
import os
import re
import threading

PROC_PATH = os.environ.get("PID_PROC_PATH", "/proc/pid")

TI_MAX_INPUT = 16           # ti_main.c: longest accepted write, newline included
PID_MAX_LIMIT = 4194304     # ti_main.c rejects pid > PID_MAX_LIMIT (64-bit kernels)
MAX_OUTPUT_BYTES = 1 << 20  # never read more than this from one report
MAX_EXPAND = 64             # children asked about when looking for grandchildren

STATUS_OK = "OK"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_ERROR = "ERROR"
STATUS_EMPTY = "EMPTY"
_STATUSES = (STATUS_OK, STATUS_NOT_FOUND, STATUS_ERROR, STATUS_EMPTY)

ERR_FORMAT = "FORMAT_ERROR"
ERR_BOUNDARY = "BOUNDARY_ERROR"
ERR_MODULE = "MODULE_NOT_LOADED"
ERR_PERMISSION = "PERMISSION_DENIED"
ERR_PARSE = "PARSE_ERROR"

MSG_FORMAT = "Зөвхөн бүхэл тоон PID оруулна уу."
_DEFAULT_MESSAGES = {
    STATUS_ERROR: "Алдаа гарлаа.",
    STATUS_NOT_FOUND: "Процесс системд олдсонгүй.",
    STATUS_EMPTY: "Сонгосон PID цэвэрлэгдлээ.",
}

_INT_RE = re.compile(r"[+-]?[0-9]+")
_PAIR_RE = re.compile(r"(\w+)\s*=\s*\[(.*?)\](?=\s|$)")
_ERROR_RE = re.compile(r"\b([A-Z][A-Z_]*_ERROR)\b\s*:?\s*(.*)")

# task->__state / exit_state bits (include/linux/sched.h)
_TASK_STOPPED_OR_TRACED = 0x4 | 0x8
_TASK_SLEEPING = 0x1 | 0x2
_EXIT_DEAD = 0x10
_EXIT_ZOMBIE = 0x20
_TASK_DEAD = 0x80

_LETTER_STATES = {
    "R": "RUNNING", "S": "SLEEPING", "D": "SLEEPING", "I": "SLEEPING",
    "T": "STOPPED", "t": "STOPPED", "Z": "ZOMBIE", "X": "DEAD",
}
_WORD_STATES = ("RUNNING", "SLEEPING", "STOPPED", "ZOMBIE", "DEAD")

_ROLES = {1: "child", 2: "grandchild"}


def _to_int(text):
    """int(text) for decimal or 0x.. numbers, None when it is not a number."""
    if text is None:
        return None
    for base in (0, 10):
        try:
            return int(str(text).strip(), base)
        except ValueError:
            pass
    return None


def classify_state(raw, exit_state=None):
    """Map the module's `state` (and optional `exit_state`) to a UI state name."""
    if exit_state:
        if exit_state & _EXIT_ZOMBIE:
            return "ZOMBIE"
        if exit_state & _EXIT_DEAD:
            return "DEAD"
    value = _to_int(raw)
    if value is None:
        text = str(raw).strip()
        if text.upper() in _WORD_STATES:
            return text.upper()
        return _LETTER_STATES.get(text, "UNKNOWN")
    if value < 0:                       # textbook: -1 means "unrunnable"
        return "SLEEPING"
    if value & _EXIT_ZOMBIE:
        return "ZOMBIE"
    if value & (_EXIT_DEAD | _TASK_DEAD):
        return "DEAD"
    if value & _TASK_STOPPED_OR_TRACED:
        return "STOPPED"
    if value & _TASK_SLEEPING:
        return "SLEEPING"
    if value & 0xFF == 0:               # TASK_RUNNING, possibly with WAKING/NEW flags
        return "RUNNING"
    return "UNKNOWN"


def _is_zero(text):
    return bool(_INT_RE.fullmatch(text)) and text.lstrip("+-").strip("0") == ""


def _refusal(text):
    """(error_code, message) explaining why the module refuses `text`."""
    if not _INT_RE.fullmatch(text):
        return ERR_FORMAT, MSG_FORMAT
    magnitude = text.lstrip("+-").lstrip("0") or "0"
    if text.startswith("-") and magnitude != "0":
        return ERR_BOUNDARY, "PID сөрөг тоо байх боломжгүй."
    if len(magnitude) > len(str(PID_MAX_LIMIT)) or int(magnitude) > PID_MAX_LIMIT:
        return ERR_BOUNDARY, "PID хэт том байна (дээд хязгаар %d)." % PID_MAX_LIMIT
    return ERR_FORMAT, "Оролт хэт урт байна."


def _result(status, requested, raw="", error_code=None, message=None):
    """Response skeleton; every query returns this same shape."""
    if message is None:
        message = _DEFAULT_MESSAGES.get(status, "")
    return {
        "ok": status in (STATUS_OK, STATUS_EMPTY),
        "status": status,
        "error_code": error_code,
        "message": message,
        "requested": requested,
        "pid": None,
        "target": None,
        "ancestors": [],
        "children": [],
        "tree": None,
        "counts": {"ancestors": 0, "children": 0, "grandchildren": 0},
        "truncated": False,
        "raw": raw,
    }


def _error(code, message, requested, raw=""):
    return _result(STATUS_ERROR, requested, raw, code, message)


def _make_record(pairs):
    pid = _to_int(pairs.get("pid"))
    if pid is None or "command" not in pairs:
        return None
    state_raw = pairs.get("state", "")
    state = _to_int(state_raw)
    return {
        "pid": pid,
        "ppid": _to_int(pairs.get("ppid")),
        "command": pairs["command"],
        "state": state if state is not None else state_raw,
        "state_name": classify_state(state_raw, _to_int(pairs.get("exit_state"))),
    }


def parse_report(text):
    """Split the module's text into status, error info and task records.

    Returns {"status", "error_code", "message", "records"}; records maps
    pid -> task dict in the order the lines appeared (target first).
    """
    status = error_code = message = None
    records = {}
    for line in text.splitlines():
        pairs = {key.lower(): value.strip() for key, value in _PAIR_RE.findall(line)}
        if "status" in pairs:
            status = pairs["status"].upper()
        error_code = pairs.get("error_code") or pairs.get("code") or error_code
        message = pairs.get("message") or message
        record = _make_record(pairs)
        if record:
            records.setdefault(record["pid"], record)
            continue
        rest = _PAIR_RE.sub("", line).strip()
        if not rest:
            continue
        found = _ERROR_RE.search(rest)
        if found:
            error_code = error_code or found.group(1)
            message = message or found.group(2).strip() or rest
        else:
            message = message or rest

    if status is None:
        if records:
            status = STATUS_OK
        elif not text.strip():
            status = STATUS_NOT_FOUND       # the module returns 0 bytes for an unknown pid
        else:
            status, error_code = STATUS_ERROR, error_code or ERR_PARSE
            message = message or "Цөмийн гаралтыг задлах боломжгүй байна."
    elif status not in _STATUSES:
        message = "Үл мэдэх status: %s" % status
        status, error_code = STATUS_ERROR, ERR_PARSE
    elif status == STATUS_OK and not records:
        status, error_code = STATUS_ERROR, ERR_PARSE
        message = "status = [OK] боловч процессийн мөр олдсонгүй."
    if status == STATUS_ERROR and not error_code:
        error_code = STATUS_ERROR
    if status == STATUS_OK:
        message = ""
    return {"status": status, "error_code": error_code, "message": message,
            "records": records}


def _node(record, role):
    node = {key: record[key] for key in ("pid", "ppid", "command", "state", "state_name")}
    node["role"] = role
    return node


def _pick_target(records, requested_pid):
    return records.get(requested_pid) or next(iter(records.values()))


def build_hierarchy(records, requested_pid=None):
    """Ancestors -> target -> children -> grandchildren, rebuilt from pid/ppid."""
    target = _pick_target(records, requested_pid)

    chain = []                          # nearest ancestor first
    seen = {target["pid"]}
    current = target
    while current["ppid"] in records and current["ppid"] not in seen:
        current = records[current["ppid"]]
        seen.add(current["pid"])
        chain.append(current)
    chain.reverse()                     # root first

    by_parent = {}
    for record in records.values():
        by_parent.setdefault(record["ppid"], []).append(record)

    def descend(record, depth):
        nodes = []
        for kid in sorted(by_parent.get(record["pid"], []), key=lambda r: r["pid"]):
            if kid["pid"] in seen:
                continue
            seen.add(kid["pid"])
            node = _node(kid, _ROLES[depth])
            node["children"] = descend(kid, depth + 1) if depth < len(_ROLES) else []
            nodes.append(node)
        return nodes

    children = descend(target, 1)
    target_node = _node(target, "target")
    tree = dict(target_node, children=children)
    for record in reversed(chain):
        tree = dict(_node(record, "ancestor"), children=[tree])

    return {
        "pid": target["pid"],
        "target": target_node,
        "ancestors": [_node(record, "ancestor") for record in chain],
        "children": children,
        "tree": tree,
        "counts": {
            "ancestors": len(chain),
            "children": len(children),
            "grandchildren": sum(len(node.get("children", [])) for node in children),
        },
    }


def build_result(report, requested, raw=""):
    result = _result(report["status"], requested, raw, report["error_code"],
                     report["message"])
    if report["status"] == STATUS_OK:
        result.update(build_hierarchy(report["records"], _to_int(requested)))
        result["truncated"] = report.get("truncated", False)
    return result


class ProcBridge:
    """Talks to /proc/pid. One query = one write + one read (+ child lookups)."""

    def __init__(self, proc_path=PROC_PATH):
        self.proc_path = proc_path
        self._lock = threading.Lock()

    def available(self):
        return os.path.exists(self.proc_path)

    def query(self, pid):
        """Return the JSON-ready result for `pid` (a string typed by the user)."""
        requested = "" if pid is None else str(pid)
        text = requested.strip()
        if not text or not text.isprintable():
            return _error(ERR_FORMAT, MSG_FORMAT, requested)
        if _is_zero(text):                  # reset: the module cannot select pid 0
            return _result(STATUS_EMPTY, requested)
        if len(text.encode("utf-8")) + 1 > TI_MAX_INPUT:
            return _error(*_refusal(text), requested)
        try:
            with self._lock:
                return self._collect(text, requested)
        except FileNotFoundError:
            return _error(ERR_MODULE, "%s олдсонгүй. Модулийг ачаалсан эсэхээ "
                          "шалгана уу (sudo insmod task_info.ko)." % self.proc_path,
                          requested)
        except PermissionError:
            return _error(ERR_PERMISSION, "%s руу хандах эрх алга." % self.proc_path,
                          requested)

    def _collect(self, text, requested):
        try:
            output = self._exchange(text)
        except (FileNotFoundError, PermissionError):
            raise
        except OSError as exc:              # the module refused the write (EINVAL)
            code, message = _refusal(text)
            return _error(code, message, requested, raw=str(exc))
        report = parse_report(output)
        if report["status"] == STATUS_OK:
            report["truncated"] = self._expand(report["records"], _to_int(text))
        return build_result(report, requested, output)

    def _expand(self, records, target_pid):
        """Look up every child so its own children (grandchildren) are known.

        Returns True when there were more children than MAX_EXPAND.
        """
        target = _pick_target(records, target_pid)
        children = [r for r in records.values() if r["ppid"] == target["pid"]]
        for child in children[:MAX_EXPAND]:
            if any(r["ppid"] == child["pid"] for r in records.values()):
                continue
            try:
                sub = parse_report(self._exchange(str(child["pid"])))
            except OSError:
                continue
            for pid, record in sub["records"].items():
                records.setdefault(pid, record)
        return len(children) > MAX_EXPAND

    def _exchange(self, text):
        """write(pid) then read the whole report. Caller holds the lock."""
        fd = os.open(self.proc_path, os.O_WRONLY)
        try:
            os.write(fd, (text + "\n").encode("utf-8"))
        finally:
            os.close(fd)
        fd = os.open(self.proc_path, os.O_RDONLY)
        try:
            chunks, size = [], 0
            while size < MAX_OUTPUT_BYTES:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
        finally:
            os.close(fd)
        return b"".join(chunks).decode("utf-8", errors="replace")


# pid: [ppid, command, state, exit_state]
_MOCK_PROCESSES = {
    1: [0, "systemd", 1, 0],
    2: [0, "kthreadd", 1, 0],
    812: [1, "sshd", 1, 0],
    1190: [812, "sshd", 1, 0],
    1203: [1190, "bash", 1, 0],
    1511: [1203, "python3", 0, 0],
    1630: [1203, "sleep", 1, 0],
    1702: [1203, "vim", 4, 0],
    1888: [1203, "worker", 128, 32],        # zombie
}
_MOCK_SERVER_PID = 1511


class MockProcBridge(ProcBridge):
    """ProcBridge on an in-memory process table (--mock), for machines without
    the kernel module. It behaves like ti_main.c: EINVAL for a bad write, an
    empty report for an unknown pid, and direct children only."""

    def __init__(self):
        super().__init__("(mock)")
        self._table = {pid: list(entry) for pid, entry in _MOCK_PROCESSES.items()}
        self._next_pid = 4000
        self._trees = []

    def available(self):
        return True

    def _line(self, pid):
        ppid, command, state, exit_state = self._table[pid]
        line = "command = [%s] pid = [%d] ppid = [%d] state = [%d]" % (
            command, pid, ppid, state)
        if exit_state:
            line += " exit_state = [%d]" % exit_state
        return line

    def _exchange(self, text):
        if not _INT_RE.fullmatch(text):
            raise OSError(errno.EINVAL, "input is not a decimal number")
        pid = int(text)
        if pid <= 0 or pid > PID_MAX_LIMIT:
            raise OSError(errno.EINVAL, "pid out of range")
        if pid not in self._table:
            return ""
        lines = [self._line(pid)]
        current = pid
        while self._table[current][0] in self._table:
            current = self._table[current][0]
            lines.append(self._line(current))
        lines.extend(self._line(child) for child, entry in sorted(self._table.items())
                     if entry[0] == pid)
        return "\n".join(lines) + "\n"

    def _take_pid(self):
        self._next_pid += 1
        return self._next_pid

    def add_tree(self, zombie=False):
        """Fake counterpart of /api/spawn: parent -> 2 children -> 1 grandchild."""
        with self._lock:
            parent, first, second, grand = (self._take_pid() for _ in range(4))
            self._table[parent] = [_MOCK_SERVER_PID, "tree_parent", 1, 0]
            self._table[first] = [parent, "tree_child1", 1, 0]
            self._table[second] = [parent, "tree_child2",
                                   128 if zombie else 1, 32 if zombie else 0]
            self._table[grand] = [first, "tree_grand", 1, 0]
            self._trees.append((parent, first, second, grand))
        return {"parent": parent, "children": [first, second],
                "grandchildren": [grand], "zombies": [second] if zombie else []}

    def remove_trees(self):
        with self._lock:
            parents = [tree[0] for tree in self._trees]
            for tree in self._trees:
                for pid in tree:
                    self._table.pop(pid, None)
            self._trees = []
        return parents

    def active_trees(self):
        return len(self._trees)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Query /proc/pid and print JSON.")
    parser.add_argument("pid", help="PID to look up (0 resets)")
    parser.add_argument("--mock", action="store_true",
                        help="use the built-in fake process table")
    parser.add_argument("--proc-path", default=PROC_PATH)
    args = parser.parse_args(argv)
    bridge = MockProcBridge() if args.mock else ProcBridge(args.proc_path)
    print(json.dumps(bridge.query(args.pid), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
