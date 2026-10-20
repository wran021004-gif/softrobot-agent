"""Sealed decision-time snapshots; no solver, workflow dispatch, or archive writes."""
from copy import deepcopy
import json
from unittest.mock import Mock
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json, digest
from tests.research.s8_audit import archive_host

CASES = (('historical_start',34),('fresh_failure',319),('last_exploration_request',450))
OUT = ROOT/'evidence/s12_decision_probe'


def snapshot(sequence, folder='evidence/s11_mirror/study'):
    h,values=archive_host(folder)
    events=[e for e in h.store.events(h.run_id) if e['sequence']<=sequence]
    event=next(e for e in events if e['sequence']==sequence)
    packet=deepcopy(h.store.artifact(event['outputs'][0]))
    # Only objects reachable from already published event inputs/outputs exist here.
    available={}
    def include(value):
        if isinstance(value,dict):
            identity=value.get('artifact_id')
            if isinstance(identity,str) and identity in values and identity not in available:
                available[identity]=values[identity];include(values[identity])
            else:
                for x in value.values():include(x)
        elif isinstance(value,list):
            for x in value:include(x)
    for e in events:include(e.get('inputs',[]));include(e.get('outputs',[]))
    s=deepcopy(state(h));research=packet['research']
    for key in ('results','physical_replays','mechanics_results','analysis_results','control_search_results',
                'matched_state_results','rl_evaluations','plans','research_mathematics','reads','evaluation_reads'):
        s[key]=[r for r in s.get(key,[]) if r['artifact_id'] in available]
    s['candidates']={k:r for k,r in s['candidates'].items() if r['artifact_id'] in available}
    s['control_initializations']=[r for r in s['control_initializations'] if r['source']['artifact_id'] in available]
    s.update(research_status='ready',pending=None,selected=None,final_disposition=None)
    s.pop('success_gate',None)
    for key,value in research['method_used'].items():s[key]=value
    s['physical_replay_launches']=len(s['physical_replays'])
    ledger=deepcopy(h.store.remaining());ledger['remaining']['model_calls']=research['budget']['provider_budget']['remaining_total']
    ledger['remaining']['backend_solves']=research['budget']['science_budget']['remaining_physical']
    ledger['remaining']['tool_calls']=s['spec']['budgets']['public_operations']-sum(e['kind']=='model_original_tool_request' for e in events)
    h.store.session.return_value={'state':s};h.store.events.return_value=events;h.store.remaining.return_value=ledger
    h.store.artifact.side_effect=lambda r,raw=False:available[dict(r)['artifact_id']]
    # Any persistence/dispatch accidentally introduced into this probe fails closed.
    h.store.transaction.side_effect=AssertionError('READ_ONLY_PROBE_NO_WRITES')
    h.store.reserve.side_effect=AssertionError('READ_ONLY_PROBE_NO_RESERVATION')
    return h,packet,available,event


