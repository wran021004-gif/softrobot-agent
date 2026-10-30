"""Read-only comparison of the already completed V0 Replay and saved G3 samples."""
import json,sqlite3
from pathlib import Path
import numpy as np
from tools.research.config import ROOT
from tools.state_io import atomic_json

def open_readonly(path):
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
    return db
def artifact(db,ref):
    sha=ref if isinstance(ref,str) else ref['artifact_id']
    return json.loads(db.execute('select body from artifacts where id=?',(sha,)).fetchone()[0])
oldpath=ROOT.parent/'softrobot-g3/runs/research/p63g3-m3-action-handoff-sol-20261030/platform.sqlite'
vpath=ROOT/'runs/research/p63v0-g3-best-independent-replay-20261030/platform.sqlite'
stamps=[(p.stat().st_size,p.stat().st_mtime_ns) for p in (oldpath,vpath)]
old,validation=open_readonly(oldpath),open_readonly(vpath)
vstate=json.loads(validation.execute('select state from sessions').fetchone()[0])
assert vstate['research_status']=='stopped' and len(vstate['physical_replays'])==1
result=artifact(validation,vstate['physical_replays'][0]);raw=artifact(validation,result['raw_reference'])
math=artifact(old,'536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6')
control=artifact(old,'39084ae2f79becfac990df5b9f65d71d67bbf9ed809dc231099a217fe3f00449')
bound_control=artifact(validation,result['source_reference'])
assert bound_control['trajectory']==control['trajectory']
pred=math['native_dynamics']['optimization']['best']['outputs'];samples=raw['samples']
t=np.array([x['time_s'] for x in samples]);pt=np.array(pred['times_s'])
aligned=len(t)==len(pt) and np.max(np.abs(t-pt))<=1e-12
assert aligned,dict(physical_samples=len(t),mathematical_samples=len(pt))
dp=np.array([x['tip_m'] for x in samples])-np.asarray(pred['tip_positions_m'])
dv=np.array([x['tip_velocity_m_s'] for x in samples])-np.asarray(pred['tip_velocities_m_s'])
actual=np.array([x['actual_tension_n'] for x in samples])
expected=np.asarray(pred['actual_tensions_n'])
if actual.shape==(len(t),expected.shape[1]) and expected.shape[0]==len(t)-1:
    actual=actual[1:]  # Original input arrays index intervals; physical sample k is post-step.
assert actual.shape==expected.shape,(actual.shape,expected.shape)
a=result['acceptance']
summary=dict(schema='p63v0_saved_sample_comparison_v1',decision_owner='Operator',new_physics_runs=0,new_provider_requests=0,
    independent_evaluation_classification='independent_pass' if a['accepted'] else 'valid_failure' if a['status']=='valid_failure' else 'invalid_or_incomplete',
    result_reference=vstate['physical_replays'][0],g3_candidate=math['candidate'],
    g3_math_reference=dict(artifact_id='536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6',media_type='application/json'),
    original_math_source='536e97dd81f7f1df4e564f6c44b90f75261197137817d25f7df728fa364dcfe6/native_dynamics/optimization/best/outputs',
    comparison_status='aligned_saved_trajectories',samples=len(t),maximum_time_difference_s=float(np.max(np.abs(t-pt))),
    maximum_position_difference_m=float(np.max(np.linalg.norm(dp,axis=1))),
    maximum_velocity_difference_m_s=float(np.max(np.linalg.norm(dv,axis=1))),
    maximum_actual_tension_difference_n=float(np.max(np.abs(actual-expected))),
    physical_metrics=a['metrics'],mathematical_metrics=math['nonlinear_capability']['best_metrics'],
    original_dispatch_comparison=result['comparison'],
    comparison_note='The original control source omitted mathematical_outputs, so dispatch comparison was unavailable. This read-only comparison resolves it from the original mathematical artifact without reintegration or changing either Store.',
    acceptance_predicates_unchanged=True,main_autonomous_select=False)
assert stamps==[(p.stat().st_size,p.stat().st_mtime_ns) for p in (oldpath,vpath)]
atomic_json(ROOT/'docs/research/p63v0_comparison_audit.json',summary)
print(json.dumps({k:v for k,v in summary.items() if k not in ('original_dispatch_comparison','mathematical_metrics')},indent=2))
