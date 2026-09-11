# Single-section PCC kinematics — M1

Human-owned V1 contract. L is RobotIR.section.length_m. The straight limit is
[L,0,0]. For nonzero theta, x=L*sin(theta)/theta and
rho=L*(1-cos(theta))/theta; tip=[x,rho*cos(phi),rho*sin(phi)]. Implementation
uses rho=2*L*sin(theta/2)^2/theta and the existing abs(theta)<1e-8 straight
limit. MATLAB fminbnd minimizes squared target distance on [0,pi] and compares
both exact endpoints, with the existing MATLAB default solver options.

M0 independently tests norm(target)<=L. Neither screen nor PCC includes load,
stiffness, dynamics, contact, tendon elasticity or material identification.
M1 is a kinematic hypothesis, not a validated physical prediction. Segments,
body radius and surrogate mechanics do not enter its equations.

Tool pass means finite outputs and positive finite tendon commands. Predicted
error above TaskSpec.position_error_max_m yields model_task_success=false but
still permits MuJoCo execution. Only the canonical metric on the actual simulated
tip decides task success. No optimizer, target adjustment or retuning is applied.
