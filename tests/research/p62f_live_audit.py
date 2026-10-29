"""Bounded P6.2-F operator entry point, reusing the P6.2 audit and production loop.

Commands with --live send real requests. Never run as a unit-test fixture.
One independent Store, Main <=7, Reporter <=3, total <=10, zero new science.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import httpx
from tests.research import p62_live_audit as previous
from tests.research import p62_results_audit as export
from tools.platform_host import Host
from tools.research import agent, reporter
from tools.research.config import ROOT
from tools.research.core import prepare
from tools.research.experience import read_progress
from tools.research.provider import credential, discover_models, received, record, pending
from tools.research.state import state, update, save
from tools.state_io import atomic_json, digest

RUN='p62f-luna-20261029'
CONFIG=ROOT/'configs/research/study_p62f_luna.json'
BASE='574fee7476cdc893e7ff39e0faf34e5df2fb4005'


def host(arm='luna'):
    if arm!='luna':raise ValueError('P62F_LUNA_ONLY')
    return Host(ROOT/'runs/research'/RUN,RUN,actor='unified-research')


def configure():
    c=json.loads((ROOT/'configs/research/study_p62_luna.json').read_text())
    c.update(study_id=RUN,base_commit=BASE,evidence_destination='runs/research/'+RUN,
        authorization='Explicit P6.2-F user authorization 2026-10-29, reaffirmed before sleep: ten total sends, Main 7, Reporter 3, failed sends count, no retries or replacement grants, zero new mathematics/physics/NMPC/RL.')
    c['execution_instructions']=previous.INSTRUCTIONS.replace('P6.2','P6.2-F')
    atomic_json(CONFIG,c)


def provision():
    # The historical importer already verifies byte identities and transitive
    # references. Select only the new config/host; never alter the old Study.
    with patch.object(previous,'host',host),patch.object(previous,'prepare',
            side_effect=lambda path,directory:prepare(CONFIG,directory=directory)):
        previous.provision('luna')


async def health():
    h=host();s=state(h);p=s['pilot']['provider']
    assert p['adapter']=='chatgpt_gateway' and p['model']=='gpt-5.6-luna' and p['reasoning']=='none'
    catalog=await discover_models(p,credential(p,s['spec']['runtime']['credentials_reference']))
    names=[row['id'] for row in catalog['models']]
    if p['model'] not in names:raise ValueError('AUTHORIZED_LUNA_MODEL_NOT_IN_CATALOG')
    record(h,'p62f_gateway_health',dict(model=p['model'],catalog_contains_model=True,
        provider_requests=0,scope='Catalog only; no model capability probe or Echo'))
    print(json.dumps(dict(catalog_contains_model=True,model=p['model'])))


def admit_archived_continuation():
    """Same gateway/model actual native feedback proof, not synthetic admission."""
    h=host();archive=Host(ROOT.parent/'p6-2-reporter-handoff/runs/research/p62-luna-20261029',
        'p62-luna-20261029',actor='unified-research')
    before=hashlib.sha256(archive.store.db.read_bytes()).hexdigest()
    provider=state(h)['pilot']['provider'];old=state(archive)['pilot']['provider']
    for key in ('adapter','model','base_url','reasoning'):
        assert provider[key]==old[key],key
    feedback={archive.store.artifact(e['outputs'][0])['tool_use']['toolUseId'] for e in archive.store.events(archive.run_id)
        if e['kind']=='model_original_tool_feedback'}
    proofs=[]
    for event in archive.store.events(archive.run_id):
        if event['kind']!='r3_request':continue
        meta=archive.store.artifact(event['outputs'][0]);response=received(archive,event['request_id'])
        wire=archive.store.artifact(meta['request'])
        if meta['purpose']!='conversation' or not response or response['http_status']!=200:continue
        delivered=[m['tool_call_id'] for m in wire['messages'] if m['role']=='tool' and m['tool_call_id'] in feedback]
        if delivered and wire['model']==provider['model']:
            proofs.append(dict(request=meta['request'],response=response['body'],delivered_tool_ids=delivered))
    if not proofs or pending(h) or state(h)['pilot'].get('unconsumed_response'):
        raise ValueError('REAL_SAME_MODEL_FEEDBACK_PROOF_REQUIRED')
    assert hashlib.sha256(archive.store.db.read_bytes()).hexdigest()==before
    record(h,'p62f_live_handoff_admission',dict(source_store=str(archive.store.db),source_store_sha256=before,
        proofs=proofs,scope='Existing actual successful same-provider same-model tool continuation; transport admission only, no transferred scientific credit.'))
    update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
    print(json.dumps(dict(admitted=True,proofs=len(proofs))))


async def investigate(index, live):
    with patch.object(previous,'host',host):
        await previous.investigate('luna',index,live)


async def main_window(requests):
    with patch.object(previous,'host',host):
        await previous.main_window('luna',requests,True)


async def supervised_knowledge(requests):
    """Explicitly isolated procedural delivery check, never autonomous research."""
    h=host();old=state(h);ledger=h.store.remaining()
    if pending(h) or old.get('pending') or old['pilot'].get('unconsumed_response'):
        raise ValueError('SUPERVISED_CHECK_REQUIRES_SETTLED_BOUNDARY')
    if read_progress(h) and any(r['body_delivered'] for r in read_progress(h)['reads']):
        raise ValueError('KNOWLEDGE_ALREADY_DELIVERED_NO_DUPLICATE_TEST')
    prompt=('Supervised read-only handoff verification, separate from your autonomous scientific trajectory. '
        'The user explicitly authorized this subtest. Use experience_retrieve to search available English procedural Knowledge without strict task/version filters, '
        'then precisely read one returned English entry using its actual entry_id and revision. '
        'After its body is delivered across automatic Handoff, describe its actual scope and whether cross-task transfer is verified. '
        'Use CURRENT_RESEARCH_PACKET knowledge.read_progress to avoid duplicate body reads. This check grants no scientific evidence or acceptance. '
        'Do not repeat Reporter investigations or perform science. Finish with a concise assessment after consuming the body; no scientific success is requested.')
    if old['research_status']=='stopped':
        if old.get('success_gate') or old.get('selected'):raise ValueError('CANNOT_CONTINUE_SUCCESS')
        prior=save(h,old,'p62f_sealed_autonomous_stop_state')
        approval=record(h,'p62f_supervised_continuation',dict(user_approval=True,
            authorization='P6.2-F user task expressly permits isolated supervised read-only Knowledge handoff test within remaining original budget.',
            previous_state=prior,previous_final_disposition=old['final_disposition'],previous_ledger=ledger,
            additional_provider_requests=0,scientific_limits_unchanged=True,prompt=prompt,
            scope='Supervised only; never evidence that Main autonomously selected Knowledge or continued a natural STOP.'))
        update(h,research_status='ready',count_closeout=False,final_disposition=None,
            research_continuations=[*old.get('research_continuations',[]),approval],pending_authorized_continuation=approval)
    else:
        record(h,'p62f_supervised_window',dict(prompt=prompt,previous_ledger=ledger,scope='Explicit supervision, not autonomous Knowledge choice.'))
    from tools.research import session_handoff
    with patch.object(session_handoff,'INVOCATION_PROMPT',prompt):
        await main_window(requests)


def audit():
    destination=ROOT/'docs/research/p62f_luna_results.json'
    with patch.object(export,'host',host),patch.object(export,'atomic_json',side_effect=lambda path,value:atomic_json(destination,value)):
        result=export.audit('luna')
    h=host();before=hashlib.sha256(h.store.db.read_bytes()).hexdigest()
    result['knowledge_read_progress']=read_progress(h)
    result['knowledge_retrievals']=[dict(reference=r,**h.store.artifact(r)) for r in state(h)['retrievals']]
    result['operator_events'] += [dict(sequence=e['sequence'],kind=e['kind'],references=e['outputs'],
        records=[dict(immutable_state_snapshot=True,restore_query=dict(reference=r,view='full'))
            if e['kind'].endswith('_state') else h.store.artifact(r) for r in e['outputs']])
        for e in h.store.events(h.run_id) if e['kind'].startswith('p62f_')]
    # The original exact payloads stay in the Store. Export equality and hashes
    # instead of duplicating a whole report in both sides of a continuity check.
    for handoff in result['handoffs']:
        expected=handoff['pending_feedback_expected'];actual=handoff['actual_feedback']
        assert handoff['precise_feedback_preserved'] and expected==actual
        assert all(handoff['authoritative_snapshot_to_actual_wire'].values())
        handoff['feedback_digests']=dict(expected=digest(expected),actual=digest(actual))
        handoff['feedback_restore_queries']=[item['original_result_query'] for item in expected['items']]
        if len(json.dumps(expected).encode())>16000:
            handoff['pending_feedback_expected']=dict(omitted_from_export=True,restore_from=handoff['reference'],pointer='/pending_feedback_delivery')
            handoff['actual_feedback']=dict(omitted_from_export=True,restore_from=next(r['request_reference'] for r in result['rows']
                if r['sequence']==handoff['next_request_sequence']),scope='Actual CURRENT_RESEARCH_PACKET pending_feedback; exact equality checked before export.')
    calls=[(row,tool) for row in result['rows'] for tool in row['tool_calls']]
    raw_ids={r['artifact_id'] for r in result['source_manifest']['references']}
    searches=[digest(t['arguments']) for _,t in calls if t['name']=='experience_retrieve' and t['arguments']['operation']=='search']
    result['tool_counts']=dict(total=len(calls),direct_original_result_reads=sum(t['name']=='evidence_read' and
            t['arguments'].get('reference',{}).get('artifact_id') in raw_ids for _,t in calls),
        full_report_reads=sum(t['name']=='evidence_read' and not t['arguments'].get('pointer') for _,t in calls),
        reporter_investigations=sum(t['name']=='research_investigate' for _,t in calls),
        routing=sum(t['name']=='research_route' for _,t in calls),
        knowledge_searches=sum(t['name']=='experience_retrieve' and t['arguments']['operation']=='search' for _,t in calls),
        knowledge_exact_reads=sum(t['name']=='experience_retrieve' and t['arguments']['operation']=='read' for _,t in calls),
        repeated_knowledge_searches=len(searches)-len(set(searches)),accepted_scientific_plans=len(state(h)['plans']))
    result['efficiency']=dict(reporter_input_tokens=[r['usage']['prompt_tokens'] for r in result['rows'] if r['purpose']=='reporter'],
        main_max_input_tokens=max(r['usage']['prompt_tokens'] for r in result['rows'] if r['purpose']!='reporter'),
        total_tokens=sum(v['total_tokens'] for v in result['usage'].values()),
        comparison_scope='First two Reporter questions reuse original sources; third synthesis differs. Main 1-4 autonomous, 5-7 supervised with preceding full-report feedback. No causal end-to-end efficiency or autonomous Knowledge adoption claim.',
        tokens_per_completed_reporter_request=result['usage']['reporter']['total_tokens']/result['usage']['reporter']['requests'],
        tokens_per_accepted_scientific_plan=None)
    assert hashlib.sha256(h.store.db.read_bytes()).hexdigest()==before
    atomic_json(destination,result)
    print(json.dumps(dict(knowledge=result['knowledge_read_progress'],status=result['final_status'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['configure','prepare','health','admit','math','physics','main','supervised','audit'])
    parser.add_argument('--live',action='store_true');parser.add_argument('--requests',type=int,default=2)
    args=parser.parse_args()
    if args.command=='configure':configure()
    elif args.command=='prepare':provision()
    elif args.command=='health':asyncio.run(health())
    elif args.command=='admit':admit_archived_continuation()
    elif args.command in ('math','physics'):asyncio.run(investigate(0 if args.command=='math' else 1,args.live))
    elif args.command=='main':asyncio.run(main_window(args.requests))
    elif args.command=='supervised':asyncio.run(supervised_knowledge(args.requests))
    else:audit()
