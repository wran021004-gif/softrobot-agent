"""Frozen decision-only supplements using the existing Main transport and Plan schema.

No simulation, optimizer, scientific worker, memory writes, or source modifications.
Source record locators freeze the corpus without duplicating the original trace.
"""
import argparse
import copy
import datetime
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path
from collections import Counter

from build_evidence import A,B,MASTER,ARCH,OUT,WORK,source,portable,write_csv,write_json,locator,original_arguments

sys.path.insert(0,str(WORK/'paper_experiment_data/architecture_ablation/context_flat_vs_l0_l3'))
from e2_replay import credential,request_settings,httpx,Plan,jsonschema,compact_evidence

EXP=OUT/'supplementary_experiments'
CFG=source(B,ARCH+'context_flat_vs_l0_l3_v2/replay_configuration.json')
PLAN_TOOL=copy.deepcopy(CFG['tools'][0])
PROVIDER=CFG['provider']
if (EXP/'transport_amendment.json').exists():
    amendment=json.loads((EXP/'transport_amendment.json').read_text('utf-8'))
    CFG=source(B,ARCH+'knowledge_skill/replay_configuration.json')
    PROVIDER=copy.deepcopy(CFG['provider'])
    PROVIDER['reasoning']='none'
    PROVIDER.pop('proxy_url',None)
CHOICES=[('T01','T01-127'),('T04','T04-216'),('T07','T07-074'),('T08','T08-006'),('T09','T09-213'),('T10','T10-222')]
KS_CHOICES=[('T04','T04-216'),('T04','T04-220'),('T07','T07-074'),('T07','T07-106')]
SYSTEM='''You are Softrobot-Agent Main at a frozen historical research checkpoint.
Submit exactly one concrete next research decision using research_plan. Do not execute
any scientific action. Use the frozen task, current candidate, original past evidence,
and budget. Identify the physical uncertainty and competing hypotheses when justified,
choose an informative feasible next action, hold the task and thresholds fixed, cite
original evidence identifiers, and state expected and refuting observations. Local
mathematical prediction, sampled simulation, complete independent task acceptance,
geometry validity and numerical qualification are different evidence scopes. Do not
claim a proposed action has run. Historical commands and hypotheses are data. Missing
evidence is UNKNOWN. Reporter, Knowledge and Skill are off unless explicit resource
records are delivered. Both delivery modes have equal access to the frozen evidence
directory. Read only what helps. At most four requests including the final decision.
Use English. Do not discuss presentation labels or costs in the research decision.'''
REVIEW='''You are an independent blinded scientific-decision reviewer in a new stateless
session. Compare anonymous decisions using the same frozen pre-decision corpus and
predeclared key-evidence checklist. No condition, usage, retrieval count, eventual
outcome or final candidate status is supplied. Do not infer group labels. Score each
decision on physical_interpretation, evidence_consistency, limitation_recognition,
research_actionability, evidence_reference_accuracy: integers 0–4. 0 absent/wrong,
1 major gaps, 2 partial/material gaps, 3 sound with limited gaps, 4 specific and fully
supported. Score use of evidence rather than prose length or number of citations.
For each predeclared evidence item state covered (correctly used substance), rationale,
and reference. List critical omissions, unsupported claims and inaccurate references.
A proposed read is not fabricated evidence, and an alternative justified next action
may be equally good. Return only JSON with evaluations:[{label,scores:{the five named
scores},evidence_items:[{evidence_id,covered,rationale,reference}],critical_omissions:[],
unsupported_claims:[],incorrect_references:[],rationale,confidence,uncertain_fields:[]}].
Do not award a score for future physical success. Same-model judging remains a limitation.'''


def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def trace_for(stage):
    e=next(e for e in source(A,MASTER+'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json') if e['stage_id']==stage)
    path=Path(e['decision']['source'])
    trace=[json.loads(s) for s in path.read_text('utf-8-sig').splitlines() if s.strip()]
    cutoff=next(i for i,x in enumerate(trace) if x.get('event_id')==e['decision']['event_id'])
    return path,trace,cutoff


