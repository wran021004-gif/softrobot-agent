"""One fresh continuous real conversation; original Store, Harness and budgets.

prepare/check never send requests. run is explicit, once only, and uses the
combined Store ceiling. audit exports sanitized receipts, not private Store data.
"""
import argparse
import asyncio
import json
from unittest.mock import patch
from tools.research import core, agent, reporter, experience
from tools.research.config import ROOT, resolve
from tools.research.state import state, save
from tools.research.budget import provider_allowance
from tools.research.session_handoff import assess_live_admission, admit_formal_study
from tools.platform_host import Host
from tools.state_io import digest, atomic_json

NAME='passive-knowledge-loop-20261107'
PROFILE=ROOT/'configs/research/study_passive_knowledge_loop_20261107.json'
OUT=ROOT/'evidence/passive_knowledge_loop_20261107'
SOURCE=ROOT.parent/'stage2-research-workflow-20261106/runs/research/phs2d-topology-successor-20261106'
QUESTION=(
    'Conduct one continuous independent passive Base-only research conversation. '
    'Use the normal L0 Knowledge catalogue to discover and search the sanitized PHS-2D Case, '
    'then read its full Action Trace. Explain historical observations versus retrospective '
    'interpretation, failures and direction changes, unqualified baseline versus task failure, '
    'local geometry versus finite deformation, unilateral slack, and static versus dynamic eligibility. '
    'Do not request or reconstruct historical successful designs. '
    'Independently read relevant General and Diagnostic knowledge and form a NEW falsifiable '
    'physical hypothesis: observations, mechanism, observable prediction, weakening result, '
    'competing explanation, and why the next mathematics discriminates them. '
    'Through normal tools generate your own fresh legal candidate, choose a registered high-level '
    'passive mathematical question and parameter groups as appropriate. Fixed programs own numerical '
    'steps and solvers. At most one primary math evaluation plus one correction YOU explicitly justify; '
    'no finite-time integration, full ten-condition task, physical Replay, BDF, NMPC or RL. '
    'Use the existing Reporter on current mathematical evidence and its initial qualification. '
    'Knowledge is context, current Evidence is observation; use exact delivered knowledge_refs and '
    'current sources. Prefer reusing relevant full Knowledge receipts already read. '
    'After Reporter feedback assess hypothesis support/weakening/unknowns and result scope, choose '
    'and SAVE a valid next-round research_plan with scientific rationale; chat intention alone is '
    'insufficient. The next action is your choice. End your invocation once this Plan is saved; '
    'you need not execute it. Total budget is 12 shared Main+Reporter requests INCLUDING 2 closeout, '
    'not extra; batch independent reads where supported, avoid redundant reads, prefer <=8 Main '
    'and <=2 Reporter plus closeout. No extensions or second Study. Tool success alone is not reasoning.')


def host():return Host(ROOT/'runs/research'/NAME,NAME)


def check(h=None):
    spec=state(h)['spec'] if h else resolve(PROFILE)
    b=spec['budgets']
    assert spec['mode']=='formal_research'
    assert (b['provider_requests'],b['protected_provider_requests'],b['provider_reserve_policy'])==(12,2,'last_requests_v2')
    assert b['mathematical_evaluations']==2
    assert all(b[k]==0 for k in ('physical_launches','offline_nlp','bdf_replays'))
    assert spec['nmpc_limits']['executions']==0
    assert spec['rl_limits']['training_stages']==spec['rl_limits']['evaluation_episodes']==0
    assert not spec.get('provider_request_extension_policy')
    assert not spec['supplied_evidence']
    assert all(not spec['research_decisions'][k] for k in ('history','mathematics','control_seeds'))
    result=dict(provider_total=12,closeout_within_total=2,exploration_capacity=10,mathematics=2,
        physical_replay=0,BDF=0,NMPC=0,RL=0,extensions=False,shared_reporter_accounting='LiveBoundary original Store model_calls debit')
    if h:
        assert h.store.remaining()['used']['model_calls']==0
        actual=provider_allowance(h);assert actual['science_capable_main_requests']==10
        result['initial_allowance']=actual
        remaining=h.store.remaining()
        with patch.object(h.store,'remaining',return_value={**remaining,'remaining':{**remaining['remaining'],'model_calls':2}}):
            last=provider_allowance(h);assert last['protected_current_request']
            assert last['science_capable_main_requests']==0
        result['last_two_allowance_offline_projection']=last
    return result


