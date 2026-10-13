# 强化学习控制 pilot：诊断、训练与独立评价

本分支从 `6fecec4c8a404fa46d46f7c0885186302d1d2b71` 继续。
`env.py` 实现物理任务与失败取证；`train.py` 执行单环境 CPU PPO；
`evaluate.py` 加载保存策略作确定性评价；`diagnose.py` 重放已捕获的张力序列。
本轮结果见 [紧凑汇总](../../evidence/rl_pilot_20261013/result_summary.json)。
完整运行数据在忽略的 `runs/rl_pilot/`，没有修改主线环境、历史 XML、账本或旧失败试验。

## 本轮结果（原验收门槛）

| 最终策略 | 终点误差 mm | 保持最大误差 mm | 保持最大速度 m/s | 六样本 | 结果 |
|---|---:|---:|---:|---|---|
| direct | 2.847921 | 2.847921 | 0.004975700 | 完整 | 通过；两次新重置确认均通过 |
| residual | 1.234211 | 1.629899 | 0.031745556 | 完整 | 未通过速度要求 |

两种最终策略评价均无数值异常、命令/施加张力差均为 0 N，每条轨迹 36 行。
direct 在 210 个张力通道样本中饱和 7 个、环境裁剪 0 个；residual 饱和/裁剪各 1 个，
保持六步没有裁剪。residual 六个保持速度都超过门槛，位置小并不代表已经停稳。
其最后一万训练动作的平均保持速度约 0.05944 m/s，保持速度奖励均值 -1.883、
位置奖励均值 -1.571（均按所有动作平均）；独立评价仍有运动，未把它判为成功。
第二轮预算已用完，没有第三轮或检查点筛选。

| 正式训练费用（不含前置短训练） | direct | residual |
|---|---:|---:|
| 尝试动作 | 400000 | ≥374485 |
| 实际物理步 | 7995279 | ≥7489700 |
| 完整/数值失败回合 | 11090 / 485 | ≥10699 / 已记录 0 |
| PPO 批次 / epochs | 1562 / 15620 | ≥1462 / ≥14620 |
| 训练墙钟秒 | 828.148 | ≥671.461 |

两种第二轮均正常达到 200000 动作上限，分别 314.229、312.843 s，
均完成 781 批/7810 epochs、5714 完整回合、0 数值失败，时间超出量为 0。
direct 首轮的 485 次数值失败均取证并按失败终止，未作为正常物理轨迹接受。
residual 首轮中断不能声称正常完成或已评价，其费用是下界；当前 residual 网络只继承
4096 短训练动作与第二轮 200000 动作，丢失的首轮费用仍计入总账。
前置诊断墙钟 660.871 s，低于 15 分钟；所有有设置记录的本轮训练累计至少
1519.836 s（约 25.33 分钟），包含短训练和失败尝试，不包括诊断重放/代码编辑/评价。
没有外部 API 请求。完整分项及计数口径见 `result_summary.json`。

## 诊断结论与边界

原用户短训练：direct 完成 30 动作、0 次优化；residual 完成 311 动作、
10 遍优化。原来的“动作数 × 20”漏掉失败动作内已尝试的物理步。
旧文件没有完整输入，不能证明精确复现了历史故障。

本轮先以原 PPO 配置、seed 17 捕获 direct：第 1 回合第 31 动作、
第 13 个物理子步之前时间 0.3060 s，出现 BADQACC，引擎时间回到 0.0005 s。
已完成 30 动作，但实际尝试 613 个物理步。保存同一张力序列后，从零态重放、
恢复区间起点、恢复失败子步之前状态，均重现该新捕获故障。
正常边界处命令与 `-actuator_force` 最大差为 0 N。

失败动作含饱和与大幅切换，但小探索幅度仍会失败，所以它们不是已证实的唯一原因。
区间起点已有较大误差；恢复检查发现地板与载荷接触，随后状态迅速增长。
这只是关联证据，未隔离接触、刚性动力学、积分或约束求解的各自贡献。
原输入在 implicitfast 的 0.0005、0.00025、0.000125 s 下都失败；
完整 implicit 的相同三种步长也未解决；一次 RK4/0.0005 s 对照更早失败。
这些是有限的区分性检查，不是收敛证明或全面参数扫描。试验最终保留原
implicitfast/0.0005 s，不采用这些替代配置。

