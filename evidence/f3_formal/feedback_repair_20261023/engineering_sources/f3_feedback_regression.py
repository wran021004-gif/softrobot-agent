"""Focused offline regression and reviewable test receipt."""
import io
import time
import unittest
from tools.research.config import ROOT
from tools.state_io import atomic_json
names=['tests.research.test_f3_feedback_repairs','tests.research.test_research_reporting',
    'tests.research.test_s129_agent_reporting','tests.research.test_request_boundary_handoff',
    'tests.research.test_f3_provider_recovery','tests.research.test_f3_family_sensitivity',
    'tests.research.test_provider_context','tests.research.test_s127_provider_output',
    'tests.research.test_f3_formal_admission','tests.research.test_f3_request_tail',
    'tests.research.test_s127_session_recovery.SessionRecoveryTests.test_initial_contents_completed_growth_and_unrecorded_round']
stream=io.StringIO();started=time.perf_counter()
result=unittest.TextTestRunner(stream=stream,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
out=ROOT/'evidence/f3_formal/feedback_repair_20261023'
out.mkdir(parents=True,exist_ok=True)
(out/'offline_test_output.txt').write_text(stream.getvalue(),encoding='utf-8')
receipt=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
    skipped=len(result.skipped),elapsed_s=time.perf_counter()-started,successful=result.wasSuccessful(),
    suites=names,scope='Real SDK/Store and mock HTTP; synthetic numerical fixtures only; no live Provider, MATLAB, physics rollouts or training.')
atomic_json(out/'offline_tests.json',receipt)
print(stream.getvalue());print(receipt)
raise SystemExit(0 if result.wasSuccessful() else 1)
