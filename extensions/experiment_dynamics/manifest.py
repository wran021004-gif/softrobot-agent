"""Model selection uses existing backend bindings, with typed solver parameters."""
from schemas.platform import BackendResult, Payload
from schemas.exploration import ExplorationControl
from extensions.reference.contracts import ControlOutput
from tools.platform_registry import Extension
from . import contracts as c
from .signals import declarations

CONTRACTS = [('experiment.'+name, '1.0.0', schema) for name, schema in (
    ('assembly',c.Assembly), ('initial',c.Initial), ('physics',c.ResolvedPhysics), ('scene',c.Scene),
    ('spatial_parameters',c.SpatialParameters), ('planar_parameters',c.PlanarParameters),
    ('mujoco_parameters',c.MujocoParameters), ('backend_data',c.DynamicsData))]
SOURCES = tuple('extensions/experiment_dynamics/'+name+'.py' for name in
    ('contracts','physics','scene','spatial','signals','backends','manifest')) + (
    'tools/design_compiler.py','schemas/exploration.py','schemas/robot_ir.py',
    'controllers/factories.py','controllers/open_loop_length.py','controllers/pcc_tip_feedback.py',
    'tools/pcc_math.py','tools/reach_dynamics.py','extensions/robot_domain/signals.py',
    'schemas/environment_spec.py','schemas/design_spec.py','schemas/control_spec.py','schemas/feedback.py',
    'schemas/experiment_policy.py','tools/state_io.py','extensions/robot_domain/contracts.py')
EXTENSIONS = [
    Extension('initialize.experiment','initializer','1.0.0',c.Initial,Payload,
        'extensions.experiment_dynamics.scene:initialize','Explicit eight-cell y/z joint positions and velocities; no random initial-state changes',
        sources=SOURCES, capabilities=dict(category='scene_assembly',role='adapter')),
    Extension('controller.experiment_length','controller','1.0.0',ExplorationControl,ControlOutput,
        'extensions.experiment_dynamics.backends:LengthController','Reuse C1/C2; transform live world-frame tip observations to the mount frame',
        sources=SOURCES, capabilities=dict(category='control',role='adapter',channel='tendon_target_lengths_m',
            observations=['tip_position'],reset=True,restore=False,
            realtime_observations='actual current tip, joint positions/velocities and tendon lengths before each integration interval; world tip transformed to mount frame for C2')),
]
for name, schema, model, dependencies, resources, description in [
    ('math_spatial',c.SpatialParameters,'spatial',('numpy','scipy'),(), 'Independent spatial coupled dynamics with 16 degrees of freedom; no MuJoCo dependency'),
    ('math_planar',c.PlanarParameters,'matlab',('numpy','matlab.engine'),('matlab_engine',), 'Original MATLAB planar v1 algorithm using shared physical quantities directly; no MuJoCo'),
    ('scene_mujoco',c.MujocoParameters,'mujoco',('numpy','mujoco'),(), 'Map shared physics and unified scenes to MuJoCo'),
]:
    binding = {'math_spatial':'SpatialBackend','math_planar':'PlanarBackend','scene_mujoco':'MujocoBackend'}[name]
    phase = 'sampled_state' if model == 'matlab' else 'post_step'
    EXTENSIONS.append(Extension('backend.'+name,'backend','1.0.0',schema,BackendResult,
        'extensions.experiment_dynamics.backends:'+binding,description,
        dependencies=dependencies,resources=resources,sources=SOURCES+(
            ('tools/mujoco_tools.py','tools/spec_tools.py') if model == 'mujoco' else
            ('tools/matlab_tools.py',) if model == 'matlab' else ()),
        assets=('physics_contracts/equivalent_rod_v2.md',)+(
            ('matlab/tdcr_planar_dynamic.m',) if model == 'matlab' else
            ('tasks/reach_free/task.yaml','configs/simulator.yaml') if model == 'mujoco' else ()),
        contract_dependencies=tuple((n,v) for n,v,_ in CONTRACTS),
        capabilities=dict(category='mathematical_models' if model != 'mujoco' else 'simulation',role='adapter',
            conversion='typed assembled equivalent rod',families=['task.reach'],robots=['tendon_driven_continuum'],
            robot_contracts=['domain.rod_design'],channels=['tendon_target_lengths_m'],environments=['experiment.assembly'],
            controllers=['controller.experiment_length'],
            signals=sorted({s['name'] for s in declarations(model)}|{'tendon_tension'}),
            signal_templates=declarations(model),signal_specs_resolver='extensions.experiment_dynamics.signals:observation_specs',
            signal_phases=[phase] if model == 'matlab' else [phase,'pre_step_solver'],
            model=schema.model_fields['model'].default, model_version='1.0.0',
            realtime_control='MATLAB internal C1/C2 at its original update times; update log unavailable' if model == 'matlab' else
                'C1/C2 adapter consumes actual pre-integration world tip; logs world observations and mount-frame feedback updates',
            dofs='8 ordered y axes' if model == 'matlab' else '16 ordered y,z axes; eight links',
            physics='equivalent rod compiler; SI; COM body-local full inertia',
            force_convention='actuator negative pulls; tension positive; external world force at named link COM, [start,end)',
            contact_count_semantics='positive-normal-force segments in math; detected contact points in MuJoCo; not directly comparable',
            required_environment='one named horizontal floor; fixed mount',
            applicability='Planar: identity mount, zero state, x-z target/control/gravity, no external force' if model == 'matlab' else
                'Spatial bending; fixed mount pose; explicit state; named floor and timed COM forces',
            omissions=['axial extension','shear','material twist','tendon friction','self collision'],
            operations=['compile','initialize','run','export','close'], cancellation='between public calls',
            timeout='numerical loop deadline; startup/close not hard bounded')))
