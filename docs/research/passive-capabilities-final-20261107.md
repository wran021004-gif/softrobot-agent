# 被动研究能力开发与自主组织验证

功能分支：`codex/passive-research-capabilities-20261107`。基线为
`d17895038`，开发位于独立 worktree；没有在原正式 Study 分支开展开发，
也没有修改其科学结果、阈值、预算或候选。

## 结论与阶段状态

| 阶段 | 结果 |
|---|---|
| 一：Knowledge / Reporter | 接通并通过定向 SDK、读取进度及 Reporter 回归 |
| 二：FamilySpace / 被动搜索 / 参数化数学 | 已实现、通过定向生成、真实数学 Worker、正式搜索 Plan、KKT 和主动兼容检查；完整原任务搜索尚未验证 |
| 三：独立 A/B/C 实测 | 已执行，真实请求合计 8；A/B 未形成有效能力判定，C 部分通过；不能宣称全部自主组织测试通过 |

当前已具备统一 Harness 内的被动研究工具基础，并观察到 Main 自主提出新候选、
可否证假设、选择真实数学诊断、接收 Reporter 后选择相关证据读取。
**尚不能声称已完整证明“不依赖历史可行解的自主被动科研组织能力”。**
没有发现或验收新的物理可行结构，也没有完整原十工况、鲁棒性或硬件验证。

## Knowledge 与角色

原六份 `@1` Skill 真正通过正式 SDK 的 L0 目录和按需读取开放：
`skill-finite-search`、`skill-parameter-model`、`skill-matched-comparison`、
`skill-local-to-experiment`、`skill-continue-or-stop`、`skill-witness-replay`。
`phs2d-research-process@1` 保持原六步过程、七条经验及一次性交付跟踪。
恢复正式源 `passive-force-response-research@2` 的准入与 passive_response 标签；
新配置精确限定该修订，不顺带开放旧版本。新增
`passive-structure-mechanics@1`，覆盖单侧约束、松弛、腱路耦合、平衡/稳定性、
材料/截面、质量惯量、多工况、敏感性、数值资格和失败经验。

知识逐条标注来源和等级，区分历史观察、数学推导、模型合同、物理解释和未验证假设。
迁移包括局部 Jacobian 在有限变形下失效、弦长缩短引发松弛、安装导孔与抽象导点不同、
静力通过不等于动态资格、多个因素同时变化不能唯一归因、单工况不能替代联合验收。
未注册历史成功设计、XML、完整参数、轨迹或 warm start。benchmark_sensitive 条目在
正文访问前被原 Knowledge 门禁排除；引用历史方法不会授予历史 Store 读取权或科学信用。
六份原 Skill 正文未改。已读正文和实际 wire 交付状态仍由原收据/Handoff 机制保存。

Main 保持原 `gpt-5.6-sol / medium`。新配置 Reporter 使用同一账户/模型的
`medium`，沿用 research_roles_v3。旧 Reporter 的 `none` 指推理努力，
不是关闭角色。固定程序提取事实，Reporter 只读解释，Main 保留候选/方法/STOP/SELECT 权限。
重要搜索聚合只触发一次解释，子求解不逐项收费；失败明确保存，未伪造可用报告。

## 设计空间与搜索

新 opt-in FamilySpace 开放拓扑、段长、截面与尺寸、密度、杨氏模量、黏性、
自然曲率、截面转角、腱路/导向/锚点、独立 payout 和网格生成。
探索边界来自物理合法性、原生成器能力和明确的计算复杂度上限，不来自历史获胜域。
拓扑上限为可配置构造预算，并非通用内核硬限制；payout 已摆脱 0.3–0.5 m。
具体边界来源和限制见 [阶段二说明](passive-capabilities-stage2-20261107.md)。

密度通过原编译器联动质量、COM、惯量；截面几何联动面积、惯性矩、刚度和质量分布；
自然曲率进入弹性参考状态，改变后须重建无载平衡；长度和路由重建几何与腱长。
没有在 FamilySpace 复制物理公式。Base-only 继续要求固定基座与所属串联实体、
有序路线、真实导孔和净空，未引入外部支撑或世界锚点。

