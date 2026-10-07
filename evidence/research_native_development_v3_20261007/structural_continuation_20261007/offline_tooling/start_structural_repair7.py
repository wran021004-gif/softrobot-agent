from pathlib import Path
import time, shutil, hashlib
from examples import research_model_v1 as pilot
from tools.state_io import read,atomic_json,digest
from tools.platform_store import zero
w=pilot.restore(Path('runs/research_native_development_v3_20261007').resolve())
assert w.status=='failed' and w.repairs==6 and w.stop_reason.startswith('CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET:')
assert time.time()<w.freeze['live_clock']['deadline_unix']
with w.store.connect(True) as db:
    assert not list(db.execute('SELECT 1 FROM calls WHERE receipt IS NULL'))
out=Path(w.freeze['experiment']['evidence_directory'])/'repair7'
out.mkdir(exist_ok=False)
copies={}
for name in ('freeze.json','scheduler_state.json','working_state.json','failure.json','final_interpretation_failure.json'):
    shutil.copyfile(w.directory/name,out/name)
    copies[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
boundary=dict(version='v3-final-request-representation-repair@3.6.0',started_unix=time.time(),
    authorization=w.freeze['structural_continuation_authorization'],previous_repairs=6,cumulative_material_repairs=7,
    failed_snapshot=copies,failure=w.stop_reason,settled_usage=w.store.remaining(),
    original_clock=w.freeze['live_clock'],repair_scope='Exact inline fact-table representation and same-session next-request continuation; no scientific choices or provider settings changed')
reservation,_=w.store.reserve(w.host.run_id,'structural-inline-fact-repair7',digest(boundary),'engineering',
    {**zero(),'tool_calls':1,'wall_s':1800.})
atomic_json(w.directory/'structural_repair7_start.json',dict(boundary=boundary,reservation=reservation,output=str(out)))
atomic_json(out/'start.json',dict(boundary=boundary,reservation=reservation))
print(w.store.remaining())
