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


def baseline_module(name,baseline=BASE):
    module=ModuleType('s126_baseline_'+name)
    source=subprocess.check_output(['git','show',baseline+':tools/research/'+name+'.py'],cwd=ROOT,encoding='utf8')
    exec(compile(source,baseline+'/'+name+'.py','exec'),module.__dict__)
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


def prepare_s127():
    """Reuse the existing cutoff snapshots, wire Store and intercepted probe scope."""
    from tools.research.agent import decision_packet, plan_schema
    import hashlib
    from tools.research.contracts import EvidenceQuery
    from extensions.tendon_family.control_evidence import ControlEvidence
    from tests.research.test_s127_working_set import historical_host
    destination=ROOT/'evidence/s127_decision_probe'
    previous=read(destination/'manifest.json') if (destination/'manifest.json').exists() else None
    if previous and (previous['new_provider_requests'] or (destination/'live_results.json').exists()):raise ValueError('EXECUTED_S127_PROBE_CANNOT_BE_REFROZEN')
    sink=cold_host();source=historical_host();old=baseline_module('research_context','bd31326296afb6daace6db5afb1205daa8e01841')
    superseded=save(sink,previous,'unexecuted_s127_probe_draft') if previous else None
    cases=[('candidate_without_results',128),('invalid_math_correction',144),('same_candidate_failed_controls',473),
        ('fixed_failure_near_protection',637),('complete_nmpc_residual_reference',556),('independent_session_boundary',556)]
    first=next(e for e in source.store.events(source.run_id) if e['kind']=='r3_request')
    template=source.store.artifact(source.store.artifact(first['outputs'][0])['request']);rows=[]
    for name,sequence in cases:
        frozen,_,available,event=snapshot(sequence,'evidence/s126_cold/study');s=state(frozen)
        cutoff_events=frozen.store.events.return_value
        frozen.store.connect.side_effect=source.store.connect
        frozen.store.events.side_effect=lambda run,events=cutoff_events:events if run==source.run_id else source.store.events(run)
        # Make only known completed executions' immutable backend measurements readable.
        for ref in s.get('results',[]):
            result=source.store.artifact(ref);backend=ControlEvidence(source.store).resolve(result['execution_id'])
            for r in [backend['manifest'],backend['metadata']['candidate_input'],{'artifact_id':backend['metadata']['artifact_id']},*backend['files'].values()]:
                available[r['artifact_id']]=source.store.artifact(r,raw=r.get('media_type','application/json')!='application/json')
        frozen.store.artifact.side_effect=lambda ref,raw=False,a=available:a[plain_id(ref)]
        # The source cache is filtered to results that already exist at the cutoff.
        s['compatible_residual_references']=[r for r in s.get('compatible_residual_references',[]) if r['source'] in s['results']+s['mechanics_results']]
        if name=='fixed_failure_near_protection':frozen.store.remaining.return_value['remaining']['model_calls']=5
        new_packet=decision_packet(frozen)
        with patch('tools.research.research_context.decision_brief',side_effect=lambda c:old.decision_brief(old.context(frozen))):prior=decision_packet(frozen)
        assert prior['research']['all_fresh_results']==new_packet['research']['all_fresh_results']
        with sink.store.transaction() as db:
            for identity,value in available.items():
                ref=sink.store.put(db,value,media='application/octet-stream' if isinstance(value,bytes) else 'application/json')
                assert ref.artifact_id==identity
        frozen_ref=save(sink,dict(state=s,ledger=frozen.store.remaining(),accessible_artifacts=list(available)), 's127_frozen_probe_state')
        tools=deepcopy(template['tools'])
        for tool in tools:
            if tool['function']['name']=='research_plan':tool['function']['parameters']=plan_schema(new_packet['research']['actions'],decision_required=True)
            if tool['function']['name']=='evidence_read':tool['function']['parameters']=EvidenceQuery.model_json_schema()
        for arm,packet in (('s127_full',prior),('layered',new_packet)):
            wire={k:deepcopy(v) for k,v in template.items() if k not in ('messages','tools')}
            wire.update(max_tokens=8192,tools=deepcopy(tools),messages=[dict(role='system',content=s['spec']['execution_instructions']+
                '\nCURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))),dict(role='user',content=
                'Choose one next research tool using this frozen evidence. Scientific execution is intercepted. Full scientific admission is not_tested until checked. No adaptive additional request is authorized.')])
            ref=save(sink,wire,'s127_frozen_probe_wire')
            rows.append(dict(name=name,arm=arm,cutoff_sequence=sequence,state=frozen_ref,request=ref,identity=digest(wire),
                experiment='session_protocol_separate_no_compression_causality_claim' if name=='independent_session_boundary' else 'layered_context_pair',
                decision_context_bytes=payload(wire)['serialized_bytes']['current_packet'],**payload(wire)))
    manifest=dict(status='frozen_offline_independent_authorization_required',request_ceiling=12,automatic_retries=0,
        endpoint='https://api.deepseek.com',model=template['model'],max_output_tokens_per_request=8192,
        store=str(sink.store.root),run_id=sink.run_id,baseline='bd31326296afb6daace6db5afb1205daa8e01841',
        cases=rows,scientific_execution='intercepted; full admission not_tested',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'tools/research').glob('*.py')},
        superseded_unexecuted_draft=superseded,
        data_scope='Six exact frozen project states, their candidate/task/evidence references and tool schemas, system/user instructions only. No unrelated files, credentials or old complete chat history.',
        actual_prompt_tokens=None,actual_completion_tokens=None,cache_hit_tokens=None,cache_miss_tokens=None,
        new_provider_requests=0,new_scientific_executions=0,legal_proposals=None,first_scientifically_admissible_proposal=None,
        effective_evidence_deliveries=None,unnecessary_detail_reads=None,
        publication_scope='Only metadata/byte counts/hashes. Raw wires and raw responses are not authorized for GitHub upload.')
    manifest['frozen_manifest_identity']=digest(manifest)
    atomic_json(destination/'manifest.json',manifest)
    return manifest


