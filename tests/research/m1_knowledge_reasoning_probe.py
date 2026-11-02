"""Bounded engineering comparison over the real STOP context; zero science dispatch."""
import argparse,asyncio,json,subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaError
from schemas.platform import ProjectConfig
from tools.platform_store import Store,plain,zero
from tools.state_io import read,atomic_json,digest
from tools.research.provider import LiveBoundary,credential,record
from tools.research.state import state,update
from tools.research.contracts import ExperienceQuery,Plan
from tools.research import experience
from tools.research.core import read_tool_evidence
from tools.research.object_choices import reference_choices,reference_schema,expand_references,main_projection
from tools.research.scientific_intent import parameter_catalog
from tools.research.research_context import research_opportunity_review
from tests.research.m1_stop_review import historical_decision
from tools.research.config import ROOT

ARMS=['original_none','repair_none','repair_medium','taxonomy_no_extra','taxonomy_skill','taxonomy_experience','taxonomy_both']
IDS=dict(original_none=[],repair_none=['research-bounded-continuation','research-witness-and-cost'],repair_medium=['research-bounded-continuation','research-witness-and-cost'],
 taxonomy_no_extra=[],taxonomy_skill=['skill-continue-or-stop'],taxonomy_experience=['experience-premature-stop'],taxonomy_both=['skill-continue-or-stop','experience-premature-stop'])
TASK=('Engineering-only evaluation over this exact historical decision boundary. Do not run science or claim progress. '
 'In the original Plan interpretation, address all three diagnostics: (1) default pretension as a mechanism under an identical complete absolute-tension schedule and initial state; '
 '(2) tendon diameter as tendon elastic stiffness in the current Native ideal-tension model; (3) whether to continue, change route or STOP with the recorded allowance and unlike-condition topology results. '
 'For each, propose a physically applicable and tool-admissible discriminating experiment if one is worthwhile, with expected observation, weakening condition and next-route consequence. '
 'If no such experiment is admitted, explain the actual limitation. Give the exact next scientific tool input JSON in interpretation when possible. '
 'Knowledge is optional context, not evidence or permission. All authorized actions are proposals only in this harness. No real Worker/Replay executes. '
 'Use at most three Provider turns total; choose a typed Plan by the final turn. No fixed preferred action, topology or requirement to continue.')


class Overlay:
    """Original artifacts are read-only; all new receipts use the existing engineering Store."""
    def __init__(self,own,historical,start):self.own=own;self.historical=historical;self.start=start
    def artifact(self,ref,*a,**kw):
        try:return self.own.artifact(ref,*a,**kw)
        except (ValueError,FileNotFoundError,KeyError):return self.historical.artifact(ref,*a,**kw)
    def events(self,run_id,db=None):return [*self.historical.events(run_id),*[e for e in self.own.events(run_id,db=db) if e['sequence']>self.start]]
    def remaining(self,db=None):return self.historical.remaining()
    def __getattr__(self,name):return getattr(self.own,name)


def prepare(out,context=73):
    h,wire,source=historical_decision(context);s=state(h);schemas={}
    for e in h.store.events(h.run_id):
        if e['kind']!='r3_request':continue
        w=h.store.artifact(h.store.artifact(e['outputs'][0])['request'])
        for t in w.get('tools',[]):
            if t['function']['name']=='research_plan':
                actions=t['function']['parameters'].get('properties',{}).get('action',{}).get('enum',[])
                if len(actions)==1:schemas[actions[0]]=t
    current=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
    facts=research_opportunity_review(h)
    candidates=list(s['candidates'].values());catalog=[]
    for ref in candidates:
        c=h.store.artifact(ref)
        if c.get('generation_version'):
            catalog=[r for r in parameter_catalog(s['spec'],c) if r['parameter_id'] in ('tendon_parameters.pretension_n','tendon_parameters.diameter_m')];break
    protocol=dict(version='m1_knowledge_reasoning_engineering_v1',source=source,original_wire=digest(wire),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_model=s['pilot']['provider']['model'],arms=ARMS,context_number=context,per_arm_request_ceiling=2 if context==70 else 3,total_request_ceiling=21,
        scientific_workers=0,replay=0,remaining_science_budget=current['budget'],diagnostics=TASK.replace('three Provider','two Provider') if context==70 else TASK,
        taxonomy_control='Same none reasoning, deterministic parameter facts, original task/history/tools/candidates/remaining allowance; only optional allowed Knowledge catalogue/hints differ.',
        reasoning_control='repair_none vs repair_medium differ only reasoning_effort; original_none vs repair_none also adds timely existing Knowledge + deterministic facts.',
        limitations='One bundled three-diagnostic context per arm, sequential order/cache differences; no population or causal effect estimate. Existing history is retained; original hints cannot be unseen.')
    out.mkdir(parents=True,exist_ok=True);atomic_json(out/('protocol-context70.json' if context==70 else 'protocol.json'),protocol)
    return h,wire,schemas,facts,catalog,protocol