证据包含捕获输入、完整状态、各配置结果和正常边界轨迹：
[诊断摘要](../../evidence/rl_pilot_20261013/diagnosis.json)。
数值告警发生在奖励计算之前；direct 首次失败时尚未优化网络，
因此不能归因于保持惩罚或首次 PPO 更新。

## 修改后的失败语义

修复的是取证、计数和训练对数值失败的处理；没有证明物理数值失稳根因已消除。
训练将数值失败视为**单独的吸收终止事件**，不是成功完成任务或普通物理转移：

- 每个控制区间及每次 `mj_step` 前保存 `mjSTATE_INTEGRATION` 状态；
  包含时间、qpos/qvel、执行器/历史/热启动、控制、外力及插件等积分状态。
- 检测 BADQPOS/BADQVEL/BADQACC、时间倒退或非有限状态，先保存故障证据，
  再恢复该控制区间起点；不使用引擎自动重置后的数据。
- 返回有限的区间起点观测、`terminated=True, truncated=False` 和 -10000 失败惩罚，
  标注 `numerical_failure=True, valid_physical_transition=False`。
  此观测是失败终止的有限表示，不声称是失败区间的真实末态。
- 后续回合从原零态重新开始。失败回合、完整 35 动作回合、尝试动作、
  完成动作与实际物理步分别统计。完整回合不等于任务达标。
- 评价环境使用 `failure_mode="raise"`；评价器捕获数值异常，保存已有轨迹和失败 JSON，
  不给伪造的终点指标。训练期间不能构造有限终止观测时仍会停止并保存检查点。

每次故障保存 `failure_episode_N.json/.npz/.jsonl`：
回合与动作索引、收到的动作、张力与变化量、裁剪/饱和、起点误差/速度、
失败子步和告警、区间起点/子步前状态、该回合完整已尝试动作/张力序列。
失败动作没有正常的步后奖励；CSV 单独记录吸收失败惩罚。

两个模式共同将 PPO 初始 `log_std_init` 从默认 0 改为 -3：
标准差从 1 降为约 0.049787。动作映射、残差尺度 8 N 和物理上限均未缩小。
短训练均完成 4096 动作、15 批优化、150 遍训练：
direct 有 89 次显式失败和 59 个完整回合；residual 无数值失败、117 个完整回合。
短训练最终确定性评价均完整，但均未达到原任务。

## 正式训练与恢复约定

第一轮两种模式均申请 200000 动作/1800 s，seed 17、学习率 3e-4。
direct 正常完成；独立评价最大位置误差 10.0366 mm，保持速度合格，严格判失败。
residual 首轮进程意外消失，没有最终 checkpoint；只可证实 CSV 已落盘的至少
174485 动作、3489700 物理步、681 批优化和 358.618 s。中断机制未确定，
不记为正常完成，原目录保留。预算保守按第一轮全部消耗，没有另开第三轮。

仅再运行一轮：direct 从首轮最终策略续训；residual 从此前 4096 动作的短训练策略恢复，
无法恢复丢失的首轮网络。两者均额外 200000 动作/1800 s，学习率统一降为 1e-4，
其他环境、动作和 PPO 设置不变。direct 的依据是接近阈值后的细化；residual 的依据
是首轮末期较大 KL（约 0.352）与波动，且可恢复策略更早。两者网络经历不同。
恢复会新建环境回到零态，不承诺跨进程随机数序列逐位接续。

每 25 个完整 rollout（6400 动作），在其优化完成后覆盖一个
`recovery/policy.zip` 与配套设置；不做策略筛选或自动重启。
`--resume` 校验环境、种子及除学习率以外的 PPO 设置；`--additional-cost`
加入明确记录的丢失训练费用，本轮只用于残差中断。`cumulative_training` 包括已有费用，
中断部分是落盘下界。CSV 的 `cumulative_control_steps` 是 checkpoint 继承的计数，
不包含丢失网络的费用。`optimization_updates` 指完整 PPO 批次；每批 10 epochs、
40 次 Adam 梯度更新。最终策略独立评价，不根据中途 checkpoint 挑选成绩。

## 固定任务、观测与独立验收

