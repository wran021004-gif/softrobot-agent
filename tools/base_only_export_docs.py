"""Chinese portable package documentation, rendered from exact saved metadata."""
import json


LIMITATIONS=('这是每段 12-cell、每 cell 两个弯曲铰链的离散化理想张力驱动模型，不是制造 CAD。'
    '六根腱是直线分段、无摩擦的理想路径；材料、惯性、重力及接触参数以 XML 和 structure.json 为准。'
    '未验证真实摩擦、制造公差、驱动动态、硬件安全或跨机器鲁棒性。控制 CSV 的单位为 N，'
    '不是已验证可直接下发真机的电机命令。本包不提供电控、通信、驱动器或电机转角映射。')


def pretty(value):return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)


def task_zh(key,condition,task):
    d=task['definition'];goal=d['goal']['data'];a=task['historical_acceptance']
    names={'M1':'共享结构多目标定位保持','M2':'多方向 COM 扰动下定位保持','M3':'保持任务 development draft',
        'M4':'有时限折线路径跟踪','M5':'位置与有向工具轴定位','M6':'20 g 刚性传感工具的非接触定向扫描'}
    components='\n'.join(f"| {k} | {v['value']} | {v['limit']} | {v['unit']} | {v['passed']} |"
        for k,v in a['components'].items())
    return f'''# {key} / {condition}：{names[key]}

任务原名：{d['name']}。目的：在原时限与载荷下满足原 registered evaluator 和额外协议约束。
{'本项属于 development draft，尚不是已批准的正式 Benchmark。' if key=='M3' else '本项沿用原 development 任务与历史 accepted 见证。'}

所有目标位置与有向轴均为 world 坐标。Base 的 world 位姿为：
```json
{pretty(d['environment']['data']['mount'])}
```
Base 局部 +X 沿初始机器人纵向，Y/Z 为横截面方向；实际旋转由上述四元数确定。
初始状态是原具名关节 qpos/qvel，完整值在 task.json 的 definition.initializer；
replay_spec.json 给出 CSV joint_map 顺序的原始初态。未指定关节按原 zero 规则处理。

实际目标、轨迹顶点和方向（位置 m，时间 s，角度 rad，方向向量无量纲）：
```json
{pretty(goal)}
```
原时限和采样：
```json
{pretty(d['timing'])}
```
原 evaluator 使用的完整 post-step 采样时刻在 task.json.evaluator_sample_times_s；
任务采样窗口为 {d['sampling']['window_s']} s。保持窗口为 {task['holding_window_s']}。
reference.csv 是逐物理步的可视化参考，其标志列区分 evaluator 输入网格、任务窗口和保持窗口；
它不是规划得到的物理轨迹。原 evaluator 的 geometry_step 等空间网格参数也完整保留。

载荷组件见 ../structure.json 的 design.components；外力定义为：
```json
{pretty(d['environment']['data'].get('external_forces',[]))}
```
M2 外力是 world 系、作用于具名刚体 COM 的力；每个积分步前刷新，
窗口 [start_s,end_s)，以整数 tick 比较。无额外 COM 力矩，不施加于 tip_site。
M6 使用 XML 中真实刚性工具的完整质量、COM 和惯量，不用外力替代。

注册 evaluator：{d['evaluator']['extension_id']} / {d['evaluator']['version']}。
任务身份：`{task['task_identity']}`；任务 ID：`{d['task_id']}` / {d['task_version']}。
协议：`{a['protocol_id']}`。历史结果：`{a['status']}`，accepted={a['accepted']}。
失败包括任一冻结约束不满足、数值失败或执行/采样不完整；成功须全部原验收组件通过。
没有未声明的速度或完整姿态约束；有向工具轴任务不约束绕轴 roll。

| 验收组件 | 原值 | 原上限/要求 | 单位 | 通过 |
|---|---|---|---|---|
{components}

精确裕量（上限减去数值，非布尔值）与原始浮点数据见 task.json.acceptance_margins。
历史 accepted 不会因导出而改写；validation.json 单独记录导出数值一致性。
尤其 M2 positive 的速度裕量很小，应读取 JSON 原始双精度值，不按显示舍入重新判定。

{LIMITATIONS}
原科学验收是采样网格结论，不是连续时间安全、真机或新环境通过的证明。
'''


