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

from schemas.platform import ProjectConfig, SessionInput
from tools.platform_store import Store, plain
from tools.research.agent import build_harness, LiveBoundary, live_model_class, load_credential
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest, EvidenceQuery, Plan, PLAN_RESEARCH_INTENTS
from tools.research.core import read_evidence
from tools.research.state import state, update, save
from tools.research.task_constraints import describe_analysis_requirements, check_analysis_applicability, model_assessment
from tools.state_io import atomic_json, read
from tests.research.agent_math_decision_probe import provider_usage

OUT=ROOT/'runs/flash-pro-bf5-bf6'
INSTRUCTIONS=('You are the public Softrobot research decision Agent in an independent read-only comparison. '
    'Use the frozen task and visible evidence to choose the next decision, explain what it establishes and '
    'what remains unknown. You may evidence_read or submit a typed research_plan/research_analysis proposal. '
    'Every scientific proposal is intercepted: no generation, initialization, analysis, solve, replay, '
    'SELECT or STOP is executed. Schema/reference/applicability checks are distinct from full scientific '
    'admission, which is not tested. The isolated ledger has zero science allowance. '
    'At most two Provider requests are available for this case, including tool follow-up. '
    'Cite visible evidence and state budget units. Do not infer structural infeasibility or task success '
    'from finite optimization or incomplete execution. Answer in Chinese; keep scope and unknowns explicit.')


def freeze(folder=OUT):
    if (folder/'frozen.json').exists():return read(folder/'frozen.json')
    protocol=read(ROOT/'configs/research/provider_flash_pro.json')
    spec=resolve(ROOT/'configs/research/study_bf5_public.json')
    source=Store(ROOT/'runs/integration-bf5-smoke/private-store')
    s=source.session('integration-bf5-smoke')['state'];result=source.artifact(s['physical_replays'][0])
    candidate=source.artifact(result['candidate'])
    native=source.artifact(s['analysis_results'][0])
    bf5=dict(kind='read_only_projection',source_study='A independent BF5 engineering baseline',
        source_implementation=result['implementation'],acceptance=result['acceptance'],
        native_task_acceptance=native['task_acceptance'],native_cost=native['native_dynamics']['cost'],
        independent_physics_steps=source.artifact(result['raw_reference'])['physics_steps'],
        control_source=native['control_schedule_reference'],candidate=result['candidate'],
        remaining_science=0,scope='Original frozen task and this failed baseline only; no B witness supplied.')
    raw=json.loads(subprocess.check_output(['git','show','e67d9d68e:evidence/bf6_sensor_oriented_tracking/summary.json']))
    bf6={k:raw[k] for k in ('stage','status','independent_witness','native_failure','native_cost',
        'native_complete_rollouts','native_callback_attempts','independent_status','independent_acceptance')}
    bf6.update(kind='read_only_public_B_projection',source_commit='e67d9d68e',
        compiled_load=dict(mass_kg=.020,com_m=[.007,.001,-.002],external_forces=[]),
        completed_physics_steps_lower_bound=452,attempted_step_calls=453,
        failed_call_internal_progress='unknown',integration_status='not_registered_in_A',
        scope='Task not ready: no complete stable independent full-horizon execution; no current C data.')
    frozen=dict(protocol=protocol,provider=spec['runtime']['provider'],
        credentials_reference=spec['runtime']['credentials_reference'],instructions=INSTRUCTIONS,
        cases=dict(bf5_failed_baseline=dict(task=candidate['configuration']['task'],evidence=bf5,
            configuration=candidate['configuration'],candidate=result['candidate'],source=native['control_schedule_reference'],
            analysis_protocol=spec['analysis_protocol']),bf6_incomplete=dict(evidence=bf6)))
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'frozen.json',frozen)
    return frozen


def tools_for(host,case,reference,rows):
    def handle(name):
        def run(use,**kwargs):
            value=use['input'];row=dict(tool=name,scientific_execution_started=False)
            try:
                if name=='evidence_read':
                    query=EvidenceQuery.model_validate(value);row['schema_valid']=True
                    if plain(query.reference)!=reference:raise ValueError('ONLY_FROZEN_CASE_EVIDENCE_IS_READABLE')
                    if query.view not in ('full','summary','fields','range'):raise ValueError('NO_DYNAMIC_STUDY_VIEW_IN_THIS_PROBE')
                    output=read_evidence(host,query,record_read=False)
                    row.update(contract='valid',scope='frozen_read')
                elif name=='research_plan':
                    plan=Plan.model_validate(value);row['schema_valid']=True
                    if plan.decision is None or plan.decision.research_intent!=PLAN_RESEARCH_INTENTS[plan.action]:
                        raise ValueError('ACTION_DECISION_INTENT_MISMATCH')
                    if any(plain(r)!=reference for r in plan.supporting_evidence):raise ValueError('UNSCOPED_SUPPORTING_EVIDENCE')
                    row.update(contract='valid',action=plan.action,intent=plan.decision.research_intent,
                        selected_method=plan.decision.selected_method,claimed_inference=plan.decision.claimed_inference,
                        requested_budget=plan.decision.requested_budget)
                    if plan.action=='select':row['selection_eligible']=False
                    output=dict(status='proposal_intercepted',scientific_admission='not_tested_zero_allowance',**row)
                else:
                    query=AnalysisRequest.model_validate(value);row['schema_valid']=True
                    if 'configuration' not in case:raise ValueError('BF6_NOT_REGISTERED_FOR_EXECUTION')
                    if plain(query.candidate)!=case['candidate'] or plain(query.protocol)!=case['analysis_protocol']:
                        raise ValueError('FROZEN_CANDIDATE_OR_PROTOCOL_MISMATCH')
                    if query.control_optimization and plain(query.control_optimization.source)!=case['source']:
                        raise ValueError('FROZEN_CONTROL_SOURCE_REQUIRED')
                    cfg=SessionInput.model_validate(case['configuration']);requirements=describe_analysis_requirements(cfg,{})
                    fit=check_analysis_applicability(requirements,query,model_assessment(cfg,requirements,
                        query.operation,model_source=query.model_source),exact_point=dict(actual_time_s=0.)
                        if query.operating_point=='standardized_initial_pretension' else None)
                    row.update(contract='valid',operation=query.operation,applicability=fit['status'])
                    output=dict(status='proposal_intercepted',scientific_admission='not_tested_zero_allowance',**row)
                row['input']=value
                save(host,row,'probe_tool_check');rows.append({k:v for k,v in row.items() if k!='input'})
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(output))])
            except (ValueError,KeyError) as exc:
                row.update(contract='rejected',error=str(exc));save(host,row,'probe_tool_check');rows.append(row)
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(row))])
        return run
    return [PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema.model_json_schema()}),handle(name))
        for name,description,schema in [('evidence_read','Read the frozen evidence projection with production pointer/view semantics',EvidenceQuery),
            ('research_plan','Validate a production Plan proposal only; never execute',Plan),
            ('research_analysis','Validate a production analysis proposal/applicability only; never execute',AnalysisRequest)]]


