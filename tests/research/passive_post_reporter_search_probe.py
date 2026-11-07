"""One continuous Study, supervised at existing settled-budget boundaries.

No scientific choices are scripted. Explicit extend uses the original user
addendum mechanism; costs, failures, history and source identities are retained.
"""
import argparse
import asyncio
import json
from tools.research import core,agent,reporter
from tools.research.config import ROOT,resolve
from tools.research.state import state,save
from tools.research.budget import provider_allowance,extend_provider_requests
from tools.research.session_handoff import assess_live_admission,admit_formal_study
from tools.research.tool_readiness import execution_environment
from tools.platform_host import Host
from tools.state_io import digest,atomic_json
from tests.research.passive_knowledge_loop_probe import audit,SOURCE

NAME='passive-post-reporter-mixed-search-20261107'
PROFILE=ROOT/'configs/research/study_passive_post_reporter_mixed_search_20261107.json'
OUT=ROOT/'evidence/passive_post_reporter_search_20261107'
QUESTION=(
    'Continue research on Base-only passive soft structures. Independently use necessary scoped Knowledge '
    'to form a falsifiable mechanism hypothesis, generate a fresh small legal candidate, and choose one '
    'informative cheap non-dynamic mathematical diagnostic through the registered high-level interface. '
    'Use catalogue metadata, exact read queries and finite effort; do not repeat the previous full case-reading test. '
    'The existing Reporter should interpret this first result before your next scientific Plan. '
    'Then assess support, weakening, competing explanations and unknowns, and decide whether a finite '
    'discrete-topology plus continuous-parameter search is scientifically worthwhile. '
    'Submit your own formal research_plan after Reporter, explicitly relating current candidate, math question, '
    'current scientific evidence, hypothesis, variables, effort and stopping conditions. A report is context, '
    'not scientific supporting_evidence. Direct research_plan is available; do not spend a request on route '
    'when your intended action is already advertised. Read only facts still needed for your decision. '
    'If searching, independently choose a reasoned SUBSET with at least one discrete group and at least '
    'one continuous group, explain why other groups stay fixed, and choose meaningful finite intervals '
    'for every selected open coordinate. No variable group or numerical design is prescribed. '
    'Use the existing scientific_structure_search_v1 Plan, compiled to FamilyMixedSearch '
    'bounded_mixed_coordinate_v1. Search authorization is segment counts [2,3] and tendon counts [3,4], '
    'up to8 proposals and3 mathematical evaluations. Choose starts, load subset, objective, ranges and '
    'effort to exercise both discrete and continuous updates within that small allowance. '
    'Keep total math at most4 including the initial diagnostic; no finite-time integration, full ten-condition '
    'task, physical Replay, BDF, NMPC or RL. No historical winning design, prior C candidate or old candidate '
    'pool is supplied. Fixed code owns geometry, model construction, solver and numerical steps. '
    'Actually execute your scientifically justified search, then read the saved search result. Explain '
    'how many candidates were evaluated, actual changed coordinates, qualifications/failures, best mathematical '
    'candidate if any, unexplored scope and unmeasured full task acceptance. End the invocation after that '
    'evidence-based assessment; no further physics is required. Initial shared Provider total16 includes '
    '2 closeout; aim for <=9 Main before the first Reporter and retain4 ordinary Main requests after it. '
    'Supervisor reviews capacity at settled boundaries and may apply recorded user-authorized progress-based '
    'addenda. This does not grant Main an automatic extension or scientific success.')


def host():return Host(ROOT/'runs/research'/NAME,NAME)


def check(h=None):
    spec=state(h)['spec'] if h else resolve(PROFILE);b=spec['budgets']
    assert b['provider_requests']>=16 and b['protected_provider_requests']==2 and b['provider_reserve_policy']=='last_requests_v2'
    assert b['mathematical_evaluations']==4
    assert all(b[k]==0 for k in ('physical_launches','offline_nlp','bdf_replays'))
    assert spec['nmpc_limits']['executions']==0
    assert spec['rl_limits']['training_stages']==spec['rl_limits']['evaluation_episodes']==0
    assert all(not spec['research_decisions'][k] for k in ('history','mathematics','control_seeds'))
    assert not spec['supplied_evidence']
    assert spec['family_search']['max_proposals']==8 and spec['family_search']['max_evaluations']==3
    environment=execution_environment(spec);assert environment['status']=='ready',environment
    return dict(initial_provider_total=16,closeout_within_total=2,pre_reporter_main_review_at=9,
        reserved_ordinary_after_one_reporter=4,review_hook='pause_exploration_remaining=5 before first Reporter; 2 afterward',
        current_limit=b['provider_requests'],provider_extensions='Explicit supervisor addenda only; original Store counter never reset.',
        mathematics=4,search_max_evaluations=3,search_max_proposals=8,physics=0,environment=environment)


def authorize(h,transport):
    scope=dict(study_id=NAME,resolved_identity=state(h)['spec']['resolved_identity'],implementation_freeze=state(h)['freeze'],
        execution_scopes=['registered mathematics','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=transport))
    grant=save(h,dict(user_approval='User c70bfb63 task and direct budget clarification authorize this continuous real test, necessary progress-based finite Provider addenda, math4 and search3, no integration/Replay/BDF/NMPC/RL.',
        scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admit_formal_study(h,grant)


def prepare():
    if (ROOT/'runs/research'/NAME).exists():raise ValueError('STUDY_EXISTS_NO_RESET')
    checked=check();h=core.prepare(PROFILE);core.bind(h)
    transport=save(h,assess_live_admission(h,SOURCE,'phs2d-topology-successor-20261106'),'handoff_transport_evidence')
    authorize(h,transport);save(h,dict(instruction=QUESTION,independent_history=True),'post_reporter_search_prompt')
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'budget_check.json',checked)
    print(json.dumps(dict(budget=checked,allowance=provider_allowance(h))))


async def run():
    h=host();check(h)
    available=any(v['interpretation_status']=='available' for _,v in reporter.current_reports(h,status_only=True))
    threshold=2 if available else 5
    prompt=next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='post_reporter_search_prompt')
    try:await agent.converse(h,max_new_provider_requests=h.store.remaining()['remaining']['model_calls'],
        pause_exploration_remaining=threshold,pause_after_completed_invocations=1,operator_request=prompt)
    finally:audit(h,OUT)


def extend(requests,reason):
    h=host();s=state(h)
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],previous_request_limit=s['spec']['budgets']['provider_requests'],additional_requests=requests)
    approval=dict(version='provider_request_extension_approval_v1',approved=True,
        source='User direct 2026-11-07 clarification: budget is reference; progress-based additions authorized. Supervisor review: '+reason,
        scope=scope,scope_identity=digest(scope))
    result=extend_provider_requests(h,approval)
    core.bind(h,reason='User-authorized finite Provider addendum; '+reason)
    transport=next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='handoff_transport_evidence')
    authorize(h,transport);print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check','prepare','run','audit','extend'])
    p.add_argument('--requests',type=int);p.add_argument('--reason');args=p.parse_args()
    if args.command=='run':asyncio.run(run())
    elif args.command=='prepare':prepare()
    elif args.command=='audit':audit(host(),OUT)
    elif args.command=='extend':
        if not args.requests or not args.reason:p.error('extend requires --requests and --reason')
        extend(args.requests,args.reason)
    else:print(json.dumps(check()))
