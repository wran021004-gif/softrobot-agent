"""Propagate fabrication/bend tolerances to local tip uncertainty and rank sources."""
import numpy as np
from schemas.pcc_tolerance import PCCTolerance
from tools.model_provider import PCCModel


def analyze(arguments):
    args=PCCTolerance.model_validate(arguments)
    model=PCCModel(args.length_m,args.bend_rad)
    tip=np.asarray(model.get(dict(quantity='tip',units='m'))['value'])
    jac=np.asarray(model.get(dict(quantity='tip_jacobian',units='m/rad'))['value'])
    derivatives=np.column_stack((tip/args.length_m,jac))
    deviations=derivatives*np.array([args.length_std_m,*args.bend_std_rad])
    covariance=deviations@deviations.T
    values,vectors=np.linalg.eigh(covariance)
    order=np.argsort(values)[::-1];values=np.maximum(values[order],0.);vectors=vectors[:,order]
    # Eigenvector sign is arbitrary; canonicalize it for stable saved output.
    for j in range(3):
        if vectors[np.argmax(np.abs(vectors[:,j])),j]<0:vectors[:,j]*=-1
    contributions=np.sum(deviations**2,axis=0);total=float(contributions.sum())
    ranked=sorted([dict(parameter=name,variance_contribution_m2=float(value),
        fraction_of_total=float(value/total) if total else 0.) for name,value in
        zip(('length_m','bend_u_rad','bend_v_rad'),contributions)],key=lambda r:-r['variance_contribution_m2'])
    return dict(nominal_tip_m=tip.tolist(),tip_covariance_m2=covariance.tolist(),
        tip_axis_std_m=np.sqrt(np.diag(covariance)).tolist(),rms_position_deviation_m=total**.5,
        principal_variances_m2=values.tolist(),principal_directions=vectors.T.tolist(),
        parameter_contributions=ranked,model=model.capabilities(),input=args.model_dump(mode='json'),backend_solves=0,
        assumptions=['Centered independent parameter perturbations; standard deviations are supplied, not calibrated.',
            'First-order covariance A diag(sigma^2) A^T; no finite-range bound, Gaussian assumption or confidence level.',
            'Local approximation can be poor for large tolerances or near the PCC branch boundary.',
            'Equal-fraction tolerance reduction benefits rank by variance contribution; manufacturing cost is not modeled.',
            'Directions in a repeated-eigenvalue subspace are not unique. Geometry only; no task or dynamics prediction.'])
