"""Finite paired multi-turn decision probes; all scientific execution intercepted."""
from copy import deepcopy
import asyncio, json, os, subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch
from tools.research.config import ROOT
from tools.research.state import state, update, save
from tools.state_io import read, atomic_json, digest
from tests.research.s8_audit import archive_host, payload
from tests.research.s12_decision_probe import snapshot, validate
from tests.research.test_s125_contract import cold_host

OUT=ROOT/'evidence/s126_decision_probe'
BASE='3e370ab7adc97deadb0f2d5b0bc641280774bf1a'


def baseline_module(name):
    module=ModuleType('s126_baseline_'+name)
    source=subprocess.check_output(['git','show',BASE+':tools/research/'+name+'.py'],cwd=ROOT,encoding='utf8')
    exec(compile(source,BASE+'/'+name+'.py','exec'),module.__dict__)
    return module


def prepare():
    from tools.research.agent import decision_packet, plan_schema
    from tools.research.design import generate_candidate
    from tools.research.physical_replay import seed_control
    from tools.research.contracts import ControlSeedRequest
    from extensions.tendon_family.family_space import decision_summary
    if (OUT/'manifest.json').exists():raise ValueError('FROZEN_PROBE_EXISTS')
    h=cold_host();update(h,freeze='s126_isolated_decision_fixture')
    def ids():
        with h.store.connect(True) as db:return [r[0] for r in db.execute('SELECT id FROM artifacts')]
    cases=[('empty',deepcopy(state(h)),ids(),None)]
    generation=dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
        segment_count=2,tendon_count=4,spans=[dict(last_segment=1,count=4,angular_offsets_rad=[0,-1.5707963267948966,0,0])])
    failure=generate_candidate(h,generation,dict(origin='isolated_geometry_fixture'))
    cases.append(('geometry_failure',deepcopy(state(h)),ids(),failure))
    generation['spans']=[];candidate=generate_candidate(h,generation,dict(origin='isolated_geometry_fixture'))['candidate']
    cases.append(('valid_without_control',deepcopy(state(h)),ids(),None))
    seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'))
    cases.append(('valid_with_control',deepcopy(state(h)),ids(),None))
    old,_=archive_host('evidence/s125_cold/study')
    event=next(e for e in old.store.events(old.run_id) if e['kind']=='model_decision_packet' and
        old.store.artifact(e['outputs'][0])['research'].get('latest_scientific_feedback'))
    historic,_,available,_=snapshot(event['sequence'],'evidence/s125_cold/study')
    with h.store.transaction() as db:
        for identity,value in available.items():
            ref=h.store.put(db,value,media='application/octet-stream' if isinstance(value,bytes) else 'application/json')
            assert ref.artifact_id==identity
    cases.append(('physical_failure',historic,list(available),None))
    cases.append(('near_closeout',deepcopy(cases[3][1]),cases[3][2],None))
    original_event=next(e for e in old.store.events(old.run_id) if e['kind']=='r3_request')
    original=old.store.artifact(old.store.artifact(original_event['outputs'][0])['request'])
    old_context=baseline_module('research_context');old_budget=baseline_module('budget');rows=[]
    for name,frozen,accessible,failed in cases:
        host=h if isinstance(frozen,dict) else frozen
        frozen=frozen if isinstance(frozen,dict) else deepcopy(state(host))
        ledger=deepcopy(host.store.remaining())
        if name=='near_closeout':ledger['remaining']['model_calls']=5
        with patch.object(host.store,'session',return_value=dict(state=frozen)),patch.object(host.store,'remaining',return_value=ledger):
            packet=decision_packet(host)
            with patch('tools.research.research_context.context',side_effect=old_context.context),patch('tools.research.budget.decision_budget',side_effect=old_budget.decision_budget):
                prior=decision_packet(host)
            prior['family_space'].pop('angular_semantics',None)
        for version,current in (('s125',prior),('s126',packet)):
            if failed:
                current['latest_generation_feedback']=failed if version=='s126' else {k:failed[k] for k in ('status','reason','candidate','task_success')}
            actions=current['research']['actions'];tools=deepcopy(original['tools'])
            tools=[t for t in tools if t['function']['name']!='experience_retrieve' and
                (name!='near_closeout' or t['function']['name'] in ('research_plan','evidence_read'))]
            for tool in tools:
                if tool['function']['name']=='research_plan':
                    tool['function']['parameters']=plan_schema(actions,decision_required=True)
                    if version=='s125':tool['function']['parameters'].get('$defs',{}).get('Span',{}).get('properties',{}).get('angular_offsets_rad',{}).pop('description',None)
            wire={k:v for k,v in original.items() if k not in ('messages','tools')}
            wire.update(tools=tools,messages=[dict(role='system',content=frozen['spec']['execution_instructions']+
                '\nCURRENT_RESEARCH_PACKET\n'+json.dumps(current,separators=(',',':'))),dict(role='user',content=
                'Choose research tools freely using this frozen evidence. Scientific execution is intercepted. You may read real evidence or check a generation request. No scientific success is fabricated. Consume tool feedback and choose again when a second round is available.')])
            rows.append(dict(name=name,version=version,request=save(h,wire,'s126_probe_wire'),identity=digest(wire),
                state=save(h,dict(state=frozen,ledger=ledger,accessible_artifacts=accessible),'s126_probe_state'),
                rounds=2 if name in ('geometry_failure','valid_with_control','physical_failure') else 1,**payload(wire)))
    manifest=dict(request_ceiling=18,checkpoint_request_ceiling=2,total_provider_ceiling=20,baseline=BASE,
        store=str(h.store.root),run_id=h.run_id,cases=rows,endpoint='https://api.deepseek.com',
        live_status='awaiting_new_scoped_authorization',scientific_dispatch='intercepted',new_provider_requests=0,
        checkpoint_admission='not_admitted; separate actual continuation and recovery gates required')
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'manifest.json',manifest)
    return manifest