async def run_case(folder,frozen,case_id,model,transport=None):
    destination=folder/(case_id+'-'+model)
    if (destination/'summary.json').exists():return read(destination/'summary.json')
    if (destination/'platform.sqlite').exists():raise ValueError('EXISTING_PROBE_REQUIRES_RECORDED_OUTCOME_RECOVERY_NO_AUTOMATIC_RESEND')
    protocol=frozen['protocol'];provider=deepcopy(frozen['provider'])
    provider.update(model=model,max_tokens=protocol['max_tokens'],thinking=protocol['thinking'],reasoning_effort=protocol['reasoning_effort'])
    host=SimpleNamespace(store=Store(destination),run_id='probe-'+folder.name+'-'+case_id+'-'+model)
    project=ProjectConfig(project_id=host.run_id,grant_id=host.run_id,authorization_source=protocol['authorization'],
        budget=dict(model_calls=protocol['requests_per_case_model'],tool_calls=0,worker_calls=0,backend_solves=0,wall_s=None),
        exclusive_resources={'provider_request':1})
    host.store.create(project)
    host.store.create_session(dict(input=dict(run_id=host.run_id,policy=dict(budget=plain(project.budget))),purpose='Provider-only comparison; no Study'))
    update(host,spec=dict(mode='engineering_numerical',research_decisions=dict(context_limits={'evidence':3})),
        pilot=dict(provider=provider,live_model_requests=0,framework_session_id=host.run_id))
    case=frozen['cases'][case_id];reference=save(host,case['evidence'],'probe_frozen_evidence');rows=[]
    packet=dict(case_id=case_id,evidence_reference=reference,task=case.get('task'),
        candidate=case.get('candidate'),control_source=case.get('source'),analysis_protocol=case.get('analysis_protocol'),
        scientific_budget=0,scope='Read the frozen evidence, then submit a typed decision or proposal and explain its scope.')
    boundary=LiveBoundary(host,transport);error=None
    try:
        agent=build_harness(host,transport=boundary,api_key='offline-fixture' if transport else os.environ['DEEPSEEK_API_KEY'],
            instructions=frozen['instructions'],model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),
            research_tools=tools_for(host,case,reference,rows),configuration_path=destination/'framework.json',
            session_directory=destination/'sdk')
        await agent.invoke_async(json.dumps(packet,ensure_ascii=False))
    except Exception as exc:error=type(exc).__name__+': '+str(exc)[:300]
    finally:await boundary.aclose()
    usage=provider_usage(host)
    assert not any(usage['provider_ledger']['used'][k] for k in ('backend_solves','worker_calls','tool_calls'))
    summary=dict(case_id=case_id,model=model,tool_checks=rows,termination=error or 'completed',
        scientific_workers=0,physics_steps=0,reporter_requests=0,formal_studies=0,
        scientific_admission='not_tested_zero_allowance',**usage)
    atomic_json(destination/'summary.json',summary)
    return summary


async def main(live=False):
    frozen=freeze()
    if not live:print(json.dumps(dict(status='frozen',request_ceiling=8,science_workers=0)));return
    load_credential(Path(frozen['credentials_reference']).expanduser())
    results=[]
    for index,case in enumerate(frozen['protocol']['cases']):
        models=frozen['protocol']['models'][::1 if index==0 else -1]
        for model in models:
            results.append(await run_case(OUT,frozen,case,model))
            atomic_json(OUT/'summary.json',dict(status='running',results=results))
    summary=dict(status='completed',results=results,science_workers=0,physics_steps=0,
        actual_requests=sum(r['actual_requests'] for r in results),
        usage={k:sum(r['usage'][k] for r in results) if all(r['usage'][k] is not None for r in results) else None
            for k in results[0]['usage']})
    atomic_json(OUT/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    asyncio.run(main(parser.parse_args().live))
