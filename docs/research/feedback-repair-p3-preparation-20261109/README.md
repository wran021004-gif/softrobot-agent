# 通用反馈修复与 P3 启动准备审计

本轮基于 `codex/passive-research-capabilities-20261107` 的实际 HEAD
`8f5a1e7619134d1218f277629f7dce974cfc3f77`，在其干净独立工作树修改。
根目录 `D:/softrobot-agent` 属于另一个分支，本轮未在那里改代码。
修改尚未提交；没有 push、PR、合并或历史重写。

**A–C 已实现并完成定向验证。P3 原始权威材料已恢复，但启动草案仍有六项协议等价阻塞，不能直接启动。**
本轮没有运行真实 Provider、数学 Worker、物理 Worker、积分或 Replay，也没有创建 P3 Store。

## 1. 修改文件与函数

| 文件 | 实际修改 |
|---|---|
| `extensions/reference/passive_evaluation_v2.py` | 抽出 `bound_values()`，原正式 `metrics()` 复用；新增只读 `diagnostic_metrics()`，保留冻结公式、评分窗口、参考状态、聚合与单位 |
| `tools/research_tasks.py` | `ResearchTaskAdapter.diagnostic_task_gap()`：冻结任务身份与轨迹绑定检查；complete/partial/unavailable；来源、时间、未知原因与不可排名标记 |
| `tools/research/feedback.py` | `diagnostic_task_gap()`：重投影已有 Result/record；绑定候选与来源；原 `task_gap()` 排名与正式资格逻辑保持不变 |
| `tools/research/structure_research.py` | `calculate()` 为新有限时域观察附上诊断；原正式 gap 和失败保留 |
| `tools/research/physical_replay.py` | `recover()` 结果组装在 acceptance 外保存诊断，指向原 raw artifact |
| `tools/research/evidence_views.py` | `task_diagnosis()` 同时显示原资格、正式 gap 与逐工况诊断；`compact_task_diagnosis()` 提供短记忆数值投影 |
| `tools/research/contracts.py` | 从现有 `ScientificStructureV4` 派生 `CoupledInteraction`：interact、两个不同连续参数、四点评价；复用现有 Search 类型，不新增工具或算法 |
| `tools/research/agent.py` | `plan_schema()` 对开放 topology 要求有限显式 choices；Main Schema 引用同一个四点 Contract；`error_feedback()` 返回简短搜索修正信息 |
| `tools/research/search.py` | `search_failure()` 从 Pydantic Contract 生成字段、期望、合法值、可重试信息；`coupled_problem()`、`request_guidance()` 对齐四点与预算位置 |
| `tools/research/research_context.py` | `milestone_facts()`、`trace_entry()`、`bounded_action_trace()`、`agent_decision_brief()`、`research_recall()`：真实谱系、增量、数值、成本与解释；`_research_action_trace()` 只投影所需原始字段 |
| `tools/research/reporter.py` | `investigate()` 复用同证据同问题的已有报告版本；`_wire()` 提供前报告身份和新增证据范围，要求解释新增信息 |

恢复的配置、权威源文件副本、草案和四个定向测试文件见本目录及 Git 工作树。
没有修改 `passive_execution.py`、原 PHS TaskDefinition、评价阈值或历史账本。

## 2. 三条数据流

1. **Qualification**：原执行记录和 `inspect()` 的资格检查保留。原失败门槛、原因和逐工况来源继续显示。
2. **Diagnostic TaskGap**：冻结 TaskDefinition/Evaluator + 已保存轨迹 → 共享纯函数 `bound_values()` / `stiffness()` → `constraint_observations()` → 带来源的诊断行。缺数据或无合法提取器时返回未知；不会调用引擎。诊断的 `comparable=false`、`accepted=null`，没有正式排名分数。
3. **Formal Acceptance**：仍由原 `metrics()` / 独立 Evaluator 与 `assemble_acceptance()` 建立。资格失败仍提前拒绝。诊断不能将 invalid 变成 valid，也不会使候选获得 SELECT 或 Replay 资格。

Reporter 只解释确定性数值；Main 选择研究问题和下一步。完整诊断通过原
`evidence_read(view=working_set, pointer=/task_diagnosis)` 读取，不新增数据库。
原正式归一化仍由 `constraint_gap()` 拥有；诊断逐项显示的 signed normalized violation
只描述冻结约束的数值差，不能作为正式候选排名。

