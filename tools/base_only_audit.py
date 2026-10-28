"""Owner review of original receipts, with a scalar-only public export.

This verifies bindings; task acceptance is consumed exclusively from the original
Research Study evaluator. It never executes science or manufactures acceptance.
"""
import json
import sqlite3
from tools.base_only_campaign import OWNER, ROOT, CAPS, host_for, load_index, costs
from tools.research.state import state
from tools.research import core
from tools.research_tasks import _source_issue, _outcome_issue
from tools.state_io import atomic_json, digest


def audit(key, *, host=None, owner=None, write_manifest=True):
    """Verify existing receipts; injected read-only host avoids preparation writes."""
    owner=OWNER if owner is None else owner
    if not (owner/key/'private-store/platform.sqlite').exists():
        raise ValueError('EXISTING_OWNER_STORE_REQUIRED_FOR_READ_ONLY_AUDIT')
    h=host if host is not None else host_for(key);s=state(h)
    index=json.loads((owner/key/'index.json').read_text(encoding='utf8'))
    assert s['pending'] is None
    assert all(op['status']=='settled' for op in index['operations'])
    records=[]
    for entry in index['replays']:
        ref=entry['reference'];result=h.store.artifact(ref)
        assert _source_issue(result['acceptance']) is None
        if result['acceptance']['status'] in ('accepted','valid_failure'):
            assert _outcome_issue(result['acceptance']) is None
        receipt=json.loads(h.store.lookup(h.run_id,result['request_id'])['receipt'])
        assert receipt['execution_id']==result['execution_id']
        profile=h.store.artifact(result['profile_reference'])
        assert profile['execution_id']==receipt['execution_id']
        raw=h.store.artifact(result['raw_reference'])
        candidate=h.store.artifact(result['candidate'])
        cfg=candidate['configuration'];design=cfg['robot']['structure']['data']
        source=h.store.artifact(result['source_reference'])
        from tools.research.physical_replay import binding
        binding(cfg,source['trajectory'])
        assert all(t['points'][0]['attachment']['part']=='fixed_base' and t['points'][0]['role']=='start' for t in design['tendons'])
        assert cfg['task']['timing']==result['acceptance']['timing'] or all(
            result['acceptance']['timing'][k]==v for k,v in cfg['task']['timing'].items())
        if key=='M6':
            assert raw['rigid_tool_binding']['matched']
            if result['acceptance']['accepted']:
                assert raw['environment_contact']['contact_free']
                assert raw['environment_contact']['checked_physics_steps']==round(.6/cfg['task']['timing']['timestep_s'])
        records.append(dict(reference=ref,candidate=result['candidate'],source=result['source_reference'],
            raw=result['raw_reference'],evaluation=result['evaluation_reference'],profile=result['profile_reference'],
            receipt=receipt,condition=entry['condition'],structure_identity=digest(design),
            mesh_identity=digest(cfg['policy']['discretization']),acceptance=result['acceptance']))
    selected=s.get('selected');selected_refs=selected if isinstance(selected,list) else [selected] if selected else []
    if selected and isinstance(selected,dict):
        selection=h.store.artifact(selected)
        if selection.get('kind')=='joint_condition_result_v1':
            assert selection['task_gap']['accepted']
            selected_refs=selection['condition_results']
    selected_records=[r for r in records if r['reference'] in selected_refs]
    if selected_refs:
        assert len(selected_records)==len(selected_refs)
        assert all(r['acceptance']['accepted'] for r in selected_records)
        assert len({r['structure_identity'] for r in selected_records})==1
        assert len({r['mesh_identity'] for r in selected_records})==1
        if s['spec'].get('task_conditions'):
            assert {r['condition'] for r in selected_records}=={c['condition_id'] for c in s['spec']['task_conditions']}
    witness=dict(benchmark=key,store=str(h.store.root),study=s['spec']['resolved_identity'],
        frozen_implementation=s.get('freeze'),selected=selected,selected_records=selected_records,
        all_records=records,supervisor_index_identity=digest(index))
    if write_manifest:atomic_json(owner/key/'review_manifest.json',witness)
    lower=sum(op.get('confirmed_lower',0) for op in index['operations'])
    upper=sum(op.get('charged_upper',op['reserved_upper']) for op in index['operations'])
    assert upper<=CAPS[key]
    native_cost=[r['cost'] for r in index['analyses']]
    task_cfg=s['spec']['configuration']['task']
    status='accepted' if selected_refs else 'valid_failure' if any(r['acceptance']['status']=='valid_failure' for r in records) else 'incomplete' if records else 'not_run'
    result=dict(benchmark=key,status=status,selected=bool(selected_refs),stop_status=s['research_status'],
        task_id=task_cfg['task_id'],task_version=task_cfg.get('task_version'),task_identity=digest(task_cfg),
        selected_task_identities=[r['acceptance']['task_identity'] for r in selected_records],
        canonical_task_identity=digest(s['spec']['canonical_task']),
        source_provenance=s['spec']['configuration_provenance']['references'],
        condition_tasks=[dict(condition_id=c['condition_id'],task_id=c['task']['task_id'],task_identity=digest(c['task'])) for c in s['spec'].get('task_conditions',[])],
        family_space_identity=s['spec']['family_space_identity'],conditional_rules=s['spec']['family_space']['conditional_rules'],
        study_identity=s['spec']['resolved_identity'],implementation=s.get('freeze'),
        private_review_manifest_identity=digest(witness),private_review_relative_path=key+'/review_manifest.json',
        proposals=len(index['candidates']),mathematical_requests=s.get('mathematical_evaluations',0),
        native_callbacks=sum(c.get('optimization_evaluations',c.get('rollouts',0)) for c in native_cost),
        replay_count=len(records),physics_step_attempts_lower=lower,physics_step_attempts_upper=upper,
        confirmed_completed_steps=sum(op['cost'].get('physics_steps',0) for op in index['operations']),
        physics_step_cap=CAPS[key],native_kernel_wall_s=sum(c.get('kernel_wall_s',0) for c in native_cost),
        replay_kernel_wall_s=sum(r['cost'].get('kernel_wall_s',0) for r in index['replays']),
        operation_driver_elapsed_s=sum(op['finished']-op['started'] for op in index['operations']),
        numerical_s=s['numerical_s'],provider_requests=h.store.remaining()['used']['model_calls'],
        nmpc_executions=len(s.get('results',[])),rl_training_stages=s.get('rl_training_stages',0),
        selected_metrics=[dict(condition=r['condition'],metrics=r['acceptance']['metrics'],
            components={k:v for k,v in r['acceptance']['components'].items() if k in ('holding_position','holding_speed') or k.startswith('evaluator:')},
            result_identity=r['reference']['artifact_id']) for r in selected_records],
        independent_statuses=[dict(condition=r['condition'],status=r['acceptance']['status'],metrics=r['acceptance']['metrics']) for r in records],
        receipt_binding_audit=True,pending=False)
    return result


