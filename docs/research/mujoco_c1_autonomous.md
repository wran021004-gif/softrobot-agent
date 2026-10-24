# C1：开放 NMPC、MuJoCo-direct 和 PPO 的自主 Study

Study `mujoco-c1-autonomous-20261024`，从用户指定 C0 提交
`12f0464ca8fb78907a081c2520b4f83dcb3758b9` 建立独立 worktree 和分支
`codex/mujoco-c1-autonomous-study`。用户 C1 附件明确授权一次正式研究及持续工程监督、
同 Study 恢复、必要修复、普通 commit/push；不授权改变冻结验收或启动另一项 Study。

## 启动前冻结

配置为 `configs/research/study_mujoco_c1_autonomous.json`，保留原 robot/task/control/runtime。
新 Store、Provider session、证据目的地；history、mathematics、control_seeds、supplied_evidence 全为空。
不提供历史候选、控制、成功序列或科学动作顺序。源结构及注册控制默认是工程先验。
结构仍由原 source-relative propose 生成，不新增拓扑或任务域。

| 资源 | 冻结上限 |
| --- | ---: |
| Provider / 其中保护 | 32 / 6 |
| Public operations / 其中保护 | 120 / 12 |
| 数学评价 | 10 |
| 共享物理启动 | 9 |
| NMPC / 固定张力回放 | 2 / 5 |
| PPO stages / actions / 每 trial actions | 1 / 8192 / 8192 |
| RL 独立评价 | 1 |
| 新增独立确认 | 0 |

所有物理子额度共享 9 次；原 reserve_rl_evaluation 保护已准入 PPO 的独立评价。
未使用独立 local_solves/offline_nlp/bdf_replays，均为 0；MuJoCo-direct 使用数学评价额度。
所有科学 wall-time 限制仍为 null。PPO 原 n_steps=256、默认 allocation=2048、
rollout 对齐及至少两优化批次规则保持。Agent 自行决定有限 allocation 和科学路线。

已阅读 AGENTS、A/B/C0 报告及原实现。现有 measured_nmpc_trajectory 已核对当前 Study、
完整性、科学配置、实际 SI 张力及原执行所有权；不要求任务通过。
只在 control_initialization_methods 增强权威说明，并在 research_plan 工具描述引用它，
补齐 capability_sequence 简短说明。没有新增 Schema 或实现第二套转换。
NMPC、MuJoCo-direct、direct/residual PPO 均可选，原模型适用范围及独立验收边界保留。

预检验证配置解析、依赖导入、凭据存在。尝试的旧 NMPC 合成测试因其 SoRoSim
fixture 缺少 matlab.engine，未进入测试主体；另一个旧环境路径不存在。
这不影响实际冻结的 GVS NMPC，未安装 MATLAB 或修改测试/生产准入。
没有发送预检 Provider 请求或进行科学仿真。host 沿用现有 .s135-env；
worker 使用冻结 .mainline5-env / .rl-pilot-env，单线程环境不变。未安装依赖。

运行过程、最终结果、资源账本及恢复记录将在本 Study 原 Store 基础上补充。
