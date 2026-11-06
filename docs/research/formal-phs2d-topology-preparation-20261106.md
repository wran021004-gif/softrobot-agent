# PHS-2D 拓扑扩展及正式研究准备（2026-11-06）

本次在 `codex/formal-study-phs2d-20261106` 延续 Stage II 工作，不合并 main。
正式研究尚未启动；新的 Study 等待最终身份、预算与执行范围的明确批准。

## 设计空间与冻结边界

新的 `family_space_phs2d_topology_research_v3.json` 使用现有
`serial_family_space_v2` 生成接口，开放 **1～9 段、1～12 腱**。
版本化的 FamilySpace 定义、范围及生成规则可追溯；候选及其中合法参数由 Main 自主选择。
长度、Young 模量、截面形状和尺寸、已注册材料/几何参数、路由半径、角度、相位、
导向孔、锚点与逐腱 payout 都保留各自原有合法范围及实际效果语义。
不预设某个拓扑或优化方向，也不把历史 C4 作为默认最优或固定参考。

原始十工况任务、载荷、环境、边界、模型形式与假设、质量定义、张力容量、
SLSQP 设置、差分步长、KKT/静力/稳定性标准、积分与接触设置、独立验收规则均未降低。
被动固定 payout 模型中，张力由约束和平衡决定；`pretension_n` 没有主动初始化效果。
该字段的改变不能被报告为有效预紧力实验。

## 原限制的来源与最小实现

| 位置 | 原限制 | 处理 |
|---|---|---|
| 旧 FamilySpace 配置 | executable segments `[9]`，tendons `[4,4]` | 旧文件保留；新空间显式开放全部声明范围 |
| `family_space.validate_request` | 执行域检查，以及 payout 字典键必须完全等于实际 tendon ID | 保留冻结域检查；通用 payout 域按实际腱数展开 |
| `FamilySpaceV2` | 只有四个具名 payout 域的接口 | 增加单一 `passive_payout_domain_m`；旧映射仍可读取并保持原序列化身份 |
| `agent.plan_schema` / `compact_plan_schema` | 从冻结执行域生成 Schema | 新域直接显示全部范围；补齐根据 Study 推断 family version 及 payout 数值界限 |
| `generated_serial.serial_components` / `generate_family` | V2 已动态生成 segment、guide、connector、payload、mesh 和路由 | 复用生成器，仅改 payout 赋值 |

V1 的两段入口仍服务历史任务；V2 通过原有 `serial=True` 路径动态构造串联组件，
不受该历史入口的两段检查约束。本次未新建生成器、Worker、参数注册系统或静力框架。

通用 payout 域沿用原四项完全相同的数值：**[0.3, 0.5] m，默认 0.406 m**。
候选拥有独立的 `payout_lengths_m.tendon_0` 到 `tendon_(ntendon-1)`。
每项可取不同值，遗漏项继承默认值，候选不存在的腱 ID 被拒绝。
长度不同的候选可能需要 Main 重新选择合法 payout；默认值不保证静力资格。

`PassiveModel.payout` 按真实 physics tendon 顺序取值；`tendon_jac` 使用
`(model.ntendon, model.nv)`；`StaticProblem` 的约束、Jacobian、乘子、容量与约化刚度
原已采用实际维度。`passive_execution` 的 tendon 索引、约束观测及十工况信号也按真实腱数构造。
未发现需要改写这些物理公式的固定四腱假设。

## 代表性工程检查

真实工程记录见 [topology_checks.json](../../evidence/formal_phs2d_preparation_20261106/topology_checks.json)。
使用正式原任务、8 cells/段、冻结原型和求解设置；独立临时工程 Store 不属于正式 Study 科学账本。
每组均通过请求解析、候选生成、连接关系、独立 guide hole、路由/孔距检查、原生编译、
payout 顺序、Jacobian 维度、约束分类数组以及十工况输出信号绑定检查。

| 段×腱 | 原生 nv | payout / Jacobian 维度 | 零位姿接触 | 原始 forward |
|---|---:|---|---:|---|
| 1×1 | 16 | 1 / 1×16 | 0 | 完成；另做原设置无载静力检查，通过局部资格 |
| 1×12 | 16 | 12 / 12×16 | 0 | 完成；零位姿资格诊断维度检查完成 |
| 9×1 | 144 | 1 / 1×144 | 228 | `FactorizeHessian: rank-deficient sparse Hessian` |
| 9×12 | 144 | 12 / 12×144 | 228 | 同上 |
| 9×4 | 144 | 4 / 4×144 | 228 | 同上 |
| 5×6 | 80 | 6 / 6×80 | 68 | 同上 |

