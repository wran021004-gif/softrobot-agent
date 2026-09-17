"""Reproducible family candidates and three budgeted public-platform solves."""
import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def example_design():
    from extensions.tendon_family.contracts import Design
    def attach(part='fixed_base',s=0.,pos=(0.,0.,0.)):
        return dict(part=part,s=s,position_m=list(pos))
    components=[dict(id='near',kind='flexible_segment',length_m=.16,cells=3,
        sections=[dict(s=0.,section=dict(kind='ellipse',parameters=dict(semi_y_m=.010,semi_z_m=.008),angle_rad=.35))],
        physics=dict(mode='material',density_kg_m3=1100.,young_pa=8e6,bending_viscosity_nm2_s=[.0005,.0007])),
        dict(id='mid_guide',kind='guide',connection=attach('near',1.),mass_kg=.002,com_local_m=[0.,0.,0.],
            inertia_com_local_kg_m2=[[4e-7,0.,0.],[0.,2e-7,0.],[0.,0.,2e-7]],envelope_halfsize_m=[.002,.025,.025],
            guide_holes={},hole_radius_m=.0015),
        dict(id='connector',kind='rigid_connector',connection=attach('mid_guide',pos=(.002,0.,0.)),mass_kg=.003,
            com_local_m=[.006,0.,0.],inertia_com_local_kg_m2=[[5e-8,0.,0.],[0.,7e-8,0.],[0.,0.,7e-8]],envelope_halfsize_m=[.006,.006,.006]),
        dict(id='far',kind='flexible_segment',connection=attach('connector',pos=(.012,0.,0.)),length_m=.12,cells=2,
            sections=[dict(s=0.,section=dict(kind='rectangle',parameters=dict(width_y_m=.014,height_z_m=.010),angle_rad=-.25)),
                      dict(s=1.,section=dict(kind='rectangle',parameters=dict(width_y_m=.012,height_z_m=.009),angle_rad=.15))],
            interpolation='linear',physics=dict(mode='material',density_kg_m3=1050.,young_pa=6e6,bending_viscosity_nm2_s=[.0003,.0004])),
        dict(id='payload',kind='payload',connection=attach('far',1.),mass_kg=.010,com_local_m=[.007,.001,-.002],
            inertia_com_local_kg_m2=[[6e-7,1e-7,0.],[1e-7,8e-7,1e-7],[0.,1e-7,9e-7]],envelope_halfsize_m=[.009,.009,.008])]
    tendons=[]; actuators=[]
    for group,angles,radius in [('near',[.2,2.2,4.4],.018),('far',[.7,2.8,4.8],.022)]:
        for i,angle in enumerate(angles):
            y,z=radius*math.cos(angle),radius*math.sin(angle); name=f'{group}_t{i}'; hole=f'{group}_h{i}'
            components[1]['guide_holes'][hole]=[0.,y,z]
            points=[dict(attachment=attach(pos=(0.,y,z)),role='start'),
                dict(attachment=attach('near',.5,pos=(0.,y*1.03,z*.97)),role='guide'),
                dict(attachment=attach('mid_guide'),hole=hole,role='anchor' if group=='near' else 'guide')]
            if group=='far': points += [dict(attachment=attach('far',.5,pos=(0.,y*.8,z*.8)),role='guide'),
                dict(attachment=attach('far',1.,pos=(0.,y*.7,z*.7)),role='anchor')]
            tendons.append(dict(id=name,points=points,diameter_m=.001,length_servo_gain_n_m=900.,pretension_n=.2,force_limit_n=8.))
            actuators.append(dict(id=group+f'_motor{i}',transmission=[dict(tendon=name,ratio=1.)],limits=[-.015,.015],velocity_limit=.025))
    return Design.model_validate(dict(id='two_segment_development',components=components,tendons=tendons,actuators=actuators,tip=attach('payload',pos=(.014,0.,0.))))


def design_space(design):
    from extensions.tendon_family.contracts import Space
    changed=design.model_dump(mode='json'); changed['id']='tube_distal_three_cells'
    far=next(c for c in changed['components'] if c['id']=='far')
    far.update(cells=3,sections=[dict(s=0.,section=dict(kind='tube',parameters=dict(outer_radius_m=.008,inner_radius_m=.004),angle_rad=.2))],interpolation='step')
    return Space.model_validate(dict(parameters={
        'components/near/length_m':dict(type='number',bounds=[.14,.20]),
        'components/near/cells':dict(type='integer',bounds=[2,6]),
        'components/near/interpolation':dict(type='choice',options=['step','linear']),
        'components/far/sections/0/section/parameters/inner_radius_m':dict(type='number',bounds=[.002,.006],when={'components/far/sections/0/section/kind':'tube'})},
        templates={'tube_distal':changed}))


