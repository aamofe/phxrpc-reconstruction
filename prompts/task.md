一、针对sample

task1

```
Role: 你是一位资深的后台架构师和自动化测试专家，精通 C++ 和 PhxRPC 框架。

Context:
我现在已经成功在本地编译并运行了 PhxRPC 的 sample 项目。服务监听在 127.0.0.1:16162。项目包含以下关键文件：

search.proto: 定义了 Search 和 Notify 接口。

search_service_impl.cpp: 包含业务逻辑的实现（当前我已注入了简单的模拟逻辑）。

phxrpc_search_dispatcher.cpp: 框架的请求路由逻辑。

Task 1: 业务规则重建与文档化

深度源码分析： 请全链路扫描 /work/phxrpc/sample 目录下的源码。分析从 search.proto 定义开始，经由 dispatcher 路由，最终在 search_service_impl.cpp 中被处理的完整流程。

抽取业务规则： 请以 Markdown 格式产出一份 《PhxRPC 业务规则规格文档 (BRD)》。文档需明确包含：

接口列表（Method, Input, Output）。

每个接口的业务逻辑触发点。

隐含的业务规则（例如：请求参数的边界、错误处理码、协议头要求等）。

Task 2: 代码覆盖度分析

逻辑对齐： 基于上述抽取的业务规则，分析当前 search_service_impl.cpp 中的代码实现。

覆盖度评估： 识别出业务规则中哪些部分已被代码实现（Implemented），哪些部分目前是空实现（Empty/Todo）。

缺项识别： 给出具体的分析报告，指出如果要达到 100% 的业务规则覆盖，现有的 C++ 代码或未来的测试用例需要补充哪些场景。

Output Requirements:

请将产出的文档直接保存在 /work/docs/business_rules.md。

文档要求专业、整洁、具备可追溯性。
```

task2

```
Role: 你是一位高级自动化测试工程师，擅长使用 Python 进行分布式系统的集成测试和契约测试。

Context:
参考已生成的 /work/phxrpc/sample/docs/business_rules.md 文档。我们已经拥有一个运行中的 PhxRPC Search 服务（127.0.0.1:16162）。现在需要完成任务 2：全链路自动化测试的构建。

Task 1: 生成《测试剧本文档 (Test Scenarios)》

请在 /work/docs/test_scenarios_v2.md 中产出一份测试剧本。

剧本需覆盖：

正向链路：PHXEcho 连通性、Search 基础功能。

负向链路：Notify 的已知失败（根据 BRD，当前实现返回 -1）、非法路由、超时模拟建议。

数据验证：断言响应中的 Protobuf 字段（如 url、title）。

Task 2: 生成 Python 集成测试脚本

在 /work/tests/integration_test.py 创建 Python 脚本。

技术实现方案：

优先选择调用命令行工具方案：利用 Python 的 subprocess 模块调用 ./search_tool_main。这种方式最能直接验证“二进制工具+服务端”的整体可靠性。

框架要求：使用 Python 自带的 unittest 库。

测试逻辑要点：

Echo Test: 验证 -s 输入与返回的 value 是否完全一致。

Search Test: 验证 -q 输入后，返回的 resp 是否包含 Success Reconstruction 关键字。

Notify Test: 验证调用后返回码为 -1（根据当前代码实现），并标记为 expectedFailure。

解析逻辑：脚本需要解析 ./search_tool_main 输出的文本串（例如：Search return 0 和 resp: { ... }），建议使用正则表达式。

Output Requirements:

脚本必须包含详细的注释，解释每个 Case 对应的 BRD 规则 ID。

确保脚本具有良好的错误处理，如果二进制文件不存在，给出友好的提示。
```

二、针对整个项目

task1

