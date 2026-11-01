"""Six-request engineering contrast. No scientific dispatch or Study mutation."""
import asyncio,json,subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaError
from schemas.platform import ProjectConfig
from tools.platform_store import Store,plain,zero
from tools.research.provider import LiveBoundary,credential,record
from tools.research.state import state,update
from tools.research.core import read_tool_evidence
from tools.research.object_choices import reference_choices,reference_schema,expand_references,main_projection
from tools.research.contracts import Plan
from tools.research.research_context import research_opportunity_review
from tools.state_io import atomic_json,digest,read
from tests.research.m1_stop_review import historical_decision
from tools.research.config import ROOT


def prepare(out):
    h,wire,source=historical_decision();original=h.store.store
    schemas={}
    for e in original.events(h.run_id):
        if e['kind']!='r3_request':continue
        w=original.artifact(original.artifact(e['outputs'][0])['request'])
        for t in w.get('tools',[]):
            if t['function']['name']=='research_plan':
                actions=t['function']['parameters'].get('properties',{}).get('action',{}).get('enum',[])
                if len(actions)==1:schemas[actions[0]]=t
    new=deepcopy(wire);packet=json.loads(new['messages'][-1]['content'].split('\n',1)[1])
    query=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/research_opportunities')
    packet['research']['evidence_access']['opportunity_review']=main_projection(h,dict(query=query,
        purpose='Before voluntary STOP, inspect research coverage, comparable evidence, finite-search limits and remaining admitted opportunities. Explain considered alternatives in Plan interpretation; no direction is prescribed.'))
    new['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    frozen=dict(source=source,commit=commit,provider=state(h)['pilot']['provider'],scientific_budget_unchanged=True,
        engineering_request_ceiling=6,per_arm_ceiling=3,mathematical_workers=0,replay=0,
        comparison='Same historical task, 14 results, resource counts, original system/history, model settings and tool inventory. Only the new on-demand opportunity query and STOP explanation description differ. Outcomes are engineering decisions, not autonomous scientific results.')
    out.mkdir(parents=True,exist_ok=True)
    atomic_json(out/'frozen.json',frozen);atomic_json(out/'old-wire.json',wire);atomic_json(out/'new-wire.json',new)
    atomic_json(out/'opportunity-example.json',research_opportunity_review(h))
    return h,wire,new,schemas,frozen


