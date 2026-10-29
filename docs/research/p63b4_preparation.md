# P6.3-B4：M / M0 准备完成，未执行

基线 `58d5a793223c2c71b145abd3f19a351eb508c7f7`，独立分支
`codex/p6-3b4-math-validation-preparation`。执行代码已提交并通过原 bind 绑定为
`ae315c3565e220b18bbbf4aef02d8685eb3a24ba`；后续交付提交仅增加本说明与审查 JSON。
两个实际 Store 位于本 worktree `runs/research/<study_id>`，不提交完整 Store。
[准确配置、请求、来源与离线检查](p63b4_preparation_audit.json) 可直接审查。

## 1. B3 最后两处检查

确认两处展示缺口，生产修改只涉及 `research_context.py` 和 `agent.py`：

- 保护期 `current_research_state.object.provenance_query` 确实仍指向不在原可读集合中的候选。
  现在依原保护期/同请求收尾状态及既有 readable_results 抑制不可用查询；相邻 current_candidate
  的 parameters/provenance 重复查询同步抑制。非保护期仍提供精确查询，可读集合和权限未修改。
- `remaining_scientific_fields` 原值准确反映顶层 required，但容易被误认为全部科学输入。
  保留该列表，明确标注仅顶层，并单独列出 saved_state 条件下必须二选一的
  `saved_state` 或 `execution + update_id`。当前来源提示直接使用原 operating_point_guidance：
  无保存态时是 missing_exact_state_source，冻结初始态是 frozen_initialization_available。
  没有填入虚构来源或代选工作点，原 Schema/AnalysisRequest 准入不变。

两项定向离线测试通过，14.708 秒：第一项检查保护查询与真实 Mock HTTP Schema/来源交接；
第二项检查独立 M/M0 配置、原候选比较前置条件、完整及 bound 请求 Schema、零授权/零计算。
测试禁止创建 NativeModel 或启动 contained Worker。`git diff --check` 通过。
没有扩大测试到完整科研、五候选链或九任务。没有新增求解器、指标注册或信息流框架。

目前没有离线已确认的合法 Native 请求工程阻断；真实 Provider 行为、数值运行时与 Main 决策能力尚未验证。

## 2. M：独立真实 Main 验证准备

配置：[study_p63b4_m_sol_prepared.json](../../configs/research/study_p63b4_m_sol_prepared.json)。

| 字段 | 已冻结内容 |
| --- | --- |
| Study | p63b4-m-sol-20261029 |
| Resolved identity | 2e0cf5935c3de1a7ae98427ce7e30dd3590b697f2ae66deaea4173555f214b84 |
| 起点 | 原生成器的 2 段 / 4 腱合法候选；provenance.decision_owner=Operator；任务 unmeasured |
| Provider | 原 sol / reasoning=none 配置；最多 12，包含 Reporter、失败和最后 1 次保护收尾 |
| 数学 | 共享 4；Native 每请求 callbacks≤24、iterations≤3、knots≤4 |
| 公共操作 | 32，含 2 次保护操作 |
| 独立物理 / NMPC / RL / NLP / BDF | 全部 0 |
| Knowledge | 原九项 success_case 可读；未预读、未注入正文、未导入历史候选/控制/数学结果 |

候选、配置、解释器/线程/依赖导入检查、代码绑定和未使用预算均就绪；九项 Knowledge 源文件均存在。
尚无本 Study 的 formal_study_authorization 或 live_handoff_admission；原授权检查明确拒绝执行。
没有发送模型目录 GET、Provider 推理或启动 Worker；Provider/网关实时可用性未验证。
独立授权后仍须按既有机制记录准确 Study 授权和 request-feedback Handoff 准入。

届时使用原入口（本轮未执行）：

```powershell
& D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe -m tools.research run --run-id p63b4-m-sol-20261029 --session-handoff --max-new-provider-requests 12
```

