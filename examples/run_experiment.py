"""Explicit deterministic experiment entry; policy validation owns authorization."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.experiment_tools import optimize_design, run_parameter_sensitivity, run_repair_loop, evaluate_candidate
from tools.experiment_policy_tools import load_experiment_policy
from tools.spec_tools import ROOT, load_yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', required=True, type=Path)
    parser.add_argument('--operation', required=True, choices=('evaluate', 'optimize', 'sensitivity', 'repair'))
    parser.add_argument('--fidelity', choices=('M0', 'M1', 'MUJOCO'), default='M1')
    parser.add_argument('--controller-level', choices=('C1', 'C2'), default='C1')
    parser.add_argument('--design', type=Path)
    args = parser.parse_args()
    if args.operation == 'evaluate':
        policy = load_experiment_policy(args.policy)
        _, run = evaluate_candidate(ROOT/policy.task_contract_source,
            load_yaml(args.design or ROOT/policy.baseline_design), args.policy,
            args.fidelity, controller_level=args.controller_level)
    elif args.operation == 'optimize':
        run = optimize_design(args.policy)
    elif args.operation == 'sensitivity':
        run = run_parameter_sensitivity(args.policy, fidelity=args.fidelity)
    else:
        run = run_repair_loop(args.policy)
    print(f'Experiment: {run.path}')
    print(f'Execution status: {run.record.final_status} (not canonical task success)')
    return 0 if run.record.final_status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