```
# 角色设定
你是一位资深的软件测试架构师，擅长通过静态源码分析重建业务规则和框架规则，并评估这些规则与代码实现的覆盖度。

# 项目背景
项目：**PhxRPC** —— 腾讯开源的高性能、轻量级 RPC 框架（C++）。  
仓库地址：https://github.com/Tencent/phxrpc  
任务：对**整个仓库**（包括框架核心 + sample 示例）进行**需求重建**：从功能/接口入手，分析源码，抽取业务/框架规则文档，并分析该文档对代码的覆盖度。

# 输入信息
- 仓库根目录：假设我们已经克隆到本地，路径为 `/workspace/phxrpc`。
- 关键子目录：
  - `phxrpc/`：框架核心代码（rpc, msg, thread, http, etc.）
  - `sample/`：基于 PhxRPC 的示例服务（search 服务）
  - `third_party/`：依赖（protobuf 等）
- 代码语言：C++，少量 Python 工具脚本。
- 构建系统：make。

# 任务目标
产出 **业务/框架规则文档（BRD/FRD）**，并分析该文档对代码实现的**覆盖度**（即文档中的每条规则，在源码中是否实现、部分实现还是缺失）。  
文档需要具备以下特点：
1. **可追溯**：每条规则都标注源码文件、函数、行号范围（或 commit hash）。
2. **分类清晰**：区分框架级规则（FR-xxx）和业务级规则（BR-xxx，针对 sample 服务）。
3. **覆盖度量化**：最终给出一个覆盖度矩阵（按模块/按接口），说明哪些规则已实现、哪些未实现/部分实现。
4. **可验证**：文档应能直接指导后续的测试用例生成（任务2）。

# 分析范围（必须覆盖，不能只分析 sample）
- **框架核心模块**（`phxrpc/` 目录）：
  - RPC 调用链：`caller.cpp` / `stub` 生成机制 / `base_dispatcher.h` / `hsha_server.h`
  - 网络层：`socket_stream.h` / `tcp_utils.h` / `http_client.h`
  - 线程模型：`thread_pool.h` / `co_routine.h` (协程)
  - 超时与重试：`rpc_channel.h` 中的超时配置、`caller.cpp` 中的 socket 超时处理
  - 配置与监控：`config.h` / `monitor.h` 相关逻辑
- **示例服务**（`sample/` 目录）：
  - `search.proto` 定义的接口
  - `search_service_impl.cpp` 的业务实现
  - `search_tool_impl.cpp` 命令行工具
  - `search_client.cpp` / `search_server.conf`
- **代码生成器**（`tools/` 目录，如有）：`phxrpc_tools` 如何从 proto 生成 stub/dispatcher 的规则。

# 分析步骤（AI 需按顺序执行）

## 步骤1：项目结构扫描与模块识别
- 列出 `/workspace/phxrpc/phxrpc` 下所有 `.h/.cpp`，按功能分组（rpc, msg, thread, http, etc.）。
- 识别 `sample/` 下的关键源文件、proto 文件和配置文件。
- 记录构建系统（Makefile）中哪些源文件被编译进 `libphxrpc.a`，哪些是示例特有。

## 步骤2：Proto 契约与扩展提取
- 提取 `search.proto` 中定义的 service、method、message，以及 `phxrpc` 扩展字段（`CmdID`、`OptString`、`Usage`）。
- 检查 `phxrpc/phxrpc.proto` 中扩展定义。
- 记录每个 RPC 方法的 URI 映射规则（例如 `/search/PHXEcho` 从何处生成）。

## 步骤3：框架级规则抽取（FR）
- 分析 **分发器（Dispatcher）机制**：
  - `phxrpc/msg/base_dispatcher.h`：URI 映射表如何填写、`Dispatch` 如何调用、返回值如何写入 `BaseResponse::result`。
  - 生成的 dispatcher（如 `sample/phxrpc_search_dispatcher.cpp`）如何遵循此框架。
  - 规则示例：`FR-URI-01` URI 必须与映射表完全匹配；`FR-Dispatch-01` 未命中映射时返回 `DISPATCH_ERROR`。
- 分析 **Caller 调用链**：
  - `phxrpc/rpc/caller.cpp`：连接建立、超时、序列化、发送、接收、解析 result。
  - `phxrpc/rpc/rpc_channel.h`：`SocketTimeoutMS` 与 `ConnectTimeoutMS` 的应用位置。
  - 规则示例：`FR-Timeout-01` 读超时后 `Caller::Call` 返回 `-1` 且不会重试。
- 分析 **线程模型与并发**：
  - `phxrpc/thread/thread_pool.h`：任务提交、队列满的行为。
  - `phxrpc/co_routine.h`：协程切换点（如有）。
  - 规则示例：`FR-Thread-01` 服务端默认使用固定大小线程池处理请求。
- 分析 **HTTP 协议兼容层**：
  - `phxrpc/http/http_client.h` / `http_server.h`：如何将 HTTP 请求转换为 PhxRPC BaseRequest。
  - 规则：`FR-HTTP-01` HTTP 路径中的 `/search/PHXEcho` 必须完整匹配等。

## 步骤4：业务级规则抽取（BR，针对 sample 服务）
- 分析 `sample/search_service_impl.cpp` 中三个方法的实现：
  - `PHXEcho`：检查是否回显，返回 0。
  - `Search`：检查是否读取 `req.query()`、固定返回一条 `Site`、缺失字段等。
  - `Notify`：当前返回 `-1`，记录为“未实现”规则。
- 分析 `sample/search_tool_impl.cpp` 中命令行参数映射：
  - `-s` 用于 `PHXEcho`，`-q` 用于 `Search`，`-m` 用于 `Notify`，但实际 `Search`/`Notify` 的 TODO 状态。
  - 规则：`BR-Tool-01`：`Search` 工具目前未将 `-q` 填入 `SearchRequest.query`。
- 分析客户端配置 `search_client.conf` 的作用：是否支持多 endpoint、随机选取等。
- 规则分类：正确定义（已实现）、部分实现（如 Search 未用 query）、空实现（Notify）、工具未完成（TODO）。

## 步骤5：整合规则文档（产出文件 `docs/business_rules.md`）
- 文档格式使用 Markdown，包含：
  - 元数据（项目名、版本、分析日期、commit hash）。
  - 符号约定：FR-xxx（框架规则）、BR-xxx（业务规则）、PR-xxx（配置规则）。
  - 每个规则的编号、描述、源码证据（文件:行号）、实现状态（✅/⚠️/❌）。
  - 一个独立的 **覆盖度分析** 章节，用表格展示：
    | 模块 | 规则总数 | 已实现 | 部分实现 | 未实现 | 覆盖率(%) |
    |------|----------|--------|----------|--------|-----------|
    | 服务端分发 | 8 | 7 | 0 | 1 | 87.5% |
    | 客户端调用 | 6 | 6 | 0 | 0 | 100% |
    | sample/业务 | 10 | 2 | 4 | 4 | 20% |
    | ... | ... | ... | ... | ... | ... |
  - 最后给出 **总体规则覆盖率**（加权或简单平均）和 **缺口优先级建议**。

## 步骤6：生成覆盖率验证计划（可选，供任务2使用）
- 针对每条“未实现”或“部分实现”的规则，建议一个具体的测试用例（测试剧本）。
- 针对“已实现”的规则，指出哪些已有现有测试覆盖（如 `tests/integration_test.py` 中的用例），哪些需要补充。

# 输出要求
- 只输出最终的 `business_rules.md` 文档内容（不要输出多余解释）。
- 确保文档可读性强，代码引用精确（行号可以用 `L123-L145` 形式）。
- 若某些行号因代码版本变化无法确定，可使用函数名 + 正则特征代替，但需注明“依赖当前 master 分支”。

# 成功标准
- 文档规则数量不少于 40 条（框架 + 业务 + 配置）。
- 覆盖度分析至少包含 5 个核心模块。
- 每个模块的覆盖率是基于实际代码检查得出的，非臆测。
- 能够直接用于下一步“生成测试剧本和代码”。

# 开始执行
请现在开始分析 `/workspace/phxrpc` 源码，并输出上述文档。
```

