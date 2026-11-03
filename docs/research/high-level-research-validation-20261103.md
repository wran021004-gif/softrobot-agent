# Softrobot Agent 高层科研接口及真实 Main 最终验证

原 Study `m1-low-tendon-speed004-20261102-campaign3` 已完成正式SELECT并封存，状态 `stopped`。同一三段三绳结构在三个冻结工况的独立Replay全部通过，成功门和结构选择均已完成。运行实现 `2542a839c78cf68db20fc6cb23c0c2750562962c`；联合选定结果 `7fee7f0cde4669da72b2d0a4e0fe61a8507f45c0cf28560d995e03558c42f18b`。报告提交与运行冻结身份另列，文档提交不重开已封存研究。科学结论及局限详见后文；单个Native模型过线不等于任务验收。

本轮实际新增 38 次 Provider（角色 {"conversation": 35, "reporter": 3}），累计 182/191；公共操作 172/569、独立 Replay 3/18。新增数学计费 85 单位，保存 85 条分析结果，实际 52,850 次 rollout、31,710,000 个物理步。上述为正式 Study；隔离工程测试成本单列。

独立 Replay 另有 3 次 rollout、1800 物理步；正式续研两类合计 52,853 次 rollout、31,711,800 物理步。它们是仿真成本，不是硬件试验。

其中 9 次 Main Provider 请求实际启动计算，类型计数为 {"joint_structure_control_search": 2, "mathematical_worker": 4, "independent_physical_replay": 3}。一次联合搜索可以启动多次按工况计费的 T1；路由、读取、候选生成、拒绝和收尾请求不算数值实验。独立 Replay 的后端成本另列，不混入 Native 数学 Worker 的 rollout/物理步统计。

原2244个封存 artifacts、原STOP和旧历史及费用已逐项验证保留；原h43的39/39引用完整性保留。最终 pending、Provider reservation、SDK未消费响应和未封口调用均为零。最终结算动作为 `select`；三工况联合独立接受核对为 `True`，原确认门禁满足为 `True`。冻结协议要求额外重复次数 `0`，重复性评估为 `False`。本次SELECT引用所选三项完整验收证书；STOP的全结果引用规则不适用，审计中all_required_results_cited=false不表示原SELECT未完成。 最终原 Plan 的解释为：

> All three acceptance certificates were completely read and have no validation issues. Evaluation_3820 accepted positive_high with terminal error 0.0090037621 m, holding error 0.0095447053 m, and holding speed 0.0393806548 m/s. Evaluation_3782 accepted negative_low with terminal error 0.0096790791 m, holding error 0.0099993249 m, and holding speed 0.0398635266 m/s. Evaluation_3851 accepted central_high with terminal error 0.0098762850 m, holding error 0.0099974635 m, and holding speed 0.0399949885 m/s. Every execution is complete, current-study fresh, force-bounded, solver-error-free, and has complete holding coverage. The negative_low and central_high certificates explicitly bind their structure_candidate to candidate_3090. The prior two SELECT rejections were repaired interface defects, not scientific failures, and no evidence or cost changed. Therefore the full frozen three-condition gate is satisfied and immediate SELECT is required.

## Main 自主研究结果

两轮联合搜索都由 Main 选择科学假设、物理变量组、腱数、分辨率、控制范围和有限努力。监督器未指定两绳或三绳，也未强制 T2。

| Main 选择 | 实际执行 | 共享结构最坏 J | 实际结束原因 |
|---|---|---:|---|
| 三段两绳，5类结构变量，fine/broad，4096 callbacks/T1，12提案、36分析 | 12结构×3工况，36个 T1；9结点×2通道=18维、8N修正跨度 | 基准22.4647985 → 最佳16.2667108 | evaluation_budget_exhausted；34次局部线搜索数值失败、2次停滞 |
| 三段三绳，5类结构变量，fine/broad，8000 callbacks/T1，16提案、48分析上限 | 1个裁剪后重复提案无计算，15合法结构×3工况，45个 T1；9结点×3通道=27维 | 基准15.2966585 → 最佳0.726920071 | proposal_budget_exhausted；原始逐工况停止及成本保留 |

