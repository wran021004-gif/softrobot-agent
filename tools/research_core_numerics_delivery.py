"""Deliver numerical diagnosis from existing evidence; never dispatch an experiment."""
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import tarfile
import time
import numpy as np
from tools import research_core as core
from tools.research_core_numerics import archived, compact_numerics
from tools.platform_host import Host
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.gvs_codesign import classify_replay


def common_nodes(trajectory):
    times=np.asarray(trajectory['times_s']);indices=[]
    for t in np.arange(36)*.01:
        found=np.flatnonzero(abs(times-t)<1e-10)
        if len(found)!=1:raise ValueError('COMPLETE_UNIQUE_ORIGINAL_NODE_GRID_REQUIRED')
        indices.append(int(found[0]))
    return {k:np.asarray(trajectory[k])[indices] for k in ('states','tip_positions_m','tip_velocities_m_s')}


def sampled_metrics(trajectory):
    values=common_nodes(trajectory);target=np.array([.29,.035,.19])
    errors=np.linalg.norm(values['tip_positions_m']-target,axis=1);speeds=np.linalg.norm(values['tip_velocities_m_s'],axis=1)
    return dict(holding_max_position_error_m=float(errors[30:].max()),holding_max_speed_m_s=float(speeds[30:].max()),
        terminal_position_error_m=float(errors[-1]),accepted=bool(errors[30:].max()<=.01 and speeds[30:].max()<=.02))


def compare_nodes(left,right):
    a,b=common_nodes(left),common_nodes(right)
    dp=np.linalg.norm(a['tip_positions_m']-b['tip_positions_m'],axis=1)
    dv=np.linalg.norm(a['tip_velocities_m_s']-b['tip_velocities_m_s'],axis=1)
    dx=a['states']-b['states'];n=dx.shape[1]//2
    per=[dict(time_s=round(k*.01,2),tip_difference_m=float(dp[k]),velocity_vector_difference_m_s=float(dv[k]),
        coordinate_difference_norm_rad_m=float(np.linalg.norm(dx[k,:n])),rate_difference_norm_rad_m_s=float(np.linalg.norm(dx[k,n:]))) for k in range(36)]
    return dict(maximum_tip_difference_m=float(dp.max()),maximum_velocity_vector_difference_m_s=float(dv.max()),
        maximum_coordinate_component_difference_rad_m=float(abs(dx[:,:n]).max()),
        maximum_rate_component_difference_rad_m_s=float(abs(dx[:,n:]).max()),
        earliest_tip_difference_over_1mm_s=next((p['time_s'] for p in per if p['tip_difference_m']>.001),None),
        earliest_velocity_vector_difference_over_2mm_s=next((p['time_s'] for p in per if p['velocity_vector_difference_m_s']>.002),None),
        per_original_node=per)


def action_comparison(row,record):
    names=record['tendon_order']
    def command(plan):return np.array([plan['u/0/'+name] for name in names])
    stages=[]
    for label,key,original_key in [('raw','raw_returned_plan','raw_returned_plan'),('retained','selected_feasible_plan','selected_feasible_plan'),
        ('delivered','accepted_plan','delivered_plan')]:
        delta=command(row[key])-command(record[original_key])
        stages.append(dict(stage=label,max_first_command_difference_n=float(abs(delta).max())))
    return dict(stages=stages,first_different_stage=next((r['stage'] for r in stages if r['max_first_command_difference_n']>1e-8),None),
        source_original_iteration=record['diagnostics']['iterations'],source_original_recovery_selected=record['recovery']['selected'],
        new_iteration=row['diagnostics']['iterations'],stopping_reason=row['diagnostics']['policy_stop_reason'],
        selected_iteration=row['diagnostics']['selected_feasible_iteration'],recovery_selected=row['recovery']['selected'],
        accepted_scaled_violation=row['verification']['scaled_violation'],
        initialized_vector_equal=row['exact_initialized_vector_equal'],bounds_equal=row['exact_bounds_equal'],
        problem_inspection=row['problem_inspection'],stopping_controls=row['stopping_controls'],
        prefix_iterations=None if not row['prefix'] else row['prefix']['diagnostics']['iterations'])


def series(name,times,values,color):
    return dict(name=name,color=color,points=np.column_stack([times,values]).tolist())


