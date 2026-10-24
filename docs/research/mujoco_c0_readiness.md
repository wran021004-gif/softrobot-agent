# C0：科研闭环接口收尾与冷启动就绪检查

**固定张力的正式 SELECT、同路线确认、确认统计和中断恢复已接通；新结构可直接从冻结初始化获得 MuJoCo 数学/控制优化起点。**
没有启动 Provider、自主 Study、PPO、NMPC 或阶段 A/B 数值搜索，也没有新增完整物理仿真。
确认闭环用合成 worker 验证；C0 没有执行新的真实确认或建立新的任务通过结论。

从已推送基线 `codex/mujoco-direct-control-stage-b@60c304396b0e56f6e02df7017329e32340fc62f4`
建立独立工作树 `.worktrees/mujoco-c0-study-readiness`、分支 `codex/mujoco-c0-study-readiness`，
并用远端 ls-remote 核验基线。已读取 AGENTS 和阶段 B 实现、报告及相关证据。
原主工作树、阶段 A/B 分支及封存结果均未修改。

## 固定张力 SELECT 与确认

审查发现五个实际断点，均在原函数内修复：

1. core 的 confirm 只有 RL 与 NMPC 分支；fixed_tension 现在按选中结果的路线调用原 physical_replay。
   execution 的 NMPC 入口也明确拒绝固定张力确认，避免混用相同字段后误运行另一控制器。
2. confirmation_progress 漏掉 physical_replays；现在纳入原同解、同 Study、同执行身份的去重统计。
   失败、不完整和历史确认仍保留，不能因更换操作名或来源标签清零。
3. 成功后的保护动作未包含待完成 confirm；只有已 SELECT、仍有冻结确认额度且没有失败/不完整确认时才放行。
4. 固定张力原误用 NMPC 次数预算；现在复用 capacity，按固定张力启动上限、共享 backend 余量、
   原 RL 评价保留及当前/后续 public Plan 成本准入。开发回放为已冻结确认数保留启动容量，
   不要求 NMPC 额度；确认不能扩大共享总额。
5. config 原本一律拒绝非零确认。现在原 fresh_independent_repetitions 字段允许显式冻结的非负整数，
   并要求开发执行加确认能够容纳于物理总额。默认值仍为 0，没有新授权字段或预算系统。

固定张力结果的 controller 视图也指向实际 schedule source，不再展示未执行的 NMPC 控制器参数；原 SELECT 字段说明已同步包含 fixed-tension 结果。

完整路线为：

`完整独立通过 → evidence_read → SELECT → 冻结 selected_solution → 原 source 完整重放确认 → 原独立评价 → 原确认统计/封存`

确认必须引用此前正式 SELECT 的结果，以及完全相同的候选和控制 source。
只有通过现有 eligibility、冻结重复额度和路线预算后，才向原 experiment_preflight 传 repeat=true。
普通 physical_replay 继续执行重复实验准入，更换 operation key 不获得重复授权。
零额外确认的 SELECT 仍直接封存；正额度按每次独立启动保存 role、selected_execution、operation_key，
不会把原成功回放计作新增确认，也不会重用开发结果充当确认。

新回放结果保留原 scientific_configuration、profile_identity，并直接记录绑定 schedule 的
model_identity / design_identity，使带 fidelity_policy 的正式评价可以使用原完整配置核验。
核心恢复流程依据原 worker receipt 的准确输出引用封存父 confirm，不按候选/source 猜测结果，
不重放已结束 worker，也不会因存在多个同控制确认而混淆。

合成验证包括 NMPC 额度为 0 的固定张力成功、零确认 SELECT、正确认、父流程在 worker 已结算后中断、
恢复封存、同 key receipt 复用、失败/不完整确认、换 source 标签和不同 key 的拒绝。
它验证接口生命周期，不是机器人任务能力或真实重复性证据。

## 不依赖历史成功控制的冷启动

复用原 AnalysisRequest 已有的 operating_point；下例只列模型/状态字段，candidate、operation、冻结 protocol 等仍按原请求提供：

```json
{
  "model_source": "mujoco",
  "operating_point": "standardized_initial_pretension"
}
```

该选择不提供 saved_state、execution 或 update_id。原 native_point 从当前候选和冻结 TaskDefinition
读取具名 qpos/qvel、安装/环境/时间信息及候选预张力，以原 native_replay 的**空前缀**进入 worker。
原 NativeModel.reconstruct 在真实引擎内建立完整初始状态、执行一次 forward，不进行积分。
这表示冻结初始化时刻的状态，不是目标平衡，也不是已经到达保持区域。
saved_state 与 execution + update_id 的原接口继续保留；不能混合两种状态来源。

