# PhxRPC — 业务/框架规则规格文档（BRD/FRD v2）

| 元数据（Metadata） | 值（Value） |
|----------|--------|
| Project | PhxRPC (Tencent open-source RPC framework, C++) |
| Repository | https://github.com/Tencent/phxrpc |
| Analysis date | 2026-05-10 |
| Git commit (analyzed tree) | `58318ef02854f7aea02cae67e53b00fd8acc8e15` |
| Scope | Framework core `phxrpc/`, sample `sample/`, codegen `codegen/`, build `phxrpc/Makefile` |

**符号约定（Symbol convention）**

| 前缀（Prefix） | 含义（Meaning） |
|--------|---------|
| FR-xxx | 框架规则（`libphxrpc.a` 的运行时行为） |
| BR-xxx | 业务规则（sample Search 服务行为） |
| PR-xxx | 配置规则（INI 风格 configs） |
| CG-xxx | 代码生成器规则（`codegen/phxrpc_pb2*`） |

**状态标记（Status legend）**

| 标记（Symbol） | 含义（Meaning） |
|--------|---------|
| ✅ | 按文档描述在源码中已实现 |
| ⚠️ | 部分实现 / sample 侧刻意不完整 |
| ❌ | 未实现 / 占位实现 |

---

## Part A — 项目结构与构建（step 1）

### A.1 框架源码按职责分组

| 分组（Group） | 代表性路径（Representative paths，除非特别说明默认在 `phxrpc/` 下） |
|-------|-----------------------------------------------|
| RPC runtime | `rpc/caller.cpp`, `rpc/hsha_server.cpp`, `rpc/server_config.cpp`, `rpc/client_config.cpp`, `rpc/socket_stream_phxrpc.cpp`, `rpc/client_monitor.cpp`, `rpc/server_monitor.cpp`, `rpc/monitor_factory.cpp`, `rpc/phxrpc.pb.cc` |
| Message / dispatch | `msg/base_msg.{h,cpp}`, `msg/base_msg_handler.{h,cpp}`, `msg/base_dispatcher.h`, `msg/base_msg_handler_factory.{h,cpp}` |
| HTTP binding | `http/http_protocol.cpp`, `http/http_msg.{h,cpp}`, `http/http_msg_handler.{h,cpp}`, `http/http_client.{h,cpp}`, `http/http_msg_handler_factory.{h,cpp}` |
| Network / “coroutine” IO | `network/socket_stream_base.{h,cpp}`, `network/socket_stream_block.{h,cpp}`, `network/socket_stream_uthread.{h,cpp}`, `network/uthread_epoll.{h,cpp}`, `network/uthread_runtime.{h,cpp}`, `network/timer.{h,cpp}`, … |
| File / config / CLI opt | `file/config.{h,cpp}`, `file/opt_map.{h,cpp}`, `file/log_utils.{h,cpp}`, `file/file_utils.{h,cpp}` |
| Comm | `comm/assert.{h,cpp}` |

**说明：** 当前代码树中 **不存在** `rpc_channel.h` 或 `thread_pool.h`；超时通过 `ClientConfig` + socket stream 体系生效；并发主要依赖 `WorkerPool` / `ThdQueue` / uthread 调度器（`phxrpc/rpc/hsha_server.cpp`, `phxrpc/rpc/thread_queue.h`, `phxrpc/network/uthread_epoll.*`）。

### A.2 `libphxrpc.a` 组成

证据：`phxrpc/Makefile` 将 `LIB_RPC_OBJS`, `LIB_MSG_OBJS`, `LIB_HTTP_OBJS`, `LIB_NETWORK_OBJS`, `LIB_FILE_OBJS`, `LIB_COMM_OBJS` 打包为 `libphxrpc.a`（`phxrpc/Makefile` **L29–L38**）。

### A.3 sample 产物与文件

| 产物（Artefact） | 角色（Role） |
|----------|------|
| `sample/search.proto` | 服务定义与消息（Service & messages） |
| `sample/phxrpc_search_*.{h,cpp}` | 生成代码：stub / dispatcher / service base / tool |
| `sample/search_service_impl.cpp` | 用户业务实现 |
| `sample/search_main.cpp` | 服务入口与分发 wiring |
| `sample/search_client.{h,cpp}` | 生成的 blocking client |
| `sample/search_tool_*` | CLI 工具 |
| `sample/search_* .conf` | Client/server profile |

