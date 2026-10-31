#!/usr/bin/env python3
"""
server.py - backend of the Task hierarchy UI (Member 3)

Talks to the kernel module through /proc/pid exactly like the textbook:
    write "<pid>"  ->  read report
and serves the browser UI in ui/static/.

Modes
  real (default)  uses the kernel module entry   (--proc /proc/pid)
  --mock          emulates the module's output from /proc/<pid>/stat so the
                  UI can be tried on a machine WITHOUT the module loaded.
                  The UI shows a visible MOCK banner in this mode.

Only the Python standard library is used. Binds to 127.0.0.1 by default.
"""
import argparse, errno, json, os, re, signal, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PID_MAX = 4194304                      # PID_MAX_LIMIT on 64-bit Linux
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
FIELD = re.compile(r"(\w+)\s*=\s*\[(.*?)\]")
LOCK = threading.Lock()                # the module keeps ONE global pid
SPAWNED = []                           # demo process groups to clean up
CFG = {"proc": "/proc/pid", "mock": False}


class ApiError(Exception):
    def __init__(self, code, status, message):
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


# ---------------------------------------------------------------- mock ----
STATE_NAMES = {"R": "TASK_RUNNING", "S": "TASK_INTERRUPTIBLE",
               "D": "TASK_UNINTERRUPTIBLE", "T": "__TASK_STOPPED",
               "t": "__TASK_TRACED", "Z": "EXIT_ZOMBIE", "X": "EXIT_DEAD",
               "I": "TASK_INTERRUPTIBLE"}
STATE_NUM = {"R": 0, "S": 1, "I": 1, "D": 2, "T": 4, "t": 8, "Z": 0, "X": 0}