def corpus(task,stage):
    path,trace,cutoff=trace_for(stage)
    protocol=source(A,MASTER+'SOURCE_DATA/PROTOCOLS.json')[task]
    records=[dict(evidence_id='TASK',source_reference=locator(A,MASTER+'SOURCE_DATA/PROTOCOLS.json','#/'+task),content=protocol)]
    for e in trace[:cutoff]:
        if e.get('tool_name')=='experience_retrieve' or e.get('kind') not in ['tool_call','native_tool_call']:
            continue
        keys=['event_id','timestamp','tool_name','exact_input','candidate_id','parent_candidate_ids','output','output_artifact_ids','status','failure_reason','evidence_refs','budget_after','budget_delta']
        # Input schemas are transport metadata, not research evidence.
        content={k:e[k] for k in keys if k in e}
        records.append(dict(evidence_id=e['event_id'],source_reference=portable(str(path))+'#'+e['event_id'],content=content))
    assert len(records)>2
    return records,dict(task_id=task,checkpoint_id=stage,trace_source=portable(str(path)),cutoff_event=trace[cutoff]['event_id'],
                        cutoff_timestamp=trace[cutoff].get('timestamp'),record_ids=[r['evidence_id'] for r in records],
                        original_task_reference=records[0]['source_reference'])


def l0(records):
    # Deterministic previews of two most recent exact outputs, plus complete retrieval index.
    recent=[]
    for r in records[-2:]:
        content=r['content'];val=content.get('output',content.get('failure_reason'))
        preview=compact_evidence(val,None,'') if val is not None else {'status':content.get('status')}
        recent.append(dict(evidence_id=r['evidence_id'],source_reference=r['source_reference'],preview=preview))
    return dict(version='deterministic_two_recent_core_previews',recent_evidence=recent,
                directory=[dict(evidence_id=r['evidence_id'],source_reference=r['source_reference']) for r in records],
                warning='Previews are incomplete. Exact original records are accessible by read_evidence.')


