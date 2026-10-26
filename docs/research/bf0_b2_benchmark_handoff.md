# BF0：B2 v1 Benchmark 收口与交接

2026-10-26，Asia/Shanghai。B2 v1 是已有物理可行性及有限算法结构辨别力的结构—控制联合设计 **Benchmark 候选**。本轮不修改冻结任务、不重新实验；联合包装见 `configs/research/b2_joint_benchmark_v1.json`。包装不是新 TaskDefinition，也不是已注册的多任务 Study。

## 基线与已有证据

远端核对：B=`f28c00d79f9736aea9a8d024dd9e0b3f103f0b8e`，A=`d7b0f91f966ef96fa17b181ead99dff9a2d457cc`，与用户指定一致。B 原工作区干净；仓库主工作区已有大量无关未跟踪文件，未处理。独立 `research/bf0-b2-benchmark-handoff` 从 B 建立，A/C 仅只读。分支差异包含 B 的任务/证据/固定程序与 A 的统一研究反馈修复；A 已有共享外力运行时及 C3.3 说明，无须重移植，也不能整分支互相覆盖。

首个同结构双条件独立可行见证消耗 899,500 次积分尝试。另立账本的独立对照消耗 5,472,309 次积分尝试，包含 8 次数值失败调用；已确认正常完成 5,472,301 次，失败调用内部进度 unknown。四结构×双条件×双起点共 16 案例。历史匿名 S3 两起点均通过，等六通道 S2 的受力条件仍失败，支持共同初始化、冻结任务、既有控制算法及有限机会下的腱路布置收益。首解与对照合计 6,371,809 次科学积分尝试，B1 的 4,360 工程步单列。

来源为 `docs/research/b2_first_feasible_pair.md`、`docs/research/b2_structural_contrast.md`、`evidence/b2_feasibility_search/summary.json` 与 `evidence/b2_structural_contrast/summary.json`。这些是维护者证据，**不得作为 Cold-start 背景**。现有标签和标量保留，不公开其精确结构映射。BF0 只检查公开摘要的一致性与冻结来源，不声称重新打开或重验全部私有原始结果。

## 联合任务契约

原 `tasks/b2_load_hold_{zero,force}_frozen_v1.json` 的文本 SHA-256 及任务版本由包装引用；原文件、原 `source` 与原准备配置中的历史 unmeasured 状态均不改写。摘要状态演进不能回写成搜索前已知。任务内涵身份用 `digest(task)`，文件身份用通用换行 UTF-8 SHA-256，二者不同。

同结构指 `same_robot_structure()` 比较的 robot family 与完整 structure 相等（含被动尺寸、材料、腱路、导向孔及每通道上限），并要求相同离散物理网格。不同条件的环境外力与控制可不同，不能要求包含 task 的整个 model identity 相同。各条件模型身份必须分别匹配其真实模型。生成时将空 qpos/qvel 字典按实际命名自由度展开为全零，所以执行任务 digest 可以不同于任务文件内 task digest；必须保留原任务文件哈希、展开后的 TaskDefinition、有效配置身份及这一步确定性展开，不能把两者混称。

| 项目 | 冻结含义 |
|---|---|
| 目标 | 世界坐标 `[0.29,-0.035,0.19]` m |
| 时域/积分 | 0.35 s / 0.0005 s；完整轨迹 700 次积分调用 |
| 控制/记录 | 0.01 s；35 段合法绝对张力 ZOH，控制边界为 0…0.35 s 共 36 点 |
| 初态 | 当前结构全部命名 qpos/qvel=0，seed=17；每条件独立重新建初态 |
| 重力/接触 | 原 `[0,0,-9.81]` m/s²、安装位姿、地面及接触设置全部保留；Native 的无接触适用范围仍有效 |
| 无力/受力 | 无力；或 payload body COM、世界恒力 `[0,.02,-.03]` N、窗口 `[.10,.35)` s；不是附加质量或 tip 点载荷 |
| 终点 | 原注册 `evaluate.reach@1.0.0`：位置误差 ≤.010 m |
| 保持 | 原 profile：最后 .05 s，`.30,.31,.32,.33,.34,.35` 六个包含端点采样，最大位置误差 ≤.010 m、绝对世界 tip 速度 ≤.020 m/s |
| 张力 | 按该结构 tendon_order，有限、非负且不超过各自 force_limit_n；FamilySpace 原执行上限不放宽，默认上限 8 N |

`binding()` 检查每条件轨迹 task/model/design 身份、张力形状/顺序/范围、完整时间网格和 ideal_tension。必须分别保存控制源及 `schedule_identity`，独立 `playback_tensions` 原始结果、注册 endpoint evaluation、profile 和 `assemble_acceptance`。正式通过包含 evaluation_validity、execution_complete、task_evaluator、evaluator:task_bound、solver_errors、force_bounds、holding_coverage、holding_position、holding_speed 全部通过，且身份一致、无 issues/missing。Native 搜索分数、数学证书和自验不能代替这些来源。

联合通过只在**同一结构的全部声明条件**各自有合法控制和完整独立 accepted 时成立。每条件控制可重新优化；不得拼接不同结构的单项成功。一个完整有效条件失败时保留具体 components、metrics 和超限，联合为未通过；缺失、未执行、覆盖不全、无效评价、数值错误保持未决/错误。若同时有有效失败和缺失，联合已不能通过，但完整联合评估仍未完成。数值错误保留警告、停止位置与成本，不叫结构不可行。历史通过是历史见证，不是本 Study 的新重复。

