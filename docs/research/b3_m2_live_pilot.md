# B3 M2：有限真实自主科研试点

2026-10-26（Asia/Shanghai）。状态：**B/C 各一次正式自主研究均已合法 STOP，均未找到完整物理通过解。**
C 在同一参考结构上，通过 native 控制搜索及独立回放将保持峰速降低 **21.09%**，仍超限。
没有结构修改、T1 或 T2 数值执行，不能宣称结构联合设计收益或 T2 科研指导有效性已得到验证。

| 最佳完整独立结果 | B：参考 NMPC | C：native 优化序列独立回放 | 硬阈值 |
|---|---:|---:|---:|
| 终点误差 | 3.148373 mm | 4.515550 mm | ≤10 mm |
| 保持最大位置误差 | 6.038027 mm | 6.675937 mm | ≤10 mm |
| 保持峰速 | 0.111373944 m/s | 0.087887791 m/s | ≤0.020 m/s |
| 完整有效性 / 张力 / solver_errors | 均通过 | 均通过 | 原冻结协议 |
| 完整任务验收 | valid_failure | valid_failure | 全部硬条件同时通过 |

B 的模型请求主要消耗在读取和调用修复；C 成功执行了有界控制搜索，但没有找到停稳解。
结果只能比较本轮最佳已找到控制，不构成结构不可行、全局控制最优、统计显著或 Benchmark 排名。

基线 `feat/b3-t2-guided-design@fcdc0a4f47dea98afe3a355f491b15b1f7a51a6d`。
研究分支 `research/b3-m2-live-pilot`，复用原 M1 工作树与原 Store，保留 M1 分支和其他工作树。

用户附件 `68af1110-5541-410b-86e2-cc47f5b933b8/已粘贴的文本.txt` 及本次消息明确授权
M2 两组各一次真实研究、最小必要修复、原恢复机制、commit 和普通 push。
不追加第二次 Study，不重置预算，不把 B 本次结果注入 C，不替 Agent 选择科研方向。

## 冻结与运行入口

| 条件 | B | C |
|---|---|---|
| 原 Study | b3-t2-050-b-v2-draft | b3-t2-050-c-v2-draft |
| resolved_identity | 4a623b709812f4787383e4386a7d0deaec9ed76cb370f11312951d323423f554 | 4de5e88479238e3e5f478d8251aaf2a6951ec7fa7d6d06f379aba15f93a03093 |
| 原冻结实现 | dc773ea20aad9146a4f2080ec64b2d65b6b7d99f | 相同 |
| 结构 | 固定共同参考 | 至多两种独立物理结构，含共同参考 |
| Provider / 公开操作 / 数学 | 32 / 80 / 22 | 相同 |
| 共享独立物理 / NMPC / 完整回放 | 4 / 2 / 2 | 相同；每结构至多 1 NMPC + 1 回放 |
| 保护 Provider / 公开操作 | 4 / 6，包含在总额 | 相同 |
| native callbacks / iterations / knots | 8 / 2 / 4 | 相同 |
| PPO | 0 | 0 |

原 Store：本工作树 `runs/research/<study_id>`。初始全部使用为零、无 pending 请求或占用。
科学源码哈希、core 哈希和 Host compatibility 与原冻结实现全部一致，未重新 prepare、复制或重写 SQLite。
三条共同历史背景已存在，仅为背景，不作为本轮结果或控制种子。

NMPC **重规划/求解间隔 0.1 s**，horizon=10、substeps=1、max_iterations≤120、tolerance=1e-6。
控制与验收采样仍为 0.01 s、MuJoCo 积分仍为 0.0005 s；这三个时间尺度分开记录。
冻结 B3 0.50 s、目标、初态、保持窗口、位置/速度硬阈值和张力界保持不变。

原 C3 request-feedback Handoff 准入来源：
`evidence/c3_handoff_admission_20261025` 中
`aaaf83b7e9f8e2c8e573e42cc7bcef163197d83edcc9537322b97bfee4ac4a88`。
已用原 archived 校验归档及 member 身份，真实请求、反馈、切换与新进程恢复均 passed。
本轮两组分别通过原 formal_study_authorization/scope_identity 登记，准入引用原证明及本轮授权。

环境：使用原 s135 Python，numpy 2.4.6、scipy 1.17.1、casadi 3.7.2、MuJoCo 3.13.0、
CVXPY 1.9.3、CLARABEL 0.11.1，三种数值线程均为 1；只做导入检查，没有重复科学预检。
两项定向 unittest 通过（8.847 s）：原 request-feedback rotation、B/C 冻结公平配置与正式授权门禁。