task2

```
# 任务2：基于业务规则文档生成测试剧本与 Python 集成测试代码

## 输入材料
你已经有一份完整的规则文档：`docs/business_rules.md`（BRD/FRD v2），其中包含：
- 框架规则（FR）37 条  
- 业务规则（BR）11 条  
- 配置规则（PR）5 条  
- 代码生成规则（CG）3 条  
总计 56 条规则，并已给出覆盖度矩阵和优先级（P0～P3）。

**当前代码环境**：
- PhxRPC 仓库位于 `/workspace/phxrpc`（或你本地的等效路径）
- 已编译 `libphxrpc.a`、`search_main` 服务端以及 `search_tool_main` 客户端工具
- 已有基础测试文件 `tests/integration_test.py`（覆盖了 Echo、Search demo 字段、Notify 预期失败）

## 任务目标
1. **生成测试剧本文档**（`docs/test_scenarios_v2.md`），基于业务规则设计测试场景，每条场景关联到具体的规则 ID（FR/BR/PR/CG），并说明前置条件、步骤、预期结果。  
2. **生成完整的 Python 集成测试代码**（`tests/integration_test_v2.py`），扩展现有测试，尽可能覆盖上述规则。代码应当：
   - 使用 `unittest` 或 `pytest` 框架。
   - 主要通过 `subprocess` 调用 `search_tool_main` 来驱动 RPC，必要时可以添加 HTTP 客户端（`requests`）或直接 socket 发送畸形请求，以覆盖框架错误路径。
   - 包含正向测试、负向测试、超时测试、配置变更测试（临时修改 conf 文件或使用不同 conf）。
   - 对已知未实现的规则（如 `Notify` 返回 -1、`Search` 未使用 query）使用 `@unittest.expectedFailure` 或条件跳过，并注释关联的规则 ID。
   - 提供清晰的断言和错误信息。
3. **给出运行指令**：说明如何启动服务端、安装依赖、执行测试并查看报告。

## 测试覆盖要求（优先级递减）
- **P0（必须覆盖）**：  
  - FR-Dispatch-01/02/03/04（URI 映射、返回值传播、分发失败）  
  - FR-Caller-01～09（客户端调用链，包括序列化失败、超时、无重试、监控）  
  - FR-CfgCli-01～04（多 endpoint、随机选取、超时配置）  
  - FR-Hsha-02（队列等待超时丢弃请求）——可通过压力与耗时模拟  
  - BR-Echo-01（回显）  
  - BR-Notify-01（已知失败，预期未来成功）  
- **P1（强烈建议）**：  
  - FR-Svc-01～02（ToPb/FromPb 错误码）  
  - FR-Net-01～05（连接超时、无效 IP、TCP_NODELAY）  
  - BR-Search-01～03（query 未使用、固定 demo 数据、字段缺失）  
  - PR-Svr-01～03（服务端配置）  
- **P2（可选但加分）**：  
  - FR-HTTP-01/02（HTTP 映射）  
  - FR-Queue-01/02（线程队列行为）  
  - BR-Tool-01～03（CLI 参数映射，包括 TODO 标记）  
- **P3（若不实现则文档中说明无法自动化）**：  
  - CG-* 规则（代码生成器本身通过静态分析已覆盖，无需动态测试）

最终产出应注明 **实际覆盖的规则数量/总规则数量**，并给出未覆盖规则的理由（例如依赖代码生成器或需要侵入性 mock）。

## 输出文件列表与内容要求

### 1. 测试剧本文档 `docs/test_scenarios_v2.md`
- 格式 Must 包含表格：
  | 场景ID | 关联规则ID | 测试目标 | 前置条件 | 输入/操作 | 预期结果 | 实现方式（cli/http/…） |
- 至少 30 个测试场景（可合并部分小规则为一个场景）
- 每个场景都应能映射到后续 Python 测试代码中的一个或一组断言

### 2. Python 测试代码 `tests/integration_test_v2.py`
- 继承或扩展原有 `integration_test.py`，但更完整。
- 代码结构示例：
  ```python
  class TestPhxRPCRules(unittest.TestCase):
      @classmethod
      def setUpClass(cls):
          # 确保服务端运行，准备临时配置文件副本等
      def test_fr_dispatch_01_uri_mapping(self):
          # 使用正确的 URI (默认 /search/Search) 应成功
          # 使用错误的 URI 应返回错误码或空结果
      def test_fr_caller_07_no_retry(self):
          # 通过临时阻断服务端验证无重试
      # ... 更多测试
