# Reporter → Formal Plan 与自主被动混合搜索验证

基线 `9c59b7d771c5fb179d8cadbd8565ea536c3b1579`。在同一功能分支保留此前提交。唯一新真实 Study：`passive-post-reporter-mixed-search-20261107`，现已 `stopped`，没有待执行科学动作、悬空 Provider 请求或未结算占用。

## 验收结论

| 能力 | 结果 | 依据 |
|---|---|---|
| Reporter 后正式 Plan | passed | 真实 Reporter seq111，真实 Main Search Plan seq250，均存于原 Store |
| 决策衔接 | partial | 直接 Plan 已可用且形成前未进入 Closeout；仍有重复读取、无效输入和中途接口修复 |
| 自主混合搜索 | passed | Main 自选 tendon_count + routing；实际发生腱数与相位更新 |
| 搜索执行与证据 | passed | 三个新结构均真实评价、保存成本；Main 获得保存结果的数值投影并提交准确收尾 |

这是一次经维护者审查和修复后完成的连续真实实验，不是最终版本从头无干预运行成功的证明。没有另开第二次真实 Study 来掩盖失败，没有程序代写科研 Plan，没有重算搜索。

证据入口：[审计](../../evidence/passive_post_reporter_search_20261107/audit.json)、[验收及数值摘要](../../evidence/passive_post_reporter_search_20261107/assessment.json)、[旧失败只读审查](../../evidence/passive_post_reporter_search_20261107/previous_failure_review.json)、[初始预算检查](../../evidence/passive_post_reporter_search_20261107/budget_check.json)、[主动兼容性](../../evidence/passive_post_reporter_search_20261107/active_regression.json)。原始私有 Store 未纳入 Git；未导出凭据或历史成功结构。

## 1. 上次失败的真实原因

旧 `passive-knowledge-loop-20261107` 仅通过 query-only Store 和原审计读取，未修改旧 Study、预算或 Evidence。Reporter 解释确实交付给后续三个 Main 请求。第一个请求已有 diagnose Plan 入口，Main 仍选同一 diagnose route：不是必须的步骤，公开记录不能确定其内部动机。

当时单动作 Schema 使其他 Plan 先经过 route，route 只选择工具，明确需下一个请求提交。L0 同时说旧 diagnose 完成、提供数学接口、建议新诊断或 route，表达存在冲突；被动动作过滤器还遗漏了已实现且授权的 search。最后一次普通请求消耗于路由，随后两个 Closeout 无权新开研究。12/2 算术正确，但阶段容量不足。更早的无效 metadata 查询、刚存 Plan 的重复读取、错误顶层 selected_candidate 也浪费容量，不能全归因于预算。

## 2. route 与 plan 的职责

Reporter 可用后，在原 information_flow_v1 工具选择机制中同时暴露当前已准入的正式 Plan 动作。Main 知道动作即可直接 research_plan；research_route 保留用于动作或工具歧义。原编译、候选/证据引用、准入和费用检查照常执行，没有新 Planner、Agent、状态机、计数器或搜索器，没有自动生成科学 Plan。

修复空候选动作列表产生 enum:[] 的 Schema 情况。发现并修正被动 L0 遗漏 search：只在授权了被动搜索模式时显示，主动动作过滤不变。

## 3. 决策上下文和实际发现的接口问题

L0 增加最新数学来源、当前候选、Reporter 支持/削弱/假设/未知解释索引、直接正式 Plan 动作和被动搜索能力。Reporter 与 Knowledge 是参考解释，不变成实验事实；不注入全部正文或底层矩阵。

真实请求8缺失材料组 physical.* 有限区间，随后又把搜索组 materials 当作普通参数分类。补充原 Search.bounds 的精确字段目录及冻结域、保留有限区间错误跨读取的反馈，并说明一个候选按选定工况数收费。没有替 Main 选组或区间。

原可表示种子判断错误地把生成器固有的站点截面旋转判为不均一截面。修复尺寸/形状比较，保留原型角度的独立精确检查；额外旋转及真正异形仍拒绝，不做有损转换。真实 Main 最终明确选择新的 family-default 中心，原候选只作为研究证据。

真实搜索完成后发现旧 scientific_result_delivery 假定所有搜索都有 Native 控制 comparison_summary，导致下一次发请求前 KeyError。改为 Main 与 Reporter 共用一个被动静态批次事实投影，保留拓扑、实际变化、各工况资格、独立基线资格、失败、成本、最佳数学候选和证据指针；子分析归属原批次，不套用 Native 控制 J 排名。只重读已保存结果，没有重算。

