"""Provider packet construction excludes export-only Store work."""
import unittest
from unittest.mock import patch
from tools.research.agent import decision_packet
from tools.research.state import update
from tests.research.test_phs2d_topology_support import topology_fixture


class DecisionPacketDeliveryTests(unittest.TestCase):
    def test_delivery_preserves_research_and_generation_without_export_queries(self):
        with topology_fixture() as h:
            update(h,freeze='offline-packet-fixture')
            full=decision_packet(h)
            with patch('tools.research.research_context.agent_decision_brief',return_value=full['research']), patch(
                    'tools.research.research_context.controller_capabilities',
                    side_effect=AssertionError('Export-only controller query on Provider path')):
                delivered=decision_packet(h,research_only=True)
            self.assertEqual(set(delivered),{'research','family_space','study_id'})
            for key in delivered:self.assertEqual(delivered[key],full[key])
            # Preserve the existing export contract and its real consumers.
            self.assertIn('candidate_profile_bindings',full)
            self.assertIn('implementation',full)


if __name__=='__main__':unittest.main()
