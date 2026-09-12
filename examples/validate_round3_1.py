"""Retain Round 3.1 regression and ONE Human-authorized 12-evaluation experiment."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.artifact_tools import create_run, finalize_run
from tools.harness import run_reach, _snapshot_sources
from tools.experiment_tools import optimize_design
from tools.spec_tools import ROOT
from examples.validate_round3 import audit, compare, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, help='Retained pre-change baseline run ID')
    parser.add_argument('--visualize', action='store_true', help='Also verify a real passive viewer on the baseline')
    args = parser.parse_args()
    from tools.matlab_tools import MatlabTools
    matlab = MatlabTools()
    class Shared:
        def __getattr__(self, name):
            return getattr(matlab, name)
        def close(self):
            pass
    validation = create_run()
    status = 'ERROR'
    try:
        _snapshot_sources(validation, (Path(__file__).resolve(),))
        baseline = run_reach(matlab_factory=Shared)
        result = {'regression': compare(ROOT/'runs'/args.before, baseline.path)}
        debug = run_reach(matlab_factory=Shared, debug=True)
        result['debug_regression'] = compare(baseline.path, debug.path)
        assert read(debug.path/'debug/status.json')['errors'] == []
        if args.visualize:
            live = run_reach(matlab_factory=Shared, debug=True, visualize=True)
            result['live_viewer_regression'] = compare(baseline.path, live.path)
            assert read(live.path/'debug/status.json')['errors'] == []
        window = run_reach(task_package=ROOT/'tests/fixtures/reach_window_dev', matlab_factory=Shared, debug=True)
        assert read(window.path/'debug/status.json')['errors'] == []
        assert (window.path/'debug/matlab_clearance.png').is_file()
        result['window_development_debug'] = audit(window.path)
        # No formal experiment starts until the observational regression above passes.
        experiment = optimize_design(ROOT/'configs/experiments/round3_1_reach_free.yaml',
                                     matlab_factory=Shared, debug=True)
        result['formal_experiment'] = {'parent': audit(experiment.path),
            'summary': read(experiment.path/'optimization_summary.json'),
            'budget': read(experiment.path/'experiment_summary.json'),
            'candidates': read(experiment.path/'candidate_comparison.json')}
        assert experiment.record.final_status == 'PASS'
        assert result['formal_experiment']['budget']['evaluations'] == 12
        assert result['formal_experiment']['budget']['mujoco_attempts'] == 5
        children = []
        for reference in sorted(experiment.path.glob('candidate_*_run_reference.json')):
            ref = read(reference)
            child = ROOT/'runs'/ref['run_id']
            info = audit(child)
            assert info['run_manifest_hash'] == ref['run_manifest_hash']
            assert read(child/'experiment_context.json')['parent_experiment_id'] == experiment.record.run_id
            assert read(child/'debug/status.json')['errors'] == []
            children.append(info)
        result['formal_experiment']['children'] = children
        result['sensitivity'] = {'source': 'Existing M1 evaluations; zero additional budget consumed',
            'observations': [{k:r[k] for k in ('candidate_id','total_length_m','m1_predicted_error_m','model_run_id')}
                             for r in result['formal_experiment']['candidates'][:3]],
            'causal_attribution': 'UNKNOWN', 'limitation': 'Observed samples only; no causal physics claim'}
        validation.save('round3_1_validation.json', result)
        status = 'PASS'
        print('Validation:', validation.path, flush=True)
        print('Formal experiment:', experiment.path, flush=True)
        print(json.dumps(result['formal_experiment']['summary'], indent=2), flush=True)
    except Exception as exc:
        validation.save('validation_error.json', {'message': str(exc)})
        print('Incomplete validation:', validation.path, flush=True)
        raise
    finally:
        matlab.close()
        finalize_run(validation, status, None if status == 'PASS' else 'UNKNOWN')


if __name__ == '__main__':
    main()
