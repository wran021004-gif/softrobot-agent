# C3 A/B 真实准入与对比记录

2026-10-25；起点 `f62a6c40cc831fa005771f046449e861c30a0377`，专用分支
`feat/c3-math-search-readiness`。用户本次指令授权独立准入后自动顺序运行 A/B；
不增加任何额度，不导入工程预检或旧 C3 科学答案。共同条件见 `c3_ab_protocol.md`。

首次门禁复用现有状态：A 在首个合法 `generate` 前仅允许生成/诊断/STOP，
非法生成不解除门禁；B 在首个有支持的任务 CONIC 搜索候选前保持搜索/诊断/STOP。
L0、Plan Schema 与执行使用同一个判定。取得首个候选后开放共同能力。

短轨迹保留初始路线、首次结构/数学/物理/控制节点及最近三项，最多八项，
只呈现动作、状态、结果和原 Store 来源，不推断因果。最近假设三字段各取原文
最多 240 字符，明确标为摘录，并保留完整 Plan 指针；Reporter 不改写动机。

| 旧 C3 请求边界 | 原完整请求 bytes | 新 Handoff 离线投影 bytes | 轨迹节点 | 最近原始假设 |
|---|---:|---:|---:|---|
| 1 | 84,965 | 77,372 | 0 | 尚无 Plan |
| 13 | 332,894 | 104,698 | 6 | 可见 |
| 25 | 639,373 | 95,536 | 7 | 可见 |

这里只是原存档的离线完整 wire 投影，使用本地 tokenizer，不是新的 Provider 用量。
历史 reasoning 未放回新会话；原 Store 历史仍可查询。STOP、SELECT、原预算字段、
独立验收及 Reporter 非权威地位不变。

原 `converse` 增加 `--restore-only`：沿原 reconcile/trusted-history/反馈恢复入口核对
SDK 与 Store 后返回，不启动新 Provider 请求；不另建会话管理。
定向检查覆盖 A 非法重试/解除门禁、B 两格成本/解除门禁、共同配置、
真实 SDK mock HTTP 切换后无发送恢复，均通过。

## 独立真实准入

修复提交：`644c08c5e454252e1d615fbc7e13b1d19a7ac91c`，已普通推送。
两个独立 Study 均将本次用户授权通过原 `formal_study_authorization` 绑定到
各自 `resolved_identity`。Handoff 的测试范围准入引用该授权，正式组须引用真实验证，
没有无来源地切换布尔值。工程结果不进入 A/B 候选/历史/科学上下文。

| 准入 | 实际结果 | Provider | public ops | 数学 | 物理/NMPC/PPO |
|---|---|---:|---:|---:|---|
| Search | 通过执行与比较能力；科学收益未验证 | 0 | 1 | 4/6 | 全 0 |
| Live Handoff | 通过请求—反馈—切换—新请求—新进程核对 | 4/4 | 3/12 | 0 | 全 0 |

Search 原导出：[原档案](../../evidence/c3_search_admission_20261025/immutable_artifacts.tar.gz)、
[成本](../../evidence/c3_search_admission_20261025/ledger.json)。
`engineering_search_admission` 原 Store artifact：
`2fc2f7e8e86f93e25a08db5f325ce9b01f342dfbc6fb42a930993e9548eab80c`。
明确工程子域：1 段、3 腱，只动长度，工程默认值附近 ±10%，两项提案。
真实 FamilyMixedSearch→生成器→GVS→CONIC→ranking→Store/ResultCard 全链路执行；
两个不同物理结构各计 1 模型准备 + 1 CONIC，共 4 次，两个真实 kernel/internal CONIC calls。
数值计时合计 5.90527 s（不同计时口径不相加）。signed violation 10.6000→9.8000，
第二项替换 incumbent；均有合法输入和数值 replay，均为 `optimal_inaccurate`、
`optimality_status=unknown`、物理任务 `unmeasured`。不称严格最优或物理改善。
首次工程脚本漏填 typed decision，准入前被拒绝、数学和 public receipt 成本 0；
原 `research_decision_rejected` 留存，同 Study 补齐输入后执行，无重置或扩额。
Worker 回报实际 s135 Python、所有线程为 1，原日志和数值 attempt/returned 边界均在 Store。

