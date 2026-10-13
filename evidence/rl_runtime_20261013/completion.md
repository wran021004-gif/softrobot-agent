# RL runtime migration — 2026-10-13

独立 RL 接口已完成迁移和限定验证。入口为 `python -m tools.rl.run start|status|stop|resume|diagnose|evaluate`；[README](../../tools/rl/README.md) 包含可直接使用的 PowerShell 命令、配置和恢复约定。Strands 集成与真实模型调用尚未进行，亦不在本里程碑范围。

新增 `tools/rl/{__init__.py,run.py,env.py,train.py,checks.py,config.json,README.md}` 和 `tests/test_rl_runtime.py`。删除旧 `experiments/rl_pilot/{env.py,train.py,evaluate.py,diagnose.py,README.md}`，不再并存两套实现。历史策略、证据和报告保持原样。任务初态已按关节名写入冻结配置，direct 不再读取参考文件，验收与奖励缩放分离。三条经验复用现有 curated diagnostic index；没有新建知识系统或自动检索流程。

训练沿用 SB3 2.9.0。停止/恢复时保持原始 2048 动作调度终点，`reset_num_timesteps=False`，调用参数为原终点减去加载计数；恢复验证包含调度终点、进度、学习率、策略及 value-function 裁剪值。优化后才原子发布完整检查点代际。已消耗计算、检查点继承学习和当前 worker 成本分开记录；未刷新预留保守扣费且保留不确定性。动作/累计活跃时间限额优先于预期优化次数，非整批采样计费但不宣称已学习。

唯一短训练 campaign 为 `migration-20261013`，seed 17、单 CPU 环境/单 Torch 线程，共享上限 2048 次动作/120 s。第一 worker 经真实 stop 请求在 1024 次动作完成 4 次 PPO 优化、40 epochs；第二 worker 恢复同一 run，开始新物理回合，训练前逐项比对参数、Adam、计数及调度，最终累计 8 次优化、80 epochs、320 Adam 步。调度进度 1 → 0.5 → 0；两段参数均实际变化。累计活跃时间 8.4440223 s；实际物理步 40441，1997 次成功动作，51 次数值失败动作仍计费。预算耗尽后的再次 resume 被拒绝且无新采样。[机器证据](verification.json) 保留原始状态与恢复检查。

既有 direct 策略仅评估一次：35 动作、700 物理步、36 行、六个 holding 样本，终点误差 2.847921 mm，保持最大速度 0.004975700 m/s，按冻结标准通过。与归档同配置结果进行逐项数值比较；仅允许舍入级误差。[评估证据](existing-policy/result.json)。既有故障只回放一个保存的 pre-failure 状态/一个物理步，重现 BADQACC 与时间 0.3060 → 0.0005 s 回退；根因仍未解决。[回放证据](existing-failure/result.json)。

仅运行聚焦廉价检查，没有增加训练 campaign、重训正式策略、改变 residual 失败事实、运行 NMPC/BDF、重新生成轨迹、读 API 凭据或发起外部模型/API 请求。历史 residual 保持速度约 0.031746 m/s，仍未通过；第一正式轮丢失网络，之后从早期短训练恢复。这里验证的是独立 RL 生命周期与固定名义任务兼容性，不是鲁棒性、泛化或真实机器人效果。

提交与普通推送目标：`origin/feat/rl-control-pilot`。交付后终端核验远端与本地提交 SHA 一致；最终答复给出完整 SHA。
