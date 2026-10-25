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
