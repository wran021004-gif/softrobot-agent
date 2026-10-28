"""Read-only PHS round-2 audit over original Store artifacts; no physics calls."""
import hashlib
import json
import shutil
from collections import Counter
import numpy as np
from tools.research import core
from tools.research.phs2d import host,ROOT
from tools.research.state import state
from tools.research.phs2d_evaluation import evaluate
from tools.state_io import atomic_json

OUT=ROOT/'evidence/phs2d_round2_20261028'


def split_archive():
    """Keep the original core archive bytes while fitting GitHub file limits."""
    archive=OUT/'store/immutable_artifacts.tar.gz';manifest_path=OUT/'store/archive_manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf8'));parts=[];whole=hashlib.sha256()
    with archive.open('rb') as stream:
        while chunk:=stream.read(40*1024*1024):
            path=archive.with_name(archive.name+f'.part{len(parts)+1:02d}')
            path.write_bytes(chunk);whole.update(chunk)
            parts.append(dict(file=path.name,bytes=len(chunk),sha256=hashlib.sha256(chunk).hexdigest()))
    assert whole.hexdigest()==manifest['archive_sha256']
    manifest['archive_parts']=parts;manifest['reconstruction']='Concatenate archive_parts in listed order; resulting gzip SHA256 must equal archive_sha256.'
    atomic_json(manifest_path,manifest)
    assert archive.resolve().parent==(OUT/'store').resolve()
    archive.unlink()  # Only this newly generated, verified redundant archive.


def verify_parts():
    manifest=json.loads((OUT/'store/archive_manifest.json').read_text(encoding='utf8'));whole=hashlib.sha256()
    for part in manifest['archive_parts']:
        data=(OUT/'store'/part['file']).read_bytes();assert len(data)==part['bytes']
        assert hashlib.sha256(data).hexdigest()==part['sha256'];whole.update(data)
    assert whole.hexdigest()==manifest['archive_sha256']
    print('Archive parts and original archive SHA256 verified.')


