# B3 T1/T2 数学控制能力与结构指导验证

2026-10-26，Asia/Shanghai。独立研究分支 `research/b3-t1t2-control-predictivity`，
基于 `78ca687fd893bfc805cfcaf1370ea62dd14dbf65`，独立工作树
`D:/softrobot-agent/.worktrees/b3-t1t2-control-predictivity`。

## 求解前冻结

本轮是独立数学—仿真工程验证，不运行 Provider 或自主研究 Agent，不创建正式 Study。
授权为用户本轮附件 `289c8522-a9e4-4f10-8f5a-6a787dde8051/已粘贴的文本.txt`。
冻结计划为 [frozen_plan.json](../../evidence/b3_t1_t2_control_predictivity/frozen_plan.json)，
在任何新模型构建、CONIC、控制搜索和物理积分之前提交。

B3 原任务目标 `[0.29,-0.035,0.19] m`，完整 0.50 s，控制/采样 0.01 s，
物理步长 0.0005 s，保持 `[0.45,0.50] s` 六个含端点样本，位置 10 mm、速度 0.020 m/s。
两段四腱的唯一变化为远段 Young 模量 4.86/5.40/5.94 MPa。
近段 10.45 MPa，长度 0.16/0.11 m，每段 12 cells，其余几何、材料、布线、阻尼、
控制配方与各自具名零初态不变。0–8 N 理想绝对张力，通道 `tendon_0/1/2/3`。

共同 U0 为 M2 C `30994c15…`，已通过原 `archived()` 校验且逐项等于原独立回放实际张力。
各候选通过原 FamilySpace 合法生成并以 `initialize_schedule` 绑定，未继承验收。
先做三份原 backend 固定输入回放，再做每结构各自的原 native 搜索及一次独立完整回放。
原控制搜索四 knots `[0,.38,.45,.50] s`，固定活动系数 `[9,10,13,14]`，
规则沿用 M2 C 已保存系数选择，不按本轮结果选取；差分 .01 N、信赖半径 .1 N、
系数界 2 N、最小半径 .0001 N、内部目标余量 5%，最多 12 回调/2 更新。
原 native 目标达到即停规则保留；相同额度不代表各结构控制最优。

数学先做三份原 `analysis.calculate(linearization)`，复用其归一化控制权指标；
原 T2 单尺度 h=540,000 Pa 的三次内部 CONIC 同时提供 T1，无重复独立 T1。
不做 h/2、不改变工作点、不追加参数或扫描；平坦也继续有限 MuJoCo 对照。
模型/任务准入失败时保留失败，不绕过原检查形成数学推断。

计算上限：数学计费等价口径 22，结构 3，物理步 50,000，Provider/PPO/MATLAB/正式 Study 0。
最坏 3×(12+1+1)×1,000=42,000 物理步，内部 native 积分全部计入。
本最小实验不分配可选 NMPC；没有实际反馈执行即不形成闭环验证标签。
T1 用原支撑/重放分辨率；T2 保留原方向状态；MuJoCo 给出原评价器全部指标及 J。
缺少优化误差界时不把有限搜索差异升级为结构最优排序，不构造统计置信区间。

## 开始审计

已读取目标 `AGENTS.md`、S130、B3 readiness、M1、M2、S143–S145。
S140 `2913fbb11`、S141 `f2223c24b` 与旧六腱重优化 `515500267` 仅只读查看，未合并。
原数学内核、任务适配、`compare_acceptance`、ResultCard 与敏感性视图已覆盖核心功能。
只需在现有 capability.py 加纯派生比较函数；不需要新闭环数学核或第二套评价器/Store。

连接的 GitHub 确认仓库为用户指定的 public 仓库，有 push 权限。
远端 R0 HEAD 精确为指定提交；R1 HEAD `7922de156`。
主工作树 `feat/gvs-dynamics@d629a80d` 的既有未跟踪环境/runs 文件原样保留。
R1 工作树唯一既有未跟踪 `evidence/b3_r1_history_assisted_050/first_feedback_wire.json` 未触碰。
R1 原 Store 使用 SQLite `mode=ro&immutable=1`、`query_only=ON` 检查，
开始时 ready、pending=null、数学计数 0，具体文件属性、现有结果数量和记录数保存在冻结计划。
不恢复、不 prepare、不运行 R1；M2 B/C Store 与封存归档始终不写。

原始配置、模型、完整控制、优化回调、保存轨迹与计算检查点保留在忽略的
`runs/b3-t1t2-control-predictivity/`；Git 仅交付实验入口、冻结计划、派生摘要、定向测试及本报告。

## 结果

冻结后填入实测结果；本提交尚未开始科学计算。
