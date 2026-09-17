"""Read the already produced evidence; verify replay, controls and old static terms."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from numpy.testing import assert_allclose
from tools.state_io import atomic_json


def check(root):
    from tools.platform_store import Store
    from extensions.tendon_family.compiler import quat
    from extensions.tendon_family.geometry import geometry
    root=Path(root); store=Store(root); result=dict(extra_backend_solves=0,records={})
    for name in ('single_permitted','matlab_spatial','family_mujoco'):
        record=json.loads((root/(name+'_record.json')).read_text(encoding='utf8'))
        folder=Path(record['saved_folder']); read=lambda n:json.loads((folder/n).read_text(encoding='utf8'))
        rows=read('replay_trajectory.json'); p=read('resolved_physics.json'); scene=read('experiment_scene.json'); obs=read('controller_observations.json')
        backend=store.artifact(record['receipts']['simulation']['output'])
        assert len([s for s in backend['signals'] if s['spec']['name']=='joint_position'])==len(p['dofs'])
        assert len([s for s in backend['signals'] if s['spec']['name']=='actuator_command'])==len(p['actuators'])
        assert len(rows)==len(obs)
        for i,(r,o) in enumerate(zip(rows,obs)):
            assert_allclose(r['time_s']-r['solver_time_s'],scene['control_period_s'],atol=1e-12)
            assert_allclose(o['qpos_rad'],rows[i-1]['qpos_rad'] if i else scene['qpos_rad'],atol=1e-12)
            expected=np.array(p['reference_lengths_m'])+np.array(p['transmission'])@r['actuator_command']-np.array([t['pretension_n']/t['kp_n_m'] for t in p['tendons']])
            assert_allclose(r['command_m'],expected,atol=1e-12)
        q=np.array(rows[-1]['qpos_rad']); delta=q-scene['qpos_rad']
        assert np.linalg.norm(delta[::2])>1e-4 and np.linalg.norm(delta[1::2])>1e-4
        forces=[r['solver_time_s'] for r in rows if np.linalg.norm(r['external_torque_nm'])>1e-12]
        if name!='single_permitted': assert_allclose(forces,np.arange(12,20)/100,atol=1e-12)
        g=geometry(p,q,scene['assembly']['mount']); assert_allclose(g['tip'],rows[-1]['tip_m'],atol=1e-12)
        for a,b in zip(g['routes'],rows[-1]['tendon_routes_m']): assert_allclose(a,b,atol=1e-12)
        result['records'][name]=dict(samples=len(rows),q_y_change_norm_rad=float(np.linalg.norm(delta[::2])),q_z_change_norm_rad=float(np.linalg.norm(delta[1::2])),
            max_tension_n=float(np.max([r['tension_n'] for r in rows])),active_force_times_s=forces,
            final_tip_m=rows[-1]['tip_m'],initial_target_error_m=float(np.linalg.norm(geometry(p,np.array(scene['qpos_rad']),scene['assembly']['mount'])['tip']-scene['target_world_m'])),
            final_target_error_m=record['evaluation']['metrics'][0]['value'])
        if name=='single_permitted':
            from types import SimpleNamespace
            from extensions.robot_domain.contracts import RodDesign
            from extensions.experiment_dynamics.physics import resolve_physics
            from extensions.experiment_dynamics.contracts import Assembly,SpatialParameters
            from extensions.experiment_dynamics.spatial import SpatialModel
            old=resolve_physics(RodDesign.model_validate(read('robot_description.json')['data']))
            model=SpatialModel(old,SimpleNamespace(assembly=Assembly.model_validate(scene['assembly'])),SpatialParameters())
            terms=model.terms(np.array(scene['qpos_rad']),np.array(scene['qvel_rad_s']),np.array(p['reference_lengths_m']),{})
            ms=read('matlab_static.json')
            for key in ('mass','bias','gravity'): assert_allclose(ms[key],terms[key],rtol=1e-12,atol=1e-13)
            assert_allclose(ms['lengths'],terms['geometry']['lengths'],atol=1e-13)
            result['legacy_python_static_match']=True
        if name=='family_mujoco':
            import mujoco
            mapping=read('compiled_physics.json'); model=mujoco.MjModel.from_xml_path(str(folder/'robot.xml')); data=mujoco.MjData(model)
            data.qpos[mapping['qpos_indices']]=q; data.qvel[mapping['qvel_indices']]=rows[-1]['qvel_rad_s']; mujoco.mj_forward(model,data)
            assert_allclose(data.site_xpos[model.site('tip_site').id],rows[-1]['tip_m'],atol=1e-12)
            for part,bid in zip(p['parts'],mapping['body_ids']):
                R=quat(model.body_iquat[bid]); assert_allclose(R@np.diag(model.body_inertia[bid])@R.T,part['inertia_com_local_kg_m2'],atol=1e-14)
            camera=mujoco.MjvCamera(); mujoco.mjv_defaultFreeCamera(model,camera)
            camera.lookat[:]=[.15,0.,.17]; camera.distance=.6; camera.azimuth=120; camera.elevation=-20
            with mujoco.Renderer(model,height=480,width=640) as renderer:
                renderer.update_scene(data,camera=camera); pixels=renderer.render()
            from PIL import Image
            Image.fromarray(pixels).save(root/'mujoco_saved_frame.png')
            result['mujoco_saved_render']='actual saved XML and qpos; mj_forward/render only, no mj_step'
    atomic_json(root/'saved_checks.json',result); return result


if __name__=='__main__': print(json.dumps(check(Path(sys.argv[1])),indent=2))
