# U1/U2 通用任务适配

开发基线 `a73981c12a6212b5201c297f52d52d1c27f05d40`，独立分支
`codex/u1-u2-general-task-adaptation`。2026-11-01 核对远端 HEAD：
`main@2a854280db69425dc50af9012b8da52194a679ee`；R0 分支仍为开发基线。
本轮遵循 R0 九任务审计及其真实历史来源口径；未重跑历史搜索。

## U1

V4 的 `control_feasibility` 从当前候选的 `mathematical_method_view` 选择已授权、
模型/任务适用且有预算的方法。Reach/Hold 保留原默认 T1；Tracking、位置与工具轴、
带载有向 Tracking 可选择原 Direct。显式 `numerical_method` 可表达目录中的科学选择；
被阻断的 Reach/Hold T1 不会被自动换成另一身份。方法选择仍只是编译，原
AnalysisRequest、dispatch、Worker 和累计预算执行最终准入。

| 当前任务族 | V4 默认数值身份 | T1/T2 | 物理成功依据 |
|---|---|---|---|
| Reach/Hold（含合法 COM 外力） | T1，原有限预算 J 解释 | 保留原 T1 / 可比较已保存 T1 的 T2 | 原独立 Replay 全 acceptance |
| timed Tracking | `mujoco_direct_control_v1` | 不适用 | 原 timed evaluator |
| position + tool axis | `mujoco_direct_control_v1` | 不适用 | 位置与有向轴两个谓词 |
| loaded oriented Tracking | `mujoco_direct_control_v1` | 不适用 | 原时序、刚性工具与每步无接触门禁 |
| passive / 未支持主动模式 | 无合法控制方法 | 不适用 | 不以控制诊断建立被动成功 |

Direct 不生成 T1 科学身份，不成为 T2 来源。Response/Pattern、NMPC、Conic、T1/T2
数值算法未修改。原控制来源绑定、effort、Native 设置上限和 Worker 准入保持有效。
Main 仍只选择 `control_feasibility`，按需 Schema 中展示当前候选合法数值身份，
短 handoff 给出 `control_methods` 的身份、目的、准入状态和缺失项。

最小 Main 请求（无私有 ID，候选由完成的 diagnose 绑定）：

```json
{"version":"scientific_question_v4","domain":"control","control":{"question_type":"control_feasibility","effect_semantics":"reoptimized_task_capability","control_scope":{"mode":"full_task"},"control_search_effort":{"method":"response","knot_count":4,"iterations":1,"evaluation_requests":1}}}
```

对适用的 M4–M6，动态 Schema 的 `domain.const="control"`、
`control.question_type.const="control_feasibility"`，`numerical_method.enum` 仅包括
`null` 和当前候选目录可选择的方法。原 V1/V2/V3 Schema 不增加这个字段。

U1 定向验证：新增一个参数化 Mock 准入测试覆盖 M4/M5/M6 的正式候选生成、
initialize_control、V4 编译、T1/T2 拒绝和预算耗尽拒绝；复用原 M1 SDK/Mock、
T1 编译/原计费、Native 上限在 Worker 前拒绝的测试。所有数字与运动输出是 fixture。
真实 Provider、正式数学 Worker、新积分、正式 Replay 均为 0。

## U2 冻结配置及联合结果

`task_conditions` 接受非空有限列表、唯一条件 ID 和真实注册 TaskDefinition。
旧 `{condition_id, task}` 格式不变。可选 `execution` 仅声明该条件的 `control`
配置引用、注册 `backend` binding 和必要的原 `analysis_protocol`；没有通用任意 patch。
control 使用原 `_reference` 单层组合和同一个 controller 解析函数，冻结后不重读源文件。
实际候选继续经原 SessionInput、Registry、正式生成、initialize_control、research_analysis、
physical_replay。任务时域不同时必须显式冻结匹配的原 TaskAnalysisProtocol，不替 Main 发明分析窗。

四条件配置片段（路径相对于 `configs/research`；只作接口示例，不是已授权 Study）：

