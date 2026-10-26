# B3 R0/R1：科研决策交付修复与有限自主研究

2026-10-26，Asia/Shanghai。基线 `research/b3-m2-live-pilot@f98b979fbbc69f77f8593ad1759cb4a761545332`。
独立工作树 `.worktrees/b3-r0-decision-efficiency`；旧工作树、未跟踪文件及 M2 STOP Store 保持原样。
授权来源为用户本轮附件 `64a01c75-f0df-477b-95aa-ad3d952d4231/已粘贴的文本.txt`。

## R0：已完成的最小修复

M2 C 逐轮审计已证实：native 方法的完整 L1 反馈带 `execution_limits=8/2/4`，
SDK offload 后该字段可能处于被截断的中间；`mathematical_catalog` 已保留它，
但 `compact_scientific_delivery(decision_only=True)` 再次按白名单投影时删掉它。
因此不能将后来的所有越限都解释成模型明知上限仍忽略。

修复仅让原 `native_control_limits` 派生字段通过 L0，未增加第二份限制配置。
候选身份仍由目录顶层 candidate 和方法键标识；同一短包每次在 SDK offload 后加入完整 wire，
Handoff 新会话继续从 Store 重建，因此无须扩展 `session_handoff.feedback_delivery` 或复制历史。
大型反馈仍有原 `original_result_query`；完整方法、矩阵、控制和轨迹仍在 L1/L2。

| 已有文件 | 最终行为 |
|---|---|
| research_context.py | L0 保留 execution_limits 及两个准确的 L1 查询，不复制方法详情 |
| task_constraints.py | 实测 NMPC 控制初始化 source/parent 查询；已授权 T2 缺模型组时给 readiness 查询和准备说明 |
| agent.py | 真实 Plan Schema 对有实际候选的四类动作要求非空 decision.selected_candidate；缺动作 payload 指明字段；非 evidence_read KeyError 不再误报 JSON Pointer；不支持方法—模型组合、protocol 扩展和控制 parent 反馈精确化 |
| contracts.py | 现有候选/source/parent、analysis protocol、JSON Pointer/fields 描述明确绑定和按需读取；不改变 Plan 版本或替 Agent 填参 |
| native_control.py | 原 not_applicable 原因显示选定状态时间、收到的窗口及冻结初态 0 s；数值算法不变 |

Schema 不能表达两个 EvidenceRef 的运行时相等关系；原 `admit_decision` 仍是唯一权威验证，
未复制候选身份检查。R0 减少的是重复调用错误的接口来源，不宣称此后模型永不犯错。
T2 保留 registered / study_authorized / authorized / applicable / executable 和实际 missing，
准备提示不覆盖依赖、预算、STOP 或收尾保护，也不自动选参数/执行 T2。
原 readiness 提供五个授权参数的值/界、h 与 h/2、模型组、成本与原请求模板。

## R0 验证与资源

六项定向 unittest 全部通过（59.432 s）：

- 新 M2 B/C 原始完整 wire 对照：开局、首反馈、收尾各一边界；真实 formatter 和 Schema；同会话及 Handoff 投影。
- 新真实 Schema 和准确错误反馈：缺 candidate、缺 selected_candidate、非指针 KeyError、JSON Pointer 子键、MuJoCo/instantaneous_braking 不支持及非法 protocol。
- 复用 M1 缺组/完整组/原 dispatch/生成/L1 测试（明确的离线合成模型，不是新数学证据）。
- 复用 B3 G2 完整历史 wire、offload 及 L1/L2/历史所属 Study 隔离两项回归。
- 复用真实 SDK request-feedback rotation（显式 mock HTTP，原恢复/配对边界）。

简洁对照见 [offline_wire_comparison.json](../../evidence/b3_r0_decision_efficiency/offline_wire_comparison.json)。
原六个请求成员另用既有 `archived` 校验归档与内容身份；原 messages 和 STOP 身份未写回。
对照是离线重建的完整请求，不冒充真实新增发送。实际 rotation 是独立离线 SDK 测试。
最终对照进一步固定为原封存 L0，仅替换本次改变的方法目录和真实 Schema，
避免用最终 snapshot 的控制/报告字段推断早期上下文；该单项收紧后再通过（9.363 s）。
首轮发现新增目录常量缺局部导入、archive fixture 用最终余额误触收尾保护，均已修正；
这些失败发生在零 Provider/科学执行下。保存对照重复了唯一 archive 测试，没有扩展全仓测试。
未修 S130 无关 fixture。

