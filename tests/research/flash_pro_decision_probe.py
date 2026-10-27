"""Bounded Provider-only probe using the production Harness, schemas and ledger.

No scientific dispatcher is invoked. Only explicit frozen evidence reads and
request validation are tool handlers. Raw SDK/Provider material stays in runs.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import httpx
from strands.tools import PythonAgentTool
from strands.tools.executors import SequentialToolExecutor

from schemas.platform import ProjectConfig
from tools.platform_store import Store, plain
from tools.research.agent import build_harness, LiveBoundary, live_model_class, load_credential, error_feedback
from tools.research.config import ROOT, resolve, _reference
from tools.research.contracts import EvidenceQuery, Plan, PLAN_RESEARCH_INTENTS
from tools.research.core import read_evidence
from tools.research.state import state, update, save
from tools.state_io import atomic_json, read
from tests.research.agent_math_decision_probe import provider_usage, decision_schema

OUT=ROOT/'runs/flash-pro-public-v2'
ROUTE_OUT=ROOT/'runs/flash-pro-routes-v4'
INSTRUCTIONS=('You are the public Softrobot research decision Agent in an independent read-only comparison. '
    'Use the frozen task and visible evidence to choose the next decision, explain what it establishes and '
    'what remains unknown. Submit one typed diagnose/stop research_plan decision, then finish with a short assessment. '
    'The exact public scalar evidence is already inline with its reference. Optional evidence_read is for '
    'a named missing fact, not a prerequisite to deciding from the supplied value. '
    'Every scientific proposal is intercepted: no generation, initialization, analysis, solve, replay, '
    'SELECT or STOP is executed. Schema/reference/intent checks are distinct from full scientific '
    'admission, which is not tested. The isolated ledger has zero science allowance. '
    'Tool arguments are the Plan object itself, without an outer plan property. '
    'At most {requests} Provider requests are available for this case, including correction and tool follow-up. '
    'Cite visible evidence and state budget units. Do not infer structural infeasibility or task success '
    'from finite optimization or incomplete execution. Answer in Chinese; keep scope and unknowns explicit.')


def freeze(folder=OUT):
    if (folder/'frozen.json').exists():return read(folder/'frozen.json')
    protocol=read(ROOT/'configs/research/provider_flash_pro.json')
    spec=resolve(ROOT/'configs/research/study_bf5_public.json')
    public=read(ROOT/'evidence/integration_research_next/bf5_engineering.json')
    bf5=dict(kind='committed_public_summary',source='evidence/integration_research_next/bf5_engineering.json',
        source_implementation=public['implementation'],acceptance_status=public['acceptance_status'],
        selected=public['selected'],native_task_acceptance='unmeasured',native_cost=public['native'],
        independent_cost=public['independent_replay'],physics_steps=public['physics_steps'],
        scope='Public failed baseline only; no candidate/control/Store identity or original receipt is supplied.')
    raw=json.loads(subprocess.check_output(['git','show','e67d9d68e:evidence/bf6_sensor_oriented_tracking/summary.json']))
    bf6={k:raw[k] for k in ('stage','status','independent_witness','native_cost',
        'native_complete_rollouts','native_callback_attempts','independent_status')}
    bf6.update(kind='committed_public_B_summary',source_commit='e67d9d68e',
        acceptance=raw['independent_acceptance']['accepted'],task_success=None,
        compiled_load=dict(mass_kg=.020,com_m=[.007,.001,-.002],external_forces=[]),
        completed_physics_steps_lower_bound=452,attempted_step_calls=453,
        failed_call_internal_progress='unknown',integration_status='not_registered_in_A',
        scope='Public incomplete-result facts only; no candidate/control/Store identity or C data.')
    frozen=dict(protocol=protocol,provider=spec['runtime']['provider'],
        credentials_reference=spec['runtime']['credentials_reference'],instructions=INSTRUCTIONS.format(requests=protocol['requests_per_case_model']),
        cases=dict(bf5_failed_baseline=dict(task=read(ROOT/'tasks/bf5_position_tool_axis_v1.json')['task'],evidence=bf5),
            bf6_incomplete=dict(evidence=bf6)))
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'frozen.json',frozen)
    return frozen


def freeze_routes(folder=ROUTE_OUT):
    """New independent cohort; previous frozen inputs and receipts stay sealed."""
    if (folder/'frozen.json').exists():return read(folder/'frozen.json')
    public=freeze();protocol=read(ROOT/'configs/research/provider_flash_pro_routes.json')
    evidence=read(ROOT/'tests/research/fixtures/research_route_public.json')
    source=evidence['c_task_source']
    ctask=_reference(ROOT/source['file'],'task',dict(references={}))['task']
    ctask['initializer']['parameters']['data']=dict(rule=source['candidate_initialization'])
    if ctask['timing']['duration_s']!=evidence['math_without_physics']['native_prediction']['horizon_s']:
        raise ValueError('FROZEN_EVIDENCE_TASK_HORIZON_MISMATCH')
    prior=ROOT/protocol['prior_invalid_cohort']
    prior_requests=read(prior)['actual_requests'] if prior.exists() else 0
    if prior_requests+len(protocol['cases'])*len(protocol['models'])*protocol['requests_per_case_model']>protocol['total_request_ceiling_including_invalid_cohort']:
        raise ValueError('CUMULATIVE_PROVIDER_PROBE_REQUEST_CEILING')
    cases={k:dict(task=ctask,evidence=evidence[k]) for k in ('fixed_control_stagnation','math_without_physics')}
    cases['bf5_failure_bf6_incomplete']=dict(evidence=dict(
        bf5=public['cases']['bf5_failed_baseline']['evidence'],bf6=public['cases']['bf6_incomplete']['evidence'],
        question='Compare BF5 valid independent failure with BF6 incomplete execution; explain acceptance, costs, missing facts and a justified next route.'))
    instructions=INSTRUCTIONS.format(requests=protocol['requests_per_case_model'])+(
        ' Diagnose may describe structure/control/joint optimization, physical validation or Reporter investigation; '
        'it does not execute those methods. Compare alternatives in interpretation using the existing hypothesis fields. '
        'A STOP must distinguish budget exhaustion, engineering blockage, local stagnation and proved conclusions. '
        'Historical allowance is context only; this comparison cannot spend it. '
        'Do not recount inline facts through repeated reads. Final assessment should be concise. '
        'Actual Provider requests and Token cost come only from receipts, including the request producing your final answer.')
    frozen=dict(protocol=protocol,provider=public['provider'],credentials_reference=public['credentials_reference'],
        instructions=instructions,cases=cases,prior_actual_requests=prior_requests)
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'frozen.json',frozen)
    return frozen


def tools_for(host,case,reference,rows,*,experience_enabled=False):
    def handle(name):
        def run(use,**kwargs):
            value=use['input'];before=deepcopy(state(host))
            row=dict(tool=name,input=value,scientific_execution_started=False,
                provider_request_number=host.store.remaining()['used']['model_calls'])
            try:
                if name=='experience_retrieve':
                    from tools.research.experience import retrieve
                    output=retrieve(host,value)
                    row.update(contract='valid',operation=value.get('operation','search'),
                        exact_keys=[r['exact_key'] for r in output['results']])
                elif name=='evidence_read':
                    query=EvidenceQuery.model_validate(value);row['schema_valid']=True
                    if plain(query.reference)!=reference:raise ValueError('ONLY_FROZEN_CASE_EVIDENCE_IS_READABLE')
                    if query.view not in ('full','summary','fields','range'):raise ValueError('NO_DYNAMIC_STUDY_VIEW_IN_THIS_PROBE')
                    output=read_evidence(host,query,record_read=False)
                    row.update(contract='valid',scope='frozen_read')
                elif name=='research_plan':
                    plan=Plan.model_validate(value);row['schema_valid']=True
                    from tools.research.experience import disposition_bindings
                    disposition_bindings(host,plan.experience_disposition)
                    if plan.action not in ('diagnose','stop'):raise ValueError('OUTSIDE_READ_ONLY_DECISION_SCOPE')
                    if plan.decision is None or plan.decision.research_intent!=PLAN_RESEARCH_INTENTS[plan.action]:
                        raise ValueError('ACTION_DECISION_INTENT_MISMATCH')
                    if any(plain(r)!=reference for r in plan.supporting_evidence):raise ValueError('UNSCOPED_SUPPORTING_EVIDENCE')
                    row.update(contract='valid',action=plan.action,intent=plan.decision.research_intent,
                        selected_method=plan.decision.selected_method,claimed_inference=plan.decision.claimed_inference,
                        requested_budget=plan.decision.requested_budget)
                    output=dict(status='proposal_intercepted',scientific_admission='not_tested_zero_allowance',
                        next='Decision recorded; finish with a short assessment. No scientific action was executed.',
                        **{k:v for k,v in row.items() if k!='input'})
                save(host,row,'probe_tool_check');rows.append({k:v for k,v in row.items() if k!='input'})
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(output))])
            except (ValueError,KeyError) as exc:
                feedback=error_feedback(host,use,exc,before)
                row.update(contract='rejected',error_code=feedback['error_code'],reason=feedback['reason'])
                save(host,row,'probe_tool_check');rows.append({k:v for k,v in row.items() if k!='input'})
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(feedback))])
        return run
    evidence_schema=EvidenceQuery.model_json_schema()
    evidence_schema['properties']['view']['enum']=['full','summary','fields','range']
    tools=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema}),handle(name))
        for name,description,schema in [('evidence_read','Read the committed public summary with production pointer/view semantics',evidence_schema),
            ('research_plan','Validate the descriptive production Plan directly, without an outer plan property; never execute',decision_schema())]]
    if experience_enabled:
        from tools.research.contracts import ExperienceQuery
        tools.append(PythonAgentTool('experience_retrieve',dict(name='experience_retrieve',
            description='Read-only curated diagnostic search, then exact read; historical guidance is not current scientific evidence.',
            inputSchema={'json':ExperienceQuery.model_json_schema()}),handle('experience_retrieve')))
    return tools



async def run_case(folder,frozen,case_id,model,transport=None,*,recover_unsent=False,experience_enabled=False):
    destination=folder/(case_id+'-'+model)
    previous=read(destination/'summary.json') if (destination/'summary.json').exists() else None
    if previous and (not recover_unsent or previous['actual_requests']):return previous
    existing=(destination/'platform.sqlite').exists()
    if existing and not (recover_unsent and previous and previous['actual_requests']==0):
        raise ValueError('EXISTING_PROBE_REQUIRES_RECORDED_OUTCOME_RECOVERY_NO_AUTOMATIC_RESEND')
    protocol=frozen['protocol'];provider=deepcopy(frozen['provider'])
    provider.update(model=model,max_tokens=protocol['max_tokens'],thinking=protocol['thinking'],reasoning_effort=protocol['reasoning_effort'])
    host=SimpleNamespace(store=Store(destination),run_id='probe-'+folder.name+'-'+case_id+'-'+model)
    short_session=case_id[:3]+('-p' if model.endswith('pro') else '-f')
    project=ProjectConfig(project_id=host.run_id,grant_id=host.run_id,authorization_source=protocol['authorization'],
        budget=dict(model_calls=protocol['requests_per_case_model'],tool_calls=0,worker_calls=0,backend_solves=0,wall_s=None),
        exclusive_resources={'provider_request':1})
    if not existing:
        host.store.create(project)
        host.store.create_session(dict(input=dict(run_id=host.run_id,policy=dict(budget=plain(project.budget))),purpose='Provider-only comparison; no Study'))
        update(host,spec=dict(mode='engineering_numerical',research_decisions=dict(context_limits={'evidence':3})),
            pilot=dict(provider=provider,live_model_requests=0,framework_session_id=short_session))
        update(host,retrievals=[])
    else:
        current=state(host)
        if host.store.remaining()['used']['model_calls'] or current['pilot'].get('unconsumed_response'):
            raise ValueError('UNSENT_RECOVERY_REQUIRES_ZERO_ACTUAL_REQUESTS')
        save(host,previous,'probe_pre_send_storage_failure_retained')
        update(host,pilot={**current['pilot'],'framework_session_id':short_session})
    case=frozen['cases'][case_id];reference=save(host,case['evidence'],'probe_frozen_evidence');rows=[]
    packet=dict(case_id=case_id,evidence_reference=reference,evidence=case['evidence'],task=case.get('task'),
        evidence_delivery='Exact public scalar projection; no scientific registration, complete-result read credit or inherited acceptance.',
        scientific_budget=0,scope='Read the frozen evidence, then submit a typed decision or proposal and explain its scope.')
    if experience_enabled:
        from tools.research.experience import retrieval_hint
        update(host,spec={**state(host)['spec'],'capabilities':['analysis'],'canonical_task':dict(family='task.oriented_tracking')})
        packet['experience_guidance']=retrieval_hint(host)
    boundary=LiveBoundary(host,transport);error=None;final_text=''
    try:
        agent=build_harness(host,transport=boundary,api_key='offline-fixture' if transport else os.environ['DEEPSEEK_API_KEY'],
            instructions=frozen['instructions'],model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),
            research_tools=tools_for(host,case,reference,rows,experience_enabled=experience_enabled),configuration_path=destination/'framework.json',
            session_directory=folder/'sdk'/short_session,session_id=short_session)
        await agent.invoke_async(json.dumps(packet,ensure_ascii=False))
        final_text=''.join(b.get('text','') for b in agent.messages[-1]['content'])
        save(host,dict(text=final_text),'probe_final_answer')
    except Exception as exc:error=type(exc).__name__+': '+str(exc)[:300]
    finally:await boundary.aclose()
    usage=provider_usage(host)
    assert not any(usage['provider_ledger']['used'][k] for k in ('backend_solves','worker_calls','tool_calls'))
    rejections=[host.store.artifact(e['outputs'][0])['reason'] for e in host.store.events(host.run_id)
        if e['kind']=='r3_send_rejected']
    termination='request_limit_reached' if error and rejections and rejections[-1]=='PROVIDER_COUNT_EXHAUSTED' else error or 'completed'
    summary=dict(case_id=case_id,model=model,tool_checks=rows,termination=termination,harness_error=error,
        accepted_decisions=sum(r['tool']=='research_plan' and r['contract']=='valid' for r in rows),
        first_valid_decision_request=next((r['provider_request_number'] for r in rows if r['tool']=='research_plan' and r['contract']=='valid'),None),
        final_answer_present=bool(final_text),
        scientific_workers=0,physics_steps=0,reporter_requests=0,formal_studies=0,
        scientific_admission='not_tested_zero_allowance',**usage)
    atomic_json(destination/'summary.json',summary)
    return summary


async def main(live=False,recover_unsent=False,routes=False):
    folder=ROUTE_OUT if routes else OUT
    frozen=freeze_routes(folder) if routes else freeze(folder)
    if not live:print(json.dumps(dict(status='frozen',request_ceiling=len(frozen['cases'])*len(frozen['protocol']['models'])*frozen['protocol']['requests_per_case_model'],science_workers=0)));return
    load_credential(Path(frozen['credentials_reference']).expanduser())
    results=[]
    for index,case in enumerate(frozen['protocol']['cases']):
        models=frozen['protocol']['models'][::1 if index%2==0 else -1]
        for model in models:
            results.append(await run_case(folder,frozen,case,model,recover_unsent=recover_unsent))
            atomic_json(folder/'summary.json',dict(status='running',results=results))
    summary=dict(status='completed',results=results,science_workers=0,physics_steps=0,
        actual_requests=sum(r['actual_requests'] for r in results),
        usage={k:sum(r['usage'][k] for r in results) if all(r['usage'][k] is not None for r in results) else None
            for k in results[0]['usage']})
    atomic_json(folder/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    parser.add_argument('--recover-unsent',action='store_true')
    parser.add_argument('--routes',action='store_true',help='Independent three-case P2 route comparison, 24 requests maximum')
    args=parser.parse_args();asyncio.run(main(args.live,args.recover_unsent,args.routes))