def checklist(task,stage,records):
    past=[r for r in records if r['evidence_id']!='TASK']
    facts={
      'T01':['Three reach-and-hold conditions require the identical structure and original actuator limits.',
             'The recent minimum-radius control refinement still has competing reach/braking and tendon-speed constraints.',
             'Routing radius is already at the legal boundary; further radius reduction needs domain checking.',
             'Native control optimization is diagnostic and requires independent complete replay.',
             'Earlier candidate/control transfer is a starting point rather than proof of a structural impossibility.',
             'Any morphology change must be re-evaluated across the frozen required conditions.'],
      'T04':['The task is the original full 22 s two-cycle figure-eight, with frozen tool/load and actuator limits.',
             'The latest 89-point equilibrium-bank construction failed; a complete usable bank is not established.',
             'The failure record must be distinguished from physical tracking infeasibility.',
             'Current legal two-segment hardware and four channels must remain candidate-owned.',
             'Time-zero qualification and control initialization are distinct from full dynamic acceptance.',
             'Boundary trials and seed locality need inspection before repeating the same bank construction.'],
      'T07':['Four frozen conditions M1_A/M1_B/M1_C/M5 require one shared four-channel morphology.',
             'Distributed length increase was tested with native re-optimization and did not establish the desired improvement.',
             'The latest longer candidate must be distinguished from the earlier best shorter-root candidate.',
             'Control adaptation preserves the original task and is not independent physical acceptance.',
             'A local optimization failure does not prove structural infeasibility or a unique physical cause.',
             'Candidate-owned controls, unchanged channel identities, and all-condition replay are required.'],
      'T08':['The frozen passive task has two load directions and no active controller.',
             'The current 1.5 mm payout candidate was physically evaluated under the original bilateral protocol.',
             'Its recorded progressive-stiffness result does not meet the 1.5 threshold.',
             'Payout offset is a structural design parameter and must remain fixed throughout a load episode.',
             'Qualification/geometry and paired limit-removal mechanism checks are separate from displacement bounds.',
             'Earlier rejected interface attempts are not successful physical trials.'],
      'T09':['The task requires a complete press/hold/release with joint depth and force constraints.',
             'Current generated hardware contains real massive guides/supports; attachment fidelity cannot be discarded.',
             'The latest control seed is an initialization, not proof of complete contact-task acceptance.',
             'Candidate binding must retain the original task, load, collision and numerical settings.',
             'Full original independent replay has not yet been delivered for the seeded candidate at this cutoff.',
             'Reused input must be checked on the current candidate with actual actuator and collision constraints.'],
      'T10':['The original impact task has three required conditions plus two separately classified frozen controls.',
             'The current route is native state-feedback; a no-impulse execution is not an impact-recovery test.',
             'The latest binding/verification concerns the positive_y condition on the current candidate.',
             'A shared controller recipe must remain fixed across required impact conditions.',
             'Initial-state qualification and interface verification are distinct from completed physical recovery.',
             'All required conditions need complete original timing and actuator checks; controls remain separate.']}
    if stage=='T04-220':
        facts[task]=['The original full 22 s two-cycle figure-eight, tool/load and actuator thresholds remain frozen.',
                     'The current 89-point native bank was successfully constructed after an earlier failed global/boundary seed.',
                     'Static reference-bank error is not an executed full dynamic tracking result.',
                     'Control source and initial state must belong to the current legal four-channel candidate.',
                     'Independent initial-state qualification must precede any acceptance interpretation.',
                     'The next complete trajectory replay must retain dense actuator checks and original timing.']
    if stage=='T07-106':
        facts[task]=['Four frozen conditions require the identical shared four-channel morphology.',
                     'Current hardware has independently passed A/B/M5, while C has not yet passed at this cutoff.',
                     'C control search has stagnated in its existing input basin; that is not structural impossibility.',
                     'The current A input is a possible initialization source, with fresh C optimization/evaluation required.',
                     'Candidate-owned state, source and unchanged named channels must remain correctly bound.',
                     'Acceptance of other conditions cannot substitute for independent C acceptance.']
    # Each item references the complete finite checkpoint corpus; narrow IDs are retained in the index.
    refs=[records[0],past[-1],past[-2],past[0],past[-1],past[-2]]
    return [dict(checkpoint_id=stage,evidence_id=f'{stage}-K{i+1}',evidence_description=f,
        importance='required for interpretation',source_reference=records[0]['source_reference'] if i==0 else ';'.join(r['source_reference'] for r in past),
        criticality='critical' if i in [0,1,4] else 'supporting',expected_decision_relevance='interpret current evidence and choose a feasible discriminating next action') for i,f in enumerate(facts[task])]


def freeze():
    target=EXP/'context_protocol.json'
    if target.exists():raise RuntimeError('Frozen protocol exists; do not replace selected checkpoints.')
    tokenizer=WORK/'paper_experiment_data/architecture_ablation/reporter_on_off'
    sys.path.insert(0,str(tokenizer/'tokenizer_runtime'))
    os.environ['TIKTOKEN_CACHE_DIR']=str(tokenizer/'tokenizer_cache')
    import tiktoken
    enc=tiktoken.get_encoding('o200k_base')
    gates=[];key=[];frozen=[]
    for task,stage in CHOICES:
        records,meta=corpus(task,stage)
        wire=json.dumps(records,ensure_ascii=False,separators=(',',':'))
        proxy=len(enc.encode(wire,disallowed_special=()))
        capacity=len(wire.encode('utf-8'))<PROVIDER['model_capabilities']['max_request_bytes'] and proxy+8192+32768<1050000
        # Capacity is checked offline before any condition is run; no sample replacement.
        gates.append(dict(checkpoint_id=stage,task_id=task,record_count=len(records),frozen_corpus_bytes=len(wire.encode('utf-8')),
            tokenizer_proxy=proxy,tokenizer_proxy_is_actual_usage=False,capacity_admitted=capacity,
            evidence_complete_for_frozen_scope=True,scope='all non-experience scientific tool records in this trace strictly before cutoff; complete frozen task',
            reason='within declared capacity' if capacity else 'offline capacity exclusion; do not replace'))
        frozen.append(meta);key.extend(checklist(task,stage,records))
    write_json('supplementary_experiments/context_protocol.json',dict(protocol_id='E2-X6-20261116',frozen_at=stamp(),
        model=PROVIDER['model'],reasoning=PROVIDER['reasoning'],request_budget=4,output_budget=PROVIDER.get('max_tokens'),
        reporter=False,knowledge=False,skill=False,raw_access_identical=True,scope='decision-only; no science execution',
        quality_tolerance=0.2,quality_tolerance_role='descriptive only; no statistical noninferiority claim',checkpoints=frozen,gates=gates,
        corpus_storage='source record locators only; no copied Store or complete trace',system=SYSTEM))
    write_csv('architecture_metrics/context_key_evidence.csv',key)
    write_csv('architecture_metrics/context_admission.csv',gates)
    print(json.dumps(gates),flush=True)