生产五文件 `+31/-14`，净增 **17 行**；测试只扩展既有 `test_b3_t2_readiness.py`。
R0 实际 Provider、真实数学、MuJoCo 步进、NMPC、PPO 全为 **0**。
读取了 M1/M2、C 逐轮审计、C3 A/B、F1/F2、G2 与 S140–S145；
保留局部模型平台/退化、历史跨任务及同输入预测对齐的科学边界，未重算封存实验。

## R1：交付中断修复与同 Study 续研

以下初始预检快照保留原时间语义。用户随后在聊天明确批准 DeepSeek 地址/载荷及公开 GitHub
分支披露；`7922de156` 已推送，唯一 R1 已真实运行。中断前累计 Provider 39/48、公开操作
74/96、独立物理 2/4、NMPC 2/2，数学 0/26；没有 Agent STOP 或 SELECT。
新结构与控制配方的组合把 holding_speed 降到 0.043009681835387996 m/s，仍未达到 0.02，
不能将改善归因于结构单因素。两次 NMPC 原始结果、全部费用与失败均保留。

Reporter 的 `_source_catalog` 丢弃 `working_set`/`mathematical_capabilities` 视图，把投影
路径当作 raw JSON Pointer，准备 wire 时抛出 KeyError，进程退出；该失败没有发出 Reporter
请求。修复保留 selected_reads 的完整查询，派生路径以原始 artifact 根作来源；不伪造 raw
子路径。准备阶段也纳入既有 unavailable 回退，不让只读解释失败阻断主 Agent。
五项定向离线回归通过（2.743 s），涵盖投影视图、准备失败零发送、来源 ID 拒绝、历史响应
恢复及未知发送阻塞。另直接重建真实中断报告的三个查询，原事实和账本逐值未变，见
[reporter_repair.json](../../evidence/b3_r1_history_assisted_050/reporter_repair.json)。

用户明确要求修复后恢复，并在聊天选择 **新增 Provider 48、公开操作 96**：总上限变为
96/192，保护额度仍 4/6，所有数学、独立物理、NMPC、native 积分上限不变。
单次人工入口 `tests/research/b3_r1_resume.py` 只接受原 R1 身份及无占用/无悬账边界，
在原 Store 中登记授权、更新原 grant/输入快照上限，再调用原 bind 显式迁移；不新建 Study、
不重置或复制账本。修复前原归档已保存在 ignored runs，零请求 restore-only 已通过。
后续执行与最终结果另追加真实审计；本提交尚未应用增额或重启。

### 初始预检及当时的审批状态（历史快照）

R0 源码提交 **`78ca687fd893bfc805cfcaf1370ea62dd14dbf65`** 已普通推送，
核对 `origin/feat/b3-r0-decision-efficiency` HEAD 完全相同，随后创建
`research/b3-r1-autonomous-pilot`。R1 配置与 M2 策略监督入口提交
**`7283d07d652d2a382e16e2ba33e9b99533572414`** 已推送；原科学源码未再修改。

| 冻结项 | 实际登记 |
|---|---|
| 新 Study | b3-r1-history-assisted-050 |
| resolved_identity | a5754add34ed56639bacb431e256569d03a99c9094a1f7af63f75d56411b718a |
| 当前实现 freeze | 7283d07d652d2a382e16e2ba33e9b99533572414 |
| 原 Store formal_study_authorization | cc93c4e295158720cc6600d4c67fa2e8392d8c0b8b9bc90f01fe7f6181297734 |
| 原 Handoff 准入 | 47459b9e33a370aaf42c3d6b5a27dfa72d9eef16838b5e17f9c48dd71bcabcd3 |
| 原准入证明 | c3_handoff_admission_20261025 / aaaf83b7e9f8e2c8e573e42cc7bcef163197d83edcc9537322b97bfee4ac4a88 |
| 本 Study 参考候选 | cb6db6255de7cfbe1c3286c171c90770ed4856a473a249845748de1636e31453 |
| 合法导入后的控制源 | 2a554eeb59e44ac776b68a3d7a573e6c11017cd6dfb762569dc733212e13d3ea |

Provider 48（保护 4）、公开操作 96（保护 6）、数学 26、独立物理 4、NMPC 2、完整回放 2；
两结构各至多一次 NMPC、native 分析及完整回放。native 每次最多 24 callbacks、3 iterations、4 knots，
全 Study native 积分最多 60,000；PPO 0。监督入口复用 M2 的原 dispatch 前配方/机会核对，
增加此轮 native 单结构/总次数与原 raw cost.physics_steps 核对；保守请求步数上界包括前缀。
它通过 `runpy` 执行原 `python -m tools.research run`，不替 Agent 选实验、不改 Plan、
不替代 Worker、调度器或账本。完成 operation ID 仍走原收据幂等复用。

