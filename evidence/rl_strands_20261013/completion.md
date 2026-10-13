本次代码集成与聚焦验证已完成，真实模型验收未全部通过。唯一训练进程在 Torch 导入阶段因 Windows 服务提供程序错误退出，未采样、未优化、未生成 checkpoint；因此独立策略评估未执行，任务性能未测量。

模型通过现有 Strands 公开工具生成候选 `core-ee5f4d577a6250f93398faa996dfc76d2b34e171af00901b26f96c50f9a6dad9`，`d=0.5`，长度 `0.16275 / 0.10725 m`；旧 RL 机器人为 `0.15758113296570092 / 0.11241886703429908 m`。结构参数与编译后的 XML 身份均改变。任务目标、零关节初态、0.35 s 时长、0.01 s 控制周期、0.0005 s 物理步、含端点的 .30–.35 s holding 窗口与 .01 m/.02 m/s 阈值保留。

模型选择 direct，无兼容 residual reference；PPO `n_steps=128, batch_size=64, n_epochs=4, learning_rate=0.0005, gamma=0.99`；holding-speed 奖励权重由 1 改为 2，其他奖励项保持默认。配置已保存，但本次 worker 未到达 PPO 与奖励计算，不宣称这些覆盖项已经通过真实训练验收。

累计消耗：23 次实际 provider 请求、23 次公开工具操作，包含错误与修正；live study 401.100 s。唯一训练 allocation 为 1024 动作/90 s，实际动作与物理步均 0，完成优化/epochs 均 0；启动时间未可靠写回，原账本保守计费 90 s（已知下界 0 s），未退款或重置。评估 episode、评估物理步、诊断回放均 0。另一次带不兼容 `failure` 字段的 evaluate 请求在 schema 层被拒绝，不是第二次评估 episode。

| 五项要求 | 结果 | 证据 |
|---|---|---|
| 真实模型生成新候选并配置 RL | 部分完成；配置选择/保存成功，真实 PPO 参数应用未验证 | [候选](candidate.json)、[有效配置](effective_configuration.json) |
| 启动短训练并完成至少两批优化 | 失败；零动作、无 checkpoint | [状态](run_status.json)、[worker 错误](worker_failure.txt) |
| 查询真实进度和累计成本 | 通过；公开终态查询保留保守计费 | [工具原始记录](tool_trace.json) |
| 独立评估保存策略 | 未完成；无保存策略，性能未测量 | [不可执行评估证据](evaluation_unavailable.json) |
| 明确读证据并作下一步决定 | 部分完成；读的是评估不可执行证据，非策略评估结果 | [读取记录](evidence_reads.json)、[模型决定](model_decision.json) |

模型明确读取失败证据 `0a39ef2d78fadedbfe9b816a50db13d499a6fa94d51070d7e39e40a808c5428e`，选择 `adjust_training` 并通过 STOP 关闭当前 study，建议将来在健康 worker 上重试训练；本次没有执行第二次训练。其完整原话与不准确的早期解释均保留，未由开发者改写。事实校正：设计/数值参考的 0.2 N pretension 元数据不等于 RL 初态施加了 0.2 N 张力；RL 初态仍为任务冻结的零 qpos/qvel。

已修复桥接层枚举 Windows 环境变量时遗漏 `SystemRoot` 的具体缺陷。32 项聚焦检查通过，包括真实生成 XML 的加载、不同维度及无关 scene joint、张力符号/限幅、时间网格、奖励独立验收、重复 receipt/状态幂等、checkpoint 恢复，以及无训练的真实 PPO 构造和无凭据 Torch/asyncio 子进程导入。新增异常评估子进程测试保留未知消耗，不把未知成本伪装为零。没有运行全仓库测试、恢复 campaign、NMPC/BDF/MATLAB 或物理诊断 replay。

桥接实现复用原 Store/receipt、候选验证、XML 生成链和 RL 命令边界。`strands_pilot.py` 未改；`strands_pilot_r3.py` 仅增加 opt-in 的剩余时间预留，避免原固定 600 s 预留阻断 900 s study 后期请求。研究反馈 helper 添加 scoped RL 事实，避免数值实验 confirmation 逻辑误处理 RL。

完整非秘密 provider 请求、原始响应字节与接收 metadata 在 [压缩原始记录](provider_trace.jsonl.gz)，索引见 [provider_index.json](provider_index.json)。[共享账本](ledger.json)、[操作 receipts](calls.json)、[机器摘要](summary.json) 保留所有消耗。大 XML 和运行目录留在既有 `runs/` 存储；有效配置证据给出 SHA 与 runtime 路径。

剩余限制：五项接口验收未全部通过；短训练、保存 checkpoint、独立评估与真实 PPO/奖励覆盖应用仍缺实证。仅支持选定 hinge、ideal-tension、reach-and-hold；外部 XML assets 明确拒绝。原运行时协作式 active-time 超限记录机制仍保留。没有机器人不可行性、鲁棒性、泛化、数值根因已解决或完整自主研究结论。交付分支为 `feat/rl-control-pilot`，完整推送 SHA 由最终答复和 Git remote 校验给出。
