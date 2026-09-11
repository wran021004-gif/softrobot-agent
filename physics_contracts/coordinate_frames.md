# Coordinate frames — V1

Human-owned scientific contract, extracted without retuning from main@245a785.
All lengths are meters, angles radians, mass kilograms, time seconds and forces
newtons. World and robot base frames coincide at [0,0,0]. The straight arm lies
along +x; its cross-section is y-z. Each segment uses its parent's frame with
local +x along its centerline. There is no implicit frame transform in MATLAB.
The environment declares this frame explicitly; both adapters check agreement.

phi = atan2(target_z, target_y), measured from +y toward +z. theta is the total
bend magnitude on [0,pi]. Tendon i is indexed from zero; alpha_i = 2*pi*i/N.
Its local offset is [0, r_t*cos(alpha_i), r_t*sin(alpha_i)]. RobotIR stores
angles and offsets once; MATLAB uses its angles, MuJoCo uses its offsets.

Environment gravity belongs to EnvironmentSpec. M0/M1 omit gravity and contact;
they need no gravity/object parameters in their present equations. Python checks
the shared environment identity/frame; no MATLAB environment file exists.
