# PhxRPC — Test Scenarios (mapped to `docs/business_rules_v2.md`)


| Metadata        | Value                                                 |
| --------------- | ----------------------------------------------------- |
| Related BRD/FRD | `docs/business_rules_v2.md`                           |
| Sample root     | `phxrpc/sample/` (tests are under repo root `tests/`) |


**Legend — implementation column**


| Value  | Meaning                                                      |
| ------ | ------------------------------------------------------------ |
| CLI    | `search_tool_main` via `subprocess`                          |
| HTTP   | `http.client` (stdlib) against `search_main`                 |
| CONF   | temporary `search_client.conf` variant                       |
| TCP    | socket reachability / refusal                                |
| SKIP   | scenario documented but automated test `@skip` (environment) |
| STATIC | verification by codegen / inspection only (CG-*)             |


**Legend — 对应测试方法列**


| 取值                                                             | 含义                                            |
| -------------------------------------------------------------- | --------------------------------------------- |
| `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_`*      | 已实现自动化（方法名与剧本文档互链）                            |
| `tests/integration_test_v2.py::TestRuleCoverageReport::test_*` | 元测试（覆盖度摘要等）                                   |
| `Skipped (…)`                                                  | 仓库中已有占位用例但被 `@skip` / `skipUnless` 跳过，括号内为方法名 |
| `Not automated`                                                | 当前无对应用例（静态审查、白盒或待补充）                          |


---

## Scenario table (≥30)


