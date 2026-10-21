"""Offline scope/admission checks. No live model request is authorized here."""
import asyncio
import json
import unittest
from unittest.mock import patch
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.state_io import read,atomic_json,digest
from tools.research.state import state
from tests.research import s127_6_decisions as probe
from tests.research.s7_study import engineering_plan


class NewValidationTests(unittest.TestCase):
    def test_read_only_resume_rejects_unresolved_or_scientifically_changed_prefix(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from tests.research import s127_4_sdk_continuation as sdk
        approval=dict(stage='explicit-fixture');scope=dict(request_ceiling=12,max_output_tokens=65536)
        original=dict(research_status='ready',pending=None,candidates={},
            pilot=dict(provider=dict(max_tokens=65536)))
        store=MagicMock();h=SimpleNamespace(store=store,run_id='fixture')
        store.remaining.return_value=dict(limit=dict(model_calls=12),remaining=dict(model_calls=9),used=dict(model_calls=3))
        store.events.return_value=[dict(kind='s127_4b_authorization',outputs=[dict(artifact_id='fixture')])]
        store.artifact.return_value=approval
        store.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value=[0]
        with patch.object(sdk,'state',return_value=original),patch.object(sdk,'pending',return_value=[]),patch.object(sdk.core,'guard') as guard:
            ledger=deepcopy(store.remaining())
            self.assertEqual(sdk.admit_read_only_resume(h,scope,approval)['ledger'],ledger);guard.assert_called_once_with(h)
            self.assertFalse(store.create.called or store.reserve.called or store.transaction.called)
            for field in ('unconsumed_response','handoff','handoff_preparation'):
                bad=deepcopy(original);bad['pilot'][field]=dict(fixture=True)
                with patch.object(sdk,'state',return_value=bad):
                    with self.assertRaisesRegex(ValueError,'READ_ONLY_RESUME_REQUIRES'):sdk.admit_read_only_resume(h,scope,approval)
            with patch.object(sdk,'pending',return_value=[dict(status='unknown')]):
                with self.assertRaisesRegex(ValueError,'READ_ONLY_RESUME_REQUIRES'):sdk.admit_read_only_resume(h,scope,approval)
            bad=deepcopy(original);bad['candidates']={'fixture':{}}
            with patch.object(sdk,'state',return_value=bad):
                with self.assertRaisesRegex(ValueError,'READ_ONLY_RESUME_REQUIRES'):sdk.admit_read_only_resume(h,scope,approval)

    def test_old_approval_is_rejected_before_credentials_or_grant_creation(self):
        path=ROOT/'runs/s127_6_old_authorization_fixture.json'
        atomic_json(path,dict(stage='S12.7.4A',user_approval='Old fixture authorization',request_ceiling=18))
        with patch('tools.research.agent.load_credential',side_effect=AssertionError('NO_CREDENTIALS')):
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_S127_6A'):
                asyncio.run(probe.live(path))
        from tests.research.s127_6_sdk_continuation import SPEC,OUT
        from tests.research.s127_4_sdk_continuation import run
        with patch('tools.research.agent.load_credential',side_effect=AssertionError('NO_CREDENTIALS')):
            with self.assertRaisesRegex(ValueError,'TRANSFER_AUTHORIZATION_REQUIRED'):
                asyncio.run(run(path,spec_path=SPEC,out=OUT,stage='S12.7.6B'))

    def test_paired_tools_tasks_budgets_science_and_output_capacity_match(self):
        manifest=read(probe.OUT/'manifest.json');scope=read(probe.OUT/'scope.json')
        self.assertEqual(scope['manifest_identity'],digest(manifest));self.assertEqual(len(manifest['cases']),6)
        source=Host(manifest['store'],manifest['run_id'])
        for a,b in zip(manifest['cases'][::2],manifest['cases'][1::2]):
            self.assertEqual(a['state'],b['state']);self.assertEqual(a['cutoff_sequence'],b['cutoff_sequence'])
            wires=[source.store.artifact(c['request']) for c in (a,b)]
            self.assertEqual(wires[0]['tools'],wires[1]['tools'])
            self.assertEqual(wires[0]['messages'][1],wires[1]['messages'][1])
            packets=[json.loads(w['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1])['research'] for w in wires]
            for key in ('task','actions','all_fresh_results'):self.assertEqual(packets[0][key],packets[1][key])
            for key in packets[0]['budget']:self.assertEqual(packets[0]['budget'][key],packets[1]['budget'][key])
            self.assertTrue(all(w['max_tokens']==65536 for w in wires))
            self.assertTrue(all([m['role'] for m in w['messages']]==['system','user'] for w in wires))

    def test_real_scientific_preflight_is_used_without_a_worker(self):
        manifest=read(probe.OUT/'manifest.json');source=Host(manifest['store'],manifest['run_id']);case=manifest['cases'][0]
        frozen=source.store.artifact(case['state'])['state'];before=digest(frozen)
        candidate=list(frozen['candidates'].values())[-1]
        plan=engineering_plan('initialize_control','CONTROL_SEARCH',candidate,control_seed=dict(candidate=candidate,method='baseline'))
        call=dict(id='explicit-fixture',function=dict(name='research_plan',arguments=json.dumps(plan)))
        result=probe.feedback(source,case,call)
        self.assertEqual(result['full_execution_admission'],'passed',result)
        self.assertEqual(before,digest(source.store.artifact(case['state'])['state']))
        plan['supporting_evidence']=[frozen['family_space_reference']]
        call['function']['arguments']=json.dumps(plan)
        result=probe.feedback(source,case,call)
        self.assertEqual(result['status'],'rejected');self.assertEqual(result['feedback']['error_code'],'UNREGISTERED_RESEARCH_EVIDENCE')
        query=dict(candidate=candidate,operation='equilibrium',operating_point='target_equilibrium',protocol=frozen['spec']['analysis_protocol'])
        call=dict(id='explicit-mathematical-fixture',function=dict(name='research_analysis',arguments=json.dumps(query)))
        result=probe.feedback(source,case,call)
        self.assertEqual(result['status'],'execution_intercepted',result)
        self.assertEqual(result['full_execution_admission'],'prelaunch_passed')

    def test_synthetic_multiturn_delivers_actual_previous_feedback(self):
        value=read(probe.OUT/'offline.json');rows=value['cases']
        self.assertEqual(len(rows),18);self.assertEqual(value['new_provider_requests'],0)
        for row in rows:
            self.assertEqual(row['previous_tool_feedback_in_request'],row['turn'])
            self.assertTrue(all(c['actual_store_read'] for c in row['checks']))
        self.assertEqual(value['ledger']['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
