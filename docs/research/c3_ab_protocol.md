# C3 A/B 与数学证据决策对照协议（草案，尚未授权或运行）

2026-10-25，Asia/Shanghai。工程准备基线见 `c3_p0_math_search_readiness.md`。
本文件不授权 Provider、worker、NMPC、PPO 或任何正式 Study。旧 C3 保持封存。

## 对照一：首次结构获取策略

配置：`configs/research/study_c3_heuristic_ab.json` 与 `study_c3_math_search_ab.json`，
共同复用 `family_study_defaults.json`、`family_space_v2.json`、`reach_hold_c3_mirror.json`
和 `runtime_c3_ab.json`。两份原始配置仅 study_id、输出目录、initial_structure_strategy、
首次策略说明不同。共同执行子域为 1–3 段、3–4 腱；生成和搜索均受此冻结子域约束。
它不修改全家族文件，也不宣称更大拓扑不可行。

| 条件 | 两组共同值 |
|---|---|
| 初始化 | 空候选池、具名全零初态；无历史科学反馈/控制/排名/答案 |
| 任务 | 原 C3 mirror 全部物理阈值、0.35 s 时域和完整独立验收不变 |
| Provider / 收尾保留 | 总 64 / 8，包括 Reporter；不保证全部是主 Agent 请求 |
| Public operations / 收尾保留 | 160 / 16 |
| 数学 | Study 总 24；每次 search 子上限 12，含模型准备和所有内部 CONIC branch |
| 搜索提案 | 单次最多 16；重复/非法仍计提案，实际计算按原账本 |
| 共享物理启动 | 总 8；NMPC≤1、固定回放≤5、PPO stage≤1，训练与其独立评价仍共享池 |
| PPO | 总≤4096 actions，独立评价≤1；原 rollout/优化 batch 与评价保护不变 |
| Native 控制搜索 | ≤60 callbacks、≤2 updates、≤4 knots |
| 额外成功确认 | 0；首次 fresh complete final-fidelity pass 公开读后精确 SELECT |
| 时间和金额 | 原时间预算 null、实际测量；Provider 未返回金额时 unknown，不能记 0 |

64 次总 Provider 是针对旧 C3 25 主请求 + 6 Reporter 的有限扩充，并保留 8 次收尾；
55 是初始最多可执行探索工具的主请求数，后续 Reporter 共享扣减。24 数学额度允许
首次搜索 6 个新结构（本任务每结构 1 模型准备 + 1 CONIC），余下 12 可由 Agent 自主用于
模型诊断/控制/局部敏感性；不是必须用满的目标。物理和控制机会两组相同。
内部 rollout、差分、prefix、CONIC、失败和独立物理 launch 不混为同一个计数。

启发式组由 Agent 自主选择 generate 或 search。数学组在取得首个有支持的
family_mixed_search_v1/task_violation 搜索候选前，只能继续合法首次搜索、诊断或 STOP；
不能通过一次未准入/失败搜索后直接 generate 逃离策略。参数块、拓扑、bounds 和假设仍由 Agent 选。
静态 residual 或局部 Gramian 不替代任务能力。其后结构/控制/数学工具机会相同。

首次运行前由监督者在同一代码/方法/环境下解析并冻结两配置，核对相同共同字段和实际工具 Schema，
绑定新的独立 Study 身份和用户正式授权；保持原 Store、成本、源码与 receipt 所有者。
公开工程 priors 包含生成器/材料/控制默认值及注册模型，不是随机或无信息初始化。
不把本报告、旧 C3、工程复现或历史 probe 的诊断答案塞进新 Agent 上下文。

建议监督启动选项：`--session-handoff --handoff-request-bytes 160000
--pause-exploration-remaining 4 --pause-after-completed-invocations 1`。
须先通过原 live continuation 准入并保存真实验证；本轮 mock 测试不代替它。
Handoff 和暂停只发生于原收据已结算、反馈成对、Reporter 已交付的可验证边界。
监督者每次检查 `science_capable_main_requests`、待 Reporter、保护状态、未决 worker/请求；
如需有限追加，先取得用户授权，使用原 addendum/ledger 在保护和 STOP 前办理。
未知结果先原 recover，不重发、不清零、不重建 Store 躲费用；首个独立成功或合法 STOP 即结束。

封存后用只读脚本：

```text
python -m tests.research.c3_readiness_audit --compare-exports <heuristic-export-directory> <math-export-directory>
```

脚本核对共同冻结条件，列原首次结构 Plan、原 Provider/Reporter usage、ledger、数学内部计算
和独立验收；不重算 evaluator、不按代理评分制造结构排名。用原 action_trace/原始 reasoning
审查路径和机制解释。单次一组只构成有限任务内案例，不作统计显著性或跨任务优势结论。

## 对照二：有无数学证据的下一步决策

复用 `tests/research/agent_math_decision_probe.py` 的 packet/wire、Plan/ResearchDecision、
LiveBoundary、原始保存和 Provider 成本机制。输入草案为
`tests/research/fixtures/c3_math_decision_template.json`；当前 candidate/state/task identity、
common/evidence/round2 均未绑定，未填入目标方向或历史答案。

未来经用户独立授权后，监督者绑定同一个 owned candidate、冻结任务、同一研究初态、
可见方法、原完整剩余预算和公共物理事实。来源必须是原 Store 中验证过的结果与精确 pointer，
包含模型、任务、初态、输入 bounds/order、单位、时间、采样和推断限制。
baseline 数学诊断为空，evidence 组只增加被检验的验证后数学结果；其余逐字段相同。
不要给 baseline 留下结果型状态、排序或 Reporter 文本等间接泄漏。

冻结双方 turn 1 输入、独立 round2 反馈和评分规则后才发送。
反馈不得伪称执行了 Agent 提案；需要自适应执行时，另经用户授权沿原科学接口办理。
turn 2 要求根据真实反馈修订假说。各组历史隔离；Provider 参数一致；一案例两组两轮，
总请求上限 4，Reporter/科学 worker/物理执行均 0。

输出保留原 hypothesis、decision（实际所选方法和预算）、expected_observation、
weakening_observation、fixed_conditions、stopping_condition、interpretation，
以及原 response/reasoning/tool ID、精确完整 wire、receipt、tokens/cache/费用未知项。
以结构修改、控制优化、模型诊断或停止为研究选择，不预设哪一种是正确答案。

冻结输入应将 `binding_status` 设为 `bound_verified_input_v1`，且附真实绑定来源。
现有 freeze 支持 `--cases <bound-input.json> --out <new-ignored-directory>`；自定义输入不会继承
旧 probe 授权。未来 `--approval-file` 必须来自本次新用户授权，draft 和 pending 均阻止 live。
输出目录不得已存在，未知/已发请求不得自动重跑。不要运行默认旧案例冒充 C3 新对照。

只读预览/评分材料（本轮允许）：

```text
python -m tests.research.agent_math_decision_probe c3-template
python -m tests.research.agent_math_decision_probe review --results <saved-summary.json>
```

六项评分均在输入中预声明，由盲审者按原输入/反馈逐项给 0/1/2 或适当 not_applicable：
证据范围解释、可检验竞争假说、区分失败机制的动作、反馈后的修订、完整成本、
以及参数方向是否获后续独立评价支持。最后一项在另行授权的 held-out、同控制机会、
原独立验收完成前保持未评分；未提出方向记 not_applicable。不得根据未来结果修改 rubric。
read-only review 只检查并呈现原字段/usage，不用关键词自动给科学正确性分。