第二轮最佳共享结构的三个工况为 positive_high J≈0.726920071、negative_low J≈0.605353045、central_high J≈−0.000125288。中央工况保持位置最大误差0.009997463486 m、保持速度0.039994988493 m/s、终端误差0.009876284992 m，均只是采样 Native 模型中的窄幅过线；不能推定连续时间裕量、鲁棒性、硬件或独立验收。两轮81次 T1 中共有5个单工况模型过线，分布在不同结构，不能把它们拼成一个通过结构。

Main 在初次续研已指出旧两绳搜索有限且未匹配，不能证明不可行。第一轮后，它仍把大残差和边界张力较强地归因为方向驱动不足，选择测试三绳。实际 Reporter 随后指出数值失败和机制工作点缺失；Main 后续明确承认回调远未用尽、局部数值收敛未解决，并选择保留最佳三绳结构、增加时间分辨率和多个起点。这显示它利用新证据转向控制不足这一可检验解释，但未完全消除过强的结构归因。

特别是，Main 对“三绳是当前最低有根据数量”的表述只能视为有限搜索偏好，不能当作最少腱数结论。两轮同时改变了结构变量、输入维度、搜索努力4096→8000及数值停止事实，不是腱数的受控因果实验。Main 还曾说条件克隆导致搜索错误混排；实际程序按同一物理结构联合排名，克隆用于冻结的不同工况。监督核对证明后续完整 materialization 与原最佳共享候选逐项相同，并复用同一不可变身份，没有产生另一结构。

第21次新 Provider 请求是 Main 自主提交的 V4 控制实验：同一正高工况结构、全任务、very_fine/broad、8000共享回调、两个明确控制源，关注保持速度但未改变完整任务评分。实际编译和 Worker 设置逐项一致：17结点×3通道=51维，8N修正跨度，原协议/求解方法保持。真实 Worker 正常完成并确认终止，213次回调对应213个唯一输入、213次rollout、127800物理步。

从已保存最佳控制出发的起点将正高 J 从0.726920071改进到−0.015483629，保持位置最大误差0.009544705295m、保持速度0.039380654826m/s、终端误差0.009003762101m，停止 local_target_reached。另一个合法起点从J22.1995165仅改进到17.4998137，没有过线。两起点提供了不同且实际执行的信息，不能把“选择多起点”本身当成改善原因；新时间基函数、继续搜索及已有最佳控制共同参与，本轮未作单因素分辨率对照。该模型过线仍不授予独立任务验收。

第23次新请求暴露出一次实质性的自主交接不足：h49 文字打算研究负低/中央，但结构化 V4 请求仍是正高候选，所选3个源也属于正高。实际 Worker只做3次起点rollout、1800物理步、0优化迭代，返回已有正高通过值，没有新的负低或中央信息。它不是另两工况的科研进展，费用和原结果完整保留。随后在安全边界新增必选高层工况字段及匹配反馈，而非把这次结果重新解释成其他任务。

修复后的第24次新请求由 Main 明确选择 negative_low。实际编译器发现当前候选仍绑定正高，未运行数值求解，返回已有同结构负低候选和两个合法源；只计1次公共操作，无 Worker 资源。第25次 Main 据此记录h50，明确承认第23次只重复了正高，选择 exact same physical structure 的负低候选，纠正了此前把工况克隆当成另一物理设计的混淆。该实际交接和同一物理配置核对单列在 actual-condition-handoff-validation.json。

第26次新请求实际执行了负低 very_fine/broad 双起点 T1，显式condition_id与实际候选一致，17结点/51维及原冻结协议逐项核对通过。J从0.605353045降至0.191193970，保持位置误差0.011752867408m、保持速度0.047647758806m/s、终端误差0.011492137573m，仍未通过。677 callbacks中51个重复输入复用缓存，仅执行626次rollout、375600物理步。Worker正常完成并确认终止，停止原因为局部线搜索数值失败，8000回调上限未耗尽。这证明高层工况交接已实际执行了正确问题，也提供真实多起点去重证据；它没有证明结构不可行或全局最优。

Main h51把这次68%的改善解释为控制假设的部分支持，认为局部早停不足以直接转向结构，选择测试逐区间控制自由度；但误以为Direct方法会自动取消插值耦合。源码核实Direct/T1共用搜索后，在下次请求前补齐明确control_grid选项及真实方法说明，未执行名义换方法而参数化不变的错误对照。冻结协议提供30个输入区间而非31；最终是否采用此档位仍由Main自主选择，后续结果单列，不把工程测试当作实际实验。

