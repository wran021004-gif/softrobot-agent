"""Public cross-task contracts with fabricated motion; never scientific evidence."""
from copy import deepcopy
from pathlib import Path
from contextlib import contextmanager
import shutil
import gc
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.contracts import PLAN_RESEARCH_INTENTS
from tools.research.state import state, save, update
from tools.research_tasks import task_adapter, _source_issue
from tools.state_io import atomic_json, read, digest


def plan(action, candidate=None, **payload):
    return dict(action=action, hypothesis='Public interface engineering check',
        expected_observation='Registered task-bound result', weakening_observation='Invalid binding',
        fixed_conditions='Frozen engineering task', stopping_condition='One fixture operation',
        interpretation='Engineering check only; no benchmark feasibility claim', decision=dict(hypothesis_id='interface-fixture',
            research_intent=PLAN_RESEARCH_INTENTS[action], selected_method=action,
            **(dict(selected_candidate=candidate) if candidate else {})), **payload)


@contextmanager
def fixture_directory():
    folder=ROOT/'runs'/('cross-task-'+uuid4().hex[:8])
    folder.mkdir(parents=True)
    try:yield folder
    finally:
        gc.collect()
        shutil.rmtree(folder)


def fixture_host(folder, leaf='study_tracking_public.json'):
    spec=resolve(ROOT/'configs/research'/leaf)
    spec=deepcopy(spec)
    spec['mode']='engineering_numerical'
    spec['study_id']='cross-task-fixture-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id']
    spec['budgets'].update(physical_launches=3, public_operations=100)
    spec['configuration']['policy']['budget'].update(backend_solves=3, tool_calls=100)
    with patch('tools.research.config.resolve',return_value=spec):
        host=core.prepare(directory=folder)
    update(host,freeze='fabricated-interface-fixture')
    scope=dict(study_id=host.run_id,resolved_identity=spec['resolved_identity'],capabilities=['analysis'])
    save(host,dict(user_approval='Fixture only',scope=scope,scope_identity=digest(scope)),
        'formal_study_authorization')
    return host


def perfect_tracking_worker(command, log, timeout):
    request=read(Path(command[-1]));cfg=request['configuration']
    times=np.arange(round(cfg['task']['timing']['duration_s']/cfg['task']['timing']['sample_period_s'])+1)*cfg['task']['timing']['sample_period_s']
    positions=task_adapter(cfg).reference_at(times)[0]
    atomic_json(Path(command[-1]).parent/'result.json',dict(
        fixture='Fabricated perfect motion; no physics executed', status='completed',
        physics_steps=round(cfg['task']['timing']['duration_s']/cfg['task']['timing']['timestep_s']),
        tendon_order=request['trajectory']['tendon_order'], samples=[dict(time_s=float(t),tip_m=p.tolist(),
            **(dict(tip_tool_axis_world=cfg['task']['goal']['data']['target_axis_world']) if cfg['task']['family']=='task.position_tool_axis' else {}),
            speed_m_s=0.,actual_tension_n=u) for t,p,u in zip(times,positions,[request['trajectory']['tensions_n'][0],*request['trajectory']['tensions_n']])]))
    return SimpleNamespace(returncode=0)


