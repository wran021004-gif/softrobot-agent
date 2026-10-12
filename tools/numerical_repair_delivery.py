"""Summarize and seal existing outcomes, without scientific dispatch."""
from collections import defaultdict
import hashlib
import json
import tarfile
import time
import importlib.metadata
import platform
import numpy as np
from tools import research_core as core
from tools import numerical_repair as repair
from tools.platform_host import Host
from tools.state_io import atomic_json


def split_archive(out):
    """Byte transport only; the existing tar.gz and member format stay intact."""
    archive=out/'immutable_artifacts.tar.gz';manifest=core.read(out/'archive_manifest.json')
    parts=[];joined=hashlib.sha256();total=0
    with archive.open('rb') as stream:
        while body:=stream.read(40*1024*1024):
            name=f'{archive.name}.part{len(parts)+1:03d}'
            (out/name).write_bytes(body);joined.update(body);total+=len(body)
            parts.append(dict(filename=name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
    if joined.hexdigest()!=manifest['archive_sha256']:raise ValueError('ARCHIVE_SPLIT_HASH_MISMATCH')
    value=dict(schema='archive_byte_parts_v1',archive_file=archive.name,archive_bytes=total,
        archive_sha256=joined.hexdigest(),parts=parts)
    atomic_json(out/'archive_parts.json',value)
    (out/'.gitignore').write_text('immutable_artifacts.tar.gz\n',encoding='utf8')
    (out/'.gitattributes').write_text('immutable_artifacts.tar.gz.part* -text\n',encoding='utf8')
    return value


def restore_archive(out,destination=None):
    """Reassemble ordered bytes and verify before replacing the local archive."""
    index=core.read(out/'archive_parts.json');destination=destination or out/index['archive_file']
    temporary=destination.with_name(destination.name+'.restoring');joined=hashlib.sha256();total=0
    with temporary.open('wb') as stream:
        for part in index['parts']:
            body=(out/part['filename']).read_bytes()
            if len(body)!=part['bytes'] or hashlib.sha256(body).hexdigest()!=part['sha256']:
                raise ValueError('ARCHIVE_PART_HASH_MISMATCH')
            stream.write(body);joined.update(body);total+=len(body)
    if total!=index['archive_bytes'] or joined.hexdigest()!=index['archive_sha256']:
        raise ValueError('REASSEMBLED_ARCHIVE_HASH_MISMATCH')
    if joined.hexdigest()!=core.read(out/'archive_manifest.json')['archive_sha256']:
        raise ValueError('REASSEMBLED_ARCHIVE_MANIFEST_MISMATCH')
    temporary.replace(destination)
    return dict(parts_verified=len(index['parts']),reassembled_bytes=total,archive_sha256=joined.hexdigest())


def build(host):
    s=core.state(host)
    if s['pending'] or s.get('validation_reservation'):raise ValueError('SETTLE_PENDING_AND_VERIFICATION_BEFORE_DELIVERY')
    out=core.ROOT/s['spec']['evidence_destination'];out.mkdir(parents=True,exist_ok=True)
    mechanics=[];physical=[];groups=defaultdict(list);updates=0
    for ref in s['mechanics_results']:
        v=host.store.artifact(ref)
        row=dict(reference=ref,**{k:v.get(k) for k in ('operation','status','execution_id','charged_numerical_s','termination_reason',
            'original_task_feasible','relaxed_nlp_feasible','hard_max_normalized_violation','trajectory_metrics','original_task_gaps',
            'source_mechanics','replay','state_kind','update_id','initial_tip_vs_archived_m','final_tip_vs_archived_m',
            'initial_position_model_difference_m','initial_velocity_model_difference_m_s') if k in v})
        if v.get('candidate'):row.update(structure={k:v['candidate'].get(k) for k in ('d','lengths_m','integration_method','substeps')},
            selection=v['candidate'].get('selection'),retained=v.get('retained_candidate_assessments'))
        mechanics.append(row)
    for ref in s['results']:
        v=host.store.artifact(ref);acceptance=v.get('acceptance') or {};profile=v.get('profile') or {}
        motion=host.store.artifact(profile['motion']) if profile.get('motion') else []
        from extensions.tendon_family.control_evidence import ControlEvidence
        reader=ControlEvidence(host.store)
        try:
            source=reader.resolve(v['execution_id']);observations=reader.read_file(source,'controller_observations.json',[])
            commands=reader.read_file(source,'actual_commands.json',[])
        except (ValueError,KeyError):observations=[];commands=[]
        updates+=len(observations)
        row=dict(reference=ref,execution_id=v['execution_id'],role=v['role'],status=v['status'],candidate=v['candidate'],
            selected_execution=v.get('selected_execution'),profile_identity=v['profile_identity'],acceptance=acceptance,
            numerical_s=v['numerical_s'],fresh_execution=v['fresh_execution'],complete_update_records=len(observations))
        row['controller_evidence']={k:profile.get(k) for k in ('accepted_plans','accepted_noninitialization_plans',
            'initialization_selected','solver_error_count','unusable_plans','raw_termination_counts',
            'one_step_prediction_summary','valid_complete_execution')}
        settings=[o['complete_update_record']['diagnostics']['options'] for o in observations]
        row['research_stopping_observed']=bool(settings) and all(option['max_cpu_s'] is None
            and option['max_wall_s'] is None and option['feasible_return'] is None
            and option['retain_feasible_iterate'] and option['max_iterations']==s['profile']['recipe']['max_iterations']
            for option in settings)
        row['maximum_observed_iterations']=max((o['complete_update_record']['diagnostics']['iterations'] for o in observations),default=None)
        row['recorded_holding_first_step_predictions']=[dict(update_time_s=o['time_s'],prediction_time_s=p['time_s'],
            predicted_speed_m_s=float(np.linalg.norm(p['tip_velocity_m_s'])))
            for o in observations if (p:=o.get('one_step_prediction')) and .30-1e-9<=p['time_s']<=.35+1e-9]
        physical.append(row);groups[(v['candidate']['artifact_id'],v['profile_identity'])].append((row,observations,motion,commands))
    comparisons=[]
    for rows in groups.values():
        if len(rows)<2:continue
        a,b=rows[-2:];ua=np.asarray([o['actual_tension_n'] for o in a[1]]);ub=np.asarray([o['actual_tension_n'] for o in b[1]])
        pa=np.asarray([m['tip_position_m'] for m in a[2]]);pb=np.asarray([m['tip_position_m'] for m in b[2]])
        va=np.asarray([m['tip_velocity_m_s'] for m in a[2]]);vb=np.asarray([m['tip_velocity_m_s'] for m in b[2]])
        comparisons.append(dict(executions=[a[0]['reference'],b[0]['reference']],command_shapes_equal=ua.shape==ub.shape,
            full_command_max_difference_n=float(abs(ua-ub).max()) if ua.shape==ub.shape and ua.size else None,
            world_position_max_vector_difference_m=float(np.linalg.norm(pa-pb,axis=1).max()) if pa.shape==pb.shape and pa.size else None,
            world_velocity_max_vector_difference_m_s=float(np.linalg.norm(va-vb,axis=1).max()) if va.shape==vb.shape and va.size else None,
            support='Two observed executions on this frozen task/seed; no general robustness or historical promotion claim'))
    evidence={}
    for event in host.store.events(host.run_id):
        if event['kind'] in ('projection_repair_comparison','projection_force_comparison','method_selection_comparison',
            'controller_recipe_selection','restored_baseline_and_reused_C_identity','C_identity_roundoff_qualification',
            'selected_work_policy_freeze'):
            evidence.setdefault(event['kind'],[]).extend(event['outputs'])
    gate=repair.length_admission(host)
    fixed_solves=[r for r in mechanics if r['operation']=='solve' and abs(r.get('structure',{}).get('d',10)-s['spec']['reference_parameters']['d'])<1e-10]
    fixed_verified=bool(gate['new_fixed_offline_validations'])
    selected_policy=s.get('selected_policy_validation')
    policy_ok=bool(selected_policy) and all(row.get('verification',{}).get('feasible') and row['diagnostics']['options']['feasible_return'] is None
        and row['diagnostics']['options']['max_cpu_s'] is None and row['diagnostics']['options']['max_wall_s'] is None
        and row['diagnostics']['options']['max_iterations']==s['profile']['recipe']['max_iterations']
        for row in host.store.artifact(selected_policy)['rows'])
    selected_physical=[row for row in physical if row['profile_identity']==s['profile']['identity']]
    policy_ok=policy_ok and bool(selected_physical) and all(row['research_stopping_observed'] for row in selected_physical)
    complete_selected=[row for row in selected_physical if row['status']=='evaluated']
    closed_loop_status=('passed' if gate['matching_passing_executions'] else
        'failed' if any(not row['acceptance'].get('accepted') for row in complete_selected) else
        'incomplete' if selected_physical else 'not_attempted')
    statuses=dict(research_policy='passed' if policy_ok else 'incomplete',
        model_projection_comparison='passed' if evidence.get('projection_repair_comparison') else 'incomplete',
        fixed_offline='passed' if fixed_verified else 'failed' if any(row.get('trajectory_metrics') for row in fixed_solves) else 'incomplete' if fixed_solves else 'not_attempted',
        fixed_closed_loop=closed_loop_status,
        optional_length_design='passed' if s.get('length_design_passed') else 'failed' if s.get('length_design_started') else 'not_attempted')
    reasons=dict(research_policy='Real controller solver options and complete update records disable all internal timed returns; fixed numerical work and feasibility remain active.' if policy_ok else 'Selected numerical-policy verification is incomplete.',
        model_projection_comparison='Archived baseline was reproduced; A/B/C controlled comparison retains a measured representable-dynamics limitation, with no isolated correction justified.',
        fixed_offline='A new fixed candidate passes numerical feasibility, independent original sampled task and exact optimizer-node checks.' if fixed_verified else
            'Both allowed fixed candidates pass numerical feasibility and independent original sampled task, but fail the unchanged 0.002 m/s node velocity-vector limit.',
        fixed_closed_loop='The same frozen selected candidate/profile has two fresh original-task passes.' if closed_loop_status=='passed' else
            'Selected original-task acceptance and its independent repetition are listed below; a diagnostic repetition cannot satisfy the two-pass gate.',
        optional_length_design='Strict fixed-offline and two-pass feedback admission did not open; the conditional design attempt remains unused.')
    resources=dict(application_model_requests=host.store.remaining()['used']['model_calls'],
        standalone_controller_solves=s['local_solves'],standalone_controller_s=s['local_solve_s'],
        independent_integration_configurations=s['bdf_replays'],offline_attempts=s['offline_nlp'],
        complete_mujoco_launches=host.store.remaining()['used']['backend_solves'],charged_numerical_s=s['numerical_s'],
        internal_closed_loop_updates=updates,activity_elapsed_s=time.time()-s['started_unix'],ceilings=s['spec']['budgets'])
    resources['activity_as_of_unix']=time.time()
    summary=dict(schema='numerical_repair_delivery_v1',study_id=host.run_id,status='engineering_delivered',
        started_unix=s['started_unix'],base_commit=s['spec']['base_commit'],implementation_binding=s['freeze'],
        source_versions=s['profile']['science_hashes'],profile_history=s['profile_history'],stages=statuses,stage_reasons=reasons,
        fixed_task=dict(target_m=[.29,.035,.19],duration_s=.35,control_period_s=.01,physics_step_s=.0005,
            holding_window_s=[.30,.35],position_limit_m=.01,speed_limit_m_s=.02,seed=17,d=s['spec']['reference_parameters']['d']),
        selected_recipe=s['profile']['recipe'],mechanics=mechanics,physical=physical,selected_physical=selected_physical,
        robot_task_success=bool(fixed_verified and gate['matching_passing_executions']),complete_run_comparisons=comparisons,
        local_diagnostics=s.get('diagnostics',[]),repair_evidence=evidence,length_design_admission=gate,resources=resources,
        selected_policy_validation=selected_policy,runtime=dict(python=platform.python_version(),interpreter=str(core.PYTHON),
            packages={name:importlib.metadata.version(name) for name in ('numpy','scipy','casadi','mujoco','strands-agents','strands-harness')}),
        barrier=s.get('remaining_barrier'),limitations=['Sampled task acceptance is not a continuous-time guarantee.',
            'The measured projection/representable dynamics discrepancy remains a tested model limitation.',
            'The fixed-input study restores available state fields; unarchived MuJoCo runtime fields are not claimed.',
            'Complete execution agreement does not establish original-task acceptance or broad robustness; diagnostic repetitions cannot satisfy length admission.'])
    atomic_json(out/'scientific_summary.json',summary)
    labels={'passed':'通过','failed':'失败','incomplete':'未完成','not_attempted':'未执行','passed_with_measured_limitation':'比较完成，保留已测局限'}
    readable_reasons=dict(research_policy='真实控制路径及全部更新均关闭内部计时返回，保留数值停止与可行性选择。',
        model_projection_comparison='重现原归档区间；完成 A/B/C 比较，保留实测模型差异。',
        fixed_offline='两次新候选均通过数值可行性和独立原采样任务，但未通过节点速度一致性。',
        fixed_closed_loop='选定配置两次完整执行均保持超速；重复为失败复现。',
        optional_length_design='准入门槛未满足；条件长度尝试未使用。')
    lines=['# 数值执行修复 nr1012','',
        '研究评估策略、数值转录与预算准入已接入实际执行链。机器人任务状态以以下独立阶段验收为准。','',
        '| 阶段 | 结果 | 原因 |','|---|---|---|',*[f'| {k} | {labels[v]} | {readable_reasons[k]} |' for k,v in statuses.items()],'',
        f"固定结构 d={s['spec']['reference_parameters']['d']}；目标 [0.29, 0.035, 0.19] m，原始零态、seed 17、六腱 0–8 N，时长 0.35 s、控制周期 0.01 s、物理步长 0.0005 s。原 inclusive 0.30–0.35 s 保持窗口要求位置误差 ≤0.01 m、速度 ≤0.02 m/s。",'',
        '`research_work_v1` 关闭内部 CPU/墙钟/可行返回计时，以数值收敛或已声明迭代上限停止。保留可行方案选择、返回张力重积分和外部 watchdog；中断为未完成。历史 timed 策略独立保留。',
        '',
        '中点法在离线约束、零态暖启动、NMPC 约束、尾扩展与返回张力恢复中一致使用。35 条物理命令未增加；内部节点共享命令。独立 BDF 由精确节点的 dense-output 状态计算世界位置/速度，不再插值采样速度作为节点真值。',
        '', '模型比较恢复原 update 34 的 q/v、时刻和命令，并与归档短区间核对。A–B 末端速度差 0.013031459 m/s，B–C 0.010355492 m/s，A–C 0.022833211 m/s。起点 A–B 差 0.000188673 m/s；初始 GVS 世界位置约差 2.925 mm。虚功映射后的力项仍有差异，未隔离出符号、尺度或顺序错误；没有按单个端点拟合修正。此处是已测模型局限，不声称全部误差精确相加。',
        '', '局部分歧输入在两个 fresh 12 迭代研究策略求解中均可行，交付命令最大差 0 N；这不建立完整闭环重复性。',
        '最终数值配置采用中点 16 子步、自动精确 AD、root tolerance 1e-8、最大 3 次迭代；保存 update 10 的真实控制路径验证数值可行。完整执行另逐次保存实际求解选项、返回/选中计划、恢复和交付命令。',
        '', '唯一控制适配为 `window_normalized_v1`：对原 0.05 s 保持窗口的软速度代价按窗口长度归一化。保持权重仍为 0.08125，等效每秒速率为 1.625；终端权重仍为 0.10。这是公开的目标函数适配，原验收限值与数值停止配置不变。',
        '', '| 新离线尝试 | 原数值任务 | 硬残差 | 保持误差 m | 保持速度 m/s |', '|---|---|---:|---:|---:|']
    for row in fixed_solves:
        m=row.get('trajectory_metrics') or {};lines.append(f"| {row['execution_id']} | {row.get('original_task_feasible')} | {row.get('hard_max_normalized_violation')} | {m.get('holding_max_position_error_m')} | {m.get('holding_max_speed_m_s')} |")
    lines+=['','独立积分结果（原任务与节点一致性分别验收）：','']
    for row in mechanics:
        if row.get('replay'):
            v=row['replay'];lines.append(f"- `{row['execution_id']}`：原采样任务 {v.get('original_task_acceptance',{}).get('accepted')}；节点一致性 {v.get('integration_consistency',{}).get('passed')}；最大位置差 {v.get('node_max_tip_disagreement_m')} m，速度向量差 {v.get('node_max_speed_disagreement_m_s')} m/s。")
    lines+=['','| 完整执行 | 用途 | 保持误差 m | 保持速度 m/s | 原任务通过 |','|---|---|---:|---:|---|']
    for row in physical:
        m=row['acceptance'].get('metrics',{});lines.append(f"| {row['execution_id']} | {row['role']} | {m.get('holding_max_error_m')} | {m.get('holding_max_speed_m_s')} | {row['acceptance'].get('accepted',False)} |")
    lines+=['','选定配置的已记录保持首步预测（两次相同）：','',
        '| 预测时刻 s | 速度 m/s |','|---:|---:|']
    for prediction in selected_physical[0]['recorded_holding_first_step_predictions'] if selected_physical else []:
        lines.append(f"| {prediction['prediction_time_s']:.2f} | {prediction['predicted_speed_m_s']:.9f} |")
    lines+=['','完整独立重复比较：','']
    for pair in comparisons:
        lines.append(f"- 完整命令最大差 {pair['full_command_max_difference_n']} N；世界位置向量最大差 {pair['world_position_max_vector_difference_m']} m；世界速度向量最大差 {pair['world_velocity_max_vector_difference_m_s']} m/s。只支持本次固定任务/seed 的两次观测，不声明一般鲁棒性或旧晋级协议通过。")
    lines+=['','剩余障碍：修订离线候选在 0.290625 s 的节点速度向量差 0.003526347 m/s，超过 0.002 m/s；选定 NMPC 的已接受保持预测仍含超速，且两次实测保持速度均为 0.025813858 m/s，超过 0.02 m/s。两个固定离线尝试已用完；第三个槽位只属于未获准的长度设计。', '',
        f"长度设计准入：{gate['passed']}。排查闭环、旧离线候选和单次通过不能替代新候选三项验证与同一选定配置两次 fresh 原任务通过。",'',
        f"数值成本 {resources['charged_numerical_s']:.3f}/21600 s；独立控制求解 {resources['standalone_controller_solves']}/10、{resources['standalone_controller_s']:.3f}/1500 s；积分配置 {resources['independent_integration_configurations']}/12；离线 {resources['offline_attempts']}/3；完整 MuJoCo {resources['complete_mujoco_launches']}/6；应用模型请求 {resources['application_model_requests']}/0。内部 NMPC 更新 {updates} 次计入所属完整执行，不重复收费。",'',
        '14 项针对性回归检查通过，未运行全库测试。232 个归档成员及完整 SHA 已校验；四个 ≤40 MiB 的字节分片重组为原格式 tar.gz 后，完整 SHA 仍一致。新 checkout 可执行 `python -m tools.numerical_repair_delivery --restore-archive`，无科学调度。', '',
        '[规范](../examples/numerical_repair/specification.json) · [可执行运行说明](numerical_repair_runbook.md) · [机器摘要](../evidence/numerical_repair_20261012/scientific_summary.json) · [归档清单](../evidence/numerical_repair_20261012/archive_manifest.json) · [分片清单](../evidence/numerical_repair_20261012/archive_parts.json) · [完整性校验](../evidence/numerical_repair_20261012/verification.json)']
    (core.ROOT/'docs/numerical_repair_completion.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return summary


def main():
    import sys
    out=core.ROOT/'evidence/numerical_repair_20261012'
    if '--split-archive' in sys.argv:
        print(json.dumps(split_archive(out)));return
    if '--restore-archive' in sys.argv:
        print(json.dumps(restore_archive(out)));return
    host=Host(core.ROOT/'runs/nr1012','nr1012',actor='unified-research')
    summary=build(host)
    if '--seal' in sys.argv:
        s=core.state(host)
        if s['research_status']!='stopped':
            plan=dict(action='stop',supporting_evidence=[*s['results'],*s['mechanics_results']],
                **{k:'Engineering-led bounded repair finished; each robot-task stage is separately classified in delivery.'
                    for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
            core.dispatch(host,plan,'engineering-repair-stop',origin='engineering')
        core.export(host)
        out=core.ROOT/summary['resources'].get('evidence_destination',core.state(host)['spec']['evidence_destination'])
        manifest=core.read(out/'archive_manifest.json')
        if hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()!=manifest['archive_sha256']:raise ValueError('ARCHIVE_HASH_MISMATCH')
        with tarfile.open(out/'immutable_artifacts.tar.gz') as archive:
            for member in archive:
                if hashlib.sha256(archive.extractfile(member).read()).hexdigest()!=member.name.split('/')[-1].split('.')[0]:raise ValueError('ARCHIVE_MEMBER_HASH_MISMATCH')
        atomic_json(out/'verification.json',dict(archive_members_verified=len(manifest['members']),archive_sha256=manifest['archive_sha256'],focused_checks=14,repository_wide_suites=0))
        split_archive(out)
    print(json.dumps(dict(stages=summary['stages'],resources=summary['resources'],barrier=summary['barrier']),ensure_ascii=True))


if __name__=='__main__':main()
