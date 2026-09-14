"""Capability-oriented adapters; absent dynamics quantities are never invented."""
from schemas.public_tools import PCCJacobian
from schemas.framework import QuantityRequest


class PCCModel:
    model_id='single_section_inextensible_pcc_v1'
    quantities={'tip': 'm','tip_jacobian':'m/rad'}

    def __init__(self, length_m, bend_rad):
        self.input=PCCJacobian(length_m=length_m,bend_rad=bend_rad)

    def capabilities(self):
        return dict(model_id=self.model_id,quantities=self.quantities,
            frame=self.input.frame,domain='geometric_approximation',calibrated=False,
            assumptions=['single section','constant curvature','inextensible','fixed base'],
            unavailable=['mass_matrix','coriolis','gravity_load','contact_force','physical_calibration'])

    def get(self, request):
        request=QuantityRequest.model_validate(request)
        if request.quantity not in self.quantities:raise ValueError('MODEL_QUANTITY_UNAVAILABLE: '+request.quantity)
        if self.quantities[request.quantity]!=request.units:raise ValueError('UNIT_MISMATCH')
        from tools.pcc_math import tip_and_jacobian
        tip,jac=tip_and_jacobian(self.input.length_m,self.input.bend_rad)
        return dict(value=tip if request.quantity=='tip' else jac,units=request.units,frame=request.frame,
            model=self.capabilities(),source=self.input.model_dump(mode='json'))


class SharedModel:
    """Saved export is authoritative for compiled physical parameters, not PCC."""
    def __init__(self, shared, backend, source_hash,model_id=None):
        self.shared,self.backend,self.source_hash=shared,backend,source_hash
        self.model_id=model_id or (shared.get('model_id') if backend=='matlab' else 'mujoco_segmented')

    def capabilities(self):
        p=self.shared
        return dict(model_id=self.model_id,backend=self.backend,
            domain='uncalibrated_dynamics_prediction',calibrated=False,source_sha256=self.source_hash,
            authority=dict(structure='robot_ir.json',physical_parameters='shared_input.json compiled from IR/XML',
                state='trajectory.json.gz',task='saved task_context or task_hash/environment_hash'),
            parameters={k:p[k] for k in ('mass','inertia_y','stiffness','damping','natural','kp','fmax','gravity','offsets') if k in p},
            omissions=['out_of_plane DOFs','friction','self_collision','MuJoCo contact solver'] if self.backend=='matlab' else [],
            unavailable=['physical_calibration','public_mass_matrix','public_coriolis'],
            units=dict(mass='kg',inertia_y='kg m^2',stiffness='N m/rad',damping='N m s/rad',natural='rad',
                kp='N/m',fmax='N',gravity='m/s^2',offsets='m'),
            parameter_projection='Per-segment exported y-axis mechanics; inertia_y is not a full spatial inertia tensor.',
            frame='world_base_x_forward_yz_cross_section')

    def get_parameter(self,name,units):
        capability=self.capabilities()
        if name not in capability['parameters']:raise ValueError('MODEL_QUANTITY_UNAVAILABLE: '+name)
        if units!=capability['units'][name]:raise ValueError('UNIT_MISMATCH')
        return dict(value=capability['parameters'][name],units=units,frame=capability['frame'],
            source_sha256=self.source_hash,model_id=self.model_id,calibrated=False)