def build(host):
    s=core.state(host)
    if s['pending'] or s.get('validation_reservation'):
        raise ValueError('KNOWN_OUTCOMES_AND_SETTLED_VALIDATION_REQUIRED')
    out=core.ROOT/s['spec']['evidence_destination'];out.mkdir(parents=True,exist_ok=True)
    corrections=s.get('import_provenance_corrections',{})
    for ref in s['historical_diagnostic_sources']:
        value=host.store.artifact(ref);provenance=value.get('provenance',{})
        if not provenance.get('folder'):continue
        actual_study=core.read(core.ROOT/provenance['folder']/'scientific_summary.json')['study_id']
        if provenance['study_id']==actual_study or ref['artifact_id'] in corrections:continue
        corrected=deepcopy(value);corrected['original_study']=actual_study
        corrected['provenance'].update(study_id=actual_study,correction_of=ref,
            correction_reason='Use the source summary study_id instead of a label inferred from its folder; record/configuration and all computed inputs remain unchanged.')
        corrections[ref['artifact_id']]=core.save(host,corrected,'historical_import_provenance_correction')
    if corrections:core.update(host,import_provenance_corrections=corrections)
    values=[(r,host.store.artifact(r)) for r in s['mechanics_results']]
    inspection=next((r,v) for r,v in values if v['operation']=='inspect' and 'saved_trajectory' in v)
    closed=next((r,v) for r,v in values if v.get('investigation')=='closed_loop')
    saved=inspection[1]['saved_trajectory'];checkpoint=archived(**s['numerical_history']['saved_checkpoint_archive'])
    candidate=host.store.artifact(s['numerical_history']['mechanics'])['candidate'];scales=np.asarray(inspection[1]['state_order']['scales'])
    vector={**{'design/d':candidate['d']},**{f'x/{k}/{j}':x/scales[j] for k,state in enumerate(candidate['states']) for j,x in enumerate(state)},
        **{f'u/{k}/{j}':u/8. for k,commands in enumerate(candidate['tensions_n']) for j,u in enumerate(commands)}}
    matches=[]
    for point in checkpoint['diagnostics']['retained_diagnostic_points']:
        point_values=dict(zip(checkpoint['diagnostics']['variable_order'],point['vector']))
        error=max(abs(v-point_values[k]) for k,v in vector.items())
        matches.append(dict(label=point['label'],iteration=point['iteration'],maximum_scaled_vector_difference=error))
    match=min(matches,key=lambda p:p['maximum_scaled_vector_difference'])
    if match['maximum_scaled_vector_difference']>1e-12:raise ValueError('CHECKPOINT_SELECTED_TRAJECTORY_MISMATCH')
    bdf=archived(**s['numerical_history']['saved_bdf_archive'])
    tight=next((r,v) for r,v in values if v.get('method')=='BDF')
    offline=dict(source=s['numerical_history']['mechanics'],checkpoint_match=match,original_resolved_offline_problem_available=False,
        inspection_reference=inspection[0],maximum_normalized_residual=inspection[1]['maximum_normalized_residual'],
        physical_context=inspection[1]['physical_context'],state_order=inspection[1]['state_order'],
        saved_sampled_acceptance=sampled_metrics(saved),saved_vs_implicit_one=None,
        tight_bdf_reference=tight[0],tolerance_comparison=compare_nodes(bdf['trajectory'],tight[1]['trajectory']),
        bdf_classification_from_saved_outputs=classify_replay(deepcopy(tight[1]['replay'])),implicit_resolutions=[])
    for ref,value in values:
        if value.get('method')=='implicit Euler':
            comparison=compare_nodes(value['trajectory'],tight[1]['trajectory'])
            offline['implicit_resolutions'].append(dict(reference=ref,substeps=value['substeps'],
                official_sampled=sampled_metrics(value['trajectory']),all_discrete_grid_samples=value['metrics'],versus_tight_bdf=comparison))
            if value['substeps']==1:offline['saved_vs_implicit_one']=compare_nodes(saved,value['trajectory'])
    standalone=[]
    for ref in s['diagnostics']:
        for row in host.store.artifact(ref)['rows']:
            original=host.store.artifact(corrections.get(row['source_execution']['artifact_id'],row['source_execution']))
            standalone.append(dict(reference=ref,source_provenance=original['provenance'],mode=row['mode'],solver_reused=row['solver_reused'],
                charged_solve_attempts=row['charged_solve_attempts'],charged_numerical_s=row['charged_numerical_s'],
                comparison_to_own_original=action_comparison(row,original['record']),command_n=row['first_input_n']))
    fixed=[host.store.artifact(r)['rows'][0] for r in s['diagnostics'] if host.store.artifact(r)['rows'][0]['mode']=='fixed_iteration']
    fixed_difference=max(abs(fixed[0]['raw_returned_plan'][k]-fixed[1]['raw_returned_plan'][k]) for k in fixed[0]['raw_returned_plan'])
    intervals=[dict(reference=r,**compact_numerics(v),source_update_id=v['source_interval']['update_id'])
        for r,v in values if v.get('method')=='BDF matched NMPC interval']
    primary=next(r for r in closed[1]['runs'] if r['execution_id']=='d42321543b9a45bb97b3ff28aca097ae')
    reader=ControlEvidence(host.store);executions=[];records=0;definitions=set()
    physical_series=[]
    for ref in s['results']:
        result=host.store.artifact(ref);source=reader.resolve(result['execution_id'])
        obs=reader.read_file(source,'controller_observations.json',[])
        for ob in obs:
            record=ob['complete_update_record'];definition=record['resolved_problem_reference'];file_ref=source['files'][definition['filename']]
            if file_ref['artifact_id']!=definition['sha256']:raise ValueError('NEW_CONTROLLER_DEFINITION_LINK_MISMATCH')
            if definition['sha256'] not in definitions:
                problem=json.loads(host.store.artifact(file_ref,raw=True))
                if core.digest(problem['objective_function'])!=record['model_identity']:raise ValueError('NEW_SERIALIZED_PROBLEM_IDENTITY_MISMATCH')
                definitions.add(definition['sha256'])
            records+=1
        motion=host.store.artifact(result['profile']['motion'])
        executions.append(dict(reference=ref,execution_id=result['execution_id'],role=result['role'],
            configuration=result['scientific_configuration'],profile_identity=result['profile_identity'],
            launch_commit=host.store.session(result['owner_run_id'])['snapshot']['project_commit'],
            sampled_acceptance=result['acceptance'],numerical_s=result['numerical_s'],complete_update_records=len(obs)))
        physical_series.append(series('Fresh '+result['execution_id'][:6],[m['time_s'] for m in motion],[m['tip_speed_m_s'] for m in motion],['RoyalBlue','DarkOrange'][len(physical_series)]))
    if len(executions)!=2 or executions[0]['configuration']!=executions[1]['configuration'] or executions[0]['profile_identity']!=executions[1]['profile_identity']:
        raise ValueError('TWO_IDENTICAL_COMPLETE_PHYSICAL_EXECUTIONS_REQUIRED')
    speeds=[r['sampled_acceptance']['metrics']['holding_max_speed_m_s'] for r in executions]
    variability=dict(matched_executions=[r['reference'] for r in executions],observed_holding_speed_range_m_s=[min(speeds),max(speeds)],
        observed_spread_m_s=max(speeds)-min(speeds),sample_count=2,not_a_future_statistical_bound=True,
        action_path_comparison=s.get('matched_physical_diagnosis'),
        matched_stopping_action_path_reference=s.get('matched_stopping_action_path'),
        matched_stopping_action_path=host.store.artifact(s['matched_stopping_action_path']),
        ranking_rule='Require matched independent repetitions for every compared configuration; report all failures and observed ranges. Withhold a parameter ranking if ranges overlap or production-solver variability is unresolved at the performance scale. Two samples are only limited evidence, never a robustness guarantee.')
    resources=dict(research_model_requests=host.store.remaining()['used']['model_calls'],standalone_nmpc_attempts=s['local_solves'],
        standalone_nmpc_s=s['local_solve_s'],independent_integration_jobs=s['bdf_replays'],offline_refinement_attempts=s['offline_nlp'],
        mujoco_launches=host.store.remaining()['used']['backend_solves'],charged_numerical_s=s['numerical_s'],
        internal_closed_loop_updates=records,activity_elapsed_s=time.time()-s['started_unix'],ceilings=s['spec']['budgets'])
    summary=dict(schema='numerical_diagnosis_delivery_v1',study_id=host.run_id,status='engineering_complete',
        started_unix=s['started_unix'],start_clock_basis=s['spec']['start_clock_basis'],authorization=s['spec']['authorization'],
        base_commit=s['spec']['base_commit'],numerical_implementation_binding=s['freeze'],source_versions=s['profile']['science_hashes'],core_versions=s['core_hashes'],
        implementation_history=s.get('core_repairs',[]),profile_history=s['profile_history'],
        delivery_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        plot_tool_sha256=hashlib.sha256((core.ROOT/'tools/plot_numerical_diagnosis.ps1').read_bytes()).hexdigest(),
        runtime=dict(interpreter=str(core.PYTHON),python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ('numpy','scipy','casadi','mujoco','strands-agents','strands-harness')}),
        historical_ownership_preserved=s['numerical_history'],integration_consistency=offline,repeatability=dict(standalone=standalone,fixed_work_raw_all_variables_difference=fixed_difference,full_loop_variability=variability),
        import_provenance_corrections=corrections,
        closed_loop_diagnosis=dict(reference=closed[0],primary_execution=primary['execution_id'],
            peak_velocity_disagreement=primary['peak_velocity_disagreement'],holding_velocity_disagreement=primary['holding_velocity_disagreement'],matched_fixed_input=intervals,
            future_holding_predictions_exceed_limit_at_updates=[p['update_id'] for p in primary['points'] if p['predicted_holding_max_speed_m_s'] is not None and p['predicted_holding_max_speed_m_s']>.02],
            requested_applied_max_difference_n=max(p['requested_applied_difference_n'] for p in primary['points']),
            holding_projection_position_max_m=max(p['projected_position_difference_m'] for p in primary['points'] if p['time_s']>=.30),
            holding_applied_input_range_n=[min(p['input_min_n'] for p in primary['points'] if p['time_s']>=.30),max(p['input_max_n'] for p in primary['points'] if p['time_s']>=.30)],
            initialization_selected=primary['initialization_selected'],noninitialization_accepted=primary['noninitialization_accepted'],unusable=primary['unusable']),
        physical_validation=executions,resources=resources,verification=dict(unique_focused_checks=10,new_controller_complete_records=records,serialized_definitions_verified=len(definitions),repository_wide_suites=0),
        repairs=['Explicit zero-model numerical mode and configurable failing-case repetition reserve.',
            'Per-independent-configuration integration accounting; offline refinement protects a verification job/time until consumed.',
            'Historical archive imports retain ownership; complete current graphs are resolved from their hashed source archive.',
            'Fixed-work diagnostics disable all internal timing stops and retain an external timeout; production policy remains unchanged.',
            'BDF feedback separates official sampled acceptance, node consistency, dense diagnostics and optimizer interpolation.',
            'Reusable aligned evidence and explicit repetition/ranking qualification are exposed in the existing host packet.'],
        readiness=dict(resume_model_organized_parameter_ranking=False,next_step='Further numerical/model diagnosis of the holding predictor and projected/full-state mismatch before control adaptation or LLM-organized ranking.',
            engineering_milestone_complete=True,robot_task_success_required_for_engineering_completion=False),
        limitations=['Grid refinement supports transcription error and numerical damping as a hypothesis; modal dissipation is not uniquely isolated.',
            'The original resolved offline NLP and earlier-controller runtime cache/history are unavailable; saved-point agreement is not a full runtime reconstruction.',
            'Fixed-work agreement is restricted to this complete update and does not establish production bitwise determinism.',
            'Accurate integration improves the initial matched interval but does not explain the final fixed-input one-step discrepancy; effects on the complete closed loop and projection/model versus planning contributions remain unresolved.',
            'No control law/weight change, structural search or offline trajectory initialization was introduced.',
            'No offline refinement started: remaining integration slots were used for accuracy and matched model checks; no independent verification job remains.',
            'Two physical repetitions on one frozen task/seed give an observed range only; no stable parameter ranking or general robustness claim.'])
    core.atomic_json(out/'scientific_summary.json',summary)
    core.update(host,numerical_findings=dict(integration_consistent=False,original_sampled_offline_passes=True,independent_bdf_task_passes=False,
        fixed_work_current_case_repeated=True,production_determinism_not_established=True,full_loop_variability=variability,readiness=summary['readiness']))
    _plots(out,values,tight[1]['trajectory'],primary,physical_series)
    _report(out,summary)
    return summary


