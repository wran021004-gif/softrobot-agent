# MuJoCo 控制重优化结构敏感性：冻结实验计划

本轮是用户批准的独立 engineering validation，不创建正式自主 Study 或 SELECT。
基线 `feat/c1-method-readiness-context@e5cb92dd7`，独立分支
`research/mujoco-reoptimized-structure-sensitivity`。原 C1、S142–S148 和主线不改。

## 计算前冻结（Checkpoint A）

- 仅改变远段 distal1 Young 模量：d−/d0/d+ = 4.86/5.40/5.94 MPa。
  原准入范围 4.59–6.21 MPa，无需调整扰动。近段 7.2 MPa、长度 0.16/0.11 m，
  截面、质量材料、阻尼、几何、离散网格和环境沿用封存输入。
- 三结构分别调用原 `resolved_configuration` → `family.generate`，不编辑 XML。
  同通道控制由原 `initialize_schedule` 重新绑定；每结构从自身冻结的具名零初态执行。
- 目标 [0.29,0.035,0.19] m，时长 0.35 s，控制/采样 0.01 s，物理步长 0.0005 s。
  六路顺序 near_t0/1/2、far_t0/1/2，独立理想绝对张力 0–8 N。
- 原终点/保持位置 10 mm，保持速度 0.02 m/s；保持窗口 [0.30,0.35] s 六个含端点样本。
- U0 取 C1 封存 measured schedule `2e155dec`，逐项核对原 observations 的
  `actual_tension_n`，不是未执行预测。execution `7085f71ad12d4b54acc1c2203cdbaf4b`。
  仅读已有 tar 归档，不打开活动 C1 Store；不继承状态、通过结论或优化结果。
- 原 `NativeModel.rollout_sequence` 完整积分固定 U0，各用 700 步，先完成三组固定输入对照。
- 原 `local_control_search.search` response 法，结点 [0,0.12,0.23,0.34] s，24 个系数。
  修正界 1.5 N、初始半径 0.15 N、差分 0.02 N、最小半径 0.0001 N，内部目标裕量 5%。
  每结构最多 30 次回调、一次响应更新，预计 1+24+1=26 次；不补齐闲置回调。
- `stop_when=None`；native 回调沿用 `accepted=False`（独立验收尚未执行）。
  保留非法输入、数值失败、停滞、回调额度等原保护；实际停止原因与次数如实记录。
- 排名按原 `task_measure` 的最大归一化有符号超限 J，其次正超限和；无任意加权分数。
  J=max(终点误差/0.01，保持最大误差/0.01，保持最大速度/0.02)−1。
- 每结构最优合法控制只执行一次原 backend 完整独立回放，复用原注册 evaluator、
  `playback_profile`、`assemble_acceptance`。独立启动不继承优化器状态。
  为此仅从原 recover 局部提取共享评价函数；正式 Store/授权入口不变。
- 若 warm 比较和回放完整且无数值失败、剩余额度至少 63,000 步，再运行三组预张力
  冷启动，各同样最多 30 次回调、一次更新。冷启动单列，不与 warm 混合求差分，
  不再执行独立回放。除此不增加起点、参数扫描或重复实验。

## 资源和判读规则

沿用现有 Python 3.11.16 / MuJoCo 3.13.0 / NumPy 2.4.6 / SciPy 1.17.1。
使用 NativeModel 原 cost 计数；独立 backend 返回真实 physics_steps。
固定输入 2,100 步，warm 最多 63,000，独立回放最多 2,100，cold 最多 63,000：
合计最坏 **130,200 / 160,000 步**，搜索最多 180 回调，结构 3，独立回放 3。
每次调用前检查 700 步剩余额度；运行标记已存在就拒绝自动重跑，失败保留部分结果和成本。
Provider、正式 Study、完整 NMPC、PPO、MATLAB、真实硬件均为 0。

固定输入和 warm 最佳分别用 (J(d+)−J(d−))/1.08 MPa 计算描述性割线。
名称固定为 **Finite-budget MuJoCo reoptimized structural response estimate**，
中文“有限预算 MuJoCo 控制重优化结构响应估计”。不是严格最优能力梯度、包络梯度、
结构可行性下界或设计证书。失败/未决不会转换为有效梯度。

同时报告各硬指标、统一起点和最佳 J、真实回调/物理步、内部求解状态、修正范数、
最大张力、信赖域/输入边界、当前最难约束和实际改善。
5% 内部目标是原求解器的 epigraph 下界：通过后裕量可能被目标截断，
关闭成功即停仍不等于已收敛的性能极值；小差异不据此发布刚度优劣。
独立回放误差只检查同一 MuJoCo 模型重新执行一致性，不界定离散化、跨模型或硬件误差。
不额外做步长细化或初值多次重复；初始化影响只能由单独冷启动组作有限诊断。
若最优值接近、约束切换、求解未收敛或初始化影响更大，结构方向返回 unknown。

精确输入与方法见 `evidence/mujoco_reoptimized_structure/frozen_plan.json`。
原始数组、逐回调输出、初态和完整回放写入 Git 忽略的
`runs/mujoco-reoptimized-structure/`；Git 仅保留简明冻结计划、关键结果与报告。
不创建 SHA manifest、第二套 Store、优化器或候选生成器。

## 实测结果

计算前尚未执行数值搜索；本节将在同一冻结实验完成后填入真实结果。
