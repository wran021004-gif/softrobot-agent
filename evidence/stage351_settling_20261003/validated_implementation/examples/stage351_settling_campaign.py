"""One complete baseline, conditional development pilot and frozen matched pairs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store
from tools.diagnostic_workflow import implementation,MEMORY
from tools.improvement_workflow import execution_host,archive_store,BASELINE_LIMITS,MODE_LIMITS
from tools.diagnostic_improvement import complete_execution,actual_diff
from tools.settling_campaign import SettlingWorkflow,control_grant,campaign_metrics,RANKING
from extensions.tendon_family.control_evidence import ControlEvidence

CONFIG=ROOT/'examples/stage351_experiment.json'
EXTRA_FILES=['tools/settling_campaign.py','tools/improvement_workflow.py','examples/stage351_settling_campaign.py',
    'examples/stage351_experiment.json','tests/test_stage351_settling.py','extensions/tendon_family/contracts.py',
    'extensions/tendon_family/gvs_profile.py','extensions/tendon_family/gvs_trajectory.py',
    'extensions/tendon_family/control_evidence.py','extensions/tendon_family/delivery_facts.py',
    'extensions/tendon_family/backends.py','examples/stage350_delivery_audit.py',
    'extensions/tendon_family/compiler.py','extensions/tendon_family/execution.py','extensions/tendon_family/gvs.py',
    'extensions/tendon_family/gvs_casadi.py','extensions/tendon_family/gvs_basis.py','extensions/optimization/ipopt.py',
    'extensions/tendon_family/profiles/gvs_nmpc_free_reach_v1.json']


def frozen_implementation():
    value=implementation();value['files'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXTRA_FILES})
    return value


def usage(config):
    rows=[]
    for path in sorted(Path(config['run_directory']).glob('*/platform.sqlite')):
        store=Store(path.parent);rows.append(dict(label=path.parent.name,**store.remaining()))
    used={k:sum(r['used'][k] for r in rows) for k in config['overall_limits']}
    if any(used[k]>cap for k,cap in config['overall_limits'].items()):raise ValueError('OVERALL_CEILING_EXCEEDED')
    result=dict(runs=rows,used=used,limits=config['overall_limits'],remaining={k:cap-used[k] for k,cap in config['overall_limits'].items()},
        historical_stages='Excluded; unchanged source observations only.',monetary_cost=None)
    atomic_json(Path(config['evidence_directory'])/'cumulative_usage.json',result)
    return result


def baseline(config,runtime,freeze):
    directory=Path(config['run_directory'])/'baseline';export=Path(config['evidence_directory'])/'baseline'
    if (directory/'outcome.json').exists():return read(directory/'outcome.json')
    if directory.exists():raise ValueError('BASELINE_ALREADY_PREPARED: preserve and inspect; no repeated launch')
    source=ControlEvidence(Store(config['source_store'])).resolve(config['execution_id'])
    if source['manifest']!=config['source_manifest'] or source['metadata']['candidate_input']['artifact_id']!=config['configuration_artifact']:
        raise ValueError('SOURCE_MANIFEST_OR_CONFIGURATION_CHANGED')
    effective=control_grant(source['configuration'])
    store=Store(directory);store.create(dict(project_id='gvs-stage351-baseline',grant_id='gvs-stage351-baseline',budget=BASELINE_LIMITS,
        authorization_source=config['authorization_source']))
    host=execution_host(store,'gvs-stage351-baseline-executor',effective,BASELINE_LIMITS)
    atomic_json(directory/'freeze.json',dict(campaign=freeze,runtime=runtime,source_manifest=source['manifest'],
        source_configuration=source['metadata']['candidate_input'],grant_diff=actual_diff(source['configuration'],effective),
        effective_input=store.session(host.run_id)['snapshot']['input']))
    atomic_json(directory/'live_attempt.json',dict(started=datetime.now(timezone.utc).isoformat()))
    try:
        result=complete_execution(host,effective,'baseline-replay')
        gate=result['status']=='evaluated' and result['evaluation_data']['validity']=='valid' and result['factual_result']['valid_complete_execution']
        metrics=campaign_metrics(result['factual_result']) if gate else None
    except Exception as exc:result=dict(status='incomplete',error=str(exc));gate=False;metrics=None
    outcome=dict(status='completed' if gate else 'incomplete',gate_passed=gate,
        gate_reason='Valid complete execution and consistent evaluation/profile required; task failure remains valid evidence.',
        result=result,campaign_metrics=metrics,usage=store.remaining(),provider_usage=[],runtime=runtime)
    atomic_json(directory/'outcome.json',outcome)
    for p in directory.glob('*.json'):atomic_json(export/p.name,read(p))
    archive_store(store,export,source_stores=[config['source_store']]);usage(config)
    print('BASELINE',outcome['status'],json.dumps(metrics),flush=True)
    return outcome


def capability_gate(directory):
    outcome=read(directory/'outcome.json');physical=outcome.get('physical_improvement',{});execution=physical.get('complete_execution')
    checks=dict(workflow_completed=outcome['status']=='completed',feedback_complete=outcome.get('feedback_complete',False),
        nonempty_model_delta=bool((physical.get('preparation') or {}).get('decision',{}).get('changes')),
        actual_effective_diff=bool((physical.get('preparation') or {}).get('actual_diff')),
        complete_evaluated_execution=bool(execution and execution.get('status')=='evaluated' and execution['factual_result']['valid_complete_execution']
            and execution['evaluation_data']['validity']=='valid'),candidate_measurements_cited=False,accepted_final_decision='final_response' in outcome['chain'])
    if execution and 'revised_report' in outcome['chain']:
        report=Store(directory).artifact(outcome['chain']['revised_report'])
        checks['candidate_measurements_cited']=any(s['reference']==execution['receipts']['profile']['output']
            and isinstance(s['value'],(int,float)) and not isinstance(s['value'],bool)
            for rows in report['fact_selectors'].values() for s in rows)
    return dict(passed=all(checks.values()),checks=checks,task_success_not_required=True)


def audit(config):
    from examples.stage350_delivery_audit import audit_run
    base=Path(config['run_directory']);export=Path(config['evidence_directory']);rows=[];mapping={}
    for directory in sorted(base.iterdir()):
        if not (directory/'outcome.json').exists():continue
        row=audit_run(directory);rows.append(row)
        if directory.name=='baseline':continue
        outcome=read(directory/'outcome.json');store=Store(directory);label='case_'+str(len(mapping)+1);mapping[label]=directory.name
        products={key:store.artifact(ref) for key,ref in outcome.get('chain',{}).items()
            if key in ('initial_report','improvement_decision','revised_report','final_response')}
        encoded=json.dumps(products,ensure_ascii=False)
        with store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
        for identity in sorted(ids,key=len,reverse=True):encoded=encoded.replace(identity,'masked_context')
        for word in (directory.name,'single_context','dual_context',str(directory),directory.as_posix()):encoded=encoded.replace(word,'masked_organization')
        atomic_json(export/'masked_review'/f'{label}.json',dict(products=json.loads(encoded),
            review_type='Organization-masked implementer review; not independent blind review.',
            numerical_comparison=read(directory/'feedback.json').get('campaign_comparison') if (directory/'feedback.json').exists() else None))
    result=dict(runs=rows,usage=usage(config),tokens={k:sum(r['tokens'][k] for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        monetary_cost=None,cost_note='Provider-reported usage only; unsuccessful transports may have no token/cost data.',
        local_work={p.parent.name:read(p)['numerical_work'] for p in base.glob('*/outcome.json') if 'numerical_work' in read(p)},
        exact_source_checks='Separate from scientific prose review; no semantic acceptance claim.',
        comparative_limit='Four runs on one case are exploratory; no statistical significance or general organizational superiority.')
    atomic_json(export/'final_audit.json',result);atomic_json(export/'review_mask_mapping.json',mapping)
    return result


def main(action,credential):
    config=read(CONFIG);base=Path(config['run_directory']);export=Path(config['evidence_directory'])
    if action=='audit':return audit(config)
    from tools.runtime_identity import require_softagent_runtime
    runtime=require_softagent_runtime();current=frozen_implementation()
    marker=read(export/'focused_check.json')
    if marker['status']!='passed' or marker['implementation_files']!=current['files']:raise ValueError('FOCUSED_CHECK_REQUIRED')
    freeze_path=export/'development_freeze.json'
    if freeze_path.exists():
        freeze=read(freeze_path)
        if freeze['implementation']['files']!=current['files']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
    else:
        from tools.platform_registry import registry
        freeze=dict(implementation=current,runtime=runtime,configuration=config,ranking=RANKING,memory_policy=MEMORY,
            provider={**read(config['provider_freeze'])['provider_configuration'],'adapter_version':'4.0.0'},
            instructions=SettlingWorkflow.instructions,permissions=SettlingWorkflow.permissions,phases=SettlingWorkflow.phases,
            capabilities=SettlingWorkflow.capabilities,numerical_limits=SettlingWorkflow.numerical_limits,
            limits=dict(baseline=BASELINE_LIMITS,organization=MODE_LIMITS),
            tool_schemas={name:registry().get(name,version,'tool').input_schema.model_json_schema() for name,version in SettlingWorkflow.tools.items()},
            created=datetime.now(timezone.utc).isoformat())
        atomic_json(freeze_path,freeze)
        for filename in current['files']:
            path=export/'validated_implementation'/filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/filename).read_bytes())
    original=baseline(config,runtime,freeze)
    if action=='baseline' or not original['gate_passed']:return original
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(credential)
    replay=ControlEvidence(Store(base/'baseline')).resolve(original['result']['execution_id'])
    experiment={**config,'source_store':str(base/'baseline'),'execution_id':original['result']['execution_id'],
        'source_manifest':replay['manifest'],'baseline_facts':original['result']['factual_result']}
    pilot=base/'development_dual'
    def launch(directory,mode,pilot_run=False):
        if (directory/'outcome.json').exists():return read(directory/'outcome.json')
        if directory.exists():raise ValueError('EXISTING_RUN_REQUIRES_INSPECTION: '+directory.name)
        if frozen_implementation()['files']!=freeze['implementation']['files']:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
        remaining=usage(config)['remaining']
        if any(remaining[k]<v for k,v in MODE_LIMITS.items()):raise ValueError('INSUFFICIENT_CAMPAIGN_CAPACITY')
        w=SettlingWorkflow(directory,mode,pilot=pilot_run,experiment=experiment);w.prepare(runtime)
        result=w.run();usage(config);audit(config);return result
    launch(pilot,'dual_context',True)
    gate=capability_gate(pilot);atomic_json(export/'pilot_gate.json',gate)
    if action=='pilot' or not gate['passed']:
        atomic_json(export/'formal_status.json',dict(status='not_launched',prerequisite=gate));return gate
    paired_path=export/'paired_freeze.json'
    if not paired_path.exists():
        atomic_json(paired_path,dict(development=freeze,implementation=current,baseline=original['result'],
            baseline_manifest=replay['manifest'],pilot_gate=gate,order=config['formal_order'],candidate_count=1,
            rules='Fresh stores and working memories; common baseline only; no cross-run conclusions. No replacements or repairs.',
            experiment=experiment,ranking=RANKING))
    elif read(paired_path)['implementation']['files']!=current['files']:raise ValueError('FORMAL_FREEZE_CHANGED')
    for pair,mode in config['formal_order']:
        outcome=launch(base/f'pair{pair}_{mode}',mode)
        # Model/network/task failure remains an outcome. An explicit host defect
        # marker stops the freeze; no automatic repairs or replacement runs.
        if (export/'shared_defect.json').exists():break
        if outcome['physical_improvement'].get('validation_gap'):
            # Invalid model deltas remain run outcomes; they do not imply a host defect.
            print('MODEL_DELTA_REJECTED',pair,mode,flush=True)
    done=[f'pair{pair}_{mode}' for pair,mode in config['formal_order'] if (base/f'pair{pair}_{mode}'/'outcome.json').exists()]
    atomic_json(export/'formal_status.json',dict(status='completed' if len(done)==4 else 'stopped',terminal_runs=done))
    return audit(config)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['baseline','pilot','campaign','audit'])
    parser.add_argument('--credential',type=Path);args=parser.parse_args();main(args.action,args.credential)