第28次新请求中，Main自主明确选择negative_low、control_grid/broad、3个合法源及Direct。真实Worker执行为30结点、90有效维，原协议和请求编译逐项一致。571 callbacks/571 rollouts、342600物理步，42.19秒正常结束并确认终止。J0.191193970→−0.000067505947，保持位置误差0.009999324941m、保持速度0.039863526605m/s、终端误差0.009679079071m，停止local_target_reached。保持位置余量只有约0.675微米；当时尚未执行独立验收，鲁棒性也未验证。来自17结点最好控制的起点过线，旧9结点最好控制起点仅到J0.000532170，基准起点仍J18.2075747。方法名、更多自由度、继续搜索和起点同时改变，本轮不把改善单独归因于Direct。

只读核对证明该共享物理结构分别保存了正高、负低、中央的三个完整、合法采样模型过线控制，精确best控制源见three-sampled-witnesses-validation.json。各结果的实现身份和搜索努力不同，不能组成合格T2对照。这份核对未运行Provider或Worker，也未授予任务接受。

随后Main自主选择逐项复用精确保存的最好控制，按负低、正高、中央顺序执行原独立Replay。三个实际Worker均完整结束并确认终止，原验收器全部接受；回放实际输入与三个保存的最好输入序列逐项相同。共享的是同一完整物理结构，冻结工况目标与初值保持各自定义，没有拼接不同结构或重新求解控制。验收数值及最终SELECT/确认状态见下一节。

T2在本次未由Main选择，工程调用链及unresolved割线不冒充自主T2科研。检查点A（结构与控制瓶颈区分）部分达到：Main实际根据控制改进继续检验控制假设，但最少腱数及结构因果判断仍未证明；检查点B达到：多起点和多分辨率确实编译、执行，并给出起点差异和实际缓存收益；检查点C未选择，由独立工程测试覆盖接口。三个独立采样验收通过证明本冻结仿真任务下找到可行解，不消除上述因果、裕量或鲁棒性局限。

末次h55重提SELECT时，Main已明确补充“不声称全局最少绳数或两绳不可能”的限制；它仍称两绳对照matched，然而两轮努力和其他变量实际不同，因此本报告保留因果局限，不把文字修正当作补做了受控对照。


## 原独立验收与正式结算

以下值直接来自原注册任务验收组件；没有重算评分或放宽阈值。终端误差及保持位置上限均0.01m，保持速度上限0.04m/s。冻结保持窗口为[0.54,0.6]s，包含4个0.02s均匀采样点。原协议没有连续时间、鲁棒性、硬件或重复性保证。

| 工况 | 终端误差 m | 保持最大位置误差 m | 保持最大速度 m/s | 完整 | 原验收通过 | 输入与保存的最佳控制完全匹配 |
|---|---:|---:|---:|---|---|---|
| negative_low | 0.00967907907135136 | 0.009999324940534666 | 0.039863526604954916 | True | True | True |
| positive_high | 0.009003762101256209 | 0.009544705294598077 | 0.03938065482613654 | True | True | True |
| central_high | 0.0098762849917123 | 0.009997463486434158 | 0.03999498849250668 | True | True | True |

原 evaluator 共通过 3/3 次独立执行。数学 Worker 85 个、独立 Replay Worker 3 个均已确认终止；各次数值过程与回执保留。

共同结构为三段三绳；段长依次0.16/0.13/0.14m，Young模量13.7/6.9/7.0MPa，圆截面半径11.25/9/8mm，每段12个单元。三条全跨绳的半径为18mm，相位约270°/30°/150°。完整截面旋转、路由、物理参数及三份精确保存控制见selected-design.json，正文数值仅作摘要。

三个工况的同结构通过解按原 SELECT 和确认门禁封存。三绳是本轮找到的可行结构；最少绳数未证明。Main仍有把两绳失败较强归因为结构方向不足的表述，不能随通过解一并视为已证因果结论。

## 方法与接口

