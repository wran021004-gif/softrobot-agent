"""Focused Stage 3.35 integration checks; no provider or backend traffic."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from extensions.tendon_family.candidate_analysis import scientific_configuration_identity
from extensions.tendon_family.route import create
from schemas.platform_analysis import AnalysisResult, EndpointTarget, TaskAnalysisProtocol
from tools.platform_host import Host
from tools.platform_models import DeepSeekAdapter, payload_for, provider_name
from tools.platform_store import Store, plain
from tools.runtime_identity import SOFTAGENT_PYTHON, require_softagent_runtime


SOURCE=Path('runs/stage333_bounded_recovery_independent_lengths_20260929_114923/resolved_frozen_input.json')
VARIABLES={'components/near/length_m':(.15,.17),'components/far/length_m':(.11,.13),
    'design/section_scale':(.95,1.05)}
VERSIONS={'route.advance':'1.0.0','route.inspect':'1.0.0','route.record_analysis':'1.0.0',
    'design.optimize_math':'1.0.0'}


class Stage335RouteTests(unittest.TestCase):
    def setup_route(self,limit=3):
        root=Path('runs/stage335_focused_tests')/uuid4().hex;store=Store(root)
        budget=dict(tool_calls=30,model_calls=0,backend_solves=0,worker_calls=0,wall_s=300.)
        store.create(dict(project_id='stage335-test',grant_id=uuid4().hex,
            authorization_source='Focused offline test.',budget=budget))
        inp=json.loads(SOURCE.read_text(encoding='utf8'));inp['run_id']='stage335-'+uuid4().hex
        p=TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},duration_s=inp['task']['timing']['duration_s'],
            period_s=inp['task']['timing']['control_period_s'],frequency_rad_s=[.1,1.,10.],samples_s=[])
        control=inp['policy']['controller']['parameters']['data']
        target=EndpointTarget(position_m=tuple(inp['task']['goal']['data']['target_m']),
            position_tolerance_m=inp['task']['evaluator']['parameters']['data']['tolerance_m'],position_scale_m=.01,
            tip_speed_limit_m_s=control['settling']['speed_limit_m_s'],
            tip_velocity_scale_m_s=control['settling']['speed_limit_m_s'])
        with store.transaction() as db: pref=plain(store.put(db,p));tref=plain(store.put(db,target))
        inp['policy'].update(budget=budget,timeout_s=30.,model=inp['policy']['model'],allowed_tools=[],tool_bindings=VERSIONS)
        inp['policy']['route']['data'].update(historical_case=None,analysis_protocol=pref,endpoint_target=tref,
            analysis_required_before_run=True,math_selection_required_before_run=True,math_evaluation_limit=limit)
        create(root,inp);host=Host(root,inp['run_id'])
        built=host.invoke(dict(request_id='seed',tool_id='route.advance',tool_version='1.0.0',reason='Seed build',
            arguments=dict(node_id='seed',action='build',combination='candidate_gvs_nmpc',candidate_id='seed',
                changes={},variables={},max_trials=1,evidence=[],reason='Seed build.',next_step='Optimize.')))
        self.assertEqual(built['execution_status'],'completed',built)
        return store,host,pref,tref

    @staticmethod
    def fake_linear(ctx,candidate,binding,p,protocol):
        from tests.test_task_analysis import model_for
        model=ctx.save_artifact(model_for(p),'fake_endpoint_model')
        return AnalysisResult(kind='candidate_linearization',protocol=protocol,bindings=[binding],records=[
            dict(point=dict(name='candidate_configuration'),available=True),
            dict(point=dict(name='controller_start_input'),available=True,model=plain(model))],
            evidence=[binding['configuration']],limitations=['Synthetic local model for accounting only.'])

    @staticmethod
    def fake_endpoint(model,p,target,**kwargs):
        return dict(question='position_only',status='feasible_in_local_model',sampled_horizon=dict(step_count=1),
            checks=dict(finite=True,lower_bounds=True,upper_bounds=True,position=True,speed=True),
            endpoint=dict(position_error_m=.001,tip_speed_m_s=0.),infeasibility_certificate=None,
            independent_residual_problems=dict(position=dict(candidate_residual=.001)),normalized_input_energy=1.)

    def optimizer_patches(self):
        return (patch('extensions.tendon_family.math_analysis.linearize_candidate_configuration',self.fake_linear),
            patch('extensions.math_analysis.kernels.bounded_endpoint',self.fake_endpoint),
            patch('extensions.math_analysis.kernels.endpoint_map',return_value={}),
            patch('extensions.math_analysis.kernels._output_endpoint',return_value=(None,None,np.zeros((3,2)))))

    def invoke_optimizer(self,host,pref,tref,request_id,max_evaluations):
        return host.invoke(dict(request_id=request_id,tool_id='design.optimize_math',tool_version='1.0.0',
            reason='Focused cumulative accounting.',arguments=dict(source_node='seed',protocol=pref,target=tref,
                variables=VARIABLES,material_scenarios=['compliant','stiff'],max_evaluations=max_evaluations,
                objective='controller_start_local_endpoint_lexicographic_v1')))

    def test_provider_payload_exposes_record_analysis_and_runtime_rejects_wrong_python(self):
        _,host,_,_=self.setup_route()
        tool=next(item['function'] for item in payload_for(host,DeepSeekAdapter())['tools']
            if item['function']['name']==provider_name('route.record_analysis'))
        self.assertTrue(tool['description'].startswith('route.record_analysis@1.0.0'))
        self.assertEqual(tool['parameters']['properties']['tool_version']['const'],'1.0.0')
        self.assertIn('selected_optimizer_candidate_id',tool['parameters']['properties']['arguments']['properties'])
        with self.assertRaisesRegex(RuntimeError,'SOFTAGENT_PYTHON_3_11_REQUIRED'):
            require_softagent_runtime(executable=SOFTAGENT_PYTHON,version_info=(3,14,0),
                prefix=SOFTAGENT_PYTHON.parent)

    def test_scientific_identity_ignores_run_label_but_not_frozen_science(self):
        value=json.loads(SOURCE.read_text(encoding='utf8'));other=deepcopy(value);other['run_id']='bookkeeping-only'
        self.assertEqual(scientific_configuration_identity(value),scientific_configuration_identity(other))
        changed=deepcopy(other);changed['task']['timing']['duration_s']+=.01
        self.assertNotEqual(scientific_configuration_identity(value),scientific_configuration_identity(changed))
        changed=deepcopy(other);changed['policy']['controller']['parameters']['data']['recipe']['horizon']+=1
        self.assertNotEqual(scientific_configuration_identity(value),scientific_configuration_identity(changed))

    def test_cumulative_budget_cache_original_proposal_linkage_and_altered_rejection(self):
        store,host,pref,tref=self.setup_route(limit=3);p1,p2,p3,p4=self.optimizer_patches()
        with p1,p2,p3,p4:
            first=self.invoke_optimizer(host,pref,tref,'opt-original',2)
            second=self.invoke_optimizer(host,pref,tref,'opt-repeat',3)
        self.assertEqual(first['execution_status'],'completed',first);self.assertEqual(second['execution_status'],'completed',second)
        original=store.artifact(first['output']);repeat=store.artifact(second['output'])
        self.assertEqual(repeat['provenance']['cumulative_evaluations_used'],3)
        self.assertEqual(repeat['provenance']['cumulative_evaluations_remaining'],0)
        self.assertGreaterEqual(repeat['provenance']['cache_hits_this_call'],2)
        proposal=original['proposals'][0];changes={**proposal['parameters'],'design/material_scenario':proposal['material_scenario']}
        seed_node=store.session(host.run_id)['state']['route']['nodes'][0]
        selected=host.invoke(dict(request_id='selected-build',tool_id='route.advance',tool_version='1.0.0',reason='Exact proposal',
            arguments=dict(node_id='selected',action='build',combination='candidate_gvs_nmpc',candidate_id='selected',
                changes=changes,variables={},max_trials=1,evidence=[seed_node['result']],reason='Exact proposal.',next_step='Report.')))
        self.assertEqual(selected['execution_status'],'completed',selected)
        selected_node=store.session(host.run_id)['state']['route']['nodes'][-1];built=store.artifact(selected_node['result'])
        def analysis_refs(configuration,candidate):
            binding=dict(configuration=configuration,candidate_id=candidate)
            with store.transaction() as db:
                linear=plain(store.put(db,dict(kind='candidate_linearization',protocol=pref,bindings=[binding],records=[],evidence=[])))
                metrics=plain(store.put(db,dict(kind='control_metrics',protocol=pref,bindings=[binding],records=[],evidence=[])))
                endpoint=plain(store.put(db,dict(kind='bounded_endpoint',protocol=pref,bindings=[binding],records=[],evidence=[tref])))
                screen=plain(store.put(db,dict(kind='design_screen',protocol=pref,bindings=[binding],
                    records=[dict(priority_reasoning=dict(priority='advisory'))],evidence=[linear,metrics,endpoint])))
            return linear,metrics,endpoint,screen
        linear,metrics,endpoint,screen=analysis_refs(built['configuration'],'selected')
        report=host.invoke(dict(request_id='selected-report',tool_id='route.record_analysis',tool_version='1.0.0',
            reason='Bind original proposal.',arguments=dict(node_id='selected-report',source_node='selected',
                evidence=[selected_node['result'],first['output']],linearization=linear,metrics=metrics,endpoint=endpoint,
                screen=screen,math_optimization=first['output'],selected_optimizer_candidate_id=proposal['candidate_id'],
                validation_disposition='recommended',reason='Advisory only.',next_step='Gate.')))
        self.assertEqual(report['execution_status'],'completed',report)
        trace=store.artifact(report['output'])['detail']['summary']['math_selection_trace']
        self.assertTrue(trace['matches_proposal']);self.assertEqual(trace['optimizer_starting_build'],
            original['starting_binding']['configuration'])
        altered=host.invoke(dict(request_id='altered-build',tool_id='route.advance',tool_version='1.0.0',reason='Altered build',
            arguments=dict(node_id='altered',action='build',combination='candidate_gvs_nmpc',candidate_id='altered',
                changes={**changes,'components/near/length_m':.17 if changes['components/near/length_m']!=.17 else .15},
                variables={},max_trials=1,evidence=[selected_node['result']],reason='Deliberately altered.',next_step='Reject linkage.')))
        self.assertEqual(altered['execution_status'],'completed',altered)
        altered_node=store.session(host.run_id)['state']['route']['nodes'][-1];altered_out=store.artifact(altered_node['result'])
        linear,metrics,endpoint,screen=analysis_refs(altered_out['configuration'],'altered')
        rejected=host.invoke(dict(request_id='altered-report',tool_id='route.record_analysis',tool_version='1.0.0',
            reason='Reject altered proposal.',arguments=dict(node_id='altered-report',source_node='altered',
                evidence=[altered_node['result'],first['output']],linearization=linear,metrics=metrics,endpoint=endpoint,
                screen=screen,math_optimization=first['output'],selected_optimizer_candidate_id=proposal['candidate_id'],
                validation_disposition='recommended',reason='Must reject.',next_step='Stop.')))
        self.assertEqual(rejected['execution_status'],'failed',rejected)
        self.assertIn('SCIENTIFIC_CONFIGURATION_MISMATCH',rejected['error'])
        self.assertEqual(store.remaining(host.run_id)['used']['backend_solves'],0)

    def test_failed_mathematical_attempt_consumes_cumulative_allowance(self):
        store,host,pref,tref=self.setup_route(limit=2)
        with patch('extensions.tendon_family.math_analysis.linearize_candidate_configuration',side_effect=RuntimeError('synthetic math failure')):
            receipt=self.invoke_optimizer(host,pref,tref,'opt-failure',2)
        self.assertEqual(receipt['execution_status'],'failed',receipt)
        ledger=store.session(host.run_id)['state']['route']['math_evaluations']
        self.assertEqual((ledger['used'],ledger['remaining']),(1,1))
        self.assertEqual(ledger['attempts'][0]['status'],'failed')


if __name__=='__main__': unittest.main()
