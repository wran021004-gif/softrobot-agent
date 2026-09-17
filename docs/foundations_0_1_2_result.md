# 步骤 0、1、2 基础分层结果

基线为 `feat/independent-spatial-dynamics@c04a5f9`，开始时工作区干净且没有适用的 `AGENTS.md`。本轮未切分支、commit、push 或 merge，也未修改数学方程、控制算法、求解算法和任务评价语义。

步骤 0 已把 README 与平台导航指向当前 tendon-family 主链路，并在 `docs/platform.md` 给出推荐／兼容／历史／计划能力、权威来源和真实调用顺序。步骤 1 新增独立 `family.discretization`：推荐 `family.design` 不含 `cells`；旧 `Segment.cells` 和旧候选路径只作兼容输入，冲突会明确拒绝。公共 `preparation.py` 统一候选文件加载、最终范围检查、构建、来源身份、装配和过期检查。步骤 2 的共同场景现在包含实体映射、具名模型状态、安装、目标、外力、SI/坐标系，以及时长、控制周期、采样周期、观测相位和积分步长语义；`family.experiment_spec` 只保存来源身份和职责，不复制可编辑值。

新 prepare 生成 `design.json`、`space.json`、`discretization.json`、候选 request，以及 MATLAB/MuJoCo 各自运行配置。用户可在配置中修改现有支持范围内的目标、固定安装、初态和定时外力。支持范围仍是串联家族、固定安装、具名地面和现有定时外力；移动平台、自由落球、斜坡、复杂接触、其他状态空间转换和新模型未实现。

聚焦验证：`tests.test_tendon_family_candidates` 9 项通过；生成目录由 `examples/export_platform_contracts.py` 从源码重建；continuous 和 structural 均通过公共 build/compile/assembly，分别为 10 和 12 DOF。平台相关组合检查共 35 项，其中 34 项通过；基线已有的 `test_backend_incompatibility_before_any_solve` 期望较晚的 `BACKEND_INCOMPATIBLE`，实际由既有更早检查返回 `BACKEND_ROBOT_REPRESENTATION_UNSUPPORTED`，与本轮代码路径无关。

本轮新运行位于 `runs/foundations_build_check`，使用同一 structural 候选（近段 3 cells、远段 3 cells，总 12 DOF）、同一 0.35 s 任务、初态、控制、目标、安装和外力。实际完整积分正好 2 次，没有失败或重试：MATLAB execution `5c541fcc0c274a929fb3d754328b0570`，误差 0.02114479694 m，任务未通过；MuJoCo execution `cd27ea2df8964ee2a3996029405bdcc1`，误差 0.02115432108 m，任务未通过。两者公共物理和场景身份相同；最终末端差 0.0000901347 m，轨迹末端 RMS 差 0.000110984 m。比较、评价、信号读取和保存回放材料复用这两次结果，没有新增求解。

历史 `runs/tendon_candidate_selection_20260917` 与原文档证据保持不变；本轮结果是新的开发验证记录，不改写历史授权或账本。
