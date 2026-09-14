"""Existing length-controller generators; do not execute a backend or grant rights."""
import math
from types import SimpleNamespace
from tools.spec_tools import ROOT,load_simulator
from tools.state_io import digest
from tools.reach_dynamics import control_commands


def length_controller(ir,task,control,*,authority=None,timestep_s=None,parameter_source=None):
    from controllers.open_loop_length import OpenLoopLength
    if control.mode=='C1':
        return OpenLoopLength(control_commands(ir,control))
    from controllers.pcc_tip_feedback import PCCTipFeedback
    from schemas.experiment_policy import FeedbackParameters
    p=FeedbackParameters(gain_rad2_per_m2=control.gain_rad2_per_m2,
        update_every_steps=control.update_every_steps,max_bend_update_rad=control.max_bend_update_rad,
        max_command_update_m=control.rate_limit_ref_per_s*ir.total_length_m*control.update_every_steps*(timestep_s or load_simulator().timestep_s),
        min_tendon_length_m=.73*ir.total_length_m,max_tendon_length_m=1.30*ir.total_length_m)
    experiment=SimpleNamespace(check_unchanged=lambda:None,policy=SimpleNamespace(allowed_controller_levels=['C2'],
        feedback_parameters=p,policy_id=authority or 'round9-user-grant'),policy_hash=digest(control.model_dump()),path=parameter_source or ROOT/'configs/experiments/round9_grant.json',parameter_pointer='control' if parameter_source else 'feedback_parameters')
    plan=SimpleNamespace(metrics=dict(theta_rad=math.hypot(control.bend_y_rad,control.bend_z_rad),
        phi_rad=math.atan2(control.bend_z_rad,control.bend_y_rad),tendon_target_lengths_m=control_commands(ir,control)))
    controller=PCCTipFeedback(ir,task,plan,experiment)
    controller.length_bias_m=control.bias_fraction*ir.total_length_m
    controller.active_fraction_limit=.25
    return controller

