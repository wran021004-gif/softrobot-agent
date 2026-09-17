# 定向收尾与步骤 5–6 结果

基线：`feat/independent-spatial-dynamics` / `d11e25d`；初始工作区干净，无适用 AGENTS.md。未提交、推送或合并；历史运行与证据未改写。本轮工作停在步骤 6。

## 六项收尾

1. `run` 使用 `prepared.effective` 创建会话，仿真请求不再重复应用模板/修改。选择记录保留原输入、完整请求、来源和修改摘要。三段模板直接配三段离散、新增段具名初态、最终范围和后端检查均有无积分回归。
2. `scene`、选择记录和执行统一使用 `resolve_execution` 的规范化模型身份；`{}` 与显式默认值相同。
3. `DynamicsModel.included/omitted` 严格匹配已实现方程，任意物理开关明确拒绝。
4. build 的 MJCF 使用绑定解析出的真实 MuJoCo 参数；非默认摩擦经实际 XML 编译检查。
5. compare 从 Store 中不可变候选、任务、结果和明确旧模型映射恢复比较依据；旧选择记录缺身份不会 KeyError。依据不足返回 `not_comparable`。旧记录只读验证通过。
6. 复用 `examples/export_platform_contracts.py` 更新生成目录：35 个顶层契约、57 个负载契约、74 个扩展，包含模型、1.1.0 后端和搜索适配。

## 优化与实际结果

`family.optimization_request` 嵌入唯一 `SessionInput`，引用 TaskDefinition 的目标、目标方向/单位和评价器约束；模板先选择，实体参数与 `control/*` 参数再通过同一公共候选构建/预检。数值离散不进入实体优化；通用轨迹优化未实现。

公共 `optimize(root, request)` 复用 Host、Store、`run_search`、现有有界坐标提案和缓存/恢复。原始优化请求封存为证据，每个实际候选具有完整 `CandidateInput`。非法/不支持候选不评分；未完成求解无有效分数；预算停止仍返回最佳有效候选。另一个后端的复核不混入排名。

本次选择 `tube_distal` 完整模板；仅搜索 `components/near/length_m ∈ [0.14,0.20] m`，归一化步长 0.2，算法 `bounded_coordinate_pattern_local_v1`，最多 3 个 MuJoCo 候选（含基线）。任务目标 `[0.29,0.035,0.19] m`，最小化末端 `position_error`，容差维持 0.01 m。实验 0.35 s，积分步长 0.0005 s，控制/采样周期 0.01 s，离散 near=3、far=2。控制维持 `tip_feedback`、增益 5、阻尼 0.015、最大关节更新 0.025 rad；本次没有改变控制参数。联合设计/控制路径另有无积分检查，不声称联合优化获得改善。

| 候选 | near 长度 / m | MuJoCo 末端误差 / m | 任务达标 |
|---|---:|---:|---|
| 基线 `search-0` | 0.160 | 0.01909213871680844 | 否 |
| `search-1` | 0.172 | 0.03037268908508553 | 否 |
| 最佳有效 `search-2` | 0.148 | 0.015735781822628483 | 否 |

相对基线改善 0.003356356894179957 m，仍未达到 10 mm 容差。停止原因 `search_trial_limit`，没有追求收敛或追加候选。模型 `model.serial_bending_cells@1.0.0`、主后端 `backend.family_mujoco@1.1.0`；模型身份 `1eff34702875c584c44cb607f6943d28f4c99b176ea8661cf02ec1358bd0d85f`。

对 `search-2` 的独立 `backend.matlab_spatial@1.1.0` 复核有效，误差 **0.015669924849097322 m**，同样未达标。两后端误差接近不代表模型精度或接触模型已经标定。

- 请求：[optimization.json](../runs/family_steps56/inputs/optimization.json)。
- 完整优化结果：[family-optimization_optimization.json](../runs/family_steps56/family-optimization_optimization.json)，含基线、所有试验、最佳配置/结果引用、评价证据、预算及停止原因。
- 最佳完整配置：[best_configuration.json](../runs/family_steps56/best_configuration.json)；Store `CandidateInput`：`0122c4641fc66b4ae3ee4afafa080a660ea38ea39190a17dc16f77eb538bbb3f`。
- 复核：[crosscheck.json](../runs/family_steps56/crosscheck.json)。

## 保存诊断和原生视频

公共 `diagnostics.saved_trajectory@2.0.0` 对 `search-2` 返回 39 条查询摘要、3 个事件、零缺失项；有效状态时间范围 `[0.01,0.35] s`，求解完成。事件均为保存的 `pre_step_solver` 绳索张力，单位 N：

| 实体 | 时间 / s | 观测张力范围 / N | 判据 |
|---|---|---|---|
| `near_t2` | 0.01–0.34 | 0–0 | T ≤ 0.001 N，持续至少 0.05 s |
| `far_t1` | 0.27–0.34 | 0–0 | 同上 |
| `far_t2` | 0.01–0.34 | 0–0 | 同上 |

