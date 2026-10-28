"""Dispatch only the actual paired read-only choices with shared P2 accounting."""
import json
from types import SimpleNamespace
from tools.research.agent import received,record
from tools.research.decision_comparison import validate_proposals
from tools.research.state import state,guard
from tools.state_io import digest
from tests.research.p2_feedback_paired import host
from tests.research.p2_feedback_pair3 import CHILDREN
from tests.research.p2_feedback_execute import execute_one

REQUESTS={'on':'r3-request-f020584b4f744e18bdb4c2cae700a7fd','off':'r3-request-7d849f4811b042938acc3660d923fa77'}


def admit_calls(arm,calls):
    if arm=='off' and [c['function']['name'] for c in calls]==['evidence_read','evidence_read']:return
    if arm=='on' and len(calls)==1 and calls[0]['function']['name']=='research_plan':
        data=json.loads(calls[0]['function']['arguments'])
        if data.get('action')=='diagnose' and data.get('diagnostic') is None:return
    raise ValueError('ONLY_SAVED_READ_ONLY_PAIR_CHOICES_ADMITTED')


def confirmed(h):
    arms={};bundle=None;wires={}
    for arm in ('on','off'):
        child=SimpleNamespace(store=h.store,run_id=CHILDREN[arm]);cs=state(child)
        context=h.store.artifact(cs['paired_context'])
        if bundle is None:bundle=context
        elif bundle!=context:raise ValueError('PAIRED_CONTEXT_MISMATCH')
        row=h.store.lookup(child.run_id,REQUESTS[arm]);rec=received(child,REQUESTS[arm])
        if not row or not row['receipt'] or rec['http_status']!=200:raise ValueError('SETTLED_PAIRED_RESPONSE_REQUIRED')
        evt=next(e for e in h.store.events(child.run_id) if e['kind']=='r3_request' and e['request_id']==REQUESTS[arm])
        wire=h.store.artifact(h.store.artifact(evt['outputs'][0])['request']);body=json.loads(h.store.artifact(rec['body'],raw=True))
        check=validate_proposals(wire,bundle['packet'],body)
        if check['status']!='complete' or any(x['status']!='contract_and_visible_references_valid' for x in check['proposals']):
            raise ValueError('COMPLETE_VALIDATED_PROPOSALS_REQUIRED')
        calls=body['choices'][0]['message'].get('tool_calls',[]);admit_calls(arm,calls)
        arms[arm]=(child,calls);wires[arm]=wire
    if {k:v for k,v in wires['on'].items() if k not in ('thinking','reasoning_effort')}!={k:v for k,v in wires['off'].items() if k not in ('thinking','reasoning_effort')}:
        raise ValueError('EXACT_MATCHED_INPUT_REQUIRED')
    if (wires['on'].get('thinking')!={'type':'enabled'} or wires['on'].get('reasoning_effort')!='high'
            or wires['off'].get('thinking')!={'type':'disabled'} or 'reasoning_effort' in wires['off']):raise ValueError('EXACT_MODES_REQUIRED')
    s=state(h)
    if digest(s)!=bundle['parent_state_identity'] or h.store.remaining()['used']['model_calls']!=12:
        raise ValueError('SOURCE_CHANGED_AFTER_PAIR')
    if s['mathematical_evaluations']!=1 or s['physical_replay_launches']!=1:raise ValueError('SCIENCE_BUDGET_CHANGED')
    return arms


def main():
    h=host();guard(h);arms=confirmed(h)
    # Both inputs and decisions are frozen before any returned tool is run.
    for arm in ('off','on'):
        child,calls=arms[arm]
        for call in calls:
            result=execute_one(h,child,call);print(json.dumps(dict(arm=arm,**result)),flush=True)
            s=state(h)
            if result['pending'] or s['mathematical_evaluations']!=1 or s['physical_replay_launches']!=1:
                raise ValueError('UNEXPECTED_SCIENCE_OR_PENDING_STOP')
    ref=record(h,'paired_feedback_round3_tool_settled',dict(requests=REQUESTS,science_executions=0,
        model_followup_sent=False,ledger=h.store.remaining()))
    print(json.dumps(dict(settled=ref,ledger=h.store.remaining())),flush=True)


if __name__=='__main__':main()
