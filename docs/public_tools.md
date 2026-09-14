> Framework 1.1 supersedes extension-roadmap statements below. See [current contracts and migration](framework_extensions.md). Historical interface notes remain preserved.

# 公共工具接口 v1

本次以 `feat/round9-matlab-dynamics-design-loop` 的 `e1051c4` 为基线，把真实执行白名单、公共调用和反馈、保存证据服务接入同一目录。入口是 `tools.public_catalog`；旧 Workbench 与 Dynamics 的调度、授权和账本继续负责执行。没有重跑设计实验，也没有改变物理模型、目标、评价器或已批准预算。

## 发现与调用

```powershell
python examples/public_tools.py catalog
python examples/public_tools.py catalog --runtime services
python examples/workbench.py catalog
```

[完整工具清单](public_tools_catalog.md)是可再生成的阅读视图。JSON 目录提供每项工具的 `tool_id`、版本、实现入口、输入 schema、前置条件、权限、适用范围、依赖条件、成本规则和假设。`tools.public_catalog.discover_bound(book)`、`ServiceSession.discover()`补充当前会话的权限/模式/余额；资源预留、候选前置条件、证据与后端可用性最终由调用时检查。发现不会启动 MATLAB、MuJoCo 或外部 API；`callable=true` 表示存在调度入口，不保证机器已安装并授权相应后端。

工具身份采用 `namespace.name@1.0.0`。`workbench.evaluate_candidate` 是旧 C1 的 MATLAB + MuJoCo 完整评价；`dynamics.evaluate_candidate` 仅运行候选控制器对应的 MuJoCo。它们不是可以互换的别名。旧 wire name 只在绑定的运行器内部有效；公共 JSON 拒绝跨运行器和无命名空间的歧义名称。Dynamics 的 `evaluate_candidate` 保留为兼容入口，新调用宜使用明确后端的 `simulate_candidate`。

library 条目来自既有 manifests，仅作能力库描述，全部 `callable=false`，带 `IMPLEMENTED/PLANNED` 声明及 AST 入口存在性检查。存在函数不代表通过公共接口获得执行授权；数学、控制、旧实验库不能被目录自动提升为可执行插件。`matlab_analysis → model` 的 bundle 别名列在 `library_bundle_aliases`。

原生 provider schemas 从同一目录/同一 Pydantic 输入类生成：Dynamics 用 `schemas.dynamic_workbench.native_tools()`，旧设计 agent 用 `tools.deepseek_adapter.native_tools()`，独立服务用 `public_catalog.native_tools('services')`。未来 agent 使用这些 schema 和宿主适配器，不自行调用后端函数。

## 公共请求与宿主责任

```json
{
  "contract_version": "1.0",
  "tool_id": "analysis.pcc_jacobian",
  "tool_version": "1.0.0",
  "arguments": {"length_m": 1.25, "bend_rad": [0.4, -0.2]},
  "reason": "检查当前弯曲附近的末端局部导数",
  "evidence": []
}
```

`schemas/public_tools.py` 是契约定义；未知字段、未知版本、非有限数、错误类型和专业约束由严格校验拒绝。专业参数仍在各工具输入类中；没有把机器人、时间区间和优化边界压成无约束参数字典。原有直接 submit 的类型转换行为为兼容保留，新增公共入口使用 strict JSON 校验。

调用者 `Caller(actor_id, origin, transport, model_request_index)`由宿主传入，禁止嵌入 LLM 的 `arguments` 冒充来源。`agent`、`human_cli`、`development` 与无法恢复来源的 `legacy_unknown` 分开记录；注入测试会记录 `injected_test`/`offline_native_fixture`，不能作为真实 API 证据。旧 DeepSeek transport 也记录来源和请求序号。

已有运行器的公共适配：

```python
from tools.workbench import Workbench, owner
from tools.public_gateway import invoke_bound

book = Workbench("runs/my_existing_workbench")
with owner(book.root):
    book.load()  # 保留原有源码、运行时、证据、预算及恢复检查
    result = invoke_bound(book, request,
        caller={"actor_id": "operator", "origin": "human_cli", "transport": "python"})
```

Dynamics 同样传入已加载且已持有 owner lock 的 `DynamicCampaign`。`invoke_bound` 只调用 submit；它不绕过授权去调用 dispatch。动态实验仍要求原有真实 DeepSeek 来源，不会因 Caller 写成 agent 获得新授权。公共入口的预检拒绝和缓存复用另存 `public_calls/<id>/result.json`；原生旧调用继续使用原有 decisions/attempts。

这些是受信任宿主接口，不是任意 Python 代码的 OS 沙箱。工具目录不授予代理修改配置、账本、证据或源码的权限。

## 反馈、证据与成本

`PublicResult`提供以下互相独立的字段：

