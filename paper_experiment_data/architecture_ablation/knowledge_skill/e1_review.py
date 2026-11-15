"""Two stateless reviews through the existing independent model configuration.

No research agent, Planner or scientific worker is created. Administrative source
and condition fields are hidden; original decisions remain unchanged on disk.
"""
import argparse
import copy
import json
import time
import uuid
from e1_replay import ROOT, DATA, PREVIOUS, TASKS, read, write, csv_rows, credential, httpx

LABELS = {
    'T04': {'A':'K-S+', 'B':'K+S+', 'C':'K-S-', 'D':'K+S-'},
    'T07': {'A':'K+S-', 'B':'K-S-', 'C':'K+S+', 'D':'K-S+'},
}
METRICS = ['decision_quality','evidence_consistency','historical_experience_utilization','research_actionability']
RUBRIC = '''You are an independent blinded scientific research-decision reviewer.
Compare four anonymous decisions A/B/C/D against the shared frozen checkpoint and
reference experience library. The library is a REVIEWER-ONLY factual reference, not
evidence that every decision maker received it. Which resources were supplied to any
decision maker is deliberately hidden. Ignore all statements about resource availability,
delivery, access, or absence when scoring evidence consistency: such administrative
claims cannot be checked from your materials and must never attract a penalty. Score
historical utilization from evidenced positive use of facts/procedures in the decision,
not from a claim about having or lacking access. Do not infer or reconstruct condition labels.
You are not given condition labels, source actor/model,
future results, final acceptance, or costs. Do not infer conditions or favor any label.
Judge ONLY the next proposed decision and its stated downstream plan, not unshown
subsequent actions. There is no scientific candidate or prior current-study measurement
at this checkpoint. Historical material is reference guidance, never fresh acceptance.
That does not prove that a separately recorded earlier/concurrent trial never existed.
When a comparative trial's current-study lineage is not established, mark its provenance
unverified rather than inventing a contradiction. Do not add facts that are absent.

Give four integer scores 0-4 to each decision:
decision_quality: appropriateness and informativeness of the next research route/action;
evidence_consistency: accurate facts, frozen bounds, applicability, supported references;
historical_experience_utilization: specific correct use of identifiable reference facts
and/or procedures in making this decision, rather than mere citations;
research_actionability: a concrete current-interface action and useful expected/refuting
observations that could guide an actual next step.
0=wrong/unsupported or no evidenced utilization; 1=major defects; 2=partly correct with
clear deficiencies; 3=reasonable and mostly grounded; 4=accurate, specific and justified.
If no historical use is identifiable, utilization can be 0 without automatically lowering
the other scores. Do not penalize a method solely because it differs from a reference
recommendation; a justified informative alternative can be equally good.
Do not reward length, polished prose, generic caveats, or extra nominal steps. Do not
infer unmentioned procedures just because they occur in the library. Equally reasonable
decisions deserve equal scores. A hypothesis is not a claimed established fact.

T04: distinguish historical route evidence from current-domain admissibility. Evaluate
method applicability for timed tracking, physical initial-state qualification, bank/seed
ownership, and preservation of original full-horizon semantics when actually stated.
T07: evaluate historical structure use versus current generation, one common structure
across all required cases, compatibility of results across structure versions, and transfer
of control seeds versus importing states/acceptance, when actually stated. Unmentioned
later steps are not automatically invalid, but cannot earn procedural-use credit.
Record invalid_research_actions only for concrete proposed actions contradicted by the
frozen state, domain or interfaces; distinguish an unverified executable assumption from
a proven invalid action. Parsing a Plan does not establish task-specific admission.

Return ONLY JSON with this structure:
{"evaluations":[{"label":"A","scores":{"decision_quality":0,"evidence_consistency":0,
"historical_experience_utilization":0,"research_actionability":0},
"knowledge_observations":{"historical_facts":"observed|not_observed|not_assessable",
"historical_conclusions":"observed|not_observed|not_assessable",
"reasonable_route":"observed|not_observed|not_assessable",
"avoids_known_ineffective_attempts":"observed|not_observed|not_assessable"},
"skill_observations":{"workflow":"observed|not_observed|not_assessable",
"structure_consistency":"observed|not_observed|not_assessable",
"initial_state_and_control_seed":"observed|not_observed|not_assessable",
"critical_constraints":"observed|not_observed|not_assessable"},
"experience_integration":"Evidence-specific description of whether facts and procedure
are connected into the proposed action; do not assert a causal experimental effect.",
"invalid_research_actions":[{"action":"...","reason":"...","severity":"minor|moderate|severe"}],
"strengths":[],"weaknesses":[],"evidence_specific_rationale":"..."},
...same fields for B/C/D...],"comparative_rationale":"..."}.
Keep each explanation concise and grounded in the supplied materials.
'''


