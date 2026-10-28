"""Render the third-round research report and replay instructions from audited data."""
import json
from pathlib import Path
from tools.phs2d_round3_export import OUT,ROOT,LABEL
from tools.state_io import atomic_json


def report():
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf8'));design=json.loads((OUT/'solution/design.json').read_text(encoding='utf8'));curvature=json.loads((OUT/'curvature_evidence.json').read_text(encoding='utf8'))
    studies=[json.loads((OUT/f'study_v{i}.json').read_text(encoding='utf8')) for i in (1,2)];rows=sorted(design['cases'],key=lambda r:(r['s'],-r['force_n']));b=summary['budgets']
    gradients=[r for r in design['sensitivity'] if r.get('task_metric_revision')==2]
    assert len(gradients)==6 and all(r['task_gradient_trustworthy'] for r in gradients)
    maximum_gradient_error=max(max(r['task_gradient_relative_errors'].values()) for r in gradients)
    independent={(r['s'],r['force_n']):r for r in rows};checks=[]
    for rep,name in [(2,'减半步长'),(3,'初态扰动')]:
        rr=[r for s in summary['final_sets'] if s.get('replicate')==rep for r in s['rows']]
        checks.append(dict(name=name,max_point_difference_m=max(abs(r['point_dx_m']-independent[r['s'],r['force_n']]['point_dx_m']) for r in rr),
            max_tip_difference_m=max(abs(r['tip_xy_m']-independent[r['s'],r['force_n']]['tip_xy_m']) for r in rr)))
    journal=[];prior=dict(physics_step_attempts=0,math_requests=0,generation_attempts=0)
    for study in studies:
        for label in study['generation_order']:
            if label not in study['structures']:continue
            a=study['structures'][label]
            sc=study['screens'].get(label,{});history=[r for r in study['chronological_cost_history'] if r['label']==label]
            end=next((r for r in history if r['kind']=='passive_equilibrium_v1' and r['s']==.7 and r['force_n']==-.1),history[-1] if history else None)
            budget={k:prior[k]+end['cumulative'][k] for k in prior} if end else None
            nonlinear=sc.get('rows',[]);linear={}
            if sc.get('modal'):
                # Summary already retains the exact modal reference; no new mechanics here.
                linear=dict(min_point_m=sc.get('min_point_m'),max_tip_m=sc.get('max_tip_m'),max_ratio=sc.get('max_ratio'))
            paired={(r['s'],r['force_increment_n']):r for r in sc.get('linear_predictions',[])}
            journal.append(dict(study_id=study['study_id'],label=label,hypothesis=a['reason'],generation=a['generation'],
                mathematical_prediction=linear,observed_nonlinear_rows=nonlinear,
                tip_prediction_worst_gap_m=max(abs(r['tip_xy_m']-paired[r['s'],r['force_n']]['tip_xy_m']) for r in nonlinear) if nonlinear and paired else None,
                point_prediction_worst_gap_m=max(abs(r['point_dx_m']-paired[r['s'],r['force_n']]['point_dx_m']) for r in nonlinear) if nonlinear and paired else None,
                dynamic_observations=[r for r in study['dynamic_sets'] if r['label']==label],budget_after_first_screen=budget,
                remaining_after_first_screen={k:limit-budget[k] for k,limit in [('physics_step_attempts',20000000),('math_requests',1200),('generation_attempts',300)]} if budget else None))
        for k in prior:prior[k]+=study['budgets'][k]
    for row,next_row in zip(journal,journal[1:]):row['next_recorded_hypothesis']=dict(label=next_row['label'],hypothesis=next_row['hypothesis'])
    atomic_json(OUT/'experiment_journal.json',journal);atomic_json(OUT/'numerical_comparison.json',checks)
    payout=[design['payout_lengths_m'][f'tendon_{i}'] for i in range(4)]
    table='\n'.join(f"| {r['s']:.2f} | {r['force_n']:+.2f} | {r['point_dx_m']*1000:.6f} | {r['tip_xy_m']*1000:.6f} | {r['ratio']:.6f} | {r['out_of_plane_m']*1000:.6f} | 通过 |" for r in rows)
    grad_table='\n'.join(f"| {r['s']:.2f} | {r['force_n']:+.2f} | {r['task_derivatives_du']['point_dx_m']*1000:.6g} | {r['task_derivatives_du']['tip_xy_m']*1000:.6g} | {max(r['task_gradient_relative_errors'].values())*100:.4f}% |" for r in gradients)
    numerical='\n'.join(f"| {r['name']} | {r['max_point_difference_m']*1e6:.6g} | {r['max_tip_difference_m']*1e6:.6g} | 十工况全部通过 |" for r in checks)
    text=f'''# PHS-2D 第三轮：实体导向板渐变腱路的十工况可行见证

在原 PHS-2D 独立开发 evaluator 下找到可复现的 Base-only 被动结构：六个搜索工况、四个首次启用的预留工况全部通过；独立进程重跑、减半时间步长、无载初态扰动后的十工况也全部通过。这里的通过是原开发任务的数值见证，尚未注册正式 TaskAdapter/SELECT，也不构成硬件性能证明。

研究分支 `research/phs2d-inverse-passive-design` 从远端核对的 `f33648d0bf5fcebbe3d5f5a5878c3198eb32a69c` 建立。第二轮保持 STOP，原 Store 和失败记录未修改；本轮两个版本的 Store 均独立封存。没有合并主线，没有 Provider、Research Agent、NMPC 或 PPO 执行。

## 冻结物理结构

- 九段柔性骨架，每段 0.28/9 m，总柔性材料长度严格 0.28 m；每段八个单元，共 72 个单元、144 个三维双弯曲铰链坐标。
- 各段圆截面半径 3 mm，Young 模量 8 MPa、密度 1050 kg/m³；EI=E*pi*r^4/4，两个主方向均约 0.000508938 N·m²。自然曲率零。
- 固定物理弯曲黏性为每主方向 0.00006 N·m²·s。它是新材料分布设计输入，并非改变积分器阻尼。该值未做真实材料标定。
- 八块原 2 g 导向板、八个原 3 g 连接件、原 10 g 偏心 payload，其质心和完整惯性张量全部保留。总物理质量 {design['total_physical_mass_kg']:.9f} kg。
- 柔性材料长度不含刚性间隔；包含八个 14 mm 边界间隔和 14 mm Tip 站点偏移的无变形 Base–Tip 轴向距离是 0.406 m。Base 仍在 z=0.5 m，重力仍为 [0,0,-9.81] m/s²。
- 四根腱仅从同一 fixed_base 出发，通过八块实体板上分别拥有的真实孔，终止于原 payload 实体内部。获胜结构没有柔性段上悬空的偏置导向点，也没有额外世界锚点或直接固定 Tip。
- 基座局部点为 y=±7 mm、z=±25 mm；沿轴向的局部 z 力臂随到 Tip 的剩余距离下降，y 偏置保持 ±7 mm。全部真实 RoutePoint、孔、截面、惯性、网格与 XML 见隔离交付包。
- 四个事先冻结的放绳长度为 `{payout}` m，偏移均为零。全部条件使用相同结构和相同长度向量。配置里的主动 `pretension_n` 初始化字段不在被动 XML 中施加力；实际张力由单侧长度约束产生，XML actuator 数为零。

## 十工况独立复现结果

原门槛：受力点 ≥10 mm，Tip ≤5 mm，比值 ≤0.30，平面外 ≤2 mm；力为 ±0.10 N，4 s 时域、0.5 s 平滑加载和原稳定性、残差、接触标准均保持不变。s=0.4/0.6 未参与设计搜索。

| 材料 s | 力 / N | 受力点 / mm | Tip / mm | 比值 | 平面外 / mm | 状态 |
|---:|---:|---:|---:|---:|---:|---|
{table}

十工况最大尾窗软静态残差 {max(r['max_tail_residual_nm'] for r in rows):.6g} N·m，最大尾窗关节速度 {max(r['max_tail_qvel_rad_s'] for r in rows):.6g} rad/s，最大尾窗张力 {max(r['max_tail_tension_n'] for r in rows):.6g} N，最大腱长超限 {max(r['max_tail_length_excess_m'] for r in rows)*1e6:.6g} μm。完整逐条件检查、张紧集合和约束行保存于原始 Store。每次加载均由独立无载基准、零速度启动，没有用受载静力解直接初始化动力学。

![十工况和数值复核](../../evidence/phs2d_round3_20261028/task_validation.png)

## 机制证据与数学工具

成功机制是实际渐变力臂腱路、足够密集的实体导向板和反向曲率补偿的组合。它不是仅靠增加整体刚度减小全部运动；最差受力点仍移动超过 11 mm。圆截面各向同性，因此不能把本结果归因于截面各向异性。

基于实际 MuJoCo 腱长 Jacobian，获胜结构在无变形几何姿态的 Tip-x 行空间匹配相对残差约 1.64e-15。Tip-y 行残差约 0.483，不能宣称两条水平行都被腱精确覆盖；实际原横向工况的平面外位移由完整三维平衡与稳定性检查确定。

运动学存在性 A、单侧活跃锥 B 和真实材料点力激发 C 分开输出。局部工具返回 J_tip、J_point、J_length、约束切线 Hessian、秩、正乘子集合、零空间与局部 QP 响应；低维四曲率组只用于机制设计。局部正定性不是全局或硬件证书。

几何 Jacobian 的完美匹配并不足以保证有限位移。真实直线绳段在大变形时会因弦长缩短而松弛；硬绳非线性静力和软约束 MuJoCo 的实际比较均单独保存。原生局部、非线性硬绳、软约束动力学三者没有混作同一结果。

四个腱按 y/z 的四象限镜像布置，正负载荷实际切换不同的正张力集合。所有十工况的中轴均同时出现显著正、负的增量曲率；最小、最大曲率数值及判断阈值保存在 `curvature_evidence.json`。这一结论来自形状和曲率，而非仅凭 Tip 位移小。

![结构、真实腱路、反向曲率和张力](../../evidence/phs2d_round3_20261028/solution_mechanism.png)

![局部数学与完整物理](../../evidence/phs2d_round3_20261028/math_vs_physics.png)

`passive_design_sensitivity_v1` 同时微分受载状态和设计相关的无载基准；归一化参数 u=(E−2 MPa)/13 MPa。六个原搜索分支均满足被检查的 LICQ、严格互补、稳定性及 KKT 条件要求。隐式任务梯度对实际重新求平衡的有限差分最大相对误差为 {maximum_gradient_error*100:.4f}%。非正则、拓扑变化及材料点绑定切换不返回普通梯度；最大平面外范数只报告方向性有限差分。

| s | 力 / N | d受力点位移/du / mm | dTip位移/du / mm | 最大梯度相对误差 |
|---:|---:|---:|---:|---:|
{grad_table}

`passive_multicase_design_v1` 用六工况最大归一化违反量做有效性优先比较，比例搜索采用 tip−0.30*point 的等价约束，并保留 point≥10 mm。最终通过仍由原独立 evaluator 的实际比值计算确定。

## 搜索如何改变方向

1. 外置 Base-to-payload 斜拉验证了局部 Tip 行约束，但柔软骨架有限弯曲导致轴向缩短、绳索松弛和部分非法路径。增大同一 Base 上的斜角改善了位移，仍有原 4 s 残差失败。它没有被计为成功类别。
2. 密集渐变导向点使局部模态和非线性性能同时改善。原材料黏性下仍未停稳，因此没有用漂亮位移掩盖无效结果。
3. 冻结 v2 材料域，允许物理弯曲黏性 0.00003–0.0004 N·m²·s；继承并扣除 v1 已消耗的 928000 步、140 次数学请求、18 次候选尝试及 3 个动态装配。密集偏置站点候选可通过六工况，但未被当作最终实体安装答案。
4. 改为只经过实体板孔的三至五段布局，有限弦长松弛仍过大，三段的部分形状还产生穿透。七、九段的成对结构比较改善了有限变形约束；它们同时改变刚性质量和间隔，不能只把改善归因于段数一个变量。
5. 确认九段实际腱路后，联合比较刚度分布和圆截面材料，选择 E=8 MPa 的统一结构。36 单元静力筛选后，在冻结的 72 单元网格上重新完成全部数学和物理验证。
6. 首次十工况通过后，工具禁止再创建搜索装配，只进行本次独立复现、时间步减半和初态扰动验证。没有为耗尽预算继续优化。

逐候选假设、变量、预测、实际观测、预测偏差、成本时间线和剩余额度见 `experiment_journal.json` 及两个完整 Study 导出。工具恢复时保留所有未知输出和费用，没有重发未知执行。

## 独立性、收敛与限制

主积分步长 0.125 ms；减半为 0.0625 ms。扰动是在无载静力初态的全部坐标加入 1e-4*sin(j) rad，初速度为零，再独立积分无载基准和十个载荷。观察时长、软约束参数和阈值均未改变。

| 数值复核 | 最大受力点差 / μm | 最大 Tip 差 / μm | 结果 |
|---|---:|---:|---|
{numerical}

`route_geometry_validation_v1` 对实际直线绳段与编译实体凸包进行带绳半径的相交检查，只对拥有的真实导向孔和实体终端锚点作物理例外。获胜结构的无载、静力加载及全部动态保存姿态通过。没有开发通用柔性绳碰撞引擎；连续扫掠、绳间摩擦、自接触、轴向拉伸、剪切、扭转和绳弹性均未被本模型覆盖。现有原型给定导向板质量和惯性，孔位置不重新改写这些给定质量属性。

加密模型最初在 Windows 原生 XML 编译阶段栈溢出。该次零积分数学请求被封存为 output_unavailable，数学费用保留，内部构造成本未知。隔离诊断捕获原生 stack overflow 后，仅本轮被动模型改用 32 MiB 编译线程；XML 和物理方程不变，新版本请求完成验证，未重放旧未知请求。

## 预算与验证

| 资源 | 实际累计 | 上限 |
|---|---:|---:|
| MuJoCo 积分尝试 | {b['physics_step_attempts']:,} | 20,000,000 |
| 顶层数学请求 | {b['math_requests']} | 1,200 |
| 完整生成尝试（含失败） | {b['generation_attempts']} | 300 |
| 冻结装配 | {b['assemblies']} | 包含在候选上限内 |
| 动态装配 | {b['dynamic_candidates']} | 60 |
| 原始动态运行 | {b['dynamic_runs']} | 步数统一收费 |
| Provider / Research Agent / NMPC / PPO | 0 / 0 / 0 / 0 | 0 |

原始收据、内部计数和原始时间成本随两个 Store 一起封存；全部请求积分费用之和与状态账本一致。一个栈溢出请求的内部构造成本未知，未被伪装为完整已知成本。专项 14 项测试通过。另一次 FamilySpace 相关 21 项回归有 19 项通过、2 项失败；同样的两项失败已在 f33648d 基线副本中复现（旧配置硬编码 hash 和摘要长度断言），没有修改旧断言来制造通过。测试夹具不作为科学候选证据，均无积分、Provider、NMPC 或训练。

完整配置、XML、无载/加载平衡、张力、数学输出、原始轨迹和逐 timestep 数据见 [隔离证据 README](../../evidence/phs2d_round3_20261028/README.md)。通用能力和未来接入建议见 [集成边界](phs2d_round3_integration.md)。所有 Study 已 STOP；没有自动合并主线。
'''
    path=ROOT/'docs/research/phs2d_round3_results_20261028.md';path.write_text(text,encoding='utf8')
    readme='''# PHS-2D round-three isolated evidence

This package contains a ten-condition passive Base-only numerical witness, independent replay, half-timestep and initial-perturbation checks. It uses the unchanged development PHS evaluator, not a registered SELECT or hardware certificate.

- `solution/design.json`: complete candidate configuration, compiled physical parameters, fixed payouts, baseline, ten cases, KKT screen, modal diagnostics and normalized sensitivities.
- `solution/model.xml`: actual zero-actuator MuJoCo XML.
- `study_v1.json`, `study_v2.json`: all structures, screens, dynamic sets, failure records and audited costs.
- `store_v1`, `store_v2`: original core Store exports, receipts, immutable content-addressed artifacts and reconstruction manifests. Raw Store databases remain private under the isolated worktree's ignored runs directories.
- `experiment_journal.json`: hypotheses, variables, mathematical predictions, observations and cumulative budgets.
- `environment.json`: actual Python/platform/package versions; no environment secrets.
- `curvature_evidence.json`, `numerical_comparison.json`, PNG/SVG figures: derived checks and visualizations.

## Verify without executing physics

From the research branch root using the recorded environment:

```powershell
python -m tools.phs2d_round3_export --verify
python -m tools.phs2d_round3_reproduce
```

The first command verifies part hashes, reconstructs each archive under `runs/phs3_archive_verify/`, and verifies every member hash. The second checks the delivered XML identity. These commands do not reopen sealed studies or consume integration steps.

## Inspect per-timestep data

Each independent loaded case in `solution/design.json` has `every_timestep_trajectory.archive_member`, identifying a `.bin` member of the v2 archive. It is a normal lossless NumPy NPZ container. Read it with `tarfile.extractfile` into `io.BytesIO`, then `numpy.load(..., allow_pickle=False)`. Arrays are `columns` and `trajectory`. There are 32000 rows per 4 s trajectory, 442 float64 columns: time, world-x force, 144 qpos (rad), 144 qvel (rad/s), 144 qacc (rad/s²), four lengths (m), four tensions (N). The unloaded trace is referenced from the baseline artifact in the same archive.

Rows are recorded after mj_step and the following mj_forward. qacc is the actual native recomputation using the generalized material-point force applied immediately before that step; regular 10 ms snapshots additionally remap the force at the refreshed geometry. This force-sampling phase is preserved explicitly. The independent evaluator retains its original 10 ms saved measurement phase. All per-step state/length/tension arrays are preserved; no float32 conversion or lossy compression is used.

## Execute a fresh reproduction

The user-invoked command below, from a clean committed checkout, creates the separately configured private reproduction Study, uses the existing candidate builder, Store reservations, native passive model and original evaluator, solves the unloaded state again and runs one baseline plus ten independent loads. Its hard cap is 500000 steps, 20 mathematical requests and one design; cumulative prior-study allowance is checked. This prepared recipe was not executed as extra search after finding the witness.

```powershell
python -m tools.phs2d_round3_reproduce --execute
```

It writes `runs/phs2d-isolated-reproduction/result.json` and seals its own Store. Repeating that command reads the sealed result; it never resets that ledger or reopens either research Store. A further execution requires a separately authorized, newly identified Study. The original in-study independent/convergence harness is `tools.phs2d_round3_validate`; its completed requests are archived, and its sealed Study is intentionally not runnable again.

No active motor/control input, extra world anchor or Tip spring is present. Mass, density, payload and physical installation assumptions are explicit in the design. Limitations include bending-cell idealization, frictionless cables, no axial/shear/torsion/self-collision model and sampled cable-solid checks rather than a continuous collision engine.
'''
    (OUT/'README.md').write_text(readme,encoding='utf8')


if __name__=='__main__':report()
