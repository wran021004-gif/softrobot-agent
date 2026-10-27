# BF6 / bf6-rigid-sensor-oriented-tracking

## 当前任务

让末端按时依次经过世界坐标点 [[0.298, 0.0, 0.15], [0.29, -0.025, 0.12], [0.29, 0.015, 0.12]] m，对应时间为 [0.0, 0.3, 0.6] s，点间按原任务规则插值。 同时让工具轴跟随方向 [[1.0, 0.0, 0.0], [0.9656541190600237, -0.17381774143080425, -0.19313082381200475], [0.9738617339145248, 0.11686340806974296, -0.19477234678290495]]。 本次执行没有额外时变外力。 执行时长 0.6 s，原始验收要求：详细评价指标及阈值见 acceptance.json。完整任务配置和原始验收分别见 `task.json`、`acceptance.json`。

## 从空白 Conda base 环境启动（Windows PowerShell）

先打开已初始化 Conda 的 PowerShell，进入 base。首次使用时创建环境并安装经过本机无头验证的版本；已经创建过环境则跳过 `conda create` 和 `pip install`：

```powershell
conda activate base
conda create -n softrobot-replay python=3.11 -y
conda activate softrobot-replay
python -m pip install mujoco==3.13.0 numpy==2.4.6
cd "D:\softrobot-agent\.worktrees\b-line-delivery\runs\b_line_delivery\BF6\bf6-rigid-sensor-oriented-tracking\bf6-r8-finite-feasibility-v1_5d4f873304ac4bf4937b6801edd60ff0"
python replay.py
```

以后打开终端只需 `conda activate softrobot-replay`，进入该目录后运行 `python replay.py`。上述绝对路径适用于生成交付包的这台机器；在其他机器上先进入下载后的本见证目录，再执行相同的 `python replay.py`。这台机器已有环境也可直接运行 `& D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe replay.py`。这里使用的 Python 是 Conda 环境内的 Python 3.11，回放本身仅依赖 MuJoCo 和 NumPy，不需要私有 Store。

空格暂停/继续，鼠标调整视角；窗口关闭前保留末态。可选命令：

```powershell
python replay.py --speed 0.5
python replay.py --repeat
python replay.py --show-recorded-path
python replay.py --headless
```

XML 是哈希匹配的原执行模型；控制使用每行对应时间区间的零阶保持。`external_forces.json` 记录世界系外力，按物理步施加在指定刚体质心。蓝点表示原始采样轨迹，绿点表示任务目标或路径顶点。回放使用物理积分，不构成新的独立科研验收；真机限制见 `hardware_notes.md`。
