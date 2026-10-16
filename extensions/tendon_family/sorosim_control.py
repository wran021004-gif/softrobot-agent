"""SoRoSim controller on the shared projected-state/ideal-tension protocol."""
from pydantic import Field
from .contracts import SorosimSolver, current_nmpc_recipe
from .gvs_profile import ReachControl


class SorosimReachControl(ReachControl):
    solver: SorosimSolver = Field(default_factory=SorosimSolver)


def checked_control(inp):
    from .generated_serial import checked_reach
    control = checked_reach(inp)
    current_nmpc_recipe(control.recipe)
    if inp.policy.backend.extension_id != 'backend.family_mujoco':
        raise ValueError('SOROSIM_REQUIRES_INDEPENDENT_MUJOCO_EXECUTION')
    if control.recipe.integration_method != 'implicit_euler':
        raise ValueError('SOROSIM_UNSUPPORTED_INTEGRATION_METHOD')
    return control


class SorosimNMPCController:
    def __init__(self, parameters, period_s):
        self.control = SorosimReachControl.model_validate(parameters)
        self.parameters = self.control.recipe
        self.period_s = period_s

    def close(self):
        if getattr(self, 'session', None) is not None:
            self.session.close()