def prepare_s125():
    """Five paired states; raw wires and frozen states remain in an isolated Store."""
    import ast, subprocess, sys
    from types import ModuleType
    from unittest.mock import patch
    from tests.research.test_s125_contract import cold_host
    from tools.research.state import save, update
    from tools.research.agent import plan_schema, decision_packet
    from tools.research.research_context import import_history
    from tools.research.design import generate_candidate
    from tools.state_io import read
    out=ROOT/'evidence/s125_decision_probe';out.mkdir(exist_ok=True)
    if (out/'wire_manifest.json').exists():raise ValueError('FROZEN_PROBE_ALREADY_EXISTS')
    baseline='174cd8c04ede5058cb78ffd91a45fb43f5399cec'
    source=lambda file:subprocess.check_output(['git','show',baseline+':'+file],cwd=ROOT,text=True,encoding='utf8')
    module=ModuleType('s125_baseline_contracts');sys.modules[module.__name__]=module
    exec(compile(source('tools/research/contracts.py'),baseline+'/contracts.py','exec'),module.__dict__)
    node=next(n for n in ast.parse(source('tools/research/agent.py')).body if isinstance(n,ast.FunctionDef) and n.name=='plan_schema')
    namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),baseline+'/plan_schema','exec'),namespace)
    h=cold_host();import_history(h)
    update(h,freeze='decision_only_fixture_no_scientific_dispatch')
    def available_ids():
        with h.store.connect(True) as db:return [r[0] for r in db.execute('SELECT id FROM artifacts')]
    cases=[('empty',deepcopy(state(h)),None,available_ids())]
    generated=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
        segment_count=2,tendon_count=4),dict(origin='isolated_decision_fixture_not_formal_candidate'))
    cases.append(('generated_without_control',deepcopy(state(h)),None,available_ids()))
    # Archived failure/math states never enter the new cold-start Study.
    for name,seq in (('fresh_failure',299),('mathematics_before_physics',121)):
        old,_,available,event=snapshot(seq,'evidence/s12_mirror/study')
        cases.append((name,old,event,list(available)))
    boundary=deepcopy(cases[1][1]);cases.append(('next_request_protected',boundary,None,cases[1][3]))
    archived,_=archive_host('evidence/s12_mirror/study')
    first=next(e for e in archived.store.events(archived.run_id) if e['kind']=='r3_request')
    original=archived.store.artifact(archived.store.artifact(first['outputs'][0])['request'])
    rows=[]
    for name,frozen,event,identities in cases:
        if isinstance(frozen,dict):
            host=h
            with patch('tools.research.agent.state',return_value=frozen),patch('tools.research.research_context.state',return_value=frozen),\
                 patch('tools.research.state.state',return_value=frozen),patch.object(h.store,'session',return_value={'state':frozen}):
                ledger=deepcopy(h.store.remaining())
                if name=='next_request_protected':ledger['remaining']['model_calls']=5
                with patch.object(h.store,'remaining',return_value=ledger):packet=decision_packet(h)
        else:
            host=frozen;frozen=deepcopy(state(host));packet=decision_packet(host);ledger=deepcopy(host.store.remaining())
        packet_ref=save(h,packet,'s125_frozen_probe_packet')
        # Validation state/artifacts are immutable probe evidence, not new science.
        state_ref=save(h,dict(state=frozen,ledger=ledger,accessible_artifacts=identities),'s125_frozen_probe_state')
        if host is not h:
            # Persist only the cutoff's accessible objects, from the checked snapshot.
            _,_,available,_=snapshot(299 if name=='fresh_failure' else 121,'evidence/s12_mirror/study')
            with h.store.transaction() as db:
                for identity,value in available.items():
                    ref=h.store.put(db,value,media='application/octet-stream' if isinstance(value,bytes) else 'application/json')
                    assert ref.artifact_id==identity
        actions=packet['research']['actions']
        for version in ('s12','s125'):
            tools=deepcopy(original['tools'])
            if version=='s125':tools=[t for t in tools if t['function']['name']!='experience_retrieve']
            if name=='next_request_protected':tools=[t for t in tools if t['function']['name'] in ('research_plan','evidence_read','research_rl')]
            for t in tools:
                if t['function']['name']=='research_plan':
                    if version=='s12':
                        with patch('tools.research.contracts.Plan',module.Plan):schema=namespace['plan_schema'](actions)
                    else:schema=plan_schema(actions,decision_required=True)
                    t['function']['parameters']=schema
                if name=='next_request_protected' and t['function']['name']=='research_rl':
                    t['function']['parameters']['properties']['operation']['enum']=[]
            wire={k:deepcopy(v) for k,v in original.items() if k not in ('messages','tools')}
            wire.update(tools=tools,messages=[dict(role='system',content=state(h)['spec']['execution_instructions']+
                '\nCURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))),
                dict(role='user',content='Choose one next research tool request from this frozen state. Execution is intercepted; no scientific calculation or invented success occurs. No later evidence is available.')])
            ref=save(h,wire,'s125_frozen_probe_wire')
            from tests.research.s8_audit import payload
            rows.append(dict(name=name,version=version,request=ref,state=state_ref,packet=packet_ref,
                identity=digest(wire),source_event=event,**payload(wire)))
    manifest=dict(request_ceiling=10,store=str(h.store.root),run_id=h.run_id,baseline=baseline,wires=rows,
        provider=state(h)['pilot']['provider'],new_provider_requests=0,new_scientific_executions=0,
        live_status='awaiting_scoped_external_authorization',admission='partial only; full scientific admission not_tested')
    atomic_json(out/'wire_manifest.json',manifest)
    return manifest


def offline():
    rows=[]
    for name,sequence in CASES:
        h,p,values,event=snapshot(sequence)
        from tools.research.agent import plan_schema
        rows.append(dict(name=name,source='evidence/s11_mirror/study',cutoff_sequence=sequence,
            packet=event['outputs'][0],packet_identity=digest(p),accessible_artifacts=len(values),
            remaining=h.store.remaining()['remaining'],original_actions=p['research']['actions'],
            next_request_will_protect=p['research']['budget']['closeout']['next_request_will_protect'],
            contract_identity=digest(plan_schema(state(h)['spec']['allowed_plan_actions']))))
    result=dict(version='s12_decision_probe_v1',states=rows,provider_request_ceiling=6,
        sampling='Three identical states x old/new, one response each; no invented tool success or follow-up',
        new_provider_requests=0,new_scientific_executions=0,
        boundary='In-memory hash-verified archive subset; no dispatch, reserve, transaction or scientific callback',
        live_status='not_tested',limitation='Offline archive replay is not a newly sampled model decision')
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'frozen_cases.json',result)
    return result