---

## Part B — Proto 契约与扩展（step 2）

### B.1 `phxrpc/rpc/phxrpc.proto`

`google.protobuf.MethodOptions` 上的扩展定义（`phxrpc/rpc/phxrpc.proto` **L8–L12**）：

| 扩展项（Extension） | 字段号（Field number） |
|-----------|----------------|
| `CmdID` | 2000000 |
| `OptString` | 2000001 |
| `Usage` | 2000002 |

### B.2 `sample/search.proto`（服务面）

| RPC | Request | Response | CmdID / CLI hints (proto options) |
|-----|---------|----------|-----------------------------------|
| `Search` | `SearchRequest` | `SearchResult` | CmdID=1, OptString=`q:`, Usage=`-q <query>` (`sample/search.proto` **L35–L38**) |
| `Notify` | `google.protobuf.StringValue` | `google.protobuf.Empty` | CmdID=2, OptString=`m:`, Usage=`-m <msg>` (`sample/search.proto` **L41–L44**) |

消息定义：`Site`, `SiteType`, `SearchRequest`, `SearchResult`（`sample/search.proto` **L11–L31**）。

### B.3 URI 映射（生成的 stub 与 dispatcher）

| 机制（Mechanism） | 证据（Evidence） |
|-----------|----------|
| Stub calls `caller.set_uri("/<PackageName>/<Method>", CmdID)` | Codegen emits pattern `caller.set_uri("/%s/%s", …)` (`codegen/client_code_render.cpp` **L198**) |
| Dispatcher registers same path string | Example `"/search/Search"` (`sample/phxrpc_search_dispatcher.cpp` **L28–L31**) |
| Stub stores CmdID for monitor when `cmd_id > 0` | `Caller::MonitorReport` (`phxrpc/rpc/caller.cpp` **L69–L71**) |

**CG-URI-01** ✅ 命名空间 HTTP 路径 `/<package>/<Method>` 必须在 stub 与 dispatcher 间保持一致 —— **generator + sample**（`codegen/client_code_render.cpp` **L198**; `sample/phxrpc_search_dispatcher.cpp` **L28–L31**）。

---

## Part C — 框架规则（FR）与追溯证据（step 3）

### C.1 Dispatcher (`phxrpc/msg/base_dispatcher.h`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Dispatch-01 | Lookup uses **exact** `std::string` key `req.uri()` in `URIFuncMap`. | `find(req.uri())` (`phxrpc/msg/base_dispatcher.h` **L46–L52**) | ✅ |
| FR-Dispatch-02 | Handler return value is always stored in `resp->set_result(ret)` **even if URI not found** (then `ret` stays `-1`). | **L46–L54** | ✅ |
| FR-Dispatch-03 | `Dispatch` returns **true** iff URI existed in map; **false** otherwise. | **L56** | ✅ |
| FR-Dispatch-04 | Sample server marks fake response `DISPATCH_ERROR` when `Dispatch` returns false. | `search_main.cpp` **L33–L37** | ✅ |
| FR-Dispatch-05 | Fake reason enum includes `DISPATCH_ERROR`. | `phxrpc/msg/base_msg.h` **L86–L89** | ✅ |

### C.2 Generated service dispatcher (pattern)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Svc-01 | Request unpack: `req.ToPb` failure → return `-EINVAL`. | `sample/phxrpc_search_dispatcher.cpp` **L44–L49**, **L82–L88**, **L121–L127** | ✅ |
| FR-Svc-02 | Response pack: `resp->FromPb` failure → return `-ENOMEM` (methods with body). | **L60–L66**, **L99–L105** | ✅ |
| FR-Svc-03 | `Notify`-style path may omit `FromPb` for empty body; returns service `ret` directly. | **L113–L140** (no `FromPb`) | ✅ |
| FR-Svc-04 | Server monitor `SvrCall` invoked with CmdID-like first argument per method. | **L36**, **L75**, **L114** | ✅ |

