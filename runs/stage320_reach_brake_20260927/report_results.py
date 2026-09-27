"""Read-only consolidation of this round's sealed public evidence; no new solves."""
import json
import os
import platform
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json

HERE=Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def public_evidence(label):
    folder=HERE/label
    if not (folder/'summary.json').exists():return None
    summary=read(folder/'summary.json');store=Store(folder)
    run=read(folder/'workflow.json')['run_id']
    refs=next(e['outputs'] for e in store.events(run) if e['kind']=='simulation'
        and e['execution_id']==summary['execution_id'] and e['status']=='completed')
    bundle=next(v for r in refs if r['media_type']=='application/json' for v in [store.artifact(r)]
        if isinstance(v,dict) and 'files' in v)
    ref=next(f['reference'] for f in bundle['files'] if f['filename']=='controller_observations.json')
    observations=json.loads(store.artifact(ref,raw=True));motion=store.artifact(summary['motion'])
    inside=[r for r in motion if r['tip_error_m']<=summary['task']['evaluator']['parameters']['data']['tolerance_m']]
    quality=dict(first_entry_s=inside[0]['time_s'] if inside else None,
        final_window=[r for r in motion if r['time_s']>=summary['task']['timing']['duration_s']-summary['sampled_settling']['window_s']-1e-9],
        minimum_error_sample=min(motion,key=lambda r:r['tip_error_m']),
        peak_tip_speed_m_s=max(r['tip_speed_m_s'] for r in motion),
        recovery_attempts=sum(o['feasibility_recovery']['attempted'] for o in observations),
        recovery_errors=sum(o['feasibility_recovery'].get('error') is not None for o in observations),
        applied_hold_activations=[dict(time_s=o['time_s'],**(o.get('prediction_timing') or {})) for o in observations],
        first_tension_changes_n=[o['feedback']['first_command_change_from_initialization_n'] for o in observations],
        predicted_terminal=[dict(time_s=o['time_s'],**o['feedback']['delivered_terminal']) for o in observations])
    return dict(summary=summary,quality=quality,source_observations=ref,
        process_timing=read(HERE/(label+'_process_timing.json')),
        actual_budget=store.remaining(run)['used'])