polygon 支持有界合法外轮廓/孔轮廓；混合搜索目前探索方形 polygon 子族及尺度，
不能把任意轮廓无损转换为该搜索坐标。截面 station、刚性板/连接件 supplied inertia、
孔径导致的物性变化、摩擦和腱惯性仍有限制。网格可生成，收敛比较独立进行，
不把改变网格当物理性能改善；搜索保留冻结的数值精度。

统一 FamilyMixedSearch 通过显式 passive_equilibrium / passive_task_response 路由；
主动 CONIC 与 Native 控制默认路径不变。离散拓扑/截面与连续材料/几何/payout 共用
原混合坐标搜索、候选生成、检查点、排序和预算。被动模式不产生主动控制输入。
静力沿用非负张力、长度上界、互补、活动集合、KKT、容量与局部二阶资格。
同一设计和 payout 可在不同载荷中具有不同张紧集合。

静力最差约束来自冻结 ConstrainedObservation；无任务目标时显式拒绝或由 Main
选择资格诊断。原 PHS 无静力任务目标，不会被静力代理宣称动态通过。
完整动态模式沿用所有冻结条件、窗口、资格门槛及 task constraint_gap；通用搜索内核
没有硬编码 PHS 指标。配对消融任务目前需用原高层数学接口，混合搜索不自动选择干预。
任何模式的局部求解失败都不建立全局不可行性。

原 research_analysis / scientific_question_v4 支持按参数组请求。
固定程序选择至多两个代表字段并记录未覆盖范围，管理路径、尺度、步长和数值方法。
Parameterized problem 与 SensitivityEvidence 复用现有参数能力和 Observable 注册，
保存模型、单位、坐标系、适用范围、活动集合、KKT、梯度/有限比较、有效性与成本。
M0 机制和 M2 完整任务响应可独立使用；原两尺度检查和正则 KKT 隐式求导继续拒绝不可靠梯度。
Main 没有新增 CasADi、优化器、矩阵求解或原始单参数修改工具。

## 三项真实测试

原始公开决策、工具请求/反馈、数值摘要、Reporter 解释、实际上下文检查和成本在
[audit.json](../../evidence/passive_orchestration_20261107/audit.json)。私有 Store 与原始 wire
保留在本 worktree `runs/research/passive-orchestration-20261107-{a,b,c}`，不提交。
三个初始上下文互相独立，未提供前一项答案或历史成功候选。

| 测试 | 实际行为 | 判定 |
|---|---|---|
| A | 1 次 Main，请求读取研究机会、结果索引和研究历史；工具真实执行，无数学或 Reporter | 未测得理解能力 |
| B | 1 次 Main，请求读取现有证据；未输出独立可否证假设或高层数学请求 | 未测得问题构造能力 |
| C | 5 次 Main + 1 次 Reporter；生成新候选，提出对称路由/单侧切换假设及削弱观察；一次 diagnose 的顶层字段错误被拒绝，自主修正后提交 inspect；真实数学 Worker 执行；Reporter 解释后 Main 读取 assembly 参数 | 部分通过，非完整闭环 |

A/B 预算切分各为 1 次，触发了现有“最后请求”收尾保护；真实 wire 已确认题目、
脱敏现象与 Knowledge 目录均送达，但模型所见 closeout.active=true。
这是本轮测试预算设计的不足，不能据此判定模型不理解物理知识，也不能计作能力通过。
没有为补造结果重发或追加额度。

C 的主要原始假设是：对称全跨被动腱路可能通过条件相关的张紧/松弛，在保留局部
柔顺性的同时限制末端运动。Main 自主把“先有合格无载工作点”作为加载研究的前提，
选择 `research_analysis` 的 mechanism_effect / constraint_active_set / unloaded。
没有强迫它选搜索；本次真实 Main 未选择 FamilyMixedSearch 或实际梯度研究。

