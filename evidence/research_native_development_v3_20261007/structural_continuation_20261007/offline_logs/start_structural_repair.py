import time
from pathlib import Path
from examples import research_model_v1 as pilot
from tools.state_io import atomic_json, digest
from tools.platform_store import zero

w = pilot.restore(Path('runs/research_native_development_v3_20261007'))
out = Path('evidence/research_native_development_v3_20261007/structural_continuation_20261007')
out.mkdir(parents=True, exist_ok=True)
assert w.status == 'failed' and w.repairs == 4
assert time.time() < w.freeze['live_clock']['deadline_unix']
assert not w.store.remaining()['occupied']
session = w.store.session(w.host.run_id)
batch = session['state']['search_batch']
assert not batch['proposals'] and batch['pending'] is None
auth = dict(version='v3-structural-continuation-authorization@3.4.0',
    source_attachment='9dae342a-539d-453e-a481-0fa61888934d',
    same_campaign=w.store.config()['project_id'], same_session=w.host.run_id,
    clock=w.freeze['live_clock'], previous_repairs=4,
    additional_material_live_repairs=3, cumulative_repair_ceiling=7,
    original_limits=w.store.config()['budget'], accepted_plan=batch['plan'],
    sealed_failure=dict(path='evidence/research_native_development_v3_20261007/continuation_20261007/reviewed_delivery.json',
        sha256=__import__('hashlib').sha256(Path('evidence/research_native_development_v3_20261007/continuation_20261007/reviewed_delivery.json').read_bytes()).hexdigest()),
    started_unix=time.time(), settled_usage=w.store.remaining(),
    no_new_campaign=True, no_backend_replay=True, no_clock_reset=True)
for name in ('freeze.json','scheduler_state.json','working_state.json','failure.json','continuation_final_costs.json'):
    (out/('prior_'+name)).write_bytes((w.directory/name).read_bytes())
with w.store.transaction() as db:
    ref=w.store.put(db,auth)
    w.store.event(db,w.host.run_id,'continuation_authorization','completed',outputs=[ref],version='3.4.0')
reservation,_=w.store.reserve(w.host.run_id,'structural-historical-read-repair5',digest(auth),'engineering',
    {**zero(),'tool_calls':1,'wall_s':1800.})
atomic_json(out/'authorization.json',auth)
atomic_json(w.directory/'structural_repair_start.json',dict(authorization=auth,reservation=reservation,output=str(out)))
print({'usage':auth['settled_usage'],'plan':batch['plan'],'started':auth['started_unix']})
