"""Regression from the preserved live revision overflow; no provider or solves."""
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from schemas.platform import ModelInput
from tools.diagnostic_native import BoundSavedStateAdapter
from tools.diagnostic_facts import context_view, resolve_handles
from tools.platform_store import encode
from tools.state_io import read


class Stage350ContextTests(TestCase):
    def test_preserved_revision_fits_without_discarding_evidence(self):
        fixture=read(Path(__file__).resolve().parents[1]/'evidence/stage350_evidence_workflow_20261003/repair_context_fixture.json')
        model_input=ModelInput.model_validate(fixture['model_input'])
        state=deepcopy(fixture['fact_state']);before=deepcopy(state)
        config=model_input.context['policy']['model']
        with patch('tools.platform_store.Store') as store:
            store.return_value.session.return_value={'state':state}
            adapter=BoundSavedStateAdapter();payload=adapter.encode(model_input,config)
        context=json.loads(payload['messages'][1]['content']);role=context['role_context']
        self.assertLessEqual(len(encode(payload).encode()),200000)
        self.assertEqual(state,before)
        self.assertEqual(role['fact_catalog'],context_view(state)['fact_catalog'])
        for key in ('previous_report_content','check_feedback','request_content','working_memory','summary_content'):
            self.assertEqual(role[key],model_input.context['role_context'][key])
        restored=deepcopy(context)
        for row,original in zip(restored['role_context']['read_ledger'],context_view(state)['read_ledger'],strict=True):
            for key in ('handles','displayed_handles'):
                self.assertEqual(row.pop(key+'_count'),len(original[key]))
                row[key]=original[key]
            self.assertEqual(row,original)
        for row,original in zip(restored['batch_observations'],model_input.context['batch_observations'],strict=True):
            if 'fact_handle_count' in row:
                self.assertEqual(row.pop('fact_handle_count'),len(original['fact_handles']))
                row['fact_handles']=original['fact_handles']
            self.assertEqual(row,original)
        old_payload=deepcopy(payload);old_payload['messages'][1]['content']=encode(restored)
        self.assertGreater(len(encode(old_payload).encode()),200000)
        result=role['check_feedback'][0]['result']
        numeric=[f for f in role['fact_catalog'] if isinstance(f['value'],float)
                 and state['fact_catalog'][f['handle']]['selector']['reference']==result]
        self.assertTrue(numeric)
        resolved=resolve_handles(state,{'result':[numeric[0]['handle']]})['result'][0]
        self.assertEqual(resolved['reference'],result)
        self.assertEqual(resolved['value'],numeric[0]['value'])
        self.assertEqual(context['recovery_status'],model_input.context['recovery_status'])
        self.assertEqual(context['project_remaining'],model_input.context['project_remaining'])
