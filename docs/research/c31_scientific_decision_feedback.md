# C3.1 — 科研证据范围与成本反馈

2026-10-26，Asia/Shanghai。基线 `2aedb99c6ef222f6f84e0731561339b0c9883914`，
独立分支 `fix/c31-scientific-decision-feedback`。

工程修复已完成；没有验证 Agent 科研决策质量提升。真实 Provider、数学/native/NMPC/RL
worker、MuJoCo/GVS 积分、独立物理评价及正式 Study 均为 **0**。
原 R1/C3 结果、账本、分支和阈值保持原样。

## 实际修复

- 原 EvidenceQuery 同时在 JSON Schema 和运行时要求 `view=fields` 至少选择一个字段。
  其他 view 仍允许默认空 fields。原错误反馈返回明确原因及同 reference/pointer 的
  summary 修正查询；没有增加读取信用或权限。
- 原 EvidenceSummary 对实际已完成、best 仍违反约束的 native 搜索补充范围：
  只是在已记录初始化、参数化和预算下没有找到通过控制，不能证明结构不可行，
  也未排除权重、参数化或求解器限制。没有生成新失败机制或指定下一方法。
- 此范围进入 ResultCard、mathematical_decision_view、当前科学反馈与 L0。
  对旧 Reporter 已保存的数学短包，只在当前内存投影补充原始结果的确定性限制；
  不改封存报告或其原解释。否则旧报告会遮住新增范围，这是定向回归发现的交付缺口。
- 预算标明所属 Study、实际数学计费和 native 已知小计的完整性。
  历史目录同时索引原已声明的 JSON 依赖，因而能显示此前只隐藏在依赖中的 native 结果及原成本；
  历史结果仍仅为参考，不计入当前支出，不取得当前执行或 SELECT 信用。
- ResultCard 显示原 native rollouts、physics_steps、optimization_evaluations 及精确来源。
  缺失值保持 unknown。physics_steps 已含 prefix reconstruction 和 suffix rollout；
  callback 与优化评价计数不再被解释为额外 rollout，独立 replay 成本另列。
  未创建账本、重算历史费用或估计 Provider 金额。

## 已正确实现而复用的部分

原模型对照已经检查候选、控制、初态、网格、保存的预测和逐采样差值。
缺少后两项的真实 B 案例仍是 partial_comparison，不能据不同控制的结果相减推导模型误差。
对齐后的观察也只支持保存的预测差值，没有全域模型有效性结论。

原数学契约已区分 feasible_witness、有条件 model_infeasibility_certificate、
inconclusive、not_applicable 及不完整计算；浮点 support gap 不是真严格界，局部敏感性不是真梯度保证。
原物理接受协议已区分完整通过、完整失败与无效/不完整，未改 evaluator、SELECT/STOP 或准入。

## C3-A 零 Provider 复核

复用 `c3_readiness_audit` 的 A/B/C 原 Handoff source_state 与完整请求投影。
两版源状态一致，全部 **16** 个数学方法保留，当前推荐证据查询可读，状态未改，
R1 最终成功引用仍不可见。完整冻结包仅保存在本工作区忽略的 `runs/c31-offline/`。

| 场景 | 基线 Handoff bytes / 离线 tokens | 修复后 bytes / 离线 tokens |
|---|---:|---:|
| A | 107,592 / 31,129 | 109,842 / 31,801 |
| B | 110,077 / 31,725 | 112,327 / 32,397 |
| C | 109,921 / 32,123 | 112,325 / 32,730 |

tokens 使用仓库原固定 tokenizer 对序列化 JSON 估计，不是 Provider usage。
新增来源与范围有成本，不宣称压缩收益。current_candidate 只保留身份/状态和小来源入口；
best_valid 提供实测瓶颈，已有 same_as 消除相同物理诊断，方法详情和模板已有精确 L1 查询。
未发现需要进一步删掉的同块大信息，故没有为缩短请求隐藏方法或候选。
read_state 仍是交付元数据，不是新科学证据；offload/Handoff/恢复规则未改。

## 定向测试

13 个测试函数通过：新增三项空 fields、有限失败跨层交付及历史/当前/native/replay 成本回归；
复用原 DecisionWorksetTests 四项、方法目录/成本一项、数学 ResultCard 一项、证据等级三项、
真实 B 模型对照一项。测试仅读取封存数据或明确标注的 fixture，无科学计算。

数学 ResultCard 的原测试在基线也失败：断言漏掉已存在的 scientific_interpretation。
已把该确定性字段加入期望，仍逐项验证原证据等级、数值来源和不完整状态。
调试中的函数名/测试类名错误已修正；未隐藏失败或把这些失败视为科学实验。
使用原 `.f3-prestudy-env`；未安装依赖、运行全量 pytest 或真实 Provider。

本修复不证明模型已经能提出有辨别力的实验，也不支持直接启动下一次完整自主 Study。
C3.2 应冻结独立场景与评分标准，再按其单独授权边界验证。
