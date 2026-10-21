"""Three paired, genuinely multi-turn probes; numerical execution is intercepted."""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch
from uuid import uuid4
import httpx
from schemas.platform import ProjectConfig
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state,update,save,core_hashes
from tools.research.agent import LiveBoundary,load_credential,record,IncompleteModelOutput
from tools.state_io import read,atomic_json,digest
from tests.research.s126_decision_probe import frozen_s127

OUT=ROOT/'evidence/s127_6_decision'
PROMPT='Choose freely from the legal research tools using the frozen state. This isolated decision test returns actual Store reads and formal admission feedback. Numerical execution is intercepted; no scientific result is invented. Consume each tool result before deciding again. There is no required method or action order.'


def prepare():
    from tools.research.agent import decision_packet
    previous=read(ROOT/'evidence/s127_decision_probe/manifest.json')
    source=Host(previous['store'],previous['run_id']);sink_id='s127-6a-frozen-'+uuid4().hex[:8]
    sink=Host(ROOT/'runs'/sink_id,sink_id)
    if (OUT/'manifest.json').exists():return read(OUT/'scope.json')
    original=state(source)
    sink.store.create(ProjectConfig(project_id=sink_id,grant_id=sink_id,
        authorization_source='Current task: local probe preparation only; no Provider transfer',
        budget=dict(model_calls=0,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None)))
    cfg=deepcopy(original['base_configuration']);cfg['run_id']=sink_id;sink.create(cfg);sink.resume()
    rows=[]
    names=('candidate_without_results','same_candidate_failed_controls','complete_nmpc_residual_reference')
    for name in names:
        full=next(c for c in previous['cases'] if c['name']==name and c['arm']=='s127_full')
        frozen=frozen_s127(source,full);saved=deepcopy(source.store.artifact(full['state']))
        # Store exact cutoff objects locally; nothing is imported into a Cold-start Study.
        with sink.store.transaction() as db,source.store.connect(True) as src:
            for identity in saved['accessible_artifacts']:
                row=src.execute('SELECT * FROM artifacts WHERE id=?',(identity,)).fetchone()
                db.execute('INSERT OR IGNORE INTO artifacts VALUES ('+','.join('?' for _ in row)+')',tuple(row))
        frozen_ref=save(sink,saved,'s127_6_frozen_state')
        old_wire=source.store.artifact(full['request'])
        for arm in ('full','layered'):
            wire=deepcopy(old_wire);wire['max_tokens']=65536
            if arm=='layered':
                prefix=wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[0]
                wire['messages'][0]['content']=prefix+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(decision_packet(frozen),separators=(',',':'))
            wire['messages'][1]['content']=PROMPT
            packet=json.loads(wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])
            rows.append(dict(name=name,arm=arm,cutoff_sequence=full['cutoff_sequence'],state=frozen_ref,
                request=save(sink,wire,'s127_6_frozen_wire'),wire_identity=digest(wire),
                tool_schema_identity=digest(wire['tools']),rounds=3,history_messages=0,
                initial_scientific_result_count=len(packet['research']['all_fresh_results'])))
    manifest=dict(store=str(sink.store.root),run_id=sink_id,cases=rows,request_ceiling=18,
        original_manifest_identity=digest(previous),max_output_tokens=65536)
    atomic_json(OUT/'manifest.json',manifest)
    scope=dict(stage='S12.7.6A',manifest_identity=digest(manifest),
        endpoint='https://api.deepseek.com/chat/completions',model='deepseek-flash',thinking='enabled',reasoning_effort='high',
        max_output_tokens=65536,request_ceiling=18,automatic_retries=0,new_numerical_executions=0,
        pairs=[dict(name=n,rounds_per_arm=3) for n in names],
        transfer_scope='Three cutoff project scientific states (legal candidate without results, completed physical failures, completed failed NMPC), original task/domain/control and method contracts, registered evidence, budgets and Store-derived views. Both arms have the same task, tools, initial scientific state and budget. The layered arm adds compact citation eligibility. Actual evidence_read may expose original raw physical samples and measured NMPC arrays reachable at the cutoff. No later results, unrelated files or credentials.',
        history_scope='No old chat history. Within each new three-request arm, transmit its own complete assistant reasoning/tool IDs and actual tool feedback unchanged. Never transfer history between arms.',
        local_archive='Full request/response bytes, reasoning and feedback only under ignored runs/s127-6a-decision-20261021 and the local frozen Store recorded in manifest.json. No raw transcript upload.',
        admission_scope='Original typed contracts and real scientific preflight run in disposable local replicas. Numerical workers are intercepted without fabricated outputs. An intercepted early entry is reported separately from full prelaunch admission.',
        publication_scope='Code, derived usage/check statistics, hashes and precise references only.',
        status='awaiting_independent_authorization',independent_authorization_required=True)
    atomic_json(OUT/'scope.json',scope)
    return scope


class NumericalIntercepted(BaseException):
    """Test-only launch barrier, outside workers' ordinary failure/recovery handling."""


