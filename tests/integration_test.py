#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end integration tests for the PhxRPC Search sample (CLI tool path).

Runs search_tool_main via subprocess against a live search_main.

BRD/FRD rule IDs: docs/business_rules_v2.md
Test scenarios: docs/test_scenarios_v2.md

Usage:
    python3 tests/integration_test.py -v

Requirements:
    - Python 3.6+
    - Built search_tool_main and search_client.conf pointing at the server (default 127.0.0.1:16162)
    - Running search_main

Echo payloads must stay ASCII-only so argv survives POSIX environments where the locale
encoding is ascii (UnicodeEncodeError in subprocess otherwise).
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path


# Script lives under repo root tests/; sample root is phxrpc/sample.
SAMPLE_ROOT = Path(__file__).resolve().parent.parent / "phxrpc" / "sample"
SEARCH_TOOL_MAIN = SAMPLE_ROOT / "search_tool_main"
SEARCH_CLIENT_CONF = SAMPLE_ROOT / "search_client.conf"

# Wall-clock guard for subprocess (not RPC timeout); see test scenarios doc.
SUBPROCESS_TIMEOUT_SEC = 60

# Python 3.6: no capture_output/text= ; use PIPE + universal_newlines
_SUBPROCESS_RW_KWARGS = {
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "universal_newlines": True,
}


def _friendly_skip_missing_binary():
    """Skip with a clear hint if the CLI binary is missing or not executable."""
    if not SEARCH_TOOL_MAIN.is_file():
        raise unittest.SkipTest(
            "search_tool_main not found: {0}\n"
            "Run make under {1} and ensure search_main is configured to listen.".format(
                SEARCH_TOOL_MAIN, SAMPLE_ROOT
            )
        )
    if not os_access_x_ok(SEARCH_TOOL_MAIN):
        raise unittest.SkipTest(
            "search_tool_main exists but is not executable: {0}\n"
            "Try: chmod +x search_tool_main".format(SEARCH_TOOL_MAIN)
        )


def _friendly_skip_loader_error(proc):
    """Skip when the dynamic linker fails (often missing protobuf on LD_LIBRARY_PATH)."""
    merged = ((proc.stderr or "") + (proc.stdout or "")).lower()
    if "error while loading shared libraries" in merged or (
        proc.returncode == 127 and ("no such file" in merged or "cannot open shared object" in merged)
    ):
        excerpt = (proc.stderr or proc.stdout or "").strip()[:500]
        raise unittest.SkipTest(
            "search_tool_main failed to load shared libraries (e.g. libprotobuf).\n"
            "Run tests in the same environment as the build, or set LD_LIBRARY_PATH.\n"
            "Output excerpt: {0}".format(excerpt)
        )


def _probe_tool_dynamic_loader():
    """Probe once so every test does not repeat the same linker failure."""
    proc = subprocess.run(
        [str(SEARCH_TOOL_MAIN)],
        cwd=str(SAMPLE_ROOT),
        timeout=30,
        **_SUBPROCESS_RW_KWARGS
    )
    _friendly_skip_loader_error(proc)


def os_access_x_ok(path):
    """Best-effort executable check (POSIX os.X_OK)."""
    try:
        import os

        return os.access(str(path), os.X_OK)
    except OSError:
        return False

def run_search_tool(func_name, extra_args):
    import os
    # 核心修改：确保子进程能找到 protobuf 库
    my_env = os.environ.copy()
    my_env["LD_LIBRARY_PATH"] = "/work/phxrpc/third_party/protobuf/lib"

    cmd = [
        str(SEARCH_TOOL_MAIN),
        "-f",
        func_name,
        "-c",
        str(SEARCH_CLIENT_CONF),
    ]
    cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=str(SAMPLE_ROOT),
        timeout=SUBPROCESS_TIMEOUT_SEC,
        check=False,
        env=my_env,  # 注入环境变量
        **_SUBPROCESS_RW_KWARGS
    )

