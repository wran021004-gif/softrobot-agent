# P6.3-B1 sol 独立重复窗口

用户要求将 gpt-5.6-luna 换为准确的 gpt-5.6-sol 再测一次。本轮从 luna 交付提交 `2137ada1635e2893be13c02ee0cbe4584aca3be8` 派生独立分支/worktree，使用新 Study `p63b1-sol-m1-traces12-20261029`，不修改 luna 的配置、Store、回执、预算或结果。

配置为 `configs/research/study_p63b1_sol_m1_traces12.json` 与独立 runtime `runtime_p63b1_sol_none.json`。Main/Reporter 均使用 sol、reasoning=none，仍经同一 localhost gateway。GET /v1/models 已返回 200 并包含准确模型；[官方模型文档](https://developers.openai.com/api/docs/models/gpt-5.6-sol) 列明 function calling 与 none 支持，不能代替本轮真实工具行为验证。不发送额外 smoke 推理。

[本轮最小离线核对](p63b1_sol_preflight.json) 确认冻结任务、FamilySpace、任务协议、控制、Native 限制、连续变量授权、能力、动作、预算、Knowledge、研究角色/信息流/Handoff 和 execution_instructions 均与上一轮相同。仅模型和新 Study 身份/授权/交付路径等元数据变化。新 Store 起始无候选、控制、数学或物理结果，ledger 全零，执行环境 ready。未重复大型测试、九篇阅读或五候选 fixture；九项 success_case 冻结 manifest 与原政策一致，P3 保持原始中文。

本窗口上限：Provider 12（包括失败、Reporter 和 1 次保护 closeout）；public operations 32（含 2 次保护）；共享数学 4；Native 每请求 callbacks≤24、iterations≤3、knots≤4；独立物理、NMPC、RL、Offline NLP/BDF 为 0。Native 真正执行的模型构建、rollout、callbacks、积分步及数值耗时沿原记录计费。本次没有预先豁免任何新的失败请求。

以原 formal_study_authorization 记录当前用户的单次 sol 重复授权，绑定新 resolved identity、模型、Knowledge 及原预算。Handoff 沿用既有 request-feedback 实现及已证实的 gateway 流程；本次授权包括该流程在 sol 模型上的一次验证，不能把 luna 见证写成 sol 已通过。首次 sol 实际反馈续接将在本窗口内验证，没有另加预检模型调用。保留 Main 自主选择，不代其提交候选、假设、参数或数学请求。使用原 run/--session-handoff/--max-new-provider-requests 12。遇 API/Schema/路由阻断、上限或 Main STOP 即停止，不自动追加实验。

## 实际结果

本窗口已结束：**12/12 个真实 Provider 请求全部 HTTP 200，未产生合法候选、数学请求或数学结果。** 不能宣称数学科研闭环通过。实际执行绑定提交 `e0a1ce1e0733da41bf4cfa2763bf7c58d76004d9`，resolved identity 为 `3f58d71b1bed57f3da92a7d4c1686448349e62e01420bfcf15388ef9dfc01bce`。完整原始回执在本 worktree 的 `runs/research/p63b1-sol-m1-traces12-20261029`；[有界真实审查 JSON](p63b1_sol_audit.json) 保存逐次请求 ID、实际工具输入、失败原因、来源引用、计账与关键真实 wire 投影，不包含凭据或完整 Store。

| 次数 | Main 实际行为 | 结果 |
| --- | --- | --- |
| 1 | search reach_and_hold；working_set 查询 design_domain 等字段 | 搜索成功；design_domain 不存在，返回字段导航 |
| 2 | 精确读 research-bounded-continuation@2；读 FamilySpace summary | 成功，获得结构域导航 |
| 3 | 读段数、腱数、assembly、control_domains、actuator_defaults | 五个读取均成功 |
| 4 | 重复 search；对 FamilySpace 请求 capabilities | 搜索成功；正确拒绝非候选引用 |
| 5 | 重复精确读取相同 procedure | 成功，但无新研究动作 |
| 6 | 重复读 FamilySpace summary | 成功 |
| 7 | 再读第 3 次的五项结构/控制信息 | 成功，但主要重复已读内容 |
| 8 | 使用自由文本 structure/failure_type 过滤搜索 | 无匹配；返回原恢复导航 |
| 9 | 再次 search reach_and_hold | 成功 |
| 10 | research_plan(generate)，提交 H1 假设和结构 | 服务调用完成；科学结果 invalid：EXACT_SECTION_STATIONS_REQUIRED |
| 11 | 根据第 10 次反馈修改生成请求并再次提交 | 服务调用完成；科学结果 invalid：CELLS_OUTSIDE_FAMILY_DOMAIN |
| 12 | 保护收尾中读 /all_fresh_results，但改用了 full | EVIDENCE_VIEW_MISMATCH；原监督窗口在已结算反馈处暂停 |

第 10 次是 Main 自主提交的可证伪结构假设：两段、四腱、全跨段路线和圆截面能为后续 Reach/Hold 搜索提供尺度与控制能力。两段长度自行选为各 0.2m，半径分别 0.008m/0.007m；这只是模型的未经验证方案，不是已发现的可行结构。它明确写出有效生成不等于可达、保持或物理任务通过。第 11 次解释认为第一次失败只削弱截面编码，不足以否定结构假设，并自主尝试修复。因此观察到了基于**输入有效性反馈**的后续动作，没有观察到基于数学结果的决策。

第一次请求每段都只给一个截面；实际冻结 prototype 的 segment_0/segment_1 分别有 1/2 个截面站点，第二段不满足原 EXACT_SECTION_STATIONS_REQUIRED。第二次自行改为每段三个截面并设置 cells=2，首先被原串联组装检查拒绝：冻结 cell_count_bounds=[12,12]。该结果没有证明截面修正已有效，也不表明结构不可行。没有放宽 FamilySpace、代为纠正候选或人工补交请求。

实际 wire 中 generate Schema 和生成域查询入口在起始请求就可用；Main 本轮无需反复 route，但多数请求用于重复检索。L0 的正确 stop_index 查询一直是 view=working_set、pointer=/all_fresh_results；末次 Main 自行改成 full，于是读取原 FamilySpace 中不存在的字段。原反馈明确给出 EVIDENCE_VIEW_MISMATCH，不能把该次读取算作正式完成结果索引阅读。Provider 接口、真实反馈续接在本轮没有 API 阻断；11 次 Handoff 均提交，下一次 sol 请求均成功。这只证明传输和工具反馈续接可运行，不证明模型正确理解了反馈或数学执行链已通过。

## Knowledge、费用和停止状态

九项 success_case 的冻结权限及 manifest 与 luna 一致，25 条 manifest 记录中有 9 条 success_case；沿用上一轮准确 M1 英文/P3 原始中文权限抽查，不重复 operator 阅读。Main 实际进行了 4 次搜索、2 次精确读取；两次都是 research-bounded-continuation@2，success_case 正文读取为 0。生成请求写明 adopted 该 procedure，但仅此不能证明其研究行为有效吸收了方法经验。

资源：Provider 12/12，public operations 23/32（6 次 Knowledge、15 次证据读取、2 次 generate），共享数学 0/4。ledger.wall_s=110.889，记录 Provider/工具回执耗时，不等同于总 Study 墙钟时间或费用发票。Native 模型构建、rollout、callbacks、物理积分步、数值耗时均为 0；独立物理、NMPC、RL、Offline NLP/BDF 均为 0。原因是生成从未产生有效候选，未进入数学执行；Native 积分计费语义不变。未豁免任何请求，未追加推理或 smoke 调用。

Reporter 请求和解释为 0，没有数学证据可交付；T1/T2 的收敛、局部证据、数值可靠性及结果后的研究决策仍未验证。Store 的 research_status 保持 ready，无 Main STOP、SELECT 或物理通过；进程正常退出于原 supervisor_pause，12 次额度为 0，无未结算 Provider 或科学执行。本轮停止，不继续同一窗口或启动其他 Benchmark。

## 与 luna 的有限对照

| 观察 | luna 先前窗口 | sol 本轮 |
| --- | --- | --- |
| 计入请求 | 12（11 个 200，末次 502；另有 1 次获准豁免的 ConnectError） | 12，全部 200 |
| 公共工具操作 | 11 | 23 |
| 正式假设/生成提交 | 0 | 2 次；有明确假设和一次针对失败的修改 |
| 有效自有候选/数学/Reporter | 全为 0 | 全为 0 |
| 主要停留位置 | 重复检索和 route，未提交 Plan | 重复读取、结构域参数未满足、收尾 view 选错 |

本轮可以支持“sol 在这次同配置窗口中更进一步提交了结构假设，并尝试响应生成失败”，不能支持“sol 已完成自主数学研究”或普遍的模型能力排序。它消除了上一轮末次网络失败的干扰，但数学链路仍未被触发；当前失败不是数值求解不收敛。下一步优先审查如何让 Main 在现有冻结域查询和生成 Schema 中准确取得站点数/固定 cells、避免重复读取及保持查询 view；不必增加优化器、证据库或固定科研路线。是否需要接口文字/Schema 的最小改善或另一次授权实验，应基于这批实际错误决定，不能仅追加数学额度。

本次只新增独立 runtime、Study 配置、准备 JSON、真实审查 JSON 和本报告；没有修改生产源码、研究提示词或执行契约。必要离线核对包括 13 项冻结语义相同、新 Store 零起点、manifest 相同和运行环境 ready；本轮不新增单元测试或重跑已有大型套件。真实窗口自身提供了 12 次同模型及工具反馈记录。提交并 push 到独立分支，不合并主线。
