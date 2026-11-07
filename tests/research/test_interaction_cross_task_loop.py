"""Scripted SDK/Mock HTTP + synthetic mathematics. This does NOT test autonomy.

Both tasks retain their actual frozen definitions. No real Provider, numerical
worker, integration or Replay is authorized or launched by this fixture.
"""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
import httpx

from tools.research import agent,core,reporter
from tools.research.config import ROOT,resolve
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.design import generate_candidate
from tools.research.object_choices import main_projection
from tools.research.state import state,update
from tools.state_io import digest,read
from tests.research.test_p63a_math_interface import fixture_host
from tests.research.test_research_authorization_preflight import approve
from tests.research.test_structure_mechanism_aplus import synthetic_worker
from tests.research.test_matched_interaction import BilinearNative


class CrossTaskLoopTests(unittest.TestCase):
    def run_loop(self, *, tracking):
        task='bf4_tracking_direction_change_v1.json' if tracking else 'bf7_shared_reach_v1_central_high.json'
        original=(ROOT/'tasks'/task).read_bytes()
        arguments=dict(task=task)
        if tracking:
            frozen=resolve(ROOT/'configs/research/study_tracking_public.json')
            arguments.update(family_execution=read(ROOT/'configs/research/study_tracking_public.json')['family_execution'],control='control_bf4_tracking.json',
                family_space='family_space_bf4_s3_tracking.json',reference_parameters=read(ROOT/'configs/research/study_tracking_public.json')['reference_parameters'])
        h=fixture_host(**arguments);spec=deepcopy(state(h)['spec'])
        spec['research_decisions']['analysis_interface']='scientific_question_v4'
        spec['mathematical_methods']['mechanism_structure_v1']='OFFLINE SYNTHETIC FIXTURE ONLY'
        update(h,spec=spec);approve(h,[REGISTERED_MATHEMATICS_SCOPE])
        c=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
            segment_count=2,tendon_count=6 if tracking else 4),dict(origin='OFFLINE synthetic plumbing test'))['candidate']
        selected=['segments.0.length_m','segments.1.length_m']
        def plan(after=False):
            source=state(h)['analysis_results'][-1] if after else None
            return dict(action='diagnose',hypothesis=('SCRIPTED fixture: revise the inertial coupling hypothesis after source-linked feedback.' if after else
                'SCRIPTED fixture: joint length dependence of inertia competes with separate mass scaling; task-level relevance is unknown.'),
                expected_observation='Matched local mechanism contrasts; no task success claim',
                weakening_observation='Unresolved numerical scale or invalid matching weakens interpretation',
                fixed_conditions='Own frozen task, model, initial state, absolute input and other parameters',
                stopping_condition='One offline fixture loop; no real computation',
                interpretation='Scripted decisions do not demonstrate autonomous research.',
                supporting_evidence=[source] if source else [],next_research_action='mechanism_research',
                decision=dict(hypothesis_id='scripted-feedback' if after else 'scripted-coupling',research_intent='DIAGNOSE',
                    selected_candidate=c,selected_method='scientific_question',selected_variables=selected,requested_budget=0))
        question=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='interact',
            effect_semantics='mechanism_effect',parameter_paths=selected,target=dict(quantity='mass_matrix',reduction='norm'),
            operating_point='frozen_task_initial_state',control_treatment='fixed_absolute_tensions',requested_budget=4))
        main_wires=[];reporter_wires=[]
        def respond(request):
            wire=json.loads(request.content)
            if not wire.get('tools'):
                reporter_wires.append(wire);payload=json.loads(wire['messages'][-1]['content'])
                sources=payload['source_catalog'];source=next(k for k,v in sources.items() if v['pointer']=='/structure_research')
                interaction=payload['report']['results'][0]['mathematics']['structure_research']['interaction']
                interpretations=[dict(kind='new_information',text='Synthetic fixture finite contrasts: '+json.dumps(interaction['independent_effects'])+
                    '; interaction='+str(interaction['interaction_effect'])+'. No physical task conclusion.',source_ids=[source]),
                    dict(kind='hypothesis',text='Fixture joint inertial dependence competes with separate mass scaling; qualified finite task response could distinguish task relevance.',source_ids=[source]),
                    dict(kind='unresolved_question',text='No rigorous error bound or full-task prediction follows from this M0 synthetic fixture.',source_ids=[source])]
                message=dict(role='assistant',content=json.dumps(dict(interpretations=interpretations)));finish='stop'
            else:
                main_wires.append(wire);index=len(main_wires)
                if index>3:raise AssertionError('Unexpected extra scripted Main request')
                name,payload=('research_analysis',question) if index==2 else ('research_plan',plan(after=index==3))
                schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']==name)
                if schema.get('$defs',{}).get('EvidenceRef',{}).get('type')=='string':
                    payload=main_projection(h,payload)
                    if name=='research_plan':
                        if 'supporting_evidence' not in schema['properties']:payload.pop('supporting_evidence',None)
                        decision=schema['$defs']['ResearchDecision']['properties']
                        for key in ('selected_candidate','selected_method','requested_budget','research_intent','selected_variables'):
                            if key not in decision:payload['decision'].pop(key,None)
                message=dict(role='assistant',content=None,tool_calls=[dict(id='scripted-'+str(index),type='function',
                    function=dict(name=name,arguments=json.dumps(payload)))]);finish='tool_calls'
            return httpx.Response(200,json=dict(id='offline-interaction',object='chat.completion',created=1,model=wire['model'],
                choices=[dict(index=0,finish_reason=finish,message=message)],usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14)))
        with (patch('tools.research.agent.credential',return_value='offline'),patch('tools.research.provider.load_credential'),
                patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),patch.object(core,'guard'),patch.object(agent,'guard'),
                patch('tools.research.tool_readiness.execution_environment',return_value=dict(status='ready')),
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)),synthetic_worker(h,c,model=BilinearNative)):
            asyncio.run(agent.converse(h,max_new_provider_requests=4))
        self.assertEqual(len(main_wires),3);self.assertEqual(len(reporter_wires),1)
        self.assertEqual(state(h)['mathematical_evaluations'],4)
        raw=h.store.artifact(state(h)['analysis_results'][-1]);interaction=raw['structure_research']['interaction']
        self.assertEqual(interaction['status'],'computed_local_interaction')
        self.assertEqual(raw['structure_research']['parameterized_problem']['sensitivity_problem']['level'],'M0')
        self.assertEqual(state(h)['spec']['canonical_task']['family'],'task.tracking' if tracking else 'task.reach')
        self.assertEqual(raw['task_analysis']['binding']['task_identity'],digest(h.store.artifact(c)['configuration']['task']))
        self.assertEqual(h.store.artifact(state(h)['plans'][-1])['original_plan']['decision']['hypothesis_id'],'scripted-feedback')
        self.assertEqual(reporter.entries(h)[-1][1]['interpretation_status'],'available')
        delivered=json.dumps(main_wires[-1]);self.assertIn('Synthetic fixture finite contrasts',delivered)
        self.assertIn(str(interaction['interaction_effect']),delivered)
        self.assertEqual((ROOT/'tasks'/task).read_bytes(),original)
        if tracking:
            self.assertEqual(state(h)['spec']['canonical_task_identity'],frozen['canonical_task_identity'])
            self.assertNotIn('holding_position',{c['constraint_id'] for c in raw['task_analysis']['constraints']})

    def test_reach_free_scripted_sdk_reporter_feedback_loop(self):self.run_loop(tracking=False)

    def test_tracking_uses_own_frozen_definition_in_scripted_loop(self):self.run_loop(tracking=True)


if __name__=='__main__':unittest.main()
