"""Read-only original acceptance reconstruction; never step, train or optimize."""
import json
import asyncio
from collections import Counter
from datetime import datetime,timezone,timedelta
import hashlib
from pathlib import Path
import subprocess
import tarfile
import httpx
import numpy as np
from schemas.platform import SessionInput,BackendResult,Signal,Payload
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.feedback import task_gap
from tools.research_tasks import task_adapter,assemble_acceptance
from extensions.reference.implementation import evaluate_reach
from tools.state_io import digest,atomic_json,read
from tests.research.s128_audit import host
from tests.research.s12_audit import verify_nmpc


def reconstruct():
    h=host();s=state(h);before=digest(s);ledger=h.store.remaining();events=h.store.events(h.run_id);checks=[]
    for ref in s.get('physical_replays',[]):
        v=h.store.artifact(ref);assert v['owning_study']==h.run_id
        cfg=h.store.artifact(v['candidate'])['configuration'];inp=SessionInput.model_validate(cfg)
        raw=h.store.artifact(v['raw_reference']);samples=raw.get('samples',[]);trajectory=h.store.artifact(v['source_reference'])['trajectory']
        if not task_gap(v)['valid_complete']:
            checks.append(dict(reference=ref,complete=False,independent_recompute='not_tested',original_acceptance=v['acceptance']));continue
        assert raw['physics_timestep_s']==.0005 and inp.task.timing.duration_s==.35 and inp.task.timing.control_period_s==.01
        np.testing.assert_allclose([x['time_s'] for x in samples],np.arange(36)*.01,rtol=0,atol=1e-12)
        np.testing.assert_allclose([x['actual_tension_n'] for x in samples[1:]],trajectory['tensions_n'],rtol=0,atol=1e-12)
        for x in samples:
            assert np.isfinite(x['tip_m']).all() and np.isfinite(x['tip_velocity_m_s']).all()
            np.testing.assert_allclose(np.linalg.norm(np.asarray(x['tip_m'])-inp.task.goal.data['target_m']),x['position_error_m'],rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(np.linalg.norm(x['tip_velocity_m_s']),x['speed_m_s'],rtol=1e-12,atol=1e-12)
        signal=next(x for x in inp.task.observations if x.name=='tip_position' and x.phase=='post_step')
        backend=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
            signals=[Signal(spec=signal,times_s=[x['time_s'] for x in samples[1:]],values=[x['tip_m'] for x in samples[1:]])],
            data=Payload(contract='family.backend_data',data=dict(physical_replay=True)),limitations=['Ideal direct tendon tension; nominal sampled task only'],
            initial_state=inp.task.initializer.parameters,seed=inp.seed)
        ev=evaluate_reach(inp.task,backend,v['raw_reference'],registry(),digest(dict(candidate=v['candidate'],source=v['source_reference'])))
        assert plain(ev)==h.store.artifact(v['evaluation_reference'])
        adapter=task_adapter(cfg);limits=adapter.ranking_limits();hold=[x for x in samples if x['time_s']>=adapter.holding_start_s()-1e-12]
        complete=raw['status']=='completed' and len(samples)==len(trajectory['tensions_n'])+1 and raw['physics_steps']==700
        error=max(x['position_error_m'] for x in hold);speed=max(x['speed_m_s'] for x in hold)
        bounds={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
        force=max(max(0.,-u,u-bounds[name]) for x in samples[1:] for name,u in zip(raw['tendon_order'],x['actual_tension_n']))
        expected_hold=round(inp.policy.controller.parameters.data['settling']['window_s']/inp.task.timing.control_period_s)+1
        profile=dict(complete=complete,execution_id=v['profile']['execution_id'],simulation=v['raw_reference'],evaluation=v['evaluation_reference'],
            task=plain(inp.task),official_task_success=ev.task_success,solver_error_count=0 if complete else 1,force_bound_violation_n=force,
            sampled_settling=dict(window_s=inp.policy.controller.parameters.data['settling']['window_s'],position_limit_m=limits['holding_max_error_m'],
                speed_limit_m_s=limits['holding_max_speed_m_s'],available=len(hold)==expected_hold,max_error_m=error,max_speed_m_s=speed,
                passed=bool(len(hold)==expected_hold and error<=limits['holding_max_error_m'] and speed<=limits['holding_max_speed_m_s'])))
        assert profile==v['profile']
        acceptance=assemble_acceptance(cfg,ev,profile,evaluation_reference=v['evaluation_reference'],profile_reference=None,motion=[dict(time_s=x['time_s']) for x in samples])
        assert acceptance==v['acceptance']
        checks.append(dict(reference=ref,candidate=v['candidate'],source=v['source_reference'],complete=complete,accepted=acceptance['accepted'],metrics=acceptance['metrics'],task_gap=task_gap(v),original_evaluator_and_full_acceptance_equal=True,raw_time_grid_force_motion_and_profile_verified=True,physics_steps=raw['physics_steps']))
    rawout=h.store.root/'independent_acceptance';rawout.mkdir(exist_ok=True)
    nmpc=verify_nmpc(h,rawout)
    assert digest(state(h))==before and h.store.remaining()==ledger and h.store.events(h.run_id)==events
    report=dict(study_id=h.run_id,physical=checks,nmpc=nmpc,new_scientific_executions=0,store_state_ledger_events_unchanged=True,source='Original registered evaluator and assemble_acceptance; saved samples only, no rollout')
    atomic_json(ROOT/'evidence/s128_acceptance/reconstruction.json',report)
    return report


async def reopen(h,events,bodies):
    from strands.tools.executors import SequentialToolExecutor
    from tools.research.agent import build_harness,LiveBoundary,live_model_class
    from tools.research.session_handoff import trusted_history,unmatched
    directory=h.store.root/'framework_sessions'
    files={str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}
    def forbidden(request):raise AssertionError('Audit cannot send Provider requests')
    boundary=LiveBoundary(h,httpx.MockTransport(forbidden))
    try:
        agent=build_harness(h,transport=boundary,api_key='read-only-no-credential',instructions='Read-only completed-study audit',
            model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=[],
            configuration_path=h.store.root/'audit_framework.json',session_directory=directory)
        assert await agent._session_manager.restore_snapshot(agent)
        assert trusted_history(h,agent)=='completed' and not unmatched(agent.messages)
        sdk_reasoning=[''.join(b['reasoningContent'].get('reasoningText',{}).get('text','') for b in m['content'] if 'reasoningContent' in b)
            for m in agent.messages if m['role']=='assistant']
        raw_reasoning=[c['message'].get('reasoning_content','') for body in bodies for c in body['choices']]
        assert [v for v in sdk_reasoning if v]==[v for v in raw_reasoning if v]
        assert all(hashlib.sha256((directory/p).read_bytes()).hexdigest()==sha for p,sha in files.items())
        return dict(independent_process_reopen=True,completed_history_matches_store=True,tool_ids_results_paired=True,
            reasoning_messages_verified=sum(bool(v) for v in raw_reasoning),sdk_files_unchanged=True,
            sdk_message_identity=digest(agent.messages),sdk_files=len(files),provider_requests=0,scientific_executions=0)
    finally:await boundary.aclose()


def delivery():
    from tools.research.agent import received
    from tools.research.budget import stage_usage
    from tools.research.state import core_hashes,science_hashes
    h=host();s=state(h);before=digest(s);ledger=h.store.remaining();events=h.store.events(h.run_id)
    frozen=read(ROOT/'evidence/s128_preflight/freeze.json')
    assert s['research_status']=='stopped' and not s['selected'] and not s.get('pending') and not s['pilot'].get('unconsumed_response')
    assert s['core_hashes']==core_hashes() and s['profile']['science_hashes']==science_hashes()
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in frozen['source_files'].items())
    with h.store.connect(True) as db:assert not db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]
    disposition=h.store.artifact(s['final_disposition']);plan=disposition['original_plan']
    fresh=[r for k in ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results') for r in s.get(k,[])]
    assert plan['action']=='stop' and disposition['origin']=='model' and all(r in plan['supporting_evidence'] for r in fresh)
    assert all(not s['spec']['research_decisions'][k] for k in ('history','mathematics','control_seeds')) and not s['spec']['supplied_evidence']
    requests=[e for e in events if e['kind']=='r3_request'];assert len(requests)==len({e['request_id'] for e in requests})==ledger['used']['model_calls']==s['pilot']['live_model_requests']
    totals=Counter();bodies=[];request_rows=[];raw_tools={};delivered={}
    for e in requests:
        wire=h.store.artifact(h.store.artifact(e['outputs'][0])['request']);row=h.store.lookup(h.run_id,e['request_id'])
        assert row['request_hash']==digest(wire) and row['receipt']
        assert wire['model']=='deepseek-flash' and wire['max_tokens']==131072 and wire['thinking']==dict(type='enabled') and wire['reasoning_effort']=='high'
        reception=received(h,e['request_id']);raw=h.store.artifact(reception['body'],raw=True)
        assert hashlib.sha256(raw).hexdigest()==reception['body']['artifact_id'] and reception['http_status']==200
        body=json.loads(raw);bodies.append(body);assert all(c['finish_reason'] in ('stop','tool_calls') for c in body['choices'])
        usage=body['usage']
        for key in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):totals[key]+=usage[key]
        details=usage.get('completion_tokens_details') or {}
        if 'reasoning_tokens' in details:totals['reasoning_tokens']+=details['reasoning_tokens'];totals['reasoning_usage_responses']+=1
        for c in body['choices']:
            for t in c['message'].get('tool_calls',[]):
                assert t['id'] not in raw_tools;raw_tools[t['id']]=dict(name=t['function']['name'],input=json.loads(t['function']['arguments']))
        ids={t['id'] for m in wire['messages'] if m['role']=='assistant' for t in m.get('tool_calls',[])}
        for m in wire['messages']:
            if m['role']=='tool':assert m['tool_call_id'] in ids;delivered[m['tool_call_id']]=m['content']
        capacity=len(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire).content)+131072+8192
        assert capacity<=1000000
        request_rows.append(dict(request_id=e['request_id'],usage=usage,elapsed_s=reception['elapsed_s'],conservative_context_capacity=capacity,wire_identity=digest(wire),body=reception['body']))
    errors=[];decisions=[];generations=[];feedback={};tool_counts=Counter()
    for e in events:
        if e['kind']=='model_original_tool_request':
            use=h.store.artifact(e['outputs'][0])['tool_use'];assert raw_tools[use['toolUseId']]==dict(name=use['name'],input=use['input']);tool_counts[use['name']]+=1
            p=use['input'];d=p.get('decision',{})
            if use['name'] in ('research_plan','research_analysis','research_rl'):
                decisions.append(dict(sequence=e['sequence'],tool_use_id=use['toolUseId'],tool=use['name'],action=p.get('action') or p.get('operation'),hypothesis_id=d.get('hypothesis_id'),method=d.get('selected_method'),variables=d.get('selected_variables'),requested_budget=d.get('requested_budget'),candidate=d.get('selected_candidate') or p.get('candidate')))
        elif e['kind']=='model_original_tool_feedback':
            v=h.store.artifact(e['outputs'][0]);use=v['tool_use'];result=v['result'];key=use['toolUseId'];assert key not in feedback;feedback[key]=v
            if use['name']=='research_plan' and use['input'].get('action')=='generate' and result.get('status')=='success':
                returned=json.loads(''.join(b.get('text','') for b in result['content']))
                generated=h.store.artifact(returned['wrapper_reference'])['result']
                generations.append(dict(tool_use_id=key,hypothesis_id=use['input']['decision']['hypothesis_id'],status=generated['status'],reason=generated.get('reason'),candidate=generated.get('candidate'),result_reference=returned['wrapper_reference']))
            if result.get('status')!='success':
                text=''.join(b.get('text','') for b in result.get('content',[]))
                try:detail=json.loads(text)
                except ValueError:detail=dict(error_code='SDK_VALIDATION_ERROR')
                errors.append(dict(tool_use_id=key,tool=use['name'],action=use['input'].get('action'),error_code=detail.get('error_code'),field=detail.get('field'),scientific_execution_started=detail.get('scientific_execution_started')))
    assert set(feedback)==set(raw_tools)
    full=preview=0
    from strands._context_manager.methods.truncate import _build_preview
    for key,value in delivered.items():
        original=''.join(b.get('text','') for b in feedback[key]['result'].get('content',[]))
        if value==original:full+=1
        else:
            assert value==_build_preview(original,1,dict(preview_tokens=500))+'\n\n[Stashed] [ref: '+key+'_0]';preview+=1
    reopened=asyncio.run(reopen(h,events,bodies))
    acceptance=reconstruct();records=acceptance['physical']+acceptance['nmpc']
    valid=[r for r in records if r.get('task_gap',{}).get('valid_complete')]
    assert len(valid)==79 and not any(r['accepted'] for r in valid)
    best=min(valid,key=lambda r:r['task_gap']['normalized_gap'])
    candidates=[]
    for ref in s['candidates'].values():
        c=h.store.artifact(ref);p=c['parameters']
        candidates.append(dict(reference=ref,segment_count=p['segment_count'],tendon_count=p['tendon_count'],lengths_m=[v['length_m'] for v in p['segments'].values()],young_pa=[v['young_pa'] for v in p['segments'].values()],viscosity=[v['physical_parameters'] for v in p['segments'].values()],pretension_n=p['tendon_parameters']['pretension_n'],evaluations=sum(h.store.artifact(r['reference'])['candidate']==ref for r in records)))
    searches=[]
    for ref in s.get('control_search_results',[]):
        result=h.store.artifact(ref)
        best_summary={k:result['best'].get(k) for k in ('reference','candidate','source','best_valid_reference','task_gap','predicted_improvement','actual_improvement','prospective_guarantee','applicability')}
        searches.append(dict(reference=ref,**{k:result.get(k) for k in ('algorithm','search_dimension','finite_difference_evaluations','stop_reason','cost_feedback')},best=best_summary))
    archive=h.store.root/'export/immutable_artifacts.tar.gz';manifest=read(archive.with_name('archive_manifest.json'))
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as tar:
        for member in manifest['members']:assert hashlib.sha256(tar.extractfile(member['name']).read()).hexdigest()==member['sha256']
    old=h.__class__(ROOT/'runs/research/s126-cold-live-20261020','s126-cold-live-20261020')
    assert digest(state(old))=='d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3'
    assert not subprocess.check_output(['git','diff','--name-only','09648856','--','tasks','extensions','matlab','schemas','evidence/s126_cold','evidence/s127_6_handoff','evidence/s127_6_decision'],cwd=ROOT,text=True).strip()
    assert digest(state(h))==before and h.store.remaining()==ledger and h.store.events(h.run_id)==events
    tz=timezone(timedelta(hours=8))
    summary=dict(study_id=h.run_id,status='model_stop_without_original_task_pass',scientific_success_proven=False,selected=None,
        source_commit=s['freeze'],source_hashes_match=True,canonical_task_identity=s['spec']['canonical_task_identity'],
        started_asia_shanghai=datetime.fromtimestamp(s['live_started_unix'],tz).isoformat(),closed_asia_shanghai=datetime.fromtimestamp(s['closed_unix'],tz).isoformat(),study_elapsed_s=s['closed_unix']-s['live_started_unix'],
        candidate_count=len(candidates),independent_complete_physical_evaluations=len(valid),accepted_evaluations=0,best_valid=best,
        model_stop_reference=s['final_disposition'],model_stop_cites_all_fresh_results=True,fresh_results_cited=len(fresh),
        actual_provider_requests=len(requests),actual_usage=dict(totals),ledger=ledger,rl=stage_usage(s),
        method_counts=dict(offline_nlp=s['offline_nlp'],nmpc=s['nmpc_launches'],physical_replay=s['physical_replay_launches'],control_searches=len(searches),mathematical_analysis=s['mathematical_evaluations'],ppo_stages=len(s['rl_runs'])),
        model_tool_counts=dict(tool_counts),tool_rejections=errors,feedback_delivery=dict(full=full,configured_offload_preview=preview,last_STOP_feedback_not_sent_to_another_model_request=True),
        generation_attempts=len(generations),invalid_generation_attempts=sum(g['status']=='invalid' for g in generations),
        input_or_admission_rejections=len(errors)+sum(g['status']=='invalid' for g in generations),
        context_capacity_peak=max(r['conservative_context_capacity'] for r in request_rows),context_capacity_limit=1000000,
        sdk=reopened,pending=None,unsettled_receipts=0,unknown_sends=0,confirmed_truncations=0,new_scientific_executions_in_audit=0,
        archive=dict(local_path=str(archive.relative_to(ROOT)),sha256=manifest['archive_sha256'],members_verified=len(manifest['members']),bytes=archive.stat().st_size,raw_data_published=False),
        store_state_identity=before,store_state_ledger_events_unchanged=True,old_sealed_evidence_unchanged=True,
        ppo_not_tested_reason='Agent allocated physical launches to design/control response searches and NMPC; before its final STOP only one shared launch remained, below the unchanged two-launch training/evaluation admission requirement. No RL learning efficacy conclusion.',production_handoff_admitted=False,framework_sessions=1)
    atomic_json(ROOT/'evidence/s128_acceptance/status.json',summary)
    atomic_json(ROOT/'evidence/s128_research/designs.json',dict(candidates=candidates))
    atomic_json(ROOT/'evidence/s128_research/decisions.json',dict(decisions=decisions,generations=generations,searches=searches,errors=errors,raw_hypotheses_and_reasoning='Local immutable Store only; this file contains scientific metadata and derived counts, not raw Provider messages'))
    atomic_json(ROOT/'evidence/s128_costs/counts.json',dict(study_id=h.run_id,actual_provider_requests=len(requests),usage=dict(totals),ledger=ledger,rl=stage_usage(s),method_counts=summary['method_counts'],provider_elapsed_s=sum(r['elapsed_s'] for r in request_rows),study_elapsed_s=summary['study_elapsed_s'],dollar_cost='not_reported_by_provider',per_request=request_rows))
    return summary


if __name__=='__main__':
    r=delivery();print(json.dumps({k:r[k] for k in ('status','candidate_count','independent_complete_physical_evaluations','actual_provider_requests','actual_usage','best_valid','context_capacity_peak','archive')},ensure_ascii=False))
