"""Actual preserved complete-feedback overflow; no provider or numerical work."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import patch
from schemas.platform import ModelInput
from tools.diagnostic_native import BoundSavedStateAdapter
from tools.diagnostic_facts import resolve_handles
from tools.platform_store import encode
from tools.state_io import read
from tools.diagnostic_workflow import ROOT


class CompleteFeedbackContextTests(TestCase):
    def test_largest_authorized_structured_memory_keeps_feedback(self):
        folder=ROOT/'evidence/stage352_settling_20261003/host_repair'
        model_input=ModelInput.model_validate(read(folder/'preserved_revision_model_input.json'))
        state=read(folder/'preserved_revision_fact_state.json')
        role=model_input.context['role_context']
        role['working_memory']=[dict(phase='fixture',content={'explanation':'x'*11000}) for _ in range(4)]
        self.assertLess(len(encode(role['working_memory']).encode()),48000)
        with patch('tools.platform_store.Store') as store:
            store.return_value.session.return_value={'state':state}
            payload=BoundSavedStateAdapter().encode(model_input,model_input.context['policy']['model'])
        presented=json.loads(payload['messages'][1]['content'])['role_context']
        self.assertLessEqual(len(encode(payload).encode()),200000)
        self.assertEqual(presented['working_memory'],role['working_memory'])
        self.assertEqual(presented['check_feedback'],role['check_feedback'])
        self.assertEqual(presented['instructions'],role['instructions'])
        ref=role['check_feedback'][0]['result']
        fields={state['fact_catalog'][r['handle']]['selector']['pointer'] for r in presented['fact_catalog']
                if state['fact_catalog'][r['handle']]['selector']['reference']==ref}
        self.assertTrue({'/detail/terminal_error_m','/detail/sampled_settling/max_error_m',
            '/detail/sampled_settling/max_speed_m_s','/detail/mean_update_s'}<=fields)

    def test_preserved_complete_revision_handoff_fits(self):
        folder=ROOT/'evidence/stage352_settling_20261003/host_repair'
        defect=read(folder/'defect.json')
        model_input=ModelInput.model_validate(read(folder/'preserved_revision_model_input.json'))
        state=read(folder/'preserved_revision_fact_state.json');before=deepcopy(state)
        config=model_input.context['policy']['model']
        self.assertGreater(defect['unrepaired_payload_bytes'],config['context_bytes'])
        with patch('tools.platform_store.Store') as store:
            store.return_value.session.return_value={'state':state}
            payload=BoundSavedStateAdapter().encode(model_input,config)
        role=json.loads(payload['messages'][1]['content'])['role_context']
        self.assertLessEqual(len(encode(payload).encode()),200000)
        self.assertEqual(state,before)
        for field in ('check_feedback','improvement_feedback_content','previous_report_content','summary_content','working_memory'):
            self.assertEqual(role[field],model_input.context['role_context'][field])
        presentation=role['fact_catalog_presentation']
        self.assertLess(presentation['catalog_budget_bytes'],75000)
        self.assertEqual(presentation['catalogued_handles'],len(state['fact_catalog']))
        self.assertEqual(len(role['read_ledger']),len(state['read_ledger']))
        for row,original in zip(role['read_ledger'],state['read_ledger'],strict=True):
            self.assertEqual(row['handles_count'],len(original['handles']))
            self.assertEqual(row['result'],original['result'])
            self.assertEqual(row['coverage'],original['coverage'])
        result=role['check_feedback'][0]['result']
        pointers={'/detail/terminal_error_m','/detail/sampled_settling/max_error_m',
                  '/detail/sampled_settling/max_speed_m_s','/detail/mean_update_s'}
        for pointer in pointers:
            shown=[r for r in role['fact_catalog'] if state['fact_catalog'][r['handle']]['selector']['reference']==result
                   and state['fact_catalog'][r['handle']]['selector']['pointer']==pointer]
            self.assertTrue(shown,pointer)
            selected=resolve_handles(state,{'measurement':[shown[0]['handle']]})['measurement'][0]
            self.assertEqual(selected['pointer'],pointer)
            self.assertEqual(selected['reference'],result)
        self.assertEqual(config['context_bytes'],200000)
        self.assertEqual(json.loads(payload['messages'][1]['content'])['recovery_status'],model_input.context['recovery_status'])