```json
{
  "task_conditions": [
    {"condition_id":"positive_high","task":"../../tasks/bf7_shared_reach_v1_positive_high.json"},
    {"condition_id":"negative_low","task":"../../tasks/bf7_shared_reach_v1_negative_low.json"},
    {"condition_id":"central_high","task":"../../tasks/bf7_shared_reach_v1_central_high.json"},
    {"condition_id":"tool_axis","task":"../../tasks/bf5_position_tool_axis_v1.json",
     "execution":{"control":"control_bf5_tool_axis.json","backend":{
       "extension_id":"backend.family_mujoco","version":"1.3.0",
       "parameters":{"contract":"family.mujoco_parameters","version":"1.0.0","data":{
         "integrator":"implicitfast","timestep_source":"task.timing.timestep_s",
         "contact_model":"mujoco_convex_native","friction":[0,0,0]}}}}}
  ]
}
```

示例使用原公开 Base-only FamilySpace 生成 2 段/4 腱普通结构，没有继承 M1 的固定 6 腱
限制，也没有导入历史获胜结构或控制。Reach 的 settling 仍只含位置/速度末窗；工具轴条件
从自己的 control 配置取得 `settling=null`，位置和轴角保留在 TaskDefinition/evaluator。
原 controller 内已有的合法零速度权重不删除，也不从 Reach 条件复制到别的 controller。

`shared_physics()` 比较实际 family 编译出的 physics、离散、dynamics_model、backend 参数
及规范化 assembly。注册 backend 的版本适配不能豁免这些比较；外力仅允许来自冻结 task
的真实 COM force 声明。重力、mount、载荷实体、几何/材料/腱路、离散或模型不一致仍拒绝。
外载不会被改成无载；M6 刚性工具绑定不允许被外力代替。

同类结果仍使用 `research.task_aggregation@1.0.0`；异构结果显式使用
`heterogeneous_conditions_v1` / `research.task_aggregation@2.0.0`。旧无声明聚合异族时的
`AGGREGATION_TASK_PROTOCOL_MISMATCH` 仍在。新版本要求冻结 schedule 的每项任务身份、
task_family、protocol_id 和结果精确对应，逐项验证完整 acceptance、实际独立执行、
receipt/evaluation/profile 来源及全部条件覆盖。联合输出仍是原 joint result、Store、
证书、SELECT 和 STOP 路径，没有新的正式选择入口。

下面是 **Mock** 联合输出的关键字段，其完整 acceptance、来源和各条件 TaskGap 见保存的
Mock 示例：

```json
{
  "kind":"joint_condition_result_v1","version":"2.0.0","status":"evaluated",
  "aggregation":{"contract":"research.task_aggregation","version":"2.0.0",
    "condition_contract":"heterogeneous_conditions_v1","accepted":4,"scheduled":4,
    "task_family":null,"protocol_id":null,"all_scheduled_accepted":true,"metrics":{}},
  "task_gap":{"normalized_gap":null,"common_scale":false,"accepted":true,
    "condition_gaps":{"positive_high":"原 TaskGap","negative_low":"原 TaskGap",
      "central_high":"原 TaskGap","tool_axis":"原位置/轴角 TaskGap"}}
}
```

上例 TaskGap 字符串是展示占位；保存 JSON 是完整实际 Mock 数值对象。各条件单位及阈值
留在自身证书内，不把 m、m/s、rad 直接取最大值。没有声明共同科学尺度，联合分数为 null。
Main 必须收到每个条件的完整证书/完整原结果后才能 SELECT；本地 marker、Reporter、局部摘要
均不足。内部只读证书可以在 SELECT/STOP 后重验事实，不能再次 SELECT 或改写已选解。

真实 SDK 发包路径的 **Mock** 短对象摘录（来自保存的
`main_short_object.current_research_state.object`，不是另造的顶层工具）：

```json
{"candidate":"candidate_68","compiled":true,"control_initialized":true,
 "independently_evaluated":true,"task_acceptance":"accepted"}
```

这是一项条件的当前对象；联合选择引用四项 `evaluation_25`、`evaluation_44`、
`evaluation_63`、`evaluation_82`，不是拿最后一项替代联合结果。工具轴当前控制研究的
动态 Schema 摘录如下；完整 Schema 同保存在 Mock 输出内：

```json
{"properties":{"domain":{"type":"string","const":"control"},
  "control":{"$ref":"#/$defs/ScientificControlV4"}},
 "$defs":{"ScientificControlV4":{"properties":{
   "question_type":{"type":"string","const":"control_feasibility"},
   "numerical_method":{"enum":[null,"mujoco_direct_control_v1"]}}}}}
```

