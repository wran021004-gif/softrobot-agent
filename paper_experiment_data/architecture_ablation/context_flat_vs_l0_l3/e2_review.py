"""One independent blind comparison; no Main, Reporter or scientific worker."""
import argparse
import copy
import json
import statistics
import time
from e2_replay import ROOT,DATA,read,write,csv_rows,credential,httpx

# Fixed before collecting the second final decision; never selected using scores.
LABELS={'A':'Flat','B':'Hierarchical'}
METRICS=['research_decision_quality','evidence_consistency','limitation_recognition','research_actionability','evidence_reference_accuracy']
RUBRIC='''You are an independent blinded reviewer of two proposed next scientific decisions.
You receive one frozen pre-decision raw historical corpus and anonymous decisions A/B.
The corpus is a reviewer factual reference. It does NOT establish what was delivered
directly to a decision maker or what the decision maker actually read. Ignore claims
about context delivery, availability, or absence: you cannot verify those claims here.
No condition labels, original context form, costs, read counts or future results are
provided. Do not infer which organization method produced a decision. Score the
actual stated next decision, not subsequent unexecuted actions or robot success.

The checkpoint is after archived C035 and before C036. The source is engineering Core
records, not a recovered prior Main Provider conversation. References and numerical
results in these records are real historical evidence. Some observations are finite-load
native physics inside mathematical studies; they are NOT complete independent task
acceptance. Do not import any later candidate, later test or final outcome.

For each anonymous decision score five integers 0-4:
research_decision_quality: how appropriate and informative the next research route is;
evidence_consistency: correct interpretation of the provided math/physics and facts;
limitation_recognition: recognizes relevant scope, qualifications, missing cases and
the distinction between local math, finite dynamics and independent acceptance;
research_actionability: concrete feasible next action, parameters/held conditions,
useful observations and possible refutation at the current frozen state;
evidence_reference_accuracy: actual cited records support the claimed inference and
candidate lineage; exact IDs can be resolved in the shared corpus. Do not reward
more citations. Distinguish a missing useful reference from a false reference.
0=absent/wrong; 1=major defects; 2=partial with material gaps; 3=reasonable with
limited deficiencies; 4=accurate, grounded, specific and justified.

Do not reward text length, reading more records, polished language, generic caveats
or the number of references. Do not require the original historical route: a different
informative and feasible proposal may be equally good. A working hypothesis is not
an established fact. A record mentioned as a next read is not a claimed measurement.
Flag concrete unsupported assertions or stale redundant actions only where the raw
corpus supports that criticism. Do not assume a Plan's schema validation guarantees
task-specific scientific admission. No new action has been executed in this evaluation.
Calculate five-score arithmetic means and compare them. Equal means are a tie.
Return ONLY JSON:
{"evaluations":[{"label":"A","scores":{"research_decision_quality":0,
"evidence_consistency":0,"limitation_recognition":0,"research_actionability":0,
"evidence_reference_accuracy":0},"mean_score":0,"strengths":[],"weaknesses":[],
"supporting_source_refs":[],"evidence_specific_rationale":"..."},
{"label":"B","scores":{"research_decision_quality":0,"evidence_consistency":0,
"limitation_recognition":0,"research_actionability":0,"evidence_reference_accuracy":0},
"mean_score":0,"strengths":[],"weaknesses":[],"supporting_source_refs":[],
"evidence_specific_rationale":"..."}],"paired_winner":"A|B|tie",
"comparative_rationale":"..."}.
Keep reasons concise and grounded in the supplied evidence.
'''

