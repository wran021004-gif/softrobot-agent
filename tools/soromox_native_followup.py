"""One justified endpoint-derivative diagnostic; no optimization or mechanics repair."""
from pathlib import Path
import json
import time
import jax
jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp
import numpy as np
from soromox.systems import GVS, GVSSegment, JointSpec, LinkSpec, StrainBasisSpec


def check():
    started = time.perf_counter()
    link = LinkSpec.elliptical(length=.16, semi_major=.0095, semi_minor=.0076, density=1100.,
        young_modulus=7.2e6, poisson_ratio=.45, material_damping_coefficient=1., reference_strain=[0,0,0,1,0,0])
    probe = GVS.from_segments([GVSSegment(link, JointSpec.fixed(),
        StrainBasisSpec('legendre', ('kappa_y','kappa_z'), 2), 5)], backend='jax',
        base_pose=jnp.array([0.,0.,0.,1.,0.,0.,0.]))
    construction = time.perf_counter()-started
    tolerance = 1e-7
    records = []
    for kind in ('endpoint_abscissa', 'interior_abscissa', 'tips_api'):
        def position(length, q):
            robot = probe.update_link_params(length=jnp.reshape(length,(1,)))
            if kind=='tips_api':
                return robot.forward_kinematics_tips(q)[-1,:3,3]
            return robot.forward_kinematics(q, length*(.9 if kind=='interior_abscissa' else 1.))[:3,3]
        fn = jax.jit(position); derivative = jax.jit(jax.jacfwd(position, argnums=0))
        t = time.perf_counter()
        jax.block_until_ready((fn(.16,jnp.zeros(probe.num_coordinates)),derivative(.16,jnp.zeros(probe.num_coordinates))))
        cold = time.perf_counter()-t
        for q in (jnp.zeros(probe.num_coordinates), jnp.linspace(-2.,3.,probe.num_coordinates)):
            ad = np.asarray(derivative(.16,q))
            differences = []
            for h in (1e-4,1e-5,1e-6):
                fd = np.asarray((fn(.16+h,q)-fn(.16-h,q))/(2*h))
                differences.append(dict(step_m=h, fd=fd.tolist(), abs_error=float(np.max(np.abs(ad-fd)))))
            records.append(dict(api=kind,q=q.tolist(),position_m=np.asarray(fn(.16,q)).tolist(),ad=ad.tolist(),
                central_differences=differences,cold_compile_and_evaluate_s=cold))
    return dict(label='one unrotated native link in explicit identity pose; no candidate dynamics',
        tolerance_abs=tolerance,records=records,construction_s=construction,elapsed_s=time.perf_counter()-started)


if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(check(),indent=2),encoding='utf8')