Handoff 原导出：[原档案](../../evidence/c3_handoff_admission_20261025/immutable_artifacts.tar.gz)、
[成本](../../evidence/c3_handoff_admission_20261025/ledger.json)。
`session_handoff_live_validation` artifact：
`aaaf83b7e9f8e2c8e573e42cc7bcef163197d83edcc9537322b97bfee4ac4a88`。
HTTP 200 原响应、原工具 ID/反馈、已结算 receipt、旧 SDK 快照、原 verified request-feedback
锚点、独立 restore 的新快照、切换后真实响应均保存。新 wire 无旧工具/推理历史，
L0 含原 Plan 假设摘录与诊断轨迹；完整原文仍由 Store 查询。
原 `recover` 后在另一个 Python 进程沿 `converse --restore-only` 重新核对，
工具均已配对、未发送新请求、无未决请求。四个 request ID 唯一，无重发。
Agent 首个 diagnose 成功；额外 diagnose 一次引用未注册证据被拒，一次被收尾保护拒绝，
两次均保留原反馈与公开操作成本；最后真实响应确认已有记录并完成 invocation。
本次并未证明额外诊断获准，未将这些拒绝包装成科研结果。
Provider：prompt 54,270、completion 9,519、总 63,789 tokens；cache hit 9,984、miss 44,286；
API 金额 unknown。没有 Reporter 请求、科学计算或机器人候选。

共同环境 admission ready：s135 Python 3.11.16、NumPy 2.4.6、SciPy 1.17.1、
CasADi 3.7.2、MuJoCo 3.13.0、CVXPY 1.9.3、Clarabel 0.11.1、
Strands 1.59.0/harness 0.2.0，OMP/OpenBLAS/MKL 均为 1。
正式组从此处起冻结相同代码、任务、域、先验、方法、工具及额度；先 A 后 B，
不根据 A 的科学结果修改 B。两组统一 `handoff_request_bytes=160000`、
`pause_exploration_remaining=4`；监督暂停后仅取消暂停阈值继续原账本。

## 用户授权的 0.1 s 重求解与一次重新开始

用户明确指出本次关注 A/B 科研决策而非控制器，并要求共同修改后重启。
旧轮次已行政关闭并由原 exporter 导出；不是 Agent 科研 STOP、任务失败或预算耗尽。
旧 A 7 个主 Provider 请求（280,303 tokens：prompt 241,726、completion 38,577；
cache hit 116,480、miss 125,246；金额 unknown）、11 个公开操作、1 个物理/NMPC 启动，
数学/PPO 为 0；原账本累计 wall 7,936.723896 s，未退回费用。旧 B 全部为 0、从未启动。
原档案分别在 `evidence/c3_heuristic_ab_20261025` 和 `evidence/c3_math_search_ab_20261025`。

旧 A 先两次非法生成后自主生成合法 3 段 4 腱结构，取得首个合法候选实际为
4 个 Provider 请求、4 个公开操作，不能把 reserved/completed receipt 相加误算成 8。
两次控制初始化/执行引用错配被拒后，纠正并运行一次 NMPC。
其实际结构使用默认椭圆/矩形截面，Agent 的“圆截面、均匀 EI”推测不成立。
GVS 38 坐标、76 状态、4 输入，路由孔使 structural_linear 网格增加。
原后台部分文件保存了 t=0/0.01/0.02 三次已完成更新：
1,614.8046 / 2,560.7302 / 2,543.7947 s；首项收敛，后两项迭代上限下返回可用计划，
不是完成任务。第四次在用户要求重启后中断。耗时主要在原 IPOPT 约束 Jacobian 求值。
原进程与 named Worker Job 均已核实退出，原 recover 结算未完成操作，所有部分工作文件存回原 Store。

共同新配置锁定 `nmpc_replan_period_s=0.1`；保持 0.01 s 控制执行/预测/验收采样和
0.0005 s 物理网格。正常 0.35 s 执行由 35 次求解变为 4 次，仍施加 35 项计划控制量。
求解次数下降不能直接保证等比例加速或物理成功；每次求解仍可能很慢。
记录区分 fresh solve 和 cached plan，后者含原求解 update/time/index，
不计作新优化收敛，不声称它已在当前测量状态重新验证可行性。
失败时清除旧计划，继续原有有界保持与连续失败停止规则。
新 A/B 只导入共同公开工程 priors 和准入证明，不导入旧候选、评分或诊断。
新增检查以人工计划 fixture 验证 4 次求解/35 次执行、末次 5 区间、十区间 warm shift、
失败后禁止过期沿用、网格覆盖和共同配置锁定；8 项定向检查全部通过，包含旧默认逐步求解与
结构化证据读取/汇总不得把缓存区间计作新收敛。没有新增 Provider 或科研预检计算。
旧两组标准导出的所有文件与 tar 成员已逐项核对：现有实际密钥和 Authorization header 命中均为 0。

