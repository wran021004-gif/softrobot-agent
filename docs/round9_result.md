# Round 9 实际结果（2026-09-13）

**reach_free 数值任务已成功，真实 DeepSeek 主导闭环尚未验收。** 最佳 c066 在原 MuJoCo 评价器下的误差是 **0.00010433469129212617 m = 0.104335 mm**。本轮真实 MATLAB 动态运行 69 次、MuJoCo 运行 6 次；DeepSeek API 请求为 **0**。当前进程、Windows 用户与机器环境均没有 `DEEPSEEK_API_KEY`，已向用户说明；没有用 mock 或旧请求充当本轮 LLM 调用。

运行目录：[runs/round9_reach](../runs/round9_reach/index.html)。[最终配置](../runs/round9_reach/final_configuration.json)、[候选表](../runs/round9_reach/candidate_table.json)、[预算](../runs/round9_reach/budget.json)、[跨后端比较](../runs/round9_reach/attempts/017_compare_candidates/result.json)。源码分支 `feat/round9-matlab-dynamics-design-loop`，起点 `fb5b1f8`；没有合并或推送，没有覆盖用户未跟踪文件。

## 基线审计与执行事实

本地 HEAD 与给定审阅基线一致；未发现适用的本地 AGENTS.md。Round 8 实际状态为 STOPPED，累计 28 次模型请求，本轮新增 10/12，候选 1/1、MuJoCo 1/1、MATLAB 3/3。历史 c000/c001/c002 的实际误差分别为 0.17116166894090315、0.12187854248137178、0.11644446300291873 m。旧文档 WAITING_FOR_KEY 不是后来实际运行状态。完整核对及旧预算/来源哈希在 [history/audit.json](../runs/round9_reach/history/audit.json) 和 [lineage.json](../runs/round9_reach/inputs/lineage.json)。

Round 9 c000 对应历史 c002，保留 legacy 物理、设计和 C1 指令，重新运行 MuJoCo 得到完全相同误差；新增观测没有改变结果。V2 的质量/惯性定义与旧 capsule 密度模式不同，另立 c001，不把它叫作同一硬件的重复成绩。

冻结任务始终为目标 `[0.25,0,0.15] m`，容差 0.01 m，原点基座，初始 +x 直臂、qpos/qvel=0，重力 `[0,0,-9.81] m/s²`，floor z=-0.02 m，原碰撞开关与 0.002 s/1000 步原评分。所有实验最大拉力仍为 **20 N**。没有增加运行时长、改变初始姿态、锁定 MuJoCo 出平面自由度或改变评分器。

## 动力学模型与实际搜索

MATLAB 核心为 [tdcr_planar_dynamic.m](../matlab/tdcr_planar_dynamic.m)：八个独立 y 弯曲关节，质心 Jacobian 质量矩阵、转动惯性、重力、离心项、分布转动弹簧和阻尼、自然角、实际折线腱路由及单边长度伺服。世界 x-z 平面中正 y 角向 -z 弯曲。质量与惯性来自同一解析 IR/编译模型；V2 使用等效均匀圆柱质量惯性，接触外形保留胶囊，EI 是独立等效设计参数。

`k_theta=EI/ds`、`c_theta=viscosity/ds`，每关节含一个 ds 控制体，包括根部；自然 y 角为 `-natural_total/8`，不改变初始状态。长度伺服 `T=clip(kp*(path-command),0,Fmax)`，原始 MuJoCo force=-T。servo kp 不是腱材料刚度；显式弹性腱未实现且不可选。完整假设和范围见 [V2 合同](../physics_contracts/equivalent_rod_v2.md)、[授权配置](../configs/experiments/round9_grant.json)。

MATLAB 未模拟出平面运动、自碰撞和摩擦；地面仅采用两端半权重的单边法向罚力及阻尼启用平滑，不能当作 MuJoCo 接触求解器。所有对照明确标记 CONTACT_APPROXIMATION。没有经验参数拟合，也没有用拟合轨迹自证准确。

首个 MATLAB 基线因近水平段的最低接触端切换，ode15s 在 207959 次 RHS 后耗尽 120 s，未产生完整成绩；失败保留在 `candidates/c000/matlab/455e771d1434/` 并计费。修正接触离散后，同一任务基线在 1.883 s、1902 次 RHS 内完成，误差 0.116656 m。该修复是数值模型修复，不是任务或机器人修改。之后采用相同 RelTol=1e-5、AbsTol=1e-7、MaxStep=0.02 s，保存内部时间与 0.002 s 输出采样；搜索无绘图、无 pause/drawnow。

单个 Engine 在每批内复用。MATLAB `tdcr_search_step.m` 执行有界坐标模式搜索的数值提案，Python 持久化边界/对数映射、最佳点、逐试验后端调用及预算结算；不是一次不可观察的黑箱长调用，也不是全局优化器。Optimization Toolbox 实际可用，但本实现不依赖它。

