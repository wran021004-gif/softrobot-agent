"""One-time extraction of the executed V1 source and finite V2 catalog.

No physics execution. The committed asset is used by the public implementation.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
from tools.state_io import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / 'extensions/tendon_family/profiles/finite_templates_v2.json'
T0_CONFIGURATION = '77a1406779dbbf5c440e8077796eeb222446001587d1a9befea0c64bbc146925'


def rotate(point, angle):
    x, y, z = point
    return [x, math.cos(angle)*y-math.sin(angle)*z,
            math.sin(angle)*y+math.cos(angle)*z]


def layout8(source):
    design = deepcopy(source)
    guide = next(c for c in design['components'] if c['id'] == 'mid_guide')
    guide['guide_holes'] = {}
    design['tendons'], design['actuators'] = [], []
    for group in ('near', 'far'):
        prototype = next(t for t in source['tendons'] if t['id'] == group+'_t0')
        actuator = next(a for a in source['actuators'] if a['id'] == group+'_motor0')
        for index in range(4):
            angle = index*math.pi/2
            tendon = deepcopy(prototype)
            tendon['id'] = f'{group}_t{index}'
            for point in tendon['points']:
                if point['hole']:
                    hole = f'{group}_h{index}'
                    guide['guide_holes'][hole] = rotate(
                        next(c for c in source['components'] if c['id']=='mid_guide')['guide_holes'][point['hole']], angle)
                    point['hole'] = hole
                else:
                    point['attachment']['position_m'] = rotate(point['attachment']['position_m'], angle)
            drive = deepcopy(actuator)
            drive['id'] = f'{group}_motor{index}'
            drive['transmission'] = [dict(tendon=tendon['id'], ratio=1.)]
            design['tendons'].append(tendon)
            design['actuators'].append(drive)
    return design


def split_distal(source):
    design = deepcopy(source)
    far = next(c for c in design['components'] if c['id']=='far')
    middle = deepcopy(far)
    middle['id'] = 'middle'
    middle['length_m'] = far['length_m']/2
    far['length_m'] /= 2
    # Preserve the continuous physical taper/section angle across both halves.
    left, right = deepcopy(far['sections'][0]), deepcopy(far['sections'][-1])
    midpoint = deepcopy(left)
    midpoint['section']['angle_rad'] = (left['section']['angle_rad']+right['section']['angle_rad'])/2
    midpoint['section']['parameters'] = {k:(v+right['section']['parameters'][k])/2
        for k,v in left['section']['parameters'].items()}
    middle['sections'] = [left, dict(s=1., section=deepcopy(midpoint['section']))]
    far['sections'] = [dict(s=0., section=deepcopy(midpoint['section'])), right]
    split_guide = deepcopy(next(c for c in design['components'] if c['id']=='mid_guide'))
    split_guide['id'] = 'split_guide'
    split_guide['connection'] = dict(part='middle', s=1., position_m=[0.,0.,0.], quaternion_wxyz=[1.,0.,0.,0.])
    split_guide['guide_holes'] = {}
    far['connection'] = dict(part='split_guide', s=0., position_m=[0.,0.,0.], quaternion_wxyz=[1.,0.,0.,0.])
    index = design['components'].index(far)
    design['components'][index:index] = [middle, split_guide]
    mid_guide = next(c for c in design['components'] if c['id']=='mid_guide')
    for tendon in design['tendons']:
        if not tendon['id'].startswith('far_'): continue
        prefix = deepcopy(tendon['points'][:3])
        old_midpoint, anchor = deepcopy(tendon['points'][3]), deepcopy(tendon['points'][4])
        hole = tendon['id'].replace('_t','_h')
        split_guide['guide_holes'][hole] = old_midpoint['attachment']['position_m']
        proximal = deepcopy(old_midpoint)
        proximal['attachment']['part'] = 'middle'
        proximal['attachment']['position_m'] = [(a+b)/2 for a,b in zip(
            mid_guide['guide_holes'][hole], old_midpoint['attachment']['position_m'])]
        boundary = dict(role='guide', hole=hole, attachment=dict(part='split_guide', s=0.,
            position_m=[0.,0.,0.], quaternion_wxyz=[1.,0.,0.,0.]))
        distal = deepcopy(old_midpoint)
        distal['attachment']['position_m'] = [(a+b)/2 for a,b in zip(
            old_midpoint['attachment']['position_m'],anchor['attachment']['position_m'])]
        tendon['points'] = [*prefix, proximal, boundary, distal, anchor]
    return design


def freeze():
    bundle = json.loads((ROOT/'evidence/research_mainline3_v1_handoff_20261009/fixed_bundle.json').read_text(encoding='utf8'))
    candidate = bundle['artifacts'][T0_CONFIGURATION]
    assert digest(candidate) == T0_CONFIGURATION
    effective = candidate['effective']
    assert digest(effective) == candidate['content_identity']
    source = effective['robot']['structure']['data']
    designs = dict(T0=deepcopy(source), T1=layout8(source), T2=split_distal(source))
    designs['T3'] = split_distal(designs['T1'])
    templates = {}
    for key,design in designs.items():
        if key!='T0':
            design['id'] = 'mainline3_v2_'+key
            design['metadata'] = dict(finite_template=key, source_configuration=T0_CONFIGURATION,
                initialization='zero named segment integrated bends/rates; distal split explicitly zero')
        mesh = deepcopy(effective['policy']['discretization']['data'])
        if key in ('T2','T3'):mesh['cells'] = dict(near=12, middle=6, far=6)
        templates[key] = dict(design=design,discretization=mesh,
            difference=('Exact executed V1 robot and mesh' if key=='T0' else
                'Four tendons at each of two routing rings; 90 degree spacing; independent actuator per tendon' if key=='T1' else
                'Distal 0.11 m taper split into two 0.055 m components; extra 2 g guide and guide inertia; added intermediate routes' if key=='T2' else
                'T1 independent eight-channel layout combined with T2 distal split'),
            initialization=dict(regions={'near':['near'], 'distal':['middle','far'] if key in ('T2','T3') else ['far']},
                scientific_integrated_bends_rad=dict(near=[0.,0.],distal=[0.,0.]),
                scientific_integrated_rates_rad_s=dict(near=[0.,0.],distal=[0.,0.])))
    # Save only the needed exact scientific source, rather than its old grants.
    scientific = dict(robot=effective['robot'],task=effective['task'],seed=effective['seed'],
        policy={k:effective['policy'][k] for k in ('controller','backend','dynamics_model','discretization')})
    result = dict(version='2.0.0',t0_configuration=T0_CONFIGURATION,
        t0_backend_execution='197bceb6ff8f44b48a35bc4f79b3528d',
        scientific_source=scientific,templates=templates,
        execution_model='ideal_tension: tendon-force limits enforced; actuator travel/velocity declared only',
        supported_task_families=['task.reach'],unsupported=['arbitrary topologies','coupled actuation','motor-realistic NMPC',
            'shear','axial stretch','torsion','tendon friction','rope elasticity','self collision'],
        selection=dict(path='template',method='search.family_explicit@1.0.0',options=list(templates)))
    atomic_json(ASSET,result)
    return result


if __name__=='__main__':
    value=freeze()
    print(json.dumps(dict(asset=str(ASSET),identity=digest(value),templates=list(value['templates']))))
