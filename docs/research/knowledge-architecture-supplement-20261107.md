# 阶段一补充：九类历史任务的 Knowledge / Skill 组织

本次保留此前代码、提交和冻结 Study，仅补充知识组织与读取链路。范围按用户后续要求扩展为 M1–M6、C1、P3、PHS-2D 九类历史案例。没有运行物理搜索、历史十工况、真实 Provider、数学求解或新 Replay。先前阶段二、三的实现及实验记录保持原样。

## 同一目录、不同职责

继续使用 `memory/diagnostic_index.json`、冻结的 `knowledge_manifest`、`experience_retrieve` 和原 Store。新增 `memory/knowledge/research_organized_v2.json` 是该索引引用的内容集合；`content_key` 只选择一个记录，不是另一套注册器、存储或检索服务。既有 manifest 行、原正文和旧配置未改写。

新增配置 `configs/research/study_passive_knowledge_organized_v2.json` 明确启用 `organization=typed_knowledge_v1`，精确冻结条目修订版及内容集合哈希。该配置只允许离线架构检查：真实 Provider、数学、物理预算均为零。新内容不会进入没有明确选择此组织版本的既有主动或被动 Study。

| 资源角色 | 本次组织 | 责任 |
|---|---:|---|
| Knowledge / Case | 9 | 历史条件、假设、完整概括性 Action Trace、失败与成功、证据等级及迁移限制 |
| Knowledge / General | 9 | 可迁移的条件式物理解释和研究原则，附来源、置信、适用范围和限制 |
| Knowledge / Diagnostic | 11 | 症状、竞争假设、判别证据、诊断动作、解释；不把单次失败固定成唯一原因 |
| Knowledge / Validation | 3 | 被动资格、独立重放/细化/扰动、主动任务协议与采样范围 |
| Skill | 6 | 现有六个 ID 的 revision 2：可通过现有高层工具执行的工作流程 |
| Expert Process | 1 | PHS 领域研究方法的组织及相关 Knowledge / Skill 选择 |

Knowledge 的 `id,type,summary,trigger,source_refs,evidence_level,applicability,limitations,related_skills` 均在同一索引和正文内。Skill 均提供 `id,when_to_use,inputs,workflow,outputs,limitations,knowledge_refs`，并列出实际涉及的高层能力。互相引用使用精确 `id@revision`；历史来源引用与当前科学证据引用分开。

## 原有六份 Skill 审查与修订

以下六个原 revision 1 正文保留，组织配置只选择其 revision 2。它们仍是 Agent 可按需读取、通过已有工具执行的流程内容，不是六个新确定性执行器。授权、预算、数值步骤和验收仍由现有代码负责。

| Skill ID | 使用条件、输入 | 流程责任与输出 | 涉及高层能力 | 主要 Knowledge 与重叠边界 |
|---|---|---|---|---|
| `skill-finite-search` | 重复有限控制搜索未通过；输入搜索域、终止、有效性、任务和剩余额度 | 区分算法/控制域限制与结构假设；输出有削弱条件的对照或有限结论 | `evidence_read`, `experience_retrieve`, `research_plan` | `general-finite-claims`, `general-sensitivity`, `diagnostic-convergence`, `diagnostic-holding`；与 continue-or-stop 共享失败证据，但不替 Main 决定停止 |
| `skill-parameter-model` | 拟改变参数；输入候选、生成/编译/力学事实及固定/重优化输入约定 | 追踪参数如何进入模型并识别无效字段；输出参数语义与局部敏感性假设 | 读取、`research_analysis`, `research_plan` | `general-material-inertia`, `general-routing`, `general-active-inputs`, `general-sensitivity`；给后续流程提供模型语义，不承担独立验收 |
| `skill-matched-comparison` | 解释结果差异；输入双方结果、任务/载荷/初态/模型/控制处理身份 | 比较有效性、匹配因素和混杂；输出受限比较结论或缺失证据 | `evidence_read`, `experience_retrieve` | `general-multicondition`, `general-sensitivity`, `diagnostic-contact`, `diagnostic-near-bound`；供实验设计及机制解释共用，不重复注册新比较器 |
| `skill-local-to-experiment` | 将局部数学结果转为有限实验；输入作用点、分支、假设、合法域 | 提出机制假设、有限预测、削弱观察和资格门槛；输出正式可证伪 Plan 与结果解释 | 读取、`research_analysis`, `research_plan` | `general-routing`, `general-equilibrium`, `diagnostic-local-finite`；设计有限验证，与 witness-replay 的独立资格判定分工不同 |
| `skill-continue-or-stop` | 需要继续/停止决定；输入失败、未知、成本、剩余合法信息机会和预算 | 评估剩余实验信息价值；Main 输出有来源及未决范围的继续/停止理由 | 读取、`research_plan` | 九类 Case、`general-finite-claims`, `validation-replay`；使用 finite-search 的诊断，不把迭代上限当作科学闭合 |
| `skill-witness-replay` | 数学/开发见证需要独立验证；输入冻结身份、范围和 Replay 准入 | 获准时通过现有 Plan 请求独立回放，读取完整资格及任务结果；未获准则输出未验证状态 | 读取、`research_plan(action=physical_replay)`，仅在准入后 | 三条 Validation、`general-multicondition`；不重复局部实验设计，也不由历史成功获得当前验收信用 |