| 字段 | 语义 |
| --- | --- |
| execution_status | completed / rejected / failed / interrupted / capability_missing；只描述工具调用 |
| solver_status | NOT_APPLICABLE / NOT_RUN / COMPLETED / INCOMPLETE / FAILED / UNKNOWN；原值保留在 provenance |
| analysis_status | 局部几何、模型预测或采样规则诊断，缺少明确结果时 NOT_ASSESSED |
| task_status | PASS / FAIL 只转录明确的 canonical 评价；历史回放标 NOT_RUN；其余 NOT_ASSESSED |
| summary、details_ref | 简短可用摘要；完整数据按证据引用和 JSON Pointer 分页读取 |
| error | 分类、稳定代码、原始消息、恢复条件与下一步；默认不自动重试 |
| evidence | 输入/输出/详情引用与 SHA-256；自身结果哈希由外部 evidence registry 保存，避免自引用哈希 |
| provenance、epistemics | 调用参数、代码/配置身份、来源；观测、模型推断、未验证假设和媒体访问程度 |
| cost | 实际预留/计费、耗时、缓存命中与账本所有者 |

特别地，调度成功但数值求解失败时，可出现 `execution_status=completed, solver_status=FAILED`，并带 `SOLVER_INCOMPLETE` 失败详情；这不自动等于任务失败。数学分析成功也不产生 canonical PASS。原始 `ToolResult`、`WorkbenchResult` 的 `status/failure_code/data` 保留；新增 `WorkbenchResult.public` 是有类型的可选字段。历史缺字段不被猜测补写。

失败分类为 input、permission、budget、evidence、dependency、timeout、interrupted、execution。权限失败要求使用当前 grant 允许的工具；预算失败要求查看余额/预留记录；证据失败要求选择已登记数据或恢复匹配字节；超时/中断先检查封存结果和已收费预留。未知故障保留原始代码与消息，不从报错猜测物理因果。

计费保持运行器边界：

| 路径 | 决策/工具/后端与 API |
| --- | --- |
| Workbench 原 submit | 原 decision 计数、worker 启动前预留、完成结果缓存、超时与中断收费均保留；缓存不新增 worker/后端费用 |
| Dynamics 原 submit | 决策与工具原有预留不变；逐 rollout 收 MATLAB/MuJoCo；失败也保留；视频/读取/诊断零动力学，仍有工具次数和活动耗时 |
| 公共 gateway 预检 | 尚未进入运行器的 schema/身份拒绝不收费；保存预检回执；进入 submit 后完全使用原账本 |
| 独立 services | 已通过 schema、权限、输入证据和余额校验的调用预留 1 次 tool_call；执行失败/视频缓存也占 1 次；后端求解和 model_calls 恒为 0 |
| LLM transport | 只有宿主实际模型请求消耗 model_calls，token usage 仍保留在 provider receipt；人类或开发工具调用不冒充模型 API |

没有自动增加预算、失败退款或暗中重试。独立服务的保留调用在崩溃后只恢复可校验的封存结果；未封存调用保持 interrupted，原预留保留。它复用锁、atomic JSON 和证据哈希原语，但不共享或重置 Round 9 grant。

## 单位、模型和时间

长度 m、角度 rad、力 N、时间 s；PCC 雅可比为 m/rad。PCC 使用固定基座原点、直态沿 +x、弯曲分量在 yz 的坐标约定，`bend_rad=[theta*cos(phi), theta*sin(phi)]`，范数不超过 π；不隐式进行世界坐标变换。它是单段、不可伸长、常曲率局部几何，没有重力、接触、弹性、动力学和物理标定。任意正长度的数学输入不意味着允许建立该长度的实验候选。

轨迹的 `time_s` 是步后状态时间，`solver_time_s` 是力/路径所处的求解阶段；查询分别使用各自的时间轴。采样极值不是连续时间严格界。视频另有 `saved_times_s/scheduled_times_s/playback_duration_s`，播放时间不冒充仿真时间；活动耗时与进程之间的暂停时间也不是轨迹时间。

## 任务无关服务与保存数据

```powershell
python examples/public_tools.py init --root runs/public_geometry_demo --config configs/public_tools/development.json
python examples/public_tools.py call --root runs/public_geometry_demo --request configs/public_tools/pcc_example.json
```

新目录必须不存在；重复 init 拒绝覆盖。返回 `details_ref` 后，可以用 `evidence.read_json`、对应 JSON Pointer、offset、limit、max_bytes 继续读取。`ServiceSession.apply_tool_call(function, caller=...)` 使用 provider 的 `name/arguments` 格式，和人类 JSON 调用共用 invoke，不经过新模型网络请求。

`init --source runs/已保存运行 --evidence-ref 路径`可多次指定待导入证据。仅接受来源 registry 已登记且哈希相符的文件，按原相对路径复制，保存原 run/ref/hash；不复制/覆盖管理文件。读取源运行不调用 load/resume，因此不会恢复实验或修改源账本。视频需显式导入 result、trajectory、robot.xml 及共享输入/IR/场景资源；复用缓存再导入 native_video.json 和其中的媒体文件。缺少依赖会明确失败，不补跑仿真。