def validate(h,tool):
    from tools.research.contracts import Plan,EvidenceQuery,AnalysisRequest,RLRequest
    from tools.research.evidence_policy import admit_decision
    from tools.research.budget import decision_budget,closeout_operations
    from tools.research.mechanics import warm_start
    name=tool['function']['name'];q=json.loads(tool['function']['arguments'])
    outcome=dict(tool=name,request=q,scientific_execution_started=False,full_execution_admission='not_tested')
    try:
        if name=='research_plan':
            p=Plan.model_validate(q);admit_decision(h,p)
            if decision_budget(h)['closeout']['next_request_will_protect'] and p.action not in closeout_operations(h)['research_plan']:
                raise ValueError('POST_REQUEST_PROTECTED_CLOSEOUT')
            if p.mechanics:warm_start(h,p.mechanics)
        elif name=='evidence_read':
            p=EvidenceQuery.model_validate(q);v=h.store.artifact(p.reference)
            for key in p.pointer.strip('/').split('/') if p.pointer else []:
                key=key.replace('~1','/').replace('~0','~');v=v[int(key)] if isinstance(v,list) else v[key]
            if p.view=='fields':
                for field in p.fields:v[field]
            if p.view=='range' and not isinstance(v,list):raise ValueError('EVIDENCE_RANGE_REQUIRES_LIST_POINTER')
        else:
            (AnalysisRequest if name=='research_analysis' else RLRequest).model_validate(q)
            if decision_budget(h)['closeout']['next_request_will_protect']:raise ValueError('POST_REQUEST_PROTECTED_CLOSEOUT')
        outcome.update(contract_and_reference_checks='passed',error=None)
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        outcome.update(contract_and_reference_checks='rejected',error=str(exc))
    return outcome


def prepare_wires():
    from tools.research.agent import plan_schema
    from tools.research.research_context import context,decision_brief
    archived,values=archive_host('evidence/s11_mirror/study')
    first=next(e for e in archived.store.events(archived.run_id) if e['kind']=='r3_request')
    original=archived.store.artifact(archived.store.artifact(first['outputs'][0])['request'])
    instructions=original['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[0]
    wires=[]
    for name,sequence in CASES:
        for version in ('s11','s12'):
            h,packet,available,event=snapshot(sequence)
            if version=='s12':packet['research']=decision_brief(context(h))
            tools=deepcopy(original['tools']);actions=packet['research']['actions']
            if version=='s12' and packet['research']['budget']['closeout']['next_request_will_protect']:
                tools=[t for t in tools if t['function']['name'] in ('research_plan','evidence_read')]
            for t in tools:
                if t['function']['name']=='research_plan':t['function']['parameters']=plan_schema(actions)
            wire={k:deepcopy(v) for k,v in original.items() if k not in ('messages','tools')}
            wire.update(tools=tools,messages=[dict(role='system',content=instructions+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))),
                dict(role='user',content='Choose your next research action using this frozen decision-time evidence. Submit one tool request. All execution is intercepted by this decision-only test; no scientific result will be invented. No later evidence is available.')])
            filename=name+'_'+version+'.json';atomic_json(OUT/filename,wire)
            wires.append(dict(name=name,version=version,sequence=sequence,file=filename,identity=digest(wire)))
    atomic_json(OUT/'wire_manifest.json',dict(request_ceiling=6,wires=wires,model=original['model'],same_configuration=True))
    return wires