def main():
    local=[]
    for name in ('baseline','terminal','holding'):
        result=read(HERE/(name+'.json'))
        for row in result['rows']:
            plan=row['plan'];d=plan['diagnostics'];q=row['quality']
            local.append(dict(variant=name,label=row['label'],time_s=row['time_s'],
                reused_from=row.get('reused_from'),accepted=plan['accepted'],
                terminal_error_m=q['terminal_error_m'],terminal_speed_m_s=q['terminal_speed_m_s'],
                minimum_error_m=q['minimum_error_m'],peak_speed_m_s=q['peak_speed_m_s'],
                holding_window_max_speed_m_s=max((v for k,v in enumerate(q['tip_speed_m_s'])
                    if .30-1e-9<=row['time_s']+k*.01<=.35+1e-9),default=None),
                violation=plan['result']['constraint_violation'],graph_s=plan['graph_s'],
                solver_construction_s=d['construction_s'],warm_s=plan['warm_start']['preparation_s'],
                solve_s=d['solve_s'],recovery_s=plan['recovery']['wall_s'],
                validation_s=d['validation_s']+plan['recovery'].get('validation_s',0.),
                delivery_s=plan['update_wall_s']))
    B=public_evidence('B');A=public_evidence('A')
    historical=read(ROOT/'runs/stage319_feedback_adaptation_20260927/B/summary.json')
    bpass=bool(B and B['summary']['valid_complete_execution'] and B['summary']['official_task_success']
        and B['summary']['sampled_settling']['passed'])
    apass=bool(A and A['summary']['valid_complete_execution'] and A['summary']['official_task_success'])
    result=dict(starting_commit='d02e4e5',implementation_commit='fee35a6',
        environment=dict(interpreter=sys.executable,python=platform.python_version(),
            os=platform.platform(),processor=platform.processor(),logical_processors=os.cpu_count(),
            threads=read(HERE/'B/workflow.json')['threads']),
        candidate=read(HERE/'candidate.json'),prediction_checks=read(HERE/'prediction_checks.json'),
        local_comparison=local,B=B,A=A,control_gates=dict(B_reach_and_settling=bpass,A_reach_preserved=apass if A else None),
        historical_B={k:historical[k] for k in ('official_task_success','terminal_error_m','terminal_tip_speed_m_s',
            'sampled_settling','mean_update_s','simulation_wall_s')},
        full_backend_executions_this_round=int(B is not None)+int(A is not None),
        conditional_LLM=dict(eligible=bpass and apass,executed=False,
            reason='Control acceptance gates not both passed' if not (bpass and apass) else 'Separate conditional audit required'),
        limitations=['One robot, fixed physical scene, structural GVS predictor and 12-cell MuJoCo ideal-tension execution.',
            'Local reconstructed predictions are not original saved plans, and are not 100 ms open-loop/closed-loop transfer comparisons.',
            'Sampled settling is distinct from continuous settling, reach, optimization convergence and computational real-time operation.',
            'No arbitrary-target, cross-robot, contact, hardware or robustness generalization established.'])
    atomic_json(HERE/'results.json',result)
    lines=['# Stage 3.20：空间末端制动与任务保持窗口','',
        f"结论：新 B 原 reach={B['summary']['official_task_success'] if B else None}，sampled settling={B['summary']['sampled_settling']['passed'] if B else None}。终点到达改善，但主目标要求整个最终窗口满足速度限制；未通过该门时停止 A/LLM 条件验收，不追加全程重试。",'',
        '起点 `d02e4e5`，实现提交 `fee35a6`。单代理；三个已封存状态；两个候选；未修改历史证据、物理参数、任务时长或验收阈值。','',
        '## 原因与证据强度','',
        '旧目标惩罚曲率速度，未直接惩罚世界坐标末端速度；滚动终点没有绝对任务时间语义。终端速度代价的配对结果支持其确实影响制动，但不能唯一归因于权重。',
        '0.28 s 的仅终端候选在 0.38 s 已减速至 0.01495 m/s，在实际 0.30–0.35 s 窗口仍为 0.088–0.112 m/s，直接支持增加任务窗口代价。',
        '同一时刻、同一实际张力的局部检查如下。重建世界速度来自 MuJoCo site Jacobian；没有重跑历史后端轨迹。0 s 的后端导出只有 post-step 样本，因此初始关节状态按冻结直线静止 initializer 重建，并使用实际初始 tip observation。','',
        '| 时间 s | 重建位置差 mm | 重建速度差 m/s | 10 ms 预测位置差 mm | 10 ms 预测速度差 m/s |',
        '|---:|---:|---:|---:|---:|']
    for r in result['prediction_checks']['rows']:
        a=r['reconstruction'];b=r['one_period_prediction']
        lines.append(f"| {r['time_s']:.2f} | {1000*a['position_difference_m']:.4f} | {a['velocity_difference_m_s']:.5f} | {1000*b['position_difference_m']:.4f} | {b['velocity_difference_m_s']:.5f} |")
    lines+=['','预测对齐同一控制周期，未将后来改变命令的闭环轨迹与 100 ms 开环预测比较。误差包含有限空间表示、动力学和积分差异；没有证据将其唯一分解。','',
        '## 实现与局部选择','',
        '新增显式 position_error_scale_m、tip_speed_scale_m_s、terminal_tip_speed_weight、holding_tip_speed_weight。默认空间速度权重为零，固定 v2 资产不变。末端速度为世界 tip Jacobian × qdot。',
        '冻结候选：位置尺度 0.01 m，速度尺度 0.02 m/s，终端速度权重 1，保持阶段速度权重 100/s。其余 Stage 3.19 recipe 不变。保持起点由 task duration 减 settling.window_s 得到；当前执行时间来自 command(t)，不是更新墙钟。节点调度量固定等式边界，复用图与求解器。',
        '原动态约束、张力边界、1e-5 独立可行性阈值、完整 warm 再生成、可选恢复均保留。预测超出任务终点的节点继续保持；后端仍只执行原 0.35 s。','',
        '| 候选 | 状态 s | 预测终点误差 mm | 预测终点速度 m/s | 实际任务窗口预测最大速度 m/s | 交付 s | 最大残差 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in local:
        if r['reused_from']:continue
        speed=r['holding_window_max_speed_m_s']
        lines.append(f"| {r['variant']} | {r['time_s']:.2f} | {r['terminal_error_m']*1000:.4f} | {r['terminal_speed_m_s']:.6f} | {speed if speed is not None else '不覆盖'} | {r['delivery_s']:.3f} | {r['violation']:.3g} |")
    lines+=['','第二候选前两个窗口所有 holding 系数为零，直接复用第一候选结果。没有重复求解或比较跨代价定义的原始目标数值。后期状态已在容差外，第二候选制动后仍约 12.25 mm；这不是局部完整通过。早期预测仍能接近目标，完整 B 是检验预防超调的实际闭环实验。','',
        '## 新公共执行','',
        'B/A 均使用原任务 0.35 s、10 ms 控制、0.5 ms 物理步长、直线初态、12 cells/segment、原 10 mm reach 与最后 50 ms 的 10 mm / 0.02 m/s sampled settling。','',
        '| 指标 | B | A |','|---|---:|---:|']
    for title,key in [('完整有效执行','valid_complete_execution'),('原 reach','official_task_success'),('终点误差 m','terminal_error_m'),
        ('终点速度 m/s','terminal_tip_speed_m_s'),('接受计划','accepted_plans'),('初始化选中','initialization_selected'),
        ('恢复选中','recovered_plans'),('优化收敛','converged_updates'),('求解异常','solver_error_count'),
        ('hold-last','hold_last_responses'),('张力违反 N','force_bound_violation_n'),('最大计划残差','maximum_plan_violation'),
        ('超时更新','deadline_misses')]:
        lines.append('| '+title+' | '+' | '.join(str(v['summary'][key]) if v else '未运行（条件门）' for v in (B,A))+' |')
    for title,key in [('sampled settling','passed'),('窗口最大误差 m','max_error_m'),('窗口最大速度 m/s','max_speed_m_s')]:
        lines.append('| '+title+' | '+' | '.join(str(v['summary']['sampled_settling'][key]) if v else '未运行' for v in (B,A))+' |')
    if B:
        lines+=['','B 最终窗口逐采样结果：','',
            '| 时间 s | 位置误差 mm | 实际 tip speed m/s |','|---:|---:|---:|']
        for r in B['quality']['final_window']:
            lines.append(f"| {r['time_s']:.2f} | {r['tip_error_m']*1000:.4f} | {r['tip_speed_m_s']:.6f} |")
        lines+=['','末端单个样本速度通过不能覆盖此前超限。新制动配置改善了实际 reach 与末窗速度，但没有达到整个窗口的制动要求；这是任务性能不足，不是执行中断或计划可行性失败。局部预测误差和有限迭代质量仍是具体局限，不能据本次结果唯一归因或声称全局原因已解决。']
    lines+=['',f"历史 Stage 3.19 B：reach=False、settling=False；终点误差 {historical['terminal_error_m']*1000:.4f} mm，终点速度 {historical['terminal_tip_speed_m_s']:.6f} m/s，末窗最大误差 {historical['sampled_settling']['max_error_m']*1000:.4f} mm、最大速度 {historical['sampled_settling']['max_speed_m_s']:.6f} m/s。该历史结果直接复用，未重跑。"]
    lines+=['','## 完整计算成本','',
        '| 计时 s | B | A |','|---|---:|---:|']
    for title,key in [('图构建','graph_construction_s'),('求解器构建合计','solver_construction_s'),
        ('平均 warm 再生成','mean_preparation_s'),('平均数值求解','mean_numerical_solve_s'),
        ('平均恢复（含其验证）','mean_recovery_s'),('平均独立验证（含恢复验证）','mean_validation_s'),
        ('平均完整更新','mean_update_s'),('simulation 工具墙钟','simulation_wall_s')]:
        lines.append('| '+title+' | '+' | '.join(f"{v['summary'][key]:.6f}" if v else '未运行' for v in (B,A))+' |')
    for label,v in (('B',B),('A',A)):
        if v:
            lines += ['',f"{label} 一次性数值准备 {v['summary']['numerical_preparation']['wall_s']:.6f} s；完整进程 {v['process_timing']['process_wall_s']:.3f} s。张力范围 {v['summary']['tension_range_n']} N；峰值实际末端速度 {v['quality']['peak_tip_speed_m_s']:.6f} m/s；首次采样进入容差 {v['quality']['first_entry_s']} s。"]
    lines+=['','完整更新已包含 warm、求解器构建、求解、恢复和独立验证。恢复验证同时包含在两个分项中，不能重复加总。图构建与导入准备是一次性成本；进程总时间包含 simulation、评价和报告。局部计时见 results.json，计时受墙钟停止策略影响，不作稳健速度提升声明。','',
        '## 条件验收与局限','',
        f"B reach+settling 门：{bpass}；A reach 保留：{apass if A else '未运行'}。有条件 LLM 验收未运行；付费调用 0。未通过前提时不消耗第三次执行、不追加 B 重试。",
        '只验证本轮冻结配置、同一机器人和理想张力场景。接口可参数化不等于性能泛化；不证明任意目标、跨机器人、接触或硬件表现。可行、收敛、reach、sampled settling、计算实时性分别报告。','',
        '## 复现','',
        '```powershell',"Set-Location 'D:\\softrobot-agent'","$py = 'C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe'",
        "$env:OPENBLAS_NUM_THREADS='1'","$env:OMP_NUM_THREADS='1'","$env:MKL_NUM_THREADS='1'",
        '& $py runs/stage320_reach_brake_20260927/report_results.py',
        '& $py -m unittest tests.test_gvs_braking tests.test_gvs_feedback_recovery tests.test_gvs_parameterized_reach -v',
        '# 局部数值复现：先复制，保留本轮冻结证据',
        'Copy-Item runs/stage320_reach_brake_20260927 runs/repro320 -Recurse',
        '& $py runs/repro320/diagnose.py baseline','& $py runs/repro320/diagnose.py terminal','& $py runs/repro320/diagnose.py holding',
        '# 新完整 B 会消耗新的后端预算；本轮已执行，不自动重跑',
        '& $py examples/gvs_parameterized_reach.py run --input runs/stage320_reach_brake_20260927/B_input.json --output runs/repro320_B',
        '```','',
        '封存执行/评价/报告身份、预算、观察引用见 B/summary.json、B/platform.sqlite 和 results.json。六项聚焦检查通过；未跑全套。']
    (HERE/'implementation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(dict(gates=result['control_gates'],B=None if B is None else {
        k:B['summary'][k] for k in ('official_task_success','terminal_error_m','sampled_settling','mean_update_s')}),ensure_ascii=False))


if __name__=='__main__':main()
