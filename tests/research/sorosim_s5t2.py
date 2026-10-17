"""Exact raw-point KKT diagnostics, one secondary base solve and static fallback."""
from copy import deepcopy
import json
from pathlib import Path
import tarfile

from tests.research.sorosim_s56_refinement import initialize,finish,plan
from tests.research.sorosim_s5t_pilot import sealed
from tools.research import core,analysis
from tools.research.state import state,save,guard
from tools.state_io import atomic_json,read
from extensions.tendon_family.sorosim_codesign import integrated_control_source

ROOT=Path(__file__).resolve().parents[2]


def point_source(host,result,checkpoints):
    save(host,checkpoints,'imported_exact_optimizer_checkpoint')
    return save(host,dict(source_kind='raw_nlp_point',trajectory=result['trajectory'],
        optimizer_iterate=checkpoints['optimizer_iterate'],original_checkpoint=result['checkpoint_reference'],
        same_as_selected_trajectory=result['mathematical_facts']['kkt']['same_as_selected_trajectory'],
        regular_local_branch_verified=False),'exact_raw_optimizer_point')


def diagnose(host,candidate,warm,point,trajectory,key):
    definition=trajectory['objective_definition']
    arguments=dict(candidate=candidate,substeps=trajectory['substeps'],
        initialization='saved_candidate_controls',warm_source=warm,check_only=True,
        diagnostic_mode='regularity',diagnostic_source=point,
        **{k:definition[k] for k in ('objective_mode','position_weight','speed_weight','secondary_coefficient')})
    result=core.dispatch(host,plan('mechanics',mechanics=arguments),key)['result']
    value=host.store.artifact(result['reference'])
    value['kkt']=dict(value.get('kkt',{}),same_as_selected_trajectory=host.store.artifact(point)['same_as_selected_trajectory'])
    return result['reference'],value


def recover_sparse_diagnostic():
    host,candidate,_=initialize('s5t2_diagnostic_recovery')
    parent=read(ROOT/'evidence/sorosim_s5t2/summary.json')
    codesign=read(ROOT/'evidence/sorosim_s56/codesign/summary.json')
    with tarfile.open(ROOT/'evidence/sorosim_s56/codesign/study/immutable_artifacts.tar.gz') as archive:
        controls=integrated_control_source(sealed(archive,codesign['optimization']),sealed(archive,codesign['validation']))
    warm=save(host,controls,'versioned_complete_control_initialization')
    with tarfile.open(ROOT/'evidence/sorosim_s5t2/study/immutable_artifacts.tar.gz') as archive:
        base=sealed(archive,parent['secondary_base']['result'])
        checkpoints=sealed(archive,base['checkpoint_reference'])
        replay=sealed(archive,parent['secondary_base']['replay'])
    point=point_source(host,base,checkpoints)
    ref,result=diagnose(host,candidate,warm,point,base['trajectory'],'s5t2-recover-sparse-json')
    if result.get('status')!='computed':raise ValueError('READ_ONLY_RECOVERY_FAILED_PRESERVE_ATTEMPT')
    summary=dict(stage='S5-T2 sparse JSON recovery',source_freeze=state(host)['freeze'],
        parent='evidence/sorosim_s5t2/summary.json',original_failure=parent['secondary_base']['regularity'],
        diagnostic=ref,qualification=analysis.kkt_reliability(result['kkt'],result,replay['mathematical_facts']),
        costs=dict(new_full_nlp=0,new_diagnostics=state(host)['mathematical_evaluations'],
            cumulative_phase_diagnostics=parent['costs']['mathematical_evaluations']+state(host)['mathematical_evaluations'],
            numerical_s=state(host)['numerical_s'],physical_launches=0,ppo_actions=0,provider_requests=0))
    finish(host,summary,'evidence/sorosim_s5t2/diagnostic_recovery')
    print(json.dumps(summary),flush=True)