def main():
    results=[audit(k) for k in CAPS]
    preparations=[]
    for name in ('base-only-owner-20261028','base-only-owner-20261028-r1'):
        for path in (ROOT/'runs'/name).rglob('platform.sqlite'):
            with sqlite3.connect('file:'+path.resolve().as_posix()+'?mode=ro',uri=True) as db:
                for run_id,body in db.execute('SELECT run_id,state FROM sessions'):
                    s=json.loads(body)
                    assert s['research_status']=='stopped' and s.get('pending') is None
                    assert not s.get('analysis_results') and not s.get('physical_replays') and not s.get('results')
                    assert s.get('mathematical_evaluations',0)==0
                    preparations.append(dict(study_id=run_id,store_identity=digest(str(path.relative_to(ROOT))),
                        status='stopped',physics_step_attempts=0,mathematical_evaluations=0,
                        generated_candidates=len(s.get('candidates',{})),
                        numerical_s=s['numerical_s'],reason='Pre-integration preparation only; original admission/preflight failures preserved'))
    total=sum(r['physics_step_attempts_upper'] for r in results)
    assert total<=sum(CAPS.values())
    report=dict(version='base-only-discovery-scalar-export-v1',total_step_attempts_upper=total,
        total_step_attempts_lower=sum(r['physics_step_attempts_lower'] for r in results),
        confirmed_completed_steps=sum(r['confirmed_completed_steps'] for r in results),
        preparations=preparations,
        total_cap=sum(CAPS.values()),results=results,
        interpretation='Codex-organized development feasibility discovery. No autonomous Research Agent evaluation; no statistical structural advantage or global infeasibility claim.',
        future_agent_isolation='A fresh agent requires clean checkout, separate Store/context and enforced read scope excluding owner runs, this chat, hidden reports and historical winners. Git ignore alone is not an access boundary.')
    destination=ROOT/'evidence/base_only_benchmark_feasibility_20261028/summary.json'
    atomic_json(destination,report)
    print(json.dumps(dict(report=str(destination),total_step_attempts_upper=total,statuses={r['benchmark']:r['status'] for r in results})))


if __name__=='__main__':main()
