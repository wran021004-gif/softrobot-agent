"""Independent development scoring of recorded PHS equilibria; no physics calls."""
import numpy as np


def evaluate(protocol,baseline,loaded,s):
    a=baseline['samples'][-1];b=loaded['samples'][-1]
    delta=np.array(b['positions'])-a['positions']
    index=protocol['monitor_s'].index(s)
    dx=abs(b['force_point'][0]-a['positions'][index][0])
    tip=float(np.linalg.norm(delta[-1,:2]));y=float(np.max(np.abs(delta[:,1])))
    ratio=tip/max(dx,1e-15)
    baseline_ok=(baseline['status']=='stable' and
        np.max(np.linalg.norm(np.array(a['positions'])[:,:2],axis=1))<=protocol['initial_lateral_limit_m'])
    valid=baseline_ok and loaded['status']=='stable'
    violations=dict(tip=max(0,tip/protocol['tip_horizontal_limit_m']-1),
        middle=max(0,1-dx/protocol['force_point_x_min_m']),
        ratio=max(0,ratio/protocol['ratio_limit']-1),plane=max(0,y/protocol['out_of_plane_limit_m']-1))
    return dict(status='development_pass' if valid and max(violations.values())==0 else 'valid_failure' if valid else 'invalid',
        registered_acceptance='not_registered',valid=valid,tip_xy_m=tip,point_dx_m=dx,ratio=ratio,out_of_plane_m=y,
        violations=violations,worst_violation=max(violations.values()),delta_positions=delta.tolist())
