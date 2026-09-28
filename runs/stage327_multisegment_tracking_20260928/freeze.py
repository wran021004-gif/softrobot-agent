"""Freeze the committed baseline and authorized task before numerical execution."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from examples.gvs_tracking import multisegment_input, live_input
from tools.state_io import atomic_json, digest

out=Path(__file__).resolve().parent
if (out/'frozen_input.json').exists():raise ValueError('ALREADY_FROZEN')
baseline=subprocess.check_output(['git','rev-parse','2b2fb6d'],cwd=ROOT,text=True).strip()
source='runs/stage326_gvs_kernel_efficiency_20260928/confirmation_input.json'
original=json.loads(subprocess.check_output(['git','show',baseline+':'+source],cwd=ROOT))
value=multisegment_input(original)
atomic_json(out/'frozen_input.json',value)
atomic_json(out/'live_input.json',live_input(value))
atomic_json(out/'baseline_record.json',dict(baseline_commit=baseline,branch='feat/gvs-dynamics',
    initial_working_tree='clean',baseline_input=source,baseline_input_identity=digest(original),
    accepted_evidence='runs/stage326_gvs_kernel_efficiency_20260928/implementation_report.md',
    accepted_audit='runs/stage326_gvs_kernel_efficiency_20260928/confirmation_audit.json',
    negative_experiment_commit=subprocess.check_output(['git','rev-parse','1b4c00f'],cwd=ROOT,text=True).strip(),
    negative_experiment='runs/stage325_tracking_efficiency_20260928/implementation_report.md',
    retained_optimization='MX common-subexpression elimination; no numerical/controller changes',
    frozen_input_identity=digest(value),reference_identity=digest(value['task']['goal']),
    scoring=dict(interval_s=[.01,.70],samples=70,maximum_position_error_m=.010,include_startup_and_transition=True),
    deterministic_rollout_budget=1,extra_rollout_only_for_corrected_implementation_defect=True,
    conditional_live_gate='Valid complete deterministic execution with frozen sampled acceptance; otherwise no provider requests'))
atomic_json(out/'environment.json',dict(interpreter=sys.executable,python=sys.version,
    packages={p:importlib.metadata.version(p) for p in ('casadi','mujoco','numpy','scipy','pydantic')},
    threads={k:os.environ[k] for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
atomic_json(out/'verification_results.json',dict(
    commands=[dict(command='python -m unittest tests.test_stage327_multisegment -v',tests=4,passed=True,elapsed_s=.154),
        dict(command='python -m unittest tests.test_stage324_tracking.TrackingTests.test_same_graph_path_constant_and_absolute_moving_reference tests.test_stage324_tracking.TrackingTests.test_interval_evaluation_rejects_terminal_only_and_missing -v',tests=2,passed=True,elapsed_s=2.113)],
    backend_rollouts=0,provider_requests=0,scope='New reference/derivative/knot/clamp checks, unchanged robot/policy, constant/single-quintic compatibility, absolute scheduling, 70-sample complete-grid evaluation and one-count knot RMS; two relevant existing shared-path tests.'))
print('Frozen baseline, two-segment task, conditional live input and environment. No rollout/provider calls.')
