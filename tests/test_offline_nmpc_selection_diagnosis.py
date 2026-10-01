import unittest

from examples.offline_nmpc_selection_diagnosis import (
    INITIALIZATION_ITERATIONS,
    selection_kind,
    summary_row,
    validate_alignment,
)


class OfflineNMPCSelectionDiagnosisTests(unittest.TestCase):
    def test_alignment_and_initialization_are_explicit(self):
        update = {
            "time_s": 0.23,
            "phase": "current_state_before_integration",
            "requested_tension_n": [1.0, 2.0],
            "optimization_selected_iteration": 0,
            "optimization_constraint_violation": 1e-8,
            "optimization_returned_violation": 2e-3,
            "optimization_status": "feasible_early_stop",
            "optimization_raw_status": "User_Requested_Stop",
            "policy_stop_reason": "budget_best_feasible",
            "plan_accepted": True,
            "optimization_nonconverged": True,
            "plan_source": "ipopt_selected",
            "feasibility_recovery": {"enabled": False, "selected": False},
            "deadline_missed": True,
        }
        command = {"time_s": 0.23, "desired_tension_n": [1.0, 2.0]}
        validate_alignment([update], [command])
        row = summary_row(23, update, command)
        self.assertEqual(INITIALIZATION_ITERATIONS, {-1, 0})
        self.assertEqual(selection_kind(-1), "initialization")
        self.assertEqual(row["selection_kind"], "initialization")
        self.assertIsNone(row["selected_objective"])
        self.assertTrue(row["selected_feasible_at_1e_5"])
        self.assertFalse(row["returned_feasible_at_1e_5"])
        self.assertFalse(row["optimization_converged"])

    def test_timestamp_mismatch_fails(self):
        update = {
            "time_s": 0.22,
            "phase": "current_state_before_integration",
            "requested_tension_n": [1.0],
        }
        with self.assertRaisesRegex(ValueError, "timestamp mismatch"):
            validate_alignment([update], [{"time_s": 0.23, "desired_tension_n": [1.0]}])


if __name__ == "__main__":
    unittest.main()
