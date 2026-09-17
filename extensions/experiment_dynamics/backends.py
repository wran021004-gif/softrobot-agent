"""Existing platform lifecycle, shared physical inputs, separate numerical engines."""
import gzip
import json
import time
from types import SimpleNamespace
import numpy as np
from schemas.platform import BackendResult, Payload
from tools.state_io import atomic_json
from tools.design_compiler import ensure_robot_ir
from .contracts import Assembly, Initial, DynamicsData
from .physics import resolve_physics
from .scene import assemble, applied_forces
from .spatial import SpatialModel, mount_rotation


LIMITATIONS = ['Equivalent rod is uncalibrated.', 'No axial extension, shear, material twist, tendon friction or self collision.',
               'Guide-to-guide straight tendon paths; four length servos, tension only.']


class LengthController:
    """Reuse C1/C2 implementation, transforming world tip/target into mount frame."""
    def __init__(self, parameters, period_s):
        self.parameters, self.period_s = parameters, period_s

    def configure(self, ir, scene, source):
        from controllers.factories import length_controller
        self.R = mount_rotation(scene.assembly.mount)
        self.p = np.array(scene.assembly.mount.position_m)
        target = self.R.T@(np.array(scene.target_world_m)-self.p)
        self.actual = length_controller(ir, SimpleNamespace(target_m=target), self.parameters,
            authority=scene.sources[0], timestep_s=self.period_s, parameter_source=source)
        self.reset()

    def reset(self):
        if self.parameters.mode == 'C2':
            self.actual.reset()
        self.observations = []
        self.lifecycle = 'running'

    def finish(self, interrupted=False):
        self.lifecycle = 'aborted' if interrupted else 'finished'

    def command(self, time_s, step, observation):
        local = self.R.T@(np.array(observation['tip_position_m'])-self.p)
        self.observations.append(dict(time_s=time_s, phase='current_state_before_integration',
            frame='world', **observation))
        command = self.actual.command(time_s, dict(step=step, **{**observation, 'tip_position_m':local.tolist()}))
        return np.array(command.tendon_target_lengths_m)


