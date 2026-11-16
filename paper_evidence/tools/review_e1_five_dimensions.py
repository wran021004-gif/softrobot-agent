"""Add the same five-dimensional blind rubric to the eight original E1 decisions.

Original four-dimensional scores stay authoritative for their original metrics.
This file adds a separate score set; it never changes Main decisions or old scores.
"""
import copy
import json
from build_evidence import *
from decision_supplements import REVIEW,PROVIDER,CFG,credential,httpx,send,stamp

METRICS=['physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','evidence_reference_accuracy']


def run():
    protocol=OUT/'supplementary_experiments/e1_five_dimension_protocol.json'
    if not protocol.exists():
        write_json('supplementary_experiments/e1_five_dimension_protocol.json',dict(frozen_at=stamp(),
            user_requested=True,rubric=REVIEW,five_metrics=METRICS,original_scores_unchanged=True,
            historical_utilization='retain as a separate original E1 metric; not in the Context five dimensions',
            pairing='original four decisions per task; no Main reruns',blinding='original anonymous four-LLM material; conditions/costs/previous scores hidden',
            interpretation='new descriptive assessment, separate from original E1 four-dimensional score set; saturation retained'))
    key=credential(PROVIDER,CFG['credentials_reference'])
    with httpx.Client(timeout=PROVIDER['timeout_s'],trust_env=False,follow_redirects=False) as client:
        for task in ['T04','T07']:
            rel='supplementary_experiments/e1_five_dimension/'+task+'.json';p=OUT/rel
            if p.exists():continue
            base=ARCH+'knowledge_skill/figure_data/blind_review/complete_four_llm/'+task+'/'
            anonymous=source(B,base+'anonymous_decisions.json');evidence=source(B,base+'evidence.json')
            messages=[dict(role='system',content=REVIEW+'\nThe reference experience library is reviewer-only factual reference. Do not infer resource availability or penalize administrative access statements. There is no current candidate at this original E1 checkpoint; judge an appropriate next proposed construction/research route. Historical utilization is separately retained, not replaced by these five dimensions.'),
                dict(role='user',content=json.dumps(dict(frozen_evidence=evidence,key_evidence_checklist=[],anonymous_decisions=anonymous),ensure_ascii=False,separators=(',',':')))]
            body,account=send(client,key,messages);content=body['choices'][0]['message']['content'].strip()
            if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
            value=dict(task_id=task,review=json.loads(content),request_accounting=account,raw_review_content=content,
                source_reference=locator(B,base+'anonymous_decisions.json'),rubric_reference='supplementary_experiments/e1_five_dimension_protocol.json')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
            print('Original E1 five-dimension review complete',task,flush=True)
    summarize()


def summarize():
    records=[];original=source(B,ARCH+'knowledge_skill/figure_data/factorial_results.csv')
    for task in ['T04','T07']:
        p=OUT/'supplementary_experiments/e1_five_dimension'/f'{task}.json'
        if not p.exists():continue
        review=json.loads(p.read_text('utf-8'))['review']
        for r in original:
            if r['task_id']!=task:continue
            ev=next(x for x in review['evaluations'] if x['label']==r['anonymous_label'])
            for metric in METRICS:
                records.append(dict(protocol_id='E1-original-five-dimension-reassessment',task_id=task,checkpoint_id=task+'-original-E1',condition=r['condition'],
                    dimension=metric,score=ev['scores'][metric],session_status='completed',assessment_role='new common five-dimension assessment; original four-dimensional scores retained',
                    source_reference=p.relative_to(ROOT).as_posix(),decision_reference=portable(r['decision_source_file'])))
    folder=OUT/'supplementary_experiments/knowledge_skill/blind'
    for p in sorted(folder.glob('*.json')):
        rev=json.loads(p.read_text('utf-8'))
        if rev.get('status')!='completed':continue
        for ev in rev['review']['evaluations']:
            sid=rev['private_label_key'][ev['label']];stage=rev['checkpoint_id'];condition=sid[len(stage)+1:]
            session=json.loads((OUT/'supplementary_experiments/knowledge_skill/sessions'/f'{sid}.json').read_text('utf-8'))
            for metric in METRICS:
                records.append(dict(protocol_id='KS16-five-dimension',task_id=stage[:3],checkpoint_id=stage,condition=condition,
                    dimension=metric,score=ev['scores'].get(metric,'UNKNOWN'),session_status=session['status'],assessment_role='same five-dimension rubric; checkpoint-specific descriptive comparison',
                    source_reference=p.relative_to(ROOT).as_posix(),decision_reference='paper_evidence/supplementary_experiments/knowledge_skill/sessions/'+sid+'.json'))
    write_csv('architecture_metrics/knowledge_skill_five_dimension.csv',records)
    write_csv('figure_data/fig07_knowledge_skill_five_dimension.csv',records)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--summarize-only',action='store_true');a=p.parse_args()
    summarize() if a.summarize_only else run()