def structure_md(key,structure):
    segments=[c for c in structure['design']['components'] if c['kind']=='flexible_segment']
    lines='\n'.join(f"- {c['id']}：长度 {c['length_m']} m；Young 模量 {c['physics'].get('young_pa')} Pa；"
        f"{structure['discretization']['cells'][c['id']]} cells；截面站点 s={[s['s'] for s in c['sections']]}。" for c in segments)
    return f'''# {key} 结构信息

{lines}

structure.json.design 保留原候选的段、材料、截面种类/尺寸/方向/站点、连接件、导向孔、腱路和末端定义。
站点 s 为所属柔性段归一化轴向位置；position_m 为 attachment 所在坐标系的局部偏移。
resolved_tendons 明确每个离散路径点所属 MuJoCo 刚体、局部坐标、原 attachment 和角色 start/guide/anchor。
六根腱都从 fixed_base 的安装点出发。resolved_physics 保存每个 cell 的几何、质心、质量、惯量、刚度和阻尼。
质量 kg，长度 m，角度 rad，Young 模量 Pa，惯量 kg·m²，关节刚度 N·m/rad，阻尼 N·m·s/rad。
Base 位姿是 world 中的 position_m 与 wxyz 四元数；tip_site 局部位置以实际所属刚体为准。
工具有向轴以 tip_site 局部坐标定义；无方向要求的任务也输出局部 +X 的世界方向用于显示。
joint_map.json 按原 physics.dofs 顺序映射全部 qpos/qvel 地址和 CSV 列；actuator_order 是 XML 的理想张力通道。
design 中历史 displacement actuator 元数据不用于本次成功回放，也不是硬件驱动映射。
设计、配置、离散化及 XML 身份均列在结构与各条件 provenance.json 中。

{LIMITATIONS}
'''


def commands(key,conditions,root_prefix='.'):
    return '\n\n'.join(f'''{condition}：
```powershell
python {root_prefix}/scripts/view_trajectory.py --benchmark {key} --condition {condition} --speed 1 --loop
python {root_prefix}/scripts/simulate_controls.py --benchmark {key} --condition {condition} --output ./replay_{key}_{condition}
python {root_prefix}/scripts/validate_package.py
```''' for condition in conditions)


def benchmark_readme(key,conditions):
    return f'''# {key} 本地实验资料

从导出根目录运行下列命令；路径由脚本所在目录解析，不依赖原 Store。
在本任务目录运行时，将 scripts 前缀改为 ../scripts，或使用下面第二组完整命令。
{commands(key,conditions)}

从当前 {key} 目录运行：
{commands(key,conditions,'..')}

robot.xml 是代表条件原 accepted 回放的逐字节副本；各条件 XML 的原 SHA 与实际物理模型一致性见 provenance.json。
M1 的 XML 中静态 task_target 标记属于代表条件；查看器隐藏该标记，并按所选条件的 reference.csv 绘制参考。
structure.json / structure.md 给出结构与单位；joint_map.json 给出列与关节地址。
每个条件目录有 task_zh.md、task.json、初态/重放配置、原控制、逐步状态、参考、原验收证据和独立 validation.json。
{'M3 是 development draft，不是已批准的正式 Benchmark。' if key=='M3' else ''}

{LIMITATIONS}
'''


