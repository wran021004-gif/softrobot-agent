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