def prepare():
    records=[json.loads(x) for x in (DATA/'context_replay_results.jsonl').read_text('utf-8').splitlines()]
    assert len(records)==2 and all(x['status']=='completed' for x in records)
    by={x['condition']:x for x in records}
    folder=DATA/'blind_review';folder.mkdir(parents=True,exist_ok=True)
    assert not (folder/'review_request.json').exists()
    decisions=[]
    for label,condition in LABELS.items():
        plan=copy.deepcopy(by[condition]['decision'])
        # Administrative hypothesis labels are not scientific evidence.
        if isinstance(plan.get('decision'),dict):plan['decision'].pop('hypothesis_id',None)
        decisions.append(dict(label=label,decision=plan))
    corpus=read(ROOT/'corpus.json')
    raw=[{k:v for k,v in a.items() if k not in ['information_level','flat_included','hierarchical_accessible']} for a in corpus['atoms']]
    evidence=dict(checkpoint='After C035, before C036; no future evidence.',source_kind=corpus['source_kind'],raw_archived_information=raw)
    write(folder/'anonymous_decisions.json',decisions)
    write(folder/'shared_raw_evidence.json',evidence)
    (folder/'rubric.md').write_text(RUBRIC,encoding='utf-8')
    csv_rows(folder/'human_scoring_template.csv',[dict(label=l,**{m:None for m in METRICS},mean_score=None,evidence_specific_rationale=None,reviewer=None) for l in LABELS])
    write(ROOT/'private_condition_key.json',LABELS)
    write(ROOT/'blind_review_procedure.json',dict(labels_fixed_in_source=True,anonymous_labels=list(LABELS),
        hidden=['condition labels','initial context presentation','token costs','actual read counts','later outcomes'],
        original_decisions_preserved=True,review_copy_omissions=['Administrative hypothesis_id only.'],
        inference_warning='Decision wording and evidence choices could still suggest presentation. No guarantee against reviewer inference.',
        reviewer_corpus_scope='Shared factual reference; not proof of what either Main actually read.',human_review_retained=True))
    print(json.dumps(dict(anonymous_decisions=2,shared_raw_records=len(raw))),flush=True)

def review():
    folder=DATA/'blind_review'
    if (folder/'independent_model_review.json').exists():raise RuntimeError('Review already completed; no rerating.')
    if (folder/'review_request.json').exists():raise RuntimeError('Unresolved review send; inspect before continuation.')
    cfg=read(ROOT/'replay_configuration.json');previous=read(ROOT.parent/'reporter_on_off/independent_review_configuration.json')
    provider=dict(cfg['provider']);provider['model']=previous['model']
    write(ROOT/'independent_review_configuration.json',dict(model=provider['model'],source_configuration=str(ROOT.parent/'reporter_on_off/independent_review_configuration.json'),
        base_url=provider['base_url'],proxy_url=provider.get('proxy_url'),reasoning='Provider default, not explicitly set; no function tools.',requests=1,blinded=True,new_agent_created=False))
    key=credential(provider,cfg['credentials_reference'])
    wire=dict(model=provider['model'],stream=False,store=False,messages=[dict(role='system',content=RUBRIC),
        dict(role='user',content=json.dumps(dict(shared_evidence=read(folder/'shared_raw_evidence.json'),anonymous_decisions=read(folder/'anonymous_decisions.json')),separators=(',',':')))])
    payload=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    (folder/'review_request.json').write_bytes(payload)
    print(json.dumps(dict(event='independent_review_started',model=provider['model'],wire_bytes=len(payload))),flush=True)
    started=time.perf_counter()
    with httpx.Client(timeout=600,proxy=provider.get('proxy_url'),trust_env=False,follow_redirects=False) as client:
        response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',content=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    (folder/'review_response.txt').write_text(response.text,encoding='utf-8')
    if response.status_code!=200:
        write(folder/'review_unavailable.json',dict(http_status=response.status_code,scoring_status='Human template pending; no scores invented.'))
        print(json.dumps(dict(event='review_unavailable',http_status=response.status_code)),flush=True);return
    body=response.json();content=body['choices'][0]['message']['content'].strip()
    if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
    result=json.loads(content)
    assert {x['label'] for x in result['evaluations']}==set(LABELS)
    for e in result['evaluations']:
        assert set(e['scores'])==set(METRICS) and all(type(v)==int and 0<=v<=4 for v in e['scores'].values())
        assert abs(e['mean_score']-statistics.mean(e['scores'].values()))<1e-9
    write(folder/'independent_model_review.json',dict(review=result,model=body.get('model'),usage=body.get('usage'),provider_requests=1,wall_s=time.perf_counter()-started,blinded=True,human_verification='pending'))
    print(json.dumps(dict(event='independent_review_completed',paired_winner=result['paired_winner'])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','review']);a=p.parse_args();{'prepare':prepare,'review':review}[a.mode]()
