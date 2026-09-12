"""One frozen parent campaign; finite stages, persisted decisions and child runs."""
import gzip
import json
import math
from pathlib import Path
import random
import subprocess
import sys
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.closeout_authority import AUTH, POLICY, STAGES, FEEDBACK
from tools.closeout_state import CampaignState, read, digest, verify_run, resume_artifacts, atomic_json
from tools.experiment_policy_tools import validate_experiment_policy
from tools.harness import _snapshot_sources
from tools.pcc_math import analytic_target_matching_length
from tools.spec_tools import ROOT

REGISTRY=ROOT/'runs/round3_closeout_campaign.json'


def make_plan():
    exp=validate_experiment_policy(ROOT/POLICY); base=exp.baseline.model_dump()
    analytic=analytic_target_matching_length(exp.resolved.task.target_m)['total_length_m']
    def design(l,r,n):
        return {**base,'total_length_m':l,'tendon_routing_radius_m':r,'tendon_count':n}
    refs=[base,design(.29,.018,8),design(analytic,.015,4),design(.29,.018,4)]
    candidates=[design(l,.018,8) for l in (.282,.286,.294,.30,analytic,.32)]
    candidates += [design(.29,r,n) for r,n in ((.006,8),(.012,8),(.018,3),(.018,5),(.015,6),(.015,7))]
    rng=random.Random(17)
    candidates += [design(round(rng.uniform(.282,.32),9),round(rng.uniform(.008,.018),9),rng.randint(3,8)) for _ in range(4)]
    assert len({digest(d) for d in candidates})==16
    for d in refs+candidates: exp.validate_candidate(d)
    files={}
    for folder in ('tools','controllers','schemas','metrics','matlab','physics_contracts','capabilities','tasks','configs','benchmarks','examples'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py','.m','.yaml','.xml','.md'):
                files[path.relative_to(ROOT).as_posix()]=file_hash(path)
    from importlib.metadata import version
    versions={p:version(p) for p in ('numpy','mujoco','matlabengine','pydantic','PyYAML')}
    execution=dict(sources=files,versions=versions,python=sys.version,policy_hash=exp.policy_hash)
    return dict(schema_version=1,policy_source=POLICY,authorization_source=AUTH,seed=17,stage_budgets=STAGES,
        evaluation_budget=48,feedback_parameters=FEEDBACK,reference_designs=refs,search_candidates=candidates,
        execution=execution,execution_fingerprint=digest(execution),
        initial_state='Frozen MjData defaults, zero hinge qpos/qvel, no warm-start mutation; run seed remains configs/run.yaml',
        generation='A: baseline/history best/analytic/representative. B: 12 explicit representatives + 4 Random(17) samples, exact DesignSpec digest dedup.',
        ranking='Finite canonical Euclidean error ascending, then stable attempt_id. Model ranked separately; never rank runtime failures.',
        B_selection='Best M1, minimum radius, minimum tendon count, then best remaining M1; dedup before taking four. SCREENING failure eligible.',
        C_selection='Baseline and best C1 after B required; then historical best and analytic, exact design dedup, <=4 C2.',
        D_rules=dict(HARD='Exclude explicitly HARD-rejected candidates; next legal fixed neighbor',
            TOOL_FAILURE='Keep failed attempt, retry once under E with retry_of, never use as design score',
            TASK_FAILED='Read canonical incumbents, C1/C2 pairs and saved diagnostics; center the neighborhood on the best actual design/controller, then select model-best eligible neighbor and evaluate both C1 and C2',
            neighbors=[['total_length_m',-.004],['total_length_m',.004],['tendon_routing_radius_m',-.002],['tendon_count',-1]],
            clipping='Clip into policy bounds, round length/radius to 12 decimal places; exact DesignSpec dedup against prior MuJoCo designs and prior D screening. Previously B-screened models may be reused, without expanding the fixed four-neighbor list',
            stop='After required C pairs: canonical success, no new legal neighbors, or 2 rounds; no extra search for unused budget'),
        E_reproduction=dict(selection='global best observed after D',atol=1e-9,rtol=1e-9,
            fields=['tip_position_m','final_tendon_lengths_m','actuator_force','qpos','qvel','trajectory']),
        scientific_status='SIM_TO_SIM / UNCALIBRATED_LEGACY_SURROGATE',failure_attribution='UNKNOWN')


def history_index():
    sources=['20260912T065852_959860Z_ac884a29','20260912T065938_430868Z_300d5612']
    result=[]
    for identity in sources:
        path=ROOT/'runs'/identity
        row={'run_id':identity,'cache_eligible':False,'cache_invalidation_reason':'Current execution source revision differs; historical context only, necessary controls rerun in A'}
        if not (path/'run.json').exists():
            row['evidence_status']='REPORT_ONLY'
        else:
            try:
                manifest=verify_run(path)
                actual=read(path/'mujoco_result.json')['metrics']; task=read(path/'task.yaml') if False else None
                row.update(evidence_status='VERIFIED_LOCAL_RAW',run_manifest_hash=file_hash(path/'run.json'),
                    canonical_error_m=actual['position_error_m'],source_hashes=manifest['source_hashes'])
            except Exception as exc:
                row.update(evidence_status='INVALID_EVIDENCE',reason=str(exc))
        result.append(row)
    return result


def execute_attempt(state,stage,design,fidelity,controller='C1',*,force=False,retry_of=None):
    key=state.key(design,fidelity,controller)
    if not force:
        cached=state.cached(key)
        if cached: return cached
    a=state.reserve(stage,design,fidelity,controller,retry_of)
    request=dict(design=design,fidelity=fidelity,controller=controller,parent_id=state.run.path.name,
        attempt_id=a['attempt_id'],run_root=str(state.run.path.parent),policy=str(ROOT/POLICY))
    state.run.save(a['attempt_id']+'_request.json',request)
    command=[sys.executable,str(ROOT/'examples/run_round3_closeout.py'),'worker',str(state.run.path/a['attempt_id'])]
    print(stage,a['attempt_id'],fidelity,controller,design['total_length_m'],design['tendon_routing_radius_m'],design['tendon_count'],flush=True)
    try:
        worker=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=180)
        state.run.save(a['attempt_id']+'_worker_log.json',dict(returncode=worker.returncode,stdout=worker.stdout,stderr=worker.stderr))
        result=read(state.run.path/(a['attempt_id']+'_worker_result.json'))
        manifest=verify_run(state.run.path.parent/result['run_id'],result['run_manifest_hash'])
        a.update(result)
        child=state.run.path.parent/a['run_id']
        def artifact(name): return read(child/name) if (child/name).exists() else {}
        actual=artifact('mujoco_result.json').get('metrics',{})
        model=artifact('model_result.json').get('metrics',{})
        events=read(child/'trace.jsonl') if False else [json.loads(line) for line in (child/'trace.jsonl').read_text().splitlines()]
        calls={name:sum(e['event_type']=='TOOL_STARTED' and e['operation']==name for e in events)
            for name in ('analyze_workspace','plan_pcc_reach','pcc_centerline','compile_mujoco','run_task')}
        state.complete(a,dict(status='completed' if manifest['final_status'] in ('PASS','TASK_FAILED','MODEL_ONLY','DESIGN_INFEASIBLE') else 'failed',
            canonical_task_status='PASS' if actual.get('task_success') else 'TASK_FAILED' if 'task_success' in actual else 'NOT_RUN',
            canonical_error_m=actual.get('position_error_m'),model_error_m=model.get('predicted_position_error_m'),
            result_status=manifest['final_status'],backend_calls=calls,backend_started=bool(calls['run_task']),
            diagnostics=artifact('diagnostic_summary.json'),physics_profile='legacy_v1_surrogate',evidence_level='SIM_TO_SIM',
            robot_ir_hash=manifest['robot_ir_hash']))
    except Exception as exc:
        state.complete(a,dict(status='failed',error=repr(exc),canonical_task_status='NOT_RUN'))
    if a['status']=='failed' and stage!='E':
        return execute_attempt(state,'E',design,fidelity,controller,force=True,retry_of=a['attempt_id']) if fidelity=='MUJOCO' else a
    return a


