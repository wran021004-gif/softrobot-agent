# C3 A 组决策与反馈交付审计

2026-10-25，Asia/Shanghai。审计对象为已封存的 `c3-a-100ms-20261025`；
参照组为同代码 `395e9b65fcb51ea14758a65ff0e8085ab3b5492a` 的 B 组。
本次只读取原 Store、完整请求、原生工具回执及标准导出，没有新 Provider 请求、科学计算或生产代码修改。

## 结论

A 的直接停止条件是 Provider 探索额度进入收尾保护，不是数学/物理额度全部耗尽。
重复读取占比很高，而且发现了会话切换的反馈交付缺口：读取回执已保存，但下一次主模型请求
丢弃了对应的原生工具消息，只带重建的 L0；L0 又不展示已读记录、重复计数及最近读取回执。
因此不能把问题仅归于 Agent 不愿行动，也不能把机械恢复成功等同于科研反馈被主模型有效消费。

已确认该控制流能促成循环；不能据此断言全部重复查询都无必要，或所有重复成本都能完全节省。
两组均受到此缺陷影响。本轮能报告真实结构、计算及验收结果，不能据此证明数学搜索方法总体优于自主生成。

## 原始用量与有效产出

| 指标 | A 组 |
|---|---:|
| Provider | 61/64：主 Agent 59，Reporter 2 |
| Prompt / Completion / 总 tokens | 2,124,389 / 488,770 / 2,613,159 |
| Cache hit / miss prompt tokens | 828,672 / 1,295,717 |
| Public operations | 104/160 |
| 数学评价 | 2/24：1 次模型准备 + 1 次实际 CONIC |
| 物理 / NMPC / PPO | 1/8；1/1；0/1 stage |
| 合法结构 / 完整物理任务 | 1 / 1 |
| `evidence_read` / 不同原始查询 | 77 / 32 |
| 相同查询的额外重复 | 45，即读取调用的 58.4% |
| 含重复读取的主请求 | 25/59 |
| 只调用已有读取查询、没有新科研动作的主请求 | 16/59 |
| 上述 16 次请求实际 tokens | Prompt 583,379，Completion 192,542，共 775,921 |
| `tool_request_error` / Host failed receipts | 15 / 3；后者属于前者，不能相加 |
| 生成返回 `invalid` | 另有 3 次；不等同于 failed worker |

775,921 是这些请求的实际 token 用量，约占 A 总 tokens 的 29.7%；不是已验证的可节省量。
同一 `working_set` 查询可能随着状态变化返回新内容；这里只按完全相同的原始查询参数统计重复。
API 金额未返回，保持 unknown。账本 wall 4,548.022313 s 与实际自然经过时间、数值 kernel 计时不是同一口径，不能相加。

原导出：[账本](../../evidence/c3_heuristic_ab_100ms_20261025/ledger.json)、
[调用](../../evidence/c3_heuristic_ab_100ms_20261025/calls.json)、
[原档案](../../evidence/c3_heuristic_ab_100ms_20261025/immutable_artifacts.tar.gz)、
[最终处置](../../evidence/c3_heuristic_ab_100ms_20261025/disposition.json)。

## A 实际采取的动作

1. 先读取工程先验，再提交 4 次初始生成请求。前三次因截面 station/版本或 Schema 问题未成功，第四次得到唯一合法候选。
   结构为 3 段、4 腱；长度 0.16/0.11/0.14 m，Young 模量 7.2/5.4/7.0 MPa，路由半径 18 mm，guide_s=[0.33,0.67]。
   合法候选继承原椭圆/矩形截面，不能按早期假说称为 8 mm 圆截面。GVS 24 坐标、48 状态、4 输入。
2. 基线控制初始化纠错后成功。一次完整 NMPC 产生 4 次真实求解与 31 个计划沿用区间，执行全部 35 个控制区间。
   仿真 wall 1,415.562 s；四次求解均到迭代上限但返回通过数值可行性检查的计划，不是优化收敛。
3. 独立物理验收为 valid_failure：末端误差 21.912 mm、保持最大误差 30.190 mm、保持最大速度 0.522187 m/s，
   分别超过 10 mm、10 mm、0.02 m/s；任务完整、张力边界和零 solver error 条件通过。
4. 完成一次真实 sampled-affine CONIC，signed task violation=15.2000，数学计费 2；它是局部模型代理，不是结构物理不可行证明。
5. 诊断请求只返回只读诊断，没有实际执行其假说中的 MuJoCo 平衡松弛。三次 equilibrium 分析因未提供要求的原生方法/模型来源被拒。
6. 尝试转换实测 NMPC 输入、两次控制搜索及一次控制配方再生成，均未形成成功的控制优化或新候选。
   原生请求的 candidate/method/budget/经验处置字段不匹配，以及再生成缺少精确截面 station，分别保存原反馈与成本。
   没有第二次 NMPC、PPO 训练或新的有效物理结果。
7. 一次监督暂停核对原账本后，在原额度内恢复。进入收尾保护后，STOP 三次被拒、第四次合法完成。
   最终剩余 3 次 Provider、56 次 public、22 次数学、7 次物理；这些剩余科学额度不能越过 Provider 保护线重新探索。