第一批根据历史根部小运动、末端弯曲集中和非最大拉力饱和的证据，选择 bend_z、线密度、根部 EI、自然总角、长度偏置五个变量，40 次实际 rollout。第二批根据 c032 已静止但 x/z 都偏短的真实 MuJoCo 反馈，选择长度、bend_z、EI、偏置，24 次实际 rollout。辅助目标权重全部为零，唯一目标为有效 t=2 s 末端欧氏误差；失败/提前停止不可获胜。两份计划在首批试验前保存，明确标记 **Codex 开发决策，不是 DeepSeek API 决策**。

## 对照结果与归因边界

墙钟记录补充：首次失败的内核用时为 120.009 s，含 Engine 启动/传输为 126.828 s，不能把后者说成严格小于 120 s。收尾已将 Engine 初始化移到 rollout 前、记录独立 setup 时间，并使等待/内核预算服从每次与优化/累计剩余额度；中断后无法测量的活动保留为未结算墙钟预留，不当作暂停时间或免费额度。该护栏与模型响应恢复改动只做静态检查，没有为验证超时再次消耗研究 rollout。相应源码变化使后续新计算缓存身份更新，已有成绩与旧源码身份保留。

| 候选 | 变化与控制 | MATLAB 误差 m | MuJoCo 误差 m | 原任务通过 |
|---|---|---:|---:|---|
| c000 | 历史 c002，legacy C1 | 0.116655815 | 0.116444463 | 否 |
| c001 | V2 等效质量/惯性基线，C1 | 0.112097084 | 0.111486832 | 否 |
| c032 | 首批物理/控制联合优化，C1 | 0.014192521 | 0.014192521 | 否 |
| c065 | 从 c032 仅改长度 0.300→0.315 m | 0.006570929 | 0.006570867 | 是 |
| c057 | 第二批长度/刚度/控制细调，C1 | 0.000247088 | 0.000246923 | 是 |
| c066 | 从 c057 仅将 C1 改为 C2 | 0.000112893 | 0.000104335 | 是 |

c032→c065 支持“在该父候选与控制下，长度字段增加可降低误差”；质量和离散刚度随长度按合同联动，不是仅改变几何而保持全部动力学常数。c057→c066 是严格同设计/物理/驱动规格的控制模式对照，支持 C2 在这个案例改善终点误差。首批多个变量共同变化，尚无足够单变量对照把全部收益归给质量、EI 或偏置之一。没有增加执行器最大拉力。

最佳 c066：L=0.315 m，外形半径 0.02 m，路由半径 0.018 m，4 根腱、8 段；线密度 0.4613086649442297 kg/m，根部 EI=0.04508491629815294 N·m²，末端/根部比=1，黏性系数 0.00375 N·m²·s，自然总角=0。kp=1000 N/m、Fmax=20 N；初始 bend_z=1.76479340397763 rad、bias=-0.0112 L，C2 gain=5 rad²/m²，每 10 步更新，命令变化率上限 0.5 L/s。末端实际 `[0.2500352950,≈0,0.1500981834] m`。

## 具体实体、时间与证据

* 历史 c002 `tendon_1`，solver_time **0–1.998 s**，张力 4.665582–19.325574 N。检测规则为 `T>=19.8 N` 且持续至少 0.05 s；全区间未达到阈值。不能把历史失败归因于最大拉力饱和。[历史诊断](../runs/round9_reach/history/c002_diagnosis.json)。Codex 编写的陈述已通过实体、时间及数值引用检查，见 [verified_diagnoses.json](../runs/round9_reach/verified_diagnoses.json)；origin 明确为 codex_development，不能替代真实 DeepSeek 验收。
* 初始实际路由最低的是 `tendon_3`，z=-0.018 m，来自路由位置而非猜编号。Round 9 c000 在 **1.500–1.998 s**，命令 0.3193255744 m，实际路径 0.3148721522–0.3148791839 m，变化仅约 7.032 µm，张力为 0 N。命令放长不产生推绳力；缺少使绳路变长的外力是一种解释假设，不证明机械卡死。[时间查询](../runs/round9_reach/attempts/018_diagnose_trajectory/result.json)，原始轨迹 `candidates/c000/mujoco/1998bbf318f9/trajectory.json.gz`。
* 成功 c066 `tendon_1` 在 **0–0.104 s** 达到 19.969002–20 N，满足相同持续近最大拉力规则，样本索引 0–52；之后输出下降，2 s 任务仍通过。这与历史候选未触及近最大拉力的事实不同。[诊断](../runs/round9_reach/attempts/019_diagnose_trajectory/result.json)，原始轨迹 `candidates/c066/mujoco/bcd6ffa57302/trajectory.json.gz`。
* c066 `joint_0_y` 在状态时间 **0.002–2.000 s** 的角度范围 -0.151300–0.007017 rad，最终 -0.0392734 rad，最大采样角速度 1.414713 rad/s；自然角 0，刚度 1.145014 N·m/rad，阻尼 0.095238 N·m·s/rad。没有配置关节限位，不报告撞限位。[查询](../runs/round9_reach/attempts/020_diagnose_trajectory/result.json)。

