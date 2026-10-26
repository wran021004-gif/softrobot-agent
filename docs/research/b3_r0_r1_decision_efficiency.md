# B3 R0/R1：科研决策交付修复与有限自主研究

2026-10-26，Asia/Shanghai。基线 `research/b3-m2-live-pilot@f98b979fbbc69f77f8593ad1759cb4a761545332`。
独立工作树 `.worktrees/b3-r0-decision-efficiency`；旧工作树、未跟踪文件及 M2 STOP Store 保持原样。
授权来源为用户本轮附件 `64a01c75-f0df-477b-95aa-ad3d952d4231/已粘贴的文本.txt`。

## R0：已完成的最小修复

M2 C 逐轮审计已证实：native 方法的完整 L1 反馈带 `execution_limits=8/2/4`，
SDK offload 后该字段可能处于被截断的中间；`mathematical_catalog` 已保留它，
但 `compact_scientific_delivery(decision_only=True)` 再次按白名单投影时删掉它。
因此不能将后来的所有越限都解释成模型明知上限仍忽略。

修复仅让原 `native_control_limits` 派生字段通过 L0，未增加第二份限制配置。
候选身份仍由目录顶层 candidate 和方法键标识；同一短包每次在 SDK offload 后加入完整 wire，
Handoff 新会话继续从 Store 重建，因此无须扩展 `session_handoff.feedback_delivery` 或复制历史。
大型反馈仍有原 `original_result_query`；完整方法、矩阵、控制和轨迹仍在 L1/L2。

| 已有文件 | 最终行为 |
|---|---|
| research_context.py | L0 保留 execution_limits 及两个准确的 L1 查询，不复制方法详情 |
| task_constraints.py | 实测 NMPC 控制初始化 source/parent 查询；已授权 T2 缺模型组时给 readiness 查询和准备说明 |
| agent.py | 真实 Plan Schema 对有实际候选的四类动作要求非空 decision.selected_candidate；缺动作 payload 指明字段；非 evidence_read KeyError 不再误报 JSON Pointer；不支持方法—模型组合、protocol 扩展和控制 parent 反馈精确化 |
| contracts.py | 现有候选/source/parent、analysis protocol、JSON Pointer/fields 描述明确绑定和按需读取；不改变 Plan 版本或替 Agent 填参 |
| native_control.py | 原 not_applicable 原因显示选定状态时间、收到的窗口及冻结初态 0 s；数值算法不变 |

Schema 不能表达两个 EvidenceRef 的运行时相等关系；原 `admit_decision` 仍是唯一权威验证，
未复制候选身份检查。R0 减少的是重复调用错误的接口来源，不宣称此后模型永不犯错。
T2 保留 registered / study_authorized / authorized / applicable / executable 和实际 missing，
准备提示不覆盖依赖、预算、STOP 或收尾保护，也不自动选参数/执行 T2。
原 readiness 提供五个授权参数的值/界、h 与 h/2、模型组、成本与原请求模板。

## R0 验证与资源

六项定向 unittest 全部通过（59.432 s）：

- 新 M2 B/C 原始完整 wire 对照：开局、首反馈、收尾各一边界；真实 formatter 和 Schema；同会话及 Handoff 投影。
- 新真实 Schema 和准确错误反馈：缺 candidate、缺 selected_candidate、非指针 KeyError、JSON Pointer 子键、MuJoCo/instantaneous_braking 不支持及非法 protocol。
- 复用 M1 缺组/完整组/原 dispatch/生成/L1 测试（明确的离线合成模型，不是新数学证据）。
- 复用 B3 G2 完整历史 wire、offload 及 L1/L2/历史所属 Study 隔离两项回归。
- 复用真实 SDK request-feedback rotation（显式 mock HTTP，原恢复/配对边界）。

简洁对照见 [offline_wire_comparison.json](../../evidence/b3_r0_decision_efficiency/offline_wire_comparison.json)。
原六个请求成员另用既有 `archived` 校验归档与内容身份；原 messages 和 STOP 身份未写回。
对照是离线重建的完整请求，不冒充真实新增发送。实际 rotation 是独立离线 SDK 测试。
首轮发现新增目录常量缺局部导入、archive fixture 用最终余额误触收尾保护，均已修正；
这些失败发生在零 Provider/科学执行下。保存对照重复了唯一 archive 测试，没有扩展全仓测试。
未修 S130 无关 fixture。

生产五文件 `+31/-14`，净增 **17 行**；测试只扩展既有 `test_b3_t2_readiness.py`。
R0 实际 Provider、真实数学、MuJoCo 步进、NMPC、PPO 全为 **0**。
读取了 M1/M2、C 逐轮审计、C3 A/B、F1/F2、G2 与 S140–S145；
保留局部模型平台/退化、历史跨任务及同输入预测对齐的科学边界，未重算封存实验。

## R1

R0 提交推送后，另建 `b3-r1-history-assisted-050`；使用冻结 B3 0.50 s 原任务。
拟冻结 Provider 48（保护 4）、公开操作 96（保护 6）、数学 26、独立物理 4、
NMPC 2、完整回放 2；两结构各至多一次 NMPC、native 分析及完整回放。
native 每次最多 24 callbacks、3 iterations、4 knots，全 Study native 积分最多 60,000；PPO 0。
实际身份、授权、Agent 行动、用量与停止证据将在执行后填入本报告，不将计划上限算作已发生计算。
