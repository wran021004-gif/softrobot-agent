"""M1 wiring only: saved F2 arrays are synthetic B3 fixtures, never new science."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests.research.c3_readiness_audit import C3Archive
from tools.platform_store import plain
from tools.research import analysis, core, design, optimal_capability as opt, reporter
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest, Plan
from tools.research.evidence_views import result_card
from tools.research.research_context import compact_scientific_delivery, agent_decision_brief
from tools.research.research_context import import_history
from tools.research.state import state, update, save, require_authorization, guard
from tools.research.task_constraints import describe_analysis_requirements, mathematical_method_view
from tools.state_io import atomic_json, digest, read


def fixture_host(arm):
    from schemas.platform import ProjectConfig
    folder=ROOT/'runs'/('b3-t2-fixture-'+uuid4().hex[:8])
    with patch.object(core,'ProjectConfig',side_effect=lambda **kw:ProjectConfig(
            **{**kw,'project_id':folder.name,'grant_id':folder.name})):
        return core.prepare(ROOT/f'configs/research/study_b3_t2_pilot_{arm}_draft.json',folder)


class B3T2Tests(unittest.TestCase):
    def test_r0_archived_m2_complete_wire_and_handoff(self):
        import httpx
        from openai import AsyncOpenAI
        from tools.research.agent import live_model_class, plan_schema
        from tools.research.session_handoff import initial_messages, feedback_delivery
        from tools.research.task_constraints import mathematical_catalog
        rows=[]
        for arm in 'bc':
            archive=C3Archive(ROOT/f'evidence/b3_t2_pilot_050_{arm}/immutable_artifacts.tar.gz')
            self.addCleanup(archive.archive.close)
            requests=archive.requests()
            positions=[0,next(i for i,r in enumerate(requests) if r[3]['research'].get('latest_reports')),len(requests)-1]
            for position in positions:
                event,meta,wire,packet,events=requests[position]
                h,s=archive.host(events)
                budget=packet['research']['budget']
                s['count_closeout']=budget['closeout']['active']
                ledger=h.store.remaining.return_value
                ledger['remaining']['model_calls']=budget['provider_budget']['remaining_total']
                ledger['remaining']['backend_solves']=budget['science_budget']['remaining_physical']
                candidate=packet['research']['mathematical_capabilities']['candidate']
                view=mathematical_method_view(h,candidate)
                # Preserve the exact historical L0, including its real feedback.
                # Reproject only the changed catalog; never infer earlier context
                # from final snapshot-only control/report fields.
                brief=deepcopy(packet['research'])
                brief['mathematical_capabilities']=compact_scientific_delivery(
                    dict(mathematical_capabilities=mathematical_catalog(view)),decision_only=True)['mathematical_capabilities']
                native=brief['mathematical_capabilities']['methods']['mujoco_direct_control_v1']
                self.assertEqual(native['execution_limits'],s['spec']['native_control_limits'])
                if not budget['closeout']['active']:
                    self.assertEqual(core.read_evidence(h,native['request_template_query'],record_read=False),
                        view['methods']['mujoco_direct_control_v1']['request_template'])
                self.assertNotIn('execution_limits',packet['research']['mathematical_capabilities']['methods']['mujoco_direct_control_v1'])
                if s['results'] and not budget['closeout']['active']:
                    query=native['control_initialization_query']
                    seed=core.read_evidence(h,query,record_read=False)['control_seed']
                    self.assertEqual(seed['candidate'],candidate);self.assertEqual(seed['parent'],candidate)
                t2=brief['mathematical_capabilities']['methods'].get(opt.SENSITIVITY)
                if arm=='c':
                    self.assertTrue(t2['authorized']);self.assertFalse(t2['executable'])
                    preparation=(core.read_evidence(h,t2['preparation_query'],record_read=False) if not budget['closeout']['active'] else view['methods'][opt.SENSITIVITY]['readiness'])
                    self.assertTrue(preparation['variables']);self.assertTrue(preparation['model_preparation'])
                    self.assertIn('missing_validated_model_stencil',preparation['reasons'])
                packet=deepcopy(packet);packet['research']=brief
                boundary=SimpleNamespace(host=h,research_packet=packet)
                model=live_model_class(boundary)(model_id=wire['model'],stream=False,
                    client=AsyncOpenAI(api_key='offline-fixture',base_url='https://offline.invalid',max_retries=0))
                tail=model.format_request([],[],None)['messages'][-1]
                tools=deepcopy(wire['tools'])
                for tool in tools:
                    if tool['function']['name']=='research_plan':
                        tool['function']['parameters']=plan_schema(brief['actions'],decision_required=True,family_version='serial_family_space_v2')
                sizes={}
                for handoff in (False,True):
                    after={**wire,'tools':tools,'messages':([wire['messages'][0],*model.format_request_messages(initial_messages(h.run_id))] if handoff else wire['messages'][:-1])+[tail]}
                    encoded=httpx.Request('POST','https://offline.invalid',json=after).content
                    sizes['handoff' if handoff else 'same_session']=len(encoded)
                    delivered=json.loads(json.loads(encoded)['messages'][-1]['content'].split('\n',1)[1])['research']
                    self.assertEqual(delivered['mathematical_capabilities']['methods']['mujoco_direct_control_v1']['execution_limits'],s['spec']['native_control_limits'])
                    self.assertEqual(delivered['mathematical_capabilities']['methods']['mujoco_direct_control_v1']['request_template_query'],native['request_template_query'])
                    if not handoff:self.assertEqual(after['messages'][:-1],wire['messages'][:-1])
                last=[e for e in events if e['kind']=='model_original_tool_feedback'][-1:]
                if last and not budget['closeout']['active']:
                    key=archive.artifact(last[0]['outputs'][0])['tool_use']['toolUseId']
                    delivery=feedback_delivery(h,[key])['items'][0]
                    self.assertEqual(core.read_evidence(h,delivery['original_result_query'],record_read=False),archive.artifact(last[0]['outputs'][0])['result'])
                rows.append(dict(arm=arm,boundary=position+1,original_request=meta['request'],original_bytes=meta['input_bytes'],projected_bytes=sizes,limits=native['execution_limits'],handoff_limits_visible=True,
                    control_initialization_query=native.get('control_initialization_query'),t2_preparation_query=(t2 or {}).get('preparation_query')))
            self.assertEqual(archive.snapshot['session']['state']['research_status'],'stopped')
        type(self).r0_wire_rows=rows

    def test_r0_real_schema_and_precise_rejections(self):
        from jsonschema import Draft202012Validator
        from tools.research.agent import plan_schema,error_feedback
        from pydantic import ValidationError
        ref=self.generate();h=self.h
        value=dict(action='execute',candidate=ref,hypothesis='Offline schema check',expected_observation='No science',
            weakening_observation='Invalid binding',fixed_conditions='Frozen B3',stopping_condition='No dispatch',interpretation='Fixture',
            decision=dict(hypothesis_id='offline',research_intent='NMPC_EXECUTION',selected_method='execute',selected_candidate=ref))
        schema=plan_schema(['execute','initialize_control','physical_replay','diagnose','stop'],decision_required=True)
        validator=Draft202012Validator(schema);validator.validate(value)
        invalid=deepcopy(value);invalid['decision'].pop('selected_candidate')
        self.assertTrue(list(validator.iter_errors(invalid)))
        invalid=deepcopy(value);invalid.pop('candidate')
        self.assertTrue(list(validator.iter_errors(invalid)))
        with patch('tools.research.agent.record',return_value=ref):
            try:Plan.model_validate(invalid)
            except ValidationError as exc:feedback=error_feedback(h,dict(name='research_plan',input=invalid),exc,state(h))
            self.assertEqual(feedback['field'],'candidate');self.assertIn('non-null candidate',feedback['expected'])
            mismatch=error_feedback(h,dict(name='research_plan',input=value),ValueError('DECISION_CANDIDATE_MISMATCH'),state(h))
            self.assertEqual(mismatch['field'],'decision.selected_candidate')
            from tools.research.evidence_policy import admit_decision
            invalid_intent=deepcopy(value);invalid_intent['action']='diagnose'
            invalid_intent.pop('candidate')
            invalid_intent['decision']['research_intent']='MATHEMATICAL_ANALYSIS'
            try:admit_decision(h,Plan.model_validate(invalid_intent))
            except ValueError as exc:feedback=error_feedback(h,dict(name='research_plan',input=invalid_intent),exc,state(h))
            self.assertEqual(feedback['error_code'],'RESEARCH_INTENT_ACTION_MISMATCH')
            self.assertEqual(feedback['field'],'decision.research_intent')
            self.assertIn('requires decision.research_intent=DIAGNOSE',feedback['expected'])
            unrelated=error_feedback(h,dict(name='research_plan',input=value),KeyError('candidate'),state(h))
            self.assertNotEqual(unrelated['error_code'],'INVALID_EVIDENCE_POINTER')
            pointer=error_feedback(h,dict(name='evidence_read',input=dict(reference=ref,pointer='/absent')),KeyError('absent'),state(h))
            self.assertEqual(pointer['error_code'],'INVALID_EVIDENCE_POINTER');self.assertIn('Available children',pointer['expected'])
            query=dict(candidate=ref,operation='instantaneous_braking_v1',model_source='mujoco',operating_point='saved_state',execution=ref,update_id=0,protocol=state(h)['spec']['analysis_protocol'])
            try:AnalysisRequest.model_validate(query)
            except ValidationError as exc:feedback=error_feedback(h,dict(name='research_analysis',input=query),exc,state(h))
            self.assertEqual(feedback['field'],'operation/model_source');self.assertIn('Unsupported method-model',feedback['expected'])
            query.update(operation='linearization',model_source='gvs',operating_point='controller_start_input',execution=None,update_id=None,scoring_window_s=.05)
            query['protocol']={**query['protocol'],'holding_period_s':.05}
            try:AnalysisRequest.model_validate(query)
            except ValidationError as exc:feedback=error_feedback(h,dict(name='research_analysis',input=query),exc,state(h))
            self.assertEqual(feedback['field'],'protocol');self.assertIn('complete frozen',feedback['expected'])

    @classmethod
    def setUpClass(cls):
        cls.archive=C3Archive(ROOT/'evidence/c3_f1_f2/math/immutable_artifacts.tar.gz')
        cls.addClassCleanup(cls.archive.archive.close)
        cls.old=cls.archive.snapshot['session']['state']
        cls.raw=cls.archive.artifact(cls.old['analysis_results'][0])
        cls.h=fixture_host('c')
        update(cls.h,freeze='explicit-offline-synthetic-fixture')
        cls.initial=deepcopy(state(cls.h))

    def setUp(self):
        update(self.h,**deepcopy(self.initial))

    def generate(self,radius=.018):
        p=read(ROOT/'configs/research/b3_reference_generation.json')
        p['spans'][0]['radius_m']=radius
        result=design.generate_candidate(self.h,p,dict(origin='offline_geometry_no_math_or_physics'))
        self.assertEqual(result['status'],'generated',result)
        return result['candidate']

    def models(self):
        refs=[];candidates=[];spec=state(self.h)['spec']
        for i,radius in enumerate((.018,.0175,.0185,.01775,.01825)):
            ref=self.generate(radius);candidates.append(ref);c=design.verify_candidate(self.h,ref);cfg=c['configuration']
            raw=deepcopy(self.raw);binding=dict(raw['binding'],candidate=ref,candidate_id=c['candidate_id'],
                configuration=c['configuration_reference'],source_identity=c['source_identity'],
                task_identity=digest(cfg['task']),effective_configuration_identity=digest(cfg))
            raw.update(candidate=ref,binding=binding,implementation=state(self.h)['freeze'],protocol=spec['analysis_protocol'])
            raw['task_analysis']=plain(describe_analysis_requirements(cfg,binding))
            raw['requested_operation'].update(candidate=ref,protocol=spec['analysis_protocol'])
            raw['model']['binding'].update(binding,model_identity='synthetic-B3-'+str(i),
                analysis_protocol_identity=digest(spec['analysis_protocol']))
            raw['model']['protocol_identity']=digest(spec['analysis_protocol'])
            raw['model']['operating_point']['remaining_task_s']=.5
            refs.append(save(self.h,raw,'SYNTHETIC_REBOUND_ARRAYS_NOT_B3_NUMERICAL_EVIDENCE'))
        update(self.h,analysis_results=refs)
        return candidates,refs

    def test_drafts_fair_costs_fixed_b_and_formal_gate(self):
        b,c=[resolve(ROOT/f'configs/research/study_b3_t2_pilot_{arm}_draft.json') for arm in 'bc']
        self.assertEqual(b['budgets'],c['budgets']);self.assertEqual(b['budgets']['mathematical_evaluations'],22)
        for key in ('canonical_task','nmpc_limits','native_control_limits','physical_replay_limit'):
            self.assertEqual(b[key],c[key])
        self.assertEqual(set(c['mathematical_methods']),{opt.CONIC,opt.SENSITIVITY})
        self.assertNotIn(opt.SENSITIVITY,b['mathematical_methods']);self.assertNotIn('search',c['allowed_plan_actions'])
        self.assertEqual(opt.sensitivity_cost(2,0,22,conic_authorized=True)['remaining_total_range'],[14,19])
        self.assertEqual(opt.sensitivity_cost(2,5,22)['kernel_evaluations'],9)
        self.assertTrue(all(v.startswith('PENDING_EXPLICIT_APPROVAL:') for v in (b['authorization'],c['authorization'])))
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_authorization(self.h)
        h=fixture_host('b')
        import_history(h)
        p=read(ROOT/'configs/research/b3_reference_generation.json')
        self.assertEqual(design.generate_candidate(h,p,{})['status'],'generated')
        p['segments']['0']['length_m']-=.0005
        self.assertEqual(design.generate_candidate(h,p,{})['reason'],'FROZEN_REFERENCE_STRUCTURE_REQUIRED')
        for h in (h,self.h):
            self.assertFalse(any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)))
            self.assertEqual(state(h)['mathematical_evaluations'],0)
            self.assertFalse(state(h)['results']);self.assertFalse(state(h)['physical_replays'])

    def test_discovery_partial_models_saved_dispatch_and_generate_proposal(self):
        base=self.generate()
        method=mathematical_method_view(self.h,base)['methods'][opt.SENSITIVITY]
        self.assertTrue(method['registered']);self.assertTrue(method['study_authorized'])
        self.assertTrue(method['applicable']);self.assertFalse(method['authorized']);self.assertFalse(method['executable'])
        self.assertIn('formal_study_math_scope_required',method['missing'])
        variable=next(v for v in method['readiness']['variables'] if v['variable']=='spans.0.radius_m')
        self.assertEqual(variable['parameter']['units'],'m');self.assertEqual(variable['current_value'],.018)
        self.assertFalse(variable['ready_stencils']);self.assertTrue(method['readiness']['model_preparation']['request_template'])
        candidates,refs=self.models()
        update(self.h,analysis_results=refs[:2])
        partial=opt.candidate_methods(self.h,candidates[0])
        variable=next(v for v in partial['variables'] if v['variable']=='spans.0.radius_m')
        self.assertTrue(any(abs(value-.0185)<1e-12 for v in variable['incomplete_stencils'] for value in v['missing_parameter_values']))
        update(self.h,analysis_results=refs)
        ready=opt.candidate_methods(self.h,candidates[0])
        variable=next(v for v in ready['variables'] if v['variable']=='spans.0.radius_m')
        row=next(v for v in variable['ready_stencils'] if len(v['request']['optimal_sensitivity']['steps'])==2)
        query=AnalysisRequest.model_validate(row['request']);context=opt.sensitivity_context(self.h,query)
        self.assertEqual(len(context['points']),5);self.assertEqual(row['admission']['expected_mathematical_evaluations'],9)
        with patch('tools.research.research_context.mathematics_authorization',return_value={'registered_study_scope_authorized':True}):
            executable=mathematical_method_view(self.h,candidates[0])['methods'][opt.SENSITIVITY]
        self.assertTrue(executable['executable']);self.assertEqual(executable['planning_status'],'ready')
        # Complete fixtures do not override formal authorization for physics, Provider or analysis.
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('formal dispatch forbidden')):
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
                analysis.dispatch(self.h,plain(query),'formal-denied',guard=guard)
        self.assertEqual(state(self.h)['mathematical_evaluations'],0)
        stub=dict(method_version=opt.SENSITIVITY,status='computed_diagnostic',direction_status='unresolved',
            preferred_parameter_direction='unresolved',parameter_identity=context['parameter'],parameter_units='m',
            control_treatment='baseline absolute tension held vs independent reoptimization',model_scope='OFFLINE STUB',
            unsupported_inferences=['Physical acceptance'],reason='OFFLINE_NO_NUMERICAL_SOLVER')
        def worker(command,log,timeout):
            request=read(Path(command[-1]))
            self.assertEqual(state(self.h)['mathematical_evaluations'],9)
            with patch('extensions.math_analysis.capability_sensitivity.capability_sensitivity',return_value=stub):
                result=analysis.calculate(request['configuration'],request['binding'],request['query'],design_context=request['design_context'])
            atomic_json(Path(command[-1]).with_name('result.json'),result)
            return SimpleNamespace(returncode=0)
        # Only this explicit offline test bypasses formal guard; no real worker or math is launched.
        with patch('tools.service_execution._run_contained',side_effect=worker) as launched:
            result=analysis.dispatch(self.h,plain(query),'synthetic-dispatch',guard=lambda *a:None)
            again=analysis.dispatch(self.h,plain(query),'synthetic-dispatch',guard=lambda *a:None)
        self.assertEqual(launched.call_count,1);self.assertEqual(again['operation_reuse']['additional_analysis_evaluations'],0)
        raw=self.h.store.artifact(result['reference']);self.assertEqual(raw['optimal_sensitivity']['direction_status'],'unresolved')
        self.assertEqual(raw['model_reuse']['new_model_builds'],0)
        reporter.scientific_feedback(self.h,result)
        brief=agent_decision_brief(self.h)
        short=brief['latest_reports'][-1]['findings'][0]['mathematics']
        self.assertEqual(short['optimal_sensitivity']['preferred_parameter_direction'],'unresolved')
        self.assertEqual(core.read_evidence(self.h,short['detail_query'],record_read=False)['reason'],'OFFLINE_NO_NUMERICAL_SOLVER')
        self.assertNotIn('family_sensitivity_conditions',brief)
        p=deepcopy(design.verify_candidate(self.h,candidates[0])['parameters']);p['spans'][0]['radius_m']=.0181
        plan=Plan(action='generate',generation=p,supporting_evidence=[result['reference']],
            hypothesis='OFFLINE: unresolved T2 permits a small contrast, not a gradient step.',
            expected_observation='A fresh T1 is required for this candidate.',weakening_observation='No task improvement.',
            fixed_conditions='B3 task/topology, all other parameters and physical bounds.',stopping_condition='Geometry only.',
            interpretation='Synthetic interface validation; no B3 numerical direction.',
            decision=dict(hypothesis_id='offline-t2-proposal',research_intent='DESIGN_MODIFICATION',
                selected_method='generate',selected_candidate=candidates[0],claimed_inference='empirical_search'))
        with patch('tools.research.core.guard'),patch('tools.service_execution._run_contained',side_effect=AssertionError('no scientific launch')):
            proposal=core.dispatch(self.h,plain(plan),'synthetic-proposal')
        new=proposal['result']['candidate']
        self.assertNotEqual(new,candidates[0]);self.assertEqual(design.verify_candidate(self.h,new)['provenance']['plan'],proposal['plan'])
        self.assertFalse(any(self.h.store.artifact(r).get('candidate')==new for r in state(self.h)['analysis_results']))
        t1=AnalysisRequest(candidate=new,operation='task_capability',operating_point='controller_start_input',
            protocol=state(self.h)['spec']['analysis_protocol'],capability_method=opt.CONIC)
        self.assertEqual(opt.method_admission(state(self.h)['spec'],t1)['expected_mathematical_evaluations'],2)
        self.assertFalse(state(self.h)['results']);self.assertFalse(state(self.h)['physical_replays'])

    def test_original_f2_unresolved_evidence_l1_and_compact_l0(self):
        h,s=self.archive.host()
        ref=next(r for r in s['analysis_results'] if self.archive.artifact(r).get('optimal_sensitivity'))
        raw=self.archive.artifact(ref);card=plain(result_card(h,ref));view=card['deterministic_summary']['optimal_sensitivity']
        self.assertEqual(view['direction_status'],'directional_comparisons_only')
        self.assertEqual(view['preferred_parameter_direction'],'unresolved')
        self.assertEqual(view['sampled_parameter_values'],[.018,.0175,.0185])
        self.assertEqual(view['differences'][0]['fixed_control'],raw['optimal_sensitivity']['reoptimized_finite_difference'][0]['fixed_control'])
        self.assertTrue(view['active_constraints']['baseline'][0]['observation']['absolute_time_s']>=.3)
        self.assertEqual(core.read_evidence(h,dict(reference=ref,view='working_set',pointer='/mathematical_decision_view/optimal_sensitivity'),record_read=False),view)
        report=dict(report=plain(reporter.assemble(h,[ref])),interpretation_status='deferred',error=None)
        delivery=reporter.reporter_handoff_summary(h,ref,report)
        compact=compact_scientific_delivery(dict(latest_reports=[delivery],action_trace=dict(recent=[])),decision_only=True)
        short=compact['latest_reports'][0]['findings'][0]['mathematics']
        self.assertEqual(short['optimal_sensitivity']['direction_status'],view['direction_status'])
        self.assertEqual(short['detail_query']['reference'],ref)
        self.assertLess(len(json.dumps(short)),700)
        for field in ('differences','sampled_parameter_values','active_constraints','baseline_absolute_input_n'):
            self.assertNotIn(field,short)

    def test_saved_stable_and_flat_are_not_promoted(self):
        from tools.research.capability import sensitivity_summary
        saved=read(ROOT/'evidence/s130_optimal_capability/t2_final_comparison.json')['analyses']
        for raw,status,direction in zip(saved,('stable_reoptimized_direction_envelope_unresolved',
                'numerically_flat_fd_envelope_unresolved'),('decrease','unresolved')):
            view=sensitivity_summary(raw)
            self.assertEqual(view['direction_status'],status);self.assertEqual(view['preferred_parameter_direction'],direction)
            self.assertEqual(view['strict_gradient'],'unavailable')
            self.assertEqual(view['sampled_parameter_values'],[r['value'] for r in raw['numerical_optimality']])
            self.assertEqual(view['baseline']['baseline_parameter_value'],raw['summary']['baseline_parameter_value'])


if __name__=='__main__':unittest.main()
