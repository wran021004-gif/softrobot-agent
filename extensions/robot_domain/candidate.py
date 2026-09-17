"""Apply absolute changes to the frozen session design, then recompile all IR data."""
from schemas.exploration import ExplorationControl
from tools.design_compiler import build_robot_ir
from .contracts import RodDesign


GEOMETRY = ('total_length_m', 'body_radius_m', 'tendon_routing_radius_m')
PHYSICS = ('line_density_kg_m', 'root_ei_nm2', 'tip_ei_ratio', 'bending_viscosity_nm2_s',
           'natural_total_angle_rad', 'tendon_servo_kp_n_per_m', 'tendon_force_limit_n')
CONTROL = ('bend_y_rad', 'bend_z_rad', 'bias_fraction', 'gain_rad2_per_m2',
           'max_bend_update_rad', 'rate_limit_ref_per_s')
EDITABLE = tuple('design.' + n for n in GEOMETRY) + tuple('physics.' + n for n in PHYSICS) + tuple('controller.' + n for n in CONTROL)


def apply_design(inp, parameters, changes):
    if inp.robot.structure.contract != 'domain.rod_design':
        raise ValueError('ROD_DESIGN_BASELINE_REQUIRED')
    data = RodDesign.model_validate(inp.robot.structure.data).model_dump(mode='json')
    control = dict(inp.policy.controller.parameters.data)
    for key, value in changes.items():
        if key not in EDITABLE:
            raise ValueError('PARAMETER_NOT_EDITABLE: ' + key)
        group, name = key.split('.')
        target = data if group == 'design' else data['exploration_physics'] if group == 'physics' else control
        target[name] = value
    design = RodDesign.model_validate(data)
    build_robot_ir(design)  # Existing geometry relationships and full derived mechanics.
    control = ExplorationControl.model_validate(control)
    inp.robot.structure.data.clear()
    inp.robot.structure.data.update(design.model_dump(mode='json'))
    inp.policy.controller.parameters.data.clear()
    inp.policy.controller.parameters.data.update(control.model_dump(mode='json'))
    return inp