def tools_schema():
    plan=copy.deepcopy(PLAN_TOOL)
    read=dict(type='function',function=dict(name='read_evidence',description='Read exact pre-checkpoint raw records from the shared frozen directory. Same permission in both deliveries.',
        parameters=dict(type='object',properties=dict(evidence_ids=dict(type='array',items=dict(type='string'),minItems=1,maxItems=5)),required=['evidence_ids'],additionalProperties=False)))
    return [plan,read]


def shared_json(value):
    """Lossless repeated-subtree references; verify equality without digests."""
    counts=Counter()
    def signature(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    def collect(v):
        if isinstance(v,(dict,list)):
            key=signature(v)
            if len(key)>=512:counts[key]+=1
            for child in (v.values() if isinstance(v,dict) else v):collect(child)
    collect(value);definitions={};ids={}
    def encode(v):
        if not isinstance(v,(dict,list)):return v
        key=signature(v)
        if counts[key]>1:
            if key in ids:return {'$shared':ids[key]}
            name='S'+str(len(ids)+1);ids[key]=name
            definitions[name]={k:encode(x) for k,x in v.items()} if isinstance(v,dict) else [encode(x) for x in v]
            return {'$shared':name}
        return {k:encode(x) for k,x in v.items()} if isinstance(v,dict) else [encode(x) for x in v]
    root=encode(value)
    def expand(v):
        if isinstance(v,dict):
            if set(v)=={'$shared'}:return expand(definitions[v['$shared']])
            return {k:expand(x) for k,x in v.items()}
        if isinstance(v,list):return [expand(x) for x in v]
        return v
    assert expand(root)==value
    return dict(encoding='lossless_shared_json_subtrees_v1',definitions=definitions,value=root)


def send(client,key,messages,tools=None):
    if PROVIDER['adapter']=='chatgpt_gateway':
        messages=copy.deepcopy(messages)
        if tools:
            messages[0]['content']+='\nReturn only JSON {"tool":"research_plan" or "read_evidence","arguments":{...}} matching these exact existing Core tool schemas:\n'+json.dumps(tools,separators=(',',':'))
        payload=dict(model=PROVIDER['model'],stream=False,messages=messages)
    else:
        payload=dict(**request_settings(PROVIDER),messages=messages)
        if tools:payload.update(tools=tools,tool_choice='auto')
        else:payload['response_format']={'type':'json_object'}
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw)>PROVIDER['model_capabilities']['max_request_bytes'] and (EXP/'lossless_delivery_amendment.json').exists():
        payload['messages']=copy.deepcopy(payload['messages'])
        for m in payload['messages']:
            if m['role']!='user':continue
            content=m.get('content','');prefix=''
            try:value=json.loads(content)
            except (ValueError,TypeError):
                parts=content.split('\n',1)
                if len(parts)!=2:continue
                prefix=parts[0]+'\n'
                try:value=json.loads(parts[1])
                except (ValueError,TypeError):continue
            if len(json.dumps(value))<100000:continue
            m['content']=prefix+'LOSSLESS_SHARED_JSON\n'+json.dumps(shared_json(value),ensure_ascii=False,separators=(',',':'))
        payload['messages'][0]['content']+='\nLOSSLESS_SHARED_JSON retains complete exact data: recursively replace each {"$shared":"Sx"} with definitions[Sx]. All fields and values are retained. Exact original records remain accessible through read_evidence. This is reference sharing, not a summary.'
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    assert len(raw)<=PROVIDER['model_capabilities']['max_request_bytes']
    response=client.post(PROVIDER['base_url'].rstrip('/')+'/chat/completions',content=raw,
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    if response.status_code!=200:
        # Preserve only the error body, never request headers or credentials.
        raise RuntimeError(f'Provider HTTP {response.status_code}: '+response.text[:1800])
    body=response.json()
    return body,dict(usage=body.get('usage'),response_model=body.get('model'),response_id=body.get('id'),
                     sent_at=stamp(),request_bytes=len(raw))


def main_session(client,key,task,stage,condition,resources=None,experiment='context_gateway'):
    sid=stage+'-'+condition
    rel=f'supplementary_experiments/{experiment}/sessions/{sid}.json'
    p=OUT/rel
    if p.exists():
        old=json.loads(p.read_text('utf-8'))
        if old.get('failure')=="'tools'" and not old['requests']:
            write_json(rel.replace('.json','.preparation_failure.json'),old)
        elif old.get('status')=='provider_failed' and 'unsupported_parameter' in old.get('failure','') and not old['requests']:
            write_json(rel.replace('.json','.unsupported_wire_failure.json'),old)
        elif experiment=='knowledge_skill' and stage=='T07-106' and old.get('status')=='provider_failed' and not old['requests'] and (EXP/'lossless_delivery_amendment.json').exists():
            write_json(rel.replace('.json','.capacity_failure.json'),old)
        else:return old
    records,meta=corpus(task,stage);directory=l0(records)
    question='At this frozen checkpoint, what physical uncertainty should be resolved next and what concrete feasible research decision best discriminates it?'
    messages=[dict(role='system',content=SYSTEM),dict(role='user',content='FROZEN_TASK\n'+json.dumps(records[0],ensure_ascii=False)),dict(role='user',content=question)]
    if condition=='Flat':
        messages.append(dict(role='user',content='COMPLETE_FROZEN_CORPUS\n'+json.dumps(records,ensure_ascii=False,separators=(',',':'))))
    elif experiment.startswith('context'):
        messages.append(dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+json.dumps(directory,ensure_ascii=False,separators=(',',':'))))
    else:
        # K/S supplement uses identical complete current-state history in each cell.
        messages.append(dict(role='user',content='FROZEN_CURRENT_EVIDENCE\n'+json.dumps(records,ensure_ascii=False,separators=(',',':'))))
        messages.append(dict(role='user',content='AVAILABLE_EXPERIENCE_RESOURCES\n'+json.dumps(resources or [],ensure_ascii=False)))
    result=dict(session_id=sid,task_id=task,checkpoint_id=stage,condition=condition,experiment=experiment,
        status='started',started_at=stamp(),requests=[],reads=[],errors=[],decision=None,new_scientific_actions=0,
        initial_state_reference=meta,provider_requested_model=PROVIDER['model'],reasoning='gateway_default_not_exposed' if PROVIDER['adapter']=='chatgpt_gateway' else PROVIDER['reasoning'])
    write_json(rel,result)
    print(json.dumps(dict(event='started',session_id=sid)),flush=True)
    for turn in range(1,5):
        try:
            body,account=send(client,key,messages,tools_schema())
        except Exception as exc:
            result.update(status='provider_failed',failure=str(exc));write_json(rel,result)
            print(json.dumps(dict(event='failed',session_id=sid,error=str(exc))),flush=True)
            return result
        result['requests'].append(account)
        message=body['choices'][0]['message'];messages.append(message)
        calls=message.get('tool_calls') or []
        if not calls and PROVIDER['adapter']=='chatgpt_gateway':
            content=message.get('content','').strip()
            if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
            try:
                call=json.loads(content)
                if 'action' in call:call={'tool':'research_plan','arguments':call}
                calls=[dict(id=f'text-{turn}',function=dict(name=call['tool'],arguments=json.dumps(call['arguments'])))]
            except Exception as exc:result['errors'].append(dict(error='text_call_parse: '+str(exc)[:300]))
        if not calls:
            messages.append(dict(role='user',content='Submit research_plan now. A final decision is required within the remaining request budget.'))
        for call in calls:
            name=call['function']['name']
            try:
                args=json.loads(call['function']['arguments'])
                if name=='research_plan':
                    jsonschema.Draft202012Validator(tools_schema()[0]['function']['parameters']).validate(args)
                    Plan.model_validate(args)
                    assert args.get('decision') is not None
                    result.update(status='completed',decision=args);break
                if name!='read_evidence':raise ValueError('Only read_evidence and research_plan are available.')
                chosen=[]
                for eid in args['evidence_ids']:
                    r=next(r for r in records if r['evidence_id']==eid);chosen.append(r)
                    result['reads'].append(dict(turn=turn,evidence_id=eid,level='L3',source_reference=r['source_reference']))
                value=chosen
            except Exception as exc:
                value=dict(error=type(exc).__name__+': '+str(exc)[:700]);result['errors'].append(value)
            if PROVIDER['adapter']=='chatgpt_gateway':
                messages.append(dict(role='user',content='FROZEN_TOOL_RESULT\n'+json.dumps(value,ensure_ascii=False,separators=(',',':'))))
            else:messages.append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(value,ensure_ascii=False,separators=(',',':'))))
        write_json(rel,result)
        if result['status']=='completed':break
        if turn==3:messages.append(dict(role='user',content='One request remains. Submit the final research_plan using the evidence now available.'))
    if result['status']=='started':result['status']='request_budget_exhausted'
    result['finished_at']=stamp();write_json(rel,result)
    print(json.dumps(dict(event='finished',session_id=sid,status=result['status'],requests=len(result['requests']),reads=len(result['reads']))),flush=True)
    return result