段长 `[0.15758113296570092, 0.11241886703429908]` m，世界目标
`[0.29, 0.035, 0.19]` m。按保存的关节名称恢复零位置/零速度，不预稳定、不扰动，
不改变阻尼、刚度、安装或重力。每动作 0.01 s = 20 × 0.0005 s，
正常回合恰为 35 动作/0.35 s，并以 terminated 而非 truncated 结束。

两个模式的 float32 109 维观测相同：
48 个 XML 顺序的实际关节位置(rad)、48 个实际速度(rad/s)、
世界目标减末端位置/0.01 m、世界末端速度/0.02 m/s、上一段实际张力/8 N、动作索引/35。
关节量不缩放，无观测裁剪、GVS 投影或未来参考状态。
速度使用同步步后运动学的 `mj_jacSite @ qvel`，不用差分。

动作六维 [-1,1]，腱顺序：
`near_t0, near_t1, near_t2, far_t0, far_t1, far_t2`。
direct 为 `u=4*(a+1)`；residual 为 `u=clip(reference[k]+8*a,0,8)` N。
正命令送入保存的 `*_direct_tension`，不再取负；正施加张力是 `-actuator_force`。
direct 的动作/观测不使用离线参考。残差映射与 direct 的斜率、偏置、饱和不同，
结果只比较两条完整控制路线，不能作为离线先验贡献的严格单因素消融。

正常动作的物理奖励分项为：

```text
position      = -(position_error / 0.01)^2
holding_speed = -(tip_speed / 0.02)^2，仅控制索引 30..35
smoothness    = -0.001 * mean(((applied_tension - previous_applied_tension) / 8)^2)
reward        = position + holding_speed + smoothness
```

运动阶段不施加保持速度惩罚，也没有参考跟踪奖励。
独立验收必须同时满足：终点误差 ≤0.01 m、保持最大误差 ≤0.01 m、
保持最大速度 ≤0.02 m/s；整数索引 30..35 对应的六个样本必须完整。
奖励不替代验收。成功只意味着固定零初态与固定目标的名义任务表现。

原离线候选通过数值可行性、独立 BDF 与全节点一致性；节点速度向量差约
0.00182501 m/s（上限 0.002），BDF 保持速度约 0.0178399 m/s。
[既有 MuJoCo 回放](../../docs/fc1012_open_loop_replay.md)的保持误差约 14.1865 mm、
保持速度约 0.1513304 m/s，命令/施加张力差为 0 N。
物理配置未改变，因此复用该参考，不重复历史回放。
离线参考仍只是可能有用的先验，不是已成功的 MuJoCo 控制器。

## 环境、输入与命令

实际工作树：`D:\softrobot-agent.worktrees\rl-control-pilot`。
实际 Python：`D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe`。
用户本轮写出的 `D:\softrobot-agent.rl-pilot-env` 不存在；没有重建环境。
版本沿用 Python 3.11.16、NumPy 2.4.6、MuJoCo 3.13.0、
Gymnasium 1.4.0、SB3 2.9.0、Torch 2.14.1+cpu，没有新增依赖或读取 API 密钥。

原交付的安装命令如下；本轮没有重建或再次安装：

```powershell
& D:\softrobot-agent\.mainline5-env\Scripts\python.exe -m venv D:\softrobot-agent\.rl-pilot-env
# 当时 ensurepip 临时目录权限错误通过专用 TEMP/TMP 目录恢复
New-Item -ItemType Directory -Force D:\softrobot-agent\runs\rl_pilot\install_tmp | Out-Null
$env:TEMP = 'D:\softrobot-agent\runs\rl_pilot\install_tmp'
$env:TMP = $env:TEMP
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m ensurepip --upgrade --default-pip
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
& D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe -m pip install --no-cache-dir 'numpy==2.4.6' 'mujoco==3.13.0' gymnasium stable-baselines3
```

`--source-root` 默认实际存在的
`D:\softrobot-agent\.worktrees\mechanics-control-mainline`。
读取该处 `runs/fc1012/platform.sqlite` 中保存 XML 的 artifact：
`60c5e069f76253e05d9b0aa2cd873abda87abecb84b6d0814c30f4e0052a88de`，
对应执行 `6380ef76518b4c24a6bf459942f72545`；
只读查询失败时使用原有两处归档的对应单一成员。
提交的 `evidence/fc1012_open_loop_20261013/references.npz` 提供 35×6
`saved_tensions_n`，相邻 `execution.json` 提供初态与映射；不读旧 NMPC 命令。