def parse_return_code(stdout, rpc_name):
    """Parse a line like ``PHXEcho return 0`` from tool stdout."""
    pat = re.compile(r"^{0}\s+return\s+(-?\d+)\s*$".format(re.escape(rpc_name)), re.MULTILINE)
    m = pat.search(stdout)
    if not m:
        return None
    return int(m.group(1))


def _unescape_protobuf_debug_string(s):
    """Decode escapes inside protobuf DebugString double-quoted segments."""
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "\\":
                out.append("\\")
                i += 2
                continue
            if n == '"':
                out.append('"')
                i += 2
                continue
            if n == "n":
                out.append("\n")
                i += 2
                continue
            if n == "r":
                out.append("\r")
                i += 2
                continue
            if n == "t":
                out.append("\t")
                i += 2
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


def parse_string_value_from_resp(stdout):
    """Extract google.protobuf.StringValue ``value`` from DebugString output.

    BR-Echo-01: echoed value must match the request.
    """
    m = re.search(r'^\s*value:\s*"((?:\\.|[^"\\])*)"\s*$', stdout, re.MULTILINE)
    if not m:
        return None
    return _unescape_protobuf_debug_string(m.group(1))


class TestSearchToolIntegration(unittest.TestCase):
    """Integration tests driven by search_tool_main."""

    @classmethod
    def setUpClass(cls):
        _friendly_skip_missing_binary()
        _probe_tool_dynamic_loader()
        if not SEARCH_CLIENT_CONF.is_file():
            raise unittest.SkipTest(
                "Missing {0}. Keep sample/search_client.conf with a reachable Server endpoint.".format(
                    SEARCH_CLIENT_CONF
                )
            )

    def test_phx_echo_round_trip(self):
        """TS-ECHO-01 / BR-Echo-01 / FR-Result: -s round-trip and return 0."""
        # ASCII only: avoids UnicodeEncodeError when subprocess encodes argv under C locale.
        payload = "phx-echo-smoke"
        proc = run_search_tool("PHXEcho", ["-s", payload])
        out = self._merge_streams(proc)
        self.assertEqual(
            proc.returncode,
            0,
            msg="Unexpected exit code {0}\n{1}".format(proc.returncode, out),
        )
        code = parse_return_code(out, "PHXEcho")
        self.assertIsNotNone(code, msg="Missing PHXEcho return line:\n{0}".format(out))
        self.assertEqual(code, 0, msg=out)
        parsed = parse_string_value_from_resp(out)
        self.assertIsNotNone(parsed, msg="Missing value field:\n{0}".format(out))
        self.assertEqual(parsed, payload, msg=out)

    def test_search_contains_demo_fields(self):
        """TS-SEARCH-01 / BR-Search-01 / BR-Search-03 / FR-Result: demo title/url in response."""
        proc = run_search_tool("Search", ["-q", "smoke"])
        out = self._merge_streams(proc)
        self.assertEqual(proc.returncode, 0, msg="exit {0}\n{1}".format(proc.returncode, out))
        code = parse_return_code(out, "Search")
        self.assertIsNotNone(code, msg=out)
        self.assertEqual(code, 0, msg=out)
        self.assertIn("Success Reconstruction", out, msg=out)
        self.assertRegex(out, r'url:\s*"https://www\.tencent\.com"', msg=out)

    @unittest.expectedFailure
    def test_notify_expected_success_when_fixed(self):
        """TS-NOTIFY-01 / BR-Notify-01 / BR-Notify-02 / FR-Result.

        Today Notify returns -1; remove @expectedFailure once the server returns 0.
        """
        proc = run_search_tool("Notify", ["-m", "ping"])
        out = self._merge_streams(proc)
        self.assertEqual(proc.returncode, 0, msg="exit {0}\n{1}".format(proc.returncode, out))
        code = parse_return_code(out, "Notify")
        self.assertIsNotNone(code, msg=out)
        self.assertEqual(code, 0, msg=out)

    @staticmethod
    def _merge_streams(proc):
        """Join stdout and stderr for failure messages."""
        parts = []
        if proc.stdout:
            parts.append(proc.stdout)
        if proc.stderr:
            parts.append(proc.stderr)
        return "\n".join(parts)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