## 新两组最终结果与审计结论

新 A/B 均沿原账本合法 STOP 并完成标准导出，没有追加研究或重置费用。
两组共同冻结 `395e9b65fcb51ea14758a65ff0e8085ab3b5492a`，原 exporter 比对共同条件相同；
任务、设计域、预算、方法机会、0.1 s 重求解设置、环境与独立验收均相同，B 没有接收 A 的科学答案。
停止均由 Provider 探索进入收尾保护触发，未使用的数学/物理容量不能绕过保护重新探索。

**流程审计发现两组存在反馈交付缺陷，故本轮不能用于证明科研方法总体优劣。**
已有真实生成、数值结果和独立物理验收仍可报告；这些不升级为受控因果或统计结论。
完整 A 审计与逐请求原证据见 [A 组决策审计](c3_a_decision_audit.md)。

| 最终用量/产出 | A：自主生成 | B：先数学 Search |
|---|---:|---:|
| 合法结构 | 1 | 6 |
| 数学评价/内部 CONIC | 2/1 | 12/6 |
| Provider（主/Reporter） | 61（59/2） | 58（54/4） |
| Prompt tokens | 2,124,389 | 2,140,613 |
| Completion tokens | 488,770 | 384,035 |
| 总 tokens | 2,613,159 | 2,524,648 |
| Prompt cache hit/miss | 828,672/1,295,717 | 730,368/1,410,245 |
| Public ops | 104/160 | 108/160 |
| 共享物理启动 | 1/8 | 6/8 |
| NMPC / 真实在线 NLP 求解 | 1/4 | 1/4 |
| 固定输入物理回放 | 0/5 | 5/5 |
| PPO stage/actions/evaluation | 0/0/0 | 0/0/0 |
| 新控制搜索附加物理回放 | 0 | 4，包含在上述 5 次中 |
| 最终剩余 Provider/数学/物理 | 3/22/7 | 6/12/2 |
| 原账本 wall_s | 4,548.022313 | 2,768.407776 |
| 完整任务通过/SELECT | 否/无 | 否/无 |

金额均 unknown。账本 wall、Worker 数学计时、backend timing、自然经过时间是不同口径，不相加。
新两组共 119 Provider、212 public ops、14 数学、7 物理、2 NMPC/8 次在线 NLP、PPO=0，
Prompt 4,265,002、Completion 872,805、总 5,137,807 tokens。
包括独立准入和用户要求替换的旧轮次后，本次累计为 Provider 130、public ops 227、数学 18、
物理 8（含旧 A 的一次未完成 NMPC，不退费）、PPO=0；总 5,481,899 tokens。
该累计跨独立授权的准入与一次重启，不能与单组 64 请求上限混为一谈；更早封存的 C3 不在此累计中。

### 首次结构获取：真实边界与成本

A 自主选择全部结构参数，通过 `research_plan(generate)` 获得合法 3 段 4 腱，
长 0.16/0.11/0.14 m，Young 7.2/5.4/7.0 MPa；继承椭圆/矩形截面，导向点 0.33/0.67，半径 18 mm。
原候选 `ea7231b55c6e86d0fe39fdecac5d41de7cec294264c1bafecd50bf276a1159e5`。
4 次初始生成尝试（前三次未成功）前还有一次先验读取；从空白到合法生成回执为 **5 Provider/5 public**。
这与被替换旧 A 的 4/4 是不同实验，不能互相挪用。

B 首次受支持候选来自真实 `family_mixed_search_v1` / `task_violation`，
原完整结果 `321b1bec443dde7e1c653474bfb2cdc0e7eefc3d95dc0ac0dd880c6e02bce86b`。
6 个合法不同结构各进行 1 模型准备+1真实 CONIC，共数学 12；首次 Search 前的非法提案同样保留。

| 从空白到边界 | A | B | B−A |
|---|---:|---:|---:|
| 首个合法生成/首轮 Search 根回执：Provider | 5 | 6 | +1 |
| 同边界 public ops | 5 | 6 | +1 |
| 同边界数学 | 0 | 12 | +12 |
| 同边界 Prompt/Completion tokens | 114,172/8,801 | 155,711/18,240 | 41,539/9,439 |
| 同边界总 tokens | 122,973 | 173,951 | +50,978 |
| 完成首轮 Reporter、下次主请求发送前：Provider | 5 | 8（含 2 Reporter） | +3 |
| 同交付边界总 tokens | 122,973 | 211,823 | +88,850 |

