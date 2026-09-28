"""One recorded syntax correction in the existing live session; no counter reset."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import atomic_json,digest

root=Path(__file__).parent
record=root/'protocol_continuation.json'
if record.exists():raise ValueError('ONE_CORRECTION_ALREADY_PREPARED')
workflow=json.loads((root/'live/workflow.json').read_text())
host=Host(root/'live',workflow['run_id'])
if any(e['kind']=='stage324_protocol_continuation' for e in host.store.events(host.run_id)):
    raise ValueError('ONE_CORRECTION_ALREADY_PREPARED')
saved=host.store.session(host.run_id);before=host.store.remaining()
state=saved['state'];final=state['route']['final']
assert saved['status']=='failed' and state['stop_reason']=='BOUNDED_REPAIR_LIMIT'
assert final['explicit_delivery'] is False and final['delivery_status']=='incomplete'
assert state['turn']==11 and before['used']['model_calls']==11 and before['used']['backend_solves']==0
assert not before['occupied'] and host.compatibility()['compatible']
correction=dict(type='stage324_tool_argument_correction',requirement=(
    'The previous session stop was caused by invalid tool arguments, not a physics result. '
    'The successful candidate-bound analysis of build_near165 is already retained as artifact '
    'ccc04a6ec422d0a5406b021560fc8a6312a6b058fd363b7230c424eeb977f7b4: '
    '12 zero q and qdot values, ALL SIX tensions were 0.2 N (not zero tension), '
    'robot-base tip [0.313,0,0] m. No backend execution has occurred. '
    'Keep using the same session and remaining budgets. Decide your next action from the evidence. '
    'Syntax correction: route.advance action=run MUST OMIT combination; it preserves the source build combination. '
    'evidence.read arguments may contain only reference,pointer,offset,limit,byte_limit; NEVER arguments.reason. '
    'analysis.gvs_candidate_evaluate arguments may contain only source_node,state,input,detail,include_backbone,samples_per_segment; NEVER arguments.reason. '
    'Every tool envelope still needs OUTER reason and tool_version. route.advance does require its own nested reason and next_step. '
    'Do not repeat completed mathematics only because the route next_step text is stale. '
    'This is one explicit correction opportunity; all previous requests, errors, tool use and budgets remain counted.'))
with host.store.transaction() as db:
    old=host.store.put(db,dict(status=saved['status'],state=state,usage=before))
    state['route']['final']=None
    state['protocol_correction']=correction
    state.pop('stop_reason',None)
    host.store.update_state(db,host.run_id,state)
    note=host.store.put(db,correction)
    host.store.event(db,host.run_id,'stage324_protocol_continuation','prepared',inputs=[old],outputs=[note])
host.resume()
assert host.store.remaining()==before
assert host.store.session(host.run_id)['state']['turn']==11
for name in ('behavior_audit.json','route_status.json'):
    path=root/'live'/name
    path.rename(path.with_name('first_stop_'+name))
atomic_json(record,dict(run_id=host.run_id,previous_failure=plain(old),correction=plain(note),
    unchanged_usage=before,unchanged_turn=11,unchanged_input_identity=digest(saved['snapshot']['input']),
    no_counter_reset=True,no_new_session=True,backend_attempts_before=0))
print('One same-session protocol correction prepared; request counter remains 11 and all budgets are unchanged.')
