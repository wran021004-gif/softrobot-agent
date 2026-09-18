"""Common resolved quantities without simulator startup or new physical formulas."""
from typing import Literal
from schemas.common import Contract
from schemas.robot_ir import RobotIR
from tools.state_io import digest


class ModelQuantityRequest(Contract):
    quantity: str
    model_identity: str
    units: str
    frame: str


class ModelQuantityResult(Contract):
    quantity: str
    values: list[float]
    units: str
    frame: str
    model_identity: str
    source_identity: str
    domain: Literal['resolved_structure', 'declared_surrogate_parameters']
    assumptions: list[str]


class RobotIRProvider:
    def __init__(self, ir):
        self.ir = RobotIR.model_validate(ir)
        self.identity = digest(self.ir.model_dump(mode='json'))

    def get(self, value):
        request = ModelQuantityRequest.model_validate(value)
        if request.model_identity != self.identity or request.frame != self.ir.coordinate_frame:
            raise ValueError('MODEL_IDENTITY_OR_FRAME_MISMATCH')
        mappings = dict(length_m=([self.ir.total_length_m], 'm', 'resolved_structure'),
            tendon_routing_radius_m=([self.ir.tendon_routing_radius_m], 'm', 'resolved_structure'),
            force_limit=([self.ir.mechanics.tendon_force_limit_n], 'N', 'declared_surrogate_parameters'))
        if self.ir.resolved_rod:
            mappings['mass'] = (list(self.ir.resolved_rod.mass_kg), 'kg', 'declared_surrogate_parameters')
        if request.quantity not in mappings:
            raise ValueError('MODEL_QUANTITY_UNAVAILABLE: Do not infer dynamics from geometry; V1 compiled mass and inertia require historical exports with provenance; mass matrix interface not implemented')
        values, units, domain = mappings[request.quantity]
        if units != request.units:
            raise ValueError('UNIT_MISMATCH')
        return ModelQuantityResult(quantity=request.quantity, values=values, units=units, frame=request.frame,
            model_identity=self.identity, source_identity=self.identity, domain=domain,
            assumptions=['Reuse declared RobotIR values; no new physical formulas', 'No physical calibration performed', *self.ir.physics_contracts])
