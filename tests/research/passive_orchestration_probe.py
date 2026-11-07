"""Three independent bounded production-Harness probes; no scripted model replies.

Prepare once, then run each case once. All sends, including Reporter and failed
sends, use the original Store budget. No automatic retry or budget extension.
"""
import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path

from tools.research import core,agent,reporter
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.state_io import digest,atomic_json
from tools.platform_host import Host
from tools.research.session_handoff import assess_live_admission,admit_formal_study

PREFIX='passive-orchestration-20261107'
LIMITS={'A':1,'B':1,'C':6}
SOURCE_ROOT=ROOT.parent/'stage2-research-workflow-20261106/runs/research/phs2d-topology-successor-20261106'
SOURCE_STUDY='phs2d-topology-successor-20261106'
OUT=ROOT/'evidence/passive_orchestration_20261107'
PHENOMENA=(
    'Answer-isolated historical failed-candidate observations, not current Study evidence: '
    'a local tendon/endpoint Jacobian match did not survive finite loading; '
    'deformation and tendon slackening were observed. Apparent small drift could coexist '
    'with force-residual spikes. Other candidates improved displacement but failed '
    'tail-window balance/settling. Several guide/mass/material factors changed together, '
    'so unique causal attribution was not established. Exact topology, routes, material '
    'combinations, payouts and successful designs are withheld. Current task and thresholds prevail.')
QUESTIONS={
    'A': 'Knowledge understanding probe. Explain in your public response the physical problem, '
        'supported facts versus hypotheses, unilateral constraints, static versus dynamic '
        'qualification, local Jacobian scope, competing explanations, promising parameter '
        'groups and the next discriminating research question. Use the available sanitized '
        'knowledge/process; do not launch science in this reasoning-only case. One response is available.',
    'B': 'Scientific question construction probe. Independently propose a falsifiable mechanism '
        'hypothesis from these observations. State supporting evidence, expected observation, '
        'a weakening result, chosen parameter group, M0 versus task-performance purpose, '
        'and a high-level research_analysis request in your public response. Explain your '
        'scientific choice. Do not supply solver settings, raw parameter edits or numerical '
        'difference steps, and do not execute calculations in this case. One response is available.',
    'C': 'Independent execution probe. From these observations, form your own scientific '
        'hypothesis and choose a minimal informative action through the formal tools. You '
        'may generate a candidate, use parameterized mathematical research, passive '
        'FamilyMixedSearch or a cheap diagnostic. Inspect the current legal scope and '
        'request formats as needed. At most one search proposal and two search condition '
        'analyses are allowed; partial static loads are diagnostics only. No full '
        'ten-condition dynamics, Replay, training or large search. After meaningful '
        'evidence and Reporter feedback, explain or record your next research decision. '
        'No historical candidate is supplied; topology and mechanism are your choices.'}


def host(case):
    name=PREFIX+'-'+case.lower()
    return Host(ROOT/'runs/research'/name,name)


