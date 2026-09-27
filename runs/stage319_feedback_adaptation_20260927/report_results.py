"""Read sealed public outputs; no numerical solve or backend replay."""
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json
HERE=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    old=read(ROOT/'runs/stage318_parameterized_reach_20260927/B/summary.json')
    new=read(HERE/'B/summary.json');baseline=read(HERE/'baseline.json');candidate=read(HERE/'reintegrate.json')
    store=Store(HERE/'B');run=read(HERE/'B/workflow.json')['run_id']
    refs=next(e['outputs'] for e in store.events(run) if e['kind']=='simulation'
        and e['execution_id']==new['execution_id'] and e['status']=='completed')
    bundle=next(v for r in refs if r['media_type']=='application/json' for v in [store.artifact(r)]
        if isinstance(v,dict) and 'files' in v)
    ref=next(f['reference'] for f in bundle['files'] if f['filename']=='controller_observations.json')
    obs=json.loads(store.artifact(ref,raw=True));motion=store.artifact(new['motion'])
    material=store.artifact(new['numerical_preparation']['source']);u=np.asarray(material['warm_guess']['tensions'])
    old_commands=np.asarray([u[min(k,len(u)-1)] for k in range(len(obs))])
    actual=np.asarray([o['desired_tension_n'] for o in obs])
    feedback=[dict(time_s=o['time_s'],source=o['plan_source'],accepted=o['plan_accepted'],
        applied_tensions_n=o['desired_tension_n'],**(o['feedback'] or {}),recovery=o['feasibility_recovery']) for o in obs]
    changed=[o for o in obs if o.get('feedback') and o['feedback']['first_command_change_from_initialization_n']>1e-8]
    improved=[o for o in changed if o['feedback']['delivered_objective']<o['feedback']['initial_objective']]
    inside=[r for r in motion if r['tip_error_m']<=.01]
    first_inside=inside[0]['time_s'] if inside else None
    quality=dict(command_difference_from_historical_sequence_max_n=float(np.max(abs(actual-old_commands))),
        changed_first_commands=len(changed),changed_with_lower_predicted_objective=len(improved),
        recovery_attempts=sum(o['feasibility_recovery']['attempted'] for o in obs),
        recovery_errors=sum(o['feasibility_recovery'].get('error') is not None for o in obs),
        source_observations=ref,minimum_error_sample=min(motion,key=lambda r:r['tip_error_m']),
        first_inside_original_tolerance_s=first_inside,
        max_error_after_first_entry_m=max((r['tip_error_m'] for r in motion if first_inside is not None and r['time_s']>=first_inside),default=None),
        peak_tip_speed_m_s=max(r['tip_speed_m_s'] for r in motion))
    fields=('complete','official_task_success','terminal_error_m','terminal_tip_speed_m_s','sampled_settling',
        'accepted_plans','updates','converged_updates','initialization_selected','solver_error_count','hold_last_responses',
        'maximum_plan_violation','mean_update_s','mean_preparation_s','mean_numerical_solve_s','mean_validation_s',
        'graph_construction_s','solver_construction_s','deadline_misses','simulation_wall_s','force_bound_violation_n','tension_range_n',
        'optimization_status_counts','raw_termination_counts','solver_failure_flags')
    costs=[]
    for b,a in zip(baseline['rows'],candidate['rows']):
        item=dict(state=b['label'])
        for key,row in (('before',b),('after',a)):
            p=row['plan'];d=p['diagnostics'];physical=row['candidates'].get('delivered',row['candidates']['selected'])
            item[key]=dict(preparation_s=p['warm_start']['preparation_s'],solve_s=d['solve_s'],
                solver_construction_s=d['construction_s'],initial_check_s=d['initial_check_s'],
                validation_s=d['validation_s']+p.get('recovery',{}).get('validation_s',0.),
                recovery_s=p.get('recovery',{}).get('wall_s',0.),delivery_s=p['update_wall_s'],
                objective=p['result']['objective_value'],violation=p['result']['constraint_violation'],
                terminal_error_m=physical['terminal_error_m'],terminal_speed_m_s=physical['terminal_speed_m_s'])
        costs.append(item)
    timing=read(HERE/'B_process_timing.json')
    events=store.events(run)
    stamps=[datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')) for e in events]
    timing['session_created_to_last_public_event_s']=(max(stamps)-min(stamps)).total_seconds()
    timing['public_tool_charged_wall_s']=sum(read(HERE/'B'/(name+'_receipt.json'))['charged']['wall_s']
        for name in ('describe','simulate','evaluate','report'))
    timing['scope']='process_wall_s is fresh run process including preparation hook, simulation, evaluation and report; event interval also covers solve-free prepare session/describe and inter-process time, excludes interpreter startup before session creation'
    result=dict(implementation_commit='74b3c2e',starting_commit='36fbf88',fixed_input_identity=baseline['input_identity'],
        fixed_state_comparison=costs,quality=quality,feedback=feedback,
        historical_B={k:old[k] for k in fields},new_B={k:new[k] for k in fields},
        new_recovery_cost={k:new[k] for k in ('mean_recovery_s','mean_recovery_integration_s','mean_recovery_validation_s')},
        process_timing=timing,one_time_preparation_s=new['numerical_preparation']['wall_s'],
        full_backend_executions_this_round=1,A_confirmation='Not run: opt-in change; fixed v2/default behavior checked by existing regression',
        tests=dict(command='python -m unittest tests.test_gvs_feedback_recovery tests.test_gvs_parameterized_reach -v',passed=4),
        environment=dict(interpreter=sys.executable,python=platform.python_version(),os=platform.platform(),
            processor=platform.processor(),logical_processors=os.cpu_count(),threads=read(HERE/'B/workflow.json')['threads']))
    atomic_json(HERE/'results.json',result)
    lines=['# Stage 3.19：恢复任务相关的可行反馈','',
        f"结论：反复交付历史初始化的机制已得到针对性修复，但固定 B 任务仍未解决。新 B 原任务通过={new['official_task_success']}，sampled settling={new['sampled_settling']['passed']}；终点误差由 {old['terminal_error_m']*1000:.4f} mm 变为 {new['terminal_error_m']*1000:.4f} mm。已有可行反馈和更低末端速度，不等于整体任务改善。",'',
        '起点 `36fbf88`，实现提交 `74b3c2e`。本轮一个代理、一个修复候选、两个冻结状态、一次新的 B 完整公共执行。无付费调用、参数扫描或历史完整轨迹重跑。','',
        '## 诊断与证据强度','',
        '两个状态来自 Stage 3.18 B 的封存 Store：0 s 和 0.28 s（接近目标且速度过高）。当前测量、上一条实际张力和猜测在比较两侧完全相同。B 每次选初值，故可准确重建其输入序列；中间完整状态计划未导出，近目标状态的 Newton 猜测明确标为重复当前测量，再全量积分，不冒充原始保存计划。来源及引用见 `fixed_inputs.json`。','',
        '初始状态目标 65.8734 → 返回迭代 2.12727，残差 3.25046e-4；近目标状态 17.7935 → 0.728686，残差 7.62813e-5。原阈值为 1e-5，因而这些改进候选不可交付。逐迭代轨迹显示每次确有 4 次后续迭代；初值选中不是零优化。10% 只影响提前停止，候选保留没有这个门槛。','',
        '证据直接支持 B 类原因：在既定墙钟预算内，优化已改善目标，但动力学可行性尚未恢复。未发现有用可行迭代被选择器错误丢弃。不能据两个重建样本断言所有历史更新都有唯一相同原因，也不能归因于目标不可达或纯模型失配。无需额外 60 s 求解。','',
        '两个基线求解各约 16.1 s，其中约 15.4 s 是约束雅可比；详细函数次数和墙钟计时已保存。没有进行新的导数实现或速度位置消元实验。','',
        '## 修复','',
        '`recipe.recover_returned_tensions=true` 明确开启一次可行性恢复，默认 false，固定 v2 资产不变。对目标更低的返回迭代，保留其张力，从当前测量重新积分相同隐式动力学；使用原 NLP 独立检查初始状态、动力学和张力上下界，仅在残差 <=1e-5 且目标严格改善时选取。初值仍可被保留。恢复错误有记录，普通不可用求解仍执行原有有界 hold-last。','',
        '实际状态反馈、完整 warm 状态再生成、执行局部工作空间与来源追踪保留。未修改目标函数、任务、材料、阻尼、容差或求解预算。恢复后的计划明确是非收敛可行计划，原始 IPOPT 终止与选择仍保留。','',
        '## 固定状态：相同输入的质量与成本','',
        '| 状态 | 预测终点误差前→后 (mm) | 预测终点速度前→后 (m/s) | 目标前→后 | 完整交付前→后 (s) | 恢复成本 (s) | 恢复后残差 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for c in costs:
        b,a=c['before'],c['after']
        lines.append(f"| {c['state']} | {b['terminal_error_m']*1000:.4f} → {a['terminal_error_m']*1000:.4f} | {b['terminal_speed_m_s']:.6f} → {a['terminal_speed_m_s']:.6f} | {b['objective']:.6g} → {a['objective']:.6g} | {b['delivery_s']:.3f} → {a['delivery_s']:.3f} | {a['recovery_s']:.3f} | {a['violation']:.3g} |")
    lines+=['',
        '初始状态首条张力最大改变 1.00508 N；近目标高速状态改变 0.483217 N。初始预测为加速接近目标，其终点速度上升；近目标样本误差和速度同时下降，但预测速度仍高于 settling 限值。没有将“命令改变”直接当作质量改善。两侧独立单次计时；近目标候选因墙钟预算在第 3 次后续迭代停止，基线为第 4 次，不能视为固定迭代数比较。','',
        f"图构造基线/候选 {baseline['graph_s']:.3f}/{candidate['graph_s']:.3f} s；首次求解器构造包含在完整交付内。逐阶段成本见 `results.json`。这是质量/成本权衡，不是速度提升。","",'## 新 B 公共执行','',
        '通过 `examples/gvs_parameterized_reach.py prepare/run` 在新进程和新目录执行 controller v3。冻结目标 [0.29,0.05,0.19] m，直线初态，0.35 s，控制周期 0.01 s、物理步长 0.0005 s、12 cells/segment、10 区间预测。原 reach 阈值 10 mm；末 0.05 s sampled settling 10 mm / 0.02 m/s，均保持不变。','',
        '| 指标 | 历史 Stage 3.18 B | 新 B |','|---|---:|---:|']
    table=[('完整执行','complete'),('原任务通过','official_task_success'),('终点误差 (m)','terminal_error_m'),
        ('终点速度 (m/s)','terminal_tip_speed_m_s'),('接受计划','accepted_plans'),('选初始化','initialization_selected'),
        ('优化收敛','converged_updates'),('求解异常','solver_error_count'),('hold-last','hold_last_responses'),
        ('最大计划残差','maximum_plan_violation'),('平均完整交付 (s)','mean_update_s'),('平均 warm 再生成 (s)','mean_preparation_s'),
        ('平均数值优化 (s)','mean_numerical_solve_s'),('平均独立验证 (s)','mean_validation_s'),('图构造 (s)','graph_construction_s'),
        ('求解器构造总计 (s)','solver_construction_s'),('simulation 工具墙钟 (s)','simulation_wall_s'),('超 10 ms deadline','deadline_misses')]
    for label,k in table:
        fmt=lambda v:f'{v:.7g}' if isinstance(v,float) else str(v)
        lines.append(f'| {label} | {fmt(old[k])} | {fmt(new[k])} |')
    for label,k in [('sampled settling','passed'),('末窗最大误差 (m)','max_error_m'),('末窗最大速度 (m/s)','max_speed_m_s')]:
        lines.append(f"| {label} | {old['sampled_settling'][k]} | {new['sampled_settling'][k]} |")
    lines+=['',f"接受的非初始化计划 {new['accepted_noninitialization_plans']}；重积分后选中 {new['recovered_plans']}。{len(changed)} 次首条命令相对本次 warm 初始化发生改变，其中 {len(improved)} 次同时降低预测目标。相对历史移位输入序列的最大差异 {quality['command_difference_from_historical_sequence_max_n']:.6g} N。逐更新的预测误差/速度、目标、实际张力及恢复来源见 `results.json`，原始观察以 EvidenceRef 指向 `B/platform.sqlite`。",'',
        f"恢复尝试 {quality['recovery_attempts']}，恢复错误 {quality['recovery_errors']}。实际张力范围 {new['tension_range_n']} N，界限违反 {new['force_bound_violation_n']} N。",'',
        f"数学交付状态 {new['optimization_status_counts']}；IPOPT 原始终止 {new['raw_termination_counts']}。恢复不是收敛事件，35 个更新均非优化收敛。",'',
        f"首次采样进入原容差时间 {first_inside} s，进入后最大误差 {quality['max_error_after_first_entry_m']} m，最小误差 {quality['minimum_error_sample']['tip_error_m']} m（{quality['minimum_error_sample']['time_s']} s），峰值末端速度 {quality['peak_tip_speed_m_s']} m/s。暂时进入容差不等于终点评价或 settling 通过。",'',
        f"一次性数值导入准备 {new['numerical_preparation']['wall_s']:.6f} s（无目标感知预求解）；平均恢复 {new['mean_recovery_s']:.6f} s，其中积分 {new['mean_recovery_integration_s']:.6f} s、验证 {new['mean_recovery_validation_s']:.6f} s。完整 run 进程含启动、仿真、独立评价与报告墙钟 {timing['process_wall_s']:.3f} s。",'',
        f"从会话创建到最终公共事件共 {timing['session_created_to_last_public_event_s']:.3f} s，包含 solve-free prepare/describe 和进程间间隔；不含会话创建前的解释器启动。四个公共工具计费墙钟合计 {timing['public_tool_charged_wall_s']:.3f} s。上述区间分别报告，不能再次相加。",'',
        '完整交付已包含首次求解器构造、warm 再生成、初值检查、数值优化、恢复、验证和命令处理；不要重复加总构造或恢复验证。图构造发生于更新前。新 mean_validation 包含恢复验证。诊断输出仅在固定状态启用，全程运行未启用逐迭代诊断。', '',
        f"本次全程平均交付相对历史 B 变化 {(new['mean_update_s']/old['mean_update_s']-1)*100:.2f}%；恢复增加计算，后续求解可更早达到相对改善停止条件。单次、墙钟停止敏感的两个闭环不能建立稳健速度提升；固定状态配对样本反而增加完整交付成本。",'',
        '未新增 A 全程执行：改动显式启用，固定 v2/default 配置保留，并通过相关既有回归。四项检查通过，未运行全套测试。','',
        '## 局限','',
        '只检验两个重建局部状态和一次固定 B 闭环。新的输入使后端更早进入容差并降低末段速度，但随后超调且终点误差更大。局部预测改进已证实，充分的闭环任务表现没有证实。预测/执行偏差、当前有限时域和位置/制动权重的相对作用仍未唯一分离；没有证据支持宣称目标不可达。任务成功、采样 settling、数值可行、优化收敛及实时性分别报告；不证明连续 settling、邻域鲁棒性或全局稳定。当前实测成本远高于 10 ms，十秒交付目标也未实现。保留本次失败，不追加 B 重试或未经后端验证的第二修复。','',
        '## 复现','', '```powershell',"Set-Location 'D:\\softrobot-agent'", "$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS='1'", "$env:OMP_NUM_THREADS='1'", "$env:MKL_NUM_THREADS='1'",
        '# 只读取本轮封存结果，无仿真：','& $py runs/stage319_feedback_adaptation_20260927/report_results.py',
        '# 聚焦检查：','& $py -m unittest tests.test_gvs_feedback_recovery tests.test_gvs_parameterized_reach -v',
        '# 数值复现：先复制证据目录，避免覆盖本轮测量；无需 freeze 历史来源',
        'Copy-Item runs/stage319_feedback_adaptation_20260927 runs/repro319 -Recurse',
        '& $py runs/repro319/diagnose.py baseline','& $py runs/repro319/diagnose.py reintegrate',
        '# 新完整执行（消耗新预算），使用新输出目录：',
        '& $py -c "from pathlib import Path; from uuid import uuid4; from extensions.tendon_family.gvs_profile import reach_input; from tools.state_io import atomic_json; atomic_json(Path(\'runs/repro319_input.json\'), reach_input(\'repro319-\'+uuid4().hex[:12], target_m=[.29,.05,.19], recipe=dict(recover_returned_tensions=True)))"',
        '& $py examples/gvs_parameterized_reach.py prepare --input runs/repro319_input.json --output runs/repro319_backend',
        '& $py examples/gvs_parameterized_reach.py run --output runs/repro319_backend','```','']
    (HERE/'implementation_report.md').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps(dict(quality=quality,new={k:new[k] for k in fields},process=timing),ensure_ascii=False))

if __name__=='__main__':main()
