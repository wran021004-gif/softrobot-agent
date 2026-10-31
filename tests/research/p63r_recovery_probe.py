"""Explicit offline V1 clone/SDK recovery probe. Never opens a live transport."""
import argparse,asyncio,json,os,shutil,sqlite3,time,zipfile
from pathlib import Path
from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import patch
import httpx
from tools.platform_host import Host
from tools.platform_store import Store
from tools.research.agent import converse
from tools.research.state import state
from tools.research.config import ROOT
from tools.research.session_handoff import session_storage_path,snapshot_files

RUN='p63v1-m3-autonomous-feasibility-sol-20261030'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--migrate',action='store_true')
    parser.add_argument('--expected-provider',type=int,default=24);parser.add_argument('--expected-math',type=int,default=94)
    parser.add_argument('--expect-scope',action='store_true')
    parser.add_argument('--source-store',type=Path,help='Explicit immutable pre-R checkpoint for offline testing only; never a live replacement')
    parser.add_argument('--configuration-archive',type=Path,help='Original matching archive when the offline checkpoint contains only DB/SDK')
    parser.add_argument('--abandon-reporter-request',help='Explicit isolated Reporter-only recovery fixture, never automatic')
    parser.add_argument('--authorization-file',type=Path)
    args=parser.parse_args()
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    original=args.source_store.resolve() if args.source_store else ROOT/'runs/research'/RUN
    clone=ROOT/'runs'/('p63r-offline-recovery-'+str(time.time_ns()))
    clone.mkdir();stamp=original.joinpath('platform.sqlite').stat()
    source=sqlite3.connect(original.joinpath('platform.sqlite').as_uri()+'?mode=ro',uri=True)
    before=json.loads(source.execute('select state from sessions').fetchone()[0])
    stored_root=json.loads(source.execute("select value from meta where key='root'").fetchone()[0])
    assert before['research_status']=='ready' and before['pilot']['live_model_requests']==args.expected_provider
    assert len(before['analysis_results'])==args.expected_math and not before['pending'] and not before['pilot'].get('unconsumed_response')
    with sqlite3.connect(clone/'platform.sqlite') as destination:source.backup(destination)
    source.close();shutil.copytree(session_storage_path(original/'framework_sessions'),session_storage_path(clone/'framework_sessions'))
    if args.abandon_reporter_request:
        assert args.authorization_file
        for folder in ('analyses','physical_replay','mechanics','local_diagnostics'):
            for path in (original/folder).glob('*/boundary.json'):
                target=clone/path.relative_to(original);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    if args.configuration_archive:
        assert args.source_store,'Configuration archive is only for an explicit offline checkpoint'
        with zipfile.ZipFile(args.configuration_archive) as archive:
            freeze=json.loads(archive.read(RUN+'/implementation_freeze.json'))
            assert freeze==dict(commit=before['freeze'],profile=before['profile'])
            assert json.loads(archive.read(RUN+'/resolved_configuration.json'))==before['spec']
            for name in ('framework_configuration.json','implementation_freeze.json','resolved_configuration.json'):
                (clone/name).write_bytes(archive.read(RUN+'/'+name))
    else:
        for name in ('framework_configuration.json','implementation_freeze.json','resolved_configuration.json'):
            shutil.copy2(original/name,clone/name)
    h=Host(clone,RUN,actor='explicit-offline-recovery-fixture');assert state(h)==before
    sent=[];times={};phase={'allow_http':False};abandonment=None
    handoff_stages=[]
    def clone_transaction(store,db):
        # Fixture-only isolation, not a migrated grant. No original Store write.
        assert store.root==clone and store.db==clone/'platform.sqlite'
        assert json.loads(db.execute("select value from meta where key='root'").fetchone()[0])==stored_root
    def offline_guard(host,*args,**kwargs):assert host.store.root==clone
    def respond(request):
        assert phase['allow_http'],'Restore-only must not send even a Mock Provider request'
        wire=json.loads(request.content);sent.append(wire)
        content='OFFLINE fixture: saved evidence received; no science requested.'
        if args.abandon_reporter_request and wire['messages'][0]['content'].startswith('You are a read-only scientific Reporter.'):
            payload=json.loads(wire['messages'][-1]['content'])
            assert payload['report_reference']!=abandonment['base_report'],'Lost Reporter must never be resent'
            source_id=next(iter(payload['source_catalog']))
            content=json.dumps(dict(interpretations=[dict(kind='unresolved_question',
                text='Synthetic isolated fixture only: deterministic evidence retained; no scientific conclusion.',source_ids=[source_id])]))
        return httpx.Response(200,json=dict(id='OFFLINE-R1',object='chat.completion',created=1,model=wire['model'],
            choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content=content))],
            usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14)))
    with ExitStack() as stack:
        for target,replacement in [('tools.platform_store.Store.check_root',clone_transaction),
                ('tools.research.core.guard',offline_guard),('tools.research.agent.guard',offline_guard),
                ('tools.research.agent.credential',lambda *args:'offline-no-real-credential')]:stack.enter_context(patch(target,replacement))
        stack.enter_context(patch('tools.service_execution._run_contained',side_effect=AssertionError('OFFLINE_PROBE_FORBIDS_WORKER')))
        stack.enter_context(patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)))
        from tools.research.session_handoff import handoff as original_handoff
        async def measured_handoff(*values,**kwargs):
            start=time.perf_counter()
            def stage(name):handoff_stages.append(dict(stage=name,elapsed_s=time.perf_counter()-start))
            return await original_handoff(*values,**kwargs,stage=stage)
        stack.enter_context(patch('tools.research.session_handoff.handoff',measured_handoff))
        migration=None
        if args.abandon_reporter_request:
            from tools.research.provider import abandon_unrecoverable_reporter_attempt,received,pending
            from tools.research.core import recover
            authorization=json.loads(args.authorization_file.read_text(encoding='utf-8'))
            files=snapshot_files(clone/'framework_sessions',before['pilot']['framework_session_id'])
            abandonment=abandon_unrecoverable_reporter_attempt(h,args.abandon_reporter_request,authorization=authorization)
            assert state(h)==before and received(h,args.abandon_reporter_request) is None and not pending(h)
            assert snapshot_files(clone/'framework_sessions',before['pilot']['framework_session_id'])==files
            events_before=h.store.events(RUN)
            assert abandon_unrecoverable_reporter_attempt(h,args.abandon_reporter_request,authorization=authorization)==abandonment
            assert h.store.events(RUN)==events_before
            recover(h)
        if args.migrate:
            from tools.research.core import bind
            start=time.perf_counter();bind(h,reason='R1 isolated offline verification of committed result-delivery/reading repair')
            times['original_bind_s']=time.perf_counter()-start
            migrated=state(h);migration=migrated['core_repairs'][-1]
            assert migrated['profile_history'][:len(before['profile_history'])]==before['profile_history']
            assert migrated['profile']['science_hashes']==before['profile']['science_hashes']
        expected_profile=deepcopy(state(h)['profile'])
        start=time.perf_counter();asyncio.run(converse(h,restore_only=True));times['sdk_restore_s']=time.perf_counter()-start
        restored=state(h);assert restored['pilot']['live_model_requests']==args.expected_provider and restored['analysis_results']==before['analysis_results']
        assert not sent and not restored['pending'] and not restored['pilot'].get('unconsumed_response')
        phase['allow_http']=True
        start=time.perf_counter()
        asyncio.run(converse(h,max_new_provider_requests=80-args.expected_provider,pause_after_completed_invocations=1) if args.abandon_reporter_request else converse(h,max_new_provider_requests=1))
        times['one_mock_converse_s']=time.perf_counter()-start
    after=state(h);assert len(sent)>=1 and after['pilot']['live_model_requests']==args.expected_provider+len(sent)
    for key in ('analysis_results','candidates','control_initializations','search_results','analysis_costs','numerical_s','physical_replays'):
        assert after[key]==before[key],key
    assert after['profile']==expected_profile
    mains=[wire for wire in sent if wire.get('tools')];assert len(mains)==1
    wire=mains[0];packet=json.loads(next(m['content'].split('\n',1)[1] for m in reversed(wire['messages'])
        if m['role']=='user' and isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')))
    research=packet['research'];delivery=research['scientific_results'];latest=delivery['latest_search']['fixed_result']['best_mathematical'][0]
    best=delivery['study_best_mathematical'][0]['fact']
    assert best['candidate']['artifact_id']=='37eec2e5967481d61cd78c00c1e0b723212171e310afe200e72c2957766a2734'
    assert best['J']==-.014355323230259676
    if args.expect_scope:
        raw=h.store.artifact(before['search_results'][-1])['result']
        problem=h.store.artifact(raw['search_state'])['problem'];query=problem['query']
        scope=delivery['latest_search']['fixed_result']['search_scope']
        for key in ('variable_groups','segment_counts','tendon_counts','span_strategies','section_types','bounds','initial_tension_n','previous_candidate_ref'):
            assert scope[key]==query[key],key
        assert scope['resolved_domains']==problem['domains']
        assert latest['citation']['registered'] and latest['citation']['role']=='scientific_result'
        assert latest['J']==next(iter(raw['best_native_candidate']['evidence']['conditions'].values()))['J']
    else:assert latest['J']==-.0069635885347172355
    assert len(best['metrics'])==len(latest['metrics'])==3 and not best['executable_under_current_profile']
    for key in ('research_trace','tool_continuation','knowledge','budget','capabilities','research_focus','evidence_access'):assert key in research,key
    assert len(json.dumps(wire).encode())<1048576
    assert any(t['function']['name']=='research_plan' for t in wire['tools'])
    events=h.store.events(RUN);recoveries=[e for e in events if e['kind']=='sdk_restore_verified']
    assert recoveries
    assert original.joinpath('platform.sqlite').stat().st_mtime_ns==stamp.st_mtime_ns
    with sqlite3.connect(original.joinpath('platform.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        assert json.loads(db.execute('select state from sessions').fetchone()[0])==before
    result=dict(schema='p63r_isolated_recovery_probe_v1',original=str(original),clone=str(clone),
        fixture_only=True,configuration_archive=str(args.configuration_archive) if args.configuration_archive else None,
        real_provider_requests=0,scientific_workers=0,source_unchanged=True,
        source_provider=args.expected_provider,clone_mock_provider=after['pilot']['live_model_requests'],math_preserved=args.expected_math,searches_preserved=before['search_results'],
        abandonment=abandonment,mock_main_requests=len(mains),mock_other_reporter_requests=len(sent)-len(mains),
        profile_before=before['profile'],profile_after=expected_profile,migration=migration,
        sdk_restore_events=[e['outputs'][0] for e in recoveries],
        mock_wire_bytes=len(json.dumps(wire).encode()),timings=times,handoff_stages=handoff_stages,latest_search=delivery['latest_search']['reference'],
        latest_best=latest,study_best=best,scope_fields_verified=args.expect_scope,original_fields_preserved=True,worker_reexecutions=0,
        original_provider_retransmissions=0,notes='Only the isolated clone uses patched root/guard/credentials and Mock HTTP. These patches grant no live authorization and are never used by R2.')
    prefix='p63r3' if args.abandon_reporter_request else 'p63r'
    (ROOT/f'runs/{prefix}_recovery_probe.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (ROOT/f'runs/{prefix}_recovery_mock_wire.json').write_text(json.dumps(wire,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('profile_preserved','latest_best','study_best')},indent=2),flush=True)


if __name__=='__main__':main()