def _plots(out,values,bdf,primary,physical_series):
    curves=[];differences=[]
    for ref,value in values:
        if value.get('method')=='implicit Euler':
            tr=value['trajectory'];k=value['substeps'];color={1:'RoyalBlue',2:'DarkOrange',4:'ForestGreen'}[k]
            curves.append(series('IE '+str(k)+' nodes',tr['times_s'],np.linalg.norm(tr['tip_velocities_m_s'],axis=1),color))
            comp=compare_nodes(tr,bdf);differences.append(series('IE '+str(k)+' vs BDF',[p['time_s'] for p in comp['per_original_node']],[p['velocity_vector_difference_m_s'] for p in comp['per_original_node']],color))
    curves.append(series('BDF dense',bdf['times_s'],np.linalg.norm(bdf['tip_velocities_m_s'],axis=1),'Black'))
    curves.append(series('Speed limit',[.30,.35],[.02,.02],'Firebrick'))
    motion=primary['motion'];points=primary['points'];aligned=primary['aligned']
    physics=series('Primary measured',[m['time_s'] for m in motion],[m['tip_speed_m_s'] for m in motion],'Black')
    predictions=series('Accepted next speed',[a['end_s'] for a in aligned],[np.linalg.norm(a['predicted_tip_velocity_m_s']) for a in aligned],'RoyalBlue')
    qualifying=[p for p in points if p['predicted_holding_max_speed_m_s'] is not None]
    charts=[dict(filename='offline_integration.png',title='Fixed schedule: integration resolution and node disagreement',panels=[
        dict(y_label='Holding speed [m/s]',x_min=.30,x_max=.35,series=curves),
        dict(y_label='Velocity vector difference [m/s]',x_min=0.,x_max=.35,series=differences)]),
        dict(filename='closed_loop_alignment.png',title='Archived primary: measured motion and aligned accepted predictions',panels=[
            dict(y_label='Holding speed [m/s]',x_min=.25,x_max=.35,series=[physics,predictions,series('Holding limit',[.30,.35],[.02,.02],'Firebrick')]),
            dict(y_label='One-step vector error [m/s]',x_min=0.,x_max=.35,series=[series('Aligned velocity error',[a['end_s'] for a in aligned],[a['velocity_difference_m_s'] for a in aligned],'DarkOrange')]),
            dict(y_label='Holding forecast speed [m/s]',x_min=.20,x_max=.35,series=[series('Plan holding max',[p['time_s'] for p in qualifying],[p['predicted_holding_max_speed_m_s'] for p in qualifying],'ForestGreen'),series('Plan terminal speed',[p['time_s'] for p in qualifying],[p['predicted_terminal_speed_m_s'] for p in qualifying],'RoyalBlue')])]),
        dict(filename='physical_repetitions.png',title='Two fresh identical primary configurations: sampled holding motion',panels=[
            dict(y_label='Holding speed [m/s]',x_min=.25,x_max=.35,series=physical_series+[physics,series('Acceptance limit',[.30,.35],[.02,.02],'Firebrick')])])]
    core.atomic_json(out/'plot_data.json',charts)
    subprocess.run(['powershell.exe','-NoProfile','-File',str(core.ROOT/'tools/plot_numerical_diagnosis.ps1'),'-DataPath',str(out/'plot_data.json'),'-OutputDirectory',str(out)],check=True,cwd=core.ROOT,timeout=60)


