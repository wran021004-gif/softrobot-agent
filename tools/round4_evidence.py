"""Read-only numerical audit and small portable evidence/derived artifacts."""
import csv
import gzip
import json
import math
import tarfile
import zipfile
from pathlib import Path
import numpy as np
from tools.spec_tools import ROOT,load_yaml
from tools.closeout_state import read,atomic_json
from tools.artifact_tools import file_hash
from tools.round4_campaign import OUT


def seal(root=OUT):
    root=Path(root)
    path=root/'raw_manifest.json'
    if path.exists():return read(path)
    files={p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()
        and 'derived' not in p.relative_to(root).parts and p.suffix not in ('.lock','.tmp')
        and p.name not in ('raw_manifest.json','test_record.json')}
    manifest=dict(format='round4_raw_v1',files=files,semantics='raw files immutable after seal; derived artifacts stored separately')
    atomic_json(path,manifest);return manifest


def audit(root=OUT):
    root=Path(root);manifest=read(root/'raw_manifest.json')
    for name,expected in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or file_hash(path)!=expected:raise ValueError('Raw evidence mismatch: '+name)
    frozen=read(root/'frozen_plan.json')
    import hashlib
    with zipfile.ZipFile(root/'execution_sources.zip') as archive:
        for name,expected in frozen['execution_sources'].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=expected:raise ValueError('Execution source mismatch: '+name)
    summary=read(root/'length_summary.json');checked=[];pairs={}
    for row in summary['rows']:
        if row.get('error_m') is None:continue
        relative=Path(row['run'].replace('\\','/')).relative_to('runs/round4')
        folder=root/relative;result=read(folder/'result.json');task=load_yaml(folder/'task.yaml')
        if file_hash(folder/'result.json')!=row['result_sha256']:raise ValueError('Candidate result binding mismatch')
        error=math.dist(result['metrics']['tip_position_m'],task['target_m'])
        if not math.isfinite(error) or abs(error-row['error_m'])>1e-12:raise ValueError('Canonical error mismatch')
        if (error<=task['position_error_max_m'])!=row['task_success']:raise ValueError('Canonical task outcome mismatch')
        trajectory=json.loads(gzip.decompress((folder/'trajectory.json.gz').read_bytes()))
        if len(trajectory)!=1000 or abs(trajectory[-1]['time_s']-2)>1e-9:raise ValueError('Incomplete saved motion')
        for sample in trajectory:
            if abs(sample['time_s']-sample['solver_time_s']-.002)>1e-10:raise ValueError('Sampling phase mismatch')
        if not np.allclose(trajectory[-1]['tip_m'],result['metrics']['tip_position_m'],atol=1e-12,rtol=0):raise ValueError('Saved tip mismatch')
        pairs.setdefault(row['length_m'],{})[row['controller']]=folder
        checked.append(dict(length_m=row['length_m'],controller=row['controller'],error_m=error))
    for length,g in pairs.items():
        if set(g)!= {'C1','C2'}:raise ValueError('Unpaired design')
        for name in ('robot.xml','task.yaml','environment.yaml','design_input.yaml','model_result.json'):
            if file_hash(g['C1']/name)!=file_hash(g['C2']/name):raise ValueError('Pair input mismatch: '+name)
    coarse=[r for r in summary['rows'] if r.get('error_m') is not None and r['stage']=='coarse']
    available=sorted(set(r['length_m'] for r in coarse));selected=set()
    for c in ('C1','C2'):
        best=min((r for r in coarse if r['controller']==c),key=lambda r:(r['error_m'],r['length_m']))['length_m'];i=available.index(best)
        for j in (i-1,i+1):
            if 0<=j<len(available):selected.add(round((best+available[j])/2,9))
        expected=min((r for r in summary['rows'] if r.get('controller')==c),key=lambda r:(r['error_m'],r['length_m']))
        if summary['best'][c]!=expected:raise ValueError('Controller incumbent mismatch')
    if read(root/'refinement.json')['selected']!=sorted(selected-set(frozen['lengths']))[:4]:raise ValueError('Refinement rule mismatch')
    ledger=read(root/'budget.json');used={k:sum(r['kind']==k for r in ledger['attempts']) for k in ledger['limits']}
    if any(used[k]>limit for k,limit in ledger['limits'].items()) or len(pairs)>14:raise ValueError('Budget exceeded')
    for row in ledger['attempts']:
        if row['status']=='completed':
            normalized=row['artifact'].replace('\\','/')
            relative=normalized.split('/runs/round4/',1)[1]
            if file_hash(root/relative)!=row['sha256']:raise ValueError('Budget result binding mismatch')
    return dict(status='PASS',raw_files=len(manifest['files']),canonical_results_checked=len(checked),complete_pairs=len(pairs),
        source_files_verified=len(frozen['execution_sources']),used=used,full_regressions=0,
        observation_invariance='saved tip matches final numerical result; viewer tests forbid mj_step/mj_forward; raw file hashes unchanged',
        checked=checked)


def derive(root=OUT):
    root=Path(root);derived=root/'derived';derived.mkdir(parents=True,exist_ok=True)
    summary=read(root/'length_summary.json')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure=Figure(figsize=(10,5));FigureCanvasAgg(figure);axis=figure.subplots()
    for c in ('C1','C2'):
        rows=sorted([r for r in summary['rows'] if r.get('controller')==c and r.get('error_m') is not None],key=lambda r:r['length_m'])
        axis.plot([r['length_m'] for r in rows],[r['error_m'] for r in rows],'-o',label=c+' actual final error')
    axis.plot([r['length_m'] for r in rows],[r['model_error_m'] for r in rows],'--s',label='PCC geometric prediction (initial plan)')
    axis.axhline(.01,color='gray',ls=':',label='Frozen task tolerance')
    rejected=[r['length_m'] for r in summary['rows'] if r['status']=='GEOMETRY_REJECTED']
    axis.scatter(rejected,[0]*len(rejected),marker='x',color='red',label='Necessary geometry rejected (no simulated error)')
    axis.set(xlabel='Length (m)',ylabel='Euclidean position error (m)',xlim=(.04,.81),
        title='One finite length comparison | lines connect sampled points only')
    axis.legend(fontsize=8);axis.grid(alpha=.2);figure.tight_layout();figure.savefig(derived/'length_errors.png',dpi=140)
    with (derived/'candidates.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['length_m','stage','controller','status','error_m','model_error_m','task_success','run','reason']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(summary['rows'])


def package(root=OUT):
    root=Path(root);target=ROOT/'docs/evidence/round4';target.mkdir(parents=True,exist_ok=True)
    import shutil
    for name in ('length_summary.json','development_summary.json','historical_failure_audit.json','budget.json','test_record.json','raw_manifest.json'):
        shutil.copyfile(root/name,target/name)
    report=read(root/'derived/audit.json');atomic_json(target/'audit.json',report)
    for name in ('length_errors.png','candidates.csv','window_interaction.png','matlab_decay.gif','same_input.gif','control_pair.gif','same_input.png','window_check.json','gif_decode_check.json','gif_playback_check.json'):
        if (root/'derived'/name).exists():shutil.copyfile(root/'derived'/name,target/name)
    with tarfile.open(target/'raw_evidence.tar.xz','w:xz') as archive:
        for name in read(root/'raw_manifest.json')['files']:archive.add(root/name,arcname='round4/'+name)
        archive.add(root/'raw_manifest.json',arcname='round4/raw_manifest.json')
    return target
