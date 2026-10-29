#!/usr/bin/env python3
"""ui_server.py - HTTP server for the Task Hierarchy UI (Python 3 stdlib only).

    python3 src/ui_server.py                 # real /proc/pid, http://127.0.0.1:8080
    python3 src/ui_server.py --mock          # fake process table, no kernel module

Static files (index.html, style.css, app.js) are served from src/static/.

API - every response is JSON, errors included:

    GET  /api/query?pid=<text>   hierarchy of a process (see proc_bridge.py)
    POST /api/spawn[?ttl=300&zombie=1]
                                 start parent -> 2 children -> 1 grandchild
    POST /api/cleanup            stop every tree started by /api/spawn
    GET  /api/health             is the kernel module loaded?

/api/query answers 200 for OK and EMPTY, 404 for NOT_FOUND, 400 for
FORMAT_ERROR / BOUNDARY_ERROR, 503 when the module is not loaded.
"""
import argparse
import json
import os
import select
import signal
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from proc_bridge import (ERR_MODULE, ERR_PARSE, ERR_PERMISSION, PROC_PATH,
                         STATUS_NOT_FOUND, MockProcBridge, ProcBridge)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

DEFAULT_TTL, MIN_TTL, MAX_TTL = 300, 5, 600   # seconds a spawned tree stays alive
MAX_TREES = 8                                 # spawned trees alive at once
SPAWN_TIMEOUT = 5.0                           # seconds to wait for the launcher

_HTTP_BY_ERROR = {ERR_MODULE: 503, ERR_PERMISSION: 403, ERR_PARSE: 502}
_GET_ONLY = ("/api/query", "/api/health")
_POST_ONLY = ("/api/spawn", "/api/cleanup")

# Runs as its own interpreter so that os.fork() makes real kernel tasks:
#   tree_parent -> tree_child1 -> tree_grand
#               -> tree_child2   (a zombie when `zombie` is set: it exits and
#                                 the parent never wait()s for it)
_TREE_LAUNCHER = r'''
import ctypes, json, os, select, sys, time

ttl = int(sys.argv[1])
make_zombie = sys.argv[2] == "1"

def set_name(name):
    try:
        ctypes.CDLL(None).prctl(15, name.encode(), 0, 0, 0)    # PR_SET_NAME
    except Exception:
        pass

def idle():
    time.sleep(ttl)

def fork_task(name, body):
    pid = os.fork()
    if pid == 0:
        set_name(name)
        body()
        os._exit(0)
    return pid

read_fd, write_fd = os.pipe()

def child_with_grandchild():
    os.write(write_fd, str(fork_task("tree_grand", idle)).encode())
    idle()

set_name("tree_parent")
child_a = fork_task("tree_child1", child_with_grandchild)
child_b = fork_task("tree_child2", (lambda: None) if make_zombie else idle)
os.close(write_fd)
if not select.select([read_fd], [], [], 5)[0]:
    print(json.dumps({"error": "grandchild did not start"}), flush=True)
    sys.exit(1)
grandchild = int(os.read(read_fd, 32))
print(json.dumps({"parent": os.getpid(), "children": [child_a, child_b],
                  "grandchildren": [grandchild],
                  "zombies": [child_b] if make_zombie else []}), flush=True)
idle()
'''


