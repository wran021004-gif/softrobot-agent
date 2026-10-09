"""Read-only evidence export and factual V2 closeout summaries; no execution."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import importlib.metadata
from tools.state_io import atomic_json,read,digest
from tools.platform_store import Store
from tools.research_v2 import ROOT,OUT,RUN
from extensions.tendon_family import finite_templates as finite


def export():
    """Lossless original Store artifacts, including complete provider responses."""
    store=Store(RUN);folder=OUT/'store';(folder/'artifacts').mkdir(parents=True,exist_ok=True)
    with closing(store.connect(True)) as db:
        artifacts={}
        for row in db.execute('SELECT id,media,body FROM artifacts'):
            suffix='.json' if row['media']=='application/json' else '.bin'
            path=folder/'artifacts'/(row['id']+suffix)
            body=bytes(row['body']);assert hashlib.sha256(body).hexdigest()==row['id']
            if not path.exists():path.write_bytes(body)
            assert path.read_bytes()==body
            artifacts[row['id']]=dict(path=path.relative_to(OUT).as_posix(),media_type=row['media'],bytes=len(body),sha256=row['id'])
        calls=[]
        for row in db.execute('SELECT * FROM calls ORDER BY rowid'):
            record=dict(row)
            for key in ('reserved','charged','resources','receipt'):
                if record[key] is not None:record[key]=json.loads(record[key])
            calls.append(record)
        sessions={r['run_id']:store.session(r['run_id'],db) for r in db.execute('SELECT run_id FROM sessions')}
        events=[json.loads(r['body']) for r in db.execute('SELECT body FROM events ORDER BY seq')]
        result=dict(project=store.config(db),sessions=sessions,artifacts=artifacts,calls=calls,events=events,
            representation='Complete original JSON and binary artifact bytes, losslessly preserved by SHA256; original owners and execution IDs unchanged')
    atomic_json(OUT/'store_manifest.json',result)
    atomic_json(OUT/'cumulative_ledger.json',store.remaining())
    return result


def case_summary(key,manifest):
    result=read(OUT/(key+'_result.json'));joint=result['joint_acceptance']
    receipts={r['tool_id']:r for r in result['receipts']}
    store=Store(RUN)
    prepared=store.artifact(receipts['research.prepare_candidate']['output'])
    candidate=store.artifact(prepared['configuration']);inp=candidate['effective']
    profile=store.artifact(receipts['control.profile_report']['output'])['detail']
    linear=store.artifact(receipts['analysis.linearize_configuration']['output'])
    metrics=store.artifact(receipts['analysis.control_metrics']['output'])
    endpoint=store.artifact(receipts['analysis.bounded_endpoint']['output'])
    from schemas.platform import SessionInput
    dimensions=finite.dimensions(SessionInput.model_validate(inp))
    source=finite.catalog()['scientific_source']
    assert inp['task']['goal']==source['task']['goal']
    assert inp['task']['timing']==source['task']['timing']
    assert inp['task']['environment']==source['task']['environment']
    assert inp['policy']['controller']['parameters']==source['policy']['controller']['parameters']
    assert inp['seed']==source['seed']==17
    assert profile['configuration']==prepared['configuration']
    assert joint['configuration']==prepared['configuration']
    assert joint['execution_id']==receipts['simulation.run']['execution_id']
    assert joint['status'] in ('accepted','valid_failure')
    assert joint['components']['evaluation_validity']['passed'] is True
    assert joint['components']['execution_complete']['passed'] is True
    assert joint['components']['holding_coverage']['passed'] is True
    initial=finite.semantic_initialization(inp['robot']['structure']['data'],inp['policy']['discretization']['data'],
        inp['policy']['controller']['parameters']['data']['recipe']['basis'])
    from extensions.tendon_family.compiler import quat,resolve
    mount=inp['task']['environment']['data']['mount']
    import numpy as np
    initial['initial_tip_pose_base_m']=initial.pop('initial_tip_pose')
    initial['initial_tip_pose_world_m']=(quat(mount['quaternion_wxyz'])@initial['initial_tip_pose_base_m']+mount['position_m']).tolist()
    physics=resolve(inp['robot']['structure']['data'],inp['policy']['discretization']['data'])
    out=dict(template=key,candidate_id=candidate['candidate_id'],owner_run_id='mainline3-v2',
        configuration=prepared['configuration'],execution_id=receipts['simulation.run']['execution_id'],
        receipts=receipts,dimensions=dimensions,initialization=initial,
        resource_model=dict(flexible_segments=len([c for c in inp['robot']['structure']['data']['components'] if c['kind']=='flexible_segment']),
            components=len(physics['entity_map']),backend_cells=sum(inp['policy']['discretization']['data']['cells'].values()),
            total_mass_kg=sum(p['mass_kg'] for p in physics['parts']),
            total_tendon_force_capacity_n=sum(dimensions['force_limits_n']),
            added_physics='2 g split guide and declared inertia; preserved taper, flexible length and 24 cell distribution' if key in ('T2','T3') else 'Two additional independent tendon/actuator declarations; new quarter-turn layout'),
        mathematical_preparation=dict(linearization=linear,control_metrics=metrics,endpoint=endpoint,
            operating_points=[dict(name=r.get('point',{}).get('name',r.get('name')),
                available=r.get('point',{}).get('available',r.get('available')),
                construction_method=r.get('construction',{}).get('method')) for r in linear['records'][1:]],
            bounded_endpoint_status=[dict(point=r['operating_point']['name'],
                position=r['position_only']['status'],position_and_braking=r['position_and_braking']['status'])
                for r in endpoint['records']],
            interpretation='Unavailable equilibrium or inconclusive local diagnostics are not physical infeasibility proofs; full candidate execution is reported independently.'),
        joint_acceptance=joint,
        profile_metrics={k:profile.get(k) for k in ('valid_complete_execution','solver_status','official_task_success','terminal_error_m',
            'sampled_settling','updates','solver_error_count','solver_failure_flags','hold_last_responses',
            'accepted_noninitialization_plans','initialization_selected','force_bound_violation_n',
            'deadline_misses','mean_update_s','graph_construction_s','solver_construction_s','real_time_demonstrated')},
        unchanged_scientific_conditions=True,
        limitations=finite.catalog()['unsupported'],
        incumbent_promoted=False,performance_ablation_claim=False)
    atomic_json(OUT/(key+'_summary.json'),out)
    return out


def summarize():
    manifest=export();summaries={k:case_summary(k,manifest) for k in ('T1','T2','T3')}
    native=read(OUT/'native_result.json');report=native['state'].get('v2_capability_report')
    assert native['status']=='stopped' and report
    requests=[]
    store=Store(RUN)
    for event in manifest['events']:
        if event['kind']=='model_raw_response':
            raw=store.artifact(event['outputs'][0])
            response=raw.get('raw',raw)
            requests.append(dict(run_id=event['run_id'],request_id=event['request_id'],execution_id=event['execution_id'],
                response=event['outputs'][0],usage=response.get('usage'),finish_reason=response.get('choices',[{}])[0].get('finish_reason')))
    assert len({(r['run_id'],r['request_id']) for r in requests})==len(requests)
    ledger=read(OUT/'cumulative_ledger.json')
    known=[r['usage'] for r in requests if r.get('usage')]
    tokens={k:sum(r.get(k,0) for r in known) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    mathematics=[r for r in manifest['calls'] if r.get('receipt') and r['receipt']['tool_id'].startswith('analysis.')]
    backend=[r for r in manifest['calls'] if r.get('receipt') and r['receipt']['tool_id']=='simulation.run']
    preservation={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for path,sha in read(OUT/'preserved_history.json').items()}
    assert all(preservation.values())
    resource=dict(provider_requests=ledger['used']['model_calls'],tokens=tokens,
        response_coverage=dict(saved_complete_responses=len(requests),known_usage=len(known)),
        public_operations=ledger['used']['tool_calls'],mathematical_operations=len(mathematics),backend_attempts=len(backend),
        actual_elapsed_s=time.time()-read(OUT/'activity.json')['started_unix'],
        ledger_wall_s=ledger['used']['wall_s'],provider_monetary_cost=None,
        engineering_interventions=read(OUT/'activity.json')['engineering_interventions'])
    assert resource['provider_requests']<=40 and resource['public_operations']<=1024 and resource['mathematical_operations']<=32 and resource['backend_attempts']<=6
    assert resource['actual_elapsed_s']<43200
    atomic_json(OUT/'provider_usage.json',dict(requests=requests,totals=tokens,monetary_cost=None))
    atomic_json(OUT/'preservation_review.json',dict(passed=True,sha256_unchanged=preservation))
    result=dict(status='V2_completed',templates=list(finite.catalog()['templates']),
        builder='candidate.family@2.0.0',controller='controller.gvs_nmpc@10.0.0',
        results={k:dict(configuration=s['configuration'],execution_id=s['execution_id'],status=s['joint_acceptance']['status'],
            reach=s['joint_acceptance']['components']['evaluator:task_bound'],
            holding_position=s['joint_acceptance']['components']['holding_position'],
            holding_speed=s['joint_acceptance']['components']['holding_speed'],
            dimensions=s['dimensions']['dimensions'],timing=s['joint_acceptance']['timing']) for k,s in summaries.items()},
        baseline=dict(source_configuration=finite.catalog()['t0_configuration'],
            historical_execution=finite.catalog()['t0_backend_execution'],new_execution=False,
            reuse_basis='Exact T0 robot, task, seed, mesh and recipe preserved in offline V2 construction. Version 10 inherits the same V7 controller class/stopping behavior; no shared scientific behavior change requires a T0 rerun.'),
        native_capability_use=report,resource_use=resource,
        focused_checks=read(OUT/'focused_checks.json'),remaining_blockers=[],
        mainline4=dict(starting_template='T1',entry='python -m tools.research_v2_entry --prepare --template T1',
            scope='Start from the finite structural choices and exact evidence; no new incumbent or optimization gains claimed'))
    atomic_json(OUT/'completion.json',result)
    return result


if __name__=='__main__':
    print(json.dumps(summarize(),indent=2))