## 3. result75 只读回归

来源结果：`d671cd6b1f7200b80fa98239c53fb4e4f5425f5cb7a3551fed445d3fdfb50543`。
候选：`aec951cff2ae5054c9a59f7a3e90c477a5444c1d04f24ca46a8a365408cf6850`。
程序从原保存轨迹、原任务公式、原参考状态与评分窗口重新提取 **251/251** 项，
逐项对比已有人工审查，**最大绝对差为 0**。
另用同 Study 的有效网格、非成功 result34 对照原 HEAD Evaluator，正式输出完全一致。

| 原任务量 | 只读结果 | 原冻结门槛 |
|---|---:|---:|
| 加载点位移 | 1.383751–3.350438 mm | ≥10 mm |
| 末端平面内位移 | 1.711290–3.665312 mm | ≤5 mm |
| 末端/加载点位移比 | 1.058686–1.241839 | ≤0.3 |
| 最大离面位移 | 0.060847925 mm | ≤2 mm |

最严重数值违反是 `s3_positive_ratio_maximum`：1.2418393177312013，
门槛 0.3，signed normalized violation = 3.1394643924373375。
该点的评分窗口为 7.99–8.00 s，last 聚合采样时间为 8.00 s。
加载点和位移比在十个工况都越界；这不依赖于能否消除动态资格失败。
**原正式结果仍为 invalid / `DYNAMIC_STAGE_NOT_QUALIFIED:loaded`。**

完整数值与来源见 [result75-readonly-regression.json](result75-readonly-regression.json)。
只读审计确认原 Store 状态、预算账本、数据库大小及修改时间不变，见
[read-only-audit.json](read-only-audit.json)。原暂停 artifact
`ae838103c71520632eca84dd958f03e328e12d4cc3158d20eb6cd0e49a5f75b0`
仍记录 `execution_paused=true`、`automation_deleted=true`、
`automatic_continuation_authorized=false`。

## 4. Main 和 Reporter 的实际投影示例

[main-decision-example.json](main-decision-example.json) 是现有
`mathematical_decision_view(result_card(...))` 的离线实际输出，包含：候选身份、原资格失败、
十个正负向工况的局部/末端/比值/离面代表值、最严重诊断约束、窗口和来源。
逐工况代表值不会把比值替代其分子/分母，也保留 lower/upper 两类约束。

**这不是已发送给历史 Main 的新消息。** 本轮禁止 Provider，因此没有声称 Main 已阅读这些新诊断。
历史 Reporter 的解释以原证据版本和来源显示；其当时尚不知道的数值，不会被悄悄改写成已知。

## 5. 搜索合同

| 接口 | Main 实际 Schema / 编译与准入 |
|---|---|
| Coordinate | `ScientificStructureSearch` → 原 `FamilyMixedSearch` → `parse_search()` / `search_problem()`；`bounded_mixed_coordinate_v1` 不变 |
| 预算位置 | 科学入口为 `search.structure_search_effort.max_evaluations`；编译后的原合同才是 `search.max_evaluations`。没有为错误位置增加静默别名 |
| 开放设计域 | FamilySpace 保持开放；单次搜索必须声明有限段数/腱数 choices，所选开放连续坐标必须给有限合法局部 bounds |
| 可表达性 | 真实历史复杂 seed 无法无损表达时，明确返回 generate / matched comparison 路径；不投影成不同几何 |
| Coupled Block | `FamilyMixedSearchV2.analysis` 引用 `CoupledInteraction`；仅 interact；baseline、A、B、A+B；两个连续参数、一个完整基线、完整匹配身份与四点预算准入 |
| 无效输入 | optimize、8/12/20 次问题预算、非四点外层预算、越界与缺 bounds 在执行前拒绝；反馈保留字段、期望、合法值和原错误来源 |

测试覆盖实际 Main 最后一级别名 Schema、别名展开、冻结 FamilySpace 绑定与原后端准入。
旧 Coordinate 步进与原合法请求仍工作。未开发新的联合优化器。
失败点、跳过点和真实计算成本仍由现有四点后端和账本保留，未改动其科学算法。