持续监督：本聊天 heartbeat `b3-m2` 在明确授权后恢复，随后按用户要求改为每 10 分钟检查。
两组停止、原费用及导出核对完成后，已删除该监督任务；不追加 Study。
原始请求、响应、决策、收据、worker 和结果继续由原 Store 保存，不建立第二套日志或账本。

## 进度与恢复交接

两组原 formal_study_authorization、原 Handoff 来源和共同参考均已登记：

| 原 Store 记录 | B | C |
|---|---|---|
| 本轮 scope 授权 | f70b0237cf570d86ad20d58773ed9c664e0d9b765e79dda4f3dbd536f83d94b6 | 0d45186f5fa6bc141a1396e56deaf13dcd3aeec2d906e117549f1278025cd9ce |
| 有来源的 Handoff 准入 | 8e3290af4cd224b524853c0fa8d9d8a201cc227033cbd2d458554b1431194038 | e79f10ddb3c2bbbc9e1084e0ecd9c2f6332d1917df8ad7594d246bccf247e72a |
| 本 Study 共同参考候选 | c884086ce2fc5a2ddfe61a19bf67fab01dcc440e0329be0a7ae317855809d2a7 | 123ba9d4accff3a08b8a7eaab7303f364ffaf50014174fc0d3320a37f366fa33 |

共同 physical_design_identity 为 `676cfa6149fd3f07deea5dca853fcb2ff990def0df7fcd46d79f8ed0a486ec04`。
这是原生成器的无科学结果工程种子，没有独立物理执行，没有复制历史控制。
后续不重复 prepare/bind、重置身份或重新生成种子。

`runs/m2_run.py` 是本轮操作脚本，仅在原 dispatch 前核对冻结求解设置、final fidelity 和
C 每结构独立物理机会；核对结果直接保存到原 Store event。没有生产源码修改、替代 Agent、
求解器、执行器、账本或证据系统，也不为 Agent 指定结构或研究方法。
原本各组 `execution_instructions` 已要求这些监督检查，脚本未改变冻结科学实现。

正常运行使用原 s135 Python 执行 `runs/m2_run.py <study_id>`；其内部调用原 converse，
session_handoff=True、handoff_request_bytes=160000、pause_exploration_remaining=4。
恢复前检查进程、原账本和未知发送；优先原 recover/restore-only，不重复 launch。
到达原 supervisor_pause 后，监督者核对剩余额度、配对反馈和原快照；
若仍能在原额度内继续，可用同一操作脚本加 `--reviewed`，仅取消已经完成的监督复核暂停。
它要求存在原暂停记录、向原 Store 记下复核和 additional_budget=0；原 4 次 Provider 保护及所有科学门禁保持。

## 自动审批阻塞

两次提交同一隐藏后台启动操作均在 shell 进程创建之前被 auto-review 拒绝。
没有运行凭据加载、TCP 预检、Provider 请求或后台 study 进程。
第一次拒绝理由为尚缺向第三方地址发送私人 study 提示与仓库数据的明确授权。
随后只读核对了原冻结出口、数据包字段和本轮 scope，并经 GitHub get_repo 确认仓库 visibility=public。
第二次审批仍要求可信用户明确授权**具体地址与 payload 范围**，不接受助手对现有授权的解释。
原拒绝要点：

> The transcript does not contain trusted user authorization for that specific destination and payload.

原冻结 Provider 为 `deepseek-flash`，唯一模型出口为
`https://api.deepseek.com/chat/completions`。
请求范围为冻结 B3 任务、必要结构与控制参数、三条显式声明的共同历史背景、工具定义和本 Study
实际工具反馈；API key 仅供正常认证，不进入提示词、证据或日志；不检索其他工作区文件。
用户随后明确回复“批准”，已再次绑定原 scope：B 授权
`96ef52443b36b18dc30327a4250d67cea40bbe86cc46ec8c359a92d4ab991ccf`，C 授权
`adedc05beba95308bc65cb2b0b1f17b642d208ad6b383ad8968cabe339701369`。
同一启动操作重新提交后获准，凭据可用、原出口 TCP 连通，B 进程 PID 515372 已启动。
没有换出口、间接绕行或额外预检模型请求。之前的拦截不是网络故障或科学失败。

## 科研结果

B 早期真实交付抽查：首请求 wire 为
`63c6c4a21bfc049bc0bda4bc00116a3d5cab8ff08ac8adde1e50663a2165724a`，70,776 bytes。
后续请求 #2–#4 仍完整包含三条 research_history 结论及原 Study、MODEL_WITNESS / PHYSICAL_OBSERVATION、
task_match=false 与 L1 指针；0.35 s 旧 CONIC −0.2、回放速度 0.2741264353 m/s、
旧 NMPC 速度 0.1817335826 m/s 均进入尾部 CURRENT_RESEARCH_PACKET。
frozen_replan_period_s=0.1 可见，没有把旧结果赋予本轮验收身份。