### C.3 Caller client path (`phxrpc/rpc/caller.cpp`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Caller-01 | `GenRequest` failure → return `-1`. | **L76–L83** | ✅ |
| FR-Caller-02 | `FromPb` into wire request fails → propagate code (no send). | **L86–L91** | ✅ |
| FR-Caller-03 | After successful send path, `RecvResponse`; failure sets `recv_error` for monitor. | **L104–L112**, **L113–L116** | ✅ |
| FR-Caller-04 | Any non-zero `ret` before `ToPb` skips body decode and returns error. | **L118–L122** | ✅ |
| FR-Caller-05 | Response `ToPb` failure propagates. | **L124–L129** | ✅ |
| FR-Caller-06 | Final status is `resp_->result()` (application errno-style). | **L131–L136** | ✅ |
| FR-Caller-07 | **No retry loop** in `Caller::Call` — single send/receive attempt. | Whole function **L74–L137** | ✅ |
| FR-Caller-08 | `cmd_id_ > 0` triggers `ClientCall` metrics with URI. | **L69–L71** | ✅ |
| FR-Caller-09 | `SocketStreamError_Normal_Closed` does not count as `send_error`/`recv_error`. | **L99**, **L107** | ✅ |

### C.4 Client configuration (`phxrpc/rpc/client_config.cpp`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-CfgCli-01 | Reads `[Server]` `ServerCount`, `[Server{i}]` `IP`/`Port` into vector. | **L59–L82** | ✅ |
| FR-CfgCli-02 | Reads `[ClientTimeout]` `ConnectTimeoutMS`, `SocketTimeoutMS`. | **L84–L85** | ✅ |
| FR-CfgCli-03 | `GetRandom()` picks `random() % size`; empty → log + optional monitor `GetEndpointFail`. | **L93–L107** | ✅ |
| FR-CfgCli-04 | Default ctor timeouts: connect **200** ms, socket **5000** ms if file omits keys. | **L36–L38** | ✅ |

### C.5 TCP connect / socket (`phxrpc/network/socket_stream_block.cpp`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Net-01 | `BlockTcpUtils::Open` uses non-blocking connect + `Poll` with **`connect_timeout_ms`**. | **L147–L170** | ✅ |
| FR-Net-02 | Invalid dotted-quad `ip` → connect aborted (`inet_addr` check). | **L115–L117** | ✅ |
| FR-Net-03 | After success: switch to blocking mode + TCP_NODELAY. | **L173–L176** | ✅ |
| FR-Net-04 | `LastError`: `EAGAIN`/`EWOULDBLOCK` mapped to `SocketStreamError_Timeout`. | **L102–L107** | ✅ |

### C.6 PhxRPC TCP helper (`phxrpc/rpc/socket_stream_phxrpc.cpp`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Net-05 | Wraps `BlockTcpUtils::Open` and reports **`ClientConnect`** to monitor. | **L28–L36** | ✅ |

### C.7 HTTP message handler (`phxrpc/http/http_msg_handler.cpp`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-HTTP-01 | Incoming HTTP mapped via `HttpProtocol::RecvReq` → `HttpRequest`. | **L36–L49** | ✅ |
| FR-HTTP-02 | Outgoing response created by `req_->GenResponse()` then `Modify(keep_alive, version)`. | **L72–L76** | ✅ |

### C.8 HSHA server / worker (`phxrpc/rpc/hsha_server.cpp`, `phxrpc/rpc/hsha_server.h`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Hsha-01 | Worker executes user `dispatch_` with `DispatcherArgs_t` after `GenResponse()`. | `WorkerLogic` **L474–L480** | ✅ |
| FR-Hsha-02 | If queue wait **≥ `MAX_QUEUE_WAIT_TIME_COST` (500 ms)**, request dropped (`worker_drop_requests_`), **`dispatch_` not called**. | **L475–L486**; `#define` **L78** in `phxrpc/rpc/hsha_server.h` | ✅ |
| FR-Hsha-03 | Worker always **`PushResponse`** after `GenResponse()` (drop path still enqueues a response without running `dispatch_`). | **L474–L488** | ✅ |
| FR-Hsha-04 | `DataFlow::CanPushRequest` enforces max queue length vs config. | **L103–L105** (`hsha_server.cpp`) | ✅ |

### C.9 Thread-safe queue (`phxrpc/rpc/thread_queue.h`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Queue-01 | `ThdQueue::pluck` blocks until item or `break_out_`. | **L52–L66** | ✅ |
| FR-Queue-02 | `pick` non-blocking pop if non-empty. | **L69–L78** | ✅ |

