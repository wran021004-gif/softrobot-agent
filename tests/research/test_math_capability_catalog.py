"""Offline catalog contracts; synthetic fixtures are not scientific evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.research import core
from tools.research.contracts import AnalysisRequest
from tools.research.math_capability_catalog import (OPERATION_CATEGORIES,
    capability_inventory, parameter_sensitivity_scope)
from tools.research.state import state, update
from tools.research.task_constraints import (registered_analysis_method_names,
    mathematical_method_view, mathematical_catalog)
from tests.research.test_p63a_math_interface import fixture_host, generate


class MathCapabilityCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real frozen configuration and candidate generation, no integration.
        cls.host=fixture_host();cls.candidate=generate(cls.host)

    def setUp(self):
        for target in ('tools.service_execution._run_contained',
                'extensions.tendon_family.mujoco_analysis.NativeModel', 'mujoco.mj_step'):
            stop=patch(target,side_effect=AssertionError('NO_SCIENTIFIC_EXECUTION'))
            stop.start();self.addCleanup(stop.stop)

    def test_five_categories_and_all_original_method_identities(self):
        self.assertEqual(set(OPERATION_CATEGORIES),{'inspect','solve','analyze','differentiate_optimize','compare'})
        rows=capability_inventory();registered=set(registered_analysis_method_names())
        self.assertEqual({k for k,v in rows.items() if v['has_formal_execution_entry']},registered)
        for key,row in rows.items():
            self.assertEqual(key,row['method_id'])
            self.assertTrue(row['generic_operations'])
            self.assertEqual(len(row['generic_operations']),len(set(row['generic_operations'])))
            self.assertLessEqual(set(row['generic_operations']),set(OPERATION_CATEGORIES))
            for name in ('implementation_locations','inputs','observables','model_scope','prerequisites','limitations','source'):
                self.assertTrue(row[name],(key,name))
            if key in registered:
                self.assertFalse(row['current_execution']['assessed'])
                self.assertNotIn('executable',row['current_execution'])
            else:
                self.assertFalse(row['current_execution']['executable'])
                self.assertEqual(row['interface_status'],'not_integrated')
                self.assertNotIn('request_template',row)
        # Returned records are detached from the static annotations.
        rows['linearization']['generic_operations'].append('compare')
        self.assertEqual(capability_inventory()['linearization']['generic_operations'],['analyze'])

    def test_candidate_query_is_read_only_and_keeps_execution_directory(self):
        h=self.host;before=deepcopy(state(h));schema=AnalysisRequest.model_json_schema()
        view=mathematical_method_view(h,self.candidate)
        catalog=mathematical_catalog(view)
        self.assertTrue(catalog['listed_methods_implemented'])
        self.assertEqual(set(catalog['methods']),set(view['methods']))
        for key,detail in view['methods'].items():
            row=view['capability_inventory'][key]
            self.assertEqual(row['current_method_query'],detail['detail_query'])
            for field in ('planning_status','execution_status','missing'):
                self.assertEqual(row['current_execution'][field],detail[field])
            self.assertEqual(catalog['methods'][key]['generic_operations'],detail['generic_operations'])
            fetched=core.read_tool_evidence(h,dict(reference=self.candidate,view='mathematical_capabilities',
                pointer='/methods/'+key+'/request_template'),record_read=False)
            self.assertEqual(fetched,detail['request_template'])
        key='passive_design_sensitivity_v1'
        fetched=core.read_tool_evidence(h,view['capability_inventory'][key]['detail_query'],record_read=False)
        self.assertEqual(fetched,view['capability_inventory'][key])
        self.assertNotIn(key,view['methods'])
        self.assertEqual(AnalysisRequest.model_json_schema(),schema)
        self.assertEqual(state(h),before)
        self.assertEqual(core.read_evidence(h,dict(reference=self.candidate,view='mathematical_capabilities',
            pointer='/operation_categories'),record_read=False),OPERATION_CATEGORIES)

    def test_unadapted_capabilities_never_become_operations_or_requests(self):
        rows=capability_inventory();schema=AnalysisRequest.model_json_schema()
        operations=schema['properties']['operation']['enum']
        for key,row in rows.items():
            if row['interface_status']=='not_integrated':
                self.assertNotIn(key,operations)
                self.assertNotIn('request_template',row)
        self.assertNotEqual(rows['equilibrium']['model_scope'],rows['passive_equilibrium_v1']['model_scope'])
        self.assertNotEqual(rows['linearization']['model_scope'],rows['native_dynamics_v1']['model_scope'])
        self.assertEqual(rows['passive_mechanism_ablation_v1']['capability_kind'],'historical_helper')
        self.assertEqual(rows['passive_load_response_metrics_v1']['source']['availability'],
            'local_source_only_remote_ref_not_returned')

    def test_original_unavailable_and_budget_statuses_are_only_projected(self):
        h=self.host;original=deepcopy(state(h))
        try:
            update(h,mathematical_evaluations=original['spec']['budgets']['mathematical_evaluations'])
            view=mathematical_method_view(h,self.candidate)
            for key,detail in view['methods'].items():
                projected=view['capability_inventory'][key]['current_execution']
                self.assertEqual(projected['planning_status'],detail['planning_status'])
                self.assertNotEqual(projected['planning_status'],'ready')
                self.assertTrue(projected['requires_original_admission'])
        finally:update(h,mathematical_evaluations=original['mathematical_evaluations'])

    def test_parameter_projection_uses_original_domains_and_effectiveness(self):
        rows=mathematical_method_view(self.host,self.candidate)['research_opportunities']['parameters']
        by_id={r['parameter_id']:r for r in rows}
        self.assertEqual(by_id['segments.0.length_m']['sensitivity_scope']['parameter_kind'],'continuous_conditional')
        self.assertEqual(by_id['segment_count']['sensitivity_scope']['parameter_kind'],'discrete_comparison')
        self.assertEqual(by_id['segments.0.cells']['sensitivity_scope']['parameter_kind'],'numerical_resolution')
        self.assertEqual(by_id['tendon_parameters.length_servo_gain_n_m']['sensitivity_scope']['parameter_kind'],'inactive_or_unresolved')
        for row in rows:
            scope=row['sensitivity_scope']
            self.assertEqual(scope['methods'],row['applicable_mathematical_methods'])
            self.assertEqual(scope['derivative_validated'],'not_established_by_catalog')
            self.assertIn('domain_source',row)
        weight=dict(category='controller',parameter_id='control_weights.speed',data_type='number',
            effective_in_current_execution=False,continuous_perturbation=False)
        self.assertEqual(parameter_sensitivity_scope(weight)['parameter_kind'],'controller_performance')

    def test_nine_trace_audit_keeps_original_ownership_and_acceptance_levels(self):
        root=Path(__file__).resolve().parents[2]
        audit=json.loads((root/'docs/research/p63c0_trace_audit.json').read_text(encoding='utf-8'))
        cases=audit['cases'];self.assertEqual(set(cases),{'M1','M2','M3','M4','M5','M6','C1','PHS-2D','P3'})
        inventory=capability_inventory()
        for key,row in cases.items():
            trace=json.loads((root/row['trace']).read_text(encoding='utf-8'))
            self.assertEqual(trace['entry_id'],row['entry_id'])
            self.assertFalse(row['main_autonomous'])
            self.assertTrue(row['evidence_checks'])
            self.assertTrue(row['method_ids'])
            self.assertLessEqual(set(row['method_ids']),set(inventory))
            self.assertTrue(row['decision_use']);self.assertTrue(row['diagnostic_only'])
        self.assertEqual(cases['M3']['acceptance_level'],'development_draft')
        self.assertEqual(cases['PHS-2D']['acceptance_level'],'development_numerical_witness_no_formal_select')
        self.assertIn('4-cell INVALID',cases['P3']['acceptance_level'])


if __name__=='__main__':unittest.main()