Agent 首先公开读取历史与必要配置，自主选择固定参考上的 NMPC 控制实测，未先调用 T1/T2。
其可检验假设是：原控制配方在新 0.50 s 内满足位置和保持速度；若失败，再依据绑定指标选择剩余控制机会。
三次 execute 请求的 decision.selected_candidate 缺失或为 null，被
DECISION_CANDIDATE_MISMATCH 拒绝，没有科学启动；第四次自行修正后进入第一次 NMPC。
原错误与公开操作 / Provider 成本均保留，没有监督者改写模型提交或重置预算。

首次运行原始进程记录（现均已退出、结果已结算）：B 主研究进程 PID 341580（Windows venv launcher PID 515372），
execution owner `b3-t2-050-b-v2-draft-exec-773fd76849c64c3c`，原 worker_lifecycle PID 607404，
实际控制子进程 PID 736960。原 backend execution `630458fcbd944389a602244dfdd5a42d`。
首个在线求解在 t=0 返回 iteration_limit_feasible，plan_accepted=true、solver_failed=false、
optimization_nonconverged=true，100.7528732 s；此初始检查点保存了 0–0.09 s 的 10 条控制更新。
这是实际数值状态，不是工程错误；后续完整五次求解见下文，未调整迭代或任务阈值。
这些 PID 仅用于原执行溯源；B 已 STOP，不得再次恢复。当前监督对象为下文 C。

### B：首项独立物理结果与反馈

结果 `137dd4b22b2969ed34ff611072329375e8a9edf6e483f87710561f9cdb38ba75`，
独立验收为 **valid_failure**。完整 0.50 s、保持覆盖 6 点、张力合法、数值有效、solver_errors=0。

| 硬指标 | 本次实测 | 阈值 | 判定 |
|---|---:|---:|---|
| 终点位置误差 | 0.003148372648914904 m | 0.010 m | 通过 |
| 保持最大位置误差 | 0.006038027478928508 m | 0.010 m | 通过 |
| 保持峰速 | 0.11137394399884916 m/s | 0.020 m/s | 失败 |

原 simulation_wall_s=476.266 s（7.94 分钟），50 个更新中只在 t=0/0.1/0.2/0.3/0.4 s 求解，
各次 update_wall_s=100.753/92.406/91.659/91.923/94.676。
五次均 iteration_limit_feasible、optimization_nonconverged=true；返回计划被接受，solver_failed=false。
不能据此声称优化收敛、实时求解或充分控制最优。该离线任务不要求实时，不把墙钟 deadline_misses 当作物理失败原因。

真实 Provider #6 是 Reporter；#7 主请求 wire
`918586272d39efa02276f55c4cc9a0bc2e53f913807f3b669fc2a8fc65c42b9b`（133,979 bytes），
已包含新独立结果身份、holding_speed 主违反量 0.11137394399884916 / 0.02、原 action_trace 和非权威解释。
随后 Agent 选择瞬时制动诊断：model_source=mujoco、saved_state、当前 execution、update_id=44。
本次深入审计纠正早期摘要：operation 字段本身合法，也不是缺少某个 native 方法字段；
`instantaneous_braking_v1` 未注册为 MuJoCo native operation，属于不支持的模型—方法组合。
原 Schema 以 MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE 拒绝，数学启动和计费均为 0。
原错误不改写为科学结果，也不免费补造一次正确调用。

后续真实行为是多次读取当前候选、控制观测、历史和原 Plan，并通过 SDK retrieve_context 搜索生成参数。
读取审计发现：候选 full 为单行长 JSON，SDK 正则 retrieve_context 命中时仍返回整行，随后可再被 offload；
一次切换后 Agent 再用旧 SDK offload reference 收到 `reference not found`（原反馈事件 198）。
原 Store 的 evidence_read 与 pending_feedback_delivery.original_result_query 仍可定位稳定依据，
因此保留这一数据获取限制，不把它直接归为数值故障或静默修改上下文机制。
当前已交付新物理失败；未发现网络或未结算 worker 故障，不因 Agent 读取低效就改变提示或替其提交新控制。
这是后续审计需评估的资源效率与信息获取行为，尚未宣称其找到第二项有效科研方案。

### B：原预算复核后继续

Provider=23 / 32 时到达原 request-feedback 监督暂停（事件 422；
`178368b6cab2ca98c0595af4af5abf7c2f8042dc12bb5829ecfa7ab129e4f6fd`）。
无 pending、无未知发送、无未消费响应或运行中 worker；原 restore-only 在新进程验证通过，未发送请求。
剩 Provider=9，包含原收尾保护 4；公开操作剩 41，数学剩 22、NMPC 剩 1、物理剩 3。
监督者完成原预算复核后继续同一 Study，没有追加任何额度、指令、科学控制种子或研究方向。

