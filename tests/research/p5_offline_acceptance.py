"""Read-only P5 boundary comparisons and pending decision inputs; never sends."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
from jsonschema import Draft202012Validator
from tests.research.p4_context_audit import audit
from tools.research.config import ROOT, resolve
from tools.research.provider import request_settings
from tools.state_io import atomic_json, digest


def run():
    output=ROOT/'runs/p5-offline';output.mkdir(parents=True,exist_ok=True)
    cases=[('r2',Path('D:/softrobot-agent/.worktrees/m5-main-off-experience/runs/research/m5-main-off-experience-r2-20261028'),{}),
        ('p4_after_domain_read',ROOT/'runs/research/p4-m5-none-20261029-a01',
            dict(study='p4-m5-none-20261029-a01',handoff_event=56,request_event=60))]
    source_hashes={name:hashlib.sha256((source/'platform.sqlite').read_bytes()).digest() for name,source,_ in cases}
    report={}
    for name,source,args in cases:
        old,_,before=audit(source,**args)
        budget_only,_,uncompacted=audit(source,**args,reserve_policy='last_requests_v2')
        new,_,after=audit(source,**args,policy='on_demand_tools_v3',reserve_policy='last_requests_v2')
        old_brief=json.loads(uncompacted['messages'][-1]['content'].split('\n',1)[1])['research']
        new_brief=json.loads(after['messages'][-1]['content'].split('\n',1)[1])['research']
        old_feedback=old_brief['research_state']['pending_feedback'];new_feedback=new_brief['research_state']['pending_feedback']
        assert old_feedback==new_feedback
        assert old_brief['research_state']['task']==new_brief['research_state']['task']
        assert old_brief['research_state']['candidate_status']==new_brief['research_state']['candidate_status']
        assert old_brief['budget']==new_brief['budget']
        assert old_brief.get('current_intent')==new_brief.get('current_intent')
        assert budget_only['v2']['loaded_plan_actions']==new['v2']['loaded_plan_actions']==['generate']
        for tool in after['tools']:Draft202012Validator.check_schema(tool['function']['parameters'])
        atomic_json(output/(name+'_before.json'),before)
        atomic_json(output/(name+'_budget_only.json'),uncompacted)
        atomic_json(output/(name+'_after.json'),after)
        report[name]=dict(boundary=old['boundary'],before=old['v2'],budget_only=budget_only['v2'],after=new['v2'],
            retained=dict(task=True,candidate_status=True,budget=True,unfinished_intent=True,exact_feedback=True,
                generate_available=True,source_navigation=True),
            limitation='Offline re-projections. Budget-only and compact arms share the same new reserve semantics. Original frozen Study and authority are unchanged.')
    source,args=cases[1][1:]
    proposed,_,wire=audit(source,**args,policy='on_demand_tools_v3',reserve_policy='last_requests_v2',proposed_budget=9)
    packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])
    packet['study_id']='p5-m5-none-pending'
    packet['source_boundary']=dict(study=args['study'],state_identity=proposed['boundary']['source_state_identity'],
        request_boundary='After the fourth P4 request and its successful full FamilySpace read.',
        read_only=True,authorization_transferred=False,
        budget_scope='Proposed independent nine-request ledger, last three closeout-only. Not an execution grant; explicit new approval is required.')
    wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
    pending=resolve(ROOT/'configs/research/study_p5_m5_decision_pending.json')
    provider=pending['runtime']['provider']
    wire.update(request_settings(provider))
    atomic_json(output/'decision_input_none.json',wire)
    medium={**deepcopy(wire),**request_settings({**provider,'reasoning':'medium'})}
    atomic_json(output/'decision_input_medium.json',medium)
    differences=[k for k in wire.keys()|medium.keys() if wire.get(k)!=medium.get(k)]
    assert set(differences)=={'thinking','reasoning_effort'}
    assert not (ROOT/'runs/research'/pending['study_id']/'platform.sqlite').exists()
    report['pending_decision_test']=dict(source=proposed['boundary'],config='configs/research/study_p5_m5_decision_pending.json',
        none_input_identity=digest(wire),medium_input_identity=digest(medium),only_arm_differences=differences,
        proposed_shared_requests=9,protected_requests=3,maximum_main_exploration_requests=6,
        reporter_shares_total=True,echo_requests=0,real_requests=0,new_studies=0,
        scientific_workers=0,D1='not_run_pending_explicit_new_quota',D2='not_run',D3='not_run',D4='not_run',
        future_execution='Use existing decision probe and python -m tools.research only after explicit new approval. Do not reuse the stopped P4 grant.')
    for name,source,_ in cases:
        report[name]['source_store_unchanged']=hashlib.sha256((source/'platform.sqlite').read_bytes()).digest()==source_hashes[name]
        assert report[name]['source_store_unchanged']
    atomic_json(ROOT/'docs/research/p5_offline_metrics.json',report)
    print(json.dumps({k:dict(before=v['before']['total'],budget_only=v['budget_only']['total'],after=v['after']['total']) for k,v in report.items() if k!='pending_decision_test'}))
    return report


if __name__=='__main__':run()
