"""One fresh four-LLM blind review per task, reusing the original E1 rubric/model."""
import argparse
import copy
import json
import sys
import time
from pathlib import Path

RUN=Path(__file__).resolve().parent;ROOT=RUN.parent;sys.path.insert(0,str(ROOT))
from e1_replay import DATA,TASKS,read,write,csv_rows,credential,httpx
from e1_review import RUBRIC,METRICS

LABELS={
    'T04':{'A':'K-S-','B':'K+S+','C':'K+S-','D':'K-S+'},
    'T07':{'A':'K+S+','B':'K-S-','C':'K-S+','D':'K+S-'},
}


def prepare():
    records=[json.loads(s) for s in (DATA/'decision_results.jsonl').read_text('utf-8').splitlines()]
    assert len(records)==8 and all(r['status']=='completed' for r in records)
    assert {(r['task_id'],r['condition']) for r in records}=={(t,c) for t in TASKS for c in ['K-S-','K+S-','K-S+','K+S+']}
    write(RUN/'private_condition_key.json',LABELS)
    for task in TASKS:
        snapshot=read(ROOT/'snapshots'/f'{task}.json')
        original={r['condition']:r['decision'] for r in records if r['task_id']==task}
        substitutions={};resources=[]
        for i,entry in enumerate(snapshot['experience_records'],1):
            alias='R'+str(i);substitutions[entry['key']]=alias;substitutions[entry['key'].split('@')[0]]=alias
            resources.append(dict(resource_id=alias,content=entry['archived_result']['content'],applicability=entry['archived_result']['applicability'],limitations=entry['archived_result']['limitations']))
        def anon(v):
            if isinstance(v,dict):return {anon(k):anon(x) for k,x in v.items()}
            if isinstance(v,list):return [anon(x) for x in v]
            if isinstance(v,str):
                for old,new in sorted(substitutions.items(),key=lambda x:-len(x[0])):v=v.replace(old,new)
            return v
        decisions=[]
        for label,condition in LABELS[task].items():
            plan=copy.deepcopy(original[condition]);plan.pop('experience_disposition',None)
            if isinstance(plan.get('decision'),dict):
                plan['decision'].pop('hypothesis_id',None);plan['decision'].pop('version',None)
            decisions.append(dict(label=label,decision=anon(plan)))
        folder=DATA/'blind_review/complete_four_llm'/task
        assert not (folder/'review_request.json').exists()
        write(folder/'anonymous_decisions.json',decisions)
        write(folder/'evidence.json',dict(checkpoint=snapshot['base_context'],reference_library=anon(resources)))
        (folder/'rubric.md').write_text(RUBRIC,encoding='utf-8')
        csv_rows(folder/'human_scoring.csv',[dict(task_id=task,label=l,**{m:None for m in METRICS},invalid_research_actions=None,evidence_specific_rationale=None,reviewer=None) for l in LABELS[task]])
    write(RUN/'blind_review_procedure.json',dict(rubric_source=(ROOT/'e1_review.py').as_posix(),rubric_unchanged=True,all_decisions_Main_LLM=True,
        engineering_Core_Plans_excluded=True,previous_reviews_archived=True,new_joint_reviews=2,new_agents=0,human_review_retained=True,
        hidden=['condition','acquisition phase','costs','future results','source actors'],
        transformations=['Same original E1 administrative omissions and consistent R1/R2 resource aliases. Original decisions remain unchanged.'],
        limitation='Wording can still suggest resource use; each review is a single independent-model judgment.'))
    print(json.dumps(dict(prepared=True,anonymous_Main_decisions=8,engineering_reference_decisions=0)),flush=True)


def review():
    original=read(ROOT/'replay_configuration.json');cfg=read(ROOT/'independent_review_configuration.json')
    provider=copy.deepcopy(original['provider']);provider['model']=cfg['model'];key=credential(provider,original['credentials_reference'])
    write(RUN/'independent_review_configuration.json',dict(model=provider['model'],transport=cfg['transport'],reasoning=cfg['reasoning'],
        source_configuration=(ROOT/'independent_review_configuration.json').as_posix(),new_agents=0,requests_per_task=1,tasks=list(TASKS),human_verification='pending'))
    with httpx.Client(timeout=600,trust_env=False,follow_redirects=False) as client:
        for task in TASKS:
            folder=DATA/'blind_review/complete_four_llm'/task
            if (folder/'review_request.json').exists():raise RuntimeError('Review already sent; no automatic rerating.')
            wire=dict(model=provider['model'],stream=False,messages=[dict(role='system',content=RUBRIC),
                dict(role='user',content=json.dumps(dict(shared_evidence=read(folder/'evidence.json'),anonymous_decisions=read(folder/'anonymous_decisions.json')),separators=(',',':')))])
            payload=httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire).content
            (folder/'review_request.json').write_bytes(payload)
            print(json.dumps(dict(event='four_LLM_review_started',task_id=task)),flush=True);begun=time.perf_counter()
            response=client.post(provider['base_url']+'/chat/completions',json=wire,headers={'Authorization':'Bearer '+key})
            (folder/'review_response.txt').write_text(response.text,encoding='utf-8')
            if response.status_code!=200:
                write(folder/'review_unavailable.json',dict(http_status=response.status_code,score_status='Human scoring pending; no scores invented.'))
                raise RuntimeError('Review Gateway rejected; stop subsequent requests and inspect actual response.')
            body=response.json();text=body['choices'][0]['message']['content'].strip()
            if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
            result=json.loads(text)
            assert {e['label'] for e in result['evaluations']}=={'A','B','C','D'}
            for e in result['evaluations']:
                assert set(e['scores'])==set(METRICS) and all(type(v)==int and 0<=v<=4 for v in e['scores'].values())
            write(folder/'independent_model_review.json',dict(review=result,model=body.get('model'),usage=body.get('usage'),wall_s=time.perf_counter()-begun,
                provider_requests=1,blinded=True,human_verification='pending',all_four_decisions_Main_LLM=True,engineering_Core_Plans_included=False))
            print(json.dumps(dict(event='four_LLM_review_completed',task_id=task)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','review']);a=p.parse_args();{'prepare':prepare,'review':review}[a.mode]()
