# T10 — Impact-Recovery Control

固定结构，GVS/NMPC→原生离散反馈；三工况共同配方通过，冻结输入对照失败。

正式三工况通过；最大最终保持误差 4.131382 mm；两个冻结输入对照失败。

原始独立结果：[positive_y_RESULT.json](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/RENDER_INPUTS/positive_y_RESULT.json)。候选和决策见本目录CSV。完整逐约束数据见根 `CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv`。

本任务有54张原生截图和5段无字视频；所有截图、视频及状态来源分别见 `render_manifest.csv` 和 `video_manifest.csv`。视觉组件复用先前完成的版本，新增的是原生光照、可见地面和阴影。

- [T10_control_route_constraint_comparison.png](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/FIGURES_PAPER/T10_control_route_constraint_comparison.png)
- [T10_impact_active_vs_frozen.png](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/FIGURES_PAPER/T10_impact_active_vs_frozen.png)

视频统一入口：[VIDEO_GALLERY.html](D:/softrobot-agent/runs/multitask-paper-data-20261118/VIDEO_GALLERY.html)。