## 6. 紧凑科研记忆

[compact-memory-example.json](compact-memory-example.json) 来自真实研究请求的稳定 step **5819**：

- 保留 result75 和其候选、真实 parent candidate 与 8 项实际黏性变化。例如第 0 段 y 黏性从 0.00375 到 0.0028125 N·m²·s，delta = −0.0009375。
- 方法为 `mechanism_structure_v1`，观测目标为完整有限时域任务违反。正式 gap 仍未知，诊断为 complete。
- 保留历史真实成本：352000 physics steps、10 episodes、396.5153489 kernel seconds 等。这些是旧实验成本，本轮没有重新消耗。
- `observed_facts`、`main_hypothesis`、`reporter_interpretation` 分开。Main 的“中间黏性可能改善”仍是原假设；Reporter 解释有报告版本、状态、片段与全文查询。
- 短上下文取现有 trace limit 内最多六个里程碑，另保留最多两个较早重要失败；更早历史走原 `research_recall`。不塞原始轨迹、完整报告历史或所有候选。

同一问题与同一证据/读取版本复用已有报告；新问题或新证据形成新报告。
没有新 Memory 系统，也没有持久化报告缓存库。

## 7. P3 权威来源、身份与冻结草案

权威来源分支：`codex/passive-progressive-stiffness`；提交：
`83d9b8f35b4015a924e0f8c32d073607247f92b9`。
原任务文件和 SHA sidecar 已按 Git 原始字节恢复：
`configs/research/passive_progressive_stiffness_dev_v1.json`。

- 文件 SHA-256：`3f88a70e4461a384969d2173ae7c5da68379556344fd89df3fed7a7e993b064d`。
- 原协议 canonical identity：`7df0162f9b8d9e8213fb2ef6dbd8bb20628bcd4a411e3788c0532b8402b0e340`。
- 原 FamilySpace identity：`823432cb8ef0f1324e6b497e0dcb101dfcd8ee886a2e57f63c7e18d3d449fc92`。
- 原 Store 的 `development_freeze` 与协议/FamilySpace完全相同；最终 freeze 的 protocol/family 也相同。
- 原任务是 development evaluator，原本没有平台注册 TaskDefinition/正式 SELECT 身份；未伪造该身份。

原 Evaluator、原执行程序和 driver 的 Git 字节副本保存在 `p3-authority/*.py.txt`，
只供审查，不导入生产执行。独立历史 Replay 记录及导出 manifest 也已恢复。
完整来源见 [p3-source-manifest.json](p3-source-manifest.json)。

新独立配置草案：
`configs/research/study_p3_passive_progressive_stiffness_autonomous_v1.json`。
它是 **preparation_only 外层的不可执行草案**，不是可交给 `prepare()` 的运行配置。
候选池、计划和证据为空；Store 和预算账本未创建。初始 Provider 参考额为 24（保护 4），
累计数学/物理次数不限额、按实际成本计账，续额权属于人。
`allow_benchmark_answers=false`；历史成功结构不作为起点、候选或正式证据。
当前安全 Knowledge manifest 预览有 72 条，正式启动时须重新冻结；本轮未更改知识库。

## 8. P3 参数和方法能力矩阵

