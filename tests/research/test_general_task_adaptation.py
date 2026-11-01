"""General interface readiness only: Mock motion, no Provider/worker/integration."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator
from tools.research import core,analysis
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.nonlinear_capability import T1, T2
from tools.research.scientific_intent import DIRECT, compile_question, question_schema, control_method_choices
from tools.research.state import state, update
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import read,atomic_json
from tests.research.test_cross_task_integration import fixture_directory, fixture_host, plan,perfect_tracking_worker


def resolved_conditions(conditions, *, template='study_r0_m1_v4_draft.json', public_domain=False):
    """New offline configuration from public R0 sources, never historical answers."""
    cfg=read(ROOT/'configs/research'/template)
    cfg['study_id']='u2-mock-config-'+uuid4().hex[:8]
    cfg['task_conditions']=deepcopy(conditions)
    if public_domain:cfg.pop('topology_scope',None)  # Original C1 public Base-only domain.
    path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json')
    atomic_json(path,cfg)
    try:return resolve(path)
    finally:path.unlink()


def heterogeneous_conditions():
    conditions=read(ROOT/'configs/research/study_r0_m1_v4_draft.json')['task_conditions']
    backend=resolve(ROOT/'configs/research/study_bf5_public.json')['configuration']['policy']['backend']
    return [*conditions,dict(condition_id='tool_axis',task='../../tasks/bf5_position_tool_axis_v1.json',
        execution=dict(control='control_bf5_tool_axis.json',backend=backend))]


def v4_question(**changes):
    return dict(version='scientific_question_v4',domain='control',control=dict(
        question_type='control_feasibility',effect_semantics='reoptimized_task_capability',
        control_scope=dict(mode='full_task'),control_search_effort=dict(
            method='response',knot_count=4,iterations=1,evaluation_requests=1),**changes))


def deliver_certificates(h, refs):
    from tests.research.test_recent_round_tools import run_fixture
    spec=deepcopy(state(h)['spec']);spec['mode']='formal_research'
    update(h,spec=spec)  # Mock HTTP fixture only, as in the existing certificate tests.
    with patch('tools.research.agent.credential',return_value='offline-fixture'), \
            patch('tools.research.reporter._wire',side_effect=ValueError('MOCK_REPORTER')):
        return run_fixture(h,[('research_route',dict(tool='evidence_read')),
            *[('evidence_read',dict(reference=ref,view='acceptance_certificate')) for ref in refs],None],limit=len(refs)+2)


class GeneralTaskAdaptationTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','mujoco.mj_step',
                     'tools.research.provider.load_credential'):
            p=patch(name,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_PHYSICS'))
            p.start();self.addCleanup(p.stop)

    def test_v4_candidate_catalog_routes_native_without_t1_impersonation(self):
        summary=[]
        for leaf in ('study_tracking_public.json','study_bf5_public.json','study_bf6_public.json'):
            with self.subTest(leaf=leaf), fixture_directory() as folder:
                h=fixture_host(folder,leaf);spec=deepcopy(state(h)['spec'])
                spec['research_decisions']=resolve(ROOT/'configs/research/study_r0_m1_v4_draft.json')['research_decisions']
                spec.setdefault('mathematical_methods',{}).update({T1:'MOCK ONLY',T2:'MOCK ONLY'})
                spec['budgets']['mathematical_evaluations']=4
                update(h,spec=spec)
                with patch('tools.research.core.guard'),patch('tools.research.state.guard'):
                    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                        segment_count=2,tendon_count=6)
                    c=core.dispatch(h,plan('generate',generation=request),'generate')['result']['candidate']
                    seed=core.dispatch(h,plan('initialize_control',c,control_seed=dict(candidate=c)),'seed')['result']
                    diagnosis=plan('diagnose',c,next_research_action='control_feasibility')
                    diagnosis['decision'].pop('selected_method')
                    core.dispatch(h,diagnosis,'diagnose')
                view=mathematical_method_view(h,c)
                choices=control_method_choices(view)
                self.assertEqual([r['method'] for r in choices if r['selectable']],[DIRECT],choices)
                self.assertFalse(view['methods'][T1]['kernel_supported'])
                self.assertFalse(view['methods'][T2]['kernel_supported'])
                q=v4_question();schema=question_schema(spec,h.store.artifact(c),'control_feasibility',control_methods=choices)
                Draft202012Validator(schema).validate(q)
                compiled=compile_question(h,q,tool_use_id='mock-native-compile')
                self.assertEqual(compiled['status'],'ready',compiled)
                self.assertEqual(compiled['method'],DIRECT)
                full=compiled['request'];AnalysisRequest.model_validate(full)
                self.assertEqual(full['operation'],DIRECT)
                self.assertEqual(full['control_optimization']['source'],seed['source'])
                self.assertEqual(full['control_optimization']['settings']['evaluation_requests'],1)
                self.assertEqual(full['protocol'],spec['analysis_protocol'])
                rejected=compile_question(h,v4_question(numerical_method=T1),tool_use_id='mock-invalid-t1')
                self.assertEqual(rejected['reason'],'INVALID_SCIENTIFIC_V4_INPUT')
                self.assertFalse(rejected['scientific_execution_started'])
                closed=deepcopy(spec);closed['budgets']['mathematical_evaluations']=0
                update(h,spec=closed)
                self.assertNotEqual(compile_question(h,q,tool_use_id='mock-no-budget')['status'],'ready')
                self.assertEqual(state(h)['mathematical_evaluations'],0)
                self.assertFalse(state(h)['physical_replays'])
                update(h,spec=spec)
                captured=[]
                def mock_worker(command,log,timeout,**kwargs):
                    captured.append(read(Path(command[-1])))
                    atomic_json(Path(command[-1]).with_name('result.json'),dict(status='incomplete',
                        task_acceptance='unmeasured',fixture='MOCK worker admission only; no numerical calculation'))
                    return SimpleNamespace(returncode=0)
                with patch('tools.service_execution._run_contained',side_effect=mock_worker):
                    admitted=analysis.dispatch(h,full,'mock-direct-worker-admission',guard=lambda *a:None,origin='engineering_preflight')
                self.assertEqual(len(captured),1)
                self.assertEqual(captured[0]['configuration']['task'],h.store.artifact(c)['configuration']['task'])
                self.assertEqual(captured[0]['query']['operation'],DIRECT)
                self.assertEqual(state(h)['mathematical_evaluations'],1)  # Mock receipt only.
                self.assertNotIn('nonlinear_capability',h.store.artifact(admitted['reference']))
                cfg=captured[0]['configuration']
                if cfg['task']['family']=='task.oriented_tracking':
                    from schemas.platform import SessionInput
                    from extensions.tendon_family.backends import check_rigid_tool_definition
                    self.assertEqual(check_rigid_tool_definition(SessionInput.model_validate(cfg)),cfg['task']['goal']['data']['rigid_tool'])
                summary.append(dict(scenario=leaf,method=DIRECT,mock_worker_admitted=True,t1_t2_not_applicable=True,
                    backend=cfg['policy']['backend'],task_goal=cfg['task']['goal'],evaluator=cfg['task']['evaluator'],timing=cfg['task']['timing'],
                    constraints=captured[0]['task_analysis']['constraints'],dynamic_schema=schema))
        atomic_json(ROOT/'runs/u1-u2-readiness/mock_native.json',dict(scope='MOCK worker admission only; no native calculation',
            scenarios=summary,actual_provider_requests=0,formal_math_workers=0,new_integrations=0))

    def test_finite_conditions_and_physical_model_binding(self):
        from tools.research.conditions import configuration_for_condition
        rows=heterogeneous_conditions()
        tracking=resolve(ROOT/'configs/research/study_tracking_public.json')
        fifth=dict(condition_id='tracking',task='../../tasks/bf4_tracking_direction_change_v1.json',execution=dict(
            control='control_bf4_tracking.json',backend=tracking['configuration']['policy']['backend']))
        for conditions in (rows[:1],rows,[*rows,fifth]):
            spec=resolved_conditions(conditions,public_domain=True)
            self.assertEqual(len(spec['task_conditions']),len(conditions))
        duplicate=[*rows,deepcopy(rows[0])]
        with self.assertRaisesRegex(ValueError,'FINITE_UNIQUE'):resolved_conditions(duplicate)
        spec=resolved_conditions(rows,public_domain=True);condition=deepcopy(spec['task_conditions'][-1])
        cfg=configuration_for_condition(spec['configuration'],condition)
        self.assertIsNone(cfg['policy']['controller']['parameters']['data']['settling'])
        self.assertEqual(cfg['task']['goal']['data'],condition['task']['goal']['data'])
        condition['task']['environment']['data']['environment']['gravity_m_s2'][2]=-1.
        with self.assertRaisesRegex(ValueError,'IDENTICAL_PHYSICAL_MODEL'):
            configuration_for_condition(spec['configuration'],condition)
        from tools.research.config import frozen_analysis_protocol
        m2=resolve(ROOT/'configs/research/study_multicondition_public.json')
        short=dict(condition_id='short_reach',task='../../tasks/bf2_multidirectional_hold_frozen_v1_zero.json')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_MATCHING_ANALYSIS_PROTOCOL'):
            resolved_conditions([rows[0],short])
        short['execution']=dict(analysis_protocol=m2['analysis_protocol'])
        mixed=resolved_conditions([rows[0],short])
        self.assertEqual(frozen_analysis_protocol(mixed,dict(condition_id='short_reach')),m2['analysis_protocol'])
        condition=deepcopy(spec['task_conditions'][-1])
        condition['execution']['backend']['parameters']['data']['friction']=[.1,0.,0.]
        with self.assertRaisesRegex(ValueError,'IDENTICAL_PHYSICAL_MODEL'):
            configuration_for_condition(spec['configuration'],condition)

    def test_mock_heterogeneous_joint_certificates_and_original_select(self):
        from tools.research.conditions import joint_assessment,condition_candidate
        from tools.research.evidence_views import acceptance_certificate
        from tools.research.feedback import eligibility,result_view
        from tools.research.object_choices import main_projection
        from tools.research_tasks import aggregate_acceptance
        from tests.research.test_information_flow import packet
        spec=resolved_conditions(heterogeneous_conditions(),public_domain=True)
        spec['budgets'].update(provider_requests=12,protected_provider_requests=0)
        spec['configuration']['policy']['budget']['model_calls']=12
        with fixture_directory() as folder, patch('tests.research.test_cross_task_integration.resolve',return_value=spec):
            h=fixture_host(folder,physical_launches=4)
            update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
            refs=[];compiled=[];sources=[]
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=4)
                root=core.dispatch(h,plan('generate',generation=request),'mock-c1-generate')['result']['candidate']
                for i,condition in enumerate(spec['task_conditions']):
                    c=condition_candidate(h,root,condition['condition_id'])
                    cfg=h.store.artifact(c)['configuration']
                    self.assertEqual(cfg['robot'],h.store.artifact(root)['configuration']['robot'])
                    seed=core.dispatch(h,plan('initialize_control',c,control_seed=dict(candidate=c)),'mock-c1-seed-'+str(i))['result']
                    sources.append(seed['source'])
                    diagnosis=plan('diagnose',c,next_research_action='control_feasibility');diagnosis['decision'].pop('selected_method')
                    core.dispatch(h,diagnosis,'mock-c1-diagnose-'+str(i))
                    result=compile_question(h,v4_question(),tool_use_id='mock-c1-analysis-'+str(i))
                    self.assertEqual(result['status'],'ready',result)
                    self.assertEqual(result['method'],T1 if i<3 else DIRECT)
                    compiled.append(result['method'])
                    active_schema=question_schema(state(h)['spec'],h.store.artifact(c),'control_feasibility',
                        control_methods=control_method_choices(mathematical_method_view(h,c)))
                    with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                        replay=core.dispatch(h,plan('physical_replay',c,physical_replay=dict(candidate=c,source=seed['source'])),
                            'mock-c1-replay-'+str(i))['result']
                    refs.append(replay['reference'])
                    self.assertTrue(acceptance_certificate(h,refs[-1])['complete_acceptance_view'])
                self.assertEqual(len(set(r['artifact_id'] for r in sources)),4)
                self.assertFalse(eligibility(h,refs,selection=True)['eligible'])
                self.assertTrue(joint_assessment(h,refs,require_reads=False)['aggregation']['all_scheduled_accepted'])
                wires=deliver_certificates(h,refs)
                self.assertTrue(eligibility(h,refs,selection=True)['eligible'])
                joint=joint_assessment(h,refs[::-1]);aggregate=joint['aggregation']
                self.assertEqual(aggregate['version'],'2.0.0');self.assertEqual(aggregate['metrics'],{})
                self.assertIsNone(joint['task_gap']['normalized_gap'])
                self.assertEqual(set(joint['task_gap']['condition_gaps']),{c['condition_id'] for c in spec['task_conditions']})
                with self.assertRaisesRegex(ValueError,'DUPLICATE_TASK_CONDITION'):joint_assessment(h,[refs[0],refs[0]])
                with self.assertRaisesRegex(ValueError,'ALL_FROZEN'):joint_assessment(h,refs[:3])
                records=[dict(case_id=e['case_id'],seed=e['seed'],repetition=e['repetition'],acceptance=e['acceptance'],
                    receipt=e['receipt'],**{k:e['source_evidence'][k] for k in ('evaluation','profile','simulation')}) for e in aggregate['entries']]
                kw=dict(schedule=aggregate['schedule'],condition_contract='heterogeneous_conditions_v1')
                self.assertTrue(aggregate_acceptance(records,4,**kw)['all_scheduled_accepted'])
                self.assertFalse(aggregate_acceptance(records[:3],4,**kw)['all_scheduled_accepted'])
                with self.assertRaisesRegex(ValueError,'AGGREGATION_TASK_PROTOCOL_MISMATCH'):
                    aggregate_acceptance(records,4,schedule=aggregate['schedule'])
                wrong=deepcopy(records);wrong[0]['acceptance']['task_identity']='another-frozen-task'
                with self.assertRaisesRegex(ValueError,'CONDITION_ACCEPTANCE_TASK_BINDING_MISMATCH'):aggregate_acceptance(wrong,4,**kw)
                for mutate in ('component','source','receipt','duplicate_execution','accepted_flag'):
                    invalid=deepcopy(records)
                    if mutate=='component':invalid[0]['acceptance']['components']['force_bounds']['passed']=False
                    if mutate=='source':invalid[0]['profile']=invalid[1]['profile']
                    if mutate=='receipt':invalid[0]['receipt']['cache_hit']=True
                    if mutate=='duplicate_execution':invalid[0]['receipt']['execution_id']=invalid[1]['receipt']['execution_id']
                    if mutate=='accepted_flag':invalid[0]['acceptance']['accepted']=False
                    self.assertFalse(aggregate_acceptance(invalid,4,**kw)['all_scheduled_accepted'])
                selected=core.dispatch(h,plan('select',selected_execution=refs[::-1]),'mock-c1-select')
                self.assertTrue(selected['result']['selected'])
                chosen=state(h)['selected'];view=result_view(h,chosen)
                self.assertTrue(view['passed']);self.assertEqual(view['metrics'],{})
                certificate=acceptance_certificate(h,chosen)
                self.assertTrue(certificate['complete_acceptance_view'],certificate['validation_issues'])
                self.assertFalse(eligibility(h,refs,selection=True)['eligible'])
                core.export(h,folder/'export')
                self.assertEqual(read(folder/'export/design_package.json')['aggregation']['version'],'2.0.0')
                atomic_json(ROOT/'runs/u1-u2-readiness/mock_c1.json',dict(
                    scope='MOCK ONLY: fabricated perfect motion and Mock HTTP; no real C1 reproduction',
                    compiled_methods=compiled,aggregation=main_projection(h,aggregate),joint_task_gap=main_projection(h,joint['task_gap']),
                    main_short_object=packet(wires[-1]),
                    dynamic_schema=active_schema,
                    configuration_example=heterogeneous_conditions(),
                    select_passed=True,actual_provider_requests=0,formal_math_workers=0,new_integrations=0))

    def test_original_three_reach_and_three_external_force_joint_contracts(self):
        from tools.research.conditions import joint_assessment
        from tools.research.feedback import eligibility
        scenarios=[('M1','study_r0_m1_v4_draft.json'),('M2','study_multicondition_public.json')]
        summary=[]
        for label,template in scenarios:
            with self.subTest(label=label),fixture_directory() as folder:
                conditions=read(ROOT/'configs/research'/template)['task_conditions']
                if label=='M2':conditions.append(dict(condition_id='negative',task='../../tasks/bf2_multidirectional_hold_frozen_v1_negative.json'))
                spec=resolved_conditions(conditions,template=template)
                spec['budgets'].update(provider_requests=10,protected_provider_requests=0)
                spec['configuration']['policy']['budget']['model_calls']=10
                with patch('tests.research.test_cross_task_integration.resolve',return_value=spec):h=fixture_host(folder)
                update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
                refs=[];forces=[]
                with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=6)
                    root=core.dispatch(h,plan('generate',generation=request),'mock-'+label+'-generate')['result']['candidate']
                    for i,condition in enumerate(spec['task_conditions']):
                        seed=core.dispatch(h,plan('initialize_control',root,control_seed=dict(candidate=root,condition_id=condition['condition_id'])),
                            'mock-'+label+'-seed-'+str(i))['result']
                        cfg=h.store.artifact(seed['candidate'])['configuration']
                        self.assertEqual(cfg['task']['environment'],condition['task']['environment'])
                        forces.append(cfg['task']['environment']['data'].get('external_forces',[]))
                        with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                            replay=core.dispatch(h,plan('physical_replay',seed['candidate'],physical_replay=dict(
                                candidate=seed['candidate'],source=seed['source'])),'mock-'+label+'-replay-'+str(i))['result']
                        refs.append(replay['reference'])
                    if label=='M1':deliver_certificates(h,refs)
                    else:
                        for ref in refs:core.read_evidence(h,dict(reference=ref,view='full'))
                    joint=joint_assessment(h,refs)
                    self.assertEqual(joint['aggregation']['version'],'1.0.0')
                    self.assertTrue(joint['aggregation']['all_scheduled_accepted'])
                    self.assertTrue(eligibility(h,refs,selection=True)['eligible'])
                    self.assertTrue(core.dispatch(h,plan('select',selected_execution=refs),'mock-'+label+'-select')['result']['selected'])
                    self.assertEqual(h.store.remaining()['used']['backend_solves'],3)
                    if label=='M2':self.assertEqual([len(row) for row in forces],[0,1,1])
                    summary.append(dict(scenario=label,condition_count=3,aggregation_version='1.0.0',mock_joint_select=True,
                        frozen_external_forces=forces,actual_provider_requests=0,new_integrations=0))
        atomic_json(ROOT/'runs/u1-u2-readiness/mock_homogeneous.json',dict(scope='MOCK ONLY; fabricated motion',scenarios=summary))


if __name__=='__main__':unittest.main()
