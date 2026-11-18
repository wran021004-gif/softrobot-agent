# 证据入口

| 对象 | 入口 | 说明 |
| --- | --- | --- |
| 最终模型/状态 | FINAL_CASES.json | 22条十任务场景（含2个控制对照）及3条PHS参考 |
| 逐约束原值 | CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv | 原Store验收分量与精确pointer |
| 全部候选相关记录 | SUPPLEMENTARY/complete_candidate_index.csv | 142条；11条为执行记账记录，不计结构候选 |
| 完整原决策 | SUPPLEMENTARY/complete_decision_index.csv | 434条，保留run与原行 |
| 精选研究链 | CROSS_TASK/research_decision_summary.csv | 72条，不罗列全部调用 |
| 来源 | SUPPLEMENTARY/source_index.csv | 916条来源引用；原始文件/Store定位 |
| 已读扩展 | SUPPLEMENTARY/extension_index.csv | 19条指定前驱/反例/数值复核，不声称全仓库覆盖 |
| 截图 | SCREENSHOT_MANIFEST.json | 每图原XML、视觉模板、qpos状态/参考姿态、相机 |
| 视频 | VIDEO_MANIFEST.json | 原状态索引、逐帧来源、播放倍率与ffprobe |
| 分Study成本 | RESOURCE_USAGE.json | 31条，数学与物理管线口径分开 |

关键缺项：T07 S0/S2/S3/S4无原始物理XML，不制作伪造演化；十任务Codex宿主Tokens不可得；T04早期GVS未完整执行，T10部分旧profile不完整。其余缺少独立观察/假设字段时，只保留原决策rationale，不杜撰内部推理。

PHS原研究详见 [EVIDENCE_INDEX.md](D:/softrobot-agent/runs/phs2d-paper-data-20261112/EVIDENCE_INDEX.md)。本包新增其F8正负distal加载与F3失败过程参考动画，不改变旧研究表格。PHS原指标最小受力点14.798132 mm、最大评分Tip4.346997 mm、最大传递比0.153750600，均只属于该独立Study。
