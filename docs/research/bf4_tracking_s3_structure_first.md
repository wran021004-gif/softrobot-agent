# BF4-S3：结构搜索后控制求解的总成本对照

2026-10-27 用户授权从以往已找到可行见证的任务中选择一项，固定采用“先结构搜索优化，再控制找解”，全部新增科学工作只能使用 Study 链路，观察是否加快求解。选择原 BF4 定时空间转向 Tracking：原 0.6 s、1 ms、30 个 post-step 点、12 mm、seed17、初态、重力/地面及原负载和独立 evaluator 不变。原 BF4 S2、BF5、BF6 证据与成本保持封存，不导入历史成功控制。

## 执行前冻结

[S3 总冻结](../../configs/research/bf4_tracking_s3_freeze.json)声明三个独立新 Study：

- [结构搜索](../../configs/research/study_bf4_s3_structure_search.json)：原 `research_plan.search`、`family_mixed_search_v1`、`task_violation`。固定两段、六通道、distributed_consecutive 路由、原材料/截面与 12 cells 标准精度，只搜索两段长度，合法子域每段 0.10–0.16 m。最多 8 proposals、10 个数学评价单位，预期最多 5 次原模型构建和 5 次 CONIC 内部求解；全部构建、失败、求解成本计入结构优先路线。无数学 proxy 独立物理通过的声明。
- [结构优先控制](../../configs/research/study_bf4_s3_structure_first.json)：只使用原搜索工具返回的 best_mathematical_candidate，不由代理手动指定优化后结构；模型未返回受支持结果则如实停止，不换代理指标补结果。
- [直接控制对照](../../configs/research/study_bf4_s3_control_only.json)：使用搜索工具第 0 行的原始结构 S0，选取规则与分数无关。该结构由原混合搜索初始化规则和冻结族域默认值确定；不是事后挑选的较弱对照。第 0 行若非法，不拿后来合法或不利候选替代。

两个控制 Study 都通过原 generate 在最终精度重新生成各自结构并核对结构/离散化一致，再从全六通道常量 **0.2 N**、零物理状态开始。既不继承 CONIC 控制，也不继承旧成功控制、状态或验收。结构搜索的任务模型含局部线性化控制优化，这些内部求解全部计入搜索开销；它们不替代下一阶段的 Native 控制与独立验收。

两臂控制设置完全相同：原 `mujoco_direct_control_v1` + `local_control_search_v2/response`，4 knots `[0,0.2,0.4,0.58]`、24 系数、0.02 N 单侧差分、0.2 N 初始半径、0.005 内部规划余量，最多 **201 个 Native 回调、8 轮 response、1 次独立回放、121,200 积分调用尝试**。新对照的相对系数界统一设为 8 N，实际张力仍受原 0..8 N 硬界限制。这是两个新 Study 的共同优化器设置，不倒改旧 S2 的 ±2 N 身份，也不拿旧 S2 的首达成本作公平比较分母。

总物理上限 402 Native、2 回放、242,400 积分调用尝试，另有上述最多 10 单位的结构数学预算。所有新配置、公开监督入口 `tests/research/bf4_tracking_s3.py` 和本协议先提交，再绑定执行；科学计算只由现有 core/analysis dispatch、原搜索/生成/优化/回放/evaluator/Store 完成。没有链路外结构打分、私有优化器、手工挑选 winning design、PPO 或整仓测试。

## 对照与停止规则

预定顺序为结构搜索 → 结构优先控制 → 直接控制对照。三个 Study 各自记账，两个控制臂各自在首次完整独立通过后立即 SELECT；另一臂是预先授权的独立比较，不在已通过 Study 内续算。有限失败、contact/数值异常和未知内部进度保留真实成本，不重开同一账户或追加候选。

结构优先总成本 = 全部结构搜索准备/构建/数学/失败 + 选中结构的重新构建/控制/独立物理验收；直接控制总成本 = S0 重新构建/控制/独立验收。记录 Store 数值与包含启动/编排的 driver 两种口径，不重复相加；另列 Native 回调和积分数量，不能省略搜索成本只展示控制段更快。

仅当两臂均取得新独立可行见证时，计算本次名义总成本比。若一臂在预算内失败，该臂真实首次通过成本未知，不编造精确加速倍数。若工具最优仍为 S0，如实报告没有找出结构改进。一个确定性配对只用于此实例观察，不证明普遍或统计提速，也不证明全局最优。

## 首轮配置拒绝与独立 R1 修正

首轮冻结提交 `a2ff85cdb` 后，原混合搜索提出 8 次、跳过 2 个重复/截断移动，6 次生成均被原 BF4 校验以 `TRACKING_HAS_NO_REACH_HOLDING_OR_ABSOLUTE_SPEED_COST` 拒绝。通用族域的 holding/terminal speed-weight 默认值均为 0.1，原混合搜索会把它们写入 generation；而 BF4 原 Tracking 控制契约要求这两个权重为 0。没有生成合法结构，因此按预定第 0 行基线规则，没有替换一个后来候选，也没有运行两路控制。

该轮已 STOP，数学模型、CONIC、Native、物理步和回放均为 0；真实生成/编排成本为 **0.4500102 s Store 数值、4.0838841 s driver**，见 [原失败摘要](../../evidence/bf4_s3_initial_failure/summary.json)。它是冻结接口默认值不匹配，不是结构不可行或数学模型表现差。原配置/账本保留，不重置。

执行必要的 R1 配置修正：新[族域包装](../../configs/research/family_space_bf4_s3_tracking.json)仍单层组合原物理 prototype，只将两项 control-domain 默认值设为原 BF4 要求的 0；控制域边界、物理 prototype、结构参数域和原任务不变。不是修改 evaluator 或删验收条件，也没有修改混合搜索/数值工具代码。

[R1 冻结](../../configs/research/bf4_tracking_s3r1_freeze.json)及三个 `study_bf4_s3r1_*` 配置重新提交后才执行。新独立账本保持原 8 proposals/10 数学单位及每臂 201 Native/8 response/1 replay/121,200 步上限；不是借用旧余额。公开编排入口 `tests/research/bf4_tracking_s3r1.py` 仍仅调用原 Study 工具，且**将首轮全部失败开销纳入结构优先总成本**。后续比较既不会删除该失败，也不会把其耗时分摊给直接控制对照。

R1 首次启动时，执行前的 fingerprint assertion 发现外部总协议错误地使用完整族域 digest，而原 Study 解析器会先应用已冻结 topology_scope，得到仅两段/六通道的精确族域。此时原 Study 为 ready，候选、数学评价与分析结果均为空，没有科学工具调用。原 Study 的权威配置/预算本来就是正确的，未修改它们或创建新余额。

总协议版本 1.0.1 改为原 Study 已有的精确 fingerprint，并通过原 bind 带明确原因登记实现迁移，发生在第一项科学调用之前；保留原预算及 startup。该次失败命令耗时为执行工具实测 **1.4803855 s**，另列操作启动开销并加入结构优先 driver 总额，不伪装成数学求解耗时。详见 [manifest 检查记录](../../evidence/bf4_s3r1_manifest_check/summary.json)。不将这次登记错误解释为物理/结构失败。

结果将在 R1 执行后追加；本轮不修改原 TaskDefinition，不扩建新任务类别。
