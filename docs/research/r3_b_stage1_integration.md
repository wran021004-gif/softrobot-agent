# 阶段 I：R3/B 科研架构集成

最终累计完成 **66 个不同定向测试**；完整批次包括 27 项回归、3 项闭环修复回归、6 项短选项单元测试，以及最后 3 项实际 wire 回归。较早一批被环境更新打断，其中 33 个单项已完成通过；这里只按完成的单项计数，不宣称整批完成。重复运行按测试 ID 去重。逐项证据和批次状态见 `r3_b_stage1_validation.json`。

最终没有未修复的已运行测试失败。历史 S57 原档案测试所需 `evidence/sorosim_s56/physics/summary.json` 不在仓库中，因此未下载或重算；迁移后的共享读取器以三个历史包版本的合成输入覆盖。没有执行全仓库测试、真实 Provider 或正式物理验证。真实 Provider 请求、正式机器人 rollout 和完整自主 Study 均为 0。`git diff --check` 和 Python compileall 通过。

实际示例的 `result_1` 为 `computed` / `mechanism_effect`，baseline 为 `0.38 m/s^2/N`；`segments.0.length_m` 的两尺度数值导数均约 `1.0 (m/s^2/N)/m`。这些数值来自合成 worker fixture，不能用作物理结论。固定反馈同时显示 `task_acceptance=unmeasured`、`strict_derivative=false`、5 次 evaluation、0 physics steps 和 0 rollout。

实际 wire 审计覆盖 SDK 截断的历史工具文本：不可解析的截断 JSON 仅保留历史预览提示和原证据查询方向，不把截断内容当作完整阅读。当前固定事实和完整证书反馈仍由原有送达与准入路径处理。当前选中 Schema 优先于历史系统提示中的参数示例，避免要求 Main 填写已由程序绑定的身份。完整请求验证没有内部 SHA 或私有映射。

文件级移植、修改、删除及原因在 `r3_b_stage1_files.json`；实际最终请求在 `r3_b_stage1_wire_example.json`；选择摘要的只读核查在 `r3_b_stage1_store_audit.json`。提交、最终远端 SHA、工作树状态和 Schema/L0 摘录随当前任务的 outputs 交付。

集成分支为 `codex/r3-b-stage1-integration`，底座是指定的 R3 `8dd1e7af`；数学来源为 B `3fad4cd4`。不修改 R3/B 来源分支，不合并 main。最终提交和推送信息见随附交付清单。

## 完成情况

| 任务 | 结果 |
|---|---|
| 分支及依赖审计 | 继承本轮已完成的远端核对和独立 worktree；选择性移植 B 的三个数学模块及实际依赖，没有整文件覆盖四个 R3 主文件。 |
| 意图和执行接口 | 新 Study 使用 V4；`mechanism_research`、`single_parameter_effect`、`control_feasibility` 进入原 analysis；联合搜索继续使用原 Plan search。四种结构操作没有新增顶层工具。 |
| Main 上下文 | 实际 SDK 格式化后的请求使用稳定短引用；完整对象映射留在内部。Schema、证据响应和历史反馈复用同一投影。用户自然语言和原 Store 不改写。 |
| 固定事实和归因 | 状态、数值、单位、两尺度一致性、方向、实际成本及限制独立于 Reporter 交付；区分提出、引用、采纳和候选生成。派生 R3 摘要已按只读 Store 修正。 |
| 测试和清理 | 定向 SDK/Mock HTTP、数学编译、归因、原 SELECT/STOP 和恢复检查；删除薄包装及重复 Schema 遍历，保留独立数学内核和历史证据。详细结果见测试清单。 |

## 唯一配置入口和历史语义

新 Study 设置 `research_decisions.analysis_interface=scientific_question_v4`，沿用 `research_information_flow_v1`、原方法授权、FamilySpace 和预算；联合搜索仍由 `structure_search_interface=scientific_structure_search_v1` 决定。机制计算还必须有原 `mathematical_methods.mechanism_structure_v1` 明确授权及参数准入，不新增 enable/allow 开关。

R3 V1/V2/V3 保留原契约和控制 effort 语义。B 历史 V2 依据冻结规范中明确登记的机制方法区分，不根据请求字段相似度猜测；其 JSON 版本保持 V2，Python 类型命名为 `MechanismQuestionV2`。V4 只把既有科学载荷编译到既有 AnalysisRequest，执行、来源检查和收费仍属于原 analysis.dispatch。新 V4 的差分/优化目标必须由 Main 明确选择 increase/decrease。

候选、冻结协议、内部身份和可机械确定的数值设置由程序绑定。科学假设、目标、参数选择、研究方向和是否采纳归 Main。

## Main 实际接口

`r3_b_stage1_wire_example.json` 保存真实 Strands SDK 经最终输入投影后构建的 Mock HTTP 请求，包括 system、历史、动态工具 Schema 和英文 L0。它是合成测试，不是模型自主研究或真实物理证据。

示例中的 Main 用 diagnose 的 `next_research_action=mechanism_research` 选择接口。下一轮只有匹配结构领域的 V4 研究载荷，不再附带控制领域载荷或底层求解器全集。其科学请求为：

