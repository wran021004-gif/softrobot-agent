# BF2 / negative

## 当前任务

让软臂末端在世界坐标系中到达 [0.29, -0.035, 0.19] m，并按原验收要求保持稳定。 外力条件：在 0.1–0.35 s 对 payload 质心施加世界系力 [0.0, -0.02, -0.03] N。 执行时长 0.35 s，原始验收要求：任务误差 ≤ 0.01 m；保持位置误差 ≤ 0.01 m；保持速度 ≤ 0.02 m/s。完整任务配置和原始验收分别见 `task.json`、`acceptance.json`。

## 从空白 Conda base 环境启动（Windows PowerShell）

先打开已初始化 Conda 的 PowerShell，进入 base。首次使用时创建环境并安装经过本机无头验证的版本；已经创建过环境则跳过 `conda create` 和 `pip install`：

```powershell
conda activate base
conda create -n softrobot-replay python=3.11 -y
conda activate softrobot-replay
python -m pip install mujoco==3.13.0 numpy==2.4.6
cd "D:\softrobot-agent\.worktrees\b-line-delivery\runs\b_line_delivery\BF2\negative\bf-hidden-20261026_bf2_H1-0.2_negative_1"
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