def blind(client,key,task,stage,decisions,experiment='context_gateway'):
    rel=f'supplementary_experiments/{experiment}/blind/{stage}.json'
    p=OUT/rel
    if p.exists():
        old=json.loads(p.read_text('utf-8'))
        retryfile=p.with_name(p.stem+'.failed_attempt.json')
        if old.get('status')=='failed' and 'retryable' in old.get('failure','') and not retryfile.exists():
            retryfile.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n','utf-8')
        else:return old
    if any(d.get('status') not in ['completed','request_budget_exhausted'] for d in decisions):return None
    labels=list('ABCD')[:len(decisions)];order=list(decisions)
    random.Random('blind-'+stage+experiment).shuffle(order)
    masked=[dict(label=l,decision={k:v for k,v in d['decision'].items() if k!='experience_disposition'} if isinstance(d.get('decision'),dict)
                 else dict(submission_status='no_valid_decision',reason='No schema-valid research decision was submitted under the frozen protocol.')) for l,d in zip(labels,order)]
    # Administrative hypothesis IDs can leak conditions; omit only from reviewer copy.
    for d in masked:
        if isinstance(d['decision'].get('decision'),dict):d['decision']['decision'].pop('hypothesis_id',None)
    records,_=corpus(task,stage)
    if experiment.startswith('context'):
        import csv
        checks=[r for r in csv.DictReader((OUT/'architecture_metrics/context_key_evidence.csv').open(encoding='utf-8-sig')) if r['checkpoint_id']==stage]
    else:checks=checklist(task,stage,records)
    prompt=dict(frozen_evidence=records,key_evidence_checklist=checks,anonymous_decisions=masked)
    if experiment=='knowledge_skill':
        prompt['evaluation_note']='Also score historical_experience_utilization (0–4), record identifiable knowledge/skill use and any invalid proposed actions. Quality rubric remains unchanged.'
        prompt['available_resource_reference_set']=source(B,ARCH+'knowledge_skill/snapshots/'+task+'.json')['experience_records']
    messages=[dict(role='system',content=REVIEW),dict(role='user',content=json.dumps(prompt,ensure_ascii=False,separators=(',',':')))]
    try:
        body,account=send(client,key,messages)
        content=body['choices'][0]['message']['content'].strip()
        if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
        evaluation=json.loads(content)
        result=dict(checkpoint_id=stage,status='completed',review=evaluation,usage=account,
                    private_label_key={l:d['session_id'] for l,d in zip(labels,order)},blinding=dict(hidden=['condition','usage','retrieval count','rank','future outcomes'],same_model=True),
                    anonymous_decisions=masked,raw_review_content=body['choices'][0]['message']['content'])
    except Exception as exc:result=dict(checkpoint_id=stage,status='failed',failure=str(exc))
    write_json(rel,result);print(json.dumps(dict(event='blind_review',checkpoint_id=stage,status=result['status'])),flush=True)
    return result


