# T07 — Shared-Morphology Multi-Task Design

本任务最有说服力的贡献是“共享硬件约束使单工况可行性不足；结构修改后仍需每个原始工况重新优化控制并独立验收”。它与 PHS-2D 的被动结构设计互补。建议正文使用两个有原始物理 XML 的真实结构，以及同一最终形态的四工况执行结果。

## 数据归属与边界

- 选定 FULL 主线：`codex-expert-T07-20261113`，来自 `paper_experiments/five_task_completion_20261113/T07_C1_four_tendon`。`FINAL_ABC_DATASET_P0_20261114/D1_ABC_STATUS_MATRIX.csv` 中 method C 指向该 Study。
- 必需条件为 `M1_A`、`M1_B`、`M1_C`、`M5`；四项独立验收全通过，35 个原始硬约束全部通过，最终 SELECT 已封存。
- 实际 actor 为 `codex_surrogate_main`；原 `FINAL_RESULT.md` 明确“未运行正式 Main/Provider”。这是 Codex expert/surrogate 的真实 Core 研究执行记录，不能写为已经验证的 Main SDK 自主复现。
- 历史前驱为 `codex-surrogate-T07-20261112`，来自 `paper_experiments/ten_task_codex_solve_20261112/T07_C1_four_tendon`。该 Study 的 A/C/M5 通过而 B 失败；只作路线来源和反例，不贡献本轮最终验收。
- 本次只读取、提取和整理归档数据。没有构建新控制器、优化、积分、仿真求解或 core/XML 修改。

## 本轮六个真实形态候选

| 节点 | 根段 / 末段长度 (mm) | 根段截面 | 布线半径 (mm) | 研究状态 |
|---|---:|---|---:|---|
| S0 | 158.5 / 109 | 椭圆，半轴 9.5 / 7.6 mm，旋角 0.35 rad | 18 | B 经三次控制精化仍有诊断冲突；没有独立物理验收 |
| S1 | 158.5 / 109 | 同 S0 椭圆 | 14.1 | B 独立通过；同硬件 A/C 诊断仍未过 |
| S2 | 158.5 / 109 | 圆，半径 8 mm | 14.1 | A 诊断 excess 降至 0.008747859，未独立验收 |
| S3 | 159.5 / 109 | 同 S2 圆 | 14.1 | 增加根长 1 mm 后、全命令网格控制仍失败 |
| S4 | 162.5 / 112.5 | 同 S2 圆 | 14.1 | 分布加长反例，A 诊断 excess 增至 0.043968354 |
| S5 | 158.5 / 109 | 同 S2 圆 | 14 | 最终共享形态，四条件独立通过 |

所有本轮形态均为两段、四腱、四独立输入；根段与末段各 12 个 bending cells，实际物理自由度 48。根段 / 末段杨氏模量为 7.2 / 5.4 MPa；密度为 1100 / 1050 kg/m³。末段截面始终为沿长渐变矩形：起点 13.3 × 9.5 mm、角度 −0.25 rad；末端 11.4 × 8.55 mm、角度 0.15 rad。两根腱只跨根段，两根腱跨全臂；完整 attachment/guide/anchor 点已保存在 `evidence_bundle.json` 的 `structures.*.parameters.tendon_route_points`。

最终四条件的 Store `parameters` 和 `resolved_parameters` 逐字段相等；独立结果的 design identity 也相同（`2cc088d7…4529e`），model identity 相同（`1eff3470…d85f`）。四个 candidate artifact ID 不同源于条件绑定；不能将其误计成四套硬件。

上述形态有完整生成候选和 Store 参数。S0/S2/S3/S4 没有留存原始 XML 文件；已保留对应原始候选及保存的数学诊断 qpos。不得将它们制作成“原始独立物理验收截图”。

## 原始证据支持的研究决策

`agent_decision_timeline.csv` 保留 13 个关键决策。`recorded_rationale_quote` 是原始公开 rationale；`analysis_only_summary` 是本次整理分析，二者分列。

