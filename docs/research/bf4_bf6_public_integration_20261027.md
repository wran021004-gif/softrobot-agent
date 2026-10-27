# BF4 / BF5 / BF6 公共生产集成

同步后的 A 基线为 `a1566b91a387316405bdb2fc79eb8a087ea20e8a`，B 来源为
`8a6a15d4667b946d4e1dd6b20e544cc8d683452a`。实现提交为 `af85bf94c`。
按文件和差异块选择性集成，没有整分支合并，没有导入历史成功结构、控制答案、私有 Store、研究额度或 R2–R8 运行配置。

## 公共入口与任务语义

| Benchmark | 公共配置 | Registry / backend | 原验收条件 |
| --- | --- | --- | --- |
| BF4 | `configs/research/study_tracking_public.json` | `task.tracking` / `backend.family_mujoco@1.2.0` | 0.02–0.60 s 共 30 个 post-step 真实位置误差，最大误差 ≤12 mm；`offline_timed_tracking_v1` |
| BF5 | `configs/research/study_bf5_public.json` | `task.position_tool_axis` / `backend.family_mujoco@1.3.0` | 原 0.58、0.60 s 位置 ≤8 mm、有向工具轴角误差 ≤3°；`offline_position_tool_axis_v1` |
| BF6 | `configs/research/study_bf6_public.json` | `task.oriented_tracking` / `backend.family_mujoco@1.4.0` | 0.02–0.60 s 共 30 个 post-step 位置 ≤12 mm、方向 ≤10°；真实刚性负载绑定、每个独立物理步无接触；`offline_oriented_tracking_v2` |

继续使用 `python -m tools.research`、公共 Registry 与 Agent 的 `research_plan`、
`research_analysis`、`evidence_read`：

1. `research_plan(action=generate)` 使用当前配置的 FamilySpace 生成候选。
2. `evidence_read(reference=candidate, view=mathematical_capabilities)` 读取候选的方法目录、请求模板及适用范围。
3. `research_plan(action=initialize_control, control_seed={candidate,...})` 返回候选拥有的控制源。
4. `research_analysis(operation=mujoco_direct_control_v1, model_source=mujoco, control_optimization={source,settings},...)`
   使用显式 v2 时间窗和 knots，返回未验收的完整控制序列。
5. `research_plan(action=physical_replay, physical_replay={candidate,source})` 独立执行；
   `evidence_read(reference=result, view=full)` 完整读取后，只有原验收全部通过的当前结果才有 SELECT 资格。

三个公共配置仍为待授权模板，Provider、物理与数学额度均为零。
集成没有授权自动启动正式 Study；正式运行仍须原有冻结配置、授权、预算和 admission。
测试 fixture 的 fabricated pass 只验证接口，不是新的 Benchmark 成功证据。

## 配置所有权与 B 的差异

BF4/BF5 主要能力在 A 已存在，本次没有重复实现。两者公共配置改用 B 已验证的
`family_space_bf4_s3_tracking.json`：holding/terminal speed 默认权重为零，使用原有
FamilySpace 组合、生成和控制校验。Reach/Hold 通用 FamilySpace 的默认值不变。
BF6 的负载 FamilySpace 也使用相同的合法零权重默认值，生成无需手动修补。

BF6 的任务定义保持 B 原文；刚性 payload 的质量为 0.020 kg，局部 COM 为
`[0.007,0.001,-0.002] m`，完整 COM 惯量含非零交叉项。任务拥有冻结负载要求，
FamilySpace 拥有实际设计，已有编译器生成真实惯性刚体；backend 检查编译后的质量、
COM、完整惯量和 tip site，拒绝用外力替代负载。
原 BF4 位置评价被直接复用，再组合每个时刻的有向轴评价。
独立回放逐 `mj_step` 记录接触事实，异常时仍保留负载和首次接触证据。

保留 B 的候选内 Native continuation：显式绑定之前的分析和失败回放，复用已记录回调，
不重积分历史前缀，不继承通过资格、不重置额度。只移植通用工具能力及 synthetic 测试，
没有移植 S2/R2–R8 的历史数值结果。

没有采用 B 对 A 的 Agent、Reporter、配置解析、预算、会话恢复、读取提示、
多条件 SELECT、draft 预览或真实回放收据资格的旧实现。
`research_context.py` 仅消费 TaskAdapter 声明的不支持路线；任务规则位于适配器边界。

## 方法限制