def session(backend,design,space,legacy=False):
    from examples.platform_spatial_example import session_input
    from examples.platform_fixtures import binding,payload,budget
    value=session_input('math_spatial'); duration=.04 if legacy else .35
    value['run_id']='family-'+('single' if legacy else backend)
    value['task'].update(task_id='family-single-dev' if legacy else 'family-multisegment-dev',name='串联多段软臂独立开发验证',
        source='本轮开发任务；固定目标、容差与评分；不覆盖历史任务',actuator_channels=['actuator_commands'],
        robot_families=['tendon_driven_continuum' if legacy else 'tendon_robot_family'],
        initializer=binding('initialize.family','family.initial',{}),
        goal=payload('reference.reach_goal',dict(target_m=[.29,.035,.19])),
        timing=dict(timestep_s=.0005,control_period_s=.01,sample_period_s=.01,duration_s=duration,termination=['duration','numerical_failure']),
        sampling=dict(split='development',seeds=[17],window_s=[0.,duration]))
    assembly=value['task']['environment']['data']; assembly['mount']=dict(position_m=[0.,0.,.15],quaternion_wxyz=[1.,0.,0.,0.])
    assembly['external_forces']=[] if legacy else [dict(entity='payload',force_n=[0.,.03,.02],start_s=.12,end_s=.20)]
    value['robot']['channels']=['actuator_commands']
    if not legacy:
        value['robot'].update(family='tendon_robot_family',structure=payload('family.design',design.model_dump(mode='json')),
            assumptions=['Serial double-bending cells, separate structure/discretization, SI'],sources=['examples/platform_tendon_family.py'])
    control=dict(mode='tip_feedback',feedback_gain=5.,damping=.015,max_joint_update_rad=.025)
    if legacy: control=dict(mode='deterministic',commands={'tendon_0_actuator':-.001,'tendon_1_actuator':-.0006},ramp_s=.04)
    value['policy'].update(editable={},backend=binding('backend.'+backend,'family.parameters',dict(model='matlab_serial_bending_v1' if backend=='matlab_spatial' else 'mujoco_serial_bending_v1')),
        controller=binding('controller.family','family.control',control),
        candidate_builder=binding('candidate.controller','platform.empty') if legacy else binding('candidate.family','family.space',space.model_dump(mode='json')),
        budget=budget(tool_calls=12,backend_solves=1,wall_s=900.),timeout_s=700.)
    value['policy']['tool_bindings'].update({'design.family_build':'1.0.0','visualization.saved_replay':'1.0.0'})
    return value


def prepare(root):
    from examples.platform_fixtures import project,budget
    from tools.state_io import atomic_json
    root=Path(root).resolve(); directory=root/'inputs'; directory.mkdir(parents=True,exist_ok=False)
    d=example_design(); space=design_space(d)
    atomic_json(directory/'design.json',d.model_dump(mode='json')); atomic_json(directory/'space.json',space.model_dump(mode='json'))
    for backend in ('matlab_spatial','family_mujoco'):
        atomic_json(directory/(backend+'.json'),session(backend,d,space))
    atomic_json(directory/'single.json',session('matlab_spatial',d,space,True))
    p=project(); p.update(authorization_source='本轮用户授权 MATLAB 空间与绳驱家族贯通；3 次目标求解，最多4次常规求解',budget=budget(tool_calls=50,backend_solves=4,wall_s=3600.))
    atomic_json(directory/'project.json',p)
    return dict(inputs=str(directory),baseline=d.id)


def build_candidates(root):
    import time
    from extensions.tendon_family.candidate import build
    from extensions.tendon_family.compiler import resolve
    from extensions.tendon_family.mjcf import compile_xml
    from extensions.tendon_family.scene import assemble
    from schemas.platform import SessionInput
    from tools.platform_tasks import compile_input
    from tools.state_io import atomic_json
    root=Path(root); read=lambda n:json.loads((root/'inputs'/n).read_text(encoding='utf8'))
    start=time.perf_counter(); result={}
    for name,changes in [('continuous',{'components/near/length_m':.17}),('structural',{'template':'tube_distal'})]:
        built=build(dict(baseline=read('design.json'),space=read('space.json'),changes=changes))
        if built.status!='valid': raise ValueError(built.reason)
        atomic_json(root/(name+'_candidate.json'),built.model_dump(mode='json'))
        for backend in ('matlab_spatial','family_mujoco'):
            inp=read(backend+'.json'); inp['robot']['structure']['data']=built.candidate.model_dump(mode='json')
            compile_input(inp)
            value=SessionInput.model_validate(inp); scene=assemble(value,built.resolved_physics)
            atomic_json(root/(name+'_'+backend+'_input.json'),dict(physics=built.resolved_physics,scene=scene))
            if backend=='family_mujoco':
                import mujoco
                path=root/(name+'.xml'); compile_xml(built.resolved_physics,scene,None,path)
                model=mujoco.MjModel.from_xml_path(str(path))
                result[name]=dict(dofs=model.nv,tendons=model.ntendon,actuators=len(built.candidate.actuators),mass_kg=sum(x['mass_kg'] for x in built.resolved_physics['parts']))
    result['prepare_compile_s']=time.perf_counter()-start
    atomic_json(root/'candidate_checks.json',result); return result


