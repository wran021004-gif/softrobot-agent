"""Third P2 matched decision: same corrected authorization and real feedback."""
import asyncio,json
from copy import deepcopy
from types import SimpleNamespace
from tools.platform_store import encode,plain
from tools.research import core
from tools.research.agent import decision_packet,plan_schema,record
from tools.research.research_context import mathematics_authorization
from tools.research.state import state,guard,science_hashes,update
from tools.research.tool_readiness import execution_environment
from tools.state_io import digest
from tests.research.p2_feedback_paired import host,RUN,clean_commit
from tests.research.p2_feedback_pair2 import CHILDREN as PRIOR_CHILDREN

CHILDREN={'on':'p2-feedback-third-thinking-on-20261028','off':'p2-feedback-third-thinking-off-20261028'}
PRIOR_ID='f08e467c67323993c50392eb116fd016c3be7f6a2723fdbb797b908886d0d118'
PAUSE='9d34669c4c0423301267d2fd9a1eab305fc74238fec589a0601517ae5b206642'
READ_COMPARISON='14b9d7a38557d5b1becaa9e1e08b021326ca905919f2373119e94eba2300d3e9'


def authorize(h):
    commit=clean_commit();s=state(h);ledger=h.store.remaining()
    if s['spec']['resolved_identity']!=PRIOR_ID:raise ValueError('EXACT_PREVIOUS_AUTHORIZATION_REQUIRED_NO_REPEAT')
    if (ledger['limit']['model_calls']!=15 or ledger['used']['model_calls']!=10 or ledger['remaining']['model_calls']!=5
            or s['spec']['budgets']['protected_provider_requests']!=4):raise ValueError('EXACT_SHARED_LEDGER_REQUIRED')
    if (s['research_status']!='ready' or s.get('pending') or ledger['occupied'] or s['pilot'].get('unconsumed_response')
            or s['mathematical_evaluations']!=1 or s.get('physical_replay_launches')!=1):raise ValueError('SETTLED_EXPECTED_SCIENCE_REQUIRED')
    if not any(e['kind']=='paired_feedback_round2_supervisor_pause' and e['outputs'][0]['artifact_id']==PAUSE for e in h.store.events(RUN)):
        raise ValueError('PAIRED_SUPERVISOR_PAUSE_REQUIRED')
    prior_math=mathematics_authorization(h,s)
    if prior_math['registered_study_scope_authorized'] is not True:raise ValueError('EXISTING_APPROVED_MATH_SCOPE_REQUIRED')
    if science_hashes()!=s['profile']['science_hashes'] or execution_environment(s['spec'])['status']!='ready':
        raise ValueError('FROZEN_SCIENCE_AND_ENVIRONMENT_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    spec=deepcopy(s['spec']);spec['budgets']['provider_requests']=17
    spec['configuration']['policy']['budget']['model_calls']=17;spec.pop('resolved_identity')
    with h.store.transaction() as db:
        if h.store.remaining(db=db)!=ledger or h.store.session(RUN,db)['state']!=s:raise ValueError('SOURCE_CHANGED_DURING_AUTHORIZATION')
        prior_state=plain(h.store.put(db,s));prior_snapshot=plain(h.store.put(db,h.store.session(RUN,db)['snapshot']))
        approval=dict(version='p2_paired_feedback_cap17_v1',user_approval=True,
            approval_text='批准将 P2 全局 Provider 上限提高到 17、本阶段上限提高到 9，保留两组各两次收尾额度。请让 Thinking-On 和 Off 接收修正后的相同反馈继续配对决策，争取完成自主修订；严格遵守数学和回放预算，不启动 P3。',
            previous_state=prior_state,previous_snapshot=prior_snapshot,previous_ledger=ledger,
            provider_limit=17,new_segment_provider_limit=9,original_protected=2,segment_protected=2,
            mathematical_limit_unchanged=s['spec']['budgets']['mathematical_evaluations'],
            physical_replay_limit_unchanged=s['spec']['physical_replay_limit'],numerical_guard_unchanged=s['spec']['numerical_execution_guard'],
            prior_math_authorization=prior_math['approval_reference'],pause=PAUSE,identical_read_comparison=READ_COMPARISON,
            data_scope='Identical frozen task, tool schemas and current study, actual T1/replay summaries and exact equal prior read feedback; no unrelated files or earlier assistant reasoning.',
            no_automatic_retry=True,p3='PENDING_EXPLICIT_P3_APPROVAL',implementation_commit=commit)
        addendum=plain(h.store.put(db,approval));spec.setdefault('authorization_addenda',[]).append(addendum);spec['resolved_identity']=digest(spec)
        snapshot=deepcopy(h.store.session(RUN,db)['snapshot']);snapshot['input']['policy']['budget']['model_calls']=17
        snapref=h.store.put(db,snapshot);config=h.store.config(db);previous_hash=digest(config);config['budget']['model_calls']=17
        db.execute('ATTACH DATABASE ? AS authority',(str(core.ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(config),config['grant_id'],str(h.store.root),previous_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_GRANT_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(config),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapref.artifact_id,RUN))
        current=h.store.session(RUN,db)['state'];current.update(spec=spec,validation_extension_pending_binding=True)
        current.setdefault('validation_extensions',[]).append(addendum);h.store.update_state(db,RUN,current)
        h.store.event(db,RUN,'request_budget_extension','authorized',outputs=[addendum,snapref])
        scope=dict(study_id=RUN,resolved_identity=spec['resolved_identity'],execution_scopes=['registered mathematics'],
            capabilities=['analysis'],mathematical_methods=spec['mathematical_methods'],budgets=spec['budgets'],
            physical_replay_limit=spec['physical_replay_limit'],authorization_addendum=addendum,
            prior_math_authorization=prior_math['approval_reference'],science_limits_unchanged=True,p3='PENDING_EXPLICIT_P3_APPROVAL')
        math_ref=h.store.put(db,dict(user_approval=True,scope=scope,scope_identity=digest(scope),
            source='Explicit user-approved P2 cap-17 continuation; unchanged existing mathematical scope.'))
        h.store.event(db,RUN,'formal_study_authorization','recorded',outputs=[math_ref])
    core.bind(h,reason='Explicit P2 paired feedback continuation: total Provider 17, stage 9, preserve both closeout pools and unchanged science limits')
    guard(h);current=state(h)
    if (current['profile']!=s['profile'] or h.store.remaining()['used']!=ledger['used']
            or mathematics_authorization(h,current)['registered_study_scope_authorized'] is not True):
        raise ValueError('MIGRATION_MUST_PRESERVE_SCIENCE_USAGE_AND_MATH_SCOPE')
    return dict(addendum=addendum,math_authorization=plain(math_ref),freeze=current['freeze'],ledger=h.store.remaining())


def shared_feedback(h):
    """Exact last paired reads plus concise summaries of previously shared results."""
    prior=None;reads=[]
    for arm in ('on','off'):
        child=SimpleNamespace(store=h.store,run_id=PRIOR_CHILDREN[arm]);cs=state(child)
        bundle=h.store.artifact(cs['paired_context'])
        if prior is None:prior=bundle
        elif prior!=bundle:raise ValueError('PRIOR_MATCHED_CONTEXT_REQUIRED')
        ev=[e for e in h.store.events(child.run_id) if e['kind']=='paired_tool_feedback']
        if len(ev)!=1:raise ValueError('PRIOR_EQUAL_READ_FEEDBACK_REQUIRED')
        item=h.store.artifact(ev[0]['outputs'][0]);reads.append(item['result'])
    if reads[0]['status']!='success' or reads[0]['status']!=reads[1]['status'] or reads[0]['content']!=reads[1]['content']:
        raise ValueError('PRIOR_TOOL_OUTPUTS_NOT_IDENTICAL')
    s=state(h);t1=s['analysis_results'][0];replay=s['physical_replays'][0];rv=h.store.artifact(replay);raw=h.store.artifact(rv['raw_reference'])
    nf=raw.get('numerical_failure') or {}
    prior_tools=prior['packet']['shared_prior_tool_feedback']['results']
    reads_only=[x for x in prior_tools if x['tool_use']['name']=='evidence_read']
    return dict(version='actual_common_feedback_v1',
        description='Both modes receive identical evidence. These are real prior tool responses, not claimed as calls made in this fresh conversation.',
        t1=prior['packet']['shared_prior_tool_feedback']['shared_t1'],
        prior_evidence_read_feedback=reads_only,
        replay_summary=dict(reference=replay,raw_reference=rv['raw_reference'],status=rv['status'],acceptance=rv['acceptance'],
            raw_error=raw.get('error'),raw_reason=raw.get('reason'),completed_steps=nf.get('confirmed_completed_steps'),
            attempted_steps=nf.get('attempted_steps'),time_s=(nf.get('integration_state') or [None])[0],
            control_before_call=nf.get('control_before_call'),scope='Summary of actual previous independent replay; complete tool response and raw result remain accessible by exact Store reference.'),
        exact_common_results_index=reads[0]['content'],comparison_reference={'artifact_id':READ_COMPARISON,'media_type':'application/json'},
        authorization_discovery_correction='Current registered mathematics scope is approved within the unchanged remaining budget; individual method prerequisites and admission still apply.',
        instruction='Independently choose the next justified action or stop from this evidence. An incomplete numerical run proves neither task acceptance nor structural infeasibility.')


def freeze_pair(h):
    guard(h,True);s=state(h);ledger=h.store.remaining()
    if (ledger['limit']['model_calls']!=17 or ledger['used']['model_calls']!=10 or ledger['remaining']['model_calls']!=7
            or s['spec']['budgets']['protected_provider_requests']!=4 or s['mathematical_evaluations']!=1
            or s['physical_replay_launches']!=1):raise ValueError('APPROVED_PAIR3_BUDGET_REQUIRED')
    if mathematics_authorization(h,s)['registered_study_scope_authorized'] is not True:raise ValueError('CURRENT_MATH_SCOPE_REQUIRED')
    child=SimpleNamespace(store=h.store,run_id=PRIOR_CHILDREN['on']);previous=h.store.artifact(state(child)['paired_context'])
    packet=decision_packet(h);packet['shared_corrected_feedback']=shared_feedback(h)
    packet['shared_corrected_feedback']['paired_budget']='This snapshot precedes two paired requests; if both settle, 5 Provider requests remain, of which 4 are protected; live ledger admission applies.'
    wire=deepcopy(previous['wire']);wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'),ensure_ascii=False)
    next(t['function'] for t in wire['tools'] if t['function']['name']=='research_plan')['parameters']=plan_schema(
        packet['research']['actions'],decision_required=True,family_version=s['spec']['family_space']['version'])
    if any(m.get('role') not in ('system','user') or m.get('reasoning_content') or m.get('tool_calls') for m in wire['messages']):
        raise ValueError('CLEAN_COMMON_CONVERSATION_REQUIRED')
    return dict(version='p2_paired_feedback_round3_v1',packet=packet,wire=wire,wire_on_identity=digest(wire),
        parent_state_identity=digest(s),prior_ledger=ledger,source_implementation=s['freeze'],
        matched_scope='All fields identical except thinking and reasoning_effort; same actual prior read and corrected math authorization.')


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
            if ledger['limit']['model_calls']!=17 or ledger['used']['model_calls'] not in (10,11) or ledger['remaining']['model_calls']<=4:
                raise ValueError('PAIR_PROTECTED_CAPACITY_REQUIRED')
            if s['spec']['budgets']['protected_provider_requests']!=4 or s['mathematical_evaluations']!=1 or s['physical_replay_launches']!=1:
                raise ValueError('PROTECTED_OR_SCIENTIFIC_BUDGET_CHANGED')
            if db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown') LIMIT 1").fetchone():raise ValueError('PENDING_CALL_BLOCKS_PAIR')
            if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(self.child,)).fetchone():raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
        return self.store.reserve(run_id,request_id,request_hash,caller,cost,guard=check,**kwargs)


def prepare(h,bundle):
    with h.store.connect(True) as db:
        if any(db.execute('SELECT 1 FROM sessions WHERE run_id=?',(v,)).fetchone() for v in CHILDREN.values()):raise ValueError('PAIR_ALREADY_PREPARED_NO_RESET')
    ref=record(h,'paired_feedback_round3_context',bundle)
    budget=dict(tool_calls=0,model_calls=1,backend_solves=0,worker_calls=0,wall_s=None)
    for arm,name in CHILDREN.items():
        h.store.create_session(dict(input=dict(run_id=name,policy=dict(budget=budget)),parent_run_id=RUN,
            purpose='matched independent decisions on identical corrected actual feedback'))
        child=SimpleNamespace(store=h.store,run_id=name);provider=deepcopy(state(h)['pilot']['provider'])
        if arm=='off':provider.update(thinking='disabled',reasoning_effort=None)
        update(child,pilot=dict(provider=provider,live_model_requests=0),paired_context=ref,arm=arm)
        record(child,'paired_decision_authorization',dict(user_approved=True,context=ref,arm=arm,
            provider_requests=1,scientific_execution=0,automatic_retries=0,protected_original=2,protected_segment=2))
    return ref


async def send_arm(h,bundle,arm,api_key,transport=None):
    # Reuse the existing accounted one-shot transport with this round's guard.
    import httpx
    from tools.research.agent import LiveBoundary,received
    from tools.research.decision_comparison import validate_proposals
    name=CHILDREN[arm];child=SimpleNamespace(store=h.store,run_id=name)
    with h.store.connect(True) as db:
        if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(name,)).fetchone():raise ValueError('PAIR_ARM_ALREADY_ATTEMPTED_NO_RETRY')
    wire=deepcopy(bundle['wire'])
    if arm=='off':wire['thinking']={'type':'disabled'};wire.pop('reasoning_effort')
    content=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if not api_key or api_key.encode() in content or b'credentials_reference' in content:raise ValueError('PRIVATE_CREDENTIAL_IN_REQUEST_OR_MISSING')
    wrapped=SimpleNamespace(store=PairGuardStore(h.store,name,bundle['parent_state_identity']),run_id=name)
    boundary=LiveBoundary(wrapped,transport=transport,allow_truncated_response=True,max_model_calls=12)
    boundary.purpose='paired_feedback_round3_'+arm;provider=state(child)['pilot']['provider']
    request=httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',content=content,
        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},
        extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)})
    try:
        response=await boundary.handle_async_request(request);rec=received(child,boundary.last_request)
        result=dict(arm=arm,request_id=boundary.last_request,request_identity=digest(wire),request_bytes=len(content),
            http_status=response.status_code,usage=rec['usage'],elapsed_s=rec['elapsed_s'],response_reference=rec['body'],scientific_execution='not_dispatched')
        try:result['validation']=validate_proposals(wire,bundle['packet'],json.loads(response.content))
        except (ValueError,TypeError,AttributeError):result['validation']=dict(status='invalid_response')
        record(child,'paired_feedback_round3_observation',result,status='observed')
        if response.is_success and result['validation']['status']=='complete':boundary.consumed()
        return result
    finally:await boundary.aclose()


async def pair(h):
    import os
    from pathlib import Path
    from tools.research.agent import load_credential
    bundle=freeze_pair(h);load_credential(Path(state(h)['spec']['runtime']['credentials_reference']).expanduser())
    ref=prepare(h,bundle);print('paired_context',json.dumps(ref),flush=True)
    for arm in ('on','off'):
        result=await send_arm(h,bundle,arm,os.environ['DEEPSEEK_API_KEY']);print(json.dumps(result,ensure_ascii=True),flush=True)
        if result['http_status']!=200:break


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['authorize']:print(json.dumps(authorize(host())))
    elif sys.argv[1:]==['pair']:asyncio.run(pair(host()))
    else:raise ValueError('EXPLICIT_COMMAND_REQUIRED: authorize or pair')
