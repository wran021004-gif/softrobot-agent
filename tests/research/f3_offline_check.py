"""Bounded offline regression inventory; mock HTTP and explicitly saved fixtures."""
import argparse
from contextlib import ExitStack
import hashlib
from pathlib import Path
import time
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from tools.state_io import atomic_json
from tools.research.config import ROOT
from tools.platform_host import Host


NAMES=[
    'test_f3_family_sensitivity.FamilySensitivityTests',
    'test_f3_control_handoff.ControlHandoffTests','test_f3_request_tail.RequestTailTests',
    'test_s130_mainline.MainlineTests','test_conic_capability','test_capability_sensitivity',
    'test_s129_agent_reporting.AgentReportingTests','test_s129_agent_reporting.ReportingSessionTests',
    'test_s129_integration.IntegrationTests','test_f30_provider_check.F30Tests',
    'test_s127_session_recovery.SessionRecoveryTests','test_s127_checkpoint.CrossProcessCheckpointTests',
    'test_s8_control_seed.ControlSeedTests','test_task_analysis_contract.TaskAnalysisTests',
    'test_trajectory_feasibility','test_s129_task_capability',
    'test_family_space.FamilySpaceTests','test_variable_segments.VariableSegmentTests',
    'test_s127_math_admission','test_evidence_policy','test_research_reporting.ReportingTests']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--archive',type=Path);parser.add_argument('--names',nargs='+',default=NAMES);args=parser.parse_args()
    if Path(args.output).exists():raise ValueError('PRESERVE_PREVIOUS_REGRESSION_REPORT')
    sys.path.insert(0,str(ROOT/'tests/research'))
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.research.'+n for n in args.names])
    def restrict(group):
        for test in group:
            if isinstance(test,unittest.TestSuite):restrict(test)
            elif test.id().endswith(('test_real_candidate_gvs_through_existing_worker_store_and_packet',
                    'test_real_gvs_pair_dispatch_store_budget_and_reuse')):
                setattr(test,test._testMethodName,unittest.skip('Additional real worker regression excluded; single SOCP Study has its own runner')(
                    getattr(test,test._testMethodName)))
    restrict(suite)
    class Results(unittest.TextTestResult):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);self.passed=[]
        def addSuccess(self,test):super().addSuccess(test);self.passed.append(test.id())
    start=time.perf_counter();archive_hash=None
    with ExitStack() as stack:
        stack.enter_context(patch('tools.service_execution._run_contained',side_effect=AssertionError('Real scientific workers blocked in offline suite')))
        stack.enter_context(patch('tests.research.test_s125_contract.uuid4',side_effect=lambda:SimpleNamespace(hex=uuid4().hex[:8])))
        if args.archive:
            archive=args.archive.resolve();db=archive/'platform.sqlite'
            archive_hash=hashlib.sha256(db.read_bytes()).hexdigest()
            stack.enter_context(patch('tests.research.test_s127_session_recovery.historical_host',
                side_effect=lambda:Host(archive,'s126-cold-live-20261020',actor='unified-research')))
        result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
    if args.archive and hashlib.sha256(db.read_bytes()).hexdigest()!=archive_hash:
        raise ValueError('HISTORICAL_ARCHIVE_CHANGED')
    atomic_json(args.output,dict(tests=result.testsRun,passed=result.passed,
        failures=[dict(test=t.id(),traceback=e) for t,e in result.failures],
        errors=[dict(test=t.id(),traceback=e) for t,e in result.errors],skipped=[dict(test=t.id(),reason=r) for t,r in result.skipped],
        elapsed_s=time.perf_counter()-start,successful=result.wasSuccessful(),
        historical_archive=dict(path=str(args.archive),sha256=archive_hash,unchanged=True),
        scope='Offline contracts and numerical fixtures; real SDK/Store, mock HTTP. No scientific execution Study.',
        substitutions=['Short UUID only for Windows cold SDK fixture path length',
            'Saved numerical matrices and explicit mocked scientific worker returns in contract tests',
            'New family T2 model binding tests substitute task applicability; kernel tested separately'],
        real_provider_requests=0,physical_experiments=0,ppo_training=0))
    return not result.wasSuccessful()


if __name__=='__main__':raise SystemExit(main())