def _report(out,s):
    a=s['integration_consistency'];b=s['repeatability'];c=s['closed_loop_diagnosis'];r=s['resources']
    lines=['# 数值诊断交付 nd1011','',
        '本工程里程碑完成；机器人保持任务仍未通过。下一步应继续数值/模型诊断，随后再做有证据支持的控制适配；现在不恢复基于单次结果的 LLM 参数排序。',
        '',f"研究实际起点：{s['start_clock_basis']}。基线 `{s['base_commit']}`，数值实施绑定 `{s['numerical_implementation_binding']}`。历史 STOP 研究保持封存，归档输入保留原归属。应用层研究模型请求为 **0**。",'',
        '## A：离线优化与独立积分','',
        f"保存轨迹与检查点保留点完全一致；最大归一化动力学残差 {a['maximum_normalized_residual']:.3e}。紧根求解的 1 子步重构与保存轨迹最大速度状态分量差 {a['saved_vs_implicit_one']['maximum_rate_component_difference_rad_m_s']:.3e} rad/m/s。原始零状态、24 维状态顺序、物理缩放、世界坐标、六腱顺序及全部 35 条命令已检查。原离线序列化 NLP 未归档，不能声称恢复了所有求解运行条件。",'',
        '| 独立积分配置 | 原任务采样保持误差 mm | 保持速度 m/s | 对紧 BDF 的最大节点速度向量差 m/s | 采样接受 |',
        '|---|---:|---:|---:|---|']
    for row in a['implicit_resolutions']:
        m=row['official_sampled'];lines.append(f"| IE substeps={row['substeps']} | {m['holding_max_position_error_m']*1000:.6f} | {m['holding_max_speed_m_s']:.9f} | {row['versus_tight_bdf']['maximum_velocity_vector_difference_m_s']:.9f} | {m['accepted']} |")
    m=a['bdf_classification_from_saved_outputs']['sampled_evaluator']
    lines+= [f"| tight BDF | {m['holding_max_position_error_m']*1000:.6f} | {m['holding_max_speed_m_s']:.9f} | reference | False |",'',
        f"首次超过 0.002 m/s 的节点速度向量差已出现在 0.01 s；详见摘要中的逐节点状态、位置与速度向量差。BDF 收紧容差后最大节点速度向量变化仅 {a['tolerance_comparison']['maximum_velocity_vector_difference_m_s']:.3e} m/s，远小于分辨率误差。证据支持离散积分误差，数值阻尼与结果相符，但未唯一分离模态耗散。保持差异不是保存轨迹不满足离散方程造成的。",'',
        '修复：BDF 报告将原任务采样接受、优化器节点积分一致性、密集采样诊断及优化器输出线性插值比较分开。插值速度不再作为连续真值或接受门。保存数据重分类及一个有区别的静态夹具验证该修复；本候选仍失败。密集采样不构成连续时间保证。',
        '', '未启动重新优化。诊断模式在启动前实际保护一项对应独立积分验证和 450 s，名额/时间不足会拒绝；本研究将 6 次积分用于三个 IE 分辨率、一次 BDF 精度比较及两个闭环短区间，已无独立验证名额。',
        '', '![离线积分对齐](../evidence/numerical_diagnosis_20261011/offline_integration.png)','',
        '## B：相同输入的动作差异','',
        '早期输入来自 unified-research-20261011 的 update 1，缺少完整解析问题；当前完整输入来自已封存 mechanics-control-20261011 主案例的 update 1，原问题图通过哈希归档引用恢复。两组分别与自己的原执行比较，不把跨研究动作差当作相同配置证据。初始化向量、边界、序列化表达式身份及已保存点的目标/约束检查相符；这些检查不重建历史缓存、尾求解器或计时历史。更正了导入早期归档时从文件夹名称推断的 study_id 标签；原输入和计算结果未改变，原标签与更正引用均保留。','',
        '| 源输入 / 条件 | 新迭代 | 停止原因 | 对自己原命令的最大差 N | 可行残差 |',
        '|---|---:|---|---:|---:|']
    for row in b['standalone']:
        q=row['comparison_to_own_original'];label=row['source_provenance']['study_id']+(' / reused' if row['solver_reused'] else ' / fresh')+' / '+row['mode']
        lines.append(f"| {label} | {q['new_iteration']} | {q['stopping_reason']} | {q['stages'][-1]['max_first_command_difference_n']:.9f} | {q['accepted_scaled_violation']:.3e} |")
    lines+=['',f"当前输入的固定工作量 fresh/reused 原始返回全变量最大差为 {b['fixed_work_raw_all_variables_difference']:.3e}；对应前置解也一致。生产 fresh/reused 当前输入均在第 5 次迭代结束，原执行第 4 次；旧输入本次第 18 次，原第 8 次。差异首先出现在 raw 返回；retained/recovery/delivered 的全过程、数值可行性与选择均保存在证据中。没有发现需要修复的生产动作丢失。",'',
        '修复：固定工作量诊断关闭可行返回计时、IPOPT CPU 和墙钟限制，保留回调工作量上限、收敛终止和外部进程超时。生产记录的 tracing 始终关闭，生产停止策略保持原样。reused 条件先进行一次计费的相同输入前置解，不冒称重建了实际前序 update。旧输入唯一原因仍未证实，也不承诺生产比特确定性。',
        '', '新完整重复给出了更强的机制证据：update 10（0.10 s）的模型图、求解设置、变量/初值、测量状态、前一命令和暖启动完全相同，tracing 均关闭。一条运行在第 5 次迭代、5.7167165 s 停止，另一条在第 4 次、5.0850756 s 停止。第一条保留的第 4 迭代点与第二条 raw 返回全变量完全一致；第一条额外 raw 第 5 点不可行，随后 reintegration 将残差降至 1.4e-12 并选择更优张力，首命令因此改变 0.009705 N。结合原 5 s 最小计时停止条件，这定位了停止时点与恢复选择造成的动作机制，不能泛化为所有旧差异的唯一原因。',
        '', '## C：闭环为什么不稳定保持','',
        f"主案例全程最大一步速度向量误差 {c['peak_velocity_disagreement']['velocity_difference_m_s']:.9f} m/s 位于 0→0.01 s；保持窗口最大值 {c['holding_velocity_disagreement']['velocity_difference_m_s']:.9f} m/s 位于 0.33→0.34 s。主案例接受 {c['noninitialization_accepted']} 个非初始化方案，初始化选择 {c['initialization_selected']} 次，不可用方案 {c['unusable']} 个。",'',
        '最大有效 horizon 为 10 个控制步，绝对保持开始 0.30 s，braking lead 为 0，保持节点从当前时刻 0.20 s 起进入 horizon。接近窗口时接受计划已含超限速度；末端预测常很低，不能代表整个保持窗口。请求与施加的腱命令完全相同，保持阶段输入未逼近全部 8 N 上界；这不能证明足够控制权限，也不支持简单归因于饱和。保留方案与恢复方案均有可行性依据，没有观察到把有用方案无故丢弃的证据。', '',
        '| 同状态/输入短区间 | IE 对物理速度向量误差 m/s | BDF 对物理误差 m/s | IE 与 BDF 差 m/s |',
        '|---|---:|---:|---:|']
    for row in c['matched_fixed_input']:
        lines.append(f"| update {row['source_update_id']} | {row['final_implicit_physical_velocity_difference_m_s']:.9f} | {row['final_continuous_physical_velocity_difference_m_s']:.9f} | {row['final_implicit_continuous_velocity_difference_m_s']:.9f} |")
    lines+= ['', '两段保存的一步预测在同一 mass/force 方程下残差分别接近机器精度与 3.3e-11。初始区间说明离线与 NMPC 确有共同积分误差机制；末端区间里 IE/BDF 只差约 0.000985 m/s，物理误差却约 0.022 m/s。该末端固定输入一步误差不能单由积分精度解释；投影/模型差异及软保持规划的贡献仍未分离。这不排除更精细积分改善整个闭环的可能性。保持世界位置投影误差约 3 mm，单凭该值也不能确定主因。没有进行权重扫描或无依据的提前制动修改。','',
        '![历史主案例的对齐反馈](../evidence/numerical_diagnosis_20261011/closed_loop_alignment.png)','',
        '## 两次新完整闭环与成本','',
        '| 新执行 | 保持位置误差 mm | 保持速度 m/s | 原任务接受 |',
        '|---|---:|---:|---|']
    for row in s['physical_validation']:
        m=row['sampled_acceptance']['metrics'];lines.append(f"| `{row['execution_id']}` | {m['holding_max_error_m']*1000:.6f} | {m['holding_max_speed_m_s']:.9f} | {row['sampled_acceptance']['accepted']} |")
    lines+= ['',f"两次执行的完整科学配置及评估版本相同；均由 fresh 执行生成、记录完整输入。观察到的保持速度范围 {b['full_loop_variability']['observed_holding_speed_range_m_s']}，跨度 {b['full_loop_variability']['observed_spread_m_s']:.9f} m/s。它只是两次观察，不是未来变动上界，更不能据此排序不同控制权重。",'',
        '评价规则：每个待比较配置都需匹配的独立重复；保留失败与观察范围；范围重叠或求解变动尚未在性能尺度上测清时，拒绝参数优劣结论。一次有利结果不建立改进，固定迭代也不作为生产修复。', '',
        '![新主配置重复](../evidence/numerical_diagnosis_20261011/physical_repetitions.png)','',
        f"数值成本 {r['charged_numerical_s']:.3f}/10800 s；独立 NMPC {r['standalone_nmpc_attempts']}/8 次、{r['standalone_nmpc_s']:.3f}/1200 s（含两个前置解）；独立积分 {r['independent_integration_jobs']}/6；离线重优化 {r['offline_refinement_attempts']}/1；MuJoCo {r['mujoco_launches']}/4；模型请求 {r['research_model_requests']}/0。闭环内部 {r['internal_closed_loop_updates']} 次 NMPC 更新只计入各自仿真，没有重复收费。活动时间包含实施与交付，最大 8 h。",'',
        f"{s['verification']['unique_focused_checks']} 项独立的针对性检查通过；没有运行全仓套件、种子扫描或额外 smoke。70 条新控制输入与其原问题链接均验证；原研究缺失的一条输入仍不补造。归档/成员哈希已校验。", '',
        '最小下一实验：新预算内，从主案例末端保存的完整 MuJoCo 状态与对应投影状态出发，固定同一命令，对比初始世界运动、短区间加速度和投影残差，区分降阶/状态投影误差与反馈规划误差；之后才选择控制适配。原离线候选若需要进一步优化，应使用更细转录并预留独立 BDF 验证，不能用旧离散任务通过作为验证。', '',
        '[诊断规范](../examples/numerical_diagnosis/specification.json) · [运行说明](numerical_diagnosis_runbook.md) · [机器摘要](../evidence/numerical_diagnosis_20261011/scientific_summary.json) · [归档清单](../evidence/numerical_diagnosis_20261011/archive_manifest.json) · [原封存报告](mechanics_control_completion.md)']
    (core.ROOT/'docs/numerical_diagnosis_completion.md').write_text('\n'.join(lines)+'\n',encoding='utf8')


