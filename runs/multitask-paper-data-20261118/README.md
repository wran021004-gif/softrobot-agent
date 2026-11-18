# 多任务科研证据与原生MuJoCo素材库

GitHub入口：[八字轨迹视频](T04/VIDEOS_MJ/T04_default_native_shadows.mp4) · [全部视频清单](VIDEO_INDEX.md) · [任务结果](MULTITASK_SUMMARY.md) · [正文选择](TASK_SELECTION.md)。`VIDEO_GALLERY.html` 下载后可在本地打开；原始证据路径保留归档时的绝对位置。

已整理T01–T10及独立PHS-2D参考：188张原生PNG、25段带地面阴影的无字MP4。

先打开 [视频预览](D:/softrobot-agent/runs/multitask-paper-data-20261118/VIDEO_GALLERY.html) 或 [正文案例选择](D:/softrobot-agent/runs/multitask-paper-data-20261118/TASK_SELECTION.md)。研究数据总览见 [MULTITASK_SUMMARY.md](D:/softrobot-agent/runs/multitask-paper-data-20261118/MULTITASK_SUMMARY.md)；三组排版草稿见 [FIGURE_PLAN.md](D:/softrobot-agent/runs/multitask-paper-data-20261118/FIGURE_PLAN.md)。

每个任务的候选、决策与指标分别在candidate_timeline.csv、agent_decision_timeline.csv、metric_history.csv。evidence_bundle.json保留原Store artifact、run_id、原XML、模型与保存状态。render_manifest.csv和video_manifest.csv逐项链接对应视觉XML、相机和状态来源。全部原生PNG未裁切/修饰，MP4只编码Renderer RGB帧。

视觉组件复用前次paper_results_master_20261113/VISUAL_XML的导向盘、末端锚固板、段间包覆连接件和基座。当前修改是恢复可见地面、原生灯光与阴影、统一任务内相机并读取已有状态。不同几何的中间候选采用原先同一视觉规则，坐标来自它自身模型。组件为既有示意外观，不新增物理硬件。逐XML.check.json记录原物理模型、模板及编译后属性对比。

本次没有结构搜索、数学优化、控制执行、mj_step或新的物理结果；mj_fwdPosition只用于已有状态的空间位置更新。未修改core、原始XML、冻结条件、Figure 1、Phase 2或Overleaf。

注意数据身份：十任务原执行者是Codex expert/surrogate，不是已验证的正式Main SDK/Provider运行。部分数学节点无物理XML或独立验收，明确标unavailable。资源按31个task/run保留，不作跨Study总和；候选artifact数量不等于结构形态数量。

重现命令与环境见RENDER_COMMANDS.md；完整来源与缺项见EVIDENCE_INDEX.md。
