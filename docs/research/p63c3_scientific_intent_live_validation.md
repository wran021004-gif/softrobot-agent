# P6.3-C3 M3 科研意图真实验证

基线 C2 `2581e01a9e17461224bc712f5e4cbe26e04685af`；独立分支
`codex/p6-3c3-scientific-intent-live-validation`。本轮只授权一个小规模 Study。

## 执行前冻结

修复只涉及 scientific_question_v1 的两处旧提示：research_context 的
control_initialization_handoff，以及 agent 按需初始化 Schema 内 ControlSeedRequest.method 的说明。
新说明要求使用新 source、重新提交候选绑定 diagnose，再直接提交 ScientificQuestion；
不要求底层求解器名称，不将初始化称为数学计算。旧 v1/v2 保持原说明及执行行为。
没有修改数学适配器、Worker、任务、预算或 Store 实现。

新增三个节点的实际 Mock wire 测试，并运行旧初始化/diagnose 交接和 C2 原编译执行边界测试：
**3/3 通过，71.126 s**。命令：

```text
python -m unittest tests.research.test_p63c2_scientific_intent.ScientificIntentTests.test_c3_three_handoff_nodes_deliver_question_semantics_without_solver_choice tests.research.test_p63b5_native_entry.NativeEntryTests.test_method_margin_guidance_schema_and_diagnose_initialize_diagnose_wire tests.research.test_p63c2_scientific_intent.ScientificIntentTests.test_mock_wire_diagnose_without_method_loads_question_and_executes_original_request -v
```

Mock 数值不是科学证据；此阶段没有真实 Provider 或科学 Worker。git diff --check 通过。

## M3 原任务与运行配置

原 Trace：memory/cases/m3_research_v1/success_trace.json；原 Store 只读：
`D:/softrobot-agent/.worktrees/base-only-benchmark-feasibility/runs/base-only-owner-20261028-r2/M3/private-store/platform.sqlite`。
原 Study `base-only-m3-20261028-r2`；初始候选
`c5a370c614cf5ef6a2c9e4d5813494f0deac448feb1ae8ccb4210fc01cad06d4` 仅用于读取历史结构来源，
不作为新 Study 的自有候选或科学证据。

使用现有 tasks/reach_hold_b3_050.json，与原冻结 canonical_task、FamilySpace、control 和
analysis_protocol 按值一致。Reach/Hold 时长 0.50 s，最后 0.05 s 保持；位置 0.01 m、速度
0.02 m/s；控制/采样周期 0.01 s，积分步长 0.0005 s；目标 [0.29,-0.035,0.19] m。
原始两段、六腱、每段 12 cells、零命名初态和物理环境保持原样。仍属 development draft，
不升级为正式 Benchmark，不导入历史成功张力或验收。

[新冻结配置](../../configs/research/study_p63c3_m3_scientific_intent_sol.json)：
`p63c3-m3-scientific-intent-sol-20261030`。沿用原 Sol/none Gateway 与 Reporter 策略、
英文架构和按需工具，启用 scientific_question_v1。Provider 总上限 12（含 Reporter/失败/最后
1 次保护），公共操作 32（含 2 次保护），数学 **3**，Native 每次 callbacks≤8、累计≤24；原 iterations≤100、knots≤4。
独立 Replay、NMPC、RL、T2 新实验、NLP/BDF 均为 0。C2 实际数值默认值不改变。

先最多 6 次真实 Provider 请求到 C3-A 监督检查点，只读审查后决定是否在同一冻结额度内继续。
没有预填 ScientificQuestion 或替 Main 选择假设、控制范围、策略或下一实验。

最初准备的数学上限为 1。首次真实请求之前，用户明确选择提高至 3 次，
以保留首个结果后的研究行动空间；在同一 Study 记录授权补充与显式绑定，保留原配置、候选、source、计账和所有事件。
Provider、公共操作和其他科学上限均未增加。原 count 保护仍在全部数学额度用尽后进入收尾；
如它影响 A3，将与模型行动未完成分别记录，强制 STOP 不算自主 STOP。未修改预算或状态路由实现。

真实准备、运行、逐轮事件与 A1/A2/A3 判定将在同一 Study 结束后补充；不自动追加第二个 Study。
