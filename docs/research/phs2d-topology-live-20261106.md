# PHS-2D 被动鸡头稳定正式 Study（2026-11-06）

用户已明确批准正式研究。Study `phs2d-topology-successor-20261106` 使用
gateway `gpt-5.6-sol`，Main medium / Reporter none；实现冻结为
`f76a85282368458f01884579842876d317cc2134`。
原始十工况、物理假设、数值协议、静力/KKT/稳定性、容量和独立验收标准保持冻结。
设计域为 1～9 段、1～12 腱，合法候选及研究方向由 Main 自主选择。

精确身份授权和正式 request-feedback Handoff 准入均已通过现有 Store 记录。
授权记录见 [formal_authorization.json](../../evidence/formal_phs2d_preparation_20261106/formal_authorization.json)。
没有 Provider 预演，没有继承父 Study 科学结果或授权。

Provider 初始上限为 64 次，最后 6 次预留收尾；数学评价、物理 episode 和公开操作只记账。
有限追加使用原身份绑定流程。NMPC、PPO/RL、Offline NLP、BDF 未获授权。

## 首组真实决策

Main 自主选择先研究历史 C4 设计线索（当前 `candidate_5`），并未被要求固定研究该候选。
它是九段四腱、各段 0.04 m、四根腱 payout 均为 0.472 m 的合法候选。
历史编号 C4 不是控制器、研究方法或当前资格标签。

1. Main 首先读取方法、研究机会和路由参数，随后提出 H1：当前设计能取得无载硬平衡资格，并呈现有信息价值的约束活动状态。
2. 首个注册数学评价已完成。初始几何无接触；零初值结果通过原 KKT、张力容量和稳定性资格，扰动初值结果未合格。两次优化器均报告收敛，资格不能由优化器收敛标志替代。最佳点 LICQ 与严格互补为 false，这些事实保留在原始诊断中。
3. Main 根据最佳无载工作点提出 H2：保持同一候选和全部原条件，进行覆盖十工况的完整有限时间响应分析。它明确说明数学动态结果仍不替代独立 Replay。

首个数学结果：`370f38273907995678e0e20bc5853de4a1b28f9df23ef8d22a14f027aaf6c52f`。
此结果与候选、H1 Plan 的精确关联保存在原 Store，不继承任何父结果。
H2 动态 Worker 已完成十工况计算，共 352000 个实际积分步，耗时 952.9 秒。
结果为 `execution_incomplete`：全部加载阶段均未通过原 tip/monitor speed、tail drift、static balance 资格，
不能生成有效任务表现分数，也未取得独立 Replay 验收。计算完成不代表科学资格通过。
全部工况无接触、无数值 warning；qvel、长度超限检查通过，但不能抵消其他失败。
tail drift 为 0.655～2.973 mm，原阈值为 0.5 mm；保持阈值不变。
动态结果：`104be05d958388bbfbbf26709ea77d6d16cc04218685442e08d2971e2061e0cc`。

首个结算边界已用 Provider 8/64（Main 6、Reporter 2），数学评价 2，数学动态 episode 10，
独立物理 Replay 0，公开操作 9。无 pending、无未结算 receipt，预算与所有失败保留。
原始 Plan、解释和账本的派生快照见
[window001.json](../../evidence/phs2d_topology_live_20261106/window001.json)。
研究已恢复同一 Store，继续由 Main 自主判断；尚未 SELECT 或 STOP。

原始 Store 为
`D:/softrobot-agent/.worktrees/stage2-research-workflow-20261106/runs/research/phs2d-topology-successor-20261106`。
原始请求、反馈、计算记录、逐物理步数据和实际费用由该 Store 及其 L2 文件持有。
本文是研究过程报告，不是第二套状态或账本。
