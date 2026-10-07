"""Engineering fixtures through native decoding, research.decide and next input."""
from copy import deepcopy
import gc
import json
from pathlib import Path
import shutil
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from examples import research_model_v1 as pilot
from tools.state_io import read
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.platform_store import plain
from schemas.platform import ModelResponse,SessionInput
from tools.platform_tools import _candidate
from tools.candidate_parameters import fixed_configuration,actual_parameter_changes


class NativePilotTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=pilot.ROOT/'runs'/('native-test-'+uuid4().hex)
        cls.w=pilot.prepare(cls.root,offline_fixture=True)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        assert cls.root.resolve().is_relative_to((pilot.ROOT/'runs').resolve())
        shutil.rmtree(cls.root)

    def setUp(self):
        self.w=pilot.restore(self.root)
        # Synthetic capacity advertisement only; the Host grant stays zero-live.
        self.w.working=None
        self.patches=[patch('tools.research_scheduler.downstream_available',return_value=pilot.LIMITS),
            patch('tools.batch_budget.downstream_available',return_value=pilot.LIMITS)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.packet=pilot.configure(self.w)
        self.alias=next(iter(self.packet['current_feedback']['aliases']))

    def search(self,mixed=False,coordinate=False):
        p=deepcopy(read(pilot.reusable.continuation.RUN/'adaptation_plan.json')['plan'])
        paths={'design/near_section_scale':[.95,1.05]};point={'design/near_section_scale':.96}
        if mixed:
            paths['control/recipe/holding_tip_speed_weight']=[.025,.1]
            point['control/recipe/holding_tip_speed_weight']=.075
        p.update(source_candidate=self.w.freeze['incumbent'],predecessor_decision=self.w.previous_decision,
            variables=paths,evidence=[self.alias],candidates=None if coordinate else [point],
            method='search.family_coordinate@1.0.0' if coordinate else 'search.family_explicit@1.0.0',
            step=.25 if coordinate else None,max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,
            planned_budget=dict(model_calls=5,tool_calls=9,backend_solves=1,worker_calls=0,wall_s=1595.))
        return dict(action='structure_search',evidence=[self.alias],reasoning='Synthetic engineering fixture only.',plan=p,
            observations=[dict(evidence=self.alias,value=self.packet['current_feedback']['aliases'][self.alias]['value'])],
            interpretations=[],unresolved_uncertainties=['No scientific inference from this fixture'])

    def invoke_native(self,args):
        adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        native=next(n for n,t in adapter.advertised.items() if t=='research.decide')
        response=ModelResponse(raw=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[dict(
            id='engineering-fixture',type='function',function=dict(name=native,arguments=json.dumps(args)))]))]))
        binding=self.w.store.session(self.w.host.run_id)['snapshot']['input']['policy']['tool_bindings']
        call=adapter.decode(response,0,binding,payload['tools']);call['request_id']='engineering-'+uuid4().hex;call['cache']='new'
        self.w.host.resume();receipt=self.w.host.invoke(call)
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        state=self.w.store.session(self.w.host.run_id)['state']
        return self.w.store.artifact(state['handoffs']['research_decision']),payload

    def test_per_segment_variable_advertised_and_native_accepted(self):
        result,payload=self.invoke_native(self.search())
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertIn('design/near_section_scale',packet['capabilities']['legal']['structure_search']['paths'])
        self.assertEqual(len(packet['study']['parameter_catalog']['usable_pool']),8)
        self.assertEqual(result['batch_plan']['actual_differences'][0]['actual_changes'][0]['after'],.96)

    def test_mixed_joint_methods_and_frozen_construction(self):
        for coordinate in (False,True):
            pilot.configure(self.w)
            result,_=self.invoke_native(self.search(mixed=True,coordinate=coordinate))
            self.assertIn('joint structural/control subset',result['capabilities']['legal']['structure_search']['mixed_semantics'])
            record=result['batch_plan'];source=self.w.store.artifact(record['bindings']['execution_source_configuration'])['effective']
            changed=plain(_candidate(SessionInput.model_validate(source),self.search(mixed=True)['plan']['candidates'][0],self.w.host.reg))
            variables=record['plan']['variables']
            self.assertEqual(fixed_configuration(changed,variables),fixed_configuration(source,variables))
            self.assertEqual({r['path'] for r in actual_parameter_changes(source,changed,variables)},set(variables))
            self.assertEqual(changed['task'],source['task'])
            self.assertEqual(changed['policy']['controller']['version'],'7.0.0')
            self.assertEqual(changed['policy']['backend'],source['policy']['backend'])

    def test_reach_pass_hold_fail_in_feedback_and_actual_next_request(self):
        actual=self.w.freeze['subsequent_event']['acceptance']
        self.assertFalse(actual['accepted']);self.assertEqual(actual['status'],'valid_failure')
        self.assertTrue(actual['components']['task_evaluator']['passed'])
        self.assertFalse(actual['components']['holding_speed']['passed'])
        pilot.reusable.feedback(self.w,dict(status='completed',outcomes=[dict(candidate=self.w.freeze['subsequent_event']['facts']['candidate'],acceptance=actual,
            metrics=actual['metrics'])],classification='Engineering fixture wrapping preserved actual evidence'), 'engineering_feedback_fixture')
        self.packet=pilot.configure(self.w)
        adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        pilot.adopt_current_working(self.w)
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        aliases=packet['current_feedback']['aliases']
        self.assertTrue(any(r['pointer'].endswith('/acceptance/accepted') and r['value'] is False for r in aliases.values()))
        self.assertTrue(any(r['pointer'].endswith('/holding_speed/passed') and r['value'] is False for r in aliases.values()))
        self.assertTrue(any(r['value']==.06758272073425946 for r in aliases.values()))
        self.assertIn('recovery',packet['working_context'])
        self.assertEqual(adapter.context_assembly_audit['working_revision'],self.w.working['revision'])
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],0)
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)

    def test_joint_comparison_survives_actual_next_request(self):
        from copy import deepcopy
        from tools.research_tasks import compare_acceptance
        source=self.w.records[0]
        failed=deepcopy(source['acceptance'])
        failed['accepted']=False
        failed['status']='valid_failure'
        failed['metrics']['holding_max_speed_m_s']=.03
        failed['components']['holding_speed'].update(value=.03,passed=False)
        comparison=compare_acceptance(failed,source['acceptance'])
        pilot.reusable.feedback(self.w,dict(status='completed',source=source['facts']['candidate'],
            outcomes=[dict(candidate=source['facts']['candidate'],acceptance=failed,
                source_comparison=comparison,baseline_comparison=comparison)],
            classification='Synthetic engineering feedback; zero executions'), 'engineering_joint_comparison')
        pilot.configure(self.w)
        payload=payload_for(self.w.host,EvidenceDrivenAdapter())
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        bound=packet['current_feedback']['content']['comparison_bindings'][0]['comparisons']
        for kind in ('source_comparison','baseline_comparison'):
            self.assertEqual(bound[kind]['classification'],'worse')
            self.assertEqual(bound[kind]['baseline_execution_id'],source['execution_id'])
            self.assertEqual(bound[kind]['candidate_execution_id'],source['execution_id'])
        pilot.reusable.feedback(self.w,dict(status='model_stopped'), 'engineering_later_feedback')
        pilot.configure(self.w)
        payload_for(self.w.host,EvidenceDrivenAdapter())
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)