def blind_materials():
    key_file=ROOT/'private_condition_key.json'
    key=[dict(task_id=t,anonymous_label=l,condition=c) for t, mapping in LABELS.items() for l,c in mapping.items()]
    if key_file.exists():assert read(key_file)==key
    else:write(key_file,key)
    records=[json.loads(line) for line in (DATA/'decision_results.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(records)==6 and all(x['status']=='completed' for x in records)
    for task in TASKS:
        snapshot=read(ROOT/'snapshots'/f'{task}.json')
        original={x['condition']:x['decision'] for x in records if x['task_id']==task}
        original['K+S+']=read(ROOT/'historical_reference'/f'{task}.json')['decision']
        # Longest string first prevents replacing an unversioned ID inside @1.
        substitutions={}
        resources=[]
        for i,entry in enumerate(snapshot['experience_records'],1):
            alias='R'+str(i)
            substitutions[entry['key']]=alias
            substitutions[entry['key'].split('@')[0]]=alias
            resources.append(dict(resource_id=alias,content=entry['archived_result']['content'],
                                  applicability=entry['archived_result']['applicability'],
                                  limitations=entry['archived_result']['limitations']))
        def anonymize(v):
            if isinstance(v,dict):
                return {anonymize(k):anonymize(x) for k,x in v.items()}
            if isinstance(v,list):return [anonymize(x) for x in v]
            if isinstance(v,str):
                for old,new in sorted(substitutions.items(),key=lambda x:-len(x[0])):v=v.replace(old,new)
            return v
        decisions=[]
        for label,condition in LABELS[task].items():
            plan=copy.deepcopy(original[condition])
            plan.pop('experience_disposition',None)
            if isinstance(plan.get('decision'),dict):
                plan['decision'].pop('hypothesis_id',None)
                plan['decision'].pop('version',None)
            decisions.append(dict(label=label,decision=anonymize(plan)))
        folder=DATA/'blind_review'/task
        write(folder/'anonymous_decisions.json',decisions)
        write(folder/'evidence.json',dict(checkpoint=snapshot['base_context'],reference_library=anonymize(resources)))
        (folder/'rubric.md').write_text(RUBRIC,encoding='utf-8')
        human=[dict(task_id=task,label=l,**{k:None for k in METRICS},invalid_research_actions=None,
                    evidence_specific_rationale=None,reviewer=None) for l in ['A','B','C','D']]
        csv_rows(folder/'human_scoring.csv',human)
    write(ROOT/'blind_review_procedure.json',dict(
        label_mapping_fixed_in_source=True,condition_mapping_file=str(key_file),
        hidden=['condition labels','historical versus LLM actor','costs','future actions and FULL outcomes'],
        transformations=['Administrative experience_disposition omitted from review copies only.',
                         'Administrative hypothesis_id/version omitted from review copies only.',
                         'Resource identifiers replaced consistently with R1/R2/...; content retained.',
                         'Wording and action differences can still suggest source or availability; blinding is not guaranteed against inference.'],
        original_decisions_unchanged=True,human_scoring_retained=True))
    print(json.dumps(dict(blind_tasks=2,anonymous_decisions=8,human_templates=2)),flush=True)


def review():
    previous=read(PREVIOUS/'independent_review_configuration.json')
    cfg=read(ROOT/'replay_configuration.json');provider=dict(cfg['provider']);provider['model']=previous['model']
    key=credential(provider,cfg['credentials_reference'])
    write(ROOT/'independent_review_configuration.json',dict(model=provider['model'],main_model=cfg['provider']['model'],
          transport=previous['transport'],reasoning='gateway_default_not_exposed',requests_total=2,
          requests_per_four_decision_comparison=1,blinded=True,human_review_retained=True,new_agent_created=False))
    with httpx.Client(timeout=600,trust_env=False,follow_redirects=False) as client:
        for task in TASKS:
            folder=DATA/'blind_review'/task
            if (folder/'independent_model_review.json').exists():continue
            if (folder/'review_request.json').exists():raise RuntimeError('Unresolved review attempt: inspect before sending.')
            wire=dict(model=provider['model'],stream=False,messages=[dict(role='system',content=RUBRIC),
                      dict(role='user',content=json.dumps(dict(shared_evidence=read(folder/'evidence.json'),anonymous_decisions=read(folder/'anonymous_decisions.json')),separators=(',',':')))])
            write(folder/'review_request.json',wire)
            print(json.dumps(dict(event='review_started',task_id=task)),flush=True);started=time.perf_counter()
            response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',json=wire,headers={'Authorization':'Bearer '+key})
            (folder/'review_response.txt').write_text(response.text,encoding='utf-8')
            if response.status_code!=200:raise RuntimeError('Review gateway rejected request; stop all sends and inspect response.')
            body=response.json();content=body['choices'][0]['message']['content'].strip()
            if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
            result=json.loads(content)
            assert {x['label'] for x in result['evaluations']}=={'A','B','C','D'}
            for x in result['evaluations']:
                assert set(x['scores'])==set(METRICS)
                assert all(type(v)==int and 0<=v<=4 for v in x['scores'].values())
            write(folder/'independent_model_review.json',dict(review=result,model=body.get('model'),session_id=str(uuid.uuid4()),
                  usage=body.get('usage'),wall_s=time.perf_counter()-started,provider_requests=1,blinded=True,human_verification='pending'))
            print(json.dumps(dict(event='review_completed',task_id=task)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','review']);args=parser.parse_args()
    {'prepare':blind_materials,'review':review}[args.mode]()
