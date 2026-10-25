# C3-P0：数学搜索与对照实验准备（不执行正式实验）

2026-10-25，Asia/Shanghai。基线 `e28fda1eda0da3f695ac7ef1862b2ed2df258e58`，
远端 `research/c3-autonomous-softarm-study` 核验一致；独立分支
`feat/c3-math-search-readiness`，独立 worktree；其他工作树和封存证据未修改。

## 1. 请求上下文

只读 `evidence/c3_blank_autonomous_softarm/immutable_artifacts.tar.gz`，
脚本 `python -m tests.research.c3_readiness_audit`。数字是完整 httpx JSON 请求的 UTF-8 字节，
token 是仓库固定 DeepSeek tokenizer 对序列化 JSON 的离线估算，不是 Provider 实报。

| 主请求边界 | 原始字节 / tokens | 保留旧历史、替换 L0 | 原验证 Handoff 后完整请求投影 |
|---|---:|---:|---:|
| 1 | 84,965 / 22,565 | 84,965 / 22,565 | 85,175 / 22,608 |
| 13 | 332,894 / 95,218 | 309,577 / 88,852 | 109,400 / 30,284 |
| 25 | 639,373 / 188,692 | 597,672 / 176,378 | 88,944 / 26,996 |

末轮 Handoff 投影减少 86.1% 字节；未轮换会话仅减少 6.5%。第一个边界无历史可去掉，
短会话说明反而增加 210 字节，不应为了数字好看宣称所有边界均改善。
早/中/末 Schema 分别 51,622 / 51,622 / 15,730 字节；系统指令均 4,735；
Assistant 历史 0 / 170,100 / 452,431；工具反馈 0 / 30,263 / 56,293；
当前 packet 26,096 / 70,420 / 101,645。分项各自带 JSON 框架，不能直接加总。

实际重复：末轮数学 baseline signed excess `61.52347153119494` 出现 4 次，
瘦身后一次；物理保持误差 `0.19304308687570046` 从 5 次到 3 次
（物理指标、临界样本、带源 Reporter 假设内仍可能重复）。数学 quantities 与 comparison
重复相同分数，L0 又重复旧数学结果；方法目录大量重复 coverage 和说明。
现在保留状态/成本/缺失前提及精确详情查询、当前核心问题、最近动作、少量结果，
原矩阵、控制、推理、Reporter 全文、候选与完整 STOP 索引继续在原 Store。
完整任务和 controller schema 本阶段保留，未改科学语义。

原 C3 pilot 没有 Handoff 准入标志。新增 `--handoff-request-bytes`，例如待批准运行时
配合 `--session-handoff --handoff-request-bytes 160000`，仅在原已验证的
request-feedback 边界轮换；完成 invocation 的原轮换机制不变。
必须先获得原 `session_handoff_live_admitted` 与 `session_handoff_boundary=request_feedback`
准入，不能绕过；未知请求/worker、未配对工具、未交付 Reporter 仍阻止轮换。
离线投影不是已恢复封存 Study 或已开展 live continuation 的声明。

STOP/SELECT、预算、推断限制和原始证据引用保留；Reporter 解释在决策投影中显式标为 hypothesis。
旧 SDK 历史、原请求/响应和报告均不修改。原 C1 投影 API 默认保持历史行为。

验证：8 项 request-boundary/provider-context 定向测试通过（mock HTTP，无外发）；
首次因本 worktree 的 Windows MAX_PATH 失败，缩短测试专用 ID 后通过。
C1 历史上下文测试另有既存环境相关失败（80,255 ≥ 78,644），已用原 HEAD 代码在内存中
复现同一结果；没有改写历史验收来隐藏它。其余 C1 3 项通过。

## 2. 搜索发现、计费与效率

空池也提供 `structure_actions`：generate 使用 **generation** payload；search 使用
`family_mixed_search_v1` 与 `variable_groups`；已有候选分析使用 research_analysis。
列出必填字段、冻结 grant、fidelity、三种 objective 的不同含义及禁混旧字段。
family 模式只广告当前 generation 和 mixed search Schema；原 source-relative Plan/执行解析保留。
不替 Agent 选择 objective、拓扑或参数块。

只读几何轨迹脚本使用真实 `family_space_v2`、原 mixed_moves 和 generator，固定 incumbent，
没有优化评分、CONIC 求解或科学 worker：

| 子空间（工程示例） | 依次访问的前几个坐标 | 12 数学额度覆盖 |
|---|---|---|
| 全部块，1–3 段/3–4 腱 | initial、段数、腱数、length.0、young.0、section.0.semi_y | 6 合法新结构，6 模型准备 + 6 CONIC |
| lengths + materials，固定 3 段/3 腱 | initial、length.0、young.0、length.1、young.1、length.2 | 6 新结构；young.2 尚未访问 |
| routing + sections，固定 3 段/3 腱 | initial、phase、semi_y.0、guide_s、semi_z.0、anchor_s（重复）、width_y.1 | 7 提案，6 新结构 |

完整组的 spans 只有 whole_chain 一个策略，因此没有活动 span 坐标；路由未轮到。
以上不是任务重要性排序，也不保证实际评分更新 incumbent 后访问顺序不变。
未出现非法结构或仅改表示的有效评价；确认 anchor_s 已在上界，正移动裁剪无变化。
有限自选 bounds 的长度也复现此问题。新增最小去重：构建前发现重复 request 时记录
`skipped_moves`，消耗 proposal、不构建、不新增数学评价；原 receipt 复用和失败费用保持。
不新增算法或重要性启发式，继续按 Agent 给定 variable_groups 顺序轮换。

计费明确区分 proposed_designs、legally_constructed、actual_mathematical_evaluations；
CONIC 内部 branch 由原 conic_subproblems 计算，物理启动独立。rank 仍只把 computed 的
有限数学分数列为有效，失败为 unknown/unsupported，正负和最大/最小方向不变；任务接受仍 unmeasured。

5 项核心搜索回归通过：合法公开 Schema、旧/新字段拒绝、裁剪去重计费、真实生成候选与 lineage、
已封存分析的中断恢复复用、失败和非法候选费用。13 项旧 mixed suite 中另有 3 项既存快照/环境断言
不适用于当前基线（旧 configuration digest、六段失败源身份、未设置线程变量的 execution 门禁），
不修改科学身份/环境门禁去迎合旧断言。

加入搜索 Schema/发现后重新计算完整请求：早/中/末的保留旧历史请求为
76,681 / 301,293 / 599,722 字节，短会话投影 76,891 / 101,116 / 90,994；
相应短会话离线 tokens 20,459 / 28,135 / 27,606。末轮字节减少 85.8%。

## 后续阶段

搜索轨迹、半径敏感性、数值快照与实验配置在后续阶段补齐。此文所有工程夹具不构成科研成功。