class SpawnError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class TreeRegistry:
    """Starts process trees for /api/spawn and stops them for /api/cleanup."""

    def __init__(self):
        self._lock = threading.Lock()
        self._launchers = []

    def _prune(self):
        self._launchers = [proc for proc in self._launchers if proc.poll() is None]

    def active(self):
        with self._lock:
            self._prune()
            return len(self._launchers)

    def spawn(self, ttl, zombie):
        if not hasattr(os, "fork"):
            raise SpawnError(501, "Процесс үүсгэх нь зөвхөн Linux дээр ажиллана "
                             "(эсвэл --mock ашиглана уу).")
        with self._lock:
            self._prune()
            if len(self._launchers) >= MAX_TREES:
                raise SpawnError(429, "Асаалттай мод хэт олон байна (дээд хязгаар "
                                 "%d). Эхлээд /api/cleanup дуудна уу." % MAX_TREES)
            proc = subprocess.Popen(
                [sys.executable, "-c", _TREE_LAUNCHER, str(ttl), "1" if zombie else "0"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True)
            try:
                info = self._read_info(proc)
            except SpawnError:
                self._stop(proc)
                raise
            self._launchers.append(proc)
        return info

    @staticmethod
    def _read_info(proc):
        ready = select.select([proc.stdout], [], [], SPAWN_TIMEOUT)[0]
        data = os.read(proc.stdout.fileno(), 4096) if ready else b""
        proc.stdout.close()
        line = data.decode("utf-8", errors="replace").strip()
        try:
            info = json.loads(line.splitlines()[0])
        except (ValueError, IndexError):
            raise SpawnError(500, "Мод үүсгэгч ассангүй: %s" % (line[-300:] or "хариу алга"))
        if "error" in info:
            raise SpawnError(500, info["error"])
        return info

    @staticmethod
    def _stop(proc):
        """SIGTERM the launcher's whole process group, SIGKILL if it lingers."""
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                pass
        proc.poll()

    def cleanup(self):
        with self._lock:
            launchers, self._launchers = self._launchers, []
        for proc in launchers:
            self._stop(proc)
        return [proc.pid for proc in launchers]


class MockTrees:
    """Same interface as TreeRegistry, but edits the mock process table."""

    def __init__(self, bridge):
        self._bridge = bridge

    def active(self):
        return self._bridge.active_trees()

    def spawn(self, ttl, zombie):
        return self._bridge.add_tree(zombie)

    def cleanup(self):
        return self._bridge.remove_trees()


def http_status(result):
    """HTTP status for a proc_bridge result."""
    if result["ok"]:
        return 200
    if result["status"] == STATUS_NOT_FOUND:
        return 404
    return _HTTP_BY_ERROR.get(result["error_code"], 400)


def _int_param(params, name, default, low, high):
    try:
        return max(low, min(high, int(params[name][0])))
    except (KeyError, IndexError, ValueError):
        return default


class Handler(SimpleHTTPRequestHandler):
    server_version = "TaskInfoUI/1.0"
    bridge = None       # set by main()
    trees = None

    def _send_json(self, payload, status=200, headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _api_error(self, status, code, message, headers=()):
        self._send_json({"ok": False, "status": "ERROR", "error_code": code,
                         "message": message}, status, headers)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/query":
            raw = parse_qs(url.query).get("pid", [""])[0]
            result = self.bridge.query(raw)
            self._send_json(result, http_status(result))
        elif url.path == "/api/health":
            self._send_json({"ok": True, "module_loaded": self.bridge.available(),
                             "proc_path": self.bridge.proc_path,
                             "active_trees": self.trees.active()})
        elif url.path in _POST_ONLY:
            self._api_error(405, "METHOD_NOT_ALLOWED", "POST ашиглана уу.",
                            [("Allow", "POST")])
        elif url.path.startswith("/api/"):
            self._api_error(404, "ROUTE_NOT_FOUND", "Ийм API байхгүй: " + url.path)
        else:
            super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        self._discard_body()
        if url.path == "/api/spawn":
            self._spawn(parse_qs(url.query))
        elif url.path == "/api/cleanup":
            parents = self.trees.cleanup()
            self._send_json({"ok": True, "stopped_trees": len(parents),
                             "parents": parents})
        elif url.path in _GET_ONLY:
            self._api_error(405, "METHOD_NOT_ALLOWED", "GET ашиглана уу.",
                            [("Allow", "GET")])
        else:
            self._api_error(404, "ROUTE_NOT_FOUND", "Ийм API байхгүй: " + url.path)

    def _spawn(self, params):
        ttl = _int_param(params, "ttl", DEFAULT_TTL, MIN_TTL, MAX_TTL)
        zombie = params.get("zombie", ["0"])[0].lower() in ("1", "true", "yes")
        try:
            info = self.trees.spawn(ttl, zombie)
        except SpawnError as exc:
            self._api_error(exc.status, "SPAWN_FAILED", str(exc))
            return
        self._send_json(dict(info, ok=True, ttl=ttl), 201)

    def _discard_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return
        if 0 < length <= 65536:
            self.rfile.read(length)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Task Hierarchy UI server")
    parser.add_argument("--host", default="127.0.0.1",
                        help="address to bind (default: 127.0.0.1, local only)")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--proc-path", default=PROC_PATH)
    parser.add_argument("--static", default=STATIC_DIR, help="folder with the UI files")
    parser.add_argument("--mock", action="store_true",
                        help="use a fake process table instead of /proc/pid")
    args = parser.parse_args(argv)

    if args.mock:
        Handler.bridge = MockProcBridge()
        Handler.trees = MockTrees(Handler.bridge)
    else:
        Handler.bridge = ProcBridge(args.proc_path)
        Handler.trees = TreeRegistry()

    server = ThreadingHTTPServer((args.host, args.port),
                                 partial(Handler, directory=args.static))
    server.daemon_threads = True
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    print("Task Hierarchy UI: http://%s:%d/  (%s)" % (
        args.host, args.port, "mock data" if args.mock else args.proc_path))
    if not Handler.bridge.available():
        print("WARNING: %s not found - load the module first (sudo insmod task_info.ko)"
              % args.proc_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        Handler.trees.cleanup()


if __name__ == "__main__":
    main()