Agent 此时已自主提出 native 末段张力修正，尚未执行成功：
diagnose 与 CONTROL_SEARCH intent 不匹配；native 保存状态准入条件不满足；
随后 evaluation_requests=300 超过 8、iterations=8 超过 2，均由原门禁在计算前拒绝。
这保留为调用与预算理解错误，不把被拒的 300 回调记为已执行，也不放宽冻结上限。

### B：完整研究结束审计

最终合法 STOP 原 Plan 为 `d41a059183f6cb4ab6fb15086d5d742919aa433471e531e3ed6b1f4a3012ea51`。
模型在事件 485、518 公开读取 `/all_fresh_results`，完整索引只有上述一个独立物理失败；
事件 545 的 STOP 只引用该登记结果，事件 548 接受，最终 research_status=stopped，无 SELECT。
此前一次 STOP 引用未注册材料、一次加入不支持字段，均被原规则拒绝，随后自行改正。
没有行政替代 STOP、追加实验或第二轮 Study。

模型收到的核心内容是新 0.50 s 任务、参考结构、原 0.35 s 三条具名历史和真实新物理反馈。
实际路线为参考 NMPC → 发现停稳失败 → 尝试瞬时制动/原生末段控制修正 → 绑定控制来源未完成 → 收尾 STOP。
研究方向确实因新速度失败改变；但没有产生合法数学或第二次控制实测，不能称控制已充分优化。
未使用 T1/T2；B 本身未授予结构 T2，数学能力没有得到本组的新增实际检验。
Agent 对“没有探索预算”判断对应的是 Provider 保护/耗尽；数学 22、NMPC 1 和物理 3 仍未使用，
不能写成这些科学计数已经耗尽。

Provider 为 **31 主 Agent + 1 Reporter = 32**，32 个唯一请求均确认 HTTP 200，无未知发送或自动重试。
prompt=954,950，completion=191,321，total=1,146,271 tokens；cache hit=331,008 / miss=623,942；
reasoning=168,070（包含在 completion），金额未返回，unknown。
public operations=50，13 个原工具参数/引用错误；另有 SDK offload 读取错误。
10 次原 request-feedback Handoff，最新结果与原决策轨迹在切换后仍可见。
只有第一次 NMPC 物理启动；native 修正尝试全部在计算前拒绝，所以数学、native 内部修正积分、回放均为 0。
原 NMPC 完整物理网格为 0.50 / 0.0005 = 1,000 步，50 段已保存实际控制；无额外 native 前缀重建。

主要限制同时包括：控制 NLP 五次达迭代上限、真实停稳未通过；Agent 原生工具/引用使用和 Provider 分配低效；
长单行 JSON 与 SDK offload/切换引用造成读取阻力。不能仅据一次失败把瓶颈归因于结构，
也不能把参数修复和大量读取包装成已执行的控制优化。

已通过原 core.export 保存[完整原证据](../../evidence/b3_t2_pilot_050_b/immutable_artifacts.tar.gz)、
[账本](../../evidence/b3_t2_pilot_050_b/ledger.json)、
[原停止与结果目录](../../evidence/b3_t2_pilot_050_b/disposition.json)及 design_package。
原 archived 对归档整体和结果/STOP member 校验通过；没有覆盖之前的导出。

### B：用户追加的深入审计

**结论：独立物理失败可信、账本与 STOP 合规；后续自主优化没有实际执行。
不能把本组描述为充分控制优化后仍失败，也不能把所有后续调用失败都归为 Agent 忽视已知规则。**
此次只读核对原 Store、32 份真实请求、原反馈、冻结源码与原保存轨迹，不恢复 B、不请求新模型、不启动新求解。

第一，重算原保存观测的范数，与独立验收一致：终点误差 3.148372649 mm；
保持位置峰值 6.038027479 mm（t=0.45 s）；保持速度峰值 0.111373943999 m/s（t=0.48 s）。
原 50 个 post-step 样本覆盖 0.01–0.50 s，六个保持点齐全，engine_time 与 sample_time 最大差 3.89e-16 s。
五次求解 raw_status 全为 Maximum_Iterations_Exceeded，采用原允许的 feasible_suboptimal_update；
独立 solver_errors=0 表示无执行错误，不表示五个 NLP 收敛。
全轨迹张力峰值 **7.999945198 N**，已接近 8 N 上限；只有最后保持窗峰值为 4.387190886 N。
Agent 从末段有张力余量推断“不是 actuation-limit deficiency”缺少识别性依据，
余量既不是可用制动力证明，也不能排除更早的输入约束、求解质量或预测模型限制。