## 修改和精简清单

| 文件 | 修改/新增的函数或契约 |
|---|---|
| `tools/research/scientific_intent.py` | `control_method_choices`；`scientific_actions`、`question_schema`、`compile_question`、`compile_v1` |
| `tools/research/contracts.py` | `ScientificControlV4`、`ScientificQuestionV4.control`、`Plan.required` 的有限条件列表校验 |
| `tools/research/agent.py` | `plan_schema`、`bind_selected_analysis_request`、`converse` 中的按需 Schema |
| `tools/research/research_context.py` | `agent_decision_brief` / `information_flow_brief` 的候选控制方法 handoff |
| `tools/research/config.py` | `_reference`、`resolve`；共用 `controller_configuration` 和 `frozen_analysis_protocol` |
| `tools/research/conditions.py` | `configuration_for_condition`、`shared_physics`、`joint_assessment`、`_joint_gap`、`joint_view` |
| `tools/research/task_constraints.py` | `mathematical_method_view`、`mathematical_research_view` 使用冻结条件协议 |
| `tools/research/analysis.py` | `dispatch` 的原协议身份准入使用冻结条件协议 |
| `tools/research/design.py` | `final_fidelity_matches` 对比本条件冻结 backend，仍要求原 final mesh |
| `tools/research/feedback.py` | `eligibility` 区分内部事实重验与正式选择门禁；公开 SELECT 路径保持严格 |
| `tools/research/evidence_views.py` | `acceptance_certificate` 支持原联合对象的完整条件证书 |
| `tools/research_tasks.py` | `aggregate_acceptance` 的显式 v2 条件协议扩展，原 v1 输出不变 |
| `tests/research/test_general_task_adaptation.py` | 4 项参数化通用接口/Mock 回归，复用原 fixture 和 evaluator |
| `tests/research/test_cross_task_integration.py` | 原 `fixture_host` 增加可选 Mock episode 数；默认仍为 3 |
| `tests/research/test_c1_method_context.py` | 旧 archive fixture 的 `artifact` 支持现有 Store `paths` 读取契约 |
| `tests/research/test_information_flow.py` | 仅 Schema 测试 Mock 可选 MATLAB 包元数据；不安装或启动 Engine |

删除文件、删除旧函数：**0**。合并了 resolver 的重复 controller 组合/归一化代码；删除了
2/3 项专用条件/Plan 限制和无条件覆盖 settling 的分支。旧 T1/T2、Native、Conic、NMPC、
Worker 恢复及计费内核未修改。没有新生产 Python 模块、顶层 SDK 工具或 V5。

## 最小准备度结果及边界

| 场景 | 本轮已验证的范围 |
|---|---|
| M1 三 Reach/Hold | 原三个 TaskDefinition，三份独立 Mock 结果，经完整证书交付和原联合 SELECT；聚合仍为 v1；原 R0 SDK/Mock 及 T1/T2 保存来源回归 |
| M2 三外力 Reach/Hold | 原 zero / positive / negative COM 力、世界坐标、payload COM、0.1–0.35 s、正负 0.02 N 与 -0.03 N 全部保留；独立 Mock 来源与 v1 联合 SELECT |
| M4 Tracking | 原全时序任务约束保留，V4 → Direct → 原 dispatch 的 Mock Worker 请求；T1/T2 及预算耗尽请求拒绝 |
| M5 工具轴 | 原位置与轴角双约束保留，自己的 controller/backend 编译、初始化、V4 Direct 和 Mock Worker 准入 |
| M6 带载有向 Tracking | 原 rigid_tool 质量/COM/惯性/site 对实体绑定，时序/位置/轴角/无接触协议保留；Direct Mock 准入；不声称真实无接触执行 |
| C1 三 Reach + 工具轴 | 公开域普通 4 腱结构，四份不同控制源，T1/T1/T1/Direct 编译，真实 evaluator 处理人工运动数据，完整 Mock HTTP 证书交付，原联合 SELECT/Store/export；没有真实 C1 复现 |

