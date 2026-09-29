"""One saved-evidence boundary check; no provider requests or backend executions."""
from copy import deepcopy
from pathlib import Path
import gzip
import json
import unittest
import numpy as np
from examples.gvs_revision_input import revision_input
from examples.gvs_nmpc_route_experiment import prepare
from extensions.tendon_family.gvs_reporting import summarize
from extensions.tendon_family.gvs_profile import settling_for
from extensions.tendon_family.historical_failure import bind_cases
from schemas.platform import SessionInput
from tools.platform_models import payload_for, DeepSeekAdapter
from tools.platform_store import Store
from tools.state_io import read, atomic_json, digest
from tests.test_stage330_revision import workspace_folder

SOURCE=Path('runs/stage331_autonomous_revision_execution_20260929_014645')
IDS=['rev_compliant_max','c2_stiff_scale1p01','c3_compliant_scale1p02']


class ExplorationBoundary(unittest.TestCase):
    def test_saved_cases_context_motion_and_no_charges(self):
        original=read(SOURCE/'frozen_input.json'); inp=revision_input(SOURCE)
        source=Store(SOURCE/'live'); sid=read(SOURCE/'evidence_index.json')['run_id']
        before=digest(source.session(sid)); usage=source.remaining()
        records=read(SOURCE/'actual_revised_candidates.json')
        with workspace_folder() as root:
            atomic_json(root/'input.json',inp)
            host=prepare(root/'live',SOURCE,root/'input.json',historical_failure=SOURCE,historical_candidates=IDS)
            context=host.context()['route']; prior=read(root/'live/historical_case.json')['content']
            exp=context['exploration_summary']; values=exp['historical']['values_tested']
            self.assertEqual(values['components/near/length_m'],[.17])
            self.assertEqual(values['components/far/length_m'],[.13])
            self.assertEqual(values['design/section_scale'],[1.05,1.01,1.02])
            self.assertEqual(values['design/material_scenario'],['compliant','stiff'])
            self.assertEqual(set(exp['historical']['constant_decisions']),{'components/near/length_m','components/far/length_m'})
            self.assertEqual(exp['fresh']['sample_count'],0)
            self.assertEqual(exp['remaining_resources']['backend_solves'],6)
            self.assertEqual(exp['best_measured']['candidate_id'],IDS[0])
            self.assertEqual(host.store.remaining()['used'],dict(model_calls=0,tool_calls=0,backend_solves=0,wall_s=0.,worker_calls=0))
            with host.store.connect(True) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
            db.close()
            for case,record in zip(prior['cases'],records):
                facts=case['factual_result']; archived=record['factual_result']
                self.assertEqual(facts,archived)
                self.assertEqual(case['source_session_id'],sid)
                self.assertEqual(case['source_state_identity'],digest(source.session(sid)['state']))
                detail=host.store.artifact(case['detail_export'])
                report=detail['report']['detail']; motion=detail['sampled_motion']
                # Independently read sealed trajectory and reproduce observations.
                bundle=None
                for event in source.events(case['owner_run_id']):
                    if event['kind']=='simulation' and event['execution_id']==facts['execution_id']:
                        for ref in event['outputs']:
                            if ref['media_type']=='application/json':
                                obj=source.artifact(ref)
                                if isinstance(obj,dict) and obj.get('result')==facts['simulation'] and 'files' in obj: bundle=obj
                files={f['filename']:source.artifact(f['reference'],raw=True) for f in bundle['files']}
                rows=json.loads(gzip.decompress(files['trajectory.json.gz']))
                errors=[float(np.linalg.norm(np.asarray(r['tip_m'])-[.29,.035,.19])) for r in rows]
                minimum=int(np.argmin(errors)); m=case['motion_summary']
                self.assertAlmostEqual(m['minimum_sampled_error_m'],errors[minimum])
                self.assertEqual(m['minimum_sampled_error_time_s'],rows[minimum]['time_s'])
                self.assertEqual(m['terminal_error_m'],facts['terminal_error_m'])
                self.assertEqual(m['signed_terminal_position_error_m'],facts['signed_position_error_m'])
                late=[e for r,e in zip(rows,errors) if r['time_s']>=.30-1e-9]
                self.assertAlmostEqual(m['late_error_change_m'],late[-1]-late[0])
                self.assertEqual(m['terminal_tip_speed_m_s'],facts['terminal_tip_speed_m_s'])
                regenerated=summarize(SessionInput.model_validate(inp).task,source.artifact(facts['simulation']),
                    detail['evaluation'],rows,json.loads(files['controller_observations.json']),motion,
                    [r['limit_n'] for r in facts['applied_tension_ranges']],settling_for(SessionInput.model_validate(inp)))
                self.assertEqual(regenerated['motion_summary'],m)
            for i in (0,2):
                self.assertTrue(prior['cases'][i]['motion_summary']['entered_tolerance_earlier_but_ended_outside'])
            snapshot=host.store.session(host.run_id)['snapshot']['input']
            self.assertEqual(snapshot['task'],original['task'])
            self.assertEqual(snapshot['robot'],original['robot'])
            for k in ('candidate_builder','controller','backend','dynamics_model','discretization','timeout_s'):
                self.assertEqual(snapshot['policy'][k],original['policy'][k])
            adapter=DeepSeekAdapter(); payload=payload_for(host,adapter)
            for k in ('model','max_tokens','reasoning_effort'):
                self.assertEqual(payload[k],original['policy']['model'][k])
            self.assertEqual((payload['thinking'],adapter.timeout_s,adapter.base_url),({'type':'enabled'},600.,'https://api.deepseek.com'))
            self.assertEqual(snapshot['policy']['model']['length_recovery'],original['policy']['model']['length_recovery'])
            self.assertIn('exploration_summary',json.loads(payload['messages'][-1]['content'])['route'])
            bad=deepcopy(inp);bad['task']['timing']['duration_s']=.4
            with self.assertRaisesRegex(ValueError,'MISMATCH'):bind_cases(SOURCE,bad,IDS,host.store)
        self.assertEqual(digest(source.session(sid)),before)
        self.assertEqual(source.remaining(),usage)


if __name__=='__main__':unittest.main()