不预选方法、参数、工作点或下一步；原 T1/T2 可选权限保留，其他适用 Native 方法也保持原权限。
执行后按原 r3_request / model_original_tool_request / feedback、Plan/receipt、analysis_results、
analysis_request_binding、research_action_trace 和 Reporter 引用逐次审查，不建立新状态表：

| 观察 | 算作什么推进 |
| --- | --- |
| route | 只加载工具，不算 Plan 或数学执行 |
| diagnose 完成 | 已提交 Main 科学选择，不算数学计算 |
| research_analysis 请求 | 区分拒绝、准入与真实 computed 结果，并记录实际费用/来源 |
| 结果后的 Main Plan / STOP | 检查是否引用结果、修订判断或提出有依据的下一行动；重复读取本身不证明利用了结果 |
| 收尾 | 使用准确 fresh-result index；外部窗口暂停不能改写成 Main 原生 STOP |

## 3. M0：Operator 机制敏感性先导准备

配置：[study_p63b4_m0_mechanism_prepared.json](../../configs/research/study_p63b4_m0_mechanism_prepared.json)。
Study `p63b4-m0-mechanism-20261029`，identity
`ebc11388e95f860c0144ae3521d22cf7b7655148f9c9c91d6b8a7ef4c1d77c66`。
使用原 engineering_numerical 模式与原 AnalysisRequest/dispatch，Provider=0、数学=3、公共操作=8，
其余科学额度全 0；该模式仍受原独立授权检查约束，不借 Provider 额度执行 Operator 计算。

原 FamilySpace、task condition 和 protocol 与 M 相同，两个 Store 独立。Operator 明确规定：

- 变量 `segments.0.length_m`，单位 m；域 [0.08, 0.24]。
- 基线 0.160 m，左侧 0.159 m，右侧 0.161 m，名义 h=0.001 m。
  原请求实际浮点 delta 为 ±0.0010000000000000009 m，汇总应使用已记录实际分母。
- 同拓扑 2 段/4 腱、每段 12 cells、Native 48 个命名自由度；非研究参数不变。
- `standardized_initial_pretension`，t=0，interval_start_native；同命名 qpos/qvel 均为零。
  比较时按原内核统一 reset solver history。相同坐标不代表相同平衡或能量。
- 显式绝对张力 `[0.2,0.2,0.2,0.2]` N，通道次序一致，已逐候选核对原张力边界。
  短响应 horizon=0.01 s，非控制再优化。

一个完整合法请求已保存于实际 M0 Store 的 `m0_analysis_request.json`，准确对象也在审查 JSON
`studies.M0.preparation.request` 中。它的 structure_response.candidates 为 `[minus, plus]`，
原结构比较前置检查已确认同任务、控制、离散规则及单个连续参数变化；原 applicability=applicable。
这不代替 Worker 的运行时接触、约束与数值检查。没有实际数学结果，不自动修复或换结构。

另行授权后才可调用原接口（本轮未执行，不提供新的执行器）：

```python
from tools.platform_host import Host
from tools.research import analysis
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.state import guard
from tools.state_io import read
h = Host(ROOT/'runs/research/p63b4-m0-mechanism-20261029',
    'p63b4-m0-mechanism-20261029', actor='Operator')
request = AnalysisRequest.model_validate(read(h.store.root/'m0_analysis_request.json'))
result = analysis.dispatch(h, request,
    'p63b4-m0-fixed-input', guard=guard, origin='engineering_preflight')
```

其中 guard 为原 `tools.research.state.guard`，不是替代函数。一个请求按原规则计费 1+2=3 次数学评价，
预计构建 3 个 Native 模型并执行 3 次短 rollout；实际 model_builds、forward/mechanics evaluations、
rollouts、physics_steps、kernel_wall_s、charged_numerical_s 均以原 Store/receipt 为准。
Native 积分不因独立物理评价=0 而免费；无实际数值可在本轮填写。

## 4. 可复用字段与最小后处理

原 `extensions/tendon_family/mujoco_analysis.py::NativeModel.mechanics` 提供以下原始矩阵，
`tools/research/native_analysis.py::calculate` 已为每侧生成 mechanism_changes 和
finite_difference_per_parameter，路径已逐指标保存到审查 JSON。无需修改内核。

