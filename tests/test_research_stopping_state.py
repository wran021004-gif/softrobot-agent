"""Focused current-policy and exact execution-state checks; no new science."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from schemas.research_core import AnalysisRequest, LocalDiagnostic
from tools.research import core, analysis, numerics, diagnostic
from extensions.tendon_family.contracts import current_nmpc_recipe


class StoppingStateTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=core.ROOT/'runs',prefix='stopping-state-')
        path=Path(self.temp.name);spec=core.read(core.DEFAULT_SPEC)
        spec.update(study_id=path.name,started_unix=time.time())
        core.atomic_json(path/'spec.json',spec);self.host=core.prepare(path/'spec.json',path/'store')
        core.update(self.host,freeze='fixture',core_hashes=core.core_hashes())

    def tearDown(self):
        import gc
        gc.collect();self.temp.cleanup()

    def test_resolved_policy_and_exact_diagnostic_keep_original_problem_options(self):
        s=core.state(self.host);recipe=s['profile']['recipe']
        self.assertEqual((recipe['stopping_policy'],recipe['max_iterations'],recipe['tolerance']),('research_work_v1',120,1e-6))
        self.assertIsNone(recipe['max_cpu_s']);self.assertIsNone(recipe['feasible_return'])
        self.assertEqual(s['nominal_configuration']['policy']['controller']['parameters']['data']['recipe']['stopping_policy'],'historical_timed_v1')
        with self.assertRaises(ValueError):current_nmpc_recipe(recipe,{'max_cpu_s':30})
        summary=core.read(core.ROOT/'evidence/research_chain_20261014/scientific_summary.json')
        ref=summary['nmpc_results'][1]['reference']
        with patch.object(core,'guard'):info=numerics.import_execution(self.host,'evidence/research_chain_20261014',ref,[0])
        source=numerics.execution_update(self.host,ref,0);record=source['record']
        workspace=SimpleNamespace(problem=None,parameters=SimpleNamespace(),solver=None,_tail_solver=None)
        workspace._set_prediction_time=lambda t:None
        def solved(ws,rec):
            options=ws.solver.parameters.model_dump(mode='json')
            self.assertEqual(options['max_iterations'],120)
            for key in ('max_cpu_s','max_wall_s','feasible_return'):self.assertIsNone(options[key])
            for key in ('constraint_jacobian_mode','hessian_approximation','acceptable_tolerance'):
                self.assertEqual(options[key],rec['initialization']['solver_options'][key])
            self.assertEqual(ws.problem.variables,rec['problem_variables'])
            self.assertEqual(ws.problem.initial_guess,rec['initial_guess'])
            return {}
        with patch.object(diagnostic,'TrajectoryWorkspace',return_value=workspace),patch.object(diagnostic,'inspect_problem',return_value={}),patch.object(diagnostic,'_solve_record',side_effect=solved):
            value=diagnostic.replay(dict(configuration=source['configuration'],record=record,mode='research_policy',current_recipe=recipe,external_timeout_s=300))
        self.assertEqual(value['stopping_controls']['external_timeout_s'],300)
        self.assertEqual(LocalDiagnostic(execution=ref,update_id=0).mode,'research_policy')
        with self.assertRaises(ValueError):LocalDiagnostic(execution=ref,update_id=0,mode='production')

    def test_saved_plan_metrics_initializes_output_functions_without_solving(self):
        import numpy as np
        ws=SimpleNamespace(parameters=SimpleNamespace(horizon=1,substeps=1),period=.01,n=1,
            state_scales=np.ones(2),holding_start=.30,duration=.35,target=[0.,0.,0.],tendons=['a'])
        def prepare():ws._motion=lambda q,v:(np.zeros(3),np.zeros(3))
        ws._prepare_tail=prepare
        values={**{f'x/{k}/{j}':0. for k in range(2) for j in range(2)},'u/0/a':.2}
        self.assertEqual(diagnostic.plan_task_metrics(ws,values,.34)['holding_node_count'],2)

    def test_historical_and_current_state_phase_horizon_and_candidate_binding(self):
        h=self.host;s=core.state(h);summary=core.read(core.ROOT/'evidence/research_chain_20261014/scientific_summary.json')
        ref=summary['nmpc_results'][1]['reference']
        with patch.object(core,'guard'):info=numerics.import_execution(h,'evidence/research_chain_20261014',ref,[29,30])
        with patch.object(core,'guard'):
            with self.assertRaisesRegex(ValueError,'FRESH_EXECUTION_REQUIRES_CURRENT_PROFILE'):
                core.execute(h,info['candidate'],'historical-backend-rejected')
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        before=core.state(h);self.assertEqual(before['mathematical_evaluations'],0)
        def worker(command,log,timeout):
            req=core.read(command[-1]);point=req['exact_point'];record=numerics.execution_update(h,ref,30)['record']
            self.assertEqual(point['x'],record['measured_state']);self.assertEqual(point['u'],record['previous_applied_input_n'])
            self.assertEqual(point['phase'],'interval_start_previous_applied_input')
            self.assertAlmostEqual(point['remaining_task_s'],.05);self.assertEqual(point['actual_time_s'],.30)
            self.assertEqual(point['coordinate_order'],req['binding']['coordinate_order'])
            self.assertIsNotNone(point['backend_measurements']['tip_velocity_m_s'])
            core.atomic_json(Path(command[-1]).with_name('result.json'),dict(status='computed',substituted=True))
            return core.subprocess.CompletedProcess(command,0)
        query=dict(candidate=info['candidate'],execution=ref,update_id=30,operating_point='saved_state',operation='braking',protocol=s['spec']['analysis_protocol'])
        with patch('tools.service_execution._run_contained',side_effect=worker) as launched:
            analysis.dispatch(h,query,'state',guard=lambda *a:None,origin='engineering_preflight')
            analysis.dispatch(h,query,'state',guard=lambda *a:None)
            self.assertEqual(launched.call_count,1)
        self.assertEqual(core.state(h)['mathematical_evaluations'],1)
        query['candidate']=s['reference_candidate']
        with self.assertRaisesRegex(ValueError,'CANDIDATE_MISMATCH'):analysis.dispatch(h,query,'wrong',guard=lambda *a:None)
        query['saved_state']=ref
        with self.assertRaises(ValueError):AnalysisRequest.model_validate(query)
        source=numerics.execution_update(h,ref,30)
        current=core.save(h,dict(execution_id='new',candidate=info['candidate'],profile={'motion':host_motion(h,ref)}))
        core.update(h,results=[current])
        reader=SimpleNamespace(resolve=lambda _:dict(files={}),read_file=lambda *a:[source['observation']]*31)
        with patch('extensions.tendon_family.control_evidence.ControlEvidence',return_value=reader):
            # The same resolver also admits fresh execution evidence, without importing it as history.
            source['observation']['complete_update_record']['resolved_problem_reference']=None
            value=numerics.execution_update(h,current,30)
        self.assertFalse(value['imported_historical_evidence'])


def host_motion(host,ref):
    return host.store.artifact(ref)['profile']['motion']
