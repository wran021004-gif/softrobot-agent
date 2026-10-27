"""Replay an exported ideal-tension execution; no Store access is required."""
import argparse
import csv
import json
import time
from pathlib import Path
import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parent

def load():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf8'))
    model = mujoco.MjModel.from_xml_path(str(ROOT / 'robot.xml'))
    rows = list(csv.DictReader((ROOT / 'control.csv').open(encoding='utf8', newline='')))
    data = mujoco.MjData(model)
    initial = manifest['initial_state']
    data.qpos[:] = initial['qpos']; data.qvel[:] = initial['qvel']
    aids = [model.actuator(n + '_direct_tension').id for n in manifest['tendon_order']]
    forces = json.loads((ROOT / 'external_forces.json').read_text(encoding='utf8'))['forces']
    return manifest, model, data, rows, aids, forces

def advance(model, data, row, names, aids, forces):
    data.ctrl[aids] = [float(row[n + '_N']) for n in names]
    count = round(float(row['dt_s']) / model.opt.timestep)
    if abs(count * model.opt.timestep - float(row['dt_s'])) > 1e-10:
        raise ValueError('Control boundary is not aligned to the physical timestep')
    def apply_forces():
        tick = round(data.time / model.opt.timestep)
        data.xfrc_applied[:] = 0
        for force in forces:
            if round(force['start_s']/model.opt.timestep) <= tick < round(force['end_s']/model.opt.timestep):
                data.xfrc_applied[model.body(force['entity']).id, :3] += force['force_n']
    apply_forces()
    mujoco.mj_forward(model, data)
    for _ in range(count):
        apply_forces()
        mujoco.mj_step(model, data)
    apply_forces()
    mujoco.mj_forward(model, data)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--repeat', action='store_true')
    parser.add_argument('--show-recorded-path', action='store_true', help='Show original sampled tip positions')
    args = parser.parse_args()
    if args.speed <= 0: parser.error('--speed must be positive')
    manifest, model, data, rows, aids, forces = load()
    names = manifest['tendon_order']
    if args.headless:
        start=time.perf_counter()
        recorded=list(csv.DictReader((ROOT/'states.csv').open(encoding='utf8',newline='')))
        mujoco.mj_forward(model,data)
        errors=[]; velocity_errors=[]; jac=np.zeros((3,model.nv)); tip=model.site('tip_site').id
        for i,row in enumerate(rows):
            advance(model,data,row,names,aids,forces)
            expected=[float(recorded[i+1]['tip_'+axis+'_m']) for axis in 'xyz']
            errors.append(float(np.linalg.norm(data.site('tip_site').xpos-expected)))
            mujoco.mj_jacSite(model,data,jac,None,tip)
            velocity=[float(recorded[i+1]['tip_v'+axis+'_m_s']) for axis in 'xyz']
            velocity_errors.append(float(np.linalg.norm(jac@data.qvel-velocity)))
        print(json.dumps({'physics_steps':round(data.time/model.opt.timestep), 'wall_s':time.perf_counter()-start,
                          'tip_m':data.site('tip_site').xpos.tolist(), 'max_sample_position_error_m':max(errors),
                          'max_sample_velocity_error_m_s':max(velocity_errors)}))
        return
    from mujoco import viewer as mjviewer
    paused = [False]
    def key(code):
        if code == 32: paused[0] = not paused[0]
    print('Space pauses/resumes; mouse rotates/zooms. Close the window to exit.')
    with mjviewer.launch_passive(model, data, key_callback=key) as viewer:
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_TENDON] = True
        goal=json.loads((ROOT/'task.json').read_text(encoding='utf8'))['goal']['data']
        targets=goal.get('vertices_m', [goal['target_m']] if 'target_m' in goal else [])
        positions=[(p,[0.1,0.9,0.2,0.9],0.006) for p in targets]
        if args.show_recorded_path:
            recorded=list(csv.DictReader((ROOT/'states.csv').open(encoding='utf8',newline='')))
            positions += [([float(r['tip_'+axis+'_m']) for axis in 'xyz'],[0.2,0.6,1.0,0.6],0.002) for r in recorded]
        with viewer.lock():
            for point,color,size in positions:
                if viewer.user_scn.ngeom >= viewer.user_scn.maxgeom: break
                geom=viewer.user_scn.geoms[viewer.user_scn.ngeom]
                mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,[size,0,0],point,np.eye(3).ravel(),color)
                viewer.user_scn.ngeom+=1
        while viewer.is_running():
            for row in rows:
                if not viewer.is_running(): return
                while paused[0] and viewer.is_running(): viewer.sync(); time.sleep(0.05)
                start=time.perf_counter()
                with viewer.lock(): advance(model,data,row,names,aids,forces)
                viewer.sync()
                time.sleep(max(0, float(row['dt_s'])/args.speed - (time.perf_counter()-start)))
            if not args.repeat:
                while viewer.is_running(): viewer.sync(); time.sleep(0.05)
                return
            with viewer.lock():
                mujoco.mj_resetData(model,data)
                data.qpos[:] = manifest['initial_state']['qpos']; data.qvel[:] = manifest['initial_state']['qvel']

if __name__ == '__main__': main()