def _stat(pid):
    """-> (comm, state_char, ppid) from /proc/<pid>/stat or None."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            s = f.read()
    except OSError:
        return None
    l, r = s.index("("), s.rindex(")")
    rest = s[r + 2:].split()
    return s[l + 1:r], rest[0], int(rest[1])


def mock_report(pid):
    me = _stat(pid)
    if me is None:
        return ""
    comm, st, ppid = me
    out = [f"command = [{comm}] pid = [{pid}] state = [{STATE_NUM.get(st, 0)}]",
           f"state_name = [{STATE_NAMES.get(st, 'OTHER')}]"]
    par = _stat(ppid) if ppid > 0 else None
    out.append(f"ppid = [{ppid if par else 0}] parent_command = [{par[0] if par else '-'}]")
    chain, cur = [], ppid
    while par and len(chain) < 64:
        chain.append((cur, par))
        cur = par[2]
        par = _stat(cur) if cur > 0 else None
    kids = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            s = _stat(int(d))
            if s and s[2] == pid and int(d) != pid:
                kids.append((int(d), s))
    out.append(f"nchildren = [{len(kids)}]")
    for p, (c, s, _) in reversed(chain):
        out.append(f"ancestor: pid = [{p}] command = [{c}] state = [{STATE_NUM.get(s, 0)}]")
    for p, (c, s, _) in sorted(kids)[:128]:
        out.append(f"child: pid = [{p}] command = [{c}] state = [{STATE_NUM.get(s, 0)}]")
    if len(kids) > 128:
        out.append("truncated = [children]")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- module IO ----
def read_module(pid):
    """write pid, read report - the textbook protocol. Returns raw text."""
    if CFG["mock"]:
        return mock_report(pid)
    path = CFG["proc"]
    try:
        with LOCK:                      # keep write+read atomic for us
            with open(path, "w") as f:
                f.write(str(pid))
            with open(path, "r") as f:
                return f.read()
    except FileNotFoundError:
        raise ApiError("MODULE_NOT_LOADED", 503,
                       f"{path} олдсонгүй. Kernel module ачаалагдаагүй байна: "
                       "`sudo insmod src/task_info.ko` (эсвэл --mock ашиглана уу).")
    except PermissionError:
        raise ApiError("PERMISSION", 403, f"{path} руу бичих эрх алга (chmod/sudo шалгана уу).")
    except OSError as e:
        if e.errno == errno.EINVAL:
            raise ApiError("BAD_PID", 400, "Module энэ утгыг хүлээн авсангүй (EINVAL).")
        raise ApiError("IO", 500, f"/proc алдаа: {e.strerror}")


def parse(raw, pid):
    """Parse the module report into a dict. Empty text = no such task."""
    if not raw.strip():
        raise ApiError("NO_SUCH_PID", 404,
                       f"PID {pid} бүхий process олдсонгүй (module 0 byte буцаалаа).")
    res = {"children": [], "ancestors": [], "truncated": False}
    for line in raw.splitlines():
        f = dict(FIELD.findall(line))
        if line.startswith("ancestor:"):
            res["ancestors"].append({"pid": int(f["pid"]), "command": f["command"], "state": int(f["state"])})
        elif line.startswith("child:"):
            res["children"].append({"pid": int(f["pid"]), "command": f["command"], "state": int(f["state"])})
        elif line.startswith("command"):
            res.update(command=f["command"], pid=int(f["pid"]), state=int(f["state"]))
        elif line.startswith("state_name"):
            res["state_name"] = f["state_name"]
        elif line.startswith("ppid"):
            res.update(ppid=int(f["ppid"]), parent_command=f["parent_command"])
        elif line.startswith("nchildren"):
            res["nchildren"] = int(f["nchildren"])
        elif line.startswith("truncated"):
            res["truncated"] = True
    if "pid" not in res:
        raise ApiError("BAD_OUTPUT", 502, "Module-ийн гаралтыг задлаж чадсангүй.")
    res["raw"] = raw
    return res


def check_pid(text):
    try:
        pid = int(str(text).strip())
    except (TypeError, ValueError):
        raise ApiError("BAD_PID", 400, f"'{text}' бүхэл тоо биш байна. PID нь 1-ээс {PID_MAX} хүртэлх бүхэл тоо.")
    if pid < 1 or pid > PID_MAX:
        raise ApiError("BAD_PID", 400, f"PID {pid} хүрээнээс гадуур (1..{PID_MAX}).")
    return pid


def query(pid):
    return parse(read_module(pid), pid)


def build_tree(pid, depth, max_nodes):
    """Selected process + ancestors above it + descendants below (depth)."""
    top = query(pid)
    count = [1]
    queries = [1]

    def node(info, d):
        n = {"pid": info["pid"], "command": info["command"], "state": info["state"],
             "nchildren": info.get("nchildren", len(info["children"])), "children": []}
        if d >= depth:
            return n
        for c in info["children"]:
            if count[0] >= max_nodes:
                n["cut"] = True
                break
            count[0] += 1
            try:
                queries[0] += 1
                sub = query(c["pid"])
                n["children"].append(node(sub, d + 1))
            except ApiError:           # child exited between the two reads
                n["children"].append({"pid": c["pid"], "command": c["command"],
                                      "state": c["state"], "nchildren": 0, "children": [], "gone": True})
        return n

    root = node(top, 0)
    return {"selected": pid, "ancestors": top["ancestors"], "tree": root,
            "nodes": count[0], "queries": queries[0], "truncated": count[0] >= max_nodes,
            "state_name": top.get("state_name"), "ppid": top["ppid"],
            "parent_command": top["parent_command"], "raw": top["raw"]}


# ------------------------------------------------------------ demo spawn ----
def gen_cmd(depth, fan):
    if depth == 0:
        return "sleep 600"
    return "(" + " & ".join([gen_cmd(depth - 1, fan)] * fan) + " & wait)"


def spawn(depth, fan):
    if not (1 <= depth <= 3 and 1 <= fan <= 4):
        raise ApiError("BAD_PARAM", 400, "depth 1..3, fanout 1..4 байх ёстой.")
    p = subprocess.Popen(["sh", "-c", gen_cmd(depth, fan) + " & wait"],
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    SPAWNED.append(p)
    return p.pid


def kill_spawned():
    n = 0
    for p in SPAWNED:
        try:
            os.killpg(p.pid, signal.SIGTERM)
            n += 1
        except OSError:
            pass
        try:
            p.wait(timeout=2)
        except Exception:
            pass
    SPAWNED.clear()
    return n


# ----------------------------------------------------------------- HTTP ----
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, status, obj):
        b = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _route(self, method):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/api/info":
            return {"mode": "mock" if CFG["mock"] else "module", "proc": CFG["proc"], "self_pid": os.getpid()}
        if u.path == "/api/query":
            return query(check_pid(q.get("pid")))
        if u.path == "/api/tree":
            depth = int(q.get("depth", 2)) if str(q.get("depth", 2)).isdigit() else None
            if depth is None or not 0 <= depth <= 6:
                raise ApiError("BAD_PARAM", 400, "depth 0..6 байх ёстой.")
            mx = int(q.get("max", 200)) if str(q.get("max", 200)).isdigit() else 200
            return build_tree(check_pid(q.get("pid")), depth, min(max(mx, 1), 500))
        if u.path == "/api/spawn" and method == "POST":
            d, f = q.get("depth", "2"), q.get("fanout", "2")
            if not (d.isdigit() and f.isdigit()):
                raise ApiError("BAD_PARAM", 400, "depth, fanout бүхэл тоо байх ёстой.")
            return {"pid": spawn(int(d), int(f))}
        if u.path == "/api/cleanup" and method == "POST":
            return {"killed_groups": kill_spawned()}
        return None

    def _handle(self, method):
        try:
            r = self._route(method)
            if r is not None:
                return self._json(200, r)
            path = urlparse(self.path).path
            path = "/index.html" if path in ("/", "") else path
            fp = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
            if not fp.startswith(STATIC) or not os.path.isfile(fp):
                return self._json(404, {"error": "NOT_FOUND", "message": "Олдсонгүй"})
            with open(fp, "rb") as f:
                b = f.read()
            self.send_response(200)
            ct = {"html": "text/html", "js": "text/javascript", "css": "text/css"}.get(fp.rsplit(".", 1)[-1], "application/octet-stream")
            self.send_header("Content-Type", ct + "; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except ApiError as e:
            self._json(e.status, {"error": e.code, "message": e.message})
        except Exception as e:             # never leak a traceback to the UI
            self._json(500, {"error": "INTERNAL", "message": f"Дотоод алдаа: {e}"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proc", default="/proc/pid", help="module /proc entry (default /proc/pid)")
    ap.add_argument("--mock", action="store_true", help="emulate the module (no kernel module needed)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    CFG.update(proc=a.proc, mock=a.mock)
    srv = ThreadingHTTPServer((a.host, a.port), H)
    print(f"Task hierarchy UI: http://{a.host}:{a.port}/   mode={'MOCK' if a.mock else 'module ' + a.proc}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        kill_spawned()


if __name__ == "__main__":
    main()
