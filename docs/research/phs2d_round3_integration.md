# PHS-2D 第三轮：通用能力与待审批的集成边界

本文件是获胜结构完成验证后的接入建议。独立研究分支不自动合并 `integration/research-next`、集成主线或其他 worktree；没有改动 Reach/Hold、Tracking、BF2、既有主动控制或 M1–M6 冻结 Benchmark。

## 可复用数学内核

| 能力 | 现有实现 | 适用条件与输出边界 |
|---|---|---|
| 非线性被动静力与 KKT | `extensions/tendon_family/passive_equilibrium.py`，继承第二轮 | 完整原生铰链坐标、重力和真实材料点力；理想硬绳；局部二阶充分检查，不能替代软约束动力学 |
| `passive_modal_target_v1` | `extensions/tendon_family/passive_inverse.py::modal_target` | 可信平衡；区分理想 Tip 零空间、单侧可行锥、真实外力激发；输出实际 Jacobian、Hessian、秩、零空间、平面外诊断 |
| `tendon_jacobian_matching_v1` | 同模块 `matching`，研究编排的 `optimize_matching` | 实际 MuJoCo 长度 Jacobian 的行空间匹配；几何匹配不代表腱实际张紧；保留两个水平行的残差 |
| `route_geometry_validation_v1` | `extensions/tendon_family/route_validation.py` | 带绳半径的直线段与编译凸包相交；拥有的实体孔、终端实体锚点有明确例外；保存姿态检查，非连续碰撞引擎 |
| `passive_design_sensitivity_v1` | `passive_inverse.py::design_sensitivity/task_design_sensitivity` | 固定拓扑、固定材料绑定、正则稳定分支；归一化 KKT 隐式导数，重新求平衡有限差分核查；任务位移必须扣除设计相关无载基准 |
| `passive_multicase_design_v1` | `tools/research/phs2d_inverse.py::screen` 与 `multicase_metrics` | 有效性优先，六工况最大归一化违反量；比例搜索用差值形式，验收保留原真实比值 |

能量解释应区分弹性应变能与包含重力、腱几何项的约束 Lagrangian 二次型。现有模态的 Hessian 能量诊断属于后者；原始分布式弹性刚度保存在编译物理结构中。局部分析、对称性或有限预算失败不构成全局可行/不可行证明。

## 最小生成与运行时扩展

1. 新建独立 FamilySpace 冻结文件，不改写此前空间。段数、腱数和网格范围是该 Study 的已授权域，不是科学上限。实际完成九段、四腱、144 坐标编译和动力学验证，没有宣称所有 12 腱拓扑已验证。
2. `terminal_payload_anchor` 为默认关闭、旧序列化不输出的新字段。开启后，只允许终止在真实终端 payload 包络内；旧空间继续拒绝该路由。
3. `guide_hole_positions_m` 是默认空、旧序列化不输出的生成请求字段，并由逆向空间显式授权。必须绑定真实且实际使用的具名孔，原构造器继续检查所有孔的包络、间隙、重叠和拥有关系。
4. `inverse_routing.py` 的版本化参数函数只生成已有 RoutePoint 与具名孔请求，最终仍通过原 FamilySpace 构造器、候选身份和物理编译器。
5. 高段数原生 XML 编译在 Windows 上通过独立 32 MiB 栈线程完成，仅在本轮被动协议中启用。没有改变 XML、动力学方程、积分器或软约束设置。
6. 逐 timestep 回调只记录原生状态，不施加控制输入；压缩文件是内容寻址 Store artifact。原始 evaluator 的 10 ms 测量语义保持不变。

默认值兼容性有专项断言。扩展 FamilySpace 回归中的两个旧断言失败已经在指定基线副本重现，没有更新旧 hash 或长度阈值来掩盖失败。

## 正式 PHS TaskAdapter / evaluator 建议

正式接入应单独注册 `passive_head_stabilization_v1`，冻结世界坐标、材料点 s 语义、重力、偏心载荷、正负力、时域、采样相位和全部原门槛。不能让 Reach/Hold 的构造 scaffold 代表 PHS 执行。

TaskAdapter 应编译固定被动放绳和材料点虚功，拒绝 actuator、额外世界锚点、Tip 世界约束以及未声明的主动输入。装配身份应同时绑定设计、数值网格、固定长度向量、环境和数值协议。无载基准与受载执行分别拥有原始 artifact，每个载荷从同一合法无载基准、零速度独立启动。

