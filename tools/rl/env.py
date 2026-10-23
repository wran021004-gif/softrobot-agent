"""Candidate-selected physical observations and ideal-tension actions."""
import hashlib
import json
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

STATE_SPEC = mujoco.mjtState.mjSTATE_INTEGRATION
WARNINGS = (mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL,
            mujoco.mjtWarning.mjWARN_BADQACC)


class NumericalFailure(RuntimeError):
    """A failed physical transition; never returned as a valid PPO sample."""


def reward_terms(weights, info, before, delta_tension, limits, position_scale, speed_scale, holding=False):
    """Recomputable training preference from saved physical signals, no evaluator."""
    if info.get('numerical_failure'):
        return dict(numerical_failure=weights['failure_penalty'])
    terms = dict(position=-weights['position']*(info['position_error_m']/position_scale)**2,
        holding_speed=-weights['holding_speed']*(info['speed_m_s']/speed_scale)**2 if holding else 0.,
        smoothness=-weights['smoothness']*float(np.mean((np.asarray(delta_tension)/limits)**2)))
    if 'path_progress_m' in info:
        delta=(info['path_progress_m']-before['path_progress_m'])/position_scale
        terms.update(path_error=-weights.get('path_error',0.)*(info['path_error_m']/position_scale)**2,
            progress=weights.get('progress',0.)*max(delta,0.),
            regression=-weights.get('regression',0.)*max(-delta,0.))
    return terms


class TensionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config, trace_dir=None, failure_mode="raise", guard=None):
        self.config = config
        self.guard = guard
        self.mode = mode = config["mode"]
        if mode not in ("residual", "direct"):
            raise ValueError("Only direct and residual modes are supported")
        self.saved = config['task']
        self.tracking = self.saved['family'] == 'task.tracking'
        if self.saved['family'] not in ('task.reach','task.tracking'):
            raise ValueError('Unsupported RL task')
        if self.tracking:
            from tools.research_tasks import task_adapter
            self.task_reference = task_adapter(dict(task=self.saved['original']))
            if self.task_reference.control_reference()['kind'] != 'free_progress':
                raise ValueError('RL_TIMED_TRACKING_UNSUPPORTED')
        candidate=config.get('candidate')
        control=config.get('control_object')
        if not candidate or not control:
            raise ValueError('Explicit candidate XML/assets and control_object required')
        if control['semantics'] != 'ideal_tension':
            raise ValueError('Unsupported length-servo control; ideal_tension required')
        xml=candidate['xml']
        if hashlib.sha256(xml.encode()).hexdigest()!=candidate['sha256']:
            raise ValueError('Frozen candidate XML digest mismatch')
        self.xml_source=candidate['identity']
        import base64
        assets={name:base64.b64decode(body) for name,body in candidate.get('assets',{}).items()}
        self.model=m=mujoco.MjModel.from_xml_string(xml,assets=assets)
        self.data=mujoco.MjData(m)
        joints=[m.joint(name).id for name in control['joint_names']]
        if not joints or len(set(joints))!=len(joints) or any(m.jnt_type[j]!=mujoco.mjtJoint.mjJNT_HINGE for j in joints):
            raise ValueError('Only unique selected hinge robot joints are supported')
        self.qpos_indices=m.jnt_qposadr[joints]
        self.qvel_indices=m.jnt_dofadr[joints]
        self.tendons=control['tendon_names']
        self.actuators=a=[m.actuator(name).id for name in control['actuator_names']]
        tendon_ids=[m.tendon(name).id for name in self.tendons]
        self.channels=len(a)
        if (not a or len(set(a))!=len(a) or len(set(tendon_ids))!=len(a)
                or not np.all(m.actuator_trntype[a]==mujoco.mjtTrn.mjTRN_TENDON)
                or m.actuator_trnid[a,0].tolist()!=tendon_ids
                or not np.all(m.actuator_gaintype[a]==mujoco.mjtGain.mjGAIN_FIXED)
                or not np.all(m.actuator_biastype[a]==mujoco.mjtBias.mjBIAS_NONE)
                or not np.all(m.actuator_dyntype[a]==mujoco.mjtDyn.mjDYN_NONE)
                or not np.all(m.actuator_gainprm[a,0]==-1)
                or not np.all(m.actuator_gear[a,0]==1)
                or not np.all(m.actuator_ctrllimited[a]) or not np.all(m.actuator_forcelimited[a])):
            raise ValueError('Selected actuators do not implement Newton-valued ideal tension with negative force')
        self.lower,self.upper=m.actuator_ctrlrange[a].T.copy()
        if (not np.isfinite(m.actuator_ctrlrange[a]).all() or np.any(self.lower<0) or np.any(self.upper<=self.lower)
                or not np.allclose(m.actuator_forcerange[a],np.stack((-self.upper,-self.lower),axis=1),rtol=0,atol=1e-12)):
            raise ValueError('Tension control/force limits mismatch')
        self.target=np.asarray(self.saved['original']['goal']['data']['vertices_m'][-1]
                               if self.tracking else self.saved['target_m'],dtype=float)
        self.control_dt=float(self.saved['control_period_s'])
        self.horizon=int(self.saved['command_intervals'])
        self.hold_steps=[] if self.tracking else self.saved['acceptance']['holding_steps']
        self.substeps=round(self.control_dt/m.opt.timestep)
        if (self.substeps<1 or abs(self.substeps*m.opt.timestep-self.control_dt)>1e-12
                or abs(self.horizon*self.control_dt-self.saved['duration_s'])>1e-12):
            raise ValueError('Candidate physics timestep must exactly divide frozen task timing')
        self.integrator=int(m.opt.integrator)
        self.reward=config['reward']
        from tools.rl.run import validate_reward
        validate_reward(self.reward)
        if self.tracking and self.reward['holding_speed']:
            raise ValueError('TRACKING_HAS_NO_HOLDING_SPEED_REWARD')
        if not self.tracking and any(self.reward.get(k,0.) for k in ('path_error','progress','regression')):
            raise ValueError('PATH_REWARD_REQUIRES_GEOMETRIC_TRACKING')
        self.position_scale=config['observation']['position_scale_m']
        self.speed_scale=config['observation']['speed_scale_m_s']
        self.failure_penalty=self.reward['failure_penalty']
        self.residual_scale=np.broadcast_to(np.asarray(config['action']['residual_scale_n'],dtype=float),(self.channels,)).copy()
        if not all(np.isfinite(v).all() and np.all(np.asarray(v)>0) for v in (self.residual_scale,self.position_scale,self.speed_scale)):
            raise ValueError('Observation and residual scales must be finite and positive')
        self.reference=None
        if mode=='residual':
            ref=config.get('reference')
            if (not ref or ref['candidate_identity']!=candidate['identity'] or ref['task_identity']!=candidate['task_identity']
                    or ref['tendon_order']!=self.tendons or ref['control_period_s']!=self.control_dt):
                raise ValueError('Residual requires candidate/task/order/timing-compatible tension reference')
            path=Path(ref['path'])
            if hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:
                raise ValueError('Frozen reference digest mismatch')
            with np.load(path,allow_pickle=False) as refs:
                self.reference=refs['saved_tensions_n'].copy()
            if (self.reference.shape!=(self.horizon,self.channels) or not np.isfinite(self.reference).all()
                    or np.any(self.reference<self.lower) or np.any(self.reference>self.upper)):
                raise ValueError('Invalid complete tension reference')
        if failure_mode not in ("raise", "terminal"):
            raise ValueError("failure_mode must be raise or terminal")
        self.failure_mode = failure_mode
        self.trace_dir = Path(trace_dir) if trace_dir else None
        self.counts = dict(attempted_actions=0, completed_actions=0, attempted_physics_steps=0,
                           complete_episodes=0, failed_episodes=0)
        self.episode = 0
        self.stable_captures = 0
        self.failure = None
        self.site = m.site(control["tip_site"]).id
        self.jacobian = np.zeros((3, m.nv))
        self.action_space = gym.spaces.Box(-1.0, 1.0, (self.channels,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(
            -np.inf, np.inf, (len(joints)*2 + 7 + self.channels + int(self.tracking),), dtype=np.float32)
        self.k = self.horizon  # reset is required before step

    def settings(self):
        return dict(mode=self.mode,candidate=self.config['candidate']['identity'],task=self.config['candidate']['task_identity'],
            control_object=self.config['control_object'],tension_limits_n=np.stack((self.lower,self.upper),axis=1).tolist(),
            residual_scale_n=self.residual_scale.tolist(),physics_dt_s=float(self.model.opt.timestep),
            control_dt_s=self.control_dt,substeps=self.substeps,horizon=self.horizon,holding_steps=self.hold_steps,
            observation_dimension=self.observation_space.shape[0],action_dimension=self.channels,
            reward=self.reward,reference=self.config.get('reference'))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        for field, address, destination in (
                ("qpos_rad", self.model.jnt_qposadr, self.data.qpos),
                ("qvel_rad_s", self.model.jnt_dofadr, self.data.qvel)):
            for name, value in self.saved["initializer"][field].items():
                if name not in self.config['control_object']['joint_names']:
                    raise ValueError('Initializer names must belong to selected robot joints')
                destination[address[self.model.joint(name).id]] = value
        self.k = 0
        self.path_segment = 0
        self.needs_reset = False
        self.episode += 1
        self.episode_records = []
        self.phase_states = []
        self.failure = None
        self.previous_tension = np.zeros(self.channels)
        self.command = np.zeros(self.channels)
        self.clipped = np.zeros(self.channels, dtype=bool)
        mujoco.mj_forward(self.model, self.data)
        return self._observe()

    def map_action(self, action):
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (self.channels,) or not np.isfinite(action).all() or np.any(abs(action) > 1):
            raise ValueError("Expected selected-channel finite actions in [-1, 1]")
        raw = (self.lower + (self.upper-self.lower)*(action+1)/2 if self.mode == "direct"
               else self.reference[self.k] + self.residual_scale * action)
        tension = np.clip(raw, self.lower, self.upper)
        return tension, raw != tension

    def _observe(self):
        # step/reset synchronize kinematics before evaluating the world Jacobian.
        mujoco.mj_jacSite(self.model, self.data, self.jacobian, None, self.site)
        position = self.data.site_xpos[self.site].copy()
        velocity = self.jacobian @ self.data.qvel
        error = self.target - position
        path_info = {}
        if self.tracking:
            from extensions.reference.implementation import project_polyline
            vertices=self.saved['original']['goal']['data']['vertices_m']
            distance,progress=project_polyline([position],vertices)
            step=self.saved['original']['evaluator']['parameters']['data']['geometry_step_m']
            local=self.task_reference.local_path_reference(position,self.path_segment,3*step,step)
            self.path_segment=local['segment']
            error=np.asarray(local['position_m'])-position
            path_info=dict(path_error_m=float(distance[0]),path_progress_m=float(progress[0]))
        observation = np.concatenate((
            self.data.qpos[self.qpos_indices], self.data.qvel[self.qvel_indices], error / self.position_scale,
            velocity / self.speed_scale, self.previous_tension / self.upper,
            [self.k / self.horizon])).astype(np.float32)
        if self.tracking:
            observation=np.r_[observation,path_info['path_progress_m']/self.position_scale].astype(np.float32)
        info = dict(control_step=self.k, time_s=self.k * self.control_dt,
                    engine_time_s=float(self.data.time), tip_m=position,
                    tip_velocity_m_s=velocity, position_error_m=float(np.linalg.norm(self.target-position)),
                    speed_m_s=float(np.linalg.norm(velocity)),
                    applied_tension_n=self.previous_tension.copy(),
                    commanded_tension_n=self.command.copy(), clipped=self.clipped.copy(),
                    saturated=(self.command == self.lower) | (self.command == self.upper))
        info.update(path_info)
        return observation, info

    def get_state(self):
        state = np.empty(mujoco.mj_stateSize(self.model, STATE_SPEC))
        mujoco.mj_getState(self.model, self.data, state, STATE_SPEC)
        return state

    def fail(self, record, start_state, pre_step_state, substep, warnings):
        self.counts["failed_episodes"] += 1
        self.failure = dict(record, failed_substep=substep, warnings=warnings,
                            pre_step_time_s=float(pre_step_state[0]),
                            returned_engine_time_s=float(self.data.time),
                            state_spec=int(STATE_SPEC), counts=self.counts.copy(),
                            config_sha256=hashlib.sha256(json.dumps(self.config,sort_keys=True).encode()).hexdigest(),
                            candidate_identity=self.config["candidate"]["identity"])
        if self.trace_dir:
            self.trace_dir.mkdir(parents=True, exist_ok=True)
            prefix = self.trace_dir / f"failure_episode_{self.episode}"
            prefix.with_suffix(".json").write_text(
                json.dumps(self.failure, indent=2, allow_nan=False), encoding="utf-8")
            np.savez_compressed(prefix.with_suffix(".npz"),
                                interval_start_state=start_state, pre_step_state=pre_step_state,
                                actions=np.array([r["action"] for r in self.episode_records]),
                                tensions=np.array([r["tension_n"] for r in self.episode_records]))
            prefix.with_suffix(".jsonl").write_text(
                "\n".join(json.dumps(r, allow_nan=False) for r in self.episode_records) + "\n",
                encoding="utf-8")
        if self.failure_mode == "raise":
            raise NumericalFailure("MuJoCo numerical failure: " + ", ".join(warnings))
        # A terminal surrogate at the last valid boundary, never the engine's reset state.
        mujoco.mj_setState(self.model, self.data, start_state, STATE_SPEC)
        self.k = record["episode_action"] - 1
        self.previous_tension = np.array(record["tension_n"]) - np.array(record["delta_tension_n"])
        mujoco.mj_forward(self.model, self.data)
        observation, info = self._observe()
        if not np.isfinite(observation).all():
            raise NumericalFailure("No valid observation for failure terminal")
        self.needs_reset = True
        info.update(record, numerical_failure=True, valid_physical_transition=False,
                    counts=self.counts.copy(), failure=self.failure,
                    reward=self.failure_penalty,
                    reward_terms=dict(position=0.0, holding_speed=0.0, smoothness=0.0,
                                      numerical_failure=self.failure_penalty))
        return observation, self.failure_penalty, True, False, info

    def step(self, action):
        if self.guard:
            self.guard()
        if self.k >= self.horizon or self.needs_reset:
            raise RuntimeError("Call reset before stepping a new episode")
        self.command, self.clipped = self.map_action(action)
        self.counts["attempted_actions"] += 1
        previous = self.previous_tension.copy()
        start_state = self.get_state()
        _, before_info = self._observe()
        record = dict(episode_number=self.episode, cumulative_action=self.counts["attempted_actions"],
                      episode_action=self.k + 1, action=np.asarray(action).tolist(),
                      tension_n=self.command.tolist(), delta_tension_n=(self.command-previous).tolist(),
                      clipped=self.clipped.tolist(),
                      saturated=((self.command == self.lower) | (self.command == self.upper)).tolist(),
                      start_error_m=before_info["position_error_m"], start_speed_m_s=before_info["speed_m_s"])
        self.episode_records.append(record)
        if self.trace_dir and self.stable_captures<3 and 18<=self.k+1<=22:
            self.phase_states.append((self.k+1,start_state,self.command.copy()))
        self.data.ctrl[self.actuators] = self.command
        mujoco.mj_forward(self.model, self.data)
        for substep in range(1, self.substeps + 1):
            pre_step = self.get_state()  # capture BEFORE an engine warning can reset data
            self.counts["attempted_physics_steps"] += 1
            mujoco.mj_step(self.model, self.data)
            warnings = [w.name for w in WARNINGS if self.data.warning[w].number]
            if self.data.time <= pre_step[0]:
                warnings.append("engine_time_reset")
            if not all(np.isfinite(x).all() for x in (self.data.qpos, self.data.qvel, self.data.qacc)):
                warnings.append("nonfinite_state")
            if warnings:
                return self.fail(record, start_state, pre_step, substep, warnings)
        self.previous_tension = -self.data.actuator_force[self.actuators].copy()
        self.k += 1
        mujoco.mj_forward(self.model, self.data)
        observation, info = self._observe()
        if not np.isfinite(observation).all():
            return self.fail(record, start_state, pre_step, self.substeps, ["nonfinite_observation"])
        terms = reward_terms(self.reward,info,before_info,self.previous_tension-previous,
                             self.upper,self.position_scale,self.speed_scale,self.k in self.hold_steps)
        if self.tracking:
            record.update(start_path_progress_m=before_info['path_progress_m'],
                end_path_progress_m=info['path_progress_m'],end_path_error_m=info['path_error_m'])
        reward = float(sum(terms.values()))
        record.update(end_error_m=info["position_error_m"], end_speed_m_s=info["speed_m_s"],
                      reward_terms=terms, reward=reward)
        self.counts["completed_actions"] += 1
        self.counts["complete_episodes"] += int(self.k == self.horizon)
        if self.k==self.horizon and self.trace_dir and self.phase_states and self.stable_captures<3:
            self.trace_dir.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(self.trace_dir/f'stable_episode_{self.episode}.npz',
                episode_actions=np.array([v[0] for v in self.phase_states]),
                states=np.array([v[1] for v in self.phase_states]),
                tensions_n=np.array([v[2] for v in self.phase_states]))
            self.stable_captures+=1
        info.update(record, numerical_failure=False, valid_physical_transition=True, counts=self.counts.copy())
        return observation, reward, self.k == self.horizon, False, info

    def replay_pre_step(self, state):
        self.reset()
        mujoco.mj_setState(self.model, self.data, state, STATE_SPEC)
        before = float(self.data.time)
        self.counts["attempted_physics_steps"] += 1
        mujoco.mj_step(self.model, self.data)
        warnings = [w.name for w in WARNINGS if self.data.warning[w].number]
        return dict(before_time_s=before, returned_time_s=float(self.data.time), warnings=warnings,
                    engine_time_reset=bool(self.data.time <= before), attempted_physics_steps=1,
                    reproduced=bool(warnings or self.data.time <= before))
