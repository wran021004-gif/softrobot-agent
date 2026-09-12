"""Portable offline audit: imports no MATLAB or MuJoCo execution backend."""
import csv
import gzip
import json
import math
from pathlib import Path
import shutil
import tempfile
import zipfile
import tarfile
import io
from tools.closeout_state import read, verify_run, digest, atomic_json
from tools.artifact_tools import file_hash


def audit(root,parent_id):
    root=Path(root); parent=root/parent_id
    manifest=verify_run(parent)
    plan=read(parent/'frozen_plan.json'); state=read(parent/'campaign_state.json'); summary=read(parent/'closeout_summary.json')
    assert state['plan_hash']==digest(plan), 'Plan hash'
    assert state['completed_stages']==list('ABCDE') and state['workflow_status']=='COMPLETED', 'Incomplete stages'
    assert summary['workflow_status']=='COMPLETED' and manifest['final_status']=='PASS'
    attempts=state['attempts']; assert len(attempts)<=48
    assert len({a['attempt_id'] for a in attempts})==len(attempts)
    actual=[]; calls={}; auxiliary=set()
    for stage,budgets in plan['stage_budgets'].items():
        for fidelity,cap in budgets.items():
            assert sum(a['stage']==stage and a['fidelity']==fidelity for a in attempts)<=cap, 'Stage budget'
    for a in attempts:
        assert a['status'] not in ('pending','running'), 'Unresolved attempt'
        if a['status']=='interrupted':
            assert any(r['retry_of']==a['attempt_id'] and r['key']==a['key'] and r['status']=='completed' for r in attempts), 'Unrecovered interruption'
        if 'run_id' not in a:
            assert a['status'] in ('failed','interrupted'); continue
        child=root/a['run_id']; record=verify_run(child,a['run_manifest_hash'])
        context=read(child/'experiment_context.json')
        assert context['parent_experiment_id']==parent_id and context['candidate_id']==a['attempt_id'], 'Child identity'
        import yaml
        assert yaml.safe_load((child/'design_input.yaml').read_text())==a['design']
        assert a['key']==digest(dict(execution=plan['execution_fingerprint'],design=a['design'],fidelity=a['fidelity'],
            controller=a['controller'],feedback=plan['feedback_parameters'] if a['controller']=='C2' else None,
            initial_command='deterministic frozen MATLAB PCC plan',initial_state=plan['initial_state'],
            timing='feedback begins at step 0, before mj_step; every 20 steps')), 'Execution key'
        for name,h in plan['execution']['sources'].items():
            if name in record['source_hashes']:
                assert record['source_hashes'][name]==h, 'Mixed source revision: '+name
            else:
                # These historical hello examples were over-included by plan discovery,
                # and are not imported by the executed closeout entry point. Preserve
                # their exact planned bytes as auxiliary sources, not child execution.
                assert name in ('examples/mujoco_hello/pendulum.xml','examples/mujoco_hello/test_matlab_engine.py','examples/mujoco_hello/test_mujoco.py'), 'Missing execution source: '+name
                assert file_hash(root/'plan_sources'/name)==h, 'Missing/damaged auxiliary planned source: '+name
                auxiliary.add(name)
        for name,count in a.get('backend_calls',{}).items(): calls[name]=calls.get(name,0)+count
        if a.get('canonical_error_m') is None: continue
        r=read(child/'mujoco_result.json'); m=r['metrics']; task=yaml.safe_load((child/'task.yaml').read_text())
        assert m['target_position_m']==task['target_m'] and m['position_error_max_m']==task['position_error_max_m'], 'Metric/task truth mismatch'
        error=math.dist(m['tip_position_m'],task['target_m'])
        assert math.isclose(error,a['canonical_error_m'],abs_tol=1e-12) and error==m['position_error_m'], 'Canonical error'
        assert (error<=m['position_error_max_m'])==m['task_success'], 'Canonical gate'
        assert read(child/'gate_summary.json')['canonical_result']==('PASS' if m['task_success'] else 'FAIL')
        rows=json.loads(gzip.decompress((child/'trajectory.json.gz').read_bytes()))
        assert len(rows)==m['steps']==1000 and math.isclose(rows[-1]['time_s'],2.,abs_tol=1e-10), 'Frozen duration'
        assert math.dist(rows[-1]['tip_m'],m['tip_position_m'])<1e-12, 'Trajectory final tip'
        assert rows[-1]['qpos_rad']==r['artifacts']['final_state']['qpos'], 'Final state'
        assert all(-20.-1e-10<=f<=1e-10 for row in rows for f in row['solver_actuator_force_n']), 'Unilateral force'
        if a['controller']=='C2':
            updates=read(child/'feedback_updates.json')
            if isinstance(updates,dict): updates=updates['updates']
            assert [u['step'] for u in updates]==list(range(0,1000,20)), 'C2 timing'
            assert all(u['max_command_delta_m']<=.0001+1e-12 for u in updates), 'C2 step bounds'
            assert read(child/'shape_comparison.json')['metrics']['evidence_status']=='NOT_APPLICABLE_TIME_VARYING_COMMAND'
        actual.append(a)
    best=min(actual,key=lambda a:(a['canonical_error_m'],a['attempt_id']))
    assert summary['best']['attempt_id']==best['attempt_id']==state['incumbents']['global']['attempt_id'], 'Incumbent'
    assert summary['backend_calls']==calls and summary['attempts']==len(attempts), 'Backend accounting'
    for route in ('C1','C2'):
        route_best=min((a for a in actual if a['controller']==route),key=lambda a:(a['canonical_error_m'],a['attempt_id']))
        assert state['incumbents'][route]['attempt_id']==route_best['attempt_id'], 'Route incumbent'
    assert summary['canonical_task_status']==best['canonical_task_status']
    assert summary['improvement_observed']==(best['canonical_error_m']<summary['historical_best_current_revision']['canonical_error_m'])
    by_id={a['attempt_id']:a for a in attempts}
    pair_rows=read(parent/'control_pairs.json')
    for p in pair_rows:
        a,b=by_id[p['C1']],by_id[p['C2']]
        assert a['design']==b['design']==p['design'], 'Pair design'
        for name in ('task.yaml','environment.yaml','robot_ir.yaml','physics.yaml','simulator.yaml','run_settings.yaml','tendon_command.json'):
            assert (root/a['run_id']/name).read_bytes()==(root/b['run_id']/name).read_bytes(), 'Pair input: '+name
        am=read(root/a['run_id']/'mujoco_result.json')['metrics']; bm=read(root/b['run_id']/'mujoco_result.json')['metrics']
        assert am['execution_evidence']['tip_initial_position_m']==bm['execution_evidence']['tip_initial_position_m']
        assert p['improvement_m']==a['canonical_error_m']-b['canonical_error_m'], 'Pair effect'
    for r in read(parent/'required_pairs.json'):
        assert any(p['design']==r['design'] for p in pair_rows), 'Missing required pair'
    for name in state['decisions']:
        d=read(parent/name)
        for path,h in d['evidence'].items(): assert file_hash(parent/path)==h, 'Decision evidence'
    assert len(state['decisions'])>0
    reproduction=read(parent/'reproduction.json'); assert reproduction['passed']
    from tools.closeout_campaign import reproduce
    class State: pass
    proxy=State(); proxy.plan=plan; proxy.run=State(); proxy.run.path=parent
    assert reproduce(proxy,by_id[reproduction['original']],by_id[reproduction['replica']])==reproduction, 'Replica recomputation'
    for row in read(parent/'historical_evidence.json'):
        if row['evidence_status']=='VERIFIED_LOCAL_RAW': verify_run(root/row['run_id'],row['run_manifest_hash'])
    return dict(passed=True,parent_id=parent_id,verified_children=sum('run_id' in a for a in attempts),
        canonical_metrics_recomputed=len(actual),control_pairs=len(pair_rows),decisions=len(state['decisions']),
        auxiliary_planned_sources=sorted(auxiliary),no_backend_started=True,
        limits='Hashes detect content inconsistency, not malicious replacement of all evidence.')


