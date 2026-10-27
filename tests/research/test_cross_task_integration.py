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
    return dict(action=action, hypothesis='Fabricated public interface fixture',
        expected_observation='Registered task-bound result', weakening_observation='Invalid binding',
        fixed_conditions='Frozen fixture task', stopping_condition='One fixture operation',
        interpretation='No scientific evidence', decision=dict(hypothesis_id='interface-fixture',
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


def fixture_host(folder):
    spec=resolve(ROOT/'configs/research/study_tracking_public.json')
    spec=deepcopy(spec)
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
            speed_m_s=0.,actual_tension_n=u) for t,p,u in zip(times,positions,[request['trajectory']['tensions_n'][0],*request['trajectory']['tensions_n']])]))
    return SimpleNamespace(returncode=0)


class CrossTaskIntegrationTests(unittest.TestCase):
    def test_public_generation_discovery_replay_read_select(self):
        from tools.research.agent import plan_schema
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.feedback import eligibility
        with fixture_directory() as folder:
            host=fixture_host(folder)
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
                self.assertEqual({c['constraint_id'] for c in native['coverage']},{'timed_tracking'})
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
