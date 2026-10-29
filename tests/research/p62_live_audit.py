"""Bounded P6.2 operator audit using production Store, Reporter, SDK and handoff.

No alternate research loop or numerical worker. Each explicitly authorized arm
has one ten-request ledger. Source artifacts are copied byte-for-byte, read-only.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import httpx
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.research import agent, reporter
from tools.research.config import ROOT
from tools.research.core import prepare, bind
from tools.research.provider import LiveBoundary, record, received, pending
from tools.research.state import state, update, save, guard
from tools.state_io import atomic_json, digest

SOURCE=Path('D:/softrobot-agent/.worktrees/s142-reach-hold-autonomous')
SOURCE_STORE=SOURCE/'runs/research/s142-reach-hold-coldstart-20261023'
BASE='7a2287325a882cb70b933d3ea07db909c58237f2'
QUESTIONS=[
    'Investigate why this mathematical calculation did not prove the reach-and-hold task feasible. Check solver status, principal violated constraints, exact values and units, time coverage, model and validity limits. Distinguish failed search from infeasibility; identify unresolved questions.',
    'Investigate these two independent reach-and-hold evaluations. Give principal violations, times and numerical values. Compare the second listed result as the baseline: which quantities improved or worsened, and is the comparison valid? Separate measured facts from possible mechanisms and competing explanations. No single-factor causal attribution from confounded changes.'
]
INSTRUCTIONS=('This is a read-only investigation of the sealed S142 reach-and-hold study, not a new autonomous design study. '
    'Use the authoritative CURRENT_RESEARCH_PACKET, Reporter findings and recoverable references to understand the mathematical and physical failures. '
    'Prefer Reporter investigation for detailed scientific evidence. You may autonomously choose relevant read-only tools, inspect curated English Knowledge, '
    'and articulate a justified next research judgment, but do not launch science or claim historical evidence passes this new test. '
    'Explain reliable conclusions, competing hypotheses and unresolved questions. Use already delivered reports without repeating identical reads. '
    'You will continue across SDK handoff from the same Store; do not restart the investigation. '
    'New mathematics, physics, NMPC and RL are all forbidden. Shared allowance is ten Provider sends, Main at most seven, Reporter at most three, failures included. '
    'The audit pauses between windows. End an invocation with a concise evidence-based assessment when enough is known; no formal STOP is required for this audit.')


def host(arm):
    run='p62-'+arm+'-20261029'
    return Host(ROOT/'runs/research'/run,run,actor='unified-research')


def source_data():
    store=Store(SOURCE_STORE)
    s=store.session('s142-reach-hold-coldstart-20261023')['state']
    refs=[s['analysis_results'][1],s['results'][2],s['results'][1]]
    return store,s,refs


def configure(arm):
    """Freeze a normal engineering_investigation configuration; no Provider send."""
    old=SOURCE/'configs/research/study_reach_hold_coldstart.json'
    c=json.loads(old.read_text(encoding='utf8'))
    for k in ('robot','control','task'):
        c[k]=str((old.parent/c[k]).resolve())
    c.update(study_id='p62-'+arm+'-20261029',base_commit=BASE,mode='engineering_investigation',
        authorization='Explicit P6.2 user authorization 2026-10-29: '+arm+
        ' arm, ten shared Provider requests maximum (Main 7, Reporter 3), zero new science, no retries or replacement grant.',
        runtime='runtime_p5_luna_none.json' if arm=='luna' else 'runtime_openai_api.json',
        evidence_destination='runs/research/p62-'+arm+'-20261029',
        capabilities=['investigation'],allowed_plan_actions=['diagnose','stop'],physical_replay_limit=0,
        execution_instructions=INSTRUCTIONS,supplied_evidence=[])
    c['budgets'].update(provider_requests=10,protected_provider_requests=0,provider_reserve_policy='last_requests_v2',
        public_operations=80,protected_public_operations=0,physical_launches=0,local_solves=0,offline_nlp=0,bdf_replays=0,mathematical_evaluations=0)
    c['nmpc_limits']['executions']=0
    c['rl_limits'].update(training_stages=0,evaluation_episodes=0,diagnostic_replays=0,diagnostic_physics_steps=0)
    c['confirmation']['fresh_independent_repetitions']=0
    template=json.loads((ROOT/'configs/research/study_p5_luna_none.json').read_text())
    c['research_decisions']=deepcopy(template['research_decisions'])
    c['research_decisions']['tool_schema_policy']={'version':'research_information_flow_v1'}
    path=ROOT/'configs/research'/('study_p62_'+arm+'.json')
    atomic_json(path,c)
    return path


def provision(arm):
    h=host(arm)
    if h.store.db.exists():raise ValueError('P62_ARM_ALREADY_EXISTS_NO_RESET')
    h=prepare(ROOT/'configs/research'/('study_p62_'+arm+'.json'),directory=h.store.root)
    source,old,refs=source_data();before=hashlib.sha256(source.db.read_bytes()).hexdigest()
    copied={};missing=[]
    def copy_ref(ref):
        key=ref['artifact_id']
        if key in copied:return
        with source.connect(True) as db:row=db.execute('SELECT media,body FROM artifacts WHERE id=?',(key,)).fetchone()
        if row is None:
            missing.append(ref);return
        raw=bytes(row['body']) if not isinstance(row['body'],str) else row['body'].encode()
        assert hashlib.sha256(raw).hexdigest()==key
        with h.store.transaction() as db:
            db.execute('INSERT OR IGNORE INTO artifacts(id,media,body) VALUES (?,?,?)',(key,row['media'],raw))
        copied[key]=dict(artifact_id=key,media_type=row['media'])
        if row['media']=='application/json':walk(json.loads(raw))
    def walk(v):
        if isinstance(v,dict):
            if 'artifact_id' in v and 'media_type' in v:copy_ref(v)
            else:
                for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    for ref in refs:copy_ref(ref)
    update(h,scoped_context=refs)
    provenance=dict(source_store=str(source.db),source_store_sha256=before,source_study=old['spec']['study_id'],
        original_task_identity=source.artifact(refs[0])['binding']['task_identity'],
        original_budget=source.remaining(),references=refs,copied=list(copied.values()),missing_references=missing,
        historical_only=True,current_acceptance_credit=False,source_store_unchanged=before==hashlib.sha256(source.db.read_bytes()).hexdigest())
    assert provenance['source_store_unchanged']
    record(h,'p62_source_import',provenance)
    atomic_json(h.store.root/'source_manifest.json',provenance)
    bind(h)
    guard(h)
    print(json.dumps(dict(study=h.run_id,source_count=len(copied),missing=len(missing),ledger=h.store.remaining())))


async def limited_send(self,request):
    """Audit-only role ceilings checked BEFORE the production reservation/send."""
    counts=reporter.provider_usage(self.host)
    role=getattr(self,'purpose',None) or ('conversation' if json.loads(request.content).get('tools') else 'summarization')
    used=sum(v['requests'] for k,v in counts.items() if (k=='reporter')==(role=='reporter'))
    if used >= (3 if role=='reporter' else 7):raise ValueError('P62_ROLE_REQUEST_CEILING')
    return await ORIGINAL_SEND(self,request)


ORIGINAL_SEND=LiveBoundary.handle_async_request


async def investigate(arm,index,live):
    h=host(arm);guard(h)
    refs=json.loads((h.store.root/'source_manifest.json').read_text())['references']
    if any(e['kind']=='p62_case_'+str(index) for e in h.store.events(h.run_id)):
        raise ValueError('CASE_ALREADY_ATTEMPTED_NO_AUTOMATIC_RETRY')
    result=reporter.investigate(h,dict(question=QUESTIONS[index],references=refs[:1] if index==0 else refs[1:]))
    record(h,'p62_case_'+str(index),result)
    saved=h.store.artifact(result['report_reference'])
    wire=reporter._wire(h,result['report_reference'],saved)
    atomic_json(h.store.root/('case_'+str(index)+'_input.json'),wire)
    if live:
        provider=state(h)['pilot']['provider']
        async with httpx.AsyncHTTPTransport(retries=0,proxy=provider.get('proxy_url')) as transport:
            with patch.object(LiveBoundary,'handle_async_request',limited_send):
                await reporter.complete_reports(h,transport,max_model_calls=h.store.remaining()['used']['model_calls']+1)
    print(json.dumps(dict(case=index,live=live,reports=[dict(reference=r,status=v['interpretation_status'],error=v['error']) for r,v in reporter.current_reports(h)],usage=reporter.provider_usage(h))))


async def main_window(arm,requests,handoff):
    h=host(arm)
    with patch.object(LiveBoundary,'handle_async_request',limited_send):
        await agent.converse(h,session_handoff=handoff,max_new_provider_requests=requests,pause_after_completed_invocations=1)
    print(json.dumps(dict(usage=reporter.provider_usage(h),session=state(h)['pilot']['framework_session_id'])))


def admit_handoff(arm):
    h=host(arm);events=h.store.events(h.run_id)
    feedback={h.store.artifact(e['outputs'][0])['tool_use']['toolUseId'] for e in events if e['kind']=='model_original_tool_feedback'}
    delivered=[]
    for e in events:
        if e['kind']!='r3_request':continue
        meta=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(meta['request']);response=received(h,e['request_id'])
        if meta['purpose']=='reporter' or not response or response['http_status']!=200:continue
        delivered.extend(m['tool_call_id'] for m in wire['messages'] if m['role']=='tool' and m['tool_call_id'] in feedback)
    if not delivered or pending(h) or state(h)['pilot'].get('unconsumed_response'):
        raise ValueError('REAL_SAME_MODEL_TOOL_RESULT_CONTINUATION_NOT_YET_OBSERVED')
    record(h,'p62_live_handoff_admission',dict(delivered_tool_ids=delivered,provider=state(h)['pilot']['provider'],
        evidence='Actual successful same-model Provider wire with completed native tool feedback; no Echo.'))
    update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
    print(json.dumps(dict(admitted=True,delivered_tool_ids=delivered)))


def inspect(arm):
    h=host(arm);rows=[]
    for e in h.store.events(h.run_id):
        if e['kind']!='r3_request':continue
        meta=h.store.artifact(e['outputs'][0]);response=received(h,e['request_id'])
        body=json.loads(h.store.artifact(response['body'],raw=True)) if response else {}
        message=body.get('choices',[{}])[0].get('message',{})
        rows.append(dict(purpose=meta['purpose'],http_status=response.get('http_status') if response else None,
            message={k:v for k,v in message.items() if k in ('content','tool_calls')},usage=body.get('usage'),error=body.get('error')))
    print(json.dumps(dict(rows=rows,reports=[dict(reference=r,status=v['interpretation_status'],report=v['report'],error=v['error'])
        for r,v in reporter.current_reports(h)],ledger=h.store.remaining()),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['configure','prepare','math','physics','main','admit','inspect'])
    p.add_argument('--arm',choices=['luna','mini'],default='luna');p.add_argument('--requests',type=int,default=2)
    p.add_argument('--live',action='store_true');p.add_argument('--handoff',action='store_true');a=p.parse_args()
    if a.command=='configure':print(configure(a.arm))
    elif a.command=='prepare':provision(a.arm)
    elif a.command in ('math','physics'):asyncio.run(investigate(a.arm,0 if a.command=='math' else 1,a.live))
    elif a.command=='main':asyncio.run(main_window(a.arm,a.requests,a.handoff))
    elif a.command=='admit':admit_handoff(a.arm)
    else:inspect(a.arm)