| 原字段 | 原单位 | 中心响应单位 |
| --- | --- | --- |
| mass_matrix_kg_m2 | kg·m² | (kg·m²)/m |
| tip_jacobian_m_rad | m/rad | (m/rad)/m |
| tendon_jacobian_m_rad | m/rad | (m/rad)/m |
| tip_acceleration_input_map_m_s2_n | m/(s²·N) | (m/(s²·N))/m |
| passive_tip_acceleration_contribution_m_s2 | m/s² | (m/s²)/m |

直接复用 baseline/mechanics、structure_responses[i]/mechanics 和
structure_responses[i]/mechanism_changes/<field>/finite_difference_per_parameter；左右 value/delta/candidate、
坐标、张力及成本均保留。不要把原 relative_change 范数当作有方向的矩阵导数。

五类机制矩阵目前没有现成的中心差分字段，需要一次最小确定性后处理：
`C=(F_plus-F_minus)/(p_plus-p_minus)`；或复用单侧割线
`C=(delta_plus*s_plus-delta_minus*s_minus)/(delta_plus-delta_minus)`。
对称步长时等于两侧割线均值。保留完整左右数组及来源、单位、实际分母和左右割线差异。
一个 h 只给中心割线，不证明步长收敛或严格导数；不追加 h/2 计算。

被动贡献严格是 `J M^-1 qfrc_passive`；重力 bias 另有原字段，不能混成全部漂移。
零初始位移/速度下某些被动项或响应为零可以是正常结果；近零基线的相对变化不稳定。
这些是固定坐标/固定输入的机制响应，不能解释为重新优化后的结构能力、因果任务提升或独立任务接受。

## 5. 将来交付给 Main 的路径

M0 原 dispatch 会把不可变数学结果注册到 analysis_results。原 result_card / scientific_feedback
可生成带原始 reference、task_acceptance=unmeasured、费用和限制的确定性 Reporter 报告。
当前摘要只内联第一个对照的少量 scalar；两侧矩阵和割线须经现有 evidence_read 精确 pointer，
或 research_investigate 的显式 reads 读取，不能假称已自动内联五类中心响应。

以后的小型中心汇总可保存为带原结果 reference+pointer 的派生说明，再作为 Reporter 的精确 reads；
原数学结果仍是科学引用，派生说明/Reporter 文字不冒充新的独立物理或数学评价。
M0 的 Provider=0，只能做原确定性报告，不能顺带调用模型解释。

本次 M 是无历史数学导入的独立自主测试，不自动注入 M0。若以后要让 Main 消费 M0，
应在另行授权的后续 Study 中通过既有 research_decisions.mathematics / background+dependencies
声明结果及所需候选/派生说明，再用原 Evidence/Reporter 读取；保留 Operator/历史所有权，
不修改已冻结的 M、不把 M0 结果记作 M 的自主成果。

## 6. 下一次独立授权与停止判断

建议先单独授权一次 M0 的准确请求：3 数学评价、0 Provider、0 独立物理，不循环尝试。
成功说明该冻结工作点下原 Native 接口能产生可比较的机制观测及局部割线，不证明收敛梯度或任务能力。
拒绝/运行失败应按实际候选、来源、接触约束、数值或内核阶段报告；不据此宣称结构不可行。
随后可独立授权 M 的 12/4 窗口；M 不继承 M0 证据，仍自行选择方法。

M 成功要求实际数学结果之后 Main 作出有证据依据的下一决策；只 route、diagnose、HTTP 200
或 computed 本身都不足。未完成则按断点说明，不扩预算、不代交、不推断机器人无解。

本轮已停止在准备：两个实际 Store 均为 0 Provider、0 数学结果、0 控制初始化、0 独立物理，
无 pending Worker、无正式授权事件。仅本 worktree 新增配置、准备脚本、两项测试和两处投影修正；
历史 Study、原权限、数学内核、Reporter 与预算机制未修改。
