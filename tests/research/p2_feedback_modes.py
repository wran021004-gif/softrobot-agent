"""One pair of independent Provider decisions on the same completed T1 receipt."""
import asyncio
from copy import deepcopy
import json,os,subprocess
from pathlib import Path
from types import SimpleNamespace
import httpx
from tools.research.agent import LiveBoundary,decision_packet,load_credential,received,record,plan_schema
from tools.research.analysis import compact_result
from tools.research.decision_comparison import freeze_original,validate_proposals
from tools.research.state import state,update,guard
from tools.state_io import digest
from tests.research.p2_feedback_paired import host,RUN,T1_KEY

CHILDREN={'on':'p2-feedback-t1-thinking-on-20261028','off':'p2-feedback-t1-thinking-off-20261028'}


def freeze_pair(h):
    """Freeze one genuine T1 tool result and one identical decision context."""
    guard(h,True);s=state(h);ledger=h.store.remaining()
    if ledger['used']['model_calls']!=6 or ledger['remaining']['model_calls']!=7 or s['mathematical_evaluations']!=1:
        raise ValueError('EXACT_PRE_PAIR_BUDGET_AND_ONE_T1_REQUIRED')
    row=h.store.lookup(RUN,T1_KEY+'-analysis')
    if not row or not row['receipt'] or len(s.get('analysis_results',[]))!=1 or s.get('pending'):
        raise ValueError('SETTLED_SHARED_T1_REQUIRED')
    accounting=h.store.lookup(RUN,T1_KEY+'-public-accounting')
    if not accounting or not accounting['receipt'] or json.loads(accounting['charged'])['tool_calls']!=1:
        raise ValueError('T1_OUTER_PUBLIC_ACCOUNTING_REQUIRED')
    ref=s['analysis_results'][0];raw=h.store.artifact(ref);feedback=compact_result(raw,ref)
    if raw.get('operation_key')!=T1_KEY+'-analysis' or raw.get('candidate')!=s['control_initializations'][0]['candidate']:
        raise ValueError('SHARED_T1_SOURCE_MISMATCH')
    packet=decision_packet(h)
    packet['shared_t1_feedback']=dict(origin='One actual supervisor-executed research_analysis result, shared identically between both modes.',
        query=raw['requested_operation'],tool_response=feedback,raw_result_reference=ref,
        paired_budget='Two matched provider calls are planned from this snapshot. If both settle, 5 of 13 remain; 4 are reserved for original and new segment closeout. Runtime admission always uses live ledger counts.',
        instruction='Independently select the next appropriate research action or STOP from this same actual evidence and frozen task; incomplete numerical work is not task success or structural infeasibility.')
    baseline=freeze_original(h,'r3-request-fcacd8a931d847aca84b6dd23b6c2772')
    wire=deepcopy(baseline['wire'])
    wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'),ensure_ascii=False)
    # SDK offload retrieval is tied to the original SDK invocation and cannot
    # be honestly advertised by this fresh paired observation.
    wire['tools']=[t for t in wire['tools'] if t['function']['name']!='retrieve_context']
    plan=next(t['function'] for t in wire['tools'] if t['function']['name']=='research_plan')
    plan['parameters']=plan_schema(packet['research']['actions'],decision_required=True,
        family_version=s['spec']['family_space']['version'])
    result=dict(version='p2_feedback_paired_v1',packet=packet,wire=wire,t1=ref,
        wire_on_identity=digest(wire),parent_state_identity=digest(s),prior_ledger=ledger,
        source_implementation=s['freeze'],paired_protocol_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],text=True).strip(),
        matched_scope='All fields identical except thinking and reasoning_effort; no prior assistant reasoning is copied.')
    if any(m.get('role') not in ('system','user') or m.get('reasoning_content') or m.get('tool_calls') for m in wire['messages']):
        raise ValueError('CLEAN_PAIRED_CONVERSATION_REQUIRED')
    return result


