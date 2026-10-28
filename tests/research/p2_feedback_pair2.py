"""Second matched P2 feedback decisions; no launch or API call on import."""
import asyncio,json,os,subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import httpx
from tools.platform_store import encode,plain
from tools.research import core
from tools.research.agent import LiveBoundary,decision_packet,load_credential,received,record,plan_schema
from tools.research.decision_comparison import validate_proposals
from tools.research.state import state,guard,update,science_hashes
from tools.research.tool_readiness import execution_environment
from tools.state_io import digest
from tests.research.p2_feedback_paired import host,RUN,clean_commit
from tests.research.p2_feedback_modes import CHILDREN as FIRST_CHILDREN

CHILDREN={'on':'p2-feedback-second-thinking-on-20261028','off':'p2-feedback-second-thinking-off-20261028'}
PRIOR_ID='3e411027a5d2383d8bc100376423bf144a389ed05ae598564770a3a7cd7bb867'
T1_ID='b45d5e40b643f8c315077a8ea0812f6b7b2ab426f8a694446059fd1a3effec1f'
REPLAY_ID='b0af68a98f46fe3fc533f0c058effeabf76d0fe83d4593c1f7f15ed8cbcf9e0f'
PAUSE_ID='7562b3697c1592d79702246833e1d8152def704edf730a84e04050438816cb54'


