# PhxRPC 测试重建项目

## 1. 项目简介

本仓库是一套 **基于 PhxRPC 官方源码**，结合系统化梳理与 AI 辅助的 **测试与规格重建工程**。项目在保留 `phxrpc/` 原版代码结构的前提下，完成 **任务一：需求 / 规则重建** 与 **任务二：测试剧本与自动化用例**，目标是将框架行为（FR）、示例业务（BR）、配置与生成器约束（PR/CG）**文档化**，并通过 Python 集成测试在黑盒维度 **提升 PhxRPC 相关测试的可追溯性与完备性**。交付物可作为回归基线：当示例实现或框架行为演进时，可对照规则 ID 与场景 ID 快速定位差异。

---

## 2. 目录结构

| 路径 | 说明 |
|------|------|
| `phxrpc/` | PhxRPC 官方 C++ 框架与 `sample/` 示例（含 `search.proto`、生成代码、`search_main` / `search_tool_main` 等） |
| `phxrpc/sample/` | 示例服务与客户端工具；集成测试依赖此目录下已编译二进制与 `.conf` |
| `phxrpc/codegen/` | 代码生成器（`phxrpc_pb2*`），与规则文档中的 CG-* 对应 |
| `docs/business_rules_v2.md` | **主规格**：56 条规则（FR/BR/PR/CG）、追溯与 **覆盖度矩阵** |
| `docs/test_scenarios_v2.md` | **主剧本**：≥30 个测试场景（TS-xx），与各规则 ID 映射 |
| `docs/business_rules.md` / `docs/test_scenarios.md` | v1 / 演进过程中保留的早期文档（可选查阅） |
| `tests/integration_test.py` | 原始轻量集成测试（3 个用例，保留兼容） |
| `tests/integration_test_v2.py` | 扩展黑盒集成测试（多场景、覆盖率摘要输出） |
| `scripts/rebuild_phxrpc.sh` | **一键**：Docker 镜像/容器、`protobuf`/`phxrpc`/`sample` 构建与服务启动 |
| `prompts/task.md` | 与 AI 协作的任务拆解与产出要求提示词 |

---

## 3. 环境依赖

在**宿主机**上需要：

| 依赖 | 说明 |
|------|------|
| **Docker** | 脚本通过容器提供 Ubuntu 18.04 一致性构建环境 |
| **sudo** | `rebuild_phxrpc.sh` 使用 `sudo docker …` |
| **网络**（首次构建） | 若本地无完整 `protobuf` 源码包，脚本可能触发下载 |

在**容器内**（脚本会安装）：`build-essential`、`python3`、`make`、`wget`/基础工具；PhxRPC 与 sample 编译依赖由 `scripts/rebuild_phxrpc.sh` 编排。

建议使用 **Python 3.6** 运行仓库根目录下的 `tests/*.py`（容器内已装 `python3`）。

---

## 4. 快速开始

以下四步在**宿主机**与 **Docker 容器**之间切换；默认容器名为 `wwsearch_env`，工作目录在容器内挂载为 `/work`。

### 第一步：构建并启动环境

在仓库根目录执行：

```bash
bash scripts/rebuild_phxrpc.sh
```

脚本将：创建或启动 `wwsearch_env`、按需安装依赖、编译 Protobuf / 框架 / codegen、重新生成并注入 sample 逻辑、编译 sample，并在后台启动 `search_main`。

### 第二步：进入容器

```bash
sudo docker exec -it wwsearch_env bash
```

### 第三步：运行集成测试（推荐在 Docker 容器内）

在容器内，`cd /work`，执行：

```bash
python3 tests/integration_test.py
python3 tests/integration_test_v2.py
```

如需详细用例名，可加 `-v`（若脚本支持）。

> 说明：当前测试默认按 Docker 挂载目录 `/work` 推导依赖与样例路径（例如 `phxrpc/sample`），并在部分场景下依赖容器内已配置的 `ldconfig` / `LD_LIBRARY_PATH`。若希望在**非 Docker**或**非 `/work` 挂载路径**直接运行，请通过环境变量覆盖路径（例如 `PHXRPC_SAMPLE_ROOT`、`PHXRPC_TEST_HOST`、`PHXRPC_TEST_PORT`），并确保 `libprotobuf` 等动态库可被加载（可通过设置 `LD_LIBRARY_PATH` 或系统 `ldconfig`）。

**手工抽查示例工具（可选）：** 在 `/work/phxrpc/sample` 下，`Search` 使用 `-q`，`PHXEcho` 使用 `-s`，`Notify` 使用 `-m`（参见工具打印的 Usage）。示例：

```bash
cd /work/phxrpc/sample
./search_tool_main -c search_client.conf -f Search -q 'Hello Tencent'
```

### 第四步：核对预期输出

请参阅下一节「测试结果」中的摘要与说明；若本地环境与下文不一致，以你机器上的完整控制台输出为准替换对照。

---

## 5. 测试结果

以下为在重建环境（容器 `wwsearch_env`，工作目录 `/work`）一次典型运行的**摘录**。完整行级输出以终端保存为准。

