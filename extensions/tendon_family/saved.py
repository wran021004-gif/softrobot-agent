"""Immutable export materialization and native replay; no dynamics solve."""
import gzip
import json
from pathlib import Path
from tools.state_io import atomic_json


def materialize(root,record,destination):
    from tools.platform_store import Store
    store=Store(root); receipt=record['receipts']['simulation']; bundles=[]
    for event in store.events(record['run_id']):
        if event['execution_id']!=receipt['execution_id'] or event['kind']!='simulation': continue
        for ref in event['outputs']:
            if ref['media_type']!='application/json': continue
            value=store.artifact(ref)
            if isinstance(value,dict) and value.get('result')==receipt['output'] and 'files' in value: bundles.append(value)
    if len(bundles)!=1: raise ValueError('UNIQUE_EXPORT_BUNDLE_REQUIRED')
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    for file in bundles[0]['files']:
        name=file['filename']
        if Path(name).name!=name: raise ValueError('EXPORT_BASENAME_REQUIRED')
        (destination/name).write_bytes(store.artifact(file['reference'],raw=True))
    rows=json.loads(gzip.decompress((destination/'trajectory.json.gz').read_bytes()))
    atomic_json(destination/'replay_trajectory.json',rows)
    return destination


def view(folder,backend):
    folder=Path(folder).resolve()
    if backend=='matlab':
        from tools.matlab_tools import MatlabTools
        tool=MatlabTools()
        try:
            tool.eng.tf_view(str(folder),nargout=0)
            tool.eng.waitfor(tool.eng.gcf(),nargout=0)
        finally: tool.close()
    else:
        import time
        import mujoco
        import mujoco.viewer
        rows=json.loads((folder/'replay_trajectory.json').read_text(encoding='utf8'))
        ids=json.loads((folder/'compiled_physics.json').read_text(encoding='utf8'))
        model=mujoco.MjModel.from_xml_path(str(folder/'robot.xml')); data=mujoco.MjData(model)
        with mujoco.viewer.launch_passive(model,data) as viewer:
            start=time.monotonic()
            while viewer.is_running():
                t=(time.monotonic()-start)%rows[-1]['time_s']; r=next((r for r in rows if r['time_s']>=t),rows[-1])
                data.qpos[ids['qpos_indices']]=r['qpos_rad']; data.qvel[ids['qvel_indices']]=r['qvel_rad_s']
                mujoco.mj_forward(model,data); viewer.sync(); time.sleep(.02)
