"""Execute both semantically identical paired evidence reads, without science."""
import json
from types import SimpleNamespace
from tools.research.agent import received,record
from tools.research.contracts import EvidenceQuery
from tools.research.state import state,guard
from tools.state_io import digest
from tests.research.p2_feedback_paired import host
from tests.research.p2_feedback_pair2 import CHILDREN
from tests.research.p2_feedback_execute import execute_one

REQUESTS={'on':'r3-request-41072cf46ff94f91a2df73784f71d108','off':'r3-request-3577604cd7684549bf66d83aee72f9dd'}


def confirmed(h):
    """Require both complete matched choices before making either read."""
    arms={};bundle=None;wires={};normalized=[]
    for arm in ('on','off'):
        child=SimpleNamespace(store=h.store,run_id=CHILDREN[arm]);cs=state(child)
        context=h.store.artifact(cs['paired_context'])
        if bundle is None:bundle=context
        elif bundle!=context:raise ValueError('PAIRED_CONTEXT_MISMATCH')
        row=h.store.lookup(child.run_id,REQUESTS[arm]);rec=received(child,REQUESTS[arm])
        if not row or not row['receipt'] or rec['http_status']!=200:raise ValueError('SETTLED_PAIRED_RESPONSE_REQUIRED')
        evt=next(e for e in h.store.events(child.run_id) if e['kind']=='r3_request' and e['request_id']==REQUESTS[arm])
        wire=h.store.artifact(h.store.artifact(evt['outputs'][0])['request']);body=json.loads(h.store.artifact(rec['body'],raw=True))
        choices=body.get('choices',[])
        if len(choices)!=1 or choices[0]['finish_reason']!='tool_calls':raise ValueError('COMPLETE_TOOL_CALL_REQUIRED')
        calls=choices[0]['message'].get('tool_calls',[])
        if len(calls)!=1 or calls[0]['function']['name']!='evidence_read':raise ValueError('PAIRED_EVIDENCE_READ_REQUIRED')
        normalized.append(EvidenceQuery.model_validate_json(calls[0]['function']['arguments']).model_dump(mode='json'))
        arms[arm]=(child,calls[0]);wires[arm]=wire
    if normalized[0]!=normalized[1]:raise ValueError('IDENTICAL_NORMALIZED_READS_REQUIRED')
    if normalized[0]['view']!='working_set' or normalized[0]['pointer']!='/all_fresh_results':raise ValueError('EXACT_RESULTS_INDEX_REQUIRED')
    if {k:v for k,v in wires['on'].items() if k not in ('thinking','reasoning_effort')}!={k:v for k,v in wires['off'].items() if k not in ('thinking','reasoning_effort')}:
        raise ValueError('EXACT_MATCHED_INPUT_REQUIRED')
    if (wires['on'].get('thinking')!={'type':'enabled'} or wires['on'].get('reasoning_effort')!='high'
            or wires['off'].get('thinking')!={'type':'disabled'} or 'reasoning_effort' in wires['off']):
        raise ValueError('EXACT_MODES_REQUIRED')
    if digest(state(h))!=bundle['parent_state_identity'] or h.store.remaining()['used']['model_calls']!=10:
        raise ValueError('SOURCE_CHANGED_AFTER_PAIR')
    return arms


def main():
    h=host();guard(h);arms=confirmed(h);outputs=[]
    for arm in ('on','off'):
        child,call=arms[arm];result=execute_one(h,child,call)
        result['arm']=arm;print(json.dumps(result),flush=True)
        outputs.append(h.store.artifact(result['feedback_reference'])['result'])
        if result['status']!='success' or result['pending']:return
    # Ignore tool-use IDs, which necessarily differ between model responses.
    identical=outputs[0]['content']==outputs[1]['content'] and outputs[0]['status']==outputs[1]['status']
    ref=record(h,'paired_feedback_round2_read_comparison',dict(identical_tool_response=identical,
        tool='evidence_read',normalized_query='working_set /all_fresh_results',
        requests=REQUESTS,scientific_execution='none',model_followup_sent=False))
    print(json.dumps(dict(identical_tool_response=identical,comparison=ref,ledger=h.store.remaining())),flush=True)


if __name__=='__main__':main()