def deliver(host):
    summary=build(host);s=core.state(host)
    if s['research_status']!='stopped':
        refs=[*s['results'],*s['mechanics_results'],*s.get('diagnostics',[])]
        core.dispatch(host,dict(action='stop',supporting_evidence=refs,hypothesis='Engineering questions have bounded evidence; remaining model/projection and ranking limitations are explicit.',
            expected_observation='Sealed independent study with zero model requests and settled numerical charges.',weakening_observation='Unknown outputs, an exceeded ceiling or unverified provenance prevents delivery.',
            fixed_conditions='Preserved original frozen task and sealed historical ownership.',stopping_condition='No further scientific dispatch; export and verify immutable evidence.',
            interpretation='Diagnostic engineering complete; task success and trustworthy parameter rankings are not established.'),'engineering-diagnostic-stop',origin='engineering')
    elapsed=time.time()-s['started_unix'];used=host.store.remaining()['used']['wall_s'];engineering=max(0.,elapsed-used)
    row,fresh=host.store.reserve(host.run_id,'engineering-diagnostic-delivery',core.digest({'study':host.run_id}),host.actor,{**core.zero(),'wall_s':engineering},kind='engineering')
    if fresh:
        host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=host.actor,tool_id='engineering.numerical_delivery',tool_version='1.0.0',execution_status='completed',charged=core.zero()),dict(activity_elapsed_s=elapsed),elapsed=engineering)
        core.update(host,completed_unix=time.time())
    out=core.ROOT/s['spec']['evidence_destination'];core.export(host,out)
    manifest=core.read(out/'archive_manifest.json');archive_path=out/'immutable_artifacts.tar.gz'
    with archive_path.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=manifest['archive_sha256']:raise ValueError('DELIVERY_ARCHIVE_HASH_MISMATCH')
    with tarfile.open(archive_path) as archive:
        for member in manifest['members']:
            body=archive.extractfile(member['name']).read()
            if len(body)!=member['bytes'] or hashlib.sha256(body).hexdigest()!=member['sha256']:raise ValueError('DELIVERY_MEMBER_HASH_MISMATCH')
    current=core.state(host);b=current['spec']['budgets'];r=summary['resources']
    if (current['pending'] or current['numerical_reserved_s'] or r['research_model_requests']!=0 or r['standalone_nmpc_attempts']>b['local_solves'] or
        r['standalone_nmpc_s']>b['local_solve_s'] or r['independent_integration_jobs']>b['bdf_replays'] or r['mujoco_launches']>b['physical_launches'] or
        r['offline_refinement_attempts']>b['offline_nlp'] or r['charged_numerical_s']>b['numerical_s'] or time.time()-s['started_unix']>b['activity_s']):raise ValueError('DELIVERY_CEILING_OR_UNKNOWN_OUTCOME')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('DELIVERY_UNSEALED_CALL')
    core.atomic_json(out/'verification.json',dict(focused_checks=summary['verification'],archive_members_verified=len(manifest['members']),
        archive_sha256=manifest['archive_sha256'],ceilings_verified=True,unknown_outcomes=0,stopped=True,research_model_requests=0))
    return dict(study_id=host.run_id,status='stopped',resources=r,report='docs/numerical_diagnosis_completion.md',archive_members_verified=len(manifest['members']))


if __name__=='__main__':
    spec=core.read(core.ROOT/'examples/numerical_diagnosis/specification.json')
    host=Host(core.ROOT/'runs'/spec['study_id'],spec['study_id'],actor='engineering')
    print(json.dumps(deliver(host)))