def worker(prefix):
    from tools.harness import run_reach
    prefix=Path(prefix); request=read(str(prefix)+'_request.json')
    from tools.spec_tools import load_yaml
    design_path=prefix.with_name(prefix.name+'_design.yaml')
    import yaml
    design_path.write_text(yaml.safe_dump(request['design']),encoding='utf-8')
    child=run_reach(design_path=design_path,run_root=Path(request['run_root']),fidelity=request['fidelity'],
        experiment_path=request['policy'],controller_level=request['controller'],
        experiment_context={'parent_experiment_id':request['parent_id'],'candidate_id':request['attempt_id']})
    atomic_json(str(prefix)+'_worker_result.json',dict(run_id=child.path.name,run_manifest_hash=file_hash(child.path/'run.json')))


def ranked(rows,metric='model_error_m'):
    return sorted([r for r in rows if r.get(metric) is not None and r['status']=='completed'],key=lambda r:(r[metric],r['attempt_id']))


def unique(rows):
    result=[]; seen=set()
    for r in rows:
        key=digest(r['design'])
        if key not in seen: result.append(r); seen.add(key)
    return result


def pairs(state):
    groups={}
    for a in state.data['attempts']:
        if a.get('canonical_error_m') is not None and a['status']=='completed':
            groups.setdefault(digest(a['design']),{}).setdefault(a['controller'],a)
    return [dict(design=g['C1']['design'],C1=g['C1']['attempt_id'],C2=g['C2']['attempt_id'],
        c1_error_m=g['C1']['canonical_error_m'],c2_error_m=g['C2']['canonical_error_m'],
        improvement_m=g['C1']['canonical_error_m']-g['C2']['canonical_error_m']) for g in groups.values() if 'C1' in g and 'C2' in g]


