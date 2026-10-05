import time
import unittest
import json
import numpy as np
from tools.state_io import read
from tools.platform_store import Store
from examples import milestone5_predictor_development as stage
from examples import milestone5_first_interval as previous
from examples import milestone5_preparation as preparation
from extensions.tendon_family.milestone5_first_interval import integrate,stable,differences
from extensions.tendon_family.milestone5_serial_output import SerialOutput
from extensions.tendon_family.diagnostic_evidence import BoundReader


class PredictorRiskTests(unittest.TestCase):
    def test_diagnostic_cap_does_not_change_default(self):
        class Model:
            step_s=.01/640;n=1;scales=np.ones(2)
            def step(self,seed,x,u):return x
            def residual(self,x,y,u):return np.zeros(2)
            def motion(self,q,v):return np.zeros(3),np.zeros(3)
        with self.assertRaisesRegex(ValueError,'FIRST_INTERVAL_GRID'):integrate(Model(),[0.,0.],[],time.perf_counter()+2.)
        r=integrate(Model(),[0.,0.],[],time.perf_counter()+2.,max_substeps=2560)
        self.assertEqual(r['step_count'],640)

    def test_serial_velocity_derivative_and_real_state_alignment(self):
        store=Store(stage.RUN);binding=read(stage.RUN/'freeze.json')['bindings'][0]
        r=BoundReader(store,binding);source=r.resolve(r.binding['execution_id'])
        out=SerialOutput(source['configuration'],r.read_file(source,'resolved_physics.json'),r.read_file(source,'compiled_physics.json'),store.artifact(source['files']['robot.xml'],raw=True).decode('utf8'))
        spec=read(previous.RUN/'specification.json');z=spec['observed_projected_state']
        self.assertLess(out.differential_check(z),1e-7)
        end=out.motion(z);self.assertLess(np.linalg.norm(np.asarray(end['velocity_m_s'])-spec['observed']['velocity_m_s']),2e-5)

    def test_same_grant_receipts_and_immutable_predecessors(self):
        stage.check_previous();s=Store(stage.RUN)
        self.assertEqual(s.config()['budget'],stage.LIMITS)
        with s.connect(True) as db:receipts=[__import__('json').loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
        # No running reservation may be mistaken for a completed actual charge.
        self.assertTrue(all(abs(sum(r['charged'][k] for r in receipts)-v)<1e-7 for k,v in s.remaining()['used'].items()))
        self.assertTrue(all(r['tool_id']!='simulation.run' for r in receipts))

    def test_reference_resolution_is_separate_from_backend_error(self):
        reference=read(stage.EVIDENCE/'reference.json')
        results=reference['results'];delta=differences(results)[-2:]
        self.assertEqual(len(results),8)
        self.assertEqual(reference['new_integration_attempts'],3)
        self.assertEqual(reference['failed_attempts'],1)
        self.assertFalse(stable(results))
        self.assertGreater(delta[0]['velocity_m_s'],1e-4)
        self.assertGreater(delta[0]['speed_m_s'],1e-4)
        self.assertLessEqual(delta[1]['velocity_m_s'],1e-4)
        self.assertLessEqual(delta[1]['speed_m_s'],1e-4)
        self.assertTrue(all(np.isfinite(r['state']).all() and r['max_scaled_residual']<=1e-5 for r in results))
        self.assertGreater(results[-1]['velocity_error_norm_m_s'],1e-2)
        corrected=read(stage.EVIDENCE/'assessment.json')
        self.assertFalse(corrected['cases'][0]['locals'][0]['reference_supported'])
        self.assertTrue(all(c['locals'][2]['reference_supported'] for c in corrected['cases']))

    def test_forecast_reuse_and_split_research_binding(self):
        a=read(stage.RUN/'assessment.json')
        for c in a['cases']:
            saved=read(preparation.RUN/(c['candidate_id']+'.json'))['result']
            self.assertEqual(len(c['forecast']['rows']),len(saved['rows']))
            for original,changed in zip(saved['rows'],c['forecast']['rows']):
                for field in ('initial_state','state','input_n','previous_input_n','plan_identity'):self.assertEqual(original[field],changed[field])
            self.assertEqual(c['forecast']['solves'],35)
            self.assertTrue(c['forecast']['complete'])
        protocol=read(stage.EVIDENCE/'protocol.json')
        self.assertTrue(protocol['research_pair_selected'])
        self.assertTrue(protocol['research_interpretation_complete'])
        stores=dict(selection=Store(previous.RUN),interpretation=Store(stage.RUN))
        for phase,ref in protocol['research_decisions'].items():
            source=stores[phase]
            with source.connect(True) as db:
                receipts=[json.loads(r[0]) for r in db.execute("SELECT receipt FROM calls WHERE receipt IS NOT NULL AND status='completed'")]
            self.assertTrue(any(r['tool_id']==preparation.RESEARCH.extension_id and source.artifact(r['output']).get('reference')==ref for r in receipts))
            self.assertEqual(source.artifact(ref)['phase'],phase)
        accepted=stores['interpretation'].artifact(protocol['research_decisions']['interpretation'])
        self.assertEqual(accepted,read(stage.EVIDENCE/'interpretation_response.json'))
        self.assertNotEqual(accepted,read(stage.EVIDENCE/'interpretation_response_v1.json'))
        self.assertFalse(protocol['ready_for_bounded_prospective_experiment'])
        self.assertEqual(protocol['batches'][0]['scenario_id'],'incumbent_checkpoint_20_new_clock')
        self.assertEqual(len(protocol['batches']),1)
        self.assertFalse(read(stage.EVIDENCE/'protocol_seal.json')['backend_grant_materialized'])


if __name__=='__main__':unittest.main()
