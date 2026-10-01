"""Focused candidate-analysis composition checks; no provider, backend or worker work."""
import json
from pathlib import Path
import unittest
from uuid import uuid4

from extensions.tendon_family.route import check_run_eligibility,create
from schemas.platform_analysis import EndpointTarget,TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_store import Store,encode,plain


SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923/resolved_frozen_input.json')
TOOLS={'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'2.0.0',
    'analysis.prepare_candidate':'1.0.0','analysis.linearize_candidate':'1.0.0',
    'analysis.control_metrics':'2.0.0','analysis.bounded_endpoint':'1.0.0','design.screen':'1.0.0'}


class CandidateAnalysisBundleTests(unittest.TestCase):
    def setUp(self):
        self.root=Path('runs/stage339_candidate_analysis_tests')/uuid4().hex
        self.store=Store(self.root);budget=dict(tool_calls=20,model_calls=0,backend_solves=0,worker_calls=0,wall_s=300.)
        self.store.create(dict(project_id='stage339-analysis-test',grant_id=uuid4().hex,
            authorization_source='Focused offline candidate-analysis verification.',budget=budget))
        inp=json.loads(SOURCE.read_text(encoding='utf8'));inp['run_id']='stage339-test-'+uuid4().hex
        task=inp['task'];control=inp['policy']['controller']['parameters']['data']
        protocol=TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},
            duration_s=task['timing']['duration_s'],period_s=task['timing']['control_period_s'],
            frequency_rad_s=[.1,1.,10.],samples_s=[])
        target=EndpointTarget(position_m=tuple(task['goal']['data']['target_m']),
            position_tolerance_m=task['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
            tip_speed_limit_m_s=control['settling']['speed_limit_m_s'],
            tip_velocity_scale_m_s=control['settling']['speed_limit_m_s'])
        with self.store.transaction() as db:
            pref=plain(self.store.put(db,protocol));tref=plain(self.store.put(db,target))
        inp['policy'].update(budget=budget,timeout_s=120.,allowed_tools=[],tool_bindings=TOOLS)
        inp['policy']['route']['data'].update(historical_case=None,historical_math=None,analysis_protocol=pref,
            endpoint_target=tref,analysis_required_before_run=True,math_selection_required_before_run=False,
            math_evaluation_limit=0,max_trials=1)
        create(self.root,inp);self.host=Host(self.root,inp['run_id'])

    def call(self,request_id,tool,arguments,cache='reuse'):
        return self.host.invoke(dict(request_id=request_id,tool_id=tool,tool_version=TOOLS[tool],
            arguments=arguments,reason='Focused candidate-analysis verification.',cache=cache))

    def build(self,node_id,changes,evidence):
        receipt=self.call('build-'+node_id,'route.advance',dict(node_id=node_id,action='build',
            combination='candidate_gvs_nmpc',changes=changes,variables={},max_trials=1,source_node=None,
            candidate_id=node_id,evidence=evidence,reason='Construct an ordinary covered candidate.',
            next_step='Prepare and register its candidate analysis.',design_statement=None,result_statement=None))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        detail=self.store.artifact(receipt['output'])['detail']
        return detail['result']

    def test_complete_bundle_registers_reuses_and_foreign_bundle_is_actionable(self):
        first_build=self.build('ordinary-a',{'components/near/length_m':.165,
            'components/far/length_m':.125,'design/section_scale':1.01,
            'design/material_scenario':'compliant'},[])
        prepared=self.call('prepare-a','analysis.prepare_candidate',dict(source_node='ordinary-a'))
        self.assertEqual(prepared['execution_status'],'completed',prepared)
        bundle=self.store.artifact(prepared['output'])
        self.assertTrue(bundle['complete'],bundle)
        self.assertEqual(set(bundle['components']),{'linearization','metrics','endpoint','screen'})
        self.assertTrue(all(row['status']=='computed' for row in bundle['components'].values()))
        status=next(row for row in self.host.context()['route']['candidate_analysis_status']
            if row['source_node']=='ordinary-a')
        self.assertEqual(status['bundle'],prepared['output'])
        self.assertTrue(all(row['state']=='available_unattached' for row in status['components'].values()))
        self.assertFalse(status['run_prerequisites']['satisfied'])
        self.assertIn('analysis.prepare_candidate',status['run_prerequisites']['required_next_step'])
        repeated=self.call('prepare-a-repeat','analysis.prepare_candidate',dict(source_node='ordinary-a'))
        self.assertEqual(repeated['execution_status'],'completed',repeated)
        self.assertFalse(repeated['cache_hit'])
        repeated_bundle=self.store.artifact(repeated['output'])
        self.assertTrue(all(row['status']=='reused' for row in repeated_bundle['components'].values()))
        self.assertEqual({name:row['reference'] for name,row in repeated_bundle['components'].items()},
            {name:row['reference'] for name,row in bundle['components'].items()})
        report=self.call('report-a','route.record_analysis',dict(node_id='report-a',source_node='ordinary-a',
            evidence=[first_build],candidate_analysis_bundle=prepared['output'],
            validation_disposition='recommended',reason='The exact bundle is complete and advisory.',
            next_step='Check the existing run gate without executing.'))
        self.assertEqual(report['execution_status'],'completed',report)
        report_detail=self.store.artifact(report['output'])['detail']
        registered=self.store.artifact(report_detail['result'])
        self.assertEqual(registered['candidate_analysis_bundle'],prepared['output'])
        self.assertTrue(check_run_eligibility(self.host,'ordinary-a')['eligible'])
        attached=next(row for row in self.host.context()['route']['candidate_analysis_status']
            if row['source_node']=='ordinary-a')
        self.assertTrue(all(row['state']=='available_attached' for row in attached['components'].values()))
        self.assertTrue(attached['run_prerequisites']['satisfied'])
        self.assertLess(len(encode(attached).encode('utf8')),3500)

        second_build=self.build('ordinary-b',{'components/near/length_m':.166,
            'components/far/length_m':.126,'design/section_scale':1.02,
            'design/material_scenario':'stiff'},[report_detail['result']])
        rejected=self.call('report-b-foreign','route.record_analysis',dict(node_id='report-b',
            source_node='ordinary-b',evidence=[second_build],candidate_analysis_bundle=prepared['output'],
            validation_disposition='recommended',reason='Deliberately submit another candidate bundle.',
            next_step='Reject without backend execution.'))
        self.assertEqual(rejected['execution_status'],'failed',rejected)
        self.assertIn('BUNDLE_BUILD_OR_SCOPE_MISMATCH',rejected['error'])
        self.assertIn("candidate='ordinary-b'",rejected['error'])
        used=self.store.remaining(self.host.run_id)['used']
        self.assertEqual(used['backend_solves'],0);self.assertEqual(used['model_calls'],0);self.assertEqual(used['worker_calls'],0)


if __name__=='__main__':unittest.main()
