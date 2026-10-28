"""Portable Chinese documentation generated from the exported frozen evidence."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phs2d_io import TASK_DIR,RESEARCH_SHA,read,write,sha


def save(path,text):
    path.write_text(text.strip()+'\n',encoding='utf8')


def generate(package):
    base=package/TASK_DIR
    structure=read(base/'structure.json');physics=structure['physics'];task=read(base/'task.json')
    dataset=read(base/'dataset.json');payout=read(base/'payout_lengths.json');protocol=task['protocol']
    for name in ('phs2d_io.py','view_phs2d.py','simulate_phs2d.py','validate_phs2d.py','validate_all.py',
                 'portable_xml.py','run_portable.py'):
        shutil.copyfile(ROOT/'scripts'/name,package/'scripts'/name)
    save(base/'requirements.txt','mujoco==3.13.0\nnumpy==2.4.6')
    save(base/'task_zh.md',f'''# PHS-2D 被动头部稳定任务

机器人顶部 Base 固定于世界 z=0.5 m，在 [0,0,-9.81] m/s² 重力下向下悬垂。
四根被动腱在实验前固定放绳长度，不进行主动控制，不使用电机或主动张力输入。
在中轴指定材料位置 s 沿世界 x 轴施加 +0.10 N 或 -0.10 N 横向力。
机构允许明显弯曲，同时应保持 Tip 的世界 xy 平面位置稳定。

s 是累计柔性材料长度占 0.28 m 的比例，排除刚性板/连接件间隔；Tip 是原 tip_site，
位于 payload 的局部 [0.014,0,0] m。Base、Tip、施力点都不新增世界约束。

六个搜索条件为 s=0.30、0.50、0.70 各 ±0.10 N；四个预留独立验证条件为 s=0.40、0.60 各 ±0.10 N。
十个加载条件均从同一独立无载基准末态 qpos、零 qvel 开始，使用同一装配和长度向量。
equilibrium/ 单独保存原无力基准本身的完整 4 s 状态，其 t=0 也是原始已保存 snapshot。

## 原冻结标准（未修改）

- 受力点世界 x 位移绝对值至少 0.010 m（10 mm）。
- Tip 世界 xy 位移范数不超过 0.005 m（5 mm）。
- 上述 Tip/受力点位移比不超过 0.30。
- 全部原 monitor_s 监测点及 Tip 的世界 y 位移最大值不超过 0.002 m（2 mm）。
- 无载末态横向位置不超过 {protocol['initial_lateral_limit_m']} m，且原无载稳定检查通过。
- 原尾窗 {protocol['tail_s']} s 内：Tip 及监测点速度各不超过 {protocol['tip_speed_limit_m_s']} m/s；
  监测点漂移不超过 {protocol['tail_drift_limit_m']} m；关节速度无穷范数不超过 {protocol['qvel_inf_limit_rad_s']} rad/s；
  静态广义力残差不超过 {protocol['static_balance_inf_limit_nm']} N·m；腱长超限不超过 {protocol['length_excess_limit_m']} m。
- 单侧腱约束方向、非负乘子、各腱 8 N 容量、无异常接触及保存姿态的腱路/实体几何检查保持原样。

原 evaluator 比较无载与受载**最后一帧**位移，并在原 10 ms 样本网格检查尾窗稳定性；
逐 timestep 数据用于观察与完整性核验，不引入更改后的连续时间验收标准。
历史评价原件见各工况 original_evaluation.json 以及 evidence/artifacts/。

## 时间和数值设置

时域 4 s，timestep=0.000125 s，共 32,000 次历史积分；原真实末时间有约 2e-12 s 浮点累积误差，予以保留。
力在第 k 步开始按 t=k·dt、a=min(t/0.5,1)、F=F_target·a²(3-2a) 平滑加载。
原 XML integrator 为 implicitfast；其他 XML options 原样保留。
原 PassiveModel 在 XML 编译后另外将 iterations=100、tolerance=1e-10，独立脚本保留这两个运行时设置。
完整原协议、solreflimit/solimplimit、有效网格和采样相位见 task.json。
原协议继承的 cells_per_segment=12 是默认值；此候选实际网格以 effective_discretization 为准：每段 8 cells。

结论身份是 **PHS 开发性独立数值验收通过**，registered_acceptance 原值为 not_registered；
尚未注册正式 TaskAdapter/SELECT，也未验证真机性能。不得将历史通过改称正式 SELECT 或硬件证明。
''')
    lines=['# 九段被动结构与真实腱路','',
        '这是离散柔性机构的理想 MuJoCo 模型，不是机械加工 CAD。robot.xml 为原始 XML 的逐字节副本。','',
        f"- 来源提交：`{RESEARCH_SHA}`；候选：`{structure['label']}`。",
        f"- XML SHA-256：`{structure['xml_sha256']}`。",
        f"- 设计物理身份：`{physics['identity']}`。",
        f"- 总质量：{structure['total_physical_mass_kg']!r} kg。",
        '- 9 段、每段 8 cells、72 cells、144 弯曲 DOF、4 被动腱、8 实体导向板、8 连接件及原偏心 payload。',
        '- 柔性材料总长 0.28 m；含原刚性间隔与 Tip 偏移的无变形 Base–Tip 轴向距离为 0.406 m。',
        '- 弯曲圆截面半径 0.003 m，Young 模量 8e6 Pa，自然曲率零；每主方向物理弯曲黏性 6e-5 N·m²·s。',
        '- 近 Base 第一段密度 1100 kg/m³，其余 1050 kg/m³；材料黏性未经真材标定。',
        '- 无 actuator、无额外世界锚点、无 Tip 固定约束；pretension_n 是未启用的主动初始化字段。','',
        '## 全部实际物理部件','',
        '下表坐标均为各部件局部坐标，完整截面、碰撞顶点、旋转、COM 惯量张量及父子绑定见 structure.json。','',
        '| 部件 | 父索引 | 长度 m | 质量 kg | COM 局部 m | 刚度 N·m/rad | 黏性 N·m·s/rad | 自然角 rad |',
        '|---|---:|---:|---:|---|---|---|---|']
    for part in physics['parts']:
        lines.append(f"| {part['entity']} | {part['parent']} | {part['length_m']!r} | {part['mass_kg']!r} | "
                     f"{part['com_local_m']} | {part.get('stiffness_nm_rad',[])} | {part.get('damping_nm_s_rad',[])} | {part.get('natural_rad',[])} |")
    lines+=['','## 每个实际导向点、Base 起点和末端锚点','',
        '位置以所属固定 Base / 物理部件的局部坐标表示。guide_hole_positions_m 与原 XML site 坐标逐项绑定。','',
        '| 腱顺序 | 角色 | 物理部件 | 孔名 | 局部位置 m |','|---|---|---|---|---|']
    for tendon in physics['tendons']:
        for route in tendon['points']:
            body='fixed_base' if route['body']<0 else physics['parts'][route['body']]['entity']
            lines.append(f"| {tendon['entity']} | {route['role']} | {body} | {route['physical_binding'].get('hole') or '—'} | {route['position_m']} |")
    lines+=['','四个通道的固定 payout 均为 0.39274245978073885 m，精确顺序与 XML 上界见 payout_lengths.json。',
        '该值是单侧空间腱长度上界；腱可以松弛，张力由约束乘子产生，不是主动恒张力命令。',
        '导向路径为无摩擦理想空间折线。实体板、孔声明、孔拥有关系及历史几何检查完整保留；',
        '模型没有真实绳/孔接触、摩擦、弹性和磨损求解，不可将理想孔路等同真实穿绳接触仿真。']
    save(base/'structure.md','\n'.join(lines))
    result_table=['| s | 力 N | 受力点 mm | Tip mm | 比值 | 平面外 mm | 阶段 |','|---:|---:|---:|---:|---:|---:|---|']
    for row in sorted(task['original_cases'],key=lambda r:(r['s'],-r['force_n'])):
        result_table.append(f"| {row['s']:.2f} | {row['force_n']:+.2f} | {row['point_dx_m']*1000:.6f} | "
            f"{row['tip_xy_m']*1000:.6f} | {row['ratio']:.6f} | {row['out_of_plane_m']*1000:.6f} | {'搜索' if row['s'] in protocol['search_s'] else '独立验证'} |")
    data_table=['| 目录 | CSV 数据行 | CSV 列 | CSV bytes | NPZ bytes |','|---|---:|---:|---:|---:|']
    for entry in dataset['trajectories']:
        data_table.append(f"| {entry['directory']}/ | {entry['rows']} | {entry['csv_columns']} | {entry['csv_bytes']} | {entry['npz_bytes']} |")
    save(base/'README.md',f'''# PHS-2D：被动头部稳定十工况成功见证

顶部 Base 固定、在重力下向下悬垂的九段柔性机构，通过四根事先固定长度的被动腱，
在中轴指定位置承受世界 x 方向 ±0.10 N 横向力时明显弯曲，同时尽量稳定 Tip 的 xy 位置。
本包保存已完成的六个搜索条件、四个预留验证条件及一条完整无力基准。
本次导出新增物理积分为 **0 次**，没有搜索、优化、主动控制或真机实验。

身份是 **PHS 开发性独立数值验收通过**，未注册正式 TaskAdapter/SELECT。
原 M1–M6 的主动张力任务仍使用其原独立入口和原数据，不套用到本被动任务。

## 文件入口

- [task_zh.md](task_zh.md)、[task.json](task.json)：自然语言、冻结阈值、坐标、数值设置和观测相位。
- [structure.md](structure.md)、[structure.json](structure.json)：全部物理尺寸、材料、截面、质量、COM、惯量、真实导向点和设计身份。
- [robot.xml](robot.xml)：未经改写的成功 XML；[payout_lengths.json](payout_lengths.json)：通道顺序及真实长度上界。
- [dataset.json](dataset.json)：11 条轨迹、源 NPZ 身份、行列数、阶段与真实时间信息。
- equilibrium/：无力基准；s030_positive/ 等十个目录：真实逐 timestep 记录。
- 每条目录提供 trajectory_timestep.csv、states_timestep.npz、external_force_schedule.csv、initial_state.json、replay_spec.json、validation.json。
  十个加载目录另有 original_evaluation.json。原评价及所需原始 JSON 以内容寻址形式保存在 evidence/artifacts/。
- [evidence/numerical_validation.json](evidence/numerical_validation.json)：历史减半步长和初态扰动复核摘要，未混入主要动画数据。
- previews/：真实保存状态的中轴/位移/阈值图、原封存图及 MuJoCo 渲染。
- [../scripts/validate_all.py](../scripts/validate_all.py)：原 M1–M6 与 PHS 的类型化根校验入口。

本模型为离散柔性机构的理想 MuJoCo 模型，不是加工 CAD。柔性材料总长 0.28 m，每段 8 cells，共 72 cells、144 个弯曲 DOF。
八块导向板和八个连接件、10 g 原偏心 payload 及全部惯性保留；总质量 {structure['total_physical_mass_kg']!r} kg。
圆截面半径 3 mm，E=8 MPa；密度与物理弯曲黏性详见 structure.md。没有 actuator 或 Tip 固定约束。
Base 在世界 [0,0,0.5] m，局部 +x 经原安装旋转后竖直向下；世界 +z 向上，重力 [0,0,-9.81] m/s²。
s 为累计柔性长度比例，排除刚性间隔；Tip 为 payload 局部 [0.014,0,0] m 的 tip_site。
四根腱依 tendon_0、tendon_1、tendon_2、tendon_3 顺序，固定长度均为 **0.39274245978073885 m**。
它们是单侧长度上界，允许松弛；实际张力来自约束，而非主动张力或电机指令。

## 安装与校验

已验证原科学环境：Python 3.11.16、MuJoCo 3.13.0、NumPy 2.4.6、SciPy 1.17.1（Windows）。
查看、校验和本独立重放脚本只依赖 MuJoCo 与 NumPy，无需 SciPy、科研 Agent、Provider、Store 或 Harness。
下面命令均从**解压后的资料包根目录**执行，所有路径都相对资料包。
环境文件夹使用 .viewer-env，原根校验器允许该目录；切勿把回放输出或任意新文件放进资料包。

Windows PowerShell：
```powershell
py -3.11 -m venv .viewer-env
./.viewer-env/Scripts/python.exe -m pip install -r PHS2D_passive_head_stabilization/requirements.txt
./.viewer-env/Scripts/python.exe -B ./scripts/validate_all.py
./.viewer-env/Scripts/python.exe -B ./scripts/validate_phs2d.py
./.viewer-env/Scripts/python.exe -B ./scripts/view_phs2d.py --s 0.30 --direction positive --loop
./.viewer-env/Scripts/python.exe -B ./scripts/view_phs2d.py --condition equilibrium --loop
./.viewer-env/Scripts/python.exe -B ./scripts/view_phs2d.py --s 0.70 --direction negative --check-states --render ../phs2d_preview.png
./.viewer-env/Scripts/python.exe -B ./scripts/simulate_phs2d.py --s 0.50 --direction negative --check-only
```

Linux（未验证）：
```bash
python3.11 -m venv .viewer-env
./.viewer-env/bin/python -m pip install -r PHS2D_passive_head_stabilization/requirements.txt
./.viewer-env/bin/python -B scripts/validate_all.py
./.viewer-env/bin/python -B scripts/view_phs2d.py --s 0.40 --direction negative --loop
./.viewer-env/bin/python -B scripts/view_phs2d.py --s 0.70 --direction positive --render ../phs2d_preview.png
```

动画：空格暂停/继续，R 从头播放，L 切换循环，+/- 调整速度（也可 --speed 0.5）。
蓝线为原无力末态中轴，绿线为当前保存状态中轴，橙线为真实 Tip 轨迹；红色标记及箭头显示材料施力点和世界 x 力方向。
播放只跳转至真实保存帧，不插值、不积分。--check-states 对每帧执行独立运动学检查；--check-only 只检查加载。
--render 输出原模型 PNG，仍需要 OpenGL；Linux 的 MUJOCO_GL=egl/osmesa 未在本次 Windows 验证。
九段深层 XML 使用已验证的 32 MiB 编译线程，不改变物理方程。实际测试记录见根 viewer_validation.json。
Windows 中文路径由 Python 读取原 XML 字节后交给同一 MuJoCo 编译器，不修改或重新生成结构。
原 M1–M6 入口在中文路径下使用 `python -B scripts/run_portable.py view_trajectory.py --benchmark M1 --condition central_high`；
同样可包装 validate_package.py 和 simulate_controls.py。旧脚本及数据字节均保持不变。

## 保存动画与动力学复现的区别

保存动画只读取历史状态、执行 mj_forward，并显式禁用 mj_step/mj_step1/mj_step2。
真正动力学复现将**重新积分**，只能由接收方以后主动运行；本次交付只检查配方，未运行它。
新结果可能随 MuJoCo/平台/求解数值环境变化，不重写历史验收，也不自动取得新科学验收身份。
以下 --output 必须是资料包之外尚不存在的新目录：

```powershell
./.viewer-env/Scripts/python.exe -B ./scripts/simulate_phs2d.py --s 0.50 --direction positive --output ../new_phs2d_s050_positive_replay
```

脚本从真实初态启动，保持固定 payout、单侧长度限制、原 integrator/solver/timestep、0.5 s 平滑加载，
并在变形后材料点重算世界 x 力到广义力的映射；保留原每 10 ms snapshot 的额外力映射阶段。
没有主动 control_schedule，也不会伪造 actuator。M1–M6 的主动复现继续使用 ../scripts/simulate_controls.py。

## 数据与精度

{chr(10).join(data_table)}

每条从真实 t=0 snapshot 到第 32,000 个积分后状态，共 32,001 行，CSV 行数不含表头。
末引擎时间约为 4.000000000002015 s，保留原浮点时间，不强行改成 4.0。
全部原数据为 float64；CSV 使用 .17g 往返安全表示。每次只处理一条 NPZ、逐行写 CSV，不将所有 CSV 装入内存。

NPZ 的 trajectory 形状 [32001,442]：time_s、force_n、144 qpos、144 qvel、144 qacc、4 腱长、4 原张力；
columns 为原顺序，另存 tip_position_m、tip_rotation、force_point_m 和 reconstructed_contact_count。
第 0 行完全来自原 samples[0]，其后 32,000 行的二进制 float64 数组 SHA 与源 NPZ 完全一致。
qacc 完整保存在 NPZ；CSV 不展开 144 维 qacc，只提供 original_qacc_inf_rad_s2。
CSV 展开所有具名关节 qpos/qvel、Tip 世界位置/3×3 旋转、材料点世界位置、实际外力、腱长、长度超限及原始张力。
全部使用 SI：m、s、N、rad、rad/s、rad/s²，旋转无量纲。

**观测相位不可混淆**：原逐步 qacc、腱长、张力是在 mj_step 后及随后 mj_forward 的记录，
当时广义力仍来自该步开始前的材料点映射；每 10 ms snapshot 在记录后另重算一次力映射。
t=0 使用原 snapshot 的相位。Tip、材料点位姿和 contact_count 是在隔离 MjData 上独立 mj_forward 重建，
其重算反力不会覆盖或冒充原始张力。CSV 的力是刚执行完的步所受世界力；
external_force_schedule.csv 的 application_pre_state_* 才是该步实际施力前的材料点位置，初态区间为 [0,0]。
受力点位置随材料变形移动，力方向始终世界 x；不把力加到固定空间点或 body COM。

逐工况 validation.json 记录源引用、原 NPZ/数组 SHA、行列数和文件 SHA。
根 manifest.json 包含所有交付文件 SHA-256（不含自身，也不是数字签名）。
validate_phs2d.py 流式读取 CSV，对所有共享字段检查 float64 完全相等，并逐帧独立 forward 核验保存位姿；
validate_all.py 同时调用原 validate_package.py 原样验证 M1–M6，逐项检查原不可变文件哈希。

## 原十工况结果

下表只是原末态评价的显示舍入，精确数值与未改写的通过身份见 task.json 和原评价原件。
标准：受力点 ≥10 mm、Tip ≤5 mm、比值 ≤0.30、平面外 ≤2 mm；原稳定性、腱长、张力与接触条件保持不变。

{chr(10).join(result_table)}

## 来源与边界

研究来源：wran021004-gif/softrobot-agent，分支 research/phs2d-inverse-passive-design，提交 `{RESEARCH_SHA}`。
XML SHA-256：`{structure['xml_sha256']}`；源设计 SHA-256 与各内容寻址证据身份见 structure.json、dataset.json。
只提取成功结构、11 条原逐步数据及必要 JSON；没有把完整私有 Store 或原数 GB 研究归档复制进本包。

模型省略轴向伸长、剪切、扭转、真实腱摩擦/弹性与自碰撞；腱路几何检查只覆盖原保存姿态，非连续绳接触求解。
材料黏性未做真实标定。开发性数值见证不证明全局可行性、制造公差鲁棒性、真实材料性能或硬件安全。
不提供电机、驱动器、通信、张力控制器或可直接下发真机的命令。
''')
    old=read(base/'evidence/legacy_hash_snapshot.json')
    # Recover the exact original README from the still-unchanged staging copy on first call.
    original_readme=package/'README.md'
    marker='<!-- PHS2D_ADDITIVE_V2 -->'
    text=original_readme.read_text(encoding='utf8')
    if marker in text:text=text.split('<!-- ORIGINAL_M1_M6_README -->\n',1)[1]
    save(original_readme,f'''{marker}
# 七类 Base-only MuJoCo Benchmark 资料包（增量 v2）

原 M1–M6 的 10 条主动任务轨迹及历史验收完整保留，新增 PHS-2D 的 10 条被动力工况和 1 条无力基准。
新增入口：[PHS-2D 中文说明](PHS2D_passive_head_stabilization/README.md)。
统一校验：`python -B scripts/validate_all.py`；原主动任务校验语义未改动。
PHS 动画：`python -B scripts/view_phs2d.py --s 0.50 --direction positive --loop`。
M1–M6 动画：`python -B scripts/run_portable.py view_trajectory.py --benchmark M1 --condition central_high --loop`。
原主动校验：`python -B scripts/run_portable.py validate_package.py`；
原主动重放：`python -B scripts/run_portable.py simulate_controls.py --benchmark M2 --condition positive --output ../new_M2_replay`。
run_portable.py 仅适配 Windows 中文 XML 文件路径，原模型、主动脚本文件和验收语义不变。
下方历史说明中的直接旧入口仍可在 ASCII 路径使用；中文路径统一使用以上包装入口。
全部命令从资料包根目录执行；环境安装和 Linux/Windows 命令见各说明。

**本次 PHS 增量导出新增物理积分为 0。** 下方原 M1–M6 说明中的 6,700 步属于既有历史导出，未在本次重跑。
PHS 是开发性数值验收通过、尚未正式注册 SELECT；M1–M6 原历史验收身份不变。
`manifest.json.trajectories` 继续只代表原 10 条主动轨迹；PHS 使用版本化 `passive_benchmarks` 字段。
只读动画和完整性校验不执行积分；主动或被动动力学复现均需接收方明确执行各自脚本并指定新的包外目录。

<!-- ORIGINAL_M1_M6_README -->
{text}''')
    write(package/'code_provenance.json',dict(version='base_only_export_increment_v2',
        legacy_export_commit='c8085b8faa4d802d529d4bc8468f7c3c907662c4',
        research_commit=RESEARCH_SHA,code_branch='feat/phs2d-benchmark-package-export',
        legacy_code_provenance_sha256=old['files']['code_provenance.json'],
        script_sha256={p.name:sha(p) for p in sorted((package/'scripts').glob('*.py'))},
        data_in_git=False,physics_steps_during_phs_export=0))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True)
    generate(p.parse_args().package.resolve())


if __name__=='__main__':main()