class SpatialBackend:
    backend_id = 'backend.math_spatial'
    signal_model = 'spatial'

    @staticmethod
    def check(inp, parameters, control):
        from extensions.robot_domain.contracts import RodDesign
        if inp.robot.structure.contract != 'domain.rod_design':
            raise ValueError('ASSEMBLED_BACKEND_REQUIRES_DOMAIN_ROD_DESIGN')
        physics = resolve_physics(RodDesign.model_validate(inp.robot.structure.data))
        assemble(inp, physics)
        if inp.task.initializer.extension_id != 'initialize.experiment':
            raise ValueError('EXPLICIT_EXPERIMENT_INITIALIZER_REQUIRED')
        if inp.policy.controller.extension_id != 'controller.experiment_length':
            raise ValueError('EXPERIMENT_LENGTH_CONTROLLER_REQUIRED')
        t = inp.task.timing
        if t.control_period_s != t.timestep_s or t.sample_period_s != t.timestep_s:
            raise ValueError('ASSEMBLED_BACKEND_REQUIRES_CONTROL_AND_SAMPLE_AT_TIMESTEP')

    def compile(self, inp, reg):
        self.inp, self.reg = inp, reg
        self.parameters = reg.parse(inp.policy.backend.parameters)
        self.ir = ensure_robot_ir(reg.parse(inp.robot.structure))
        self.physics = resolve_physics(self.ir)
        self.scene = assemble(inp, self.physics)

    def initialize(self, initial, controller):
        if Initial.model_validate(initial.data) != self.scene.initial:
            raise ValueError('SCENE_INITIAL_STATE_MISMATCH')
        self.initial, self.controller = initial, controller

    def run(self, folder, timeout_s):
        folder.mkdir(parents=True, exist_ok=True)
        self.folder = folder
        atomic_json(folder/'resolved_physics.json', self.physics.model_dump(mode='json'))
        atomic_json(folder/'experiment_scene.json', self.scene.model_dump(mode='json'))
        atomic_json(folder/'robot_ir.json', self.ir.model_dump(mode='json'))
        atomic_json(folder/'solver_configuration.json', self.parameters.model_dump(mode='json'))
        self.controller.configure(self.ir, self.scene, folder/'solver_configuration.json')
        rows, complete, reason, steps = self.solve(timeout_s)
        self.controller.finish(interrupted=not complete)
        with gzip.open(folder/'trajectory.json.gz', 'wt', encoding='utf8') as stream:
            json.dump(rows, stream, allow_nan=False)
        updates = getattr(self.controller.actual, 'updates', [])
        atomic_json(folder/'controller_updates.json', updates)
        atomic_json(folder/'controller_observations.json', self.controller.observations)
        from .signals import export
        data = DynamicsData(backend=self.backend_id, physics_identity=self.physics.identity,
            scene_identity=self.scene.identity, solver_configuration=self.parameters,
            exported_files=sorted(p.name for p in folder.iterdir()), controller_mode=self.controller.parameters.mode,
            controller_updates=None if self.signal_model == 'matlab' else len(updates), numerical_steps=steps, reason=reason)
        self.result = BackendResult(solver_status='completed' if complete else 'failed', backend_id=self.backend_id,
            model_id=self.parameters.model, signals=export(rows, self.signal_model, self.ir),
            data=Payload(contract='experiment.backend_data', data=data.model_dump(mode='json')),
            limitations=self.limitations(), initial_state=self.initial, seed=self.inp.seed)
        atomic_json(folder/'result.json', self.result.model_dump(mode='json'))
        return self.export()

    def limitations(self):
        return LIMITATIONS + ['Endpoint half-weight unilateral normal penalty; no tangential friction; not a validated contact law.']

    def solve(self, timeout_s):
        from scipy.integrate import solve_ivp
        model = SpatialModel(self.physics, self.scene, self.parameters)
        n, dt = model.n, self.inp.task.timing.timestep_s
        y = np.array((*self.scene.initial.qpos_rad, *self.scene.initial.qvel_rad_s))
        rows, steps, started = [], 0, time.monotonic()
        count = round(self.scene.duration_s/dt)
        try:
            for step in range(count):
                t = step*dt
                geometry = model.geometry(y[:n])
                command = self.controller.command(t, step, dict(tip_position_m=geometry['nodes'][-1].tolist(),
                    qpos_rad=y[:n].tolist(), qvel_rad_s=y[n:].tolist(), tendon_length_m=geometry['lengths'].tolist()))
                external = applied_forces(self.scene, t)
                before = model.terms(y[:n], y[n:], command, external)
                def rhs(time_s, state):
                    if time.monotonic()-started > timeout_s:
                        raise TimeoutError('SPATIAL_SOLVER_TIMEOUT')
                    return np.r_[state[n:], model.acceleration(state[:n], state[n:], command, external)]
                sol = solve_ivp(rhs, (t,(step+1)*dt), y, method=self.parameters.solver,
                    rtol=self.parameters.rtol, atol=self.parameters.atol, max_step=self.parameters.max_step_s)
                steps += len(sol.t)-1
                if not sol.success:
                    return rows, False, sol.message, steps
                y = sol.y[:,-1]
                if not np.isfinite(y).all():
                    return rows, False, 'NONFINITE_STATE', steps
                after = model.geometry(y[:n])
                rows.append(dict(time_s=(step+1)*dt, solver_time_s=t, tip_m=after['nodes'][-1].tolist(),
                    qpos_rad=y[:n].tolist(), qvel_rad_s=y[n:].tolist(), command_m=command.tolist(),
                    solver_tendon_length_m=before['geometry']['lengths'].tolist(),
                    solver_actuator_force_n=(-before['tension']).tolist(), solver_contact_count=int(np.count_nonzero(before['normal'])),
                    solver_qfrc_actuator_nm=before['drive'].tolist(),
                    solver_qfrc_passive_nm=(before['spring']+before['damping']).tolist(),
                    external_torque_nm=before['external'].tolist(), floor_gap_m=before['gaps'].tolist(),
                    normal_contact_approx_n=before['normal'].tolist(), centerline_m=after['nodes'].tolist(),
                    tendon_routes_m=after['routes'].tolist()))
        except (TimeoutError, np.linalg.LinAlgError) as exc:
            return rows, False, str(exc), steps
        return rows, True, None, steps

    def export(self):
        return self.result

    def close(self):
        pass