def root_readme(environment,entries):
    rows='\n'.join(f"| {e['benchmark']} | {e['condition']} | {e['rows']} | {e['timestep_s']} | {e['duration_s']} |"
        for e in entries)
    return f'''# Base-only accepted MuJoCo 本地资料包

六项历史独立 accepted 任务，十条真实物理步轨迹，六份原 XML。M3 仍是 development draft。
原研究提交：314f75a4971e0a9e4521fe79ddf744ff71de61e2，分支 research/base-only-benchmark-feasibility。
来源为 base-only-owner-20261028-r2 各任务原 SELECT、内容寻址 artifact、review_manifest/index 和原始 receipt。
provenance.json 保存精确绑定；本包不需要原研究 Store。完整资料仅用于本地私有实验。

目录：M1–M6 各有 robot.xml、structure.json/md、joint_map.json 和 README；
下属 condition 目录提供 task.json、task_zh.md、control_schedule.csv、trajectory_timestep.csv、reference.csv、
replay_spec.json、原控制周期样本、原 acceptance/evaluation/profile/receipt 及 validation.json。
evidence/artifacts 保留对应内容寻址原始 JSON；其身份可用 SHA 校验。
scripts 是独立查看、显式动力学重放、零积分校验入口。manifest.json 对所有交付文件记录 SHA-256；它自身不是数字签名。

验证环境：Python {environment['python']}，MuJoCo {environment['mujoco']}，NumPy {environment['numpy']}；Windows 已验证。
原研究 .f3-prestudy-env 可直接使用。独立查看/重放只需要 MuJoCo 和 NumPy，不需要整个 Softrobot-Agent。

Windows PowerShell（从导出根目录执行）：
```powershell
py -3.11 -m venv .viewer-env
. ./.viewer-env/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python ./scripts/view_trajectory.py --benchmark M1 --condition central_high --speed 1 --loop
python ./scripts/validate_package.py
python ./scripts/simulate_controls.py --benchmark M2 --condition positive --output ../replay_M2_positive
```
若 PowerShell 禁止激活，可直接使用 ./.viewer-env/Scripts/python.exe 运行同样参数。
校验器仅核验交付清单内文件，允许额外虚拟环境目录 .viewer-env。
显式 simulate_controls 命令会新建输出目录并重新积分；导出期间未为验证而额外执行这些积分。

Linux（未验证）：
```bash
python3.11 -m venv .viewer-env
source .viewer-env/bin/activate
python -m pip install -r requirements.txt
python scripts/view_trajectory.py --benchmark M6 --condition default --loop
python scripts/validate_package.py
```
MuJoCo Python viewer 需要可用桌面/OpenGL。黑屏时检查显卡驱动、远程桌面和显示权限；
无显示设备时用 --check-states 做零积分运动学检查。--render 输出 PNG 仍需 OpenGL；
Linux 无头环境可在支持时选 MUJOCO_GL=egl 或 osmesa，二者未在本次 Windows 导出验证。
查看器空格暂停/继续，R 重播，L 切换循环，--speed 调整速度；绿色为实际末端轨迹，橙色为任务参考，蓝箭头为工具轴。
查看器只设置保存的 qpos/qvel 并计算运动学，不调用 mj_step，也不在时间点之间补帧。

| 任务 | 条件 | 逐步 CSV 数据行（不含表头） | timestep s | 时长 s |
|---|---|---|---|---|
{rows}

trajectory_timestep.csv 包含 t=0 与全部 post-step 状态。step_index 为整数物理步，time_s 为引擎真实时间。
qpos_rad__/qvel_rad_s__ 后缀为具名 hinge joint，映射见 joint_map.json；位置、速度和 rotation r00–r22 均为 world。
tool_axis_world 为 tip_site 旋转矩阵乘局部指定轴；无方向约束时局部 +X 只供显示。
control_interval_index 在初态为 -1，其后指刚执行完的区间；requested/actual_tension_n__ 单位 N，正值拉力。
actual 张力来自隔离副本 forward 后的 -actuator_force；这些通道是一腱一 actuator、gear=1 的理想张力。
external_force_n_ 及具名 body 列为刚执行的积分步所承受的 world COM 力（不是下一步的力）；t=0 为初始 force buffer。
integration_cache_contact_count 保存原积分返回时缓存，用于对齐原 M6 检查；post_state_contact_count 是新 qpos 上重算的接触数。
所有导出位姿、速度、方向、实际张力在隔离 MjData 副本上 forward，绝不影响原回放的下一步 warmstart。
control_schedule.csv 每行一个 ZOH 区间，start/end 单位 s；reference.csv 为可视化参考，标志列注明原验收网格。
原 evaluator 只验收冻结的控制周期网格与窗口，逐步 CSV 不建立新的连续时间验收标准。

validation.json 将历史 accepted 与新导出一致性分开，保留未舍入的最大差值、成本、环境和裕量。
允许数值比较的固定诊断容差为 1e-9，不修改原任务阈值；任何不一致均标 reproduction_unverified。
M2 positive 的速度裕量极小，历史 accepted 始终沿用原记录，不按舍入后的值重判。
本次仅执行十条确定性导出重放，共 6,700 次实际 mj_step；没有优化、搜索、NMPC 或 RL。

{LIMITATIONS}
'''
