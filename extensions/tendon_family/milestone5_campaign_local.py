"""Causal local-diagnosis interface over the frozen reduced mechanics method."""
import numpy as np
from .milestone5_campaign_predictor import VERSION,GRIDS
from .milestone5_first_interval import differences
from .milestone5_validation import speed_change_direction

LOCAL_VERSION='local_serial_diagnosis@1.0.0'


def report(initial,results,command,start_s):
    """Assemble only predicted quantities; no observed endpoint is accepted."""
    if len(results)!=3 or any(r['grid']!=g for r,g in zip(results,GRIDS)):
        raise ValueError('FROZEN_LOCAL_THREE_RESOLUTIONS_REQUIRED')
    if not all(r['finite'] and r['solver_success'] and r['max_scaled_residual']<=1e-5 for r in results):
        raise ValueError('VALID_LOCAL_SOLUTIONS_REQUIRED')
    d=differences([dict(**r,step_s=r['grid']['max_step_s']) for r in results])
    numeric=all(r['velocity_m_s']<=1e-4 and r['speed_m_s']<=1e-4 for r in d)
    end=results[-1];delta=end['speed_m_s']-initial['speed_m_s']
    resolved=numeric and min(abs(delta-1e-4),abs(delta+1e-4))>d[-1]['speed_m_s']
    return dict(version=LOCAL_VERSION,predictor_version=VERSION,start_s=start_s,end_s=start_s+.01,
        frame='world',position_m=end['position_m'],velocity_m_s=end['velocity_m_s'],speed_m_s=end['speed_m_s'],
        endpoint_position_m=end['position_m'],endpoint_velocity_m_s=end['velocity_m_s'],endpoint_speed_m_s=end['speed_m_s'],
        initial_projected_speed_m_s=initial['speed_m_s'],predicted_speed_change_m_s=delta,
        direction=speed_change_direction(delta) if resolved else 'indeterminate',
        numerical_stable=numeric,numerical_uncertainty=d[-1],successive_differences=d,model_error_bound=None,
        input_n=list(command),input_information_time_s=start_s,
        numerical_cost_s=sum(r['cost_s'] for r in results),backend_steps=0,
        supported_scope='Observed projected reduced state and currently available held direct input, next .01 s. Experimental offline diagnosis; no quantitative or safety authority. Resolution differences are not a physical-error bound.')


def diagnose(model,state,command,start_s,*,charge,save_result,deadline):
    """Common single/dual-model interface, with caller-owned existing ledger hooks."""
    if start_s<0 or not np.isfinite(start_s):raise ValueError('LOCAL_CLOCK')
    initial=model.motion(state);results=[]
    for grid in GRIDS:
        charge()
        result=model.propagate(state,command,grid=grid,deadline=deadline)
        save_result(result);results.append(result)
    return report(initial,results,command,start_s)