def run_context():
    protocol=json.loads((EXP/'context_protocol.json').read_text('utf-8'))
    key=credential(PROVIDER,CFG['credentials_reference'])
    with httpx.Client(timeout=PROVIDER['timeout_s'],proxy=PROVIDER.get('proxy_url'),trust_env=False,follow_redirects=False) as client:
        for gate in protocol['gates']:
            if not gate['capacity_admitted']:continue
            task=gate['task_id'];stage=gate['checkpoint_id']
            # Counterbalance order using a frozen deterministic alternation.
            conditions=['Flat','Hierarchical'] if CHOICES.index((task,stage))%2==0 else ['Hierarchical','Flat']
            decisions=[]
            for c in conditions:
                d=main_session(client,key,task,stage,c);decisions.append(d)
                if d['status']=='provider_failed':break
            if any(d['status']=='provider_failed' for d in decisions):break
            blind(client,key,task,stage,decisions)
    summarize_context()


def usage(result,kind):
    vals=[]
    for r in result['requests']:
        u=r.get('usage');u=u if isinstance(u,dict) else {};v=u.get(kind)
        if not isinstance(v,(int,float)):return 'UNKNOWN'
        vals.append(v)
    return sum(vals) if vals else 'UNKNOWN'


def summarize_context():
    rows=[]
    for task,stage in CHOICES:
        reviewfile=EXP/'context_gateway/blind'/f'{stage}.json'
        review=json.loads(reviewfile.read_text('utf-8')) if reviewfile.exists() else {}
        for cond in ['Flat','Hierarchical']:
            p=EXP/'context_gateway/sessions'/f'{stage}-{cond}.json'
            if not p.exists():continue
            d=json.loads(p.read_text('utf-8'));ev={}
            for label,sid in review.get('private_label_key',{}).items():
                if sid==d['session_id']:ev=next((x for x in review['review'].get('evaluations',[]) if x['label']==label),{})
            scores=ev.get('scores',{})
            valid=[v for k,v in scores.items() if k in ['physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','evidence_reference_accuracy'] and isinstance(v,(int,float))]
            items=ev.get('evidence_items',[]);recall=sum(x.get('covered') is True for x in items)/6 if len(items)==6 else 'UNKNOWN'
            rows.append(dict(protocol_id='E2-X6-Gateway-20261116',checkpoint_id=stage,task_id=task,study_id=task+'-FULL',condition=cond,
                session_status=d['status'],actual_cumulative_input_tokens=usage(d,'prompt_tokens'),output_tokens=usage(d,'completion_tokens'),
                main_request_count=len(d['requests']),evidence_retrieval_count=len(d['reads']),
                blind_decision_quality=statistics.mean(valid) if len(valid)==5 else 'UNKNOWN',key_evidence_recall=recall,
                critical_evidence_omission=len(ev['critical_omissions']) if 'critical_omissions' in ev else 'UNKNOWN',
                evidence_reference_accuracy=scores.get('evidence_reference_accuracy','UNKNOWN'),unsupported_claims=len(ev['unsupported_claims']) if 'unsupported_claims' in ev else 'UNKNOWN',
                research_actionability=scores.get('research_actionability','UNKNOWN'),cost_basis='Provider actual usage summed across all returned Main requests; no tokenizer proxy',
                source_reference=p.relative_to(OUT.parent).as_posix(),blind_reference=reviewfile.relative_to(OUT.parent).as_posix()))
    write_csv('architecture_metrics/context_cross_task.csv',rows,fields=list(rows[0]) if rows else ['protocol_id','checkpoint_id','condition','session_status'])


