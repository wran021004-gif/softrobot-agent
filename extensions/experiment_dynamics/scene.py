"""Named physical assembly; solver approximations remain backend parameters."""
from schemas.platform import Payload
from tools.state_io import digest
from .contracts import Assembly, Initial, Scene


def initialize(parameters, seed):
    return Payload(contract='experiment.initial', data=parameters.model_dump(mode='json'))


def assemble(inp, physics):
    a = Assembly.model_validate(inp.task.environment.data)
    initial = Initial.model_validate(inp.task.initializer.parameters.data)
    objects = {o.name: o for o in a.environment.objects}
    unsupported = [f'{o.name}:{o.kind}' for o in objects.values() if o.kind != 'plane']
    if unsupported:
        raise ValueError('SCENE_OBJECT_UNSUPPORTED: ' + ', '.join(unsupported))
    if a.floor_id not in objects or len(objects) != 1:
        raise ValueError('SCENE_REQUIRES_ONE_NAMED_FLOOR: ' + a.floor_id)
    floor = objects[a.floor_id]
    if not floor.conaffinity & 1:
        raise ValueError('SCENE_FLOOR_MUST_COLLIDE_WITH_ROBOT')
    timing = inp.task.timing
    for f in a.external_forces:
        if f.end_s > timing.duration_s or any(abs(t/timing.timestep_s-round(t/timing.timestep_s)) > 1e-8 for t in (f.start_s, f.end_s)):
            raise ValueError('FORCE_WINDOW_MUST_BE_ON_TIMESTEP_GRID_WITHIN_DURATION')
    body = dict(physics_identity=physics.identity, assembly=a, initial=initial,
        target_world_m=inp.task.goal.data['target_m'], task_identity=digest(inp.task.model_dump(mode='json')),
        duration_s=timing.duration_s, sources=(inp.task.source, *inp.robot.sources))
    scene = Scene(identity='', **body)
    return scene.model_copy(update={'identity': digest(scene.model_dump(mode='json', exclude={'identity'}))})


def applied_forces(scene, time_s):
    # The world force acts at the moving body's COM; no extra applied couple.
    result = {}
    for f in scene.assembly.external_forces:
        if f.start_s <= time_s < f.end_s:
            previous = result.get(f.entity, (0., 0., 0.))
            result[f.entity] = tuple(a+b for a,b in zip(previous, f.force_n))
    return result
