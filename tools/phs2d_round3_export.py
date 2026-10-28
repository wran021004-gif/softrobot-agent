"""Read-only third-round audit and isolated evidence export, using the core Store."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import xml.etree.ElementTree as ET
import numpy as np
from tools.research import core
from tools.research.phs2d import host,ROOT
from tools.research.state import state
from tools.research.phs2d_evaluation import evaluate
from tools.state_io import atomic_json,digest
from extensions.tendon_family.compiler import resolve

OUT=ROOT/'evidence/phs2d_round3_20261028'
LABEL='P3_real9_E80_full8'


def split_archive(folder):
    path=folder/'immutable_artifacts.tar.gz';manifest=json.loads((folder/'archive_manifest.json').read_text(encoding='utf8'));parts=[];whole=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(40*1024*1024):
            part=path.with_name(path.name+f'.part{len(parts)+1:02d}');part.write_bytes(data);whole.update(data)
            parts.append(dict(file=part.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    assert whole.hexdigest()==manifest['archive_sha256']
    manifest.update(archive_parts=parts,reconstruction='Concatenate archive_parts in listed order. Verify archive_sha256 before opening gzip/tar.')
    atomic_json(folder/'archive_manifest.json',manifest)
    assert path.resolve().parent==folder.resolve();path.unlink()


def audit_set(h,p,ref):
    item=h.store.artifact(ref);base=h.store.artifact(item['baseline']);rows=[]
    for row in item['rows']:
        raw=h.store.artifact(row['reference']);e=evaluate(p,base,raw,row['s'])
        for key in ('status','valid','point_dx_m','tip_xy_m','ratio','out_of_plane_m','worst_violation'):assert row[key]==e[key]
        assert raw['request']['assembly']==base['request']['assembly']
        assert raw['request']['baseline']==item['baseline'] and abs(raw['request']['force_n'])==p['force_n']
        np.testing.assert_array_equal(raw['samples'][0]['qpos'],base['samples'][-1]['qpos'])
        assert max(abs(x) for x in raw['samples'][0]['qvel'])==0 and raw['samples'][0]['force_n']==0
        tail=[t for t in raw['samples'] if t['time_s']>=raw['samples'][-1]['time_s']-p['tail_s']-1e-9]
        extra=dict(failed_checks=[k for k,x in raw['checks'].items() if not x],geometry=raw['geometry']['status'],
            max_tail_residual_nm=max(t['static_balance_inf_nm'] for t in tail),max_tail_qvel_rad_s=max(t['qvel_inf'] for t in tail),
            max_tail_tension_n=max(max(t['tensions_n']) for t in tail),max_tail_length_excess_m=max(max(t['length_change']) for t in tail),
            final_tensions_n=raw['samples'][-1]['tensions_n'],taut=raw['samples'][-1]['taut'],
            qpos=raw['samples'][-1]['qpos'],positions=raw['samples'][-1]['positions'],baseline_positions=base['samples'][-1]['positions'])
        if raw.get('every_timestep_trajectory'):
            binary=raw['every_timestep_trajectory'];data=h.store.artifact(binary['reference'],raw=True)
            with np.load(io.BytesIO(data),allow_pickle=False) as f:
                values=f['trajectory'];columns=f['columns'];n=len(raw['samples'][-1]['qpos']);nt=len(raw['samples'][-1]['tensions_n'])
                assert values.shape==(round(p['load_max_s']/item['timestep']),2+3*n+2*nt)
                np.testing.assert_array_equal(values[-1,2:2+n],raw['samples'][-1]['qpos'])
                assert np.isfinite(values).all() and np.min(values[:,-nt:])>=-1e-10 and np.max(values[:,-nt:])<=8.
                assert np.max(abs(np.diff(values[:,0])-item['timestep']))<1e-11
                final_window=values[values[:,0]>=values[-1,0]-p['tail_s']-1e-9]
                extra['every_timestep_tail_qvel_rad_s']=float(np.max(abs(final_window[:,2+n:2+2*n])))
                assert extra['every_timestep_tail_qvel_rad_s']<=p['qvel_inf_limit_rad_s']
                assembly=h.store.artifact(raw['request']['assembly']);payout=np.array([assembly['payout_lengths_m']['tendon_'+str(i)] for i in range(nt)])
                extra['every_timestep_tail_length_excess_m']=float(np.max(final_window[:,2+3*n:2+3*n+nt]-payout))
                assert extra['every_timestep_tail_length_excess_m']<=p['length_excess_limit_m']
                extra['every_timestep_trajectory']=dict(**binary,columns=columns.tolist(),archive_member='artifacts/'+binary['reference']['artifact_id']+'.bin')
        rows.append({**row,**extra})
    return {**item,'reference':ref,'rows':rows}


def audit_study(revision):
    h,p=host(round3=revision);s=state(h);v=s['phs'];assert v['pending'] is None
    raw=[h.store.artifact(r) for r in v['results'].values()]
    steps=sum(r['cost']['physics_step_attempts'] for r in raw);math=sum(r['cost']['math_requests'] for r in raw)
    assert (steps,math)==(v['steps'],v['math']);internal=Counter();phase=Counter(dict(P0=0,P1=0,FINAL=0))
    for r in raw:
        phase[r['request']['phase']]+=r['cost']['physics_step_attempts']
        internal.update({k:x for k,x in r.get('numerical_cost',{}).items() if isinstance(x,(int,float))})
    assert dict(phase)==v['phase_steps']
    count=0
    with h.store.connect(True) as db:
        for row in db.execute('SELECT id,body FROM artifacts'):
            assert hashlib.sha256(row['body']).hexdigest()==row['id'];count+=1
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    assert all(c['receipt'] for c in calls)
    assert h.store.remaining()['used']['model_calls']==0
    sets=[audit_set(h,p,r) for r in v.get('dynamic_sets',[])]
    structures={}
    for label,ref in v.get('assemblies',{}).items():
        a=h.store.artifact(ref);c=h.store.artifact(a['candidate'])
        structures[label]=dict(reference=ref,**a,configuration=c['configuration'])
    failures=[r for r in raw if r.get('status') in ('exception','output_unavailable')]
    lookup={ref['artifact_id']:r for ref,r in zip(v['results'].values(),raw)};labels={ref['artifact_id']:label for label,ref in v.get('assemblies',{}).items()}
    cumulative=dict(physics_step_attempts=0,math_requests=0,generation_attempts=0);history=[]
    for c in calls:
        receipt=json.loads(c['receipt']);r=lookup.get(receipt['output']['artifact_id'])
        if c['request_id'].startswith('phs-generate-'):cumulative['generation_attempts']+=1
        if r:
            cumulative['physics_step_attempts']+=r['cost']['physics_step_attempts'];cumulative['math_requests']+=r['cost']['math_requests']
            history.append(dict(request_id=c['request_id'],label=labels.get((r['request'].get('assembly') or {}).get('artifact_id')),
                kind=r['request']['kind'],phase=r['request']['phase'],s=r['request'].get('s'),force_n=r['request'].get('force_n'),status=r.get('status','diagnostic'),cumulative=dict(cumulative)))
    assert cumulative['physics_step_attempts']==steps and cumulative['math_requests']==math and cumulative['generation_attempts']==len(v['candidates'])
    screens={label:h.store.artifact(r) for label,r in v.get('screens',{}).items()}
    for screen in screens.values():
        if screen.get('modal'):
            predictions=h.store.artifact(screen['modal'])['B_C_unilateral_force_response']['predictions']
            screen['linear_predictions']=[{k:r[k] for k in ('s','force_increment_n','point_dx_m','tip_xy_m','ratio')} for r in predictions]
    return h,dict(study_id=h.run_id,study_status=s['research_status'],protocol=p,p0=h.store.artifact(v['p0_report']),
        p0_history=v.get('p0_report_history',[]),dynamic_sets=sets,structures=structures,
        screens=screens,generation_order=[c['request_id'][len('phs-generate-'):] for c in calls if c['request_id'].startswith('phs-generate-')],
        ten_case_witness=v.get('ten_case_witness'),route_optimizations=[h.store.artifact(r) for r in v.get('route_optimizations',[])],
        chronological_cost_history=history,
        analyses=[dict(reference=ref,**r) for ref,r in zip(v['results'].values(),raw) if r['request']['kind'] in ('passive_design_sensitivity_v1','tendon_jacobian_matching_v1')],
        budgets=dict(physics_step_attempts=steps,math_requests=math,generation_attempts=len(v['candidates']),assemblies=len(structures),
            dynamic_candidates=len(v.get('dynamic_candidates',[])),dynamic_runs=sum(r['cost']['physics_step_attempts']>0 for r in raw),
            phase_steps=dict(phase),internal_recorded_cost=dict(internal),elapsed_numerical_s=sum(r['cost'].get('elapsed_s') or 0 for r in raw)),
        failures=failures,source_commits=sorted({r['implementation_commit'] for r in raw if 'implementation_commit' in r}),
        audit=dict(artifact_hashes_verified=count,receipts_verified=len(calls),costs_match=True,pending=None,
            independent_evaluations_recomputed=True,unchanged_assembly_all_conditions=True,zero_model_calls=True))


def export():
    OUT.mkdir(parents=True,exist_ok=True);studies=[]
    for revision in (1,2):
        h,summary=audit_study(revision);assert summary['study_status']=='stopped'
        destination=OUT/('store_v'+str(revision));core.export(h,destination);split_archive(destination)
        atomic_json(OUT/('study_v'+str(revision)+'.json'),summary);studies.append(summary)
    totals={k:sum(s['budgets'][k] for s in studies) for k in ('physics_step_attempts','math_requests','generation_attempts','assemblies','dynamic_candidates','dynamic_runs','elapsed_numerical_s')}
    assert totals['physics_step_attempts']<=20000000 and totals['math_requests']<=1200 and totals['generation_attempts']<=300 and totals['dynamic_candidates']<=60
    current=studies[-1];sets=[s for s in current['dynamic_sets'] if s['label']==LABEL]
    assert current['ten_case_witness']['label']==LABEL
    for rep in (1,2,3):
        matched=[s for s in sets if s.get('replicate')==rep]
        assert len(matched)==2 and all(s['all_pass'] for s in matched) and sum(len(s['rows']) for s in matched)==10
    # Every original acceptance field is identical across the two freezes and round two.
    original=json.loads((ROOT/'configs/research/phs2d_protocol_v3.json').read_text(encoding='utf8'))
    keys=['gravity','mount_position','mount_rotation','total_flexible_length_m','force_n','search_s','holdout_s','monitor_s','equilibrium_max_s','load_max_s','ramp_s','tail_s','tip_horizontal_limit_m','force_point_x_min_m','ratio_limit','out_of_plane_limit_m','tip_speed_limit_m_s','monitor_speed_limit_m_s','tail_drift_limit_m','qvel_inf_limit_rad_s','static_balance_inf_limit_nm','length_excess_limit_m','initial_lateral_limit_m','solreflimit','solimplimit']
    assert all(s['protocol'][k]==original[k] for s in studies for k in keys)
    chosen=current['structures'][LABEL];cfg=chosen['configuration'];physics=resolve(cfg['robot']['structure']['data'],cfg['policy']['discretization']['data'])
    independent=[s for s in sets if s.get('replicate')==1];rows=[r for s in independent for r in s['rows']]
    primary=next(s for s in independent if not s['holdout']);h,p=host(round3=2)
    base=h.store.artifact(primary['baseline']);protocol=base['numerical_protocol']
    payout=[chosen['payout_lengths_m'][t['entity']] for t in physics['tendons']]
    folder=h.store.root.parent/'models'/digest(dict(candidate=chosen['candidate'],payout=payout,unrestricted=False,protocol=protocol))
    target=OUT/'solution';target.mkdir(exist_ok=True);shutil.copyfile(folder/'model.xml',target/'model.xml')
    xml=ET.parse(target/'model.xml').getroot();assert not xml.findall('./equality/*') and not xml.findall('./actuator/*')
    world_roots=xml.findall('./worldbody/body');assert len(world_roots)==1 and world_roots[0].attrib['name']=='fixed_base'
    assert all(t['points'][0]['body']==-1 and physics['parts'][t['points'][-1]['body']]['component']=='payload' for t in physics['tendons'])
    assert all(physics['parts'][point['body']]['component'].startswith('guide_') and point['physical_binding'].get('hole') for t in physics['tendons'] for point in t['points'][1:-1])
    package=dict(label=LABEL,**chosen,physics=physics,baseline=base['samples'][-1],cases=rows,
        protocol=protocol,total_physical_mass_kg=sum(b['mass_kg'] for b in physics['parts']),
        math_screen=current['screens'][LABEL],modal=h.store.artifact(state(h)['phs']['modal'][LABEL]),
        sensitivity=[r for r in current['analyses'] if r['request']['kind']=='passive_design_sensitivity_v1' and r['request']['assembly']==chosen['reference']],
        exact_model_sha256=hashlib.sha256((target/'model.xml').read_bytes()).hexdigest())
    atomic_json(target/'design.json',package)
    import importlib.metadata
    import platform
    import sys
    atomic_json(OUT/'environment.json',dict(python=sys.version,platform=platform.platform(),machine=platform.machine(),
        packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']},
        native_xml_compilation_stack_bytes=32*1024*1024,provider_requests=0,nmpc_executions=0,ppo_executions=0))
    summary=dict(version='phs2d_round3_audit_v1',status='TEN_CONDITION_PASS_WITH_INDEPENDENT_HALFSTEP_PERTURBATION',label=LABEL,
        task_scope='Original independent development PHS evaluator; not a registered SELECT or hardware certificate',
        budgets=totals,remaining=dict(physics_step_attempts=20000000-totals['physics_step_attempts'],math_requests=1200-totals['math_requests'],candidates=300-totals['generation_attempts']),
        final_sets=sets,original_acceptance_unchanged=True,old_round_two_store_unmodified=True,
        search_stopped_at_first_ten_case_witness=current['ten_case_witness'],
        worst_independent=dict(min_point_m=min(r['point_dx_m'] for r in rows),max_tip_m=max(r['tip_xy_m'] for r in rows),max_ratio=max(r['ratio'] for r in rows),max_out_of_plane_m=max(r['out_of_plane_m'] for r in rows)),
        limitations=['Serial bending cell model omits axial extension, shear, torsion, friction, cable elasticity and self collision.',
            'Cable/solid validation covers saved poses; no continuous cable-contact solver or manufacturing/hardware certification.',
            'Viscosity is a declared physical material parameter, not experimentally calibrated.',
            'Original 10 ms sampled acceptance retained; per-step state/length/tension traces are additionally preserved.',
            'One native XML compiler stack-overflow request recovered with top-level charge and unknown internal construction cost; never relaunched.'])
    atomic_json(OUT/'summary.json',summary);print(json.dumps(dict(status=summary['status'],budgets=totals,worst=summary['worst_independent'])))


def verify():
    count=0
    for revision in (1,2):
        folder=OUT/('store_v'+str(revision));manifest=json.loads((folder/'archive_manifest.json').read_text(encoding='utf8'));whole=hashlib.sha256()
        path=ROOT/'runs/phs3_archive_verify'/('v'+str(revision)+'.tar.gz');path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('wb') as stream:
            for part in manifest['archive_parts']:
                assert Path(part['file']).name==part['file'];data=(folder/part['file']).read_bytes()
                assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest()==part['sha256'];stream.write(data);whole.update(data)
        assert whole.hexdigest()==manifest['archive_sha256'];members={r['name']:r for r in manifest['members']}
        with tarfile.open(path,'r|gz') as archive:
            for member in archive:
                record=members.pop(member.name);hasher=hashlib.sha256();stream=archive.extractfile(member)
                while data:=stream.read(1024*1024):hasher.update(data)
                assert hasher.hexdigest()==record['sha256'] and member.size==record['bytes'];count+=1
        assert not members
    print(json.dumps(dict(verified_archive_members=count)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();verify() if args.verify else export()