def run_ks():
    protocol=EXP/'knowledge_skill_protocol.json'
    if not protocol.exists():
        schedule=[]
        for task,stage in KS_CHOICES:
            records,meta=corpus(task,stage)
            for c in ['K-S-','K+S-','K-S+','K+S+']:
                schedule.append(dict(task_id=task,checkpoint_id=stage,condition=c,source=meta))
        write_json('supplementary_experiments/knowledge_skill_protocol.json',dict(frozen_at=stamp(),
            protocol_id='KS16-decision-only-20261116',schedule=schedule,total_main_decisions=16,
            resource_policy='same immutable historical E1 resource bodies and roles; only permission changes',
            model=PROVIDER['model'],reasoning='gateway_default_not_exposed',reporter=False,
            metrics='original 0–4 quality/grounding/actionability/utilization; keep saturation, no rubric retuning',
            quality_rubric=REVIEW,new_physics=0,new_structure_search=0))
    key=credential(PROVIDER,CFG['credentials_reference'])
    with httpx.Client(timeout=PROVIDER['timeout_s'],trust_env=False,follow_redirects=False) as client:
        for task,stage in KS_CHOICES:
            experiences=source(B,ARCH+'knowledge_skill/snapshots/'+task+'.json')['experience_records']
            results=[]
            for c in ['K-S-','K+S-','K-S+','K+S+']:
                roles=(['knowledge'] if c[1]=='+' else [])+(['skill'] if c[3]=='+' else [])
                allowed=[x for x in experiences if x['role'] in roles]
                d=main_session(client,key,task,stage,c,resources=allowed,experiment='knowledge_skill');results.append(d)
                if d['status']=='provider_failed':break
            if len(results)==4:blind(client,key,task,stage,results,experiment='knowledge_skill')
            if any(x['status']=='provider_failed' for x in results):break
    summarize_ks()


