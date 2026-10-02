"""Authorized sequential native validation, feedback pilot, and matched pairs."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.diagnostic_workflow import DiagnosticWorkflow, implementation, TOOLS, INSTRUCTIONS, PHASES, MEMORY, LIMITS, SCOPE, PERMISSIONS, CAPABILITIES
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json, read
from tools.platform_registry import registry

BASE=ROOT/'runs/stage346_shared_diagnosis_20261002'
EVIDENCE=ROOT/'evidence/stage346_shared_diagnosis_20261002'
EXPERIMENT={}


def launch(label,mode,runtime,**options):
    run=DiagnosticWorkflow(BASE/label,mode,experiment=EXPERIMENT,**options);run.prepare(runtime)
    return run.run()


def require_feedback(directory):
    outcome=read(directory/'outcome.json')
    if outcome['status']!='completed' or not outcome['feedback_complete'] or outcome['numerical_check_status']!='completed':
        raise ValueError('LIVE_FEEDBACK_CAPABILITY_NOT_ESTABLISHED: '+str(directory))
    # Acceptance enforces exact selectors; scientific prose is a separate review.
    report=read(directory/'revised_report.json');response=read(directory/'final_response.json')
    if not report['report'].get('attribution') or not report['report'].get('limitations') or not response['reasoning']:
        raise ValueError('FEEDBACK_INTERPRETATION_REQUIRED')
    return outcome


def require_initial(directory):
    outcome=read(directory/'outcome.json')
    if outcome['status']!='completed' or 'initial_report' not in outcome['chain']:
        raise ValueError('INITIAL_REPORT_CAPABILITY_NOT_ESTABLISHED: '+str(directory))
    return outcome


def main(action,configuration=None,credential=None):
    global BASE,EVIDENCE,EXPERIMENT
    if configuration:
        EXPERIMENT=read(configuration)
        BASE=Path(EXPERIMENT['run_directory']);EVIDENCE=Path(EXPERIMENT['evidence_directory'])
    runtime=require_softagent_runtime()
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(credential or Path.home()/'.codex/.env')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    if action=='continue-feedback':
        return launch(EXPERIMENT['suffix_label'],'dual_context',runtime,suffix=True)
    if action=='minimal':return launch('minimal','dual_context',runtime,minimal=True)
    if action=='validate-initial':return launch(EXPERIMENT['initial_label'],'dual_context',runtime,initial_only=True)
    if action=='pilot':
        if EXPERIMENT.get('initial_label'):require_initial(BASE/EXPERIMENT['initial_label'])
        if EXPERIMENT.get('suffix_label'):require_feedback(BASE/EXPERIMENT['suffix_label'])
        if read(Path(EXPERIMENT.get('minimal_outcome',BASE/'minimal/outcome.json')))['status']!='completed':raise ValueError('MINIMAL_NATIVE_VALIDATION_REQUIRED')
        return launch(EXPERIMENT.get('pilot_label','pilot'),'dual_context',runtime,pilot=True)
    pilot_directory=BASE/EXPERIMENT.get('pilot_label','pilot')
    pilot=require_feedback(pilot_directory)
    freeze_path=EVIDENCE/'paired_freeze.json'
    if freeze_path.exists():raise ValueError('PAIRED_COMPARISON_ALREADY_STARTED: no replacement runs')
    freeze=read(pilot_directory/'freeze.json')
    if implementation()['files']!=freeze['implementation']['files']:raise ValueError('PILOT_IMPLEMENTATION_CHANGED: fresh validation required')
    from tools.platform_store import Store
    pilot_store=Store(pilot_directory);native_schemas={};validated_prompts={}
    for run_id in freeze['hosts'].values():
        for event in pilot_store.events(run_id):
            if event['kind']!='model_request':continue
            payload=pilot_store.artifact(event['inputs'][0])
            for tool in payload.get('tools',[]):native_schemas[tool['function']['name']]=tool['function']
            context=json.loads(payload['messages'][1]['content'])['role_context']
            validated_prompts[context['phase']]=dict(system=payload['messages'][0]['content'],instructions=context['instructions'])
    frozen=dict(source_manifest=freeze['source_manifest'],inventory=freeze['inventory'],implementation=implementation(),fact_policy=freeze['fact_policy'],
        native_schemas=native_schemas,validated_prompts=validated_prompts,
        adapter_version=freeze['provider_configuration']['adapter_version'],provider=freeze['provider_configuration'],instructions=INSTRUCTIONS,phases=PHASES,
        memory=MEMORY,limits=LIMITS,scope=SCOPE,permissions=PERMISSIONS,capabilities=CAPABILITIES,recovery=freeze['recovery'],experiment=EXPERIMENT,
        tool_schemas={k:registry().get(k,v,'tool').input_schema.model_json_schema() for k,v in TOOLS.items()},
        measures=freeze['outcomes'],review_rubric=freeze['review_rubric'],order=['single_context','dual_context','dual_context','single_context'],
        interpretation='Exploratory within-case organization comparison; no general superiority or significance claim.',
        cross_run_experience=False)
    atomic_json(freeze_path,frozen)
    outcomes=[]
    for i,mode in enumerate(frozen['order'],1):
        if implementation()['files']!=frozen['implementation']['files']:raise ValueError('FRAMEWORK_CHANGED_DURING_COMPARISON')
        label=f"{EXPERIMENT.get('comparison_label','pair')}{(i+1)//2}_{mode}"
        run=DiagnosticWorkflow(BASE/label,mode,experiment=EXPERIMENT);actual=run.prepare(runtime)
        for key,want in [('source_manifest',frozen['source_manifest']),('inventory',frozen['inventory']),('provider_configuration',frozen['provider']),('recovery',frozen['recovery'])]:
            if actual[key]!=want:raise ValueError('FROZEN_COMPARISON_CONFIGURATION_MISMATCH: '+key)
        outcomes.append(run.run())
        atomic_json(EVIDENCE/'paired_outcomes.json',outcomes)
        # Failed model runs are outcomes; framework invariants must not be repaired mid-comparison.
        reason=outcomes[-1]['stop_reason'] or ''
        if any(s in reason for s in ('FROZEN_','SOURCE_SUMMARY_FAILED','MODEL_ADAPTER_POLICY_MISMATCH')):break
    aggregate={k:0 for k in ('model_calls','tool_calls','backend_solves','worker_calls','wall_s')}
    suffix=[read(BASE/EXPERIMENT['suffix_label']/'outcome.json')] if EXPERIMENT.get('suffix_label') else []
    validation=[read(BASE/EXPERIMENT['initial_label']/'outcome.json')] if EXPERIMENT.get('initial_label') else []
    for result in [*validation,*suffix,pilot,*outcomes]:
        for k,v in result['usage']['used'].items():aggregate[k]+=v
    atomic_json(EVIDENCE/'workload_usage.json',dict(used=aggregate,limits=EXPERIMENT.get('overall_limits',dict(model_calls=120,tool_calls=300,wall_s=18000.,backend_solves=0,worker_calls=0))))
    # Blinding removes organization/session labels but preserves evidence hashes and scientific text.
    for i,result in enumerate(outcomes):
        label=f'report_{i+1:02d}'
        source=BASE/f"{EXPERIMENT.get('comparison_label','pair')}{(i+2)//2}_{result['mode']}"
        reports={k:read(source/(k+'.json')) for k in ('initial_report','revised_report','initial_response','final_response') if (source/(k+'.json')).exists()}
        atomic_json(EVIDENCE/'anonymous'/f'{label}.json',reports)
    atomic_json(EVIDENCE/'anonymous_key.json',{f'report_{i+1:02d}':dict(mode=r['mode'],pair=(i+2)//2) for i,r in enumerate(outcomes)})
    return outcomes


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['minimal','continue-feedback','validate-initial','pilot','compare'])
    parser.add_argument('--configuration',type=Path)
    parser.add_argument('--credential',type=Path)
    args=parser.parse_args();main(args.action,args.configuration,args.credential)
