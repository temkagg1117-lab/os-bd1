#!/usr/bin/env python3
"""Task Information /proc backend for F.CSM302 BD2.

Real mode uses the Linux kernel module at /proc/pid. Mock mode reads actual
Linux /proc/<pid>/stat (not synthetic test data) and is visibly labelled.
Only Python standard-library packages are needed at runtime.
"""
import argparse
import errno
import json
import os
import re
import signal
import subprocess
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PID_MAX = 4194304
STATIC = os.path.realpath(os.path.join(os.path.dirname(__file__), "static"))
LOCK = threading.Lock()   # The kernel module keeps one globally selected PID
SPAWN_LOCK = threading.Lock()
SPAWNED = []
MAX_SPAWN_GROUPS = 3
CFG = {"proc": "/proc/pid", "mock": False}

STATE_NAMES = {
    "R": "TASK_RUNNING", "S": "TASK_INTERRUPTIBLE",
    "D": "TASK_UNINTERRUPTIBLE", "T": "__TASK_STOPPED",
    "t": "__TASK_TRACED", "Z": "EXIT_ZOMBIE",
    "X": "EXIT_DEAD", "I": "TASK_INTERRUPTIBLE",
}
STATE_NUM = {"R": 0, "S": 1, "I": 1, "D": 2, "T": 4, "t": 8, "Z": 0, "X": 0}
LINE_MAIN = re.compile(r"^command = \[(.*)\] pid = \[(\d+)\] state = \[(\d+)\]$")
LINE_REL = re.compile(r"^(ancestor|child): pid = \[(\d+)\] command = \[(.*)\] state = \[(\d+)\]$")
LINE_PARENT = re.compile(r"^ppid = \[(\d+)\] parent_command = \[(.*)\]$")
LINE_STATE = re.compile(r"^state_name = \[(.+)\]$")
LINE_CHILD_COUNT = re.compile(r"^nchildren = \[(\d+)\]$")


class ApiError(Exception):
    def __init__(self, code, status, message):
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


def _stat(pid):
    """Read one real Linux process stat entry. PID can exit during this call."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as f:
            line = f.read()
        left, right = line.index("("), line.rindex(")")
        fields = line[right + 2:].split()
        return line[left + 1:right], fields[0], int(fields[1])
    except (OSError, ValueError, IndexError):
        return None


def mock_report(pid):
    """Generate the same protocol as the module using observed /proc data."""
    me = _stat(pid)
    if me is None:
        return ""
    comm, state, ppid = me
    out = [
        f"command = [{comm}] pid = [{pid}] state = [{STATE_NUM.get(state, 0)}]",
        f"state_name = [{STATE_NAMES.get(state, 'OTHER')}]",
    ]
    parent = _stat(ppid) if ppid > 0 else None
    out.append(f"ppid = [{ppid if parent else 0}] parent_command = [{parent[0] if parent else '-'}]")
    chain, cur = [], ppid
    seen = {pid}
    while parent is not None and len(chain) < 64 and cur not in seen:
        seen.add(cur)
        chain.append((cur, parent))
        cur = parent[2]
        parent = _stat(cur) if cur > 0 else None
    children = []
    try:
        proc_entries = os.listdir("/proc")
    except OSError:
        proc_entries = []
    for entry in proc_entries:
        if entry.isdigit():
            child_pid = int(entry)
            child = _stat(child_pid)
            if child and child[2] == pid and child_pid != pid:
                children.append((child_pid, child))
    out.append(f"nchildren = [{len(children)}]")
    for ancestor_pid, (name, st, _) in reversed(chain):
        out.append(f"ancestor: pid = [{ancestor_pid}] command = [{name}] state = [{STATE_NUM.get(st, 0)}]")
    for child_pid, (name, st, _) in sorted(children)[:128]:
        out.append(f"child: pid = [{child_pid}] command = [{name}] state = [{STATE_NUM.get(st, 0)}]")
    if len(children) > 128:
        out.append("truncated = [children]")
    return "\n".join(out) + "\n"


def read_module(pid):
    """Write the selected PID and read its report under the server's lock."""
    if CFG["mock"]:
        return mock_report(pid)
    path = CFG["proc"]
    try:
        with LOCK:
            with open(path, "w", encoding="ascii") as f:
                f.write(str(pid))
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    except FileNotFoundError:
        raise ApiError("MODULE_NOT_LOADED", 503,
                       f"{path} байхгүй. `sudo insmod src/task_info.ko` эсвэл --mock хэрэглэнэ үү.")
    except PermissionError:
        raise ApiError("PERMISSION", 403, f"{path} файлд хандах эрх алга.")
    except OSError as ex:
        if ex.errno == errno.EINVAL:
            raise ApiError("BAD_PID", 400, "Kernel module PID-ийг хүлээн авсангүй (EINVAL).")
        raise ApiError("IO", 500, "Kernel module-ээс уншихад алдаа гарлаа.")


