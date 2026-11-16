# Physics-Grounded Agentic Research for Soft-Robot Co-Design

本目录按论文科学论点组织现有证据：Main Agent 提出物理假设，PPRP 将研究意图转为可执行问题，互补的 M0–M3 支持不同物理问题，数学证据与物理证据分别进入 Research Decision。Reporter、Knowledge、Skill 与 Hierarchical Context 的结果作为决策过程证据单独报告。

**FULL：11 项任务，30 个 required 条件，另有 T10 的两个冻结对照。** 每项任务均有 2–4 个 Research Nodes。Task Registry 有 12 条物理 Study 记录，因为 PHS-2D 包含两个独立 Study；不得把独立九段结果计入原 11 项 FULL 分母。

| 证据 | 当前交付 |
|---|---|
| 任务能力 | 11 项 FULL 汇总；33 个 A/B/C 组合；3,160 条逐条件指标；保留失败、资格、偏离和缺失 |
| PHS-2D-7S | 四腱、无主动执行器，10/10；最小受力点 14.798 mm，最大 Tip 4.347 mm，最大比 0.15375；属于 FULL |
| PHS-2D-9S | 独立 Journal 的 46 个候选；四个代表机制节点；10/10；独立复核最小受力点 11.155 mm，最大 Tip 3.068 mm，最大比 0.1093；保留半步长与初态扰动检查 |
| 数学验证 | 6 载荷分支 × 3 指标，共 18 组隐式/有限差分梯度；一条共同模量扰动方向；最大相对差约 0.1191223% |
| 研究过程 | 32 个节点，1,927 条原始事件/证据—行动关系；原始假设、执行状态与事后结果范围分开；8 条数值变化记录 |
| 节点标注 | 全部节点初评；18 个关键节点独立匿名模型复核；保留理由、来源、置信度与不确定字段 |
| Reporter | 六组配对完整；平均 +0.300，2 胜/4 平/0 负；两个重点案例及原始决策对照 |
| Knowledge/Skill | 原八个四格决策完整；经验利用 0/3/3/3，其余评分饱和；补充 16/16 个会话，15 个有效决策；另按用户要求增加统一五维盲评，保留原四维 |
| Context | E2 与 E2-R2 保留各自 usage 口径；新增 12/12 个跨任务会话，11 个有效决策，6/6 组盲评；新 Gateway usage 缺失时为 UNKNOWN |
| M1/M2 | T07 两个真实结构、相同四通道契约已核对；逐条件三模式方案和原请求模板已准备；完整成对物理结果尚未执行 |

## 使用入口

- `registry/`：正式任务名、Study、符号及指标。选定参数集合使用 I_k，合法设计空间使用 D；M0–M3 不是顺序流程。
- `task_metrics/`：权威数值、候选结构、物理工况、数值复核和原始资源范围。`research_nodes/`：观察—假设—研究—证据—行动—结果及标注。
- `architecture_metrics/`：完整 Reporter/K/S/Context 配对、逐请求 usage、实际检索路径和失败记录。
- `figure_data/` 和 `figure_manifest.md`：Fig. 2–8 绘图 CSV、Panel 坐标/单位、颜色、Caption、正文/补充定位及缺失数据。Fig. 4C 的 UNKNOWN 不能绘成结果。
- 仓库根 `paper_handoff/`：供论文分支使用的自包含数据快照；不需要连接实验 Store 即可读取 CSV 和绘图数值。

## 关键解释边界

原论文草稿将 FULL 的 PHS 写为九段，与 Source A 原记录不一致。此交付按原始七段 FULL 与独立九段扩展分别注册，未修改论文正文或 Figure 1。无真机完整记录支持时不生成 Fig. 9 的测量结论。

局部数学诊断、结构生成、输入迁移、已执行重放和完整独立物理验收不相互替代。T08-C 的 development 分类和不利结果保留。不同任务的 m/rad/N 不求混合均值；不同资源范围不相加。实际 usage 不可用时保留 UNKNOWN，不用 tokenizer 估算替代。

原始数据只读，来源以 branch/path/run/candidate/condition/记录定位，不计算或校验文件哈希，不复制 Store 或完整 Trace。新输出只有归一化记录和由其生成的绘图视图；论文交付目录是生成快照，不应手工编辑第二份数据。

K/S 统一五维评价为 Physical Interpretation、Evidence Consistency、Limitation Recognition、Research Actionability、Evidence Reference Accuracy。历史经验利用单列；原四维和新增五维不混算。原 E1 和后续检查点的决策状态不同，只做分检查点的描述性比较，保留评分饱和。

## 复现与尚缺

标准库离线流程：`python paper_evidence/tools/build_evidence.py` → `research_details.py` → `prepare_m1_m2.py` → `finalize_publication.py` → `validate_evidence.py`。原来源通过固定 Git 提交只读加载；原始局部 Trace/Store 只在所需节点细节提取时读取。决策补充脚本是显式单独入口，不会由离线构建或验证触发。

数据交付已覆盖全部 Fig. 2–8 入口，但匹配 M1/M2 物理实验、结构演化统一相机渲染和新 Gateway 实际 usage 仍不能宣称完成。完整状态见 `supplementary_experiments/RESULTS.md` 与 `validation_report.md`。未访问到附加设计文本/DOCX 时，以任务说明和正式仓库记录为准。
