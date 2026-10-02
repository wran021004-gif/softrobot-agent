"""Authorized sequential native validation, feedback pilot, and matched pairs."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.diagnostic_workflow import DiagnosticWorkflow, implementation, TOOLS, INSTRUCTIONS, PHASES, MEMORY, LIMITS, SCOPE, PERMISSIONS
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json, read
from tools.platform_registry import registry

BASE=ROOT/'runs/stage346_shared_diagnosis_20261002'
EVIDENCE=ROOT/'evidence/stage346_shared_diagnosis_20261002'


def launch(label,mode,runtime,**options):
    run=DiagnosticWorkflow(BASE/label,mode,**options);run.prepare(runtime)
    return run.run()


def main(action):
    runtime=require_softagent_runtime()
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    if action=='minimal':return launch('minimal','dual_context',runtime,minimal=True)
    if action=='pilot':
        if read(BASE/'minimal/outcome.json')['status']!='completed':raise ValueError('MINIMAL_NATIVE_VALIDATION_REQUIRED')
        return launch('pilot','dual_context',runtime,pilot=True)
    pilot=read(BASE/'pilot/outcome.json')
    if not pilot['feedback_complete'] or pilot['numerical_check_status']!='completed':
        raise ValueError('LIVE_FEEDBACK_CAPABILITY_NOT_ESTABLISHED: comparisons prohibited')
    freeze_path=EVIDENCE/'paired_freeze.json'
    if freeze_path.exists():raise ValueError('PAIRED_COMPARISON_ALREADY_STARTED: no replacement runs')
    freeze=read(BASE/'pilot/freeze.json')
    frozen=dict(source_manifest=freeze['source_manifest'],inventory=freeze['inventory'],implementation=implementation(),
        adapter_version='3.0.0',provider=freeze['provider_configuration'],instructions=INSTRUCTIONS,phases=PHASES,
        memory=MEMORY,limits=LIMITS,scope=SCOPE,permissions=PERMISSIONS,recovery=freeze['recovery'],
        tool_schemas={k:registry().get(k,v,'tool').input_schema.model_json_schema() for k,v in TOOLS.items()},
        measures=freeze['outcomes'],order=['single_context','dual_context','dual_context','single_context'],
        interpretation='Exploratory within-case organization comparison; no general superiority or significance claim.',
        cross_run_experience=False)
    atomic_json(freeze_path,frozen)
    outcomes=[]
    for i,mode in enumerate(frozen['order'],1):
        if implementation()['files']!=frozen['implementation']['files']:raise ValueError('FRAMEWORK_CHANGED_DURING_COMPARISON')
        outcomes.append(launch(f'pair{(i+1)//2}_{mode}',mode,runtime))
        atomic_json(EVIDENCE/'paired_outcomes.json',outcomes)
        # Failed model runs are outcomes; framework invariants must not be repaired mid-comparison.
        reason=outcomes[-1]['stop_reason'] or ''
        if any(s in reason for s in ('FROZEN_','SOURCE_SUMMARY_FAILED','MODEL_ADAPTER_POLICY_MISMATCH')):break
    aggregate={k:0 for k in ('model_calls','tool_calls','backend_solves','worker_calls','wall_s')}
    for result in [read(BASE/'minimal/outcome.json'),pilot,*outcomes]:
        for k,v in result['usage']['used'].items():aggregate[k]+=v
    atomic_json(EVIDENCE/'workload_usage.json',dict(used=aggregate,limits=dict(model_calls=123,tool_calls=303,wall_s=18300.,backend_solves=0,worker_calls=0)))
    # Blinding removes organization/session labels but preserves evidence hashes and scientific text.
    for i,result in enumerate(outcomes):
        label=f'report_{i+1:02d}'
        source=BASE/f"pair{(i+2)//2}_{result['mode']}"
        reports={k:read(source/(k+'.json')) for k in ('initial_report','revised_report') if (source/(k+'.json')).exists()}
        atomic_json(EVIDENCE/'anonymous'/f'{label}.json',reports)
    atomic_json(EVIDENCE/'anonymous_key.json',{f'report_{i+1:02d}':dict(mode=r['mode'],pair=(i+2)//2) for i,r in enumerate(outcomes)})
    return outcomes


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['minimal','pilot','compare'])
    main(parser.parse_args().action)
