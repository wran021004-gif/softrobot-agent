"""Offline T1 evidence export from immutable saved B matrices; no model builder.

Run: python -m tests.research.s130_conic_comparison --output <new-json-path>
Refuses to overwrite an existing result. No Store, Provider or physical worker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from importlib.metadata import version

from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisProtocol, TaskAnalysisRequirement
from extensions.math_analysis.conic_capability import conic_capability
from extensions.math_analysis.task_capability import task_capability


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'evidence/s129_math_capability/gvs_pair.json'


def comparison():
    saved = json.loads(SOURCE.read_text(encoding='utf-8'))
    result = dict(scope='T1 offline saved frozen affine models only; no nonlinear/physical acceptance',
        source=dict(path=SOURCE.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    baseline_result=saved['baseline_result'], changed_result=saved['changed_result']),
        checkout_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        requested_research_baseline='13ddf460f9cb792cfb8e809a4e4f225c0bfd22f0',
        environment=dict(python=platform.python_version(), platform=platform.platform(),
            versions={name:version(name) for name in ('cvxpy', 'clarabel', 'numpy', 'scipy', 'pydantic')},
            thread_environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')}),
        implementation_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (
            'extensions/math_analysis/conic_capability.py', 'extensions/math_analysis/task_capability.py',
            'extensions/math_analysis/trajectory.py', 'tests/research/s130_conic_comparison.py')}, cases={})
    for key in ('baseline', 'changed'):
        original = saved[key]
        m = EndpointLinearizedModel.model_validate(original['model'])
        r = TaskAnalysisRequirement.model_validate(original['task_analysis'])
        p = TaskAnalysisProtocol.model_validate(original['protocol'])
        conic = conic_capability(m, r, p)
        slsqp = task_capability(m, r, p)
        replay = task_capability(m, r, p, applied_input_n=original['trajectory']['applied_input_n'])
        score = conic.get('replayed_violation')
        result['cases'][key] = dict(source_pointer='/'+key,
            historical_score=original['trajectory']['best_found_violation'],
            historical_control_replay=replay, slsqp=slsqp, conic=conic,
            slsqp_minus_conic=(slsqp['best_found_violation']-score
                if score is not None and 'best_found_violation' in slsqp else None),
            historical_minus_conic=(original['trajectory']['best_found_violation']-score if score is not None else None))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve historical evidence and choose a new path.')
    result = comparison()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for key, row in result['cases'].items():
        conic = row['conic']; dual = conic.get('dual_checks', {})
        print(json.dumps(dict(case=key, historical=row['historical_score'],
            slsqp=row['slsqp'].get('best_found_violation'), conic=conic.get('replayed_violation'),
            lower=dual.get('support_lower_estimate'), gap=dual.get('replayed_support_gap'),
            optimality=conic['optimality_status'], iterations=conic['solver'].get('iterations'),
            kernel_s=conic['kernel_elapsed_s']), allow_nan=False))
