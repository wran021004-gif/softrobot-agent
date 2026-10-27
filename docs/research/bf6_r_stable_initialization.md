# BF6-R：稳定初始化与有限可行性诊断

## 授权、目标和历史边界

2026-10-27 用户明确授权 B-R1 只读诊断、B-R2 一至两个有物理依据的合法稳定控制初始化，以及稳定后 B-R3 的新冻结有限 Native response 搜索。只使用现有研究链路 generate、initialize_control、research_analysis、physical_replay、evidence_read、SELECT/STOP；不增加任务类别或链路外优化器，不导入 BF5 成功控制。

目标仍为 BF6 原任务：相同 P1、20 g 真实刚性负载、地面、0.6 s / 1 ms 积分、原定时扫描与方向参考、全部 30 个评分样本、12 mm 和 10°。本轮新 Study 显式绑定 `offline_oriented_tracking_v2`；原 v1 Native 尝试、后续 v2 失败回放及其身份不重新解释。原 BF6 两个 Study 均已 STOP，452 个已确认积分步与 1 次失败调用内部进度未知、3.150107 s 费用保留；不存在“剩余约 150 回调”的新余额。

## B-R1：只读结论，零新物理计算

读取来源是原 Native analysis artifact、独立失败快照、`robot.xml`、已存 20 ms 样本、MuJoCo warning 及 contact 记录。只做 XML 读取和原数组代数摘要；没有实例化 MuJoCo model、forward、step、rollout、回放或重新调用 evaluator。完整只读摘要与来源位于本地 `runs/bf6-r1/read_only_audit.json`。

| 检查 | 已有证据及边界 |
|---|---|
| 原 Native 首次观察接触 | 每积分步 contact-free 检查在引擎记录时间 0.226 s 退出，最后一步区间约 `[0.225,0.226] s`。2 个 `floor`—`payload_shape` 接触、8 个约束；引擎距离分别 `-0.000262796`、`-0.000348645 m`，即约 0.263、0.349 mm 穿透 |
| 接触世界位置与法向 | 原 contact artifact 仅存 geom 名称和 distance，未存 `contact.pos/frame`。XML 地面是世界 z=-0.020 m 的默认朝向平面，其几何上侧法向为 +z；不能把这条静态几何事实伪装成已保存的实际 engine contact normal。首次接触世界点与实际法向不可恢复，未运行新 forward 重建 |
| 接触前记录的速度 | 0.02–0.22 s 所有保存关节速度绝对值最大不超过 0.465357 rad/s。0.20 / 0.22 s 分别为 0.402508 / 0.350681 rad/s，没有显示提前爆增 |
| 工具运动趋势 | 评分 site 的世界 z 从 0.15 降至 0.20 s 的 -0.003171 m、0.22 s 的 -0.017209 m；末端速度先升至约 1.14535 m/s 后降至 0.87737 m/s。这支持下垂接近地面的观察，不是数值稳定性或精确碰撞时刻证明 |
| 加速度 | 未存逐积分步 `qacc`。仅有相邻 20 ms 关节速度差分代理，最大约 14.7783 rad/s²（第一个区间），之后 ≤6.08360 rad/s²；不能称为实际瞬时加速度，也不能排除最后几毫秒的增长 |
| 失败前快照 | 0.226 s 的 pre-call 最大关节速度约 `6.455244e10 rad/s`，同时已存 2 个接触/8 个约束。失败前 warning 计数全零，随后第 227 次 step 出现 QVEL warning；warning 触发晚于数值已经很大的状态，不能用“此前没 warning”证明此状态可靠 |

0.22 s 到最后一步缺少逐步速度/加速度和实际 contact frame；而 engine contact 对应最后约束评价相位，不可直接与更新后的 qpos 当同相位几何重建。证据不足以区分接触响应触发失稳、数值失稳导致接触或二者耦合。**因果保持未决，不据此修改地面、步长、负载、刚度或碰撞模型。**