第二，**原生方法限制在工具结果中存在，但未完整交付到真实后续请求**。
原方法反馈 `f5422168ad12f74cff6dcfc8b88243db163fc87110c70324d7627d77056af880`
（事件 324）有 7,893 字符，execution_limits 在约第 6,520 字符，
measured_control_initialization 模板在约第 6,592 字符。
真实请求 #18 已切换 Session：pending_feedback_delivery 将该结果标成 summary_only，
facts 仅有 candidate/operation；execution_limits 与完整绑定模板均未进入 wire。
后续 #19–#22 亦没有这两个字段；8 次回调和 2 次更新的具体上限分别到 #23、#24 才随拒绝反馈出现。
因此，evaluation_requests=300、iterations=8 两次拒绝保护了预算，
但不能认定模型此前已经完整看见 8/2/4 后仍故意越界。
这是交付层的实质缺口，不是数学证据错误；原 L1 数据仍可通过稳定 Store 指针读取。

第三，**可明确归于 Agent 的调用与研究管理错误仍然存在**。
请求 #3、#4、#5 中均已包含 decision.selected_candidate 的明确修正反馈，模型仍反复漏填或设 null；
累计四次 DECISION_CANDIDATE_MISMATCH（含后期初始化）。
L0 始终明确说明 measured_nmpc 的 source+parent 绑定步骤，模型却在来源未绑定时提交原生控制修正，
直到 #25 才尝试 initialize_control，且再次漏填选定候选。
此外有不支持的 MuJoCo 瞬时制动组合、保存状态选择不合法、字段选择使用点路径、
STOP 引用未注册证据和添加不存在字段等错误。
这些区别于合理但最终失败的物理假设，确实消耗了有限 Provider 机会。

第四，**长对象读取与切换增加了额外阻力**。
候选 full 为长单行 JSON，SDK 按行正则命中仍返回整行；随后再被 offload，难以只取需要的结构参数。
切换后两次旧 SDK reference 失效（真实 #10、#17 返回 reference not found），
但原 Store 查询仍合法；这是临时检索引用寿命问题，不是结果丢失。
31 次主 Agent 请求中，18 次只做读取/检索（包括必要的初始历史读取和收尾，不把全部视为浪费），
5 次数学提交全部被拒，实际仅 1 次 NMPC 科研执行。
47 个模型原始工具请求与原账本 50 次公开操作口径不同，后者还含原执行内部操作；两者不混记。
32 次 Provider 全部 HTTP 200，无网络故障；失败主因不是网络中断。

第五，**科研解释的边界**。
模型确实收到新速度失败并改变问题方向，后续原生修正方向有可检验性；
但没有得到任何修正后物理数据或 T1/T2 数值，因此不能证明固定结构不可行、T2 无价值或结构修改更好。
32 次 Provider 用尽时仍剩数学 22、NMPC 1、回放 2、共享物理 3；主要执行瓶颈是模型调用预算和接口使用，
物理层面则仍未区分求解不足、预测失配、控制时序和结构能力。
Provider 实际接收计时合计 1,104.792 s，独立 NMPC 物理执行计时 476.266 s；
这两种计时与 shared ledger wall 不另行重复累加成“总科学计算”。

修复建议按实际证据排序：把当前方法的少量 execution_limits 与明确控制来源缺项保留到 L0/切换摘要；
让长对象的按需读取维持结构化小范围，切换时不把旧 SDK 引用作为唯一入口；
使行动相关的必填字段和不支持的模型—方法组合更早给出精确提示。
这些均应复用原方法视图、Handoff 和 evidence_read，不新增记忆、优化器或 Agent。
本次审计未改变正在运行的 C 的冻结提示/交付条件，也未向 C 注入本审计或 B 结果；
本轮结束后再根据完整 B/C 证据决定最小修复，不能为改善 B 结果恢复其已封存 Study。

### C：启动隔离与早期决策

B 全部进程和请求结束后才启动 C（Windows launcher PID 540692）；复用原独立 C Store、共同候选和三条背景。
C 主进程 PID 354640，首次 execution owner `b3-t2-050-c-v2-draft-exec-04c61298c33a4331`，原 launch_intent=true。
首真实请求 wire `842f3e8ab65a02acef2020f443216fd16ad33a75b1896dcf81e4bc81a0406036`，71,628 bytes；
实际序列化正文不存在本次 B 结果 `137dd4b2…`，历史仍仅来自 c3-b-100ms-20261025，求解间隔 0.1 s。
标准 B 导出没有 summary.json，不会新增原 experiment_preflight 所扫描的全局历史摘要。
Agent 自主先测同一参考结构 NMPC，没有先做 T2 或预先改结构。