旧接触记录只有 contact_count，不能恢复接触力。新 MuJoCo 记录接触对、局部法向/切向力、位置/间隙，以及 solver 阶段的广义驱动/被动力/约束力；被动力未冒充单独弹簧力。新记录保留 solver 前状态及 step 后状态，力使用 solver_time_s，角度使用 time_s。所有极值与事件是保存采样事实，非连续时间严格极值。

## 模型差异和速度

六个跨后端对照的误差排序一致。旧物理基线最终末端差异约 0.213 mm，V2 基线约 0.618 mm；c057 约 0.000174 mm，C2 有微米量级末端差异。全时段 tip RMSE 仍约为毫米量级，不能把终点相近解释成逐点完全一致。对照按实际物理时间分别插值状态与 solver 力，未混用帧编号。

MATLAB **没有节约本例单次运行时间**：完成候选的单次用时中位数约 1.507 s；MuJoCo 六次中位数约 0.172 s。C2 MATLAB 6.196 s，MuJoCo 0.172 s。MATLAB 提供了独立动态筛选与可解释反馈，但本轮并未证明总体墙钟收益；纯 MuJoCo 搜索可能更快，没有运行额外实验来制造速度对照。初次 120 s 失败计入总账。

C2 分段积分的初版步数统计把 99 个重复控制区间边界也计作步数；从保存的内部网格独立核对，c066 实际成功内部步数为 **9164**，不是原记录的 9263，RHS 次数 13387 不变。修正结果在 [solver_statistics_correction.json](../runs/round9_reach/solver_statistics_correction.json)，源码已按各区间 `numel(sol.x)-1` 累计。没有重跑动力学或改写旧任务成绩。

最佳结果距离 1 cm 阈值很远，终点速度小，独立后端一致且没有临界通过/高频不稳定证据；未额外做多网格、多步长或积分容差扫描。

## 软件链路、预算、测试及尚未完成事项

已实现并通过本地真实数值操作使用：版本化 DesignSpec/RobotIR 物理扩展、独立后端仿真、局部 MATLAB 搜索、任意登记父候选分支、control_hash 身份、分页比较、精确实体/时间诊断、保存坐标播放器、工作记忆、权限/schema/白名单、逐 rollout 账本与内容缓存。旧 evaluate/continue 路线保持兼容限制，V2 通过同一 workbench 的 `dynamics` 子命令进入新 campaign，不混用 Round 8 冻结成绩。

| 资源 | 实际新增 | 授权上限 |
|---|---:|---:|
| DeepSeek API 请求 | 0 | 120 |
| 外层工具 / 决策记录 | 23 / 23 | 240 / 260 |
| 登记候选（相同参数试验可引用缓存） | 67 | 320 |
| MATLAB 动态 | 69：68 完成，1 超时 | 240 |
| MATLAB 搜索数值提案等其他数学调用 | 76 | 600 |
| MuJoCo 动态 | 6 | 24 |
| 已记实验活动墙钟 | 约 412.55 s，暂停开发时间不计 | 14400 s |

缓存复用实测 c066 MATLAB 返回 cache_hit，动态计数不变，见 [cache_verification.json](../runs/round9_reach/cache_verification.json)。逐试验表在 `searches/initial_physical_control.json` 和 `searches/feedback_length_control.json`；每个结果目录保存共享输入、IR、XML、压缩轨迹、结果和诊断，后期数值源码快照在 `sources/`。

软件验收为 `tests.test_round9` 六项：双后端输入映射/自然角、单边伺服符号、控制身份/包络、预算中断保留与幂等键、实体时间/零力端、无仿真回放、旧序列化兼容（部分风险同一测试覆盖）。首跑因 Windows 沙箱的 tempfile 私有目录访问/清理失败，改用工作区 fixture 目录后仅补测同一失败组，6/6 通过；未运行 discover、全仓库 pytest 或历史 full-suite。证据在 `runs/round9_validation/`。之后的模型响应恢复逻辑仅静态检查，未声称真实 API/进程崩溃验收。

数值搜索已因任务达到且必要对照完成而停止，未用满预算。工作台状态保留 **WAITING_FOR_KEY**，流程完成=false、数值完成与 MuJoCo 通过分别显示。**仍缺真实 DeepSeek 读取证据→调用优化→验证→反馈的 API 闭环及该外部模型自己的核对诊断陈述。** 无密钥时不能诚实宣告整个 Round 9 验收完成；代码与数值结果已经可用，不是尚待接入的占位工具包。安全配置密钥后按 [使用说明](round9_usage.md) 从现有状态继续，额度不重置。