### 5.1 `integration_test.py`

```
test_notify_expected_success_when_fixed (__main__.TestSearchToolIntegration)
TS-NOTIFY-01 / BR-Notify-01 / BR-Notify-02 / FR-Result. ... expected failure
test_phx_echo_round_trip (__main__.TestSearchToolIntegration)
TS-ECHO-01 / BR-Echo-01 / FR-Result: -s round-trip and return 0. ... ok
test_search_contains_demo_fields (__main__.TestSearchToolIntegration)
TS-SEARCH-01 / BR-Search-01 / BR-Search-03 / FR-Result: demo title/url in response. ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.011s

OK (expected failures=1)
```

### 5.2 `integration_test_v2.py`

```
test_br_echo_01_roundtrip (__main__.TestPhxRPCRulesV2)
TS-25 / BR-Echo-01 / FR-Dispatch-01 (implicit success URI). ... ok
test_br_notify_01_future_success_remove_decorator (__main__.TestPhxRPCRulesV2)
TS-29 / BR-Notify-01 — expect 0 when implemented; today -1. ... expected failure
test_br_notify_current_returns_negative_one (__main__.TestPhxRPCRulesV2)
Document present behaviour (still passes). ... ok
test_br_search_01_query_ignored_same_output (__main__.TestPhxRPCRulesV2)
TS-26 / BR-Search-01 — two different -q produce same demo fingerprint. ... ok
test_br_search_02_demo_strings (__main__.TestPhxRPCRulesV2)
TS-27 / BR-Search-02. ... ok
test_br_search_03_no_extra_site_fields (__main__.TestPhxRPCRulesV2)
TS-28 / BR-Search-03 — current impl omits type/summary in output. ... ok
test_fr_caller_normal_closed_skipped (__main__.TestPhxRPCRulesV2) ... skipped 'FR-Caller-07 / TS-07 — needs scripted half-close or harness'
test_fr_cfg_connect_refused (__main__.TestPhxRPCRulesV2)
TS-13 / FR-CfgCli-01/02 + FR-Net-01 — unreachable port fails RPC. ... ok
test_fr_cfg_multi_endpoint_file (__main__.TestPhxRPCRulesV2)
TS-08/10/23 — FR-CfgCli-01/03 + PR-Cli — duplicate endpoints still work. ... ok
test_fr_dispatch_http_unknown_uri_404 (__main__.TestPhxRPCRulesV2)
TS-02/03 — FR-Dispatch-03/04: unknown URI → HTTP 404 Not Found. ... ok
test_fr_hsha_queue_drop_placeholder (__main__.TestPhxRPCRulesV2)
Placeholder for queue-wait drop experiment. ... skipped 'FR-Hsha-02 / TS-12 — unstable; enable ENABLE_HSHA_STRESS=1'
test_fr_http_layer_accepts_post (__main__.TestPhxRPCRulesV2)
TS-19 / FR-HTTP-01 — minimal POST hits server HTTP stack. ... ok
test_fr_net_invalid_listen_ip_rejected (__main__.TestPhxRPCRulesV2)
TS-14 / FR-Net-02 — invalid dotted-quad fails fast. ... ok
test_fr_svc_pb_errors_skipped (__main__.TestPhxRPCRulesV2) ... skipped 'FR-Svc-01/02 / TS-16/17 — malformed protobuf body not portable black-box'
test_pr_tcp_server_reachable (__main__.TestPhxRPCRulesV2)
TS implicit / PR-Svr — smoke TCP to configured port. ... ok
test_print_coverage_summary (__main__.TestRuleCoverageReport) ... 
=== Rule coverage (black-box automation) ===
Estimated rules directly exercised: ~24 / 56
Categories:
  FR-Dispatch-01,02,03 (CLI success + HTTP 404)
  FR-Caller-06 (Notify result)
  FR-CfgCli-01,02,03
  FR-Net-01,02
  FR-HTTP-01 (POST reaches server)
  PR-Cli partial (multi-endpoint conf)
  BR-Echo-01, BR-Search-01,02,03, BR-Notify-01, BR-Tool-01 (CLI paths)
Not covered here (see docs/test_scenarios_v2.md):
  FR-Caller-05/07/09, FR-Svc-01/02, FR-Hsha-02, FR-Queue-*, CG-*, many PR-Svr runtime knobs
Reason: requires white-box, traffic capture, or codegen inspection.

ok

----------------------------------------------------------------------
Ran 16 tests in 0.033s

OK (skipped=3, expected failures=1)
```

### 5.3 关于 `expected failure` 与 `skipped`

| 类型 | 原因 |
|------|------|
| **Expected failure（1）** | 示例 `Notify` 当前实现恒返回 `-1`（文档 **BR-Notify-01 ❌**），测试用 **`@unittest.expectedFailure`** 预置「将来修复后应返回 0」，用于盯住缺口而不让整条流水线误报绿灯。 |
| **Skipped（3）** | **FR-Caller-07 / TS-07**：需要可控的半关闭连接或专用夹具。**FR-Hsha-02 / TS-12**：队列等待丢弃与高负载相关，黑盒不稳定，需压力开关。**FR-Svc-01/02**：畸形 Protobuf body 在非白盒条件下难以便携构造。 |

