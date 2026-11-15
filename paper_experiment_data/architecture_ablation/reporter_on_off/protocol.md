# Reporter ON/OFF 决策回放协议

本次为六个历史边界的成对决策实验，不运行完整 Study、数学求解、结构搜索或物理 Worker。M1/P3 各 A/B/C；分类的近似匹配及限制见 snapshot_manifest.csv。类别不是对决策的预评分。

Main 模型沿用 gpt-5.6-sol 和 account3 Gateway；原准备采用历史 medium，但当前网关不暴露推理档位，实际各组统一使用其默认设置，详见传输修正。十二次请求配置相同，每次独立 UUID Session，最多四次 Provider 请求，形成第一份合法 Core Plan/ResearchDecision 后立即停止。顺序在每对间交替，匿名 A/B 分配事先固定。前一 Session 的输出不进入后一 Session。

OFF/ON 的基础 JSON、候选、冻结任务、全部原始事实、梯度/有限对照数值、单位/归一化、数值状态、原物理观测、原始证据权限、工具 Schema 和预算完全相同。ON 只附加匹配历史 Reporter 的 interpretations，OFF 不交付任何 Reporter prose/报告读取权限。六份报告均复用，保留原报告和实际历史 Provider 用量。既有程序生成的确定性 ResultCard 属于两组共同原始事实层，绝不把其单独当成 Reporter ON 处理。

只提供 evidence_read 和既有 research_plan。前者只读本快照原始 EvidenceRef；后者仅记录准备执行的请求，不调用 Core dispatch 或科研 Worker。schema 来自 Core agent.plan_schema 与 EvidenceQuery。没有现成的独立决策回放入口，因此增加此最小数据/请求脚本；未重构 Main、Reporter 或 Harness，未创建新 Planner/Agent/记忆系统。

历史结果边界包括本次数学结果及对应报告，不包含未来决策、最终成功或历史最终答案。报告中出现的原始科学来源以相同权限供两组读取。缺失信息保持未知，不补算数学或物理证据。上下文不因条件进行不同裁剪。

主要终点：五个 0–4 指标等权平均。准备时未找到现成独立盲评配置，先交付人工入口；后确认已连接网关有独立模型 gpt-6-astra，为本实验配置并实际完成六组模型盲评。人工评分仍为空，不伪造人工分数。评审只获相同事实和匿名 Plan，不获 ON/OFF 标签、报告或成本。条件映射仅置于 blind_review 目录外。

成本区分本次实际 Main/Reporter 用量与复用报告的历史生成成本；ON 输入已经包含报告阅读 Token。本次 Reporter 生成成本为零，另列历史首次生成的完整成本，避免宣称 Reporter 生成免费。六组不能支持充分统计显著性或机器人任务成功率推论。只读原始引用存在率属于程序核对，语义引用准确性和无支持结论须盲评，不填假分。

## 执行前传输修正

当前 Gateway 与历史 v8 接口不同，只支持 model/messages/stream:false。首批十二次请求都在 convertRequest 阶段因不支持 tools/reasoning_effort 返回 400，未进入 requirePlan 或上游推理。原请求/拒绝全部保留在 transport_rejections.jsonl 与 Session 文件，计入各自最多四次发送。此前没有形成任何 Main 决策。其后所有条件统一改用相同模型 gpt-5.6-sol、相同网关默认推理设置（具体档位不暴露，不能声称 medium）、完全相同的文本化 Core 工具 Schema。返回的 Plan/EvidenceQuery 用原 Schema 校验，未新增决策类型或改动生产 Harness。当前网关不返回 usage，真实 I/O Token 保持未知，不能据此声称额外 Token 成本为零。按用户补充要求优先完成 P3 三个节点。

## 最终计数与评审口径

十二次独立决策回放及六组匿名盲评已完成。确认已连接网关可用独立模型 gpt-6-astra 后建立本实验评审配置，人工入口保留；初始“无现成评审配置”的准备状态不是最终执行状态。Token 使用统一 o200k_base 可见文本代理，Provider 实测未知保持 null。详细差值及限制见 REPORTER_ABLATION_SUMMARY.md。
