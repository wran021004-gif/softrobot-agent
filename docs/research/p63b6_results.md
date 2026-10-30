# P6.3-B6：科研行动交接修复与单次 Native M 验证

基线 `a7bd7d73d9091cf85c1c108c85a239216198ea09`，独立分支
`codex/p6-3b6-decision-action-live`。[B5 原始交付审查、Mock wire 和独立准备记录](p63b6_repair_preparation_audit.json)。
本文件初始提交记录离线修复；单次真实运行结束后另行提交实际结果，不在运行中修改执行代码或冻结配置。

## 三处最小修复

已复核根 AGENTS.md、B5 两份说明和两个审查 JSON，并读取 B5 原 Store 第 3 次方法反馈与第 4 次
实际 Provider wire。B5 前 10 次 direct_plan 均为 generate；控制起点早已存在，但方法反馈的
control_input_guidance 被后续紧凑投影挤掉。B5 第 11 次才完成 diagnose，第 12 次已保护收尾。
没有数学请求或 Worker，断点是研究行动推进，不是求解失败。

- **A 默认入口**：仅调整原 load_selected_tool_schema。当前自有候选有已正式授权、预算允许的
  数学方法且未保护时，默认显示 diagnose；无候选保留 generate，显式 route 保留原选择，已完成
  diagnose 保留适用 research_analysis，保护期仍用原 STOP/SELECT。只加载入口，不生成 Plan、
  绑定科学候选/方法、填写假设或启动计算。
- **B 方法交付**：只在单个数学行动视图的 selected_evidence_facts 中优先保留目的、状态、缺参、
  source 角色/引用、模板查询、科学输入、下一工具、成本和必要限制；导航元数据靠后。
  原 3,000 字节单摘要、6,000 字节紧凑总额度不变，原始完整证据仍可查询。Math handoff 明示
  Main 选中方法、diagnose 状态、加载状态、已绑定字段及剩余科学输入。
- **C 已读与窗口**：从原确认成功的 Provider wire 和反馈重建方法阅读摘要，不再只看最近四条
  工具事件。不写新 Memory/阅读账本/状态机。仅匹配当前候选和至多三个已关注方法；区分行动
  字段交付、部分摘要、未确认以及模板/diagnose/数学请求状态，交付不代表理解或科学证据。
  按实际字段内容身份识别变化，不因整个 Study/counter/hash 变化要求重读。
  T1 时间信息派生自原 window_facts：correction_window_s 是 [start_s,end_s]，本任务为 [0,0.6] s，
  不是 0.18 之类时长标量。Main 自选合法 knots；后段 knots 不缩短 T1 全任务计算窗口。
  修正区间、knots 和 Reach/Hold 评分保持窗口不同；pattern/正裕量原限制保留。

生产修改仅四个预期文件：agent.py、research_context.py、session_handoff.py、task_constraints.py。
没有修改科学 Contract、Native 内核、T1/T2 求解器、任务阈值、FamilySpace、Knowledge manifest、
Reporter 权限、Store、账本、授权或 Handoff 核心恢复流程。

## 四项离线验收

`python -m unittest tests.research.test_p63b6_action_handoff -v`：**4/4 通过，67.871 s**。

1. 无候选 generate；有合法候选默认 diagnose；预算不足不假装 ready；显式 generate/初始化
   route 保留；已完成 diagnose 保留数学工具；保护期保留 stop/select。
2. 第一次成功读 T1 后的**下一次实际 Mock HTTP Provider 请求**含关键行动字段、source、
   [0,0.6] s 与 knot/margin 说明，摘要在原 3,000 字节内；审查 JSON 保留准确交付对象。
3. 超过最近四条事件仍恢复确认交付进度；同方法重复读标记 exact_repeat，不记为科学证据；
   新增未经评价 source 后按 scientific_inputs 实际变化标记，其他计数变化不制造阅读需求。
4. 合成 Main 直接 diagnose 后下一次实际 Provider Schema 加载 research_analysis；合法科学
   变量通过原绑定、Contract、source 和 applicability，到 Store.reserve 前截停。

Mock 仅为脚本夹具，绝非真实 Main 科研结果。NativeModel 构造和 contained Worker 用哨兵禁止；
原 Contract/来源/时间准入没有替换或放宽。没有跑全仓回归。git diff --check 通过。

## 独立准备及本条用户授权

[新配置](../../configs/research/study_p63b6_m_native_sol_prepared.json)，实际 Study 为
`p63b6-m-native-sol-20261030-r1`，resolved identity
`31d12d21a435343d6fd284cc724e9b2c9fda1e2c134325a3cefacf68f4820c73`。
原建议 ID 的首次工程准备漏用了原授权门槛要求的 `PENDING_EXPLICIT_APPROVAL:` 前缀；原检查
断言在任何绑定、授权、Provider 或 Worker 之前发现。该未执行 Store 和失败凭据原样保留，未
重置。修正配置后建立上述新 ID 的独立 Store；这不是追加真实窗口，旧准备没有任何科学执行。
原授权门槛在正式 Store 中已明确拒绝缺失授权，随后才可按本条用户许可登记原授权记录。

实际 Store 在本 worktree 的 `runs/research/p63b6-m-native-sol-20261030-r1`。复用原准备 helper，
通过原生成器创建 Operator 2 段/4 腱结构，再调用原 initialize_control 的 seed_control baseline
实现创建默认控制。没有伪造 Main Plan；结构 provenance 和控制的独立 Operator 来源凭据均保留。
候选 `4876bb29aac367eb4a9e2287d921fa3ee72b40e6657d73fbc9706050db8681e4`，source
`70654252edc6ebb519918f864d0c6212fca778feef5cc73517b2a1fe4a46b126`，均未评价。
0–0.6 s、period=0.02 s、31 时点/30 区间、四通道各 0.2 N，原边界各 [0,8] N；原绑定已通过。
同 B5 的冻结任务、FamilySpace、全零初始状态、协议和九项 success_case 权限；未预读正文，
未导入 B4/B5/M0 控制、数学结果或科研判断。

| 资源 | 本条用户授权的单次上限 |
| --- | --- |
| Provider | gpt-5.6-sol / reasoning=none；12，含失败、Reporter 与最后 1 次保护收尾 |
| 公共操作 | 32，含 2 次保护操作 |
| 共享数学 | 4 |
| Native 每请求 | callbacks≤24、iterations≤3、knots≤4 |
| 独立物理 / NMPC / RL / NLP / BDF | 全 0 |

准备时全部执行计数为 0，numerical_s=0.4964591，control_initialization_s=0.1275775；原工程
开销保留。解释器/线程/依赖检查 ready。代码提交后通过原 bind 冻结；随后使用本条用户有限授权
登记准确 formal_study_authorization 与 live_handoff_admission，原入口只运行一次。
Main 自主选择科学问题、适用 Native 方法、合法参数/对照和结果后方向；不预设 T1/T2 顺序。
数学数值只能来自原 MuJoCo Native 量、实际积分及注册内核，不能以 GVS/SoRoSim/降阶/学习代理
预测替代。Native 构建、rollout、callbacks、积分及时间完整计账，结果始终是仿真参考，不是硬件真值。