def admission_replica(source,case):
    """Disposable local fixture rebinding; preserve original science and budget."""
    from tests.research.test_s127_working_set import historical_host
    saved=source.store.artifact(case['state']);s=deepcopy(saved['state'])
    name='s127-6-admit-'+uuid4().hex[:12];h=Host(ROOT/'runs'/name,s['spec']['study_id'],actor='unified-research')
    config=historical_host().store.config()
    config.update(project_id=name,grant_id=name,authorization_source='S12.7.6 isolated local admission fixture; no numerical worker or Provider permitted')
    h.store.create(ProjectConfig.model_validate(config))
    cfg=deepcopy(s['base_configuration']);cfg['run_id']=h.run_id;h.create(cfg);h.resume()
    history=historical_host()
    with h.store.transaction() as db,source.store.connect(True) as src,history.store.connect(True) as old:
        for identity in saved['accessible_artifacts']:
            row=src.execute('SELECT * FROM artifacts WHERE id=?',(identity,)).fetchone()
            db.execute('INSERT OR IGNORE INTO artifacts VALUES ('+','.join('?' for _ in row)+')',tuple(row))
        for row in old.execute('SELECT * FROM calls'):
            receipt=json.loads(row['receipt']) if row['receipt'] else None
            if receipt and (receipt.get('output') or {}).get('artifact_id') in saved['accessible_artifacts']:
                db.execute('INSERT OR IGNORE INTO calls VALUES ('+','.join('?' for _ in row)+')',tuple(row))
        for e in history.store.events(history.run_id):
            if e['sequence']<=case['cutoff_sequence']:
                # Original event objects remain in the immutable cutoff inventory.
                h.store.event(db,h.run_id,e['kind'],e['status'],request=e.get('request_id'),
                    execution=e.get('execution_id'),inputs=e.get('inputs',[]),outputs=e.get('outputs',[]))
    s.update(core_hashes=core_hashes(),freeze=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    update(h,**s)
    return h,saved['ledger']


def feedback(source,case,call):
    from tools.research import core,analysis,rl
    from tools.research.agent import error_feedback
    frozen=frozen_s127(source,case);name=call['function']['name']
    value=json.loads(call['function']['arguments'])
    if name=='evidence_read':
        with patch('tools.research.core.update'):
            result=core.read_evidence(frozen,value)
        return dict(status='success',evidence=result,full_execution_admission='not_applicable',actual_store_read=True)
    if name=='retrieve_context':
        return dict(status='unavailable',reason='This arm has no SDK offload history',full_execution_admission='not_tested')
    h,ledger=admission_replica(source,case);before=deepcopy(state(h));key='probe-'+uuid4().hex
    def intercept(*args,**kwargs):raise NumericalIntercepted('Numerical worker intercepted after formal prelaunch checks')
    try:
        # The replica has no capability to transmit or start a numerical subprocess.
        with patch.object(h.store,'remaining',return_value=ledger),\
             patch('tools.service_execution._run_contained',side_effect=intercept),\
             patch('tools.research.rl.invoke',side_effect=NumericalIntercepted('RL worker entry intercepted; inner worker checks remain untested')):
            if name=='research_plan':result=core.dispatch(h,value,key)
            elif name=='research_analysis':result=analysis.dispatch(h,value,key,guard=core.guard)
            elif name=='research_rl':result=rl.dispatch(h,value,key)
            else:raise ValueError('UNSCOPED_TOOL')
        actual=result.get('result',result)
        completed=(name=='research_plan' and (
            value['action']=='generate' and actual.get('status')=='generated'
            or value['action']=='initialize_control' and bool(actual.get('source'))
            or value['action']=='stop' and actual.get('accepted_stop') is True))
        return dict(status='checked_in_disposable_replica',full_execution_admission='passed' if completed else 'not_tested',
            original_scientific_state_unchanged=True,scientific_result_added_to_test_state=False,
            note='Only a local non-numerical action completed; its outputs are not inserted into the frozen scientific state')
    except NumericalIntercepted as exc:
        return dict(status='execution_intercepted',full_execution_admission='not_tested' if name=='research_rl' else 'prelaunch_passed',
            remaining_checks=['inner RL worker environment/training checks'] if name=='research_rl' else [],
            scientific_execution_started=False,scientific_observation=None,reason=str(exc))
    except (ValueError,KeyError,IndexError,TypeError) as exc:
        use=dict(toolUseId=call['id'],name=name,input=value)
        return dict(status='rejected',feedback=error_feedback(h,use,exc,before),full_execution_admission='rejected',scientific_observation=None)


async def live(authorization,*,offline=False):
    scope=read(OUT/'scope.json');manifest=read(OUT/'manifest.json')
    if digest(manifest)!=scope['manifest_identity']:raise ValueError('FROZEN_MANIFEST_CHANGED')
    approval=read(authorization) if authorization else {}
    if not offline and (approval.get('stage')!='S12.7.6A' or approval.get('scope_identity')!=digest(scope)
        or approval.get('request_ceiling')!=18 or not approval.get('user_approval')):
        raise ValueError('INDEPENDENT_S127_6A_TRANSFER_AUTHORIZATION_REQUIRED')
    source=Host(manifest['store'],manifest['run_id']);s=source.store.artifact(manifest['cases'][0]['state'])['state']
    run_id='s127-6a-fixture-'+uuid4().hex[:8] if offline else 's127-6a-decision-20261021'
    h=Host(ROOT/'runs'/run_id,run_id)
    if h.store.db.exists():raise ValueError('EXISTING_GRANT_NO_AUTOMATIC_RESEND')
    h.store.create(ProjectConfig(project_id=run_id,grant_id=run_id,
        authorization_source='Explicit synthetic HTTP fixture' if offline else approval['user_approval'],
        budget=dict(model_calls=18,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None),exclusive_resources={'provider_request':1}))
    cfg=deepcopy(s['base_configuration']);cfg['run_id']=run_id;h.create(cfg);h.resume()
    provider=deepcopy(s['pilot']['provider']);provider['max_tokens']=65536
    update(h,pilot=dict(provider=provider,live_model_requests=0))
    if not offline:load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser())
    def synthetic(request):
        wire=json.loads(request.content);packet=json.loads(wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])
        query=packet['research'].get('evidence_access')
        if not isinstance(query,dict):query=dict(reference=packet['research']['all_fresh_results'][0] if packet['research']['all_fresh_results'] else wire_ref[0],view='summary')
        query={k:v for k,v in query.items() if k in ('reference','view','pointer')}
        return httpx.Response(200,json=dict(id='synthetic',model=provider['model'],
            choices=[dict(finish_reason='tool_calls',message=dict(role='assistant',content=None,
                reasoning_content='Explicit synthetic fixture',tool_calls=[dict(id='synthetic-'+str(len(wire['messages'])),type='function',
                    function=dict(name='evidence_read',arguments=json.dumps(query)))]))],usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
    class ScopedBoundary(LiveBoundary):
        async def handle_async_request(self,request):
            secret=os.environ.get('DEEPSEEK_API_KEY')
            if secret and secret.encode() in request.content:raise ValueError('CREDENTIAL_IN_REQUEST_BODY')
            if b'credentials_reference' in request.content:raise ValueError('PRIVATE_RUNTIME_IN_REQUEST_BODY')
            return await super().handle_async_request(request)
    boundary=ScopedBoundary(h,httpx.MockTransport(synthetic) if offline else None);results=[];wire_ref=[None]
    try:
        for case in manifest['cases']:
            wire=deepcopy(source.store.artifact(case['request']));assert digest(wire)==case['wire_identity']
            wire_ref[0]=source.store.artifact(case['state'])['state']['family_space_reference']
            for turn in range(case['rounds']):
                request=httpx.Request('POST',scope['endpoint'],json=wire,
                    headers={} if offline else {'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},
                    extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)})
                response=await boundary.handle_async_request(request);response.raise_for_status()
                body=response.json();message=body['choices'][0]['message'];responses=[];checks=[]
                for call in message.get('tool_calls',[]):
                    try:result=feedback(source,case,call)
                    except (ValueError,KeyError,IndexError,TypeError) as exc:result=dict(status='rejected',error=str(exc),full_execution_admission='rejected')
                    responses.append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(result,separators=(',',':'))))
                    checks.append(dict(tool=call['function']['name'],action=json.loads(call['function']['arguments']).get('action'),
                        status=result['status'],actual_store_read=result.get('actual_store_read',False),
                        full_execution_admission=result['full_execution_admission'],
                        error_code=(result.get('feedback') or {}).get('error_code'),feedback_identity=digest(result)))
                ref=record(h,'s127_6_probe_feedback',dict(case=case['name'],arm=case['arm'],turn=turn,feedback=responses))
                results.append(dict(name=case['name'],arm=case['arm'],turn=turn,request_id=boundary.last_request,
                    wire_identity=digest(wire),usage=body.get('usage'),checks=checks,feedback_reference=ref,
                    previous_tool_feedback_in_request=sum(m['role']=='tool' for m in wire['messages'])))
                boundary.consumed();wire['messages'] += [message,*responses]
                if not responses:wire['messages'].append(dict(role='user',content='Continue from the same state or explain your evidence-based stopping decision.'))
                atomic_json(OUT/('offline.json' if offline else 'results.json'),dict(cases=results,ledger=h.store.remaining(),
                    new_provider_requests=0 if offline else len(results),synthetic_http_requests=len(results) if offline else 0))
        return results
    except IncompleteModelOutput as exc:
        atomic_json(OUT/('offline_blocked.json' if offline else 'blocked.json'),dict(diagnostic=exc.diagnostic,cases=results,
            ledger=h.store.remaining(),new_provider_requests=0 if offline else state(h)['pilot']['live_model_requests']))
        raise
    finally:await boundary.aclose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--authorization',type=Path);args=parser.parse_args()
    if args.prepare:print(prepare())
    elif args.offline or args.authorization:asyncio.run(live(args.authorization,offline=args.offline))
    else:parser.error('Choose --prepare, --offline or --authorization')
