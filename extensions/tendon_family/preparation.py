"""Public candidate loading, normalization and common experiment assembly."""
from copy import deepcopy
import json
from pathlib import Path

from schemas.platform import SessionInput
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.state_io import atomic_json, digest
from .candidate import build
from .scene import assemble


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def prepare_candidate(root, candidate_id, backend, *, legacy_changes=None):
    """Build the selected candidate from authoritative files and assemble its scene.

    Candidate IDs are labels. The request file and the files it references are
    the only editable sources. Legacy requests without a discretization file are
    normalized from Segment.cells and record that compatibility source.
    """
    root = Path(root).resolve()
    inputs = root/'inputs'
    request_path = inputs/(candidate_id+'_request.json')
    if request_path.exists():
        request = _read(request_path)
        request_source = str(request_path)
    elif legacy_changes is not None:
        request = dict(baseline_file='design.json',space_file='space.json',changes=legacy_changes)
        request_source = 'legacy standalone design/space with explicit '+candidate_id+' changes'
    else:
        raise ValueError('CANDIDATE_REQUEST_NOT_FOUND: '+str(request_path))

    design_path = inputs/request.get('design_file',request.get('baseline_file','design.json'))
    space_path = inputs/request.get('space_file','space.json')
    discretization_path = inputs/request['discretization_file'] if request.get('discretization_file') else None
    build_request = dict(baseline=_read(design_path),space=_read(space_path),changes=request.get('changes',{}))
    if discretization_path is not None:
        build_request['discretization'] = _read(discretization_path)

    experiment_path=inputs/'experiment.json'
    if experiment_path.exists():
        raw_input=_read(experiment_path)
        execution=_read(inputs/'execution.json')
        raw_input['run_id']=raw_input['run_id_prefix']+'-'+backend
        del raw_input['run_id_prefix']
        raw_input['policy']['backend']=deepcopy(execution['backends'][backend])
        raw_input['policy']['dynamics_model']=deepcopy(execution['dynamics_model'])
        raw_input['policy']['controller']=_read(inputs/'control.json')
        task_source=str(experiment_path)
    else:
        raw_input = _read(inputs/(backend+'.json'))
        task_source=str(inputs/(backend+'.json'))
    raw_input['robot']['structure']['data'] = deepcopy(build_request['baseline'])
    raw_input['policy']['candidate_builder']['parameters']['data'] = deepcopy(build_request['space'])
    if 'discretization' in build_request:
        raw_input['policy']['discretization'] = dict(contract='family.discretization',version='1.0.0',
            data=deepcopy(build_request['discretization']))
    built = build({**build_request,'changes':{k:v for k,v in build_request['changes'].items() if not k.startswith('control/')}},
        task_bounds={k:v for k,v in raw_input['policy']['editable'].items() if not k.startswith('control/')})
    if built.status != 'valid':
        raise ValueError(built.status.upper()+': '+str(built.reason))

    effective = _candidate(SessionInput.model_validate(raw_input),build_request['changes'],registry())
    physical_design = built.candidate.model_dump(mode='json')
    model_discretization = built.discretization.model_dump(mode='json')
    if effective.robot.structure.data != physical_design:
        raise ValueError('PUBLIC_CANDIDATE_DESIGN_MISMATCH')
    if effective.policy.discretization is None or effective.policy.discretization.data != model_discretization:
        raise ValueError('PUBLIC_CANDIDATE_DISCRETIZATION_MISMATCH')
    scene = assemble(effective,built.resolved_physics)
    from .execution import resolve_execution
    execution_plan=resolve_execution(effective,registry())
    physics_inputs = dict(components={c.id:c.physics.model_dump(mode='json') for c in built.candidate.components if hasattr(c,'physics')},
        tendons={t.id:dict(model=t.model,diameter_m=t.diameter_m,length_servo_gain_n_m=t.length_servo_gain_n_m,
            pretension_n=t.pretension_n,force_limit_n=t.force_limit_n) for t in built.candidate.tendons})
    sources = dict(request=request_source,entity_design=str(design_path),design_space=str(space_path),
        model_discretization=str(discretization_path) if discretization_path else 'legacy Segment.cells compatibility normalization',
        task_environment=task_source,
        dynamics_model=str(inputs/'execution.json') if experiment_path.exists() else 'legacy backend binding',
        control=str(inputs/'control.json') if experiment_path.exists() else task_source)
    normalized_request = dict(baseline=build_request['baseline'],space=build_request['space'],
        discretization=build_request.get('discretization'),changes=build_request['changes'])
    selection = dict(candidate_id=candidate_id,request=normalized_request,task_bounds=raw_input['policy']['editable'],sources=sources,
        original_input=raw_input,modifications=built.summary,
        request_identity=digest(dict(request=normalized_request,task_bounds=raw_input['policy']['editable'])),
        control_identity=scene['control']['identity'],session_identity=digest(raw_input),
        dynamics_model_identity=execution_plan['dynamics_model_identity'],execution_plan_identity=execution_plan['identity'],
        experiment_identity=scene['task_identity'],
        design_identity=digest(physical_design),discretization_identity=digest(model_discretization),
        physical_inputs_identity=digest(physics_inputs),physics_identity=built.resolved_physics['identity'],
        scene_identity=scene['identity'],design_id=built.candidate.id)
    return dict(input=raw_input,effective=effective,built=built,scene=scene,selection=selection,
        normalized=dict(entity_design=physical_design,model_discretization=model_discretization,
            physical_inputs=physics_inputs,experiment=scene['experiment_spec'],execution=execution_plan,control=scene['control']))


def save_selection(root,candidate_id,backend,prepared, *, rebuild=False):
    """Replace unsealed build products only on an explicit build operation."""
    root = Path(root)
    path = root/(candidate_id+'_'+backend+'_selection.json')
    previous = _read(path) if path.exists() else None
    result_path = root/(candidate_id+'_candidate.json')
    result = prepared['built'].model_dump(mode='json')
    old_result = _read(result_path) if result_path.exists() else None
    changed = (previous is not None and previous != prepared['selection']) or (old_result is not None and old_result != result)
    if changed and not rebuild:
        raise ValueError('CANDIDATE_BUILD_STALE: '+str(path)+'; explicitly build the selected candidate again')
    atomic_json(path,prepared['selection'])
    atomic_json(result_path,result)
    return dict(rebuilt=changed,previous_request_identity=previous['request_identity'] if changed and previous else None)