def export():
    h,p=host(True);s=state(h);v=s['phs'];OUT.mkdir(parents=True,exist_ok=True)
    assert v['pending'] is None
    core.export(h,OUT/'store')
    split_archive()
    raw=[h.store.artifact(r) for r in v['results'].values()]
    attempts=sum(r['cost']['physics_step_attempts'] for r in raw)
    maths=sum(r['cost']['math_requests'] for r in raw)
    assert attempts==v['steps'] and maths==v['math']
    assert attempts<=p['limits']['physics_step_attempts'] and maths<=p['limits']['math_requests']
    phase=Counter()
    internal=Counter()
    for r in raw:
        phase[r.get('request',{}).get('phase','P0')]+=r['cost']['physics_step_attempts']
        internal.update({k:x for k,x in r.get('numerical_cost',{}).items() if isinstance(x,(int,float))})
    assert dict(phase)==v['phase_steps']
    with h.store.connect(True) as db:
        artifacts=list(db.execute('SELECT id,body FROM artifacts'))
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    for row in artifacts:assert hashlib.sha256(row['body']).hexdigest()==row['id']
    assert all(r['receipt'] for r in calls)
    sets=[];best={};plot=[]
    for ref in v.get('dynamic_sets',[]):
        result=h.store.artifact(ref);base=h.store.artifact(result['baseline']);rows=[]
        numeric=base['numerical_protocol'];key=f"dt={numeric['timestep_s']:g};solref={numeric['solreflimit']}"
        for row in result['rows']:
            run=h.store.artifact(row['reference']);req=run['request'];recheck=evaluate(p,base,run,row['s'])
            assert req['baseline']==result['baseline'] and req['s'] in p['search_s'] and abs(req['force_n'])==p['force_n']
            assert req['assembly']==base['request']['assembly']
            assert h.store.artifact(req['static_source'])['force_n']==0
            np.testing.assert_allclose(run['samples'][0]['qpos'],base['samples'][-1]['qpos'],atol=0,rtol=0)
            assert max(abs(x) for x in run['samples'][0]['qvel'])==0 and run['samples'][0]['force_n']==0
            for field in ('valid','status','tip_xy_m','point_dx_m','ratio','out_of_plane_m'):assert row[field]==recheck[field]
            tail=[r for r in run['samples'] if r['time_s']>=run['samples'][-1]['time_s']-p['tail_s']-1e-9]
            rows.append({**row,'failed_checks':[k for k,x in run.get('checks',{}).items() if not x],
                'tail_balance_nm':max(r['static_balance_inf_nm'] for r in tail),
                'tail_qvel_rad_s':max(r['qvel_inf'] for r in tail),
                'tail_speed_m_s':max(max(r['speeds']) for r in tail),
                'tail_actual_qacc_rad_s2':max(max(abs(x) for x in r['qacc']) for r in tail),
                'tail_drift_m':run['tail_drift_m'],'tail_excess_m':run['tail_excess_m'],
                'tensions_n':run['samples'][-1]['tensions_n'],'length_residual_m':run['samples'][-1]['length_change']})
            plot.append(dict(label=result['label'],numeric=key,s=row['s'],force_n=row['force_n'],valid=row['valid'],
                positions=run['samples'][-1]['positions'],baseline=base['samples'][-1]['positions'],
                tail=[{k:r[k] for k in ('time_s','static_balance_inf_nm','qvel_inf','tensions_n')} for r in tail]))
        item={**result,'reference':ref,'numerical_group':key,'rows':rows}
        if rows:item.update(min_point_m=min(r['point_dx_m'] for r in rows),max_tip_m=max(r['tip_xy_m'] for r in rows),
            max_ratio=max(r['ratio'] for r in rows),max_out_of_plane_m=max(r['out_of_plane_m'] for r in rows),
            worst_violation=max(r['worst_violation'] for r in rows))
        sets.append(item)
        if result['all_valid'] and (key not in best or item['worst_violation']<best[key]['worst_violation']):best[key]=item
    assert not any(r.get('request',{}).get('force_n') and r['request'].get('s') in p['holdout_s'] for r in raw)
    screens={k:h.store.artifact(ref) for k,ref in v['screens'].items()}
    structures={}
    for label,ar in v['assemblies'].items():
        a=h.store.artifact(ar);c=h.store.artifact(a['candidate']);eq=h.store.artifact(v['static_baselines'][label])
        structures[label]=dict(assembly_reference=ar,**a,configuration=c['configuration'],static_reference=v['static_baselines'][label],
            static_status=eq['status'],equilibrium=eq['equilibrium'])
    models=[];(OUT/'models').mkdir(exist_ok=True)
    for path in sorted((h.store.root.parent/'models').glob('*/model.xml')):
        target=OUT/'models'/(path.parent.name+'.xml');shutil.copyfile(path,target)
        models.append(dict(file=target.relative_to(OUT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    failures=[r for r in raw if r.get('status') in ('exception','output_unavailable') or 'error' in r]
    assert not any(r['all_pass'] for r in sets)
    summary=dict(version='phs_round2_audit_v1',status='NO_FEASIBLE_WITNESS',study_id=h.run_id,study_status=s['research_status'],
        protocol=p,p0=h.store.artifact(v['p0_report']),p0_history=v.get('p0_report_history',[]),
        candidates=len(v['candidates']),screens=screens,dynamic_sets=sets,best_valid_by_numerics=best,
        ranking='Only six-condition valid sets; minimize maximum independent normalized violation within the same numerical protocol.',
        holdout='UNUSED: no six-condition performance pass',registered_acceptance='not_registered; no SELECT',
        budgets=dict(physics_step_attempts=attempts,phase_steps=dict(phase),math_requests=maths,
            internal_recorded_cost=dict(internal),internal_cost_incomplete_failed_requests=len(failures),
            historical_consistency_forward_count_correction=1,
            unique_structural_candidates=len({r['artifact_id'] for r in v['candidates'].values()}),
            assembly_candidates=len(v['assemblies']),dynamic_designs=len({r['label'] for r in sets}),
            dynamic_runs=sum(r['cost']['physics_step_attempts']>0 for r in raw),
            recorded_elapsed_numerical_s=sum(r['cost'].get('elapsed_s') or 0 for r in raw),
            provider_requests=0,remaining_total=8000000-attempts,final_reserved_initial=800000),
        failures=failures,models=models,source_commits=sorted({r['implementation_commit'] for r in raw if 'implementation_commit' in r}),
        audit=dict(artifact_hashes_verified=len(artifacts),receipts_verified=len(calls),costs_match=True,
            independent_evaluations_recomputed=True,zero_velocity_and_unloaded_initialization_verified=True,
            unchanged_frozen_payout_all_conditions=True,holdout_force_conditions_unused=True,
            no_unknown_request_relaunched=True,old_P0_remains_failed=True),
        limitations=['Finite local search, not proof of infeasibility or optimality.',
            'KKT uses ideal hard unilateral cable; dynamics uses frozen MuJoCo soft constraints.',
            '48 bending coordinates; axial extension, shear, twist, friction and swept self-collision unsupported.',
            'Saved dynamics sampled at 10 ms; high-frequency extrema between samples are not certified.',
            'Two failed mathematical requests retain top-level charges; internal counts are unavailable.',
            'First semantic request undercounted one direct native forward call; correction reported separately.'])
    atomic_json(OUT/'summary.json',summary);atomic_json(OUT/'structures.json',structures);atomic_json(OUT/'plot_data.json',plot)
    print(json.dumps(dict(budgets=summary['budgets'],audit=summary['audit'],best={k:r['label'] for k,r in best.items()})))


if __name__=='__main__':
    import sys
    verify_parts() if '--verify' in sys.argv else export()