早期三次请求缺少顶层 candidate 或 decision.selected_candidate，未启动科学计算。
其中前两次被本轮操作脚本过早读取缺字段转成 KeyError；这是监督接口的工程缺口，
已局部修正为缺字段直接交还原 dispatch/Plan 验证，原科学准入不放宽、原错误与费用保留。
C 在修正前已自行补齐参数进入首次 NMPC，未中断其控制执行或更改正在运行的模型程序。
脚本修改只影响后续进程恢复时的无效输入错误交付；生产源码和冻结配置均不变。
Agent 所述“旧目标/阈值不同、速度成本是新元素”尚不符合冻结背景：新信息主要是 0.35→0.50 s 时域，
旧目标与硬阈值不能仅从 task_match=false 推断已改变。保留原自然语言误判，不改写其科研方案。

用户请求 B 深入审计期间，C 到达原 Provider=23/32 的 request-feedback 暂停（事件 407，
`6c4a0459cb5278421604ec22518c0edbb1263c1d1fe279864b89f626e908158c`）。
已完成首次独立 NMPC、1 项数学分析及 1 次独立回放；详细结果留待 C 结束统一核对。
监督者确认原进程退出、无 pending/占用/未消费响应，完成原 restore-only 验证，
使用同一 C Store `--reviewed` 继续原剩余 9 次 Provider（含保护 4），additional_budget=0。
Windows launcher PID 745260；没有将 B 新审计内容传入 C，未改变其冻结提示、科学实现或任务。

### C：真实控制搜索、独立回放与停止审计

C 首次 NMPC 独立结果为
`db55b0733c50e7f624db606b8b0076df07abf367e5086dc20306f45835d7c93f`，
backend execution `6b28a10f06d54082b8929148418a346f`。
完整物理网格、参考结构与控制配方逐值相同，因此三个硬指标与 B 基线逐值一致；
这是 C 自己的新执行和费用，不是将 B 结果或控制拷贝成 C 证据。
原 simulation_wall_s=473.671 s，五次在线求解仍均 iteration_limit_feasible。

模型收到本组速度失败后，自主选择从实测 NMPC 张力构造同候选完整控制源，
再调用 **mujoco_direct_control_v1**。其假设从早期末段脉冲提案，经合法性反馈修正成实际执行的设置：
标准零初态，correction_window=[0,0.5] s；knots=[0,0.38,0.45,0.5] s；
四维活动系数 [9,10,13,14]；coefficient_limit=2 N、difference_step=0.01 N、initial_radius=0.1 N；
evaluation_requests=8、iterations=2，未超过冻结上限。
一次选择的修正窗口与起始 checkpoint 不一致，返回 not_applicable、额外数学计费 0；
模型随后选择从初态开始的完整窗口，才获得成功计算。

唯一计算完成的分析为
`7cee4f6b079fbb8fd921b48a18c3f8567aaaddbdd9638ecf86c78664f9cf4f12`。
该方法使用 **MuJoCo native** 的同任务、同输入盒、同离散样本的有界序列重优化，
不是 GVS 仿射 CONIC，也不是结构 T2、严格最优值或全局梯度。
原 cost / internal_calculations 确认：8 个完整 rollouts、8 个 evaluation callbacks、
6 个有限差分探测、2 次已启动更新、**仅 1 次完成的 response step**、1 次模型构建、
809 次 forward_evaluations、**8,000 个 MuJoCo 积分步**；kernel_wall_s=0.6715322 s。
原账本按本方法记 1 次分析，内部回放和积分另外完整列出，不解释为零物理计算。
8 个 callback 用尽后停止，stop_reason=evaluation_request_budget，不是搜索收敛证明。
最优已采样点是第二次更新中的 **finite_difference 探测点 native-rollout-6**，
不是第二次完整响应更新；原排序允许选取该真实已评价点，全部成本保留。

产生的当前候选控制序列为
`30994c15d28a3b1b434d1f4cdc252199773e3eb4c9888a4b47b3870ac8d004ea`。
Provider 请求（事件 358，wire
`c703e54ad6ddd50c45faf314a77b6eb1e0dc0a66f9e9941eb1317142cfb556c7`）
已带真实 native 结果和明确的 physical_replay 控制交接，task_acceptance 仍为 unmeasured。
Agent 随后自主对这个精确序列做独立完整回放，而非由监督者代选。

独立结果为
`0f87cf01869d1892043a8c52f3893c9b0b433ff305f769d2fbb3ad28a991baca`，
execution `24ff4d31432a47a89c89cac1c4dee502`；完整 1,000 个物理步，原验收 **valid_failure**。
终点误差 0.004515550349894086 m、保持位置 0.006675937086453473 m 均通过，
保持峰速 0.08788779126447174 m/s 仍超 0.020 m/s，六点覆盖、张力、数值有效和 solver_errors 均通过。
native 最优点预测与这个精确序列的独立回放，以上三个保存指标逐值一致。
这是同一 MuJoCo 物理模型的控制见证核验，不是跨模型、硬件或鲁棒性验证。
回放反馈进入后续真实请求（事件 413，wire
`eb77bed12429e5ad851da451230281749cccb9ef064c62d34ed31c697bbc92a1`），模型确实看到新速度失败。

