"""M3-D offline integration. Fabricated task/solver outcomes are test fixtures."""
from copy import deepcopy
import gc
import os
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from schemas.platform import ProjectConfig, SessionInput
from tools.research import core, design, feedback, analysis
from tools.research.config import ROOT, resolve
from tools.research.state import state, update, save, core_hashes
from tools.state_io import read, digest, atomic_json
from tools.platform_store import plain


class SavedS56FeedbackTests(unittest.TestCase):
    def test_packet_preserves_failure_scope_and_no_gradient_certificate(self):
        packet=read(ROOT/'evidence/sorosim_s56/agent_feedback_packet.json')
        self.assertFalse(packet['task']['physical_success'])
        self.assertEqual(packet['provider_requests'],0)
        self.assertEqual(packet['scientific_resources']['rl_training_actions'],131072)
        self.assertEqual({r['mode'] for r in packet['rl']['routes']},{'direct','residual'})
        self.assertFalse(packet['control_optimization']['secondary']['raw_kkt']['same_as_selected_trajectory'])
        self.assertIsNone(packet['mathematical_reliability']['gradient_error_bound'])
        self.assertEqual(packet['mathematical_reliability']['descent_certificate'],'unavailable')
        self.assertTrue(packet['mathematical_reliability']['fixed_input_static_sensitivity']['verification']['passed'])

    def test_both_feedback_versions_are_readable_without_a_live_agent(self):
        from tools.research.sorosim_s55_feedback import scoped_feedback
        packets=[read(ROOT/'evidence/sorosim_s55/agent_feedback_packet.json'),
            read(ROOT/'evidence/sorosim_s56/agent_feedback_packet.json')]
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda reference:packets[reference]))
        self.assertEqual(len(scoped_feedback(host,[0,1])),2)


class AgentFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('m3d-fixture-'+uuid4().hex)
        self.addCleanup(self.cleanup)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':self.folder.name,'grant_id':self.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            self.host=core.prepare(ROOT/'configs/research/study_m3d_agent_feedback.json',self.folder)
        self.spec=state(self.host)['spec']
        update(self.host,freeze='offline_fixture_not_scientific_binding',core_hashes=core_hashes())

    def cleanup(self):
        gc.collect()
        if self.folder.resolve().parent!=(ROOT/'runs').resolve():
            raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
        if self.folder.exists():shutil.rmtree(self.folder)

    def plan(self,action,**fields):
        return dict(action=action,hypothesis='Offline integration fixture',
            expected_observation='Exact causal references and candidate binding',
            weakening_observation='Missing or mismatched evidence',fixed_conditions='Frozen task and family',
            stopping_condition='Fixture ends; no live experiment',
            interpretation='Fabricated outcomes test interfaces only',**fields)

    def generate(self,request=None,**fields):
        request=request or dict(version='serial_family_generation_v2',
            family_space_identity=self.spec['family_space_identity'],segment_count=2,tendon_count=4)
        with patch.object(core,'guard'):
            result=core.dispatch(self.host,self.plan('generate',generation=request,**fields),'generate-'+uuid4().hex)
        self.assertEqual(result['result']['status'],'generated',result)
        return result['result']['candidate']

    def result(self,candidate,*,accepted=False,status='valid_failure'):
        c=design.verify_candidate(self.host,candidate)
        motion=save(self.host,[dict(time_s=t,tip_error_m=e,tip_speed_m_s=v) for t,e,v in
            [(0.,.2,.1),(.30,.018,.03),(.31,.019,.04),(.32,.03,.05),(.33,.02,.07),(.34,.016,.04),(.35,.015,.03)]],
            'synthetic_motion_fixture')
        component=lambda value,limit,unit,passed:dict(value=value,limit=limit,unit=unit,passed=passed)
        acceptance=dict(status=status,accepted=accepted,missing=[],issues=[],
            metrics=dict(terminal_error_m=.005 if accepted else .015,
                holding_max_error_m=.005 if accepted else .03,holding_max_speed_m_s=.01 if accepted else .07),
            components={
                'evaluation_validity':component('valid',None,None,True),
                'execution_complete':component(True,None,None,True),
                'holding_coverage':component(True,6,'inclusive uniform samples',True),
                'evaluator:task_bound':component(.005 if accepted else .015,.01,'m',accepted),
                'holding_position':component(.005 if accepted else .03,.01,'m',accepted),
                'holding_speed':component(.01 if accepted else .07,.02,'m/s',accepted),
                'solver_errors':component(0,0,'count',True),
                'force_bounds':component(0.,1e-8,'N',True)})
        result=dict(status='evaluated',fixture=True,candidate=candidate,profile_identity=c['profile_identity'],
            scientific_configuration=c['scientific_configuration'],owning_study=self.host.run_id,
            role='development',execution_id='fixture-'+uuid4().hex,numerical_s=0.,acceptance=acceptance,
            profile=dict(motion=motion,solver_status='completed',evaluation_validity='valid',valid_complete_execution=True,
                last_valid_time_s=.35,optimization_status_counts={'iteration_limit':2},
                raw_termination_counts={'Maximum_Iterations_Exceeded':2},solver_error_count=0,
                maximum_plan_violation=1e-8,unusable_plans=0))
        ref=save(self.host,result,'synthetic_execution_fixture')
        update(self.host,results=[*state(self.host)['results'],ref])
        return ref

    def test_real_c3_final_materialization_and_preparation(self):
        from tools.research.numerics import archived
        from tools.platform_registry import registry
        from extensions.tendon_family.gvs_nmpc import resolve_gvs_nmpc_control
        from extensions.tendon_family.backends import physics_for
        from tools.research.agent import decision_packet
        historical=read(ROOT/'evidence/m3c3_mixed_family_search/search_verification.json')
        folder='evidence/m3c3_mixed_family_search/search'
        source=historical['best']['evidence']['candidate']
        original=archived(folder,source)
        # Import context bytes only. Historical candidates never enter our owned pool.
        for ref in (source,historical['search_result'],historical['best']['evidence']['analysis']):
            self.assertEqual(save(self.host,archived(folder,ref),'historical_context_fixture'),ref)
        self.assertEqual(state(self.host)['candidates'],{})
        self.assertIsNone(state(self.host)['reference_candidate'])
        update(self.host,search_results=[historical['search_result']])
        packet=decision_packet(self.host)
        recipe=packet['search_feedback'][0]['final_materialization']
        self.assertEqual(recipe['source_candidate'],source)
        self.assertEqual(recipe['generation'],design.final_generation_request(self.spec,original))
        candidate=self.generate(recipe['generation'],supporting_evidence=recipe['supporting_evidence'])
        c=design.verify_candidate(self.host,candidate)
        self.assertEqual(c['physical_design_identity'],original['physical_design_identity'])
        self.assertNotEqual(c['numerical_model_identity'],original['numerical_model_identity'])
        self.assertTrue(design.final_fidelity_matches(self.spec,c))
        self.assertEqual(c['final_evaluation_identity'],historical['final_evaluation_identity'])
        self.assertEqual(c['resolved_parameters']['dimensions'],dict(physical_dofs=48,gvs_coordinates=12,state=24,inputs=4))
        self.assertEqual(set(c['effective_discretization']['data']['cells'].values()),{12})
        self.assertEqual(c['configuration']['robot']['structure'],original['configuration']['robot']['structure'])
        inp=SessionInput.model_validate(c['configuration'])
        plan=resolve_gvs_nmpc_control(inp,physics_for(inp))
        controller=SimpleNamespace()
        registry().get('controller.gvs_nmpc','11.0.0','controller').hook('prepare_execution')(
            SimpleNamespace(save_artifact=lambda value,kind:save(self.host,value,kind)),controller,inp)
        self.assertEqual(controller.preparation['tendon_order'],[f'tendon_{i}' for i in range(4)])
        self.assertEqual(len(controller.profile['numerical']['measured_initial_state']),24)
        self.assertEqual(plan['stopping']['iteration_ceiling'],120)
        self.assertFalse(controller.preparation['warm_guess_is_execution_evidence'])
        self.assertEqual(digest(original),source['artifact_id'])
        s=state(self.host)
        self.assertEqual(self.host.store.artifact(s['plans'][-1])['original_plan']['supporting_evidence'],recipe['supporting_evidence'])
        self.assertEqual(s['analysis_results'],[])
        self.assertEqual(s['results'],[])
        if os.environ.get('M3D_PREFLIGHT_EVIDENCE'):
            # Opt-in offline native XML loading only: one contained child, zero steps/updates.
            from tools.research.runtime_capability import capability
            support=capability(self.host,candidate)
            self.assertEqual(support['status'],'runtime_available',support)
            export=core.export(self.host,(ROOT/os.environ['M3D_PREFLIGHT_EVIDENCE']).parent/'prelaunch')
            atomic_json(ROOT/os.environ['M3D_PREFLIGHT_EVIDENCE'],dict(
                scope='Real archived-design regeneration and controller preparation; XML load only. No scientific rollout.',
                implementation=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    core_hashes=core_hashes(),dirty_worktree=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                    binding='Offline fixture, not a bound live experiment'),
                immutable_export=export['destination'],
                study_configuration_identity=self.spec['resolved_identity'],
                family_space_identity=self.spec['family_space_identity'],canonical_task_identity=self.spec['canonical_task_identity'],
                historical_candidate=source,historical_search=historical['search_result'],
                historical_analysis=historical['best']['evidence']['analysis'],
                physical_design_identity=c['physical_design_identity'],numerical_model_identity=c['numerical_model_identity'],
                final_evaluation_identity=c['final_evaluation_identity'],request=recipe['generation'],
                dimensions=c['resolved_parameters']['dimensions'],preparation=controller.preparation,
                runtime_capability=support,construction_numerical_s=state(self.host)['construction_numerical_s'],
                resource_use=dict(provider_requests=0,mathematical_evaluations=0,controller_updates=0,
                    rl_training_stages=0,complete_task_evaluations=0,physics_steps=0,
                    native_xml_probes=state(self.host).get('runtime_probe_launches',0))))

    def test_failure_feedback_and_causal_control_revision(self):
        candidate=self.generate()
        failed=self.result(candidate)
        view=feedback.result_view(self.host,failed)
        metrics={m['metric']:m for m in view['failed_metrics']}
        for key,value,time_s in [('evaluator:task_bound',.015,.35),('holding_position',.03,.32),('holding_speed',.07,.33)]:
            self.assertEqual(metrics[key]['value'],value)
            self.assertEqual(metrics[key]['time_s'],time_s)
            sample=core.read_evidence(self.host,dict(reference=metrics[key]['sample_evidence'],pointer=metrics[key]['sample_pointer']))
            self.assertEqual(sample['time_s'],time_s)
        self.assertEqual(view['numerical_validity']['acceptance_status'],'valid_failure')
        self.assertEqual(view['solver_outcome']['raw_termination_counts'],{'Maximum_Iterations_Exceeded':2})
        self.assertFalse(view['passed'])
        request=deepcopy(design.verify_candidate(self.host,candidate)['parameters'])
        request['control_weights']['holding_tip_speed_weight']=.2
        request['control_weights']['terminal_tip_speed_weight']=.2
        core.read_evidence(self.host,dict(reference=failed,pointer='/acceptance'))
        revised=self.generate(request,supporting_evidence=[failed,candidate])
        a=design.verify_candidate(self.host,candidate);b=design.verify_candidate(self.host,revised)
        self.assertNotEqual(a['identity'],b['identity'])
        self.assertEqual(a['physical_design_identity'],b['physical_design_identity'])
        self.assertEqual(a['task_identity'],b['task_identity'])
        self.assertEqual(feedback.mathematical_context(self.host,revised),[])
        self.assertEqual(self.host.store.artifact(state(self.host)['plans'][-1])['original_plan']['supporting_evidence'],[failed,candidate])

    def test_first_pass_selects_without_math_redesign_or_execution(self):
        from tools.research.budget import observe_pass
        candidate=self.generate();passed=self.result(candidate,accepted=True,status='accepted')
        observe_pass(self.host,passed)
        self.assertIsNotNone(state(self.host)['success_gate'])
        self.assertFalse(feedback.eligibility(self.host,passed)['eligible'])
        core.read_evidence(self.host,dict(reference=passed,pointer='/acceptance'))
        for action,fields in [('generate',dict(generation=design.verify_candidate(self.host,candidate)['parameters'])),
                              ('execute',dict(candidate=candidate))]:
            with self.assertRaisesRegex(ValueError,'PROTECTED_CLOSEOUT'):
                core.dispatch(self.host,self.plan(action,**fields),'blocked-'+action)
        query=dict(candidate=candidate,operation='equilibrium',operating_point='target_equilibrium',protocol=self.spec['analysis_protocol'])
        with self.assertRaisesRegex(ValueError,'FRESH_TASK_PASS'):
            analysis.dispatch(self.host,query,'blocked-math',guard=core.guard)
        with patch.object(core,'guard'),patch.object(core,'execute') as execute:
            result=core.dispatch(self.host,self.plan('select',selected_execution=passed,supporting_evidence=[passed]),'select-pass')
            execute.assert_not_called()
        self.assertTrue(result['result']['task_passed'])
        self.assertEqual(state(self.host)['research_status'],'stopped')
        self.assertEqual(state(self.host)['mathematical_evaluations'],0)

    def test_invalid_missing_and_worker_failure_evidence(self):
        from tools.research.execution import compact_result
        from tools.research.budget import observe_pass
        candidate=self.generate();ref=self.result(candidate)
        for status in ('invalid','missing_evidence','incomplete'):
            value=self.host.store.artifact(ref)
            value['acceptance'].update(status=status,accepted=None,missing=['holding_speed'],issues=['FIXTURE_ISSUE'])
            value['acceptance']['components']['holding_speed'].update(value=None,passed=None)
            value['profile'].update(evaluation_validity='invalid',valid_complete_execution=False,solver_error_count=1)
            value['acceptance']['components']['solver_errors'].update(value=1,passed=False)
            changed=save(self.host,value,'synthetic_invalid_evidence_fixture')
            update(self.host,results=[changed])
            view=feedback.result_view(self.host,changed)
            self.assertFalse(view['passed'])
            self.assertEqual(view['numerical_validity']['acceptance_status'],status)
            self.assertEqual(view['numerical_validity']['missing'],['holding_speed'])
            self.assertEqual(view['solver_outcome']['solver_error_count'],1)
            observe_pass(self.host,changed)
            self.assertIsNone(state(self.host).get('success_gate'))
        incomplete=compact_result(dict(status='execution_incomplete',execution=dict(stage='simulation',
            failure_reason='worker exit',boundary=dict(returncode=7,termination_confirmed=True))))
        self.assertEqual(incomplete['numerical_validity']['failure_reason'],'worker exit')
        self.assertEqual(incomplete['numerical_validity']['boundary']['returncode'],7)
        self.assertIsNone(incomplete['numerical_validity']['valid_complete_execution'])

    def test_workflow_through_real_dispatch_with_synthetic_workers(self):
        from pathlib import Path
        from tools.research.agent import decision_packet
        from tools.research.contracts import AnalysisRequest
        launched=[]
        def worker(command,log,timeout,*,lifecycle_path=None):
            request_path=Path(command[-1]);request=read(request_path)
            cfg=request['configuration']
            if request.get('kind')=='candidate_analysis':
                launched.append('synthetic_analysis')
                # Deliberately fabricated static score; no numerical solver runs.
                n=sum(c['kind']=='flexible_segment' for c in cfg['robot']['structure']['data']['components'])
                result=dict(status='computed',operation='equilibrium',fixture=True,
                    proxy_values={'target_equilibrium_residual':.1/n},internal_calculations=[],
                    local_model_constraints=dict(equilibrium_available=False,global_infeasibility_proven=False))
            else:
                launched.append('synthetic_execution')
                passed=launched.count('synthetic_execution')==2
                error,speed=(.005,.01) if passed else (.015,.03)
                motion=save(self.host,[dict(time_s=i*.01,tip_error_m=error,tip_speed_m_s=speed) for i in range(36)],'synthetic_motion_fixture')
                source=save(self.host,dict(fixture=True,execution=len(launched)),'synthetic_backend_fixture')
                ev=dict(validity='valid',task_success=passed,source=source,evaluator='evaluate.reach',
                    comparison_identity='synthetic_fixture',source_execution_id=request['owner'],
                    metrics=[dict(name='position_error',value=error,units='m')],
                    constraints=[dict(name='task_bound',satisfied=passed,observed=error,limit=.01,units='m')])
                evaluation=save(self.host,ev,'synthetic_evaluator_fixture')
                profile=dict(complete=True,valid_complete_execution=True,evaluation_validity='valid',
                    solver_status='completed',last_valid_time_s=.35,solver_error_count=0,force_bound_violation_n=0.,
                    execution_id=request['owner'],evaluation=evaluation,simulation=source,motion=motion,
                    sampled_settling=dict(**cfg['policy']['controller']['parameters']['data']['settling'],
                        available=True,max_error_m=error,max_speed_m_s=speed,passed=passed))
                profile_ref=save(self.host,dict(detail=profile),'synthetic_profile_fixture')
                result=dict(status='evaluated',fixture=True,execution_id=request['owner'],
                    profile_report=dict(reference=profile_ref),evaluation_data=ev,
                    receipts=dict(evaluation=dict(output=evaluation,charged=dict(wall_s=0.)),
                        profile=dict(output=profile_ref,charged=dict(wall_s=0.))))
            atomic_json(request_path.parent/'result.json',result)
            return SimpleNamespace(returncode=0)
        query=dict(version='family_mixed_search_v1',family_space_identity=self.spec['family_space_identity'],
            variable_groups=['segment_count'],segment_counts=[1,2],tendon_counts=[4],
            screening_fidelity='coarse',objective='target_equilibrium_residual',operating_point='target_equilibrium',
            max_proposals=2,max_evaluations=2)
        with patch('tools.service_execution._run_contained',side_effect=worker), \
             patch('tools.research.runtime_capability.capability',return_value=dict(status='runtime_available',fixture=True)):
            searched=core.dispatch(self.host,self.plan('search',search=query),'workflow-search')
            rows=searched['result']['result']['evaluated']
            self.assertEqual(rows[1]['lineage']['evidence_used'],[rows[0]['evidence']['analysis']])
            core.read_evidence(self.host,dict(reference=searched['result']['reference'],pointer='/result/best_mathematical_candidate'))
            recipe=decision_packet(self.host)['search_feedback'][0]['final_materialization']
            candidate=self.generate(recipe['generation'],supporting_evidence=recipe['supporting_evidence'])
            q=plain(AnalysisRequest(candidate=candidate,operation='equilibrium',operating_point='target_equilibrium',protocol=self.spec['analysis_protocol']))
            analyzed=analysis.dispatch(self.host,q,'workflow-final-analysis',guard=core.guard)
            self.assertEqual(self.host.store.artifact(analyzed['reference'])['candidate'],candidate)
            self.assertEqual(len(feedback.mathematical_context(self.host,candidate)),1)
            screened=rows[-1]['evidence']['candidate']
            denied=core.dispatch(self.host,self.plan('execute',candidate=screened),'workflow-deny-coarse')
            self.assertEqual(denied['result']['status'],'final_fidelity_required')
            self.assertEqual(launched.count('synthetic_execution'),0)
            failed=core.dispatch(self.host,self.plan('execute',candidate=candidate,supporting_evidence=[analyzed['reference']]),'workflow-failed')['result']['reference']
            core.read_evidence(self.host,dict(reference=failed,pointer='/acceptance'))
            self.assertFalse(feedback.result_view(self.host,failed)['passed'])
            self.assertFalse(state(self.host).get('success_gate'))
            request=deepcopy(recipe['generation']);request['control_weights']['holding_tip_speed_weight']=.2
            revised=self.generate(request,supporting_evidence=[failed,candidate])
            self.assertEqual(feedback.mathematical_context(self.host,revised),[])
            passed=core.dispatch(self.host,self.plan('execute',candidate=revised,supporting_evidence=[failed]),'workflow-passed')['result']['reference']
            self.assertEqual(state(self.host)['success_gate']['evidence'],passed)
            core.read_evidence(self.host,dict(reference=passed))
            core.dispatch(self.host,self.plan('select',selected_execution=passed,supporting_evidence=[passed]),'workflow-select')
        self.assertEqual(launched,['synthetic_analysis']*3+['synthetic_execution']*2)
        self.assertEqual(state(self.host)['nmpc_launches'],2)
        self.assertEqual(state(self.host)['mathematical_evaluations'],3)
        self.assertEqual(state(self.host)['research_status'],'stopped')
        self.assertIsNone(state(self.host)['pending'])


if __name__=='__main__':unittest.main()