已由原 prepare/bind、formal_study_authorization/scope_identity、provider_egress_authorization、
`archived` 准入证明核验及 `import_history` 完成独立准备。
原 control_seeds 接口可以直接导入 C 已独立回放的完整张力序列；源
`30994c15d28a3b1b434d1f4cdc252199773e3eb4c9888a4b47b3870ac8d004ea`、原候选、
任务、通道、时间网格和实际张力边界保留，当前接受状态为 **unmeasured**。
未将历史 result 注册成当前 results/analysis_results/physical_replays，未产生新 SELECT。
历史 B NMPC 与 C 回放的 L0 结论均保留原 Study、原数值与精确 L1 查询。

冻结 canonical_task 与 M2 C 逐值相同。原 s135 Python/Worker 的 NumPy 2.4.6、SciPy 1.17.1、
CasADi 3.7.2、MuJoCo 3.13.0、CVXPY 1.9.3、Clarabel 0.11.1 可导入，三项线程均 1；
Host compatibility=true，无 pending/占用。没有启动科学环境试算。
另用 production decision_packet/formatter、当前 Schema、冻结 system instructions 和原工具声明，
构造 **74,525 bytes** 离线完整请求：24/3/4、两个历史速度与 T2 已授权缺组准备入口均可见。
这是未发送的请求构造检查，不能当成模型已经收到或理解。
详见 [preflight.json](../../evidence/b3_r1_history_assisted_050/preflight.json)。

### 自动审批拦截与恢复边界

R0 普通提交/push 最初被自动审批以“未核实远端/载荷”拒绝；之后通过连接的 GitHub
`get_repo` 确认任务指定仓库为 public 且有 push 权限，八个 R0 文件的凭据字面量检查为 0，
将本地 commit 与远端 push 分开提交复核后均获准，没有改出口或绕过审批。

R1 隐藏后台启动在 **shell 进程创建前** 被自动审批拒绝，原理由为：

> the transcript lacks trusted user authorization specifying that sensitive payload and destination.

被拒操作是运行原 CLI 监督入口，拟向 **https://api.deepseek.com/chat/completions** 发送
冻结 B3 任务、必要机器人结构/控制参数、显式授权的 M2 历史摘要、工具定义和本 Study 新反馈。
附件确实声明此范围，但运行审批仍要求聊天中的可信确认；已向用户呈现具体范围并请求确认，
不将 Store 中由助手登记的 scope 当作绕过环境审批的凭证。
该命令没有执行、没有加载运行凭据、没有建立后台研究进程、没有 Provider 发送。

本报告、收紧后的 R0 对照及 R1 preflight 的最终普通推送亦在进程创建前被自动审批拒绝：
它认为新的 R1 preflight 和详细科研 scope/metadata 向公开 GitHub 仓库披露尚缺明确出口授权。
因此这些最终材料仅本地提交，**没有推送**；已推送的 R0 实现及 R1 配置提交仍保留。
拟披露范围仅为本报告、零费用 R1 preflight、精简 R0 对照及现有测试收紧，
目的地是任务指定的公开 `wran021004-gif/softrobot-agent` 研究分支，不含凭据。
未通过改传输方式、换目的地或减少检查绕过拒绝；其后只完成无外发的本地提交。

### 截止此交付的科学状态

新 Study 的 research_status=ready，**尚未运行**，也没有由 Agent 提交 STOP 或 SELECT。
Provider、公开操作、数学计费、模型准备、CONIC、对偶、NMPC、native rollout、native 积分、
独立物理及 PPO 均为 **0**；所有上限完整保留。不是 Provider 保护造成额度未用。
没有实际 Agent 路线、T1/T2、结构修改、结构控制重优化、首次科学反馈或后续 wire 可审计；
因此本轮尚不能比较 M2 的工具错误/重复读取，也没有“产生新科学信息的 Provider 请求”。

工程能力已由离线真实 Schema/完整 wire/原 Store 路由验证接通；
**R1 模型实际收到证据、正确使用证据、新数学信息、新独立物理改善、结构额外价值均未验证。**
不能从暂停于启动前推断科研策略成败、固定结构不可行或 T2 无价值。
控制搜索不足、同输入 GVS/MuJoCo 预测失配和结构能力仍未区分；暂不能依据新研究结果
选择改控制、局部数学模型还是结构参数，须等待这唯一 Study 的真实自主行动。

恢复应使用同一个已冻结 Store，经聊天出口批准后运行
`python -m tests.research.b3_r1_supervision`，不重新 prepare、不重置预算、不新建 Study。
只有原 settled supervisor_pause 后复核通过才加 `--reviewed`，它不增加任何额度。
用户若批准，继续完成首次科学反馈后 wire 抽查、真实 Stop/Select、原导出及最终科研审计；
当前只交付可审阅的准备，不声称已完成 R1。