XML 物理定义只读核对：payload 质量 0.020 kg，局部质心 `(0.007,0.001,-0.002) m`，完整质心惯量 `[[1.2e-6,2e-7,0],[2e-7,1.6e-6,2e-7],[0,2e-7,1.8e-6]] kg*m²`；与原冻结一致。工具碰撞 box 半尺寸为 `(0.009,0.009,0.008) m`，site 局部 `(0.014,0,0) m`，即在 box 前面 5 mm，不是质心或 box 中心。site 是测量参考点，不是额外碰撞体。地面位于 -20 mm；site 在 0.22 s 高于地面不等于整个旋转后的 box 具有正间隙，且未保存接触时 body 世界位姿，不能据 site 高度补造 box 接触点。

## B-R2：前瞻性小额度稳定初始化

只读 XML 的零铰链安装几何表明，上侧绳路在 +z 偏置处沿近似 -x 方向牵引，提供抗重力的弯矩方向。两个预定候选均从原 0.2 N 合法背景张力增加上侧牵引，同时按绳路横向力臂平衡侧向弯矩；第二个候选把这个偏置幅度加倍。该静态力矩方向只是初始化假设，不是动态稳定性或任务可行性证明。

新的独立 [B-R2 冻结](../../configs/research/bf6_r2_stability_freeze.json)和[配置](../../configs/research/study_bf6_r2_stability.json)声明最多 **2 次完整独立回放、1,200 积分调用尝试**，Native/数学额度为 0。精确两个常量张力起点及顺序保存在本地冻结文件；均由原 initialize_control 绑定，不手改已执行轨迹，不读取 BF5 控制。第一个完整稳定起点即终止初始化尝试；若同时原任务通过，立即 SELECT，不再进入 R3。

稳定起点的操作性判据是原物理回放 completed、600 步/30 个完整 post-step 双信号样本、原 solver/力界/负载/采样组件通过、v2 的无接触组件通过、无缺失或来源问题。**位置/方向阈值可以尚未通过**，其原 evaluator 失败保留；“稳定起点”不是任务通过或稳定性理论证明。两个起点都不满足时立即停止，不扩大扫描或自动换结构。

### R2 实际结果

实现冻结提交 `c29cdcb46621357131f75a00feb0fdb13349d65b`。G1 第一次即获得完整独立稳定起点：600/600 积分、30 个完整 post-step 样本、0 环境接触、0 solver error，真实质量/质心/惯量/site 编译绑定 matched；来源及 outcome 无缺失。G2 未运行。原任务保持 `valid_failure`，最大位置误差 97.558257 mm，最大方向误差 0.649156 rad（37.193883°），末点位置误差 12.114652 mm；没有 SELECT。

该结果解决“此 P1/20 g/地面/冻结模型没有完整合法起点”的实验障碍，说明现阶段没有必要仅因旧冷起点失败就更换结构；它没有证明原扫描任务可行或不可行。完整独立验收绑定和费用见 [R2 receipt](../../evidence/bf6_r2_stability/summary.json)：1 replay、600 步、1 model build、61 forward、Store 全部数值费用 1.6259945 s（其中 replay 1.1502206 s）、driver 4.8035293 s。额度余量全部封存，不转移。

## B-R3：稳定后另行冻结有限搜索

[R3 新冻结](../../configs/research/bf6_r3_feasibility_freeze.json)及[新 Study](../../configs/research/study_bf6_r3_feasibility.json)只导入 R2 自己的 G1 原控制与相同父结构，通过原 initialize_control 重新绑定；物理状态仍全零，不继承验收。一个 research_analysis `mujoco_direct_control_v1` 请求，最多 151 次完整 Native callback、6 次 response 迭代，4 个原时间结点、0.02 N 差分、0.2 N 初始半径、±2 N 控制修正系数。再给最多 1 次完整独立 physical_replay，新增上限 91,200 积分调用尝试。沿用原 0.005 规划安全余量，原 12 mm/10° 硬阈值不动；实际无接触按 v2 每积分步验收。新协议在研究计算前提交。

