# B3 M2：有限真实自主科研试点

2026-10-26（Asia/Shanghai）。状态：**B 首次完整 NMPC 为有效失败，Agent 正在继续研究；C 隔离等待**。
本文件持续更新，尚不是已完成的 M2 科研报告。

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

持续监督：本聊天 heartbeat `b3-m2` 已在明确授权后恢复 ACTIVE，随后按用户要求改为每 10 分钟检查。
任务全部交付后停用。
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

运行交接：B 主研究进程 PID 341580（Windows venv launcher PID 515372），
execution owner `b3-t2-050-b-v2-draft-exec-773fd76849c64c3c`，原 worker_lifecycle PID 607404，
实际控制子进程 PID 736960。原 backend execution `630458fcbd944389a602244dfdd5a42d`。
首个在线求解在 t=0 返回 iteration_limit_feasible，plan_accepted=true、solver_failed=false、
optimization_nonconverged=true，100.7528732 s；已保存 0–0.09 s 的 10 条控制更新，
正在后续在线求解。这是实际数值状态，不是工程错误；未调整迭代或任务阈值。
监督应先检查这些进程与原 pending，再读取新增 nmpc_updates / Store 事件，不重复启动。

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
但把方法名放在 operation 且缺少正式 native 方法字段，原 Schema 以
MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE 拒绝，数学启动和计费均为 0。
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
diagnose 与 CONTROL_SEARCH intent 不匹配；native 保存状态字段缺失；
随后 evaluation_requests=300 超过 8、iterations=8 超过 2，均由原门禁在计算前拒绝。
这保留为调用与预算理解错误，不把被拒的 300 回调记为已执行，也不放宽冻结上限。

| 实际状态与费用 | B | C |
|---|---:|---:|
| 状态 | 首项有效失败，继续研究 | 未启动，隔离等待 |
| Provider（含 Reporter） | 17 / 32（含 1 Reporter） | 0 / 32 |
| 公开操作 | 28 / 80 | 0 / 80 |
| 数学总评价 / 模型 / CONIC / dual-face | 0 / 0 / 0 / 0 | 相同 |
| 独立物理启动 / NMPC / 完整回放 | 1 / 1 / 0 | 0 / 0 / 0 |
| native 内部积分 / PPO | 执行中，待原记录结算 / 0 | 0 / 0 |
| pending / 占用 / 未消费响应 | 无物理 pending；后续 Provider 执行中 | 无 |

上表为首次物理结束后继续研究时的账本快照；后续由原账本结算并替换。
T1/T2、分数平台、结构修改、GVS—MuJoCo 差异和最佳独立硬指标尚待本轮测量，不能把旧证据记成本轮结果。
没有研究 Agent 的 SELECT/STOP，也未行政关闭这两份待运行 Store。
后续须完成每组实际决策与 wire 审计、资源结算、独立物理硬验收、标准导出及完整研究结论。

生产源码修改为零；新增本准备报告和一个操作脚本。没有扩大测试、修改冻结科学配置或扩展预算。
