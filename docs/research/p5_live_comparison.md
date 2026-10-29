# P5 真实首次科学行动对比（2026-10-29）

两组真实测试已完成并停止。DeepSeek Flash none 与 GPT-5.6 Luna none 都自主提交了合法生成 Plan，
经正式工具生成了一个有效候选。DeepSeek 随后消费反馈并完成控制初始化；Luna 形成了下一步选择和正确的局限说明，
但未完成下一项科学 Plan 的执行。两组都没有物理任务正式通过，也没有成功的模型 SELECT/STOP。

V2 工作目录为 `D:\softrobot-agent\.worktrees\research-harness-v2`；
Gateway 为其下 `local-chatgpt-gateway`。无需另开同端口网关。

## 授权与公平性

用户在本次对话明确授权：先用已验证的 DeepSeek 做足够决策机会的真实测试，再改为 GPT-5.6 Luna 测试并比较。
执行前已公开采用 P5 待授权方案：**每组 9 次共享 Provider 请求，最多前 6 次探索、最后 3 次只收尾**，
Reporter 同账本。总上限 18 次，不做 Echo、不自动网络重试、不换模型、不创建替代 Study 清零。

两个正式身份为 `p5-m5-deepseek-none-20261029-a01` 和 `p5-m5-luna-none-20261029-a01`。
旧 P4 的 7/8 账本及失败记录没有恢复、追加或修改。新两组分别持有用户本轮批准的独立有限额度。

两组冻结了相同任务、FamilySpace、起始指令、来源范围和资源计数：

- 原 M5/BF5 任务 identity：`5bf2dfd66aa0e480abae53b1d502677b06891339c40573cae8af00d8296db3ab`。
- FamilySpace identity：`21318db517b2a2a701cc65e51716b9edd1ef64e41b8e80339c1a95af9f38f64b`。
- 相同起始指令 identity：`d21e02574b13ba660cc631cadeaeac2fde67ebd6ef49a589355369dd557fa654`。
- 起点是 P4 第四次反馈之后的已读参数域，不包含此后结果；完整域作为只读起始资料直接供应。
  当时 current_intent 实际为 null，按原值保留，没有人为编造研究意图。
- 每组原科学资源上限为数学评价 2、独立物理启动 2，原 native control 上限不变；无 PPO、额外 NMPC 路线或验收放宽。
- Main/Reporter 均显式 none；实际 Reporter 请求均为 0，未声称真实 Reporter 分支已经覆盖。
- 两组统一 `--no-session-handoff`，在一个持久 SDK 会话内接续真实工具结果。
  没有预先伪造 Luna 的实时 Handoff 准入，也没有运行第二套 Harness。

这不是严格模型排名试验：每个模型只有一条轨迹；Provider 原生参数、Tokenizer、输出限制不同。
Luna 组还暴露工程故障并在原账本内修复，故不能将请求数或成败差异全部归因于模型。
本次没有私有 M5 经验短卡，不能与有该经验的旧 R2 做无条件行为归因。

## 实际额度与成本

| 项目 | DeepSeek Flash none | GPT-5.6 Luna none |
|---|---:|---:|
| 账本 Provider 尝试 | 9/9 | 9/9 |
| 上游完成推理 | 9 | 8 |
| 本地拒绝、未进入上游推理 | 0 | 1（第 2 次 HTTP 400） |
| 探索阶段上游推理 | 6 | 5 |
| 收尾阶段上游推理 | 3 | 3 |
| Reporter | 0 | 0 |
| 已知 prompt Tokens | 127,612 | 83,177 |
| 已知 completion Tokens | 5,471 | 1,735 |
| 已知 total Tokens | 133,083 | 84,912 |
| 全账本 usage 是否齐全 | 是 | 否，本地 400 无 usage |
| 实际费用 / ChatGPT plan 额度扣减 | unknown | unknown |
| 有效候选 | 1 | 1 |
| 已初始化控制源 | 1 | 0 |
| 数学评价 / 独立物理评价 | 0 / 0 | 0 / 0 |

合计 18 次已扣账尝试、17 次上游完成推理，没有自动重试或未知待确认结果。
两组已知 usage 相加为 217,995 Tokens；这不是含缺失项的精确全账本总额，不把缺失 usage 写成零。
Luna 的本地失败照常消耗原账本，没有退款或补发第十次。目录查询不属于推理次数；Gateway 每次推理前仍有原有目录准入检查。
API 公共价目不等于本次 ChatGPT plan 实际计费，因此没有据此计算费用或声称 Luna 最便宜。

## DeepSeek 每轮结果

