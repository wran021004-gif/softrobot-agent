"""Primary KS16 review uses the unchanged original E1 four scoring definitions.

The earlier generic context review remains an auxiliary record, never pooled or
renamed as original E1 decision quality. No Main decision is rerun or replaced.
"""
import ast
import copy
import json
import random
from pathlib import Path
from build_evidence import *
from decision_supplements import PROVIDER,CFG,credential,httpx,send,stamp,KS_CHOICES,corpus,usage

tree=ast.parse(source(B,ARCH+'knowledge_skill/e1_review.py'))
E1_RUBRIC=next(ast.literal_eval(s.value) for s in tree.body if isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RUBRIC' for t in s.targets))
old='''There is no scientific candidate or prior current-study measurement
at this checkpoint. Historical material is reference guidance, never fresh acceptance.
That does not prove that a separately recorded earlier/concurrent trial never existed.'''
new='''The current candidate and current-study measurements are exactly those in the
supplied frozen corpus. Historical resource material remains reference guidance,
never fresh acceptance. No post-checkpoint outcome is provided.'''
assert old in E1_RUBRIC
RUBRIC=E1_RUBRIC.replace(old,new)


def freeze():
    p=OUT/'supplementary_experiments/knowledge_skill_primary_review_protocol.json'
    if not p.exists():
        write_json('supplementary_experiments/knowledge_skill_primary_review_protocol.json',dict(frozen_at=stamp(),
            original_rubric_source=locator(B,ARCH+'knowledge_skill/e1_review.py','#RUBRIC'),
            scoring_definitions_unchanged=True,only_state_description_adapted=True,
            change='Original no-current-candidate assumption replaced by the actual later frozen-checkpoint state; four metric definitions and 0–4 anchors unchanged.',
            reason='Generic Context five-dimensional auxiliary reviews cannot be substituted for original E1 decision_quality.',
            before_inspecting_supplemental_score_values=True,auxiliary_reviews_preserved=True,main_decisions_not_rerun=True,
            rubric=RUBRIC))


def run():
    freeze();key=credential(PROVIDER,CFG['credentials_reference'])
    rows=[]
    with httpx.Client(timeout=PROVIDER['timeout_s'],trust_env=False,follow_redirects=False) as client:
        for task,stage in KS_CHOICES:
            sessions=[]
            for c in ['K-S-','K+S-','K-S+','K+S+']:
                p=OUT/f'supplementary_experiments/knowledge_skill/sessions/{stage}-{c}.json'
                if not p.exists():raise RuntimeError('Await all four original sessions; do not invent or replace a cell.')
                d=json.loads(p.read_text('utf-8'))
                if d['status'] not in ['completed','request_budget_exhausted']:raise RuntimeError('Await terminal session state.')
                sessions.append(d)
            reviewfile=OUT/f'supplementary_experiments/knowledge_skill/blind_primary/{stage}.json'
            if reviewfile.exists():review=json.loads(reviewfile.read_text('utf-8'))
            else:
                experiences=source(B,ARCH+'knowledge_skill/snapshots/'+task+'.json')['experience_records']
                substitutions={};library=[]
                for i,e in enumerate(experiences,1):
                    alias='R'+str(i);substitutions[e['key']]=alias;substitutions[e['key'].split('@')[0]]=alias
                    body=e['archived_result'];library.append(dict(resource_id=alias,content=body['content'],applicability=body['applicability'],limitations=body['limitations']))
                def mask(v):
                    if isinstance(v,dict):return {k:mask(x) for k,x in v.items()}
                    if isinstance(v,list):return [mask(x) for x in v]
                    if isinstance(v,str):
                        for old,new in sorted(substitutions.items(),key=lambda p:-len(p[0])):v=v.replace(old,new)
                    return v
                order=list(sessions);random.Random('E1-four-metric-'+stage).shuffle(order)
                anonymous=[]
                for label,d in zip('ABCD',order):
                    plan=copy.deepcopy(d['decision']) if isinstance(d.get('decision'),dict) else dict(submission_status='no_valid_decision',reason='No valid Plan submitted under frozen protocol.')
                    plan.pop('experience_disposition',None)
                    if isinstance(plan.get('decision'),dict):
                        plan['decision'].pop('hypothesis_id',None);plan['decision'].pop('version',None)
                    anonymous.append(dict(label=label,decision=mask(plan)))
                records,_=corpus(task,stage)
                body,account=send(client,key,[dict(role='system',content=RUBRIC),dict(role='user',content=json.dumps(dict(frozen_checkpoint=records,reference_library=library,anonymous_decisions=anonymous),ensure_ascii=False,separators=(',',':')))])
                content=body['choices'][0]['message']['content'].strip()
                if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
                review=dict(checkpoint_id=stage,review=json.loads(content),request_accounting=account,raw_review_content=content,
                    private_label_key={l:d['session_id'] for l,d in zip('ABCD',order)},anonymous_decisions=anonymous,
                    rubric_reference='supplementary_experiments/knowledge_skill_primary_review_protocol.json',
                    hidden=['condition','cost','read count','future outcomes','previous scores'],same_model_dependence=True)
                reviewfile.parent.mkdir(parents=True,exist_ok=True);reviewfile.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n','utf-8')
                print('Primary original-rubric KS review complete',stage,flush=True)
            for d in sessions:
                label=next(l for l,s in review['private_label_key'].items() if s==d['session_id'])
                ev=next(x for x in review['review']['evaluations'] if x['label']==label);scores=ev['scores']
                for metric in ['decision_quality','evidence_consistency','historical_experience_utilization','research_actionability']:
                    assert scores[metric] in [0,1,2,3,4,'UNKNOWN']
                rows.append(dict(protocol_id='KS16-decision-only-20261116',task_id=task,checkpoint_id=stage,condition=d['condition'],session_status=d['status'],
                    **{k:scores[k] for k in ['historical_experience_utilization','decision_quality','evidence_consistency','research_actionability']},
                    experience_integration=ev.get('experience_integration'),knowledge_observations=ev.get('knowledge_observations'),skill_observations=ev.get('skill_observations'),
                    invalid_research_actions=ev.get('invalid_research_actions'),rationale=ev.get('evidence_specific_rationale'),
                    actual_cumulative_input_tokens=usage(d,'prompt_tokens'),output_tokens=usage(d,'completion_tokens'),provider_requests=len(d['requests']),
                    source_reference=f'paper_evidence/supplementary_experiments/knowledge_skill/sessions/{d["session_id"]}.json',
                    blind_reference=reviewfile.relative_to(ROOT).as_posix(),rubric_scope='original E1 four metrics; checkpoint fact updated only',new_physics=0))
    write_csv('architecture_metrics/knowledge_skill_supplement.csv',rows)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze-only',action='store_true');args=p.parse_args()
    freeze() if args.freeze_only else run()
