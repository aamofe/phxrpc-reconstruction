# PhxRPC — Test Scenarios (mapped to `docs/business_rules_v2.md`)

| Metadata | Value |
|----------|--------|
| Related BRD/FRD | `docs/business_rules_v2.md` |
| Sample root | `phxrpc/sample/` (tests are under repo root `tests/`) |

**Legend — implementation column**

| Value | Meaning |
|-------|---------|
| CLI | `search_tool_main` via `subprocess` |
| HTTP | `http.client` (stdlib) against `search_main` |
| CONF | temporary `search_client.conf` variant |
| TCP | socket reachability / refusal |
| SKIP | scenario documented but automated test `@skip` (environment) |
| STATIC | verification by codegen / inspection only (CG-*) |

---

## Scenario table (≥30)

| 场景ID | 关联规则ID | 测试目标 | 前置条件 | 输入/操作 | 预期结果 | 实现方式 |
|--------|-------------|----------|----------|-----------|----------|----------|
| TS-01 | FR-Dispatch-01 | URI 字符串与映射表键完全一致方可命中 | 服务运行 | CLI 发起合法 RPC（隐式正确 URI） | 返回码 0，业务 `return` 行显示成功 | CLI |
| TS-02 | FR-Dispatch-02 | 未命中 URI 时仍写入 `result`（默认 -1） | 服务运行 | HTTP POST 到未注册路径 | 响应 `404`，`X-PHXRPC-Result` 或缺失时为 -1 | HTTP |
| TS-03 | FR-Dispatch-03 / FR-Dispatch-04 | 分发失败标记 `DISPATCH_ERROR` | 服务运行 | 同上 | HTTP 状态 **404** `Not Found`（与 `http_msg.cpp` 一致） | HTTP |
| TS-04 | FR-Dispatch-05 | `FakeReason` 与 HTTP 状态联动 | 静态已验证 | — | `DISPATCH_ERROR` → 404 | STATIC |
| TS-05 | FR-Caller-02 / 07 | 单次 `Send`+`Recv`，无重试循环 | 服务运行 | 正常 RPC | 成功路径返回 0；**无重试**需抓包或白盒 | CLI + SKIP 注释 |
| TS-06 | FR-Caller-06 | 最终错误码来自 `resp_->result()` | 服务运行 | `Notify` RPC | 控制台 `Notify return -1` | CLI |
| TS-07 | FR-Caller-09 | `Normal_Closed` 不计致命发送错误 | 需构造关闭 | — | 不易黑盒 | SKIP |
| TS-08 | FR-CfgCli-01 | 读取多个 `[ServerN]` | 模板 conf | 临时 conf 含 Server0/Server1 | `Read` 成功且工具可调通 | CONF+CLI |
| TS-09 | FR-CfgCli-02 | `ConnectTimeoutMS` / `SocketTimeoutMS` | 可写临时文件 | 缩小超时 + 错误端口 | 快速失败（连接拒绝或超时） | CONF+CLI |
| TS-10 | FR-CfgCli-03 | `GetRandom()` 从非空列表选取 | 双 endpoint 同机 | 多次调用（概率） | 均可达（统计上不严格证明随机） | CLI |
| TS-11 | FR-CfgCli-04 | 缺省超时默认值 | 代码静态 | — | 见 `client_config.cpp` 默认 200/5000 ms | STATIC |
| TS-12 | FR-Hsha-02 | 队列等待 ≥500ms 丢弃 | 高压+慢处理 | — | 不稳定；性能环境 | SKIP |
| TS-13 | FR-Net-01 | 连接超时参数传入 `Poll` | 拒绝连接地址 | 临时 conf 指向空闲端口 | Open 失败 | CONF+CLI |
| TS-14 | FR-Net-02 | 非法 IP 字符串拒绝 | — | 无效 IP 段（若工具校验） | 连接失败 | CONF+CLI（依赖实现） |
| TS-15 | FR-Net-03 / 05 | 连接成功路径与监控封装 | 正常服务 | 正常调用 | 成功 | CLI |
| TS-16 | FR-Svc-01 | `ToPb` 失败 → `-EINVAL` | 需畸形 body | — | 黑盒难构造 | SKIP |
| TS-17 | FR-Svc-02 | `FromPb` 失败 → `-ENOMEM` | 需畸形响应 | — | 黑盒难构造 | SKIP |
| TS-18 | FR-Svc-03 | `Notify` 可不 `FromPb` empty body | 服务运行 | Notify | 返回行为符合监控行 | CLI |
| TS-19 | FR-HTTP-01 | HTTP 请求进入 `HttpProtocol::RecvReq` | 服务运行 | 任意合法 POST | 可解析并路由 | HTTP |
| TS-20 | FR-HTTP-02 | 响应经 `GenResponse`/`Modify` | 成功 RPC | CLI Search | 正常 200 路径（隐式） | CLI |
| TS-21 | FR-Queue-01 / 02 | `ThdQueue` 阻塞/非阻塞 | 仅线程模型 | — | 单元级更合适 | STATIC |
| TS-22 | FR-Msg-01 / 02 | URI/result 字段存在 | 由成功调用隐含 | — | 成功即说明链路使用 URI/result | CLI |
| TS-23 | PR-Cli-01 / 02 | 客户端 INI 节 | 临时 conf | 合法多段 | 工具 exit 0 | CONF+CLI |
| TS-24 | PR-Svr-01 / 03 | 服务端 Bind/Port/队列等 | 静态 | `search_server.conf` | 与 `HshaServerConfig` 字段对应 | STATIC |
| TS-25 | BR-Echo-01 | Echo 回显 | 服务运行 | `-s` ASCII | `value` 一致 | CLI |
| TS-26 | BR-Search-01 | `query` 未参与当前逻辑 | 服务运行 | 两次不同 `-q` | 输出相同 demo 子串 | CLI |
| TS-27 | BR-Search-02 | 固定 demo `title`/`url` | 服务运行 | Search | 含固定字符串 | CLI |
| TS-28 | BR-Search-03 | 缺少 type/summary | 服务运行 | 检查 DebugString 输出 | 无 type/summary 字段行 | CLI |
| TS-29 | BR-Notify-01 | 当前恒 `-1` | 服务运行 | Notify | `Notify return -1`；未来改为 0 后移 `@expectedFailure` | CLI |
| TS-30 | BR-Tool-01 | `-s` 驱动 Echo | 服务运行 | PHXEcho | return 0 | CLI |
| TS-31 | BR-Tool-02 / 03 | `-q`/`-m` 未写入请求（TODO） | 代码现状 | Search/Notify | 行为与未填一致 | CLI + expectedFailure 或断言缺失 |
| TS-32 | CG-URI-01 / CG-Bin-01 | 生成物 URI/Cmd 一致 | 仓库 | 比对 `phxrpc_search_stub.cpp` 与 dispatcher | 静态一致 | STATIC |
| TS-33 | CG-* 合计 | 生成器正确性 | — | `codegen/` 可执行文件存在 | 已在 BRD 声明静态覆盖 | STATIC |

---

## 与 `integration_test_v2.py` 的映射

- **自动化（默认启用）**：TS-01, TS-02/03, TS-06, TS-08~10, TS-13, TS-19, TS-23, TS-25~31（部分为 `@expectedFailure` / 条件断言）。
- **显式跳过**：TS-05, TS-07, TS-12, TS-16, TS-17（`unittest.skip` 或注释）。
- **仅文档/静态**：TS-04, TS-11, TS-21, TS-24, TS-32~33。

---

## 运行前置

1. 编译 `phxrpc/sample/search_main`、`phxrpc/sample/search_tool_main`。
2. 启动服务（示例）：`cd phxrpc/sample && ./search_main -c search_server.conf`（后台或另一终端）。
3. 执行测试（从仓库根目录）：`python3 tests/integration_test_v2.py -v`
4. 可选 HTTP 相关：无需 `pip install requests`（使用标准库 `http.client`）。

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-10 | 初版，对齐 56 条规则与 v2 集成测试 |