冷启动链路现在可以直接使用：

1. 在冻结设计域内 propose / generate 新合法结构。
2. 原 initialize_control baseline 构造候选绑定完整预张力时间表；不传历史 source/parent。
3. native_dynamics_v1、short_input_response_v1 等从上述冻结初始化开展适用范围内的分析。
4. mujoco_direct_control_v1 使用该合法时间表和同一初始状态，从 t=0 优化至冻结任务终点。
   correction_window_s 和 knots_s 必须显式覆盖该窗口及所有验收样本；不必先跑完整评价获取 t=0 状态。
5. 最佳完整 schedule 交给原 physical_replay，之后独立评价、读证据、SELECT 和按冻结额度确认。

测试实际新生成一个近段 Young 模量增加 0.5% 的合法结构，仅用本候选预张力初始化；
没有 S142/SB 控制或已完成轨迹。原生数学从 t=0 真实计算成功，仍为 diagnostic、task_acceptance=unmeasured。
完整窗口 MuJoCo-direct 请求通过适用性及绑定检查，但**没有启动求解**。
因此已验证独立起点可用，尚未验证新冷启动任务能否被有限优化预算解出。

## 证据身份、层级与科研语义

新数学绑定直接保存已编译物理模型或已绑定 schedule 提供的设计身份。
新回放记录原 schedule 的模型/设计身份。对于旧 SB artifact，ResultCard 只在原控制引用能够
直接提供身份时补齐确定性投影，原始字节不改写；没有重建、猜测或新增 SHA/digest。
数学模型的配置身份与物理执行模型声明保持各自原义，不能因同用 MuJoCo 就称为跨模型验证。

封存的 SB 数学结果、两条控制与完整评价之间的 ResultCard / Evidence Relations 已核对：
设计身份与对应 schedule 一致，模型身份不再缺失，原同结构控制关系可比；原 scalar pointer 和
原始六个保持样本 range 仍可读取。未知身份且没有可信来源的情况继续保持未知。
数学预测、局部优化、完整独立评价、正式 SELECT 仍是不同状态；数学结果没有进入可 SELECT 的执行列表。

MuJoCo 原生力学、短时响应、固定输入结构敏感性保持独立，不要求先运行新优化器。
MuJoCo-direct v1 明确标记为 **Reach/Hold only**，实际仍检查原三组 norm 约束和所有验收样本；
不能外推为任意 Tracking/接触/外力任务。GVS/SoRoSim 的模型选择、数学语义和数值实现未替换，
旧请求身份/序列化回归通过；本次没有重跑其数值搜索。

L0 直接对原 SB 封存 Store 做前后投影比较：

| 内容 | C0 前 / bytes | C0 后 / bytes |
| --- | ---: | ---: |
| 数学方法目录 | 18,192 | 16,149 |
| Reporter 摘要 | 10,182 | 10,182 |
| 完整默认 L0 | 49,708 | 47,665 |

只把重复的通用方法成本说明移至目录共同字段，并去重重复缺失原因；同时更正 native 冷启动前提。
总量减少 2,043 bytes，约 4.1%。方法、约束覆盖、科研结论、查询入口及已有 Reporter 内容保留。
L0 仍包含原目录、任务、动作、意图与近期报告，未宣称已压缩至几 KB；没有注入完整控制、轨迹状态、Jacobian 或试探数组。
没有发现需要在 C0 进一步改动的重复原始数组注入，保留按需 L1–L3 读取和原会话接续。

F0–F2、主 Agent 决策、原有子 Agent / Reporter 解释、ResultCard、正式读证据义务及会话恢复均保留。
Reporter 和 research_context 没有修改，agent 只更新一处工具说明；没有新 LLM 汇总步骤。
原 SB Store 仍为 stopped、selected=null、pending=null；未将历史工程通过事后改成正式 SELECT。
本次读取前后其大小/mtime、状态和 events/artifacts/calls **39/31/6** 一致。

## 修改、验证与成本

14 个生产文件合计 **增加 109 行、删除 44 行、净增 65 行**，无新生产模块或执行脚本：

