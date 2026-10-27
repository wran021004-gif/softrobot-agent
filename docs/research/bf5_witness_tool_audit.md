# BF5 已封存可行解：工具调用链、独立验收与累计费用

本报告只读原 Store 收据、事件和已封存摘要，不启动 Native rollout、MuJoCo forward、独立回放或重新评分。已有成功任务是末端位置加工具轴方向，在 0.58、0.60 s 评分；它尚不是携带工具的定向轨迹跟踪任务。

## 实际调用方式

入口是 `tests/research/bf5_tool_axis_preparation.py`（预检及 `--continuation`）。监督脚本直接调用现有研究链路的 typed dispatch，负责顺序、引用传递、账本与收据，不实现第二个优化器。没有启动 Provider 会话或让 Provider 自主选择工具；Provider、NMPC、RL 调用均为零。

| 顺序 | 研究工具/动作 | 实际实现及收据身份 | 作用 |
|---|---|---|---|
| 0 | Study 准备与绑定 | `core.prepare`、`core.bind`；配置与 implementation binding 事件 | 冻结任务、结构域、预算及版本，无动态积分 |
| 1 | `research_plan(action=generate)` | `core.dispatch` → 原 family generator；`research.core_plan` receipt，request `bf5-design` | 生成并绑定同一 P1 的合法候选 |
| 2 | `research_plan(action=initialize_control)` | `core.dispatch` → `physical_replay.seed_control`；`research.core_plan` receipt，request `bf5-seed` | 预检为常量 0.2 N；续算通过 Store 保存原失败候选/控制的字节，再由原初始化工具完成绑定，无手改控制或验收转移 |
| 3 | `research_analysis(operation=mujoco_direct_control_v1)` | `analysis.dispatch` → contained `execution_worker` → `native_control.calculate` → `local_control_search.search`；`research.candidate_analysis` receipt，request `bf5-native-analysis` | 原 `local_control_search_v2` response 方法；每个回调为从零状态开始的完整 600 步 Native 预测，只能产生代理结果 |
| 4 | `evidence_read` | `core.read_evidence`，原 Store evidence-read 事件 | 阅读 Native 原始结果和控制引用，无积分 |
| 5 | `research_plan(action=physical_replay)` | `core.dispatch` → `physical_replay.dispatch`；外层 `research.core_plan`，request `bf5-replay`；子 `research.physical_replay`，request `bf5-replay-physical` | 新执行 ID、新模型实例，从原初态独立执行完整控制 600 步 |
| 6 | 注册任务评价与协议验收 | `physical_replay.evaluate_playback` → Registry `evaluate.position_tool_axis@1.0.0` → `assemble_acceptance` | 评价独立回放真实位置/轴信号；评价、profile、acceptance 是保存的 artifact，嵌在回放工具内完成 |
| 7 | `evidence_read`、`research_plan(action=select)` | 读取完整回放证据，`_outcome_issue` / `_source_issue` 核查；`research.core_plan` receipt，request `bf5-select` | 仅续段独立通过后 SELECT 并封存；预检独立失败则 `bf5-stop`，保留失败和费用 |

每个阶段有 6 个 Store call receipts：generate、seed、Native、外层 replay、子物理 replay、STOP/SELECT。共 12 个 receipt，不等于 12 次物理计算；每段 5 次 public-operation 计数，子回放各计 1 次 backend solve。没有单独的 `simulation.run`、`evaluation.run` 或 `control.profile_report` 工具调用；不能把嵌入的 evaluator/profile artifact 冒充这些工具的收据。

准备阶段曾直接使用原 NativeModel 做 1 次模型构建及 3 次运动学 forward，0 积分步；这是公开工具 dispatch 之外的域检查，已单列保留。它既不是有界控制可达证明，也不是成功验收依据。用户提出“只能使用研究链路中的工具”之后，续算搜索和验收只走上述研究 dispatch，没有再做链路外的运动学或动力学试算。

## 独立验收依据

