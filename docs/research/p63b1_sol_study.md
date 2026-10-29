# P6.3-B1 sol 独立重复窗口

用户要求将 gpt-5.6-luna 换为准确的 gpt-5.6-sol 再测一次。本轮从 luna 交付提交 `2137ada1635e2893be13c02ee0cbe4584aca3be8` 派生独立分支/worktree，使用新 Study `p63b1-sol-m1-traces12-20261029`，不修改 luna 的配置、Store、回执、预算或结果。

配置为 `configs/research/study_p63b1_sol_m1_traces12.json` 与独立 runtime `runtime_p63b1_sol_none.json`。Main/Reporter 均使用 sol、reasoning=none，仍经同一 localhost gateway。GET /v1/models 已返回 200 并包含准确模型；[官方模型文档](https://developers.openai.com/api/docs/models/gpt-5.6-sol) 列明 function calling 与 none 支持，不能代替本轮真实工具行为验证。不发送额外 smoke 推理。

[本轮最小离线核对](p63b1_sol_preflight.json) 确认冻结任务、FamilySpace、任务协议、控制、Native 限制、连续变量授权、能力、动作、预算、Knowledge、研究角色/信息流/Handoff 和 execution_instructions 均与上一轮相同。仅模型和新 Study 身份/授权/交付路径等元数据变化。新 Store 起始无候选、控制、数学或物理结果，ledger 全零，执行环境 ready。未重复大型测试、九篇阅读或五候选 fixture；九项 success_case 冻结 manifest 与原政策一致，P3 保持原始中文。

本窗口上限：Provider 12（包括失败、Reporter 和 1 次保护 closeout）；public operations 32（含 2 次保护）；共享数学 4；Native 每请求 callbacks≤24、iterations≤3、knots≤4；独立物理、NMPC、RL、Offline NLP/BDF 为 0。Native 真正执行的模型构建、rollout、callbacks、积分步及数值耗时沿原记录计费。本次没有预先豁免任何新的失败请求。

以原 formal_study_authorization 记录当前用户的单次 sol 重复授权，绑定新 resolved identity、模型、Knowledge 及原预算。Handoff 沿用既有 request-feedback 实现及已证实的 gateway 流程；本次授权包括该流程在 sol 模型上的一次验证，不能把 luna 见证写成 sol 已通过。首次 sol 实际反馈续接将在本窗口内验证，没有另加预检模型调用。保留 Main 自主选择，不代其提交候选、假设、参数或数学请求。使用原 run/--session-handoff/--max-new-provider-requests 12。遇 API/Schema/路由阻断、上限或 Main STOP 即停止，不自动追加实验。
