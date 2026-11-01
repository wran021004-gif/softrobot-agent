"""Bounded bridge contracts; synthetic values are interface fixtures only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.research_tasks import constraint_observation,constraint_gap


class C0BridgeTests(unittest.TestCase):
    def test_signed_bounds_zero_scale_and_invalid_coverage(self):
        def row(key,value,bound,kind='upper'):
            return constraint_observation(dict(constraint_id=key,bound=bound,bound_type=kind,unit='m'),
                dict(value=value,passed=(value<=bound if kind=='upper' else value>=bound)))
        upper=row('upper',3.,2.);lower=row('lower',1.,2.,'lower')
        gap=constraint_gap([upper,lower],valid_complete=True)
        self.assertEqual(gap['signed_task_gap'],.5)
        self.assertEqual(lower['signed_violation'],1.)
        self.assertEqual(len(gap['dominant_constraints']),2)
        gated=constraint_gap([upper,row('zero',0.,0.)],valid_complete=True)
        self.assertEqual(gated['normalized_gap'],.5);self.assertEqual(gated['hard_gate_status'],'passed')
        self.assertIsNone(constraint_gap([upper,row('zero',1.,0.)],valid_complete=True)['normalized_gap'])
        self.assertIsNone(constraint_gap([upper],valid_complete=False)['normalized_gap'])
        passing=constraint_gap([row('upper',1.,2.)],valid_complete=True)
        self.assertEqual(passing['signed_task_gap'],-.5)
        self.assertEqual(passing['normalized_gap'],0.)
        gate_only=constraint_gap([row('zero',0.,0.)],valid_complete=True)
        self.assertTrue(gate_only['observation_feasible'])
        self.assertEqual(gate_only['objective_status'],'feasibility_comparison_only')
        self.assertIsNone(gate_only['signed_task_gap'])

    def test_freeze_detects_passive_solver_without_modifying_evidence(self):
        import tools.research.state as st
        original=st.ROOT
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in st.SCIENCE_FILES:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((original/name).read_bytes())
            with patch.object(st,'ROOT',root):
                frozen=st.science_hashes()
                for name in ('passive_equilibrium','passive_inverse'):
                    target=root/('extensions/tendon_family/'+name+'.py');body=target.read_bytes()
                    target.write_bytes(body+b'\n# isolated perturbation\n')
                    self.assertNotEqual(frozen,st.science_hashes())
                    target.write_bytes(body)
                self.assertEqual(frozen,st.science_hashes())

    def test_request_snapshot_is_detached_and_not_persistent(self):
        from tools.platform_store import Store
        with TemporaryDirectory() as tmp:
            s=Store(tmp);calls=[]
            def build():calls.append(1);return dict(value=[])
            with s.read_snapshot():
                s.snapshot_value('a',build)['value'].append(1)
                self.assertEqual(s.snapshot_value('a',build),dict(value=[]))
            s.snapshot_value('a',build)
            self.assertEqual(len(calls),2)
            self.assertFalse(s.db.exists())

    def test_v4_menu_and_old_compiler_alias(self):
        from tools.research.scientific_intent import scientific_actions,action_entry
        spec=dict(research_decisions=dict(analysis_interface='scientific_question_v4'),capabilities=['analysis'])
        goals=[r['scientific_goal'] for r in scientific_actions(spec)]
        self.assertEqual(set(goals),{'mechanism_research','control_feasibility','structure_control_codesign'})
        self.assertIsNotNone(action_entry(spec,'single_parameter_effect'))
        spec['research_decisions']['analysis_interface']='scientific_question_v3'
        self.assertIn('single_parameter_effect',[r['scientific_goal'] for r in scientific_actions(spec)])

    def test_historical_certificate_and_present_diagnostic_are_both_checked(self):
        from tests.research.test_p63g_bounded_evidence import bounded_host,BoundedEvidenceTests
        from tools.research.evidence_views import acceptance_certificate
        from tools.research.state import save
        h=bounded_host();_,ref=BoundedEvidenceTests().physical(h)
        value=h.store.artifact(ref);value['acceptance'].pop('constraint_observations',None)
        legacy=save(h,value,'synthetic_pre_diagnostic_acceptance')
        self.assertTrue(acceptance_certificate(h,legacy)['complete_acceptance_view'])
        value['acceptance']['constraint_observations']=[dict(forged=True)]
        forged=save(h,value,'synthetic_forged_diagnostic')
        cert=acceptance_certificate(h,forged)
        self.assertFalse(cert['complete_acceptance_view'])
        self.assertIn('ACCEPTANCE_DIFFERS_FROM_ORIGINAL_EVALUATOR_AND_PROFILE',cert['validation_issues'])


class C1BridgeTests(unittest.TestCase):
    def configuration(self):
        from tools.research.config import resolve,ROOT
        return resolve(ROOT/'configs/research/study_passive_engineering_v1.json')['configuration']

    def test_capability_axes_and_hybrid_rejection(self):
        from tools.research_tasks import task_adapter
        from extensions.math_analysis.differentiation_router import select_method
        cfg=self.configuration();cap=task_adapter(cfg).physical_capabilities()
        self.assertEqual(cap['actuation'],'no_active_control')
        self.assertTrue(cap['evaluation']['finite_time_structure_response'])
        cfg['task']['actuator_channels']=['actuator_commands']
        from tools.research_tasks import ResearchTaskAdapter
        hybrid=ResearchTaskAdapter(cfg).physical_capabilities()
        self.assertEqual(hybrid['status'],'unsupported')
        self.assertIn('mixed_actuation_fixed_payout_backend',hybrid['missing'])
        route=select_method(effect_semantics='finite_time_task_response',capabilities=hybrid)
        self.assertEqual(route['validity'],'unsupported')
        self.assertIsNone(route['method'])

    def test_router_methods_and_no_automatic_control_search(self):
        from extensions.math_analysis.differentiation_router import select_method
        from tools.research_tasks import task_adapter
        cap=task_adapter(self.configuration()).physical_capabilities()
        for effect,target,expected in [('re_equilibrated_passive_response','re_equilibrated_position_response','passive_kkt_implicit'),
                ('mechanism_effect','tangent_compliance','passive_re_equilibrated_pairs'),
                ('finite_time_task_response','finite_time_task_violation','finite_time_task_paired_response')]:
            self.assertEqual(select_method(effect_semantics=effect,capabilities=cap,target=target)['method'],expected)
        active=dict(cap,actuation='ideal_tension')
        route=select_method(effect_semantics='reoptimized_task_capability',capabilities=active)
        self.assertEqual(route['validity'],'needs_prerequisite');self.assertFalse(route['automatic_expensive_search'])
        self.assertEqual(select_method(effect_semantics='reoptimized_task_capability',capabilities=active,saved_t1=True)['direction_status'],
            'finite_budget_best_found_secant')
        self.assertEqual(select_method(effect_semantics='reoptimized_task_capability',capabilities=active,saved_conic=True)['method'],
            'saved_conic_capability_sensitivity')

    def test_v4_dynamic_compile_with_unscaled_hard_gate(self):
        from tests.research.test_passive_physical_acceptance import prepared_host
        from tests.research.test_p63g3_action_handoff import diagnosis
        from tools.research import core
        from tools.research.scientific_intent import question_schema,compile_question
        from tools.research.state import state
        from jsonschema import Draft202012Validator
        h,c=prepared_host(budget=10,mathematical_budget=5)
        with patch.object(core,'guard'):core.dispatch(h,diagnosis(c,'mechanism_research'),'dynamic-diagnose')
        q=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='inspect',
            effect_semantics='finite_time_task_response',target='finite_time_task_violation',
            operating_point='frozen_task_initial_state',control_treatment='no_active_control',
            physical_problem='passive_unilateral_equilibrium',load_condition='all_frozen_conditions',requested_budget=1))
        schema=question_schema(state(h)['spec'],h.store.artifact(c),'mechanism_research')
        Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(q)
        before=deepcopy(state(h));result=compile_question(h,q,tool_use_id='dynamic-inspect')
        self.assertEqual(result['status'],'ready',result)
        self.assertEqual(result['dynamic_cost_bound'],dict(model_builds=1,episodes=2,physics_steps=800))
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        q['structure'].update(operation='differentiate',parameter_paths=['payout_lengths_m.tendon_0'],requested_budget=5)
        result=compile_question(h,q,tool_use_id='gated-objective')
        self.assertEqual(result['status'],'ready',result)
        self.assertEqual(result['dynamic_cost_bound']['episodes'],10)

    def test_full_task_reduction_cannot_drop_condition_or_zero_bound(self):
        from tools.research_tasks import task_adapter,constraint_gap
        cfg=self.configuration();adapter=task_adapter(cfg)
        definitions=adapter.constraint_observations({})
        components={d['constraint_id']:dict(value=d['bound']*.5,passed=True) for d in definitions}
        components['evaluator:vertical_speed_maximum']=dict(value=6.,passed=False)
        rows=adapter.constraint_observations(components)
        gap=constraint_gap(rows,valid_complete=True)
        self.assertAlmostEqual(gap['signed_task_gap'],.2)
        self.assertIn('evaluator:no_contact',gap['unscaled_constraints'])
        self.assertEqual(gap['dominant_constraints'][0]['condition_id'],'vertical')
        components['evaluator:no_contact']=dict(value=1,passed=False)
        blocked=constraint_gap(adapter.constraint_observations(components),valid_complete=True)
        self.assertIsNone(blocked['signed_task_gap']);self.assertFalse(blocked['observation_feasible'])
        self.assertEqual(blocked['hard_gate_status'],'failed')
        del components['evaluator:lateral_response_maximum']
        self.assertFalse(constraint_gap(adapter.constraint_observations(components),valid_complete=True)['valid_complete'])

    def test_synthetic_multicondition_stencil_uses_original_local_search_and_handoff(self):
        from types import SimpleNamespace
        from schemas.platform import ConstraintResult
        from tools.state_io import digest
        from tools.platform_store import plain
        from tools.research.contracts import AnalysisRequest,MechanismStudy,PhysicalMechanismTarget
        from tools.research.structure_research import parameters,prepare_context,calculate
        from tools.research_tasks import task_adapter
        from tools.research.state import state
        from tests.research.test_passive_physical_acceptance import prepared_host
        h,c=prepared_host();spec=state(h)['spec'];candidate=deepcopy(h.store.artifact(c))
        # Synthetic observations only; the unchanged frozen no-contact gate stays.
        task=candidate['configuration']['task'];task['task_id']='synthetic_normalized_dynamic_fixture'
        candidate['task_identity']=digest(task)
        row=next(r for r in parameters(spec,candidate) if r['mechanism_differentiation']['supported'] and r['parameter_id'].startswith('payout_lengths_m.'))
        origin=row['current_value'];width=row['maximum']-row['minimum']
        def execute(inp,folder=None):
            values=inp.robot.structure.data['fixed_payout_lengths_m']
            payout=next(iter(values.values())) if isinstance(values,dict) else values[0]
            return SimpleNamespace(data=SimpleNamespace(data=dict(synthetic_payout=payout,
                physical_binding=dict(model_identity='SYNTHETIC-NO-ENGINE-'+str(payout)),
                cost=dict(model_builds=1,physics_steps=0,episodes_started=2,episodes_completed=2))))
        def measure(task,raw):
            z=(raw['synthetic_payout']-origin)/width
            if mode=='invalid_best' and abs(z+.005)<1e-8 or mode=='invalid_coarse' and abs(z+.01)<1e-8:
                return dict(validity='invalid',reason='SYNTHETIC_PROBE_FAILURE',constraints=[],metrics=[])
            rows=task_adapter(dict(task=plain(task))).constraint_observations({})
            constraints=[]
            for i,d in enumerate(rows):
                ratio=(.8+z if i==0 else .1) if mode=='smooth' else (1.2+z if i==0 else 1.18-3*z if i==1 else .1)
                value=d['bound']*ratio
                if mode=='contact_best' and d['bound']==0 and abs(z+.005)<1e-8:value=1.
                constraints.append(ConstraintResult(name=d['constraint_id'].split(':',1)[1],observed=value,
                    limit=d['bound'],units=d['unit'],satisfied=value<=d['bound']))
            return dict(validity='valid',task_success=True,constraints=constraints,metrics=[])
        for mode,operation,cap in [('smooth','differentiate',5),('smooth','optimize',6),
                ('switch','differentiate',5),('switch','optimize',6),('two_parameters','differentiate',10),('invalid_coarse','differentiate',5),
                ('invalid_best','differentiate',5),('contact_best','differentiate',5)]:
            paths=[row['parameter_id']]
            if mode=='two_parameters':paths.append(next(r['parameter_id'] for r in parameters(spec,candidate)
                if r['mechanism_differentiation']['supported'] and r['parameter_id']!=row['parameter_id']))
            study=MechanismStudy(operation=operation,target=PhysicalMechanismTarget(quantity='finite_time_task_violation',goal='decrease'),
                parameter_paths=paths,point_semantics='frozen_task_initial_state',
                effect_semantics='finite_time_task_response',max_evaluations=cap)
            q=AnalysisRequest(candidate=c,operation='mechanism_structure_v1',model_source='mujoco',
                operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],mechanism_study=study)
            context=prepare_context(spec,candidate,study,[])
            with patch('extensions.tendon_family.passive_execution.execute',side_effect=execute),patch('extensions.reference.passive_response.task_metrics',side_effect=measure):
                result=calculate(candidate['configuration'],dict(candidate=c),q,dict(actual_time_s=0.),context)
            self.assertEqual(result['status'],'computed',result)
            evidence=result['structure_research'];self.assertEqual(evidence['cost']['physics_steps'],0)
            self.assertEqual(len(evidence['records'][0]['observation']['task_gap']['constraints']),17)
            if mode in ('invalid_best','contact_best'):
                self.assertNotIn('structure_direction',evidence)
                self.assertEqual(evidence['candidate_improvement_status'],'not_observed')
                if mode=='contact_best':
                    self.assertIn('discontinuous_hard_gate',evidence['derivative_status'])
                    failed=[r['observation']['task_gap'] for r in evidence['records'] if r['observation']['task_gap']['hard_gate_status']=='failed']
                    self.assertTrue(failed);self.assertFalse(failed[0]['observation_feasible'])
                continue
            self.assertTrue(evidence['structure_direction'])
            self.assertEqual(evidence['candidate_improvement_status'],'observed_full_task_improvement')
            if mode!='smooth':
                self.assertFalse(evidence['parameter_sensitivities'][0]['consistency']['passed'])
                self.assertAlmostEqual(evidence['observed_reduction'],.005)
            from tools.research.structure_research import summary,observed_task_improvement
            compact=summary(result,dict(artifact_id='synthetic',media_type='application/json'))
            self.assertNotIn('dynamic_metrics',compact);self.assertNotIn('dynamic_task_gaps',compact)
            self.assertEqual(compact['hard_gates'][0]['bound'],0)
            self.assertEqual(compact['candidate_improvement_status'],evidence['candidate_improvement_status'])
            altered=deepcopy(evidence['records']);chosen=evidence['best_valid_record_index']
            altered[chosen]['configuration']['policy']['backend']['version']='incomparable-test-model'
            self.assertNotEqual(observed_task_improvement(altered,[row])['best_valid_record_index'],chosen)
            self.assertEqual(evidence['structure_direction']['generation_handoff']['tool'],'research_plan')
            self.assertFalse(evidence['structure_direction']['formal_candidate_created'])
            self.assertFalse(evidence['parameter_sensitivities'][0]['strict_derivative'])
            if mode=='two_parameters':self.assertFalse(evidence['parameter_sensitivities'][1]['consistency']['passed'])
            if operation=='optimize':self.assertIn('Powell',evidence['local_search']['method'])
        study=study.model_copy(update=dict(operation='inspect',parameter_paths=[],max_evaluations=1))
        q=q.model_copy(update=dict(mechanism_study=study));context=prepare_context(spec,candidate,study,[])
        invalid=dict(validity='invalid',reason='SYNTHETIC_NUMERICAL_FAILURE',constraints=[],metrics=[])
        with patch('extensions.tendon_family.passive_execution.execute',side_effect=execute),patch('extensions.reference.passive_response.task_metrics',return_value=invalid):
            result=calculate(candidate['configuration'],dict(candidate=c),q,dict(actual_time_s=0.),context)
        self.assertEqual(result['status'],'execution_incomplete')
        self.assertEqual(result['structure_research']['cost']['model_builds'],1)
        self.assertIsNone(result['structure_research']['records'][0]['observation']['task_gap']['signed_task_gap'])

        # Execute the original compiler/worker/SDK path with fabricated physics.
        from tools.research import core,analysis
        from tools.state_io import read,atomic_json
        from schemas.platform_analysis import TaskAnalysisRequirement
        from tests.research.test_p63g3_action_handoff import diagnosis
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_information_flow import packet
        import json,re
        mode='switch';h,c=prepared_host(wire=True,budget=10,mathematical_budget=5)
        def worker(command,log,timeout,**kw):
            req=read(Path(command[-1]));query=AnalysisRequest.model_validate(req['query'])
            candidate=h.store.artifact(c);context=prepare_context(state(h)['spec'],candidate,query.mechanism_study,[])
            with patch('extensions.tendon_family.passive_execution.execute',side_effect=execute),patch('extensions.reference.passive_response.task_metrics',side_effect=measure):
                value=calculate(candidate['configuration'],req['binding'],query,dict(actual_time_s=0.),context)
            value=analysis.scoped_result(value,TaskAnalysisRequirement.model_validate(req['task_analysis']),req['analysis_applicability'],query)
            atomic_json(Path(command[-1]).with_name('result.json'),value)
            return SimpleNamespace(returncode=0)
        question=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='differentiate',
            effect_semantics='finite_time_task_response',target='finite_time_task_violation',
            operating_point='frozen_task_initial_state',control_treatment='no_active_control',
            physical_problem='passive_unilateral_equilibrium',load_condition='all_frozen_conditions',
            parameter_paths=[row['parameter_id']],requested_budget=5))
        with patch('tools.service_execution._run_contained',side_effect=worker),patch('tools.research.reporter._wire',side_effect=ValueError('OFFLINE_REPORTER_UNAVAILABLE')):
            wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),
                ('research_plan',diagnosis(c,'mechanism_research')),('research_analysis',question),None])
        compact=packet(wires[-1])['mathematical_research']['latest_result']['structure_research']
        self.assertEqual(compact['candidate_improvement_status'],'observed_full_task_improvement')
        self.assertAlmostEqual(compact['baseline']['signed_task_gap'],.2)
        self.assertAlmostEqual(compact['best_valid']['signed_task_gap'],.195)
        self.assertEqual(compact['derivative_status'],'nonsmooth_maximum_switch')
        self.assertEqual(compact['hard_gates'][0]['baseline_passed'],True)
        for wire in wires:
            text=json.dumps(wire)
            self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])',text,re.I))
            for private in ('artifact_id','dynamic_metrics','dynamic_task_gaps','x-research-reference-choices'):
                self.assertNotIn(private,text)
        self.assertEqual(state(h)['mathematical_evaluations'],5)
        self.assertEqual(len(state(h)['candidates']),1)
        self.assertFalse(state(h).get('physical_replays'))
        atomic_json(Path(__file__).resolve().parents[2]/'runs/c11_validation/synthetic_wire.json',
            dict(scope='Synthetic SDK/Mock HTTP evidence, no engine or Provider',wire=wires[-1]))
        again=packet(run_fixture(h,[None])[-1])['mathematical_research']['latest_result']
        self.assertNotIn('structure_research',again)
