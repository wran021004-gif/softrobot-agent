# 已完成验证的报告续作交付（2026-10-07）

本次完成第八次报告链修复、完整确定性结果、当前模型解释和独立事实审查。没有新增机器人仿真、搜索批次、数值实验或工作角色。科学轨迹仍是三个研究批次、六次执行，加上已经完成的二十次匹配验证；原科研 STOP、失败请求、index3 历史工程报告和原始实验记录均保留。

三个研究批分别考察终端速度权重 0.10/0.025、near 截面比例 1.00/1.05、far 截面比例 1.00/1.05。near 批沿用已接受计划执行；near 反馈后 model6 接受并执行 far-only 批，两个 far 候选各自通过新鲜 nominal 联合判据。0.025 和 near 1.05 未通过。两份后续长度提案均被拒，未执行长度实验。历史隐式零与当前显式零初始化有不同原始任务身份，历史通过结果仅作描述性比较；incumbent 并非唯一历史通过配置。

原 incumbent 为 `batch-ebbeadbdaca10732-0`，源配置 `285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978`；冻结选择为 `batch-396bdbbae02626d3-0`，源配置 `3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b`。唯一选择变化是终端速度权重 0.05 → 0.10，保持速度权重仍为 0.05。near 长 0.16 m、far 长 0.11 m、两段截面比例 0.95、compliant 材料及其物理字段均不变；旧共享选择器与当前分段选择器的构建注释不同，原始配置哈希保留。各验证执行的独立配置、任务与科学身份列在完整表中。

五个固定案例、种子 17/18、每角色十次唯一完整执行，均核对官方评价与 profile 的执行链接、原始收据、最后 0.05 s 的六个均匀保持采样点。完整结果见 [JSON 表](../evidence/research_native_development_v3_20261007/report_completion_20261007/all_execution_results.json)、[CSV 表](../evidence/research_native_development_v3_20261007/report_completion_20261007/all_execution_results.csv)、[逐案例表](../evidence/research_native_development_v3_20261007/report_completion_20261007/per_case_results.json)；逐执行与逐案例费用见 [核验费用](../evidence/research_native_development_v3_20261007/report_completion_20261007/verified_execution_and_case_costs.json)。模型不负责复制或筛选这些行。

| 案例 | incumbent 联合通过 | 候选联合通过 |
| --- | ---: | ---: |
| nominal | 2/2 | 2/2 |
| near_z_plus | 2/2 | 2/2 |
| near_z_minus | 1/2 | 2/2 |
| far_y_plus | 0/2 | 0/2 |
| far_y_minus | 1/2 | 1/2 |
| 合计 | 6/10 | 7/10 |

七个失败槽均超出保持速度 0.02 m/s：incumbent 的 near_z_minus/17、far_y_plus/17、far_y_plus/18、far_y_minus/17；候选的 far_y_plus/17、far_y_plus/18、far_y_minus/17。二十次官方终端位置评价均通过，但两配置均未通过整个联合套件。没有将这一结论改写为完成旧鲁棒性协议。

| 套件最坏指标 | incumbent | 候选 |
| --- | ---: | ---: |
| 终端误差 m | 0.0031794922216638703 | 0.00401791580527543 |
| 保持误差 m | 0.0033040679451552747 | 0.004070644033629745 |
| 保持速度 m/s | 0.07026211095497123 | 0.06484873299977026 |

冻结规则以联合通过计数为首要判据，计数相同时才比较分量。因此按原规则晋升候选，同时明确其最坏位置误差升高、最坏速度降低；这不是全指标改善或结构设计获胜。十次固定观察不是总体成功概率。700/700 次更新超期，均值范围 7.927–14.491 s 对控制周期 0.01 s；未证明实时性，实时性也不是此套件的验收条件。没有证明连续时间保证、泛化、数学最优或收敛、因果贡献或 LLM 优于基线。

