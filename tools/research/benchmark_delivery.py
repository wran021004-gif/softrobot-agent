"""Export original accepted B-line fixed-tension executions to local ignored files."""
import argparse, csv, hashlib, json, math, os, re, shutil, sqlite3, subprocess, sys
from pathlib import Path
import numpy as np
import mujoco
from tools.state_io import digest
from tools.research.physical_replay import schedule_identity

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT.parent
DEFAULT_OUTPUT = ROOT / 'runs' / 'b_line_delivery'

def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def save(p, obj): Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def artifact(db, ref):
    blob = db.execute('select body from artifacts where id=?',(ref['artifact_id'],)).fetchone()
    if blob is None or hashlib.sha256(blob[0]).hexdigest()!=ref['artifact_id']: raise ValueError('missing or changed artifact '+ref['artifact_id'])
    return json.loads(blob[0])
def safe(s): return re.sub(r'[^a-zA-Z0-9_.-]+','_',str(s)).strip('_')
def write_csv(path, rows):
    with path.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def export_one(out, cfg, tr, raw, acc, xml, source, identity):
    from schemas.platform import SessionInput
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    inp=SessionInput.model_validate(cfg); physics=physics_for(inp)
    if physics['identity']!=raw['model_identity']:
        raise ValueError('frozen physical model does not match execution')
    try: scene=assemble(inp,physics)
    except ValueError as exc:
        if 'RESEARCH_TASK_ADAPTER_REQUIRED' not in str(exc): raise
        scene=None  # Older branches can have task adapters absent from this checkout.
    if scene is not None and (scene['identity']!=raw['scene_identity'] or scene['forces']!=raw['external_force_execution']['forces']):
        raise ValueError('frozen scene or forces do not match execution')
    names=tr['tendon_order']; u=np.asarray(tr['tensions_n'],float); times=np.asarray(tr['times_s'],float)
    samples=raw['samples']; dt=raw['physics_timestep_s']
    if not acc.get('accepted') or raw['status']!='completed' or not all(v.get('passed') for v in acc['components'].values()): raise ValueError('acceptance or completion failed')
    if len(times)!=len(u)+1 or len(samples)!=len(times) or u.shape!=(len(times)-1,len(names)) or not np.isfinite(u).all() or not np.isfinite(times).all() or np.any(np.diff(times)<=0): raise ValueError('invalid control grid')
    if raw['tendon_order']!=names or sha(xml)!=raw['xml_sha256']: raise ValueError('tendon order or XML hash mismatch')
    model=mujoco.MjModel.from_xml_path(str(xml)); aids=[model.actuator(n+'_direct_tension').id for n in names]
    joints=[model.joint(n).id for n in physics['dofs']]
    if list(model.jnt_qposadr[joints])!=list(range(model.nq)) or list(model.jnt_dofadr[joints])!=list(range(model.nv)):
        raise ValueError('joint ordering is not the full XML state ordering')
    tids=[model.tendon(n).id for n in names]
    if list(model.actuator_trnid[aids,0])!=tids or np.any(model.actuator_gainprm[aids,0]!=-1) or np.any(model.actuator_dyntype[aids]!=mujoco.mjtDyn.mjDYN_NONE): raise ValueError('actuator mapping mismatch')
    limits=model.actuator_ctrlrange[aids]
    if np.any(u<limits[:,0]) or np.any(u>limits[:,1]) or abs(dt-model.opt.timestep)>1e-15: raise ValueError('bounds or timestep mismatch')
    if raw['physics_steps']!=round((times[-1]-times[0])/dt) or abs(times[0])>1e-12: raise ValueError('incomplete physical steps')
    if any(abs(s['time_s']-t)>1e-10 for s,t in zip(samples,times)): raise ValueError('sample timing mismatch')
    for i,s in enumerate(samples[1:]):
        if s['requested_tension_n']!=tr['tensions_n'][i] or not np.allclose(s['actual_tension_n'],u[i],rtol=0,atol=1e-9): raise ValueError('applied or requested tension mismatch')
    if len(samples[0]['qpos_rad'])!=model.nq or len(samples[0]['qvel_rad_s'])!=model.nv: raise ValueError('initial state mapping ambiguous')
    taskid=cfg['task']['task_id']; bench=next((x.upper() for x in re.findall(r'(?i)\b(bf\d+|b[123])',taskid+' '+identity)), 'UNKNOWN')
    condition=next((x for x in ('positive_high','negative_low','central_high','positive','negative','zero','plus_y','minus_y','up_z','force') if x in taskid.lower()),safe(taskid))
    dest=out/bench/safe(condition)/safe(identity); dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(xml,dest/'robot.xml');shutil.copyfile(ROOT/'tools/research/delivery_replay.py',dest/'replay.py')
    control=[]; applied=[]
    for i,row in enumerate(u):
        base=dict(step=i,time_start_s=float(times[i]),time_end_s=float(times[i+1]),dt_s=float(times[i+1]-times[i]))
        control.append({**base,**{n+'_N':float(v) for n,v in zip(names,row)}})
        applied.append({**base,**{n+'_N':v for n,v in zip(names,samples[i+1]['actual_tension_n'])}})
    write_csv(dest/'control.csv',control);write_csv(dest/'applied_tension.csv',applied)
    with (dest/'control.csv').open(encoding='utf8',newline='') as f:
        check=list(csv.DictReader(f))
    if any(float(r[n+'_N']) != tr['tensions_n'][i][j] for i,r in enumerate(check) for j,n in enumerate(names)):
        raise ValueError('CSV changed control values')
    state=[]
    for s in samples:
        row=dict(time_s=s['time_s'],engine_time_s=s['engine_time_s'])
        for key,labels in [('tip_m',['tip_x_m','tip_y_m','tip_z_m']),('tip_velocity_m_s',['tip_vx_m_s','tip_vy_m_s','tip_vz_m_s']),('tip_tool_axis_world',['axis_x','axis_y','axis_z'])]:
            if key in s:row.update(zip(labels,s[key]))
        row['speed_m_s']=s['speed_m_s']
        for key in ('qpos_rad','qvel_rad_s','actual_tension_n'):
            row.update({f'{key}_{i}':v for i,v in enumerate(s[key])})
        state.append(row)
    write_csv(dest/'states.csv',state)
    save(dest/'task.json',cfg['task']);save(dest/'parameters.json',{'robot':cfg['robot'],'policy':cfg['policy'],'seed':cfg['seed']})
    save(dest/'external_forces.json',raw['external_force_execution'])
    save(dest/'acceptance.json',acc)
    manifest=dict(benchmark=bench,condition=condition,witness=identity,source=source,task_id=taskid,
        physical_model_identity=raw['model_identity'],scene_identity=raw['scene_identity'],design_identity=tr['design_identity'],execution_model_identity=tr['model_identity'],
        original_xml_sha256=raw['xml_sha256'],scene_recomputed=scene is not None,tendon_order=names,actuators=[n+'_direct_tension' for n in names],
        initial_state={'qpos':samples[0]['qpos_rad'],'qvel':samples[0]['qvel_rad_s']}, seed=cfg['seed'],
        timing={'physical_timestep_s':dt,'duration_s':float(times[-1]),'control_intervals':len(u)},
        semantics='Ideal tendon tension in N, zero-order hold. State sample 0 is initial; later tensions refer to the preceding interval.',
        evidence_acceptance='Original independent acceptance; engineering replay does not create a new acceptance.',
        files={})
    (dest/'hardware_notes.md').write_text('仿真采用理想肌腱张力，单位 N；正值表示拉力。通道顺序和驱动器映射见 manifest.json。串联 hinge 是连续体软臂的离散近似，不代表真机机械铰链。尚无电机映射、张力闭环、行程限制和标定，不能将张力直接当作 PWM、位置、脉冲或收缩量使用。\n',encoding='utf8')
    goal=json.dumps(cfg['task']['goal']['data'],ensure_ascii=False)
    (dest/'README.md').write_text(f"# {bench} / {condition}\n\n任务：{cfg['task'].get('name',taskid)}。目标及世界坐标（SI）：`{goal}`。完整冻结任务见 task.json；原始验收及指标见 acceptance.json。\n\n在此目录运行：`python replay.py`；无界面核对：`python replay.py --headless`；调速：`python replay.py --speed 0.5`；循环：`python replay.py --repeat`；显示原始采样轨迹：`python replay.py --show-recorded-path`。需要安装 MuJoCo 和 NumPy。空格暂停或继续，鼠标调整视角，窗口关闭前保持末态。\n\nXML 是哈希匹配的原执行模型，控制使用每行对应区间的零阶保持。外力为世界系、作用于指定刚体质心，按物理步区间施加。蓝点表示原始采样轨迹，绿点表示任务目标或路径顶点。\n",encoding='utf8')
    manifest['files']={p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name!='manifest.json'}
    save(dest/'manifest.json',manifest)
    return dict(benchmark=bench,condition=condition,witness=identity,task=taskid,model=raw['model_identity'],design=tr['design_identity'],execution=source.get('execution_id'),control_source=str(source.get('control',source.get('archive'))),acceptance='accepted',duration=times[-1],timestep=dt,control_period_s=times[1]-times[0] if np.allclose(np.diff(times),times[1]-times[0],rtol=0,atol=1e-12) else 'irregular',channels=len(names),path=str(dest))