| 位置 | 职责 |
| --- | --- |
| core.py、feedback.py | 确认按路线分派、SELECT 前提、原统计与准确 receipt 恢复 |
| physical_replay.py、execution.py | 固定控制确认、原来源/配置身份、拒绝错误 NMPC 确认路线 |
| budget.py、config.py | 原共享额度和保护动作；显式冻结非零重复数的有限校验 |
| contracts.py、numerics.py | 原 operating_point 的冻结 native 初态来源，不另造初始化 Schema |
| mujoco_analysis.py、native_analysis.py | 空前缀零步进状态、编译模型设计身份及原适用性 |
| analysis.py、evidence_views.py | 原 schedule 设计绑定、旧证据可信来源的只读身份投影 |
| task_constraints.py、agent.py | 方法目录、Reach/Hold 范围、原工具说明和少量目录去重 |

只扩展原 test_mainline.py 的合成测试；测试文件净增约 172 行，复用原 Store fixture、原 evaluator、
现有初始化和回放函数。没有第二套 Agent、Store、预算、Reporter、优化器或 manifest。

**7 项不同的定向测试通过**：

- 5 项 C0：固定张力 SELECT/确认/恢复；重复准入及失败保留；无历史冷启动；冻结确认额度；封存证据投影及 range 读取。
- 2 项原回归：零确认正式 SELECT 的读证据门禁/封存；旧 native/legacy 请求身份。

未运行全仓库或阶段 A/B 搜索。初次合成 fixture 缺少 runs 父目录和模拟后端资源声明，
被正常拒绝；修复 fixture 自身，未放松生产授权或资源门禁。
变更确认路由/计费和最终身份字段后，仅重跑对应检查，保留实际重复检查成本。

真实数值只执行两次原生初态零步进检查：共 **2 次模型构建、6 次显式 forward、2 次 mechanics 读出、
0 rollout、0 物理积分步**，内核 wall 合计 **0.0561492 s**。
第二次用于最终身份字段及诊断语义验证；没有把它隐藏为零计算。
其余生命周期 worker 是标记为 synthetic_fixture 的合成响应，不是完整物理仿真或新科学证据。
Provider、真实完整物理执行、优化搜索均为 **0**；git diff --check 通过。

审计摘要和原结果引用在 [evidence/mujoco_c0_readiness/summary.json](../../evidence/mujoco_c0_readiness/summary.json)。
没有新正式研究 Store，也没有新增科学结果的预算消耗或覆盖旧封存 artifact。

## 下一次自主 Study 的冻结建议

以下是建议，**不是启动或新增授权**：

| 冻结项 | 建议 |
| --- | --- |
| 任务/设计 | 原 Reach/Hold 阈值和采样；明确合法结构域、初态、理想张力和最终离散规格 |
| 能力 | analysis、control_correction、physical_replay；结构按现有 propose/generate 机制授权 |
| actions | propose 或 generate、initialize_control、physical_replay、select、stop；若冻结正确认数，再包含 confirm |
| 模型/状态 | 显式 model_source=mujoco；cold start 使用 standardized_initial_pretension，无历史控制 source/parent |
| Provider | 总量 24，收尾保留 4；只有另行明确授权后才启用 |
| public operations | 总量 80，收尾保留 8；保留包含在总额内 |
| 计算 | 数学 8，完整物理 6；NMPC/PPO/RL 评价均为 0，除非另行授权 |
| 单次数学搜索 | 六腱优先最多三结点/18 系数；最多 60 回调、3 迭代、内部 5% 裕量，实际张力仍守原边界 |
| 额外确认 | 首次冷启动建议 0；若明确冻结 N>0，物理总额和回放上限须包含开发加 N 次，原共享准入保留这些启动 |

从 t=0 优化时，窗口需覆盖完整实际时域及全部保持样本；不能只给尾段窗口却使用零初态。
每个新结构重新生成自己的合法控制/初态或真实前缀，在相同优化预算下比较。
数学额度按原批次准入，内部 rollout/积分/迭代成本另记，不可把一次批次等同一次引擎求值。

停止条件：首次完整原任务通过后立即停止探索，读原评价并 SELECT；正确认只执行冻结同源重复。
导数退化、信赖域停滞、数值失败或本次批次用尽，应交回未决结论；不无限加迭代或改 key 重试。
Study 额度用尽则按原 all_fresh_results 读证据/引用并 STOP；确认失败/不完整不能自动清零重来。

**接口已具备下一次冷启动自主结构—控制 Study 的条件；科学收敛和任务成功仍未由 C0 验证。**
常量预张力是否是有效优化起点、有限时间参数化能否从零态到达目标、结构间公平的重优化收益，
应由下一项已授权 Study 回答。C0 不自动启动它，也不扩展完整 MuJoCo-NMPC。
