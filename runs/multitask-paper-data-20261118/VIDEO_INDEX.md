# 原生视频清单

25 fps，1600×1200，H.264 MP4，无音轨、无文字叠加。直接渲染历史qpos，不插值姿态，不重新积分；RGB帧仅进行视频编码。短任务慢放，长任务按原时间播放。

| 任务 | 工况 | 角色 | 原时间 | 播放倍率 | 文件 |
| --- | --- | --- | --- | --- | --- |
| T01 | central_high | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T01/VIDEOS_MJ/T01_central_high_native_shadows.mp4) |
| T01 | negative_low | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T01/VIDEOS_MJ/T01_negative_low_native_shadows.mp4) |
| T01 | positive_high | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T01/VIDEOS_MJ/T01_positive_high_native_shadows.mp4) |
| T02 | negative | required | 0.35 s | 0.0875× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T02/VIDEOS_MJ/T02_negative_native_shadows.mp4) |
| T02 | positive | required | 0.35 s | 0.0875× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T02/VIDEOS_MJ/T02_positive_native_shadows.mp4) |
| T02 | zero | required | 0.35 s | 0.0875× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T02/VIDEOS_MJ/T02_zero_native_shadows.mp4) |
| T03 | default | required | 0.5 s | 0.125× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T03/VIDEOS_MJ/T03_default_native_shadows.mp4) |
| T04 | default | required | 22 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T04/VIDEOS_MJ/T04_default_native_shadows.mp4) |
| T05 | default | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T05/VIDEOS_MJ/T05_default_native_shadows.mp4) |
| T06 | default | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T06/VIDEOS_MJ/T06_default_native_shadows.mp4) |
| T07 | M1_A | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T07/VIDEOS_MJ/T07_M1_A_native_shadows.mp4) |
| T07 | M1_B | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T07/VIDEOS_MJ/T07_M1_B_native_shadows.mp4) |
| T07 | M1_C | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T07/VIDEOS_MJ/T07_M1_C_native_shadows.mp4) |
| T07 | M5 | required | 0.6 s | 0.15× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T07/VIDEOS_MJ/T07_M5_native_shadows.mp4) |
| T08 | plus_x | required | 20 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T08/VIDEOS_MJ/T08_plus_x_native_shadows.mp4) |
| T08 | minus_x | required | 20 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T08/VIDEOS_MJ/T08_minus_x_native_shadows.mp4) |
| T09 | default | required | 2 s | 0.333× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T09/VIDEOS_MJ/T09_default_native_shadows.mp4) |
| T10 | positive_y | required | 1 s | 0.25× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/VIDEOS_MJ/T10_positive_y_native_shadows.mp4) |
| T10 | negative_y | required | 1 s | 0.25× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/VIDEOS_MJ/T10_negative_y_native_shadows.mp4) |
| T10 | no_impulse | required | 1 s | 0.25× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/VIDEOS_MJ/T10_no_impulse_native_shadows.mp4) |
| T10 | positive_y_frozen | control | 1 s | 0.25× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/VIDEOS_MJ/T10_positive_y_frozen_native_shadows.mp4) |
| T10 | negative_y_frozen | control | 1 s | 0.25× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/T10/VIDEOS_MJ/T10_negative_y_frozen_native_shadows.mp4) |
| PHS-2D | F8_s7_positive | reference_accepted | 8 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/PHS-2D/VIDEOS_MJ/PHS-2D_F8_s7_positive_native_shadows.mp4) |
| PHS-2D | F8_s7_negative | reference_accepted | 8 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/PHS-2D/VIDEOS_MJ/PHS-2D_F8_s7_negative_native_shadows.mp4) |
| PHS-2D | F3_s7_positive | rejected_research_episode | 8 s | 1× | [MP4](D:/softrobot-agent/runs/multitask-paper-data-20261118/PHS-2D/VIDEOS_MJ/PHS-2D_F3_s7_positive_native_shadows.mp4) |

画面提示：绿点/轴为冻结目标及方向；灰蓝线为原保存参考路径，深色轨迹为已执行Tip；砖红箭头为原任务指定外载或实际按钮接触力。箭头显示长度只用固定视觉比例（T02 0.6 m/N、T10 1.3 m/N、T08 0.25 m/N、PHS-2D 0.45 m/N、T09 0.2 m/N），不是新物理几何。各视频frame_sources.csv保存每帧原状态索引和时间。
