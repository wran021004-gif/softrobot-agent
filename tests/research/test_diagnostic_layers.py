"""Directed real PHS failures and saved active regressions; no Provider/rollout."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from tools.platform_store import plain
from tools.research import analysis
from tools.research.config import resolve
from tools.research.contracts import AnalysisRequest
from tools.research.design import family_configuration
from tools.research.structure_research import calculate

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'runs/stage1_diagnostics'
REF=dict(artifact_id='a'*64,media_type='application/json')  # Test binding only.


def passive_inspect(length=None):
    spec=resolve(ROOT/'configs/research/study_phs2d_mechanism_successor_20261105.json')
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=9,tendon_count=4)
    if length is not None:request['segments']={str(i):dict(length_m=length) for i in range(9)}
    cfg,build,_=family_configuration(spec['configuration'],spec['family_space'],request,'stage1-engineering-test')
    query=AnalysisRequest(candidate=REF,operation='mechanism_structure_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol={**spec['analysis_protocol'],
            'duration_s':cfg['task']['timing']['duration_s'],'period_s':cfg['task']['timing']['control_period_s']},
        mechanism_study=dict(operation='inspect',target=dict(quantity='constraint_active_set'),
            point_semantics='re_equilibrated',load_condition=cfg['task']['physical_problem']['baseline_load'],max_evaluations=1))
    context=dict(selected_parameters=[],evaluations=1)
    out=calculate(cfg,dict(candidate=REF),query,dict(actual_time_s=0.),context)
    out['candidate']=REF
    return out,build,cfg


class DiagnosticLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.failed,_,cls.cfg=passive_inspect()
        cls.unqualified,_,_=passive_inspect(.04)
        OUT.mkdir(parents=True,exist_ok=True)
        for name,result in (('initial_forward_failure',cls.failed),('unqualified_multistart',cls.unqualified)):
            (OUT/(name+'.json')).write_text(json.dumps(dict(scope='Real original-scene PHS static engineering test; not a Study or task acceptance',
                result=result,diagnostic_layers=analysis.diagnostic_layers(result)),indent=2),encoding='utf-8')

    def test_real_first_forward_failure_keeps_position_geometry_and_cost(self):
        out=self.failed;layers=analysis.diagnostic_layers(out);raw=out['structure_research']
        geometry=layers['geometry'];process=layers['numerical_solve']['facts']
        self.assertEqual(geometry['status'],'passed')
        self.assertEqual(geometry['facts']['contact_count'],228)
        self.assertEqual(len(geometry['facts']['tendon_length_m']),4)
        self.assertIn('position_world_m',geometry['facts']['contact_examples'][0])
        self.assertFalse(process['initial_forward_completed'])
        self.assertEqual(process['starts_attempted'],1)
        self.assertEqual(process['starts_skipped_after_abort'],1)
        self.assertFalse(process['trials'][0]['optimizer_entered'])
        self.assertEqual(process['failure_stage'],'initial_forward')
        self.assertEqual(layers['numerical_solve']['status'],'unqualified')
        self.assertEqual(layers['static_qualification']['status'],'not_evaluated')
        self.assertEqual(layers['dynamic_validation']['status'],'not_evaluated')
        self.assertNotIn('kkt_pass',layers['static_qualification']['facts'])
        self.assertEqual(raw['cost']['native_position_calls'],1)
        self.assertEqual(raw['cost']['native_forward_attempts'],1)
        self.assertEqual(raw['cost']['native_forward_calls'],0)
        self.assertEqual(raw['cost']['physics_steps'],0)

    def test_real_contact_free_two_start_failure_has_separate_qualifications(self):
        raw=self.unqualified['structure_research'];layers=analysis.diagnostic_layers(self.unqualified)
        mech=raw['records'][0]['mechanics'];result=mech['equilibrium'];trials=result['trials']
        self.assertEqual(layers['geometry']['facts']['contact_count'],0)
        self.assertEqual(len(trials),2)
        np.testing.assert_array_equal(trials[0]['initial'],np.zeros(len(trials[0]['initial'])))
        np.testing.assert_array_equal(trials[1]['initial'],.001*np.sin(np.arange(len(trials[0]['initial']))))
        self.assertEqual([t['optimizer_status'] for t in trials],[4,9])
        self.assertEqual(trials[1]['iterations'],self.cfg['task']['goal']['data']['unloaded_static_solver']['max_iterations'])
        for trial in trials:
            self.assertTrue(trial['optimizer_entered']);self.assertTrue(trial['initial_forward_completed'])
            self.assertFalse(trial['optimizer_success'])
            self.assertEqual(set(trial['qualification_checks']),{'length_constraints','dual_nonnegative','stationarity',
                'complementarity','tension_capacity','KKT','LICQ','strict_complementarity','second_order_sufficient','contact_free'})
        self.assertEqual(layers['static_qualification']['status'],'unqualified')
        self.assertFalse(layers['static_qualification']['facts']['stability_qualified'])
        self.assertIsNone(mech['tangent_stiffness']);self.assertIsNone(mech['tangent_compliance'])
        from extensions.math_analysis.mechanism_registry import observe
        self.assertEqual(observe(mech,dict(quantity='tangent_stiffness'))['reason'],'QUALIFIED_REGULAR_EQUILIBRIUM_REQUIRED')
        self.assertEqual(layers['dynamic_validation']['status'],'not_evaluated')
        self.assertEqual(raw['cost']['physics_steps'],0)
        self.assertNotIn('structure_direction',raw)

    def test_active_saved_sorosim_results_keep_model_and_scope(self):
        from test_sorosim_analysis import inputs,BATCH
        inp,_,p,binding=inputs()
        for name in ('standardized_initial_pretension','target_equilibrium'):
            saved=json.loads((BATCH/(name+'.json')).read_text())
            q=dict(candidate=binding['candidate'],operation='controllability',operating_point=name,protocol=plain(p),scoring_window_s=.05)
            with patch('extensions.tendon_family.sorosim_analysis.calculate_candidate_configuration',return_value=deepcopy(saved)):
                out=analysis.calculate(plain(inp),binding,q)
            self.assertEqual(out['model'],saved['records'][1]['model'])
            self.assertEqual(out['construction'],saved['records'][1]['construction'])
            layers=out['diagnostic_layers']
            self.assertEqual(layers['numerical_solve']['status'],'passed')
            self.assertEqual(layers['static_qualification']['status'],'passed' if name=='target_equilibrium' else 'not_applicable')
            self.assertEqual(layers['dynamic_validation']['status'],'not_evaluated')
            self.assertNotIn('KKT',json.dumps(layers));self.assertNotIn('payout',json.dumps(layers))

    def test_interrupted_active_derivative_progress_stays_partial(self):
        # Explicit process fixture, not robot evidence: no derivative returned.
        result=dict(status='execution_incomplete',reason='Injected derivative failure',
            active_model_progress=[dict(stage='model_preparation'),dict(stage='derivative_check',
                row=dict(construction=dict(static_equilibrium=False),model=dict(y0=[0.,0.,0.],operating_point=dict(name='halfway_waypoint'))))])
        layers=analysis.diagnostic_layers(result)
        self.assertEqual(layers['geometry']['status'],'passed')
        self.assertEqual(layers['numerical_solve']['status'],'unqualified')
        self.assertIsNone(layers['numerical_solve']['facts']['derivative_check'])
        self.assertEqual(layers['dynamic_validation']['status'],'not_evaluated')

    def test_native_rejection_retains_recorded_geometry_without_static_eligibility(self):
        # Explicit unsupported-state fixture; the diagnostic was recorded after
        # native forward and before state-support rejection, not an equilibrium.
        value=dict(status='execution_incomplete',reason='Unsupported contacts',native_diagnostic=dict(
            contact_count=1,constraint_count=4,contacts=[dict(geom1='floor',geom2='body')],cost=dict(forward_evaluations=1)))
        layers=analysis.diagnostic_layers(value)
        self.assertEqual(layers['geometry']['facts']['contact_count'],1)
        self.assertEqual(layers['numerical_solve']['status'],'unqualified')
        self.assertEqual(layers['static_qualification']['status'],'not_evaluated')
        self.assertEqual(value['native_diagnostic']['cost']['forward_evaluations'],1)

    def test_second_start_abort_keeps_completed_first_trial_and_optimizer_return(self):
        from tests.research.test_constrained_mechanics import physical_fixture
        from extensions.tendon_family.passive import PassiveModel
        from extensions.tendon_family.passive_equilibrium import solve,StaticProblem,qualification_diagnosis
        *_,physics,problem=physical_fixture();native=PassiveModel(physics,problem)
        original=StaticProblem.qualify;calls=[]
        def qualify(instance,q):
            calls.append(True)
            if len(calls)==2:raise ValueError('Injected qualification interruption; fixture only')
            return original(instance,q)
        with patch.object(StaticProblem,'qualify',new=qualify),self.assertRaisesRegex(ValueError,'Injected') as failure:
            solve(native,multistart=True)
        progress=failure.exception.equilibrium_progress
        self.assertEqual(len(progress['trials']),1)
        self.assertTrue(progress['failed_trial']['initial_forward_completed'])
        self.assertIn('optimizer_status',progress['failed_trial'])
        self.assertEqual(progress['failed_trial']['failure_stage'],'qualification')
        self.assertNotIn('kkt_pass',progress['failed_trial'])
        self.assertEqual(len(qualification_diagnosis(failure=failure.exception,multistart=True)['trials']),2)

    def test_dynamic_evidence_is_independent_of_static_layers(self):
        # Recorded-shape fixture only; this test performs no integration.
        result=deepcopy(self.failed)
        result['dynamic_execution_progress']=[dict(status='completed',episodes=[dict(load_condition='fixture_case',complete=True)],cost=dict(physics_steps=2))]
        layers=analysis.diagnostic_layers(result)
        self.assertEqual(layers['static_qualification']['status'],'not_evaluated')
        self.assertEqual(layers['dynamic_validation']['status'],'passed')
        self.assertIn('independent Replay',layers['dynamic_validation']['missing_checks'])
        self.assertEqual(analysis.diagnostic_overview(layers)['highest_passed_layer'],'dynamic_validation')

    def test_main_reporter_and_tool_use_one_projection_without_mutation(self):
        from tools.research.evidence_views import quantitative_facts
        value=deepcopy(self.unqualified);before=deepcopy(value)
        expected=analysis.diagnostic_layers(value)
        self.assertEqual(analysis.compact_result(value,REF)['diagnostic_layers'],expected)
        self.assertEqual(analysis.decision_result(value,REF)['diagnostic_layers'],expected)
        self.assertEqual(quantitative_facts(value,REF)['diagnostic_layers'],expected)
        self.assertEqual(analysis.compact_result(value,REF)['candidate'],REF)
        self.assertEqual(value,before)
        compact=analysis.compact_result(self.failed,REF)['structure_research']['qualification_diagnosis']
        self.assertNotIn('numerical_failure',compact)
        self.assertNotIn('initial',compact['trials'][0])
        self.assertIn('numerical_failure_pointer',compact)

    def test_returned_active_equilibrium_before_model_failure_is_not_inapplicable(self):
        # Explicit interrupted-model fixture; a returned construction is retained,
        # but no converted model or completed qualification can be assumed.
        value=dict(status='execution_incomplete',reason='Injected model conversion failure',active_model_progress=[
            dict(stage='analysis_returned',row=dict(name='target_equilibrium',construction=dict(success=True,
                static_equilibrium=True,static_residual_inf=1e-12),raw_facts=dict(equilibrium=True)))])
        layer=analysis.diagnostic_layers(value)['static_qualification']
        self.assertEqual(layer['status'],'not_evaluated')
        self.assertEqual(layer['facts']['static_residual_inf'],1e-12)

    def test_gvs_derivative_subcheck_failure_is_not_lost_without_aggregate_flag(self):
        # GVS-shaped derivative fixture only: the real GVS contract reports three
        # independent checks and has no aggregate passed field.
        row=dict(point=dict(name='halfway_waypoint'),model=dict(y0=[0.,0.,0.]),
            derivative_check=dict(dynamics=dict(passed=False),output=dict(passed=True),tip_velocity=dict(passed=True)))
        value=dict(status='computed',raw=dict(records=[{},row]))
        layers=analysis.diagnostic_layers(value)
        self.assertEqual(layers['numerical_solve']['status'],'unqualified')
        self.assertEqual(layers['static_qualification']['status'],'unqualified')
        self.assertEqual(value['status'],'computed')  # Preserve original computation semantics.


if __name__=='__main__':unittest.main()
