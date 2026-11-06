"""Store/Plan/Schema continuity with real objects and explicitly fake workers."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from tools.research import core,analysis
from tools.research.state import state,update,save
from tools.research.design import generate_candidate
from tools.research.research_context import context,agent_decision_brief,decision_candidate,research_intent
from tools.research.scientific_intent import completed_question_plan,compile_question
from tools.research.object_choices import reference_choices,reference_schema,main_projection,expand_references,bind_plan_selection
from tools.research.agent import plan_schema
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.state_io import read,atomic_json
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_p63a_math_interface import fixture_host
from tests.research.test_p63g3_action_handoff import diagnosis
from tests.research.test_research_authorization_preflight import approve


@contextmanager
def host_fixture(passive):
    if passive:
        with fixture() as h:yield h
    else:
        h=fixture_host();s=deepcopy(state(h)['spec'])
        s['research_decisions']['analysis_interface']='scientific_question_v4'
        s['mathematical_methods']['mechanism_structure_v1']='Explicit offline fixture only'
        update(h,spec=s);yield h


def request(h,i,passive):
    return dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
        segment_count=9 if passive else 2,tendon_count=4,
        segments={str(j):dict(length_m=.04+.001*i) for j in range(9)} if passive else {'0':dict(length_m=.16+.001*i)})


def diagnose(h,c,key):
    with patch.object(core,'guard'):
        out=core.dispatch(h,diagnosis(c,'mechanism_research'),key)
    return out['plan']


class WorkflowTests(unittest.TestCase):
    def test_new_candidate_does_not_rebind_plan_and_evaluation_joins_exact_plan(self):
        for passive in (True,False):
            with self.subTest(passive=passive),host_fixture(passive) as h:
                approve(h,[REGISTERED_MATHEMATICS_SCOPE])
                cs=[generate_candidate(h,request(h,i,passive),dict(origin='Offline continuity fixture'))['candidate'] for i in range(3)]
                p1=diagnose(h,cs[2],'diagnose-c3')
                generation=diagnosis(cs[2]);generation.update(action='generate',generation=request(h,3,passive))
                generation['decision']['research_intent']='DESIGN_MODIFICATION'
                with patch.object(core,'guard'):
                    c4=core.dispatch(h,generation,'generate-c4')['result']['candidate']
                self.assertEqual(completed_question_plan(h)['plan_reference'],p1)
                self.assertEqual(decision_candidate(h,{},research_intent(h)),cs[2])
                workflow=context(h)['evidence_working_set']['research_workflow']
                self.assertEqual(len(workflow['candidates']),4)
                self.assertTrue(workflow['candidates'][-1]['unevaluated'])
                self.assertEqual(workflow['active_plan']['candidate'],cs[2])
                p2=diagnose(h,c4,'diagnose-c4')
                question=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='inspect',
                    effect_semantics='mechanism_effect',
                    operating_point='re_equilibrated' if passive else 'frozen_task_initial_state',
                    control_treatment='no_active_control' if passive else 'fixed_absolute_tensions',
                    target=dict(quantity='constraint_active_set' if passive else 'tip_jacobian',reduction='identity'),requested_budget=1))
                if passive:
                    question['structure'].update(physical_problem='passive_unilateral_equilibrium',
                        load_condition=h.store.artifact(c4)['configuration']['task']['physical_problem']['baseline_load'])
                compiled=compile_question(h,question,tool_use_id='continuity-analysis')
                self.assertEqual(compiled['status'],'ready',compiled)
                self.assertEqual(compiled['request']['candidate'],c4)
                self.assertEqual(compiled['plan_reference'],p2)
                def fake_worker(args,*a,**kw):
                    path=Path(args[-1]);atomic_json(path.with_name('result.json'),dict(status='execution_incomplete',reason='Explicit fixture: no numerical execution'))
                    return SimpleNamespace(returncode=0)
                with patch('tools.service_execution._run_contained',side_effect=fake_worker):
                    result=analysis.dispatch(h,compiled['request'],'continuity-analysis',guard=lambda *a:None,plan_reference=p2)
                raw=h.store.artifact(result['reference']);self.assertEqual(raw['candidate'],c4);self.assertEqual(raw['plan_reference'],p2)
                joined=context(h)['evidence_working_set']['research_workflow']
                self.assertEqual(joined['evaluations'][-1]['plan'],p2)
                self.assertEqual(joined['evaluations'][-1]['candidate'],c4)
                self.assertFalse(joined['candidates'][-1]['unevaluated'])
                with self.assertRaisesRegex(ValueError,'ANALYSIS_PLAN_CANDIDATE_MISMATCH'):
                    analysis.dispatch(h,compiled['request'],'wrong-plan',guard=lambda *a:None,plan_reference=p1)
                out=Path(__file__).resolve().parents[2]/'runs/stage2_workflow';out.mkdir(exist_ok=True,parents=True)
                (out/(('passive' if passive else 'active')+'_workflow.json')).write_text(json.dumps(main_projection(h,joined),indent=2),encoding='utf8')

    def test_frozen_short_choices_include_all_candidates_plans_and_results(self):
        with fixture() as h:
            cs=[generate_candidate(h,request(h,i,True),dict(origin='Offline selector fixture'))['candidate'] for i in range(4)]
            p=diagnose(h,cs[2],'frozen-plan');choices=reference_choices(h)
            schema=reference_schema(plan_schema(['diagnose'],decision_required=True,study=state(h)['spec']),choices,'diagnose')
            payload=diagnosis(cs[2]);wire=main_projection(h,payload)
            for c in cs:self.assertIn(c,choices.values())
            self.assertEqual(choices['plan_1'],p)
            generate_candidate(h,request(h,4,True),dict(origin='Later construction fixture'))
            self.assertEqual(bind_plan_selection(h,expand_references(wire,schema)),payload)
            packet=main_projection(h,context(h)['evidence_working_set']['research_workflow'])
            self.assertNotIn('artifact_id',json.dumps(packet));self.assertIn('plan_1',json.dumps(packet))

    def test_execution_information_is_mode_specific_and_never_launches_or_charges(self):
        for passive in (True,False):
            with self.subTest(passive=passive),host_fixture(passive) as h:
                c=generate_candidate(h,request(h,0,passive),dict(origin='Offline prerequisite fixture'))['candidate'];diagnose(h,c,'prerequisite-plan')
                layers=analysis.diagnostic_layers(dict(status='execution_incomplete'))
                layers['static_qualification']['status']='unqualified'
                r=save(h,dict(candidate=c,status='execution_incomplete',operation='mechanism_structure_v1',diagnostic_layers=layers),'candidate_analysis_result')
                update(h,analysis_results=[r]);before=deepcopy(state(h));cost=h.store.remaining()
                with patch('tools.service_execution._run_contained',side_effect=AssertionError('No worker permitted')):
                    current=context(h);preview=current['evidence_working_set']['execution_preview']
                    brief=agent_decision_brief(h)
                    from tools.research.research_context import information_flow_brief,research_decision_brief_v3
                    delivered=information_flow_brief(brief,research_decision_brief_v3(brief))
                    self.assertEqual(delivered['research_workflow']['active_plan']['candidate'],c)
                    self.assertEqual(delivered['execution_preview']['candidate'],c)
                self.assertEqual(preview['repeat_initialization_failure'],passive)
                self.assertEqual(preview['cost']['reserved_episodes'],10 if passive else 1)
                self.assertEqual('hard-equilibrium' in preview['initializer'],passive)
                self.assertEqual(h.store.remaining(),cost);self.assertEqual(state(h),before)

    def test_stop_short_result_handoff_keeps_complete_citation_and_identity_gates(self):
        with fixture() as h:
            cs=[generate_candidate(h,request(h,i,True),dict(origin='Offline stop fixture'))['candidate'] for i in range(2)]
            refs=[save(h,dict(candidate=c,status='execution_incomplete',operation='mechanism_structure_v1',owning_study=h.run_id),
                'candidate_analysis_result') for c in cs]
            update(h,analysis_results=refs)
            wf=context(h)['evidence_working_set']['research_workflow']
            self.assertEqual([r['reference'] for r in wf['evaluations']],refs)
            self.assertEqual([r['candidate'] for r in wf['evaluations']],cs)
            stop=diagnosis(cs[-1]);stop['action']='stop';stop['decision']['research_intent']='STOP';stop['supporting_evidence']=refs[:1]
            with patch.object(core,'guard'),self.assertRaisesRegex(ValueError,'STOP_MUST_CITE_ALL'):
                core.dispatch(h,stop,'missing-citation')
            stop['supporting_evidence']=refs
            strong=deepcopy(stop);strong['decision']['claimed_inference']='local_diagnostic'
            with patch.object(core,'guard'),self.assertRaisesRegex(ValueError,'EVIDENCE_DESIGN_IDENTITY_MISMATCH'):
                core.dispatch(h,strong,'cross-design-claim')
            schema=reference_schema(plan_schema(['stop'],decision_required=True,study=state(h)['spec']),reference_choices(h),'stop')
            expanded=expand_references(main_projection(h,stop),schema)
            with patch.object(core,'guard'):
                accepted=core.dispatch(h,expanded,'complete-citations')
            self.assertTrue(accepted['result']['accepted_stop'])

    def test_parameter_group_and_schema_correction_preserve_original_input(self):
        from tools.research.evidence_intent import resolve_evidence_intent
        with fixture() as h:
            c=generate_candidate(h,request(h,0,True),dict(origin='Offline navigation fixture'))['candidate'];diagnose(h,c,'schema-plan')
            rows=resolve_evidence_intent(h,dict(subject=c,topic='structure_parameters',group='segment'))
            self.assertGreater(len(rows['facts']),1)
            for row in rows['facts']:self.assertIn('applicable_methods',row);self.assertNotIn('execution_semantics',row)
            bad=dict(version='scientific_question_v4',domain='structure',operation='inspect',structure=dict(
                effect_semantics='mechanism_effect',operating_point='re_equilibrated',control_treatment='no_active_control',target=dict(quantity='constraint_active_set')))
            original=deepcopy(bad);before=h.store.remaining()
            result=compile_question(h,bad,tool_use_id='wrong-field')
            self.assertEqual(result['status'],'needs_choice');self.assertFalse(result['scientific_execution_started'])
            self.assertEqual(result['additional_mathematical_evaluations'],0)
            self.assertTrue(any(r.get('expected_field')=='structure.operation' for r in result['issues']))
            self.assertEqual(bad,original);self.assertEqual(h.store.remaining(),before)

    def test_qualification_observation_and_active_available_are_distinct(self):
        geometry=analysis.diagnostic_layers(dict(initial_geometry=dict(status='computed',contact_count=228)))['geometry']
        self.assertEqual(geometry['computation_status'],'completed');self.assertNotEqual(geometry['status'],'passed')
        dyn=analysis.diagnostic_layers(dict(kind='passive_dynamic_execution_v2',status='completed',episodes=[]))
        self.assertEqual(dyn['dynamic_validation']['computation_status'],'completed')
        self.assertNotEqual(dyn['dynamic_validation']['status'],'passed')
        self.assertNotIn('highest_passed_layer',analysis.diagnostic_overview(dyn))
        for available,expected in ((False,'unqualified'),(None,'not_evaluated'),(True,'passed')):
            point=dict(name='target_equilibrium')
            if available is not None:point['available']=available
            value=dict(status='computed',construction=dict(success=True),model=dict(operating_point=point))
            self.assertEqual(analysis.diagnostic_layers(value)['static_qualification']['status'],expected)
        value=dict(status='computed',model=dict(operating_point=dict(name='halfway_waypoint',available=True)),
            raw=dict(records=[{},dict(derivative_check=dict(dynamics=dict(passed=False)))]))
        layers=analysis.diagnostic_layers(value)
        self.assertEqual(layers['numerical_solve']['status'],'unqualified')
        self.assertEqual(layers['static_qualification']['status'],'not_applicable')


if __name__=='__main__':unittest.main()
