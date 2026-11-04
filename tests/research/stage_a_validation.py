"""One bounded Stage A engineering verification, using production SDK/Workers.

Scripted Mock HTTP decisions are not autonomous Main reasoning. The journal
prevents silently repeating numerical work after an interrupted validation.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator
from tools.research import agent,core
from tools.research.state import state
from tools.research.object_choices import main_projection
from tools.state_io import atomic_json
from tests.research.test_passive_program_v2 import prepared_host_v2
from tests.research.test_stage_a_handoff import dynamic_question
from tests.research.test_p63g3_action_handoff import diagnosis
from tests.research.test_information_flow import packet,generation

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT.parents[1]/'outputs'
JOURNAL=OUT/'stage-a-numerical.json'


def mock_converse(host, replies, name):
    """Real Strands assembly and Reporter HTTP, with prewritten Main decisions."""
    wires=[];index=0
    def respond(request):
        nonlocal index
        wire=json.loads(request.content)
        reporter='read-only scientific Reporter' in wire['messages'][0]['content']
        wires.append(dict(role='reporter' if reporter else 'main',wire=wire,bytes=len(request.content)))
        if reporter:
            payload=json.loads(wire['messages'][-1]['content']);sources=list(payload['source_catalog'])
            message=dict(role='assistant',content=json.dumps(dict(interpretations=[dict(kind='new_information',
                text='Recorded mechanism observations are local numerical evidence. Independent task acceptance remains separate.',
                source_ids=sources[:1])])))
            finish='stop'
        else:
            if index>=len(replies):raise AssertionError('Unexpected additional Main request')
            use=replies[index];index+=1
            message=dict(role='assistant',content='Scripted offline Main consumed the saved feedback.');finish='stop'
            if use:
                tool,payload=use;payload=deepcopy(payload)
                schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==tool)
                if schema.get('$defs',{}).get('EvidenceRef',{}).get('type')=='string':
                    payload=main_projection(host,payload)
                    if tool=='research_plan':
                        if 'supporting_evidence' not in schema.get('properties',{}):payload.pop('supporting_evidence',None)
                        fields=schema.get('$defs',{}).get('ResearchDecision',{}).get('properties',{})
                        for key in ('selected_candidate','selected_method','requested_budget','research_intent','selected_variables'):
                            if key not in fields:payload.get('decision',{}).pop(key,None)
                Draft202012Validator(schema).validate(payload)
                message.update(content=None,tool_calls=[dict(id=name+'-'+str(index),type='function',
                    function=dict(name=tool,arguments=json.dumps(payload)))])
                finish='tool_calls'
        atomic_json(OUT/(name+'-wire.json'),dict(scope='Real SDK / Mock HTTP only; scripted decisions',requests=wires))
        return httpx.Response(200,json=dict(id='stage-a-'+uuid4().hex,object='chat.completion',created=1,
            model=wire['model'],choices=[dict(index=0,finish_reason=finish,message=message)],
            usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14)))
    with patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
            patch('tools.research.tool_readiness.execution_environment',return_value=dict(status='ready',scope='Bounded SDK Mock engineering validation')),\
            patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
            patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
        asyncio.run(agent.converse(host,pause_after_completed_invocations=1))
    assert index==len(replies),(index,len(replies))
    return wires


def run():
    OUT.mkdir(exist_ok=True)
    if JOURNAL.exists():raise RuntimeError('Preserve existing evidence; do not repeat numerical verification.')
    h,c=prepared_host_v2(mathematical_budget=7,physical_budget=8,mock_provider_budget=60)
    journal=dict(scope='Engineering v2 only; no live Provider or formal benchmark',study=h.run_id,store=str(h.store.root),
        initial_candidate=c,upper_bound=dict(mathematical_evaluations=7,mathematical_physics_steps=3500,
            optional_independent_replay_steps=500,total_integration_steps=4000),phases=[])
    def record(name,**facts):
        journal['phases'].append(dict(name=name,**facts));journal['ledger']=h.store.remaining()
        atomic_json(JOURNAL,journal)
    record('frozen_before_execution',task=h.store.artifact(c)['configuration']['task'])
    mock_converse(h,[('research_route',dict(tool='research_plan',action='diagnose')),
        ('research_plan',diagnosis(c,'mechanism_research')),('research_analysis',dynamic_question()),None],'stage-a-initial')
    first=state(h)['analysis_results'][-1];initial=h.store.artifact(first)
    record('initial_real_worker',result=first,status=initial['status'],observation=initial['structure_research']['baseline'],
        cost=initial['structure_research']['cost'],boundary=initial['boundary'])
    assert initial['status']=='computed',initial
    mock_converse(h,[('research_analysis',dynamic_question('differentiate',5)),None],'stage-a-difference')
    ref=state(h)['analysis_results'][-1];raw=h.store.artifact(ref);research=raw['structure_research']
    record('real_two_scale_differences',result=ref,status=raw['status'],cost=research['cost'],
        sensitivities=research.get('parameter_sensitivities'),direction=research.get('structure_direction'),
        probes=[dict(index=r['record_index'],model=r['physics_identity'],parameters=r['parameter_values'],
            value=r['observation']['value'],qualification=r['observation'].get('qualification_diagnosis')) for r in research['records']])
    direction=research.get('structure_direction')
    if not direction:
        record('no_trustworthy_direction',reason='Retain all failures; no automatic parameter or task-threshold repair.')
        return
    plan=generation(h);plan.update(generation=dict(changes={p['parameter_path']:p['suggested_value'] for p in direction['parameter_changes']}),supporting_evidence=[ref],
        hypothesis='Scripted Main adopts one recorded Young modulus probe; task success is unmeasured.')
    plan['decision']['selected_candidate']=c
    mock_converse(h,[('evidence_read',dict(reference=ref,pointer='/structure_research/structure_direction/generation_handoff/generation')),
        ('research_route',dict(tool='research_plan',action='generate')),('research_plan',plan),None],'stage-a-adopt')
    new=next(r for r in reversed(list(state(h)['candidates'].values())) if r!=c)
    record('original_generate',candidate=new,provenance=h.store.artifact(new)['provenance'],
        original_parameters=h.store.artifact(c)['parameters'],new_parameters=h.store.artifact(new)['parameters'])
    mock_converse(h,[('research_route',dict(tool='research_plan',action='diagnose')),
        ('research_plan',diagnosis(new,'mechanism_research')),('research_analysis',dynamic_question()),None],'stage-a-recompute')
    after_ref=state(h)['analysis_results'][-1];after=h.store.artifact(after_ref)
    record('new_model_real_recomputation',result=after_ref,status=after['status'],
        observation=after['structure_research']['baseline'],cost=after['structure_research']['cost'],
        changed_model=initial['model_identity']!=after['model_identity'])
    assert after['status']=='computed',after
    # Independent replay is a separate Worker/evaluator and a separate charge.
    finish(h,journal,record,initial,after,new)


def finish(h,journal,record,initial,after,new):
    from tools.research.physical_replay import dispatch
    from tools.research.contracts import PhysicalReplayRequest
    with patch('tools.research.physical_replay.guard'):
        replay=dispatch(h,PhysicalReplayRequest(candidate=new),'stage-a-independent-replay')
    replay_raw=h.store.artifact(replay['reference']) if replay.get('reference') else replay
    record('independent_replay',result=replay,acceptance=replay_raw.get('acceptance'),
        actual_cost=replay_raw.get('actual_resource_consumption'))
    math_steps=sum(h.store.artifact(r)['structure_research']['cost']['physics_steps'] for r in state(h)['analysis_results'])
    record('completed',actual_mathematical_evaluations=state(h)['mathematical_evaluations'],
        actual_mathematical_steps=math_steps,independent_replay_is_distinct=True,
        initial_value=initial['structure_research']['baseline']['value'],new_value=after['structure_research']['baseline']['value'],
        no_autonomous_reasoning_claim=True)
    assert state(h)['mathematical_evaluations']==7 and math_steps==3500


if __name__=='__main__':run()