| 方法 | 实际作用及前提 | 证据边界 |
|---|---|---|
| generate | 明确父结构及绝对 SI 物理参数改动，或原合法拓扑生成 | 构造结构；不优化控制、不继承旧通过证据 |
| scientific_structure_search_v1 | 复用 bounded_mixed_coordinate_v1，在 Main 选择的变量组、结构范围和有限努力内生成并评价结构 | Native 模式逐工况执行 T1；Conic 代理不得冒充 Native 或物理验收 |
| mechanism_structure_v1 | 在绑定的物理工作点 inspect、differentiate、optimize、compare | 驱动、制动、惯量等机制诊断不等于任务可行性证明 |
| Native T1 | 对给定结构及工况执行有限合法控制搜索 | 记录最好 J、真实设置、初值、成本和停止；失败不证明不可行 |
| Native Direct | 与T1共用Native response/pattern及所选时间参数化，适配一般注册任务 | 方法名不增加自由度；Direct为通用诊断，T1才提供后续T2的saved-T1语义 |
| Native T2 | 聚合已保存、同实现、同工况、匹配初始输入和搜索努力的基准/正负扰动 T1 | 不额外生成结构或运行 T1；局部有限预算割线不是最优梯度 |
| Conic task capability | 冻结初始预张力下的采样仿射 minimax | 不围绕任意 Native schedule 线性化；合格序列仍需 Native 和独立 Replay |
| qualified sensitivity | 原合格 Conic 模型 stencil 的条件敏感度 | 原匹配、正则性和数值检查仍需满足，不等同 Native T2 |

Main 在 V4 控制和结构联合搜索中填写 `resolution`、`exploration`、`evaluation_requests`，不填写实际 knots、系数索引、差分步长、信赖半径、状态向量或原始 AnalysisRequest。程序在冻结网格编译 coarse/moderate/fine/very_fine 为 3/5/9/17 个结点；旧档位含义保留。另可明确选全任务 `control_grid`，本冻结任务为30有效输入区间、90个有效控制系数；31个观测边界不是31个输入区间，没有无效末端系数。此档位不支持局部窗或超过原结点额度，均明确拒绝。广范围按实际 8 N 张力跨度编译，局部精修用其 10%；底层 response 方法及物理裁剪仍由原实现负责。全过程保留 8000 回调、1000 迭代、64 结点和每 Worker 600 秒的原上限，不静默降级。

Main 可选全任务、reach、holding 或明确时间窗，以及一个或多个合法控制源。局部窗口端点修正为零，评分始终覆盖完整冻结任务的全部约束。多个起点共享一次请求的 callback 额度，相同实际控制序列使用原缓存。没有随机替 Main 选择控制源、结构变量、扰动尺度或研究方向。

多工况 V4 控制还要求明确 `condition_id`，来自真实冻结工况枚举；它必须与当前候选及所有控制源一致。工况不匹配时，编译器只读查找同一物理结构的精确已有工况候选和合法控制源，供 Main 自主 diagnose 和选择；不存在时才返回原 `initialize_control` 准备入口。不从自由文本猜测工况，不覆盖任务，也不自动启动其他工况实验。

`generation.changes` 只修改 Main 明确选择的物理路径，父结构的其余参数和截面旋转保留；`changes={}` 可明确重建历史候选而不迁移旧证据。原执行准入继续拒绝旧 profile。T2 默认准备信息只显示基准、正负扰动、匹配状态、缺失项及后续高层入口；完整域、引用和请求模板位于 `/t2_preparation/details`。用户选择的实际扰动量按原物理域反馈，不改成另一参数或尺度。

## Main 与 Reporter 的实际信息交付

实际 Provider wire、原始响应和工具回执均保存在原 Store。下表逐次列出本轮新请求的输入字节和 Provider usage，既包含科学决策，也包含路由、读取、错误及收尾。字节数是完整请求体，L0 是其中的当前科研投影；历史对话及工具 Schema 另占上下文。

历史最后探索 Main 为 334996 bytes / 49705 prompt tokens，旧收尾为 346796 / 50629，旧 Reporter 为 30012 / 7892。新旧工况、结果数量及对话历史不同，这些值不能作为同状态压缩率。原 h43 的离线同状态 L0 从 86299 降到 78985 bytes，没有额外 Provider token；隔离工程 Reporter 的双结果组装体由 54553 降到 50267 bytes，也不是新 Provider 请求。

新增瓶颈诊断和 T2 准备入口已进入实际 Main L0 和 Reporter 同源摘要，不限于程序员手动调用。L0 给出任务违反、有限搜索改善、真实停止、数值不确定性及精确查询；原始控制、状态、矩阵、迭代和完整 T2 请求留在 L1/L2。实际第 12 次新 Main 请求仍发现 4 处内部 knots 数组，已保留该次原 wire 并修复固定搜索摘要；修复后的扫描结果逐次记录在交付 JSON，不能抹去既往泄漏。