六者重复的是必要的“读证据、检查范围、保留未知”，没有复制完整物理理论或历史长轨迹。已有的 `skill-control-or-structure@1` 是后来加入的重叠流程，保留原资产及原调用者，本组织配置不额外选择它；其区分控制搜索与结构解释的责任由 finite-search、parameter-model、matched-comparison 组合覆盖，因此仍是六份 Skill。

## PHS 过程与被动研究方法的真实类型

`phs2d-research-process@1` 原来以 `kind=case` 加载，由 `retrieval_hint` 投递咨询性过程摘要，没有独立工具或执行器注册。本次 `@2` 仍在同一 manifest 中，以显式 `resource_role=expert_process` 表示其实际职责：组织基线、症状诊断、有限机制对照、独立验证/停止范围，并引用既有六份 Skill。历史经历移至 Case，理论移至 General；没有另注册同功能组合 Skill。Main 继续拥有实验和停止决定权。

`passive-force-response-research@2` 原为 `kind=procedure`，旧逻辑因此把它显示成 Skill，但正文混合互补/KKT 理论、有限变形诊断及 PHS/P3 经历。原文不改；新组织选择 `@3`，将其明确归为 Diagnostic Knowledge 的诊断选择入口。理论、具体症状和历史序列分别引用 General、其他 Diagnostic 和 Case，不增加第七份 Skill。

## 九类 Case 与 Action Trace

以下步数指概括性科研决策节点，不是终端调用数。每节点含实际动作、观察、决定、依据、假设更新、方向变化及来源。每案均含背景/初始条件、初始高层假设、结果等级、限制及迁移经验。没有记录当时理由的地方明确为未知；后验假设更新标注为 retrospective，不伪装成当时的私有推理。

| Case | 节点 | 保留的重要分支与结果 | 证据等级 |
|---|---:|---|---|
| M1 | 7 | 起始结构局部工况失败、有限继续仍失败、结构假设、逐工况重新适配、同结构联合验收与选择 | 原冻结注册任务的历史接受；不是自主 LLM 发现或硬件证明 |
| M2 | 7 | 实际外部 COM 载荷、原结构失败、结构比较、极小严格速度超限、内部搜索裕量后新 Replay | 原注册协议历史接受；原严格失败仍保留 |
| M3 | 6 | 初始搜索及位置/速度失败、借鉴 M1/M2 的结构假设、新任务重新适配及独立评估 | 开发草案协议接受；未升级为正式 Benchmark 批准 |
| M4 | 6 | 完整定时反转轨迹、任务绑定控制、首次独立通过、选择/封存及事后元数据边界 | 原注册跟踪任务历史接受；原 trace 未记录中途科研失败，不杜撰失败 |
| M5 | 6 | 实际工具帧、位置与有向工具轴联合适配、近阈值接受、无额外扰动/重复性实验 | 原注册位置/工具轴历史接受；不是完整姿态或 roll 见证 |
| M6 | 7 | 接触/数值失败导致不完整、材料变化后完整但任务失败、路由假设、重新适配、带真实工具的联合接受 | 原注册加载定向跟踪历史接受；没有证明唯一材料或路由原因 |
| C1 | 7 | 错误负载设置及保留成本、较少通道有限失败、基线数值失败、共享结构联合见证、局部尺寸比较、独立复核及采样间速度超限 | 原采样协议的有界开发见证；没有全局最少通道数或连续时间速度保证 |
| P3 | 12 | 初始静力失败、静力通过后动态 INVALID、序列化 UNKNOWN 与后续只读无效诊断、无效消融、有效稳定配对、独立复核、细网格 INVALID | 被动开发模型的有界数值见证；空间推广不成立，未作 formal SELECT |
| PHS-2D | 12 | 初始未合格基线、另授权静力/KKT及卸载检查、残差/步长、有效但性能失败、局部 Jacobian 有限变形失败、局部修改/抽象路线、版本/成本、缓慢尾段、实体导孔混杂、联合见证及独立/细步长/扰动检查 | 有界多工况开发数值见证；未作 formal SELECT，不是稳定性全局证明 |