---

## 6. 规则覆盖度

本节数据摘自 [`docs/business_rules_v2.md`](docs/business_rules_v2.md) **Part G — Coverage matrix**。规则总计 **56** 条（FR 37 + BR 11 + PR 5 + CG 3）。

### 6.1 规格侧量化矩阵（加权口径）

文档定义：⚠️ 计半权，覆盖率 = `(✅ + 0.5×⚠️) / (✅+⚠️+❌) × 100%`。

| 范围 | 规则数 | 加权覆盖率 |
|------|--------|------------|
| 框架 + 配置 + 生成器（FR + PR + CG） | **45** | **100%** |
| 示例业务 + 工具（仅 BR） | **11** | **≈ 59.1%** |
| **合计** | **56** | **≈ 92.0%** |

业务侧偏低主要来自示例中的 **占位实现**（如 `Notify`、CLI `-q`/`-m` 未贯通等），框架侧在当前分析提交上为全 ✅。

### 6.2 黑盒自动化覆盖

[`tests/integration_test_v2.py`](tests/integration_test_v2.py) 运行结束会打印：**约 **24 / 56** 条规则**在黑盒层级被直接操练（参见上文「Rule coverage」摘要）。其余条目依赖白盒断言、流量捕获、 codegen 巡检或特定性能拓扑，见 [`docs/test_scenarios_v2.md`](docs/test_scenarios_v2.md) 中 STATIC / SKIP 标注。

---

## 7. AI 协作与提示词

- **工具链**：DeepSeek（提示词设计） + Cursor Agent（代码/文档生成） + Gemini（环境脚本编写与跑通）
- **提示词文件**：`prompts/task.md`
- **说明**：
  - DeepSeek 用于产出结构化的任务1/任务2、README提示词，约束输出格式。
  - Cursor 根据提示词读取仓库上下文，生成规则文档、测试剧本和测试代码。
  - Gemini 辅助编写 `scripts/rebuild_phxrpc.sh`，解决 Docker 环境配置中的路径、编译链接问题，确保一键跑通。

---

## 8. 实现亮点与不足

**亮点**

- **全链路追溯**：从 `search.proto`、生成代码到 `libphxrpc.a` 关键路径，规则带证据路径与行号锚点（见 `business_rules_v2.md`）。
- **黑盒多模块**：集成测试同时覆盖 CLI、HTTP、临时 conf、TCP 可达性等，与 FR-Dispatch / FR-CfgCli / FR-Net / FR-HTTP / PR-Cli 及多条 BR 对齐。
- **可演进基线**：`expectedFailure` 明确标记业务缺口（Notify），避免「全绿但未实现」的假象。

**不足**

- **部分 FR**（如无重试、Normal_Closed、HSHA 队列丢弃、Svc 打包错误路径）仍需白盒单元测试或专项夹具。
- **CG-/队列/监控**等规则当前以 STATIC 或未自动化为主。
- **性能与稳定性敏感**场景未默认纳入 CI，以免 flaky。

---

## 9. 高 ROI 的补充与替代思路

| 手段 | 价值 |
|------|------|
| **变异测试** | 针对已锁定规则做小范围源码/配置变异，检验测试是否真能杀死缺陷，尤其适合 BR-Notify / CLI TODO 补缺之后。 |
| **流量回放** | 抓取真实 RPC/HTTP 报文离线重放，提高 FR-Dispatch、HTTP 头等路径覆盖而不依赖手工拼包。 |
| **差分测试** | 双版本框架或双配置对比输出，捕获重构带来的隐性行为漂移。 |
| **属性 / 模糊测试** | 对 URI、超时、大包边界做自动生成输入，补强 FR-Net / FR-CfgCli 边角。 |

---

## 10. 验收材料清单

| 类别 | 材料 |
|------|------|
| 规则与追溯 | [`docs/business_rules_v2.md`](docs/business_rules_v2.md)（56 条规则 + Part G 覆盖度矩阵 ≈92% / BR ≈59.1%） |
| 测试剧本 | [`docs/test_scenarios_v2.md`](docs/test_scenarios_v2.md)（≥30 场景，映射规则 ID） |
| 自动化代码 | [`tests/integration_test.py`](tests/integration_test.py)、[`tests/integration_test_v2.py`](tests/integration_test_v2.py) |
| 可复现环境 | [`scripts/rebuild_phxrpc.sh`](scripts/rebuild_phxrpc.sh) |
| 提示词 / 方法论 | [`prompts/task.md`](prompts/task.md) |
| 覆盖率指标（黑盒摘要） | v2 测试打印 **~24/56** 规则；规格侧加权 **≈92.0% 总体 / 框架侧 100% / BR ≈59.1%** |
| 源代码基线 | `phxrpc/`（分析提交见 `business_rules_v2.md` Metadata） |

---

## 附录：参考链接

- PhxRPC 上游：https://github.com/Tencent/phxrpc