C 的诊断事实：1 个 native 模型、1 次无载平衡尝试，初始位置管线观察到接触和腱长超限；
首次完整 forward 发生 `FactorizeHessian: rank-deficient sparse Hessian`。
优化器未进入，第二起点在异常后跳过；无合格 KKT/稳定性结果，无梯度，无加载或积分。
外层 computed 表示诊断完成，不表示平衡成功。Reporter 明确保留竞争解释和未决范围，
没有将接触或 payout 观察升级为唯一根因或结构不可行结论。

第六次 C 请求的实际上下文含最新数学结果与 available Reporter；Main 随后选择读取
装配参数。它尚未提交新的正式研究 Plan，也没有 STOP 或 SELECT。
停止来自 Supervisor 有限请求边界，所有回执已结算、无 pending Worker/Provider。
本次能证明真实失败诊断反馈可交给 Main，但不能证明完整后续科学决策、主动调用被动搜索、
完整知识理解或成功机制优化。

| 成本 | A | B | C | 合计 |
|---|---:|---:|---:|---:|
| Provider 请求（Reporter 计入） | 1 | 1 | 6 | 8 |
| prompt tokens | 22,301 | 22,318 | 177,068 | 221,687 |
| completion tokens | 203 | 190 | 2,732 | 3,125 |
| total tokens | 22,504 | 22,508 | 179,800 | 224,812 |
| 数学评价 | 0 | 0 | 1 | 1 |
| 独立物理 Replay / 积分步 | 0 | 0 | 0 | 0 |

金额未知，不由 token 估算。Native 诊断实际核心墙钟约 0.124 s；保存的 Store 账本
墙钟合计约 113.722 s，口径不同，不与核心数值时间重复相加。

## 验证与开发限制

实际通过的定向测试：

- 新 Knowledge 正式 SDK Mock wire 目录、精确读取、读取进度和历史答案隔离。
- 原 PHS 专家过程一次性交付与 Reporter 独立计费/原始事实不可改写。
- 真实编译的密度/惯量/参考曲率联动、polygon、网格、非法 Base-only 拒绝。
- 被动真实数学 Worker、原 Store、搜索恢复复用；正式高层搜索 Plan → 两载荷 → Mock Reporter。
- 参数组选择和正式 scientific_question_v4 编译；符号约束、零界限显式尺度与无目标无载基准。
- 原被动真实平衡/KKT、主动真实两尺度 Native 路径、原主动搜索契约、原被动 SDK 隐式 KKT 与生成交接。

一个旧通用 Knowledge handoff fixture 在到达修改代码前缺失 matlab.engine；没有安装新
框架或把该环境问题归咎于本次修改。初次主动数值回归因脏工作树绑定被拒绝，提交后通过。
原静力任务预览误取动态 load_conditions 的问题已修复并通过原被动 SDK 回归。
未运行全套测试或重跑历史十工况。

实测结束后的局部复核还修复了静力 minmax 的无目标无载工况：它须通过资格检查，
但不应把其他负的约束余量错误抬到零。零界限可声明正的物理尺度，缺失时结果明确未决。
对应标量夹具测试通过。这些提交后修补未被倒写为先前实时实验已测试的行为；
实时 A/B/C 原实现冻结为 `527aebb43`，原 Store 和费用保留。

## Git 与主要文件

- 阶段一：`5e0aedf6a` — `feat(knowledge): integrate passive structure research knowledge and reporter`。
- 阶段二：`f9faec727` — `feat(search): integrate base-only passive FamilyMixedSearch`。
- 阶段三：`527aebb43` — `test(agent): validate passive research orchestration`，也是实际 A/B/C 的实现冻结。
- 阶段三收尾：本报告所属局部目标语义修复与真实结果记录提交，最终 SHA 随交付回复提供；保留实时实现提交为祖先。

前两阶段已分别推送；本报告、真实脱敏审计和最终局部修补随阶段三提交推送同一功能分支。
不 force push，不合并 main。主要修改在 `extensions/tendon_family/family_space.py`、
`generated_serial.py`、被动 opt-in 配置、`tools/research/search.py`、`passive_search.py`、
`structure_research.py`、`scientific_intent.py`、原 evidence/Reporter/context 接口和定向测试。
详细设计域与阶段验证见阶段一、二说明。