另外验证 1/4/5 项合法条件配置、错误重力/backend 参数拒绝、显式不同时间协议，以及重复、
缺失、错任务、损坏 acceptance、错误 profile、缓存 receipt、重复 execution 和假 accepted
标记的拒绝。与基线 resolver 直接比较，M1/M2/M5/M6 的 `configuration`、`task_conditions`、
`analysis_protocol`、`budgets` 无差异。

所有新增 Study 都是唯一命名、显式标注的隔离测试 fixture。测试中的 Provider 请求计数、
数学计数和 Replay receipt 是 Mock 记录，不是正式计算。真实 Provider、正式数学 Worker、
真实控制优化、新 MuJoCo steps、正式独立 Replay 均为 **0**；原 R0 准备对象与历史 Store 不改。

仍不适用：Tracking/轴任务的 T1/T2；Direct 结果作为 T2 来源；用位置 Jacobian 或 Conic
冒充轴角、刚性工具或无接触完整证明；GVS/Conic 对完整 COM 外力任务的现有 unsupported；
未注册的物理任务模式。原 Native 批量结构搜索仍是完整 Reach/Hold 的 T1 研究协议，未改成
异构统一目标或全局优化器；C1 可走原 generate + 逐条件控制研究/Replay + 联合 SELECT。
数学 best-found 诊断不替代独立 evaluator，更不建立硬件、全局最优、连续时间或重复性结论。

14 个定向检查的最终结果全部通过。首轮 14 项中 12 项通过，另外两项暴露旧 archive
fixture 签名和本机缺少 MATLAB 元数据的问题；修复测试夹具后仅重跑这两项，均通过。
没有修改生产依赖检查或科学准入。编译检查与 `git diff --check` 通过。
保留原失败日志，避免将首轮失败写成一次全绿：

- [validation.json](../../evidence/u1_u2_general_task_adaptation/validation.json)：检查汇总、基线配置等值核对和真实成本。
- [initial_focused_tests.txt](../../evidence/u1_u2_general_task_adaptation/initial_focused_tests.txt)、[fixture_regressions.txt](../../evidence/u1_u2_general_task_adaptation/fixture_regressions.txt)：原首轮和修复后两项重跑。
- [mock_homogeneous.json](../../evidence/u1_u2_general_task_adaptation/mock_homogeneous.json)：M1/M2 原三条件及实际冻结 COM 力声明。
- [mock_native.json](../../evidence/u1_u2_general_task_adaptation/mock_native.json)：M4–M6 的约束、evaluator、时序、Direct Mock Worker 准入及动态 Schema。
- [mock_c1.json](../../evidence/u1_u2_general_task_adaptation/mock_c1.json)：四条件原 acceptance/来源、逐条件 TaskGap、完整实际 Mock SDK 短对象及配置/Schema 示例。

## PHS/P3 后续所需的通用被动物理协议接口

1. 在原 FamilySpace 冻结真实段/腱/材料点/放绳域与离散，不能用当前小示例代表原 9 段/4 腱
   PHS 或 3 段/2 腱 P3；保留 P3 原 4 cells 无效的空间敏感性限制。
2. 合格无载基准契约：基准状态/原始采样、平衡残差、速度/漂移/接触、来源和准入，受载任务
   必须从这份真实合格状态开始，不能自动换成零状态。
3. 扩展原 PassiveResponseGoal/执行协议：材料点坐标、frame/单位、ramp/hold、多工况/holdout；
   P3 还需连续五阶段加载、状态继承与卸载恢复，明确“连续不重置”与“每工况从基准起步”。
4. 观测与原 evaluator：受力点/Tip/平面外位移、速度、漂移、残差、长度、接触、张紧/松弛
   转换；PHS 的位移比、尾窗与预留工况；P3 的低/高载位移、刚度比、分母精度及恢复残差。
   保留各自单位、阈值、采样覆盖和硬门禁，不生成未经定义的统一分数。
5. 机制对照与独立检查绑定：相同合格基准、完整时序、有效消融、半步长与初态扰动；所有
   额外执行沿用原累计预算、Worker 恢复和真实 receipt，不复活历史编排器。
6. 在原 TaskAdapter、passive_execution、独立 Replay、证书与现有组合验收中注册完整协议，
   再接原 SELECT/STOP。现有静力 KKT/Jacobian/可行锥或开发通过不能替代这一步。

这些是后续接口清单，本轮未实现、未授权或启动 PHS/P3 研究。