def reproduce(state,original,repeated):
    import numpy as np
    if repeated['status']!='completed': return dict(passed=False,reason='replica failed')
    paths=[state.run.path.parent/a['run_id'] for a in (original,repeated)]
    results=[read(p/'mujoco_result.json') for p in paths]
    tolerances={k:state.plan['E_reproduction'][k] for k in ('atol','rtol')}
    deltas={}
    for field in ('tip_position_m','final_tendon_lengths_m','actuator_force'):
        arrays=[np.array(r['metrics'][field]) for r in results]
        deltas[field]=float(np.max(np.abs(arrays[0]-arrays[1])))
        if not np.allclose(*arrays,**tolerances): return dict(passed=False,field=field,deltas=deltas)
    for field in ('qpos','qvel'):
        arrays=[np.array(r['artifacts']['final_state'][field]) for r in results]
        deltas[field]=float(np.max(np.abs(arrays[0]-arrays[1])))
        if not np.allclose(*arrays,**tolerances): return dict(passed=False,field=field,deltas=deltas)
    trajectories=[json.loads(gzip.decompress((p/'trajectory.json.gz').read_bytes())) for p in paths]
    for field in ('time_s','tip_m','qpos_rad','qvel_rad_s','command_m','solver_tendon_length_m','solver_actuator_force_n','solver_contact_count'):
        arrays=[np.array([row[field] for row in t]) for t in trajectories]
        if arrays[0].shape!=arrays[1].shape or not np.allclose(*arrays,**tolerances):
            return dict(passed=False,field='trajectory.'+field)
        deltas['trajectory.'+field]=float(np.max(np.abs(arrays[0]-arrays[1])))
    return dict(passed=True,original=original['attempt_id'],replica=repeated['attempt_id'],tolerances=tolerances,max_abs_differences=deltas)