```json
{
  "version": "scientific_question_v4",
  "domain": "structure",
  "structure": {
    "operation": "differentiate",
    "effect_semantics": "mechanism_effect",
    "parameter_paths": ["segments.0.length_m"],
    "target": {"quantity": "tip_acceleration_input_map", "reduction": "norm", "goal": "increase"},
    "operating_point": "frozen_task_initial_state",
    "control_treatment": "fixed_absolute_tensions",
    "requested_budget": 5
  }
}
```

数值事实的权威位置为 `mathematical_research.latest_result`；其他菜单、回放选项和反馈只提供短引用及 `facts_at`。首轮给出具体数值，后续已确认送达且无新结果时保留结论和查询入口。完整 Trace、原始张量、全部差分记录和不可变身份始终留在原 Store，通过既有 evidence_read / research_recall 查询。

结构结果的 `generation_handoff` 指向原 generate 的合法请求。Main 可以读取后采纳，也可以拒绝；数学计算本身不注册正式候选。B0 根据真实参数变化核对采纳，引用证据不等于采纳方向。

## 实际清理

- 删除 `tools/research/diagnostic_relations.py`；唯一的 scoped_feedback 读视图迁入 evidence_views，core 和两个历史测试调用方同步迁移。
- 删除 Plan、数学 Schema 和短引用 Schema 三份重复的定义可达性遍历，改用 contracts 中同一个实现。
- 删除 Replay description 内完整 options JSON、数学 Schema description 内重复的来源对象 JSON，以及 L0 短选项旁的完整对象引用。
- 删除单参数方向摘要中的重复标量字段、重复 native 成本及重复 baseline；完整原始记录保留。
- 正式生成和数学探针共享 `family_configuration`，移除原候选构建中的重复材料化代码。
- B 测试不复制已有 C2 测试正文；沿用现有 fixture，并把必要历史配置放在测试 fixture 目录。未复制 B 的正式研究脚本和研究流水线。

短引用沿用原 Store 行号/结果序号及原 Schema 私有绑定，没有新的哈希验证服务、预算、缓存、送达账本或规划状态机。原控制来源、独立评价、验收证书、SELECT/STOP 和冻结预算的准入保持。

## R3 摘要修正

原 Store 通过 SQLite `mode=ro` 和 `query_only=ON` 核查。`selected_solution` 非空，其 evaluation 与 selected 完全一致，最终 disposition 是 select。短选项摘要正确；总摘要的 null 来自派生审计源漏导出该字段。已补充原审计导出字段，并仅修正派生 JSON；核查依据在 `r3_b_stage1_store_audit.json`。未执行 Replay，未修改原数据库或科研记录。

## 能力边界和阶段 II 接口审计

当前支持原生瞬时机制、受控结构重建、合法两尺度差分、局部有限预算方向搜索、M1 短时固定输入响应，以及已保存的 Conic/Native M2 证据聚合。没有严格梯度、全局最优、硬件结论、完整闭环结构梯度、任意 AD/KKT 或混合接触求导。Native T1/T2 的完整 Tracking 支持边界保持原样，不替换为终点误差。

PHS 来源仅做只读接口核查，未移植其流程：

| 来源接口（9d6d160e） | 下一阶段的精确对接点和缺口 |
|---|---|
| `passive.PassiveModel(physics, protocol, payout, folder, unrestricted=False)` | 独立的 `passive_fixed_payout_v1` 物理语义；payout 单位 m，模型 `nu=0`。不能把当前主动张力通道或 input_force_map 当作被动绳长约束。需冻结 mount/gravity、绳路、坐标和协议。 |
| `StaticProblem.objective/gradient/constraint/jacobian/hessian/qualify` | `g=l(q)-payout<=0`，势能含重力与材料点外力；输出张力、主动集、平衡/原始/互补残差、LICQ、严格互补、约束 Hessian 和约化正定性。需独立的方法契约、适用性和来源绑定。 |
| `passive_equilibrium.solve(native,s=.5,force=0.,initial=None,multistart=False)` | 仅 `qualified_local_minimum` 可作为后续切线基础；区分理想硬约束平衡与 MuJoCo 软约束动态稳定结果。 |
| `passive_equilibrium.tangent(native,equilibrium,s,force,locations,increment=.1)` | 基于合格平衡与正乘子零空间；边界松弛通道使用不等式 QP。输出 `smooth_fixed_active_set` 或 `nonsmooth_or_degenerate`。需保留主动集切换、退化和单边方向语义。 |
| `passive_inverse.design_sensitivity(...)` / `task_design_sensitivity(...)` | 绑定同一被动平衡/载荷、minus/plus 候选、真实参数及步长，不能复用主动张力控制的 M0 差分语义。 |
| `phs2d_evaluation.evaluate(protocol,baseline,loaded,s)` | 原输出 `registered_acceptance=not_registered`，仅开发评分；下一阶段需注册完整任务 adapter/evaluator，不能直接获得现有 SELECT 资格。 |

成本继续接入原数学 allowance：forward、目标/梯度、约束/Jacobian、Hessian 列、QP 和 optimizer 次数采用原返回的 numerical_cost；不得把这些计数当成独立物理 Replay。本阶段未实现上述被动适配，也未启动阶段 II。
