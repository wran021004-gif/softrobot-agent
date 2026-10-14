"""Explicit cross-session imports and compact saved evidence, without a solve."""
from copy import deepcopy
import json
import numpy as np
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.state_io import digest
from .control_evidence import ControlEvidence, EvidenceQuery






def import_execution(reader, execution_id, destination, run_id, expected_manifest=None):
    source=reader.resolve(execution_id)
    if expected_manifest is not None and plain(expected_manifest)!=source['manifest']:
        raise ValueError('EXECUTION_MANIFEST_OWNERSHIP_MISMATCH')
    cfg=source['configuration']
    refs=[source['manifest'],source['metadata']['candidate_input'],
        dict(artifact_id=source['metadata']['artifact_id'],media_type='application/json'),*source['files'].values()]
    with destination.transaction() as db:
        for ref in refs:
            copied=destination.put(db,reader.store.artifact(ref,raw=True),ref['media_type'])
            if plain(copied)!=ref: raise ValueError('IMPORT_HASH_MISMATCH')
        binding=dict(schema_version='1.0.0',execution_id=execution_id,owner_run_id=source['owner'],
            source_project_id=reader.store.config()['project_id'],source_store=str(reader.store.root),
            candidate_id=source['metadata']['candidate'],configuration=source['metadata']['candidate_input'],
            evidence_manifest=source['manifest'],task_identity=digest(cfg['task']),controller_identity=digest(cfg['policy']['controller']),
            source=source,classification='Imported immutable evidence; original execution ownership is unchanged')
        ref=destination.put(db,binding)
        destination.event(db,run_id,'cross_session_evidence','bound',inputs=[source['manifest']],outputs=[ref])
    return plain(ref)


class BoundReader(ControlEvidence):
    def __init__(self,store,binding):
        super().__init__(store);self.binding=store.artifact(binding)
        required={'execution_id','owner_run_id','configuration','evidence_manifest','source','task_identity','controller_identity'}
        if not isinstance(self.binding,dict) or not required<=self.binding.keys():
            raise ValueError('EXPLICIT_EXECUTION_BINDING_REQUIRED: pass the imported binding, not a query result reference')
    def resolve(self,execution_id):
        b=self.binding;s=deepcopy(b['source'])
        if (execution_id!=b['execution_id'] or s['execution_id']!=execution_id or s['owner']!=b['owner_run_id']
                or s['manifest']!=b['evidence_manifest'] or s['metadata']['candidate']!=b['candidate_id']
                or s['metadata']['candidate_input']!=b['configuration']):
            raise ValueError('BOUND_EXECUTION_IDENTITY_MISMATCH')
        bundle=self.store.artifact(s['manifest'])
        if bundle['result']['artifact_id']!=s['metadata']['artifact_id'] or {f['filename']:f['reference'] for f in bundle['files']}!=s['files']:
            raise ValueError('BOUND_MANIFEST_CONTENT_MISMATCH')
        effective=self.store.artifact(b['configuration'])['effective']
        if effective!=s['configuration'] or digest(effective['task'])!=b['task_identity'] or digest(effective['policy']['controller'])!=b['controller_identity']:
            raise ValueError('BOUND_CONFIGURATION_MISMATCH')
        return s


def measured_motion(reader,source):
    """World Jacobian at recorded serial backend q, qdot. No stepping/solver."""
    import mujoco
    rows=reader.read_file(source,'trajectory.json.gz',[])
    physics=reader.read_file(source,'resolved_physics.json')
    model=mujoco.MjModel.from_xml_string(reader.store.artifact(source['files']['robot.xml'],raw=True).decode('utf8'))
    data=mujoco.MjData(model)
    ids=[model.joint(j).id for j in physics['dofs']]
    qi=model.jnt_qposadr[ids];vi=model.jnt_dofadr[ids]
    target=np.array(source['configuration']['task']['goal']['data']['target_m'])
    motion=[]
    for row in rows:
        data.qpos[qi]=row['qpos_rad'];data.qvel[vi]=row['qvel_rad_s'];mujoco.mj_forward(model,data)
        J=np.zeros((3,model.nv));Jr=np.zeros_like(J)
        mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
        velocity=J@data.qvel
        motion.append(dict(time_s=row['time_s'],position_m=row['tip_m'],
            velocity_m_s=velocity.tolist(),speed_m_s=float(np.linalg.norm(velocity)),
            error_m=float(np.linalg.norm(np.array(row['tip_m'])-target)),
            reconstructed_position_difference_m=float(np.linalg.norm(data.site_xpos[model.site('tip_site').id]-row['tip_m']))))
    return motion








