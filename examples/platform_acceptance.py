"""轻量平台验收；默认仅检查。--real 最多两次短 MuJoCo，--matlab 一次短 MATLAB。"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time
import unittest
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf8')
from tools.spec_tools import ROOT
from tools.state_io import atomic_json


def accounting(roots):
    total = dict(real_model_requests=0, offline_model_replies=0, mathematical_executions=0,
        reference_backend_executions=0, mujoco_reservations=0, matlab_reservations=0, mujoco_completed=0, matlab_completed=0,
        workers_completed=0, workers_failed=0, workers_cancelled=0, unknown_reservations=0)
    total.update(worker_processes_started=0, worker_unsettled_records=0)
    for root in roots:
        with sqlite3.connect(root / 'platform.sqlite') as db:
            for worker in db.execute('SELECT pid,status FROM workers'):
                total['worker_processes_started'] += int(worker[0] is not None)
                total['worker_unsettled_records'] += int(worker[0] is not None and worker[1] in ('running', 'reserved', 'unknown'))
            for row in db.execute('SELECT receipt,status,request_id,charged,run_id FROM calls'):
                if row[1] == 'unknown': total['unknown_reservations'] += 1
                if not row[0]: continue
                receipt = json.loads(row[0]); tool = receipt['tool_id']
                if tool == 'simulation.run' and receipt['charged']['backend_solves']:
                    snapshot_id = db.execute('SELECT snapshot FROM sessions WHERE run_id=?', (row[4],)).fetchone()[0]
                    snapshot = json.loads(db.execute('SELECT body FROM artifacts WHERE id=?', (snapshot_id,)).fetchone()[0])
                    configured = snapshot['input']['policy']['backend']['extension_id']
                    key = {'backend.mujoco': 'mujoco_reservations', 'backend.matlab': 'matlab_reservations'}.get(configured)
                    if key: total[key] += receipt['charged']['backend_solves']
                total['real_model_requests'] += receipt['charged']['model_calls']
                if tool == 'model.offline' and receipt['execution_status'] == 'completed': total['offline_model_replies'] += 1
                if tool.startswith('analysis.') and receipt['execution_status'] == 'completed' and not receipt['cache_hit']:
                    total['mathematical_executions'] += 1
                if tool == 'simulation.run' and receipt.get('output') and not receipt['cache_hit']:
                    artifact = db.execute('SELECT body FROM artifacts WHERE id=?', (receipt['output']['artifact_id'],)).fetchone()
                    result = json.loads(artifact[0])
                    backend = result.get('backend_id')
                    if backend is None:  # Explicit corruption fixture; count frozen dispatch identity.
                        snapshot_id = db.execute('SELECT snapshot FROM sessions WHERE run_id=?', (row[4],)).fetchone()[0]
                        snapshot = json.loads(db.execute('SELECT body FROM artifacts WHERE id=?', (snapshot_id,)).fetchone()[0])
                        backend = snapshot['input']['policy']['backend']['extension_id']
                    key = {'backend.reference': 'reference_backend_executions', 'backend.mujoco': 'mujoco_completed', 'backend.matlab': 'matlab_completed'}[backend]
                    total[key] += 1
                if tool.startswith('worker.') and receipt['execution_status'] in ('completed', 'failed', 'cancelled'):
                    total['workers_' + receipt['execution_status']] += 1
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true'); parser.add_argument('--matlab', action='store_true')
    parser.add_argument('--skip-checks', action='store_true'); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = (args.output or ROOT / 'runs/platform_acceptance' / uuid4().hex).resolve()
    root.mkdir(parents=True, exist_ok=False)
    report = dict(root=str(root), checks=None, numerical=[], boundaries=['离线回复不证明自主决策质量', '确定性工作者不等于真实多模型协作', '参考信号模型不代表机器人物理'])
    roots = []
    if not args.skip_checks:
        from tests import test_platform
        names = ['tests.test_platform',
            'tests.test_skills.SkillTests.test_valid_candidate_and_invalid_schema',
            'tests.test_skills.SkillTests.test_negative_validation_preserved_and_coverage_verified',
            'tests.test_skills.SkillTests.test_validation_cannot_borrow_other_strategy_or_relabel_failure',
            'tests.test_skills.SkillTests.test_version_history_and_approval_content_binding',
            'tests.test_public_tools.PublicToolTests.test_directory_identity_schema_and_actual_native_tools']
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        # Managed Windows denies access inside tempfile's private ACL directories.
        # Retain ordinary workspace directories, with original assertions unchanged.
        class RetainedWorkspaceDirectory:
            def __init__(self, *a, **kw):
                folder = ROOT / 'runs/platform_legacy_fixtures' / uuid4().hex
                folder.mkdir(parents=True)
                self.name = str(folder)
            def cleanup(self): pass
            def __enter__(self): return self.name
            def __exit__(self, *args): pass
        from unittest.mock import patch
        with (root / 'checks.log').open('w', encoding='utf8') as log, patch('tests.test_skills.tempfile.TemporaryDirectory', RetainedWorkspaceDirectory):
            outcome = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        report['checks'] = dict(run=outcome.testsRun, failures=len(outcome.failures), errors=len(outcome.errors), skipped=len(outcome.skipped))
        roots += test_platform.TEST_ROOTS
        report['counts'] = accounting(roots)
        report['test_project_roots'] = [str(r) for r in roots]
        atomic_json(root / 'acceptance.json', report)
        if not outcome.wasSuccessful():
            print(json.dumps(report, ensure_ascii=False, indent=2)); return 1
    if args.real or args.matlab:
        from examples.platform_fixtures import project, reach_input
        from tools.platform_store import Store
        from tools.platform_host import Host
        config = project()
        config['budget']['backend_solves'] = (2 if args.real else 0) + (1 if args.matlab else 0)
        store = Store(root / 'numerical'); store.create(config); roots.append(store.root)
        cases = [('reach-a', 'mujoco', 40), ('reach-b', 'mujoco', 60)] if args.real else []
        if args.matlab: cases.append(('matlab-short', 'matlab', 40))
        for name, backend, steps in cases:
            inp = reach_input(name, backend)
            if name == 'reach-b':
                inp['task']['goal']['data']['target_m'] = [0.28, 0.02, 0.12]
                inp['task']['task_version'] = '1.0.1'
                inp['task']['source'] = '独立开发变体：目标 [0.28,0.02,0.12]，60 步；原环境与 0.01 m 容差'
            duration = steps * inp['task']['timing']['timestep_s']
            inp['task']['timing']['duration_s'] = duration
            inp['task']['sampling']['window_s'] = [0., duration]
            host = Host(store.root, name)
            try:
                host.create(inp)
            except ValueError as exc:
                report['numerical'].append(dict(case=name, status='capability_unavailable', reason=str(exc), solver_started=False))
                continue
            print('开始独立短后端验收：' + name, flush=True)
            started = time.monotonic()
            receipt = host.invoke(dict(request_id='short-solve', tool_id='simulation.run', arguments={}, reason='用户授权的独立短接口验证', cache='new'))
            record = dict(case=name, backend=backend, steps_requested=steps, solve=receipt, elapsed_s=time.monotonic() - started)
            if receipt['execution_status'] == 'completed':
                evaluation = host.invoke(dict(request_id='score', tool_id='evaluation.run', arguments=dict(result=receipt['output']), reason='固定任务评价'))
                record['evaluation'] = evaluation
                if evaluation.get('output'):
                    record['result'] = store.artifact(evaluation['output'])
                from tools.platform_view import export_html
                export_html(host, root / (name + '.html'))
            report['numerical'].append(record)
            report['counts'] = accounting(roots)
            atomic_json(root / 'acceptance.json', report)
    report['counts'] = accounting(roots)
    atomic_json(root / 'acceptance.json', report)
    print(json.dumps(dict(report=str(root / 'acceptance.json'), checks=report['checks'], counts=report['counts']), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
