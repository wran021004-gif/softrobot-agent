# 被动失败、统一接口与开放设计空间补充检查

## 1. C 的 Hessian 失败原因及确定性

直接读取原 C Store（SQLite 只读连接）、Worker 请求与保存结果，没有重发 Provider、重跑 C Worker、积分或修改原记录。提取见 `evidence/passive_interface_audit_20261107/c_failure.json`；原始文件仍在 `runs/research/passive-orchestration-20261107-c`。

候选引用 `944c1ba3a556b6da4f11129f8493d082e6960afb5373b5391e4ae4acbe8e83a9`，配置引用 `662d218c4c51bce96a3ff00b99c74369d919339bf642043cee8655aad00c5a40`，数学结果 `28322ac035817ec2aad2efc78620817deab2102d06e373c77e51db2d957517a9`。这是本次 C 的新失败候选，未导入历史成功设计。

调用位置是 `passive_equilibrium.solve → StaticProblem.constraint → StaticProblem.at → MujocoFailureSnapshot.call(mj_forward)`，阶段 `initial_forward`。128 个初始位置与速度分量均为零。首次 `mj_forward` 在 MuJoCo 3.13.0 内部报 `FactorizeHessian: rank-deficient sparse Hessian`；SLSQP 没有进入，第二起点未尝试。