成本取该边界前已经发生的唯一原 call receipt，不叠加 reserved/completed 两条事件。
首次回执边界账本 wall：A 48.454 s，B 168.837472 s；B 首轮 Search 单独 elapsed 71.485348 s。
候选编译/构建只是工程合法性，A 在该边界没有运行数学模型或控制器；B 六个模型和 CONIC 均真实执行。

### B 的数学搜索及实际使用

| 提案 | 段/腱 | 关键变化 | signed task violation |
|---|---|---|---:|
| 1 | 2/3 | 初始结构 | 14.9039483 |
| 2 | 3/3 | 增加一段 | 46.1080057 |
| 3 | 2/4 | 增加一腱 | 13.2573220 |
| 4 | 2/4 | 第 2/4 腱跨段起点由 segment 1 改为 0，圆截面保持 | −0.2000000 |
| 5 | 2/4 | 根段长度 0.16→0.20 m | 3.8000000 |
| 6 | 2/4 | 根段 Young 7.2→10.45 MPa | −0.2000000 |

六个模型对应各自冻结构型；全为 CVXPY/Clarabel `optimal`、原 replay/数值检查通过，
`optimality_status=numerically_checked`，不是全局非线性或硬件保证。第 4 与 6 项差约 2.6e−13，不能解释为严格优劣。
返回数学 incumbent 为第 4 项；Agent 后续实际选择并物理测试第 6 项：2 段 4 腱，0.16/0.11 m、
Young 10.45/5.4 MPa、圆截面、12 GVS 坐标/24 状态、4 输入。
说明 Agent 实际用过数学结果选择候选/能力控制序列；根段材料选择中仍包含自主判断，不能宣称由显著数学分差唯一确定。

第 6 项原候选 `e0f2ccf53680ad00b1ed5d258d8b5eed38ced55fbc07f3bde07d3e5ce415ac1d`。
能力序列的首个真实回放未通过任务，展示了局部数学可行代理不能直接转移为独立物理成功。
其后 NMPC 降低了位置误差，但保持速度仍失败，不能由这些观察唯一归因于结构、离散控制频率或模型误差。
两个控制搜索根提案均失败；其中一次已花费 4 次附加物理回放，全部保留，未形成完成的优化更新。
另一次批量请求超过冻结共享容量被拒，不能声称控制搜索已完成或 PPO 已运行。

### 独立物理结果

| 完整执行 | 末端误差 mm | 保持最大误差 mm | 保持最大速度 m/s | 原验收 |
|---|---:|---:|---:|---|
| A NMPC | 21.9121 | 30.1895 | 0.522187 | valid_failure |
| B 数学能力序列回放 | 13.7064 | 13.7064 | 0.274126 | valid_failure |
| B NMPC | 4.0920 | 4.5172 | 0.181734 | valid_failure |
| B 控制搜索回放 1 | 13.3271 | 13.3271 | 0.274010 | valid_failure |
| B 控制搜索回放 2 | 13.8111 | 13.8111 | 0.274525 | valid_failure |
| B 控制搜索回放 3 | 14.0945 | 14.0945 | 0.274264 | valid_failure |
| B 控制搜索回放 4 | 13.6239 | 13.6239 | 0.273749 | valid_failure |

原阈值为 10 mm / 10 mm / 0.02 m/s。七次轨迹均完整、验收有效、张力界限通过且 solver_errors=0；
没有把迭代上限误写成 solver error 或把收敛误写成物理成功。没有 MuJoCo Hessian 故障或不完整轨迹进入本表。
A 四次在线求解全为 iteration_limit 可行计划；B 前三次为 iteration_limit、末次收敛。
两次 NMPC 各 4 次求解与 31 个计划沿用区间，不能把 35 个控制区间记为 35 次求解。
完整仿真 wall 为 A 1,415.562 s、B 305.422 s。结构状态维度不同，不能把二者时间差全归于重求解协议或数学策略。
CONIC 原内核还包含 7 次独立局部模型数值 replay，不能计作 MuJoCo 物理启动。
未在原接口中记录的低层积分/函数内部调用总数保持 unknown，不将 IPOPT 迭代数伪装成 rollout 数。

### 短会话与预算瓶颈：准入结论需要收窄