async def live(authorization):
    """Use the existing accounted boundary. Never dispatch a scientific operation."""
    import httpx
    from tools.platform_host import Host
    from schemas.platform import ProjectConfig
    from tools.research.agent import LiveBoundary, load_credential, record
    from tools.research.contracts import EvidenceQuery
    from tools.research.core import read_evidence
    from extensions.tendon_family.generated_serial import generate_family
    manifest=read(OUT/'manifest.json');approval=read(authorization)
    if approval.get('endpoint')!=manifest['endpoint'] or approval.get('probe_request_ceiling')!=20 or not approval.get('user_approval'):
        raise ValueError('NEW_S126_EXTERNAL_AUTHORIZATION_REQUIRED')
    source=Host(manifest['store'],manifest['run_id']);s=state(source)
    run_id='s126-decision-probe-20261020';h=Host(ROOT/'runs/research'/run_id,run_id)
    if h.store.db.exists():raise ValueError('EXISTING_PROBE_REQUIRES_EXACT_SAVED_REQUEST_RECOVERY_NO_RESEND')
    h.store.create(ProjectConfig(project_id=run_id,grant_id=run_id,authorization_source=approval['user_approval'],
        budget=dict(model_calls=20,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None),exclusive_resources={'provider_request':1}))
    cfg=deepcopy(s['base_configuration']);cfg['run_id']=run_id;h.create(cfg);h.resume()
    update(h,pilot=dict(provider=s['pilot']['provider'],live_model_requests=0))
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser())
    boundary=LiveBoundary(h);results=[]
    try:
        for case in manifest['cases']:
            wire=deepcopy(source.store.artifact(case['request']));assert digest(wire)==case['identity']
            saved=source.store.artifact(case['state']);store=Mock()
            store.session.return_value=dict(state=saved['state']);store.remaining.return_value=saved['ledger']
            def artifact(ref,raw=False):
                if plain_id(ref) not in saved['accessible_artifacts']:raise ValueError('UNSCOPED_EVIDENCE')
                return source.store.artifact(ref,raw=raw)
            store.artifact.side_effect=artifact
            store.transaction.side_effect=AssertionError('NO_SCIENCE');store.reserve.side_effect=AssertionError('NO_SCIENCE')
            frozen=SimpleNamespace(store=store,run_id=saved['state']['spec']['study_id'])
            for turn in range(case['rounds']):
                response=await boundary.handle_async_request(httpx.Request('POST',manifest['endpoint']+'/chat/completions',json=wire,
                    headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},extensions={'timeout':{'connect':30,'read':600,'write':30,'pool':30}}))
                response.raise_for_status();body=response.json();message=body['choices'][0]['message'];feedback=[]
                for call in message.get('tool_calls',[]):
                    checked=validate(frozen,call);q=checked['request'];name=call['function']['name']
                    value=dict(intercepted=True,checks=checked,scientific_observation=None)
                    if checked['contract_and_reference_checks']=='passed':
                        try:
                            if name=='evidence_read':
                                # Same public pointer/view semantics; suppress only read bookkeeping in the frozen fixture.
                                with patch('tools.research.core.update'):value['evidence']=read_evidence(frozen,EvidenceQuery.model_validate(q))
                            if name=='research_plan' and q['action']=='generate':
                                generate_family(dict(space=saved['state']['spec']['family_space'],request=q['generation']))
                                value['construction_check']='valid; not registered or evaluated'
                        except (ValueError,KeyError,TypeError) as exc:
                            value['check_error']=str(exc)
                            if case['version']=='s126':value['diagnostic']=getattr(exc,'diagnostic',None)
                    feedback.append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(value,separators=(',',':'))))
                record(h,'s126_probe_feedback',dict(case=case['name'],version=case['version'],turn=turn,feedback=feedback))
                results.append(dict(name=case['name'],version=case['version'],turn=turn,usage=body.get('usage'),proposals=[validate(frozen,c) for c in message.get('tool_calls',[])]))
                boundary.consumed();atomic_json(OUT/'live_results.json',dict(results=results,ledger=h.store.remaining(),new_scientific_executions=0))
                wire['messages'] += [message,*feedback]
                if not feedback:wire['messages'].append(dict(role='user',content='Continue from the same frozen state; choose a legal research tool. No science has executed.'))
            if case['name']=='valid_with_control' and case['version']=='s126':
                comparison_wire=deepcopy(wire)
        # Same unchanged science packet/capabilities, with versus without the actual probe history.
        # HTTP dialogue experiment only; this does not admit production SDK checkpoint recovery.
        for arm in ('continuous','independent'):
            wire=deepcopy(comparison_wire)
            if arm=='independent':wire['messages']=wire['messages'][:2]
            record(h,'s126_protocol_comparison',dict(arm=arm,source_science_state='valid_with_control',
                protocol='Independent HTTP dialogue; SDK crash recovery admission remains separate'))
            response=await boundary.handle_async_request(httpx.Request('POST',manifest['endpoint']+'/chat/completions',json=wire,
                headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},extensions={'timeout':{'connect':30,'read':600,'write':30,'pool':30}}))
            response.raise_for_status();body=response.json()
            results.append(dict(name='context_comparison',version=arm,usage=body.get('usage'),
                scientific_execution_started=False,full_execution_admission='not_tested'))
            boundary.consumed();atomic_json(OUT/'live_results.json',dict(results=results,ledger=h.store.remaining(),
                new_scientific_executions=0,checkpoint_admission='not_admitted'))
    finally:await boundary.aclose()


def plain_id(ref):
    from tools.platform_store import plain
    return plain(ref)['artifact_id']


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',type=Path);args=parser.parse_args()
    if args.authorization:asyncio.run(live(args.authorization))
    else:print(json.dumps(prepare()))
