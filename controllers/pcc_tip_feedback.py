"""Experimental Jacobian-transpose feedback; no tuning defaults or success claim."""
import math
from schemas.control_spec import ControlSpec, ControlCommand, ControllerResult
from schemas.feedback import FeedbackArtifact, FeedbackUpdate
from tools.pcc_math import tip_and_jacobian
from tools.spec_tools import ROOT


class PCCTipFeedback:
    requires_tip_observation = True

    def __init__(self, robot_ir, task, plan, experiment):
        experiment.check_unchanged()
        p = experiment.policy
        if "C2" not in p.allowed_controller_levels or p.feedback_parameters is None:
            raise ValueError("BLOCKED_FOR_HUMAN_APPROVAL: feedback parameters required")
        self.parameters = p.feedback_parameters
        self.robot_ir, self.task = robot_ir, task
        self.spec = ControlSpec(controller="pcc_tip_feedback", level="C2", command_source=f"ExperimentPolicy {p.policy_id}")
        theta, phi = plan.metrics["theta_rad"], plan.metrics["phi_rad"]
        self.bend = [theta * math.cos(phi), theta * math.sin(phi)]
        tip_and_jacobian(robot_ir.total_length_m, self.bend)
        self.target = ControlCommand(tendon_target_lengths_m=tuple(plan.metrics["tendon_target_lengths_m"]))
        if len(self.target.tendon_target_lengths_m) != robot_ir.tendon_count or any(
                not self.parameters.min_tendon_length_m <= x <= self.parameters.max_tendon_length_m
                for x in self.target.tendon_target_lengths_m):
            raise ValueError("Initial PCC command outside approved feedback bounds")
        self.artifact = FeedbackArtifact(policy_id=p.policy_id, policy_hash=experiment.policy_hash,
            parameter_source=experiment.path.relative_to(ROOT).as_posix() + '#feedback_parameters',
            parameters=self.parameters, initial_command=self.target)
        self.updates = []
        self.last_step = -1

    def command(self, time_s, observation):
        step = observation["step"]
        if type(step) is not int or step != self.last_step + 1 or not math.isfinite(time_s) or time_s < 0:
            raise ValueError("Feedback requires sequential deterministic simulation steps")
        self.last_step = step
        if step % self.parameters.update_every_steps:
            return self.target
        tip = observation["tip_position_m"]
        if len(tip) != 3 or not all(math.isfinite(x) for x in tip):
            raise ValueError("Feedback requires a finite actual MuJoCo tip observation")
        error = [target - actual for target, actual in zip(self.task.target_m, tip)]
        _, jac = tip_and_jacobian(self.robot_ir.total_length_m, self.bend)
        delta = [self.parameters.gain_rad2_per_m2 * sum(jac[j][i] * error[j] for j in range(3)) for i in range(2)]
        norm = math.hypot(*delta)
        if norm > self.parameters.max_bend_update_rad:
            delta = [x * self.parameters.max_bend_update_rad / norm for x in delta]
        bend = [a + b for a, b in zip(self.bend, delta)]
        norm = math.hypot(*bend)
        if norm > math.pi:
            bend = [x * math.pi / norm for x in bend]
        raw = [self.robot_ir.total_length_m + getattr(self, 'length_bias_m', 0.) - self.robot_ir.tendon_routing_radius_m *
               (bend[0] * math.cos(route.angle_rad) + bend[1] * math.sin(route.angle_rad))
               for route in self.robot_ir.tendon_routes]
        if getattr(self,'active_fraction_limit',None) is not None:
            base=self.robot_ir.total_length_m+getattr(self,'length_bias_m',0.)
            cap=self.active_fraction_limit*self.robot_ir.total_length_m
            raw=[base+min(cap,max(-cap,value-base)) for value in raw]
        previous = self.target.tendon_target_lengths_m
        cap = self.parameters.max_command_update_m
        bounded = [min(self.parameters.max_tendon_length_m, old + cap,
                       max(self.parameters.min_tendon_length_m, old - cap, value))
                   for value, old in zip(raw, previous)]
        command = ControlCommand(tendon_target_lengths_m=tuple(bounded))
        update = FeedbackUpdate(step=step, time_s=time_s, observed_tip_m=tuple(tip), error_m=tuple(error),
            bend_rad=tuple(bend), command=command, max_command_delta_m=max(abs(a-b) for a,b in zip(bounded, previous)),
            command_clipped=bounded != raw)
        self.bend, self.target = bend, command
        self.updates.append(update.model_dump(mode="json"))
        return command

    def result(self):
        return ControllerResult(status="pass", spec=self.spec, command=self.target)


def synthesize_feedback(robot_ir, task, plan, experiment):
    return PCCTipFeedback(robot_ir, task, plan, experiment)
