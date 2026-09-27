"""Two aligned intervals from the failed A run, no solve or backend replay."""
import gzip
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import read,atomic_json
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace

if __name__=='__main__':
    import mujoco
    folder=HERE/'A';store=Store(folder);summary=read(folder/'summary.json')
    run=read(folder/'workflow.json')['run_id']
    refs=next(e['outputs'] for e in store.events(run) if e['kind']=='simulation' and e['execution_id']==summary['execution_id'] and e['status']=='completed')
    bundle=next(v for r in refs if r['media_type']=='application/json' for v in [store.artifact(r)] if isinstance(v,dict) and 'files' in v)
    references={f['filename']:f['reference'] for f in bundle['files']}
    files={name:store.artifact(ref,raw=True) for name,ref in references.items()}
    obs=json.loads(files['controller_observations.json']);rows=json.loads(gzip.decompress(files['trajectory.json.gz']))
    physics=json.loads(files['resolved_physics.json']);model=mujoco.MjModel.from_xml_string(files['robot.xml'].decode('utf8'));data=mujoco.MjData(model)
    ids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[ids];vi=model.jnt_dofadr[ids]
    def actual(t):
        row=next(r for r in rows if abs(r['time_s']-t)<1e-8)
        data.qpos[qi]=row['qpos_rad'];data.qvel[vi]=row['qvel_rad_s'];mujoco.mj_forward(model,data)
        J=np.zeros((3,model.nv));mujoco.mj_jacSite(model,data,J,np.zeros_like(J),model.site('tip_site').id)
        return np.asarray(row['tip_m']),J@data.qvel
    inp=SessionInput.model_validate(read(folder/'input.json'));control=inp.policy.controller.parameters.data
    numerical=store.artifact(summary['numerical_preparation']['source']);nominal=numerical['nominal']
    w=TrajectoryWorkspace(inp.task,inp.robot,control['recipe'],nominal['q0']+[0.]*len(nominal['q0']),nominal['u0'],settling=control['settling'])
    out=[]
    for k in (29,33):
        o=obs[k];x=np.asarray(o['measured_initial_state']);t=o['time_s']
        y,timing=w._extend_tail(x,o['desired_tension_n'])
        def compare(state,time):
            p,v=w._motion(state[:w.n],state[w.n:]);p=np.asarray(p).ravel();v=np.asarray(v).ravel();ap,av=actual(time)
            return dict(time_s=time,predicted_position_m=p.tolist(),actual_position_m=ap.tolist(),
                predicted_velocity_m_s=v.tolist(),actual_velocity_m_s=av.tolist(),
                position_vector_error_m=float(np.linalg.norm(p-ap)),velocity_vector_error_m_s=float(np.linalg.norm(v-av)),
                predicted_speed_m_s=float(np.linalg.norm(v)),actual_speed_m_s=float(np.linalg.norm(av)),
                scalar_speed_error_m_s=float(np.linalg.norm(v)-np.linalg.norm(av)))
        out.append(dict(time_s=t,source_observation_index=k,applied_tension_n=o['desired_tension_n'],
            reconstruction=compare(x,t),one_period=compare(y,t+.01),integration_timing=timing,
            selection={key:o[key] for key in ('plan_source','optimization_selected_iteration','optimization_constraint_violation','optimization_returned_violation','feedback')}))
    result=dict(execution_id=summary['execution_id'],observations=references['controller_observations.json'],trajectory=references['trajectory.json.gz'],rows=out,
        provenance='Two reconstructed implicit-Euler intervals using the actual applied command from the saved A execution. MuJoCo world velocity from saved full joint states and site Jacobian. No backend stepping, new optimization or changed recipe.',
        unresolved='Finite representation, dynamics, integration and limited optimizer progress are not separately identified by these checks. Low rolling-end speeds are not the current measured speeds.')
    atomic_json(HERE/'A_failure_review.json',result)
    for r in out:print(json.dumps(dict(t=r['time_s'],reconstruction=r['reconstruction'],one_period=r['one_period'])))
