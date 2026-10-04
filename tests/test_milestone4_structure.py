"""Structural domains, absolute semantics, shared plan/build path and stale bindings."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from examples import milestone4 as campaign
from tools.state_io import read,digest
from tools.platform_store import Store,plain
from tools.platform_tools import _candidate
from tools.platform_registry import registry
from tools.candidate_parameters import parameter_value,fixed_configuration,comparison_scope
from tools.structural_study import structural_input
from schemas.platform import SessionInput
from extensions.tendon_family.optimization import batch_search

PROFILE=campaign.ROOT/'extensions/tendon_family/profiles/milestone4_reach_experiment_v1.json'


class StructuralParameterTests(TestCase):
    @classmethod
    def setUpClass(cls):
        execution=read(campaign.RUN/'control_batch_result.json')['candidates'][0]['execution']
        cls.archived=Store(campaign.RUN).artifact(execution['configuration'])['effective']
        cls.source=structural_input(cls.archived,read(PROFILE));cls.reg=registry()

    def build(self,changes,source=None):return plain(_candidate(SessionInput.model_validate(source or self.source),changes,self.reg))

    def test_one_length_fixed_fields_and_candidate_initialization(self):
        changed=self.build({'components/near/length_m':.16})
        self.assertEqual(parameter_value(changed,'components/near/length_m'),.16)
        self.assertEqual(parameter_value(changed,'components/far/length_m'),.11)
        self.assertEqual(fixed_configuration(self.source,['components/near/length_m']),fixed_configuration(changed,['components/near/length_m']))
        self.assertEqual(changed['task'],self.source['task'])
        self.assertEqual(changed['policy']['controller'],self.source['policy']['controller'])
        from extensions.tendon_family.gvs_profile import candidate_numerical,checked_reach,load_profile,execution_scope
        inp=SessionInput.model_validate(changed);numerical=candidate_numerical(inp,checked_reach(inp),load_profile())
        self.assertFalse(numerical['provenance']['historical_states_reused'])
        self.assertFalse(numerical['provenance']['nominal_is_current_target_solution'])
        self.assertEqual(numerical['provenance']['current_scope'],execution_scope(changed))
        self.assertNotEqual(execution_scope(changed),execution_scope(self.source))
        self.assertEqual(comparison_scope(changed),comparison_scope(self.source))
        bad=deepcopy(changed);bad['robot']['structure']['data']['tendons'][0]['force_limit_n']=9.
        self.assertNotEqual(comparison_scope(bad),comparison_scope(self.source))

    def test_scale_material_absolute_source_and_unchanged_fields(self):
        first=self.build({'design/section_scale':1.01,'design/material_scenario':'stiff'})
        second=self.build({'design/section_scale':.97,'design/material_scenario':'compliant'},first)
        near=next(c for c in second['robot']['structure']['data']['components'] if c['id']=='near')
        self.assertAlmostEqual(near['sections'][0]['section']['parameters']['semi_y_m'],.01*.97)
        self.assertAlmostEqual(near['physics']['young_pa'],8e6*.9)
        self.assertEqual(near['length_m'],.15)
        self.assertEqual(second['policy']['candidate_builder']['parameters']['data']['semantic_source'],self.source['policy']['candidate_builder']['parameters']['data']['semantic_source'])
        self.assertEqual(parameter_value(second,'design/material_scenario'),'compliant')
        self.assertEqual(fixed_configuration(first,['design/section_scale','design/material_scenario']),fixed_configuration(second,['design/section_scale','design/material_scenario']))
        self.assertEqual(self.build({})['robot'],self.source['robot'])

    def test_discrete_finite_search_and_numeric_archives(self):
        method='search.family_explicit@1.0.0';path='design/material_scenario'
        parameters=dict(initial={path:'compliant'},bounds={path:dict(kind='discrete',choices=['baseline','compliant','stiff'])},
            candidates=[{path:'stiff'},{path:'baseline'}])
        a=batch_search(method,parameters);self.assertEqual(a.propose(),{path:'stiff'});a.feedback(1.)
        b=batch_search(method,parameters);b.restore(a.save().data);self.assertEqual(b.propose(),{path:'baseline'})
        with self.assertRaises(Exception):batch_search('search.family_coordinate@1.0.0',{**parameters,'max_trials':2,'step':.5})
        numeric=batch_search(method,dict(initial={'x':.05},bounds={'x':[0.,1.]},candidates=[{'x':.1}]))
        self.assertEqual(numeric.propose(),{'x':.1})


class StructuralBatchTests(TestCase):
    def test_plan_projection_preparation_ownership_and_stale_profile_rejection(self):
        from tests.test_stage356_batch import offline_directory
        with offline_directory() as tmp:
            with patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')),patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=AssertionError('OFFLINE')):
                w=campaign.prepare(Path(tmp)/'shared')
                host=w.host('design');current=w.store.session(host.run_id)['snapshot']['input']
                host=campaign.migrate_planning_host(w,'structural-offline',input_override=structural_input(current,read(PROFILE)))
                granted=w.store.session(host.run_id)['snapshot']['input']['policy']['candidate_builder']['parameters']['data']['control_parameters']
                self.assertIn('control/recipe/holding_tip_speed_weight',granted)
                self.assertIn('control/recipe/terminal_tip_speed_weight',granted)
                source=w.historical_results[-2]['facts'];original_bytes=w.store.artifact(source['configuration'],raw=True)
                def submit_fixture(h):
                    from tools.working_state import project_working_state
                    from tools.platform_search import validate_batch_plan
                    packet=campaign.planning_packet(w,1);args=deepcopy(read(campaign.prior.RUN/'search_plan.json')['plan'])
                    args.update(source_candidate=source['candidate'],predecessor_decision=w.predecessor_decision,
                        evidence=packet['evidence_aliases']['performed_check_result'],variables={'components/near/length_m':dict(kind='continuous',bounds=[.15,.17])},
                        candidates=[{'components/near/length_m':.16}],step=None,max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,
                        planned_budget=dict(model_calls=8,tool_calls=20,backend_solves=1,worker_calls=0,wall_s=2500.))
                    valid=validate_batch_plan(w.store,project_working_state(w.store,h.run_id),args)
                    self.assertEqual(valid['actual_differences'][0]['actual_changes'],[dict(path='components/near/length_m',before=.15,after=.16)])
                    self.assertEqual(valid['cost_floor_per_candidate_s']['apply'],5.)
                    h.resume();receipt=h.invoke(dict(request_id='offline-structural-plan',tool_id='design.submit_search_plan',tool_version='1.0.0',arguments=args,reason='Explicit offline fixture',cache='new'))
                    self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
                with patch('tools.diagnostic_workflow.run_loop',side_effect=submit_fixture):record=campaign.plan(w,'structure',1,campaign.COMMON_PLAN)
                from tools.platform_diagnosis_coordinator import configure_role
                from tools.platform_search import prepare_offline_batch,run_live_batch
                configure_role(host,'executor','Offline apply-only fixture.',phase_budget={});host.resume()
                prepare_offline_batch(host,w.chain['search_plan'],mode='live',starting_facts=source,retained_baseline=w.retained_baseline,historical_results=w.historical_results)
                result=run_live_batch(host,stop_after_stage='apply');pending=result['pending']
                self.assertEqual(w.store.remaining()['used']['backend_solves'],0)
                self.assertEqual(w.store.remaining()['used']['model_calls'],0)
                self.assertEqual(w.store.artifact(source['configuration'],raw=True),original_bytes)
                prepared=w.store.artifact(pending['configuration'])
                self.assertEqual(prepared['content_identity'],digest(prepared['effective']))
                self.assertEqual(prepared['candidate_id'],pending['candidate_id'])
                self.assertNotEqual(pending['configuration'],source['configuration'])
                from tools.live_batch_execution import LiveBatchExecution
                with patch('tools.live_batch_execution.complete_execution',return_value=dict(status='evaluated',configuration=source['configuration'])):
                    with self.assertRaisesRegex(ValueError,'CONFIGURATION_MISMATCH'):LiveBatchExecution(host).facts(pending)
