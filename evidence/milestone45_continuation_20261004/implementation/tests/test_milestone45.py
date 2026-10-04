"""Focused continuation projection and candidate-bound numerical pilot checks."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from tools.state_io import read,digest
from tools.platform_store import Store
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from examples import milestone45_continuation as run
from examples import milestone4 as prior
from extensions.tendon_family.gvs_profile import execution_scope
from tools.structural_study import research_planning_input


class ContinuationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory(prefix='m45-check-',dir=run.ROOT/'runs')
        cls.old_usage=Store(run.ORIGINAL).remaining()
        with patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')):
            cls.w=run.prepare(Path(cls.tmp.name)/'single_context')

    @classmethod
    def tearDownClass(cls):
        import gc
        gc.collect();cls.tmp.cleanup()

    def test_remaining_grant_and_completed_source_are_imported(self):
        w=self.w
        self.assertEqual(w.limits,run.allocation(self.old_usage))
        self.assertEqual(len(w.historical_results),7)
        self.assertEqual(w.latest_tested['execution_id'],run.CONTROL_EXECUTION)
        self.assertEqual(Store(run.ORIGINAL).remaining(),self.old_usage)
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)
        self.assertEqual(run.combined(w)['combined']['backend_solves'],1)
        self.assertEqual(w.store.session(w.host('design').run_id)['state'].get('protocol_corrections_used',0),0)
        self.assertEqual(w.freeze['authorization_link']['old_corrections'],4)

    def test_serialized_structure_final_and_adaptation_handoffs(self):
        w=self.w
        def inspect(host):
            w.check_provider_payload(host)
            adapter=EvidenceDrivenAdapter();payload=payload_for(host,adapter)
            expected='design.submit_search_plan' if adapter.phase=='improvement' else 'design.respond_diagnosis'
            rows=[t for t in payload['tools'] if adapter.advertised[t['function']['name']]==expected]
            self.assertEqual(len(rows),1)
            self.assertTrue(rows[0]['function']['parameters'])
            raise RuntimeError('OFFLINE_SERIALIZED_HANDOFF')
        with patch('tools.diagnostic_workflow.run_loop',side_effect=inspect):
            with self.assertRaisesRegex(RuntimeError,'OFFLINE_SERIALIZED_HANDOFF'):prior.plan(w,'structure',1,prior.STRUCTURE_PLAN)
            w.current_stage='structure'
            with self.assertRaisesRegex(RuntimeError,'OFFLINE_SERIALIZED_HANDOFF'):
                w.phase('response_final','design_response','unused_final',decision_packet=dict(scope='offline'),
                    improvement_feedback_content=dict(baseline_facts=w.retained_baseline,execution=None),check_feedback=[dict(reference=w.chain['feedback'])])
            child=Store(run.ORIGINAL).artifact(w.latest_tested['configuration'])['effective']
            from tools.platform_tools import _candidate
            from tools.platform_store import plain
            from schemas.platform import SessionInput
            granted=research_planning_input(child,read(run.PROFILE),budget=w.limits,
                model=w.freeze['provider_configuration'],tool_bindings=w.freeze['tool_bindings'])
            changed=plain(_candidate(SessionInput.model_validate(granted),{'components/far/length_m':.12},w.host('design').reg))
            # Concrete transition projection check: candidate-bound changed science,
            # execution-only administrative restrictions, no fabricated evaluation.
            changed['policy']['budget']['model_calls']=0
            changed['policy']['tool_bindings']=child['policy']['tool_bindings']
            projected=research_planning_input(changed,read(run.PROFILE),budget=w.limits,
                model=w.freeze['provider_configuration'],tool_bindings=w.freeze['tool_bindings'])
            self.assertEqual(execution_scope(projected),execution_scope(changed))
            self.assertGreater(projected['policy']['budget']['model_calls'],0)
            prior.migrate_planning_host(w,'offline-adaptation-projection',input_override=projected)
            with self.assertRaisesRegex(RuntimeError,'OFFLINE_SERIALIZED_HANDOFF'):prior.plan(w,'adaptation',2,prior.ADAPT_PLAN)
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)


class PilotPhysicalTests(TestCase):
    def test_sealed_execution_recovery_never_calls_executor(self):
        from types import SimpleNamespace
        sealed=dict(status='completed',fully_evaluated_distinct_changed_configurations=1,candidates=[])
        from contextlib import nullcontext
        store=SimpleNamespace(artifact=lambda ref:sealed,connect=lambda *a:nullcontext(SimpleNamespace(execute=lambda sql:[])))
        candidate=dict(candidate_id='source')
        w=SimpleNamespace(store=store,chain=dict(batch_result={}),historical_results=[dict(facts=dict(candidate=candidate))],host=lambda role:None)
        record=dict(bindings=dict(subject=candidate),plan=dict(target_changed_configurations=1))
        # Stop at summary construction; preceding execution and preparation must
        # be bypassed while the exact sealed result is checked.
        with (patch.object(prior,'atomic_json'),patch.object(prior,'run_live_batch',side_effect=AssertionError('BACKEND_REPLAY')),
            patch.object(prior,'prepare_offline_batch',side_effect=AssertionError('BATCH_REPREPARATION')),
            patch.object(prior.prior.previous,'compact_summary',side_effect=RuntimeError('SUMMARY_REACHED'))):
            w.directory=Path('.')
            with self.assertRaisesRegex(RuntimeError,'SUMMARY_REACHED'):prior.execute(w,'structure',record,sealed_result=sealed)

    def test_weight_specific_commands_drive_prospective_rollouts(self):
        from types import SimpleNamespace
        import numpy as np
        from extensions.tendon_family import milestone5_preview as pilot
        base=Store(run.ORIGINAL).artifact(read(run.ORIGINAL/'control_batch_result.json')['candidates'][0]['execution']['configuration'])['effective']
        configurations=[];artifacts={};commands=[];charges=[]
        for i,weight in enumerate((.05,.1,.2)):
            cfg=deepcopy(base);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
            ref=dict(artifact_id=str(i),media_type='application/json');artifacts[str(i)]=dict(effective=cfg)
            configurations.append(dict(candidate_id=str(i),configuration=ref,scientific_identity=digest(execution_scope(cfg))))
        protocol=dict(classification='prospective_same_structure_control_pilot',snapshot=dict(measured_initial_state=[0.,0.],previous_input_n=[0.],effective_horizon=1,time_s=.34),
            configurations=configurations,limits=dict(max_wall_s=300),force_limits_n=[10.],integration_step_s=.002,horizon_s=.01)
        artifacts['protocol']=protocol
        class Workspace:
            def __init__(self,task,robot,parameters,*args,**kwargs):
                self.command=parameters['holding_tip_speed_weight'];self.problem=None
                self.solver=SimpleNamespace(evaluate_candidate=lambda *a:dict(feasible=True))
            def solve(self,*a,**kw):
                return dict(tensions=[[self.command]],states=[[0.,0.],[0.,0.]],result=dict(optimum={}),
                    diagnostics=dict(selected_feasible_iteration=1,policy_stop_reason='fixture'))
        class Model:
            def __init__(self,*a):pass
            def rollout(self,x,u,*a):
                commands.append(float(u[0]));speed=.1-float(u[0])/10
                return [dict(speed_m_s=.1),dict(speed_m_s=speed,displacement_m=.001,error_m=.008)]
        ctx=SimpleNamespace(artifact=lambda ref:artifacts[ref['artifact_id']],save_artifact=lambda *a:dict(artifact_id='saved',media_type='application/json'))
        with (patch.object(pilot,'TrajectoryWorkspace',Workspace),patch.object(pilot,'NonlinearModel',Model),patch.object(pilot,'plan_metrics',return_value={}),
            patch.object(pilot,'charge_units',side_effect=lambda ctx,kind,count:charges.append((kind,count)))):
            result=pilot.execute(ctx,SimpleNamespace(protocol=dict(artifact_id='protocol',media_type='application/json'))).detail
        self.assertEqual(commands,[.05,.1,.2])
        self.assertEqual(charges.count(('local_solves',1)),3)
        self.assertEqual(charges.count(('prediction_evaluations',1)),3)
        self.assertEqual(result['predicted_speed_order'],['2','1'])
        self.assertEqual(result['rows'][1]['full_task_hypothesis']['joint_acceptance'],'unknown')

    def test_direction_uses_physical_delta_and_abstains_for_ties(self):
        from extensions.tendon_family.milestone5_preview import physical_direction
        self.assertEqual(physical_direction(-.001),'improvement')
        self.assertEqual(physical_direction(.001),'worsening')
        self.assertEqual(physical_direction(1e-9),'unresolved')


class FinalRecoveryTests(TestCase):
    def test_actual_complete_payload_and_latest_receipt_identity_offline(self):
        import json
        w=run.restore();host=w.host('design');role=w.store.session(host.run_id)['state']['role_context']
        packet=role['decision_packet'];compact=run.compact_decision_packet(packet,role['decision_packet_reference'])
        self.assertEqual(compact['completed_results'],packet['completed_results'])
        for original,projected in zip(packet['history']['rows'],compact['history']['rows']):
            self.assertEqual(original['metrics'],projected['metrics']);self.assertEqual(original['decisions'],projected['decisions'])
        payload=payload_for(host,EvidenceDrivenAdapter());context=json.loads(payload['messages'][1]['content'])
        context['role_context']['decision_packet']=compact;payload['messages'][1]['content']=json.dumps(context)
        self.assertLess(len(json.dumps(payload).encode()),100000)
        with w.store.connect(True) as db:
            latest=db.execute("SELECT run_id FROM calls WHERE request_id='complete-profile' AND status='completed' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        self.assertEqual(w.latest_tested['owner_run_id'],latest)
        self.assertEqual(w.store.artifact(w.chain['pilot_forecast_seal']),read(run.RUN/'pilot_forecast_seal.json'))