本轮专门的数学 Reporter 交付核对由监督器通过原公共操作显式发起，属于只读接口验证，不冒充 Main 自主调用。它实际消耗共享账本 1 次 Provider 和 1 次公共操作，未产生数值 Worker 或修改科学计划。完整请求 106370 bytes，输入 28442、输出 720 tokens；三结果交付体 95842 bytes，无完整原始数组。Reporter 正确保留指标、阈值及来源，区分 4096 请求上限、361/418/247 实际回调、266/306/247 唯一输入和缓存复用；指出局部数值失败而非额度耗尽，缺少与最佳控制绑定的机制证据，不能从饱和张力推断结构不足，也没有独立验收。

Main 后续发起的独立 Replay 按原流程自动触发 Reporter，也计入同一 Provider 账本。首份真实负低 Replay 解释输入6638、输出531 tokens，正确说明原验收accepted、精确指标与阈值、0求解错误/0输入超界，指出0.675微米保持位置余量且没有连续时间、鲁棒性、重复性或硬件证据。这个自动解释属于原正式实验信息流，不冒充Main主动调用research_investigate。各份实际请求字节、usage和交付体字段见逐次请求表与formal-main-progress.json。

精确 Source ID、EvidenceRef、指针和原始设置查询均可从摘要进入详细原值。真实Main上下文仍有数万tokens；历史投影曾约耗时210秒并占用数GiB，完整对话和历史规模仍有改进空间。收尾时还定位到元数据视图重复完整解码约1GB分析工件；使用原Store字段投影修复，124份真实工件、107组候选的返回元数据逐项完全相同，修复下只读联合资格检查约7.15秒。该测量不是整个Main请求耗时或同状态端到端加速比，没有删除科学事实或改验收。

## T1 与 T2 的工程和自主证据

隔离工程 Store 在提交 a29aad3 下实际完成 6 个 Worker：多起点、细分辨率、3 个匹配 T1 和 1 次 T2 聚合。合计 11 rollouts、6600 物理步，全部终止确认。3 个起点中有一个重复实际输入，4 callbacks 只产生 3 次 rollout；粗/细控制维度真实为 6/18。Young 模量基准 3.5 MPa、实际对称步长 ±260000 Pa，对应 Main 所选 2% 冻结物理域跨度。T2 复用 3 份 T1，新增 rollout 和物理步均为零，结论 unresolved，未宣称结构最优梯度。

这组工程结果只证明调用链与匹配检查。正式 Main 是否实际选择 T2、多个起点或新分辨率，以本报告的自主结果和逐次请求为准。旧实现完成的 T1 不会自动成为新实现的合格 T2，结构修改也不要求先过 T2。没有强制 Main 按固定顺序研究，没有启动 PPO 或另建 RL Study。

## 监督期间修复和验证

所有修复在无在途 Provider/Worker、无未消费 SDK 响应及未封口调用的安全边界提交、普通推送并按原机制绑定。暂停自有 Job 是工程暂停，不制造科学 STOP，不重复已完成 Worker。