class PairGuardStore:
    def __init__(self,store,parent,child,parent_state_identity):
        self.store,self.parent,self.child,self.parent_state_identity=store,parent,child,parent_state_identity
    def __getattr__(self,name):return getattr(self.store,name)
    def reserve(self,run_id,request_id,request_hash,caller,cost,**kwargs):
        previous=kwargs.pop('guard',None)
        def guard_pair(db):
            if previous:previous(db)
            parent=self.store.session(self.parent,db)['state'];ledger=self.store.remaining(db=db)
            if digest(parent)!=self.parent_state_identity or parent.get('pending'):
                raise ValueError('FROZEN_PAIR_SOURCE_CHANGED')
            if run_id!=self.child or cost['model_calls']!=1 or any(cost[k] for k in ('tool_calls','backend_solves','worker_calls')):
                raise ValueError('PAIR_PROVIDER_ONLY_CHILD_REQUIRED')
            if ledger['limit']['model_calls']!=13 or ledger['used']['model_calls'] not in (6,7) or ledger['remaining']['model_calls']<=4:
                raise ValueError('PAIR_PROTECTED_CAPACITY_REQUIRED')
            if parent['spec']['budgets']['protected_provider_requests']!=4:
                raise ValueError('BOTH_CLOSEOUT_POOLS_REQUIRED')
            if db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown') LIMIT 1").fetchone():
                raise ValueError('PENDING_CALL_BLOCKS_PAIR')
            if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(self.child,)).fetchone():
                raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
        return self.store.reserve(run_id,request_id,request_hash,caller,cost,guard=guard_pair,**kwargs)


def prepare(h,bundle):
    """Both children share the original parent/project ledger and fixed input."""
    with h.store.connect(True) as db:
        if any(db.execute('SELECT 1 FROM sessions WHERE run_id=?',(name,)).fetchone() for name in CHILDREN.values()):
            raise ValueError('PAIR_ALREADY_PREPARED_NO_RESET')
    ref=record(h,'paired_t1_decision_context',bundle)
    budget=dict(tool_calls=0,model_calls=1,backend_solves=0,worker_calls=0,wall_s=None)
    for arm,name in CHILDREN.items():
        h.store.create_session(dict(input=dict(run_id=name,policy=dict(budget=budget)),parent_run_id=RUN,
            purpose='independent paired decision on identical actual T1 feedback'))
        child=SimpleNamespace(store=h.store,run_id=name)
        provider=deepcopy(state(h)['pilot']['provider'])
        if arm=='off':provider.update(thinking='disabled',reasoning_effort=None)
        update(child,pilot=dict(provider=provider,live_model_requests=0),paired_context=ref,arm=arm)
        record(child,'paired_decision_authorization',dict(user_approved=True,context=ref,arm=arm,
            provider_requests=1,scientific_execution=0,automatic_retries=0,protected_original=2,protected_segment=2))
    return ref


async def send_arm(h,bundle,arm,api_key,transport=None):
    name=CHILDREN[arm];child=SimpleNamespace(store=h.store,run_id=name)
    with h.store.connect(True) as db:
        if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(name,)).fetchone():
            raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
    wire=deepcopy(bundle['wire'])
    if arm=='off':wire['thinking']={'type':'disabled'};wire.pop('reasoning_effort')
    content=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if not api_key or api_key.encode() in content or b'credentials_reference' in content:
        raise ValueError('PRIVATE_CREDENTIAL_IN_REQUEST_OR_MISSING')
    wrapped=SimpleNamespace(store=PairGuardStore(h.store,RUN,name,bundle['parent_state_identity']),run_id=name)
    boundary=LiveBoundary(wrapped,transport=transport,allow_truncated_response=True,max_model_calls=8)
    boundary.purpose='paired_t1_feedback_'+arm
    provider=state(child)['pilot']['provider']
    request=httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',content=content,
        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},
        extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)})
    try:
        response=await boundary.handle_async_request(request);rec=received(child,boundary.last_request)
        result=dict(arm=arm,request_id=boundary.last_request,request_identity=digest(wire),request_bytes=len(content),
            http_status=response.status_code,usage=rec['usage'],elapsed_s=rec['elapsed_s'],response_reference=rec['body'],
            t1=bundle['t1'],scientific_execution='not_dispatched')
        try:result['validation']=validate_proposals(wire,bundle['packet'],json.loads(response.content))
        except (ValueError,TypeError,AttributeError):result['validation']=dict(status='invalid_response')
        record(child,'paired_t1_decision_observation',result,status='observed')
        if response.is_success and result['validation']['status']=='complete':boundary.consumed()
        return result
    finally:await boundary.aclose()


async def main():
    h=host();bundle=freeze_pair(h)
    load_credential(Path(state(h)['spec']['runtime']['credentials_reference']).expanduser())
    ref=prepare(h,bundle);print('paired_context',json.dumps(ref),flush=True)
    for arm in ('on','off'):
        result=await send_arm(h,bundle,arm,os.environ['DEEPSEEK_API_KEY'])
        print(json.dumps(result,ensure_ascii=True),flush=True)
        if result['http_status']!=200:break


if __name__=='__main__':asyncio.run(main())
