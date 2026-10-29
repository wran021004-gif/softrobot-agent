"""Small offline M1 interface fixtures. All returned numbers are fabricated.

Real candidate generation and frozen task admission are exercised. The contained
worker boundary is replaced in-process; no Provider, numerical or physical worker
is launched. This route is an engineering test, never a prescribed Study plan.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.state_io import atomic_json, digest, read
from tools.research import agent, analysis, core, reporter
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest, ControlSeedRequest
from tools.research.design import generate_candidate
from tools.research.evidence_views import result_card, quantitative_facts
from tools.research.nonlinear_capability import T1, T2, T1_OPERATION, T2_OPERATION, t1_summary, saved_context
from tools.research.physical_replay import seed_control
from tools.research.provider import provider_schema
from tools.research.research_context import agent_decision_brief, research_decision_brief_v3, information_flow_brief
from tools.research.state import state, update
from tools.research.task_constraints import mathematical_method_view, describe_analysis_requirements, analysis_capabilities


def fixture_host():
    """Prepare a fresh isolated M1 central_high condition, not a historical Store."""
    cfg=read(ROOT/'configs/research/study_s125_cold.json')
    cfg.update(study_id='p63a-fixture-'+uuid4().hex[:8],
        task=str(ROOT/'tasks/bf7_shared_reach_v1_central_high.json'),
        family_space=str(ROOT/'configs/research/family_space_stage0_base_only_v1.json'),
        control=str(ROOT/'configs/research/control.json'),
        mathematical_methods={T1:'OFFLINE FIXTURE ONLY',T2:'OFFLINE FIXTURE ONLY'},
        family_sensitivity_variables=dict(version='family_sensitivity_v2',variables=['segments.*.length_m']))
    cfg['defaults']=str(ROOT/'configs/research/family_study_defaults.json')
    cfg['budgets']['mathematical_evaluations']=12
    cfg['research_decisions'].update(analysis_interface='bound_scientific_variables_v2',
        architecture='english_decision_v1',tool_schema_policy=dict(version='research_information_flow_v1'),
        role_policy=dict(version='research_roles_v2',main=dict(thinking='disabled',reasoning_effort='none'),
            reporter=dict(thinking='enabled',reasoning_effort='low')),
        conversation_policy=dict(version='recent_round_trace_v1',trace_limit=8),
        language_policy=dict(version='english_sources_v1',authored_language='en'))
    folder=ROOT/'runs'/cfg['study_id'];folder.mkdir(parents=True)
    path=ROOT/'configs/research'/('._'+cfg['study_id']+'.json')
    atomic_json(path,cfg)
    try:h=core.prepare(path,folder)
    finally:path.unlink()
    pilot=state(h)['pilot'];pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback')
    update(h,freeze='p63a-offline-fixture-no-science',pilot=pilot)
    return h


def generate(h, lengths=(.16,.11)):
    request=dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
        segment_count=2,tendon_count=4,segments={str(i):dict(length_m=x) for i,x in enumerate(lengths)})
    return generate_candidate(h,request,dict(origin='P63A offline engineering fixture'))['candidate']


def t1_request(h,candidate):
    source=seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'))['source']
    spec=state(h)['spec'];duration=spec['analysis_protocol']['duration_s']
    return dict(candidate=candidate,operation=T1_OPERATION,model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=source,settings=dict(version='local_control_search_v2',
            method='response',knots_s=[0.,duration],correction_window_s=[0.,duration],
            evaluation_requests=4,iterations=1,active_coefficients=[0])))


def diagnose(h,candidate,method):
    plan=dict(action='diagnose',hypothesis='Offline interface hypothesis',expected_observation='Bound request',
        weakening_observation='Binding rejected',fixed_conditions='Frozen M1 central_high',
        stopping_condition='No real computation',interpretation='Synthetic fixture only',
        decision=dict(hypothesis_id='offline-p63a',research_intent='DIAGNOSE',selected_method=method,
            selected_candidate=candidate,requested_budget=0))
    with patch.object(core,'guard'):return core.dispatch(h,plan,'diagnose-'+uuid4().hex[:8])


def synthetic_t1(request):
    """A contained-worker replacement with explicit fixture provenance."""
    cfg=request['configuration'];query=AnalysisRequest.model_validate(request['query'])
    context=request['design_context'];schedule=context['schedule']
    parts={c['id']:c for c in cfg['robot']['structure']['data']['components']}
    lengths=[parts['segment_'+str(i)]['length_m'] for i in range(2)]
    j=.5+2*(lengths[0]-.16)-3*(lengths[1]-.11)
    speed_limit=next(c['radius'] for c in request['task_analysis']['constraints'] if c['constraint_id']=='holding_max_speed_m_s')
    def measure(x):return dict(terminal_position_error_m=.001,holding_max_position_error_m=.001,
        holding_max_speed_m_s=speed_limit*(1+x),signed_maximum_excess=x,normalized_gap=max(0,x),
        worst_constraint=dict(kind='holding_speed'))
    initial,best=measure(j+.2),measure(j)
    times=request['task_analysis']['time_grid_s'];target=cfg['task']['goal']['data']['target_m']
    def outputs(m):return dict(times_s=times,tip_positions_m=[[target[0]+.001,*target[1:]] for _ in times],
        tip_velocities_m_s=[[m['holding_max_speed_m_s'],0.,0.] for _ in times])
    search=dict(best=dict(measure=best,outputs=outputs(best),reference='fabricated-rollout',label='local_response_proposal',coefficients_n=[0.]*8),
        candidates=[dict(measure=initial,outputs=outputs(initial),label='baseline'),dict(measure=best,outputs=outputs(best),label='local_response_proposal')],
        stop_reason='iteration_limit',cost_feedback=dict(evaluation_callbacks=4),iterations_started=1,
        local_responses=[dict(diagnostic='resolved_local_response')])
    raw=dict(optimization=search,original_schedule=schedule,optimized_schedule=schedule,
        initial_state=dict(actual_time_s=0.,configuration_identity=digest(cfg)),
        cost=dict(model_builds=1,rollouts=4,physics_steps=400,optimization_evaluations=4))
    value=dict(status='computed',operation=query.operation,binding=request['binding'],protocol=plain(query.protocol),
        native_dynamics=raw,native_analysis=dict(basis=dict(model='OFFLINE SYNTHETIC FIXTURE'),quantities=[],
            comparison=dict(baseline=initial,best=best),interpretation='Fabricated offline fixture',
            limitations=['No computation performed'],unresolved=['Synthetic numbers establish no scientific result']),task_acceptance='unmeasured',
        fixture='Fabricated numbers for interface verification; no science or simulation executed.')
    requirements=describe_analysis_requirements(cfg,request['binding'])
    value=analysis.scoped_result(value,requirements,request['analysis_applicability'],query)
    value['nonlinear_capability']=t1_summary(value,query.control_optimization.settings)
    return value


def offline_dispatch(h,query,key):
    def contained(command,log,timeout,**kwargs):
        request=read(Path(command[-1]))
        if request['query']['operation']==T1_OPERATION:value=synthetic_t1(request)
        else:
            # Existing T2 arithmetic only, operating on the admitted saved fixtures.
            value=analysis.calculate(request['configuration'],request['binding'],request['query'],
                design_context=request['design_context'])
        atomic_json(Path(command[-1]).with_name('result.json'),value)
        return SimpleNamespace(returncode=0)
    with patch('tools.service_execution._run_contained',side_effect=contained):
        return analysis.dispatch(h,query,key,guard=lambda *a:None,origin='engineering_preflight')


class MathInterfaceTests(unittest.TestCase):
    def test_candidate_parameters_task_units_and_l0_wire(self):
        from tests.research.test_information_flow import packet
        from tests.research.test_recent_round_tools import run_fixture
        h=fixture_host();candidate=generate(h)
        view=mathematical_method_view(h,candidate);research=view['research_opportunities']
        rows={p['parameter_id']:p for p in research['parameters']}
        for path,bounds in [('segments.0.length_m',(.08,.24)),('segments.1.length_m',(.06,.20))]:
            self.assertEqual((rows[path]['minimum'],rows[path]['maximum']),bounds)
            self.assertEqual(rows[path]['unit'],'m');self.assertTrue(rows[path]['study_authorized'])
            self.assertIn(T2,[m['method'] for m in rows[path]['method_links']])
        self.assertFalse(rows['segments.0.cells']['continuous_perturbation'])
        self.assertEqual(research['task_binding']['task_family'],'task.reach')
        self.assertEqual([m['constraint']['signal']['units'] for m in research['metrics'][:-1]],['m','m','m/s'])
        before=deepcopy(state(h));readback=core.read_evidence(h,dict(reference=candidate,
            view='mathematical_capabilities',pointer='/research_opportunities'),record_read=False)
        self.assertEqual(readback,research);self.assertEqual(state(h),before)
        wire=run_fixture(h,[None])[0];l0=packet(wire)['mathematical_research']
        self.assertEqual(l0['candidate'],candidate);self.assertNotIn('segments.0.length_m',json.dumps(l0))
        self.assertEqual(l0['parameters']['continuous_authorized'],2)
        self.assertEqual(l0['parameters']['categories'],['segment'])
        self.assertIn('controller',l0['parameters']['registered_categories'])
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertTrue(all(t['function']['parameters'] for t in wire['tools']))

    def test_selected_request_binding_and_provider_schema_both_t2_forms(self):
        h=fixture_host();candidate=generate(h);view=mathematical_method_view(h,candidate)
        ref=dict(artifact_id='a'*64,media_type='application/json')
        payloads=[(T1,dict(control_optimization=t1_request(h,candidate)['control_optimization'])),
            (T2,dict(nonlinear_response=dict(variable='segments.0.length_m',unit='m',t1_results=[ref]*3))),
            (T2,dict(nonlinear_response=dict(version='nonlinear_response_v2',directions=[dict(
                direction_id='length0',variables={'segments.0.length_m':1.},coordinate_unit='m',
                coordinates=[0.,-.005,.005],t1_results=[ref]*3)])))]
        for method,payload in payloads:
            detail=view['methods'][method]
            schema=provider_schema(agent.selected_analysis_schema(method,detail,bound=True))
            Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(payload)
            self.assertFalse({'allOf','anyOf','oneOf','not'} & schema.keys())
            diagnose(h,candidate,method)
            with patch.object(agent,'selected_analysis',return_value=(method,detail)):
                full=agent.bind_selected_analysis_request(h,payload,tool_use_id='offline-'+method)
            self.assertEqual(full['candidate'],candidate);self.assertEqual(full['protocol'],state(h)['spec']['analysis_protocol'])
            self.assertEqual(full['operation'],detail['operation']);AnalysisRequest.model_validate(full)
            self.assertNotIn('candidate',schema['properties'])
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_task_coverage_stays_method_specific(self):
        from tools.research.native_control import nonlinear_task_reason
        from tools.research_tasks import task_adapter
        h=fixture_host();candidate=generate(h);cfg=deepcopy(h.store.artifact(candidate)['configuration'])
        cfg['task']=read(ROOT/'tasks/bf5_position_tool_axis_v1.json')['task']
        requirements=task_adapter(cfg).analysis_requirements({})
        rows={r['operation']:r for r in analysis_capabilities(cfg,requirements,state(h)['spec']['analysis_protocol'])}
        self.assertEqual(rows['task_capability']['planning_status'],'unsupported')
        self.assertEqual(rows['mujoco_direct_control_v1']['planning_status'],'requires_parameters')
        self.assertIsNotNone(nonlinear_task_reason(cfg['task']['family']))
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_five_saved_t1_two_parameters_t2_reporter_main_and_budget(self):
        h=fixture_host();lengths=[(.16,.11),(.155,.11),(.165,.11),(.16,.105),(.16,.115)]
        candidates=[generate(h,x) for x in lengths]
        results=[offline_dispatch(h,t1_request(h,c),'fixture-t1-'+str(i)) for i,c in enumerate(candidates)]
        refs=[r['reference'] for r in results];base=candidates[0]
        view=mathematical_method_view(h,base)
        query=view['methods'][T2]['request_template']
        self.assertEqual(query['nonlinear_response']['version'],'nonlinear_response_v2')
        self.assertEqual(len(query['nonlinear_response']['directions']),2)
        result=offline_dispatch(h,query,'fixture-t2')
        diagnose(h,base,T2)
        self.assertEqual(state(h)['mathematical_evaluations'],6)
        again=offline_dispatch(h,query,'fixture-t2')
        self.assertEqual(again['operation_reuse']['additional_analysis_evaluations'],0)
        card=plain(result_card(h,result['reference']))
        quantities=card['mathematics']['quantities']
        self.assertEqual(len(quantities),4)
        self.assertTrue(any(q['control_reoptimization']=='fixed_control' for q in quantities))
        self.assertTrue(all(q['source']['pointer'].endswith('/central') for q in quantities))
        raw=h.store.artifact(result['reference'])
        self.assertEqual(quantitative_facts(raw,result['reference'])['nonlinear_research']['directions'][0]['status'],'unresolved')
        self.assertEqual(raw['nonlinear_response']['cost']['physics_steps'],0)
        self.assertEqual(raw['nonlinear_response']['cost']['reused_t1_results'],5)
        delivery=reporter.scientific_feedback(h,result)
        self.assertEqual(delivery['interpretation_status'],'deferred')
        self.assertEqual(delivery['task_acceptance'],'unmeasured')
        report_ref=delivery['report_reference'];saved=h.store.artifact(report_ref)
        handoff=reporter.reporter_handoff_summary(h,report_ref,saved)
        self.assertTrue(handoff['findings'][0]['quantitative_facts']['nonlinear_research'])
        brief=agent_decision_brief(h);l0=information_flow_brief(brief,research_decision_brief_v3(brief))
        self.assertIn(result['reference'],[f['result_reference'] for f in l0['verified_facts']])
        self.assertFalse(state(h)['results']);self.assertFalse(state(h)['physical_replays'])
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        # Units and source comparability still use the original admission gates.
        # Legacy units have an exact gate; no unit is inferred by the interface.
        legacy={**query,'nonlinear_response':dict(variable='segments.0.length_m',unit='Pa',t1_results=refs[:3])}
        self.assertEqual(saved_context(h,AnalysisRequest.model_validate(legacy))['not_comparable'],'PARAMETER_UNIT_MISMATCH')
        spec=state(h)['spec'];spec['budgets']['mathematical_evaluations']=6;update(h,spec=spec)
        self.assertEqual(mathematical_method_view(h,base)['methods'][T2]['planning_status'],'unauthorized')
        with self.assertRaisesRegex(ValueError,'BUDGET'):
            offline_dispatch(h,query,'exhausted-budget')


if __name__=='__main__':unittest.main()
