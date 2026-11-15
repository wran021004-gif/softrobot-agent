"""Stateless independent blind review; no new Agent or scientific work."""
import argparse
import copy
import json
import statistics
import time
from r2_replay import ROOT,DATA,PREVIOUS,read,write,csv_rows,credential,httpx,stamp

METRICS=['physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','evidence_reference_accuracy']
LABELS={'PHS_C037_A':{'A':'Flat','B':'Hierarchical'},'PHS_C042_B':{'A':'Hierarchical','B':'Flat'}}
CRITICAL=[
    dict(id='G1',fact='Matched F2/F3/F4 near-load evidence has mixed trends: lower drift at higher viscosity does not imply monotone improvement of speeds and static-balance residual.',refs=['C029_OUTPUT','C032_OUTPUT','C035_OUTPUT']),
    dict(id='G2',fact='Recorded loaded qualifications remain failed; some unloaded/local mathematical qualification does not establish loaded dynamic qualification.',refs=['C031_EP0_qualifications','C034_EP0_qualifications','C036_EP0_qualifications','C037_OUTPUT']),
    dict(id='G3',fact='F3 distal finite-load transfer is much worse than its near-load transfer; distinguish load case and candidate lineage.',refs=['C032_OUTPUT','C037_OUTPUT']),
    dict(id='G4',fact='Original raw route record detects cable-solid intersection at pose/time zero, separate from contact count and tail settling.',refs=['C031_EP0_route_geometry','C034_EP0_route_geometry','C036_EP0_route_geometry']),
    dict(id='G5',fact='Exploratory sampled evidence covers only selected cases and does not establish every-step qualification, independent full acceptance, numerical convergence or a unique failure cause.',refs=['C027_OUTPUT','C031_OUTPUT','C034_OUTPUT','C036_OUTPUT','C037_OUTPUT'])]
RUBRIC='''You are an independent blinded scientific-decision reviewer. Compare anonymous
decisions A/B using the SAME frozen pre-decision raw corpus and question. No context
condition, token cost, original presentation, actual read count or Reporter content is
provided. Do not infer labels or conditions. The reviewer corpus is factual reference,
not proof of what either Main was directly given or actually read. Do not penalize or
reward administrative claims about delivery/access. Judge the stated next action and
its reasoning, not an unexecuted follow-up or eventual robot success. No post-checkpoint
fact or outcome is available to you; do not import future solutions.

Score five integers 0-4:
physical_interpretation: correct physical mechanisms and competing interpretations,
without mistaking failed qualification, contact counts or local math for causal proof;
evidence_consistency: faithful numeric/qualitative interpretation, candidate/load binding;
limitation_recognition: scope of local math, sampled dynamics, missing cases, geometry,
integration and independent acceptance where relevant;
research_actionability: a feasible informative concrete next action, held conditions,
expected observations and falsification; prefer information gain over redundant work;
evidence_reference_accuracy: cited exact original sources support the actual claims.
0=absent/wrong; 1=major defects; 2=partial/material gaps; 3=reasonable/limited gaps;
4=accurate, specific and justified. Average the five equally; compare means, tie if equal.
Do not reward length, number of reads/citations or polished prose. Distinct informative
actions can be equally good. A hypothesis is not an asserted fact. A planned future read
is not a fabricated observation. A valid Plan is not proof of task-specific admission.

The supplied critical-evidence checklist was frozen before scoring. For each group,
mark covered=true only when the decision uses its substance correctly; exact numbers
or all listed refs are not mandatory if the interpretation is accurate. Report covered
groups / total groups as descriptive coverage; it is not an extra score or an automatic
penalty for a justified narrower action. Record unsupported conclusions, wrong refs,
missed critical evidence and unnecessary repeat research only with source justification.
Do not assume an absent citation means the evidence was never read. Actual on-demand
read correctness cannot be observed blind: mark it not_assessable_blind; it is assessed
separately from original tool/response traces after scores are frozen.

Return ONLY JSON:
{"evaluations":[{"label":"A","scores":{"physical_interpretation":0,
"evidence_consistency":0,"limitation_recognition":0,"research_actionability":0,
"evidence_reference_accuracy":0},"mean_score":0,
"critical_evidence":[{"group":"G1","covered":false,"rationale":"...","source_refs":[]}],
"key_evidence_coverage":0,"unsupported_conclusions":[],"incorrect_references":[],
"missed_key_evidence":[],"unnecessary_repeated_research":[],
"on_demand_read_correctness":"not_assessable_blind","strengths":[],"weaknesses":[],
"evidence_specific_rationale":"..."},
{"label":"B",...same fields...}],"paired_winner":"A|B|tie",
"comparative_rationale":"..."}.
Include every checklist group for each label. Keep rationales concise and evidence-bound.
'''


def freeze_checklist():
    path=ROOT/'critical_evidence_checklist.json'
    assert not path.exists()
    write(path,dict(frozen_at=stamp(),before_blind_scoring=True,groups=CRITICAL,
        reason='Predefined factual groups for the selected checkpoint; no score-dependent selection. Coverage is descriptive, not another scoring weight.'))