def run_campaign(plan_path=None,resume=None):
    if resume:
        run=resume_artifacts(resume); plan=read(run.path/'frozen_plan.json')
    else:
        if REGISTRY.exists(): raise ValueError('A formal campaign already exists; use resume/audit, never reset its budget')
        plan=read(plan_path)
        if plan!=make_plan(): raise ValueError('Plan/execution inputs changed; freeze the plan again before first execution')
        run=create_run(ROOT/'runs'); atomic_json(REGISTRY,{'parent_id':run.path.name,'path':str(run.path)})
        run.save('frozen_plan.json',plan); _snapshot_sources(run)
        run.save('historical_evidence.json',history_index())
    if plan['execution_fingerprint']!=make_plan()['execution_fingerprint']:
        raise ValueError('Execution revision changed; automatic mixed-revision ranking is forbidden')
    state=CampaignState(run,plan,resume=bool(resume))
    try:
        for phase in 'ABCDE':
            if phase in state.data['completed_stages']: continue
            if phase=='A':
                for d in plan['reference_designs']:
                    execute_attempt(state,'A',d,'M1'); execute_attempt(state,'A',d,'MUJOCO')
            elif phase=='B':
                rows=[execute_attempt(state,'B',d,'M1') for d in plan['search_candidates']]
                valid=ranked(rows)
                if not valid: raise ValueError('No valid model candidates')
                chosen=unique([valid[0],min(valid,key=lambda r:(r['design']['tendon_routing_radius_m'],r['attempt_id'])),
                    min(valid,key=lambda r:(r['design']['tendon_count'],r['attempt_id'])),*valid])[:4]
                state.decide('B_GEOMETRIC_DIVERSITY',[r['attempt_id']+'_result.json' for r in rows],
                    {'selected':[r['attempt_id'] for r in chosen],'controllers':['C1'],'reason':plan['B_selection']})
                for r in chosen: execute_attempt(state,'B',r['design'],'MUJOCO')
            elif phase=='C':
                best=read(run.path/'campaign_state.json')['incumbents']['C1']
                required=unique([{'design':plan['reference_designs'][0]},best,
                    {'design':plan['reference_designs'][1]},{'design':plan['reference_designs'][2]}])
                run.save('required_pairs.json',required)
                for r in required: execute_attempt(state,'C',r['design'],'MUJOCO','C2')
                run.save('control_pairs.json',pairs(state))
                if len(pairs(state))<len(required): raise ValueError('Required C1/C2 control incomplete')
            elif phase=='D':
                for iteration in range(2):
                    marker=f'improvement_{iteration}.json'
                    if (run.path/marker).exists(): continue
                    persisted=read(run.path/'campaign_state.json'); best=persisted['incumbents']['global']
                    if best['canonical_task_status']=='PASS':
                        state.data['stop_reason']='CANONICAL_SUCCESS_AFTER_REQUIRED_CONTROLS'; break
                    exp=validate_experiment_policy(ROOT/POLICY)
                    seen={digest(a['design']) for a in persisted['attempts'] if a['fidelity']=='MUJOCO' or a['stage']=='D'}
                    neighbors=[]
                    for name,delta in plan['D_rules']['neighbors']:
                        bounds=next(v for v in exp.policy.variables if v.name==name)
                        value=min(bounds.upper_bound,max(bounds.lower_bound,best['design'][name]+delta))
                        value=int(value) if name=='tendon_count' else round(value,12)
                        d={**best['design'],name:value}
                        if digest(d) not in seen:
                            exp.validate_candidate(d); neighbors.append(d); seen.add(digest(d))
                    if not neighbors:
                        state.data['stop_reason']='NO_NEW_LEGAL_NEIGHBORS'; break
                    # Copy immutable decision input: mutable state files are not evidence refs.
                    name=f'improvement_{iteration}_observations.json'
                    run.save(name,dict(incumbents=persisted['incumbents'],pairs=read(run.path/'control_pairs.json')))
                    state.decide('D_TASK_FAILED_LOCAL_NEIGHBORS',[name,best['attempt_id']+'_result.json'],
                        dict(neighbors=neighbors,reason=plan['D_rules']['TASK_FAILED']))
                    rows=[execute_attempt(state,'D',d,'M1') for d in neighbors]
                    valid=ranked(rows)
                    if not valid: state.data['stop_reason']='NO_VALID_LOCAL_MODEL'; break
                    # Selection really reads the persisted candidate results.
                    saved=[read(run.path/(r['attempt_id']+'_result.json')) for r in valid]
                    selected=ranked(saved)[0]
                    state.decide('D_MODEL_RANK_PAIRED_ACTUAL',[r['attempt_id']+'_result.json' for r in rows],
                        dict(next_design=selected['design'],controllers=['C1','C2'],before_error_m=best['canonical_error_m']))
                    evaluated=[execute_attempt(state,'D',selected['design'],'MUJOCO',c) for c in ('C1','C2')]
                    run.save(marker,dict(iteration=iteration,previous=best['attempt_id'],selected=selected['attempt_id'],
                        actual=[r['attempt_id'] for r in evaluated],before_error_m=best['canonical_error_m'],
                        incumbent_after=state.data['incumbents']['global']['attempt_id'],
                        after_error_m=state.data['incumbents']['global']['canonical_error_m']))
                    run.save('control_pairs.json',pairs(state))
                state.data.setdefault('stop_reason','TWO_IMPROVEMENT_ROUNDS_EXHAUSTED')
            else:
                best=read(run.path/'campaign_state.json')['incumbents']['global']
                state.decide('E_INDEPENDENT_REPRODUCTION',[best['attempt_id']+'_result.json'],
                    dict(design=best['design'],controller=best['controller'],tolerances=plan['E_reproduction']))
                rep=execute_attempt(state,'E',best['design'],'MUJOCO',best['controller'],force=True)
                reproduction=reproduce(state,best,rep); run.save('reproduction.json',reproduction)
                if not reproduction['passed']: raise ValueError('Numerical reproduction did not pass')
            state.data['completed_stages'].append(phase); state.save()
        summary=build_summary(state)
        run.save('closeout_summary.json',summary)
        state.data['workflow_status']='COMPLETED'; state.save()
        finalize_run(run,'PASS')
    except Exception as exc:
        state.data['workflow_status']='INCOMPLETE'; state.data['error']=repr(exc); state.save()
        run.save('campaign_error.json',dict(error=repr(exc)))
        # Leave root open for candidate-boundary recovery; never fake completion.
        raise
    print('CAMPAIGN',run.path,flush=True)
    return run.path