S127_ID='330d4b06ec479abcf97a08996430ed601de6cf751bd6c4cd1eee609571929c6a'
S127_OUT=ROOT/'evidence/s127_4_decision'


def audit_s127():
    """Read the original frozen wires, never regenerate or amend the experiment."""
    import re
    from tools.platform_host import Host
    manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json')
    unsigned=dict(manifest);unsigned.pop('frozen_manifest_identity')
    if digest(unsigned)!=S127_ID or manifest['frozen_manifest_identity']!=S127_ID:
        raise ValueError('FROZEN_S127_MANIFEST_CHANGED')
    source=Host(manifest['store'],manifest['run_id']);rows=[]
    assert len(manifest['cases'])==manifest['request_ceiling']==12 and manifest['automatic_retries']==0
    for case in manifest['cases']:
        wire=source.store.artifact(case['request']);saved=source.store.artifact(case['state'])
        assert digest(wire)==case['identity']
        assert set(wire)=={'model','messages','tools','max_tokens','stream','thinking','reasoning_effort'}
        assert wire['model']=='deepseek-flash' and wire['max_tokens']==8192 and wire['stream'] is False
        assert wire['thinking']=={'type':'enabled'} and wire['reasoning_effort']=='high'
        assert [m['role'] for m in wire['messages']]==['system','user']
        text=json.dumps(wire)
        assert not re.search(r'DEEPSEEK_API_KEY|credentials_reference|api_key|Authorization|\.env\b|C:\\\\Users',text,re.I)
        packet=json.loads(wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])
        rows.append(dict(name=case['name'],arm=case['arm'],wire_identity=case['identity'],state=case['state'],
            tool_schema_identity=digest(wire['tools']),tool_names=[t['function']['name'] for t in wire['tools']],
            roles=['system','user'],history_messages=0,accessible_artifact_count=len(saved['accessible_artifacts']),
            scientific_result_count=len(packet['research']['all_fresh_results']),bytes=case['total_bytes'],
            credentials_or_unrelated_file_content_found=False))
    for a,b in zip(rows[::2],rows[1::2]):
        assert a['name']==b['name'] and a['state']==b['state'] and a['tool_schema_identity']==b['tool_schema_identity']
        wires=[source.store.artifact(c['request']) for c in manifest['cases'] if c['name']==a['name']]
        packets=[json.loads(w['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])['research'] for w in wires]
        assert all(packets[0][k]==packets[1][k] for k in ('task','actions','all_fresh_results'))
        assert all(packets[0]['budget'][k]==packets[1]['budget'][k] for k in packets[0]['budget'])
    result=dict(stage='S12.7.4A',status='not_run',frozen_manifest_identity=S127_ID,endpoint=manifest['endpoint'],
        model=manifest['model'],request_ceiling=12,max_output_tokens=8192,automatic_retries=0,cases=rows,
        transfer_scope='Only the 12 exact hash-verified system/user request bodies: frozen project task, family/design/control descriptions, scientific evidence summaries/references, budgets and five tool schemas. No prior assistant/tool history or unrelated files. API key is an authentication header only and is never stored in request artifacts.',
        isolation='Only read evidence or check a proposal; no dispatch, worker, NMPC, physics or PPO. All execution admission remains not_tested.',
        evidence_read_limit='One request per arm. A requested detail can be read locally but cannot be delivered to the model in a later request within this frozen design. Effective new detail deliveries are zero; retrieval benefit and adaptive token cost are unmeasured.',
        sixth_pair='Separate independent-session condition; exclude from compression-only totals. Both frozen wires contain no assistant/tool history; no SDK continuation claim.',
        new_provider_requests=0,actual_tokens=None,
        official_protocol_sources=['https://api-docs.deepseek.com/guides/thinking_mode/','https://api-docs.deepseek.com/api/create-chat-completion/'],
        availability='Official documentation checked 2026-10-21: deepseek-flash, thinking enabled, high effort, tools and non-streaming Chat Completions are documented. Account availability not tested before scoped approval.',
        publication_scope='Derived metadata, hashes, statistics and code only. Raw prompts/responses/reasoning, full Store and SDK files remain under ignored runs/.')
    atomic_json(S127_OUT/'scope.json',result)
    return result


def frozen_s127(source,case):
    from tests.research.test_s127_working_set import historical_host
    saved=source.store.artifact(case['state']);store=Mock()
    store.session.return_value=dict(state=deepcopy(saved['state']));store.remaining.return_value=deepcopy(saved['ledger'])
    def artifact(ref,raw=False):
        if plain_id(ref) not in saved['accessible_artifacts']:raise ValueError('UNSCOPED_EVIDENCE')
        return source.store.artifact(ref,raw=raw)
    store.artifact.side_effect=artifact
    history=historical_host()
    store.connect.side_effect=lambda *args,**kwargs:history.store.connect(True)
    store.events.side_effect=lambda run:[e for e in history.store.events(run)
        if run!=history.run_id or e['sequence']<=case['cutoff_sequence']]
    store.reserve.side_effect=store.transaction.side_effect=AssertionError('NO_SCIENTIFIC_EXECUTION')
    return SimpleNamespace(store=store,run_id=saved['state']['spec']['study_id'])


def check_s127(host,call):
    """Partial, side-effect-free checks; never claim scientific dispatch admission."""
    name=call['function']['name']
    if name=='evidence_read':
        from tools.research.contracts import EvidenceQuery
        from tools.research.core import read_evidence
        try:
            q=EvidenceQuery.model_validate_json(call['function']['arguments'])
            with patch('tools.research.core.update'):
                value=read_evidence(host,q)
            return dict(tool=name,contract_and_reference_checks='passed',local_read=True,
                working_set=q.view=='working_set',provided_to_model=False,read_value_identity=digest(value),
                full_execution_admission='not_tested',scientific_execution_started=False)
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            return dict(tool=name,contract_and_reference_checks='rejected',error=str(exc),
                full_execution_admission='not_tested',scientific_execution_started=False)
    if name=='retrieve_context':
        return dict(tool=name,contract_and_reference_checks='not_tested',
            reason='No SDK offload history exists in this frozen single-request arm',full_execution_admission='not_tested')
    checked=validate(host,call)
    # Raw proposed arguments are archived locally only.
    return {k:v for k,v in checked.items() if k!='request'}


async def live_s127(authorization):
    import httpx
    from tools.platform_host import Host
    from schemas.platform import ProjectConfig
    from tools.research.agent import LiveBoundary,load_credential,record
    scope=audit_s127();approval=read(authorization)
    if (approval.get('stage')!='S12.7.4A' or approval.get('frozen_manifest_identity')!=S127_ID
        or approval.get('scope_identity')!=digest(scope) or approval.get('request_ceiling')!=12
        or approval.get('endpoint')!=scope['endpoint'] or not approval.get('user_approval')):
        raise ValueError('INDEPENDENT_S127_4A_TRANSFER_AUTHORIZATION_REQUIRED')
    manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json');source=Host(manifest['store'],manifest['run_id'])
    run='s127-4a-decision-20261021';h=Host(ROOT/'runs'/run,run)
    if h.store.db.exists():raise ValueError('EXISTING_LIVE_GRANT_NO_AUTOMATIC_RESEND')
    h.store.create(ProjectConfig(project_id=run,grant_id=run,authorization_source=approval['user_approval'],
        budget=dict(model_calls=12,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None),exclusive_resources={'provider_request':1}))
    original=state(source);cfg=deepcopy(original['base_configuration']);cfg['run_id']=run;h.create(cfg);h.resume()
    provider=deepcopy(original['pilot']['provider']);provider['max_tokens']=8192
    update(h,pilot=dict(provider=provider,live_model_requests=0))
    load_credential(Path(original['spec']['runtime']['credentials_reference']).expanduser())
    boundary=LiveBoundary(h);results=[]
    try:
        for case in manifest['cases']:
            wire=source.store.artifact(case['request']);assert digest(wire)==case['identity']
            response=await boundary.handle_async_request(httpx.Request('POST',scope['endpoint']+'/chat/completions',json=wire,
                headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)}))
            response.raise_for_status();body=response.json();message=body['choices'][0]['message']
            frozen=frozen_s127(source,case)
            checks=[check_s127(frozen,c) for c in message.get('tool_calls',[])]
            raw=record(h,'s127_4a_local_checks',dict(case=case['name'],arm=case['arm'],checks=checks))
            results.append(dict(name=case['name'],arm=case['arm'],request_id=boundary.last_request,
                provider_response_id=body.get('id'),actual_model=body.get('model'),request_model=wire['model'],
                wire_identity=case['identity'],tool_schema_identity=digest(wire['tools']),raw_checks_reference=raw,
                usage=body.get('usage'),checks=checks,full_execution_admission='not_tested',
                effective_new_evidence_deliveries=0,unnecessary_detail_reads=None,critical_fact_omissions=None))
            boundary.consumed()
            atomic_json(S127_OUT/'results.json',dict(status='partial' if len(results)<12 else 'completed',cases=results,
                ledger=h.store.remaining(),new_scientific_executions=0,
                compression_only_cases=[r for r in results if r['name']!='independent_session_boundary']))
    finally:await boundary.aclose()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',type=Path);parser.add_argument('--prepare-s127',action='store_true')
    parser.add_argument('--audit-s127',action='store_true');parser.add_argument('--s127-authorization',type=Path);args=parser.parse_args()
    if args.audit_s127:print(json.dumps(audit_s127()))
    elif args.s127_authorization:asyncio.run(live_s127(args.s127_authorization))
    elif args.prepare_s127:print(json.dumps(prepare_s127()))
    elif args.authorization:asyncio.run(live(args.authorization))
    else:print(json.dumps(prepare()))