独立 evaluator 只读冻结记录，先检查基准、稳定性、接触、单侧方向、张力、长度残差和几何有效性，再计算位移与真实比例。十工况聚合必须检查同一物理装配；首次启用预留集后，该数据不再作为新候选的全新盲测数据。正式 SELECT 只能接受已注册 evaluator 的完整聚合结果。

## 与现有研究架构的接入

- `research_analysis`：增加显式方法版本和适用条件，不把本轮全部数学方法设为通用任务求解器。请求应绑定 assembly、可信 equilibrium、参数归一化、活跃集合与数值差分协议；输出区分计算状态、局部数学强度、物理执行状态和任务验收。
- `physical_replay`：增加固定被动装配的执行输入，而非以零电机命令模拟被动绳。复用现有资源预约、每次 mj_step 尝试计数、原始轨迹和独立 evaluator。
- Store / 预算：沿用现有候选身份、内容寻址 artifact、收据、pending 恢复和 STOP。跨版本 Study 必须扣除已用物理、数学、候选和动态装配额度。未知请求先恢复，不自动重发。
- Agent 决策：Agent 仍只选择假设、解释证据和决定下一项研究；数学与物理工具拥有数值有效性，独立 evaluator 拥有验收。没有让数学输出直接选择成功，也没有注入固定获胜答案替代探索。
- 上下文边界：完整答案和原始 Store 保留于本研究分支的隔离数据；未来 Agent 默认上下文只暴露通用工具声明和经审阅的适用条件。获胜结构仅通过显式 artifact 引用读取。

## 建议迁移顺序

### 对实际正在发展的主线的只读核查

本轮检查了 `integration/research-next` 的本地快照 `618bb16b2a42a1be93ca80c527e4608d67e30371`，并在发布前核对远端新 HEAD `455ec55347ce6ab05cfbf71ad439044e9db77aca`：两者仅涉及 Agent 错误反馈和搜索引导的两个小变更，已只读检查，没有增加被动执行契约。另检查了当前推荐共同主线 `mainline/softarm-codesign` 的 `4de5d5d475755578653e9cca8febe395adeb8764`。依据实际主线报告、`analysis.py`、`physical_replay.py`、`contracts.py` 和文件差异，职责分离与预算/Store/ResearchDecision 模式兼容，但本分支**不是可直接整体合入的补丁**。

推荐主线已经删除旧 `phs2d*` runner、`passive.py`、`passive_equilibrium.py` 和若干旧 native 数学入口；其 `AnalysisRequest.operation` 仍有显式枚举，`physical_replay` 当前绑定固定主动张力时间序列。因此新被动方法需要经过新的显式方法/物理输入契约和 TaskAdapter 授权，不能把固定被动长度伪装成当前固定张力 schedule，也不能借本分支把已精简的整个旧研究平台恢复到生产主线。

建议仅移植经审阅的纯数学、几何内核和最小结构字段，并在当前 `research_tasks.task_adapter`、`analysis.calculate`、`check_analysis_applicability`、原 Store 与独立评价边界上增加新的任务适配。现有 `ResearchDecision` 的 `empirical_search`/supported_inferences 规则继续生效：局部 KKT、行空间匹配、单次数值见证不自动升级成区域性定理或结构优越性。

这是一项绑定上述提交的静态兼容性核查，没有在其他 worktree 执行实验、修改文件或宣称主线运行回归已通过。具体文件差异和核查范围保存在隔离证据的 `mainline_compatibility.json`。

先审批可复用几何、单侧约束数学与可选序列化字段；为正式 PHS TaskAdapter 和固定被动执行增加独立契约、注册版本、评价及预算回归。随后新建正式 Study 身份，重新冻结任务、结构空间和数值环境，再进行用户批准的验证。不得把本次开发结果追认成此前已封存 Benchmark 的成功，也不得覆盖第一、第二轮失败记录。

未来回归应覆盖旧配置身份、原主动执行的输入与物理语义、混合终止腱稀疏 Jacobian、实体孔穿越/穿透反例、材料点绑定切换、非正则梯度拒绝、真实正负张力集合、逐步计费和未知执行恢复。主线合并由用户另行审批。