PHS 的原九个科研节点全部保留，并吸收原专家过程中的局部修改、材料尾段和实体安装分支，整理成十二节点。P3 保留原十二节点。其他七案与各自原 trace 的节点一一对应；只抽去可恢复成功设计的信息和不必要的底层事件编号。这里的“完整”针对已保存的高层历史 trace，不声称补出了原资料没有记录的行动或理由。

九条 General 覆盖：单侧张紧/松弛、路由与有限变形、平衡/KKT/稳定性、材料/密度/截面/惯量、多工况、机制与任务敏感性、主动输入与外部载荷、任务观测量与时间范围、有限搜索/严格边界/最小性。它们独立保存条件式物理解释、来源与置信。

十一条 Diagnostic 覆盖七个要求症状、一个被动方法选择入口，以及主动保持速度、接触/不完整、近阈值判读。每条均按 `Symptom → Hypotheses → Discriminating Evidence → Diagnostic Action → Interpretation` 组织，至少三个竞争解释。三条 Validation 保存资格、Replay/细化/扰动和主动协议经验；没有复制任何正式任务数值阈值。

## Main、Reporter 与历史答案隔离

新组织的 CURRENT_RESEARCH_PACKET L0 仅有四类数量/搜索入口、六份流程及一份 Expert Process 的简短能力入口。不会注入案例正文、理论、诊断链或验证全文。L1 可按 `type` 搜索元数据，或精确 `detail=summary` 阅读；L2/L3 用同一 exact read 获取单条完整 Action Trace/流程，当前允许的原始科学证据仍走原 `evidence_read`。摘要与完整正文的阅读收据分别统计，摘要不会获得 `body_delivered` 的完整正文信用。

Reporter 的显式相关 `experience_queries` 仍可使用。未指定时，新组织最多从当前冻结目录自动读取两条相关 Knowledge，优先匹配 question/focus，再匹配当前报告诊断字段；没有匹配则不自动加载。匹配使用确定性的触发词，不声称具有语义理解保证。没有默认全库正文加载。

Reporter 继续要求当前科学 `source_ids`，Knowledge 不进入科学 `source_catalog`。新增 `knowledge_refs` 只接受已实际投递给这次 Reporter 的精确条目身份；它们保留到保存的解释及 Main 反馈投影。`new_information`、`supported_explanation/weakened_explanation`、`hypothesis`、`unresolved_question` 分别用于事实新信息、解释、竞争假设与未知。模型输出不能替换保存的确定性结果、注册证据或选择参数/停止。

九个历史原始成功条目均为 benchmark-sensitive，新配置不授权它们。新 Case 不包含成功结构的精确材料/几何/路由/放绳参数、XML、控制序列、成功候选标签、原 Store artifact ID、数据库/原设计重建位置。历史来源仅给不授予读取权限的逻辑来源及原记录哈希；精确来源链保留在原资产中，未复制进 Main 可读 Case。

本组织的通用证据读取和短引用选择进一步限制为当前 Study 的已有输出/注册域和科学引用。即使同一 Store 中存在另一个未属本 Study 的 artifact，知道哈希也不能通过普通 `evidence_read` 或短引用目录取得它。不存在文件路径读取入口。此处证明的是科研 Main/Reporter 的现有工具边界；维护者 Codex 为整理历史而读取仓库原资产，不等同于给科研 Agent 开放操作系统文件访问。旧冻结 Study 的既有显式授权和语义不重写。

## 必要验证

使用现有 Python 环境、真实 Store/Strands SDK 与 Mock HTTP，新增四个定向测试，未增加物理测试集：

1. 四类加载、九 Case 节点、必需元数据、精确交叉引用、旧默认/旧配置的隔离。
2. 实际 SDK 的 L0 索引、摘要与完整 PHS Action Trace 按需送达、分开的阅读进度；零数学/物理调用。
3. 分类及任务检索、全部组织内容检查、九个原始成功条目拒读、同 Store 外部 artifact 拒读及不被短引用公布、路径输入拒绝、当前检索收据仍能正常读取。
4. Reporter 自动选到相关腱松弛诊断、至多两条真实读取收据、Mock HTTP 保存引用知识的假设解释、Main 反馈及精确解释读取、未读 Knowledge 引用被拒绝、确定性结果未改、无科学证据/验收信用增长。

此外定向运行旧被动知识 SDK、旧 Reporter 只读协议、旧主动 Knowledge 过滤/采纳、原六 Skill 冻结配置及原 PHS 专家提示六项兼容性回归。共十个定向测试通过；对最后扩大为九个原始案例拒读的测试另作单项复核。`git diff --check` 通过，既有 manifest 行与原 Knowledge/Skill/案例正文、原配置均未改写。

这些检查证明分类、读取、保存和隔离协议；Mock 回复不是自主研究表现或新的物理结论。本次阶段一补充单独提交，不消耗原真实研究请求预算，不重算封存历史，也不改动此前阶段二、三结果。
