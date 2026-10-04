"""Focused accounting identities and alignment safeguards; no numerical rollouts."""
import unittest
import numpy as np
from extensions.tendon_family.milestone5_diagnostic import decomposition
from extensions.tendon_family.milestone5_validation import aligned_interval


class DiagnosticTests(unittest.TestCase):
    def test_vector_identity_and_equal_norms(self):
        # Equal speed norms hide a large orthogonal velocity projection error.
        initial=dict(projected=dict(position_m=[1,0,0],velocity_m_s=[1,0,0]),
                     backend=dict(position_m=[0,0,0],velocity_m_s=[0,1,0]))
        predicted=dict(position_m=[2,0,0],velocity_m_s=[2,0,0])
        observed=dict(position_m=[0,2,0],velocity_m_s=[0,3,0])
        result=decomposition(initial,predicted,observed)
        self.assertEqual(result['speed_m_s']['initial_projection_error'],0.)
        self.assertAlmostEqual(result['velocity_m_s']['initial_error_norm'],np.sqrt(2))
        for row in result.values():self.assertEqual(row['identity_residual'],0.)
        self.assertEqual(result['velocity_m_s']['endpoint_error'],[2.,-3.,0.])

    def test_wrong_input_rejected(self):
        obs=dict(time_s=.3,actual_tension_n=[1.],one_step_prediction=dict(time_s=.31,applied_tension_n=[2.]))
        with self.assertRaisesRegex(ValueError,'APPLIED_INPUT'):aligned_interval(obs,dict(time_s=.31),.01)

    def test_wrong_endpoint_time_rejected(self):
        obs=dict(time_s=.3,actual_tension_n=[1.],one_step_prediction=dict(time_s=.31,applied_tension_n=[1.]))
        with self.assertRaisesRegex(ValueError,'INTERVAL_MISMATCH'):aligned_interval(obs,dict(time_s=.32),.01)


if __name__=='__main__':unittest.main()
