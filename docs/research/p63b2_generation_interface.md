# P6.3-B2：生成入口最小修复与 G / M 草案

基线远端及本地均为 `codex/p6-3b1-sol-math-study@59b7e690fe6588680872ccf6dd14d930b59c449b`。在独立 `codex/p6-3b2-generation-interface` worktree 开发。只读核对两份 Study 报告及审查 JSON、生成器/FamilySpace、工具加载及 L0 源码；另外按审查 JSON 中的原引用各读取一个真实请求 artifact，核对 Knowledge 已读进度，没有扫描或重复加载完整历史 Store。

## 实际失败与修复范围

- Luna：6 次 route（5 次 generate 入口），0 次 Plan。generate Schema 在首个请求及 route 后均可用，选择入口没有变成动作提交。
- Sol：Provider 12 次均为 200；两次 generate 服务调用成功返回，但业务结果为 invalid。第一次第二段只给一个截面，违反原型的 2 个站点要求；第二次 cells=2，违反冻结 [12,12]。有效候选、数学请求、数学计算和 Reporter 均为 0。不能将 HTTP/工具调用成功当成结构有效，也不能将输入失败说成数学求解失败。
- 重复读取确实发生，Knowledge 进度并未丢失。Luna 第 8 次请求 `r3-request-580b11d5b01341d396fba01339a3a162` 的 L0 已有 research-bounded-continuation@2 的 tool_read_completed=true；这是首次携带正文的请求，body_delivered 尚为 false。Sol 第 10 次 `r3-request-1ad1827b6fc5445a8560c9f7bfbc1d61` 两个标记均为 true。确认交付只证明原文进入请求，不证明理解、采纳或科研证据资格；不修改 Knowledge。

生产改动共三个文件，约 30 行新增，仅改变提示及 Schema 投影：

1. `extensions/tendon_family/family_space.py::decision_summary` 从现有冻结原型派生 generation_inputs：只填想改变的变量；未改变的 sections/cells 等可省略；显式截面数和顺序匹配原型站点；显式 cells 遵守 serial_assembly.cell_count_bounds。v2 按已有 root/repeated 原型派生，v1 按原索引派生，没有第二套域表。保留“有效生成只是未经任务评价的候选”说明。`resolved_request` 和生成器逻辑不变。
2. `tools/research/agent.py` 通过原 generation_contract 交付该摘要。原 compact_plan_schema 为可选 sections/cells 补充继承说明，v2 cells 的 integer 分支直接取冻结上下界；省略和 null 仍可用。原 Schema 校验与原执行域检查继续成立，未自动补交或修复用户请求。
3. `tools/research/research_context.py` 由实际 loaded.plan_action 投影 direct_plan：已暴露的 Plan 可直接提交，无需再 route；route 继续负责切换。generate 可用时附上 generation_inputs，不重复注入完整结构域。没有选择或提交候选、科研假设或参数。

例如 M1 的派生 L0 关键部分为：

```json
{
  "direct_plan": {
    "tool": "research_plan",
    "action": "generate",
    "instruction": "This Plan Schema is already available: submit the Plan object directly to act; no research_route call is needed for this action.",
    "generation_inputs": {
      "overrides": "Supply only design variables you intend to change. Omit unchanged sections, cells and other optional overrides; the existing resolver inherits frozen defaults and prototypes.",
      "sections": {
        "prototypes": [
          {"applies_to": "index 0", "prototype": "segment_0", "count": 1, "stations_s": [0.0]},
          {"applies_to": "indices >= 1", "prototype": "segment_1", "count": 2, "stations_s": [0.0, 1.0]}
        ]
      },
      "cells": {"bounds": [12, 12], "default": 12}
    }
  }
}
```

这是有意省略其余字段的 M1 派生示例，完整原型规则、继承说明和未评价声明见 [离线示例 JSON](p63b2_offline_examples.json)。该文件另存了本轮真实 SDK/Mock HTTP 的 L0 和 Schema 摘录。Mock 通用 fixture 的 cells 域为 [1,32]；M1 冻结域为 [12,12]，两者均从各自源派生，未在生产代码写死 M1。

## 必要离线验证

新增 2 项，复用并补充 2 项现有测试，共 **4 项通过，13.247 秒**：

| 用例 | 验证 |
| --- | --- |
| GenerationInputTests.test_sparse_overrides_inherit_prototypes_without_task_evaluation | M1 两段请求只改长度、省略 sections/cells；原 resolved_request 与原生成器继承相同截面和 cells，合法构建，无任务评价 |
| GenerationInputTests.test_observed_explicit_overrides_still_fail_original_domain | 复用 Sol 两个实际请求输入；截面数量错误仍有原 EXACT_SECTION_STATIONS_REQUIRED；cells 越界被新投影 Schema 拒绝且原生成器仍报 CELLS_OUTSIDE_FAMILY_DOMAIN |
| InformationFlowTests.test_direct_reads_preserve_generate_and_stable_prompt | 真实 Mock HTTP wire 含 direct_plan、冻结默认/站点提示及 cells 上下界；sections/cells 仍可省略；直接读取不卸载 generate，随后可直接生成合法自有候选；Schema 可序列化、无禁止的根级 composition |
| InformationFlowTests.test_new_packet_confirms_exact_reads_and_knowledge_delivery | 已读进度实际进入 Mock 请求，精确交付的确认时序保留；不改 Knowledge |