### C.10 Generic message API (`phxrpc/msg/base_msg.h`)

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| FR-Msg-01 | Request exposes `set_uri` / `uri()` for routing string. | **L76–L77** | ✅ |
| FR-Msg-02 | Response exposes `result` / `set_result`. | **L97–L98** | ✅ |

---

## Part D — 业务规则（BR）— sample Search（step 4）

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| BR-Echo-01 | `PHXEcho` echoes `req.value()` and returns `0`. | `sample/search_service_impl.cpp` **L24–L26** | ✅ |
| BR-Search-01 | `Search` ignores `req.query()` in current code. | No read of `req` fields except implicit default — **L29–L33** uses only `resp` | ⚠️ |
| BR-Search-02 | `Search` returns exactly one `Site` with fixed URL/title. | **L30–L33** | ⚠️ (demo stub, not full-text search) |
| BR-Search-03 | `Site.type` / `summary` unset. | **L30–L32** only `url`/`title` | ⚠️ |
| BR-Notify-01 | `Notify` returns `-1` always (no success path). | **L36–L37** | ❌ |
| BR-Tool-01 | CLI maps `-s` → Echo (`search_tool_impl.cpp` **L24–L36**). | ✅ |
| BR-Tool-02 | `Search` tool **does not** fill `SearchRequest` from `-q` (TODO). | **L40–L51** | ❌ |
| BR-Tool-03 | `Notify` tool **does not** fill request from `-m` (TODO). | **L54–L65** | ❌ |
| BR-Cli-01 | Blocking client uses `GetRandom()` endpoint + `PhxrpcTcpUtils::Open` + `SearchStub`. | `sample/search_client.cpp` **L103–L121** pattern | ✅ |
| BR-Cli-02 | `GetPackageName()` falls back to `"search"` if empty. | **L30–L35** | ✅ |
| BR-Svr-01 | Each request constructs **new** `SearchServiceImpl` on stack in `Dispatch`. | `sample/search_main.cpp` **L30–L31** | ✅ |

---

## Part E — 配置规则（PR）

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| PR-Svr-01 | Server binds `BindIP`/`Port` from `[Server]` via `HshaServerConfig`. | `sample/search_server.conf`; `ServerConfig` API `phxrpc/rpc/server_config.h` **L42–L46** | ✅ |
| PR-Svr-02 | `[ServerTimeout] SocketTimeoutMS` drives server-side socket timeout accessor. | `SetSocketTimeoutMS` **L51–L52** | ✅ |
| PR-Svr-03 | HSHA extras: `MaxConnections`, `MaxQueueLength`, `FastRejectThresholdMS`, `IOThreadCount`, … | `HshaServerConfig` **L85–L98** | ✅ |
| PR-Cli-01 | Client reads `[ServerN]` endpoints — supports **multiple** servers; random selection. | `client_config.cpp` **L69–L82**, **L93–L98** | ✅ |
| PR-Cli-02 | Timeouts in `[ClientTimeout]` section. | **L84–L85** | ✅ |

---

## Part F — 代码生成器规则（CG）

| ID | Rule | Evidence | Status |
|----|------|----------|--------|
| CG-Bin-01 | Binaries: `phxrpc_pb2service`, `phxrpc_pb2client`, `phxrpc_pb2tool`, `phxrpc_pb2server`. | `codegen/Makefile` **L6** | ✅ |
| CG-Cli-02 | Client stub emits `Caller::set_uri` with package + RPC name. | `client_code_render.cpp` **L198** | ✅ |
| CG-Svc-03 | Service codegen produces dispatcher `.cpp` with **standard** unpack/service/pack template (mirrors sample). | Compare `sample/phxrpc_search_dispatcher.cpp` header comment **L3–L5** | ✅ |

---

## Part G — 覆盖度矩阵（量化，step 5）

Counts per **implementation status** against rules listed above (FR **37**, BR **11**, PR **5**, CG **3** → **56** rules total).

### G.1 By module

