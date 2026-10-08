from pathlib import Path
from copy import deepcopy
import json
from tools.state_io import read,atomic_json
from tools.platform_store import encode
from tools.research_investigations import InvestigationDispatcher
from tools.context_assembly import measure_input
out=Path('evidence/research_mainline3_v1_complete_20261009');wire=read(out/'principal_capacity_failed_wire.json');original=deepcopy(wire);cfg=read(out/'frozen_configuration.json')['policy']['model'];packet=json.loads(wire['messages'][1]['content']);before=measure_input(wire,cfg,'research_decision');full=deepcopy(packet['historical_handoffs']);packet['historical_handoffs']=InvestigationDispatcher._handoff_view(full);packet['historical_handoff_presentation']='Provenance metadata only; full immutable historical bindings and reports remain in Host state. No new report or authorization is inferred.';wire['messages'][1]['content']=encode(packet);after=measure_input(wire,cfg,'research_decision')
assert after['passed'];assert wire['messages'][2:]==original['messages'][2:];assert packet['reads']==json.loads(original['messages'][1]['content'])['reads'];assert packet['fact_catalog']==json.loads(original['messages'][1]['content'])['fact_catalog']
atomic_json(out/'principal_capacity_repaired_wire.json',wire)
atomic_json(out/'repair1_saved_wire_check.json',dict(before=before,after=after,provider_requests=0,reasoning_and_native_history_unchanged=True,original_report_and_current_evidence_unchanged=True,full_historical_binding_archived=True,scope='Duplicate program-owned historical execution metadata compacted; no response filtering or scientific edits.'))
print(dict(before=before['utf8_bytes'],after=after['utf8_bytes'],passed=after['passed']))