C 最后继续尝试 native 控制请求，其中 80/300 callbacks 越过 8 的上限被拒；
另一次起点与窗口不匹配返回 not_applicable，不产生新数学计算或免费积分。
进入原 Provider 保护后，公开读取 `/all_fresh_results` 的三个精确结果，并全部引用 STOP。
合法停止 Plan 为 `1255f5a40c63c0c77fdb0772842a9f4a2a68d82344fe66bf562624e24bf71c3f`，
模型事件 490 提交，后续原 receipt 接受；research_status=stopped，无 SELECT、无未知工作。

STOP 的自然语言仍有需保留的科研误判：
“方向转移但幅度没有转移”与保存指标逐值一致不符；真正未实现的是达到硬速度阈值。
“reproducible measured cause / braking authority”也超出了本轮证据，
当前只识别出 holding_speed 活跃失败指标，尚未证明物理制动力上限或唯一失败机制。
它把三项 fresh 索引的一项称作 decision brief，而真实第三项是首次 NMPC；
实际 supporting_evidence 的三个 ID 正确且完整，所以原 STOP 引用门禁通过，但自然语言索引解释不准确。

C 用量为 **26 主 Agent + 3 Reporter = 29 / 32**，所有唯一发送确认 HTTP 200，无重发或未知结果。
prompt=849,794、completion=185,622、total=1,035,416 tokens；cache hit=289,024 / miss=560,770；
reasoning=162,576（包含在 completion），金额 unknown；Provider 接收计时合计 1,140.296 s。
9 次原工具错误记录、9 次已提交 Handoff；错误原样保留，未给额外 Provider 或科学额度。

已通过原 core.export 保存[完整 C 证据](../../evidence/b3_t2_pilot_050_c/immutable_artifacts.tar.gz)、
[账本](../../evidence/b3_t2_pilot_050_c/ledger.json)、
[停止与结果索引](../../evidence/b3_t2_pilot_050_c/disposition.json)和 design_package。
原 archived 校验了整个归档以及 NMPC、native 分析、独立回放和 STOP 四个 member，与原 Store 相同。

## 最终资源与对照解释

| 实际状态与费用 | B | C |
|---|---:|---:|
| 状态 | 已合法 STOP，无通过解 | 已合法 STOP，无通过解 |
| 首次真实请求—STOP（Asia/Shanghai） | 08:16:46—08:50:33 | 08:57:07—09:30:44 |
| Provider（主 Agent + Reporter） | 32 / 32（31 + 1） | 29 / 32（26 + 3） |
| 公开操作 | 50 / 80 | 38 / 80 |
| 数学分析原账本 | 0 / 22 | 1 / 22（native 控制分析） |
| 新 T1/T2 模型准备 / CONIC / dual-face | 0 / 0 / 0 | 0 / 0 / 0 |
| 独立物理启动 / NMPC / 完整回放 | 1 / 1 / 0 | 2 / 1 / 1 |
| NMPC 在线求解 | 5 | 5 |
| 独立物理积分步 | 1,000 | 2,000 |
| native 内部 callbacks / rollouts / 积分步 | 0 / 0 / 0 | 8 / 8 / 8,000 |
| native 更新启动 / 完成 response step | 0 / 0 | 2 / 1 |
| native 搜索模型构建 | 0 | 1 |
| PPO | 0 | 0 |
| pending / 占用 / 未消费响应 | 均无 | 均无 |
| 剩 Provider / 公开操作 / 数学 | 0 / 30 / 22 | 3 / 42 / 21 |
| 剩共享物理 / NMPC / 回放总额 | 3 / 1 / 2 | 2 / 1 / 1（参考结构本身的 NMPC/回放机会均已用） |

总计 61 / 64 Provider、88 / 160 公开操作、原数学账本 1 / 44、
3 / 8 独立物理启动、2 / 4 NMPC、1 / 4 独立完整回放，PPO=0。
总实际 MuJoCo 积分为 **11,000 步**：3,000 独立执行 + 8,000 native 搜索。
原 native 1 次分析与其 8 个内部评估是两个口径，均列出，不能把内部 native 计算视为免费或再造预算计费。
所有遗留额度都保留，未重置、扩展或创建替代 Study；非实时任务，0.1 s 指仿真求解调度间隔。