def build_summary(state):
    attempts=state.data['attempts']; actual=ranked(attempts,'canonical_error_m'); best=actual[0]
    base=next(a for a in actual if a['design']==state.plan['reference_designs'][0] and a['controller']=='C1')
    hist=next(a for a in actual if a['design']==state.plan['reference_designs'][1] and a['controller']=='C1')
    return dict(workflow_status='COMPLETED',canonical_task_status=best['canonical_task_status'],
        scientific_status='PHYSICS_MODEL_REFINEMENT_REQUIRED' if best['canonical_task_status']!='PASS' else 'UNCALIBRATED_SURROGATE_TASK_SUCCESS',
        failure_attribution='UNKNOWN',best=best,baseline=base,historical_best_current_revision=hist,
        best_model=ranked(attempts)[0],incumbents=state.data['incumbents'],pairs=pairs(state),
        improvement_observed=best['canonical_error_m']<hist['canonical_error_m'],
        improvement_vs_baseline_m=base['canonical_error_m']-best['canonical_error_m'],
        improvement_vs_historical_design_m=hist['canonical_error_m']-best['canonical_error_m'],
        stop_reason=state.data['stop_reason'],attempts=len(attempts),
        model_attempts=sum(a['fidelity']=='M1' for a in attempts),mujoco_route_attempts=sum(a['fidelity']=='MUJOCO' for a in attempts),
        backend_calls={name:sum(a.get('backend_calls',{}).get(name,0) for a in attempts)
            for name in ('analyze_workspace','plan_pcc_reach','pcc_centerline','compile_mujoco','run_task')},
        cache_reads=len(state.data['reuse']),retries=sum(a['retry_of'] is not None for a in attempts),
        remaining_budget=state.remaining(),execution_commit=state.run.record.git_commit,
        execution_fingerprint=state.plan['execution_fingerprint'])