def parse(raw, pid):
    """Strictly validate the text protocol, preserving bracketed command names."""
    if not raw.strip():
        raise ApiError("NO_SUCH_PID", 404, f"PID {pid} бүхий процесс олдсонгүй.")
    result = {"children": [], "ancestors": [], "truncated": False}
    for line in raw.splitlines():
        m = LINE_MAIN.fullmatch(line)
        if m:
            result.update(command=m.group(1), pid=int(m.group(2)), state=int(m.group(3)))
            continue
        m = LINE_REL.fullmatch(line)
        if m:
            record = {"pid": int(m.group(2)), "command": m.group(3), "state": int(m.group(4))}
            result["ancestors" if m.group(1) == "ancestor" else "children"].append(record)
            continue
        m = LINE_PARENT.fullmatch(line)
        if m:
            result.update(ppid=int(m.group(1)), parent_command=m.group(2))
            continue
        m = LINE_STATE.fullmatch(line)
        if m:
            result["state_name"] = m.group(1)
            continue
        m = LINE_CHILD_COUNT.fullmatch(line)
        if m:
            result["nchildren"] = int(m.group(1))
            continue
        if line == "truncated = [children]":
            result["truncated"] = True
            continue
        # Recognized prefixes must not silently become partial/corrupt results.
        if line.startswith(("command", "ancestor:", "child:", "ppid", "state_name", "nchildren", "truncated")):
            raise ApiError("BAD_OUTPUT", 502, "Kernel module буруу форматтай мэдээлэл буцаалаа.")
    required = {"pid", "command", "state", "ppid", "parent_command", "nchildren", "state_name"}
    if not required.issubset(result) or result["pid"] != pid:
        raise ApiError("BAD_OUTPUT", 502,
                       "Module-ийн хариулт дутуу эсвэл өөр PID буцаасан (зэрэгцээ хандалт байж болно).")
    if result["nchildren"] < len(result["children"]):
        raise ApiError("BAD_OUTPUT", 502, "Module-ийн child тоо буруу байна.")
    result["raw"] = raw
    return result


def check_pid(text):
    text = str(text).strip() if text is not None else ""
    if not re.fullmatch(r"[0-9]+", text):
        raise ApiError("BAD_PID", 400, f"'{text}' зөв бүхэл PID биш. 1..{PID_MAX} байх ёстой.")
    pid = int(text)
    if not 1 <= pid <= PID_MAX:
        raise ApiError("BAD_PID", 400, f"PID {pid} хүрээнээс гадуур (1..{PID_MAX}).")
    return pid


def query(pid):
    return parse(read_module(pid), pid)


def build_tree(pid, depth, max_nodes):
    """Requested node + all ancestors + descendants within depth / node cap."""
    top = query(pid)
    count, queries = [1], [1]
    had_cut = [bool(top["truncated"])]
    visited = {pid}

    def build(info, current_depth):
        source_cut = info["truncated"] or info["nchildren"] > len(info["children"])
        n = {"pid": info["pid"], "command": info["command"], "state": info["state"],
             "nchildren": info["nchildren"], "children": [], "source_truncated": bool(source_cut),
             "zombie": info.get("state_name", "").startswith("EXIT_")}
        if source_cut:
            had_cut[0] = True
        if current_depth >= depth:
            return n
        for child in info["children"]:
            if child["pid"] in visited:
                n["cut"] = True
                had_cut[0] = True
                continue
            if count[0] >= max_nodes:
                n["cut"] = True
                had_cut[0] = True
                break
            count[0] += 1
            visited.add(child["pid"])
            try:
                queries[0] += 1
                detail = query(child["pid"])
                n["children"].append(build(detail, current_depth + 1))
            except ApiError as ex:
                if ex.code != "NO_SUCH_PID":
                    raise
                n["children"].append({"pid": child["pid"], "command": child["command"],
                                      "state": child["state"], "nchildren": 0,
                                      "children": [], "gone": True})
        return n

    return {"selected": pid, "ancestors": top["ancestors"], "tree": build(top, 0),
            "nodes": count[0], "queries": queries[0], "truncated": had_cut[0],
            "state_name": top["state_name"], "ppid": top["ppid"],
            "parent_command": top["parent_command"], "raw": top["raw"]}


def gen_cmd(depth, fanout):
    if depth == 0:
        return "sleep 600"
    return "(" + " & ".join([gen_cmd(depth - 1, fanout)] * fanout) + " & wait)"


