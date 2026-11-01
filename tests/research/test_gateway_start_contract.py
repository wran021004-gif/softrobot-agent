"""Offline executable-contract checks, without credentials or Provider requests."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.research.config import ROOT
from tests.research.test_cross_task_integration import fixture_directory


class GatewayStartContractTests(unittest.TestCase):
    def test_bound_gateway_converter_accepts_research_contract(self):
        with fixture_directory() as folder:
            source=folder/'src';source.mkdir()
            # The converter itself is the exact repository source. Its error
            # formatter only needs this SDK error-class test double, no OAuth.
            sdk=folder/'node_modules/@siwc/local';sdk.mkdir(parents=True)
            (sdk/'package.json').write_text('{"type":"module","exports":"./index.mjs"}',encoding='utf8')
            (sdk/'index.mjs').write_text('export class ChatGPTError extends Error {}\n',encoding='utf8')
            (source/'cli.mjs').write_text('// Offline presence fixture\n',encoding='utf8')
            for name in ('request.mjs','errors.mjs'):
                (source/name).write_bytes(subprocess.check_output(
                    ['git','show','HEAD:local-chatgpt-gateway/src/'+name],cwd=ROOT))
            completed=subprocess.run(['node',str(ROOT/'tools/check_research_gateway.mjs'),str(folder)],
                capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(json.loads(completed.stdout),dict(status='ready',tools=True,reasoning='none',inference_requests=0))

    def test_old_gateway_converter_is_rejected_before_service_start(self):
        with fixture_directory() as folder:
            source=folder/'src';source.mkdir()
            (source/'cli.mjs').write_text('throw new Error("Must not start service");\n',encoding='utf8')
            (source/'request.mjs').write_text('export function convertRequest() { throw new Error("Unsupported tools"); }\n',encoding='utf8')
            completed=subprocess.run(['node',str(ROOT/'tools/check_research_gateway.mjs'),str(folder)],
                capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(completed.returncode,1)
            self.assertEqual(json.loads(completed.stderr)['inference_requests'],0)
            self.assertNotIn('Must not start service',completed.stderr)