| 次数 | 实际调用及结果 |
|---|---|
| 1 | 自主 route 到 generate；仅选工具，没有科学执行。 |
| 2 | 提交具体结构 Plan；把 FamilySpace 写成 supporting_evidence，被 `UNREGISTERED_RESEARCH_EVIDENCE` 拒绝。 |
| 3 | 读取并解释拒绝，移除错误引用后重新生成；重复 guide_s=[0.5,0.5] 导致生成结果 invalid，原因 `ORDERED_UNIQUE_GUIDE_STATIONS_REQUIRED`。工具完成不等于候选成功。 |
| 4 | 根据真实失败反馈，自主改为有序 guide_s=[0.3,0.7]；正式生成、编译和结构检查通过，产生候选。首窗口至此停止检查。 |
| 5 | 明确读取生成成功及检查事实，说明不构成物理通过，自主 route 到 initialize_control。 |
| 6 | 提交合法 initialize_control，实际生成覆盖六个执行通道的完整控制序列；task_acceptance=unmeasured。 |
| 7 | 正确认识尚无独立评价，但在保护期尝试不存在的 evaluate_task route，被动作准入拒绝。 |
| 8 | 说明无任务成功、应停止，调用 research_plan/stop；当时 Plan 已因旧选定动作过期而被卸载，返回 Unknown tool。此处有确认的工程因素。 |
| 9 | 根据反馈 route 到 stop，但没有余量再提交 STOP；选择不等于提交。随后原额耗尽，执行工程封存。 |

真实候选为 `1b3413e66002341cb60ab8ae108f1e70e2a69cfb62aff85e3607d2568ceadc20`，
控制源为 `98b56a347dea92878c90c2c0ff8bfd7c47166edb782ab9ea264d155d39df61d8`。
这些是模型自主选择的结果，不是 Supervisor 预填参数。结构可执行与控制序列完整不证明任务可达或物理成功。

## Luna 每轮结果

| 次数 | 实际调用及结果 |
|---|---|
| 1 | 经真实 Gateway 上游完成响应，自主 route 到 generate。 |
| 2 | 本地 Gateway 拒绝接续：`Provider output call identity mismatch`。已停止排查，没有进入上游推理。 |
| 3 | 确认并修复参数字节恢复后，在原账本内首次向上游发送该接续；HTTP 200。自主提交生成 Plan，但缺 generation，收到 `TOOL_SCHEMA_REQUIRED`。 |
| 4 | 消费反馈，补全 generation；省略 version 在当时 Schema 合法，却被运行时按 V1 默认解析，V2 构建器返回 invalid。没有候选。 |
| 5 | 显式版本 Schema 修复后，模型自主提交带 serial_family_generation_v2 的完整 Plan，生成有效候选。 |
| 6 | 基于生成反馈自主 route 到 initialize_control。选择已记录，尚未执行控制初始化。 |
| 7 | 已进入保护期，改为 STOP；正确说明结构有效、物理未验证，但引用未注册的候选/包装资料，受到 `UNREGISTERED_RESEARCH_EVIDENCE` 拒绝。 |
| 8 | 根据反馈 route 到 evidence_read。 |
| 9 | 查询 /citation_eligibility 时使用了错误 reference，不是反馈所给 inventory_query 的 FamilySpace reference，受到 `TOOL_SCHEMA_ENUM` 拒绝。额度耗尽后工程封存。 |

有效候选 reference、模型原始参数、每轮 Schema identity、call ID、反馈及原始回执引用全部见
`p5_comparison_results.json`。没有将 Luna 的本地转换失败当成模型不支持工具，也没有把 invalid 生成包装成成功。
按真实完成推理计，两组都在第 4 次上游推理时产生首个有效候选；这个单次观察不构成质量或成本排名。

## 本次确认的最小工程修复

1. **正式注册缺失。** 准备 Luna Study 时注册表没有 chatgpt_gateway@8.0.0，零推理阶段即拒绝。
   在原 manifest 增加指向现有 build_harness 的一条模型适配注册，没有新建 Provider/Harness。
2. **原始参数与 opaque output 未共同恢复。** SDK 把紧凑 JSON 重新序列化为带空格 JSON。
   Gateway 严格字节比较因此拒绝第二次请求。现在原回执同时拥有 tool_calls 与 provider_output，原参数字节保持一致。
   离线重新转换失败输入的修正版本已通过；之后的真实接续也通过。没有改写 SDK 工具结果或放宽 Gateway 身份校验。
3. **版本默认歧义。** 新 V3 Schema 现在明确要求 generation.version，避免允许省略但运行时落入旧 Union 默认 V1。
   旧冻结版本不重新解释，也没有替模型填写版本以外的科学参数；实际新 Plan 仍由模型生成。
4. **保护期丢失 STOP Schema。** 新 V3 在旧 Plan 动作已不可用时保留合法 STOP 契约；仅加载，不自动提交。
   旧 V1/V2 语义保留。DeepSeek 已封存，不回头重跑来抹去该缺陷的实际影响。

