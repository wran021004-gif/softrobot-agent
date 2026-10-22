"""Reproducible T3 interface regression; synthetic transport and no science worker."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    if args.output and Path(args.output).exists():raise ValueError('PRESERVE_EXISTING_VALIDATION')
    sys.path.insert(0,str(Path('tests/research').resolve()))
    from tools.platform_registry import Registry
    original=Registry.inspect
    def offline_inspect(self,definition,allowed=None):
        row=original(self,definition,allowed)
        # Compile the existing cold-study test fixture without installing/starting MATLAB.
        if row['reasons']==['DEPENDENCY_MISSING: matlab.engine']:
            row.update(reasons=[],dependencies_available=True,executable=True)
        return row
    names=['tests.research.test_s130_mainline.MainlineTests',
        'tests.research.test_s129_integration.IntegrationTests',
        'tests.research.test_s129_agent_reporting.AgentReportingTests',
        'tests.research.test_s129_agent_reporting.ReportingSessionTests',
        'tests.research.test_f30_provider_check.F30Tests']
    suite=unittest.defaultTestLoader.loadTestsFromNames(names)
    started=time.perf_counter()
    with patch.object(Registry,'inspect',offline_inspect),patch('tests.research.test_s125_contract.uuid4',
            side_effect=lambda:SimpleNamespace(hex=uuid4().hex[:8])),patch(
            'tools.service_execution._run_contained',side_effect=AssertionError('No scientific worker in T3 offline validation')):
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    report=dict(scope='Offline interface/contract validation, not real LLM decision performance',
        tests=names,count=result.testsRun,passed=result.wasSuccessful(),failures=[str(t) for t,_ in result.failures],
        errors=[str(t) for t,_ in result.errors],elapsed_s=time.perf_counter()-started,python=sys.executable,
        versions={name:importlib.metadata.version(name) for name in ('numpy','scipy','pydantic','httpx','strands-agents')},
        scientific_workers='blocked; individual tests replace worker boundary with explicit synthetic returns',
        provider='existing httpx.MockTransport fixtures only',
        fixture_adaptations=['MATLAB dependency availability only is stubbed for cold-study interface tests',
            'Cold fixture UUID shortened to 8 hex digits to fit Windows SDK snapshot paths; no production Session code changed'],
        scientific_results='No new physical validation; T1/T2 numbers read from immutable saved artifacts')
    if args.output:Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return not result.wasSuccessful()


if __name__=='__main__':raise SystemExit(main())
