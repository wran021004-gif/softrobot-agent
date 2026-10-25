# C3 G2：真实数学指导科研闭环

2026-10-25，Asia/Shanghai。基线 `576a18a0be6e77da6840d09ab1a2f4360d499f30`；
独立分支 `codex/c3-g2-scientific-decision-loop`。

## 首发前冻结范围

本次新授权的独立 Study 为 `c3-g2-scientific-20261025`：Provider 总上限 8（包括 Reporter），
数学评价上限 4（准备、内部求解和失败仍按原账本），public operations 上限 24；独立物理、
NMPC、PPO 均为 0。只执行一项主要数学实验及反馈后的科研决策。未重跑 G1 Provider、A/B 或半径敏感性。

生产修改仅在 `task_constraints.py` 和 `evidence_views.py`：复用现有方法说明、ResultCard 和
diagnostic_relations，为测量、模型计算、研究假设、因果结论以及控制/初态/通道/时间对齐提供
通用 L1 解释范围。L0 保持原有入口与简短事实；L2 原证据不重写。未修改任务验收、物理、求解器、
Handoff、正式收尾保护或 SELECT/STOP 读取规则。

新的离线协议回归在正常探索预算下执行 SDK request-feedback Handoff：原历史摘录登记到既有
scoped_context，原查询在第二次 Schema 中可用，read_state 与 pending_feedback_delivery 保留首次
读取；整个 Study 的一次性要求不随 Session 重置。此结果验证协议与可选性，不能冒充真实模型的自主不重读行为。

新 Study 通过原 FamilySpace 重新生成历史 B 设计，保留原历史来源；历史物理结果不登记为当前结果。
原 update 30 是 0.30 s，原生 qpos/qvel 与控制前缀可读，但现有接口要求当前 Study 拥有原生执行。
没有已登记的跨 Study 原生状态重绑定，本轮不手工改 candidate/准入标志；将此限制如实告知 Agent。
可用方法由原目录和具体请求准入决定，Host 不指定研究方法或解释结论。

首发前定向测试及最终真实结果将在本报告后续段落登记；此冻结段落不预判 G2 成功。