def prepare():
    records=[json.loads(s) for s in (DATA/'decision_replay_results.jsonl').read_text('utf-8').splitlines()]
    assert len(records)==len(read(ROOT/'execution_schedule.json')) and all(r['status']=='completed' for r in records)
    write(ROOT/'private_condition_key.json',LABELS)
    for sid in sorted({r['snapshot_id'] for r in records}):
        folder=DATA/'blind_review'/sid
        assert not (folder/'review_request.json').exists()
        by={r['condition']:r for r in records if r['snapshot_id']==sid}
        decisions=[]
        for label,condition in LABELS[sid].items():
            plan=copy.deepcopy(by[condition]['decision'])
            if plan.get('decision'):plan['decision'].pop('hypothesis_id',None)
            decisions.append(dict(label=label,decision=plan))
        corpus=read(ROOT/'snapshots'/sid/'corpus.json')
        raw=[{k:v for k,v in a.items() if k not in ['information_level','flat_included','hierarchical_accessible','query']} for a in corpus['atoms']]
        write(folder/'anonymous_decisions.json',decisions)
        write(folder/'shared_frozen_evidence.json',dict(question=corpus['question'],cutoff_before=corpus['cutoff_before'],raw_information=raw))
        write(folder/'critical_evidence_checklist.json',read(ROOT/'critical_evidence_checklist.json'))
        (folder/'rubric.md').write_text(RUBRIC,encoding='utf-8')
        csv_rows(folder/'human_scoring_template.csv',[dict(label=l,**{m:None for m in METRICS},mean_score=None,key_evidence_coverage=None,unsupported_conclusions=None,incorrect_references=None,missed_key_evidence=None,unnecessary_repeated_research=None,reviewer=None) for l in ['A','B']])
    write(ROOT/'blind_review_procedure.json',dict(prepared_at=stamp(),new_agent_created=False,labels_fixed_in_source=True,
        hidden=['condition','context presentation','usage/cost','actual read count','future data','Reporter content'],
        original_decisions_preserved=True,review_copy_omissions=['Administrative hypothesis_id only.'],
        limitation='Wording or reference choices can suggest resource use despite hidden labels. Human verification remains pending.',
        on_demand_assessment='Blind judge marks not assessable; exact actual read traces assessed separately after scoring.',
        future_scope='Future results retained only as separate retrospective source references, absent from both Main and primary blinded reviewer.'))
    print(json.dumps(dict(event='blind_materials_prepared',snapshots=len({r['snapshot_id'] for r in records}))),flush=True)


def review():
    cfg=read(ROOT/'replay_configuration.json');old=read(PREVIOUS/'independent_review_configuration.json')
    provider=copy.deepcopy(cfg['provider']);provider['model']=old['model'];key=credential(provider,cfg['credentials_reference'])
    write(ROOT/'independent_review_configuration.json',dict(model=provider['model'],configuration_source=(PREVIOUS/'independent_review_configuration.json').as_posix(),
        base_url=provider['base_url'],reasoning='API default, no function tools.',new_agent_created=False,one_request_per_pair=True))
    for folder in sorted((DATA/'blind_review').iterdir()):
        if not folder.is_dir():continue
        if (folder/'review_request.json').exists():raise RuntimeError('Review send already exists; no automatic rerating.')
        content=dict(shared_evidence=read(folder/'shared_frozen_evidence.json'),critical_evidence_checklist=read(folder/'critical_evidence_checklist.json'),anonymous_decisions=read(folder/'anonymous_decisions.json'))
        wire=dict(model=provider['model'],stream=False,store=False,messages=[dict(role='system',content=RUBRIC),dict(role='user',content=json.dumps(content,separators=(',',':')))])
        payload=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        (folder/'review_request.json').write_bytes(payload)
        print(json.dumps(dict(event='independent_review_started',snapshot_id=folder.name,wire_bytes=len(payload))),flush=True);begun=time.perf_counter()
        with httpx.Client(timeout=600,proxy=provider.get('proxy_url'),trust_env=False,follow_redirects=False) as client:
            response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',content=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        (folder/'review_response.txt').write_text(response.text,encoding='utf-8')
        if response.status_code!=200:
            write(folder/'review_unavailable.json',dict(http_status=response.status_code,status='Human scoring pending, no scores invented.'));return
        body=response.json();text=body['choices'][0]['message']['content'].strip()
        if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
        result=json.loads(text);assert {e['label'] for e in result['evaluations']}=={'A','B'}
        for e in result['evaluations']:
            assert set(e['scores'])==set(METRICS) and all(type(v)==int and 0<=v<=4 for v in e['scores'].values())
            assert abs(statistics.mean(e['scores'].values())-e['mean_score'])<1e-9
            assert {x['group'] for x in e['critical_evidence']}=={x['id'] for x in CRITICAL}
            coverage=sum(x['covered'] for x in e['critical_evidence'])/len(CRITICAL)
            assert abs(coverage-e['key_evidence_coverage'])<1e-9
        write(folder/'independent_model_review.json',dict(review=result,model=body.get('model'),usage=body.get('usage'),wall_s=time.perf_counter()-begun,provider_requests=1,human_verification='pending',blinded=True))
        print(json.dumps(dict(event='independent_review_finished',snapshot_id=folder.name,paired_winner=result['paired_winner'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['checklist','prepare','review']);a=p.parse_args();{'checklist':freeze_checklist,'prepare':prepare,'review':review}[a.mode]()
