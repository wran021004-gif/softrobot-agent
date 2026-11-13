# 后续论文绘图计划

当前优先交付原始结果、结构与任务动画；暂不新增或精修数据统计图。FIGURES已有文件均为草稿，不作为出版定稿，不进行多面板拼接。

建议保留六个主图组的组织：1任务能力覆盖；2代表性真实结构；3PHS F0/F3/F8结构演化；4观察—假设—数学—修改—物理反馈；5任务性能；6资源成本。每个结构视角、动画、数据图均独立文件，最终排版在写论文时决定。结构组和演化组可以共用同一独立图片，不重复制造图。

优先取数：逐工况TASK_CASE_RESULTS；结构版本CANDIDATE_EVOLUTION与PHS候选进展；关键过程KEY_RESEARCH_NODES、RESEARCH_PROCESS；完整时间序列SOURCE_DATA/TASK_TIME_SERIES和FIGURE_DATA原始signals；资源RESOURCE_COSTS。各图保留原协议/工况/评价范围，不把不同范围连成收敛曲线。

配色沿用[ColorBrewer BuGn 3](https://colorbrewer2.org/#type=sequential&scheme=BuGn&n=3)：#E5F5F9、#99D8C9、#2CA25F，搭配深灰、浅灰和白色，并用标记/线型区分。最终统计图布局和字体后续统一设计。

结构与任务动画必须继续采用MuJoCo原生渲染。原负载形状和连接来自物理XML，底座及段间外观仅为零质量示意；目标、参考路径和真实受力箭头采用MuJoCo原生场景元素，不后期绘制机器人。相机、轨迹、帧时间及源XML保存在各manifest。