| Module | Rules (#) | ✅ | ⚠️ | ❌ | Coverage %¹ |
|--------|-----------|----|----|----|---------------|
| Dispatcher / fake response | 5 | 5 | 0 | 0 | 100% |
| Generated dispatcher pattern | 4 | 4 | 0 | 0 | 100% |
| Caller / RPC round-trip | 9 | 9 | 0 | 0 | 100% |
| Client config / endpoints | 4 | 4 | 0 | 0 | 100% |
| Network / TCP helpers | 5 | 5 | 0 | 0 | 100% |
| HTTP handler glue | 2 | 2 | 0 | 0 | 100% |
| HSHA worker / queue | 4 | 4 | 0 | 0 | 100% |
| Base message API | 2 | 2 | 0 | 0 | 100% |
| Sample **business** Search/Notify | 5 | 1 | 3 | 1 | 40% |
| Sample **tool** | 3 | 1 | 0 | 2 | 33% |
| Sample **client/server wiring** | 3 | 3 | 0 | 0 | 100% |
| Profile INI | 5 | 5 | 0 | 0 | 100% |
| Codegen | 3 | 3 | 0 | 0 | 100% |

¹ *Coverage %* = `(✅ + 0.5×⚠️) / (✅+⚠️+❌) × 100` rounded to one decimal (⚠️ counts half toward “met intent” for sample-only stubs).

### G.2 Aggregate

| Scope | Rule count | Weighted coverage¹ |
|-------|------------|-------------------|
| Framework + config + codegen (FR+PR+CG) | 45 | **100%** (all ✅) |
| Sample business + tool (BR only) | 11 | **≈ 59.1%** ((5 + 0.5×3) / 11) |
| **Overall** | **56** | **≈ 92.0%** |

¹ Same ⚠️ half-weight as section G.1.

**解读：** 框架侧规则均可在 `libphxrpc.a` 对应源码中找到直接证据支撑；BR 覆盖率偏低主要来自 **sample 的刻意占位/未实现**（如 `Notify`、CLI TODO、demo `Search`）。

---

## Part H — 缺口优先级（step 5 收尾）

| Priority | Item | Rules |
|----------|------|-------|
| P0 | Implement real `Notify` semantics & return `0` on success | BR-Notify-01 |
| P1 | Wire `-q`/`-m` in `search_tool_impl.cpp` | BR-Tool-02, BR-Tool-03 |
| P2 | Use `req.query()` in `Search` if query-aware behaviour is required | BR-Search-01–03 |
| P3 | Negative tests: bad URI (`FR-Dispatch-04`), queue-drop (`FR-Hsha-02`), connect timeout (`FR-CfgCli` + `FR-Net-01`) | Testing |

---

## Part I — 验证计划挂钩（step 6）

| Rule ID | Suggested verification | Existing automation |
|---------|------------------------|---------------------|
| FR-Dispatch-04 | HTTP client hits unknown `/package/method` → fake dispatch error | Manual / future HTTP test |
| FR-Caller-07 | Abort mid-flight → single attempt (no retry) — inspect logs / tcpdump | — |
| FR-Hsha-02 | Synthetic slow worker → queue wait ≥500 ms → drop counter increase | Stress harness |
| BR-Echo-01 | CLI Echo round-trip | `tests/integration_test.py` `test_phx_echo_round_trip` |
| BR-Search-02 | Response contains demo strings | `test_search_contains_demo_fields` |
| BR-Notify-01 | Until fixed: `@unittest.expectedFailure` expecting `return 0` | `test_notify_expected_success_when_fixed` |
| BR-Tool-02/03 | After fix: assert protobuf body contains query/msg | Extend same Python suite |

---

## 附录 — 文件索引（快速导航）

| Path | Role |
|------|------|
| `phxrpc/msg/base_dispatcher.h` | URI dispatch core |
| `phxrpc/rpc/caller.cpp` | Sync client call |
| `phxrpc/rpc/client_config.cpp` | Client INI |
| `phxrpc/rpc/hsha_server.{h,cpp}` | Server runtime |
| `phxrpc/network/socket_stream_block.cpp` | Blocking TCP |
| `phxrpc/http/http_msg_handler.cpp` | HTTP↔message bridge |
| `sample/search_main.cpp` | Sample dispatch hook |
| `sample/search_service_impl.cpp` | Business |
| `sample/search_tool_impl.cpp` | CLI TODOs |
| `codegen/client_code_render.cpp` | Stub URI emission |
| `phxrpc/Makefile` | `libphxrpc.a` membership |

*行号引用基于 commit `58318ef02854f7aea02cae67e53b00fd8acc8e15`；如果你的分支有偏移，请用上方的函数名/文件名重新定位。*