旧报告失败由两个事实 `f_96edaddd1d3309826302`、`f_c331bc418b39770ae17e` 的值/来源错配引起：profile 值 0.0026978288583256148 被标成 evaluation 来源，原评价实际为 0.002697828858325615 m。新投影 `authoritative_metric_projection@1.0.0` 同时从评价读取终端值与 `/metrics/0/value` 指针，保持最大值仍从 profile 的 sampled_settling 读取，并生成新事实 ID 和显式 supersession；未改原值、放宽相等保护或改验收阈值。[修复记录](../evidence/research_native_development_v3_20261007/report_completion_20261007/corrected_fact_projection.json)及[真实记录门检查](../evidence/research_native_development_v3_20261007/report_completion_20261007/offline_acceptance.json)包含来源、单位、错误绑定拒绝及冻结请求恢复检查。十项受影响回归测试与四项原始记录对抗测试通过。

报告专用入口为 `examples/research_campaign_v3.py report-completed`，替代本次失败的 v2 `finish` 报告调用，未恢复科学执行。它使用原账本/current_authority 记账绑定、共享 context_assembly 和原 DeepSeek 凭据加载/传输；只提供报告接收函数，所需证据预取，未宣称模型能调用不可用的读取工具。完整请求含函数 schema，估计输入 59,251 token，低于冻结 96,000 输入限额；保留原模型、端点、high 推理、65536 输出限额、600 s 超时及 TLS 验证。请求自己的事实快照恢复后不依赖最新状态。

本次实际获得两份当前响应：[首次解释](../evidence/research_native_development_v3_20261007/report_completion_20261007/model_attempt_1.json)与[唯一纠正后的解释](../evidence/research_native_development_v3_20261007/report_completion_20261007/model_attempt_2.json)，均显式绑定完整二十行证据。首次连接拒绝已收费；核对无完整响应或动作后使用唯一传输重试。独立审查认定主要科研结论、全部计数、反例和取舍受证据支持，但[最终审查](../evidence/research_native_development_v3_20261007/report_completion_20261007/independent_review_attempt_2.json)仍未完整采纳其文字：模型仍将“实际可用容量的不足量为零”混写为补缺口的剩余容量为零，并把第八次修复混入先前七次失败边界。正确解释是计划 2000 s 比完整需求 2590 s 少 590 s，而实际可用额度相对该需求没有短缺；model9 自愿 STOP 不证明资源耗尽或最优停止。提供方三次尝试及一次纠正均已用完，不再调用；完整确定性报告独立交付，不把未通过审查的文字当成已核实结论。

原本地结算基线为 106 workflow ops、10 model attempts、26 backend solves、18361.17524650578 s。本次三次提供方尝试已结算 77.98399999999674 s；新增 workflow op 一次（覆盖修复、离线核验、审查、发布），backend/独立数值/worker 均零。完整二十验证原费用为 60 tool ops、20 backend solves、7047.4959999999555 s，已在原账本内，不重复收费。本次已知 token 为 prompt 35156、completion 19093、total 54249；累计已知 token 为 458582/225833/684415。连接失败 token 和货币费用未知。

发布快照的累计占用为 107 tool ops、13 model attempts、26 backend solves、20239.159246505777 s，含尚未结算的 1800 s 交付预留；其中已结算累计时间为 18439.159246505777 s，不能把预留当实际费用。[在途说明](../evidence/research_native_development_v3_20261007/report_completion_20261007/publication_inflight_accounting.json)保留此区分。正常 push 和远端 SHA 核验后，原本地账本按实际总耗时扣除已单列的提供方时间，一次性结算；精确新增/累计成本、剩余额度及已核验远端 SHA 记录在 `runs/research_native_development_v3_20261007/report_completion_settled_costs.json`，并在终端交付说明公布。原截止仍为 2026-10-07 12:43:49 UTC，新增上限仍为 1800 s/12 workflow ops/3 provider attempts，无时钟或额度重置。

报告链到此结束。未来目标是以证据支持 LLM 组织设计，完成明确任务；无需全局最优。若另有科研授权，应先明确旧失败案例需要达到的联合标准，再设计容量可行的改进与独立验证；模型建议的长度搜索只是未证实提议，不是已识别原因或本次授权动作。
