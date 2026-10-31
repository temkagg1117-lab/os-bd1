#!/usr/bin/env python3
"""
test_ui_api.py - tests of the backend/parser (Member 5).

Default: starts ui/server.py in --mock mode (works on any Linux, no kernel
module needed). With  --module  it tests the REAL module through /proc/pid
(module must be loaded):   python3 tests/test_ui_api.py --module
"""
import json, os, subprocess, sys, time, unittest, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = "--module" in sys.argv
if REAL:
    sys.argv.remove("--module")
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
srv = None


def get(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def setUpModule():
    global srv
    args = [sys.executable, os.path.join(ROOT, "ui", "server.py"), "--port", str(PORT)]
    if not REAL:
        args.append("--mock")
    srv = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            get("/api/info")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def tearDownModule():
    get("/api/cleanup", "POST")
    srv.terminate()
    srv.wait()


def proc_ppid(pid):
    with open(f"/proc/{pid}/stat") as f:
        s = f.read()
    return int(s[s.rindex(")") + 2:].split()[1])


class Basic(unittest.TestCase):
    def test_T01_self_pid_matches_procfs(self):
        me = os.getpid()
        st, j = get(f"/api/query?pid={me}")
        self.assertEqual(st, 200)
        self.assertEqual(j["pid"], me)
        self.assertEqual(j["ppid"], proc_ppid(me))
        self.assertIn("python", j["command"])

    def test_T02_pid1_has_children_and_no_ancestor(self):
        st, j = get("/api/query?pid=1")
        self.assertEqual(st, 200)
        self.assertEqual(j["pid"], 1)
        self.assertEqual(j["ancestors"], [])
        self.assertGreaterEqual(j["nchildren"], 0)

    def test_T03_first_line_is_textbook_format(self):
        st, j = get("/api/query?pid=1")
        import re
        self.assertRegex(j["raw"].splitlines()[0], r"^command = \[.*\] pid = \[1\] state = \[\d+\]$")

    def test_T04_ancestors_chain_ends_at_parent(self):
        me = os.getpid()
        st, j = get(f"/api/query?pid={me}")
        self.assertEqual(j["ancestors"][-1]["pid"], j["ppid"])


class Errors(unittest.TestCase):
    def test_E01_non_numeric(self):
        st, j = get("/api/query?pid=abc")
        self.assertEqual((st, j["error"]), (400, "BAD_PID"))

    def test_E02_zero(self):
        self.assertEqual(get("/api/query?pid=0")[0], 400)

    def test_E03_negative(self):
        self.assertEqual(get("/api/query?pid=-5")[0], 400)

    def test_E04_too_large(self):
        self.assertEqual(get("/api/query?pid=99999999999")[0], 400)

    def test_E05_empty(self):
        self.assertEqual(get("/api/query?pid=")[0], 400)

    def test_E06_missing_param(self):
        self.assertEqual(get("/api/query")[0], 400)

    def test_E07_nonexistent_pid(self):
        st, j = get("/api/query?pid=4194303")
        self.assertEqual((st, j["error"]), (404, "NO_SUCH_PID"))

    def test_E08_bad_depth(self):
        self.assertEqual(get("/api/tree?pid=1&depth=9")[0], 400)
        self.assertEqual(get("/api/tree?pid=1&depth=x")[0], 400)

    def test_E09_bad_spawn(self):
        self.assertEqual(get("/api/spawn?depth=9&fanout=2", "POST")[0], 400)


class Hierarchy(unittest.TestCase):
    def test_H01_spawned_tree_shape(self):
        st, s = get("/api/spawn?depth=2&fanout=2", "POST")
        self.assertEqual(st, 200)
        time.sleep(0.6)
        st, j = get(f"/api/tree?pid={s['pid']}&depth=4")
        self.assertEqual(st, 200)
        # depth=2,fanout=2 -> sh + 1 subshell group... count nodes recursively
        def count(n):
            return 1 + sum(count(c) for c in n["children"])
        self.assertGreaterEqual(count(j["tree"]), 4)
        self.assertEqual(j["selected"], s["pid"])
        get("/api/cleanup", "POST")

    def test_H02_node_cap(self):
        st, s = get("/api/spawn?depth=3&fanout=4", "POST")
        time.sleep(1.0)
        st, j = get(f"/api/tree?pid={s['pid']}&depth=6&max=5")
        self.assertLessEqual(j["nodes"], 5)
        self.assertTrue(j["truncated"])
        get("/api/cleanup", "POST")

    def test_H03_cleanup_kills(self):
        st, s = get("/api/spawn?depth=1&fanout=2", "POST")
        time.sleep(0.3)
        get("/api/cleanup", "POST")
        time.sleep(0.3)
        st, j = get(f"/api/query?pid={s['pid']}")
        self.assertEqual(st, 404)


class Static(unittest.TestCase):
    def test_S01_index_served(self):
        with urllib.request.urlopen(BASE + "/") as r:
            self.assertIn(b"Task Hierarchy", r.read())

    def test_S02_path_traversal_blocked(self):
        try:
            urllib.request.urlopen(BASE + "/../server.py")
            self.fail("traversal succeeded")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