def bundle(parent,output):
    parent=Path(parent); output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    state=read(parent/'campaign_state.json'); identities=[parent.name]
    identities += [a['run_id'] for a in state['attempts'] if 'run_id' in a]
    identities += [r['run_id'] for r in read(parent/'historical_evidence.json') if r['evidence_status']=='VERIFIED_LOCAL_RAW']
    result=audit(parent.parent,parent.name)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        archive.writestr('bundle_index.json',json.dumps(dict(parent_id=parent.name,audit=result)))
        for identity in sorted(set(identities)):
            for path in sorted((parent.parent/identity).rglob('*')):
                if path.is_file(): archive.write(path,path.relative_to(parent.parent).as_posix())
        for name in result['auxiliary_planned_sources']:
            archive.write(parent.parent/'plan_sources'/name,'plan_sources/'+name)
    return dict(path=str(output),bytes=output.stat().st_size,sha256=file_hash(output),audit=result)


def audit_bundle(path):
    with tempfile.TemporaryDirectory() as tmp:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    assert (Path(tmp)/name).resolve().is_relative_to(Path(tmp).resolve()), 'Unsafe ZIP path'
                z.extractall(tmp)
        else:
            with tarfile.open(path,'r:xz') as archive:
                for member in archive:
                    target=(Path(tmp)/member.name).resolve()
                    assert member.isfile() and target.is_relative_to(Path(tmp).resolve()), 'Unsafe TAR member'
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
        index=read(Path(tmp)/'bundle_index.json')
        result=audit(tmp,index['parent_id'])
        validation=Path(tmp)/'validation_index.json'
        if validation.exists():
            v=read(validation)
            for identity,h in v['runs'].items():verify_run(Path(tmp)/identity,h)
            for name,h in v['files'].items():assert file_hash(Path(tmp)/name)==h, 'Validation supplement hash: '+name
            result['verified_validation_runs']=len(v['runs'])
        return result


