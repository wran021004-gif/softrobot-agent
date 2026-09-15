"""Run the affected offline combination once and retain machine-readable evidence."""
import io
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.spec_tools import ROOT


def main():
    from tests import test_platform_convergence as current, test_platform as legacy
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(current.ConvergenceTests)
    for name in ('test_existing_service_executor_adapted_without_double_charge',
                 'test_skill_existing_lifecycle_and_next_context',
                 'test_worker_failure_cancel_and_conflict',
                 'test_late_sealed_worker_output_reconciles_unknown_without_relaunch'):
        suite.addTest(legacy.PlatformTests(name))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    folder = ROOT / 'docs/evidence/platform_convergence'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'acceptance.log').write_text(stream.getvalue(), encoding='utf8')
    record = dict(success=result.wasSuccessful(), cases=result.testsRun,
        failures=len(result.failures), errors=len(result.errors),
        roots=[str(p.relative_to(ROOT)) for p in [*current.ROOTS, *legacy.TEST_ROOTS]],
        scope='offline interface acceptance; no physical or model quality claim')
    (folder / 'acceptance.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
