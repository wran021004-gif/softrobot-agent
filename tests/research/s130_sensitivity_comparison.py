"""Bounded T2 offline rebuild and analysis; immutable saved configuration as source.

build: nine local GVS/CasADi models, no Store/Study/controller execution.
analyze: only stored models and conic programs. Output paths must be new.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from importlib.metadata import version

import numpy as np
from schemas.platform import SessionInput
from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisRequirement, TaskAnalysisProtocol
from tools.platform_store import plain
from tools.state_io import digest
from extensions.math_analysis.capability_sensitivity import capability_sensitivity, _prepare, _contributions


ROOT = Path(__file__).resolve().parents[2]
T1 = '3d782aa435e7c3b1e1cc7cd6eac27fe5565859cb'
SAVED = ROOT/'evidence/s129_math_capability/gvs_pair.json'


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def build(output):
    from tools.research.design import resolved_configuration, set_parameter, parameter_value
    from extensions.tendon_family.math_analysis import make_graph_from_input, _candidate_points, linear_model
    saved = json.loads(SAVED.read_text(encoding='utf-8'))
    original = saved['baseline']; candidate = saved['supporting_artifacts'][original['candidate']['artifact_id']]
    cfg = candidate['configuration']; params = candidate['parameters']
    source = deepcopy(cfg); generator = cfg['policy']['candidate_builder']['parameters']['data']
    source['robot']['structure']['data'] = generator['source_design']
    source['policy']['discretization']['data'] = generator['source_mesh']
    p = TaskAnalysisProtocol.model_validate(original['protocol'])
    # Read bounds from a fixed Git object, never resolve a mutable Study or create one.
    study_bytes = subprocess.check_output(['git','show',T1+':configs/research/study.json'], cwd=ROOT)
    study = json.loads(study_bytes)
    parameters = [dict(path='segments.near.length_m', units='m', steps=[.0005,.00025]),
                  dict(path='segments.distal1.young_pa', units='Pa', steps=[54000.,27000.])]
    for parameter in parameters:
        parameter.update(source=dict(file=SAVED.relative_to(ROOT).as_posix(),
            pointer='/supporting_artifacts/'+original['candidate']['artifact_id']+'/parameters'),
            bounds=study['allowed_parameters'][parameter['path']],
            bounds_source=dict(commit=T1, path='configs/research/study.json',
                pointer='/allowed_parameters/'+parameter['path'], sha256=hashlib.sha256(study_bytes).hexdigest()))
    # Membership is based on the frozen actual segment IDs, not tendon prefixes.
    assert 'distal1' in params['segments'] and 'far' not in params['segments']
    context = dict(source_identity=candidate['source_identity'],
        topology_identity=digest(generator),
        fixed_configuration_identity=digest(dict(task=cfg['task'], seed=cfg['seed'],
            policy={k:v for k,v in cfg['policy'].items() if k!='candidate_builder'})),
        construction_rule='generated_serial via resolved_configuration; projected initializer; controller_start_input; actual_time=0; initial_delta=None')
    variants=[('baseline',deepcopy(params))]
    for a in parameters:
        for h in a['steps']:
            for sign in (-1,1):
                variant=deepcopy(params); d=parameter_value(params,a['path'])+sign*h
                assert a['bounds'][0] <= d <= a['bounds'][1]
                set_parameter(variant,a['path'],d)
                variants.append((a['path']+':'+str(d),variant))
    records=[]
    for index,(label,parameters_i) in enumerate(variants):
        tick=time.perf_counter()
        generated=resolved_configuration(source,cfg,parameters_i,'s130-t2-offline')
        assert generated['task']==cfg['task']
        inp=SessionInput.model_validate(generated)
        binding=deepcopy(original['binding'])
        ref=dict(artifact_id=digest(generated), media_type='application/json')
        binding.update(configuration=ref, candidate_id='s130-t2-'+digest(parameters_i),
                       effective_configuration_identity=digest(generated))
        binding.pop('candidate',None)
        seed=dict(x=[0.]*len(original['model']['x0']),u=original['model']['u0'])
        graph=make_graph_from_input(inp,seed)
        point=_candidate_points(inp,graph,p,['controller_start_input'])[0]
        model=linear_model(dict(binding=binding),point,p,ref,graph)
        operating=dict(model.operating_point,actual_time_s=0.,time_origin='frozen initializer via existing controller preparation')
        model=model.model_copy(update=dict(operating_point=operating))
        record=dict(label=label, parameters=parameters_i, model=plain(model), initial_delta=None,
            requirements=original['task_analysis'], context=context, configuration=generated,
            construction_s=time.perf_counter()-tick,
            source_reference=dict(file=output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else output.name,
                pointer='/models/'+str(index), model_sha256=digest(plain(model)),
                configuration_identity=ref['artifact_id'], storage='offline JSON snapshot; not a registered Store artifact'))
        records.append(record)
        print(json.dumps(dict(index=index,label=label,construction_s=record['construction_s'])),flush=True)
        del graph
    old=EndpointLinearizedModel.model_validate(original['model']); new=EndpointLinearizedModel.model_validate(records[0]['model'])
    errors={k:float(np.max(abs(np.array(getattr(old,k))-getattr(new,k)))) for k in ('A','B','drift','x0','u0','C','D','y0')}
    for a,b in zip(old.endpoint_outputs,new.endpoint_outputs):
        for k in ('value0','C','D'):
            errors[a.name+'.'+k]=float(np.max(abs(np.array(getattr(a,k))-getattr(b,k))))
    result=dict(scope='Nine GVS/CasADi local mathematical rebuilds only; no physical execution',
        source=dict(path=SAVED.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(SAVED.read_bytes()).hexdigest()),
        source_baseline=T1, parameters=parameters, protocol=original['protocol'], models=records,
        baseline_reconstruction_max_absolute_errors=errors,
        baseline_reconstruction_passed=all(v<1e-9 for v in errors.values()),
        environment=dict(python=platform.python_version(),versions={n:version(n) for n in ('casadi','numpy','scipy','pydantic','PyYAML')},
                         threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}),
        computation_cost=dict(model_builds=len(records), construction_s=sum(r['construction_s'] for r in records)))
    write_new(output,result)
    if not result['baseline_reconstruction_passed']:
        raise ValueError('Baseline reconstruction mismatch; evidence saved, sensitivity not authorized by this script')


def analyze(models_path, output):
    from tools.research.design import parameter_value
    raw=json.loads(models_path.read_text(encoding='utf-8'))
    if not raw['baseline_reconstruction_passed']: raise ValueError('BASELINE_REBUILD_MISMATCH')
    protocol=TaskAnalysisProtocol.model_validate(raw['protocol'])
    groups=[]
    for parameter in raw['parameters']:
        points=[]
        for record in raw['models']:
            if record['label']!='baseline' and not record['label'].startswith(parameter['path']+':'): continue
            points.append(dict(record, value=parameter_value(record['parameters'],parameter['path']),
                model=EndpointLinearizedModel.model_validate(record['model']),
                requirements=TaskAnalysisRequirement.model_validate(record['requirements'])))
        result=capability_sensitivity(points,parameter,protocol)
        groups.append(result)
        print(json.dumps(dict(parameter=parameter['path'],status=result['status'],direction=result['direction_status'],
            differences=[{k:r[k] for k in ('step','reoptimized','envelope','fixed_control')} for r in result.get('reoptimized_finite_difference',[])],
            reason=result.get('reason')),allow_nan=False),flush=True)
    # Historical B pair remains a finite secant, independent of the new local stencils.
    old=json.loads(SAVED.read_text(encoding='utf-8'))
    t1path=ROOT/'evidence/s130_optimal_capability/comparison.json'
    t1=json.loads(t1path.read_text(encoding='utf-8'))
    data=[]
    for key in ('baseline','changed'):
        row=old[key]
        data.append(_prepare(dict(model=EndpointLinearizedModel.model_validate(row['model']),
            requirements=TaskAnalysisRequirement.model_validate(row['task_analysis']),initial_delta=None),protocol))
    solution=t1['cases']['baseline']['conic']; U=np.array(solution['applied_input_n']).ravel()
    _,_,_,contributions,box=_contributions(data[0],data[1],.001,U,solution['dual_checks'])
    history=dict(kind='finite_secant_not_local_derivative', source=str(t1path.relative_to(ROOT)),
        source_sha256=hashlib.sha256(t1path.read_bytes()).hexdigest(),
        parameter_values=[.160,.161],
        reoptimized_secant=(t1['cases']['changed']['conic']['replayed_violation']-solution['replayed_violation'])/.001,
        baseline_dual_finite_lagrangian_secant=sum(r['contribution'] for r in contributions)+box,
        constraint_contributions=contributions, box_contribution=box)
    result=dict(scope='T2 local frozen-model sensitivity diagnostics only', model_file=models_path.name,
        model_file_sha256=hashlib.sha256(models_path.read_bytes()).hexdigest(), historical_B_secant=history, analyses=groups,
        computation_cost=dict(unique_model_builds=raw['computation_cost']['model_builds'],
            unique_construction_s=raw['computation_cost']['construction_s'],
            conic_solves=sum(r.get('computation_cost',{}).get('conic_solves',0) for r in groups),
            conic_kernel_s=sum(r.get('computation_cost',{}).get('conic_kernel_s',0.) for r in groups),
            dual_face_solves=sum(r.get('computation_cost',{}).get('dual_face_solves',0) for r in groups),
            dual_face_wall_s=sum(r.get('computation_cost',{}).get('dual_face_wall_s',0.) for r in groups)),
        implementation_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
            'extensions/math_analysis/capability_sensitivity.py','extensions/math_analysis/conic_capability.py',
            'extensions/math_analysis/trajectory.py','extensions/tendon_family/math_analysis.py',
            'extensions/tendon_family/generated_serial.py','tests/research/s130_sensitivity_comparison.py')})
    write_new(output,result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['build','analyze'])
    parser.add_argument('--models',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('Choose a new output path; preserve earlier evidence.')
    if args.mode=='build': build(args.output.resolve())
    else: analyze(args.models,args.output)