只回放正常返回的完整 best schedule 一次；若 Native 因探针接触或数值失败中止，则保留全部真实部分成本，不靠链路外算法取回私有“最好解”、不扩额度。首个独立完整通过立即 SELECT，否则 STOP，原任务结论保持未决。原 BF6、R2、R3 三份账本各自封存。

### R3 实际结果及未决原因

实现冻结提交 `bf6b7b7594839a69bfb1f54a52c29f2bbbd5d485`。原 response 优化正常完成 151 个 600 步 Native 回调、6 次 response 步，停止原因为 `iteration_limit`；没有一个 Native 代理候选达到原硬阈值。随后新的独立回放正常完成 600 步，在全部 30 个评分点验收位置和轴方向，并在每个积分步检查环境接触。结果见 [R3 receipt](../../evidence/bf6_r3_feasibility/summary.json)。

| 独立指标 | R2 稳定起点 G1 | R3 最终 best 回放 | 原验收 |
|---|---:|---:|---:|
| 最大位置误差 | 97.558257 mm | 22.748539 mm | ≤12 mm |
| RMS 位置误差 | 60.257967 mm | 18.716163 mm | 仅报告 |
| 末点位置误差 | 12.114652 mm | 22.748539 mm | 同属全点最大误差条件 |
| 最大工具轴角误差 | 37.193883° | 18.834777° | ≤10° |
| 每步环境接触 | 0 / 600 | 0 / 600 | 0 |
| solver error / 张力越界 | 0 / 0 N | 0 / 0 N | 0 / 原合法界 |
| 真实 20 g 负载绑定及完整双信号采样 | 通过 | 通过 | 通过 |
| 原任务结论 | valid_failure | valid_failure | 全部条件同时通过 |

两次独立验收均有 7 个协议组件通过；任务 evaluator、位置和轴方向这 3 个组件失败，未缺失未知组件。R3 样本最大关节速度绝对值 0.569421 rad/s（R2 为 0.797089 rad/s），这是保存采样点的摘要，不声称逐积分步速度上界。数值合法性来自完整回放、原引擎失败检查及有效评价；不是只看这个采样指标。

本轮未决原因已经从“控制起点无法完整运行”变为“有限 response 优化后，原位置和方向任务仍有残差”。不能由 151 个局部回调推断结构不可行、任务不可达或必须换结构；R2 的完整稳定证据已表明旧失败不构成更换 P1 的必要理由。两个新 Study 都已 STOP，selected=null；不继续加回调、不改变时间/目标/容差，也没有开发新任务、接触或写字功能。

## 实际研究工具调用链及独立性

监督入口是公开的 `tests/research/bf6_r2_stability.py` 和 `tests/research/bf6_r3_feasibility.py`，只编排现有 typed dispatch、引用传递、读证据和 STOP，不含私有搜索器。没有 Provider 会话、NMPC 或 RL。下表对应的完整 request/execution/tool/version/cache/charged 收据见 [调用链与累计账本](../../evidence/bf6_r_tool_audit/summary.json)。

| 阶段 | 实际链路 | Store receipts |
|---|---|---:|
| R2 | prepare/bind → generate → initialize_control(G1) → physical_replay → evidence_read → STOP | 5 |
| R3 | prepare/bind → generate(同一 P1) → initialize_control(R2 自身 source/parent) → research_analysis(mujoco_direct_control_v1) → evidence_read → physical_replay → evidence_read → STOP | 6 |