class CrossTaskIntegrationTests(unittest.TestCase):
    def test_two_conditions_resume_independent_controls_and_joint_select(self):
        from tools.research.feedback import eligibility, result_view
        from tools.research.conditions import joint_assessment
        with fixture_directory() as folder:
            host=fixture_host(folder,'study_multicondition_public.json')
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                spec=state(host)['spec']
                request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                    segment_count=2,tendon_count=6)
                candidate=core.dispatch(host,plan('generate',generation=request),'generate')['result']['candidate']
                results=[];seeds=[]
                for index,condition in enumerate(spec['task_conditions']):
                    seed=core.dispatch(host,plan('initialize_control',candidate,control_seed=dict(candidate=candidate,
                        condition_id=condition['condition_id'],tensions_n=[[.2+index*.1]*6])),'seed-'+str(index))['result']
                    seeds.append(seed)
                    with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                        result=core.dispatch(host,plan('physical_replay',seed['candidate'],physical_replay=dict(
                            candidate=seed['candidate'],source=seed['source'])),'replay-'+str(index))['result']
                    results.append(result['reference'])
                    core.read_evidence(host,dict(reference=result['reference'],view='full'))
                    if index==0:
                        self.assertFalse(state(host).get('success_gate'))
                        self.assertFalse(eligibility(host,results,selection=True)['eligible'])
                        self.assertFalse(eligibility(host,results[0],selection=True)['eligible'])
                        # Reopen the same partial Store; neither budget nor result is reset.
                        host=core.Host(folder,host.run_id,actor=host.actor);host.resume()
                        self.assertEqual(state(host)['physical_replays'],results)
                self.assertNotEqual(seeds[0]['source'],seeds[1]['source'])
                self.assertNotEqual(seeds[0]['candidate'],seeds[1]['candidate'])
                self.assertTrue(state(host)['success_gate']['observed_task_pass'])
                self.assertTrue(eligibility(host,results[::-1],selection=True)['eligible'])
                with self.assertRaisesRegex(ValueError,'DUPLICATE_TASK_CONDITION'):
                    joint_assessment(host,[results[0],results[0]])
                selected=core.dispatch(host,plan('select',selected_execution=results[::-1]),'select')
                self.assertTrue(selected['result']['selected'])
                joint=host.store.artifact(state(host)['selected'])
                self.assertEqual(joint['condition_results'],results)
                self.assertTrue(result_view(host,state(host)['selected'])['passed'])
                self.assertEqual(joint['costs']['backend_solves'],2)
                self.assertEqual(host.store.remaining()['used']['backend_solves'],2)
                core.export(host,Path(folder)/'export')
                package=read(Path(folder)/'export/design_package.json')
                self.assertTrue(package['accepted'])
                self.assertEqual(len(package['condition_results']),2)

    def test_three_condition_identity_and_invalid_sources(self):
        from tools.research.conditions import condition_candidate, joint_assessment
        from tools.research.design import verify_candidate
        from tools.research.feedback import eligibility
        with fixture_directory() as folder:
            host=fixture_host(folder,'study_multicondition_public.json')
            s=state(host);third=deepcopy(s['spec']['task_conditions'][1])
            value=read(ROOT/'tasks/bf2_multidirectional_hold_frozen_v1_negative.json')
            third.update(condition_id='negative',task=value['task'],settling=value['settling'],seed=value['seed'])
            third['task']['initializer']['parameters']['data']=dict(rule='all_candidate_dofs_zero_v1')
            s['spec']['task_conditions'].append(third);update(host,spec=s['spec'])
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                request=dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],
                    segment_count=2,tendon_count=6)
                root=core.dispatch(host,plan('generate',generation=request),'generate')['result']['candidate']
                third_ref=condition_candidate(host,root,'negative')
                candidate=verify_candidate(host,third_ref)
                self.assertEqual(candidate['configuration']['robot'],host.store.artifact(root)['configuration']['robot'])
                self.assertEqual(candidate['configuration']['task']['environment'],third['task']['environment'])
                self.assertEqual(third_ref,condition_candidate(host,root,'negative'))
                seed=core.dispatch(host,plan('initialize_control',root,control_seed=dict(candidate=root)),'seed')['result']
                with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                    result=core.dispatch(host,plan('physical_replay',root,physical_replay=dict(candidate=root,source=seed['source'])),'replay')['result']
                core.read_evidence(host,dict(reference=result['reference'],view='full'))
                self.assertFalse(eligibility(host,[result['reference']],selection=True)['eligible'])
                with self.assertRaisesRegex(ValueError,'TASK|MODEL|IDENTITY'):
                    core.dispatch(host,plan('physical_replay',third_ref,physical_replay=dict(candidate=third_ref,source=seed['source'])),'wrong-source')
                forged=deepcopy(result);forged.pop('reference');forged['execution_id']='not-a-store-execution'
                ref=save(host,forged,'fabricated_invalid_receipt_fixture')
                update(host,physical_replays=[*state(host)['physical_replays'],ref],evaluation_reads=[ref])
                with self.assertRaisesRegex(ValueError,'RECEIPT_REQUIRED'):
                    joint_assessment(host,[ref])
                failed=deepcopy(result);failed.pop('reference');failed['acceptance']['accepted']=False
                failed_ref=save(host,failed,'fabricated_failed_condition_fixture')
                update(host,physical_replays=[*state(host)['physical_replays'],failed_ref],evaluation_reads=[failed_ref])
                with self.assertRaisesRegex(ValueError,'did not pass'):
                    joint_assessment(host,[failed_ref])
                length=next(c['length_m'] for c in host.store.artifact(root)['configuration']['robot']['structure']['data']['components'] if c['kind']=='flexible_segment')
                changed={**request,'segments':{'0':dict(length_m=length+.01)}}
                other=core.dispatch(host,plan('generate',generation=changed),'other-structure')['result']['candidate']
                mixed=deepcopy(result);mixed.pop('reference');mixed['candidate']=condition_candidate(host,other,'positive')
                other_candidate=verify_candidate(host,mixed['candidate'])
                mixed['scientific_configuration']=other_candidate['scientific_configuration']
                mixed['source_reference']=core.dispatch(host,plan('initialize_control',mixed['candidate'],
                    control_seed=dict(candidate=mixed['candidate'])),'other-seed')['result']['source']
                mixed_ref=save(host,mixed,'fabricated_mixed_structure_fixture')
                update(host,physical_replays=[*state(host)['physical_replays'],mixed_ref],evaluation_reads=[result['reference'],mixed_ref])
                with self.assertRaisesRegex(ValueError,'IDENTICAL_STRUCTURE'):
                    joint_assessment(host,[result['reference'],mixed_ref])

    def test_public_generation_discovery_replay_read_select(self):
        self.public_route('study_tracking_public.json',{'timed_tracking'})

    def test_bf5_public_generation_discovery_replay_read_select(self):
        self.public_route('study_bf5_public.json',{'tool_position','tool_axis_direction'})

    def public_route(self,leaf,constraints):
        from tools.research.agent import plan_schema
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.feedback import eligibility
        with fixture_directory() as folder:
            host=fixture_host(folder,leaf)
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                spec=state(host)['spec']
                schema=plan_schema(spec['allowed_plan_actions'],decision_required=True,
                    family_version=spec['family_space']['version'])
                self.assertIn('physical_replay',schema['properties']['action']['enum'])
                request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                    segment_count=2,tendon_count=6,control_weights=dict(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.))
                generated=core.dispatch(host,plan('generate',generation=request),'generate')['result']
                self.assertEqual(generated['status'],'generated',generated)
                candidate=generated['candidate']
                methods=mathematical_method_view(host,candidate)['methods']
                native=methods['mujoco_direct_control_v1']
                self.assertTrue(native['formal_execution_authorized'])
                self.assertNotEqual(native['planning_status'],'unsupported')
                self.assertEqual({c['constraint_id'] for c in native['coverage']},constraints)
                seed=core.dispatch(host,plan('initialize_control',candidate,
                    control_seed=dict(candidate=candidate)),'seed')['result']['source']
                with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                    result=core.dispatch(host,plan('physical_replay',candidate,
                        physical_replay=dict(candidate=candidate,source=seed)),'replay')['result']
                self.assertTrue(result['acceptance']['accepted'],result['acceptance'])
                self.assertIsNone(_source_issue(result['acceptance']))
                receipt=read(Path(folder)/'physical_replay'/result['execution_id']/'request.json')
                self.assertEqual(host.store.lookup(host.run_id,receipt['request_id'])['execution_id'],result['execution_id'])
                self.assertEqual(host.store.artifact(result['profile_reference'])['execution_id'],result['execution_id'])
                self.assertFalse(eligibility(host,result['reference'],selection=True)['eligible'])
                core.read_evidence(host,dict(reference=result['reference'],view='full'))
                self.assertTrue(eligibility(host,result['reference'],selection=True)['eligible'])
                selected=core.dispatch(host,plan('select',selected_execution=result['reference']),'select')
                self.assertTrue(selected['result']['selected'])
                self.assertEqual(host.store.remaining()['used']['backend_solves'],1)


if __name__=='__main__':
    unittest.main()