```

三、针对README

```
# 任务：为当前仓库生成 README.md

你正在阅读一个 **PhxRPC 测试重建项目**的根目录。  
该项目已完成了 **任务1（需求重建）** 和 **任务2（生成测试剧本与代码）**，具体产出如下：

- `docs/business_rules_v2.md`：56 条规则（FR/BR/PR/CG），含覆盖度矩阵
- `docs/test_scenarios_v2.md`：30+ 测试场景，关联规则 ID
- `tests/integration_test_v2.py`：扩展的 Python 集成测试（覆盖约 24 条黑盒规则）
- `tests/integration_test.py`：原始简单测试（保留）
- `scripts/rebuild_phxrpc.sh`：Docker 环境重建脚本
- 其他提示词文件（如有）

## 你的职责

请扫描仓库中所有相关文件，理解项目目标，然后**生成一份完整的 README.md**，内容需包含以下章节：

1. **项目简介** – 说明本仓库的目的（基于源码 + AI 重建测试用例，增强 PhxRPC 测试完备性）
2. **目录结构** – 列出主要目录和关键文件，并简要说明作用
3. **环境依赖** – 需要安装 Docker、Python 3.6+、make 等
4. **快速开始** – 按照用户提供的四步操作：
   - 第一步：`bash scripts/rebuild_phxrpc.sh`（构建 Docker 镜像并启动容器）
   - 第二步：`sudo docker exec -it wwsearch_env bash`（进入容器）
   - 第三步：执行测试命令（两个 python 测试脚本）
   - 第四步：展示预期输出（用户会粘贴执行结果，你需整合进 README 的“测试结果”部分）
