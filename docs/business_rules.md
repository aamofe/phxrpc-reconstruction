# PhxRPC Sample（Search 服务）业务规则规格文档（BRD）

| 元数据 | 值 |
|--------|-----|
| 文档版本 | 1.0 |
| 生成日期 | 2026-05-10 |
| 代码基路径 | `sample/`（仓库根：`phxrpc`） |
| 约定监听地址 | `127.0.0.1:16162`（见 `search_server.conf`） |

---

## 1. 目的与范围

本文档基于 `/work/sample`（即仓库内 `sample/`）目录下与 **Search 微服务**相关的源码，从 `search.proto` 契约出发，经 HTTP 请求分发（`phxrpc_search_dispatcher.*`）与服务器入口（`search_main.cpp`），落实到业务实现类 `SearchServiceImpl`（`search_service_impl.cpp`），梳理**可观测的业务与框架行为**，并评估当前实现与测试覆盖缺口。

**不在本文推导范围内的内容**：PhxRPC 框架通用实现的全部细节（仅引用与样例直接相关的 `BaseDispatcher`、`Caller` 等行为）。

---

## 2. 全链路请求路径（可追溯）

### 2.1 文本流程

1. **客户端**：`SearchClient` 根据 `search_client.conf` 选取 Endpoint，建立 TCP，构造 `SearchStub`，调用 `caller.set_uri(...)` 与 `Caller::Call`（`phxrpc_search_stub.cpp`、`search_client.cpp`）。
2. **传输**：`Caller` 将 Protobuf 请求序列化进 `BaseRequest`，写入 URI、可选 keep-alive，经 socket 发送并接收 `BaseResponse`（`phxrpc/rpc/caller.cpp`）。
3. **服务端**：`HshaServer` 工作线程取出 `BaseRequest`，调用用户注册的 `Dispatch`（`search_main.cpp`）。
4. **分发**：`Dispatch` 栈上构造 `SearchServiceImpl` 与 `SearchDispatcher`，由 `BaseDispatcher<SearchDispatcher>::Dispatch` 按 **`req.uri()`** 在 URI→成员函数映射表中查找处理函数（`phxrpc/msg/base_dispatcher.h`）。
5. **方法级处理**：各 `SearchDispatcher::<Method>` 顺序执行：**反序列化 `ToPb`** → **`SearchService::<Method>`（多态到 `SearchServiceImpl`）** → **（部分接口）序列化响应 `FromPb`** → 返回 **errno 风格整数**（`phxrpc_search_dispatcher.cpp`）。
6. **结果写回**：`BaseDispatcher::Dispatch` 将返回值写入 `resp->set_result(ret)`；若 URI 未命中映射，`search_main.cpp` 中对响应调用 `SetFake(DISPATCH_ERROR)`（`search_main.cpp`、`phxrpc/msg/base_msg.h`）。

### 2.2 链路示意图（Mermaid）

```mermaid
flowchart LR
    subgraph Client["客户端 sample"]
        Conf["search_client.conf"]
        SC["SearchClient"]
        Stub["SearchStub"]
        Conf --> SC --> Stub
    end
    subgraph Transport["PhxRPC Caller / Socket"]
        Call["Caller::Call"]
        Stub --> Call
    end
    subgraph Server["服务端 sample"]
        Main["search_main::Dispatch"]
        BD["BaseDispatcher::Dispatch"]
        Disp["SearchDispatcher"]
        Svc["SearchServiceImpl"]
        Call --> Main --> BD --> Disp --> Svc
    end
```

### 2.3 URI 与 CmdID 映射（可追溯）

| 逻辑 RPC | HTTP URI（服务端映射键） | Stub `set_uri` 第二参数（CmdID） | `search.proto` 中 `phxrpc.CmdID` |
|----------|---------------------------|-----------------------------------|----------------------------------|
| PHXEcho | `/search/PHXEcho` | `-1`（框架/监控约定，非 proto 扩展） | *未在 proto 中定义此方法* |
| Search | `/search/Search` | `1` | `1` |
| Notify | `/search/Notify` | `2` | `2` |

说明：**Proto 文件仅声明 `Search` 与 `Notify`**；`PHXEcho` 由代码生成器额外加入 Stub/Dispatcher，用于框架级 Echo 测试（见 `phxrpc_search_dispatcher.cpp` 与 `phxrpc_search_stub.cpp`）。

---

## 3. 接口规格（Method / Input / Output）

### 3.1 数据类型（源自 `search.proto`）

| 类型 | 字段/取值 | 说明 |
|------|-----------|------|
| `SiteType` | `BLOG`, `NEWS`, `VIDEO`, `UNKNOWN` | 站点类型枚举 |
| `Site` | `url`, `title`, `type`, `summary` | 单条站点结果 |
| `SearchRequest` | `query` | 查询字符串 |
| `SearchResult` | `sites`（repeated `Site`） | 查询结果列表 |

### 3.2 对外 RPC 列表（Proto 定义）