def store_cases(root, output):
    for w in root.iterdir():
        if not w.is_dir() or not re.match(r'(?i)^(b[123]|bf)',w.name):continue
        for d,_,files in os.walk(w/'runs'):
            if 'platform.sqlite' not in files:continue
            p=Path(d)/'platform.sqlite'
            try:
                db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
                for aid,body in db.execute("select id,body from artifacts where media='application/json' and cast(body as text) like '%\"accepted\":true%'"):
                    try: x=json.loads(body)
                    except (ValueError,TypeError):continue
                    if not isinstance(x,dict) or not isinstance(x.get('acceptance'),dict) or x['acceptance'].get('accepted') is not True or not x.get('raw_reference') or not x.get('execution_id'):continue
                    folder=Path(d)/'physical_replay'/x['execution_id']
                    try:
                        ctrl=artifact(db,x['source_reference']); candidate=artifact(db,x['candidate'])
                        raw=artifact(db,x['raw_reference'])
                        if (folder/'request.json').exists():
                            request=read(folder/'request.json'); original=read(folder/'result.json'); xml=folder/'robot.xml'
                            if any(raw.get(k)!=original.get(k) for k in ('samples','xml_sha256','physics_steps','model_identity')):raise ValueError('raw artifact differs from execution')
                            if ctrl['trajectory']!=request['trajectory'] or candidate['configuration']!=request['configuration']:raise ValueError('candidate or control binding mismatch')
                            if request['candidate']!=x['candidate'] or request['source_reference']!=x['source_reference']:raise ValueError('request binding mismatch')
                        else:
                            # Rebuild only from the immutable candidate and verify the original byte hash.
                            from tools.research.physical_replay import model_context
                            from extensions.tendon_family.mjcf import compile_xml
                            from tools.platform_registry import registry
                            inp,physics,scene,_=model_context(candidate['configuration'])
                            if physics['identity']!=raw['model_identity']:raise ValueError('reconstructed model identity mismatch')
                            xml=output/('_reconstructed_'+x['execution_id']+'.xml')
                            compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),xml)
                            if sha(xml)!=raw['xml_sha256']:raise ValueError('reconstructed XML hash mismatch')
                            original=dict(raw)
                            original.setdefault('external_force_execution',dict(forces=scene['forces'],semantics=scene['semantics'].get('external_forces')))
                            request=dict(configuration=candidate['configuration'],trajectory=ctrl['trajectory'])
                        artifact(db,x['evaluation_reference'])
                        profile_ref=x.get('profile_reference'); actual_id=x['acceptance']['execution_id']
                        if profile_ref:
                            artifact(db,profile_ref)
                            if actual_id!=x['execution_id']:raise ValueError('execution binding mismatch')
                        else:
                            # Older replay stored request_id in its execution_id field.
                            call=db.execute('select execution_id,receipt from calls where run_id=? and request_id=?',(x['owning_study'],x['execution_id'])).fetchone()
                            if not call or call[0]!=actual_id or x['profile'].get('execution_id')!=actual_id or json.loads(call[1])['output']['artifact_id']!=aid or x['acceptance']['evidence_binding']['profile_binding']['simulation']!=x['raw_reference']:
                                raise ValueError('legacy request-to-execution receipt binding mismatch')
                        yield request['configuration'],request['trajectory'],original,x['acceptance'],xml,dict(store=str(p),replay_artifact=aid,execution_id=actual_id,legacy_replay_id=x['execution_id'] if not profile_ref else None,implementation=x['implementation'],candidate=x['candidate'],control=x['source_reference'],raw=x['raw_reference'],evaluation=x['evaluation_reference'],profile=profile_ref,profile_inline=not bool(profile_ref),study=x['owning_study'],xml_reconstructed=not (folder/'request.json').exists()),x['owning_study']+'_'+actual_id,None
                    except Exception as e:yield None,None,None,None,None,dict(store=str(p),execution_id=x.get('execution_id')),x.get('owning_study','unknown'),str(e)
                db.close()
            except (sqlite3.Error,OSError):continue

