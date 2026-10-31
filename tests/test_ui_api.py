#!/usr/bin/env python3
"""Black-box API tests for ui_server.py --mock (Python standard library only)."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SERVER = Path(os.environ.get("UI_SERVER", ROOT / "src" / "ui_server.py"))
STARTUP_TIMEOUT = 10
REQUEST_TIMEOUT = 3


def request(path, method="GET"):
    req = Request(BASE_URL + path, method=method)
    try:
        response = urlopen(req, timeout=REQUEST_TIMEOUT)
    except HTTPError as error:
        response = error
    with response:
        body = response.read().decode("utf-8")
        if "application/json" in response.headers.get("Content-Type", ""):
            body = json.loads(body)
        return response.status, body, response.headers


class UiApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global BASE_URL
        if not SERVER.is_file():
            raise RuntimeError(
                f"Backend server not found: {SERVER}. "
                "Merge the M3 backend first or set UI_SERVER to ui_server.py."
            )

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        BASE_URL = f"http://127.0.0.1:{port}"

        cls.server_process = subprocess.Popen(
            [
                sys.executable,
                str(SERVER),
                "--mock",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=SERVER.parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.monotonic() + STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if cls.server_process.poll() is not None:
                output = cls.server_process.stdout.read()
                raise RuntimeError(f"Backend exited during startup:\n{output}")
            try:
                with urlopen(BASE_URL + "/api/health", timeout=0.5):
                    break
            except (OSError, URLError):
                time.sleep(0.1)
        else:
            cls.stop_server()
            raise RuntimeError(f"Backend did not start within {STARTUP_TIMEOUT}s")

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()

    @classmethod
    def stop_server(cls):
        process = getattr(cls, "server_process", None)
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()

    def api(self, path, method="GET"):
        status, payload, headers = request(path, method)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertIsInstance(payload, dict)
        return status, payload

    def test_01_health_reports_mock_ready(self):
        status, body = self.api("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["module_loaded"])
        self.assertEqual(body["proc_path"], "(mock)")

    def test_02_init_pid_is_returned(self):
        status, body = self.api("/api/query?" + urlencode({"pid": "1"}))
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "OK")
        self.assertEqual(body["target"]["pid"], 1)
        self.assertEqual(body["target"]["command"], "systemd")
        self.assertEqual(body["counts"]["ancestors"], 0)

    def test_03_regular_process_has_expected_record(self):
        status, body = self.api("/api/query?" + urlencode({"pid": "1203"}))
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "OK")
        self.assertEqual(body["requested"], "1203")
        self.assertEqual(body["target"]["command"], "bash")
        self.assertEqual(body["target"]["ppid"], 1190)
        self.assertIn("command = [bash]", body["raw"])

    def test_04_ancestor_chain_is_root_first(self):
        _, body = self.api("/api/query?pid=1203")
        self.assertEqual([item["pid"] for item in body["ancestors"]], [1, 812, 1190])

    def test_05_existing_children_are_in_hierarchy(self):
        _, body = self.api("/api/query?pid=1203")
        child_pids = {item["pid"] for item in body["children"]}
        self.assertTrue({1511, 1630, 1702, 1888}.issubset(child_pids))
        self.assertEqual(body["counts"]["children"], len(body["children"]))

    def test_06_spawned_tree_can_be_queried(self):
        status, spawned = self.api("/api/spawn", "POST")
        self.assertEqual(status, 201)
        try:
            query_status, body = self.api(
                "/api/query?" + urlencode({"pid": str(spawned["parent"])})
            )
            self.assertEqual(query_status, 200)
            self.assertEqual(body["target"]["command"], "tree_parent")
            self.assertEqual(body["counts"]["children"], 2)
            self.assertEqual(body["counts"]["grandchildren"], 1)
        finally:
            self.api("/api/cleanup", "POST")

    def test_07_zero_pid_resets_selection(self):
        status, body = self.api("/api/query?pid=0")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "EMPTY")
        self.assertTrue(body["ok"])
        self.assertIsNone(body["target"])

    def test_08_unknown_pid_returns_not_found(self):
        status, body = self.api("/api/query?pid=4194303")
        self.assertEqual(status, 404)
        self.assertEqual(body["status"], "NOT_FOUND")
        self.assertFalse(body["ok"])

    def test_09_non_numeric_pid_is_rejected(self):
        status, body = self.api("/api/query?pid=abc")
        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "FORMAT_ERROR")

    def test_10_negative_pid_is_rejected(self):
        status, body = self.api("/api/query?pid=-5")
        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "BOUNDARY_ERROR")

    def test_11_pid_above_kernel_limit_is_rejected(self):
        status, body = self.api("/api/query?pid=4194305")
        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "BOUNDARY_ERROR")

    def test_12_oversized_pid_input_is_rejected(self):
        status, body = self.api("/api/query?pid=99999999999999999")
        self.assertEqual(status, 400)
        self.assertIn(body["error_code"], ("FORMAT_ERROR", "BOUNDARY_ERROR"))

    def test_13_missing_pid_is_rejected(self):
        status, body = self.api("/api/query")
        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "FORMAT_ERROR")

    def test_14_spawn_rejects_get_method(self):
        status, body = self.api("/api/spawn")
        self.assertEqual(status, 405)
        self.assertEqual(body["error_code"], "METHOD_NOT_ALLOWED")

    def test_15_query_rejects_post_method(self):
        status, body = self.api("/api/query?pid=1203", "POST")
        self.assertEqual(status, 405)
        self.assertEqual(body["error_code"], "METHOD_NOT_ALLOWED")

    def test_16_unknown_api_route_is_json_not_found(self):
        status, body = self.api("/api/unknown")
        self.assertEqual(status, 404)
        self.assertEqual(body["error_code"], "ROUTE_NOT_FOUND")

    def test_17_spawn_clamps_ttl_to_supported_range(self):
        status, body = self.api("/api/spawn?ttl=1", "POST")
        try:
            self.assertEqual(status, 201)
            self.assertEqual(body["ttl"], 5)
            self.assertIn("parent", body)
            self.assertEqual(len(body["children"]), 2)
        finally:
            self.api("/api/cleanup", "POST")

    def test_18_zombie_spawn_is_marked_and_cleaned(self):
        _, spawned = self.api("/api/spawn?zombie=1", "POST")
        try:
            _, body = self.api(
                "/api/query?" + urlencode({"pid": str(spawned["parent"])})
            )
            zombie_pids = {
                item["pid"]
                for item in body["children"]
                if item["state_name"] == "ZOMBIE"
            }
            self.assertTrue(set(spawned["zombies"]).issubset(zombie_pids))
        finally:
            cleanup_status, cleanup = self.api("/api/cleanup", "POST")
        self.assertEqual(cleanup_status, 200)
        self.assertEqual(cleanup["stopped_trees"], 1)

    def test_19_cleanup_is_idempotent(self):
        self.api("/api/cleanup", "POST")
        status, body = self.api("/api/cleanup", "POST")
        self.assertEqual(status, 200)
        self.assertEqual(body["stopped_trees"], 0)

    def test_20_static_handler_cannot_escape_its_directory(self):
        status, body, _ = request("/../proc_bridge.py")
        self.assertEqual(status, 404)
        self.assertNotIn("import argparse", body)


if __name__ == "__main__":
    if not SERVER.is_file():
        raise SystemExit(
            f"ERROR: backend server not found: {SERVER}\n"
            "Merge the M3 backend first or set UI_SERVER to ui_server.py."
        )
    unittest.main(verbosity=2)