阈值复用 `tools.trajectory_diagnosis.RULES`。这些事实不证明绳索松弛、控制裁剪或机械故障。例：`near_motor0` 命令采样差分最大速度为 0.01322458 m/s，保存限值 0.025 m/s，未接近 99% 判据。关节输出具名角度和速度范围；未配置关节限位，不推断越限。

诊断：[diagnose.json](../runs/family_steps56/diagnose.json)。每条关键发现含候选、后端、具名实体、相位/坐标系/单位、时间、数值和结果 EvidenceRef。来源结果：`a4ce655fc9582a9dfaea4572a06b7745ce2f0a0582719d75004eee2a3c4ee4da`。不重新求解或评分。

公共视频调用使用同一来源结果的 ExportBundle、保存 XML 及具名 qpos/qvel，由 `mujoco.Renderer` 原生渲染；`mj_forward` 仅重建状态/几何，没有积分。编码器为现有 MATLAB VideoWriter MPEG-4，解码验证 9 帧、800×600、25 fps、0.36 s；请求区间 0.01–0.35 s，实际取样末帧 0.33 s，末帧显示 1/fps 秒。

- [原生 MP4](../runs/family_steps56/products/observations/videos/431ea13159a4cbb8b495/video.mp4)
- [预览](../runs/family_steps56/products/observations/videos/431ea13159a4cbb8b495/preview.png)
- [视频回执与完整产物引用](../runs/family_steps56/video.json)

视频新增动力学求解 **0**、新增评分 **0**。MATLAB 原生 Figure 路径复用 `tf_view` 保存姿态回放；已检查无需 XML 的源适配、指定帧索引、视角和 Figure 生命周期，未额外渲染 MATLAB 视频。没有未完成的主链路事项；MATLAB 实际视频渲染不在本轮实测范围。

## 检查和预算

23 项不同的定向检查通过：原候选模块 13 项，本轮 8 项，公共搜索/封存恢复 2 项。初次 Windows 沙箱下 Python 临时目录出现访问限制，修正测试导入后在获准的沙箱外执行通过；没有因此启动动力学求解。未跑全仓历史测试。

实际完整动力学求解 **4**（MuJoCo 3、MATLAB 1），额外故障重跑 **0**；独立数学工具调用 **0**，MATLAB 后端内部另执行既有 `tf_static` 静态初始化 **1** 次，搜索有 1 个基线与 2 次 Python 坐标提案。评分 **4**、诊断 **1**、视频渲染调用 **1**（9 帧）、LLM 调用 **0**。不把求解内部的几何/Jacobian计算计作额外完整求解。真实项目 Host 使用 10 次工具调用、4 次求解、约 48.235 s 工具执行计时；各求解/引擎耗时保存在结果 `timings_s`。优化停于试验上限，随后复核耗尽常规 4 次求解配额。

运行数据保存在 git 忽略的 `runs/family_steps56`，这份记录与生成目录可提交；原始 Store/MP4 为本机可用产物。

## 可复制命令

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
$run = 'runs/my_family_steps56'  # 准备时使用新目录；读取本轮产物则设为 runs/family_steps56
python examples/workbench.py platform tendon-family prepare-opt $run
python examples/workbench.py platform tendon-family build-opt $run
python examples/workbench.py platform tendon-family optimize $run
$best = python examples/workbench.py platform tendon-family best $run | ConvertFrom-Json
$best.best.candidate_id
$best.configuration.effective
python examples/workbench.py platform tendon-family crosscheck $run
python examples/workbench.py platform tendon-family diagnose $run
python examples/workbench.py platform tendon-family video $run --t-start-s 0.01 --t-end-s 0.35 --fps 25
```

没有激活 conda 的 PowerShell 可将 `python` 替换为 `& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'`。诊断/视频已经封存的相同请求返回原回执；改变时间或视角会产生新的按需派生调用，但不求解。

主要实现：`extensions/tendon_family/{candidate,preparation,scene,contracts,optimization,comparison,diagnostics,saved}.py`；公共桥接 `extensions/robot_domain/saved.py`；复用搜索驱动 `tools/platform_search.py`、视频执行器 `tools/simulation_video.py`；CLI `examples/platform_family_optimization.py` 与原家族入口；相关契约、manifest、定向测试及文档。

建议提交（尚未执行）：

```powershell
git add README.md docs/platform.md docs/tendon_family.md docs/steps_5_6_result.md docs/platform_generated `
  examples/platform_tendon_family.py examples/platform_family_optimization.py `
  extensions/tendon_family extensions/robot_domain/contracts.py extensions/robot_domain/manifest.py extensions/robot_domain/saved.py `
  schemas/dynamic_workbench.py tools/platform_search.py tools/platform_tasks.py tools/simulation_video.py tests/test_family_steps56.py
git commit -m "feat: connect family optimization diagnostics and native saved video"
```
