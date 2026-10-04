"""Focused causal/history/seal checks. No backend or prospective numerical forecast."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import tempfile
from uuid import uuid4
import numpy as np
from tools.state_io import read
from examples.milestone5_preparation import RUN,ROOT,calculate
from extensions.tendon_family.milestone5_preparation import history,grid
from extensions.tendon_family.milestone5_protocol import pair_decision,seal_pair,checkpoint_observer,assess_screening


class MemoryStore:
    def __init__(self):self.state={};self.values={};self.events=[];self.backend=False
    @contextmanager
    def transaction(self):yield self
    def execute(self,query,*args):
        if 'COUNT' in query:return SimpleNamespace(fetchone=lambda:[int(self.backend)])
        return [dict(execution_id='future-fixture',request_id='complete-simulation')]
    def session(self,*args):return dict(state=self.state)
    def update_state(self,db,run,state):self.state=state
    def put(self,db,value):
        ref=dict(artifact_id=str(len(self.values)),media_type='application/json');self.values[ref['artifact_id']]=deepcopy(value);return ref
    def artifact(self,ref):return deepcopy(self.values[ref['artifact_id']])
    def event(self,db,run,kind,status,**kwargs):self.events.append((kind,status,kwargs))


class WorkspaceFixture:
    def __init__(self,task,robot,p,x,u,settling=None):
        self.parameters=SimpleNamespace(**p);self.n=len(x)//2;self.target=np.zeros(3);self.last=None
        self.problem=None;self.solver=SimpleNamespace(evaluate_candidate=lambda *args:dict(feasible=True))
        self.weight=p['holding_tip_speed_weight']
    def solve(self,x,previous,warm=None,elapsed_s=None):
        # An actual weight-dependent state/control relation after .20, independent of any outcome file.
        u=np.asarray(previous)+self.weight*(1. if elapsed_s>=.2 else 0.)
        output=dict(accepted=True,tensions=[u.tolist()]*self.parameters.horizon,
            states=[list(x)]*(self.parameters.horizon+1),result=dict(optimum={}),
            diagnostics=dict(selected_feasible_iteration=0,policy_stop_reason='fixture'),warm_start=dict(executed_intervals=int(warm is None)))
        self.last=output;return output
    def _extend_tail(self,x,u):return np.asarray(x)+sum(u)*.001,dict(integration_s=0.,extended_tail_scaled_defect=0.)
    def _motion(self,q,v):return np.asarray(q[:3]),np.asarray(v[:3])


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cfg=read(RUN/'registration.json')['development_configuration']
    def test_independent_histories_and_full_clock(self):
        guesses=dict(nominal=dict(q0=[0.]*12,u0=[.2]*6),warm_guess=dict(states=[[0.]*24]*11,tensions=[[.2]*6]*10),provenance={})
        counts=[];original=deepcopy(self.cfg)
        def run(weight):
            cfg=deepcopy(self.cfg);cfg['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=weight
            return history(cfg,[0.]*24,lambda:counts.append(1),deadline=float('inf'),workspace_factory=WorkspaceFixture)
        with patch('extensions.tendon_family.gvs_profile.reach_numerical',return_value=guesses):
            a=run(.075);b=run(.15);again=run(.075)
        self.assertEqual(len(a['rows']),35);self.assertEqual(len(counts),105)
        self.assertEqual(a['rows'][0]['previous_input_n'],b['rows'][0]['previous_input_n'])
        self.assertEqual(a['rows'][-1]['state'],again['rows'][-1]['state'])
        self.assertNotEqual(a['rows'][-1]['state'],b['rows'][-1]['state'])
        self.assertEqual(a['rows'][30]['effective_horizon'],5);self.assertEqual(a['rows'][-1]['effective_horizon'],1)
        self.assertAlmostEqual(a['rows'][-1]['endpoint_s'],.35);self.assertEqual(self.cfg,original)
        self.assertEqual(guesses['warm_guess']['states'][0],[0.]*24)
    def forecasts(self):
        from extensions.tendon_family.gvs_profile import execution_scope
        from tools.state_io import digest
        return [dict(candidate_id=n,recipe_id=n,scenario_id='s',version='candidate_history@1.0.0',complete=True,scientific_identity=digest(execution_scope(self.cfg)),
            rows=[dict(accepted=True)],metrics=dict(holding_max_error_m=.001,terminal_error_m=.001,holding_max_speed_m_s=v)) for n,v in [('a',.01),('b',.015)]]
    def test_pair_seal_and_revision_barrier(self):
        store=MemoryStore();f=self.forecasts();p=dict(recipes=[dict(recipe_id='a',configuration=self.cfg),dict(recipe_id='b',configuration=self.cfg)],task_interval_s=[0,.35],controller='controller.gvs_nmpc@7.0.0');scenario=dict(scenario_id='s',configuration=self.cfg)
        with self.assertRaisesRegex(ValueError,'BOTH'):seal_pair(store,'run',p,scenario,f[:1])
        ref=seal_pair(store,'run',p,scenario,f);self.assertEqual(store.artifact(ref)['pair_decision']['order'],['a','b'])
        f[0]['metrics']['holding_max_speed_m_s']=.019
        with self.assertRaisesRegex(ValueError,'IMMUTABLE'):seal_pair(store,'run',p,scenario,f)
        store.backend=True
        with self.assertRaisesRegex(ValueError,'STARTED'):seal_pair(store,'run',p,scenario,f)
    def test_checkpoint_causality_and_seal_before_advance(self):
        store=MemoryStore();seal=dict(artifact_id='pair',media_type='application/json');store.state['m5_pair_seal']=seal
        controller=SimpleNamespace(last=dict(desired_tension_n=[1.]),observations=[dict(measured_initial_state=[0.,0.])])
        observer=checkpoint_observer(store,'run',{},seal,dict(local_step_s=.000125))
        with patch('extensions.tendon_family.milestone5_protocol.local_forecast',return_value=dict(start_s=.2,end_s=.21)) as forecast:
            observer(20,.2,controller,dict(tip=np.zeros(3)),np.zeros(3),np.array([1.]))
            store.events.append(('backend','advance',{}))
            self.assertEqual(store.events[0][1],'sealed_before_step')
            self.assertEqual(forecast.call_args.args[2].tolist(),[1.])
            with self.assertRaisesRegex(ValueError,'CAUSAL'):observer(20,.2,controller,dict(tip=np.zeros(3)),np.zeros(3),np.array([2.]))
    def test_real_store_schema_and_sealed_calculation_reuse(self):
        from tools.platform_store import Store
        from tools.platform_host import Host
        from tools.state_io import digest
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            budget=dict(model_calls=0,tool_calls=2,backend_solves=0,worker_calls=0,wall_s=10.)
            store=Store(folder);store.create(dict(project_id='readiness-'+uuid4().hex,grant_id='fixture-'+uuid4().hex,budget=budget,authorization_source='Synthetic static readiness fixture, no backend advancement'))
            cfg=deepcopy(self.cfg);cfg['run_id']='fixture';cfg['policy'].update(budget=budget,allowed_tools=[],tool_bindings={})
            h=Host(folder,'fixture');h.create(cfg)
            p=dict(recipes=[dict(recipe_id='a',configuration=self.cfg),dict(recipe_id='b',configuration=self.cfg)],task_interval_s=[0,.35],controller='controller.gvs_nmpc@7.0.0')
            seal=seal_pair(store,'fixture',p,dict(scenario_id='s',configuration=self.cfg),self.forecasts())
            self.assertEqual(store.session('fixture')['state']['m5_pair_seal'],seal)
            store.reserve('fixture','complete-simulation',digest({}),'local-human',dict(model_calls=0,tool_calls=1,backend_solves=0,worker_calls=0,wall_s=1.))
            with self.assertRaisesRegex(ValueError,'STARTED'):seal_pair(store,'fixture',p,dict(scenario_id='s',configuration=self.cfg),self.forecasts())
        receipt=read(RUN/'reference_receipt.json');output=dict(detail=dict(result='cached'))
        fake=SimpleNamespace(run_id='reference',store=SimpleNamespace(lookup=lambda *args:dict(receipt=__import__('json').dumps(receipt)),artifact=lambda ref:output))
        with patch('examples.milestone5_preparation.host',return_value=fake),patch('examples.milestone5_preparation.atomic_json'):
            self.assertEqual(calculate('reference',dict(operation='reference')),output['detail'])
    def test_abstention_and_false_safe_are_scored(self):
        f=self.forecasts();f[1]['metrics']['holding_max_speed_m_s']=.01001;decision=pair_decision(f)
        self.assertIsNone(decision['order'])
        score=assess_screening(decision,[dict(candidate_id='a',holding_max_speed_m_s=.03,joint_acceptance=False),dict(candidate_id='b',holding_max_speed_m_s=.01,joint_acceptance=True)],1,10)
        self.assertIsNone(score['accuracy_among_resolved']);self.assertEqual(score['predicted_safe_observed_violating'],['a'])
    def test_blocked_protocol_cannot_start_future_work(self):
        from examples.milestone5_future_validation import readiness,execute
        protocol=read(ROOT/'evidence/milestone5_preparation_20261005/protocol.json')
        with patch('examples.milestone5_future_validation.future_preview') as preview,patch('examples.milestone5_future_validation.complete_execution') as backend:
            self.assertFalse(readiness(protocol)['passed'])
            with self.assertRaisesRegex(ValueError,'NOT_READY'):execute(protocol,1,ROOT/'uncreated-grant.json')
            preview.assert_not_called();backend.assert_not_called()


if __name__=='__main__':unittest.main()