class PlanarBackend(SpatialBackend):
    backend_id = 'backend.math_planar'
    signal_model = 'matlab'

    @staticmethod
    def check(inp, parameters, control):
        SpatialBackend.check(inp, parameters, control)
        a = Assembly.model_validate(inp.task.environment.data)
        initial = Initial.model_validate(inp.task.initializer.parameters.data)
        # Preserve the existing algorithm, including its world x-z projection.
        if (a.mount.position_m != (0.,0.,0.) or a.mount.quaternion_wxyz != (1.,0.,0.,0.) or
            any(initial.qpos_rad) or any(initial.qvel_rad_s) or a.external_forces or
            abs(control.bend_y_rad) > 1e-8 or abs(inp.task.goal.data['target_m'][1]) > 1e-8 or
            abs(a.environment.gravity_m_s2[1]) > 1e-8):
            raise ValueError('PLANAR_V1_SCOPE: identity mount, zero initial state, x-z target/gravity/control, no external force')

    def limitations(self):
        return LIMITATIONS + ['Original MATLAB planar v1 algorithm: x-z motion only; zero initial state; identity mount; no external force.']

    def solve(self, timeout_s):
        from tools.reach_dynamics import control_commands, SOLVER
        from tools.matlab_tools import MatlabTools
        parts, ir, c = self.physics.parts, self.ir, self.controller.parameters
        env = self.scene.assembly.environment
        floor = next(o for o in env.objects if o.name == self.scene.assembly.floor_id)
        p = dict(model_id=self.parameters.model, length=ir.total_length_m, ds=ir.section.segment_length_m,
            radius=ir.tendon_routing_radius_m, body_radius=ir.body_radius_m,
            mass=[p.mass_kg for p in parts], inertia_y=[p.inertia_com_local_kg_m2[1][1] for p in parts],
            stiffness=[p.stiffness_nm_rad[0] for p in parts], damping=[p.damping_nm_s_rad[0] for p in parts],
            natural=[p.natural_rad[0] for p in parts], kp=self.physics.tendons[0].kp_n_m,
            fmax=self.physics.tendons[0].force_limit_n, offsets=[t.offset_yz_m for t in self.physics.tendons],
            angles=[r.angle_rad for r in ir.tendon_routes], command=control_commands(ir,c),
            bend=[c.bend_y_rad,c.bend_z_rad], control=c.model_dump(mode='json'), gravity=env.gravity_m_s2,
            floor_z=floor.position_m[2], duration=self.scene.duration_s, dt=self.inp.task.timing.timestep_s,
            target=self.scene.target_world_m, tolerance=self.inp.task.evaluator.parameters.data['tolerance_m'],
            solver=SOLVER, timeout_s=timeout_s, physics_identity=self.physics.identity, scene_identity=self.scene.identity)
        atomic_json(self.folder/'shared_input.json', p)
        executor = MatlabTools()
        try:
            raw = self.folder/'matlab_raw.json'
            future = executor.eng.tdcr_planar_dynamic(json.dumps(p), str(raw.resolve()), nargout=0, background=True)
            try:
                future.result(timeout=timeout_s)
            except Exception:
                future.cancel()
                raise
            out = json.loads(raw.read_text(encoding='utf8'))
            return out['trajectory'], out['complete'], out['reason'] or None, out['successful_internal_steps']
        finally:
            executor.close()