def run(diagnostics_only=False):
    host,candidate,warm=initialize('s5t2');historical=[]
    index=read(ROOT/'evidence/sorosim_s55/p3_p4_optimality.json')
    with tarfile.open(ROOT/'evidence/sorosim_s55/optimality_study/immutable_artifacts.tar.gz') as archive:
        for number in (1,2):
            old=sealed(archive,dict(artifact_id=index['raw_artifact_ids'][f'solve_{number}']))
            checkpoint=sealed(archive,old['checkpoint_reference'])
            point=point_source(host,old,checkpoint)
            ref,result=diagnose(host,candidate,warm,point,old['trajectory'],f's5t2-historical-{number}')
            replay=sealed(archive,dict(artifact_id=index['raw_artifact_ids'][f'replay_{number}']))
            qualification=analysis.kkt_reliability(result.get('kkt',{}),result,replay['mathematical_facts'])
            historical.append(dict(source=index['raw_artifact_ids'][f'solve_{number}'],
                diagnostic=ref,qualification=qualification))
    atomic_json(host.store.root/'historical_diagnostics.json',historical)
    if diagnostics_only:
        print(json.dumps(historical),flush=True);return
    # The feasibility value is flat at zero. Test a different, explicitly named value.
    codesign=read(ROOT/'evidence/sorosim_s56/codesign/summary.json')
    with tarfile.open(ROOT/'evidence/sorosim_s56/codesign/study/immutable_artifacts.tar.gz') as archive:
        source=integrated_control_source(sealed(archive,codesign['optimization']),sealed(archive,codesign['validation']))
    control_source=save(host,source,'imported_P2_control_only_initialization')
    solved=core.dispatch(host,plan('mechanics',mechanics=dict(candidate=candidate,substeps=4,
        initialization='saved_candidate_controls',warm_source=control_source,
        objective_mode='task_feasible_effort',secondary_coefficient=1.,max_iterations=60)),
        's5t2-secondary-base')['result']
    base=host.store.artifact(solved['reference']);base_row=dict(result=solved['reference'],status=base['status'])
    if base.get('trajectory'):
        replay=core.dispatch(host,plan('replay',mechanics_source=solved['reference']),
            's5t2-base-independent-replay')['result']
        checkpoint=host.store.artifact(base['checkpoint_reference'])
        point=point_source(host,base,checkpoint)
        ref,result=diagnose(host,candidate,control_source,point,base['trajectory'],'s5t2-secondary-regularity')
        qualification=analysis.kkt_reliability(result.get('kkt',{}),result,replay.get('mathematical_facts',{}))
        base_row.update(replay=replay['reference'],regularity=ref,qualification=qualification,
            facts=base['mathematical_facts'])
    atomic_json(host.store.root/'partial_summary.json',dict(historical=historical,base=base_row))
    # Useful lower-level evidence, without misusing unresolved SQP multipliers.
    parameters=host.store.artifact(candidate)['parameters'];pair=[];h=.00002
    for sign in (-1,1):
        parameters=deepcopy(parameters);parameters['segments']['0']['length_m']+=sign*h
        generated=core.dispatch(host,plan('generate',generation=parameters),f's5t2-length-{sign}')['result']
        pair.append(generated['candidate'])
        parameters=host.store.artifact(candidate)['parameters']
    sensitivity=analysis.dispatch(host,dict(candidate=candidate,operation='design_sensitivity',
        operating_point='fixed_input_equilibrium',protocol=state(host)['spec']['analysis_protocol'],
        design_sensitivity=dict(variable='segments.0.length_m',step=h,minus_candidate=pair[0],plus_candidate=pair[1])),
        's5t2-fixed-input-static-sensitivity',guard=guard,origin='engineering_preflight')
    summary=dict(stage='S5-T2',source_freeze=state(host)['freeze'],candidate=candidate,
        historical=historical,secondary_base=base_row,static_sensitivity=sensitivity['reference'],
        perturbation_reoptimizations=0,full_lagrangian_sensitivity='unavailable_without_regular_local_branch',
        gradient_error_bound=None,regional_lipschitz_bound=None,descent_certificate='unavailable',
        conditional_descent='W(d+Delta)-W(d) <= s_hat^T Delta + delta_s ||Delta|| + L/2 ||Delta||^2 only under differentiable branch, valid gradient-error bound and regional Lipschitz assumptions; strict negativity implies branch-local mathematical descent',
        costs=dict(full_nlp=state(host)['offline_nlp'],mathematical_evaluations=state(host)['mathematical_evaluations'],
            independent_replays=state(host)['bdf_replays'],numerical_s=state(host)['numerical_s'],
            physical_launches=0,ppo_actions=0,provider_requests=0))
    finish(host,summary,'evidence/sorosim_s5t2')
    print(json.dumps(dict(costs=summary['costs'],historical=historical,base=base_row.get('qualification'))),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--diagnostics-only',action='store_true')
    parser.add_argument('--recover-sparse-diagnostic',action='store_true');args=parser.parse_args()
    if args.recover_sparse_diagnostic:recover_sparse_diagnostic()
    else:run(args.diagnostics_only)
