"""One Operator-owned exact G3 schedule Replay, in a separate numerical Store."""
import json,os,sqlite3
from copy import deepcopy
from pathlib import Path
from tools.platform_store import plain
from tools.research import core
from tools.research.config import ROOT
from tools.research.state import state,save,require_authorization,guard
from tools.research.design import generate_candidate,verify_candidate,full_science,final_fidelity_matches
from tools.research.physical_replay import binding,dispatch
from tools.research.contracts import PhysicalReplayRequest
from tools.research.budget import engineering_closeout
from tools.state_io import read,atomic_json,digest

RUN='p63v0-g3-best-independent-replay-20261030'
ORIGINAL=ROOT.parent/'softrobot-g3/runs/research/p63g3-m3-action-handoff-sol-20261030/platform.sqlite'
C='da1c14850fcd93aa33705f1caae54ceafd5366e9225d77d2737168fd459f2dac'
M='536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6'
U='39084ae2f79becfac990df5b9f65d71d67bbf9ed809dc231099a217fe3f00449'
if (ROOT/'runs/research'/RUN/'platform.sqlite').exists():
    raise RuntimeError('The single V0 validation already exists; recover/read it, never repeat.')
for k,v in read(ROOT/'configs/research/runtime_p63b1_sol_none.json')['threads'].items():os.environ[k]=v
stamp=lambda:dict(size=ORIGINAL.stat().st_size,mtime_ns=ORIGINAL.stat().st_mtime_ns)
before=stamp()
db=sqlite3.connect(ORIGINAL.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
art=lambda sha:json.loads(db.execute('select body from artifacts where id=?',(sha,)).fetchone()[0])
c,m,u=art(C),art(M),art(U)
old=json.loads(db.execute('select state from sessions').fetchone()[0])
ref=lambda sha:dict(artifact_id=sha,media_type='application/json')
assert old['research_status']=='stopped' and m['candidate']==ref(C) and m['control_schedule_reference']==ref(U)
assert m['status']=='computed' and m['operation']=='mujoco_nonlinear_task_capability_v1'
binding(c['configuration'],u['trajectory'],mathematical_outputs=u.get('mathematical_outputs'))
assert set(c['configuration']['policy']['discretization']['data']['cells'].values())=={12}
h=core.prepare(ROOT/'configs/research/study_p63v0_g3_best_replay.json');h.actor='operator-v0'
spec=state(h)['spec']
scope=dict(study_id=RUN,resolved_identity=spec['resolved_identity'],decision_owner='Operator',
    source_study=old['spec']['study_id'],candidate=ref(C),math_result=ref(M),control_source=ref(U),
    authorized_provider_ceiling=0,physical_replay_ceiling=1,original_store_read_only=True,
    user_request='f985cfb8-175c-48d6-a027-208747a6f60f/已粘贴的文本.txt')
authorization=save(h,dict(user_approval='Explicit V0 one-Replay authorization from current user task.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
require_authorization(h);core.bind(h,specification=spec);guard(h)
assert all(spec[k]==old['spec'][k] for k in ('canonical_task','family_space','analysis_protocol','control','fidelity_policy'))
created=generate_candidate(h,c['parameters'],dict(origin='operator_v0_exact_reconstruction',
    original_study=old['spec']['study_id'],original_candidate=ref(C),no_main_ownership=True),
    screening_fidelity=c.get('screening_fidelity'))
newref=created['candidate'];new=verify_candidate(h,newref)
equivalence=dict(scientific_configuration=full_science(new['configuration'])==full_science(c['configuration']),
    physical_design=new['physical_design_identity']==c['physical_design_identity'],
    numerical_model=new['numerical_model_identity']==c['numerical_model_identity'],
    original_full_trajectory=True,final_fidelity=final_fidelity_matches(spec,new))
assert all(equivalence.values()),equivalence
source=deepcopy(u)
source['provenance']=dict(origin='operator_v0_exact_schedule_import',original_study=old['spec']['study_id'],
    original_source=ref(U),original_mathematical_result=ref(M),original_provenance=u['provenance'],inherited_acceptance=False)
assert source['trajectory']==u['trajectory']
binding(new['configuration'],source['trajectory'],mathematical_outputs=source.get('mathematical_outputs'))
source_ref=save(h,source,'operator_v0_exact_control_source')
saved_binding=save(h,dict(original_candidate=ref(C),new_candidate=newref,original_source=ref(U),
    replay_source=source_ref,equivalence=equivalence,authorization=authorization),'operator_v0_source_binding')
result=dispatch(h,PhysicalReplayRequest(candidate=newref,source=source_ref),'v0-single-original-physical-replay')
raw=h.store.artifact(result['raw_reference']);acceptance=result['acceptance']
numeric=[]
for name,component in acceptance['components'].items():
    value,limit=component.get('value'),component.get('limit')
    if isinstance(value,(int,float)) and not isinstance(value,bool) and isinstance(limit,(int,float)) and not isinstance(limit,bool):
        numeric.append(dict(constraint=name,value=value,threshold=limit,signed_excess=value-limit,
            unit=component.get('unit'),passed=component['passed']))
category='independent_pass' if acceptance['accepted'] else 'valid_failure' if acceptance['status']=='valid_failure' else 'invalid_or_incomplete'
if not result['comparison']['aligned']:category='comparison_unresolved'
summary=dict(schema='p63v0_independent_replay_v1',study_id=RUN,decision_owner='Operator',
    classification=category,original_sources=scope,source_binding=saved_binding,equivalence=equivalence,
    result_reference=result['reference'],raw_reference=result['raw_reference'],
    evaluation_reference=result['evaluation_reference'],profile_reference=result['profile_reference'],
    acceptance=acceptance,signed_constraint_excesses=numeric,
    trajectory_comparison={k:v for k,v in result['comparison'].items() if k!='samples'},
    mathematical_metrics=m['nonlinear_capability']['best_metrics'],
    exact_source_control_rows=len(source['trajectory']['tensions_n']),
    tension_bounds_n=dict(minimum=min(map(min,source['trajectory']['tensions_n'])),maximum=max(map(max,source['trajectory']['tensions_n']))),
    boundary=result['boundary'],cost=raw.get('cost'),physics_steps=raw.get('physics_steps'),
    charged_worker_wall_s=result['charged_numerical_s'],numerical_s=state(h)['numerical_s'],
    construction_numerical_s=state(h).get('construction_numerical_s'),shared_ledger=h.store.remaining()['used'],
    original_store=dict(path=str(ORIGINAL),sqlite_mode='ro',query_only=True,before=before,after=stamp(),unchanged=before==stamp()),
    main_autonomous_select=False,threshold_or_tolerance_changed=False)
assert before==stamp() and state(h)['physical_replay_launches']==1 and h.store.remaining()['used']['model_calls']==0
engineering_closeout(h,'V0 single Operator independent validation complete; no Main SELECT or STOP claimed')
atomic_json(ROOT/'docs/research/p63v0_replay_audit.json',summary)
atomic_json(h.store.root/'v0_summary.json',summary)
print(json.dumps({k:summary[k] for k in ('classification','equivalence','signed_constraint_excesses','trajectory_comparison','charged_worker_wall_s')},indent=2))