kinematics position stage 用于记录实际初始几何和维度；它不替代失败的完整 forward，
也不赋予静力或动态资格。失败完整保留。接触与秩亏的因果关系尚未建立。
这些默认候选的初始化失败不构成全局拓扑限制，更不证明该拓扑不可行。
即使单段无载静力合格，也不能推断加载后的十工况表现。

9×4 回归比较新旧空间生成的完整 `(design, mesh, physics)`，结果相等。
未做完整十工况、批量拓扑搜索、Provider 预演或正式科学 Worker 执行。
准确耗时与原始最小拓扑静力结果保存在上述 JSON 中。

## 研究工作流与请求预算

修复了物理 Replay pending 的展示：实际 candidate、Plan、source、route、episode 数、
request ID、预留资源与真实 Worker 记录。没有启动/终止记录时保持未知，不推测存活状态。
物理 Plan、pending、result 直接保留精确关联，并拒绝不同候选或不同操作键的关联。

全部新结果索引、最新数学结果、最新静力资格与资格之后的证据，改为使用原 Store 事件顺序，
不再按结果类别拼接后猜测最新记录。交错数学—物理—数学资格的回归已覆盖。

预算申请按用户直接修正准备为：Provider **64**，其中最后 **6** 次用于收尾；
数学评价、物理 episode、公开操作只记账，不设累计配额。
NMPC、PPO/RL、Offline NLP、BDF 仍为 0 授权。每次方法请求的有限参数和现有工程 watchdog 保留。
请求预算可在已结算边界通过现有、精确身份绑定的有限追加机制增补；Main 无权自行追加。
追加任务附表写回 32/80/320，与此前直接修正冲突，已向用户提出澄清。
当前申请是待批准提案，不能作为已获科学授权的记录。

## Gateway、环境与 Handoff

运行配置为 gateway `http://127.0.0.1:8787/v1` 的 `gpt-5.6-sol`，
Main `medium`、Reporter `none`，共用请求预算。认证信息仅引用本地私有文件，不进入证据。
认证只读 health/models GET 均为 HTTP200，精确模型存在；这不证明推理额度恢复。

执行环境预检使用指定 `.mainline5-env/Scripts/python.exe` 和三项单线程变量，状态 `ready`。
已核对 NumPy、SciPy、CasADi、MuJoCo、Pydantic 与 SDK 版本。
没有启动 MATLAB/SoRoSim。可选 cvxpy 未安装，但本 Study 未授权其 conic 方法，不影响本范围 readiness。

S127.6 提供真实工具调用和独立 SDK 恢复证据，但模型为 `deepseek-flash`，不能单独作为当前 gateway 的同接口证明。
进一步复用了父 `phs2d-mechanism-successor-20261105` 原始 104 次请求账本中的真实
gateway `gpt-5.6-sol / medium` request-feedback handoff：原始请求/收据、独立恢复、
下一次成功请求中的精确 feedback 均可核验。

新增的 `session_handoff.assess_live_admission` 只读复核这些技术记录；
`admit_formal_study` 复用 `formal_study_authorization`，要求当前 Study 身份、implementation freeze、
明确 handoff 执行范围和技术证据。只有用户正式批准后才由该入口记录原有 pilot 准入字段。
当前未手工改布尔字段，未使用 `session_handoff=False`，未继承父授权。

## 独立身份与剩余边界

原绑定机制只允许 implementation migration，不允许改变冻结 FamilySpace。
依追加任务第七节，保留两个原 Store 及全部账本，另准备独立
`phs2d-topology-successor-20261106`。仅从原准备候选重新绑定 C4 参数；
它仍未评价，不导入父 Plan、数学结果、资格、物理结果或授权。
原父账本仍为 104 次请求；旧准备 Study 仍为零 Provider、零数学与零物理评价。

最终身份、freeze、环境、候选与技术准入证据见
[preparation.json](../../evidence/formal_phs2d_preparation_20261106/preparation.json)，
独立授权范围见 [authorization_request.json](../../evidence/formal_phs2d_preparation_20261106/authorization_request.json)。
测试结果见 [validation.json](../../evidence/formal_phs2d_preparation_20261106/validation.json)。

仍保留真实模型限制：串联弯曲、无轴向/剪切/扭转/摩擦模型、未验证 swept self-collision；
具体孔距、截面与路由必须通过真实几何检查；默认长链初始接触/forward 失败待 Main 研究。
本次没有证明任何拓扑的完整动态通过、硬件性能、全局可行性或不可行性。
下一步仅在用户批准最终申请后，记录授权和正式 Handoff 准入，直接启动原十工况自主研究。
