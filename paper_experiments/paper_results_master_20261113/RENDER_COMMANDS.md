# 原生渲染命令

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/render_full.py
& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/animate_native.py
```

结构截图为2400×1800原生PNG；动画1280×960，原始帧保存于ANIMATIONS_MUJOCO/FRAMES，每项有FRAME_INDEX.json。原XML、独立视觉XML、相机、姿态、编码、时间及选择范围见相应manifest。Pillow只用于GIF容器编码，不用于绘制、合成、裁切或补结构。没有新积分、结构求解或任务验收。

数据图当前不继续生成；FIGURES和plot_master.py仅为暂存草稿。
