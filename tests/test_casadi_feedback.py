"""Focused changes only; no NLP solve. Numeric tests run inside speed reservation."""
import unittest
import numpy as np
import casadi as ca
from pydantic import ValidationError
from schemas.casadi_feedback import Candidate,Plan
from extensions.tendon_family.gvs_codesign import Workspace
from tools.casadi_feedback_worker import assess


class PlanTests(unittest.TestCase):
    def test_failed_initial_batch_can_be_revised_without_missing_replay(self):
        from types import SimpleNamespace
        from contextlib import nullcontext
        import time
        from tools.casadi_feedback_service import plan
        from schemas.platform import EvidenceRef
        ref=dict(artifact_id='a'*64,media_type='application/json')
        state=dict(research_status='ready',results=[dict(operation='solve',reference=ref,candidate=None)],
            plans=[dict(action='batch')],batch_counts=dict(initial=1,revision=0),nlp_solves=1,
            numerical_s=0.,investigation_s=0.,cutoff_unix=time.time()+10000.,refined_grid_supported=True)
        store=SimpleNamespace(session=lambda *a:dict(state=state),remaining=lambda:dict(remaining=dict(model_calls=10,tool_calls=80,backend_solves=1)),
            transaction=lambda:nullcontext(None),update_state=lambda *a:None)
        ctx=SimpleNamespace(store=store,run_id='casadi-feedback-research-20261010',artifact=lambda r:{},
            save_artifact=lambda *a:EvidenceRef(**ref))
        args=Plan(action='batch',hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',
            candidates=[Candidate(substeps=2)],requested_nlp_solves=1,requested_replays=1,revision_or_stop_rule='r',disposition='d',limitations=['l'])
        self.assertTrue(plan(ctx,args).detail['accepted'])
        state['plans']=[dict(action='batch')];state['results'][0]['candidate']=ref
        with self.assertRaisesRegex(ValueError,'AVAILABLE_INITIAL_CANDIDATE_REPLAY'):plan(ctx,args)

    def test_protected_closeout_schema(self):
        from schemas.casadi_feedback import CloseoutPlan
        ref=dict(artifact_id='a'*64,media_type='application/json')
        base=dict(hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',revision_or_stop_rule='r',disposition='d',limitations=['l'])
        self.assertEqual(CloseoutPlan(action='stop',**base).action,'stop')
        with self.assertRaises(ValidationError):CloseoutPlan(action='batch',**base)

    def test_solver_return_survives_candidate_packaging(self):
        from types import SimpleNamespace
        from unittest.mock import patch,Mock
        from pathlib import Path
        from schemas.platform_math import OptimizationResult
        from tools.casadi_feedback_worker import solve,recover
        from tools.state_io import read
        order=['design/d','slack/position','slack/speed']+[f'u/{k}/0' for k in range(35)]
        values=dict.fromkeys(order,0.)
        problem=SimpleNamespace(variables={k:dict(type='number',bounds=[0.,1.]) for k in order},
            constraints=[SimpleNamespace(name=k) for k in ['dynamics_0_0','terminal_position','holding_speed_35']])
        candidate=dict(d=0.,lengths_m=[.16,.11])
        w=SimpleNamespace(n=1,m=1,assemble=lambda *a:problem,decode=lambda v:dict(candidate),
            mechanics_construction_s=0.,assembly_s=0.,initial_rollout={})
        result=OptimizationResult(status='converged',optimum=values,objective_value=0.,constraint_violation=0.,iterations=3)
        solver=SimpleNamespace(solve=Mock(return_value=result),_bounds=lambda p,o:([0.]*len(o),[1.]*len(o),[0.]*len(o)),
            last_returned_optimum=values,last_diagnostics=dict(return_status='Solve_Succeeded',variable_order=order,
                constraint_upper=[float('inf')],construction_s=0.,solve_s=0.,
                retained_diagnostic_points=[dict(iteration=3,vector=list(values.values()),label='returned')]))
        assessment=dict(candidate=dict(candidate),hard_max_normalized_violation=0.,original_task_gaps=dict(position=0.,speed=0.),
            effort=0.,variation_weighted=0.,slack_values=dict(position=0.,speed=0.))
        args=dict(substeps=1,initialization='pretension_0_2',position_weight=1.,speed_weight=1.,secondary_coefficient=0.)
        test_root=Path(__file__).resolve().parents[1]/'runs/casadi-feedback-closeout-20261010/checks'
        test_root.mkdir(parents=True,exist_ok=True)
        with patch('tools.casadi_feedback_worker.Workspace',return_value=w),\
            patch('tools.casadi_feedback_worker.IpoptSolver',return_value=solver),patch('tools.casadi_feedback_worker.assess',side_effect=ValueError('injected extraction failure')):
            progress=str(test_root/'completed_solve_packaging.json')
            with self.assertRaisesRegex(ValueError,'injected extraction failure'):solve({},args,'reverse',progress=progress,execution=dict(request_id='original'))
            saved=read(progress);self.assertEqual(saved['phase'],'solver_returned')
            self.assertEqual(saved['raw_returned_optimum'],values)
            self.assertEqual(saved['diagnostics']['constraint_upper'],[None])
        with patch('tools.casadi_feedback_worker.Workspace',return_value=w),\
            patch('tools.casadi_feedback_worker.IpoptSolver',side_effect=AssertionError('recovery must not invoke IPOPT')),\
            patch('tools.casadi_feedback_worker.assess',return_value=assessment):
            output=recover(saved)
            self.assertEqual(output['candidate']['selection']['iteration'],3)
            self.assertEqual(output['status'],'converged')
            self.assertEqual(output['execution'],dict(request_id='original'))
            self.assertEqual(output['costs_s'],saved['costs_s'])
            solver.solve.assert_called_once()

    def test_batch_pauses_and_preserves_unexecuted_choice(self):
        from types import SimpleNamespace
        from contextlib import nullcontext
        from unittest.mock import patch
        from tools.research_casadi_feedback import execute_batch
        state={};ref=dict(artifact_id='a'*64,media_type='application/json')
        store=SimpleNamespace(artifact=lambda r:dict(detail=dict(status='engineering_error')),
            transaction=lambda:nullcontext(None),session=lambda *a:dict(state=state),update_state=lambda *a:None)
        base=dict(action='batch',hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',
            candidates=[Candidate(),Candidate(substeps=2)],requested_nlp_solves=2,requested_replays=2,revision_or_stop_rule='r',disposition='d',limitations=['l'])
        with patch('tools.research_casadi_feedback.invoke',return_value=dict(execution_status='completed',output=ref)) as call:
            operations=execute_batch(SimpleNamespace(store=store),Plan(**base),dict(batch='initial',plan_reference=ref),'fixture')
        self.assertEqual(call.call_count,1);self.assertEqual(len(operations),1)
        self.assertEqual(state['engineering_pause']['unexecuted_choices'][0]['substeps'],2)

    def test_provider_compatibility_and_protected_boundary(self):
        import asyncio,json,httpx
        from types import SimpleNamespace
        from schemas.casadi_feedback import CloseoutPlan
        from tools.research_casadi_feedback import FeedbackBoundary
        sends=[];state=dict(research_status='ready',pilot={})
        store=SimpleNamespace(session=lambda *a:dict(state=state),remaining=lambda:dict(remaining=dict(model_calls=4)))
        host=SimpleNamespace(store=store,compatibility=lambda:dict(compatible=False))
        transport=httpx.MockTransport(lambda request:sends.append(request))
        boundary=FeedbackBoundary(host,transport=transport)
        request=httpx.Request('POST','https://api.deepseek.com/chat/completions',json={})
        with self.assertRaisesRegex(ValueError,'DEPENDENCIES_CHANGED_BEFORE_PROVIDER_SEND'):
            asyncio.run(boundary.handle_async_request(request))
        self.assertEqual(sends,[])
        host.compatibility=lambda:dict(compatible=True)
        with self.assertRaisesRegex(ValueError,'PROTECTED_SEND'):
            asyncio.run(boundary.handle_async_request(request))
        from tools.research_casadi_feedback import provider_guard
        provider_guard(host,dict(tools=[dict(function=dict(name='research_plan',parameters=CloseoutPlan.model_json_schema()))]))
        from unittest.mock import patch
        native={'tools':[{'function':{'name':'research_plan','parameters':CloseoutPlan.model_json_schema()}},
            {'function':{'name':'retrieve_context','parameters':{'properties':{'reference':{'type':'string','enum':['fresh_0']}}}}}]}
        with patch('tools.research_casadi_feedback.feedback_context_references',return_value=['fresh_0']):
            provider_guard(host,native)
            native['tools'][1]['function']['parameters']['properties']['reference']['enum']=['historical_0']
            with self.assertRaisesRegex(ValueError,'PROTECTED_RETRIEVAL'):provider_guard(host,native)
        from strands.tools.tools import PythonAgentTool
        from tools.research_casadi_feedback import protect_context_tool
        retrieval=PythonAgentTool('retrieve_context',dict(name='retrieve_context',description='Fixture matching native direct JSON schema',
            inputSchema=dict(type='object',properties=dict(reference=dict(type='string')),required=['reference'])),lambda *a:None)
        protect_context_tool(retrieval,['fresh_0'])
        self.assertEqual(retrieval.tool_spec['inputSchema']['json']['properties']['reference']['enum'],['fresh_0'])
        state['research_status']='stopped'
        with self.assertRaisesRegex(ValueError,'ACCEPTED_STOP_NO_MORE_SENDS'):
            asyncio.run(boundary.handle_async_request(request))
        self.assertEqual(sends,[]);asyncio.run(boundary.aclose())

    def test_activity_plan_and_accepted_native_stop(self):
        from schemas.casadi_feedback import ActivityPlan
        from schemas.platform import EvidenceRef
        from types import SimpleNamespace
        from contextlib import nullcontext
        from tools.casadi_feedback_service import plan
        import time
        ref=dict(artifact_id='a'*64,media_type='application/json')
        base=dict(hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',revision_or_stop_rule='r',disposition='d',limitations=['l'])
        with self.assertRaises(ValidationError):ActivityPlan(action='batch',candidates=[Candidate(),Candidate()],requested_nlp_solves=2,requested_replays=2,**base)
        state=dict(research_status='ready',results=[dict(operation='solve',reference=ref,candidate=None)],plans=[],numerical_s=0.,
            investigation_s=0.,nlp_solves=1,batch_counts=dict(initial=1,revision=0),cutoff_unix=time.time()+10000.)
        store=SimpleNamespace(session=lambda *a:dict(state=state),remaining=lambda:dict(remaining=dict(model_calls=4,tool_calls=40,backend_solves=0)),
            transaction=lambda:nullcontext(None),update_state=lambda *a:None)
        ctx=SimpleNamespace(store=store,run_id='fixture',artifact=lambda r:{},save_artifact=lambda *a:EvidenceRef(**ref))
        result=plan(ctx,ActivityPlan(action='stop',**base))
        self.assertTrue(result.detail['accepted']);self.assertEqual(state['final_disposition'],ref)
        with self.assertRaisesRegex(ValueError,'MODEL_STOP_SEALED'):plan(ctx,ActivityPlan(action='stop',**base))

    def test_generic_incumbent_keeps_original_gap_rank(self):
        from extensions.optimization.ipopt import _FeasibleIterate
        callback=_FeasibleIterate(1,1)
        callback.reset([0.],[1.],[-np.inf],[1.],0.,trace=True)
        callback.research_rank=lambda x,g:(float(x[0]),)
        def invoke(x,objective):
            args=[ca.DM([x]) if name=='x' else ca.DM([.5]) if name=='g' else ca.DM([objective]) if name=='f'
                else ca.DM.zeros(callback.get_sparsity_in(i)) for i,name in enumerate(callback.names)]
            callback.eval(args)
        invoke(.9,0.);invoke(.8,1.);invoke(.2,9.)
        self.assertAlmostEqual(callback.checkpoints['research_incumbent']['x'][0],.2)
        self.assertEqual(callback.checkpoints['research_incumbent']['iteration'],2)

    def test_frozen_domains_and_weight_menu(self):
        for kwargs in [dict(design_bounds=(-1.1,1.)),dict(design_bounds=(.1,.2),design_initial=0.),
            dict(position_weight=0.),dict(speed_weight=4.1),dict(secondary_coefficient=.01),
            dict(initialization='saved_schedule'),dict(objective_mode='task_gap',secondary_coefficient=.001)]:
            with self.assertRaises(ValidationError):Candidate(**kwargs)
        self.assertEqual(Candidate(design_bounds=(.2,.2),design_initial=.2).design_initial,.2)

    def test_plan_operations_match(self):
        ref=dict(artifact_id='a'*64,media_type='application/json')
        base=dict(hypothesis='h',supporting_evidence=[ref],weakening_observation='o',fixed_conditions='f',
            revision_or_stop_rule='r',disposition='d',limitations=['l'])
        with self.assertRaises(ValidationError):Plan(action='batch',**base)
        with self.assertRaises(ValidationError):Plan(action='stop',requested_nlp_solves=1,**base)
        self.assertEqual(Plan(action='batch',candidates=[Candidate()],requested_nlp_solves=1,requested_replays=1,**base).action,'batch')

    def test_refined_rollout_actual_design_and_continuous_zero(self):
        # Analytic implicit integrator checks saved schedule, nonzero design and switches.
        w=Workspace.__new__(Workspace);w.n=w.m=1;w.steps=70;w.substeps=2;w.h=.005;w.scales=np.array([10.,1000.])
        a=ca.MX.sym('a',2);b=ca.MX.sym('b',2);u=ca.MX.sym('u');d=ca.MX.sym('d')
        w.step=ca.Function('toy_step',[a,b,u,d],[ca.vertcat((b[0]-a[0]-w.h*b[1])/10.,(b[1]-a[1]-w.h*(u+d))/.001)])
        schedule=np.r_[np.full(10,.2),np.full(25,.4)][:,None]
        result=w.rollout(schedule,.5)
        self.assertIsNone(result['failure']);self.assertEqual(len(result['states']),71)
        np.testing.assert_array_equal(result['states'][0],[0.,0.])
        self.assertAlmostEqual(result['states'][-1][1],.7*.1+.9*.25,places=12)
        self.assertLess(max(r['max_normalized_residual'] for r in result['residuals']),1e-10)


def numerical_semantics(configuration):
    """One actual graph, nonzero design, coherent zero rollout, shared slack semantics."""
    w=Workspace(configuration,local_ad='automatic')
    research=dict(design_bounds=[-.5,-.5],design_initial=-.5,objective_mode='task_gap',
        position_weight=1.,speed_weight=1.,secondary_coefficient=0.)
    problem=w.assemble('B','pretension_0_2',research)
    item=assess(w,problem,problem.initial_guess)
    if problem.initial_guess['design/d']!=-.5 or item['hard_max_normalized_violation']>1e-7:
        raise AssertionError('ACTUAL_DESIGN_INITIALIZATION_NOT_COHERENT')
    if not item['relaxed_nlp_feasible'] or item['original_task_feasible']:
        raise AssertionError('SLACK_SEMANTICS_MUST_SEPARATE_RELAXED_AND_ORIGINAL_ACCEPTANCE')
    if len([name for name in problem.variables if name.startswith('slack/')])!=2:raise AssertionError('TWO_SHARED_SLACKS_REQUIRED')
    return dict(status='passed',design_initial=-.5,hard_residual=item['hard_max_normalized_violation'],
        relaxed_feasible=item['relaxed_nlp_feasible'],original_task_feasible=item['original_task_feasible'],
        slacks=item['slack_values'],original_gaps=item['original_task_gaps'],nlp_invocations=0)


if __name__=='__main__':unittest.main()
