"""Real sealed command conversion plus explicit malformed-reference fixtures."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from tools.research.contracts import ControlSeedRequest, LocalControlSearchSettings
from tools.research import physical_replay as replay
from tools.research.rl import measured_nmpc_trajectory
from tools.research.state import state, save
from tools.research.control_correction import task_outputs
from tools.research_tasks import task_adapter
from tools.research.local_control_search import search
from tests.research.test_s127_working_set import historical_host
from tests.research import test_s127_rl_handoff as rl_fixture
from tests.research.test_s125_contract import cold_host


class NMPCControlStartTests(unittest.TestCase):
    def test_two_real_executions_convert_without_writes_to_historical_store(self):
        original=historical_host();before=deepcopy(state(original));ledger=original.store.remaining();events=original.store.events(original.run_id)
        sink=cold_host();projection=deepcopy(before)
        def changed(host,**values):projection.update(values)
        for ref in before['results']:
            result=original.store.artifact(ref);candidate=result['candidate'];cfg=original.store.artifact(candidate)['configuration']
            trajectory,origin=measured_nmpc_trajectory(original,ref)
            # Only test persistence is redirected; actual Store reads/identities remain real.
            with patch.object(replay,'save',side_effect=lambda h,v,k:save(sink,v,k)),patch.object(replay,'update',side_effect=changed),patch.object(replay,'state',return_value=projection):
                entry=replay.seed_control(original,ControlSeedRequest(candidate=candidate,parent=candidate,source=ref))
            source=sink.store.artifact(entry['source'])
            self.assertTrue(np.array_equal(source['trajectory']['tensions_n'],trajectory['tensions_n']))
            self.assertTrue(np.allclose(source['trajectory']['times_s'],trajectory['times_s'],rtol=0,atol=1e-12))
            self.assertFalse(source['provenance']['inherited_acceptance'])
            self.assertEqual(source['provenance']['execution_reference'],ref);self.assertEqual(source['task_acceptance'],'unmeasured')
            self.assertEqual(source['provenance']['command_origin'],'measured_applied_interval_inputs')
            self.assertTrue(replay.explicit_control_source(source));replay.binding(cfg,source['trajectory'])
            positive_zero=deepcopy(source['trajectory'])
            positive_zero['tensions_n']=(np.asarray(positive_zero['tensions_n'])+0.).tolist()
            self.assertEqual(replay.schedule_identity(cfg,source['trajectory']),replay.schedule_identity(cfg,positive_zero))
            for method in ('pattern','response'):
                adapter=task_adapter(cfg);limits=adapter.ranking_limits();channels=len(trajectory['tendon_order'])
                start=dict(id='real-source',candidate=candidate,schedule=source,limits=[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']],
                    task_options=dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
                        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s']))
                # Intercepted callback checks entry only, makes no scientific success assertion.
                probe=search([start],lambda *args:dict(reference=ref,task_gap=dict(valid_complete=False,normalized_gap=None,accepted=False)),
                    dict(version='local_control_search_v2',method=method,knots_s=[0.,trajectory['times_s'][-1]],evaluation_requests=1))
                self.assertEqual(probe['stop_reason'],'no_valid_start');self.assertEqual(probe['search_dimension'],2*channels)
        self.assertEqual(state(original),before);self.assertEqual(original.store.remaining(),ledger);self.assertEqual(original.store.events(original.run_id),events)
        self.assertEqual(sink.store.remaining()['used']['backend_solves'],0)

    def test_bad_current_ownership_and_missing_execution_are_rejected(self):
        rl_fixture.RLHandoffTests.setUpClass();fixture=rl_fixture.RLHandoffTests();fixture.setUp()
        h=fixture.h
        other=save(h,dict(status='evaluated',candidate=fixture.candidate,execution_id='unregistered'))
        with self.assertRaisesRegex(ValueError,'REGISTERED_CURRENT'):measured_nmpc_trajectory(h,other)
        from extensions.tendon_family.control_evidence import ControlEvidence
        with patch.object(ControlEvidence,'resolve',return_value=fixture.source),patch.object(ControlEvidence,'read_file',return_value=fixture.observations):
            q=ControlSeedRequest(candidate=fixture.candidate,parent=fixture.candidate,source=fixture.result,channel_map={})
            with self.assertRaisesRegex(ValueError,'WITHOUT_CHANNEL_MAPPING'):replay.seed_control(h,q)
            fixture.source['configuration']['robot']['structure']['data']['tendons'].reverse()
            with self.assertRaisesRegex(ValueError,'SCIENTIFIC_CONFIGURATION'):measured_nmpc_trajectory(h,fixture.result)


if __name__=='__main__':unittest.main()