def standalone_cases(root):
    for w in root.iterdir():
        if not w.is_dir() or not re.match(r'(?i)^(b[123]|bf)',w.name):continue
        for d,_,files in os.walk(w/'runs'):
            if not {'acceptance.json','raw.json','robot.xml'}.issubset(files):continue
            folder=Path(d); parent=folder.parent
            if not (parent/'configuration.json').exists() or not (parent/'control.json').exists():continue
            try:
                a=read(folder/'acceptance.json');acc=a['acceptance']
                if not acc.get('accepted'):continue
                cfg=read(parent/'configuration.json');ctrl=read(parent/'control.json');raw=read(folder/'raw.json')
                if digest(cfg)!=a['configuration_identity'] or schedule_identity(cfg,ctrl['trajectory'])!=a['control_identity'] or digest(cfg['task'])!=a['task_identity']:raise ValueError('standalone content binding mismatch')
                if digest(raw)!=a['raw_reference']['artifact_id']:raise ValueError('standalone raw identity mismatch')
                yield cfg,ctrl['trajectory'],raw,acc,folder/'robot.xml',dict(archive=str(parent),execution_id=acc.get('execution_id'),bindings=a),safe(str(parent.relative_to(w/'runs'))),None
            except Exception as e:yield None,None,None,None,None,dict(archive=str(parent)),safe(parent.name),str(e)