| 实际暴露的问题 | 最小修复与实际验证 |
|---|---|
| 历史 profile 的只读能力目录误用执行准入，Main packet 无法构建 | 历史读取明确返回需当前 profile；执行门禁保持；14 项当前接口测试及原 Store 无发送迁移预检通过 |
| SDK 在首次交付前截断刚请求的完整索引，Main 连续重复读取 | 使用 SDK 原生 preserve_recent=1，最近工具反馈完整交付一次；6 项 SDK 测试和 3 项恢复测试通过，后者含 14 种进程中断子场景；原 Store 无发送恢复完成且费用不变 |
| 宿主往合法 generation.changes 注入旧身份字段，两次生成请求被拒 | 只对传统完整生成绑定旧字段；8 项定向用例含真实 SDK/Mock 回归通过，重建物理配置逐项相同 |
| 固定搜索 L0 泄漏内部 knots，未直观汇总原停止原因 | 设置改为努力摘要及精确原值查询，保留指标、来源、成本和全部结构观测；7 项定向测试及原数据只读核对通过 |
| 高层 Schema 未公开原 8000 回调上限，Main 请求 8192 | 投影真实冻结 maximum 并返回精确字段/请求值/上限，不截断不加限；7 项高层测试及 1 项 SDK 回归通过，Main 随后自主改为 8000 并实际执行 |
| Main h47 要求比已用 fine 更密，但高层枚举无法表达 | 增补 very_fine17，保留旧 3/5/9；8 项定向测试通过，生产 correction_basis 的三通道秩实际为 9/15/27/51，冻结网格及结点额度不足时拒绝 |
| h49 文字要研究另两工况，但实际 V4 请求仍绑定正高 | 多工况 Schema 必选 condition_id，缺失或不匹配在 Worker 前明确反馈；复用原工况候选查找的只读分支，提供匹配候选和合法源供 Main 选择，缺失才提供原初始化准备；9项高层、4项SDK/控制回归和1项已有候选复测通过，批次重叠 |
| h51 计划逐区间独立控制，却误认为换Direct方法会自动改变参数化 | 澄清Direct/T1共用搜索；提供明确control_grid档位，派生30个有效区间/90维，保留旧档位和上限；修正Provider投影丢失努力字段说明；11项高层测试及1项双方法编译复测通过，无真实Provider或Worker |
| 三项Replay完成后，联合资格视图反复解码约1GB原始分析数组 | 复用原Store哈希校验字段投影，只读取原有7个元数据字段及候选身份；124份工件/107组候选逐项完全相同，原联合资格仍通过，相关反馈回归1项通过；安全边界绑定b8dd55a，85条新增数学结果、3项独立验收及全部费用保持，无重放 |
| Main h55正式SELECT三工况结果时，高层绑定器误要求候选ID完全相同 | SELECT列表改为复用原joint_assessment绑定共同结构；所有原物理、工况、验收、回执和读取门禁保持；7项回归通过，真实三证书只读绑定通过且缺失/重复工况仍拒绝；实现4c78de6安全绑定，无额度追加或仿真重跑 |
| h55重提SELECT后，下游推断准入仍把多工况引用与单一根任务比较 | 仅允许已通过原严格joint_assessment的精确所选成员保留各自冻结任务身份，要求根候选一致，非成员仍按原任务检查；7项相关回归及补充完整提交/非成员拒绝复测通过；真实三证书绑定+observed_task_pass准入只读通过。此前只读绑定测试遗漏此后续链路已补正。2542a83安全绑定，未退费或增额 |

初始接口实现累计 72 个定向用例通过，包括修正夹具后的历史 V2 用例。以上批次存在重叠，不相加冒充互不重复的测试数。扩展运行的另外 4 项历史恢复用例未通过：3 个旧夹具缺少现行数学授权，1 个依赖本克隆未包含的历史数据库。日志完整保留，未削弱生产准入，也不声称整个仓库测试全部通过。

三项独立Replay实际运行于59429b9；收尾b8dd55a仅优化元数据读取，4c78de6和2542a83修复高层SELECT绑定与精确成员推断作用域。它们没有改变science/profile、任务、求解或验收，原结果的实现身份和全部工件保持。数学结果也各自保留真实执行提交，未改标签为最后冻结实现，未借此使旧T1满足当前实现的T2匹配要求。

## 原 Study 和资源授权

原 h43 STOP、39 条结果、2244 个封存 artifacts 和原费用均为只读核实后续研。初始真实账本为 Provider144/152、公共操作134/569、Replay0/18、数学累计58且无累计次数配额。旧冻结实现 d9b357f 与起始交付提交7bf449f不同，未将二者混用。

用户先明确批准 scope d1d0a7f0 的普通推送、原 B3 nonpass 迁移和 Provider152→176，随后明确授权睡眠期间监督、必要有限资源增加及接口修复。依据后者，原机制先一次性加 5 次至181，对应 3 次 SDK 索引交付故障和 2 次宿主身份注入故障占用的机会；全部费用仍保留，未退款或重置，也没有滚动自动续额。Main h48 明确选择的同结构三工况控制细化实际使正高工况过线后，剩4次探索不足以覆盖另两工况及通过后的3次新 Replay（保护收尾禁止启动新 Replay）；因此再一次性增加8次至189，限定于该已选有限验证及可能的独立 Replay，保留12次收尾，不自动续额。实现2431e68、profile和全部已完成证据保持原身份。最后12次收尾保护保持，Main/Reporter 共用账本，公共操作569和 Replay18的上限均未增加。

