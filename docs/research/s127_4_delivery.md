# S12.7.4 验证交付

2026-10-21。工作树 `D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc`，
分支 `feat/sorosim-matlab-nmpc`。重新 fetch 成功，起点与远端均为
`6c9cba2873e58012ccf16dafabfcab335275c634`；起点工作树干净。
IDE 中其他工作树未作修改。未启动 S12.8，未改任何任务阈值、历史科学结果或生产准入标志。

## 结论

| 阶段 | 实际结果 | 解释边界 |
|---|---|---|
| A | 独立授权后完成 12/12 次真实 DeepSeek 请求；前五对 prompt tokens 减少 40.5503%，总 tokens 减少 35.3785% | 真实首次请求输入收益成立；自适应读取净收益、完整科学准入、决策无退化未获证明 |
| B | 独立授权后发送 1/6 次；旧 SDK 首次响应全部用于推理并在 8192 tokens 截断，未形成工具回合 | 明确阻断；新会话 live 科研接续未通过，生产门禁继续关闭；剩余 5 次未发送 |
| C | 独立新工程 Study 完成 4/4 次物理探测；四次均略微恶化总体违反量 | 测到三个局部输入方向，位置与速度存在本次观测中的冲突；没有通过原任务，不推断全局不可行 |

**S12.8：No-Go，当前证据不足以准入完整自主 Cold-start Study。**
这不是以 B 未准入或 C 未改善作为硬前置条件：原连续 Strands 路径仍保留，
数学、物理、NMPC、局部搜索、Direct PPO 和 Residual PPO 的原入口与保护均保留。
主要未完成条件是实际决策质量验证：A 未证明正确数学操作选择、完整科学准入或事实无遗漏，
分层侧还出现两次引用资格错误。不能把较低输入成本当成已验证科研质量。
未发现需要放宽准入规则或重写生产系统的确定性接口缺陷；本轮生产代码改动为零。

## A：真实决策对照

[冻结范围](../../evidence/s127_4_decision/scope.json)、
[逐请求结果](../../evidence/s127_4_decision/results.json)、
[实际用量及检查](../../evidence/s127_4_decision/metrics.json)。
原清单及 12 份 wire 身份保持不变，manifest 为
`330d4b06ec479abcf97a08996430ed601de6cf751bd6c4cd1eee609571929c6a`。
原清单中的生产源码 hash 全部仍匹配。

用户在本次聊天独立批准了 [A/B 范围说明](s127_4_authorization_scope.md) 中的 A；
授权记录留在忽略的 `runs/s127_4_decision_authorization.json`。
没有借用旧 S12.6 授权。实际 endpoint 为 `https://api.deepseek.com/chat/completions`，
请求和响应模型均为 `deepseek-flash`，thinking enabled、high effort、非流式，
每次最大输出 8192 tokens。无模型替换、prompt 修改、额外请求或自动重试。