def b1_archived_cases(root):
    w=root/'b1-math-guided-benchmark-discovery'; evidence=w/'evidence/b1_math_guided_benchmark_discovery'
    if not evidence.exists(): return
    for summary in evidence.glob('*_independent.json'):
        doc=read(summary)
        for condition,v in doc.get('results',{}).items():
            if not v.get('acceptance',{}).get('accepted'): continue
            label=summary.name.removesuffix('_independent.json'); detail=evidence/(label+'_'+condition+'.json')
            folder=w/'runs/b1_math_guided_benchmark_discovery'/('replay_'+label+'_'+condition)
            try:
                data=read(detail); cfg=data['configuration']; tr=data['schedule']['trajectory']; raw=v['raw']; acc=v['acceptance']
                if digest(raw)!=v['evaluation']['source']['artifact_id'] or acc['task_identity']!=digest(cfg['task']) or v['profile']['task']!=cfg['task']:
                    raise ValueError('B1 archived evidence binding mismatch')
                if read(folder/'samples.json')!=raw['samples']: raise ValueError('B1 execution samples differ from archive')
                raw=dict(raw,external_force_execution=dict(forces=[],semantics=None))
                yield cfg,tr,raw,acc,folder/'robot.xml',dict(archive=str(summary),control=str(detail),execution_id=None,execution_label=str(folder),note='Original fixed-program execution has no execution ID; no ID invented.'),'B1_'+label+'_'+condition,None
            except Exception as e:yield None,None,None,None,None,dict(archive=str(summary),execution_label=str(folder)),label+'_'+condition,str(e)

