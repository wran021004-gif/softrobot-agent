"""B0/B directed offline fixtures; no real engine or Provider."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.platform_store import plain
from tools.research import core
from tools.research.state import state,update
from tools.research.research_context import agent_decision_brief
from tools.research.design import set_parameter
from extensions.tendon_family.family_space import resolved_request
from tests.research.test_structure_mechanism_aplus import prepare,execute_synthetic
from tests.research.test_p63a_math_interface import generate,diagnose
from tests.research.test_p63c2_scientific_intent import mechanism_question
from tests.research.test_information_flow import generation


class DirectionProjectionTests(unittest.TestCase):
    def test_two_candidates_alternate_without_cross_candidate_direction(self):
        h,a=prepare();b=generate(h,(.17,.11));diagnose(h,a,'scientific_question')
        ar=execute_synthetic(h,a,mechanism_question())['reference']
        diagnose(h,b,'scientific_question');br=execute_synthetic(h,b,mechanism_question())['reference']
        for candidate,expected,other in [(b,br,ar),(a,ar,br),(b,br,ar)]:
            diagnose(h,candidate,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
            self.assertEqual(view['candidate'],candidate);self.assertEqual(view['direction_candidate'],candidate)
            self.assertEqual(view['direction_query']['reference'],expected)
            self.assertTrue(any(r['query']['reference']==other and r['relation']=='other_candidate_history' for r in view['historical_directions']))
        c=generate(h,(.18,.11));diagnose(h,c,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
        self.assertFalse(view['direction_proposed']);self.assertIsNone(view['direction_query'])

    def test_citation_and_generated_candidate_do_not_prove_suggestion_adopted(self):
        h,c=prepare();ref=execute_synthetic(h,c,mechanism_question())['reference']
        request=resolved_request(state(h)['spec']['family_space'],h.store.artifact(c)['parameters'])
        set_parameter(request,'segments.1.length_m',.111)
        plan=generation(h);plan.update(generation=request,supporting_evidence=[ref])
        with patch.object(core,'guard'):out=core.dispatch(h,plan,'b0-cite-but-other-edit')
        changed=out['result']['candidate'];diagnose(h,changed,'scientific_question')
        view=agent_decision_brief(h)['mechanism_research']
        self.assertFalse(view['direction_proposed']);self.assertIsNone(view['direction_candidate'])
        self.assertTrue(view['generation_plan_cited_evidence']);self.assertTrue(view['formal_candidate_created'])
        self.assertFalse(view['suggestion_adopted'])
        self.assertEqual(view['generation_relations'][0]['relation'],'historical_parent_direction')
        diagnose(h,c,'scientific_question');view=agent_decision_brief(h)['mechanism_research']
        self.assertTrue(view['direction_proposed']);self.assertFalse(view['suggestion_adopted'])

    def test_original_budget_closeout_and_authorization_own_l0_admission(self):
        h,c=prepare();original=deepcopy(state(h))
        ready=agent_decision_brief(h)['mechanism_research'];self.assertTrue(ready['operation_admission']['differentiate']['can_prepare'])
        for change in ('budget','closeout','grant'):
            update(h,**deepcopy(original))
            if change=='budget':update(h,mathematical_evaluations=32)
            elif change=='closeout':update(h,count_closeout=True)
            else:
                spec=deepcopy(state(h)['spec']);spec['mathematical_methods'].pop('mechanism_structure_v1');update(h,spec=spec)
            brief=agent_decision_brief(h);view=brief['mechanism_research']
            self.assertTrue(brief['mathematical_research'])
            self.assertTrue(all(not r['can_prepare'] for r in view['operation_admission'].values()),view)

    def test_declared_historical_direction_can_be_adopted_without_becoming_current(self):
        h,c=prepare();ref=execute_synthetic(h,c,mechanism_question())['reference']
        raw=h.store.artifact(ref);update(h,analysis_results=[],research_mathematics=[ref])
        plan=generation(h);plan.update(generation=raw['structure_research']['structure_direction']['generation_handoff']['generation'],supporting_evidence=[ref])
        with patch.object(core,'guard'):out=core.dispatch(h,plan,'b0-historical-adoption')
        child=out['result']['candidate'];diagnose(h,child,'scientific_question')
        view=agent_decision_brief(h)['mechanism_research']
        self.assertFalse(view['direction_proposed']);self.assertTrue(view['suggestion_adopted'])
        self.assertEqual(view['generation_relations'][0]['relation'],'historical_parent_direction')
        self.assertEqual(view['historical_directions'][0]['relation'],'declared_historical_mathematics')


def m2_question(**changes):
    q=mechanism_question();q.update(effect_semantics='reoptimized_task_capability',
        control_treatment='reoptimized',target='holding_max_speed_m_s',requested_budget=1)
    q.update(changes);return q


class JointSemanticsTests(unittest.TestCase):
    def compile(self,h,q):
        from tools.research.scientific_intent import compile_question
        return compile_question(h,q,tool_use_id='b-joint-synthetic')

    def triplet(self):
        from tests.research.test_p63a_math_interface import t1_request,offline_dispatch
        h,c=prepare();candidates=[c,generate(h,(.155,.11)),generate(h,(.165,.11))]
        refs=[offline_dispatch(h,t1_request(h,r),'b-t1-fixture-'+str(i))['reference'] for i,r in enumerate(candidates)]
        diagnose(h,c,'scientific_question');return h,c,refs

    def test_same_high_level_request_aggregates_saved_t1_without_rollouts(self):
        from tests.research.test_p63a_math_interface import offline_dispatch
        from tools.research.contracts import AnalysisRequest
        h,c,refs=self.triplet();r=self.compile(h,m2_question(source_selection=dict(t1_results=refs)))
        self.assertEqual(r['status'],'ready',r);self.assertEqual(r['method'],'mujoco-reoptimized-structure-response-v1')
        self.assertFalse(r['automatic_T1']);AnalysisRequest.model_validate(r['request'])
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',side_effect=AssertionError('NO_NEW_ROLLOUT')):
            out=offline_dispatch(h,r['request'],'b-saved-t2')
        raw=h.store.artifact(out['reference'])['nonlinear_response']
        self.assertEqual(raw['cost']['physics_steps'],0);self.assertEqual(raw['cost']['reused_t1_results'],3)
        comparison=raw['comparison_summary'][0]['effect_comparison']
        self.assertIn('fixed_control_secant',comparison);self.assertIn('reoptimized_best_found_secant',comparison)
        self.assertIn('CONTROL_SEARCH_QUALITY_UNRESOLVED_AT_LIMIT_OR_FAILURE',comparison['search_quality_reasons'])
        self.assertEqual(raw['direction_status'],'unresolved')
        from tools.research.capability import compact_nonlinear_directions
        compact=compact_nonlinear_directions(raw)[0]['effect_comparison']
        self.assertIn('same_observed_sign',compact);self.assertNotIn('active_constraints',compact)

    def test_missing_or_incomparable_t1_returns_preparation_not_a_new_search(self):
        h,c=prepare();before=deepcopy(state(h));r=self.compile(h,m2_question())
        self.assertEqual(r['status'],'needs_prerequisite');self.assertFalse(r['automatic_T1'])
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        h,c,refs=self.triplet();last=h.store.artifact(refs[-1]);altered=deepcopy(last)
        altered['nonlinear_capability']['settings']['evaluation_requests']+=1
        from tools.research.state import save
        bad=save(h,altered,'B synthetic incomparable T1 fixture')
        update(h,analysis_results=[*state(h)['analysis_results'],bad])
        r=self.compile(h,m2_question(source_selection=dict(t1_results=[*refs[:2],bad])))
        self.assertEqual(r['status'],'needs_prerequisite');self.assertFalse(r['automatic_T1'])

    def test_v2_control_search_uses_original_t1_and_requires_explicit_choices(self):
        from tests.research.test_p63a_math_interface import t1_request
        h,c=prepare();t1_request(h,c);q=m2_question(operation='optimize',parameter_paths=[],requested_budget=3,
            control_scope=dict(mode='full_task'),search_strategy='response')
        r=self.compile(h,q);self.assertEqual(r['status'],'ready',r)
        self.assertEqual(r['request']['operation'],'mujoco_nonlinear_task_capability_v1')
        self.assertEqual(r['request']['control_optimization']['settings']['evaluation_requests'],3)
        q['parameter_paths']=['segments.0.length_m'];r=self.compile(h,q)
        self.assertEqual(r['reason'],'GENERATE_CONTRAST_THEN_OPTIMIZE_CONTROL_PER_CANDIDATE');self.assertFalse(r['automatic_T1'])

    def test_conic_ready_models_are_preferred_with_original_request_and_cost(self):
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.optimal_capability import CONIC,SENSITIVITY
        from tools.research.contracts import AnalysisRequest
        h,c=prepare();spec=deepcopy(state(h)['spec']);spec['mathematical_methods'].update({CONIC:'OFFLINE',SENSITIVITY:'OFFLINE'})
        update(h,spec=spec);view=mathematical_method_view(h,c);detail=view['methods'][SENSITIVITY]
        refs=[dict(artifact_id=str(i)*64,media_type='application/json') for i in range(1,4)]
        stencil=dict(candidate=c,operation='task_capability',operating_point='standardized_initial_pretension',
            protocol=spec['analysis_protocol'],capability_method=CONIC,optimal_sensitivity=dict(variable='segments.0.length_m',steps=[.005],model_results=refs))
        # Fabricated readiness only. The original execution gate is never bypassed or run.
        detail.update(planning_status='ready',execution_status='conditional_on_admission',formal_execution_authorized=True,
            missing=[],readiness=dict(variables=[dict(variable='segments.0.length_m',ready_stencils=[dict(request=stencil,
                admission=dict(status='admissible',expected_mathematical_evaluations=5))])]))
        with patch('tools.research.task_constraints.mathematical_method_view',return_value=view):
            r=self.compile(h,m2_question(requested_budget=5))
            self.assertEqual(r['status'],'ready',r);self.assertEqual(r['method'],SENSITIVITY)
            self.assertEqual(r['required_evaluations'],5);self.assertFalse(r['strict_optimal_value_gradient'])
            self.assertEqual(AnalysisRequest.model_validate(r['request']).optimal_sensitivity.model_results[0].artifact_id,refs[0]['artifact_id'])
            self.assertEqual(self.compile(h,m2_question(requested_budget=4))['status'],'blocked')
            selected=self.compile(h,m2_question(requested_budget=5,source_selection=dict(model_results=refs)))
            self.assertEqual(selected['status'],'ready',selected)

    def test_tracking_preserves_adapter_samples_and_explicit_native_t2_boundary(self):
        from tests.research.test_tracking import TASK
        from tools.research.task_constraints import describe_analysis_requirements,mathematical_method_view
        from tools.research.state import save
        from tools.research_tasks import task_adapter
        h,c=prepare();base=h.store.artifact(c);cfg=deepcopy(base['configuration']);cfg['task']=deepcopy(TASK)
        requirements=describe_analysis_requirements(cfg,{})
        self.assertEqual(requirements.binding['task_family'],'task.tracking')
        self.assertTrue(any(x.kind=='path_bound' for x in requirements.constraints))
        self.assertNotIn('terminal_error_m',[x.constraint_id for x in requirements.constraints])
        # Same compiler: task-specific admission is the existing view, not an endpoint substitute.
        view=mathematical_method_view(h,c);detail=view['methods']['mujoco-reoptimized-structure-response-v1']
        detail.update(planning_status='unsupported',missing=['Tracking nonlinear T1/T2 is not applicable'])
        with patch('tools.research.task_constraints.mathematical_method_view',return_value=view):
            r=self.compile(h,m2_question());self.assertEqual(r['status'],'unsupported')
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_same_v2_m0_compiles_for_a_fresh_timed_tracking_task(self):
        from uuid import uuid4
        from tools.research.config import ROOT
        from tools.research.design import generate_candidate
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.state import save
        from tools.state_io import read,atomic_json,digest
        cfg=read(ROOT/'configs/research/study_structure_mechanism_aplus_check.json')
        cfg.update(study_id='b-tracking-fixture-'+uuid4().hex[:8],task='../../tasks/bf4_tracking_direction_change_v1.json')
        cfg['family_execution']=read(ROOT/'configs/research/study_tracking_public.json')['family_execution']
        cfg['control']='control_bf4_tracking.json'
        cfg['reference_parameters']=dict(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.)
        cfg['budgets']['mathematical_evaluations']=6
        cfg['mathematical_methods']['mujoco-reoptimized-structure-response-v1']='OFFLINE fixture only'
        path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json');atomic_json(path,cfg)
        try:h=core.prepare(path,ROOT/'runs'/cfg['study_id'])
        finally:path.unlink()
        update(h,freeze='offline-tracking-source-no-numerics')
        scope=dict(study_id=h.run_id,resolved_identity=state(h)['spec']['resolved_identity'],execution_scopes=['registered mathematics'])
        save(h,dict(user_approval='OFFLINE ONLY',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
        c=generate_candidate(h,dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],segment_count=2,tendon_count=4,
            control_weights=dict(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.)),dict(origin='offline tracking fixture'))['candidate']
        diagnose(h,c,'scientific_question')
        q=mechanism_question();q.update(parameter_paths=['segments.1.sections.0.parameters.width_y_m'],
            target=dict(quantity='directional_drive',tendon_channel=0,direction_world=[0.,1.,0.]))
        r=self.compile(h,q);self.assertEqual(r['status'],'ready',r)
        view=mathematical_method_view(h,c);constraints=view['research_opportunities']['metrics']
        self.assertTrue(any(x.get('constraint',{}).get('constraint_id')=='timed_tracking' for x in constraints))
        r=self.compile(h,m2_question(parameter_paths=q['parameter_paths'],target='timed_tracking'))
        self.assertEqual(r['status'],'unsupported');self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_m0_m1_m2_m3_cannot_mix_control_conditions(self):
        h,c=prepare()
        r=self.compile(h,m2_question(control_treatment='fixed_absolute_tensions'))
        self.assertEqual(r['reason'],'M2_REQUIRES_EXPLICIT_REOPTIMIZED_CONTROL_TREATMENT')
        for semantics in ('closed_loop_performance','re_equilibrated_passive_response'):
            q=mechanism_question();q['effect_semantics']=semantics
            self.assertEqual(self.compile(h,q)['status'],'unsupported')
        q=mechanism_question();q['source_selection']=dict(t1_results=[c])
        self.assertEqual(self.compile(h,q)['status'],'unsupported')
        self.assertEqual(state(h)['mathematical_evaluations'],0)


if __name__=='__main__':unittest.main()