def spawn(depth, fanout):
    if not (1 <= depth <= 3 and 1 <= fanout <= 4):
        raise ApiError("BAD_PARAM", 400, "depth 1..3, fanout 1..4 байх ёстой.")
    with SPAWN_LOCK:
        SPAWNED[:] = [p for p in SPAWNED if p.poll() is None]
        if len(SPAWNED) >= MAX_SPAWN_GROUPS:
            raise ApiError("DEMO_LIMIT", 429,
                           "3 туршилтын мод ажиллаж байна. 'Цэвэрлэх' дараад дахин оролдоно уу.")
        p = subprocess.Popen(["sh", "-c", gen_cmd(depth, fanout) + " & wait"],
                             start_new_session=True, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
        SPAWNED.append(p)
        return p.pid


def kill_spawned():
    with SPAWN_LOCK:
        processes = list(SPAWNED)
        SPAWNED.clear()
    count = 0
    for p in processes:
        try:
            os.killpg(p.pid, signal.SIGTERM)
            count += 1
        except ProcessLookupError:
            pass
        except PermissionError:
            pass
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    return count


def positive_int(value, name, minimum, maximum):
    if not re.fullmatch(r"[0-9]+", str(value)):
        raise ApiError("BAD_PARAM", 400, f"{name} нь {minimum}..{maximum} бүхэл тоо байна.")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ApiError("BAD_PARAM", 400, f"{name} нь {minimum}..{maximum} байх ёстой.")
    return number


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[backend] " + (fmt % args) + "\n")

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self, method):
        url = urlparse(self.path)
        params = {k: values[0] for k, values in parse_qs(url.query, keep_blank_values=True).items()}
        if url.path in ("/api/info", "/api/query", "/api/tree") and method != "GET":
            raise ApiError("METHOD_NOT_ALLOWED", 405, "Энд зөвхөн GET хүсэлт зөвшөөрнө.")
        if url.path in ("/api/spawn", "/api/cleanup") and method != "POST":
            raise ApiError("METHOD_NOT_ALLOWED", 405, "Энд зөвхөн POST хүсэлт зөвшөөрнө.")
        if url.path == "/api/info":
            return {"mode": "mock" if CFG["mock"] else "module", "proc": CFG["proc"], "self_pid": os.getpid()}
        if url.path == "/api/query":
            return query(check_pid(params.get("pid")))
        if url.path == "/api/tree":
            pid = check_pid(params.get("pid"))
            depth = positive_int(params.get("depth", "2"), "depth", 0, 6)
            limit = positive_int(params.get("max", "200"), "max", 1, 500)
            return build_tree(pid, depth, limit)
        if url.path == "/api/spawn":
            depth = positive_int(params.get("depth", "2"), "depth", 1, 3)
            fanout = positive_int(params.get("fanout", "2"), "fanout", 1, 4)
            return {"pid": spawn(depth, fanout)}
        if url.path == "/api/cleanup":
            return {"killed_groups": kill_spawned()}
        return None

    def _handle(self, method):
        try:
            if len(self.path) > 2048:
                raise ApiError("URI_TOO_LONG", 414, "Хүсэлтийн урт хэтэрсэн.")
            result = self._route(method)
            if result is not None:
                return self._json(200, result)
            if method != "GET":
                raise ApiError("METHOD_NOT_ALLOWED", 405, "Статик файлд GET ашиглана.")
            path = urlparse(self.path).path
            if path in ("", "/"):
                path = "/index.html"
            file_path = os.path.realpath(os.path.join(STATIC, path.lstrip("/")))
            if os.path.commonpath((STATIC, file_path)) != STATIC or not os.path.isfile(file_path):
                raise ApiError("NOT_FOUND", 404, "Хуудас олдсонгүй.")
            with open(file_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            kind = {"html": "text/html", "js": "text/javascript", "css": "text/css",
                    "svg": "image/svg+xml", "png": "image/png"}.get(file_path.rsplit(".", 1)[-1],
                                                              "application/octet-stream")
            self.send_header("Content-Type", kind + ("; charset=utf-8" if kind.startswith("text/") else ""))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except ApiError as ex:
            self._json(ex.status, {"error": ex.code, "message": ex.message})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            traceback.print_exc()
            self._json(500, {"error": "INTERNAL", "message": "Дотоод алдаа. Server log-ийг шалгана уу."})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proc", default="/proc/pid")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    opts = ap.parse_args()
    CFG.update(proc=opts.proc, mock=opts.mock)
    srv = ThreadingHTTPServer((opts.host, opts.port), H)
    srv.daemon_threads = True
    print(f"Task hierarchy UI: http://{opts.host}:{opts.port}/   mode={'MOCK' if opts.mock else 'module'}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        kill_spawned()


if __name__ == "__main__":
    main()
