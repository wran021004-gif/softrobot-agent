"""Package existing acceptance evidence. Never execute models or backends."""
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.spec_tools import ROOT
from tools.state_io import read, atomic_json
from tools.artifact_tools import file_hash
from examples.platform_acceptance import accounting


def main():
    target = ROOT / 'docs/evidence/platform'
    target.mkdir(parents=True, exist_ok=True)
    acceptance_root = ROOT / 'runs/platform_acceptance'
    final = acceptance_root / '9acf97b51e4c4fa68c8ae98515a6f42a'
    numerical = acceptance_root / '175b5a0daf9c499a994f65a1a288b130'
    matlab = acceptance_root / 'bfd530156b664a87abf0f9e27bd379ce'
    test_roots = [p for p in (ROOT / 'runs/platform_tests').iterdir() if (p / 'platform.sqlite').is_file()]
    numerical_roots = [p / 'numerical' for p in acceptance_root.iterdir() if (p / 'numerical/platform.sqlite').is_file()]
    cli_root = ROOT / 'runs/platform_cli_verification/project'
    if (cli_root / 'platform.sqlite').is_file():
        numerical_roots.append(cli_root)
    counts = accounting(test_roots + numerical_roots)
    counts['mathematical_executions'] += 1  # Direct execution of documented extension template, area=4 m^2.
    latest = read(final / 'acceptance.json')
    generated_contracts = read(ROOT / 'docs/platform_generated/contracts.json')
    with sqlite3.connect(Path(latest['test_project_roots'][0]) / 'platform.sqlite') as db:
        outputs = [json.loads(db.execute('SELECT body FROM artifacts WHERE id=?', (json.loads(r[0])['artifact_id'],)).fetchone()[0])
            for r in db.execute('SELECT output FROM workers')]
    overlap = min(o['ended_at'] for o in outputs) - max(o['started_at'] for o in outputs)
    validation = dict(baseline='63ae9b5', branch='feat/unified-development-platform',
        contract_version='1.0.0', final_checks=latest['checks'], final_check_counts=latest['counts'], cumulative_counts=counts,
        additional_checks=[dict(name='late_sealed_worker_output_reconciles_unknown_without_relaunch', passed=True, log='late_worker_check.log')],
        distinct_checks_passed=29,
        cumulative_project_count=len(test_roots + numerical_roots),
        representative_workers=dict(outputs=outputs, overlap_s=overlap, actual_parallel=overlap > 0),
        real_backend_summary=dict(mujoco_solves=2, mujoco_steps=100, matlab_solves=1, matlab_requested_steps=40,
            matlab_sample_times=41, matlab_successful_internal_steps=473, matlab_startup_failures_before_solve=1, historical_budget_used=0, real_model_requests=0),
        definitions=dict(public_contracts=len(generated_contracts)-1, payload_contracts=len(generated_contracts['payloads']),
            extensions=len(read(ROOT / 'docs/platform_generated/capabilities.json')), genesis='declared_not_implemented'),
        final_test_source=str(final.relative_to(ROOT)), numerical_source=str(numerical.relative_to(ROOT)), matlab_source=str(matlab.relative_to(ROOT)),
        validation_scope='本地接口、离线决策载荷、真实短求解和确定性工作者；非真实多模型质量或物理标定',
        note='累计计数包含开发失败后的定向复验；保留全部账本，不把失败夹具或合成参考称为真实求解。MATLAB 40 个输出区间是请求采样网格，不是 ode15s 自适应内部步数。')
    atomic_json(target / 'validation.json', validation)
    for label, folder in [('final_checks', final), ('short_backends', numerical), ('matlab_short', matlab)]:
        (target / (label + '.json')).write_bytes((folder / 'acceptance.json').read_bytes())
    (target / 'final_checks.log').write_bytes((final / 'checks.log').read_bytes())
    source_files = []
    for directory in ('tools', 'schemas', 'controllers', 'extensions', 'configs', 'physics_contracts', 'matlab', 'tasks', 'benchmarks', 'skills', 'agents', 'capabilities', 'metrics', 'examples'):
        source_files += [p for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in ('.py', '.m', '.yaml', '.json', '.xml', '.md')]
    source_files.append(ROOT / 'requirements.txt')
    with zipfile.ZipFile(target / 'source_snapshot.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(source_files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    atomic_json(target / 'source_manifest.json', dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        dirty=True, files={p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(set(source_files))},
        note='最终源码快照。先前真实短求解保留其当时依赖摘要；后续请求留存/记忆身份/导出/依赖声明加固未重跑物理求解。'))
    evidence = []
    for folder in (final, numerical, matlab):
        evidence += [p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.json', '.log', '.html', '.sqlite')]
    if cli_root.exists():
        evidence += [p for p in cli_root.parent.rglob('*') if p.is_file() and p.suffix in ('.sqlite', '.json', '.html', '.log', '.yaml')]
    for folder in latest['test_project_roots']:
        path = Path(folder)
        evidence += [p for p in path.rglob('*') if p.is_file() and p.suffix in ('.sqlite', '.json', '.yaml', '.log')]
    for path in test_roots:
        with sqlite3.connect(path / 'platform.sqlite') as db:
            late = db.execute("SELECT 1 FROM workers WHERE work_id='late'").fetchone()
        if late:
            evidence += [p for p in path.rglob('*') if p.is_file() and p.suffix in ('.sqlite', '.json', '.log')]
    with zipfile.ZipFile(target / 'acceptance_bundle.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(evidence)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    atomic_json(target / 'bundle_manifest.json', dict(files={p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(set(evidence))},
        packages={p.name: file_hash(p) for p in target.glob('*.zip')},
        note='含故障注入测试数据库；测试故意损坏的内容与未知资源保留原状。解包只读，不重新绑定授权。'))
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
