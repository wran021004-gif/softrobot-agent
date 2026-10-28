"""Execute the two saved paired decisions once using original study services."""
import json
from types import SimpleNamespace
from tools.platform_store import plain,zero
from tools.research import core
from tools.research.agent import received,record,read_tool_evidence,error_feedback
from tools.research.decision_comparison import validate_proposals
from tools.research.state import state,guard
from tools.state_io import digest
from tests.research.p2_feedback_paired import host,RUN
from tests.research.p2_feedback_modes import CHILDREN

REQUESTS={'on':'r3-request-979d5dfe7ed44d15abfe5cdaac4ad7c1',
          'off':'r3-request-bcad1ad1e05249a5a234ed9a29bcd600'}


def choices(h):
    result={};bundle=None;wires={}
    for arm in ('on','off'):
        child=SimpleNamespace(store=h.store,run_id=CHILDREN[arm]);s=state(child)
        current=h.store.artifact(s['paired_context'])
        if bundle is None:bundle=current
        elif bundle!=current:raise ValueError('PAIRED_CONTEXT_IDENTITY_MISMATCH')
        row=h.store.lookup(child.run_id,REQUESTS[arm]);rec=received(child,REQUESTS[arm])
        if not row or not row['receipt'] or rec['http_status']!=200:raise ValueError('SETTLED_PAIRED_RESPONSE_REQUIRED')
        event=next(e for e in h.store.events(child.run_id) if e['kind']=='r3_request' and e['request_id']==REQUESTS[arm])
        wire=h.store.artifact(h.store.artifact(event['outputs'][0])['request']);body=json.loads(h.store.artifact(rec['body'],raw=True))
        check=validate_proposals(wire,bundle['packet'],body)
        if check['status']!='complete' or any(x['status']!='contract_and_visible_references_valid' for x in check['proposals']):
            raise ValueError('COMPLETE_MATCHED_VALIDATED_PROPOSALS_REQUIRED')
        result[arm]=(child,body['choices'][0]['message']['tool_calls']);wires[arm]=wire
    a={k:v for k,v in wires['on'].items() if k not in ('thinking','reasoning_effort')}
    b={k:v for k,v in wires['off'].items() if k not in ('thinking','reasoning_effort')}
    if (a!=b or wires['on'].get('thinking')!={'type':'enabled'} or wires['on'].get('reasoning_effort')!='high'
            or wires['off'].get('thinking')!={'type':'disabled'} or 'reasoning_effort' in wires['off']):
        raise ValueError('EXACT_MATCHED_REQUESTS_REQUIRED')
    if digest(state(h))!=bundle['parent_state_identity'] or h.store.remaining()['used']['model_calls']!=8:
        raise ValueError('POST_PAIR_SOURCE_OR_LEDGER_CHANGED')
    if [x['function']['name'] for x in result['off'][1]]!=['evidence_read','evidence_read']:
        raise ValueError('UNEXPECTED_OFF_TOOLS')
    if [x['function']['name'] for x in result['on'][1]]!=['research_plan']:
        raise ValueError('UNEXPECTED_ON_TOOL')
    return result


def execute_one(h,child,call):
    fn=call['function'];arguments=json.loads(fn['arguments']);use=dict(name=fn['name'],toolUseId=call['id'],input=arguments)
    key='native-'+call['id']
    if h.store.lookup(RUN,key) or any(e['kind']=='paired_tool_dispatch' and h.store.artifact(e['outputs'][0])['tool_use']['toolUseId']==call['id'] for e in h.store.events(child.run_id)):
        raise ValueError('TOOL_ALREADY_ATTEMPTED_NO_RETRY')
    before=state(h)
    record(child,'paired_tool_dispatch',dict(tool_use=use,request_id=key,status='dispatch_started'))
    def protect_public(db):
        if h.store.remaining(db=db)['remaining']['tool_calls']<=3:raise ValueError('PROTECTED_PUBLIC_CAPACITY')
    try:
        if fn['name']=='evidence_read':
            row,_=h.store.reserve(RUN,key,digest(arguments),h.actor,{**zero(),'tool_calls':1},guard=protect_public)
            value=read_tool_evidence(h,arguments)
            h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                tool_id='research.core_evidence',tool_version='1.0.0',execution_status='completed',charged=zero()),value)
        elif fn['name']=='research_plan':
            value=core.dispatch(h,arguments,key,origin='paired_model_'+state(child)['arm'])
        else:raise ValueError('UNAUTHORIZED_PAIRED_TOOL')
        result=dict(toolUseId=call['id'],status='success',content=[dict(text=json.dumps(value,separators=(',',':'),ensure_ascii=False))])
    except Exception as exc:
        row=h.store.lookup(RUN,key)
        if not row:
            row,_=h.store.reserve(RUN,key,digest(use),h.actor,{**zero(),'tool_calls':1},guard=protect_public)
        if not row['receipt']:
            h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                tool_id=fn['name'],tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),dict(error=str(exc)))
        result=dict(toolUseId=call['id'],status='error',content=[dict(text=json.dumps(error_feedback(h,use,exc,before),ensure_ascii=False))])
    reference=record(child,'paired_tool_feedback',dict(tool_use=use,result=result))
    return dict(tool=fn['name'],tool_id=call['id'],status=result['status'],feedback_reference=reference,
        ledger=h.store.remaining(),pending=state(h).get('pending'))


def main():
    h=host();guard(h,True);arms=choices(h)
    # Both choices were frozen first; execute the read-only branch before the
    # independent replay so that the latter cannot contaminate the former's view.
    for arm in ('off','on'):
        child,calls=arms[arm]
        for call in calls:
            result=execute_one(h,child,call)
            print(json.dumps(dict(arm=arm,**result),ensure_ascii=True),flush=True)
            if result['pending']:return


if __name__=='__main__':main()
