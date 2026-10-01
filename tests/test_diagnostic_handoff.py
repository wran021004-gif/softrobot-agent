"""Focused contracts, real saved-evidence binding, accounting and kinematics."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase,main
from uuid import uuid4
import itertools
import numpy as np
from schemas.platform_handoff import EvidenceSelector,DesignResponse,DiagnosisSubmission
from tools.platform_handoff import validate_selector,respond,submit
from tools.platform_store import Store,plain,encode
from tools.platform_host import Host
from tools.platform_diagnosis_coordinator import configure_role,transfer_recovery
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader,BoundQuery,inspect,add_velocity_comparisons
from extensions.tendon_family.control_evidence import ControlEvidence,aligned_interval_predictions
from extensions.tendon_family.diagnostic_math import endpoint_acceleration,braking_box_input,charge_units

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'runs/stage341_autonomous_20261001'
EXECUTION='5991de53e82747439e87ba8569667e1b'


class HandoffTests(TestCase):
    def setUp(self):
        if not (SOURCE/'platform.sqlite').exists():self.skipTest('Local-only historical source unavailable')
        self.temp=TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.cleanup_store)
        self.store=Store(self.temp.name);self.run='diagnostic-test-'+uuid4().hex
        self.budget=dict(tool_calls=5,model_calls=2,backend_solves=0,worker_calls=0,wall_s=100.)
        self.store.create(dict(project_id=self.run,grant_id=self.run,budget=self.budget,authorization_source='Focused offline implementation test'))
        self.reader=ControlEvidence(Store(SOURCE));self.source=self.reader.resolve(EXECUTION)
        from examples.stage342_diagnostic_cycle import input_for_role,DESIGN,DIAGNOSTIC
        self.host=Host(self.temp.name,self.run)
        inp=input_for_role(self.source['configuration'],self.run,DESIGN);inp['policy']['budget']=self.budget
        self.host.create(inp)
        self.binding=import_execution(self.reader,EXECUTION,self.store,self.run,self.source['manifest'])
        self.bound=BoundReader(self.store,self.binding)

    def cleanup_store(self):
        # SQLite context managers commit but CPython closes cycles on collection.
        # Collect before Windows removes the temporary store's open database.
        import gc
        gc.collect()
        self.temp.cleanup()

    def test_binding_preserves_owner_and_rejects_wrong_manifest(self):
        s=self.bound.resolve(EXECUTION)
        self.assertEqual(s['owner'],self.source['owner']);self.assertNotEqual(s['owner'],self.run)
        self.assertEqual(s['configuration'],self.source['configuration'])
        self.assertNotIn('result_executions',self.store.session(self.run)['state'])
        with self.assertRaisesRegex(ValueError,'OWNERSHIP'):
            import_execution(self.reader,EXECUTION,self.store,self.run,dict(artifact_id='0'*64,media_type='application/json'))
        bad=self.store.artifact(self.binding);bad['source']['owner']=self.run
        with self.store.transaction() as db:ref=plain(self.store.put(db,bad))
        with self.assertRaisesRegex(ValueError,'IDENTITY'):BoundReader(self.store,ref).resolve(EXECUTION)

    def test_velocity_is_reconstructed_and_missing_plans_stay_missing(self):
        from unittest.mock import patch
        with patch('extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.solve',side_effect=AssertionError('READ_ONLY')):
            result=inspect(self.bound,self.binding,BoundQuery(binding=self.binding,view='prediction',update_ids=[30,34]))
        detail=result.detail
        self.assertFalse(detail['summary']['full_snapshots_available'])
        self.assertTrue(detail['summary']['reach_passed']);self.assertFalse(detail['summary']['sampled_settling_passed'])
        for row in detail['evidence']['observations']['aligned_intervals']:
            v=row['velocity'];self.assertEqual(v['status'],'aligned')
            self.assertAlmostEqual(v['vector_difference_norm_m_s'],np.linalg.norm(np.array(v['predicted_m_s'])-v['measured_m_s']))
        self.assertAlmostEqual(detail['summary']['terminal_speed_m_s'],.635173,places=5)

    def test_selectors_and_design_linkage(self):
        with self.store.transaction() as db:ref=plain(self.store.put(db,{'facts':{'value':7}}))
        selector=EvidenceSelector(reference=ref,pointer='/facts/value',value=7)
        self.assertEqual(validate_selector(self.store,selector),7)
        with self.assertRaisesRegex(ValueError,'VALUE_MISMATCH'):validate_selector(self.store,selector.model_copy(update={'value':8}))
        configure_role(self.host,'design','test',report=ref)
        ctx=SimpleNamespace(store=self.store,run_id=self.run)
        with self.assertRaisesRegex(ValueError,'REPORT_LINK'):
            respond(ctx,DesignResponse(report=self.binding,disposition='reject',reasoning='test',next_action='stop'))
        configure_role(self.host,'diagnostic','test',request=ref)
        with self.assertRaisesRegex(ValueError,'REPORT_REQUEST'):
            submit(ctx,DiagnosisSubmission(request=self.binding,report=dict(subject='test',source=self.binding),fact_selectors={},missing_evidence=[],recommendations=[]))

    def test_project_accounting_and_recovery_are_shared(self):
        from examples.stage342_diagnostic_cycle import input_for_role,DIAGNOSTIC
        other=Host(self.temp.name,self.run+'-other');inp=input_for_role(self.source['configuration'],other.run_id,DIAGNOSTIC);inp['policy']['budget']=self.budget;other.create(inp)
        from tools.platform_store import zero
        cost={**zero(),'model_calls':1,'wall_s':1.}
        self.store.reserve(self.run,'attempt-a','hash-a','model-transport',cost)
        self.store.reserve(other.run_id,'attempt-b','hash-b','model-transport',cost)
        with self.assertRaisesRegex(ValueError,'BUDGET_EXHAUSTED'):self.store.reserve(other.run_id,'attempt-c','hash-c','model-transport',cost)
        with self.store.transaction() as db:
            state=self.store.session(self.run,db)['state'];state['protocol_corrections_used']=3;self.store.update_state(db,self.run,state)
            db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits={'local_solves':2},used={'local_solves':0})),))
        transfer_recovery(self.host,other);self.assertEqual(self.store.session(other.run_id)['state']['protocol_corrections_used'],3)
        for h in (self.host,other):charge_units(SimpleNamespace(store=self.store,run_id=h.run_id,row={'request_id':'offline'}),'local_solves',1)
        with self.assertRaisesRegex(ValueError,'WORK_LIMIT'):charge_units(SimpleNamespace(store=self.store,run_id=self.run,row={'request_id':'offline'}),'local_solves',1)

    def test_model_requested_subgrant_is_enforced_before_work(self):
        from tools.platform_diagnosis_coordinator import bind_diagnostic_grant
        from tools.platform_store import zero
        b=self.store.artifact(self.binding)
        request=dict(question='Inspect the saved result',subject='control',binding=self.binding,
            **{k:b[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest')},
            permitted_tools=['evidence.read'],scope=['saved evidence only'],
            budget={**self.budget,'model_calls':1,'tool_calls':1},stopping_conditions=['request budget exhausted'])
        with self.store.transaction() as db:ref=plain(self.store.put(db,request))
        bind_diagnostic_grant(self.host,ref)
        cost={**zero(),'model_calls':1,'wall_s':1.}
        self.store.reserve(self.run,'first','hash-first','model-transport',cost)
        with self.assertRaisesRegex(ValueError,'diagnostic request subgrant'):
            self.store.reserve(self.run,'second','hash-second','model-transport',cost)
        receipt=self.host.invoke(dict(request_id='forbidden',tool_id='diagnosis.request',tool_version='1.0.0',arguments={},reason='offline scope test'))
        self.assertIn('TOOL_NOT_IN_DIAGNOSTIC_REQUEST_SCOPE',receipt['error'])

    def test_compact_prediction_fits_host_envelope_and_rejects_query_as_binding(self):
        result=inspect(self.bound,self.binding,BoundQuery(binding=self.binding,view='prediction'))
        with self.store.transaction() as db:ref=plain(self.store.put(db,result))
        from schemas.platform import ToolReceipt
        from tools.platform_store import zero
        receipt=plain(ToolReceipt(request_id='offline',execution_id='offline',caller='local-human',
            tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',execution_status='completed',output=ref,charged=zero()))
        self.assertFalse(self.host.observation(receipt)['truncated'])
        with self.assertRaisesRegex(ValueError,'EXPLICIT_EXECUTION_BINDING_REQUIRED'):BoundReader(self.store,ref)


class NumericalTests(TestCase):
    def test_kinematic_acceleration_and_unilateral_box(self):
        # A rotating endpoint's acceleration includes the centripetal term.
        q=.4;rate=2.;qdd=-.7
        J=np.array([[-np.sin(q)],[np.cos(q)],[0.]])
        kin=np.array([-np.cos(q),-np.sin(q),0])*rate**2
        actual=endpoint_acceleration(J,[qdd],kin)
        def tip(t):
            a=q+rate*t+.5*qdd*t*t
            return np.array([np.cos(a),np.sin(a),0])
        h=1e-4;numerical=(tip(h)-2*tip(0)+tip(-h))/h**2
        np.testing.assert_allclose(actual,numerical,atol=1e-7)
        v=np.array([1.,2.,0.]);B=np.array([[2.,-3.],[1.,.2],[0.,0.]])
        chosen=braking_box_input(v,B,[4.,5.],[1.,1.])
        value=v@B@chosen
        self.assertAlmostEqual(value,min(v@B@np.array(u) for u in itertools.product([0.,4.],[0.,5.])))
        np.testing.assert_equal(braking_box_input(np.zeros(3),B,[4.,5.],[1.,2.]),[1.,2.])

    def test_alignment_rejects_frame_and_separates_speed_from_vector_error(self):
        u=dict(time_s=.1,phase='current_state_before_integration',tip_position_m=[0,0,0],actual_tension_n=[1.],
            one_step_prediction=dict(time_s=.11,frame='world',applied_tension_n=[1.],tip_position_m=[.01,0,0],tip_velocity_m_s=[1.,0,0]))
        rows=[dict(time_s=.11,tip_m=[.012,0,0])];commands=[dict(time_s=.1,desired_tension_n=[1.])]
        good,_=aligned_interval_predictions(rows,[u],commands,.01,[.02,0,0],[0])
        add_velocity_comparisons(good,[u],[dict(time_s=.11,velocity_m_s=[-1.,0,0])])
        self.assertEqual(good[0]['velocity']['vector_difference_norm_m_s'],2.)
        self.assertEqual(good[0]['velocity']['predicted_speed_m_s'],good[0]['velocity']['measured_speed_m_s'])
        u['one_step_prediction']['frame']='local'
        good,missing=aligned_interval_predictions(rows,[u],commands,.01,[.02,0,0],[0])
        self.assertFalse(good);self.assertTrue(missing)


if __name__=='__main__':main()