5. **测试结果** – 展示 `integration_test.py` 和 `integration_test_v2.py` 的运行输出摘要（例如：`OK (expected failures=1, skipped=3)`），并解释为什么有 expected failure 和 skip。
6. **规则覆盖度** – 从 `business_rules_v2.md` 中提取覆盖度矩阵（框架 100%，业务 59.1%，总体 92.0%），以及黑盒自动化覆盖的规则数量（约 24/56）。
7. **与 AI 交互的提示词** – 可提供 `prompts/` 目录下的提示词文件链接或简要描述。
8. **实现亮点与不足** – 基于任务1和任务2的完成情况，总结亮点（如全链路分析、黑盒覆盖多模块）和不足（如部分规则需白盒/性能环境）。
9. **高 ROI 的替代/补充方案** – 简单讨论突变测试、流量回放、差分测试等。
10. **验收材料清单** – 列出符合验收要求的所有材料（规则文档、测试剧本、测试代码、提示词、覆盖率指标等）。

## 输出要求

- 直接输出 `README.md` 的完整内容，使用 Markdown 格式。
- 不要输出多余的解释，只输出 README 文本。
- 对于用户尚未粘贴的具体测试输出，你可以**预留占位符**（例如 ```` ... 实际输出见下方 ````），并提示用户替换。但最好先根据用户已提供的执行记录（在对话历史中）填入真实输出。
- 保持语言专业、清晰，中文。

## 额外信息（用户已提供）

在之前的对话中，用户给出了测试运行的输出：

请将这些输出整合到 README 的“测试结果”章节。

## 开始

请读取仓库文件（重点关注 `docs/`、`tests/`、`scripts/`、`phxrpc/sample/` 等），然后生成 README.md。
```