独立的 `diagnostics.saved_trajectory` 从已保存样本推导默认时间范围，接受任意候选标识，不依赖 c032、c071 或两秒。专业诊断仍使用现有列结构和 `reach_events_v2` 阈值，因此只是该模型格式的诊断适配器，不能宣称可诊断任意机器人模型。

旧 Dynamics 的诊断、观察和比较新增源哈希检查及派生过程元数据。HTML 的目标、地面位置和时间轴来自 shared_input/保存样本；缺少目标时隐藏目标误差曲线。曲线上的到目标距离仅是保存坐标的展示计算，不调用评分器、不改变 canonical 结果。旧 `diagnose_trajectory` 的两秒缺省参数保留在其命名空间中；新工具不继承这项实验约束。

`render_simulation_video` 的双原生后端、片段选择、自动返回、采样/编码元数据和哈希缓存保持原实现。新公共别名直接复用此实现；没有新增求解或评分。视频文件引用、预览引用和实际向模型提供像素是不同能力：本项目文本模型得到引用时 `visual_access=reference_only`。宿主尚未实现通用视频理解工具；不要把文件生成、展示网页、或模型引用视频当作模型看过画面。

## 兼容与迁移

1. 旧命令和 wire names 继续有效；公共调用显式选择 namespace，先发现再调用。旧 ToolResult/WorkbenchResult 文件无需批量改写。
2. Round 9 历史状态、已消耗预算、缓存身份、候选编号和实验终止状态保留。`round9_llm_reach.json`只是把已有 c032 子实验的基线、40/3/24/1800 限额、20 N 固定值和说明从代码提取到所属配置；新启动保存 profile，旧记录使用相同旧配置解释，不赋予额外额度。
3. 任务/环境/冻结数值设置、求解器、评价器与后端物理实现未修改。通用工具不替代 TaskSpec 或 grant 作为科学事实来源。现有 Dynamics 仍是 reach_free 冻结路线，通用数学/读取服务可独立复用；本轮没有伪装成已经支持任意新动力学任务。
4. V1 `resume` 保留严格源码/运行时检查；接口更新后应走既有的、只允许非数值文件变化的 continuation 流程。增加的允许项仅是本轮公共契约/调度/展示。Round 6 历史运行已存在后续数值文件差异时，仍应拒绝续跑；不得为了让旧测试通过而放宽物理兼容规则。Dynamics 使用原有独立数值身份缓存。
5. `raw dispatch`、后端库和历史 experiment CLI 是受信任实现入口；没有变成其他 agent 可任意执行的权限。新 agent 必须复用宿主锁、caller 归属和 submit 预算。

## 数学、优化与控制的后续接入

| 扩展 | 必须先明确的边界 | 接入方式 |
| --- | --- | --- |
| 数学分析 | 假设、输入域、单位/坐标、条件数/收敛、推断适用性 | 增加专业输入类、实现及目录 entry；用 PublicResult 和 hash-linked details；本次 PCC 接入是已执行示例 |
| 参数优化 | 优化器只产生授权变量内的提议；评价器决定指标及任务成绩；无效求解不可作为优胜分数 | 包装已授权 evaluator，通过运行器每次预留、缓存和试验 checkpoint；显式绑定 bounds/objective 引用。现有 optimize_matlab 是指定 grant 的坐标搜索，尚不是通用 optimizer 插件 |
| 控制器生成 | 生成的控制律/参数与运行控制器分离；采样周期、执行约束、状态/动作单位必须明确 | 生成结果输出 controller artifact/hash；执行仍通过 simulate/evaluate 预留资源；不能通过“生成”工具隐式 rollout |
| 控制优化/系统辨识 | 数据来源、训练/验证划分、目标授权、模型失配与可辨识性 | 数学/优化契约组合；拟合结果不能回写冻结 physics contract 或宣称标定通过 |
| 其他 agent | 来源由宿主认证，同样的权限/预算和证据引用 | 使用 ToolCall/native schema → invoke_bound/ServiceSession；每次调用带 caller 和运行身份，不新增自行复位的账本 |

每次提升可执行能力需增加真实适配与直接相关验证，再更改目录状态；计划项不会因文档出现函数名就获得 callable 标记。算法扩充与多 agent 编排不在本轮。

## 验证

执行 `python examples/check_public_tools.py`。它固定运行相关模块，禁止新的 `mj_step` 和 DynamicsBackends rollout，生成机器目录、完整测试日志、JavaScript 语法检查及历史/冻结文件前后 SHA-256 对照。[验收记录](public_tools_validation.md)区分代码检查、注入模拟链路、真实 MuJoCo 静态检查及历史原生视频复用；不把它们混写成新的 MATLAB 动力学或真实 LLM 实验。
