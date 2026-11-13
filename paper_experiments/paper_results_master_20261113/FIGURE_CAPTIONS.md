# 图注草稿与展示来源

## 结构截图

所有结构图由MuJoCo Renderer直接生成独立PNG。主体mesh、原导向孔/支杆、真实tendon和负载保留；新增底座、端部锚点板及连接护套为零质量、无碰撞的示意外观。形状未提供制造证据时不宣称为真实硬件。PHS早期候选的已记录穿越/松弛缺陷仍见KEY_RESEARCH_NODES，不因外观完整而宣称任务可行。

- fig_robot_M2_oblique.png：T02，M2，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T02_negative_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_tracking_oblique.png：T04，tracking，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T04_default_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_P3_oblique.png：T08，P3，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_PHS2D_F0_oblique.png：PHS-2D，PHS2D_F0，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_PHS2D_F3_oblique.png：PHS-2D，PHS2D_F3，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T09_guides_oblique.png：T09，T09_guides，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T09_guides_detail.png：T09，T09_guides，guides_detail；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_PHS2D_oblique.png：PHS-2D，PHS2D，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_PHS2D_side.png：PHS-2D，PHS2D，side；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_PHS2D_front.png：PHS-2D，PHS2D，front；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T01_oblique.png：T01，T01，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T01_central_high_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T03_oblique.png：T03，T03，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T03_default_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T05_oblique.png：T05，T05，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T05_default_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T06_oblique.png：T06，T06，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T06_default_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T07_oblique.png：T07，T07，oblique；D:\softrobot-agent\paper_experiments\paper_results_master_20261113\FIGURE_DATA\T07_M1_A_SAMPLES.json#/0/qpos_rad。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。
- fig_robot_T10_oblique.png：T10，T10，oblique；XML qpos0 reference pose。相机、原模型与视觉XML见SCREENSHOT_SOURCES.json。

## 任务动画

由已保存关节姿态及环境状态逐帧更新，在带同款底座、连接、负载和导向件的模型中用MuJoCo原生渲染；无新积分。目标球、参考路径、工具轴和力箭头是依据原任务/记录的视觉提示，不是新增物理结构。T09按钮使用已保存button_slide位移；原始无放大变形。播放时长不等于物理时间，见屏幕时间及ANIMATION_MANIFEST。

## 暂存数据图（未定稿）

- fig_portfolio：Protocol-defined capability coverage of eleven Full Study cases; filled cells identify task requirements rather than independent performance scores.
- fig_research_decisions：Selected PHS-2D decisions link local diagnostics, failed finite-load tests and geometry checks to the frozen design. Local and finite-load quantities have different scopes and do not form a convergence curve.
- fig_tracking_path：World y–z projection of the complete 22 s archived trajectory and 89 stored target nodes. Full 3D evaluator RMSE is 0.68785 mm and maximum error is 1.02066 mm; no interpolated target/error curve is introduced.
- fig_impact_position：Archived 10 ms sampled position signals under one common feedback recipe. Pulse: 0.50–0.55 s; final hold: 0.90–1.00 s. Dotted line denotes the hold bound, applicable to required hold windows. Three required cases pass; both frozen controls fail the complete evaluator. Sampled curves do not replace full-step acceptance.
- fig_impact_speed：Archived 10 ms sampled speed signals under one common feedback recipe. Pulse: 0.50–0.55 s; final hold: 0.90–1.00 s. Dotted line denotes the hold bound, applicable to required hold windows. Three required cases pass; both frozen controls fail the complete evaluator. Sampled curves do not replace full-step acceptance.
- fig_phs_point_x_abs_m：Frozen F8 in ten formal conditions. Force-point displacement (mm) is evaluated per condition; dashed line is the original lower bound. No search-stage values are connected to formal acceptance.
- fig_phs_tip_projected_m：Frozen F8 in ten formal conditions. Projected Tip displacement (mm) is evaluated per condition; dashed line is the original upper bound. No search-stage values are connected to formal acceptance.
- fig_phs_ratio：Frozen F8 in ten formal conditions. Tip / force-point ratio is evaluated per condition; dashed line is the original upper bound. No search-stage values are connected to formal acceptance.
- fig_position_axis_constraints：Position and directed-axis errors divided by their respective original upper bounds. Quantities retain their units and thresholds in the CSV; normalized bars are not a common task score.
- fig_resource_math_evaluations：Resource use of the selected Full task series, including its failed/preparatory studies. Only disjoint run IDs within a series are summed; superseded batch duplicates and PHS half-step verification are excluded. Math charges, physical episode launches and nested integration steps use different definitions and are shown separately. Incomplete step totals are explicitly lower bounds.
- fig_resource_physical_episodes：Resource use of the selected Full task series, including its failed/preparatory studies. Only disjoint run IDs within a series are summed; superseded batch duplicates and PHS half-step verification are excluded. Math charges, physical episode launches and nested integration steps use different definitions and are shown separately. Incomplete step totals are explicitly lower bounds.
- fig_resource_known_integration_steps：Resource use of the selected Full task series, including its failed/preparatory studies. Only disjoint run IDs within a series are summed; superseded batch duplicates and PHS half-step verification are excluded. Math charges, physical episode launches and nested integration steps use different definitions and are shown separately. Incomplete step totals are explicitly lower bounds.