身份链至少保留：包装版本及 digest → 原任务文件哈希与确定性展开 → 有效配置/robot structure/网格 → 每条件合法控制源/模型/顺序/时间网格 → 执行请求和真实收据 → raw/evaluation/profile/acceptance 引用及内容哈希。公开摘要仅留标量和私有收据哈希，私有验收方持有原始链。

## 双条件公共入口审计与最小缺口

`examples/b2_fixed_search.py` 已能对同一生成结构顺序运行两个条件，经原独立评价形成首解，且有失败检查点和累计积分上限；它是固定程序，原配置不是后来成功研究过程的复现配方。`tools/research/config.py::resolve()`、`core.prepare()` 与 candidate 校验均围绕单一冻结 task。公共 Agent 有生成、控制初始化、Native 搜索和单条件 physical_replay 能力，但目前**不能直接以一个 Study 完成双条件 Benchmark 的任务切换、联合选择/确认和收口**。

现有 `aggregate_acceptance()` 不能直接消费真实 `physical_replay` 收据：fresh/reuse 都要求 `tool_id=simulation.run`；真实收据是 `research.physical_replay`。`physical_replay.recover()` 把 profile 内嵌在结果中，传 `profile_reference=None`，而通用来源审查要求独立 profile 引用；profile.execution_id 使用执行目录名，最终结果 execution_id 使用 worker_request_id，Store receipt 则另有 execution_id，不能假定三者相等。固定程序有独立 profile 内容哈希，但没有 Store 的 `simulation.run` 真实收据。聚合器的 observed fraction 也没有验证同结构这一联合条件。

因此 BF0 **不适配、不更改原聚合器**，不把历史记录包装成 fresh、不伪造 simulation 来源、不覆盖 accepted。安全适配前必须补齐以下真实信息：

1. 在真实 replay 结算时保存 profile artifact，显式绑定 Store execution_id、worker_request_id、raw/evaluation/profile/source/candidate 和冻结 task；保留原收据 tool_id 和真实计费。
2. 添加明确版本的 replay 来源分支/适配，核对这些 owned Store 引用、原完整协议、freshness/历史复用政策以及每条件合法控制；保留原 aggregation 对 simulation.run 的所有语义。不能只放宽工具名或只读 accepted。
3. 给 Study 一个冻结条件清单及同结构身份关联，在各条件有效配置下分别生成控制/执行，并联合 select/confirm；逐条件失败可回读，缺失条件不能从分母消失。

这些是正式 Agent Study 的最小运行接口工作，不在 BF0 重建调度器。本包装明确规定验收，并诚实标记入口缺口；已有完整私有见证不依赖通用聚合器成立。

## 允许的初始化与数学范围

恒张力、合法短时响应初始化、现有工具授权的其他方式均允许，需记录选择依据与全部成本。既有对照中 .2/.4 N 是起点标签，随后对所有结构用相同三次 .05 s 两尺度响应及原 constrained_response_step 产生合法常张力，独立短时检查后才进入完整优化。该方法是已有合法初始化，不能把历史成功向量预置给 Agent。`initialize_control` 的公开响应初始化与原 short_input_response 工具各有适用范围和授权，不能把私有三步驱动误称已经存在的单条公共命令。

SVD 张力映射秩只解释局部作用方向。固定控制敏感性不能证明控制重优化后的优势；A4、Native T1/T2 只能在实际支持的变量、模型和预算内使用，离散腱路不可伪造连续导数。有限预算结构比较不能证明全局最优性/失败结构无解。短时响应确实帮助本次初始化，但未做等成本消融，不能宣称数学降低总成本。无需每任务都调用数学；不增加算法、VOI 系统或后验结构推荐器。

## Cold-start 与预算交接

使用单独 checkout/导出、全新上下文、独立 Store 与明确可读范围。只提供包装及冻结任务、合法 FamilySpace 与实际可执行域、注册工具、必要工程默认/物理实现，以及 Agent 自己产生的证据。`family_space_v1` 只执行两个 segment，其他声明范围不代表可执行或有运行授权。历史报告、整个 evidence/research 档案、成功映射/控制、runs 下私有收据/驱动、旧 Store、Provider trace、历史聊天和 Git 历史检索全部排除。普通完整 Git checkout 加 `.gitignore` 本身不构成隔离。

现有上下文只导入 spec 明确声明的 supplied_evidence/research_decisions.background/history/mathematics/control_seeds，故未来设为空，不能把本报告导入背景。现有仓库内已有暴露控制/结构的历史工程证据，也必须从 Agent 文件可读范围排除；本轮不删除/重写封存记录，不新增复杂访问控制。本会话已看历史结果，不能担任该任务盲测 Agent。

未来正式 Study 需单独预算与授权，不继承 899,500/5,472,309 的剩余额度。计费主数为**积分调用尝试**；初始化、数学内部 rollout、Native 优化、独立回放、部分进度、失败及重试均计入。完成数、失败调用内部 unknown、model builds/forward、算法调用数和 wall time 分列；未测不能填零。固定累计账本与批准身份，换目录不清零；只在预先规则内续算。Provider/数学 worker/物理积分均须按实际报告。

BF0 验证见 `evidence/bf0_b2_benchmark_handoff/audit.json`：冻结哈希、公开 16 案例/计数、真实来源接口只读核对及原固定程序零积分定向测试；没有新 Provider 请求、物理积分或科学数学 worker。BF1/F2 属另立任务与预算，后续授权不回写 B2 历史。