[官方思考模式说明](https://api-docs.deepseek.com/guides/thinking_mode/)和
[Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/)
在本日核对；真实 200 响应进一步确认了本账户的该模型/格式可用性。

下表的 P/C/T 是 Provider 返回的 prompt/completion/total tokens，不是字节估计。

| 冻结组 | 原完整 P/C/T | 分层 P/C/T | 首次工具结果 |
|---|---:|---:|---|
| 1 无科研结果候选 | 20,544 / 1,623 / 22,167 | 17,419 / 2,235 / 19,654 | 完整侧读参数；分层侧读 capabilities 和完整对象 |
| 2 非法数学工作点后的状态 | 20,745 / 707 / 21,452 | 17,419 / 6,305 / 23,724 | 完整侧两次读取；分层侧 execute 因未注册支持证据被拒绝，未验证正确数学修正 |
| 3 同候选两个控制失败 | 44,774 / 3,156 / 47,930 | 25,528 / 2,826 / 28,354 | 两侧 execute 均通过契约/引用等部分检查；真实科学执行资格仍 not_tested |
| 4 固定输入失败、预算近保护 | 44,623 / 2,767 / 47,390 | 21,075 / 3,002 / 24,077 | 两侧 STOP 均通过部分检查；未执行 STOP 或新科研 |
| 5 完整 NMPC 失败/残差参考 | 48,553 / 8,192 / 56,745 | 25,116 / 5,529 / 30,645 | 完整侧截断；分层侧读取证据，未实际选择 PPO 或完整科学动作 |
| 6 独立会话标记条件，单列 | 48,553 / 8,192 / 56,745 | 25,116 / 7,870 / 32,986 | 完整侧截断；分层侧 initialize_control 因未注册支持证据被拒绝 |

前五对的汇总：

| 指标 | 原完整工作集 | 分层工作集 |
|---|---:|---:|
| 请求数 | 5 | 5 |
| prompt tokens | 179,239 | 106,557 |
| completion tokens | 16,445 | 19,897 |
| total tokens | 195,684 | 126,454 |
| cache hit tokens | 14,080 | 7,552 |
| cache miss tokens | 165,159 | 99,005 |
| reasoning tokens（包含于 completion） | 12,686 | 15,640 |
| 截断响应 | 1 | 0 |
| evidence_read 调用提案 | 3 | 3 |
| working_set 详情读取提案 | 0 | 0 |
| 提案部分检查拒绝 | 0 | 1 |
| 部分检查通过的 Plan | 2：execute、STOP | 2：execute、STOP |
| 交付新读取结果给模型 | 0 | 0 |
| 完整合法科研提案/科学执行资格 | not_tested | not_tested |
| 不必要详情读取、关键事实遗漏 | 未能判定 | 未能判定 |

输入少 72,682 tokens（40.5503%），未命中输入少 66,154（40.0547%）。
输出增加 3,452，仍保留 69,230 总 token 节省（35.3785%）。
这支持冻结五对首次请求的实际输入效率收益；没有实际美元账单字段，不推算费用。
各请求的缓存、推理 tokens、模型/Schema hash、原请求 ID、原响应引用均在 metrics 中。

第六对两份 wire **分别与第五对完全相同**，均只有 system/user 两条消息。
其完整侧 cache hit/miss 为 48,384/169，分层侧为 24,960/156，明显受到前一请求暖缓存影响。
它只能作为另一次独立采样条件单列，不能当成真正不同历史条件比较或 SDK 接续证据。
六对描述性总量是完整侧 252,429、分层侧 159,440 tokens；不以此代替前五对比较。

两次分层引用错误分别将 family-space 完整规格和原始运动样本引用用作
`supporting_evidence`；它们可检索，但不属于该状态正式登记的科学支持引用。
保留 `UNREGISTERED_RESEARCH_EVIDENCE`，没有删除拒绝规则或改写模型输出。
目前不能区分采样差异与上下文展示的因果影响，也没有证据证明完整工作集科研成功率更高。

冻结设计每个 arm 仅允许一次请求。证据读取在本地使用原接口成功检查，
但读取反馈未再次发送，所以不能声称它已有效帮助模型、节约了后续读取成本，
或不必要的读取已经减少。PPO/数学等入口保留由离线回归确认；A 并未实际验证这些方法的模型选择质量。
所有 MuJoCo、NMPC、数学 worker、PPO 和真实控制搜索均被隔离，未伪造任何科研成功。

第 9 次响应首先触发原 `R3_LENGTH_TRUNCATED_NO_NATIVE_SUBMISSION` 保护。
原账本已计费、原字节已保存；后续从完全相同请求的已确认响应本地重放一次，
将其记录为截断后才继续剩余三份 wire。**实际发送仍为 12，本地重放不是第 13 次请求。**
第 11 次完整侧同样截断并被如实记录，均未作 native 科研提交。
初始 runner 在 `db083e40` 执行；接续脚本的实际内容保存在后继提交 `ee225753`。
该接续脚本在接续后提交，未改变冻结 wire、生产源码或计数；A 不存在科学 implementation_binding。

## B：真实 SDK 接续及准入

[独立范围](../../evidence/s127_4_handoff/scope.json)、
[真实阻断](../../evidence/s127_4_handoff/live.json)、
[真实 SDK 离线流程](../../evidence/s127_4_handoff/offline.json)。
独立 Study `s127-4b-sdk-20261021` 冻结于 `7117a1c6`，
6 次 Provider、40 次公共操作、2 次共享小型固定输入物理启动；数学/NMPC/PPO 为零。
没有导入 S12.6 候选、成果、预算或旧 SDK 文件。

用户另行批准 B 后，真实 `build_harness()`/Strands 发出一次请求。
HTTP 200，prompt 9,890、completion 8,192、total 18,082，
cache hit/miss 1,024/8,866，reasoning 8,192，finish_reason=`length`，无 tool call。
原完整 reasoning 和原响应字节在本地 Store 中保留。

边界拒绝将该截断作 native 输出，上层 OpenAI SDK 把这个本地异常包装成
`APIConnectionError`；不能把它误报成网络失败或未知发送。
该请求已结清，unknown outcome 和未结 receipt 都是零；
**已确认响应仍未消费**，因此没有旧完整工具回合、新会话指针或科研动作。
没有重发、另开 grant、提高输出上限、伪造工具结果或手动打开批准标志。
剩余 5 次 Provider、40 次公共操作和 2 次物理容量未使用，原 Study 保持安全阻断。

| 准入等级 | 状态 |
|---|---|
| offline_protocol_passed | true，限明确合成 HTTP/决策 fixture |
| live_sdk_continuation_passed | false |
| live_scientific_action_passed | false |
| production_recovery_validated | false |
| production_handoff_admitted | false |

离线 fixture 实际用正式 Plan 生成了四腱候选并初始化控制：
真实 Harness/SDK 保存旧工具回合，准备新会话、落盘、独立重开验证，再原子提交 Store 指针；
新会话没有拷贝旧 tool-use/tool-result 历史，原候选身份、旧消息和累计账本保持，
新工具动作只有一次，无 pending 或未结 receipt。
4 次 HTTP 用量全部是合成 fixture，不计入真实 Provider 统计。
14 个真实进程终止子场景及保存反馈恢复继续通过；未知发送/未完成 worker 等保护保持。

本次 B 的 8192 输出上限只属于该独立验证配置，未修改生产 `runtime.json` 的 32768 上限。
不能凭 B 截断推断原连续 Strands 路径不可用；本轮仍保留默认连续路径，
`--session-handoff` 仍默认关闭并要求原 live admission。

## C：控制敏感性与有限物理探测

[零物理审计](../../evidence/s127_4_control/audit.json)、
[四次冻结方案](../../evidence/s127_4_control/preflight.json)、
[真实物理结果](../../evidence/s127_4_control/experiment.json)。
新 Study `s127-4-control-sensitivity-20261021` 冻结于 `39739f78`；
原工程 Study 仍 STOP，其原来剩余 4 次额度未动用。
历史失败通过原正式 archive/history/control-seed 接口导入，保留原 Study 与结果身份，
不计为新研究成果或新鲜任务验收。

已审计 S12.6 的两份 NMPC 实测输入及原物理诊断。
本次六腱基线与已导出开环的 gap 均为 6.491881645，
终点误差 0.073460217 m，保持最大位置误差 0.074918816 m，
保持最大速度 0.141219774 m/s，原限值分别为 0.01 m、0.01 m、0.02 m/s。
保持位置为主导违反，原 holding 起点 0.30 s 为最坏位置/速度样本，终点为 0.35 s；
诊断保留精确时刻、末端位置/速度和实际张力引用。

输入为 35×6，pre-step ZOH，周期 0.01 s，各腱力限 8 N。
`tendon_1`/`tendon_4` 全程 8 N；其他四腱在 [0,0.34) 为 0 N、最后一段为 8 N。
完整逐时刻输入、上下限区间及每个扰动裁剪后的有效支持均在 audit。
到达边界不能据此认定整个结构不可控。

原 `correction_basis()` 两节点 `[0,0.35]`、六通道，knot-major 共 12 个系数。
后节点在 0.30 s 的权重为 6/7，实际最后一次输入开始于 0.34 s；
0.35 s 节点本身没有新的输入区间。正系数 6 的历史 +0.01 N
实际最大输入变化 0.009428571 N，只有最后一个条目被上限裁剪；
反向 -0.01 N 则被下限裁剪 33 个条目，仅改变最后一段，不能作为对称反向导数。
系数 7、10 的负方向释放饱和腱，可在保持窗口前及窗口内改变输入而不裁剪。

| 新试验 | 系数改动 N | 总体 gap | 保持位置误差 m | 保持速度 m/s | 裁剪条目 |
|---|---|---:|---:|---:|---:|
| 历史基线，未重跑 | 全零 | 6.491881645 | 0.074918816 | 0.141219774 | — |
| 半幅正向一致性 | c6=+0.005 | 6.492079841 | 0.074920798 | 0.141162466 | 1 |
| 释放 tendon_1 | c7=-0.01 | 6.492563850 | 0.074925638 | 0.141047078 | 0 |
| 释放 tendon_4 | c10=-0.01 | 6.492079926 | 0.074920799 | 0.141180069 | 0 |
| 联合释放 | c7=c10=-0.01 | 6.492762271 | 0.074927623 | 0.141007375 | 0 |

四次都降低保持速度，同时增大终点/保持位置误差，所以主导 gap 略微恶化。
半幅 c6 的预测/实测 gap 增量为 0.000198172/0.000198196；
联合释放的加性预测/实测增量为 0.000880680/0.000880626。
方向一致表示**预测和实测都变差**，不表示优化成功。
每次原注册评价器均返回原任务失败，另对保存数组重算完整终点/保持约束并与原验收核对。
没有以数学预测、平均误差或速度单项改善替代验收。

实际证据支持 c6 正方向两个幅度、c7/c10 负方向及其组合的有限响应；
其余系数、不同窗口、负 c6 的独特最后一段输入效果仍未验证。
不能据此构造完整 12 维雅可比、给所有系数排名或证明结构全局不可行。
P1 四腱 response 曾把 gap 从 1.090705 降至 0.054502；S12 四腱有原任务通过记录，
仅作为算法能力参考，未移作六腱雅可比。

本轮四次新试验均 cache_hit=false，历史基线和原 +0.01 N 测量直接引用，未重跑。
物理 worker 合计 4.2855715 s，累计 numerical_s=5.5702926 s（含导入/构造等），
5 次正式公共操作，4 次物理启动，零 Provider、数学 worker、NMPC、PPO。
只读审计 CPU 时间未单独计量。新 Study 已 STOP，无 pending、未知发送或未结 receipt；
所有原始物理输出、receipt、轨迹和独立验收保存在本地原 Store。

## 回归、预算与上传

[验证清单](../../evidence/s127_4_handoff/verification.json)记录 38 个不同通过测试 ID：
31 项聚焦回归、1 项截断响应无重发恢复检查、6 项会话/进程恢复测试；
另列 14 个真实 killed-process 子场景，不重复累加为测试 ID。
最终 SDK 驱动也在合成 HTTP 下通过真实工具与持久化回归。`git diff --check` 通过。

指定 Python 缺少 `matlab.engine` 曾阻断首次回归；最终复用本机已有 R2024a
Python 包的本地受控副本，经 `PYTHONPATH` 供测试/worker 使用。
没有启动 MATLAB/NMPC、升级 Strands 或改生产依赖文件。
`strands-agents==1.59.0`、`strands-harness==0.2.0`，三个数值线程变量均为 1。

| 独立账本 | Provider 实际/上限 | 新物理实际/上限 | 正式公共操作 |
|---|---:|---:|---:|
| A 隔离决策 | 12/12 | 0/0 | 0，工具仅隔离检查 |
| B SDK 验证 | 1/6 | 0/2 | 0，旧首发即截断 |
| C 数值工程 | 0/0 | 4/4 | 5/200 |

真实 Provider 共 13 次、429,951 tokens；合成 HTTP 不计入。
B 的已确认未消费响应仍保留，不将其伪装成已消费的清洁边界。
S12.6 原状态身份仍为
`d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3`，
原 STOP 工程 Study 状态/账本/事件未改变，未借用余额。

生产 `tools/`、`extensions/` **+0/-0**。测试/审计七文件 **+749/-7，净 +742**；
新 Python 模块仅 SDK 验证驱动及只读控制审计两个。
复用唯一 Plan/ResearchDecision、Strands/Harness、Store、资源账本、原评价器及全部原方法。
测试输出改到忽略的 runs，避免重写已封存会话恢复证据。

API 密钥只用于认证请求头；传输体检查和上传文件检查未发现实际密钥。
Git 仅上传代码、配置、派生统计、有限数值与 hash/引用。
原始 Provider 请求/响应/完整 reasoning、完整 Store/SDK 和本地 archive 留在忽略的 runs，
没有利用普通 push 权限上传这些原始数据。

## 提交与远端

只向目标分支普通 push，每次 push 后核对远端 SHA，没有 force push。
源码/证据提交链如下；本文为后继交付提交，最终报告提交及远端完整 SHA 见交付回复。

```text
d26ea6ad test(research): validate frozen layered-context decision comparisons
d12d8323 test(research): analyze measured NMPC control sensitivities
50fcf9a8 test(research): prepare isolated SDK scientific continuation validation
fd2c5768 test(research): verify isolated SDK snapshots and real tool receipts
db083e40 test(research): freeze four targeted control sensitivity probes
45f61588 test(research): require confirmed new-session request for live admission
ee225753 test(research): record twelve live decisions and recover saved truncation
d468c6a8 test(research): account cancelled SDK tools and constrain transfer bodies
7117a1c6 test(research): confirm final SDK driver with synthetic HTTP only
39739f78 docs(research): record live SDK truncation and retained admission gate
8ece586c test(research): report targeted physics and final validation evidence
```
