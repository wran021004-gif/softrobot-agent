"""S145 offline diagnosis of saved S142/S144 evidence; never steps physics.

Run with the existing .mainline5-env Python from this worktree. Large outputs
go to ignored runs/s145. Source worktrees and the sealed Store are read-only.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sqlite3
import sys
import time

import casadi as ca
import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from extensions.tendon_family.compiler import rx
from extensions.tendon_family.contracts import GVSModelParameters, ResolvedGVSBasis
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_casadi import expression_from_system, functions_for
from extensions.tendon_family.gvs_projection import discretization_jacobian, discretize, project
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
from schemas.platform import RobotDescription
from schemas.platform_math import SystemContext


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    def convert(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                               allow_nan=False, default=convert), encoding='utf8')


def audit(root):
    path = root / 'platform.sqlite'
    stat = path.stat()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        state = json.loads(db.execute('select state from sessions where run_id=?',
                                     (root.name,)).fetchone()[0])
        return dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns,
                    status=state['research_status'], pending=state['pending'],
                    counts={t: db.execute('select count(*) from ' + t).fetchone()[0]
                            for t in ('events', 'artifacts', 'calls')})


def norm(x):
    return float(np.linalg.norm(x))


def maxabs(x):
    return float(np.max(np.abs(x), initial=0.))


class Diagnosis:
    def __init__(self, source, paired, output):
        self.source, self.output = source, output
        assert not output.is_relative_to(source) and not output.is_relative_to(paired)
        self.output.mkdir(parents=True, exist_ok=True)
        self.paired = read(paired / 'result.json')
        self.backend = next(source.glob('sessions/*/executions/' +
            '3c78b551965f443abd966bfb68b969dd/backend'))
        b = self.backend
        self.physics = read(b / 'resolved_physics.json')
        self.scene = read(b / 'experiment_scene.json')
        self.spec = read(b / 'control_spec.json')
        self.updates = read(b / 'nmpc_updates.json')
        self.rows = json.loads(gzip.decompress((b / 'trajectory.json.gz').read_bytes()))
        self.commands = read(b / 'actual_commands.json')
        self.basis = ResolvedGVSBasis.model_validate(self.spec['projector']['resolved_basis'])
        self.mapping = discretization_jacobian(self.physics, self.basis)
        self.inverse = np.linalg.pinv(self.mapping)
        self.model = mujoco.MjModel.from_xml_path(str(b / 'robot.xml'))
        self.data = mujoco.MjData(self.model)
        jids = [self.model.joint(n).id for n in self.physics['dofs']]
        self.qi = self.model.jnt_qposadr[jids]
        self.vi = self.model.jnt_dofadr[jids]
        self.aids = [self.model.actuator(t['entity'] + '_direct_tension').id
                     for t in self.physics['tendons']]
        self.tids = [self.model.tendon(t['entity']).id for t in self.physics['tendons']]
        self.tip = self.model.site('tip_site').id
        self.ledger = dict(mujoco_model_load=1, mujoco_steps=0, mujoco_fwd_position=0, mujoco_forward=0,
                           mujoco_site_jacobian=0, mujoco_full_mass=0,
                           mujoco_body_com_jacobian=0,
                           gvs_graph_build=0, gvs_motion=0, gvs_dynamics=0,
                           gvs_implicit_residual=0,
                           gvs_root=0, provider=0, ipopt=0, nmpc=0, ppo=0, study=0)
        self.result = dict(source_backend=str(b), paired_results=str(paired),
                           physics_identity=self.physics['identity'],
                           projector=self.spec['projector']['id'],
                           basis=self.basis.model_dump(mode='json'),
                           runtime=dict(python=sys.version, mujoco=mujoco.__version__, casadi=ca.__version__),
                           ledger=self.ledger, store_before=audit(source))
        assert self.result['store_before']['status'] == 'stopped'
        assert self.result['store_before']['pending'] is None
        assert self.model.nq == self.model.nv == 48 and self.model.na == 0
        assert self.basis.dimension == 12
        assert self.physics['identity'] == self.scene['physics_identity']
        assert self.physics['identity'] == read(b / 'compiled_physics.json')['physics_identity']
        assert Path(self.paired['preflight']['source_backend']).resolve() == b.resolve()
        assert np.array_equal(sorted(self.qi), np.arange(48))
        assert np.array_equal(sorted(self.vi), np.arange(48))
        assert self.spec['projector']['id'] == 'backend_discrete_to_gvs_integrated_v2'
        assert self.scene['control']['tension_execution_mode'] == 'ideal_tension'
        assert not self.scene['forces']
        for k, row in enumerate(self.rows):
            assert abs(row['time_s'] - (k + 1) * .01) < 1e-12
            assert row['tension_n'] == self.commands[k]['desired_tension_n']
            assert row['tension_n'] == self.updates[k]['complete_update_record']['actual_applied_action_n']
        assert maxabs(np.asarray(self.paired['reconstruction']['pre']['qvel_rad_s']) - self.rows[33]['qvel_rad_s']) == 0
        assert maxabs(np.asarray(self.paired['A']['sample']['qpos_rad']) - self.rows[34]['qpos_rad']) == 0
        assert maxabs(np.asarray(self.paired['A']['sample']['qvel_rad_s']) - self.rows[34]['qvel_rad_s']) == 0
        self.states = {}
        self.functions = None

    def prepare_functions(self):
        if self.functions is not None:
            return
        params = GVSModelParameters(basis=self.basis.specification)
        start = time.perf_counter()
        system = GVSModel(params).build_system(RobotDescription.model_validate(self.spec['robot']),
            params, None, SystemContext(x0=self.updates[34]['measured_initial_state'],
            u0=self.spec['reference']['u0'], scene=self.spec['task']['environment']))
        self.functions = functions_for(expression_from_system(system))
        self.ledger['gvs_graph_build'] += 1
        self.result['graph_wall_s'] = self.result.get('graph_wall_s',0.) + time.perf_counter() - start
        q = self.functions.q_symbol
        v = ca.MX.sym('rate', 12)
        mount = self.spec['task']['environment']['data']['mount']
        tip = ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])) @ self.functions.tip_position_expression + ca.DM(mount['position_m'])
        self.motion_fn = ca.Function('s145_motion', [q, v], [tip, ca.jacobian(tip, q) @ v])

    def motion(self, x):
        self.prepare_functions()
        self.ledger['gvs_motion'] += 1
        return tuple(np.asarray(z).ravel() for z in self.motion_fn(x[:12], x[12:]))

    def position(self, q, v):
        self.data.qpos[self.qi] = q
        self.data.qvel[self.vi] = v
        mujoco.mj_fwdPosition(self.model, self.data)
        self.ledger['mujoco_fwd_position'] += 1
        jac = np.zeros((3, self.model.nv))
        mujoco.mj_jacSite(self.model, self.data, jac, None, self.tip)
        self.ledger['mujoco_site_jacobian'] += 1
        return self.data.site_xpos[self.tip].copy(), jac[:, self.vi]

    def projection(self):
        t = self.mapping
        singular = np.linalg.svd(t, compute_uv=False)
        self.result['mapping'] = dict(rank=int(np.linalg.matrix_rank(t)), shape=t.shape,
            singular_values=singular, left_inverse_error=maxabs(self.inverse @ t - np.eye(12)),
            condition_number=float(np.linalg.cond(t)))
        samples, cells = [], []
        for index in (4, 14, *range(28, 35)):
            row = self.rows[index]
            q, v = np.asarray(row['qpos_rad']), np.asarray(row['qvel_rad_s'])
            pr = project(self.physics, self.basis, q, v)
            x = np.r_[pr['q_gvs'], pr['qdot_gvs']]
            self.states[index] = x
            qhat, vhat = discretize(self.physics, self.basis, x[:12], x[12:])
            assert maxabs(x[:12] - self.inverse @ q) < 1e-10
            assert maxabs(x[12:] - self.inverse @ v) < 1e-10
            reprojection = project(self.physics, self.basis, qhat, vhat)
            assert maxabs(np.r_[reprojection['q_gvs'], reprojection['qdot_gvs']] - x) < 1e-10
            if index < 34:
                assert maxabs(x - self.updates[index+1]['measured_initial_state']) < 1e-10
            pos, jac = self.position(q, v)
            a, b = jac @ v, jac @ vhat
            pc, c = self.motion(x)
            pd, jd = self.position(qhat, vhat)
            d = jd @ vhat
            assert maxabs(pos - row['tip_m']) < 1e-10
            assert maxabs(a - row['tip_velocity_m_s']) < 1e-10
            assert maxabs((a-b) + (b-c) - (a-c)) < 1e-14
            groups = []
            for local in self.basis.segments:
                parts = [self.physics['parts'][i] for i in self.physics['entity_map'][local.segment]['bodies']]
                for axis in range(2):
                    component = np.zeros(48)
                    residual_angles, residual_rates, original_rates = [], [], []
                    for cell_index, part in enumerate(parts):
                        ids = part['dofs']
                        rotation = rx(part['section_axis_rad'])[1:, 1:]
                        dq = rotation @ (q[ids] - qhat[ids])
                        dv = rotation @ (v[ids] - vhat[ids])
                        vv = rotation @ v[ids]
                        residual_angles.append(dq[axis])
                        residual_rates.append(dv[axis])
                        original_rates.append(vv[axis])
                        component[ids] = rotation.T[:, axis] * dv[axis]
                        cells.append(dict(time_s=row['time_s'], segment=local.segment,
                            cell=cell_index, normalized_center=(cell_index+.5)/len(parts),
                            axis=('y', 'z')[axis], cell_length_m=part['length_m'],
                            principal_q_rad=q[ids][axis], principal_qhat_rad=qhat[ids][axis],
                            principal_v_rad_s=v[ids][axis], principal_vhat_rad_s=vhat[ids][axis],
                            segment_q_rad=(rotation @ q[ids])[axis],
                            segment_qhat_rad=(rotation @ qhat[ids])[axis],
                            segment_v_rad_s=vv[axis], segment_vhat_rad_s=(rotation @ vhat[ids])[axis],
                            segment_dq_rad=dq[axis], segment_dv_rad_s=dv[axis],
                            curvature_residual_rad_m=dq[axis]/part['length_m'],
                            curvature_rate_residual_rad_m_s=dv[axis]/part['length_m']))
                    groups.append(dict(segment=local.segment, axis=('y','z')[axis],
                        joint_angle_residual_norm_rad=norm(residual_angles),
                        joint_rate_norm_rad_s=norm(original_rates),
                        joint_rate_residual_norm_rad_s=norm(residual_rates),
                        joint_rate_residual_max_rad_s=maxabs(residual_rates),
                        lost_tip_velocity_m_s=jac @ component))
            samples.append(dict(time_s=row['time_s'], input_interval_s=[row['solver_time_s'],row['time_s']],
                tension_n=row['tension_n'], qpos_rad=q, qvel_rad_s=v, represented_qpos_rad=qhat,
                represented_qvel_rad_s=vhat, state=x, projection=pr,
                rate_residual_orthogonality=maxabs(t.T @ (v-vhat)),
                A_m_s=a, B_m_s=b, C_m_s=c, D_m_s=d,
                A_minus_B_m_s=a-b, B_minus_C_m_s=b-c, A_minus_C_m_s=a-c,
                A_minus_B_norm_m_s=norm(a-b), B_minus_C_norm_m_s=norm(b-c),
                A_minus_C_norm_m_s=norm(a-c), B_minus_D_norm_m_s=norm(b-d),
                D_minus_C_norm_m_s=norm(d-c), position_C_minus_A_m=pc-pos,
                position_D_minus_A_m=pd-pos, position_C_minus_D_m=pc-pd, groups=groups))
        self.result['projection'] = samples
        with (self.output / 'cells.csv').open('w', newline='', encoding='utf8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(cells[0]))
            writer.writeheader()
            writer.writerows(cells)
        write(self.output / 'projection.json', self.result)
        print('A complete', [(s['time_s'],s['A_minus_B_norm_m_s'],s['B_minus_C_norm_m_s']) for s in samples], flush=True)

    def finish(self):
        self.result['store_after'] = audit(self.source)
        assert self.result['store_after'] == self.result['store_before']
        self.result['store_unchanged'] = True
        write(self.output / 'result.json', self.result)
        print('ledger', self.ledger, flush=True)

    def dynamics_terms(self, q, v, u, sample_time):
        """Zero-time forward on private MjData; all forces are from this input."""
        m, d, t = self.model, self.data, self.mapping
        d.time = sample_time  # Set saved sample time; never advance physical time.
        d.qpos[self.qi], d.qvel[self.vi], d.ctrl[self.aids] = q, v, u
        mujoco.mj_forward(m, d)
        self.ledger['mujoco_forward'] += 1
        assert d.time == sample_time and d.ncon == 0
        assert maxabs(-d.actuator_force[self.aids] - u) < 1e-12
        mass = np.empty((m.nv, m.nv))
        mujoco.mj_fullM(m, d, mass)
        self.ledger['mujoco_full_mass'] += 1
        mass = mass[np.ix_(self.vi, self.vi)]
        gravity = np.zeros(m.nv)
        jac = np.zeros((3, m.nv))
        for body in range(1, m.nbody):
            mujoco.mj_jacBodyCom(m, d, jac, None, body)
            self.ledger['mujoco_body_com_jacobian'] += 1
            gravity += jac.T @ (m.body_mass[body] * m.opt.gravity)
        elastic = m.jnt_stiffness[[m.joint(n).id for n in self.physics['dofs']]] * (q-m.qpos_spring[self.qi])
        damping = m.dof_damping[self.vi] * v
        assert maxabs(d.qfrc_passive[self.vi] + elastic + damping) < 1e-12
        acceleration = d.qacc[self.vi].copy()
        rhs = d.qfrc_actuator[self.vi] + d.qfrc_passive[self.vi] - d.qfrc_bias[self.vi]
        assert maxabs(mass @ acceleration - rhs) < 1e-10
        tendon_jac = np.zeros((m.ntendon, m.nv))
        if d.ten_J.size == m.ntendon*m.nv:
            tendon_jac[:] = d.ten_J.reshape(m.ntendon, m.nv)
        else:
            layout = m if hasattr(m, 'ten_J_rowadr') else d
            for k in range(m.ntendon):
                start, count = layout.ten_J_rowadr[k], layout.ten_J_rownnz[k]
                tendon_jac[k, layout.ten_J_colind[start:start+count]] = d.ten_J[start:start+count]
        length_jac = tendon_jac[self.tids][:, self.vi]
        assert maxabs(-length_jac.T @ u - d.qfrc_actuator[self.vi]) < 1e-12
        reduced_mass = t.T @ mass @ t
        return dict(qacc_rad_s2=acceleration,
            projected_qacc_rad_m_s2=self.inverse @ acceleration,
            constrained_qacc_rad_m_s2=np.linalg.solve(reduced_mass, t.T @ rhs),
            mass_matrix=reduced_mass, elastic_force=t.T @ elastic,
            damping_force=t.T @ damping, gravity_force=t.T @ gravity[self.vi],
            velocity_bias=t.T @ (d.qfrc_bias[self.vi] + gravity[self.vi]),
            tendon_generalized_force=t.T @ d.qfrc_actuator[self.vi],
            tendon_length_jacobian=length_jac @ t,
            tendon_lengths_m=d.ten_length[self.tids].copy(),
            balance_residual_nm=maxabs(mass @ acceleration-rhs))

    def dynamics(self):
        # Stage A must have been completed and inspected before this method.
        assert self.result['projection'] and self.result['mapping']['rank'] == 12
        t = self.mapping
        comparisons = []
        for start_index in (32, 33):
            end_index = start_index+1
            before, after = self.rows[start_index], self.rows[end_index]
            initial, final = self.states[start_index], self.states[end_index]
            if end_index == 34:
                saved = self.paired['predictions']['A']['one']
                pred = np.asarray(saved['state'])
                assert self.paired['A']['actual_tension_n'] == after['tension_n']
                half = np.asarray(self.paired['predictions']['A']['two_half']['state'])
            else:
                saved = self.updates[end_index]['one_step_prediction']
                pred = np.asarray(saved['state'])
                half = None
            record = self.updates[end_index]['complete_update_record']
            assert maxabs(initial-record['measured_state']) < 1e-10
            assert record['actual_applied_action_n'] == after['tension_n']
            assert record['tendon_order'] == [z['entity'] for z in self.physics['tendons']]
            pp, pv = self.motion(pred)
            ip, iv = self.motion(initial)
            fp, fv = self.motion(final)
            rows = []
            scales = np.asarray(record['state_scales'])
            for i, name in enumerate(self.basis.coordinate_order):
                rows.append(dict(coordinate=name, q_initial_rad_m=initial[i],
                    q_final_rad_m=final[i], q_predicted_rad_m=pred[i],
                    observed_delta_q_rad_m=final[i]-initial[i],
                    predicted_delta_q_rad_m=pred[i]-initial[i],
                    observed_delta_rate_rad_m_s=final[12+i]-initial[12+i],
                    predicted_delta_rate_rad_m_s=pred[12+i]-initial[12+i],
                    rate_error_rad_m_s=pred[12+i]-final[12+i],
                    scaled_state_error=(pred-final)[[i,12+i]]/scales[[i,12+i]]))
            comparisons.append(dict(interval_s=[before['time_s'],after['time_s']],
                actual_tension_n=after['tension_n'], initial=initial, endpoint_projection=final,
                saved_prediction=pred, saved_half_prediction=half, modes=rows,
                state_scales=scales, q_error_norm_rad_m=norm(pred[:12]-final[:12]),
                rate_error_norm_rad_m_s=norm(pred[12:]-final[12:]),
                actual_tip_velocity_change_m_s=np.asarray(after['tip_velocity_m_s'])-before['tip_velocity_m_s'],
                projected_tip_velocity_change_m_s=fv-iv,
                predicted_tip_velocity_change_m_s=pv-iv,
                predicted_minus_projected_endpoint_velocity_m_s=pv-fv,
                predicted_minus_actual_endpoint_velocity_m_s=pv-after['tip_velocity_m_s']))
        self.result['evolution'] = comparisons
        # Saved S144 qacc is after its pre-control forward with the previous u.
        before = self.rows[33]
        q, v = np.asarray(before['qpos_rad']), np.asarray(before['qvel_rad_s'])
        previous_u = np.asarray(before['tension_n'])
        final_u = np.asarray(self.rows[34]['tension_n'])
        previous = self.dynamics_terms(q, v, previous_u, before['engine_time_s'])
        saved_acc = np.asarray(self.paired['reconstruction']['internal']['qacc'])[self.vi]
        assert maxabs(saved_acc-previous['qacc_rad_s2']) < 1e-10
        assert self.paired['reconstruction']['internal']['ctrl'] == before['tension_n']
        self.result['acceleration_phase'] = dict(
            saved_qacc_input_n=previous_u, current_interval_input_n=final_u,
            saved_previous_input_match_rad_s2=maxabs(saved_acc-previous['qacc_rad_s2']),
            saved_is_current_input=False, previous_input_terms=previous,
            trajectory_has_qacc=any('qacc' in key for key in self.rows[0]))
        mechanics = []
        for index in (32, 33, 34):
            row, x = self.rows[index], self.states[index]
            # At .33 use original .33-.34 input; at .34/.35 use original final input.
            u = np.asarray(self.rows[min(index+1,34)]['tension_n'])
            q, v = np.asarray(row['qpos_rad']), np.asarray(row['qvel_rad_s'])
            original = self.dynamics_terms(q,v,u,row['engine_time_s'])
            represented = self.dynamics_terms(t @ x[:12],t @ x[12:],u,row['engine_time_s'])
            self.ledger['gvs_dynamics'] += 1
            gvs = {k: np.asarray(z).squeeze() for k,z in self.functions.evaluate(x,u).items()}
            terms = []
            for key in ('mass_matrix','elastic_force','damping_force','gravity_force',
                        'velocity_bias','tendon_generalized_force','tendon_length_jacobian'):
                error = represented[key]-gvs[key]
                terms.append(dict(term=key, represented_minus_gvs_norm=norm(error),
                    relative_to_represented=norm(error)/max(norm(represented[key]),1e-30)))
            mechanics.append(dict(time_s=row['time_s'], input_n=u, original=original,
                represented=represented, gvs=gvs, term_comparison=terms,
                original_minus_represented_projected_acceleration=original['projected_qacc_rad_m_s2']-represented['projected_qacc_rad_m_s2'],
                full_minus_constrained_acceleration=represented['projected_qacc_rad_m_s2']-represented['constrained_qacc_rad_m_s2'],
                constrained_minus_gvs_acceleration=represented['constrained_qacc_rad_m_s2']-gvs['qdd']))
        self.result['mechanics'] = mechanics
        self.result['acceleration_phase']['saved_minus_current_input_qacc_rad_s2'] = saved_acc-mechanics[1]['original']['qacc_rad_s2']
        self.result['difference_estimate'] = dict(interval_s=[.34,.35],
            meaning='finite-difference interval average, not instantaneous acceleration',
            projected_acceleration_rad_m_s2=(self.states[34][12:]-self.states[33][12:])/.01,
            predicted_average_acceleration_rad_m_s2=(comparisons[1]['saved_prediction'][12:]-self.states[33][12:])/.01)
        print('B complete', [(z['interval_s'],z['rate_error_norm_rad_m_s']) for z in comparisons], flush=True)

    def attribution(self):
        """Separate loss of velocity from loss of configuration, without stepping."""
        detail = []
        for index, existing in zip((32,33), self.result['mechanics'][:2]):
            row, x = self.rows[index], self.states[index]
            q = np.asarray(row['qpos_rad'])
            u = np.asarray(self.rows[index+1]['tension_n'])
            velocity_only = self.dynamics_terms(q,self.mapping @ x[12:],u,row['engine_time_s'])
            original, reconstructed = existing['original'], existing['represented']
            detail.append(dict(time_s=row['time_s'], velocity_only=velocity_only,
                projected_acceleration_change_from_velocity_replacement_rad_m_s2=
                    velocity_only['projected_qacc_rad_m_s2']-original['projected_qacc_rad_m_s2'],
                projected_acceleration_change_from_configuration_replacement_rad_m_s2=
                    reconstructed['projected_qacc_rad_m_s2']-velocity_only['projected_qacc_rad_m_s2']))
        self.result['information_loss_dynamics'] = detail
        m, p = self.model, self.physics
        bids = [m.body(part['entity']).id for part in p['parts']]
        jids = [m.joint(n).id for n in p['dofs']]
        k = np.concatenate([a['stiffness_nm_rad'] for a in p['parts']])
        damping = np.concatenate([a['damping_nm_s_rad'] for a in p['parts']])
        natural = np.concatenate([a['natural_rad'] for a in p['parts']])
        inertia_errors = []
        for part,bid in zip(p['parts'],bids):
            rotation = quaternion_wxyz_to_rotation(m.body_iquat[bid])
            inertia_errors.append(maxabs(rotation @ np.diag(m.body_inertia[bid]) @ rotation.T-
                                         part['inertia_com_local_kg_m2']))
        parameters = dict(mass_kg=maxabs(m.body_mass[bids]-np.array([a['mass_kg'] for a in p['parts']])),
            com_m=maxabs(m.body_ipos[bids]-np.array([a['com_local_m'] for a in p['parts']])),
            inertia_kg_m2=max(inertia_errors),
            stiffness_nm_rad=maxabs(m.jnt_stiffness[jids]-k),
            damping_nm_s_rad=maxabs(m.dof_damping[self.vi]-damping),
            natural_rad=maxabs(m.qpos_spring[self.qi]-natural),
            gravity_m_s2=maxabs(m.opt.gravity-np.array(self.scene['gravity'])),
            armature_kg_m2=maxabs(m.dof_armature), frictionloss_nm=maxabs(m.dof_frictionloss))
        assert max(parameters.values()) < 1e-12
        assert np.all(m.actuator_gainprm[self.aids,0] == -1)
        assert np.all(m.actuator_gear[self.aids,0] == 1)
        assert m.actuator_trnid[self.aids,0].tolist() == self.tids
        self.result['xml_resolved_physics_max_differences'] = parameters
        print('additional attribution complete', flush=True)

    def verify_force_balance(self):
        """Check the actual implicit integrator expression against explicit terms."""
        self.prepare_functions()
        errors = []
        for entry, index in zip(self.result['mechanics'],(32,33,34)):
            x, u = self.states[index], entry['input_n']
            self.ledger['gvs_implicit_residual'] += 1
            residual = np.asarray(self.functions.implicit_residual(x,u,entry['gvs']['qdd'])).ravel()
            assert maxabs(residual) < 1e-10
            errors.append(dict(time_s=entry['time_s'], max_force_residual_nm2=maxabs(residual)))
        self.result['implicit_explicit_consistency'] = errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO.parent / 's142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023')
    parser.add_argument('--paired', type=Path, default=REPO.parent / 's144-terminal-control-diagnosis/runs/s144')
    parser.add_argument('--output', type=Path, default=REPO / 'runs/s145')
    parser.add_argument('--stage', choices=('projection','dynamics','attribution','all'), default='all')
    args = parser.parse_args()
    diagnosis = Diagnosis(args.source.resolve(), args.paired.resolve(), args.output.resolve())
    if args.stage in ('dynamics','attribution'):
        previous = read(args.output / 'result.json')
        assert previous['store_before'] == diagnosis.result['store_before']
        assert previous['physics_identity'] == diagnosis.result['physics_identity']
        if args.stage == 'dynamics':
            assert 'mechanics' not in previous
        else:
            assert 'information_loss_dynamics' not in previous
        for key,value in previous['ledger'].items():
            diagnosis.ledger[key] += value
        previous['ledger'] = diagnosis.ledger
        diagnosis.result = previous
        diagnosis.states = {round(s['time_s']/.01)-1:np.asarray(s['state']) for s in previous['projection']}
    else:
        diagnosis.projection()
    if args.stage in ('dynamics','all'):
        diagnosis.dynamics()
    if args.stage in ('attribution','all'):
        diagnosis.attribution()
        diagnosis.verify_force_balance()
    diagnosis.finish()


if __name__ == '__main__':
    main()
