"""Final engineering ownership/configuration checks; no Study or science launch."""
import importlib
import json
import subprocess
import sys
import unittest
from schemas.platform import ModelConfig
from tools.research.config import ROOT,resolve,role_provider
from tools.research.provider import request_settings
from tools.research.evidence_policy import require_english


class AcceptanceTests(unittest.TestCase):
    def test_cli_and_pending_configuration_do_not_prepare_a_study(self):
        help_text=subprocess.check_output([sys.executable,'-m','tools.research','--help'],cwd=ROOT,text=True)
        self.assertIn('--restore-only',help_text);self.assertIn('models',help_text)
        spec=resolve(ROOT/'configs/research/study_harness_v2.json')
        self.assertTrue(spec['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))
        self.assertEqual(spec['budgets']['provider_requests'],8)
        self.assertFalse((ROOT/'runs/research'/spec['study_id']/'platform.sqlite').exists())
        for purpose in ('conversation','reporter'):
            p=role_provider(spec,spec['runtime']['provider'],purpose)
            self.assertEqual(request_settings(p)['thinking'],dict(type='disabled'))
        require_english(spec['execution_instructions'],spec,source='reviewed English instructions')

    def test_frozen_r2_provider_serialization_is_unchanged(self):
        fixture=json.loads((ROOT/'tests/research/fixtures/r2_harness_boundary.json').read_text(encoding='utf8'))
        original=fixture['frozen_model']
        self.assertEqual(ModelConfig.model_validate(original).model_dump(),original)
        self.assertNotIn('reasoning',original);self.assertNotIn('model_capabilities',original)
        self.assertEqual(original['thinking'],'disabled')

    def test_science_entrypoints_remain_callable_without_launching(self):
        entries={'tools.research.design':'generate_candidate','tools.research.analysis':'dispatch',
            'tools.research.execution':'execute','tools.research.physical_replay':'dispatch',
            'tools.research.search':'run_search','tools.research_tasks':'task_adapter',
            'tools.research.reporter':'assemble','extensions.tendon_family.compiler':'resolve',
            'extensions.tendon_family.gvs_nmpc':'resolve_gvs_nmpc_control'}
        for module,function in entries.items():
            with self.subTest(module=module):self.assertTrue(callable(getattr(importlib.import_module(module),function)))


if __name__=='__main__':unittest.main()