| 路线 | BF4 | BF5 / BF6 |
| --- | --- | --- |
| Native `mujoco_direct_control_v1` | 完整定时位置网格优化 | 完整位置和有向轴样本网格优化；BF6 使用真实负载 |
| GVS / affine / CONIC | 保留已有 sampled timed 模型、结构搜索及 Native 后续验证连接；模型计算不是物理验收 | 不覆盖方向约束，明确 `not_applicable` / 不支持完整任务；不能用仅位置结果证明完整任务可行 |
| NMPC | 保留已有定时 Tracking 路由 | 不支持有向轴控制；显式 Native 序列 backend 拒绝 NMPC 替代 |
| PPO | 保留原 Reach/Tracking 环境的适用范围与原授权要求 | 不支持 BF5/BF6；公共反馈明确 `not_applicable` |
| Native T1/T2 非线性能力/结构响应 | 保留原有不适用范围 | 不宣称 BF5/BF6 完整任务支持 |

BF6 公共模板只开放 Native 分析、控制初始化和独立回放所需能力，没有开放未验证的批量物理控制搜索。
BF6 的方向是工具轴方向，不是完整 3D 姿态或轴向 roll；没有连续时间位置/方向保证。
无接触条件则按原协议检查每个独立物理步。

## 定向验证与真实成本

定向集 70 项通过：三类任务、公共生成/发现/初始化/读取/SELECT、BF6 有效/失败/不完整状态、
负载和回放绑定、Native continuation、Reach/Hold、A 的任务协议与执行反馈。
Reporter 单独 13 项通过，Tracking 数学 7 项通过。
最终 BF6 公共模板与 Tracking 数学复查 8 项通过。未增加优化器或测试矩阵。

使用已有 `.f3-prestudy-env` 验证 CONIC；默认 `.mainline5-env` 缺少 `cvxpy`，没有安装依赖。
legacy 测试绝对导入需要将 `tests/research` 加入 `PYTHONPATH`。
CLARABEL 的既有 dual-face fixture 出现精度警告，原条件化诊断断言通过。
另有旧 `ReportingSessionTests.test_three_real_sdk_sessions_keep_tools_budget_and_bounded_input`
报 `KeyError: decision`，在未修改的 A 基线、相同环境上复现；未把它当作本次引入的问题或擅自修改会话实现。

只做了一次 BF6 实际路由检查：原生基线 1 次、独立回放 1 次，没有优化迭代或求解重试。
Native 在 0.225 s 检测到 floor/payload 接触，返回 `execution_incomplete`。
独立回放同样记录到首次接触，随后发生 `MUJOCO_NUMERICAL_FAILURE`，原验收为 `incomplete`，
完整读取后 SELECT 正确拒绝。20 g 负载的编译绑定匹配。失败诊断与原始 Store 均留在本地 runs。

- Native：225 个完成步、225 次物理步调用，1 个模型、1 个 rollout。
- 独立回放：225 个确认完成步、226 次调用；最后失败调用内部步数未知。
- 合计：450 个确认完成步、451 次调用，不能声称精确总步数为 450。
- 原账本：1 次数学请求、1 次独立 backend solve，累计 numerical time 约 2.595 s。
- Provider 请求 0、NMPC update 0、RL action 0；无 Provider 货币费用。

第一次 smoke 检查的辅助脚本错误地假定失败分析也总有 `task_acceptance` 字段。
修正辅助脚本后复用了同一分析收据，再执行尚未使用的独立回放，没有新增 Native 回调或额度。
成本补充直接读取原失败快照；没有改写原收据或失败记录。
工程检查已通过公共 STOP 封存，`pending=None`，保留同一账本的一次数学请求和一次独立回放。

可审计摘要：`evidence/bf4_bf6_public_integration_20261027/summary.json`。
该目录只包含本次集成检查摘要，没有 B 私有数据或历史成功答案。

## 修改文件

- 公共配置：`study_tracking_public.json`、`study_bf5_public.json`、新增 `study_bf6_public.json`；
  FamilySpace：新增 `family_space_bf4_s3_tracking.json`、`family_space_bf6_sensor_tool.json`。
- 任务：新增 `tasks/bf6_sensor_oriented_tracking_v1.json`。
- Registry/物理：`extensions/reference/{contracts,implementation}.py`、
  `extensions/tendon_family/{manifest,backends,generated_serial,mujoco_analysis,signals}.py`。
- 任务与研究接口：`tools/research_tasks.py`、
  `tools/research/{tool_axis_task,task_constraints,native_control,physical_replay,analysis,feedback,contracts,control_correction,research_context}.py`。
- 定向验证：`tests/research/{test_bf6_oriented_tracking,test_cross_task_integration,test_native_control,integration_tracking_smoke}.py`。
- 本报告与本次检查摘要。

本次止于生产接口集成和上述一次工程物理检查；未重跑 B 的 R2–R8，未运行 Provider、正式 Study 或 BF7。