class MujocoBackend(SpatialBackend):
    backend_id = 'backend.scene_mujoco'
    signal_model = 'mujoco'

    def limitations(self):
        return LIMITATIONS + ['MuJoCo rigid-body contact solver and default contact/friction parameters, recorded in robot.xml.']

    def solve(self, timeout_s):
        # Only this physical engine adapter imports MuJoCo.
        import mujoco
        import xml.etree.ElementTree as ET
        from tools.mujoco_tools import compile_mujoco
        from tools.spec_tools import load_task, load_simulator
        from schemas.task_spec import TaskSpec
        old = load_task()
        env = self.scene.assembly.environment
        task = TaskSpec.model_validate({**old.model_dump(mode='json'), 'environment_id':env.environment_id,
            'target_m':self.scene.target_world_m, 'position_error_max_m':self.inp.task.evaluator.parameters.data['tolerance_m']})
        dt = self.inp.task.timing.timestep_s
        simulator = load_simulator().model_copy(update={'timestep_s':dt})
        path = self.folder/'robot.xml'
        compiled = compile_mujoco(self.ir, task, path, env, simulator)
        if compiled.status != 'pass':
            raise ValueError(compiled.message)
        tree = ET.parse(path); root = tree.getroot(); world = root.find('worldbody')
        base = ET.SubElement(world, 'body', name='fixed_base',
            pos=' '.join(map(str,self.scene.assembly.mount.position_m)),
            quat=' '.join(map(str,self.scene.assembly.mount.quaternion_wxyz)))
        for node in list(world):
            if node.get('name') == 'segment_0' or node.get('name','').startswith('tendon_'):
                world.remove(node); base.append(node)
        root.find('option').set('integrator', self.parameters.integrator)
        tree.write(path, encoding='utf8', xml_declaration=True)
        model = mujoco.MjModel.from_xml_path(str(path))
        data, pose = mujoco.MjData(model), mujoco.MjData(model)
        data.qpos[:] = self.scene.initial.qpos_rad; data.qvel[:] = self.scene.initial.qvel_rad_s
        ids = [model.body(p.entity).id for p in self.physics.parts]
        # Recorded compiled inputs prove that the physical engine consumed resolution.
        atomic_json(self.folder/'compiled_physics.json', dict(physics_identity=self.physics.identity,
            scene_identity=self.scene.identity, mass_kg=model.body_mass[ids].tolist(),
            com_local_m=model.body_ipos[ids].tolist(), inertia_principal_kg_m2=model.body_inertia[ids].tolist(),
            stiffness_nm_rad=model.jnt_stiffness.tolist(), damping_nm_s_rad=model.dof_damping.tolist(),
            initial_qpos=data.qpos.tolist(), initial_qvel=data.qvel.tolist(), timestep_s=model.opt.timestep))
        rows, started = [], time.monotonic()
        count = round(self.scene.duration_s/dt)
        for step in range(count):
            if time.monotonic()-started > timeout_s:
                return rows, False, 'MUJOCO_SOLVER_TIMEOUT', step
            t = step*dt
            pose.qpos[:] = data.qpos; pose.qvel[:] = data.qvel
            mujoco.mj_forward(model, pose)
            command = self.controller.command(t,step,dict(tip_position_m=pose.site_xpos[model.site('tip_site').id].tolist(),
                qpos_rad=data.qpos.tolist(), qvel_rad_s=data.qvel.tolist(), tendon_length_m=pose.ten_length.tolist()))
            data.ctrl[:] = command
            data.xfrc_applied[:] = 0
            external_torque = np.zeros(model.nv)
            for entity, force in applied_forces(self.scene,t).items():
                bid = model.body(entity).id
                data.xfrc_applied[bid,:3] += force
                J = np.zeros((3,model.nv)); Jr = np.zeros_like(J)
                mujoco.mj_jacBodyCom(model,pose,J,Jr,bid)
                external_torque += J.T@force
            mujoco.mj_step(model,data)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                return rows, False, 'NONFINITE_STATE', step+1
            pose.qpos[:] = data.qpos
            mujoco.mj_kinematics(model,pose)
            rows.append(dict(time_s=(step+1)*dt, solver_time_s=t, tip_m=pose.site_xpos[model.site('tip_site').id].tolist(),
                qpos_rad=data.qpos.tolist(), qvel_rad_s=data.qvel.tolist(), command_m=command.tolist(),
                solver_tendon_length_m=data.ten_length.tolist(), solver_actuator_force_n=data.actuator_force.tolist(),
                solver_contact_count=int(data.ncon), solver_qfrc_actuator_nm=data.qfrc_actuator.tolist(),
                solver_qfrc_passive_nm=data.qfrc_passive.tolist(), external_torque_nm=external_torque.tolist(),
                centerline_m=[pose.xpos[i].tolist() for i in ids]+[pose.site_xpos[model.site('tip_site').id].tolist()]))
        return rows, True, None, count
