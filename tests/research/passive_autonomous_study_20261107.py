"""Operator entry for the formal Study; no scripted scientific decisions.

Uses the existing CLI/Harness, frozen Store, grants and Provider addenda.
Status/export never prints credential files or model reasoning.
"""
import argparse
import asyncio
import json
from collections import Counter
from tools.research import core, agent
from tools.research.config import ROOT, resolve
from tools.research.state import state, save
from tools.research.budget import extend_provider_requests, mathematical_remaining, replay_remaining
from tools.research.session_handoff import assess_live_admission, admit_formal_study
from tools.research.tool_readiness import execution_environment
from tools.platform_host import Host
from tools.state_io import atomic_json, digest

NAME='passive-base-only-autonomous-study-20261107'
PROFILE=ROOT/'configs/research/study_passive_base_only_autonomous_study_20261107.json'
OUT=ROOT/'evidence/passive_autonomous_study_20261107'
SOURCE=ROOT.parent/'stage2-research-workflow-20261106/runs/research/phs2d-topology-successor-20261106'


def host():return Host(ROOT/'runs/research'/NAME, NAME)


def check():
    spec=resolve(PROFILE);b=spec['budgets'];rows=spec['knowledge_manifest']['entries']
    assert spec['request_budget_only'] and b['mathematical_evaluations'] is None
    assert b['physical_launches'] is None and b['public_operations'] is None and spec['analysis_cap_s'] is None
    assert mathematical_remaining(spec,10**6) is None and replay_remaining(spec,10**6) is None
    assert spec['knowledge'].get('include_entry_ids') is None and not spec['knowledge']['allow_benchmark_answers']
    assert sum(r.get('resource_role')=='skill' for r in rows)==6
    assert any(r['entry_id']=='phs2d-research-process' and r.get('resource_role')=='expert_process' for r in rows)
    assert all(not r.get('benchmark_sensitive') for r in rows)
    assert not spec['supplied_evidence'] and not any(spec['research_decisions'][k] for k in ('history','mathematics','control_seeds','background'))
    assert spec['family_search']['segment_counts'] is None and spec['family_search']['tendon_counts'] is None
    assert set(spec['family_search']['evaluation_modes'])=={'passive_equilibrium','passive_task_response'}
    assert spec['configuration']['task']==resolve(ROOT/'configs/research/study_passive_post_reporter_mixed_search_20261107.json')['configuration']['task']
    environment=execution_environment(spec);assert environment['status']=='ready',environment
    for row in rows:assert (ROOT/row['path']).is_file()
    return dict(study=NAME,code_baseline='9050738b5',knowledge_entries=len(rows),
        knowledge_types=dict(Counter(r.get('type','legacy_or_workflow') for r in rows)),
        formal_skills=6,expert_process=True,full_ten_condition_task_unchanged=True,
        budget_semantics=spec['budget_semantics'],budgets=b,
        provider=dict(adapter=spec['runtime']['provider']['adapter'],model=spec['runtime']['provider']['model']),
        environment=environment,independent_candidate_pool=True,
        validation_limitations=['Generic active-control trajectory BDF has no registered passive full-task route; not advertised as a passive verifier. Native passive dynamics and Replay remain enabled.'])


def authorize(h):
    scope=dict(study_id=NAME,resolved_identity=state(h)['spec']['resolved_identity'],implementation_freeze=state(h)['freeze'],
        execution_scopes=['registered mathematics','physical replay','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='handoff_transport_evidence')))
    grant=save(h,dict(user_approval='Formal task 4625d228 and direct budget clarification authorize autonomous passive research, full original task and independent Replay, unmetered cumulative mathematics/physics, progress-based Provider addenda, configured official fallback and applicable validation; no historical answers or threshold relaxation.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admit_formal_study(h,grant)


def prepare():
    if (ROOT/'runs/research'/NAME).exists():raise ValueError('EXISTING_STUDY_NO_RESET')
    checked=check();h=core.prepare(PROFILE);core.bind(h)
    save(h,assess_live_admission(h,SOURCE,'phs2d-topology-successor-20261106'),'handoff_transport_evidence')
    authorize(h);OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'preflight.json',checked)
    print(json.dumps(status()))


def status():
    h=host();s=state(h);events=h.store.events(h.run_id)
    plans=[dict(sequence=e['sequence'],reference=e['outputs'][0],
        plan=h.store.artifact(e['outputs'][0])) for e in events if e['kind']=='original_research_plan']
    latest=plans[-1] if plans else None
    if latest:latest={**latest,'plan':{k:latest['plan'].get(k) for k in ('action','hypothesis','interpretation','stopping_condition','decision')}}
    return dict(study=NAME,status=s['research_status'],implementation=s['freeze'],
        ledger=h.store.remaining(),provider_requests=sum(e['kind']=='r3_request' for e in events),
        candidates=len(s['candidates']),analyses=len(s['analysis_results']),searches=len(s.get('search_results',[])),
        mathematical_evaluations=s['mathematical_evaluations'],physical_episodes=s.get('physical_replay_launches',0),
        physical_results=len(s.get('physical_replays',[])),pending=s.get('pending'),
        latest_plan=latest,provider_addenda=s.get('provider_request_extensions',[]))


def extend(count,reason):
    h=host();s=state(h);scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],
        previous_request_limit=s['spec']['budgets']['provider_requests'],additional_requests=count)
    result=extend_provider_requests(h,dict(version='provider_request_extension_approval_v1',approved=True,
        source='User formal task 4625d228: Codex may add requests by scientific progress without asking each time. Review: '+reason,
        scope=scope,scope_identity=digest(scope)))
    core.bind(h,reason='Recorded user-authorized progress-based Provider addition. '+reason);authorize(h)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check','prepare','run','status','extend','audit'])
    p.add_argument('--requests',type=int,default=8);p.add_argument('--reason');a=p.parse_args()
    if a.command=='check':print(json.dumps(check()))
    elif a.command=='prepare':prepare()
    elif a.command=='status':print(json.dumps(status()))
    elif a.command=='extend':
        if not a.reason:p.error('extend requires a progress-based --reason')
        extend(a.requests,a.reason)
    elif a.command=='run':asyncio.run(agent.converse(host(),max_new_provider_requests=a.requests,pause_exploration_remaining=4))
    elif a.command=='audit':
        from tests.research.passive_knowledge_loop_probe import audit
        audit(host(),OUT)