async def run(out,transport=None):
    h,old,new,schemas,frozen=prepare(out)
    if (out/'provider/platform.sqlite').exists():raise ValueError('EXISTING_ENGINEERING_LEDGER_NO_RESEND')
    run_id='m1-stop-real-decision-contrast-20261102'+('-'+out.name if transport is not None else '')
    store=Store(out/'provider');host=SimpleNamespace(store=store,run_id=run_id)
    project=ProjectConfig(project_id=run_id,grant_id=run_id,authorization_source='Explicit current task section 7: bounded independently charged real Provider decisions if needed; no mathematical Worker.',
        budget=dict(model_calls=6,tool_calls=6,worker_calls=0,backend_solves=0,wall_s=None),exclusive_resources={'provider_request':1})
    store.create(project);store.create_session(dict(input=dict(run_id=run_id,policy=dict(budget=plain(project.budget))),purpose='Engineering decision contrast only; not a formal Study'))
    spec=deepcopy(state(h)['spec']);spec['budgets'].update(provider_requests=6,protected_provider_requests=0)
    update(host,spec=spec,pilot=dict(provider=frozen['provider'],live_model_requests=0))
    record(host,'provider_egress_authorization',dict(user_approval=project.authorization_source,scope=frozen))
    key=credential(frozen['provider'],state(h)['spec']['runtime']['credentials_reference'])
    boundary=LiveBoundary(host,transport,max_model_calls=6);choices=reference_choices(h,include_all=True);results=[]
    try:
        for arm,base in [('old',old),('new',new)]:
            wire=deepcopy(base)
            for turn in range(1,4):
                label=f'{arm}-{turn}';atomic_json(out/(label+'-request.json'),wire)
                response=await boundary.handle_async_request(httpx.Request('POST',frozen['provider']['base_url'].rstrip('/')+'/chat/completions',json=wire,
                    headers={'Authorization':'Bearer '+key},extensions={'timeout':dict(connect=30,read=frozen['provider']['timeout_s'],write=30,pool=30)}))
                response.raise_for_status();body=response.json();atomic_json(out/(label+'-response.json'),body)
                message=body['choices'][0]['message'];row=dict(arm=arm,turn=turn,request_id=boundary.last_request,usage=body.get('usage'),decisions=[],scientific_dispatch=False)
                results.append(row);boundary.consumed();wire['messages'].append(message);terminal=False
                for call in message.get('tool_calls',[]):
                    name=call['function']['name'];payload=json.loads(call['function']['arguments']);feedback={}
                    try:
                        schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name)
                        Draft202012Validator(schema).validate(payload)
                        if name=='evidence_read':
                            q=deepcopy(payload)
                            if isinstance(q.get('reference'),str):q['reference']=choices[q['reference']]
                            if arm=='old' and q.get('pointer','').startswith('/research_opportunities'):raise ValueError('VIEW_NOT_AVAILABLE_IN_BASELINE')
                            feedback=main_projection(h,read_tool_evidence(h,q,record_read=False))
                        elif name=='research_route':
                            action=payload.get('action')
                            if payload['tool']=='research_plan':
                                if action not in state(h)['spec']['allowed_plan_actions']:raise ValueError('ACTION_OUTSIDE_FROZEN_GRANT')
                                selected=deepcopy(schemas[action])
                                if arm=='new' and action=='stop':
                                    selected['function']['parameters']['properties']['interpretation']['description']='Review /research_opportunities before voluntary STOP. Explain considered legal alternatives, information value, grounds for declining them and uncertainty. No failed candidate or unused budget alone decides closure.'
                                wire['tools']=[t for t in wire['tools'] if t['function']['name'] not in ('research_plan','research_analysis')]+[selected]
                            feedback=dict(status='selected',scientific_execution=False,scope='Engineering tool selection only; next request loads the original selected Schema.')
                        elif name=='research_plan':
                            expanded=expand_references(payload,reference_schema(deepcopy(schema),choices,payload['action']))
                            plan=Plan.model_validate(expanded)
                            from tools.research.evidence_policy import admit_decision
                            admit_decision(h,plan)
                            if plan.action=='generate':
                                from tools.research.design import family_configuration
                                family_configuration(state(h)['spec']['configuration'],state(h)['spec']['family_space'],plan.generation,'engineering-unexecuted-proposal')
                            if plan.action=='stop':
                                if any(r not in [plain(v) for v in plan.supporting_evidence] for r in state(h)['analysis_results']):raise ValueError('STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS')
                            feedback=dict(status='typed_proposal_validated',action=plan.action,scientific_execution=False,scope='Original schema/Plan, evidence and pure generation admission only. No Worker or new scientific evidence; full execution admission remains untested.')
                            terminal=True
                        else:
                            feedback=dict(status='proposal_recorded_without_scientific_dispatch',scope='Engineering decision only; no mathematical execution admission or result is claimed.');terminal=True
                    except (ValueError,KeyError,SchemaError) as exc:feedback=dict(status='rejected',reason=str(exc)[:1000],scientific_execution=False)
                    row['decisions'].append(dict(tool=name,input=payload,feedback=feedback))
                    reservation,_=store.reserve(run_id,label+'-'+call['id'],digest(payload),'engineering-read',{**zero(),'tool_calls':1},kind='engineering_decision_feedback')
                    store.complete(reservation,dict(request_id=reservation['request_id'],execution_id=reservation['execution_id'],caller='engineering-read',
                        tool_id='engineering.decision_feedback',tool_version='1',execution_status='completed',charged={**zero(),'tool_calls':1}),feedback)
                    wire['messages'].append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(feedback)))
                atomic_json(out/'results-private.json',dict(frozen=frozen,results=results,ledger=store.remaining()))
                print(json.dumps(dict(arm=arm,turn=turn,decisions=[dict(tool=d['tool'],action=d['input'].get('action'),status=d['feedback'].get('status') if isinstance(d['feedback'],dict) else 'read_delivered') for d in row['decisions']])) ,flush=True)
                if terminal or not message.get('tool_calls'):break
    finally:await boundary.aclose()
    return dict(results=results,ledger=store.remaining())


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--live',action='store_true');a=p.parse_args()
    if a.live:asyncio.run(run(a.out))
    else:prepare(a.out);print('OFFLINE_INPUTS_PREPARED_NO_PROVIDER')
