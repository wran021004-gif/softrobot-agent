# BF5 / bf5-position-tool-axis

任务：BF5 inspection probe positioning and directed tool-axis aiming。目标及世界坐标（SI）：`{"axis_frame": "tip_site_local", "axis_local": [1.0, 0.0, 0.0], "frame": "world", "target_axis_world": [0.9656541190600237, -0.17381774143080425, -0.19313082381200475], "target_m": [0.29, -0.025, 0.12]}`。完整冻结任务见 task.json；原始验收及指标见 acceptance.json。

在此目录运行：`python replay.py`；无界面核对：`python replay.py --headless`；调速：`python replay.py --speed 0.5`；循环：`python replay.py --repeat`；显示原始采样轨迹：`python replay.py --show-recorded-path`。需要安装 MuJoCo 和 NumPy。空格暂停或继续，鼠标调整视角，窗口关闭前保持末态。

XML 是哈希匹配的原执行模型，控制使用每行对应区间的零阶保持。外力为世界系、作用于指定刚体质心，按物理步区间施加。蓝点表示原始采样轨迹，绿点表示任务目标或路径顶点。