| 参数或能力 | 原协议 / 当前真实能力 |
|---|---|
| 段、腱拓扑 | 原完整域 2–6 段、2–4 腱；草案保留全部 choices，未套用 U3 的窄域 |
| 长度、材料 | 各段 0.025–0.14 m；Young 模量 2–15 MPa；材料/黏性/密度域由恢复原件拥有 |
| 截面、方向 | circle/tube/ellipse/rectangle 的原始尺寸域；截面角 −π..π；原始文件完整保留 |
| 腱路、终止 | base-only consecutive spans、guide、anchor、radius、phase/angular offsets、末端载荷 anchor；候选实际合法性仍由原家族验证 |
| 自然曲率 | 原权威 FamilySpace 未授予可变 curvature domains，原型为零；通用 registry 支持显式授权后的曲率。不凭摘要把新范围叫作原域 |
| payout | 原为实际零态腱路长度 + [0,0.003] m；当前绝对 payout domain 尚不能等价冻结此耦合域 |
| equilibrium、KKT/active-set | 现有被动原语可用；有效性与动态资格分开 |
| parameterized/sensitivity/matched comparison | 现有真实注册参数、有限局部区间和匹配身份接口可用；无全局可行性保证 |
| Coordinate / Coupled interaction | 现有两个方法可用；后者仅四点 interact |
| 连续五阶段时序 | force_at 可表达 +X/−X、s=0.7、0/0.05/0.1/0.2/0 N、4 s/阶段、20 s、0.5 s interval-end smoothstep |
| 同腱 slack-to-taut | 现有 `PassiveStiffnessV2` 和 `stiffness()` 支持同一腱低载 tension≤0.005 N、slack≥1e−7 m，高载 tension≥0.05 N、残差≤5e−5 m及真实 active row；分母精度和 ratio≥1.5 |
| paired ablation | 现有执行接口支持 Main 选中的约束、公共合格初态、仅禁用所选 limits；两臂无效/不可比时机制必须 UNKNOWN |
| 原机制阈值 | 位移比≥1.25 或末区间刚度比≤0.8，可由现有机制参数表达 |
| CSV / 每步检查 / Replay | 已有完整物理 CSV、every_physics_step route/qualification 能力；原 P3 的完整跨执行证明范围仍有缺口 |
| M2/M3 | 没有被动 reoptimization/closed-loop 后端，保持 unavailable |

## 9. 六项启动阻塞与协议等价性结论

现有连续程序、每步采样、同腱转换和选择性消融提供了大部分机制基础，
但不能宣称当前实现与原 P3 完全等价：

1. 原 development 协议需翻译成有身份的平台注册任务与独立验收，且验证数值等价。
2. 原 driver 每方向从同一个合格静态平衡 qpos 冷启动，阶段连续。当前 continuous_v1 用命名初态；fresh hard-equilibrium 分支绑定 PHS 的 qpos-only 加载复位，均不能直接替代原 P3。
3. 零态路长加 offset 的 payout 域是随几何变化的原域；不能用 U3 绝对长度或任意正 payout 替代。
4. 完整八例验证：两个方向的受限/消融，以及受限半步长和初态扰动；dt=0.0000625 s、0.001·sin(arange(nq)) rad、对应位移差≤0.001 m。当前没有完整通用跨执行聚合证书。
5. 原 Evaluator 使用尾窗平均点位移、全部五个尾窗的 spread 和完整尾窗重读；当前 stiffness 的投影 spread、选定阶段范围、inclusive 窗口与资格中 tip drift 的差异需要审计翻译，不能叫作原公式等价。
6. 原构造器还检查完整轴向装配（含连接件/tool）长度≤0.35 m；仅恢复单段长度域不等价于这个耦合约束。

详情见 [p3-capability-audit.json](p3-capability-audit.json)。
这些缺口未通过放宽原任务、复制成功结构或新增 P3 专用 Agent/Reporter/Search 来掩盖。
因此本轮交付启动准备材料及明确阻塞，**不建议将当前草案直接批准启动**。

## 10. 定向测试、限制和成本

新增四组定向测试共 15 项通过；另两个已有搜索准入/编译测试通过。
旧 `test_search_contract_and_legacy_identities` 中的搜索准入检查均走到通过，
但其固定配置 digest 断言失败。将未修改的当前 HEAD 用 `git archive` 展开后，
原 `resolve(study.json)` 同样得到
`a6446a271e68c152df9c684f792a140b3245a9ab8439817830b09b41d0087dc0`，
不同于旧测试期待的 `31af3e…`，证明该断言失败为原有基线问题；未改测试期待来掩盖。
本轮另一条测试早期误把 cost 中的 `integration_state_saves` 计数当成原始状态，
修正为检查实际原始状态键后，紧凑记忆测试通过。

没有运行完整套件、历史 M1、数学合成实验或物理集成测试。
测试与导出只做配置、准入和已存数据投影；新增科学成本为 **0 Provider / 0 Worker / 0 physics steps / 0 Replay**。
已记录 unittest 批次耗时累计约 178.43 s（包含定向修正复测），完整只读导出约 34–52 s/次。
一次全历史导出因解析占用过大中止，改成单条实际请求投影后通过；原 Store 未发生写入。
完整测试清单和局限见 [test-results.json](test-results.json)。
