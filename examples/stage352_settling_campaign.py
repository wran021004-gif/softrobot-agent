"""Stage 3.52 entry point: reuse baseline, delegate to validated settling runner."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store,plain
from tools.platform_host import Host
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import import_execution,BoundReader
from extensions.tendon_family.gvs_profile import execution_scope
from extensions.tendon_family.delivery_facts import bound_result_facts
from tools.settling_campaign import control_grant,campaign_metrics
from tools.improvement_workflow import archive_store
from examples import stage351_settling_campaign as campaign

CONFIG=ROOT/'examples/stage352_experiment.json'
REUSE_LIMITS=dict(model_calls=0,tool_calls=5,wall_s=120.,backend_solves=0,worker_calls=0)
EXTRA=['examples/stage352_settling_campaign.py','examples/stage352_experiment.json',
       'examples/stage352_preflight.py','tests/test_stage352_transport.py','tests/test_stage352_reuse.py']
_usage=campaign.usage


def verify_baseline(config):
    """Read sealed prior execution; retain identities and recompute existing facts."""
    store=Store(config['source_store']);reader=ControlEvidence(store)
    source=reader.resolve(config['execution_id']);original=read(store.root/'outcome.json');result=original['result']
    expected={'configuration':config['configuration_artifact'],'evaluation':config['evaluation_artifact'],
              'profile':config['profile_artifact']}
    actual=dict(configuration=source['metadata']['candidate_input']['artifact_id'],
        evaluation=result['receipts']['evaluation']['output']['artifact_id'],profile=result['receipts']['profile']['output']['artifact_id'])
    if actual!=expected:raise ValueError('PRIOR_BASELINE_REFERENCE_MISMATCH')
    refs=[source['manifest'],source['metadata']['candidate_input'],result['receipts']['simulation']['output'],
          result['receipts']['evaluation']['output'],result['receipts']['profile']['output'],*source['files'].values()]
    hashes={ref['artifact_id']:hashlib.sha256(store.artifact(ref,raw=True)).hexdigest() for ref in refs}
    evaluation=store.artifact(result['receipts']['evaluation']['output'])
    profile=store.artifact(result['receipts']['profile']['output'])['detail']
    if result['execution_id']!=source['execution_id'] or evaluation['source_execution_id']!=source['execution_id']:
        raise ValueError('PRIOR_BASELINE_EXECUTION_LINKAGE_MISMATCH')
    if evaluation['source']!=result['receipts']['simulation']['output'] or profile['execution_id']!=source['execution_id']:
        raise ValueError('PRIOR_BASELINE_EVALUATION_PROFILE_LINKAGE_MISMATCH')
    if profile['configuration']!=source['metadata']['candidate_input'] or profile['evaluation']!=result['receipts']['evaluation']['output']:
        raise ValueError('PRIOR_BASELINE_PROFILE_REFERENCES_MISMATCH')
    scope=execution_scope(source['configuration'])
    if profile['execution_scope']!=scope:raise ValueError('PRIOR_BASELINE_EXECUTION_SCOPE_MISMATCH')
    recipe=source['configuration']['policy']['controller']['parameters']['data']['recipe']
    if recipe['terminal_tip_speed_weight']!=0. or recipe['holding_tip_speed_weight']!=0.:
        raise ValueError('PRIOR_BASELINE_WEIGHTS_MISMATCH')
    facts=bound_result_facts(store,dict(profile_report=result['profile_report'],
        evaluation=result['receipts']['evaluation']['output'],simulation=result['receipts']['simulation']),result['design_statement'])
    if facts!=result['factual_result'] or evaluation!=result['evaluation_data']:
        raise ValueError('PRIOR_BASELINE_SAVED_SUMMARY_MISMATCH')
    if not campaign_metrics(facts)['valid_complete_execution']:raise ValueError('VALID_PRIOR_BASELINE_REQUIRED')
    effective=control_grant(source['configuration'])
    if execution_scope(effective)!=scope:raise ValueError('REUSE_CHANGED_BASELINE_SCIENCE')
    return dict(source=source,result=result,artifact_hashes=hashes,scope=scope,recipe=recipe,
        effective_input_identity=digest(effective),historical_usage=original['usage']['used'])


def reuse_baseline(config,runtime,freeze):
    export=Path(config['evidence_directory']);path=export/'baseline_reuse.json'
    if path.exists():return read(path)
    started=time.monotonic();verified=verify_baseline(config);source=verified['source']
    directory=Path(config['run_directory'])/'baseline_import'
    if directory.exists():raise ValueError('BASELINE_IMPORT_ALREADY_STARTED_PRESERVE_RECORDS')
    store=Store(directory);identity=config['project_prefix']+'-baseline-import'
    store.create(dict(project_id=identity,grant_id=identity,budget=REUSE_LIMITS,authorization_source=config['authorization_source']))
    inp=deepcopy(control_grant(source['configuration']));inp['run_id']=identity
    inp['policy'].update(route=None,search=None,budget=REUSE_LIMITS,timeout_s=30.,allowed_tools=[],
        tool_bindings={'diagnosis.inspect_evidence':'1.0.0'})
    host=Host(directory,identity);host.create(inp)
    binding=import_execution(ControlEvidence(Store(config['source_store'])),source['execution_id'],store,identity,source['manifest'])
    refs=[verified['result']['receipts'][name]['output'] for name in ('evaluation','profile')]
    with store.transaction() as db:
        for ref in refs:
            copied=plain(store.put(db,Store(config['source_store']).artifact(ref,raw=True),ref['media_type']))
            if copied!=ref:raise ValueError('BASELINE_IMPORT_HASH_MISMATCH')
        store.event(db,identity,'prior_baseline_evaluation_profile','imported',inputs=refs,outputs=refs)
    imported=BoundReader(store,binding).resolve(source['execution_id'])
    if imported!=source:raise ValueError('BASELINE_IMPORT_OWNER_OR_CONTENT_CHANGED')
    host.resume();receipt=host.invoke(dict(request_id='reused-baseline-summary',tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',
        arguments=dict(binding=binding,view='summary'),reason='Verify imported prior-stage baseline; zero new execution',cache='new'))
    if receipt['execution_status']!='completed':raise ValueError('REUSED_BASELINE_SUMMARY_FAILED')
    archive_store(store,export/'baseline_import',source_stores=[config['source_store']])
    elapsed=time.monotonic()-started;used=store.remaining()['used'];overhead=max(0.,elapsed-used['wall_s'])
    if used['wall_s']+overhead>REUSE_LIMITS['wall_s']:raise ValueError('BASELINE_REUSE_CEILING_EXCEEDED')
    result=dict(status='reused',gate_passed=True,classification='Reused prior-stage baseline; no new backend execution',
        source_store=config['source_store'],source_manifest=source['manifest'],owner_run_id=source['owner'],
        result=verified['result'],campaign_metrics=campaign_metrics(verified['result']['factual_result']),
        verification=verified,import_binding=binding,import_store=str(directory),new_backend_executions=0,
        new_usage={**used,'wall_s':used['wall_s']+overhead},import_overhead_s=overhead,
        historical_usage=verified['historical_usage'],gate_reason='Original integrity, ownership, execution/evaluation/profile linkage and frozen science verified',runtime=runtime)
    atomic_json(path,result);print('REUSED_BASELINE',source['execution_id'],json.dumps(result['campaign_metrics']),flush=True)
    return result


def usage(config):
    value=_usage(config);export=Path(config['evidence_directory']);rows=value['runs']
    path=export/'preflight.json'
    if path.exists():rows.append(dict(label='communication_preflight',used=read(path)['used']))
    path=export/'baseline_reuse.json'
    if path.exists():rows.append(dict(label='baseline_import_overhead',used=dict(model_calls=0,tool_calls=0,
        wall_s=read(path)['import_overhead_s'],backend_solves=0,worker_calls=0)))
    used={k:sum(r['used'][k] for r in rows) for k in config['overall_limits']}
    if any(used[k]>cap for k,cap in config['overall_limits'].items()):raise ValueError('OVERALL_CEILING_EXCEEDED')
    value.update(used=used,remaining={k:cap-used[k] for k,cap in config['overall_limits'].items()},
        historical_stages='Stage 3.51 execution and failed pilot costs excluded; prior baseline cost recorded separately.')
    atomic_json(export/'cumulative_usage.json',value);return value


def setup():
    campaign.CONFIG=CONFIG
    for filename in EXTRA:
        if filename not in campaign.EXTRA_FILES:campaign.EXTRA_FILES.append(filename)
    campaign.usage=usage


def main(action,credential):
    setup();config=read(CONFIG);export=Path(config['evidence_directory'])
    if action!='audit' and not read(export/'preflight.json')['communication_validated']:
        raise ValueError('LIVE_COMMUNICATION_PREFLIGHT_REQUIRED')
    return campaign.main(action,credential,baseline_loader=reuse_baseline)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['baseline','pilot','campaign','audit'])
    parser.add_argument('--credential',type=Path)
    args=parser.parse_args();main(args.action,args.credential)