失败矩阵是原生 Newton 加速度/软约束求解的矩阵，不是项目静力目标的有限差分 Hessian。官方版本源码中，`FactorizeHessian` 对质量/有效度量与活动软约束贡献构成的矩阵做稀疏 Cholesky，返回秩不等于维数便抛此错误；见 [MuJoCo 3.13 engine_solver.c](https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_solver.c#L2261)。不能用这个错误推断项目弹性 Hessian 非正定或候选全局不可行。

| 观察 | 已确定 | 尚不能确定 |
|---|---|---|
| 初始位置管线 | 172 个接触，最深记录约 -0.567 m；包括 floor 与柔性体接触 | 是否为唯一分解根因；别的构型是否可避免 |
| 腱长/payout | 四根腱路径约 1.058 m，固定 payout 为 0.25 m，超长约 0.808 m；几何上均在违反长度侧 | 没有平衡张力或合格活动集；不能称为已证实的张紧平衡 |
| 平衡求解 | 仅一次初始 forward 尝试；objective、gradient、项目 Hessian 列、QP/KKT 均为零 | 平衡残差、平衡点、KKT/稳定性资格均不可得 |
| 原生矩阵 | 报错确认进入原生稀疏分解路径 | 没有保存内部矩阵、实际数值秩、对称误差、条件数、特征值或失败主元 |
| 成本 | 原记录保留 1 个模型、1 次平衡尝试、1 次失败 forward；核心墙钟约 0.124 s；零积分 | 不把核心墙钟与外层准备/Worker 墙钟重复相加 |

归类为“**已确定的初始条件问题，与已确定的原生数值分解失败并存；二者的精确因果关系证据不足**”。初始状态不满足无接触/长度资格，不等于整个连续结构无解。快照中调用前 `ncon=0` 是未执行位置管线的数据，不能解释为无接触；另存的 position-only 结果才是初始几何观察。

没有证据证明项目 Hessian 构造、SLSQP 或活动集实现存在错误，因此未更换优化器、修改积分器、改动约束、加正则化或备用算法，也未升级 MuJoCo。未来应由 Main 根据这些事实选择合法初值/几何/payout 对照；本轮不替它搜索修复 C。

## 2–3. 六条接口边界及实际修复

| 边界 | 检查结论及改动 |
|---|---|
| Main → Tool Admission | 原被动搜索准入修复保留。新开放配置仍经原 `research_plan → ScientificStructureSearch → FamilyMixedSearch`，每次明确有限拓扑与搜索区间；不增加底层计算工具或 Main 权限 |
| Candidate → Identity | 原 `numerical_binding` 的被动 `basis=None` 分支保留，主动 basis 校验未删。新参数仍进入原物理与数值身份；错误的 mechanism/GVS 组合已被现有 AnalysisRequest 拒绝，无需重复检查 |
| FamilySpace → Generator | 新增可明确表达无人工上界的域；旧配置、旧域及序列化不变。固定绝对 payout 默认改为新配置显式选择的“实际零坐标路长”，不替代资格检查 |
| Generator → Compiler → Model | 修复相同 Polygon 截面在后续段继承 linear 插值时仍被拒绝的问题；相同截面可作为常截面返回。增加显式 step/linear 选择，允许使用现有 step 模型表达不同 Polygon 站点；不新增 Polygon 线性变形内核 |
| PhysicalProblem → Search/Math | 主动与被动适配器及原准入保持。修复旧样式被动搜索 guidance 残留 CONIC 目标/“省略 evaluation_mode”的说明。查询仍必须显式选被动模型，不能落入主动 CONIC 路径 |
| Evidence → Reporter → Main | 原被动搜索 `physical_problem/diagnostic_only/score_semantics/task_acceptance=unmeasured`、资格与失败字段保留。C 原 Reporter 已 available，后续 Main 确实读装配参数；没有新 Main/Reporter 请求。未改写原解释或把数学 computed 改成物理通过 |

没有发现需要复制 Store、工具、状态机或改动主动数值内核的问题。本次代码改动集中在已有 FamilySpace、生成器、截面插值及搜索/配置接口，Knowledge/Skill、manifest 和旧知识读取实现未修改。新检查配置复用已完成的组织版 Knowledge 策略，不重排知识正文。

## 4. 参数贯通表

R/G/C/F 分别表示 Registered / Generated / Compiled / Reflected。F 使用真实 MuJoCo XML 模型属性检查，不以注册元数据代替。少量确定性样例涵盖两段两腱和三段三腱；没有进行物理积分或宣称这些结构能完成任务。

| 类别 | R/G/C/F | 证据及限制 |
|---|---|---|
| 段数、段长 | 是/是/是/是 | 真实模型自由度与段长/单元分配一致；非默认段长改变单元质量和刚度。未生成大规模链来声称所有数量均物理可行 |
| 腱数、拓扑 | 是/是/是/是 | 二腱、三腱模型及共享 Base 起点；显式 route 可经过真实导孔、终止于终端 payload。外部锚点/环境支持仍被原检查拒绝 |
| Payout | 是/是/是/是 | 新配置遗漏值由该候选零坐标路长确定；真实长度变化带动默认 payout，模型无主动通道。任意显式正长度是否张紧/可平衡须另诊断，不存在通用有限长度区间保证可行 |
| 密度 | 是/是/是/是 | 密度、长度、截面经编译联动质量及质心处惯量；检查真实 body_mass、body_ipos、主惯量之和。均匀密度单独缩放不会改变几何质心位置 |
| 自然曲率 | 是/是/是/是（弹性参考） | 进入编译 natural_rad 与模型 qpos_spring。**不改变零坐标初始几何**：这是原 constitutive_reference_only 语义及冻结初始化要求，未擅自改成预弯初态 |
| Polygon | 是/是/是/是 | 后续段相同 Polygon 站点可真实编译；独立矩形轮廓面积、偏心质心检查；原多边形有效性/孔洞检查保留。不同轮廓的任意 linear 插值仍不支持，可显式选择 step |
| 截面尺寸、壁厚 | 是/是/是/是 | tube 内外半径的解析面积与最终单元属性检查；原截面惯量与质量/刚度计算保留 |
| 杨氏模量 | 是/是/是/是 | 模量/单元长度的已知比例与真实 jnt_stiffness 对应 |
| 阻尼 | 是/是/是/是 | 原弯曲黏性/单元长度映射与真实 dof_damping 对应；不宣称已校准材料 |
| 网格 | 是/是/是/是 | 非默认 1/2/3 单元真正改变模型 DOF、单元质量/惯量/刚度分配；最终独立验收仍须遵守所选数值协议，不把网格当物理结构性能变量 |
| 导向位置 | 是/是/是/是 | 真实 guide_hole 和 payload 端点变化改变编译路长、默认 payout 与最终腱路径；仍受实体导孔包络和间距约束 |

## 5. 旧人工范围与当前边界

旧 `family_space_base_only_passive_v1.json` 未改写，它仍冻结 1–32 段、1–64 腱、1–64 单元及有限材料/几何/payout 范围，这些只约束旧配置。

新 `family_space_base_only_passive_open_v2.json` 的计数上界、材料/尺寸/曲率/黏性与 payout 等人工上界为 null；正长度、正密度/模量、非负黏性、站点 [0,1] 等数学/物理定义仍保留。Polygon 不再有旧 64 顶点复杂度上限。实体包络、孔间距、截面正面积/合法惯量、路线所属与顺序、Base 起点及无外部支撑由原生成/编译器检查。没有用历史成功结构提供新边界。

`study_passive_open_interface_audit_v2.json` 选择该开放域，Provider/被动数学/物理预算为零。它不是新搜索活动。自动坐标搜索必须给出本次有限计数和有限坐标区间；没有把无穷域变成隐含的巨大数值搜索范围。完整显式生成可用更多合法路线、导向和 Polygon，原混合搜索仍是有限极坐标/方形 Polygon 子空间，任意路线无法无损作为搜索种子时继续明确拒绝并引导显式生成。

开放物理域没有有限全局宽度时，原“按域宽归一化”的局部导数/优化不会被虚报为可用；参数视图明确要求另选有限局部研究域。生成能力与特定数学方法支持保持分开。这不是永久物理参数上界，也没有更换数学框架。

## 6. 十工况评分

新配置 canonical_task 与原阶段三配置完全相等：原五个 material_s 的正/反向载荷，共十工况；加载点、力幅值、所有时间/评分窗口、位置/速度/稳定性/长度约束、求解器及失效状态均未修改。原 `phs2d_original_v1` 完整动态评价适配路径仍被识别，独立 Replay 准入和正式评价器不变。没有重跑十工况；静力资格或局部数学结果始终不获得正式验收信用。

## 7–8. 验证状态

已通过新增三个定向检查：归档 C 及任务一致性、代表性参数到真实模型、开放搜索区间及主动/被动准入。另通过原四个定向回归：科学问题组编译、被动物理联动/Polygon/网格/Base-only、历史空间与设计序列化不变、旧主动配置身份不变。

主动真实两尺度回归：待对已提交源码执行现有 `ConstrainedMechanicsTests.test_real_active_two_scale_native_path`。该测试走原 Worker，不用合成数值矩阵；不运行新的 Main 或 Provider，也不是完整 Replay。结果将在完成后追加到本报告。

## 9. Git

使用现有 `codex/passive-research-capabilities-20261107`，保留此前所有提交及知识资产。实现与验证记录采用增量提交，待主动真实回归记录完成后一并正常 push；不 Force Push，不提交 Store、凭据或历史成功配置。