async def run(out,live=False,followup_context70=False):
    h,base,schemas,facts,catalog,protocol=prepare(out,70 if followup_context70 else 73);s=state(h);provider=s['pilot']['provider']
    results_path=out/('results-context70.json' if followup_context70 else 'results.json')
    key=credential(provider,s['spec']['runtime']['credentials_reference'])
    with httpx.Client(trust_env=False,timeout=45,headers={'Authorization':'Bearer '+key}) as client:
        response=client.get(provider['base_url']+'/models');response.raise_for_status()
        exact=any(r['id']==provider['model'] for r in response.json()['data'])
    if not exact:raise ValueError('EXACT_ORIGINAL_MODEL_NOT_IN_ACTUAL_CATALOG_NO_SUBSTITUTION')
    preflight=dict(exact_model_available=exact,medium_local_contract='none/medium accepted by pinned convertRequest',inference_requests=0)
    atomic_json(out/'preflight.json',preflight)
    if not live:return preflight
    if (out/'provider/platform.sqlite').exists() and not followup_context70:raise ValueError('EXISTING_ENGINEERING_LEDGER_NO_AUTOMATIC_RESEND')
    own=Store(out/'provider');run_id=h.run_id
    project=ProjectConfig(project_id='m1-knowledge-reasoning-engineering',grant_id='current-user-bounded-probe',
        authorization_source='Current user sections 5 and appended section 9: bounded independently charged real Provider diagnostics; no scientific Worker or formal Study continuation.',
        budget=dict(model_calls=21,tool_calls=84,worker_calls=0,backend_solves=0,wall_s=None),exclusive_resources={'provider_request':1})
    if followup_context70:
        if own.remaining()['used']['model_calls']!=7:raise ValueError('EXACT_SEVEN_PRIOR_CALLS_REQUIRED_FOR_ONE_BOUNDED_NEUTRAL_CONTEXT_FOLLOWUP')
        protocol.update(prior_actual_requests=7,additional_request_ceiling=14,reason='Correct the selected-STOP entry bias within the original total ceiling; not a statistical expansion or retry.')
        atomic_json(out/'protocol-context70.json',protocol)
    else:
        own.create(project);own.create_session(dict(input=dict(run_id=run_id,policy=dict(budget=plain(project.budget))),purpose='Engineering comparison only; not formal research'))
    update(SimpleNamespace(store=own,run_id=run_id),spec=deepcopy(s['spec']),pilot=dict(provider=provider,live_model_requests=0))
    engine=SimpleNamespace(store=own,run_id=run_id);record(engine,'provider_egress_authorization',protocol)
    choices=reference_choices(h,include_all=True);rows=[];original=deepcopy(s)
    boundary=LiveBoundary(engine,max_model_calls=21)
    try:
        for arm in ARMS:
            snapshot=deepcopy(original);spec=snapshot['spec'];spec['knowledge']=dict(mode='enabled',include_entry_ids=IDS[arm],allowed_kinds=['procedure','case'])
            if arm.startswith('repair'):
                spec['knowledge_manifest']=deepcopy(original['spec']['knowledge_manifest'])
            elif arm=='original_none':spec['knowledge_manifest']=deepcopy(original['spec']['knowledge_manifest'])
            else:spec['knowledge_manifest']=experience.freeze_knowledge(spec['knowledge'])
            snapshot['retrievals']=[]
            snapshot['pilot']['provider']=deepcopy(provider)
            snapshot['pilot']['provider']['reasoning']='medium' if arm=='repair_medium' else 'none'
            snapshot['pilot']['unconsumed_response']=None
            policy=spec.get('research_decisions',{}).get('role_policy',{})
            if 'main' in policy:policy['main']['reasoning']=snapshot['pilot']['provider']['reasoning']
            start=max((e['sequence'] for e in own.events(run_id)),default=0)
            with own.transaction() as db:own.update_state(db,run_id,snapshot)
            rh=SimpleNamespace(store=Overlay(own,h.store,start),run_id=run_id,reg=h.reg)
            wire=deepcopy(base);packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1]);current=packet['research']
            if arm!='original_none':
                current['parameter_effect_facts']=catalog;current['evidence_access']['opportunity_review']=main_projection(h,dict(facts=facts))
                current['knowledge']['access']=experience.retrieval_hint(rh)
                for t in wire['tools']:
                    if t['function']['name']=='experience_retrieve':t['function']['parameters']=ExperienceQuery.model_json_schema()
            if arm.startswith('taxonomy') and not IDS[arm]:current['knowledge']['access']=None
            if arm=='original_none':wire['reasoning_effort']='none'
            else:wire['reasoning_effort']='medium' if arm=='repair_medium' else 'none'
            packet['engineering_decision_diagnostics']=protocol['diagnostics']
            wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
            for turn in range(1,protocol['per_arm_request_ceiling']+1):
                label=('context70-' if followup_context70 else '')+f'{arm}-{turn}';atomic_json(out/(label+'-request.json'),wire)
                response=await boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire,
                    headers={'Authorization':'Bearer '+key},extensions={'timeout':dict(connect=30,read=provider['timeout_s'],write=30,pool=30)}))
                body=response.json();atomic_json(out/(label+'-response.json'),body)
                row=dict(arm=arm,turn=turn,http_status=response.status_code,usage=body.get('usage'),decisions=[],scientific_dispatch=False);rows.append(row)
                if response.status_code!=200:
                    row['error']=body;atomic_json(results_path,dict(protocol=protocol,results=rows,ledger=own.remaining()));raise ValueError('PROVIDER_REJECTED_NO_RETRY: '+arm)
                boundary.consumed();message=body['choices'][0]['message'];wire['messages'].append(message);terminal=False
                for call in message.get('tool_calls',[]):
                    name=call['function']['name'];payload=json.loads(call['function']['arguments'])
                    try:
                        schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name);Draft202012Validator(schema).validate(payload)
                        if name=='experience_retrieve':feedback=experience.retrieve(rh,payload)
                        elif name=='evidence_read':
                            q=deepcopy(payload)
                            if isinstance(q.get('reference'),str):q['reference']=choices[q['reference']]
                            feedback=main_projection(h,read_tool_evidence(h,q,record_read=False))
                        elif name=='research_route':
                            action=payload.get('action')
                            if payload['tool']=='research_plan':
                                if action not in original['spec']['allowed_plan_actions']:raise ValueError('OUTSIDE_ORIGINAL_FROZEN_SCIENTIFIC_AUTHORIZATION')
                                wire['tools']=[t for t in wire['tools'] if t['function']['name'] not in ('research_plan','research_analysis')]+[deepcopy(schemas[action])]
                            feedback=dict(status='selected_for_proposal_only',scientific_execution=False)
                        elif name=='research_plan':
                            p=Plan.model_validate(expand_references(payload,reference_schema(deepcopy(schema),choices,payload['action'])))
                            from tools.research.evidence_policy import admit_decision
                            admit_decision(h,p)
                            if p.action=='generate':
                                from tools.research.design import family_configuration
                                family_configuration(original['spec']['configuration'],original['spec']['family_space'],p.generation,'engineering-unexecuted-proposal')
                            bindings=experience.disposition_bindings(rh,p.experience_disposition)
                            feedback=dict(status='original_plan_and_evidence_admission_passed',knowledge_bindings=bindings,
                                scientific_execution=False,scope='Plan/generation admission only. A prose next experiment is not an executed or fully admitted AnalysisRequest.')
                            terminal=True
                        elif name=='research_analysis':
                            from tools.research.scientific_intent import compile_question
                            expanded=expand_references(payload,reference_schema(deepcopy(schema),choices,None))
                            feedback=compile_question(rh,expanded,tool_use_id=label+'-'+call['id'])
                            feedback['scientific_execution']=False
                            terminal=True
                        else:feedback=dict(status='unexecuted_proposal',scientific_execution=False);terminal=True
                    except (ValueError,KeyError,StopIteration,SchemaError) as exc:feedback=dict(status='rejected',reason=str(exc)[:1400],scientific_execution=False)
                    row['decisions'].append(dict(tool=name,input=payload,feedback=feedback))
                    reservation,_=own.reserve(run_id,label+'-'+call['id'],digest(payload),'engineering-decision',{**zero(),'tool_calls':1},kind='engineering_decision_feedback')
                    own.complete(reservation,dict(request_id=reservation['request_id'],execution_id=reservation['execution_id'],caller='engineering-decision',
                        tool_id='engineering.decision_feedback',tool_version='1',execution_status='completed',charged={**zero(),'tool_calls':1}),feedback)
                    wire['messages'].append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(feedback)))
                atomic_json(results_path,dict(protocol=protocol,results=rows,ledger=own.remaining()))
                print(json.dumps(dict(arm=arm,turn=turn,http_status=response.status_code,tools=[r['tool'] for r in row['decisions']])),flush=True)
                if terminal or not message.get('tool_calls'):break
    finally:await boundary.aclose()
    return dict(results=rows,ledger=own.remaining())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--live',action='store_true');p.add_argument('--followup-context70',action='store_true');p.add_argument('--history-root',type=Path,required=True);a=p.parse_args()
    import tests.research.m1_stop_review as history
    history.ROOT=a.history_root
    asyncio.run(run(a.out,a.live,a.followup_context70))
