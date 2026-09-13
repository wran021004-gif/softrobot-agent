# 动态观察入口

在仓库根目录使用 `conda activate softagent`。统一入口只读取保存文件：

```powershell
python examples/observe.py runs/20260912T082510_835553Z_9e140aae runs/20260912T082519_263560Z_eb328077
```

左右分别是相同长度0.298 m设计的固定指令和反馈控制。粗线为从保存关节状态重建的真实 MuJoCo 中心线；不是 PCC 几何插值。红星为任务目标。下方显示末端误差、XYZ、腱长目标（虚线）/实际值和有符号执行器力（负号表示拉力）。曲线的垂线跟随播放时间。

点击 Play / pause 播放或暂停；Step 逐帧；0.25x / 1x 切换慢放；Time 拖动时间。鼠标拖动三维区域可调整视角，工具栏可缩放。PNG 和 GIF 按钮导出到 `runs/round4/derived/`，也可指定 GIF 路径：

```powershell
python examples/observe.py runs/round4/validation/oscillator/mujoco_observation.json runs/round4/validation/oscillator/matlab_observation.json
python examples/observe.py runs/round4/historical/mechanics_5.json --export runs/round4/derived/matlab_decay.gif
```

历史成功动态文件的准确列表见 `runs/round4/historical_animation_index.json`。一个 `{input,result}` 力学 JSON 可以直接打开；静态结果或失败结果只显示状态及原因，不补齐动画。缺少的腱长、接触位置、接触力显示为不可用，不能从接触数量推断。

位置在积分后记录；实际腱长和力来自上一次动力学阶段，用原记录的 `solver_time_s` 绘制。旧 debug 记录没有该时间戳时，对应力曲线无可定位时间，不推造时间。中心线重建与末端误差重算会在观察语义中注明；不会推进动力学、改变控制或修改原始结果。GIF 选取已保存帧，稀疏播放没有新增求解，也不是连续时间精度承诺。

跨后端定量误差只有在双方保存了相同输入、初态、参数、自由度映射与时间契约时才可计算。主任务的 PCC 静态形状、单总弯角动态分析与有接触 MuJoCo 运动并不天然具备这种条件。
