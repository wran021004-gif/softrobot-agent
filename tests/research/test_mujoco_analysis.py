"""Native public boundaries and existing L1/L3 projections; synthetic fixtures."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from tools.platform_store import plain
from tools.state_io import digest
from tools.research import analysis
from tools.research.contracts import AnalysisRequest,NativeAnalysisOptions
from tools.research.native_analysis import assessment,applicability,structure_context
from tools.research.core import read_evidence
from tools.research.evidence_views import result_card
from tools.research.research_context import mathematical_decision_view
from tests.research.test_research_reporting import ReportingTests,offline_host


class NativeAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):ReportingTests.setUpClass()

    def setUp(self):
        self.f=ReportingTests();self.f.setUp();self.t=self.f.fixture
        self.q=AnalysisRequest(candidate=self.t.ref,operation='native_dynamics_v1',model_source='mujoco',
            operating_point='saved_state',saved_state=self.t.ref,protocol=self.t.q.protocol)

    def test_native_source_and_legacy_request_identity(self):
        legacy=plain(self.t.q)
        self.assertNotIn('model_source',legacy)
        self.assertEqual(digest(legacy),digest(plain(AnalysisRequest.model_validate(legacy))))
        for changed in (dict(model_source='controller'),dict(operation='controllability',scoring_window_s=.35),dict(operating_point='controller_start_input',saved_state=None)):
            with self.subTest(changed=changed),self.assertRaises(ValueError):AnalysisRequest.model_validate({**plain(self.q),**changed})
        # No native state: fail before compiling a model, rather than project GVS.
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',side_effect=AssertionError('NO_BUILD')):
            out=analysis.calculate(self.t.cfg,self.t.binding,self.q,dict(x=[0.]*24,actual_time_s=.34))
        self.assertEqual(out['status'],'not_applicable')

    def test_actual_bounds_one_sided_difference(self):
        from extensions.tendon_family.mujoco_analysis import input_response
        seen=[]
        class Fixture:
            limits=np.array([[0.,8.],[0.,8.]])
            tendons=['upper','lower']
            def rollout(self,start,u,horizon):
                self.assertion=bool(np.all(u>=0) and np.all(u<=8));assert self.assertion
                seen.append(np.array(u))
                return dict(tip_position_m=[u[0]+2*u[1],0.,0.],tip_velocity_m_s=[0.,3*u[0]-u[1],0.],actual_tensions_n=list(u))
        r=input_response(Fixture(),None,[8.,0.],NativeAnalysisOptions())
        self.assertTrue(all(p['scheme']=='one_sided' for p in r['probes']))
        np.testing.assert_allclose(r['position_input_jacobian_m_n'],[[1.,2.],[0.,0.],[0.,0.]],atol=1e-10)
        self.assertTrue(r['step_consistency_passed'])

    def test_structure_context_requires_single_fixed_parameter(self):
        base=dict(parameters=dict(segments=dict(distal1=dict(young_pa=6e6))),configuration=self.t.cfg)
        other=deepcopy(base);other['parameters']['segments']['distal1']['young_pa']=5.9e6
        request=SimpleNamespace(variable='segments.distal1.young_pa')
        row=structure_context(base,[(self.t.ref,other)],request)[0]
        self.assertEqual(row['delta'],-1e5)
        other['configuration']['task']['seed_fixture']=1
        with self.assertRaisesRegex(ValueError,'FIXED_TASK'):structure_context(base,[(self.t.ref,other)],request)

    def test_owned_native_prefix_uses_execution_science_without_projected_optimizer_record(self):
        from tools.research.numerics import native_point
        from unittest.mock import Mock
        cfg=self.t.cfg;executed=deepcopy(cfg);executed['run_id']='execution-child-owner'
        result_ref=dict(artifact_id='b'*64,media_type='application/json')
        values={result_ref['artifact_id']:dict(candidate=self.f.candidate,execution_id='fixture-execution')}
        host,current=offline_host(values,results=[result_ref])
        query=self.q.model_copy(update=dict(saved_state=None,execution=result_ref,update_id=0))
        source=dict(configuration=executed,files={'trajectory.json.gz':self.t.ref})
        files={'trajectory.json.gz':[dict(tension_n=[.2]*6)],
            'resolved_physics.json':dict(identity='fixture',dofs=['hinge'],tendons=[dict(entity='t'+str(i)) for i in range(6)]),
            'experiment_scene.json':dict(control=dict(tension_execution_mode='ideal_tension'),qpos_rad=[0.],qvel_rad_s=[0.])}
        reader=Mock();reader.resolve.return_value=source;reader.read_file.side_effect=lambda s,name:files[name]
        with patch('extensions.tendon_family.control_evidence.ControlEvidence',return_value=reader):
            point=native_point(host,query,cfg)
        self.assertEqual(point['native_replay']['rows'],[])
        self.assertEqual(point['u'],[.2]*6)
        self.assertNotIn('x',point)

    def test_native_result_reuses_card_summary_and_pointer_reads(self):
        from schemas.platform import SessionInput
        point=dict(actual_time_s=.34,integration_state=[1.],phase='interval_start_native',input_units='N')
        fit=applicability(self.t.req,self.q,assessment(SessionInput.model_validate(self.t.cfg),self.t.req),point)
        raw=dict(status='computed',candidate=self.f.candidate,binding=self.t.binding,operation=self.q.operation,
            model_identity='fixture-native-identity',operating_point={k:v for k,v in point.items() if k!='integration_state'},
            native_dynamics=dict(matrix=[[0.]*48 for _ in range(48)],mechanics=dict(balance=1e-14)),
            native_analysis=dict(question='fixture mechanics',basis=dict(model='fixture native',state_time_s=.34),
                quantities=[dict(name='balance',value=1e-14,unit='N*m',source_pointer='/native_dynamics/mechanics/balance')],
                interpretation='Synthetic native projection fixture',unresolved=['Full task unmeasured'],cost={}),
            charged_analysis_evaluations=1,charged_numerical_s=.01)
        raw=analysis.scoped_result(raw,self.t.req,fit,self.q)
        reference=self.f.put(raw);host,current=offline_host(self.f.values,analysis_results=[reference])
        before=deepcopy(current);card=plain(result_card(host,reference));view=mathematical_decision_view(card)
        self.assertEqual(card['evidence_summary']['claim_kind'],'NUMERICAL_DIAGNOSTIC')
        self.assertEqual(view['quantities'][0]['value'],1e-14)
        self.assertEqual(read_evidence(host,view['quantities'][0]['source'],record_read=False),1e-14)
        self.assertLess(len(json.dumps(view)),4500)
        self.assertNotIn('matrix',json.dumps(view));self.assertEqual(current,before)
        self.assertEqual(read_evidence(host,dict(reference=reference,pointer='/native_dynamics/matrix'),record_read=False),raw['native_dynamics']['matrix'])


if __name__=='__main__':unittest.main()