## 4. 预算阶段与实际请求

初始共享 Provider16，Closeout2包含在其中；数学4，搜索评价最多3，提案授权最多8，物理/Replay/BDF/NMPC/RL均0。复用 last_requests_v2 和现有已结算暂停：Reporter 前剩余普通容量阈值5，最迟9次 Main 后保留一次 Reporter、四次普通 Main、两次 Closeout；Reporter 后阈值2。不新增预算系统。

实际顺序（编号为 Main/Reporter 共用请求序号）：

| 请求 | 实际动作 |
|---|---|
| 1–5 | 新候选、修正无效诊断参数和一次多余 route、真实无载数学诊断 |
| 6 | 首个真实 Reporter；此时 Main仅5次，及时触发 |
| 7–9 | 读取路由；直接 Search Plan 因材料有限区间不足拒绝；误用参数分类 |
| 10–12 | 研究回读和失败输入/参数分页；已结算边界审查 |
| 13 | Main 自主改为腱数+路由、单载荷；task_violation 静态目标不可用，求解前拒绝 |
| 14 | Main 自主改为 equilibrium_qualification；正式 Plan 保存并真实搜索 |
| 15 | 结果读取及收尾所需未探索机会检查 |
| 16 | 准确解释结果，正式 STOP Plan 保存 |

用户直接说明预算仅供参考、可按实际进展追加，覆盖附件“不追加”的旧约束。维护者在12次已结算请求后通过原有限追加机制明确增加8次，seq214，Provider16→24；失败、费用和计数均保留，Main不能自动扩额。最后总用量仍为16，剩余8次；不是因为 Provider 用尽而停止。数学4次完成了本次限定静态实验，没有因额度不足截断已提交研究。

## 5. Reporter 后正式 Plan

真实 Reporter `0da973b327…` 在seq111返回 available，引用初始数学结果与相关 general-equilibrium/general-sensitivity 知识。新 Search Plan `d42d82a04a…` 在seq250创建，晚于 Reporter；Main明确关联 candidate_19 与 result_1，提出可证伪 H2、变量、依据、削弱条件、固定量、最多6提案/3工况评价和终止条件。

搜索中心由 Main 明确选为新的默认结构，而非投影 station-dependent 原候选。result_1 是科学前提，Reporter 不是 supporting_evidence。后续 STOP Plan `85ed3e098f…` 在seq338保存。不存在固定程序从 Reporter 自动触发搜索。

## 6–7. Main 的变量选择与理由

离散组 tendon_count∈{3,4}；连续组 routing。Main认为新增腱可检验方向约束覆盖，路由位置可检验横向载荷下张紧参与及资格是否保持。固定两段、whole_chain 跨段方式，以及长度、材料、截面、payout坐标，以减少三次评价中的混杂因素；固定 payout 坐标不表示更换路由后实际腱路零态长度完全相同。

Main 自定有限区间：anchor_s [0.75,1]，guide_s [0.3,0.7]，radius_m [0.012,0.022]，phase_rad及angular_offset_rad均[-0.35,0.35]。这些是局部至中等幅度试验子域，不收缩完整 FamilySpace。只选 s3_positive，使三次工况条目能评价三个结构。

Main最初想检查任务 proxy；接口明确拒绝静态 task_violation 后，Main自行将假设收窄为“离散+连续变化下是否保留合格静态平衡”。本次验证的是这个较弱假设，没有宣称改善位移或原任务性能。

## 8–10. 真实执行与数学结果

原 FamilyMixedSearch / bounded_mixed_coordinate_v1 完成3提案、3合法构造、3真实评价，未跳过坐标。以3次评价耗尽终止，未到6提案上限。Main只提交高层问题，固定程序完成模型生成和求解。

| 本次候选 | 腱数 | 实际变化 | 相位rad | 资格分数 | s3_positive |
|---|---:|---|---:|---:|---|
| candidate_271 | 3 | 默认中心及授权区间初始化 | 0 | -0.999241927 | 合格 |
| candidate_280 | 4 | tendon_count | 0 | -0.999513111 | 合格 |
| candidate_289 | 4 | routing.phase_rad | 0.175 | -0.999927928 | 合格 |