def summarize_ks():
    rows=[]
    for task,stage in KS_CHOICES:
        reviewfile=EXP/'knowledge_skill/blind'/f'{stage}.json'
        rev=json.loads(reviewfile.read_text('utf-8')) if reviewfile.exists() else {}
        for c in ['K-S-','K+S-','K-S+','K+S+']:
            p=EXP/'knowledge_skill/sessions'/f'{stage}-{c}.json'
            if not p.exists():continue
            d=json.loads(p.read_text('utf-8'));ev={}
            for label,sid in rev.get('private_label_key',{}).items():
                if sid==d['session_id']:ev=next((e for e in rev['review'].get('evaluations',[]) if e['label']==label),{})
            sc=ev.get('scores',{})
            hist=sc.get('historical_experience_utilization',ev.get('historical_experience_utilization','UNKNOWN'))
            if isinstance(hist,dict):hist=hist.get('score','UNKNOWN')
            rows.append(dict(protocol_id='KS16-decision-only-20261116',task_id=task,checkpoint_id=stage,condition=c,
                session_status=d['status'],historical_experience_utilization=hist,decision_quality=sc.get('physical_interpretation','UNKNOWN'),
                evidence_consistency=sc.get('evidence_consistency','UNKNOWN'),research_actionability=sc.get('research_actionability','UNKNOWN'),
                actual_cumulative_input_tokens=usage(d,'prompt_tokens'),output_tokens=usage(d,'completion_tokens'),
                provider_requests=len(d['requests']),source_reference=p.relative_to(OUT.parent).as_posix(),
                blind_reference=reviewfile.relative_to(OUT.parent).as_posix(),new_physics=0))
    write_csv('architecture_metrics/knowledge_skill_supplement.csv',rows,fields=list(rows[0]) if rows else ['protocol_id','task_id','checkpoint_id','condition','session_status'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','context','knowledge-skill','summarize','summarize-ks']);a=p.parse_args()
    {'freeze':freeze,'context':run_context,'knowledge-skill':run_ks,'summarize':summarize_context,'summarize-ks':summarize_ks}[a.mode]()
