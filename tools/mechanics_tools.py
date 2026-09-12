"""Python contracts/transport for MATLAB mechanics, with a persistent solve cap."""
import json
from pathlib import Path
from tools.artifact_tools import file_hash
from tools.spec_tools import ROOT, load_yaml


def resolve_analysis_capability(parameters):
    """Check exact inputs, scoped authority, MATLAB function and dependency presence."""
    from schemas.analysis_spec import AnalysisSpec
    from tools.closeout_authority import analysis_permission
    import importlib.util
    try:
        spec=AnalysisSpec.model_validate(parameters)
        analysis_permission(spec.operation)
        if not (ROOT/'matlab/closeout_mechanics.m').is_file() or importlib.util.find_spec('matlab.engine') is None:
            return {'status':'DEPENDENCY_UNAVAILABLE','fallback':None}
        return {'status':'SUPPORTED','operation':spec.operation,'model':'one_mode_discrete_rod_v1',
            'scope':'INDEPENDENT_SURROGATE_ANALYSIS','license_check':'requires Engine startup','fallback':None}
    except (ValueError,ModuleNotFoundError) as exc:
        return {'status':'REJECTED','reason':str(exc),'fallback':None}


def export_parameters(xml_path, ir):
    # Load only: no numerical rollout and no duplicated capsule mass formula.
    import mujoco
    import numpy as np
    model=mujoco.MjModel.from_xml_path(str(xml_path))
    ids=[model.body(f'segment_{i}').id for i in range(ir.segments)]
    if model.nq != 2*ir.segments or model.ntendon != ir.tendon_count:
        raise ValueError('Compiled structure/RobotIR mismatch')
    for i,b in enumerate(ids):
        expected=[ir.section.segment_length_m/2,0,0]
        if not np.allclose(model.body_ipos[b],expected,atol=1e-12):
            raise ValueError('Unsupported mass-center mapping')
    # Capsule inertia frame can be rotated: map principal inertias to body y.
    inertias=[]
    for b in ids:
        rotation=np.zeros(9); mujoco.mju_quat2Mat(rotation,model.body_iquat[b])
        r=rotation.reshape(3,3); inertias.append(float((r@np.diag(model.body_inertia[b])@r.T)[1,1]))
    return dict(n=ir.segments,length_m=ir.total_length_m,offset_yz_m=[list(x.offset_yz_m) for x in ir.tendon_routes],
        mass_kg=model.body_mass[ids].tolist(),inertia_y_kg_m2=inertias,
        stiffness_nm_rad=model.jnt_stiffness[::2].tolist(),damping_nm_s_rad=model.dof_damping[::2].tolist(),
        gravity_m_s2=model.opt.gravity.tolist(),tension_n=[0.]*ir.tendon_count,tip_force_n=[0.,0.,0.],
        stiffness_scale=1.,damping_scale=1.,source=dict(xml_sha256=file_hash(xml_path),mujoco_version=mujoco.__version__,
        method='MjModel compiled mass, inertial frame, joint stiffness/damping; planar projection onto equal hinge bends',
        scientific_status='SURROGATE_ASSUMPTION',contract='physics_contracts/closeout_analysis_v1.md'))


class MechanicsTools:
    def __init__(self, matlab, ledger_path=ROOT/'runs/closeout_development_budget.json'):
        self.matlab=matlab; self.path=Path(ledger_path)

    def solve(self, parameters, **changes):
        from tools.closeout_authority import analysis_permission
        from tools.closeout_state import atomic_json
        p={**parameters,**changes}
        analysis_permission(p['operation'])
        from schemas.analysis_spec import AnalysisSpec
        try:
            p=AnalysisSpec.model_validate(p).model_dump(exclude_none=True)
        except ValueError as exc:
            return {'status':'fail','reason':str(exc),'backend_started':False}
        ledger=json.loads(self.path.read_text()) if self.path.exists() else {'mechanics':[], 'mujoco':[], 'full_suite':[]}
        if len(ledger['mechanics'])>=200:
            raise ValueError('Independent mechanics solve budget exhausted')
        row={'id':len(ledger['mechanics']), 'status':'running','input':p}
        ledger['mechanics'].append(row); atomic_json(self.path,ledger)
        try:
            result=json.loads(self.matlab.eng.closeout_mechanics(json.dumps(p,allow_nan=False),nargout=1))
            row.update(status=result['status'],result=result)
            return result
        except Exception as exc:
            row.update(status='fail',reason=str(exc))
            return {'status':'fail','reason':str(exc)}
        finally:
            atomic_json(self.path,ledger)
