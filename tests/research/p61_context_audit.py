"""Paired read-only P6.1 projection, using the actual baseline checkout; no sends."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tests.research.p4_context_audit import audit
from tools.research.session_handoff import packet_feedback


def compare(baseline_repo, source, *, study, handoff_event, request_event):
    arguments=dict(study=study,handoff_event=handoff_event,request_event=request_event)
    db=source/'platform.sqlite';original=hashlib.sha256(db.read_bytes()).hexdigest()
    baseline_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=baseline_repo,text=True).strip()
    program=('import json,sys; from pathlib import Path; from tests.research.p4_context_audit import audit; '
        'r,_,w=audit(Path(sys.argv[1]),**json.loads(sys.argv[2]),policy="on_demand_tools_v3"); '
        'print(json.dumps(dict(metrics=r,wire=w)))')
    previous=json.loads(subprocess.check_output([sys.executable,'-c',program,str(source),json.dumps(arguments)],
        cwd=baseline_repo,text=True,encoding='utf8'))
    result,_,wire=audit(source,**arguments,policy='research_information_flow_v1')
    old=json.loads(previous['wire']['messages'][-1]['content'].split('\n',1)[1])['research']
    new=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
    retained=dict(task=old['research_state']['task']==new['study_goal']['task'],
        task_identity=old['research_state']['task_identity']==new['study_goal']['task_identity'],
        candidate=old['research_state']['current_candidate']==new['research_focus']['candidate'],
        candidate_status=old['research_state']['candidate_status']==new['research_focus']['candidate_status'],
        task_accepted=old['research_state']['task_accepted']==new['research_focus']['task_accepted'],
        budget=old['budget']==new['budget'],exact_feedback=packet_feedback(old)==packet_feedback(new),
        loaded_plan=previous['metrics']['v2']['loaded_plan_actions']==result['v2']['loaded_plan_actions'],
        system_prompt=previous['wire']['messages'][0]==wire['messages'][0])
    if old.get('current_intent'):
        retained['formal_plan']=old['current_intent']['plan_reference']==new['research_focus']['formal_hypothesis']['plan_reference']
    retained['verified_facts']=all(any(f.get('name')==v.get('name') and f.get('value')==v.get('value')
        and f.get('source')==v.get('source') for v in new['verified_facts']) for f in old['verified_facts'])
    assert all(retained.values()),retained
    unchanged=original==hashlib.sha256(db.read_bytes()).hexdigest();assert unchanged
    return dict(baseline_sha=baseline_sha,boundary=result['boundary'],
        before=previous['metrics']['v2'],after=result['v2'],retained=retained,
        source_store_sha256=original,source_store_unchanged=unchanged,
        token_estimator=result['token_estimator'],
        removed_repeated_fields=[k for k in ('current_intent','history_trace','research_state','recent_round','tool_directory') if k in old and k not in new],
        resources=dict(real_provider_requests=0,new_math_workers=0,physical_workers=0,rl_training=0),
        limitation='Read-only projections of the same archived state and allowance; token counts are local estimates, not usage. Newly direct tool schemas add bytes and avoid routing calls; no model-behavior claim.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-repo',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--study',required=True)
    parser.add_argument('--handoff-event',type=int,required=True)
    parser.add_argument('--request-event',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=vars(parser.parse_args());output=args.pop('output');report=compare(**args)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(before=report['before']['components'],after=report['after']['components'],retained=report['retained'])))