| Method | Input | Output | Proto 扩展（代码生成/工具链） |
|--------|--------|--------|------------------------------|
| `Search` | `search.SearchRequest` | `search.SearchResult` | `CmdID=1`，`OptString="q:"`，`Usage="-q <query>"` |
| `Notify` | `google.protobuf.StringValue` | `google.protobuf.Empty` | `CmdID=2`，`OptString="m:"`，`Usage="-m <msg>"` |

### 3.3 框架附加 RPC（未在 `search.proto` service 块声明）

| Method | Input | Output | 触发条件 |
|--------|--------|--------|----------|
| `PHXEcho` | `google.protobuf.StringValue` | `google.protobuf.StringValue` | URI=`/search/PHXEcho`；工具链 `SearchTool` 登记名为 `PHXEcho`，命令行 `-s` |

---

## 4. 各接口业务逻辑触发点与隐含规则

### 4.1 通用框架规则（适用于本 sample 中 Dispatcher 实现）

| 规则 ID | 描述 | 证据位置 |
|---------|------|----------|
| FR-URI | 路由唯一键为 **`BaseRequest::uri()`** 字符串，须与 `SearchDispatcher::GetURIFuncMap()` 中键完全一致（含大小写、前缀 `/search/`）。 | `phxrpc/msg/base_dispatcher.h`，`phxrpc_search_dispatcher.cpp` |
| FR-Dispatch | URI **未命中**映射时：`Dispatch` 返回 `false`，`search_main` 设置 **`FakeReason::DISPATCH_ERROR`**。 | `search_main.cpp`，`phxrpc/msg/base_dispatcher.h` |
| FR-Result | 处理函数返回值经 `resp->set_result(ret)` 传递；客户端 `Caller::Call` 最终 **`ret = resp_->result()`**。非 0 视为调用失败（日志记 err）。 | `phxrpc/msg/base_dispatcher.h`，`phxrpc/rpc/caller.cpp` |
| FR-ToPb | 请求反序列化失败时，Dispatcher 返回 **`-EINVAL`**。 | `phxrpc_search_dispatcher.cpp` |
| FR-FromPb | 响应 `FromPb` 失败时，Dispatcher 返回 **`-ENOMEM`**（适用于实现了 `FromPb` 的分支）。 | `phxrpc_search_dispatcher.cpp` |
| FR-NotifyBody | **`Notify` 分支在成功路径未调用 `resp->FromPb`**，与 `PHXEcho`/`Search` 不同；依赖框架生成的空响应与客户端 `ToPb` 约定。 | `phxrpc_search_dispatcher.cpp`（对比 `Search`） |
| FR-Monitor | `SvrCall` 第一参数为 CmdID 或占位：`PHXEcho` 使用 **`-1`**，`Search` 为 **`1`**，`Notify` 为 **`2`**。 | `phxrpc_search_dispatcher.cpp` |

### 4.2 `Search`

| 规则 ID | 描述 |
|---------|------|
| BR-Search-01 | 业务入口：`SearchDispatcher::Search` 在 `ToPb` 成功后调用 `service_.Search(req_pb, &resp_pb)`。 |
| BR-Search-02 | 契约含义：`SearchRequest.query` 表示用户检索词；`SearchResult.sites` 为零或多条 `Site`。Proto3 字符串默认允许为空字符串。 |
| BR-Search-03 | 生成代码期望：`Site` 可包含 `url`、`title`、`type`、`summary`；枚举默认值为 `BLOG(0)`（若未设置）。 |
| BR-Search-04 | 客户端：Stub URI `/search/Search`，CmdID `1`；随请求发送 Protobuf 编码体。 |

### 4.3 `Notify`

| 规则 ID | 描述 |
|---------|------|
| BR-Notify-01 | 业务入口：`SearchDispatcher::Notify` 在 `ToPb` 成功后调用 `service_.Notify(req_pb, &resp_pb)`。 |
| BR-Notify-02 | 响应体为 `google.protobuf.Empty`，无业务字段；返回值仍以整数 `result` 传递。 |
| BR-Notify-03 | 客户端 Stub URI `/search/Notify`，CmdID `2`。 |

### 4.4 `PHXEcho`

| 规则 ID | 描述 |
|---------|------|
| BR-Echo-01 | 典型语义：响应 `value` 应与请求 `value` 一致（回归/连通性测试）。 |
| BR-Echo-02 | 工具链：`search_tool_impl.cpp` 中从 `opt_map.Get('s')` 填充请求（需命令行提供 `-s`）。 |

---

## 5. 配置与运维隐含约束

| 配置项 | 作用 | 来源文件 |
|--------|------|----------|
| `BindIP` / `Port` | 服务监听地址与端口（默认 `127.0.0.1:16162`） | `search_server.conf` |
| `PackageName` | 与监控/包名相关（客户端默认包名回退为 `"search"`） | `search_server.conf`、`search_client.cpp` |
| `ConnectTimeoutMS` / `SocketTimeoutMS` | 客户端连接与读写超时 | `search_client.conf` |
| `ServerCount` / `[ServerN]` | 多 Endpoint；`GetRandom()` 选取 | `search_client.conf`、`search_client.cpp` |

