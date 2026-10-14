"""Stage-separated delivery from fc1012's existing immutable Store and exporter."""
import hashlib
import json
import tarfile
import time
import numpy as np
from tools.research import core as core
from tools.fixed_task_milestone import host
from tools.numerical_repair_delivery import split_archive
from extensions.tendon_family.control_evidence import ControlEvidence


def summary(h):
    s=core.state(h);mechanics=[];physical=[];groups={};reader=ControlEvidence(h.store)
    for ref in s['mechanics_results']:
        v=h.store.artifact(ref)
        row=dict(reference=ref,**{k:v.get(k) for k in ('operation','status','execution_id','charged_numerical_s',
            'source_mechanics','termination_reason','iterations','hard_max_normalized_violation',
            'original_task_feasible','relaxed_nlp_feasible','slack_values','trajectory_metrics','replay','trajectory_reference','checkpoint_reference')})
        if v.get('candidate'):row['numerical_configuration']={k:v['candidate'].get(k) for k in ('d','lengths_m','substeps','interval_substeps','integration_method')}
        if v.get('rollout'):row.update(numerical_configuration={k:v.get(k) for k in ('substeps','interval_substeps','method')},metrics=v.get('metrics'))
        mechanics.append(row)
    locals=[]
    for ref in s.get('diagnostics',[]):
        for v in h.store.artifact(ref)['rows']:
            locals.append(dict(reference=ref,execution_id=v['execution_id'],source_update_id=v['source_update_id'],mode=v.get('mode'),
                cost_s=v['charged_numerical_s'],solver={k:v.get('diagnostics',{}).get(k) for k in ('iterations','return_status','initial_objective','returned_iterate_objective','selected_feasible_iteration','construction_s','solve_s','validation_s')},
                verification={k:v.get('verification',{}).get(k) for k in ('feasible','objective','scaled_violation')},
                exact_initialized_vector_equal=v.get('exact_initialized_vector_equal'),
                plans={name:{k:z for k,z in row.items() if k not in ('times_s','position_error_m','speed_m_s')} for name,row in v.get('task_plans',{}).items()}))
    for ref in s['results']:
        v=h.store.artifact(ref);p=v.get('profile') or {};obs=[];motion=[];source=None
        if v.get('execution_id') and v['status']=='evaluated':
            source=reader.resolve(v['execution_id']);obs=reader.read_file(source,'controller_observations.json',[])
            motion=h.store.artifact(p['motion'])
        row=dict(reference=ref,execution_id=v.get('execution_id'),role=v['role'],status=v['status'],candidate=v['candidate'],
            selected_execution=v.get('selected_execution'),profile_identity=v['profile_identity'],acceptance=v.get('acceptance'),
            numerical_s=v['numerical_s'],complete_update_records=sum('complete_update_record' in o for o in obs),
            controller_evidence={k:p.get(k) for k in ('accepted_plans','accepted_noninitialization_plans','initialization_selected','solver_error_count',
                'unusable_plans','raw_termination_counts','one_step_prediction_summary','valid_complete_execution')},
            observed_iterations=[o.get('complete_update_record',{}).get('diagnostics',{}).get('iterations') for o in obs],
            holding_predictions=[dict(update_time_s=o['time_s'],prediction_time_s=r['time_s'],speed_m_s=float(np.linalg.norm(r['tip_velocity_m_s'])))
                for o in obs if (r:=o.get('one_step_prediction')) and .30-1e-9<=r['time_s']<=.35+1e-9],
            task_slacks='No NMPC slack variables; speed objective is soft and actual violations remain task failures',source=source)
        physical.append(row);groups.setdefault((v['candidate']['artifact_id'],v['profile_identity']),[]).append((row,obs,motion))
    comparisons=[]
    for group in groups.values():
        if len(group)<2:continue
        a,b=group[-2:];ua=np.asarray([o['actual_tension_n'] for o in a[1]]);ub=np.asarray([o['actual_tension_n'] for o in b[1]])
        pa=np.asarray([m['tip_position_m'] for m in a[2]]);pb=np.asarray([m['tip_position_m'] for m in b[2]])
        va=np.asarray([m['tip_velocity_m_s'] for m in a[2]]);vb=np.asarray([m['tip_velocity_m_s'] for m in b[2]])
        comparisons.append(dict(executions=[a[0]['reference'],b[0]['reference']],
            command_max_difference_n=float(abs(ua-ub).max()) if ua.shape==ub.shape and ua.size else None,
            world_position_max_vector_difference_m=float(np.linalg.norm(pa-pb,axis=1).max()) if pa.shape==pb.shape and pa.size else None,
            world_velocity_max_vector_difference_m_s=float(np.linalg.norm(va-vb,axis=1).max()) if va.shape==vb.shape and va.size else None,
            qualification='Two observed fresh executions of this frozen configuration and original state; general robustness unverified'))
    solves=[r for r in mechanics if r['operation']=='solve' and r.get('trajectory_reference')]
    verifications=[r for r in mechanics if r.get('source_mechanics') in [v['reference'] for v in solves] and r.get('replay')]
    numerical=any(r.get('hard_max_normalized_violation') is not None and r['hard_max_normalized_violation']<=1e-5 for r in solves)
    independent=any(r['replay']['original_task_acceptance']['accepted'] for r in verifications)
    consistent=any(r['replay']['integration_consistency']['passed'] for r in verifications)
    jointly_verified=any(r['replay']['gates_passed'] and next(v for v in solves if v['reference']==r['source_mechanics']).get('original_task_feasible')
        and next(v for v in solves if v['reference']==r['source_mechanics'])['hard_max_normalized_violation']<=1e-5 for r in verifications)
    accepted=[r for r in physical if (r.get('acceptance') or {}).get('accepted')]
    repeated=any(r['role']=='engineering_repetition' and r.get('selected_execution') in [a['reference'] for a in accepted] for r in accepted)
    resources=dict(application_model_requests=h.store.remaining()['used']['model_calls'],standalone_controller_solves=s['local_solves'],
        standalone_controller_s=s['local_solve_s'],independent_integration_configurations=s['bdf_replays'],offline_attempts=s['offline_nlp'],
        full_mujoco_execution_starts=h.store.remaining()['used']['backend_solves'],charged_numerical_s=s['numerical_s'],
        internal_closed_loop_updates=sum(len(g[1]) for group in groups.values() for g in group),
        activity_elapsed_s=time.time()-s['started_unix'],activity_as_of_unix=time.time(),ceilings=s['spec']['budgets'])
    return dict(schema='fixed_task_scientific_summary_v1',study_id=h.run_id,status=s['research_status'],started_unix=s['started_unix'],
        implementation_binding=s['freeze'],specification=s['spec'],selected_recipe=s['profile']['recipe'],profile_identity=s['profile']['identity'],
        source_binding=s.get('physical_numerical_binding'),offline_onset_diagnosis=s.get('offline_diagnosis'),
        stages=dict(offline_numerical_feasibility=numerical,independent_integration_original_task_acceptance=independent,
            all_node_consistency=consistent,accepted_offline_candidate=jointly_verified,full_feedback_original_task_acceptance=bool(accepted),
            independent_repetition=repeated,experience_retrieval_readiness=bool(s.get('experience_engineering_check'))),
        joint_chain_completed=bool(jointly_verified and repeated),local_diagnostics=locals,mechanics=mechanics,physical=physical,
        confirmation_comparisons=comparisons,cost_estimates=s.get('cost_estimates',[]),
        experience_engineering_check=s.get('experience_engineering_check'),resources=resources,
        handoff='Fixed structure only; current goal NMPC uses measured feedback and original initial-state pretension guess. Offline tensions are retained as evidence.',
        limitations=['Iteration-cap feasibility does not establish optimizer convergence.','Original sampled task is not a continuous-time guarantee.',
            'Independent BDF validates the reduced model, not MuJoCo or hardware.','Engineering retrieval proves exact read/disposition wiring; no LLM reuse or research savings demonstrated.'])


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    h=host();s=core.state(h)
    if s['pending']:raise ValueError('RECOVER_PENDING_BEFORE_DELIVERY')
    if args.seal and s['research_status']!='stopped':
        core.dispatch(h,dict(action='stop',supporting_evidence=[*s['results'],*s['mechanics_results']],
            **{k:'Bounded fixed-structure milestone complete or stopped with separately supported stage outcomes; no new research request.'
                for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')}),
            'engineering-fixed-task-stop',origin='engineering')
    value=summary(h);out=core.ROOT/s['spec']['evidence_destination'];out.mkdir(parents=True,exist_ok=True)
    core.atomic_json(out/'scientific_summary.json',value)
    if args.seal:
        core.export(h)
        manifest=core.read(out/'archive_manifest.json')
        with (out/'immutable_artifacts.tar.gz').open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=manifest['archive_sha256']:raise ValueError('ARCHIVE_HASH_MISMATCH')
        with tarfile.open(out/'immutable_artifacts.tar.gz') as archive:
            for member in archive:
                body=archive.extractfile(member).read()
                if hashlib.sha256(body).hexdigest()!=member.name.split('/')[-1].split('.')[0]:raise ValueError('ARCHIVE_MEMBER_HASH_MISMATCH')
        split_archive(out)
        core.atomic_json(out/'verification.json',dict(archive_members_verified=len(manifest['members']),archive_sha256=manifest['archive_sha256'],
            provider_requests=0,checks='Focused regression commands and results recorded in completion report'))
    print(json.dumps(dict(stages=value['stages'],resources=value['resources']),ensure_ascii=True))


if __name__=='__main__':main()