| 场景ID  | 关联规则ID                          | 测试目标                                   | 前置条件                        | 输入/操作                                    | 预期结果                                             | 实现方式                        | 对应测试方法                                                                                                                                                                                |
| ----- | ------------------------------- | -------------------------------------- | --------------------------- | ---------------------------------------- | ------------------------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TS-01 | FR-Dispatch-01                  | URI 字符串与映射表键完全一致方可命中                   | 服务运行                        | CLI 发起合法 RPC（隐式正确 URI）                   | 返回码 0，业务 `return` 行显示成功                          | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_echo_01_roundtrip`（与其它成功 CLI 共用隐含）                                                                                          |
| TS-02 | FR-Dispatch-02                  | 未命中 URI 时仍写入 `result`（默认 -1）           | 服务运行                        | HTTP POST 到未注册路径                         | 响应 `404`，`X-PHXRPC-Result` 或缺失时为 -1              | HTTP                        | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_dispatch_http_unknown_uri_404`                                                                                              |
| TS-03 | FR-Dispatch-03 / FR-Dispatch-04 | 分发失败标记 `DISPATCH_ERROR`                | 服务运行                        | 同上                                       | HTTP 状态 **404** `Not Found`（与 `http_msg.cpp` 一致） | HTTP                        | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_dispatch_http_unknown_uri_404`                                                                                              |
| TS-04 | FR-Dispatch-05                  | `FakeReason` 与 HTTP 状态联动               | 静态已验证                       | —                                        | `DISPATCH_ERROR` → 404                           | STATIC                      | Not automated                                                                                                                                                                         |
| TS-05 | FR-Caller-02 / 07               | 单次 `Send`+`Recv`，无重试循环                 | 服务运行                        | 正常 RPC                                   | 成功路径返回 0；**无重试**需抓包或白盒                           | CLI + SKIP 注释               | Not automated（无重试需白盒；`test_fr_caller_normal_closed_skipped` 仅覆盖 TS-07）                                                                                                                |
| TS-06 | FR-Caller-06                    | 最终错误码来自 `resp_->result()`              | 服务运行                        | `Notify` RPC                             | 控制台 `Notify return -1`                           | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_notify_current_returns_negative_one`                                                                                        |
| TS-07 | FR-Caller-09                    | `Normal_Closed` 不计致命发送错误               | 需构造关闭                       | —                                        | 不易黑盒                                             | SKIP                        | Skipped (`test_fr_caller_normal_closed_skipped`)                                                                                                                                      |
| TS-08 | FR-CfgCli-01                    | 读取多个 `[ServerN]`                       | 模板 conf                     | 临时 conf 含 Server0/Server1                | `Read` 成功且工具可调通                                  | CONF+CLI                    | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_cfg_multi_endpoint_file`                                                                                                    |
| TS-09 | FR-CfgCli-02                    | `ConnectTimeoutMS` / `SocketTimeoutMS` | 可写临时文件                      | 缩小超时 + 错误端口                              | 快速失败（连接拒绝或超时）                                    | CONF+CLI                    | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_cfg_connect_refused`                                                                                                        |
| TS-10 | FR-CfgCli-03                    | `GetRandom()` 从非空列表选取                  | 双 endpoint 同机               | 多次调用（概率）                                 | 均可达（统计上不严格证明随机）                                  | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_cfg_multi_endpoint_file`                                                                                                    |
| TS-11 | FR-CfgCli-04                    | 缺省超时默认值                                | 代码静态                        | —                                        | 见 `client_config.cpp` 默认 200/5000 ms             | STATIC                      | Not automated                                                                                                                                                                         |
| TS-12 | FR-Hsha-02                      | 队列等待 ≥500ms 丢弃                         | 高压+慢处理                      | —                                        | 不稳定；性能环境                                         | SKIP                        | Skipped (`test_fr_hsha_queue_drop_placeholder`，默认 `ENABLE_HSHA_STRESS≠1`）                                                                                                             |
| TS-13 | FR-Net-01                       | 连接超时参数传入 `Poll`                        | 拒绝连接地址                      | 临时 conf 指向空闲端口                           | Open 失败                                          | CONF+CLI                    | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_cfg_connect_refused`                                                                                                        |
| TS-14 | FR-Net-02                       | 非法 IP 字符串拒绝                            | —                           | 无效 IP 段（若工具校验）                           | 连接失败                                             | CONF+CLI（依赖实现）              | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_net_invalid_listen_ip_rejected`                                                                                             |
| TS-15 | FR-Net-03 / 05                  | 连接成功路径与监控封装                            | 正常服务                        | 正常调用                                     | 成功                                               | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_echo_01_roundtrip`（及 Search 成功用例隐含）                                                                                         |
| TS-16 | FR-Svc-01                       | `ToPb` 失败 → `-EINVAL`                  | 需畸形 body                    | —                                        | 黑盒难构造                                            | SKIP                        | Skipped (`test_fr_svc_pb_errors_skipped`)                                                                                                                                             |
| TS-17 | FR-Svc-02                       | `FromPb` 失败 → `-ENOMEM`                | 需畸形响应                       | —                                        | 黑盒难构造                                            | SKIP                        | Skipped (`test_fr_svc_pb_errors_skipped`)                                                                                                                                             |
| TS-18 | FR-Svc-03                       | `Notify` 可不 `FromPb` empty body        | 服务运行                        | Notify                                   | 返回行为符合监控行                                        | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_notify_current_returns_negative_one`                                                                                        |
| TS-19 | FR-HTTP-01                      | HTTP 请求进入 `HttpProtocol::RecvReq`      | 服务运行                        | 任意合法 POST                                | 可解析并路由                                           | HTTP                        | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_http_layer_accepts_post`                                                                                                    |
| TS-20 | FR-HTTP-02                      | 响应经 `GenResponse`/`Modify`             | 成功 RPC                      | CLI Search                               | 正常 200 路径（隐式）                                    | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_search_02_demo_strings`（CLI Search 成功）                                                                                      |
| TS-21 | FR-Queue-01 / 02                | `ThdQueue` 阻塞/非阻塞                      | 仅线程模型                       | —                                        | 单元级更合适                                           | STATIC                      | Not automated                                                                                                                                                                         |
| TS-22 | FR-Msg-01 / 02                  | URI/result 字段存在                        | 由成功调用隐含                     | —                                        | 成功即说明链路使用 URI/result                             | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_echo_01_roundtrip`（及 Search 成功用例隐含）                                                                                         |
| TS-23 | PR-Cli-01 / 02                  | 客户端 INI 节                              | 临时 conf                     | 合法多段                                     | 工具 exit 0                                        | CONF+CLI                    | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_fr_cfg_multi_endpoint_file`                                                                                                    |
| TS-24 | PR-Svr-01 / 03                  | 服务端 Bind/Port/队列等                      | 静态                          | `search_server.conf`                     | 与 `HshaServerConfig` 字段对应                        | STATIC                      | Not automated                                                                                                                                                                         |
| TS-25 | BR-Echo-01                      | Echo 回显                                | 服务运行                        | `-s` ASCII                               | `value` 一致                                       | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_echo_01_roundtrip`                                                                                                          |
| TS-26 | BR-Search-01                    | `query` 未参与当前逻辑                        | 服务运行                        | 两次不同 `-q`                                | 输出相同 demo 子串                                     | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_search_01_query_ignored_same_output`                                                                                        |
| TS-27 | BR-Search-02                    | 固定 demo `title`/`url`                  | 服务运行                        | Search                                   | 含固定字符串                                           | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_search_02_demo_strings`                                                                                                     |
| TS-28 | BR-Search-03                    | 缺少 type/summary                        | 服务运行                        | 检查 DebugString 输出                        | 无 type/summary 字段行                               | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_search_03_no_extra_site_fields`                                                                                             |
| TS-29 | BR-Notify-01                    | 当前恒 `-1`                               | 服务运行                        | Notify                                   | `Notify return -1`；未来改为 0 后移 `@expectedFailure`  | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_notify_current_returns_negative_one`；`test_br_notify_01_future_success_remove_decorator`（`@unittest.expectedFailure` 预置成功态） |
| TS-30 | BR-Tool-01                      | `-s` 驱动 Echo                           | 服务运行                        | PHXEcho                                  | return 0                                         | CLI                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_br_echo_01_roundtrip`                                                                                                          |
| TS-31 | BR-Tool-02 / 03                 | `-q`/`-m` 未写入请求（TODO）                  | 代码现状                        | Search/Notify                            | 行为与未填一致                                          | CLI + expectedFailure 或断言缺失 | Not automated（无专门断言用例；现状由 BR 文档与 TS-26/29 间接体现）                                                                                                                                       |
| TS-32 | CG-URI-01 / CG-Bin-01           | 生成物 URI/Cmd 一致                         | 仓库                          | 比对 `phxrpc_search_stub.cpp` 与 dispatcher | 静态一致                                             | STATIC                      | Not automated                                                                                                                                                                         |
| TS-33 | CG-* 合计                         | 生成器正确性                                 | —                           | `codegen/` 可执行文件存在                       | 已在 BRD 声明静态覆盖                                    | STATIC                      | Not automated                                                                                                                                                                         |
| TS-34 | （元）                             | 运行结束打印黑盒规则覆盖摘要                         | 执行 `integration_test_v2.py` | —                                        | 控制台输出覆盖类别与缺口说明                                   | META                        | `tests/integration_test_v2.py::TestRuleCoverageReport::test_print_coverage_summary`                                                                                                   |
| TS-35 | PR-Svr-01 / FR-Net-03           | 配置端口 TCP 可达（冒烟）                        | 服务运行                        | `socket.create_connection`               | 连接成功                                             | TCP                         | `tests/integration_test_v2.py::TestPhxRPCRulesV2::test_pr_tcp_server_reachable`（`setUpClass` 亦做同类探测）                                                                                  |


---

## 与 `integration_test_v2.py` 的映射（索引）

- **按场景查代码**：见上表最后一列「对应测试方法」；反向从 `integration_test_v2.py` 文件头注释块「测试方法 ↔ 场景 ID 快速映射」可查 TS 列表。
- **自动化（默认执行）**：TS-01~~03, TS-06, TS-08~~10, TS-13~~15, TS-18~~20, TS-22~~23, TS-25~~30, TS-34~35 等（部分场景与其它场景共用同一测试方法）。
- **显式跳过**：TS-07（`test_fr_caller_normal_closed_skipped`）；TS-12（`test_fr_hsha_queue_drop_placeholder`，需 `ENABLE_HSHA_STRESS=1`）；TS-16/17（`test_fr_svc_pb_errors_skipped`）。
- **预期失败**：TS-29 对应 `test_br_notify_01_future_success_remove_decorator`（`@unittest.expectedFailure`，待 BR-Notify-01 修复后移除装饰器）。
- **仅文档 / 静态 / 未实现**：TS-04, TS-05, TS-11, TS-21, TS-24, TS-31~33 等见表中 `Not automated` 或 `Skipped`。

---

## 运行前置

1. 编译 `phxrpc/sample/search_main`、`phxrpc/sample/search_tool_main`。
2. 启动服务（示例）：`cd phxrpc/sample && ./search_main -c search_server.conf`（后台或另一终端）。
3. 执行测试（从仓库根目录）：`python3 tests/integration_test_v2.py -v`
4. 可选 HTTP 相关：无需 `pip install requests`（使用标准库 `http.client`）。

---

## 修订记录


| 版本  | 日期         | 说明                                       |
| --- | ---------- | ---------------------------------------- |
| 1.0 | 2026-05-10 | 初版，对齐 56 条规则与 v2 集成测试                    |
| 1.1 | 2026-05-11 | 增加「对应测试方法」列；补充 TS-34/TS-35；索引节与测试文件头映射互链 |