---

## 6. 当前实现与业务规则对齐（`search_service_impl.cpp`）

### 6.1 方法级覆盖矩阵

| 接口 | 业务规则要点 | 当前实现摘要 | 覆盖结论 |
|------|----------------|--------------|----------|
| `PHXEcho` | 回显字符串（BR-Echo-01） | `resp->set_value(req.value())`，返回 `0` | **已实现** |
| `Search` | 基于 `query` 返回结构化 `SearchResult`（BR-Search-02/03） | 固定写入一条 `Site`：`url`、`title`；**未读取 `req.query()`**；**未设置 `type`、`summary`** | **部分实现**（演示/占位） |
| `Notify` | 处理通知消息并通常返回成功或业务错误码（BR-Notify-01/02） | **直接 `return -1`**，无业务处理 | **空实现 / 恒失败** |

### 6.2 与 Proto 类型完整性对照

| Proto 元素 | 是否在 `Search` 实现中体现 |
|------------|---------------------------|
| `SearchRequest.query` | 否（未使用） |
| `Site.url` / `title` | 是（硬编码） |
| `Site.type` | 否 |
| `Site.summary` | 否 |
| `SiteType` 枚举语义 | 否 |
| 多条 `sites` | 否（仅一条） |

---

## 7. 覆盖度评估与缺口分析（达成「规则级 100%」的建议）

以下「100%」指：**BR 节中由 Proto + 本 sample 约定的语义与边界均有对应实现或可自动化验证**。

### 7.1 已实现（Implemented）

- **FR-URI / FR-Dispatch / FR-Result**：由框架与 `search_main` + Dispatcher 共同满足；可通过集成测试断言 URI、返回码。
- **FR-ToPb / FR-FromPb / FR-NotifyBody**：由 Dispatcher 实现；需**针对性单测或集成测试**覆盖非法 body、超大消息等（框架层）。
- **BR-Echo-01**：`PHXEcho` 在 `SearchServiceImpl` 中已实现。

### 7.2 空实现 / 待办（Empty / Todo）

| 区域 | 缺口 | 建议补充 |
|------|------|----------|
| `Notify` | 恒返回 `-1`，无日志或状态 | 实现具体通知逻辑；定义成功 `0` 与错误码约定；可选写审计日志 |
| `Search` | 未使用 `query`，未填充 `type`/`summary`，未覆盖多结果 | 按产品规则解析检索词并组装完整 `Site`；定义空 `query`、无结果时的约定（空列表 vs 错误码） |
| CLI 工具 | `search_tool_impl.cpp` 中 `Search`/`Notify` 标注 **TODO**，未从 `opt_map` 填 `req` | 实现 `-q`、`-m` 与 proto `OptString` 对齐，便于手工验收与回归 |
| `PHXBatchEcho` | 客户端存在批量 Echo 路径 | 若纳入规格，需定义与单点 Echo 一致的成功准则及并发语义 |

### 7.3 测试用例建议（便于追溯 BR ID）

| 用例类型 | 建议场景 | 对应 BR / FR |
|----------|----------|--------------|
| 集成 / 契约 | `Search`：带不同 `query`，断言响应中 `sites` 条数与字段 | BR-Search-* |
| 集成 | `Notify`：合法消息后断言 **`result == 0`** 且客户端无错误 | BR-Notify-* |
| 集成 | `PHXEcho`：任意字符串回显 | BR-Echo-01 |
| 负面 | 畸形 HTTP body / 非 Protobuf：期望 `-EINVAL`（若可构造） | FR-ToPb |
| 负面 | URI 错误路径：期望分发失败 / `DISPATCH_ERROR` | FR-Dispatch |
| 配置 | 错误 IP/端口：客户端返回 `-1` | 配置节 |

---

## 8. 源代码索引（便于评审）

| 文件 | 职责 |
|------|------|
| `search.proto` | 接口与消息契约、`phxrpc` 方法扩展 |
| `search_main.cpp` | `HshaServer` 启动、`Dispatch` 装配、`DISPATCH_ERROR` |
| `phxrpc_search_dispatcher.{h,cpp}` | URI 路由、ToPb/FromPb、监控、返回值 |
| `phxrpc_search_service.{h,cpp}` | `SearchService` 默认桩（未实现返回 `-1`） |
| `search_service_impl.{h,cpp}` | **业务实现（本文评估核心）** |
| `phxrpc_search_stub.{h,cpp}` | 客户端 URI 与 CmdID |
| `search_client.{h,cpp}` | 连接池化客户端封装 |
| `search_tool_impl.cpp` | 命令行工具与 OptMap（部分 TODO） |
| `phxrpc/rpc/phxrpc.proto` | `CmdID` / `OptString` / `Usage` 扩展定义 |
| `phxrpc/msg/base_dispatcher.h` | 通用 URI 分发与 `set_result` |

---

## 9. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-10 | 初版：基于 `sample/` 全量静态源码分析 |