R2 的 request 前缀为 `bf6r2`，R3 为 `bf6r3`。generate、seed、STOP 和外层 replay 的真实 tool_id 为 `research.core_plan@1.0.0`，Native 分析为 `research.candidate_analysis@1.0.0`，子物理执行为 `research.physical_replay@1.0.0`。11 个 receipts 不代表 11 次动态仿真：实际是 1 次分析请求内 151 个 Native 回调和 2 次独立回放。所有这 11 个收据均 completed、cache_hit=false。evidence_read 由 `core.read_evidence` 实际调用；独立结果各留下一个 evaluation_reads 标记，Native 阅读不生成这一类标记。

R3 Native 分析执行 ID 为 `e945570b3ebe4db8aabcf58ab4a79bf8`，独立回放 ID 为 `ed8cad038f434672be6095661c8bbb93`，两者不同。R2 独立回放 ID 为 `4c341908891f4b9a82b0143af9ec416b`。独立回放新建 MuJoCo model、从冻结零状态执行，自己的 world position 和 `site_xmat @ axis_local` 信号进入 Registry `evaluate.oriented_tracking@1.0.0`，再装配 v2 acceptance。R3 注册评价 artifact 为 `5b164f3722d7bbec64eb4af8aae100548e11ad6656b3916a00afb6ed7376ebce`；raw/profile/evaluation/执行 ID 的绑定保存在 receipt 中。任务评价和 profile 在 physical_replay 内完成，没有单独 `simulation.run` / `evaluation.run` / `control.profile_report` 工具调用。

这里的独立性是同一模型下新的物理执行和独立任务评价，不是硬件或不同动力学模型验证。原 BF6 v1 身份、失败结果与历史成本保持原样；本轮明确以前瞻性的 v2 无接触协议执行。最终整理仅阅读已存 receipt 和数组，没有重新评分、forward、积分或搜索。

## 费用与封存

| 阶段 | Native 回调尝试 / 完整 | 独立回放尝试 / 完整 | 已确认积分步 / 调用尝试 | Store 数值 s | 驱动 s |
|---|---:|---:|---:|---:|---:|
| 原 BF6（保留） | 1 / 0 | 1 / 0 | ≥452 / 453 | 3.1501073 | validation 段未记录，合计未知 |
| R1 只读诊断 | 0 / 0 | 0 / 0 | 0 / 0 | 无新科学计算 | 只读整理时间未计为数值费用 |
| R2 新额度 | 0 / 0 | 1 / 1 | 600 / 600 | 1.6259945 | 4.8035293 |
| R3 新额度 | 151 / 151 | 1 / 1 | 91,200 / 91,200 | 11.5574382 | 15.4045685 |
| **本轮 R2+R3** | **151 / 151** | **2 / 2** | **91,800 / 91,800** | **13.1834327** | **20.2080978** |
| **BF6 含原失败累计** | **152 / 151** | **3 / 2** | **≥92,252 / 92,253** | **16.3335400** | **不能补造历史未知时间** |

原失败 mj_step 调用内部进度始终未知，故累计确认步数保留 ≥ 语义。新增科学阶段共 3 次物理 model build（R2 replay 1，R3 Native 1、replay 1），含原 BF6 共 5 次。R3 Native 为 90,600 步，最后独立回放 600 步；R2 的剩余一次 replay、原 BF6 的未使用回调均不转移。

Store 数值时间由 construction、control initialization、charged worker receipts 组成，审计文件保存原数；startup compatibility_preparation 分别另记 0.544336 / 0.534638 s，包含于各 driver。driver 也包含数值时间与编排，不能将这些口径重复相加。Provider 请求为 0；未记录机器的货币成本，不能将秒数称为货币费用。

工程验证另计：最初一次针对性测试收集了 4 个新稳定门槛 fixture 与 6 个已有方向任务 fixture，10 项均通过；其中 1 次编译惯量检查 model build、0 forward、0 积分。随后只修正测试导入以避免将来重复收集，没有重跑整仓或科学任务。监督代码做纯语法检查；fixture evaluator 的合成数据不作为研究证据，测试耗时未计入科学 Store 账本。没有新增物理模型、评价器或优化器实现。
