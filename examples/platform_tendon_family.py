"""Reproducible family candidates and three budgeted public-platform solves."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def example_design():
    from extensions.tendon_family.contracts import Design
    def attach(part='fixed_base',s=0.,pos=(0.,0.,0.)):
        return dict(part=part,s=s,position_m=list(pos))
    components=[dict(id='near',kind='flexible_segment',length_m=.16,
        sections=[dict(s=0.,section=dict(kind='ellipse',parameters=dict(semi_y_m=.010,semi_z_m=.008),angle_rad=.35))],
        physics=dict(mode='material',density_kg_m3=1100.,young_pa=8e6,bending_viscosity_nm2_s=[.0005,.0007])),
        dict(id='mid_guide',kind='guide',connection=attach('near',1.),mass_kg=.002,com_local_m=[0.,0.,0.],
            inertia_com_local_kg_m2=[[4e-7,0.,0.],[0.,2e-7,0.],[0.,0.,2e-7]],envelope_halfsize_m=[.002,.025,.025],
            guide_holes={},hole_radius_m=.0015),
        dict(id='connector',kind='rigid_connector',connection=attach('mid_guide',pos=(.002,0.,0.)),mass_kg=.003,
            com_local_m=[.006,0.,0.],inertia_com_local_kg_m2=[[5e-8,0.,0.],[0.,7e-8,0.],[0.,0.,7e-8]],envelope_halfsize_m=[.006,.006,.006]),
        dict(id='far',kind='flexible_segment',connection=attach('connector',pos=(.012,0.,0.)),length_m=.12,
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


def example_discretization():
    from extensions.tendon_family.contracts import Discretization
    return Discretization(cells={'near':3,'far':2})


def design_space(design):
    from extensions.tendon_family.contracts import Space
    changed=design.model_dump(mode='json'); changed['id']='tube_distal'
    far=next(c for c in changed['components'] if c['id']=='far')
    far.update(sections=[dict(s=0.,section=dict(kind='tube',parameters=dict(outer_radius_m=.008,inner_radius_m=.004),angle_rad=.2))],interpolation='step')
    return Space.model_validate(dict(parameters={
        'components/near/length_m':dict(type='number',bounds=[.14,.20]),
        'components/near/interpolation':dict(type='choice',options=['step','linear']),
        'components/far/sections/0/section/parameters/inner_radius_m':dict(type='number',bounds=[.002,.006],when={'components/far/sections/0/section/kind':'tube'})},
        templates={'tube_distal':changed},discretization_parameters={
        'discretization/cells/near':dict(type='integer',bounds=[2,6]),
        'discretization/cells/far':dict(type='integer',bounds=[2,6])}))


def session(backend,design,space,legacy=False,discretization=None):
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
    control=dict(mode='tip_feedback',reference=dict(kind='task_goal',commands={},units='m',frame='world'),
        feedback_gain=5.,damping=.015,max_joint_update_rad=.025)
    if legacy: control=dict(mode='deterministic',commands={'tendon_0_actuator':-.001,'tendon_1_actuator':-.0006},ramp_s=.04)
    if legacy:
        backend_binding=binding('backend.'+backend,'family.parameters',dict(model='matlab_serial_bending_v1'))
        dynamics_model=None
    else:
        numerical_contract='family.matlab_parameters' if backend=='matlab_spatial' else 'family.mujoco_parameters'
        backend_binding=binding('backend.'+backend,numerical_contract,{})
        backend_binding['version']='1.1.0'
        dynamics_model=binding('model.serial_bending_cells','family.dynamics_model',{})
    value['policy'].update(editable={},backend=backend_binding,dynamics_model=dynamics_model,
        controller=binding('controller.family','family.control',control),
        discretization=None if legacy else payload('family.discretization',(discretization or example_discretization()).model_dump(mode='json')),
        candidate_builder=binding('candidate.controller','platform.empty') if legacy else binding('candidate.family','family.space',space.model_dump(mode='json')),
        budget=budget(tool_calls=12,backend_solves=1,wall_s=900.),timeout_s=700.)
    value['policy']['tool_bindings'].update({'design.family_build':'1.0.0','visualization.saved_replay':'1.0.0'})
    return value


def prepare(root):
    from examples.platform_fixtures import project,budget
    from tools.state_io import atomic_json
    root=Path(root).resolve(); directory=root/'inputs'; directory.mkdir(parents=True,exist_ok=False)
    d=example_design(); discretization=example_discretization(); space=design_space(d)
    atomic_json(directory/'design.json',d.model_dump(mode='json')); atomic_json(directory/'discretization.json',discretization.model_dump(mode='json'))
    atomic_json(directory/'space.json',space.model_dump(mode='json'))
    for name,changes in CANDIDATES.items():
        atomic_json(directory/(name+'_request.json'),dict(design_file='design.json',space_file='space.json',
            discretization_file='discretization.json',changes=changes))
    configs={backend:session(backend,d,space,discretization=discretization) for backend in ('matlab_spatial','family_mujoco')}
    common=deepcopy(configs['matlab_spatial']); common['run_id_prefix']='family'; del common['run_id']
    common['robot']['structure']['data']={}
    common['policy']['candidate_builder']['parameters']['data']={}
    common['policy']['discretization']['data']={}
    execution=dict(dynamics_model=common['policy'].pop('dynamics_model'),backends={})
    control=common['policy'].pop('controller'); common['policy'].pop('backend')
    for backend,config in configs.items(): execution['backends'][backend]=config['policy']['backend']
    atomic_json(directory/'experiment.json',common)
    atomic_json(directory/'execution.json',execution)
    atomic_json(directory/'control.json',control)
    atomic_json(directory/'single.json',session('matlab_spatial',d,space,True))
    p=project(); p.update(authorization_source='本轮用户授权 MATLAB 空间与绳驱家族贯通；3 次目标求解，最多4次常规求解',budget=budget(tool_calls=50,backend_solves=4,wall_s=3600.))
    atomic_json(directory/'project.json',p)
    return dict(inputs=str(directory),baseline=d.id)


CANDIDATES = {'continuous': {'components/near/length_m':.17},
              'structural': {'template':'tube_distal','discretization/cells/far':3}}


def prepare_candidate(root, candidate, backend):
    from extensions.tendon_family.preparation import prepare_candidate as common_prepare
    return common_prepare(root,candidate,backend,legacy_changes=CANDIDATES[candidate])


def save_selection(root,candidate,backend,prepared, *, rebuild=False):
    from extensions.tendon_family.preparation import save_selection as common_save
    return common_save(root,candidate,backend,prepared,rebuild=rebuild)


def build_candidates(root,candidate=None):
    import time
    from extensions.tendon_family.mjcf import compile_xml
    from tools.platform_tasks import compile_input
    from tools.state_io import atomic_json
    root=Path(root)
    start=time.perf_counter(); result={}
    for name in ([candidate] if candidate else CANDIDATES):
        for backend in ('matlab_spatial','family_mujoco'):
            prepared=prepare_candidate(root,name,backend)
            built,scene=prepared['built'],prepared['scene']
            compile_input(prepared['effective'].model_dump(mode='json'))
            rebuild=save_selection(root,name,backend,prepared,rebuild=True)
            atomic_json(root/(name+'_'+backend+'_input.json'),dict(normalized=prepared['normalized'],
                physics=built.resolved_physics,scene=scene,sources=prepared['selection']['sources']))
            if backend=='family_mujoco':
                import mujoco
                from tools.platform_registry import registry
                config=registry().bind(prepared['effective'].policy.backend,'backend')[1]
                path=root/(name+'.xml'); compile_xml(built.resolved_physics,scene,config,path)
                model=mujoco.MjModel.from_xml_path(str(path))
                result[name]=dict(dofs=model.nv,tendons=model.ntendon,actuators=len(built.candidate.actuators),mass_kg=sum(x['mass_kg'] for x in built.resolved_physics['parts']),
                    selection=prepared['selection'],**rebuild)
    result['prepare_compile_s']=time.perf_counter()-start
    from tools.platform_registry import registry
    reg=registry(); wanted={'model.serial_bending_cells','backend.matlab_spatial','backend.family_mujoco','controller.family'}
    catalog=[dict(extension_id=d.extension_id,version=d.version,kind=d.kind,
        parameter_contract=d.input_schema.__name__,capabilities=d.capabilities)
        for _,d in sorted(reg.extensions.items()) if d.extension_id in wanted]
    atomic_json(root/'capability_catalog.json',dict(source='extensions/tendon_family/manifest.py',entries=catalog))
    atomic_json(root/'candidate_checks.json',result); return result


def run(root,backend,label='',candidate=None):
    from tools.platform_store import Store
    from tools.platform_host import Host
    from tools.state_io import atomic_json
    from extensions.tendon_family.saved import materialize
    from tools.state_io import digest
    root=Path(root).resolve(); read=lambda n:json.loads((root/'inputs'/n).read_text(encoding='utf8'))
    if backend=='single':
        if candidate is not None: raise ValueError('SINGLE_ENTRY_DOES_NOT_ACCEPT_FAMILY_CANDIDATE')
        inp=read('single.json'); selection=None; changes={}; selected='legacy-single'; prefix=backend
    else:
        selected=candidate or 'continuous'
        prepared=prepare_candidate(root,selected,backend)
        save_selection(root,selected,backend,prepared)
        inp=prepared['effective'].model_dump(mode='json'); selection=prepared['selection']; changes={}
        prefix=selected+'_'+backend
        inp['run_id']+='_'+selected
    store=Store(root)
    if not store.db.exists(): store.create(read('project.json'))
    suffix='_'+label if label else ''
    inp['run_id']+=suffix
    host=Host(root,inp['run_id']); host.create(inp)
    record=dict(backend=backend,run_id=inp['run_id'],candidate_id=selected,selection=selection,receipts={})
    def invoke(name,tool,args):
        r=host.invoke(dict(request_id='family-'+name,tool_id=tool,tool_version=inp['policy']['tool_bindings'][tool],arguments=args,cache='new',reason='本轮授权的真实求解或保存结果读取'))
        record['receipts'][name]=r; atomic_json(root/(prefix+suffix+'_record.json'),record)
        if r['execution_status']!='completed': raise RuntimeError(str(r))
        return r
    sim=invoke('simulation','simulation.run',dict(candidate_id=selected,changes=changes))
    if sim['solver_status']!='completed': raise RuntimeError('Solver failed; partial evidence retained')
    ev=invoke('evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    invoke('tip','signals.read',dict(result=sim['output'],name='tip_position',entity='tip'))
    invoke('tension','signals.read',dict(result=sim['output'],name='tendon_tension',entity='tendon_0' if backend=='single' else 'far_t0'))
    record['evaluation']=store.artifact(ev['output']); record['usage']=store.remaining(host.run_id)['used']
    record['result_data']=store.artifact(sim['output'])['data']['data']
    record['saved_folder']=str(materialize(root,record,root/'saved'/(prefix+suffix)))
    if selection:
        folder=Path(record['saved_folder'])
        actual=json.loads((folder/'robot_description.json').read_text(encoding='utf8'))
        if digest(actual['data'])!=selection['design_identity'] or any(record['result_data'][key]!=selection[key] for key in ('physics_identity','scene_identity')):
            raise ValueError('SOLVED_CANDIDATE_IDENTITY_MISMATCH: sealed evidence retained')
        record['selected_input_verified']=True
    atomic_json(root/(prefix+suffix+'_record.json'),record); return record


def read_record(root,backend,candidate=None,label=''):
    if backend=='single' and candidate is not None: raise ValueError('SINGLE_ENTRY_DOES_NOT_ACCEPT_FAMILY_CANDIDATE')
    suffix='_'+label if label else ''
    selected=candidate or 'continuous'
    path=Path(root)/(('' if backend=='single' else selected+'_')+backend+suffix+'_record.json')
    if not path.exists() and candidate is None:
        path=Path(root)/(backend+suffix+'_record.json')
    record=json.loads(path.read_text(encoding='utf8'))
    actual=record.get('candidate_id',record.get('evaluation',{}).get('candidate_id'))
    if backend!='single' and actual!=selected: raise ValueError('SAVED_CANDIDATE_SELECTION_MISMATCH')
    return record


def compare(root,candidate=None,label=''):
    import numpy as np
    from tools.state_io import atomic_json
    root=Path(root); records=[read_record(root,b,candidate,label) for b in ('matlab_spatial','family_mujoco')]
    from extensions.tendon_family.comparison import comparable
    basis=comparable(root,records)
    if not basis['comparable']: return dict(status='not_comparable',**basis,extra_backend_solves=0)
    rows=[json.loads((Path(r['saved_folder'])/'replay_trajectory.json').read_text(encoding='utf8')) for r in records]
    np.testing.assert_allclose([r['time_s'] for r in rows[0]],[r['time_s'] for r in rows[1]],rtol=0,atol=1e-12)
    tips=[np.array([r['tip_m'] for r in rs]) for rs in rows]
    lengths=[np.array([r['tendon_length_m'] for r in rs]) for rs in rows]
    tensions=[np.array([r['tension_n'] for r in rs]) for rs in rows]
    out=dict(candidate_id=candidate or 'continuous',selection=records[0].get('selection'),comparison_basis=basis,meaning='Independent backends, shared physical entities and sample clocks; no ground-truth or calibration claim',
        tip_final_difference_m=float(np.linalg.norm(tips[0][-1]-tips[1][-1])),tip_rms_difference_m=float(np.sqrt(np.mean(np.sum((tips[0]-tips[1])**2,axis=1)))),
        length_max_difference_m=float(np.max(np.abs(lengths[0]-lengths[1]))),tension_max_difference_n=float(np.max(np.abs(tensions[0]-tensions[1]))),
        records=[dict(backend=r['backend'],timings=r['result_data']['timings_s'],evaluation=r['evaluation'],usage=r['usage']) for r in records],
        extra_backend_solves=0)
    atomic_json(root/((candidate+'_' if candidate else '')+'comparison.json'),out); return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('action',choices=['prepare','build','run','compare','view',
        'prepare-opt','build-opt','optimize','best','diagnose','video','crosscheck'])
    parser.add_argument('root',type=Path); parser.add_argument('--backend',choices=['single','matlab_spatial','family_mujoco'],default='matlab_spatial')
    parser.add_argument('--label',default='',help='Explicit distinct invocation label after a diagnosed failure; never auto-retry')
    parser.add_argument('--candidate',choices=list(CANDIDATES),help='Explicit request selection; run defaults to continuous, build defaults to both')
    parser.add_argument('--request',type=Path)
    parser.add_argument('--t-start-s',type=float); parser.add_argument('--t-end-s',type=float)
    parser.add_argument('--fps',type=int,default=25)
    parser.add_argument('--azimuth-deg',type=float,default=135.); parser.add_argument('--elevation-deg',type=float,default=-20.)
    args=parser.parse_args(argv)
    if args.action in ('prepare-opt','build-opt','optimize','best','diagnose','video','crosscheck'):
        from examples.platform_family_optimization import command
        out=command(args.root,args.action,args.request,args.t_start_s,args.t_end_s,args.fps,args.azimuth_deg,args.elevation_deg)
    elif args.action=='run': out=run(args.root,args.backend,args.label,args.candidate)
    elif args.action=='build': out=build_candidates(args.root,args.candidate)
    elif args.action=='compare': out=compare(args.root,args.candidate,args.label)
    elif args.action=='view':
        from extensions.tendon_family.saved import view
        record=read_record(args.root,args.backend,args.candidate,args.label)
        out=view(record['saved_folder'],'mujoco' if args.backend=='family_mujoco' else 'matlab')
    else: out=globals()[{'build':'build_candidates'}.get(args.action,args.action)](args.root)
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf8')
    main()
