# PhxRPC Search Sample — 测试剧本文档（Test Scenarios）

| 元数据 | 值 |
|--------|-----|
| 文档版本 | 1.0 |
| 关联 BRD | `sample/docs/business_rules.md` |
| 默认服务端 | `127.0.0.1:16162`（与 `search_server.conf` / `search_client.conf` 一致） |

---

## 1. 测试目标

在 **运行中的 Search 服务** 前提下，通过 **`search_tool_main`（命令行）+ 可选 HTTP 辅助手段**，验证端到端链路、契约字段与已知负向行为，并与 BRD 中的规则 ID 对齐。

---

## 2. 前置条件

| 条件 | 说明 |
|------|------|
| 服务端 | 已启动 `search_main`，监听与客户端配置一致 |
| 客户端配置 | `sample/search_client.conf` 中 `[Server0]` 指向可达地址 |
| 构建产物 | `sample/search_tool_main` 已成功链接 `libsearch_client.a` |
| Python | 3.6+（用于 `sample/tests/integration_test.py`） |
| 动态库 | 若出现 `error while loading shared libraries: libprotobuf.so.*`，需在运行测试的 shell 中配置与编译时一致的 `LD_LIBRARY_PATH`；脚本会 **Skip** 并提示 |

---

## 3. 正向链路（Happy Path）

### TS-ECHO-01：PHXEcho 连通性（BR-Echo-01, FR-Result）

| 项 | 内容 |
|----|------|
| 目的 | 验证 TCP/HTTP/Protobuf 全栈可用，回显语义正确 |
| 触发命令（示例） | `./search_tool_main -f PHXEcho -c search_client.conf -s "integration-test-你好"` |
| 期望退出码 | `0`（工具进程成功） |
| 期望控制台 | 含 `PHXEcho return 0`；`resp` 段中 `value` 与 `-s` 字符串**完全一致** |
| 自动化 | `integration_test.py::test_phx_echo_round_trip` |

### TS-SEARCH-01：Search 基础功能（BR-Search-01/04, FR-Result）

| 项 | 内容 |
|----|------|
| 目的 | 验证 Search RPC 返回当前实现下的固定演示数据 |
| 触发命令（示例） | `./search_tool_main -f Search -c search_client.conf -q "任意查询词"` |
| 期望控制台 | `Search return 0`；`resp` 中含 **`Success Reconstruction`**（`search_service_impl.cpp` 中 `title`） |
| 数据校验 | `resp` 中含 `url: "https://www.tencent.com"`（或与 BRD 一致的当前硬编码） |
| 说明 | 当前 `SearchToolImpl::Search` **尚未**将 `-q` 写入 `SearchRequest.query`（TODO）；本用例仍验证「工具→客户端→服务端」整体可达性 |
| 自动化 | `integration_test.py::test_search_contains_demo_fields` |

---

## 4. 负向链路（Negative / Known-Broken）

### TS-NOTIFY-01：Notify 已知失败（BR-Notify-01, §6 `SearchServiceImpl::Notify`）

| 项 | 内容 |
|----|------|
| 目的 | 记录**当前实现**下服务端恒返回 `-1` 的可观测行为 |
| 触发命令（示例） | `./search_tool_main -f Notify -c search_client.conf -m "hello"` |
| 期望控制台 | `Notify return -1` |
| 自动化策略 | 使用 `@unittest.expectedFailure` 断言「未来应为 `return 0`」；修复业务后测试转绿并移除装饰器 |
| 自动化 | `integration_test.py::test_notify_expected_success_when_fixed` |

### TS-ROUTE-01：非法路由 / 分发失败（FR-Dispatch, FR-URI）

| 项 | 内容 |
|----|------|
| 目的 | URI 不在 `SearchDispatcher::GetURIFuncMap()` 中时，不应按正常 RPC 成功返回 |
| 建议做法 | 使用 **HTTP 客户端**向 `http://127.0.0.1:16162/search/NonExistent` 发送请求（需符合 PhxRPC HTTP 封装格式）；或查阅框架文档使用最小合法 POST |
| 期望 | 客户端收到错误类结果（例如分发失败 / 非 0 `result`）；与 `search_main` 中 `DISPATCH_ERROR` 路径一致 |
| 自动化 | 当前 **未** 默认纳入 `integration_test.py`（依赖精确 HTTP 载荷）；可在具备帧格式后补充 |

### TS-TIMEOUT-01：超时模拟（配置侧 FR）

| 项 | 内容 |
|----|------|
| 目的 | 验证超时与熔断相关配置在集成环境中的可观测性 |
| 建议 | （1）将 `search_client.conf` 中 `SocketTimeoutMS` 改为极小值后重试 Search；（2）或在防火墙/iptables 层阻断端口观察客户端超时；（3）Python `subprocess.run(..., timeout=N)` 用于防止**测试脚本**本身挂死，而非模拟 RPC 超时 |
| 自动化 | 建议在测试文档与 CI 中作为**手工/专项**场景执行 |

---

## 5. 数据验证清单（Protobuf / DebugString）

| 接口 | 字段或关键字 | 关联 BRD |
|------|----------------|----------|
| PHXEcho | `value` 等于请求字符串 | BR-Echo-01 |
| Search | `title` 含 `Success Reconstruction` | BR-Search-03（演示数据） |
| Search | `url` 含 `tencent.com` 或与实现一致 | BR-Search-03 |
| Notify | `Empty` 无字段；以 **`return` 行数值**为主 | BR-Notify-02 |

---

## 6. 执行命令速查

```bash
cd sample
./search_tool_main -f PHXEcho -c search_client.conf -s 'test'
./search_tool_main -f Search   -c search_client.conf -q 'query'
./search_tool_main -f Notify   -c search_client.conf -m 'msg'

python3 tests/integration_test.py -v
```

---

## 7. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-10 | 初版：对齐 BRD 与 `integration_test.py` |