def prepare():
    if (ROOT/'runs/research'/NAME).exists():raise ValueError('FRESH_STUDY_ALREADY_EXISTS_NO_RESET')
    check();h=core.prepare(PROFILE);core.bind(h)
    transport=save(h,assess_live_admission(h,SOURCE,'phs2d-topology-successor-20261106'),'handoff_transport_evidence')
    scope=dict(study_id=NAME,resolved_identity=state(h)['spec']['resolved_identity'],implementation_freeze=state(h)['freeze'],
        execution_scopes=['registered mathematics','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=transport))
    approval=save(h,dict(user_approval='User attachment c4d09464 explicitly authorizes this ONE new continuous Study: combined12 including2reserve, math2, Replay/BDF/NMPC/RL0; no extensions.',
        scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admit_formal_study(h,approval)
    save(h,dict(instruction=QUESTION,independent_history=True),'knowledge_loop_prompt')
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'budget_check.json',check(h))
    print(json.dumps(check(h)))


def audit():
    h=host();s=state(h);requests=[];responses=[];tools=[];reporter_guidance=[]
    for e in h.store.events(h.run_id):
        if e['kind']=='r3_request':
            meta=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(meta['request'])
            requests.append(dict(request_id=e['request_id'],purpose=meta['purpose'],model=wire['model'],reasoning=wire.get('reasoning_effort')))
            if meta['purpose']=='reporter':
                payload=json.loads(wire['messages'][-1]['content'])
                reporter_guidance.append(dict(request_id=e['request_id'],knowledge=[r['entry_id']+'@'+r['revision']
                    for rec in payload.get('procedural_guidance',[]) for r in rec['results']],source_catalog=payload['source_catalog']))
        if e['kind']=='r3_response' and e['status']=='metadata_saved':
            meta=h.store.artifact(e['outputs'][0]);body=json.loads(h.store.artifact(meta['body'],raw=True))
            responses.append(dict(request_id=e['request_id'],purpose=meta['purpose'],http_status=meta['http_status'],usage=meta.get('usage'),
                choices=[dict(finish_reason=c.get('finish_reason'),message={k:v for k,v in (c.get('message') or {}).items() if k in ('role','content','tool_calls')}) for c in body.get('choices',[])]))
        if e['kind'] in ('model_original_tool_request','model_original_tool_feedback'):
            tools.append(dict(kind=e['kind'],value=h.store.artifact(e['outputs'][0])))
    value=dict(study=NAME,implementation=s.get('freeze'),requests=requests,responses=responses,tools=tools,
        provider_usage=reporter.provider_usage(h),ledger=h.store.remaining(),knowledge_progress=experience.read_progress(h),
        reporter_delivered_knowledge=reporter_guidance,
        plans=[dict(reference=r,plan=h.store.artifact(r)['original_plan']) for r in s['plans']],
        analyses=[dict(reference=r,status=(a:=h.store.artifact(r))['status'],summary=__import__('tools.research.analysis',fromlist=['compact_result']).compact_result(a,r)) for r in s['analysis_results']],
        reports=[dict(reference=r,status=v['interpretation_status'],error=v.get('error'),interpretations=v['report'].get('interpretations',[])) for r,v in reporter.current_reports(h)],
        mathematical_evaluations=s['mathematical_evaluations'],physical_replays=len(s['physical_replays']),
        research_status=s['research_status'],pending_science=bool(s.get('pending')),
        provider_pending=bool(__import__('tools.research.provider',fromlist=['pending']).pending(h)))
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'audit.json',value)
    print(json.dumps(dict(requests=len(requests),roles=value['provider_usage'],math=s['mathematical_evaluations'],plans=len(s['plans']),reports=[v['status'] for v in value['reports']]),default=str))


async def run():
    h=host();check(h)  # Fails if any send already occurred: no automatic rerun.
    prompt=next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='knowledge_loop_prompt')
    try:await agent.converse(h,max_new_provider_requests=12,pause_after_completed_invocations=1,operator_request=prompt)
    finally:audit()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check','prepare','run','audit']);args=p.parse_args()
    if args.command=='run':asyncio.run(run())
    elif args.command=='prepare':prepare()
    elif args.command=='audit':audit()
    else:print(json.dumps(check()))