两组短包确实保留关键动作轨迹、最近原始假设摘录及完整 Store 指针；A 样本含 4–7 节点，B 样本含 4–7 节点。
但 A 33 次、B 38 次切换中，分别有 44/66 次读取反馈未作为原生 tool 消息进入紧随其后的主请求；
分别有 7/4 个相邻立即重读循环。全部实际短包未直接包含 `read_counts`。
因此真实 Handoff 准入只能证明收据、ID、快照与独立恢复的机械一致性，不能证明刚读取的内容已被主模型有效消费。
监督期间未出现需要科学 Worker 重启的中断；各一次预算监督暂停均沿原账本恢复，没有额外费用额度。
此前只报告进程健康而未识别语义交付缺口，是监督遗漏，不能包装成会话科学连续性成功。

本轮的主要工作流瓶颈是反馈交付/重复读取消耗 Provider 探索容量；实际物理表现还受到停稳失败的约束。
B 的已测位置误差较 A 小，但不同结构与自主控制路线、单次实验及共享流程缺陷同时存在，
不能据此断言数学搜索造成实际性能提升或具有统计/跨任务优势。未证实控制频率、结构和模型误差各自的因果贡献。

### 工程量、版本与原证据

相对用户指定起点 `f62a6c40cc831fa005771f046449e861c30a0377`，生产 Python 改动 12 文件，
+167/−48，净 +119 行；配置、测试、文档和标准证据单列，不将归档大文件行数当生产代码量。

| 文件 | +/− | 直接用途 |
|---|---:|---|
| extensions/tendon_family/contracts.py | 8/0 | 共同 replan 字段/网格覆盖验证 |
| extensions/tendon_family/control_evidence.py | 7/2 | 缓存计划来源与求解次数 |
| extensions/tendon_family/generated_serial.py | 2/0 | 候选控制网格验证 |
| extensions/tendon_family/gvs_nmpc.py | 57/14 | 0.1 s 规划序列执行、末次时域、失败清除 |
| extensions/tendon_family/gvs_reporting.py | 19/14 | 区分求解、沿用计划及预测来源 |
| extensions/tendon_family/gvs_trajectory.py | 15/4 | 按真实已执行区间移动 warm guess |
| tools/research/__main__.py | 2/1 | 原恢复入口的 restore-only |
| tools/research/agent.py | 8/1 | 原 SDK 恢复核对、共同 replan 元信息 |
| tools/research/config.py | 10/1 | 首次策略/共同 replan 冻结 |
| tools/research/core.py | 11/3 | 首次结构获取门禁的统一调用 |
| tools/research/design.py | 3/0 | 禁止覆盖共同 replan |
| tools/research/research_context.py | 25/8 | 短科研轨迹与原始意图摘录 |

提交 `644c08c5e`（门禁/意图）、`3799119508`（真实准入）、`395e9b65f`（用户要求的共同 0.1 s 与旧轮次封存）
已普通推送至 `feat/c3-math-search-readiness`。最终文档/导出提交不再修改生产代码或已冻结科研语义。
相关门禁、共同条件、真实 SDK mock HTTP 恢复及 8 项 replan/证据检查已通过；本次真实运行后只读审计，未重跑无关测试或额外研究。

两组原始标准导出：

- A：[配置](../../evidence/c3_heuristic_ab_100ms_20261025/configuration.json)、[账本](../../evidence/c3_heuristic_ab_100ms_20261025/ledger.json)、[原档案](../../evidence/c3_heuristic_ab_100ms_20261025/immutable_artifacts.tar.gz)。
- B：[配置](../../evidence/c3_math_search_ab_100ms_20261025/configuration.json)、[账本](../../evidence/c3_math_search_ab_100ms_20261025/ledger.json)、[原档案](../../evidence/c3_math_search_ab_100ms_20261025/immutable_artifacts.tar.gz)。

只读完成时，主工作区原有 80 项、f3-prestudy 12 项、s135 2 项、strands-mainline5 10 项未提交状态仍保留，
本任务只写专用工作树。其余工作树没有新增任务写入。最终推送和专用树清洁状态在交付中核实。

能够支持的科学结论：真实数学搜索确实生成、比较候选并产生有来源的能力序列；本例 B 的已测位置表现较好，但保持速度仍失败。
不能支持的结论：完整任务已成功、结构全局可行/不可行、数学策略具有一般优势，或本轮 Handoff 已证明科研语义连续。
下一步最有价值的工作是先修复并验证原工具反馈跨会话交付与已读状态，再在独立授权下研究停稳问题；当前不再启动额外实验。
