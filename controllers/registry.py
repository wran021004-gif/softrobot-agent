"""Deterministic controller lifecycle and backend/actuator contracts."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ControllerContract:
    version: str
    level: str
    backend: str
    input_type: str
    observations: tuple[str,...]
    reset: str


CONTROLLERS={
    'open_loop_length':ControllerContract('1.0','C1','mujoco','tendon_target_lengths_m',(), 'stateless'),
    'pcc_tip_feedback':ControllerContract('1.0','C2','mujoco','tendon_target_lengths_m',('step','tip_position_m'),'reset'),
}
GENERATORS={name:'controllers.factories:length_controller' for name in CONTROLLERS}
MODE_DEFAULTS={'C1':'open_loop_length','C2':'pcc_tip_feedback'}


def generate(ir,task,control,*,controller_id=None,**kwargs):
    from importlib import import_module
    name=controller_id or MODE_DEFAULTS.get(control.mode)
    if name not in GENERATORS or name not in CONTROLLERS:raise ValueError('CONTROLLER_ADAPTER_REQUIRED')
    if CONTROLLERS[name].level!=control.mode:raise ValueError('CONTROLLER_LEVEL_MISMATCH')
    module,fn=GENERATORS[name].split(':')
    return getattr(import_module(module),fn)(ir,task,control,**kwargs)


def check_backend(mode, backend, task_context=None,*,controller_id=None):
    # MATLAB executes its own deterministic C1/C2 loop; it does not host Python controllers.
    channels={('C1','mujoco'):'python_length_servo',('C2','mujoco'):'python_length_servo',
              ('C1','matlab'):'matlab_native_length_servo',('C2','matlab'):'matlab_native_length_servo'}
    if (mode,backend) not in channels:raise ValueError('CONTROLLER_BACKEND_UNSUPPORTED')
    if controller_id is not None:
        contract=CONTROLLERS.get(controller_id)
        if contract is None or controller_id not in GENERATORS:raise ValueError('CONTROLLER_ADAPTER_REQUIRED')
        if contract.level!=mode or contract.backend!=backend:raise ValueError('CONTROLLER_BACKEND_UNSUPPORTED')
    if task_context and backend=='matlab':
        from schemas.environment_spec import Plane
        if task_context.task.task_type!='reach' or len(task_context.environment.objects)!=1 or not isinstance(task_context.environment.objects[0],Plane):
            raise ValueError('MODEL_TASK_UNSUPPORTED: MATLAB planar backend supports one floor and positional reach only')
    return channels[(mode,backend)]


class ControllerRuntime:
    def __init__(self, controller, backend, dt):
        name=controller.spec.controller
        if name not in CONTROLLERS:raise ValueError('CONTROLLER_ADAPTER_REQUIRED: '+name)
        self.contract=CONTROLLERS[name];self.controller=controller
        if self.contract.backend!=backend:raise ValueError('CONTROLLER_BACKEND_UNSUPPORTED')
        if self.contract.input_type!='tendon_target_lengths_m':raise ValueError('ACTUATOR_ADAPTER_REQUIRED')
        if set(self.contract.observations)-{'step','tip_position_m','qpos','qvel'}:raise ValueError('CONTROL_OBSERVATION_UNSUPPORTED')
        if not math.isfinite(dt) or dt<=0:raise ValueError('INVALID_CONTROL_PERIOD')
        self.dt=dt;self.steps=0;self.lifecycle='created'

    def __getattr__(self,name):return getattr(self.controller,name)

    @property
    def requires_tip_observation(self):return 'tip_position_m' in self.contract.observations

    def start(self):
        if self.contract.reset=='reset':self.controller.reset()
        self.steps=0;self.lifecycle='running'

    def command(self,time_s,observation):
        if self.lifecycle!='running':raise ValueError('CONTROLLER_NOT_RUNNING')
        if not math.isfinite(time_s) or abs(time_s-self.steps*self.dt)>max(1e-8,self.dt*1e-6):
            raise ValueError('CONTROL_TIME_MISMATCH')
        if any(k not in observation for k in self.contract.observations):raise ValueError('CONTROL_OBSERVATION_MISSING')
        output=self.controller.command(time_s,observation)
        self.steps+=1
        return output

    def finish(self):self.lifecycle='finished'
    def abort(self):self.lifecycle='aborted'

    def diagnostics(self):
        return dict(version=self.contract.version,lifecycle=self.lifecycle,steps=self.steps,period_s=self.dt,
            required_observations=list(self.contract.observations),input_type=self.contract.input_type,
            backend=self.contract.backend,reset=self.contract.reset)
