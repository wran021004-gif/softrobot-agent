"""Use the same six-request ledger to check each model's own proposed mathematics."""
import asyncio,json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator
from tools.platform_store import Store
from tools.platform_store import plain
from tools.research.provider import LiveBoundary,credential,record,provider_schema
from tools.research.state import state
from tools.research.object_choices import reference_choices,reference_schema,expand_references,main_projection,main_tool_schema
from tools.research.task_constraints import mathematical_method_view
from tools.research.scientific_intent import question_schema,compile_question,control_method_choices
from tools.research.core import read_tool_evidence
from tools.state_io import read,atomic_json
from tests.research.m1_stop_review import historical_decision


async def followup(out):
    data=read(out/'results-private.json');h,_,_=historical_decision()
    engine=SimpleNamespace(store=Store(out/'provider'),run_id='m1-stop-real-decision-contrast-20261102')
    if engine.store.remaining()['used']['model_calls']!=2:raise ValueError('EXACT_TWO_REQUEST_PROBE_CONTINUATION_ONLY')
    choices=reference_choices(h,include_all=True);provider=state(h)['pilot']['provider']
    boundary=LiveBoundary(engine,max_model_calls=6);key=credential(provider,state(h)['spec']['runtime']['credentials_reference'])
    try:
        for arm in ('old','new'):
            row=next(r for r in data['results'] if r['arm']==arm)
            decision=row['decisions'][0];payload=decision['input']
            if payload.get('action')!='diagnose' or decision['feedback']['status']!='typed_proposal_validated':raise ValueError('VALIDATED_MODEL_DIAGNOSE_REQUIRED')
            wire=read(out/(arm+'-1-request.json'));schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='research_plan')
            full=expand_references(payload,reference_schema(deepcopy(schema),choices,'diagnose'))
            candidate=full['decision']['selected_candidate'];ref=record(engine,'engineering_unexecuted_diagnose',full)
            intent=dict(action='diagnose',execution_status='completed',candidate=candidate,plan_reference=ref,
                agent_hypothesis=full)
            selected=question_schema(state(h)['spec'],h.store.artifact(candidate),full.get('next_research_action'),
                control_methods=control_method_choices(mathematical_method_view(h,candidate)))
            selected=main_tool_schema(provider_schema(selected),choices)
            wire['tools']=[t for t in wire['tools'] if t['function']['name']!='research_analysis']+[
                dict(type='function',function=dict(name='research_analysis',description='Propose scientific inputs for your engineering-bound diagnose. Original request compilation is checked; no mathematical Worker or scientific experiment executes in this contrast.',parameters=selected))]
            body=read(out/(arm+'-1-response.json'));message=body['choices'][0]['message']
            wire['messages']+=[message,dict(role='tool',tool_call_id=message['tool_calls'][0]['id'],content=json.dumps(dict(status='engineering_binding_only',
                candidate=payload['decision']['selected_candidate'],hypothesis=payload['hypothesis'],next_research_action=payload.get('next_research_action'),
                scope='Your own proposed diagnose is bound only for this non-executing engineering check. Submit scientific choices through the loaded research_analysis Schema. All old scientific results and original remaining Study budgets are unchanged; no new scientific evidence exists.')))]
            for turn in (2,3):
                label=f'{arm}-{turn}';atomic_json(out/(label+'-request.json'),wire)
                response=await boundary.handle_async_request(httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',json=wire,
                    headers={'Authorization':'Bearer '+key},extensions={'timeout':dict(connect=30,read=provider['timeout_s'],write=30,pool=30)}))
                response.raise_for_status();body=response.json();atomic_json(out/(label+'-response.json'),body);boundary.consumed()
                message=body['choices'][0]['message'];row=dict(arm=arm,turn=turn,request_id=boundary.last_request,usage=body.get('usage'),decisions=[],scientific_dispatch=False)
                data['results'].append(row);wire['messages'].append(message);ready=False
                for call in message.get('tool_calls',[]):
                    name=call['function']['name'];payload=json.loads(call['function']['arguments'])
                    try:
                        schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name)
                        Draft202012Validator(schema).validate(payload)
                        if name=='research_analysis':
                            # Bind only the model's own Plan. Redirect audit writes to
                            # the existing engineering ledger; keep all original
                            # candidate, method, source, Pydantic and budget checks.
                            with patch('tools.research.research_context.research_intent',return_value=dict(latest_decision=intent)),patch('tools.research.agent.record',side_effect=lambda _,kind,value:record(engine,kind,value)),patch('tools.research.state.save',side_effect=lambda _,value,kind:record(engine,kind,value)),patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')),patch('mujoco.mj_step',side_effect=AssertionError('NO_INTEGRATION')):
                                result=compile_question(h,payload,tool_use_id=call['id'])
                            feedback=main_projection(h,{k:v for k,v in result.items() if k!='request'})
                            if result.get('request'):record(engine,'engineering_compiled_request_no_dispatch',result['request'])
                            ready=result.get('status')=='ready'
                        elif name=='evidence_read':
                            q=deepcopy(payload)
                            if isinstance(q['reference'],str):q['reference']=choices[q['reference']]
                            feedback=main_projection(h,read_tool_evidence(h,q,record_read=False))
                        else:feedback=dict(status='proposal_not_dispatched',scientific_execution=False)
                    except Exception as exc:
                        feedback=dict(status='rejected',exception=type(exc).__name__,reason=str(exc)[:1000],scientific_execution=False)
                    row['decisions'].append(dict(tool=name,input=payload,feedback=feedback))
                    wire['messages'].append(dict(role='tool',tool_call_id=call['id'],content=json.dumps(feedback)))
                data['ledger']=engine.store.remaining();atomic_json(out/'results-private.json',data)
                print(json.dumps(dict(arm=arm,turn=turn,outcomes=[d['feedback'].get('status') if isinstance(d['feedback'],dict) else 'read' for d in row['decisions']])),flush=True)
                if ready or not message.get('tool_calls'):break
    finally:await boundary.aclose()


if __name__=='__main__':
    import sys
    asyncio.run(followup(Path(sys.argv[1])))
