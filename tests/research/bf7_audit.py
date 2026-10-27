"""Read-only BF7 evidence/cost export from the original Study Stores."""
from pathlib import Path
from copy import deepcopy
import json

from tools.platform_store import Store
from tools.research.config import ROOT, same_robot_structure
from tools.research.feedback import task_gap
from tools.research_tasks import _source_issue, _outcome_issue
from tools.state_io import read, atomic_json


def main():
    output=ROOT/'evidence/bf7_final'
    audit=dict(contract='bf7.study_evidence_audit',version='1.0.0',additional_scientific_calls=0,studies={})
    totals=dict(mathematical_evaluation_units=0,conic_solves=0,gvs_model_builds=0,native_analysis_entries=0,
        native_callback_attempts=0,native_complete_rollouts=0,native_physics_steps=0,native_worker_model_builds=0,
        independent_replays=0,independent_replay_physics_steps=0,independent_replay_model_builds=0,
        independently_accepted_replays=0,numerical_s=0.,driver_recorded_lower_bound_s=0.,compatibility_preparation_s=0.,provider_requests=0)
    matrices={};stores={};states={}
    for stage,roles in [('bf7-v1',['math','best','peer']),('bf7-r2',['math','best'])]:
        for role in roles:
            folder=ROOT/'runs'/stage/role;store=Store(folder/'private-store')
            run_id=stage+('-prescreen' if role=='math' else '-'+role)
            s=store.session(run_id)['state'];key=stage+'/'+role;stores[key]=store;states[key]=s
            assert s['research_status']=='stopped' and s['pending'] is None and not store.remaining()['occupied']
            calls=[]
            requests=dict.fromkeys(e['request_id'] for e in store.events(run_id) if e['request_id'])
            for request in requests:
                call=store.lookup(run_id,request);receipt=json.loads(call['receipt'])
                calls.append(dict(request_id=request,execution_id=call['execution_id'],status=call['status'],
                    **{k:receipt.get(k) for k in ['tool_id','tool_version','execution_status','cache_hit','charged','error','output']}))
            analyses=[]
            for reference in s['analysis_results']:
                a=store.artifact(reference)
                row=dict(reference=reference,status=a['status'],operation=a['operation'],
                    charged_analysis_evaluations=a['charged_analysis_evaluations'],charged_numerical_s=a['charged_numerical_s'])
                if a['operation']=='task_capability':
                    row.update(actual_mathematical_calls=a['actual_mathematical_calls'],
                        recorded_attempt_boundaries=a['recorded_attempt_boundaries'],recorded_return_boundaries=a['recorded_return_boundaries'])
                    totals['conic_solves']+=a['actual_mathematical_calls']['internal_conic_solves']
                    totals['gvs_model_builds']+=a['recorded_return_boundaries']['model_build']
                else:
                    progress=a.get('native_progress') or {};native=a.get('native_dynamics') or {}
                    cost=native.get('cost') or progress.get('cost') or a.get('native_diagnostic',{}).get('cost')
                    totals['native_analysis_entries']+=1;totals['native_callback_attempts']+=cost['rollouts']
                    totals['native_complete_rollouts']+=cost['rollouts'] if a['status']=='computed' else progress['completed_rollouts']
                    totals['native_physics_steps']+=cost['physics_steps'];totals['native_worker_model_builds']+=cost['model_builds']
                    row.update(cost=cost,reason=a.get('reason'),native_progress=a.get('native_progress'))
                    if native:
                        opt=native['optimization'];trajectory=native['optimized_schedule']['trajectory']
                        forces=[u for values in trajectory['tensions_n'] for u in values]
                        row.update(stop_reason=opt['stop_reason'],baseline=opt['candidates'][0]['measure'],best=opt['best']['measure'],
                            active_coefficients=opt['active_coefficients'],applied_force_range_n=[min(forces),max(forces)],
                            response_conditions=[r.get('resolved_subspace_condition') for r in opt['local_responses']])
                analyses.append(row)
            replays=[]
            for reference in s['physical_replays']:
                r=store.artifact(reference);raw=store.artifact(r['raw_reference']);cost=raw['cost']
                assert _source_issue(r['acceptance']) is None and _outcome_issue(r['acceptance']) is None
                assert raw['status']=='completed' and raw['physics_steps']==600 and len(raw['samples'])==31
                totals['independent_replays']+=1;totals['independent_replay_physics_steps']+=cost['physics_steps']
                totals['independent_replay_model_builds']+=cost['model_builds'];totals['independently_accepted_replays']+=int(r['acceptance']['accepted'])
                replays.append(dict(reference=reference,candidate=r['candidate'],raw=r['raw_reference'],evaluation=r['evaluation_reference'],
                    profile=r['profile_reference'],execution_id=r['execution_id'],acceptance=r['acceptance'],task_gap=task_gap(r),
                    cost=cost,physical_model_identity=raw['model_identity'],xml_sha256=raw['xml_sha256']))
            drivers=[]
            if role=='math':
                summary=read(folder/'summary.json');drivers.append(summary['driver_elapsed_s']);matrix=[]
                for design in summary['designs']:
                    c=store.artifact(design['candidate']);parameters=c['parameters']
                    matrix.append(dict(index=design['index'],candidate=design['candidate'],structure_summary={i:{k:v for k,v in part.items() if k in ('length_m','young_pa')} for i,part in parameters['segments'].items()},
                        shared_score=design['shared_score'],conditions=design['conditions']))
                matrices[stage]=matrix
            else:
                for name in ('initial.json','continuation.json'):
                    if not (folder/name).exists():continue
                    summary=read(folder/name);drivers.append(summary['driver_elapsed_s'])
                    if summary.get('driver_scope'):drivers.append(summary['prior_target_driver_s'])
            totals['numerical_s']+=s['numerical_s'];totals['mathematical_evaluation_units']+=s['mathematical_evaluations']
            totals['compatibility_preparation_s']+=s['compatibility_preparation_s'];totals['driver_recorded_lower_bound_s']+=sum(drivers)
            totals['provider_requests']+=store.remaining()['used']['model_calls']
            audit['studies'][key]=dict(run_id=run_id,implementation=s['freeze'],resolved_identity=s['spec']['resolved_identity'],
                research_status=s['research_status'],selected=s['selected'],final_disposition=s['final_disposition'],ledger=store.remaining(),
                numerical_s=s['numerical_s'],construction_numerical_s=s['construction_numerical_s'],
                control_initialization_s=s.get('control_initialization_s',0.),compatibility_preparation_s=s['compatibility_preparation_s'],
                mathematical_evaluations=s['mathematical_evaluations'],recorded_driver_s=sum(drivers),receipts=calls,analyses=analyses,replays=replays)
    store=stores['bf7-r2/best'];summary=read(ROOT/'runs/bf7-r2/best/initial.json');root=store.artifact(summary['candidate']);cfg=root['configuration']
    witness=dict(contract='bf7.independent_shared_structure_witness',version='1.0.0',accepted_all_three=True,joint_select=False,
        implementation=summary['implementation'],structure_candidate=summary['candidate'],generation_parameters=root['parameters'],
        physical_design_identity=root['physical_design_identity'],discretization=cfg['policy']['discretization'],
        backend=cfg['policy']['backend'],dynamics_model=cfg['policy']['dynamics_model'],
        payload=[c for c in cfg['robot']['structure']['data']['components'] if c['kind']=='payload'],conditions={})
    models=set()
    for key,row in summary['conditions'].items():
        candidate=store.artifact(row['candidate']);r=store.artifact(row['replay']);raw=store.artifact(row['raw']);a=store.artifact(row['analysis'])
        assert same_robot_structure(cfg,candidate['configuration']) and cfg['policy']['discretization']==candidate['configuration']['policy']['discretization']
        assert r['acceptance']['accepted'] and all(c['passed'] is True for c in r['acceptance']['components'].values())
        initial=a['native_dynamics']['initial_state'];assert all(v==0 for k in ['qpos_rad','qvel_rad_s'] for v in initial[k])
        source=row['initial_seed'];previous=Store(ROOT/source['store']).artifact(source['control_source'])
        assert previous['trajectory']['tensions_n']==a['native_dynamics']['original_schedule']['trajectory']['tensions_n']
        models.add(raw['model_identity'])
        witness['conditions'][key]=dict(candidate=row['candidate'],analysis=row['analysis'],replay=row['replay'],raw=row['raw'],evaluation=row['evaluation'],
            profile=row['profile'],execution_id=row['execution_id'],acceptance=row['acceptance'],native_cost=row['native_cost'],replay_cost=row['replay_cost'],
            control_source=row['control_source'],control=store.artifact(row['control_source']),initial_seed=source,
            fixed_transferred_control_measure=row['baseline'],fresh_zero_state=True,exact_failed_control_transfer_verified=True)
    assert len(models)==1 and len(witness['conditions'])==3
    witness['shared_physical_model_identity']=models.pop();witness['joint_selection_limitation']='../bf7_r2/joint_selection_limitation.json'
    totals['total_physics_steps']=totals['native_physics_steps']+totals['independent_replay_physics_steps']
    totals.update(driver_total_exact_s=None,driver_limitation='R2 best original invocation threw after its third pass at joint SELECT. Its complete entry duration was not persisted; per-target times plus closeout are retained. Total is a measured lower bound, not a fabricated exact driver time.',
        model_build_count_scope='GVS model events, Native worker cost and replay worker cost; source-binding/host compatibility preparation is separately measured in seconds.',monetary_cost=None)
    manifest=dict(benchmark_id='bf7-shared-reach-nominal-v1',version='1.0.0',status='frozen_nominal_independently_feasible_candidate',
        task_protocol='bf7_protocol_v1.json',design_and_control_protocol='bf7_r2_protocol.json',family_space='family_space_bf7_r2.json',
        explored_design_domain=dict(segment_count=2,tendon_count=6,length_bounds_m=[.10,.16],young_bounds_pa=[8e6,15e6],
            fixed='Original sections, routing, 12 cells/segment, mass/inertia/payload and backend/model.'),
        task_conditions=states['bf7-r2/best']['spec']['task_conditions'],
        physical_limits=dict(duration_s=.6,timestep_s=.001,control_period_s=.02,sample_period_s=.02,force_bounds_n=[0.,8.],payload_kg=.01,seed=17),
        independent_witness='../../evidence/bf7_final/independent_witness.json',common_structure_verified=True,joint_select=False,
        structural_advantage_established=False,
        formal_comparison_status='Not executed. A matched cold-start control comparison on the same new parameterization is still required; R2 changed structure, initial control and active basis together.',
        future_nominal_per_strategy_per_seed_budget=dict(structure_math_units=24,native_callbacks_per_target=401,independent_replays=3,physics_step_attempts=723600),
        prerequisites_for_formal_benchmark=['Version and validate exact frozen-condition fidelity admission; do not silently change these original records.',
            'Freeze identical fresh control initialization/parameterization and total construction/search/replay costs across strategies; no archived witness input as an Agent seed.',
            'Confirm a meaningful structure effect under matched control budgets; one finite failed optimization is not structural infeasibility.'])
    public=dict(contract='bf7.exploration_summary',version='1.0.0',base_commit='a1566b91a387316405bdb2fc79eb8a087ea20e8a',
        branch='research/bf7-shared-structure-benchmark',complete_shared_independent_witness=True,joint_select=False,formal_agent_comparison_executed=False,
        physical_structure={i:{k:v for k,v in part.items() if k in ('length_m','young_pa')} for i,part in witness['generation_parameters']['segments'].items()},shared_physical_model_identity=witness['shared_physical_model_identity'],
        witness_results={k:dict(native_callbacks=r['native_cost']['rollouts'],metrics=r['acceptance']['metrics'],accepted=r['acceptance']['accepted'],
            passed_components=len(r['acceptance']['components']),execution_id=r['execution_id']) for k,r in witness['conditions'].items()},
        mathematical_shared_scores={k:[r['shared_score'] for r in v] for k,v in matrices.items()},totals=totals,
        unstarted_r2_peer='Not materialized or executed after the first full shared independent witness.',additional_scientific_calls_during_audit=0,
        interpretation='Actual three-target feasibility on one structure established. Global optimality, structural causal advantage, a general speedup and hardware/repeatability are not established.')
    atomic_json(ROOT/'runs/bf7-r2/independent_witness_private.json',witness)
    published=deepcopy(witness);published.pop('generation_parameters')
    published['structure_summary']=public['physical_structure']
    published['complete_private_witness']='runs/bf7-r2/independent_witness_private.json (local, excluded from Git and future Agent seeds)'
    for row in published['conditions'].values():row.pop('control')
    atomic_json(output/'audit.json',audit);atomic_json(output/'mathematical_prescreen.json',matrices)
    atomic_json(output/'independent_witness.json',published);atomic_json(output/'summary.json',public)
    atomic_json(ROOT/'configs/research/bf7_benchmark_v1.json',manifest)
    print(json.dumps(dict(status='read_only_audit_passed',totals=totals,witness=public['witness_results']),ensure_ascii=False))


if __name__=='__main__':main()