async def live(s125_authorization=None):
    import httpx,os
    from pathlib import Path
    from schemas.platform import ProjectConfig
    from tools.platform_host import Host
    from tools.research.agent import LiveBoundary,load_credential
    from tools.research.state import update
    from tools.state_io import read
    destination=ROOT/'evidence/s125_decision_probe' if s125_authorization else OUT
    manifest=read(destination/'wire_manifest.json');rows=manifest['wires']
    if s125_authorization:
        authority=read(s125_authorization)
        if authority.get('endpoint')!='https://api.deepseek.com' or authority.get('probe_request_ceiling')!=10 or not authority.get('user_approval'):
            raise ValueError('EXPLICIT_S125_SCOPED_EXTERNAL_APPROVAL_REQUIRED')
        source=Host(manifest['store'],manifest['run_id'])
        s=state(source);run_id='s125-decision-probe-20261020';ceiling=10
        authorization=authority['user_approval']
    else:
        source,p,values,event=snapshot(34);s=state(source)
        run_id='s12-decision-probe-20261020';ceiling=6
        authorization='User S12: six frozen DeepSeek decision-only requests; project task, evidence, contracts and budgets only; no scientific dispatch'
    h=Host(ROOT/'runs/research'/run_id,run_id)
    if h.store.db.exists():raise ValueError('PROBE_LEDGER_ALREADY_EXISTS_NO_AUTOMATIC_RESEND')
    h.store.create(ProjectConfig(project_id=run_id,grant_id=run_id+'-authorized',
        authorization_source=authorization,
        budget=dict(model_calls=ceiling,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None),exclusive_resources={'provider_request':1}))
    cfg=deepcopy(s['base_configuration']);cfg['run_id']=run_id;h.create(cfg);h.resume()
    update(h,pilot=dict(provider=s['pilot']['provider'],live_model_requests=0))
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser())
    boundary=LiveBoundary(h);results=[]
    try:
        for row in rows:
            wire=source.store.artifact(row['request']) if s125_authorization else read(OUT/row['file'])
            assert digest(wire)==row['identity']
            request=httpx.Request('POST',s['pilot']['provider']['base_url']+'/chat/completions',json=wire,
                headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY']},extensions={'timeout':{'connect':30,'read':600,'write':30,'pool':30}})
            response=await boundary.handle_async_request(request);body=response.json()
            if s125_authorization:
                from types import SimpleNamespace
                saved=source.store.artifact(row['state']);store=Mock()
                store.session.return_value={'state':saved['state']};store.remaining.return_value=saved['ledger']
                def artifact(ref,raw=False):
                    if dict(ref)['artifact_id'] not in saved['accessible_artifacts']:raise ValueError('PROBE_FUTURE_OR_UNSCOPED_ARTIFACT')
                    return source.store.artifact(ref,raw=raw)
                store.artifact.side_effect=artifact
                store.transaction.side_effect=AssertionError('NO_PROBE_WRITES')
                store.reserve.side_effect=AssertionError('NO_PROBE_SCIENCE')
                frozen=SimpleNamespace(store=store,run_id=saved['state']['spec']['study_id'])
            else:
                atomic_json(OUT/(row['name']+'_'+row['version']+'_response.json'),body)
                frozen,_,_,_=snapshot(row['sequence'])
            results.append(dict(**row,usage=body.get('usage'),http_status=response.status_code,
                proposals=[validate(frozen,t) for c in body.get('choices',[]) for t in c['message'].get('tool_calls',[])]))
            boundary.consumed();atomic_json(destination/'live_results.json',dict(results=results,ledger=h.store.remaining(),
                new_scientific_executions=0,full_scientific_admission='not_tested; no dispatch or fabricated result',
                limitation='One turn per case/interface; valid evidence queries are not research actions; legality is separate from method quality'))
    finally:await boundary.aclose()


if __name__=='__main__':
    import sys,asyncio
    if '--s125' in sys.argv:
        if '--live' in sys.argv:
            if '--authorization' not in sys.argv:raise ValueError('EXPLICIT_S125_AUTHORIZATION_FILE_REQUIRED')
            asyncio.run(live(sys.argv[sys.argv.index('--authorization')+1]))
        else:prepare_s125();print('Frozen 5 states x 2 interfaces; ten requests; zero scientific execution')
    elif '--live' in sys.argv:asyncio.run(live())
    else:offline();prepare_wires();print('Frozen 3 states x 2 interfaces; six requests; zero scientific execution')
