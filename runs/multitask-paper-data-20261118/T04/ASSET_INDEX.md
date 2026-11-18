# T04 — Figure-Eight Trajectory Tracking

早期GVS路线未完整交付；改为原生静力bank及前馈，完整22 s八字轨迹通过。

RMSE 0.687853 mm；最大 1.020664 mm。

原始独立结果：[default_RESULT.json](D:/softrobot-agent/runs/multitask-paper-data-20261118/T04/RENDER_INPUTS/default_RESULT.json)。候选和决策见本目录CSV。完整逐约束数据见根 `CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv`。

本任务有11张原生截图和1段无字视频；所有截图、视频及状态来源分别见 `render_manifest.csv` 和 `video_manifest.csv`。视觉组件复用先前完成的版本，新增的是原生光照、可见地面和阴影。

- [T04_figure_eight_path_and_error.png](D:/softrobot-agent/runs/multitask-paper-data-20261118/T04/FIGURES_PAPER/T04_figure_eight_path_and_error.png)

视频统一入口：[VIDEO_GALLERY.html](D:/softrobot-agent/runs/multitask-paper-data-20261118/VIDEO_GALLERY.html)。
