"""Independent stateless model review of the six already-anonymized decision pairs."""
import json,time,uuid
from run_ablation import ROOT,read,write,httpx,credential

RUBRIC='''You are an independent blinded scientific decision reviewer. Evaluate two anonymous Main decisions, A and B, using ONLY the shared raw evidence.
You receive no experimental labels, explanation reports, historical next decisions, or cost information. Do not infer their conditions.
Give each decision five integer scores 0-4, equally weighted: physical_interpretation, evidence_consistency,
limitation_recognition, research_actionability, main_decision_quality. 0=wrong/unsupported,1=major defects,
2=partly correct with clear deficiencies,3=reasonable and mostly consistent,4=accurate, well-grounded and scientifically specific.
Do not reward length, polished prose, repeated caveats or the mere number of hypotheses. Two equally reasonable actions deserve equal scores.
Evaluate whether the action actually addresses the missing evidence or discriminates mechanisms. Original task constraints remain frozen.
Distinguish proposed/testable hypotheses with expected and weakening observations from assertions of established fact: unproven hypotheses are not automatically unsupported claims.
Finite differences/contrasts are local and need valid qualification; no strict derivative, global causality or task success may be invented.
Check semantic evidence-reference correctness, not just real IDs. A request that parses is not proof of task-specific executable admission.
Return ONLY JSON {"evaluations":[{"label":"A","scores":{"physical_interpretation":0,"evidence_consistency":0,"limitation_recognition":0,"research_actionability":0,"main_decision_quality":0},"unsupported_claims":[{"claim":"...","reason":"...","severity":"minor|moderate|severe"}],"reference_assessment":{"correct":0,"total":0,"issues":[]},"strengths":[],"weaknesses":[]},...same B...],"preferred":"A|B|tie","rationale":"..."}.
Supply evidence-specific reasons. Do not manufacture missing measurements or reinterpret sampled or failed qualification as independent success.
'''
cfg=read(ROOT/'replay_configuration.json');provider=dict(cfg['provider']);provider['model']='gpt-6-astra'
# The model is available through the already connected gateway, independently of Main.
# This is a review role requested in the protocol, not a new research Agent or worker.
key=credential(provider,cfg['credentials_reference'])
write(ROOT/'independent_review_configuration.json',dict(model=provider['model'],main_model=cfg['provider']['model'],
    transport='existing text-only gateway',reasoning='gateway_default_not_exposed',budget=6,max_requests_per_pair=1,
    labels_hidden=True,reporter_reports_hidden=True,costs_hidden=True,human_review_retained=True))
folders=sorted(p for p in (ROOT/'blind_review').iterdir() if p.is_dir())
with httpx.Client(timeout=600,trust_env=False,follow_redirects=False) as client:
 for folder in folders:
  out=folder/'independent_model_review.json'
  if out.exists():continue
  request=folder/'review_request.json'
  if request.exists():raise RuntimeError('Unknown review attempt; no automatic retry.')
  wire=dict(model=provider['model'],stream=False,messages=[dict(role='system',content=RUBRIC),
    dict(role='user',content=json.dumps(dict(raw_evidence=read(folder/'evidence.json'),anonymous_decisions=read(folder/'anonymous_decisions.json')),separators=(',',':')))])
  write(request,wire);t=time.perf_counter();print(json.dumps(dict(review_started=folder.name,model=provider['model'])),flush=True)
  response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',json=wire,headers={'Authorization':'Bearer '+key})
  (folder/'review_response.txt').write_text(response.text,encoding='utf8');response.raise_for_status();body=response.json();content=body['choices'][0]['message']['content'].strip()
  if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
  result=json.loads(content);assert {r['label'] for r in result['evaluations']}=={'A','B'}
  for row in result['evaluations']:
   assert set(row['scores'])=={'physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','main_decision_quality'}
   assert all(type(v)==int and 0<=v<=4 for v in row['scores'].values())
  write(out,dict(review=result,model=body.get('model'),session_id=str(uuid.uuid4()),wall_s=time.perf_counter()-t,
      usage=body.get('usage'),provider_requests=1,blinded=True))
  print(json.dumps(dict(review_completed=folder.name,preferred=result['preferred'],wall_s=time.perf_counter()-t)),flush=True)
