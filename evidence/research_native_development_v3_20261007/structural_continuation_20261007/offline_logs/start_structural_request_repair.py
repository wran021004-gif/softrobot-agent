import time
from pathlib import Path
from examples import research_model_v1 as pilot
from tools.state_io import read,atomic_json,digest
from tools.platform_store import zero
w=pilot.restore('runs/research_native_development_v3_20261007')
start=read(w.directory/'structural_repair_start.json')
boundary=dict(version='v3-feedback-request-repair@3.5.0',authorization=start['authorization'],
    previous_repairs=5,cumulative_material_repairs=6,started_unix=time.time(),
    failure='Saved accepted-plan complete offline path: post-batch next-request exceeds unchanged input budget',
    failure_log='runs/structural_complete_path_checks.log',
    implementation_boundary='tools/context_assembly.py:fit_request redundant bound selector representations',
    live_provider_calls=0,live_backend_attempts=0)
row=start['reservation']
receipt=w.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller='engineering',
    tool_id='engineering.shared_historical_parameter_read',tool_version='3.4.0',execution_status='completed',charged=zero()),
    dict(shared_reader_fixed=True,complete_request_gate_passed=False,next_failure=boundary),boundary['started_unix']-start['authorization']['started_unix'])
reservation,_=w.store.reserve(w.host.run_id,'structural-next-request-repair6',digest(boundary),'engineering',
    {**zero(),'tool_calls':1,'wall_s':1800.})
atomic_json(Path(start['output'])/'repair5_reader_and_request_failure.json',dict(boundary=boundary,receipt=receipt))
atomic_json(w.directory/'structural_request_repair_start.json',dict(boundary=boundary,reservation=reservation))
print(w.store.remaining())