首个负低 Replay 实际通过后，原流程自动调用Reporter并计费第175次。上一轮剩余请求估算漏计了这种自动解释；当时只剩2次探索，却还需两工况Replay Main请求及最多两次原自动Reporter。依据同一用户授权再精确一次性+2至191，仅覆盖既定验收收尾，不开启新的结构或控制研究阶段。该次实现59429b9及profile不变，原12次保护、public569/Replay18上限和所有费用保持；未使用的额度不收费。

原无数学累计配额保留，每个 Worker 的冻结工程限制仍生效。外层自有监督 Job 为使 Main 已选择的有限研究完成，由30分钟/4GiB有限扩至2小时/8GiB；单 Worker600秒、实际任务、数值方法及验收规则保持。资源接管、内存增加、每次接口实现授权和绑定证据均在交付目录。

旧账本 `worker_calls` 字段不用于计数本轮 Native 数学 Worker；实际数量来自保存的分析及 `boundary.worker_started/termination_confirmed`，数学累计另由 `mathematical_evaluations` 计量。独立 Replay 的后端额度与 T1 的数值 rollout 成本也分别报告，不用旧字段的零值掩盖真实计算。

最终审计逐项复核原2244个 artifacts 的哈希、原317条调用状态及费用、旧结果/计划前缀、候选、原STOP和源代码绑定。合法续研会追加原数据库，因此初始整个数据库哈希不再要求相等。最终科学结算和是否有未封口调用见报告开头及 continuation-final-audit.json；原 Store 仍是权威，导出的 ZIP 是本地证据包，不是另一套运行 Store。

没有强推、合并基础分支、修改历史封存证据、启动 PPO 或新增科研架构。原独立任务 evaluator 仍是通过判断的唯一来源；单工况 Native 模型过线不能替代三工况同一结构的联合独立验收。


## 逐次实际 Provider 请求

编号为续研以来新增请求顺序，含监督器只读 Reporter 核对。原 Store 保留所有 wire 和响应；表中 tokens 来自 Provider usage，不用字节估算。

| 新序号 | 角色及阶段 | 工具或回复 | 输入 bytes | prompt tokens | completion tokens | L0 数组扫描命中 |
|---|---|---|---:|---:|---:|---:|
| 1 | conversation / exploration | evidence_read:success | 88315 | 18190 | 43 | 0 |
| 2 | conversation / exploration | evidence_read:success | 89191 | 18279 | 43 | 0 |
| 3 | conversation / exploration | research_plan(diagnose):error | 89999 | 18353 | 608 | 0 |
| 4 | conversation / exploration | research_plan(diagnose):error | 98906 | 19300 | 641 | 0 |
| 5 | conversation / exploration | research_route(generate):success | 106322 | 19999 | 24 | 0 |
| 6 | conversation / exploration | research_plan(generate):error | 112451 | 20940 | 577 | 0 |
| 7 | conversation / exploration | research_plan(generate):error | 120228 | 21717 | 561 | 0 |
| 8 | conversation / exploration | research_plan(generate):success | 127945 | 22484 | 560 | 0 |
| 9 | conversation / exploration | research_route(diagnose):success | 138960 | 24270 | 25 | 0 |
| 10 | conversation / exploration | research_plan(diagnose):success | 134665 | 23553 | 739 | 0 |
| 11 | conversation / exploration | research_plan(search):success | 155828 | 26740 | 743 | 0 |
| 12 | conversation / exploration | research_plan(diagnose):success | 209152 | 38134 | 762 | 4 |
| 13 | conversation / exploration | research_plan(search):error | 216498 | 38292 | 800 | 0 |
| 14 | reporter / exploration | text/report | 106370 | 28442 | 720 | 0 |
| 15 | conversation / exploration | research_plan(search):success | 248986 | 44870 | 834 | 0 |
| 16 | conversation / exploration | research_plan(diagnose):success | 246925 | 46167 | 840 | 0 |
| 17 | conversation / exploration | research_route(generate):success | 262224 | 48125 | 24 | 0 |
| 18 | conversation / exploration | research_plan(generate):success | 260378 | 47673 | 1146 | 0 |
| 19 | conversation / exploration | research_route(diagnose):success | 277855 | 50735 | 25 | 0 |
| 20 | conversation / exploration | research_plan(diagnose):success | 267015 | 48189 | 734 | 0 |
| 21 | conversation / exploration | research_analysis:success | 285182 | 50770 | 131 | 0 |
| 22 | conversation / exploration | research_plan(diagnose):success | 278386 | 47297 | 824 | 0 |
| 23 | conversation / exploration | research_analysis:success | 289357 | 48607 | 137 | 0 |
| 24 | conversation / exploration | research_analysis:success | 295916 | 48295 | 132 | 1 |
| 25 | conversation / exploration | research_plan(diagnose):success | 298220 | 48564 | 685 | 1 |
| 26 | conversation / exploration | research_analysis:success | 314253 | 51002 | 137 | 1 |
| 27 | conversation / exploration | research_plan(diagnose):success | 309550 | 49422 | 794 | 0 |
| 28 | conversation / exploration | research_analysis:success | 320932 | 50850 | 138 | 0 |
| 29 | conversation / exploration | research_route(physical_replay):success | 332558 | 54081 | 26 | 0 |
| 30 | conversation / exploration | research_plan(physical_replay):success | 323124 | 52311 | 559 | 0 |
| 31 | reporter / exploration | text/report | 23289 | 6638 | 531 | 0 |
| 32 | conversation / exploration | research_plan(physical_replay):success | 332796 | 53058 | 552 | 0 |
| 33 | reporter / exploration | text/report | 34798 | 9749 | 565 | 0 |
| 34 | conversation / exploration | research_plan(physical_replay):success | 360214 | 58398 | 556 | 0 |
| 35 | conversation / exploration | evidence_read:success; evidence_read:success; evidence_read:success | 357885 | 57703 | 92 | 0 |
| 36 | conversation / closeout | research_plan(select):error | 405257 | 68191 | 697 | 0 |
| 37 | conversation / closeout | research_plan(select):error | 388682 | 63868 | 760 | 0 |
| 38 | conversation / closeout | research_plan(select):success | 399145 | 65171 | 721 | 0 |

