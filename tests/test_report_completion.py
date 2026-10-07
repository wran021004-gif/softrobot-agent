"""Targeted source-binding checks using the original completed verification."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from tools.state_io import read,digest
from tools.bound_reporting import authoritative_metrics
from tools.study_history import reporting_scientific_scope

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/research_native_development_v3_20261007/structural_continuation_20261007'

class CanonicalReportTests(TestCase):
    def setUp(self):
        self.record=read(OLD/'verification.json')['groups'][0]['records'][0]
        def resolve(ref):return read(OLD/'store/artifacts'/f'{ref["artifact_id"]}.json')
        self.resolve=resolve;r=self.record;p=resolve(r['profile'])['detail'];cfg=resolve(r['configuration'])['effective']
        self.row=dict(execution_id=r['receipt']['execution_id'],sources=dict(evaluation=r['evaluation'],profile=r['profile']),
            structure_identity=digest(cfg['robot']),scientific_configuration_identity=digest(reporting_scientific_scope(cfg)),
            legacy_metrics=dict(terminal_error_m=p['terminal_error_m'],holding_max_error_m=p['sampled_settling']['max_error_m'],holding_max_speed_m_s=p['sampled_settling']['max_speed_m_s']))

    def test_exact_source_value_supersedes_legacy_without_mutation(self):
        before=deepcopy(self.row);out=authoritative_metrics(self.row,self.resolve)
        terminal=next(f for f in out['facts'].values() if f['metric']=='terminal_error_m')
        self.assertEqual(terminal['value'],self.resolve(self.record['evaluation'])['metrics'][0]['value'])
        self.assertNotEqual(terminal['value'],self.row['legacy_metrics']['terminal_error_m'])
        self.assertEqual(terminal['source_pointer'],'/metrics/0/value')
        self.assertEqual(self.row,before)
        self.assertIn('f_96edaddd1d3309826302',[s['legacy_fact_id'] for s in out['supersessions']])

    def test_foreign_execution_equal_value_is_rejected(self):
        def wrong(ref):
            v=self.resolve(ref)
            if ref==self.record['evaluation']:v['source_execution_id']='foreign'
            return v
        with self.assertRaisesRegex(ValueError,'CROSS_EXECUTION_SOURCE'):authoritative_metrics(self.row,wrong)

    def test_same_execution_wrong_profile_evaluation_source_rejected(self):
        def wrong(ref):
            v=self.resolve(ref)
            if ref==self.record['profile']:v['detail']['evaluation']=self.record['profile']
            return v
        with self.assertRaisesRegex(ValueError,'CROSS_EXECUTION_SOURCE'):authoritative_metrics(self.row,wrong)

    def test_wrong_units_and_definition_are_rejected(self):
        for key,bad in [('units','N'),('name','tip_speed')]:
            def wrong(ref):
                v=self.resolve(ref)
                if ref==self.record['evaluation']:v['metrics'][0][key]=bad
                return v
            with self.assertRaisesRegex(ValueError,'WRONG_METRIC'):authoritative_metrics(self.row,wrong)