续算绑定提交 `091faed0bb31f8679ccb2fb9902dd3f9ddc70b69`，Study `bf5-tool-axis-feasibility-continuation-v1`。Native 分析执行 ID `502dcfa7afe547f7a9585323f929783f`；独立物理回放执行 ID `805f2938e91648acadebf569c805d046`，两者不同，receipt 均 completed 且非缓存。原 Store 的 SELECT 收据已完成，Study 状态 stopped，selected 指向本次独立回放结果。

工具轴由独立回放自己的 `data.site_xmat[tip_site] @ axis_local` 得到；评价器读取其保存的 30 个 post-step 双信号样本，分别在 0.58、0.60 s 计算位置范数误差和有向单位轴的 arccos 夹角，不使用 Native 的预测数值代替回放。全部 8 个协议组件通过：evaluation validity、完整执行、任务 evaluator、位置、轴方向、零 solver errors、张力界和完整双信号采样。

| 指标 | 独立结果 | 冻结要求 |
|---|---:|---:|
| 最大位置误差 | 0.00795895632595311 m | ≤0.008 m |
| 最大工具轴误差 | 0.051758721734539846 rad（2.965556308°） | ≤π/60 rad（3°） |
| 张力违反 | 0 N | 原 0..8 N 物理界 |
| solver error | 0 | 0 |
| 完整性 | 600 步，30 个 post-step 双信号样本 | 全时域完成，两个评分时刻完整 |

真实独立 evaluator artifact 为 `2cb9d744183d0230d91d8acf3f1f3b28bd770d6f7e65ded26e8be2ce245e0e08`；[公开成功收据](../../evidence/bf5_tool_axis_continuation/summary.json)保存这个引用及全部验收组件。本地 Store 保留 raw/profile/acceptance 的完整映射；原程序的 `_outcome_issue` 与 `_source_issue` 均无问题。本次仅阅读已保存结果，没有重新调用 evaluator。

“独立”指同一 MuJoCo 物理模型下的新执行及独立任务评价，不是硬件、不同动力学模型、鲁棒性或重复性验证。此可行解没有完整姿态或轴向 roll 约束，也没有定向轨迹或额外工具负载的验收条件。

## 累计费用

| 阶段 | Native 完整回调 | 独立回放 | Native / 回放积分步 | Store 数值累计 s | 驱动 s |
|---|---:|---:|---:|---:|---:|
| 原 BF5 预检，valid_failure | 51 | 1 | 30,600 / 600 | 5.672948 | 9.403430 |
| BF5 续算，accepted | 3 | 1 | 1,800 / 600 | 2.893614 | 6.907970 |
| 到首次独立通过的 BF5 合计 | **54** | **2** | **32,400 / 1,200 = 33,600** | **8.566562** | **16.311400** |

动态阶段模型构建共 4 次；前置运动学检查另计 1 次构建、3 次 forward、0 积分。原失败回放不能扣除；续段第 3 次回调通过，不能写成从常量起点总共只需 3 次。续算在有限差分探测阶段达标，完成 response proposal 次数为 0，不应将其报告为一次新局部求解器 proposal 的成功。

Store 数值累计包含 worker 与研究准备开销，驱动时间包含前者，不能重复相加。原始 ledger `wall_s`、Native kernel 与回放 kernel 时间具有不同计费边界；不能将其中任一项改名为总实验耗时。以上不是货币费用或实时运行性能。零 Provider 请求没有产生模型服务用量。

BF4 S2 另为 **606 次 Native、6 次独立回放、367,200 步、51.497991 s Store 数值累计**，保留原公平 C 类结论。S2 加 BF5 两阶段共 660 次 Native、8 次回放、400,800 步；此合计不包含更早 BF4 S0/S1/S1b。历史 S1/S1b 的 329 次 Native、4 次回放、199,800 步及 S0 的 1,200 步仍各自封存，不转移为新任务余额。

本次审计新增科学计算为 **0**。下一项携带工具的定向轨迹任务需要独立冻结和独立预算，不能沿用这条可行解的通过身份。