def run(root,backend,label=''):
    from tools.platform_store import Store
    from tools.platform_host import Host
    from tools.state_io import atomic_json
    from extensions.tendon_family.saved import materialize
    root=Path(root).resolve(); read=lambda n:json.loads((root/'inputs'/n).read_text(encoding='utf8'))
    store=Store(root)
    if not store.db.exists(): store.create(read('project.json'))
    inp=read(backend+'.json')
    suffix='_'+label if label else ''
    inp['run_id']+=suffix
    host=Host(root,inp['run_id']); host.create(inp)
    record=dict(backend=backend,run_id=inp['run_id'],receipts={})
    def invoke(name,tool,args):
        r=host.invoke(dict(request_id='family-'+name,tool_id=tool,tool_version=inp['policy']['tool_bindings'][tool],arguments=args,cache='new',reason='本轮授权的真实求解或保存结果读取'))
        record['receipts'][name]=r; atomic_json(root/(backend+suffix+'_record.json'),record)
        if r['execution_status']!='completed': raise RuntimeError(str(r))
        return r
    sim=invoke('simulation','simulation.run',dict(candidate_id='legacy-single' if backend=='single' else 'continuous',changes={} if backend=='single' else {'components/near/length_m':.17}))
    if sim['solver_status']!='completed': raise RuntimeError('Solver failed; partial evidence retained')
    ev=invoke('evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    invoke('tip','signals.read',dict(result=sim['output'],name='tip_position',entity='tip'))
    invoke('tension','signals.read',dict(result=sim['output'],name='tendon_tension',entity='tendon_0' if backend=='single' else 'far_t0'))
    record['evaluation']=store.artifact(ev['output']); record['usage']=store.remaining(host.run_id)['used']
    record['result_data']=store.artifact(sim['output'])['data']['data']
    record['saved_folder']=str(materialize(root,record,root/'saved'/(backend+suffix)))
    atomic_json(root/(backend+suffix+'_record.json'),record); return record


def compare(root):
    import numpy as np
    from tools.state_io import atomic_json
    root=Path(root); records=[json.loads((root/(b+'_record.json')).read_text(encoding='utf8')) for b in ('matlab_spatial','family_mujoco')]
    for key in ('physics_identity','scene_identity'):
        assert records[0]['result_data'][key]==records[1]['result_data'][key]
    rows=[json.loads((Path(r['saved_folder'])/'replay_trajectory.json').read_text(encoding='utf8')) for r in records]
    np.testing.assert_allclose([r['time_s'] for r in rows[0]],[r['time_s'] for r in rows[1]],rtol=0,atol=1e-12)
    tips=[np.array([r['tip_m'] for r in rs]) for rs in rows]
    lengths=[np.array([r['tendon_length_m'] for r in rs]) for rs in rows]
    tensions=[np.array([r['tension_n'] for r in rs]) for rs in rows]
    out=dict(meaning='Independent backends, shared physical entities and sample clocks; no ground-truth or calibration claim',
        tip_final_difference_m=float(np.linalg.norm(tips[0][-1]-tips[1][-1])),tip_rms_difference_m=float(np.sqrt(np.mean(np.sum((tips[0]-tips[1])**2,axis=1)))),
        length_max_difference_m=float(np.max(np.abs(lengths[0]-lengths[1]))),tension_max_difference_n=float(np.max(np.abs(tensions[0]-tensions[1]))),
        records=[dict(backend=r['backend'],timings=r['result_data']['timings_s'],evaluation=r['evaluation'],usage=r['usage']) for r in records],
        extra_backend_solves=0)
    atomic_json(root/'comparison.json',out); return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('action',choices=['prepare','build','run','compare','view'])
    parser.add_argument('root',type=Path); parser.add_argument('--backend',choices=['single','matlab_spatial','family_mujoco'],default='matlab_spatial')
    parser.add_argument('--label',default='',help='Explicit distinct invocation label after a diagnosed failure; never auto-retry')
    args=parser.parse_args(argv)
    if args.action=='run': out=run(args.root,args.backend,args.label)
    elif args.action=='view':
        from extensions.tendon_family.saved import view
        suffix='_'+args.label if args.label else ''
        out=view(args.root/'saved'/(args.backend+suffix),'mujoco' if args.backend=='family_mujoco' else 'matlab')
    else: out=globals()[{'build':'build_candidates'}.get(args.action,args.action)](args.root)
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf8')
    main()