本轮 Provider 合计报告输入 1,508,427、输出 18,486 tokens，其中报告缓存命中 51,456 输入 tokens；完整输入体累计 8,707,757 bytes。缓存命中仍包含在报告的 prompt 总数内。


## 交付与复核入口

- `final-validation-summary.json`：可直接审阅的最终费用、结果及资源摘要。
- `selected-design.json`：原正式选中结构的完整物理参数、三份保存控制源、冻结工况及验收值，只读导出，不重放。
- `formal-main-progress.json`：逐次真实请求、工具参数、反馈、usage、各数学结果设置、实际成本及来源。
- `formal-search-outcomes.json`、`actual-main-compilation-validation.json`：两轮共享结构搜索的工况对照与 Main→Native 实际编译核对。
- `actual-reporter-delivery-validation.json`：监督器专门的数学 Reporter 交付及来源核对；Replay自动Reporter的真实wire另见逐次请求审计。
- `actual-main-control-refinement.json`、`actual-condition-handoff-validation.json`：高层工况、分辨率、控制源到真实 Native Worker 的对应及安全交接。
- `three-sampled-witnesses-validation.json`、`actual-independent-replay-validation.json`：同结构三个采样模型过线控制、实际独立验收与输入源核对。
- `metadata-projection-validation.json`、`joint-selection-binding-validation.json`：真实工件元数据逐项相等及SELECT绑定、缺失/重复工况拒绝的只读核对。
- `high-level-worker-validation.json`、`isolated-high-level-worker-evidence.zip`：隔离工程 T1/T2 与多起点调用链。
- `continuation-final-audit.json`：原2244个 artifact、原317条调用和费用、最终引用完整性与无悬挂状态。
- `formal-main-validation-evidence.zip`、`formal-evidence-export.json`：新增原始证据与哈希清单，仅本地交付，未推送原始大包。
- `softrobot-agent-high-level-changes.patch`：从7bf449f至最终交付的补丁。
- `delivery-sha256.json`：最终交付文件校验清单。

仓库分支为 `codex/m1-knowledge-physics-reasoning`。代码与非秘密报告普通推送；未强推或修改基础分支。每次修复绑定及有限资源追加的详细身份保留在本地交付 JSON 和原 Store 中。

本仓库只包含报告和精简账目。文中大证据包、逐次wire审计及校验文件为用户本地交付，原运行Store仍是权威；不把本地文件名误作本仓库文件。