```powershell
Set-Location D:\softrobot-agent.worktrees\rl-control-pilot
$py = 'D:\softrobot-agent\.rl-pilot-env\Scripts\python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'

# 新输出目录；不会覆盖既有失败或训练数据
& $py -m experiments.rl_pilot.train --mode direct --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/new_direct
& $py -m experiments.rl_pilot.train --mode residual --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/new_residual
& $py -m experiments.rl_pilot.evaluate --policy runs/rl_pilot/new_direct/policy.zip
& $py -m experiments.rl_pilot.evaluate --policy runs/rl_pilot/new_residual/policy.zip

# 重新评价本轮最终策略；新目录，不训练
& $py -m experiments.rl_pilot.evaluate --policy evidence/rl_pilot_20261013/round2_direct/policy.zip --output runs/rl_pilot/recheck_direct
& $py -m experiments.rl_pilot.evaluate --policy evidence/rl_pilot_20261013/round2_residual/policy.zip --output runs/rl_pilot/recheck_residual

# 本轮第二轮的可复制命令；新输出目录
& $py -m experiments.rl_pilot.train --mode direct --resume evidence/rl_pilot_20261013/round1_direct/policy.zip --learning-rate 0.0001 --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/reproduce_round2_direct
& $py -m experiments.rl_pilot.train --mode residual --resume evidence/rl_pilot_20261013/short_residual_recovery/policy.zip --additional-cost evidence/rl_pilot_20261013/round1_residual/interruption.json --learning-rate 0.0001 --steps 200000 --seed 17 --max-seconds 1800 --output runs/rl_pilot/reproduce_round2_residual

# 只对已通过策略确认；本轮 direct 两次确认已经保存
& $py -m experiments.rl_pilot.evaluate --policy evidence/rl_pilot_20261013/round2_direct/policy.zip --episodes 2 --output runs/rl_pilot/new_confirmation

# 保存输入的诊断重放（会明确记录数值失败，不训练策略）
& $py -m experiments.rl_pilot.diagnose --capture evidence/rl_pilot_20261013/direct_capture.npz --output runs/rl_pilot/new_replay
Get-Content evidence/rl_pilot_20261013/result_summary.json
```

PPO 仍为一环境、CPU、一 Torch 线程，actor/critic 各两层 64 单元 Tanh，
rollout 256、batch 64、10 epochs、学习率 3e-4、gamma 0.99、GAE 0.95、
clip 0.2、entropy 0、vf_coef 0.5、max_grad_norm 0.5。两种模式共用 seed 17。
正常物理配置标识为 `pilot-v2-implicitfast-dt-0.0005`。
`--physics-dt`/`--integrator` 用于复现诊断对照，本轮正式训练不修改它们。

训练输出 `policy.zip`、`settings.json`、逐动作 `training.csv`、SB3 `progress.csv`；
前者日志含完整动作、张力、奖励分项、失败标志和真实计数。
停止后的不足一批数据不用于优化；总步数不是优化数据量。
时间预算包括采样和网络优化，采用协作式回调，设置文件记录实际超出秒数，
不宣称严格 watchdog 超时。评价从 checkpoint 的设置读取模式与数值配置，
输出 `evaluation/result.json` 与 `trajectory_N.csv`。完整评价有 36 行；
边界行张力属于刚结束区间，初始行无动作。失败则保留真实已有样本，不补齐伪轨迹。

仅做针对性状态恢复、计数/训练日志和评价导出检查，没有运行全仓库测试、
历史优化、NMPC 或 BDF 实验。一次新日志字段与 SB3 保留字段冲突、
一次评价列表/数组类型不匹配均已修复，失败输出保留在前置目录。
合成数值异常检查验证部分轨迹与明确失败结果可导出，未额外推进物理。

接口依据：[MuJoCo 状态枚举](https://mujoco.readthedocs.io/en/stable/APIreference/APItypes.html#mjtstate)、
[MuJoCo 数值积分](https://mujoco.readthedocs.io/en/stable/computation/index.html#numerical-integration)、
[Gymnasium Env](https://gymnasium.farama.org/api/env/)、
[SB3 PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)。