1. **先检验控制表达是否不足。** S0 的 B 在 18 mm 布线半径下，控制精化和更细 startup/hold knot 未解决互相冲突的目标、停稳与腱速约束；最后诊断 signed excess 为 0.156432068。没有将有限局部失败宣称为数学不可行证明。
2. **用几何杠杆改变冲突。** `020-generate-smaller-radius-hypothesis.json` 明确提出减小布线半径降低几何腱行程；保留长度、截面、材料、通道拓扑。14.1 mm 半径 S1 的 B 控制重新优化后独立通过。
3. **一项通过不足以称为共享设计。** 同一 S1 硬件测试 A/C；A 经更细控制仍有 0.105688453 excess，C 有 0.006972694 excess。A/C 数值仅是数学诊断，非独立验收失败结果。
4. **修改根截面。** `060-test-isotropic-root-mechanism.json` 原文提出以圆形根降低重力质量和异向截面耦合，并明确承认质量与刚度同时改变，是经验性机制假设，不是隔离因果导数。A 的诊断 excess 降为 0.008747859。
5. **否决直觉上的加长路线。** 根长增加 1 mm 后的全命令网格 excess 仍为 0.010983781；分布加长则增至 0.043968354。决策 `074` 明确拒绝分布长度方案，回到 158.5 mm 根段，并将布线半径微调到原合法边界 14 mm。
6. **同硬件，分别重算控制。** S5 先独立通过 A，再绑定 B/C/M5 并分别优化。旧椭圆根 B 的通过记录没有转移给圆根 S5。
7. **最后改变控制初始化路线，保持硬件。** A/B/M5 已通过而 C 从历史输入种子仍有 0.041124620 excess；`104` 明确选择当前 A 输入作为 C 的“未验收初始化”，再对原 C 条件重优化。A 控制直接放到 C 时初始位置误差为 44.305932 mm，重算后 C holding error 9.897785 mm，独立验收通过。这不是直接控制迁移成功。
8. **联合封存同一形态。** `114-select-all-current-shared-conditions.json` 选择四个本轮独立结果，明确排除椭圆根及其他硬件的旧通过记录。

## 最终独立物理结果

下表来自四个原始 replay artifact 的 `acceptance.metrics`；逐约束的真实限值、裕量、方向和证据路径在 `final_condition_results.csv` 与 `metric_history.csv`。

| 条件 | 位置指标 (mm) | hold 最大速度 (mm/s) | 最大几何腱速 (mm/s) | 原始验收 |
|---|---:|---:|---:|---|
| M1_A | terminal / hold：9.900000 / 9.900000 | 29.700000 | 24.750000 | PASS |
| M1_B | terminal / hold：9.895483 / 9.895483 | 29.699412 | 24.750000 | PASS |
| M1_C | terminal / hold：9.840813 / 9.897785 | 29.660147 | 24.749857 | PASS |
| M5 | 最大工具位置误差：7.920000 | unavailable | 24.750000 | PASS |

M5 最大工具轴角误差 0.05183616091804452 rad（约 2.97°），原限值 3°；位置限值 8 mm。Reach 原位置限值 10 mm，hold 速度限值 30 mm/s。四条件均保留腱位移 ±15 mm、几何腱速 25 mm/s、张力 0–8 N、零 solver error 等原始约束。最终表现接近设定边界，不能把 PASS 解释为大裕量鲁棒性。

各独立物理回合均为 0.6 s、1 ms 积分步、20 ms 采样，保存 31 帧、每帧 48 维 qpos。提取状态没有重新积分。

历史 P0（E=12/12 MPa，圆根 8 mm / 圆尾 7 mm，长度 160/110 mm，半径 14.1 mm）在 B 的独立结果：hold error 16.844494 mm、hold speed 53.490836 mm/s、几何腱速 44.615374 mm/s，失败。P1 仅降低根模量到 9 MPa后仍失败，hold error 16.963469 mm。它们与最终是不同 Study，不能直接连成“同运行收敛曲线”。

## 直接渲染可用素材

优先两个结构并排：S1 椭圆根、14.1 mm 路径；S5 圆根、14 mm 路径。两者段长、末段截面和通道拓扑一致，因此结构差异真实且可解释。统一相机、比例、材质、灯光；建议额外近景以辨认椭圆转圆截面，不能用视觉外壳虚构几何差别。

