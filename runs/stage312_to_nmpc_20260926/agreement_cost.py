"""Reuse frozen Stage 3.11 errors; measure four small serial execution batches."""
import io
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import mujoco
import numpy as np
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.contracts import ResolvedGVSBasis, GVSModelParameters
from extensions.tendon_family.gvs_projection import discretization_jacobian, discretize, project, cell_average_basis
from extensions.tendon_family.mjcf import compile_xml
from extensions.tendon_family.model_applicability import assess_model_uses
from schemas.platform import Binding, Payload, SessionInput
from schemas.platform_math import ModelAgreementEvidence
from tools.platform_store import Store
from tools.state_io import atomic_json

HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'runs/stage311_discretization_convergence_20260926/discretization_convergence.json'
ROUTE = ROOT/'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def store():
    result = Store(HERE)
    if not result.db.exists():
        result.create(dict(project_id='stage312-nmpc', grant_id='stage312-nmpc-20260926',
            authorization_source='User requested autonomous Stage 3.12 through deterministic public NMPC execution',
            budget=dict(tool_calls=40, model_calls=0, backend_solves=8, worker_calls=0, wall_s=43200)))
    return result


def main():
    saved = read(SOURCE); frozen = saved['frozen_reference']; inp = SessionInput.model_validate(read(ROUTE))
    basis = ResolvedGVSBasis.model_validate(frozen['resolved_basis']); db = store()
    machine = dict(python=sys.version, interpreter=sys.executable, platform=platform.platform(),
        processor=platform.processor(), logical_cpus=os.cpu_count(), numpy=np.__version__, mujoco=mujoco.__version__)
    binding = Binding(extension_id='model.gvs', parameters=Payload(contract='family.gvs_model',
        data=GVSModelParameters.model_validate(frozen['gvs_parameters']).model_dump(mode='json')))
    output = []
    with db.transaction() as conn:
        source_ref = db.put(conn, saved)
        for row in saved['resolutions']:
            count = row['cells_per_segment']; timings = []
            for repetition in range(3):
                start = time.perf_counter(); physics = resolve(inp.robot.structure.data, row['discretization'])
                resolution_s = time.perf_counter()-start
                start = time.perf_counter(); xml = io.BytesIO(); compile_xml(physics, frozen['compiler_scene'], None, xml)
                generation_s = time.perf_counter()-start
                start = time.perf_counter(); model = mujoco.MjModel.from_xml_string(xml.getvalue().decode())
                compilation_s = time.perf_counter()-start; data = mujoco.MjData(model)
                joints = [model.joint(j).id for j in physics['dofs']]; qi = model.jnt_qposadr[joints]
                aids = [model.actuator(t+'_direct_tension').id for t in frozen['tendon_order']]
                q, v = discretize(physics, basis, frozen['q0'], np.zeros(basis.dimension))
                data.qpos[qi] = q; data.ctrl[aids] = frozen['u0_n']
                for _ in range(10): mujoco.mj_forward(model, data)
                start = time.perf_counter()
                for _ in range(100): mujoco.mj_forward(model, data)
                forward_s = (time.perf_counter()-start)/100
                for _ in range(10): mujoco.mj_step(model, data)
                mujoco.mj_resetData(model, data); data.qpos[qi] = q; data.ctrl[aids] = frozen['u0_n']
                start = time.perf_counter(); contacts = 0
                for _ in range(200):
                    mujoco.mj_step(model, data); contacts = max(contacts, data.ncon)
                step_s = time.perf_counter()-start
                valid = bool(np.isfinite(data.qpos).all() and not any(w.number for w in data.warning)
                             and abs(data.time-.1)<1e-10)
                timings.append(dict(resolve_s=resolution_s, mjcf_s=generation_s, compile_s=compilation_s,
                    forward_s=forward_s, step_wall_s=step_s, numerical_valid=valid, max_contacts=contacts))
            costs = dict(machine=machine, repetitions=timings, timestep_s=.0005, simulated_duration_s=.1,
                forward_calls=100, step_calls=200, warmup_forward=10, warmup_step=10,
                integrator='implicitfast', rendering=False, execution='held ideal tension u0; mapped q0, zero velocity')
            metrics = {}
            for name, comp, units in [('tip', row['component_positions']['tip'], 'm'),
                ('com',row['whole_robot']['com_comparison'],'m'),('gravity',row['gravity'],'N*m^2/rad'),
                ('constitutive_stiffness',row['stiffness'],'N*m^3/rad^2'),
                ('tendon_jacobian',row['tendon_jacobian'],'m^2/rad')]:
                metrics[name] = dict(absolute_error=comp['absolute_error'], relative_error=comp['relative_error'],
                    units=units, norm='Euclidean / Frobenius; relative to reference norm')
            ref_shape = np.concatenate([frozen['values']['backbone_world_m'][s.segment] for s in basis.segments])
            rms_reference = np.sqrt(np.mean(np.sum(ref_shape**2,axis=1)))
            metrics['shape'] = dict(absolute_error=row['metrics']['backbone_rms_error_m'],
                relative_error=row['metrics']['backbone_rms_error_m']/rms_reference if rms_reference else None,
                units='m', norm='RMS over 202 material points; relative to world-position RMS')
            item = ModelAgreementEvidence(design_identity=frozen['design_identity'], model_bindings=[binding],
                representation_ids={'model.gvs':frozen['basis_identity'],
                    'model.serial_bending_cells':row['discretization_identity']},
                numerical_settings=dict(gvs=frozen['gvs_parameters'], serial=row['discretization'],
                    backend_implementation='mujoco_serial_bending_v1', mujoco_version=saved['software']['mujoco']),
                mapping_convention='integrated_curvature_split_knots_v2',
                reference_state_input=dict(q=frozen['q0'], qdot=[0.]*basis.dimension, u=frozen['u0_n'],
                    coordinate_order=frozen['coordinate_order'], tendon_order=frozen['tendon_order']),
                environment=frozen['assembly'], measured_uses=['shape_prediction','static_equilibrium'],
                metrics=metrics, sources=[source_ref], source_locations=[str(SOURCE.relative_to(ROOT))+
                    f'#resolutions/{count}: complete per-tendon vectors and matrices'],
                limitations=['Single frozen state, static forces and geometry only; not equilibrium residual validation.',
                    'No dynamic, contact, global-equivalence or closed-loop validation.',
                    'Historical pre-Stage-3.11 evidence used midpoint mapping; unchanged.',
                    'Exact basis integration does not give exact finite-chain SE(3) geometry.'], costs=costs)
            ref = db.put(conn,item)
            context = {key:getattr(item,key) for key in ('numerical_settings','mapping_convention','reference_state_input','environment')}
            assessment = assess_model_uses(inp.robot,inp.task,binding,['shape_prediction','local_model_control'],
                evidence=[ref], evidence_loader=lambda r:db.artifact(r,db=conn), evidence_context=context)
            assert assessment.uses['shape_prediction'].validation=='measured_local'
            assert assessment.uses['local_model_control'].validation=='unavailable'
            np.testing.assert_allclose(discretization_jacobian(physics,basis),row['mapping_jacobian'],atol=1e-15)
            recovered = project(physics,basis,q,v)
            np.testing.assert_allclose(recovered['q_gvs'],frozen['q0'],atol=1e-12)
            output.append(dict(cells=count,evidence=ref.model_dump(),record=item.model_dump(mode='json'),
                assessment=assessment.model_dump(mode='json')))
            print(count, {k:float(np.median([t[k] for t in timings])) for k in ('resolve_s','mjcf_s','compile_s','forward_s','step_wall_s')},flush=True)
    # The middle third crosses the structural knot; average hat weights are 1/12, 5/6, 1/12.
    np.testing.assert_allclose(cell_average_basis(basis,basis.segments[0],1/3,2/3)[0,:3],[1/12,5/6,1/12],atol=1e-14)
    result = dict(rows=output, development_cells_per_segment=12,
        choice='12 cells: 4.14 mm measured tip discrepancy, below a 5 mm development allocation within the 10 mm task tolerance. Single-state static allowance, not a dynamic guarantee.',
        focused_checks='knot crossing, represented-state round trip and matched evidence consumption passed')
    atomic_json(HERE/'agreement_cost.json',result)


if __name__=='__main__': main()
