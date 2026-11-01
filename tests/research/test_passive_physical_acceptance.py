"""Small real MuJoCo engineering fixtures and real SDK/Mock HTTP integration.

All thresholds are frozen in committed tasks before execution. No Provider call,
autonomous design result, historical PHS success or robustness claim.
"""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import re
import unittest
from unittest.mock import patch
import numpy as np
from schemas.platform import SessionInput, EvidenceRef
from tools.platform_store import plain
from tools.platform_registry import registry
from tools.state_io import atomic_json
from tools.research.config import resolve
from tools.research.state import state,update,save
from tools.research import core
from tools.research_tasks import task_adapter
from extensions.tendon_family.passive_execution import execute,backend_result
from extensions.reference.passive_response import evaluate

ROOT=Path(__file__).resolve().parents[2]
CONFIG=ROOT/'configs/research/study_passive_engineering_v1.json'
OUT=ROOT/'runs/stage3ab_validation'
OUT.mkdir(parents=True,exist_ok=True)


def prepared_host(*,failure=False,wire=False,budget=4):
    name='stage3ab-'+uuid4().hex[:10]
    cfg=json.loads(CONFIG.read_text())
    cfg.update(study_id=name,evidence_destination='runs/'+name)
    cfg['budgets']['physical_launches']=budget
    if failure:cfg['task']='../../tasks/passive_response_engineering_failure_v1.json'
    if wire:cfg['mode']='formal_research' # Mock HTTP protocol test; still engineering task/authorization.
    path=ROOT/'configs/research'/('._'+name+'.json')
    path.write_text(json.dumps(cfg),encoding='utf8')
    try:h=core.prepare(path,ROOT/'runs'/name)
    finally:path.unlink()
    core.bind(h)
    pilot=state(h)['pilot'];pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback')
    update(h,pilot=pilot)
    from tools.research.design import generate_candidate
    s=state(h)
    request=dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],segment_count=1,tendon_count=1)
    result=generate_candidate(h,request,dict(origin='stage3ab_engineering_fixture'))
    assert result['status']=='generated',result
    return h,result['candidate']


def replay_plan(candidate):
    from tests.research.test_saved_object_choices import rationale
    plan=rationale('physical_replay')
    plan.update(physical_replay=dict(candidate=candidate),supporting_evidence=[])
    plan['decision']=dict(hypothesis_id='passive-engineering',research_intent='PHYSICAL_VALIDATION',
        selected_method='frozen_passive_protocol',selected_candidate=candidate,requested_budget=2,
        claimed_inference='empirical_search',selected_variables=[])
    return plan


class PassiveAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=resolve(CONFIG)['configuration']
        cls.inp=SessionInput.model_validate(cls.cfg)
        cls.backend=execute(cls.inp,OUT/'real_default')
        cls.source=EvidenceRef(artifact_id='0'*64) # Direct evaluator fixture, no formal read/SELECT credit.
        cls.evaluation=evaluate(cls.inp.task,cls.backend,cls.source,registry(),'engineering-direct')
        atomic_json(OUT/'direct_backend.json',plain(cls.backend))
        atomic_json(OUT/'direct_evaluation.json',plain(cls.evaluation))

    def test_registered_task_adapter_and_true_no_control(self):
        from tools.platform_tasks import compile_input
        self.assertTrue(compile_input(self.cfg)['approval']['capabilities_ready'])
        a=task_adapter(self.cfg)
        self.assertEqual(a.describe()['registered_acceptance'],'offline_passive_response_v1')
        self.assertEqual(a.control_reference()['kind'],'passive_loading_protocol')
        self.assertFalse(a.ppo_applicability()['supported'])
        self.assertEqual(a.operating_point()['time_reference'],'passive_episode_local_time')
        self.assertTrue(a.ranking_limits())
        for fn,args in [(a.reference_at,([0.],)),(a.control_search_options,()),(a.holding_start_s,())]:
            with self.assertRaisesRegex(ValueError,'NOT_APPLICABLE_PASSIVE'):fn(*args)
        self.assertFalse(a.analysis_requirements({}).constraints)
        bad=deepcopy(self.cfg);bad['policy']['controller']=resolve(ROOT/'configs/research/study_s125_cold.json')['configuration']['policy']['controller']
        with self.assertRaises(ValueError):compile_input(bad)

    def test_complete_real_execution_and_different_loads(self):
        b=self.backend;raw=b.data.data
        self.assertEqual(b.solver_status,'completed')
        self.assertEqual(raw['active_actuators'],0)
        self.assertEqual(raw['cost']['model_builds'],1)
        self.assertEqual(raw['cost']['physics_steps'],800)
        self.assertEqual(raw['cost']['episodes_completed'],2)
        self.assertEqual(self.evaluation.validity,'valid');self.assertTrue(self.evaluation.task_success)
        self.assertTrue(b.signals)
        a,z=raw['episodes']
        self.assertEqual(a['initial_state'],z['initial_state'])
        self.assertEqual(len(a['samples']),41)
        self.assertNotEqual(a['samples'][-1]['material_positions_m'],z['samples'][-1]['material_positions_m'])
        for e in raw['episodes']:
            self.assertEqual(e['physics_steps'],400)
            self.assertEqual(e['checked_physics_steps'],400)
            self.assertEqual(e['samples'][10]['force_world_n'],[0.,0.,0.])
            self.assertEqual(e['samples'][15]['phase'],'ramp')
            self.assertIn('actual_tension_n',e['samples'][-1])

    def test_real_taut_assembly_and_frozen_failure(self):
        cfg=deepcopy(self.cfg)
        space=json.loads((ROOT/'configs/research/family_space_passive_engineering_v1.json').read_text())
        cfg['robot']['structure']['data']['fixed_payout_lengths_m']['tendon_0']=space['passive_payout_domains_m']['tendon_0']['minimum']
        taut=execute(SessionInput.model_validate(cfg),OUT/'real_taut')
        self.assertEqual(taut.solver_status,'completed')
        self.assertGreater(max(e['maximum_tension_n'] for e in taut.data.data['episodes']),0.)
        failure_cfg=deepcopy(self.cfg)
        failure_cfg['task']=json.loads((ROOT/'tasks/passive_response_engineering_failure_v1.json').read_text())['task']
        # Apply the same frozen zero initializer to this already materialized mesh.
        failure_cfg['task']['initializer']=deepcopy(self.cfg['task']['initializer'])
        inp=SessionInput.model_validate(failure_cfg)
        failed=execute(inp,OUT/'real_failure')
        ev=evaluate(inp.task,failed,self.source,registry(),'engineering-negative-control')
        self.assertEqual(ev.validity,'valid');self.assertFalse(ev.task_success)
        self.assertIn('lateral_response_maximum',[c.name for c in ev.constraints if not c.satisfied])
        atomic_json(OUT/'failure_evaluation.json',plain(ev))
        atomic_json(OUT/'taut_cost.json',taut.data.data['cost'])

    def test_incomplete_invalid_and_every_bound(self):
        raw=deepcopy(self.backend.data.data);raw['episodes'].pop()
        ev=evaluate(self.inp.task,backend_result(self.inp,raw),self.source,registry(),'missing-load')
        self.assertEqual(ev.validity,'incomplete');self.assertIsNone(ev.task_success)
        raw=deepcopy(self.backend.data.data);raw['episodes'][0]['samples'].pop(20)
        self.assertEqual(evaluate(self.inp.task,backend_result(self.inp,raw),self.source,registry(),'missing-sample').validity,'incomplete')
        raw=deepcopy(self.backend.data.data);raw['numerical_failure']=dict(reason='Explicit numerical-invalidity fixture')
        self.assertEqual(evaluate(self.inp.task,backend_result(self.inp,raw),self.source,registry(),'invalid').validity,'invalid')
        raw=deepcopy(self.backend.data.data);raw['episodes'][0]['samples'][15]['force_world_n']=[0.,0.,0.]
        self.assertEqual(evaluate(self.inp.task,backend_result(self.inp,raw),self.source,registry(),'wrong-force').validity,'invalid')
        raw=deepcopy(self.backend.data.data);del raw['episodes'][0]['samples'][0]['qvel_rad_s']
        # Missing required samples stay incomplete, with no task score.
        modified=self.backend.model_copy(update=dict(data=self.backend.data.model_copy(update=dict(data=raw))))
        self.assertEqual(evaluate(self.inp.task,modified,self.source,registry(),'missing-state').validity,'incomplete')

    def test_shared_worker_budget_and_failing_result_cannot_select(self):
        h,c=prepared_host(failure=True)
        with patch.object(core,'guard'),patch('tools.research.physical_replay.guard'):
            result=core.dispatch(h,replay_plan(c),'real-negative-replay')['result']
        ref=result['reference'];raw=h.store.artifact(result['raw_reference'])
        self.assertEqual(result['acceptance']['status'],'valid_failure')
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        self.assertEqual(state(h)['physical_replay_launches'],2)
        self.assertEqual(raw['physics_steps'],800)
        from tools.research.feedback import eligibility
        from tools.research.evidence_views import acceptance_certificate
        cert=acceptance_certificate(h,ref)
        self.assertTrue(cert['complete_acceptance_view'],cert)
        self.assertFalse(eligibility(h,ref,selection=True)['eligible'])
        # Recovery after a settled request reuses the receipt; no new episode.
        before=h.store.remaining()['used']['backend_solves']
        with patch.object(core,'guard'):
            cached=core.dispatch(h,replay_plan(c),'real-negative-replay')
        self.assertEqual(h.store.remaining()['used']['backend_solves'],before)
        update(h,success_gate=None)
        from tests.research.test_p63r3_closure import selection
        stop=selection(c,ref);stop.update(action='stop',selected_execution=None,supporting_evidence=[ref])
        stop['decision'].update(research_intent='STOP',claimed_inference='empirical_search')
        with patch.object(core,'guard'):core.dispatch(h,stop,'failure-stop')
        self.assertEqual(state(h)['research_status'],'stopped')
        # Two episodes cannot be admitted against a one-episode budget.
        small,sc=prepared_host(budget=1)
        with patch.object(core,'guard'),patch('tools.research.physical_replay.guard'):
            with self.assertRaisesRegex(ValueError,'RESERVE_CANNOT_FIT'):core.dispatch(small,replay_plan(sc),'too-small')
        self.assertEqual(small.store.remaining()['used']['backend_solves'],0)

    def test_real_sdk_mock_wire_worker_certificate_select_stop(self):
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_p63r3_closure import selection
        from tools.research.evidence_views import acceptance_certificate
        from tools.research.feedback import eligibility
        from tools.research.object_choices import reference_choices
        h,c=prepared_host(wire=True)
        with patch('tools.research.physical_replay.guard'),patch('tools.research.reporter._wire',side_effect=ValueError('MOCK_REPORTER_UNAVAILABLE')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='physical_replay')),('research_plan',replay_plan(c))],limit=2)
        self.assertEqual(len(state(h)['physical_replays']),1)
        ref=state(h)['physical_replays'][0]
        self.assertFalse(eligibility(h,ref,selection=True)['eligible'])
        cert=acceptance_certificate(h,ref)
        self.assertTrue(cert['complete_acceptance_view'],cert)
        self.assertFalse(eligibility(h,ref,selection=True)['eligible']) # Reading as a developer/Reporter gives Main no credit.
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_ADDITIONAL_PHYSICS')),patch('tools.research.reporter._wire',side_effect=ValueError('MOCK_REPORTER_UNAVAILABLE')):
            wires+=run_fixture(h,[('evidence_read',dict(reference=ref,view='acceptance_certificate')),('research_route',dict(tool='research_plan',action='select')),('research_plan',selection(c,ref))],id_offset=2)
        self.assertEqual(state(h)['selected'],ref)
        self.assertEqual(state(h)['research_status'],'stopped')
        self.assertEqual(h.store.remaining()['used']['backend_solves'],2)
        for w in wires:
            text=json.dumps(w)
            self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])',text,re.I))
            self.assertNotIn('x-research-reference-choices',text)
        schema=next(t['function']['parameters'] for t in wires[1]['tools'] if t['function']['name']=='research_plan')
        self.assertNotIn('source',schema['$defs']['PhysicalReplayRequest']['properties'])
        alias=next(k for k,v in reference_choices(h).items() if v==ref)
        self.assertTrue(alias.startswith('evaluation_'))
        atomic_json(OUT/'wire_validation.json',dict(study=h.run_id,store=str(h.store.root),evaluation=ref,certificate=cert,
            physical_cost=h.store.artifact(ref)['actual_resource_consumption'],main_alias=alias,
            state=state(h)['research_status'],wire=wires,provider='Mock HTTP only; no real Provider calls'))

    def test_legacy_mathematical_task_remains_unregistered(self):
        from tests.research.test_constrained_mechanics import physical_fixture
        cfg=resolve(ROOT/'configs/research/study_s125_cold.json')['configuration']
        cfg['task'].update(physical_problem=physical_fixture()[-1],actuator_channels=[])
        a=task_adapter(cfg)
        self.assertEqual(a.execution_requirements()['registered_acceptance'],'not_registered')
        self.assertFalse(a.ppo_applicability()['supported'])
        with self.assertRaisesRegex(ValueError,'NOT_APPLICABLE_PASSIVE'):a.reference_at([0.])


if __name__=='__main__':unittest.main()
