# 论文结果包的仓库副本

入口为`PAPER_SUMMARY.md`，原始逐工况数据见`TASK_CASE_RESULTS.csv`及`SOURCE_DATA/FULL_CASES.json`，研究过程见`RESEARCH_PROCESS.md`。结构和动画分别位于`FIGURES_MUJOCO`和`ANIMATIONS_MUJOCO`。

T04完整逐步数组采用无损gzip保存：

`SOURCE_DATA/TASK_TIME_SERIES/T04_default_FULL_ARRAYS.json.gz`

本地未压缩原文件保留但不提交。克隆后如需普通JSON文件，可在本目录执行：

```powershell
python restore_archived_data.py
```

也可直接使用Python标准库读取：

```python
import gzip, json
with gzip.open('SOURCE_DATA/TASK_TIME_SERIES/T04_default_FULL_ARRAYS.json.gz', 'rt', encoding='utf-8') as f:
    data = json.load(f)
```

`SOURCE_DATA/ORIGINAL_PHYSICS_XML`保存这批结构展示对应的原始物理XML副本；`SOURCE_DATA/PORTABLE_MODEL_INDEX.json`关联原始模型、独立视觉XML及其历史来源。文件中的原实验绝对路径用于来源追溯，历史Store和数GB完整PHS轨迹仍位于原实验目录，本次不把工作区其他未提交目录混入结果提交。

统计图仍为草稿，后续写论文时根据已整理数据重新设计。所有结构截图和动画均为MuJoCo原生渲染，未重新求解或积分。