def compress_bundle(zip_path,output):
    """Solid xz deduplicates repeated snapshots while preserving every hashed byte."""
    with zipfile.ZipFile(zip_path) as source,tarfile.open(output,'w:xz',preset=6) as dest:
        for name in source.namelist():
            data=source.read(name);info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0
            dest.addfile(info,io.BytesIO(data))
    return dict(path=str(output),bytes=Path(output).stat().st_size,sha256=file_hash(output))


def export_report(parent,output):
    parent=Path(parent); s=read(parent/'closeout_summary.json'); state=read(parent/'campaign_state.json')
    lines=['# ROUND 3 DETERMINISTIC CLOSEOUT RESULT','',
        f"workflow_status: **{s['workflow_status']}**; canonical_task_status: **{s['canonical_task_status']}**.",
        f"scientific_status: **{s['scientific_status']}**; failure_attribution: **UNKNOWN**.",'',
        'The frozen reach target, 0.01 m tolerance, 1000 steps / 2 s, gravity, initial state, inner servo and unilateral limits remain unchanged. '
        'New permission covers this C2 experiment and independent analysis only; see [authorization](../configs/experiments/round3_closeout_authorization.yaml).',
        '',f"Execution commit: `{s['execution_commit']}`. Parent: `{parent.name}`. Delivery commit is the commit containing this report; it is not the execution revision.",
        '',f"Best observed error: **{s['best']['canonical_error_m']:.12f} m**. Improvement vs baseline: {s['improvement_vs_baseline_m']:.12f} m; "
        f"vs historical-best design re-evaluated on this revision: {s['improvement_vs_historical_design_m']:.12f} m. improvement_observed={str(s['improvement_observed']).lower()}.",
        '',f"Stop: `{s['stop_reason']}`. Finite samples are not global optimization or real robot validation.",'',
        '## All executed candidates','',
        '| Attempt / run | Stage / route | L m | routing r m | tendons | body r m | segments / sections | M1 error m | actual error m | status |',
        '|---|---|---:|---:|---:|---:|---|---:|---:|---|']
    for a in state['attempts']:
        d=a['design']; lines.append(f"| {a['attempt_id']} / {a.get('run_id','none')} | {a['stage']} / {a['fidelity']} / {a['controller']} | {d['total_length_m']:.12g} | {d['tendon_routing_radius_m']:.12g} | {d['tendon_count']} | {d['body_radius_m']} | {d['segments']} / {d['sections']} | {a.get('model_error_m')} | {a.get('canonical_error_m')} | {a.get('canonical_task_status')} |")
    lines += ['', 'Every row uses legacy_v1_surrogate; model values are MODEL/SCREENING evidence, actual values are SIM_TO_SIM canonical surrogate evidence.',
        '', '## Same-design C1/C2 comparisons','', '| L / r / count | C1 error m | C2 error m | C1 minus C2 m | Attempts |','|---|---:|---:|---:|---|']
    for p in s['pairs']:
        d=p['design']; lines.append(f"| {d['total_length_m']} / {d['tendon_routing_radius_m']} / {d['tendon_count']} | {p['c1_error_m']:.12f} | {p['c2_error_m']:.12f} | {p['improvement_m']:.12f} | {p['C1']} / {p['C2']} |")
    lines += ['', '| Attempt | final max tendon tracking error m | peak force N | max-pull limit sampled | C2 updates / clipped |','|---|---:|---:|---|---|']
    pair_ids={p[c] for p in s['pairs'] for c in ('C1','C2')}
    for a in state['attempts']:
        if a['attempt_id'] not in pair_ids: continue
        child=parent.parent/a['run_id']; tracking=read(child/'check_tendon_tracking.json')['metrics']
        force=read(child/'check_actuator_limits.json')['metrics']
        updates=read(child/'feedback_updates.json') if (child/'feedback_updates.json').exists() else []
        lines.append(f"| {a['attempt_id']} | {tracking.get('max_absolute_error_m')} | {max(r['observed_peak_abs_force_n'] for r in force['actuators'])} | {force['max_pull_limit_observed']} | {len(updates)} / {sum(u['command_clipped'] for u in updates)} |")
    lines += ['', 'Paired effects compare identical design/initial PCC command/initial state/physics/numerics. Joint design and controller effects are separate. '
        'C2 shape mismatch is NOT_APPLICABLE_TIME_VARYING_COMMAND. Improved feedback does not identify the sole cause of previous failures.',
        '', '## Decisions and stop','']
    for name in state['decisions']:
        d=read(parent/name); lines.append(f"- `{name}`: `{d['rule_id']}` read {len(d['evidence'])} persisted evidence files before the next action; hashes, observations and remaining budgets are in the bundle.")
    lines += ['', '## Evidence and budgets','',
        f"{s['attempts']} candidate attempts: {s['model_attempts']} M1 routes and {s['mujoco_route_attempts']} MuJoCo routes; {s['retries']} retries, {s['cache_reads']} exact cache reads. Backend calls: `{json.dumps(s['backend_calls'])}`.",
        '', 'The compressed [portable evidence bundle](evidence/round3_closeout_evidence.tar.xz) contains all referenced numerical artifacts, source snapshots, manifests, trajectories, frozen plan, decisions and historical raw sources. '
        'Run `python examples/run_round3_closeout.py audit docs/evidence/round3_closeout_evidence.tar.xz` without MATLAB/MuJoCo execution.',
        '', 'Numerical reproduction checks full saved trajectory plus final state, tip, lengths and forces at atol=rtol=1e-9; these are reproduction tolerances, not task tolerances.',
        '', 'See [capability and parameter matrix](round3_closeout_tools.md) and [validation record](round3_closeout_validation.md) for the independent mechanics tests, recovery demonstration, damaged-copy audit and backend accounting.',
        '', '## Limitations / next phase','',
        'All physical parameters remain uncalibrated. The independent planar single-mode model omits contact, out-of-plane bending, shear, extension and torsion. '
        'Its static equilibria are not equivalent to a 2-second transient final pose. Synthetic stiffness recovery validates software under known assumptions, not physical identifiability. '
        'Next steps require measured mass/inertia, tendon/actuator response, shape observations and an approved calibrated PhysicsContract. '
        'A future restricted Agent can use these bounded tools after executor isolation and write permissions are enforced; no LLM or hardware integration is claimed.','']
    Path(output).write_text('\n'.join(lines),encoding='utf-8')
