"""Opt-in component probes for the recorded C1 dense GVS failure; no rollout."""
from copy import deepcopy
import platform
import time
from pathlib import Path
import casadi as ca
import numpy as np
from tools.research.config import ROOT, resolve
from tools.platform_store import plain
from tools.state_io import read, digest, atomic_json
from extensions.tendon_family.family_space import FamilyBuild
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.gvs import GVSModel, coordinate_order
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions, expression_from_system
from schemas.platform import SessionInput
from schemas.platform_math import SystemContext


def run():
    spec = resolve(ROOT/'configs/research/study_family_space_dev.json')
    original = read(ROOT/'evidence/m3c1_family_space/numerical_limitation.json')
    controls = read(ROOT/'evidence/m3c1_family_space/construction.json')
    requests = dict(dense=original['request_parameters'],
                    control12=controls['candidates']['1']['request'],
                    control14=controls['candidates']['mixed']['request'])
    rows = {}
    for name, request in requests.items():
        started = time.perf_counter()
        build = FamilyBuild(space=spec['family_space'], request=dict(
            family_space_identity=spec['family_space_identity'], **request))
        design, mesh, physics = generate_family(build)
        cfg = deepcopy(spec['configuration'])
        cfg['robot']['structure']['data'] = design
        cfg['policy']['discretization']['data'] = mesh
        inp = SessionInput.model_validate(cfg)
        params = GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
        system = GVSModel(params).build_system(inp.robot, params, None,
            SystemContext(x0=[0.]*(2*len(coordinate_order(design,params.basis))),
                u0=[t['pretension_n'] for t in design['tendons']],scene=inp.task.environment))
        expression = expression_from_system(system)
        funcs = GVSCasadiFunctions(expression)
        n = len(expression.coordinate_order)
        x = np.zeros(2*n)
        u = np.array([t['pretension_n'] for t in design['tendons']])
        row = dict(physical_identity=physics['identity'], request=request,
            physical_design_identity=digest(design), coordinate_order=expression.coordinate_order,
            tendon_order=expression.tendon_order, tensions_n=u.tolist(),
            resolved_basis=plain(expression.resolved_basis), parameters=plain(params),
            gravity_robot_base_m_s2=expression.gravity_robot_base_m_s2,
            scene=plain(inp.task.environment), model_construction='passed', coordinates=n)
        # Function.factory selects outputs and excludes the unused solve graph.
        terms = funcs.function.factory('component_probe', ['x','u'],
            ['mass_matrix','gravity_force','velocity_bias','elastic_force',
             'damping_force','tendon_generalized_force','tendon_lengths_m','tendon_length_jacobian'])
        values = terms(x=x,u=u)
        arr = {k:np.array(v) for k,v in values.items()}
        row['terms'] = {k:dict(shape=list(v.shape), finite=bool(np.isfinite(v).all()),
            norm=float(np.linalg.norm(v))) for k,v in arr.items()}
        mass = arr['mass_matrix']
        rhs = (arr['tendon_generalized_force']+arr['gravity_force']-arr['velocity_bias']
               -arr['elastic_force']-arr['damping_force'])
        singular = np.linalg.svd(mass,compute_uv=False)
        row.update(mass_shape=list(mass.shape), rank=int(np.linalg.matrix_rank(mass)),
            singular_values=singular.tolist(), condition=float(singular[0]/singular[-1]),
            symmetry_residual=float(np.linalg.norm(mass-mass.T)),
            minimum_eigenvalue=float(np.linalg.eigvalsh(mass).min()),
            eigenvalue_caveat='Generalized mass entries depend on curvature-coordinate units and basis scaling.',
            rhs_finite=bool(np.isfinite(rhs).all()),rhs_norm=float(np.linalg.norm(rhs)))
        solved = np.linalg.solve(mass,rhs)
        row['numpy_solve'] = dict(finite=bool(np.isfinite(solved).all()),
            relative_residual=float(np.linalg.norm(mass@solved-rhs)/np.linalg.norm(rhs)))
        row['implicit_terms_finite'] = all(np.isfinite(np.array(v)).all()
            for v in funcs.implicit_terms(x,u))
        try:
            evaluated = funcs.evaluate(x,u)
            row['xdot'] = dict(status='passed',finite=bool(np.isfinite(evaluated['xdot']).all()),
                relative_residual=float(np.linalg.norm(mass@evaluated['qdd']-rhs)/np.linalg.norm(rhs)),
                numpy_relative_difference=float(np.linalg.norm(evaluated['qdd']-solved)/np.linalg.norm(solved)))
        except RuntimeError as exc:
            row['xdot'] = dict(status='failed',exception=str(exc))
        row['isolated_solvers'] = {}
        for plugin in ('qr','csparse','lapacklu'):
            try:
                a=ca.MX.sym('a',n,n);b=ca.MX.sym('b',n)
                solve=ca.Function('isolated_'+plugin,[a,b],[ca.solve(a,b,plugin)])
                result=np.array(solve(mass,rhs))
                row['isolated_solvers'][plugin]=dict(status='passed',finite=bool(np.isfinite(result).all()),
                    relative_residual=float(np.linalg.norm(mass@result-rhs)/np.linalg.norm(rhs)))
            except RuntimeError as exc:
                row['isolated_solvers'][plugin]=dict(status='failed',exception=str(exc))
        row['elapsed_s']=time.perf_counter()-started
        rows[name]=row
        print(name,n,row['xdot']['status'],flush=True)
        atomic_json(ROOT/'evidence/m3c2_variable_segments/gvs_dense_diagnostic.json',dict(
            original_failure=original, implementation_base='bafad737824f7ff09741dbbc9273a2dba34bf882',
            environment=dict(python=platform.python_version(),casadi=ca.__version__,numpy=np.__version__,
                threads={k:__import__('os').environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}),
            physical_pose='Candidate-owned zero curvature and velocity; bounded candidate pretensions',
            comparison_caveat='Historical controls differ in tendon/routing geometry, not dimension alone. No basis-only override supported by structural-node semantics.',
            cases=rows,resources=dict(provider_requests=0,physics_steps=0,rl_training=0,complete_task_evaluations=0)))


if __name__ == '__main__':
    run()