| 同一参考物理结构的实际控制机会 | B | C |
|---|---|---|
| GVS NMPC | 1 套参考配方，5 次有界在线求解 | 相同 |
| 当前实测 NMPC 控制来源绑定 | 未成功完成 | 成功，无新物理或求解 |
| native 序列优化 | 未执行成功 | 8 次全程积分、1 次完成响应更新 |
| 独立完整序列回放 | 0 | 1 |
| 新物理结构 / 每结构再优化 | 0 / 0 | 0 / 0 |

两个冻结组具有相同资源上限，但实际可执行机会因 Agent 工具使用而不同。
C 的 21.09% 速度改善完全发生在同一个 physical_design_identity 上，并有更多已记录控制计算；
不能解释为结构变化的收益，也不证明 C 的结构联合设计能力优于 B。
位置误差略变差但仍合法，故也不称所有指标同时改善。

## 最终科研回答与边界

固定结构的控制优化在 C 中带来经独立回放确认的有限速度改善；B 没有执行后续优化，
两者都未达到完整硬验收。单次名义条件不支持统计显著性、跨任务泛化或全域不可行性。

C **没有使用 T2，也没有改结构**。可观察依据是它先研究当前参考配方，
收到 holding_speed 失败后选择直接优化实际输入，再用独立回放核验；
最终因 Provider 保护停止，未准备任何结构敏感性模型组。
因此，本轮不能回答 T2 数值方向是否平坦、是否改变了结构选择或实验顺序，
也没有新的 0.50 s CONIC −0.2 平台证据。旧平台及 S140/S141 的 X 一阶退化仍只是具名背景，
不能把本轮相同参考 NMPC 结果当成数学代理平分。

本轮没有执行新的 GVS 仿射见证—MuJoCo 同输入对照，不能把两组速度差解释成 GVS 模型误差。
已有 NMPC 保存预测仍受投影、起点和计划来源约束，未新增正式配对误差诊断。
C native 优化与独立回放的精确同序列、同初始化、同任务指标可比且一致，
证明该控制见证在同一 MuJoCo 模型中的复现，不证明跨物理模型或真实硬件转移。

当前最直接的物理瓶颈是停稳速度：最好结果仍为阈值的 4.394 倍。
其机制仍可能涉及 NMPC 求解质量、预测模型、制动时序和结构/输入能力；
五个有限迭代求解及八个 native 探测不足以在这些机制之间作唯一归因。
流程瓶颈包括 Provider 被读取/调用修复消耗、方法限制和按需证据交付不完整；
C 则展示了完成一次模型内搜索—独立物理核验的实际反馈闭环，同时仍有自然语言过度解释。

历史确已交付，并支持两组把停稳作为研究问题；没有隐藏导入 B 本轮结果、旧控制种子或当前验收信用。
Agent 仍出现重复读取、对 task_match 的错误推断和“制动力不足”的过强解释。
因此不能将“历史可见”直接等同于高效或正确利用历史。

现有证据**没有给出必须扩展截面、腱路、阻尼或其他 T2 参数的依据**：本轮尚未实际检验已有结构 T2。
下一步应先处理已经定位的局部交付/调用缺口，并在后续独立授权范围内分辨控制与模型问题，
不自动添加任务、模型调用、参数扫描、PPO 或第二轮 Study。

## 交付、修复与验证

生产科学源码和研究 core 修改 **0**；两组冻结 science_hashes、core_hashes 仍与 M1 实现一致。
新增 `runs/m2_run.py` 65 行操作脚本：原 dispatch 前核对冻结计算上限与 C 每结构机会，
原暂停后记录零增额复核再恢复；唯一真实接口修补是缺候选字段直接交回原 Plan 验证。
脚本没有选择科学方向、增加求解器、改模型、改任务或新建账本；C 前两次错误及费用保留。
本轮其余新增仅本文与两组标准不可变证据导出，没有第二套 Reporter 或研究记忆。

验证仅包含前述 2 项定向 unittest（8.847 s）、操作脚本语法检查、真实请求与预算审阅、
原轨迹读数复核、原 archived 整体/member 校验和 git diff --check；没有全仓测试或科学重跑。
最终两组 ledger 文件与原 Store 一致，所有原执行进程退出，无未知发送、未消费响应、pending worker 或费用占用。

已普通推送的阶段提交：43f1bcba5（准备）、3fcb402ab（B 启动）、7d200fee6（首项失败）、
d559aaecb（预算复核）、cbdefd26d（B 归档/C 启动）、57d42e8ff（B 深入审计）。
本文与 C 原导出属于最后交付提交；其完整 SHA、普通 push 后 origin/research/b3-m2-live-pilot HEAD
和目标树清洁状态在最终交付消息核对，避免自引用提交 SHA。
保留 M1 分支、两组原 Store、旧封存证据和主工作树既有环境/runs 文件；未强推、未合并 main、未批量清理。