Luna 的修复接续均有明确新证据和变更后的请求，失败及费用保留；第二次请求没有抵达上游，
第三次不是对已执行上游输入的重复采样。没有 Provider 自动重试、改模型、隐式降级或猜 slug。

尚存问题分开记录：错误引用 supporting_evidence、漏填 generation、错误动作名、错误查询 reference 是模型输出问题；
Schema 可省略版本与旧默认不一致、保护期卸载 Plan 是工程问题。工具切换的请求成本和如何清晰表达引用资格仍值得观察，
但未证明应再增加 Planner、校验层或提示补丁。本次没有扩建架构。

## 接续、恢复及上下文证据

只读审计验证了每次 request 的规范 JSON digest 与计费 receipt 一致，Gateway/Provider 原始 HTTP 响应 bytes 的 SHA256 可恢复；
两组的已返回工具结果文本与保存的原始反馈逐字一致。Luna 唯一原参数字节不一致是已保存的第 2 次失败，修复后所有接续均一致。
Gateway 仅在 response.completed 路径返回成功；8 次 Luna HTTP 200 均沿该路径完成。
原生 function_call 项与参数保存在响应中，后续请求保留原始 call ID 和对应结果；none 的返回 usage 中 reasoning_tokens 为 0。

完整上游 SSE 未单独归档；保存的是真实 Gateway 响应体及其原生 output 项，不声称拥有未保存的完整上游网络抓包。
本次原生 output 主要为 function_call，未凭 none 测试宣称 medium 加密推理接续已经验证。
完整模型输入、响应、SDK 会话和 Store 均在 ignored 本地目录；公共 Git 不发布完整 Provider 请求或 opaque reasoning。

完整本地请求最大为 DeepSeek 61,672 字节、Luna 64,829 字节，均小于 Gateway 1 MiB 限制。
本次统一关闭自动 Handoff，因此历史随同一 SDK 会话增长；这些实际成本不能当成自动 Handoff 下的长期成本估计。
此前 P5 离线 R2 同边界的去重结果仍为 8,919 → 8,120 Tokens，反馈和 generate 保留；本次没有重新写旧指标。
真实结果证明输入足以支持行动，但不是压缩造成更好行动的因果试验，也没有比较 none 与 medium。

## 等级与下一步

| 等级 | DeepSeek | Luna |
|---|---|---|
| D1 合法且有研究依据的 Plan | 通过，第 4 次产生有效生成 | 通过，第 5 次账本请求产生有效生成 |
| D2 实际新候选/结果 | 通过，候选及后续控制源 | 通过，有效新候选 |
| D3 消费反馈并形成下一决策 | 通过，第 5–6 次解释候选反馈并实际初始化控制 | 部分：第 6 次选初始化，第 7 次正确解释局限；没有提交并执行下一项科学 Plan，STOP 也被拒绝 |
| D4 正式任务通过及规定 SELECT/STOP | 未达到 | 未达到 |

总体已经用真实调用证明 Main 能自主开展一次有依据的科研行动并利用反馈继续决策。
这不等于完成 BF5，也不证明找到可成功执行任务的结构。最终封存均为工程额度收尾，不是模型成功 STOP。

目前无须强制 medium 对照：none 已达首要生成目标，应先巩固收尾和证据引用行为。
可以准备下一阶段有独立物理评价机会的有限 Study，但没有自动开启完整长期科研的依据或追加额度。
若要严格比较模型，应在统一修复后的冻结实现、同一背景和实际正常决策机会下预注册配对预算；
本次不为获得更漂亮结果另开重复 Study。

## 验证与提交

- 平台/Gateway 准备及原有验收 4 项通过。
- 原参数恢复 Provider 回归 7 项通过；Gateway 请求转换 20 项通过。
- 生成版本、保护期 STOP 和预算/Handoff 定向回归 6 项通过。
- 原 recent-round 路由及恢复回归 9 项通过，未改变旧版本的已验证语义。
- 最终只读回执审计：两组 Store 检查前后 SHA256 一致，pending Provider、pending science、unconsumed response 均为空。
- 发布前 14 个相关文件与两组当前 credential 的精确匹配为零；这是定向检查，不是通用秘密识别证明。
  旧 P4 复核仍为 stopped、7 次 Provider 使用。
- 原任务、独立 evaluator、数值内核没有修改；没有科学 Worker、PPO 或额外科学预算消耗。

配置冻结提交 `f39a926c4`；注册修复 `919423894`；参数字节恢复 `56027977c`；版本及 STOP 契约修复 `f332b619a`，
均已 push 到 `origin/mainline/research-harness-v2`。
DeepSeek 实际执行绑定为 `919423894c8c065da253fd8d799a69d9132958a1`；
Luna 最终执行绑定为 `f332b619a` 对应完整提交（详见回执审计），中间迁移没有重新解释旧调用和预算。
最终脱敏审计及中文报告另由结算提交收录，最终 HEAD 见交付消息。
