"""Compare saved startup evidence and locate discrepancies without repeating a run."""
import gzip
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from extensions.tendon_family.tracking import reference_at
from tools.state_io import atomic_json
out=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))

def saved(root):
    inp=read(root/'input.json');s=read(root/'summary.json')
    b=root/'sessions'/inp['run_id']/'executions'/s['execution_id']/'backend'
    return inp,json.loads(gzip.decompress((b/'trajectory.json.gz').read_bytes())),read(b/'controller_observations.json')

old,oldrows,oldo=saved(ROOT/'runs/stage326_gvs_kernel_efficiency_20260928/confirmation')
new,rows,obs=saved(out/'deterministic')
t=np.arange(0,41)*.01
p,v=reference_at(old['task']['goal']['data'],t);p2,v2=reference_at(new['task']['goal']['data'],t)
assert np.array_equal(p,p2) and np.array_equal(v,v2)
def error(r,inp):
    desired,_=reference_at(inp['task']['goal']['data'],r['time_s'])
    return float(np.linalg.norm(np.array(r['tip_m'])-desired))
comparison=[]
for i in range(8):
    x,y=oldo[i],obs[i]
    comparison.append(dict(start_s=y['time_s'],baseline_error_at_endpoint_m=error(oldrows[i],old),new_error_at_endpoint_m=error(rows[i],new),
        baseline_plan_source=x.get('plan_source'),new_plan_source=y.get('plan_source'),
        baseline_stop_reason=x.get('policy_stop_reason'),new_stop_reason=y.get('policy_stop_reason'),
        baseline_update_s=x['update_wall_s'],new_update_s=y['update_wall_s'],
        command_max_difference_n=float(np.max(abs(np.array(oldrows[i]['tension_n'])-rows[i]['tension_n'])))))
a=read(out/'deterministic_audit.json')
atomic_json(out/'failure_diagnostics.json',dict(
    reference_comparison=dict(times_s=t.tolist(),maximum_position_difference_m=float(np.max(abs(p-p2))),maximum_velocity_difference_m_s=float(np.max(abs(v-v2)))),
    startup_comparison=comparison,violations=[dict(time_s=r['time_s'],error_m=error(r,new)) for r in rows if error(r,new)>.010],
    maximum_prediction_interval=max(a['prediction']['intervals'],key=lambda r:r['difference_m']),
    prediction_over_1mm=[r for r in a['prediction']['intervals'] if r['difference_m']>.001],
    diagnostic_threshold_note='1 mm is a descriptive post-run prediction threshold, not a task acceptance criterion.',
    conclusion='Complete scientifically failed task; no reference/scheduling defect identified. First-segment position and velocity match the archived baseline at every 0.01 s node. Accepted commands already differ at t=0, before the horizon sees the new segment. The unchanged wall-time solver stopping policy can return different plans; this saved-run comparison does not isolate causality. No repeat rollout or provider session follows the failed gate.'))
atomic_json(out/'live_gate_decision.json',dict(deterministic_accepted=False,decision='Do not prepare or run live session',
    reason='Complete valid execution violates frozen 0.010 m global sampled limit at 0.05 and 0.06 seconds.',
    implementation_defect_identified=False,second_deterministic_rollout=False,live_input_preserved=True,
    provider_requests=0,live_backend_attempts=0,credentials_loaded=False))
atomic_json(out/'provider_delivery_review.json',dict(status='not_performed',reason='Deterministic acceptance gate failed; no live session, provider response or selected live candidate exists.',
    live_tracking_outcome=None,structured_delivery_outcome=None,prose_delivery_outcome=None,full_live_regression_pass=False,
    no_program_generated_facts_substituted_for_provider_delivery=True))
print('Saved startup comparison, affected prediction intervals and skipped live/delivery decision.')
