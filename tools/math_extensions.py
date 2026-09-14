"""A local mathematical extension: implementation + contract + registry only."""
import numpy as np
from schemas.framework import PCCCondition
from tools.model_provider import PCCModel


def pcc_condition(arguments):
    args=PCCCondition.model_validate(arguments)
    model=PCCModel(args.length_m,args.bend_rad)
    value=model.get(dict(quantity='tip_jacobian',units='m/rad'))
    singular=np.linalg.svd(value['value'],compute_uv=False)
    rank=int(np.count_nonzero(singular>singular[0]*args.relative_rank_tolerance))
    return dict(singular_values_m_per_rad=singular.tolist(),rank=rank,
        condition_number=float(singular[0]/singular[-1]) if rank==2 else None,
        condition_status='FINITE' if rank==2 else 'RANK_DEFICIENT',
        relative_rank_tolerance=args.relative_rank_tolerance,model=value['model'],input=value['source'],
        analysis_status='LOCAL_GEOMETRY_ONLY',backend_solves=0,
        limitations=['A geometric differential is not dynamic controllability, reachability, stability or calibration.'])