| 节点/条件 | 原始 physical_replay execution 目录 | 本次抽取的 qpos 文件 |
|---|---|---|
| S1 / M1_B | `STORE_RESEARCH/physical_replay/b1843e1db9c347769f4f3eed0fdd0ca1/robot.xml` | `EXTRACTED_STATES/S1_M1_B_physical_samples.json` |
| S5 / M1_A | `STORE_RESEARCH/physical_replay/01bc6bd847544030a9184a0c75b74cc7/robot.xml` | `EXTRACTED_STATES/S5_M1_A_physical_samples.json` |
| S5 / M1_B | `STORE_RESEARCH/physical_replay/ce240df474034c5abd1d71026481f36f/robot.xml` | `EXTRACTED_STATES/S5_M1_B_physical_samples.json` |
| S5 / M1_C | `STORE_RESEARCH/physical_replay/410c70fe3b4d45de9d023fe2c419a532/robot.xml` | `EXTRACTED_STATES/S5_M1_C_physical_samples.json` |
| S5 / M5 | `STORE_RESEARCH/physical_replay/58afa7b0fe0d43f392929fb1864f995f/robot.xml` | `EXTRACTED_STATES/S5_M5_physical_samples.json` |

表内原始目录均相对于本轮源目录。完整绝对路径、Store raw artifact ID、原始 result 路径、状态指针和 qpos 维度均位于 `evidence_bundle.json`。建议最终共享硬件四个末态（t=0.6 s）展示各工况，在 B 用 S1/S5 同工况的末态作为结构修改对照。历史 P0/P1 保留原 XML 和已存轨迹作补充反例。

## 图表建议与资源

正文优先组合：左侧两个真实结构，中间用“B passed → A remains infeasible under current control → circular root → reject elongation → final hardware”极简标注，右侧共享形态四个已存末态以及按工况保留量纲的约束结果。C 的初始化路线变化是另一条控制研究发现，可用同硬件两条控制张力序列与相同 C 目标的位置误差支持；不得画成两种硬件。

不同工况、原生局部诊断与独立验收采用独立 panel/符号。不要把 B、A、C 和 M5 的原始误差连成一条收敛线。诊断 excess 可作为明确标注“finite native diagnostic”的离散设计试验点，但应保留控制设置和预算差异，不声称单一结构因果消融。

本轮成本单独为：16 次计费数学评价、5 个独立物理 replay、122 个 budget tool calls，budget wall 1749.667384 s，数值记录 wall 1738.269096 s。数学内部有 16,481 个 rollout / optimization evaluations 和 9,888,600 个积分步；这些是历史数学诊断内部成本，不是本次素材整理的新计算。5 个独立 replay 共 3,000 步。Codex 编排 Token unavailable；model_calls=0 与“未运行 Provider”不能推断编排 Token 为零。前驱原成本单独保存在 `resource_usage.json`，不加到本轮。

## 缺失与交付

已整理：8 个结构节点（本轮 6，前驱 2）、13 个关键决策、184 行原始指标/约束、10 个独立 replay（本轮 5，前驱 5）、16 个本轮数学诊断、26 个已存状态提取文件。没有全量 SHA 审计。

缺失：S0/S2/S3/S4 原 XML 文件；S1 A/C/M5 的独立验收；官方 Main SDK/Provider 自主执行；Codex 编排 Token。均明确标记 unavailable，未填造数据。渲染由统一根流程读取现有 XML 与状态完成；本提取脚本不调用 MuJoCo。

## 已生成的正式科研图与表

- `FIGURES_PAPER/T07_final_physical_constraints.png` / `.svg`：7.16 × 2.35 inch，三个 panel 分别展示四工况位置指标、holding/几何腱速和 M5 轴向误差；原始硬限值以短虚线直接标记。M5 没有 holding speed 指标，显示 n/a。所有图值来自原独立 replay 的 constraint margins。
- `FIGURES_PAPER/T07_evidence_driven_research.png` / `.svg`：7.16 × 2.5 inch，两个 panel，A 的五个真实形态诊断试验与同一最终硬件上的 C 控制初始化变化。所有点均不连线；明确只为有限预算 native diagnostic，不冒充独立验收或隔离因果消融。
- `FIGURES_PAPER/TABLE_T07_FINAL.tex`：六列 booktabs 表；四个工况逐项结果，缺失项显示 `--`。
- `FIGURES_PAPER/FIGURE_CAPTIONS.md`：中英文图注、适用结论与归属说明。
- `FIGURE_DATA/*_plotdata.csv`、`T07_structural_parameters.csv`、`SOURCE_PROVENANCE.json`：保留精确图值、原始限值、单位转换、control schedule settings、预算/求解终止状态、原证据 Store 路径和绘图命令。

这些图适合伴随真实机器人结构与执行画面，正文最有用的证据是：圆根修改解决共享形态条件冲突、加长路线被数据否决，以及最终硬件冻结后 C 必须更换控制初始化并重新优化。图中未将不同工况混合平均，也未将各诊断点连接为收敛曲线。