三个加载条件均 computed，LICQ、严格互补、容量及约束资格通过，正约束张力数分别2、2、1；最大张力约0.03621、0.03151、0.03200 N，最小约化刚度约0.19041、0.19051、0.19053 N m/rad。最佳数学候选 `c1afb9f608e0c8105e8d5046cc3697fa27bff449551c29a3fa779a02358acb59`，加载 stationarity≈7.207e-11 N m，primal violation=0。

资格分数是归一化 KKT 残差量，数值更低不代表更好的任务响应。最佳候选独立无载 multistart 摘要中的选定工作点 LICQ和严格互补不通过；它与上述加载平衡是不同工作点，不能混为普遍稳定/鲁棒结论。失败输入、不可用目标和投影异常均保留，不能算结构物理失败。

只测三个点、一个载荷、一个实际连续相位更新；三段、其他 spans、材料/长度/截面/payout、绝大多数路由组合、反向及其余载荷均未探索。完整动态任务、独立Replay、十工况正式验收保持 unmeasured。

## 11. Main 的实际读取和理解

第15次真实请求读取保存搜索结果 `/result`、all_fresh_results及收尾所需 research_opportunities。原结果过大，因此全文请求返回 main_evidence_navigation_v1 索引，不授予全文或正式验收阅读资格。关键数值实际通过当前 L0 的有来源批次投影及 working-set 索引交付；不声称读完全部原始数组。

第16次 Main自行准确描述三个候选、离散与连续更新、最佳数学候选、加载资格与无载基线不一致、分数语义、未搜索范围及任务未测量，并提交正式STOP。这证明理解了实际保存结果的相关事实。第二份搜索报告的确定性事实已保存，但真实 Reporter 解释因数学额度耗尽触发 protected closeout 而 unavailable；没有第二次真实 Reporter 请求，未伪称两轮解释均完成。

## 12. 实际成本与科学身份

Provider Main15 + Reporter1 =16/24，剩余8；总tokens596730（Main586213，Reporter10517），美元成本未知。初始诊断1次、搜索3次，共数学4次；各自charged_numerical_s为1.236956、1.593547、1.451719、1.508981，总5.791203秒，其中搜索4.554247秒。外层搜索elapsed14.770543秒与子成本重叠，不相加。科学台账归集4模型、1989次native forward、352个Hessian列、414次优化器迭代、7次平衡求解；积分、rollout、Replay均0。

同一Study保留连续身份及全部历史：初始诊断源码80e259977，搜索源码c57395c5f，最后结果交付源码702787523。中途原bind迁移声明 material_behavior_change=false、原数学profile版本1；更改元数据/接口反馈，没有更改科学模型、物理条件或重生成已有结构。审计保留这些来源，不能将全次实验说成同一最终SHA从头运行。

## 13. 必要验证及主动兼容性

五项新增针对性测试通过：直接原Plan契约/可选route的真实SDK+Mock HTTP检查；上下文/来源/有限区间与计费目录；16/2原台账阶段保留；真实坐标编译和可表示种子；Main/Reporter共用被动搜索投影（明确标记合成数值，无真实Provider）。真实已保存搜索结果只读投影也通过。

现有主动种子/路由保留检查通过。一次原生主动真实 two-scale 检查通过：5模型、16forward、5数学评价、0积分；另一个真实执行器模型编译nu4。该兼容检查不等于梯度可信：两个差分方向相反且信号低于阈值，derivative_status仍unreliable。没有为通过而修改算法。共享反馈修改后，现有 Native 搜索交付真实SDK/Mock HTTP回归单独通过。两项旧SoRoSim Mock检查在fixture阶段缺matlab.engine，未通过，未安装或用替代结果冒充。没有大型套件、完整物理搜索或十工况重复。

## 14. Git 交付

保留基线之前全部提交，新增：

- `80e259977` — fix(research): preserve post-reporter planning capacity
- `c57395c5f` — fix(search): expose finite coordinate bounds and condition costs
- `702787523` — fix(search): deliver passive batch evidence to Main
- 本报告及最终审计独立提交：test(search): validate autonomous passive mixed search

正常推送至 origin/codex/passive-research-capabilities-20261107；交付时核对本地HEAD与远端相同。未amend、重写历史或force push。仓库只包含任务代码、测试、配置和允许导出的实验审计/报告，未提交私有Study Store、凭据或历史成功设计。