此前“12 次错误反馈”只统计了 `tool completed/status=error` 的封装结果；完整错误事件为 15 条，
其中包含另 3 条 Host failed receipts。此处纠正口径，不重复累计失败数或费用。

## 会话交付缺口的直接证据

A 有 33 次 committed Handoff。44 次读取调用的反馈与紧随其后的主请求之间发生切换，
后一个 wire 不含对应的原生 tool 消息。发现 7 个“读 → 切换 → 下一轮马上用同样参数再读”的相邻循环。
原有严格 `read_coverage` 投影识别 73 条读取记录，仅 13 条在成功请求中找到完整一致的原反馈，
其中 5 条满足完整数据读取条件。其余可能有 SDK preview 或 L0 概括，不能把它们一律称为完全没看到任何信息。

例如主请求 #19 读取物理结果的 `/control_result_links`，回执已保存；随后切换；
主请求 #20 的消息只有 system、handoff 提示、继续研究提示和 L0，没有 assistant/tool 反馈，
其响应再次请求完全相同的 `/control_result_links`。

| 原 Store 内容 | 原 artifact_id |
|---|---|
| #19 原反馈 | `5b81946825e082d1439c8b8eafad0ad989af6dc10d82e9d19e47a071e61052fb` |
| 中间 Handoff | `0d4fda089e72e23b5c2894c4999f85a8443da29342af38d8d40d369cfb4519f5` |
| #20 实际 wire | `729a64ebe286ea2c4fb625c526ed4a01d13925766399264c46ead1099449b027` |
| #20 重读请求 | `01bc55e91a9f8b746ffedfaaf441376a5a0f20c87c1afd05b33b260c31e9cbb5` |

完整原证据均在上述原档案内，没有创建第二套证据归档或重算结果。

调用路径：`agent.before_model` 在已配对 tool feedback 后、下一次模型发送前触发切换；
`session_handoff.initial_messages/handoff` 的新会话只放提示与重建状态；
`research_context.decision_brief` 省去了已有 working_set 的 `read_coverage/read_counts`，
`agent_decision_brief` 又将控制结果链接改为按需查询。
59 个实际 A 主请求的短包都没有直接带 `read_counts`。已有原始假设与 4–7 个关键科研轨迹节点确实保留，
但这不能替代最近工具反馈和“已读什么”的连续性。

160,000 bytes 阈值下，A 稳态新请求约 126–128 KB，B 约 143 KB，留给工具反馈与历史的余量较少，
容易再次触发切换。阈值影响频率；缺少反馈语义交付是更直接的问题，不应只靠抬阈值掩盖。

## 另一项已确认的纠错缺陷

`experience.disposition_bindings` 因 `experience_disposition` 使用了科研结果/自拟假说名称而拒绝请求。
`agent.error_feedback` 却把 `DISPOSITION_REQUIRES_EXACT_ACTUAL_READ` 映射为“读 selected_execution 然后 SELECT”，
指向错误字段和动作。A 的两次 STOP 与一次 control_search 受到这个误导；另一次 STOP 是缺 hypothesis。
原错误 `88198cb9d0e212ce214abe5ce20fcdb50ea21b6174e0fdf2abaf9770c223a554`
及 `d8ab49bfdf292a2e6a0576be7f9856781a847d7f32e32c6601bc041e6db3c036` 的 traceback 明确落在 experience.py:50。
这里不能解释为物理结果没有重新读取即可解决；需要改正经验处置字段或其提示。

## 与 B 的交叉核对及限制

B 最终也有 85 次读取、51 个不同查询、34 次额外重复、38 次切换和 4 个相邻立即重读循环。
其 66 次读取后切换未将对应原生 tool 消息带入下一个请求。B 仍真实完成了 6 个候选/12 次数学评价、
一次完整 NMPC、5 次物理回放，产出比 A 更多；两组都未通过完整任务。详细成本和物理对照见
[正式记录](c3_ab_live_comparison.md)。

Search 的真实 Worker 准入和 Handoff 的 HTTP/工具 ID/SDK 独立恢复机械验证确实完成，
但此前 Handoff 准入没有验证“读取刚返回的新内容在切换后被下一次主模型有效消费”。
因此它不能证明科研决策链语义连续。此前监督只确认进程、收据与预算健康，未及时审计此项，是监督遗漏。

## 下一步最小修复目标（本审计未执行）

1. 在切换前消费待处理反馈，或沿原 Store/会话机制将最近一轮必要读取回执、精确来源、查询及实际交付状态带入短包；不复制全历史。
2. 直接保留少量已读清单、重复提示和原 working_set 查询入口；区分调用成功、SDK preview、实际主请求已交付，不能用布尔值冒充模型理解。
3. 对已交付且源未更新的重复查询给明确提示，保留有理由的复核能力；不得简单封禁所有重复读取。
4. 修正经验处置错误的字段/动作提示，避免引导 STOP 去做无关的 SELECT 读取。
5. 先用本次真实 #19→#20 等边界进行离线回归，再独立验证语义交付；不得在已冻结 B 中热修，不能扩额补跑或自动再开一轮 A/B。

支持的结论是：存在真实读取循环及可定位的交付缺口，B 的已记录位置表现更好而完整任务仍失败。
不能支持“数学搜索一般更优”“结构不可行”或“恢复成功即科研有效连续”。最有价值的下一步是先修复反馈交付并验证决策能向前推进。