首次运行中新增的 Knowledge 断言曾错误地要求“首次携带正文的请求发送前已确认交付”；按真实确认时序修正该测试断言后，四项全部通过，未改产品逻辑来迎合测试。无大型回归、真实 Provider、数学/物理 Worker、NMPC 或 RL。离线结构生成和编译不是物理评价或数值求解，也不是正式 Study 科研证据。

## 分别待授权的两项测试

两份草案均通过现有 resolver；**尚未 prepare、创建 Store、bind 或记录正式授权，尚未启动**。沿用 sol/none runtime、原 M1 central_high 任务及阈值、角色 v3、bound v2、information flow、Handoff 和 Knowledge-enabled/success-case-accessible 政策（九项权限在准备时重新冻结，P3 保持中文）。不从 Luna/Sol 继承候选、控制、结果或剩余额度。Provider 型号和实际许可在各自授权准备时按原机制核对。

| 项目 | G：空起点合法生成 | M：Operator 合法起点的数学决策 |
| --- | --- | --- |
| 草案 | [study_p63b2_g_m1_draft.json](../../configs/research/study_p63b2_g_m1_draft.json) | [study_p63b2_m_m1_draft.json](../../configs/research/study_p63b2_m_m1_draft.json) |
| Study ID | p63b2-g-m1-pending | p63b2-m-m1-pending |
| 起点 | 无候选，全部合法结构设计选择归 Main | 原生成器在新 Study 生成一个合法、未经任务评价的当前候选，明确标记 Operator 提供 |
| 建议 Provider 总额 | 8，含失败及 1 个 closeout | 12，含 Reporter、失败及 1 个 closeout |
| 建议 public operations | 16，含 2 个保护操作 | 32，含 2 个保护操作 |
| 数学 / Native | 0，不开放数学执行 | 共享数学 4；callbacks≤24、iterations≤3、knots≤4，原准入/计账不变 |
| 独立物理 / NMPC / RL / NLP / BDF | 全为 0 | 全为 0 |
| 主要观察 | 能否少量读取后自主提交合法生成；能否依据域错误自纠并诚实收尾 | 能否自主选题、选参数/指标/方法、diagnose、实际数学调用，并据结果提出有依据的下一步 |
| 停止 | 得到合法候选后按原规则 STOP，或上限/真实阻断 | 完成一次数学依据的后续判断即可收尾，或上限/真实阻断；不为耗完额度强行计算 |

G 的成功只表示 Agent 原创请求生成了合法结构，不表示该结构完成任务。它关闭数学和控制执行，仍保留完整获准结构域中的设计自主权。重复 route、重复检索、非法显式覆盖和 STOP 查询均照实记录；不自动纠正或替其提交。

M 的 Operator 预备动作仅在单独获准后，通过现有 `design.generate_candidate` 在新 Store 注册；请求建议为 version=serial_family_generation_v2、当期 family_space_identity、segment_count=2、tendon_count=4，其余可继承字段省略。此为工程有效性起点，未经数学/物理任务评价，不按历史成功结构挑选或调参。provenance 明确 origin=operator_provided_unmeasured_baseline，并保存原请求/返回候选引用；不伪造 Main Plan 或把起点归为 Agent 原创。现有 decision_candidate 会显示最新合法构建，候选索引/数学机会查询保持原绑定。若原生成器未产生合法起点，停止准备并报告，不做自动搜索或候选修复。

Main 仍自行决定科学假设、实际参数、任务指标、方法、步长及后续方向，允许在原准入内提出结构修改；不强制长度差分、T1/T2 顺序或三点/五点路线。M 的输入是 Operator 合法候选，输出须区分科学证据、未解决的数值问题和任务接受。Reporter 只沿原来源事实/只读解释流程工作；没有独立评价额度，不能 SELECT 任务成功。

M 的 4 份共享数学规模沿用原三 T1 加一 T2 的规划口径，但不固定配额。原 T2 汇总已计费 T1 的同源结果，不重新求解。每份 24 callbacks、全窗 0.6s、dt=0.001s 时，一次完整 rollout 的积分步基数为 600；三份 T1 的 callback 步基数约 43200，四份 T1 约 57600。还须按原回执另记实际重建/回放、失败尝试、model_builds、rollouts、physics_steps 和 numerical wall time；这些基数不是额外预算或成本硬上限。不得因独立物理预算为 0 而将 Native 积分记为免费。

草案 resolved identity 与准确预算见示例 JSON 的 proposed_tests。分别批准 G 或 M 后才创建其独立 Store，核对零历史起点/Operator 归属，提交绑定当前 B2 代码，并沿原 formal_study_authorization 记录准确模型、Knowledge、identity、计算范围和预算，再运行相应有限窗口。没有第二套授权包装。两项均具备分别申请小规模执行授权的工程准备条件；接口可用性修复已离线验证，Main 是否减少重复读取、正确生成或完成数学决策仍须相应真实实验验证。

交付文件为上述三个生产文件、两个测试文件、两份待批准配置、离线示例 JSON 和本文。不改任务阈值、生成规则、T1/T2 内核、Knowledge、Handoff、Store 或数学请求系统；不添加自动修复、Planner、Memory、Reporter 或来源校验。提交并 push 独立分支后停止。
