# 双 Panel 布局建议

- **(a) 配对质量分**：横轴 OFF / ON，纵轴 0–4；P3-A 与 M1-C 各用一条连线连接原盲评均分，标注 3.0→4.0（+1.0）和 2.8→3.6（+0.8）。分数是五项等权平均，不是单独 main_decision_quality 子分。单次观测，不画误差条或显著性星号。
- **(b) 决策差异**：两行对应两个案例。P3-A 展示“完整协议独立回放 → 显式关闭 tendon_1 / tendon_3 的成对被动限制消融”，附原机制阈值 1.25 / 0.8 和 UNKNOWN 缺口。M1-C 展示“120 次再求解请求（冻结上限 100）→ 两次局部诊断”；ON 的优化迭代数标“未请求”，不能画成 0 或 100。原文注释从 reporter_decision_clips.md 选取。
- 各案例旁小字列出既有额外可见上下文代理：P3-A +956、M1-C +1,051。统一标注“本地 o200k_base 估算；Main 实测用量缺失”；额外值不含输出、隐藏推理或历史 Reporter 生成成本。
- 图注范围：六组既有配对中的两个指定正向案例；每对一次独立模型盲评，人工复核待完成。展示拟议科研决策，验证行动未执行，不能替代机器人任务成功率。
- M1-C 只写“ON 避开超限提案”；Reporter 原文强调资格与进展缺口，未直接写出 100 次上限。不要把两个案例拆成多个独立发现。

数据：[比较表](D:/softrobot-agent/paper_experiment_data/architecture_ablation/reporter_on_off/figure_data/reporter_comparison_table.csv) · [完整 JSON](D:/softrobot-agent/paper_experiment_data/architecture_ablation/reporter_on_off/figure_data/reporter_positive_cases.json)
