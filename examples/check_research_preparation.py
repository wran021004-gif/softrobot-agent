"""Export compact validation facts from the completed first-study preparation."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import atomic_json, read, digest
from tools.research_spec import load_spec
from tools.parameter_catalog import effective_catalog
from tools.research_tasks import assemble_acceptance, task_adapter
from tools.platform_store import Store

DEST=ROOT/'evidence/research_preparation_20261006'


def main():
    spec=load_spec();delivery=read(DEST/'smoke/delivery.json');entry=delivery['result']
    store=Store(ROOT/'runs/research_first_study_smoke_20261006')
    manifest=read(DEST/'smoke/artifact_manifest.json')
    for row in manifest['artifacts']:
        body=(DEST/'smoke'/row['path']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==row['reference']['artifact_id']==row['sha256']
    report=store.artifact(entry['profile'])
    cfg=store.artifact(entry['configuration'])
    evaluation=store.artifact(entry['evaluation']);motion=store.artifact(report['detail']['motion'])
    assert assemble_acceptance(cfg,evaluation,report,evaluation_reference=entry['evaluation'],
        profile_reference=entry['profile'],motion=motion)==entry['acceptance']
    protected=read(DEST/'protected_before.json')
    actual={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
    assert protected==actual
    atomic_json(DEST/'protected_verification.json',dict(before=protected,after=actual,unchanged=True))
    catalog=effective_catalog(spec['execution_template'])
    for row in catalog['parameters']:
        row['validation_evidence']['offline_check_result']='evidence/research_preparation_20261006/validation.json#/offline_checks/parameter_catalog'
        if row['id']=='design/near_section_scale':
            row['validation_evidence']['integration_execution']=entry['receipt']['execution_id']
            row['validation_evidence']['integration_outcome']=entry['acceptance']['status']
            row['validation_evidence']['scope']='One .96 section edit plus nonzero near_z initial angle/rate; complete valid physical failure, not a robustness pass.'
    catalog['identity']=digest({k:v for k,v in catalog.items() if k!='identity'})
    atomic_json(DEST/'parameter_catalog.json',catalog)
    atomic_json(DEST/'task_adapter.json',task_adapter(spec['execution_template']).describe())
    # Capture the actual live snapshot fingerprints separately from final sources.
    snapshot=store.session(entry['candidate_id'])['snapshot']
    files=['tools/fixed_research.py','tools/research_spec.py','tools/parameter_catalog.py','tools/research_tasks.py',
        'tools/context_assembly.py','tools/platform_store.py','tools/parameter_impacts.py','tools/platform_search.py',
        'tools/candidate_parameters.py','extensions/tendon_family/candidate.py','extensions/tendon_family/design_decisions.py',
        'extensions/tendon_family/parameter_capabilities.py','extensions/tendon_family/manifest.py',
        'examples/fixed_research_baseline.py','examples/check_research_recovery.py','examples/check_research_preparation.py']
    atomic_json(DEST/'implementation_manifest.json',dict(version=spec['version'],
        frozen_specification_identity=digest(spec),source_configuration=spec['source']['candidate']['configuration'],
        live_snapshot_project_commit=snapshot['project_commit'],live_snapshot_worktree_dirty=snapshot['worktree_dirty'],
        live_dependency_fingerprints=snapshot['dependencies'],
        final_source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
        post_smoke_amendments=['New-builder-only existing LLM batch parameter mapping; verified offline.',
            'Tracking default protocol identifier repaired; current reach result reassembles byte-equivalent JSON values.'],
        controller_behavior='Stable v7 recipe and numerical kernels unchanged. Smoke source remains independently bound; no rerun or rescore.'))
    checks=dict(fixed_baseline=dict(passed=True,checks=5,initial_duration_s=1.123,affected_duration_s=.006),
        parameter_catalog=dict(passed=True,checks=3,initial_duration_s=.297,combined_nine_check_duration_s=.301,command='python -m unittest tests.test_parameter_catalog'),
        task_adapters=dict(passed=True,checks=6,duration_s=.229,tracking_affected_duration_s=.202),
        recovery=read(DEST/'recovery_checks.json'),
        historical_structure=dict(passed=True,checks=3,duration_s=.233),
        historical_context=dict(passed=True,checks=5,duration_s=7.898,
            initial_failure='Sandbox denied private Python temporary-directory ACL; all five tests repeated with approved filesystem access. No scientific failure or evidence modification.'))
    if (DEST/'shared_parameter_checks.json').exists():checks['shared_parameter_batch']=read(DEST/'shared_parameter_checks.json')
    atomic_json(DEST/'validation.json',dict(version=spec['version'],specification_identity=digest(spec),
        environment=dict(branch='feat/gvs-dynamics',starting_checkout='46a8d91e217060c6f3cc8dda6e93baea4981d6c7',
            python='3.11.16',mujoco='3.13.0',numpy='2.4.6',casadi='3.7.2',pydantic='2.13.5',pytest='not_installed; existing unittest used',
            provider='Configured deepseek-flash settings preserved; existing credential loader used; no credentials archived.',
            services='No MATLAB or unrelated service started.'),
        offline_checks=checks,integration=dict(complete=delivery['status']=='complete_integration',
            execution_id=entry['receipt']['execution_id'],configuration=entry['configuration'],evaluation=entry['evaluation'],profile=entry['profile'],
            acceptance=entry['acceptance'],cost=entry['cost'],budget=delivery['budget'],
            scheduled_cases_consumed=1,formal_campaign_launched=False,repair_backend_slot_used=False),
        protected_historical_sources_unchanged=True,
        pending=['Eligible live context input-cost/response-quality validation','Full frozen perturbation study','Formal three-group comparison'],
        engineering_parallel_tasks=3,scientific_worker_calls=0,
        scientific_claim='Shared pipeline completed with honest holding-speed failure; no robustness/superiority/real-time claim.'))
    print('Frozen study, portable artifact hashes, exact reach acceptance and protected sources verified.')


if __name__=='__main__':main()