def b2_archived_cases(root):
    w=root/'b2-load-force-runtime'; runs=w/'runs'
    if not runs.exists(): return
    for acceptance_file in runs.glob('b2-hidden-*/*-acceptance.json'):
        a=read(acceptance_file); acc=a.get('acceptance',{})
        if not acc.get('accepted'): continue
        base=str(acceptance_file).removesuffix('-acceptance.json'); folder=Path(base)
        try:
            raw=read(base+'-raw.json')
            if 'configuration' in a:
                cfg=a['configuration']; tr=read(base+'-schedule.json')['trajectory']; control_path=base+'-schedule.json'
            else:
                cfg=read(base+'-configuration.json'); search=read(base+'-search.json'); tr=search['native_dynamics']['optimized_schedule']['trajectory']; control_path=base+'-search.json'
            if digest(raw)!=a['evaluation']['source']['artifact_id'] or acc['task_identity']!=digest(cfg['task']) or a['profile']['task']!=cfg['task']:
                raise ValueError('B2 archived evidence binding mismatch')
            if read(folder/'samples.json')!=raw['samples']: raise ValueError('B2 execution samples differ from archive')
            yield cfg,tr,raw,acc,folder/'robot.xml',dict(archive=str(acceptance_file),control=control_path,execution_id=acc.get('execution_id'),configuration='embedded in acceptance' if 'configuration' in a else base+'-configuration.json',raw=base+'-raw.json'),'B2_'+folder.parent.name+'_'+folder.name,None
        except Exception as e:yield None,None,None,None,None,dict(archive=str(acceptance_file)),folder.name,str(e)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['export','list','view']);p.add_argument('--source',type=Path,default=DEFAULT_SOURCE);p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);p.add_argument('--task');p.add_argument('--condition');p.add_argument('--witness');p.add_argument('--headless',action='store_true');p.add_argument('--speed',type=float,default=1);p.add_argument('--repeat',action='store_true');p.add_argument('--show-recorded-path',action='store_true');a=p.parse_args()
    if a.command=='list':
        print((a.output/'index.csv').read_text(encoding='utf8') if (a.output/'index.csv').exists() else 'No export yet');return
    if a.command=='view':
        with (a.output/'index.csv').open(encoding='utf8',newline='') as f: rows=list(csv.DictReader(f))
        rows=[r for r in rows if (not a.task or r['benchmark'].lower()==a.task.lower()) and (not a.condition or r['condition']==a.condition) and (not a.witness or a.witness in r['witness'])]
        if len(rows)!=1: raise SystemExit('Selection must identify one witness; run list and pass --task, --condition and --witness as needed.')
        cmd=[sys.executable,str(Path(rows[0]['path'])/'replay.py'),'--speed',str(a.speed)]
        for key in ('headless','repeat','show_recorded_path'):
            if getattr(a,key):cmd.append('--'+key.replace('_','-'))
        raise SystemExit(subprocess.call(cmd))
    a.output.mkdir(parents=True,exist_ok=True); successes=[]; failures=[]; seen=set()
    for cfg,tr,raw,acc,xml,source,identity,error in list(store_cases(a.source,a.output))+list(standalone_cases(a.source))+list(b1_archived_cases(a.source))+list(b2_archived_cases(a.source)):
        if error:failures.append(dict(source=source,error=error));continue
        try:
            key=(raw['xml_sha256'],digest(tr),digest(acc))
            if key in seen:continue
            seen.add(key); successes.append(export_one(a.output,cfg,tr,raw,acc,xml,source,identity))
        except Exception as e:failures.append(dict(source=source,error=str(e)))
    if successes:write_csv(a.output/'index.csv',successes)
    save(a.output/'audit_failures.json',failures)
    print(json.dumps({'exported':len(successes),'failures':len(failures),'output':str(a.output)},ensure_ascii=False))
if __name__=='__main__':main()