def prepare():
    base=json.loads((ROOT/'configs/research/study_passive_research_capabilities_v1.json').read_text())
    for case,limit in LIMITS.items():
        spec=deepcopy(base);name=PREFIX+'-'+case.lower()
        if (ROOT/'runs/research'/name).exists():raise ValueError('PROBE_EXISTS_NO_BUDGET_RESET: '+case)
        spec.update(study_id=name,mode='formal_research',evidence_destination='runs/research/'+name+'/private-evidence')
        spec['budgets'].update(provider_requests=limit,protected_provider_requests=0,
            mathematical_evaluations=12 if case=='C' else 0,physical_launches=0)
        spec['family_search'].update(max_proposals=1,max_evaluations=2)
        spec['mathematical_worker_watchdog_s']=120
        path=ROOT/'configs/research'/('._'+name+'.json')
        atomic_json(path,spec)
        try:h=core.prepare(path)
        finally:path.unlink()
        core.bind(h)
        evidence=save(h,assess_live_admission(h,SOURCE_ROOT,SOURCE_STUDY),'handoff_transport_evidence')
        scope=dict(study_id=name,resolved_identity=state(h)['spec']['resolved_identity'],
            implementation_freeze=state(h)['freeze'],
            execution_scopes=['registered mathematics','request-feedback session handoff'],
            session_handoff=dict(boundary='request_feedback',evidence=evidence))
        approval=save(h,dict(user_approval='User task 2026-11-07 explicitly authorizes three small production-Harness probes, at most eight shared Provider sends including Reporter; no extensions or full Replay.',
            scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
        admit_formal_study(h,approval)
        save(h,dict(case=case,phenomena=PHENOMENA,question=QUESTIONS[case],
            independent_context=True,previous_case_answers_supplied=False), 'passive_probe_prompt')
    audit()


def prompt_reference(h):
    return next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='passive_probe_prompt')


def audit():
    OUT.mkdir(parents=True,exist_ok=True);results={}
    for case in LIMITS:
        h=host(case);s=state(h);events=h.store.events(h.run_id)
        responses=[];requests=[];tools=[]
        for e in events:
            if e['kind']=='r3_request':
                meta=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(meta['request'])
                packets=[json.loads(m['content'].split('\n',1)[1]) for m in wire['messages']
                    if isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')]
                packet=packets[-1] if packets else {};research=packet.get('research',{})
                requests.append(dict(request_id=e['request_id'],purpose=meta['purpose'],model=wire['model'],
                    reasoning=wire.get('reasoning_effort'),tools=[t['function']['name'] for t in wire.get('tools',[])],
                    context=dict(operator_question_delivered=packet.get('operator_request',{}).get('instruction',{}).get('case')==case,
                        closeout=research.get('budget',{}).get('closeout'),
                        knowledge_entries=[r['entry_id']+'@'+r['revision'] for r in research.get('knowledge',{}).get('catalogue',[])],
                        reporter_statuses=[r.get('status') for r in research.get('reporter_findings',[])],
                        latest_mathematics=research.get('mathematical_research',{}).get('latest_result'))))
            if e['kind']=='r3_response' and e['status']=='metadata_saved':
                meta=h.store.artifact(e['outputs'][0]);body=json.loads(h.store.artifact(meta['body'],raw=True))
                responses.append(dict(request_id=e['request_id'],purpose=meta['purpose'],http_status=meta['http_status'],
                    usage=meta.get('usage'),choices=[dict(finish_reason=c.get('finish_reason'),
                        content=c.get('message',{}).get('content'),tool_calls=c.get('message',{}).get('tool_calls')) for c in body.get('choices',[])]))
            if e['kind'] in ('model_original_tool_request','model_original_tool_feedback'):
                tools.append(dict(kind=e['kind'],value=h.store.artifact(e['outputs'][0])))
        results[case]=dict(study=h.run_id,implementation=s.get('freeze'),requests=requests,responses=responses,
            tools=tools,provider_usage=reporter.provider_usage(h),ledger=h.store.remaining(),
            plans=[h.store.artifact(r)['original_plan'] for r in s['plans']],
            analyses=[dict(reference=r,status=(a:=h.store.artifact(r))['status'],
                summary=__import__('tools.research.structure_research',fromlist=['summary']).summary(a,r)
                    if a.get('structure_research') else None) for r in s['analysis_results']],
            searches=[dict(reference=r,result=h.store.artifact(r)['result']) for r in s.get('search_results',[])],
            reports=[dict(reference=r,status=v['interpretation_status'],error=v.get('error'),
                interpretations=v['report'].get('interpretations',[])) for r,v in reporter.current_reports(h)],
            mathematical_evaluations=s['mathematical_evaluations'],research_status=s['research_status'],
            pending_science=bool(s.get('pending')),provider_pending=bool(__import__('tools.research.provider',fromlist=['pending']).pending(h)),
            limitations=['A/B/C independent sessions; no historical winner or previous-case answers supplied.',
                'No complete original physical task validation or new feasible-structure claim.'])
    atomic_json(OUT/'audit.json',dict(version='passive_orchestration_probe_v1',cases=results,
        total_provider_requests=sum(len(v['requests']) for v in results.values()),authorized_maximum=8))
    print(json.dumps({k:dict(provider_requests=len(v['requests']),mathematical_evaluations=v['mathematical_evaluations'],
        reports=[r['status'] for r in v['reports']]) for k,v in results.items()}))


async def run(case):
    h=host(case)
    if h.store.remaining()['used']['model_calls']:raise ValueError('PROBE_ALREADY_SENT_NO_AUTOMATIC_RETRY')
    total=sum(host(c).store.remaining()['used']['model_calls'] for c in LIMITS)
    if total+LIMITS[case]>8:raise ValueError('SHARED_EIGHT_REQUEST_LIMIT')
    try:
        await agent.converse(h,max_new_provider_requests=LIMITS[case],pause_after_completed_invocations=1,
            operator_request=prompt_reference(h))
    finally:audit()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run','audit'])
    parser.add_argument('--case',choices=list(LIMITS))
    args=parser.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='audit':audit()
    elif args.case:asyncio.run(run(args.case))
    else:parser.error('run requires --case')
