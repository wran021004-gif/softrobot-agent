"""Explicit future dynamics reproduction; not used during the saved-data export."""
import json
from pathlib import Path
import platform

import mujoco
import numpy as np
from phs2d_io import (parser,locate,read,write,sha,require,forbid_integration,load_model,
                     material_point,apply_force,ramp_force,state_columns)


def check_replay(base,folder,entry):
    from validate_phs2d import validate_model
    model,structure,task,mapping,payout=validate_model(base)
    spec=read(folder/'replay_spec.json')
    require(spec['s']==entry['s'] and spec['force_n']==entry['force_n'] and
            spec['material_point_binding']==material_point(structure['physics'],entry['s']), 'REPLAY_FORCE_BINDING')
    initial=read(folder/'initial_state.json')['snapshot']
    require(initial['time_s']==0 and len(initial['qpos'])==model.nq and len(initial['qvel'])==model.nv, 'REPLAY_INITIAL_STATE')
    return model,structure,task,spec,initial


def main():
    p=parser(__doc__)
    p.add_argument('--output',type=Path)
    p.add_argument('--check-only',action='store_true',help='Validate recipe without any integration')
    args=p.parse_args()
    if args.check_only:forbid_integration()
    elif args.output is None:p.error('--output is required for explicit integration')
    base,folder,entry=locate(args)
    model,structure,task,spec,initial=check_replay(base,folder,entry)
    if args.check_only:
        print(json.dumps(dict(status='replay_recipe_checked',nq=model.nq,ntendon=model.ntendon,
                             nu=model.nu,steps_if_explicitly_run=32000,physics_steps=0)))
        return
    output=args.output.resolve()
    require(not output.is_relative_to(base.parent) and not base.parent.is_relative_to(output),
            'OUTPUT_MUST_BE_A_NEW_DIRECTORY_OUTSIDE_PACKAGE')
    output.mkdir(parents=True,exist_ok=False)
    physics=structure['physics'];protocol=task['protocol'];binding=spec['material_point_binding']
    data=mujoco.MjData(model)
    data.qpos[:]=initial['qpos'];data.qvel[:]=initial['qvel'];data.time=0.
    mujoco.mj_forward(model,data)
    apply_force(model,data,physics,binding,0.);mujoco.mj_forward(model,data)
    rows=np.empty((32001,442),dtype=np.float64)
    def record(index,force):
        tensions=np.zeros(model.ntendon)
        for r in range(data.nefc):
            if data.efc_type[r]==int(mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON):
                tensions[int(data.efc_id[r])]+=data.efc_force[r]
        rows[index]=np.r_[data.time,force,data.qpos,data.qvel,data.qacc,data.ten_length,tensions]
    record(0,0.);steps=0
    try:
        for tick in range(32000):
            force=ramp_force(tick,model.opt.timestep,entry['force_n'],protocol['ramp_s'])
            apply_force(model,data,physics,binding,force)
            steps+=1
            mujoco.mj_step(model,data)
            require(np.isfinite(data.qpos).all() and not np.any(data.warning.number), 'REPLAY_NUMERICAL_FAILURE')
            mujoco.mj_forward(model,data)
            record(tick+1,force)
            require(data.ncon==0,'REPLAY_CONTACT_FAILURE')
            # Preserve the original 10 ms snapshot's extra refreshed force mapping.
            if (tick+1)%protocol['sample_every_steps']==0:
                apply_force(model,data,physics,binding,force);mujoco.mj_forward(model,data)
        with np.load(folder/'states_timestep.npz',allow_pickle=False) as original:
            max_q=float(np.max(abs(rows[:,2:146]-original['trajectory'][:,2:146])))
        np.savez_compressed(output/'replayed_states.npz',trajectory=rows,columns=np.asarray(state_columns()))
        report=dict(status='dynamics_replayed_not_new_task_acceptance',physics_step_attempts=steps,
            maximum_qpos_difference_rad=max_q,xml_sha256=sha(base/'robot.xml'),
            python=platform.python_version(),mujoco=mujoco.__version__,numpy=np.__version__,
            historical_acceptance_unchanged=True,original_package_overwritten=False)
        write(output/'replay_report.json',report);print(json.dumps(report))
    except BaseException as exc:
        write(output/'replay_failure.json',dict(error=str(exc),physics_step_attempts=steps))
        raise


if __name__=='__main__':main()
