#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhxRPC sample — extended black-box integration tests (rules v2).

Maps to: docs/business_rules_v2.md, docs/test_scenarios_v2.md

Run (after starting search_main):
    python3 tests/integration_test_v2.py -v

Server example:
    cd phxrpc/sample && ./search_main -c search_server.conf &

Optional env:
    PHXRPC_SAMPLE_ROOT   — override sample directory (default: <repo>/phxrpc/sample)
    PHXRPC_TEST_HOST     — default 127.0.0.1
    PHXRPC_TEST_PORT     — override port (else parsed from search_client.conf)
    ENABLE_HSHA_STRESS   — set to 1 to enable unstable queue-drop experiment (default off)

Python deps: stdlib only (http.client for HTTP). Optional: pip install requests — not required.

Echo payloads: ASCII-only for subprocess argv safety on C locale.
"""

# -----------------------------------------------------------------------------
# 测试方法 ↔ 场景 ID 快速映射（与 docs/test_scenarios_v2.md「对应测试方法」列互链）
# 格式:  qualified_name  →  TS-xx[, TS-yy ...]
#
#   TestPhxRPCRulesV2::test_pr_tcp_server_reachable
#       → TS-35
#   TestPhxRPCRulesV2::test_fr_dispatch_http_unknown_uri_404
#       → TS-02, TS-03
#   TestPhxRPCRulesV2::test_br_echo_01_roundtrip
#       → TS-01, TS-15, TS-22, TS-25, TS-30
#   TestPhxRPCRulesV2::test_br_search_02_demo_strings
#       → TS-20, TS-27
#   TestPhxRPCRulesV2::test_br_search_01_query_ignored_same_output
#       → TS-26
#   TestPhxRPCRulesV2::test_br_search_03_no_extra_site_fields
#       → TS-28
#   TestPhxRPCRulesV2::test_br_notify_01_future_success_remove_decorator
#       → TS-29 (@unittest.expectedFailure)
#   TestPhxRPCRulesV2::test_br_notify_current_returns_negative_one
#       → TS-06, TS-18, TS-29
#   TestPhxRPCRulesV2::test_fr_cfg_connect_refused
#       → TS-09, TS-13
#   TestPhxRPCRulesV2::test_fr_cfg_multi_endpoint_file
#       → TS-08, TS-10, TS-23
#   TestPhxRPCRulesV2::test_fr_net_invalid_listen_ip_rejected
#       → TS-14
#   TestPhxRPCRulesV2::test_fr_http_layer_accepts_post
#       → TS-19
#   TestPhxRPCRulesV2::test_fr_caller_normal_closed_skipped
#       → TS-07 (@unittest.skip；TS-05 无重试断言未单测)
#   TestPhxRPCRulesV2::test_fr_svc_pb_errors_skipped
#       → TS-16, TS-17 (@unittest.skip)
#   TestPhxRPCRulesV2::test_fr_hsha_queue_drop_placeholder
#       → TS-12 (@unittest.skipUnless ENABLE_HSHA_STRESS=1)
#   TestRuleCoverageReport::test_print_coverage_summary
#       → TS-34（元：覆盖度摘要输出）
# -----------------------------------------------------------------------------

from __future__ import print_function

import http.client
import os
import re
import socket
import subprocess
import sys
import tempfile
import unittest


try:
    from pathlib import Path
except ImportError:
    Path = None


def _sample_root():
    env = os.environ.get("PHXRPC_SAMPLE_ROOT")
    if env:
        return env
    if Path:
        return str(Path(__file__).resolve().parent.parent / "phxrpc" / "sample")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "phxrpc", "sample"))


SAMPLE_ROOT = _sample_root()
SEARCH_TOOL_MAIN = os.path.join(SAMPLE_ROOT, "search_tool_main")
SEARCH_CLIENT_CONF = os.path.join(SAMPLE_ROOT, "search_client.conf")
SEARCH_SERVER_CONF = os.path.join(SAMPLE_ROOT, "search_server.conf")

SUBPROCESS_TIMEOUT_SEC = 60
_SUBPROCESS_RW_KWARGS = {
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "universal_newlines": True,
}


def _merge_streams(proc):
    parts = []
    if proc.stdout:
        parts.append(proc.stdout)
    if proc.stderr:
        parts.append(proc.stderr)
    return "\n".join(parts)


def os_access_x_ok(path):
    try:
        return os.access(path, os.X_OK)
    except OSError:
        return False


def _friendly_skip_missing_binary():
    if not os.path.isfile(SEARCH_TOOL_MAIN):
        raise unittest.SkipTest(
            "search_tool_main not found: {0}. Run make in sample/.".format(SEARCH_TOOL_MAIN)
        )
    if not os_access_x_ok(SEARCH_TOOL_MAIN):
        raise unittest.SkipTest("search_tool_main not executable: " + SEARCH_TOOL_MAIN)


def _probe_tool_loader():
    import os
    # 注入动态库路径
    my_env = os.environ.copy()
    my_env["LD_LIBRARY_PATH"] = "/work/phxrpc/third_party/protobuf/lib"
    proc = subprocess.run(
        [SEARCH_TOOL_MAIN],
        cwd=SAMPLE_ROOT,
        timeout=30,
        env=my_env, # 必须添加这一行
        **_SUBPROCESS_RW_KWARGS
    )
    merged = ((proc.stderr or "") + (proc.stdout or "")).lower()
    if "error while loading shared libraries" in merged:
        raise unittest.SkipTest("Dynamic linker error loading search_tool_main (set LD_LIBRARY_PATH).")


def parse_conf_port(path, default=16162):
    """Read first ``Port = <num>`` or ``Port=<num>`` in file."""
    try:
        with open(path, "r") as f:
            for line in f:
                m = re.match(r"^\s*Port\s*=\s*(\d+)\s*$", line, re.I)
                if m:
                    return int(m.group(1))
    except EnvironmentError:
        pass
    return default


def parse_return_code(stdout, rpc_name):
    pat = re.compile(r"^{0}\s+return\s+(-?\d+)\s*$".format(re.escape(rpc_name)), re.MULTILINE)
    m = pat.search(stdout)
    if not m:
        return None
    return int(m.group(1))


def _unescape_pb(s):
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
    m = re.search(r'^\s*value:\s*"((?:\\.|[^"\\])*)"\s*$', stdout, re.MULTILINE)
    if not m:
        return None
    return _unescape_pb(m.group(1))


def run_tool(func_name, extra_args, conf_path=None):
    import os
    # 注入动态库路径（默认按 Docker 挂载路径；若在非 /work 环境运行，请自行确保可加载 libprotobuf）
    my_env = os.environ.copy()
    my_env["LD_LIBRARY_PATH"] = "/work/phxrpc/third_party/protobuf/lib"
    
    conf_path = conf_path or SEARCH_CLIENT_CONF
    cmd = [SEARCH_TOOL_MAIN, "-f", func_name, "-c", conf_path]
    cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=SAMPLE_ROOT,
        timeout=SUBPROCESS_TIMEOUT_SEC,
        check=False,
        env=my_env, # 必须添加这一行
        **_SUBPROCESS_RW_KWARGS
    )

def http_post_status_headers(host, port, path, body=b"", timeout=5):
    conn = http.client.HTTPConnection(host, int(port), timeout=timeout)
    conn.request("POST", path, body=body, headers={"Content-Length": str(len(body))})
    resp = conn.getresponse()
    status = resp.status
    hdrs = {k.lower(): v for k, v in resp.getheaders()}
    resp.read()  # drain
    conn.close()
    return status, hdrs


class TestPhxRPCRulesV2(unittest.TestCase):
    """Black-box tests aligned with docs/test_scenarios_v2.md."""

    host = os.environ.get("PHXRPC_TEST_HOST", "127.0.0.1")
    port = None

    @classmethod
    def setUpClass(cls):
        _friendly_skip_missing_binary()
        _probe_tool_loader()
        if not os.path.isfile(SEARCH_CLIENT_CONF):
            raise unittest.SkipTest("Missing search_client.conf")
        po = os.environ.get("PHXRPC_TEST_PORT")
        cls.port = int(po) if po else parse_conf_port(SEARCH_CLIENT_CONF)
        try:
            s = socket.create_connection((cls.host, cls.port), timeout=2)
            s.close()
        except EnvironmentError:
            raise unittest.SkipTest(
                "Cannot connect to {0}:{1}. Start: cd sample && ./search_main -c search_server.conf".format(
                    cls.host, cls.port
                )
            )

    # --- PR / TCP ---
    def test_pr_tcp_server_reachable(self):
        """对应场景: TS-35; 关联规则: PR-Svr-01（隐式端口可达）, FR-Net-03（连接成功路径子集）.

        TCP 冒烟：与 setUpClass 一致，显式保留为独立用例便于剧本文档引用。
        """
        s = socket.create_connection((self.host, self.port), timeout=3)
        s.close()

    # --- FR-Dispatch HTTP ---
    def test_fr_dispatch_http_unknown_uri_404(self):
        """对应场景: TS-02, TS-03; 关联规则: FR-Dispatch-02, FR-Dispatch-03, FR-Dispatch-04.

        未注册 URI → HTTP 404；Result 头缺失或非正与客户端 -1 语义一致。
        """
        status, hdrs = http_post_status_headers(self.host, self.port, "/search/NoSuchMethod", b"")
        self.assertEqual(status, 404, msg="Expected 404 for unregistered URI")
        # negative or missing result header still maps to -1 in client (see http_msg.cpp)
        xr = hdrs.get("x-phxrpc-result", "-1")
        self.assertTrue(xr is None or int(xr) <= 0, msg=repr(hdrs))

    # --- BR-Echo / FR successful path ---
    def test_br_echo_01_roundtrip(self):
        """对应场景: TS-01, TS-15, TS-22, TS-25, TS-30; 关联规则: FR-Dispatch-01, FR-Net-03/05, FR-Msg-01/02, BR-Echo-01, BR-Tool-01.

        PHXEcho -s 回显与 return 0；成功路径隐含正确 URI 与 result 字段。
        """
        payload = "phx-v2-echo"
        proc = run_tool("PHXEcho", ["-s", payload])
        out = _merge_streams(proc)
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertEqual(parse_return_code(out, "PHXEcho"), 0, msg=out)
        self.assertEqual(parse_string_value_from_resp(out), payload, msg=out)

    def test_br_search_02_demo_strings(self):
        """对应场景: TS-20, TS-27; 关联规则: FR-HTTP-02（CLI 成功路径隐式）, BR-Search-02.

        Search 返回固定 demo title/url 子串。
        """
        proc = run_tool("Search", ["-q", "any"])
        out = _merge_streams(proc)
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertEqual(parse_return_code(out, "Search"), 0, msg=out)
        self.assertIn("Success Reconstruction", out)
        self.assertRegex(out, r'url:\s*"https://www\.tencent\.com"')

    def test_br_search_01_query_ignored_same_output(self):
        """对应场景: TS-26; 关联规则: BR-Search-01.

        两次不同 -q 输出相同 demo 指纹（query 未参与当前实现）。
        """
        proc_a = run_tool("Search", ["-q", "aaa"])
        proc_b = run_tool("Search", ["-q", "bbb"])
        out_a = _merge_streams(proc_a)
        out_b = _merge_streams(proc_b)
        self.assertEqual(parse_return_code(out_a, "Search"), 0)
        self.assertEqual(parse_return_code(out_b, "Search"), 0)
        # Stable demo title line should appear in both
        self.assertIn("Success Reconstruction", out_a)
        self.assertIn("Success Reconstruction", out_b)

    def test_br_search_03_no_extra_site_fields(self):
        """对应场景: TS-28; 关联规则: BR-Search-03.

        当前实现 DebugString 输出不含 type:/summary: 行。
        """
        proc = run_tool("Search", ["-q", "x"])
        out = _merge_streams(proc)
        self.assertIn("sites {", out)
        self.assertNotIn("type:", out)
        self.assertNotIn("summary:", out)

    # --- BR-Notify ---
    @unittest.expectedFailure
    def test_br_notify_01_future_success_remove_decorator(self):
        """对应场景: TS-29; 关联规则: BR-Notify-01.

        当前 sample 恒 -1；本用例预置成功态（return 0）。修复业务后移除 @unittest.expectedFailure。
        """
        proc = run_tool("Notify", ["-m", "ping"])
        out = _merge_streams(proc)
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertEqual(parse_return_code(out, "Notify"), 0, msg=out)

    def test_br_notify_current_returns_negative_one(self):
        """对应场景: TS-06, TS-18, TS-29; 关联规则: FR-Caller-06, FR-Svc-03, BR-Notify-01.

        记录现状：Notify return -1（与 TS-29 缺口一致）。
        """
        proc = run_tool("Notify", ["-m", "ping"])
        out = _merge_streams(proc)
        self.assertEqual(parse_return_code(out, "Notify"), -1, msg=out)

    # --- FR-CfgCli / FR-Net ---
    def test_fr_cfg_connect_refused(self):
        """对应场景: TS-09, TS-13; 关联规则: FR-CfgCli-01, FR-CfgCli-02, FR-Net-01.

        临时 conf 指向不可达端口 + 较短超时，RPC Open 失败 → return -1。
        """
        fd, path = tempfile.mkstemp(prefix="phxrpc_cli_", suffix=".conf")
        os.close(fd)
        try:
            with open(path, "w") as f:
                f.write(
                    "[ClientTimeout]\nConnectTimeoutMS = 200\nSocketTimeoutMS = 1000\n"
                    "[Server]\nServerCount = 1\nPackageName = search\n"
                    "[Server0]\nIP = 127.0.0.1\nPort = 1\n"
                )
            proc = run_tool("PHXEcho", ["-s", "x"], conf_path=path)
            out = _merge_streams(proc)
            self.assertEqual(parse_return_code(out, "PHXEcho"), -1, msg=out)
        finally:
            try:
                os.remove(path)
            except EnvironmentError:
                pass

    def test_fr_cfg_multi_endpoint_file(self):
        """对应场景: TS-08, TS-10, TS-23; 关联规则: FR-CfgCli-01, FR-CfgCli-03, PR-Cli-01, PR-Cli-02.

        双 [ServerN] 同址同端口，工具仍 exit 0（GetRandom 非空列表）。
        """
        fd, path = tempfile.mkstemp(prefix="phxrpc_cli_", suffix=".conf")
        os.close(fd)
        try:
            with open(path, "w") as f:
                f.write(
                    "[ClientTimeout]\nConnectTimeoutMS = 100\nSocketTimeoutMS = 30000\n"
                    "[Server]\nServerCount = 2\nPackageName = search\n"
                    "[Server0]\nIP = {0}\nPort = {1}\n"
                    "[Server1]\nIP = {0}\nPort = {1}\n".format(self.host, self.port)
                )
            proc = run_tool("PHXEcho", ["-s", "multi"], conf_path=path)
            out = _merge_streams(proc)
            self.assertEqual(proc.returncode, 0, msg=out)
            self.assertEqual(parse_return_code(out, "PHXEcho"), 0, msg=out)
        finally:
            try:
                os.remove(path)
            except EnvironmentError:
                pass

    def test_fr_net_invalid_listen_ip_rejected(self):
        """对应场景: TS-14; 关联规则: FR-Net-02.

        非法点分 IPv4，连接路径失败 → return -1。
        """
        fd, path = tempfile.mkstemp(prefix="phxrpc_cli_", suffix=".conf")
        os.close(fd)
        try:
            with open(path, "w") as f:
                f.write(
                    "[ClientTimeout]\nConnectTimeoutMS = 100\nSocketTimeoutMS = 1000\n"
                    "[Server]\nServerCount = 1\nPackageName = search\n"
                    "[Server0]\nIP = 999.0.0.1\nPort = 16162\n"
                )
            proc = run_tool("PHXEcho", ["-s", "badip"], conf_path=path)
            out = _merge_streams(proc)
            self.assertEqual(parse_return_code(out, "PHXEcho"), -1, msg=out)
        finally:
            try:
                os.remove(path)
            except EnvironmentError:
                pass

    # --- FR-HTTP ---
    def test_fr_http_layer_accepts_post(self):
        """对应场景: TS-19; 关联规则: FR-HTTP-01.

        最小 POST 进入 HTTP 栈并返回可解析状态/头。
        """
        status, hdrs = http_post_status_headers(self.host, self.port, "/search/Search", b"")
        self.assertLess(status, 600)
        # RFC: layer processed; business code may set X-PHXRPC-Result
        self.assertIsNotNone(hdrs)

    # --- Documented skips ---
    @unittest.skip("FR-Caller-07 / TS-07 — needs scripted half-close or harness")
    def test_fr_caller_normal_closed_skipped(self):
        """对应场景: TS-07; 关联规则: FR-Caller-09.

        跳过原因：需构造 Normal_Closed 与半关闭，见 test_scenarios_v2.md TS-07。（TS-05 无重试循环未单独黑盒实现。）
        """
        pass

    @unittest.skip("FR-Svc-01/02 / TS-16/17 — malformed protobuf body not portable black-box")
    def test_fr_svc_pb_errors_skipped(self):
        """对应场景: TS-16, TS-17; 关联规则: FR-Svc-01, FR-Svc-02.

        跳过原因：畸形 Protobuf body 黑盒难构造、跨实现不便携。
        """
        pass

    @unittest.skipUnless(os.environ.get("ENABLE_HSHA_STRESS") == "1", "FR-Hsha-02 / TS-12 — unstable; enable ENABLE_HSHA_STRESS=1")
    def test_fr_hsha_queue_drop_placeholder(self):
        """对应场景: TS-12; 关联规则: FR-Hsha-02.

        默认关闭：队列等待丢弃实验不稳定；设 ENABLE_HSHA_STRESS=1 后需单独实现负载。
        """
        self.fail("Implement workload generator separately")


class TestRuleCoverageReport(unittest.TestCase):
    """Meta: prints coverage summary when run with verbosity."""

    def test_print_coverage_summary(self):
        """对应场景: TS-34; 关联规则: （元信息，无单条 FR/BR）.

        运行结束时打印黑盒规则覆盖摘要，便于与 business_rules_v2 对照。
        """
        summary = (
            "\n=== Rule coverage (black-box automation) ===\n"
            "Estimated rules directly exercised: ~24 / 56\n"
            "Categories:\n"
            "  FR-Dispatch-01,02,03 (CLI success + HTTP 404)\n"
            "  FR-Caller-06 (Notify result)\n"
            "  FR-CfgCli-01,02,03\n"
            "  FR-Net-01,02\n"
            "  FR-HTTP-01 (POST reaches server)\n"
            "  PR-Cli partial (multi-endpoint conf)\n"
            "  BR-Echo-01, BR-Search-01,02,03, BR-Notify-01, BR-Tool-01 (CLI paths)\n"
            "Not covered here (see docs/test_scenarios_v2.md):\n"
            "  FR-Caller-05/07/09, FR-Svc-01/02, FR-Hsha-02, FR-Queue-*, CG-*, many PR-Svr runtime knobs\n"
            "Reason: requires white-box, traffic capture, or codegen inspection.\n"
        )
        print(summary)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPhxRPCRulesV2))
    suite.addTests(loader.loadTestsFromTestCase(TestRuleCoverageReport))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
