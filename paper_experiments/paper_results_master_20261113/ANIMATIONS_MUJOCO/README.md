# MuJoCo任务动画

以下动画均由已有姿态驱动同一可视化XML，通过MuJoCo原生Renderer录制。机器人、原负载、导向件、底座/护套、原任务物体及任务提示均在MuJoCo场景中渲染；文字使用原生mjr_overlay。GIF编码只保存原始帧，不绘制或拼接机器人；全部原始RGB PNG帧及帧时间索引均保留。

每项目前选择一个代表性required工况展示，不代表已经为全部工况录制视频。全部32条逐工况验收及轨迹入口仍在原结果表中。慢放、抽样及完整覆盖范围见下表与manifest，不能按播放时长读取物理速度。

| 任务 / 工况 | 已保存物理时间/s | 帧数 | 动画 |
|---|---|---|---|
| PHS-2D / s7_positive | 4.0001–8 | 81 | [anim_PHS-2D_s7_positive.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_PHS-2D_s7_positive.gif>) |
| T01 / central_high | 0–0.6 | 31 | [anim_T01_central_high.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T01_central_high.gif>) |
| T02 / negative | 0–0.35 | 36 | [anim_T02_negative.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T02_negative.gif>) |
| T03 / default | 0–0.5 | 51 | [anim_T03_default.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T03_default.gif>) |
| T04 / default | 0–22 | 276 | [anim_T04_default.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T04_default.gif>) |
| T05 / default | 0–0.6 | 31 | [anim_T05_default.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T05_default.gif>) |
| T06 / default | 0–0.6 | 31 | [anim_T06_default.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T06_default.gif>) |
| T07 / M1_A | 0–0.6 | 31 | [anim_T07_M1_A.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T07_M1_A.gif>) |
| T08 / plus_x | 0–20 | 287 | [anim_T08_plus_x.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T08_plus_x.gif>) |
| T09 / default | 0–2 | 183 | [anim_T09_default.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T09_default.gif>) |
| T10 / positive_y | 0.01–1 | 100 | [anim_T10_positive_y.gif](<D:/softrobot-agent/paper_experiments/paper_results_master_20261113/ANIMATIONS_MUJOCO/anim_T10_positive_y.gif>) |

PHS s7_positive源文件是共用无载基线之后的已保存加载分支，动画按实际源时间显示该分支；共用基线及其余工况仍在原执行manifest中。PHS与P3的受力点标记为材料坐标s=.7，不是Tip。箭头长度仅为固定显示尺度；屏幕数字来自原任务载荷定义或原记录，不从箭头长度读力。

T04：原存89个目标节点显示为参考路径；T05/T06：原有向工具轴以原生箭头标记；T09：真实按钮与探头连接保留，button_slide按原始环境状态逐帧更新，展示深度和原接触力；T10：原+Y脉冲只作视觉提示，不向控制器增加信息。

底座、端部锚点板和连接护套是零质量示意外观；负载和星形导向孔/支杆来自原模型。实际几何与质量信息以original_physical_xml为准，视觉提示不参加动力学。

命令：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/animate_native.py
```

仅重录一项可加`--only T09`等参数。动画脚本中没有mj_step，渲染不产生新的物理解。
