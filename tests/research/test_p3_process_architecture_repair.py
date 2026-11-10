"""Seven directed offline contracts. All numeric fixture responses are fabricated.
Historical tests read immutable artifacts; no Provider, integration or Replay.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
import json
import unittest
from jsonschema import Draft202012Validator
from tools.platform_store import Store,plain
from tools.state_io import digest
from schemas.platform import SessionInput,TaskDefinition,EvaluationResult
from tools.research.config import resolve
from tools.research.contracts import MechanismStudy,AnalysisRequest,FamilyMixedSearch,fidelity_levels
from tools.research.structure_research import prepare_context,calculate,reusable_execution,finite_time_discovery
from tools.research.design import family_configuration
from tools.research_tasks import task_adapter
from extensions.reference.contracts import PassiveResponseEvaluationV2,PassiveResponseGoalV2
from extensions.reference.passive_program import execution_scope,execution_identity,qualification
from extensions.reference.passive_evaluation_v2 import stiffness,metrics
from extensions.tendon_family.passive_execution import paired_raw,baseline_arm
from tests.research.test_p3_study_readiness import small_task as fixture_task,fixture
from contextlib import contextmanager
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/research/p3-process-architecture-repair-20261110'
DRAFT=ROOT/'configs/research/study_p3_passive_progressive_stiffness_architecture_v1_1.json'
P3=ROOT/'runs/research/p3-passive-progressive-stiffness-autonomous-20261109-01'


def small_task():
    value=plain(fixture_task())
    for stages in value['goal']['data']['programs'].values():
        for stage in stages:stage['ramp_until_s']=stage['start_s']+.0005
    return TaskDefinition.model_validate(value)


@contextmanager
def fixture_directory():
    path=ROOT/'runs'/('p3-reuse-contract-'+uuid4().hex);path.mkdir()
    yield path


def candidate(spec):
    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
        segment_count=2,tendon_count=2,segments={'0':dict(length_m=.025),'1':dict(length_m=.025)},
        payout_offsets_m={'tendon_0':.001,'tendon_1':.001})
    cfg,build,_=family_configuration(spec['configuration'],spec['family_space'],request,'offline-contract-fixture')
    return dict(configuration=cfg,parameters=plain(build.request),generation_version='serial_family_generation_v2',
        task_identity=spec['canonical_task_identity'],family_space_identity=spec['family_space_identity'])


def study(**edits):
    return MechanismStudy.model_validate(dict(dict(operation='inspect',point_semantics='frozen_task_initial_state',
        target=dict(quantity='finite_time_task_violation',goal='decrease'),effect_semantics='finite_time_task_response',
        max_evaluations=1),**edits))


class OfflineContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guards=[patch('mujoco.mj_step',side_effect=AssertionError('NEW_INTEGRATION_FORBIDDEN')),
            patch('httpx.Client.send',side_effect=AssertionError('PROVIDER_FORBIDDEN')),
            patch('httpx.AsyncClient.send',side_effect=AssertionError('PROVIDER_FORBIDDEN'))]
        for guard in cls.guards:guard.start()
        cls.spec=resolve(DRAFT);cls.c=candidate(cls.spec)

    @classmethod
    def tearDownClass(cls):
        for guard in cls.guards:guard.stop()

    def test_1_independent_measurements_and_tendon_predicates(self):
        task=small_task();raw=fixture(task);spec=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data).progressive_stiffness[0]
        # Deliberately unresolved stiffness, while tendon evidence remains present.
        for r in raw['episodes'][0]['qualification_samples']:
            if r['phase']=='middle':r['material_positions_m']=[[.007,0.,.5]]*len(task.physical_problem['monitor_s'])
            if r['phase']=='low':r['actual_tension_n'][0]=.1
            if r['phase']=='high':
                r['actual_tension_n'][1]=0.;r['constraint_active'][1]=False;r['length_residual_m'][1]=-.001
        value=stiffness(task,raw,spec)
        self.assertFalse(value['denominator_valid']);self.assertIsNone(value['stiffness_ratio'])
        self.assertEqual([t['classification'] for t in value['tendon_transitions']],['early_engagement','no_high_engagement'])
        measured=metrics(task,raw,check_confirmation=False,check_mechanism=False)
        self.assertTrue(measured['metrics']);self.assertFalse(measured['task_success']) if measured['validity']=='valid' else self.assertIsNone(measured['task_success'])
        gap=task_adapter(dict(task=plain(task))).diagnostic_task_gap(raw)
        rows={r['constraint_id']:r for r in gap['constraints']}
        self.assertEqual(rows['evaluator:plus_x_slack_to_taut']['observed_value'],0.)
        self.assertIsNone(rows['evaluator:plus_x_stiffness_ratio']['observed_value'])
        self.assertFalse(gap['comparable'])
        partial=deepcopy(raw);partial['episodes']=partial['episodes'][:1]
        missing=task_adapter(dict(task=plain(task))).diagnostic_task_gap(partial)
        self.assertEqual(missing['status'],'partial')
        self.assertTrue(any(r['measurement_status']=='UNKNOWN' for r in missing['constraints']))
        # A pre-v2 passive adapter also retains independent facts on a partial trajectory.
        legacy=resolve(ROOT/'configs/research/study_passive_engineering_v1.json')['configuration']
        legacy_task=SessionInput.model_validate(legacy).task;goal=legacy_task.goal.data
        case=goal['load_conditions'][0];times=[goal['unloaded_until_s'],goal['hold_window_s'][0],goal['hold_window_s'][1]]
        positions=[[0.,0.,0.5]]*len(legacy_task.physical_problem['monitor_s'])
        rows=[dict(time_s=t,material_positions_m=positions,tip_m=[.001,0.,.5],actual_tension_n=[.02],
            length_residual_m=[0.],material_velocities_m_s=[[0.,0.,0.]]*len(positions),tip_velocity_m_s=[0.,0.,0.],
            qpos_rad=[0.],qvel_rad_s=[0.]) for t in times]
        raw=dict(kind='passive_dynamic_execution_v1',active_actuators=0,joint_count=1,tendon_order=['fixture'],
            physical_binding=dict(task_identity=digest(plain(legacy_task)),model_identity='fixture',design_identity='fixture'),
            episodes=[dict(load_condition=case,complete=False,samples=rows,maximum_contacts=0,maximum_tension_n=.02,maximum_length_excess_m=0.)])
        from extensions.reference.passive_response import task_metrics
        measured=task_metrics(legacy_task,raw)
        self.assertTrue(measured['metrics']);self.assertIsNone(measured['task_success'])
        gap=task_adapter(legacy).diagnostic_task_gap(raw)
        self.assertTrue(gap['coverage']['measured']);self.assertFalse(gap['comparable'])


    def test_2_fidelity_schema_compiler_and_actual_search_admission(self):
        from tools.research.structure_intent import compile_search
        from tools.research.agent import plan_schema
        from tools.research.search import search_problem,rank
        spec=self.spec;host=SimpleNamespace(store=Mock())
        state=dict(spec=spec,profile=dict(identity='fixture'),base_configuration=spec['configuration'])
        query=dict(version='scientific_structure_search_v1',research_goal='passive_structure_research',
            design_variable_groups=['lengths'],evaluation_model='passive_task_response',control_treatment='no_active_control',
            structure_search_effort=dict(max_proposals=2,max_evaluations=2),proxy_objective='task_violation',
            segment_counts=[2],tendon_counts=[2],bounds={'length_m':[.025,.1]},
            execution_profile=dict(purpose='exploration',load_conditions=['plus_x'],stage_prefix='low'))
        plan=dict(action='search',hypothesis='Fixture baseline response',expected_observation='Fixture displacement',
            weakening_observation='Fixture no change',fixed_conditions='Frozen physics',stopping_condition='Finite request',
            interpretation='Offline only',decision=dict(hypothesis_id='fixture'))
        schema=plan_schema(['search'],decision_required=True,focused=True,study=spec)
        for name,level in fidelity_levels(spec['fidelity_policy']).items():
            submitted={**plan,'search':{**query,'screening_fidelity':name}}
            Draft202012Validator(schema).validate(submitted)
            with patch('tools.research.structure_intent.state',return_value=state),patch('tools.research.search.state',return_value=state),patch('tools.research.structure_intent.save'),patch('tools.research.analysis.admission',return_value=dict(admitted=2)):
                compiled=compile_search(host,submitted,'offline-compile')
                problem=search_problem(host,compiled['search'],2)
            self.assertEqual(problem['passive_problem']['action'],'baseline_response')
            self.assertEqual(compiled['search']['screening_fidelity'],name)
            # Exercise the real generated-search construction, where inherited cells used to conflict.
            from tools.research.mixed_moves import initial,generation
            from tools.research.design import generate_candidate
            from tools.platform_registry import registry
            host.run_id='offline-contract-fixture';host.reg=registry()
            local={**state,'profile':dict(identity='fixture',version=1),
                'candidates':{},'numerical_s':0.,'construction_numerical_s':0.}
            q=FamilyMixedSearch.model_validate(compiled['search'])
            generated_request=generation(spec['family_space'],q,initial(spec['family_space'],q))
            with patch('tools.research.design.state',return_value=local),patch('tools.research.design.update',side_effect=lambda host,**kwargs:local.update(kwargs)),patch('tools.research.design.save',return_value={'artifact_id':'a'*64}):
                built=generate_candidate(host,generated_request,dict(origin='offline_fixture'),screening_fidelity=name)
            self.assertEqual(built['status'],'generated')
            self.assertEqual(set(built['resolved']['discretization']['cells'].values()),{level['cells_per_segment']})

            row=dict(computation_status='computed',proxy_values={'task_violation':1.},comparison_scope=dict(
                fidelity=name,evaluation_mode='passive_task_response',execution_profile=plain(q.execution_profile),objective='task_violation'))
            q=FamilyMixedSearch.model_validate(compiled['search']);self.assertEqual(rank(row,q)[0],0)
            row['comparison_scope']['fidelity']='incompatible';self.assertEqual(rank(row,q)[0],1)
        self.assertEqual(spec['fidelity_policy']['final_evaluation']['cells_per_segment'],12)
        self.assertFalse(finite_time_discovery(self.c['configuration'])['paired_required'])

    def test_3_baseline_and_independent_pair_contract(self):
        baseline=prepare_context(self.spec,self.c,study(),[])
        self.assertEqual(baseline['dynamic_cost_bound']['episodes'],2)
        paired=prepare_context(self.spec,self.c,study(passive_ablation=['tendon_0']),[])
        self.assertEqual(paired['dynamic_cost_bound']['episodes'],4)
        task=small_task();raw=paired_raw(fixture(task),fixture(task,True),Path('fixture'),['tendon_0','tendon_1'],0.)
        result=metrics(task,raw,check_confirmation=False)
        self.assertEqual(result['validity'],'valid');self.assertFalse(result['task_success'])
        raw['paired_ablation']['ablation']['solver_options']['timestep_s']*=2
        result=metrics(task,raw,check_confirmation=False)
        self.assertEqual(result['validity'],'invalid');self.assertTrue(result['metrics'])
        self.assertFalse(any(c.name.endswith('paired_mechanism') for c in result['constraints']))

    def test_4_exploration_and_frozen_final_scope(self):
        task=SessionInput.model_validate(self.c['configuration']).task
        profile=dict(purpose='exploration',load_conditions=['plus_x'],stage_prefix='middle',route_sampling='score_grid',recording='sampled')
        scope=execution_scope(task,profile)
        self.assertEqual(scope['end_s'],{'plus_x':12.});self.assertEqual(scope['acceptance_status'],'not_evaluated')
        context=prepare_context(self.spec,self.c,study(execution_profile={**profile,'fidelity':'screening'}),[])
        self.assertEqual(context['dynamic_cost_bound']['physics_steps'],96000)
        self.assertEqual(set(context['execution_configuration']['policy']['discretization']['data']['cells'].values()),{2})
        with self.assertRaisesRegex(ValueError,'FINAL_ACCEPTANCE'):execution_scope(task,dict(purpose='final_acceptance',load_conditions=['plus_x']))
        final=execution_scope(task,dict(purpose='final_acceptance'))
        self.assertEqual(final['load_conditions'],['plus_x','minus_x']);self.assertEqual(final['recording'],'full_physics_csv')
        synthetic=fixture(small_task());synthetic['execution_profile']=execution_scope(small_task(),dict(purpose='exploration'))
        outcome=metrics(small_task(),synthetic,check_confirmation=False,check_mechanism=False)
        self.assertEqual(outcome['acceptance_status'],'not_evaluated');self.assertIsNone(outcome['task_success'])

    def test_5_exact_store_reuse_and_replay_exclusion(self):
        cfg=self.c['configuration'];identity=execution_identity(cfg)
        raw=dict(status='completed',episodes=[dict(complete=True)],execution_identity=identity,cost={'physics_steps':100})
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(dict(structure_research=dict(records=[dict(mechanics=dict(dynamic_execution=raw))]),physical_execution_index=[dict(identity=identity['identity'],pointer='/structure_research/records/0/mechanics/dynamic_execution')]))
            reused=reusable_execution(store,[ref],identity)
            self.assertEqual(reused['source']['reference'],ref);self.assertEqual(reused['actual_new_cost']['physics_steps'],0)
            for edits in (dict(initial_state={'state_identity':'different'}),dict(intervention=['tendon_0']),dict(profile={'purpose':'exploration','stage_prefix':'low'})):
                self.assertIsNone(reusable_execution(store,[ref],execution_identity(cfg,**edits)))
            other=deepcopy(cfg);other['policy']['discretization']['data']['cells']={'segment_0':2,'segment_1':2}
            self.assertIsNone(reusable_execution(store,[ref],execution_identity(other)))
            self.assertIsNone(reusable_execution(store,[ref],identity,independent_replay=True))
        from extensions.tendon_family.passive_execution import execute_pair
        cfg=deepcopy(cfg);cfg['task']=plain(small_task());inp=SessionInput.model_validate(cfg)
        base=fixture(inp.task);abl=fixture(inp.task,True)
        base['execution_identity']=execution_identity(cfg)
        abl['execution_identity']=execution_identity(cfg,intervention=['tendon_0','tendon_1'])
        def saved(raw):return dict(raw=raw,execution_directory=str(ROOT/'runs'/'synthetic-original-traces'),source=dict(reference={'artifact_id':'b'*64},pointer=''),actual_new_cost={'physics_steps':0})
        with fixture_directory() as folder,patch('extensions.tendon_family.passive_execution.physics_for',return_value={'tendons':[{'entity':'tendon_0'},{'entity':'tendon_1'}]}),patch('extensions.tendon_family.passive_execution.backend_result',side_effect=lambda inp,raw:raw),patch('extensions.tendon_family.passive_execution.execute',side_effect=AssertionError('CACHED_PAIR_REEXECUTED')):
            pair=execute_pair(inp,folder,['tendon_0','tendon_1'],baseline=saved(base),ablation=saved(abl))
        self.assertEqual(pair['cost']['physics_steps'],0);self.assertEqual(pair['model_builds'],0)
        self.assertEqual(metrics(inp.task,pair,check_confirmation=False)['validity'],'valid')


    def test_6_versioned_qualification_and_all_metric_statuses(self):
        task=small_task();raw=fixture(task);rule=PassiveResponseGoalV2.model_validate(task.goal.data).qualifications[0]
        rows=raw['episodes'][0]['qualification_samples'];changed=deepcopy(rows)
        for row in changed:row['qvel_rad_s']=[1.,1.]
        self.assertFalse(qualification(changed,rule)['passed'])
        q=rule.model_copy(update=dict(qvel_role='diagnostic',drift_role='speed_covered_diagnostic'))
        value=qualification(changed,q)
        self.assertTrue(value['passed']);self.assertIn('tail_drift',value['diagnostic_checks']);self.assertIn('qvel',value['diagnostic_checks'])
        self.assertEqual(value['observed']['static_balance_inf_nm'],0.);self.assertIsNone(value['observed']['normalized_static_balance'])
        outcome=metrics(task,raw,check_confirmation=False,check_mechanism=False);self.assertEqual(outcome['overall_status'],'PASS')
        outcome=metrics(task,raw);self.assertEqual(outcome['overall_status'],'INCOMPLETE')
        raw['episodes'][0]['maximum_contacts']=1
        outcome=metrics(task,raw);self.assertEqual(outcome['overall_status'],'FAIL');self.assertGreater(len(outcome['metrics']),5)
        EvaluationResult.model_validate(dict(outcome,source={'artifact_id':'a'*64},evaluator='evaluate.passive_response',comparison_identity='fixture'))
        self.assertIsNone(self.spec['family_search']['max_evaluations'])
        for name in ('mathematical_evaluations','physical_launches','offline_nlp','bdf_replays'):self.assertIsNone(self.spec['budgets'][name])

    def test_7_worker_diagnostic_interaction_and_baseline_dispatch(self):
        # The real calculation orchestrator executes four fixture callbacks with no scalar.
        c=self.c;spec=self.spec;paths=['segments.0.young_pa','segments.1.young_pa']
        from tools.research.search import search_problem
        coupled=dict(version='family_mixed_search_v2',family_space_identity=spec['family_space_identity'],previous_candidate_ref={'artifact_id':'a'*64},
            analysis=dict(effect_semantics='finite_time_task_response',target='finite_time_task_violation',parameter_paths=paths,
                operating_point='frozen_task_initial_state',control_treatment='no_active_control',physical_problem='passive_unilateral_equilibrium',
                execution_profile=dict(purpose='exploration',load_conditions=['plus_x'],stage_prefix='low',fidelity='screening')))
        from tools.research.agent import plan_schema
        schema=plan_schema(['search'],decision_required=True,focused=True,study=spec)
        Draft202012Validator({**schema['properties']['search'],'$defs':schema['$defs']}).validate(coupled)
        host=SimpleNamespace()
        with patch('tools.research.search.state',return_value=dict(spec=spec,profile={'identity':'fixture'})),patch('tools.research.search.verify_candidate',return_value=c):
            admitted=search_problem(host,coupled,4)
        q=MechanismStudy.model_validate(admitted['analysis_request']['mechanism_study'])
        context=prepare_context(spec,c,q,[])
        request=AnalysisRequest.model_validate(dict(candidate={'artifact_id':'a'*64},operation='mechanism_structure_v1',
            model_source='mujoco',operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],mechanism_study=plain(q)))
        def synthetic(inp,folder=None,**kwargs):
            t=small_task();r=fixture(t)
            # Missing full original trajectories gives UNKNOWN formal metrics. This is a fixture, not physics.
            r['physical_binding']['task_identity']=digest(plain(inp.task))
            r['execution_identity']=execution_identity(plain(inp),profile=kwargs.get('execution_profile'),execution_checks=kwargs.get('execution_checks','full'))
            if kwargs.get('execution_profile'):
                r['execution_profile']=execution_scope(inp.task,kwargs['execution_profile'])
                r['episodes']=[e for e in r['episodes'] if e['load_condition'] in r['execution_profile']['load_conditions']]
            return SimpleNamespace(data=SimpleNamespace(data=r))
        with patch('extensions.tendon_family.passive_execution.execute',side_effect=synthetic) as run,patch('extensions.tendon_family.passive_execution.execute_pair',side_effect=AssertionError('UNREQUESTED_PAIR')):
            out=calculate(c['configuration'],{},request,dict(actual_time_s=0.),context)
        self.assertEqual(run.call_count,4)
        self.assertEqual(len(out['structure_research']['records']),4)
        self.assertEqual(out['structure_research']['interaction']['status'],'diagnostic_comparison')
        self.assertFalse(out['structure_research']['interaction']['formal_causal_conclusion'])
        self.assertNotIn('structure_direction',out['structure_research'])
        # Cross-request orchestration uses that original Result and performs no callback.
        with fixture_directory() as folder:
            store=Store(folder);ref=store.put_context_checkpoint(out)
            inspect_query=request.model_copy(update=dict(mechanism_study=study(execution_profile=plain(q.execution_profile))))
            inspect_context=prepare_context(spec,c,inspect_query.mechanism_study,[])
            inspect_context.update(result_store=str(store.root),result_sources=[ref])
            with patch('extensions.tendon_family.passive_execution.execute',side_effect=AssertionError('REPEATED_PHYSICS')):
                reused=calculate(c['configuration'],{},inspect_query,dict(actual_time_s=0.),inspect_context)
            self.assertEqual(reused['structure_research']['cost']['physics_steps'],0)
            self.assertEqual(reused['structure_research']['records'][0]['reuse']['source']['reference'],ref)
        from tools.research.reporter import scientific_feedback
        result_ref={'artifact_id':'b'*64,'media_type':'application/json'}
        host=SimpleNamespace(store=Mock());host.store.artifact.return_value=reused
        with patch('tools.research.reporter.state',return_value=dict(analysis_results=[result_ref])),patch('tools.research.reporter.assemble',side_effect=AssertionError('MANDATORY_REPORTER')):
            feedback=scientific_feedback(host,dict(reference=result_ref))
        self.assertEqual(feedback['interpretation_status'],'not_requested')
        self.assertTrue(feedback['task_diagnosis']['conditions'])
        # A missing formal scalar also allows the explicitly requested coordinate probes.
        derivative=study(operation='differentiate',max_evaluations=8,parameter_paths=paths[:1])
        derivative_context=prepare_context(spec,c,derivative,[])
        derivative_query=request.model_copy(update=dict(mechanism_study=derivative))
        with patch('extensions.tendon_family.passive_execution.execute',side_effect=synthetic) as run:
            diagnostic=calculate(c['configuration'],{},derivative_query,dict(actual_time_s=0.),derivative_context)
        self.assertGreater(run.call_count,1)
        self.assertEqual(diagnostic['structure_research']['direction_status'],'diagnostic_comparison')
        self.assertNotIn('structure_direction',diagnostic['structure_research'])
        self.assertTrue(diagnostic['structure_research']['diagnostic_comparison']['comparisons'])



class HistoricalProjection(unittest.TestCase):
    def test_p3_results_2_9_14_and_non_p3_result75_readonly(self):
        from tools.research.evidence_views import task_diagnosis,compact_task_diagnosis
        from tools.research.feedback import diagnostic_task_gap
        audit=json.loads((ROOT/'docs/research/p3-autonomous-study-readiness-20261109/process-audit-measurements-20261110.json').read_text())
        store=Store(P3);before=digest(store.session(P3.name)['state']);projections=[]
        for index in (2,9,14):
            ref=next(r['reference'] for r in audit['results'] if r['result_index']==index)
            path='/structure_research/records/0';record=store.artifact(ref,pointers=(path,))[path]
            raw=record['mechanics']['dynamic_execution'];task=SessionInput.model_validate(record['configuration']).task
            gap=task_adapter(record['configuration']).diagnostic_task_gap(raw,source_reference=ref,pointer=path+'/mechanics/dynamic_execution')
            spec=PassiveResponseEvaluationV2.model_validate(task.evaluator.parameters.data).progressive_stiffness[0]
            result=stiffness(task,raw,spec)
            for i,tendon in enumerate(result['tendon_transitions']):
                from extensions.reference.passive_evaluation_v2 import stage_rows
                rows=stage_rows(PassiveResponseGoalV2.model_validate(task.goal.data),raw['episodes'][0],'low')
                self.assertEqual(tendon['low']['tension_max_n'],max(r['actual_tension_n'][i] for r in rows))
            self.assertTrue(any(t['classification']=='early_engagement' for t in result['tendon_transitions']))
            if index==14:
                self.assertFalse(result['denominator_valid'])
                self.assertTrue(any(t['classification']=='no_high_engagement' for t in result['tendon_transitions']))
            wrapped=dict(structure_research=dict(records=[record],baseline=record['observation']),diagnostic_task_gap=gap,candidate=None)
            diagnostic=task_diagnosis(wrapped,ref);compact=compact_task_diagnosis(diagnostic)
            self.assertTrue(any('observable' in r and r['observable'] for c in compact['conditions'] for r in c['observations']))
            projections.append(dict(result_index=index,source=ref,
                stiffness={k:v for k,v in result.items() if k not in ('tendon_transitions','transition_tendons','slack_to_taut')},
                coverage=gap['coverage'],main_projection=compact))
            del wrapped,record,raw
        self.assertEqual(digest(store.session(P3.name)['state']),before)
        from tests.research.test_diagnostic_feedback_repair import STORE,REF
        store=Store(STORE);record=store.artifact(REF,pointers=('/structure_research/records/0',))['/structure_research/records/0']
        gap=task_adapter(record['configuration']).diagnostic_task_gap(record['mechanics']['dynamic_execution'],source_reference=REF)
        self.assertEqual(gap['status'],'complete');self.assertEqual(len(gap['constraints']),251)
        expected=json.loads((ROOT/'docs/research/passive-study-review-20261109/result75-original-task-diagnostic.json').read_text())
        values={r['name']:r['value'] for r in expected['diagnostic_measurements']}
        for row in gap['constraints']:self.assertAlmostEqual(row['observed_value'],values[row['constraint_id'].removeprefix('evaluator:')],places=14)
        DOC.mkdir(parents=True,exist_ok=True)
        (DOC/'historical-projections.json').write_text(json.dumps(dict(scope='Read-only projection; zero new physics and Provider calls; no acceptance upgrade',p3=projections,
            non_p3=dict(source=REF,measured_count=251,all_values_match_historical_audit=True)),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':unittest.main()
