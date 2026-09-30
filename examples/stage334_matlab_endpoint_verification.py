"""One-session MATLAB/SciPy verification of repaired endpoint mathematics."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from extensions.math_analysis.kernels import (_minimum_residual_certificate, _output_endpoint,
    bounded_endpoint, endpoint_map)
from extensions.math_analysis.matlab import MatlabBatch
from schemas.platform_analysis import EndpointLinearizedModel, EndpointTarget, TaskAnalysisProtocol
from tools.platform_store import Store
from tools.state_io import atomic_json


def actual_models(long_root):
    long_store=Store(long_root/'analysis')
    linear=json.loads((long_root/'linearization.json').read_text(encoding='utf8'))
    long_ref=next(row['model'] for row in linear['records'] if row.get('model') and row['point']['name']=='controller_start_input')
    long_model=EndpointLinearizedModel.model_validate(long_store.artifact(long_ref))
    late_root=Path('runs/offline_task_analysis_20260930_final_v2');late_store=Store(late_root/'analysis')
    refs=json.loads((late_root/'late_public_references.json').read_text(encoding='utf8'))['linearizations']
    late_linear=late_store.artifact(refs['b2_near0p169_far0p129_compliant_s1p05'])
    one_ref=next(row['model'] for row in late_linear['records'] if row.get('model'))
    one_model=EndpointLinearizedModel.model_validate(late_store.artifact(one_ref))
    return [('actual_one_step_remaining',one_model,one_ref),('actual_full_task_remaining',long_model,long_ref)]


def check_close(a,b,atol=1e-8,rtol=2e-6):
    av,bv=np.asarray(a,dtype=float),np.asarray(b,dtype=float);difference=np.abs(av-bv)
    return dict(passed=bool(np.allclose(av,bv,atol=atol,rtol=rtol)),
        max_absolute_error=float(np.max(difference,initial=0.)),
        max_scaled_error=float(np.max(difference/(atol+rtol*np.abs(bv)),initial=0.)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    parser.add_argument('--long-root',type=Path,default=Path('runs/stage334_math_route_validation_20260930_v3'))
    args=parser.parse_args();root=args.output or Path('runs')/('stage334_matlab_endpoint_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    root.mkdir(parents=True,exist_ok=False)
    p=TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},duration_s=.35,period_s=.01,
        frequency_rad_s=[.1,1.,10.],samples_s=[])
    target=EndpointTarget(position_m=(.29,.035,.19),position_tolerance_m=.01,position_scale_m=.01,
        tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02)
    residual_fixtures=[
        ('scaled_regression',np.asarray([[5e-8,5e-8]]),np.asarray([0.]),np.asarray([7.5e-8]),np.asarray([0.,0.]),np.asarray([.1,2.]),2e-8,1e-8),
        ('analytic_feasible',np.asarray([[1.,0.]]),np.asarray([0.]),np.asarray([.5]),np.asarray([0.,0.]),np.asarray([1.,1.]),1e-8,1e-10),
        ('analytic_infeasible',np.zeros((1,2)),np.asarray([0.]),np.asarray([1.]),np.asarray([0.,0.]),np.asarray([1.,1.]),.1,1e-8),
    ]
    residual_rows=[];endpoint_rows=[]
    with MatlabBatch() as matlab:
        environment=matlab.environment
        for name,P,base,desired,lower,upper,limit,atol in residual_fixtures:
            scipy=_minimum_residual_certificate(P,base,desired,lower,upper,limit,atol)
            other=matlab.residual_certificate(P,base,desired,lower,upper,limit,atol)
            checks=dict(candidate_residual=check_close(scipy['candidate_residual'],other['candidate_residual']),
                lower_bound=check_close(scipy['separating_direction']['lower_bound'],other['separating_direction']['lower_bound']),
                certificate_agreement=scipy['certified_infeasible']==other['certified_infeasible'])
            residual_rows.append(dict(name=name,inputs=dict(P=P.tolist(),base=base.tolist(),target=desired.tolist(),
                lower=lower.tolist(),upper=upper.tolist(),limit=limit,atol=atol),scipy=scipy,matlab=other,checks=checks,
                passed=all(row if isinstance(row,bool) else row['passed'] for row in checks.values())))
        for name,model,reference in actual_models(args.long_root):
            local_target=EndpointTarget(position_m=tuple(model.binding['target_m']),
                position_tolerance_m=.01,position_scale_m=.01,tip_speed_limit_m_s=.02,tip_velocity_scale_m_s=.02)
            mapping=endpoint_map(model,model.operating_point['remaining_task_s'],p.period_s,p.horizon_alignment_atol_s)
            _,pbase,P=_output_endpoint(model,mapping,'tip_position');_,vbase,V=_output_endpoint(model,mapping,'tip_velocity')
            position=bounded_endpoint(model,p,local_target,braking=False)
            joint=bounded_endpoint(model,p,local_target,braking=True,
                warm_start=np.asarray(position['delta_input_n']).reshape(-1))
            other=matlab.endpoint(model,p,local_target)
            checks=dict(A_d=check_close(mapping['A_d'],other['A_d']),B_d=check_close(mapping['B_d'],other['B_d']),
                drift_d=check_close(mapping['drift_d'],other['drift_d']),affine_state=check_close(mapping['affine_state'],other['affine_state']),
                influence=check_close(mapping['influence'],other['influence']),position_base=check_close(pbase,other['position_base']),
                position_matrix=check_close(P,other['position_matrix']),velocity_base=check_close(vbase,other['velocity_base']),
                velocity_matrix=check_close(V,other['velocity_matrix']),
                position_candidate_residual=check_close(position['independent_residual_problems']['position']['candidate_residual'],
                    other['position_candidate']['candidate_residual'],atol=2e-8,rtol=2e-5),
                position_certificate=position['independent_residual_problems']['position']['certified_infeasible']==other['position_candidate']['certified_infeasible'],
                velocity_certificate=joint['independent_residual_problems']['tip_speed']['certified_infeasible']==other['velocity_candidate']['certified_infeasible'],
                joint_feasibility=joint['status']=='feasible_in_local_model' and other['joint']['feasible'] or
                    joint['status']!='feasible_in_local_model' and not other['joint']['feasible'])
            endpoint_rows.append(dict(name=name,model_reference=reference,remaining_task_s=model.operating_point['remaining_task_s'],
                dimensions=dict(state=len(model.x0),input=len(model.u0),steps=mapping['step_count']),
                scipy=dict(position=position,position_and_braking=joint),matlab=other,checks=checks,
                passed=all(row if isinstance(row,bool) else row['passed'] for row in checks.values())))
    result=dict(environment=environment,session_count=1,residual_fixtures=residual_rows,actual_endpoint_models=endpoint_rows,
        acceptance=dict(all_residual_fixtures_passed=all(row['passed'] for row in residual_rows),
            all_actual_endpoint_checks_passed=all(row['passed'] for row in endpoint_rows)))
    result['acceptance']['passed']=all(result['acceptance'].values())
    atomic_json(root/'matlab_scipy_endpoint_comparison.json',result)
    # Compact reproducible arrays; JSON report retains references and declared results.
    arrays={}
    for name,model,_ in actual_models(args.long_root):
        mapping=endpoint_map(model,model.operating_point['remaining_task_s'],p.period_s,p.horizon_alignment_atol_s)
        _,pbase,P=_output_endpoint(model,mapping,'tip_position');_,vbase,V=_output_endpoint(model,mapping,'tip_velocity')
        arrays.update({name+'_A':np.asarray(model.A),name+'_B':np.asarray(model.B),name+'_drift':np.asarray(model.drift),
            name+'_Ad':mapping['A_d'],name+'_Bd':mapping['B_d'],name+'_gd':mapping['drift_d'],
            name+'_pbase':pbase,name+'_P':P,name+'_vbase':vbase,name+'_V':V})
    np.savez_compressed(root/'representative_endpoint_matrices.npz',**arrays)
    if not result['acceptance']['passed']: raise RuntimeError(json.dumps(result['acceptance'],indent=2))
    print('Completed: '+str(root),flush=True)


if __name__=='__main__': main()