def authorize(h):
    """Append the user's cap increase to the existing anchored ledger."""
    commit=clean_commit();s=state(h);ledger=h.store.remaining()
    if s['spec']['resolved_identity']!=PRIOR_ID:raise ValueError('EXACT_PREVIOUS_AUTHORIZATION_REQUIRED_NO_REPEAT')
    if (ledger['limit']['model_calls']!=13 or ledger['used']['model_calls']!=8 or ledger['remaining']['model_calls']!=5
            or s['spec']['budgets']['protected_provider_requests']!=4):raise ValueError('EXACT_SHARED_LEDGER_REQUIRED')
    if (s['research_status']!='ready' or s.get('pending') or ledger['occupied'] or s.get('pilot',{}).get('unconsumed_response')
            or s['mathematical_evaluations']!=1 or s.get('physical_replay_launches')!=1):raise ValueError('SETTLED_EXPECTED_SCIENCE_REQUIRED')
    if s['analysis_results'][0]['artifact_id']!=T1_ID or s['physical_replays'][0]['artifact_id']!=REPLAY_ID:
        raise ValueError('EXACT_MATCHED_FEEDBACK_REQUIRED')
    if not any(e['kind']=='paired_feedback_supervisor_pause' and e['outputs'][0]['artifact_id']==PAUSE_ID for e in h.store.events(RUN)):
        raise ValueError('PAIRED_SUPERVISOR_PAUSE_REQUIRED')
    if science_hashes()!=s['profile']['science_hashes'] or execution_environment(s['spec'])['status']!='ready':
        raise ValueError('FROZEN_SCIENCE_AND_ENVIRONMENT_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    spec=deepcopy(s['spec']);spec['budgets']['provider_requests']=15
    spec['configuration']['policy']['budget']['model_calls']=15;spec.pop('resolved_identity')
    with h.store.transaction() as db:
        if h.store.remaining(db=db)!=ledger or h.store.session(RUN,db)['state']!=s:raise ValueError('SOURCE_CHANGED_DURING_AUTHORIZATION')
        prior_state=plain(h.store.put(db,s));prior_snapshot=plain(h.store.put(db,h.store.session(RUN,db)['snapshot']))
        approval=dict(version='p2_paired_feedback_cap15_v1',user_approval=True,
            approval_text='批准将 P2 全局 Provider 上限提高到 15、本阶段上限提高到 7，保留原研究和本阶段各两次收尾额度。请让 Thinking-On 和 Off 接收相同反馈继续配对决策，严格遵守数学和回放预算，不启动 P3。',
            previous_state=prior_state,previous_snapshot=prior_snapshot,previous_ledger=ledger,
            provider_limit=15,new_segment_provider_limit=7,original_protected=2,segment_protected=2,
            mathematical_limit_unchanged=s['spec']['budgets']['mathematical_evaluations'],
            physical_replay_limit_unchanged=s['spec']['physical_replay_limit'],
            numerical_guard_unchanged=s['spec']['numerical_execution_guard'],
            t1=s['analysis_results'][0],replay=s['physical_replays'][0],pause=PAUSE_ID,
            data_scope='Identical frozen task, schemas and current Study state plus the shared T1, actual paired evidence-read and physical-replay tool feedback; no unrelated Study or prior private reasoning.',
            no_automatic_retry=True,p3='PENDING_EXPLICIT_P3_APPROVAL',implementation_commit=commit)
        addendum=plain(h.store.put(db,approval));spec.setdefault('authorization_addenda',[]).append(addendum);spec['resolved_identity']=digest(spec)
        snapshot=deepcopy(h.store.session(RUN,db)['snapshot']);snapshot['input']['policy']['budget']['model_calls']=15
        snapref=h.store.put(db,snapshot);config=h.store.config(db);previous_hash=digest(config);config['budget']['model_calls']=15
        db.execute('ATTACH DATABASE ? AS authority',(str(core.ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(config),config['grant_id'],str(h.store.root),previous_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_GRANT_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(config),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapref.artifact_id,RUN))
        current=h.store.session(RUN,db)['state'];current.update(spec=spec,validation_extension_pending_binding=True)
        current.setdefault('validation_extensions',[]).append(addendum);h.store.update_state(db,RUN,current)
        h.store.event(db,RUN,'request_budget_extension','authorized',outputs=[addendum,snapref])
    core.bind(h,reason='Explicit user P2 paired-feedback continuation: total Provider 15, stage 7; original and stage two-request closeout pools, science limits and historical evidence preserved')
    guard(h);current=state(h)
    if current['profile']!=s['profile'] or h.store.remaining()['used']!=ledger['used']:
        raise ValueError('MIGRATION_MUST_PRESERVE_SCIENCE_AND_USAGE')
    return dict(addendum=addendum,freeze=current['freeze'],ledger=h.store.remaining(),profile_preserved=True)


def freeze_pair(h):
    """Create identical context including the actual three prior tool responses."""
    guard(h,True);s=state(h);ledger=h.store.remaining()
    if (ledger['limit']['model_calls']!=15 or ledger['used']['model_calls']!=8 or ledger['remaining']['model_calls']!=7
            or s['spec']['budgets']['protected_provider_requests']!=4 or s['mathematical_evaluations']!=1
            or s.get('physical_replay_launches')!=1):raise ValueError('APPROVED_PAIR2_BUDGET_REQUIRED')
    outputs=[];previous_bundle=None
    for arm in ('off','on'):
        child=SimpleNamespace(store=h.store,run_id=FIRST_CHILDREN[arm]);cs=state(child)
        bundle=h.store.artifact(cs['paired_context'])
        if previous_bundle is None:previous_bundle=bundle
        elif previous_bundle!=bundle:raise ValueError('PREVIOUS_SHARED_CONTEXT_MISMATCH')
        events=[e for e in h.store.events(child.run_id) if e['kind']=='paired_tool_feedback']
        if len(events)!=(2 if arm=='off' else 1):raise ValueError('ACTUAL_PAIRED_TOOL_FEEDBACK_REQUIRED')
        for event in events:
            item=h.store.artifact(event['outputs'][0]);outputs.append(dict(source_session=child.run_id,
                feedback_reference=event['outputs'][0],tool_use=item['tool_use'],actual_tool_response=item['result']))
    packet=decision_packet(h)
    packet['shared_prior_tool_feedback']=dict(version='actual_matched_feedback_v1',
        context='The following actual outcomes came from the prior paired decisions; all are shared identically with both modes. They are prior separate agents, not tool calls in this conversation.',
        shared_t1=previous_bundle['packet']['shared_t1_feedback'],results=outputs,
        instruction='Select the next justified available action or stop. Numerical incompleteness does not establish infeasibility or task acceptance. Do not presume there is a remaining independent replay.',
        paired_budget='This snapshot precedes two paired requests; after both, 5 Provider requests remain and 4 are protected. Actual admission uses the live shared ledger.')
    wire=deepcopy(previous_bundle['wire']);wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'),ensure_ascii=False)
    plan=next(t['function'] for t in wire['tools'] if t['function']['name']=='research_plan')
    plan['parameters']=plan_schema(packet['research']['actions'],decision_required=True,family_version=s['spec']['family_space']['version'])
    if any(m.get('role') not in ('system','user') or m.get('reasoning_content') or m.get('tool_calls') for m in wire['messages']):
        raise ValueError('CLEAN_COMMON_CONVERSATION_REQUIRED')
    return dict(version='p2_paired_feedback_round2_v1',packet=packet,wire=wire,wire_on_identity=digest(wire),
        parent_state_identity=digest(s),prior_ledger=ledger,t1=s['analysis_results'][0],replay=s['physical_replays'][0],
        source_implementation=s['freeze'],matched_scope='All fields identical except thinking and reasoning_effort; actual feedback from both prior decisions is shared without invented tool messages.')


class PairGuardStore:
    def __init__(self,store,child,identity):self.store,self.child,self.identity=store,child,identity
    def __getattr__(self,name):return getattr(self.store,name)
    def reserve(self,run_id,request_id,request_hash,caller,cost,**kwargs):
        previous=kwargs.pop('guard',None)
        def check(db):
            if previous:previous(db)
            s=self.store.session(RUN,db)['state'];ledger=self.store.remaining(db=db)
            if digest(s)!=self.identity or s.get('pending'):raise ValueError('FROZEN_PAIR_SOURCE_CHANGED')
            if run_id!=self.child or cost['model_calls']!=1 or any(cost[k] for k in ('tool_calls','backend_solves','worker_calls')):
                raise ValueError('PAIR_PROVIDER_ONLY_CHILD_REQUIRED')
            if ledger['limit']['model_calls']!=15 or ledger['used']['model_calls'] not in (8,9) or ledger['remaining']['model_calls']<=4:
                raise ValueError('PAIR_PROTECTED_CAPACITY_REQUIRED')
            if s['spec']['budgets']['protected_provider_requests']!=4 or s['mathematical_evaluations']!=1 or s['physical_replay_launches']!=1:
                raise ValueError('PROTECTED_OR_SCIENTIFIC_BUDGET_CHANGED')
            if db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown') LIMIT 1").fetchone():raise ValueError('PENDING_CALL_BLOCKS_PAIR')
            if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(self.child,)).fetchone():raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
        return self.store.reserve(run_id,request_id,request_hash,caller,cost,guard=check,**kwargs)


def prepare(h,bundle):
    with h.store.connect(True) as db:
        if any(db.execute('SELECT 1 FROM sessions WHERE run_id=?',(v,)).fetchone() for v in CHILDREN.values()):
            raise ValueError('PAIR_ALREADY_PREPARED_NO_RESET')
    ref=record(h,'paired_feedback_round2_context',bundle)
    budget=dict(tool_calls=0,model_calls=1,backend_solves=0,worker_calls=0,wall_s=None)
    for arm,name in CHILDREN.items():
        h.store.create_session(dict(input=dict(run_id=name,policy=dict(budget=budget)),parent_run_id=RUN,
            purpose='matched independent decisions on identical real paired feedback'))
        child=SimpleNamespace(store=h.store,run_id=name);provider=deepcopy(state(h)['pilot']['provider'])
        if arm=='off':provider.update(thinking='disabled',reasoning_effort=None)
        update(child,pilot=dict(provider=provider,live_model_requests=0),paired_context=ref,arm=arm)
        record(child,'paired_decision_authorization',dict(user_approved=True,context=ref,arm=arm,
            provider_requests=1,scientific_execution=0,automatic_retries=0,protected_original=2,protected_segment=2))
    return ref


async def send_arm(h,bundle,arm,api_key,transport=None):
    name=CHILDREN[arm];child=SimpleNamespace(store=h.store,run_id=name)
    with h.store.connect(True) as db:
        if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(name,)).fetchone():raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
    wire=deepcopy(bundle['wire'])
    if arm=='off':wire['thinking']={'type':'disabled'};wire.pop('reasoning_effort')
    content=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if not api_key or api_key.encode() in content or b'credentials_reference' in content:raise ValueError('PRIVATE_CREDENTIAL_IN_REQUEST_OR_MISSING')
    wrapped=SimpleNamespace(store=PairGuardStore(h.store,name,bundle['parent_state_identity']),run_id=name)
    boundary=LiveBoundary(wrapped,transport=transport,allow_truncated_response=True,max_model_calls=10)
    boundary.purpose='paired_feedback_round2_'+arm;provider=state(child)['pilot']['provider']
    request=httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',content=content,
        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},
        extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)})
    try:
        response=await boundary.handle_async_request(request);rec=received(child,boundary.last_request)
        result=dict(arm=arm,request_id=boundary.last_request,request_identity=digest(wire),request_bytes=len(content),
            http_status=response.status_code,usage=rec['usage'],elapsed_s=rec['elapsed_s'],response_reference=rec['body'],
            scientific_execution='not_dispatched')
        try:result['validation']=validate_proposals(wire,bundle['packet'],json.loads(response.content))
        except (ValueError,TypeError,AttributeError):result['validation']=dict(status='invalid_response')
        record(child,'paired_feedback_round2_observation',result,status='observed')
        if response.is_success and result['validation']['status']=='complete':boundary.consumed()
        return result
    finally:await boundary.aclose()


async def pair(h):
    bundle=freeze_pair(h);load_credential(Path(state(h)['spec']['runtime']['credentials_reference']).expanduser())
    ref=prepare(h,bundle);print('paired_context',json.dumps(ref),flush=True)
    for arm in ('on','off'):
        result=await send_arm(h,bundle,arm,os.environ['DEEPSEEK_API_KEY']);print(json.dumps(result,ensure_ascii=True),flush=True)
        if result['http_status']!=200:break


if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['authorize']:print(json.dumps(authorize(host())))
    elif sys.argv[1:] == ['pair']:asyncio.run(pair(host()))
    else:raise ValueError('EXPLICIT_COMMAND_REQUIRED: authorize or pair')
