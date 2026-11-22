#!/usr/bin/env python3
"""F.CSM302 BD2 regression suite. Mock checks /proc, not the kernel module.

Usage:
  python3 -m unittest discover -s tests -p 'test_bd2_api.py' -v
  # optional, after loading real kernel module:
  python3 tests/test_bd2_api.py --module
"""
import http.client
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = "--module" in sys.argv
if REAL:
    sys.argv.remove("--module")
SRC = ROOT / "ui" / "server.py"
spec = importlib.util.spec_from_file_location("bd2_server", SRC)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


def request(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as ex:
        return ex.code, json.loads(ex.read())


def temporary_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class ProtocolTests(unittest.TestCase):
    SAMPLE = ("command = [a]b] pid = [123] state = [1]\n"
              "state_name = [TASK_INTERRUPTIBLE]\n"
              "ppid = [1] parent_command = [init]\n"
              "nchildren = [1]\n"
              "child: pid = [124] command = [c]d] state = [0]\n")

    def test_parse_preserves_command_containing_closing_bracket(self):
        data = backend.parse(self.SAMPLE, 123)
        self.assertEqual(data["command"], "a]b")
        self.assertEqual(data["children"][0]["command"], "c]d")

    def test_parse_rejects_malformed_report(self):
        with self.assertRaises(backend.ApiError) as ctx:
            backend.parse(self.SAMPLE.replace("nchildren = [1]", "nchildren = [oops]"), 123)
        self.assertEqual(ctx.exception.status, 502)

    def test_parse_rejects_mismatched_pid(self):
        with self.assertRaises(backend.ApiError) as ctx:
            backend.parse(self.SAMPLE, 124)
        self.assertEqual(ctx.exception.code, "BAD_OUTPUT")

    def test_parse_rejects_impossible_child_count(self):
        with self.assertRaises(backend.ApiError):
            backend.parse(self.SAMPLE.replace("nchildren = [1]", "nchildren = [0]"), 123)

    def test_parser_empty_report_is_404(self):
        with self.assertRaises(backend.ApiError) as ctx:
            backend.parse("", 4194303)
        self.assertEqual(ctx.exception.status, 404)

    def test_check_pid_rejects_signed_whitespace_and_invalid(self):
        for pid in [None, "", "abc", "0", "-1", "+1", "1.0", "4194305"]:
            with self.subTest(pid=pid), self.assertRaises(backend.ApiError):
                backend.check_pid(pid)
        self.assertEqual(backend.check_pid("  12  "), 12)

    def test_strict_integer_validation(self):
        for value in ["", "-1", "abc", "0", "501", "2.5"]:
            with self.subTest(value=value), self.assertRaises(backend.ApiError):
                backend.positive_int(value, "max", 1, 500)

    def test_state_not_faked(self):
        p = os.getpid()
        self.assertEqual(backend.parse(backend.mock_report(p), p)["pid"], p)


class LiveApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global BASE
        cls.port = temporary_port()
        BASE = f"http://127.0.0.1:{cls.port}"
        cmd = [sys.executable, str(SRC), "--port", str(cls.port)]
        if not REAL:
            cmd.append("--mock")
        cls.server = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(80):
            if cls.server.poll() is not None:
                raise RuntimeError("Backend terminated before startup")
            try:
                request("/api/info")
                return
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        cls.server.terminate()
        raise RuntimeError("Backend did not start")

    @classmethod
    def tearDownClass(cls):
        try:
            request("/api/cleanup", "POST")
        except Exception:
            pass
        cls.server.terminate()
        try:
            cls.server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.communicate()

    def test_info_mode(self):
        status, data = request("/api/info")
        self.assertEqual(status, 200)
        self.assertEqual(data["mode"], "module" if REAL else "mock")

    def test_query_self_matches_real_proc(self):
        pid = os.getpid()
        status, data = request(f"/api/query?pid={pid}")
        self.assertEqual(status, 200)
        self.assertEqual(data["pid"], pid)
        with open(f"/proc/{pid}/stat") as f:
            s = f.read()
        expected_ppid = int(s[s.rindex(")") + 2:].split()[1])
        self.assertEqual(data["ppid"], expected_ppid)

    def test_pid1_textbook_format(self):
        status, data = request("/api/query?pid=1")
        self.assertEqual(status, 200)
        self.assertRegex(data["raw"].splitlines()[0], r"^command = \[.*\] pid = \[1\] state = \[\d+\]$")

    def test_missing_and_invalid_pid(self):
        for pid in ["", "-1", "0", "abc", "4194305", "%2B1"]:
            with self.subTest(pid=pid):
                status, data = request(f"/api/query?pid={pid}")
                self.assertEqual((status, data["error"]), (400, "BAD_PID"))

    def test_invalid_depth_or_max_fails_not_clamped(self):
        for suffix in ["depth=-1", "depth=7", "depth=x", "max=0", "max=501", "max=no", "max="]:
            with self.subTest(suffix=suffix):
                status, data = request("/api/tree?pid=1&" + suffix)
                self.assertEqual((status, data["error"]), (400, "BAD_PARAM"))

    def test_depth_zero_has_no_descendants(self):
        status, data = request("/api/tree?pid=1&depth=0&max=1")
        self.assertEqual(status, 200)
        self.assertEqual(data["nodes"], 1)
        self.assertEqual(data["tree"]["children"], [])
        # The node limit does not mean truncation if no node was omitted.
        self.assertFalse(data["truncated"])

    def test_http_method_validation(self):
        self.assertEqual(request("/api/spawn")[0], 405)
        self.assertEqual(request("/api/query?pid=1", "POST")[0], 405)
        self.assertEqual(request("/", "POST")[0], 405)

    def test_static_traversal(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/../server.py")
        result = conn.getresponse()
        self.assertEqual(result.status, 404)
        result.read()
        conn.close()

    def test_static_symlink_escape_blocked(self):
        static = ROOT / "ui" / "static"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "secret.txt"
            target.write_text("NOT_PUBLIC", encoding="utf-8")
            link = static / "__bd2_escape_test.txt"
            if link.exists() or link.is_symlink():
                self.skipTest("Test symlink already exists")
            try:
                link.symlink_to(target)
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                conn.request("GET", "/__bd2_escape_test.txt")
                result = conn.getresponse()
                self.assertEqual(result.status, 404)
                self.assertNotIn(b"NOT_PUBLIC", result.read())
                conn.close()
            finally:
                link.unlink(missing_ok=True)

    def test_spawn_and_cleanup(self):
        status, data = request("/api/spawn?depth=1&fanout=2", "POST")
        self.assertEqual(status, 200)
        pid = data["pid"]
        time.sleep(.35)
        status, tree = request(f"/api/tree?pid={pid}&depth=3")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(tree["nodes"], 2)
        status, killed = request("/api/cleanup", "POST")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(killed["killed_groups"], 1)

    def test_spawn_fanout_validation(self):
        for suffix in ["depth=4&fanout=2", "depth=0&fanout=2", "depth=1&fanout=0", "depth=1&fanout=5", "depth=x&fanout=2"]:
            with self.subTest(suffix=suffix):
                self.assertEqual(request("/api/spawn?" + suffix, "POST")[0], 400)

    def test_demo_group_cap(self):
        try:
            for _ in range(3):
                self.assertEqual(request("/api/spawn?depth=1&fanout=1", "POST")[0], 200)
            code, data = request("/api/spawn?depth=1&fanout=1", "POST")
            self.assertEqual((code, data["error"]), (429, "DEMO_LIMIT"))
        finally:
            request("/api/cleanup", "POST")

    def test_index_served(self):
        with urllib.request.urlopen(BASE + "/", timeout=5) as r:
            body = r.read()
            self.assertIn(b"Task Hierarchy", body)
            self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")


if __name__ == "__main__":
    unittest.main(verbosity=2)
