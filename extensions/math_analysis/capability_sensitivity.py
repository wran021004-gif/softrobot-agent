"""T2: controlled model stencils in absolute tension coordinates, without builders.

All derivatives and dual-face ranges are floating-point diagnostics, not proofs.
Caller owns the frozen source, topology and initial/operating-point construction.
"""
from copy import deepcopy
import time
import numpy as np

from extensions.math_analysis.conic_capability import conic_capability, _identity, _plain, DEFAULT_OPTIONS
from extensions.math_analysis.task_capability import normalization
from extensions.math_analysis.trajectory import prepare_trajectory, verify_witness


METHOD = 'controlled-capability-sensitivity-v1'
FACE_OPTIONS = dict(DEFAULT_OPTIONS, tol_gap_abs=1e-8, tol_gap_rel=1e-8)


def _parameter(parameters, path):
    parent = parameters
    for key in path.split('.')[:-1]:
        parent = parent[key]
    return parent, path.split('.')[-1]


def _prepare(point, protocol):
    model, req = point['model'], point['requirements']
    info = dict(coverage=[])
    scope, dynamics, initial, rows, lo, hi, _ = prepare_trajectory(
        model, req, protocol, info, point['initial_delta'])
    if not rows:
        raise ValueError('NO_COMMON_ANALYZED_CONSTRAINTS')
    # Convert the entire prediction map to absolute tensions U, including u0(d).
    nominal = np.tile(model.u0, scope['step_count'])
    atoms = []
    for row_index, (c, index, k, ref, _, base, matrix) in enumerate(rows):
        scale = normalization(c)
        M, b = matrix/scale, (base-ref-matrix@nominal)/scale
        identity = dict(row_index=row_index, constraint_id=c.constraint_id, sample_index=index,
                        control_step=k, normalization_scale=scale, signal=_plain(c.signal))
        if c.kind == 'norm_bound':
            atoms.append(dict(**identity, kind='soc', M=M, b=b))
        else:
            for side, sign, bound in (('lower', -1., -np.array(c.lower)/scale),
                                      ('upper', 1., np.array(c.upper)/scale)):
                for j in range(len(b)):
                    atoms.append(dict(**identity, kind='linear', side=side, component=j,
                                      M=sign*M[j], b=sign*b[j]-bound[j]))
    if not all(np.all(np.isfinite(a[k])) for a in atoms for k in ('M', 'b')):
        raise ValueError('NONFINITE_ABSOLUTE_INPUT_MAP')
    return dict(info=info, scope=scope, dynamics=dynamics, initial=initial, rows=rows,
                atoms=atoms, lower=lo+nominal, upper=hi+nominal)


def _validate(points, parameter, protocol):
    base = points[0]
    path = parameter['path']
    if not parameter.get('units') or not parameter.get('source'):
        raise ValueError('PARAMETER_UNITS_AND_SOURCE_REQUIRED')
    bounds = parameter.get('bounds')
    if bounds is not None and (len(bounds) != 2 or not np.all(np.isfinite(bounds))
            or bounds[0] >= bounds[1] or not parameter.get('bounds_source')):
        raise ValueError('AUTHORITATIVE_PARAMETER_RANGE_REQUIRED')
    seen = set(); prepared = []
    base_req = _plain(base['requirements']); base_req.pop('binding', None)
    bound_rule = parameter.get('input_bounds_treatment', 'fixed')
    if bound_rule not in ('fixed', 'parameter_dependent'):
        raise ValueError('UNKNOWN_INPUT_BOUND_TREATMENT')
    if bound_rule == 'parameter_dependent':
        if not parameter.get('input_bounds_source'):
            raise ValueError('PARAMETER_DEPENDENT_BOUND_SOURCE_REQUIRED')
        base_req['physical_inputs'] = {k:v for k,v in base_req['physical_inputs'].items() if k not in ('lower','upper')}
    context_keys = ('source_identity', 'topology_identity', 'fixed_configuration_identity', 'construction_rule')
    for point in points:
        if not point.get('source_reference') or 'initial_delta' not in point:
            raise ValueError('MODEL_SOURCE_AND_EXPLICIT_INITIAL_DELTA_REQUIRED')
        value = point['value']
        if not np.isfinite(value) or value in seen or (bounds is not None and not bounds[0] <= value <= bounds[1]):
            raise ValueError('DISTINCT_FINITE_PARAMETER_POINTS_INSIDE_RANGE_REQUIRED')
        seen.add(value)
        expected = deepcopy(base['parameters']); parent, key = _parameter(expected, path); parent[key] = value
        if expected != point['parameters']:
            raise ValueError('SINGLE_PARAMETER_CONTROLLED_COMPARISON_REQUIRED')
        if any(not base['context'].get(k) or point['context'].get(k) != base['context'][k] for k in context_keys):
            raise ValueError('SOURCE_TOPOLOGY_FIXED_CONFIGURATION_OR_CONSTRUCTION_MISMATCH')
        m, b = point['model'], base['model']
        for key in ('source_identity', 'task_identity', 'analysis_protocol_identity'):
            if m.binding.get(key) != b.binding.get(key):
                raise ValueError('MODEL_SOURCE_TASK_OR_PROTOCOL_MISMATCH')
        if m.binding.get('source_identity') is not None and m.binding['source_identity'] != point['context']['source_identity']:
            raise ValueError('DECLARED_AND_MODEL_SOURCE_MISMATCH')
        for key in ('coordinate_order', 'tendon_order'):
            if not b.binding.get(key) or m.binding.get(key) != b.binding[key]:
                raise ValueError('COORDINATE_OR_CHANNEL_IDENTITY_MISMATCH')
        order = point['requirements'].physical_inputs.get('tendon_order')
        if order is not None and order != m.binding['tendon_order']:
            raise ValueError('TASK_AND_MODEL_TENDON_ORDER_MISMATCH')
        for key in ('state_definition', 'input_definition'):
            if not getattr(b, key, None) or _plain(getattr(m, key, None)) != _plain(getattr(b, key)):
                raise ValueError('STATE_OR_INPUT_DEFINITION_MISMATCH')
        for key in ('name', 'phase', 'actual_time_s', 'remaining_task_s'):
            if m.operating_point.get(key) != b.operating_point.get(key):
                raise ValueError('OPERATING_POINT_RULE_OR_TIME_MISMATCH')
        req = _plain(point['requirements']); req.pop('binding', None)
        if bound_rule == 'parameter_dependent':
            req['physical_inputs'] = {k:v for k,v in req['physical_inputs'].items() if k not in ('lower','upper')}
        if req != base_req:
            raise ValueError('FROZEN_TASK_OR_PHYSICAL_INPUT_SEMANTICS_MISMATCH')
        data = _prepare(point, protocol)
        if prepared and (data['info']['coverage'] != prepared[0]['info']['coverage']
                or data['scope'] != prepared[0]['scope']):
            raise ValueError('TASK_COVERAGE_OR_SAMPLE_PHASE_MISMATCH')
        prepared.append(data)
    return prepared


def _fixed_replay(point, data, control, protocol):
    m = point['model']; scope = data['scope']
    delta = control.reshape(scope['step_count'], len(m.u0))-m.u0
    replay = verify_witness(m, data['dynamics'], data['initial'], delta, data['rows'], scope,
                            protocol.endpoint_check_atol)
    legal = bool(np.all(control >= data['lower']) and np.all(control <= data['upper']))
    valid = bool(replay.get('finite') and len(replay.get('records', [])) == len(data['rows'])
                 and replay['max_prediction_replay_error'] <= protocol.endpoint_check_atol)
    score = None
    if valid:
        for record, (c, *_) in zip(replay['records'], data['rows']):
            record['signed_excesses'] = (-np.array(record['margins'])/normalization(c)).tolist()
        score = max(max(r['signed_excesses']) for r in replay['records'])
    return dict(input_legal=legal, replay_valid=valid, score=score, replay=replay,
                control_treatment='same absolute tensions; illegal controls are diagnostic only')


def _contributions(left, right, width, control, dual):
    derivatives, records = [], []
    for a, b, multiplier in zip(left['atoms'], right['atoms'], dual['constraint_multipliers']):
        derivative = ((b['M']-a['M'])@control+b['b']-a['b'])/width
        left_residual, right_residual = a['M']@control+a['b'], b['M']@control+b['b']
        fixed_signed = ((float(np.linalg.norm(right_residual))-float(np.linalg.norm(left_residual)))/width
                        if a['kind'] == 'soc' else float(derivative))
        contribution = (-np.array(multiplier['soc_vector'])@derivative if a['kind'] == 'soc'
                        else multiplier['signed_multiplier']*derivative)
        derivatives.append(derivative)
        records.append(dict(**{k:v for k,v in a.items() if k not in ('M','b')},
            partial_normalized_residual=np.asarray(derivative).tolist(),
            fixed_signed_constraint_secant=fixed_signed,
            signed_multiplier=multiplier['signed_multiplier'], contribution=float(contribution)))
    dl, dh = (right['lower']-left['lower'])/width, (right['upper']-left['upper'])/width
    box = float(np.array(dual['box_lower_multipliers'])@dl-np.array(dual['box_upper_multipliers'])@dh)
    return derivatives, dl, dh, records, box


def _dual_face(data, solution, derivatives, dl, dh, parameter_scale, face_atol, progress=None):
    """Min/max envelope over a near-optimal dual face; independently check each return.

    This explores nonunique multipliers at one numerical primal. It does not prove
    primal uniqueness, regularity, or completeness of floating-point extrema.
    """
    import cvxpy as cp
    n = len(data['lower']); grad = cp.Constant(np.zeros(n)) if n else None
    mass, constant, objective = 0., 0., 0.
    constraints, variables = [], []
    for a, dr in zip(data['atoms'], derivatives):
        alpha = cp.Variable(nonneg=True)
        if a['kind'] == 'soc':
            v = cp.Variable(len(a['b'])); constraints.append(cp.SOC(alpha, v))
            if n: grad = grad-a['M'].T@v
            constant = constant-alpha-a['b']@v
            objective = objective-cp.sum(cp.multiply(dr, v))
        else:
            v = None
            if n: grad = grad+alpha*a['M']
            constant = constant+alpha*a['b']; objective = objective+alpha*float(dr)
        mass = mass+alpha; variables.append((alpha, v))
    ml = cp.Variable(n, nonneg=True) if n else None
    mh = cp.Variable(n, nonneg=True) if n else None
    if n:
        constraints.append(grad-ml+mh == 0)
        constant = constant+ml@data['lower']-mh@data['upper']
        objective = objective+ml@dl-mh@dh
    constraints.extend([mass == 1, constant >= solution['replayed_violation']-face_atol])
    extrema = []; tick = time.perf_counter()
    for sense in (1., -1.):
        problem = cp.Problem(cp.Minimize(sense*parameter_scale*objective), constraints)
        try:
            if progress:progress('dual_face','attempt',dict(sense=sense))
            problem.solve(solver='CLARABEL', **FACE_OPTIONS)
            if progress:progress('dual_face','returned',dict(sense=sense,status=problem.status))
        except cp.error.SolverError as exc:
            if progress:progress('dual_face','returned',dict(sense=sense,error=str(exc)))
            extrema.append(dict(status='unavailable', error=str(exc))); continue
        if problem.status != cp.OPTIMAL:
            extrema.append(dict(status=problem.status)); continue
        multipliers = []; gradient = np.zeros(n); c = 0.; weights = 0.; cone = 0.; slope = 0.
        for a, dr, (alpha, v) in zip(data['atoms'], derivatives, variables):
            w = float(alpha.value); weights += w; cone = max(cone, -w)
            row = dict(signed_multiplier=w)
            if v is not None:
                vec = np.array(v.value).ravel()
                cone = max(cone, float(np.linalg.norm(vec))-w)
                gradient -= a['M'].T@vec; c += -w-float(a['b']@vec)
                slope -= float(np.asarray(dr)@vec); row['soc_vector'] = vec.tolist()
            else:
                gradient += a['M']*w; c += a['b']*w; slope += float(dr)*w
            multipliers.append(row)
        low, high = (np.array(ml.value), np.array(mh.value)) if n else (np.zeros(0), np.zeros(0))
        gradient = gradient-low+high; c += low@data['lower']-high@data['upper']
        slope += low@dl-high@dh
        residual = max(float(np.max(abs(gradient), initial=0.)), abs(weights-1), cone,
                       float(np.max(-low, initial=0.)), float(np.max(-high, initial=0.)))
        face_gap = float(solution['replayed_violation']-c)
        checked = bool(np.isfinite(slope) and residual <= 1e-7 and -1e-7 <= face_gap <= face_atol+1e-7)
        extrema.append(dict(status='numerically_checked' if checked else 'unresolved', solver_status=problem.status, value=float(slope),
            residual=residual, primal_dual_gap=face_gap, task_multipliers=multipliers,
            box_lower_multipliers=low.tolist(), box_upper_multipliers=high.tolist(),
            iterations=problem.solver_stats.num_iters, solve_time_s=problem.solver_stats.solve_time))
    available = all(e['status'] == 'numerically_checked' for e in extrema)
    return dict(status='numerically_checked' if available else 'unresolved', extrema=extrema,
                range=[min(e['value'] for e in extrema), max(e['value'] for e in extrema)] if available else None,
                face_atol=face_atol, wall_s=time.perf_counter()-tick, solve_count=2,
                solver_options=FACE_OPTIONS,
                scope='Approximate near-optimal dual face at one primal; not a rigorous derivative range')


def _duplicates(prepared):
    """Exact equality across all supplied stencils, not merely close active scores."""
    groups = []; assigned = set()
    for i, a in enumerate(prepared[0]['atoms']):
        if i in assigned: continue
        group = [i]
        for j in range(i+1, len(prepared[0]['atoms'])):
            if j in assigned: continue
            if all(p['atoms'][i]['kind'] == p['atoms'][j]['kind']
                   and np.array_equal(p['atoms'][i]['M'], p['atoms'][j]['M'])
                   and np.array_equal(p['atoms'][i]['b'], p['atoms'][j]['b']) for p in prepared):
                group.append(j)
        if len(group) > 1:
            groups.append(group); assigned.update(group)
    return groups


def _redistribute(group, atoms, derivatives, multipliers):
    """Construct two legal-in-exact-arithmetic allocations for identical functions."""
    weight = sum(multipliers[j]['signed_multiplier'] for j in group)
    vector = (sum((np.array(multipliers[j]['soc_vector']) for j in group), np.zeros(len(atoms[group[0]]['b'])))
              if atoms[group[0]]['kind'] == 'soc' else None)
    alternatives = []
    for receiver in (group[0], group[-1]):
        if vector is not None:
            contribution = -float(vector@derivatives[receiver])
            gradient = -atoms[receiver]['M'].T@vector
            original = -sum((atoms[j]['M'].T@np.array(multipliers[j]['soc_vector']) for j in group), np.zeros_like(gradient))
        else:
            contribution = weight*float(derivatives[receiver]); gradient = atoms[receiver]['M']*weight
            original = sum((atoms[j]['M']*multipliers[j]['signed_multiplier'] for j in group), np.zeros_like(gradient))
        alternatives.append(dict(receiver_atom=receiver, other_group_weights=0., signed_multiplier=weight,
            soc_vector=vector.tolist() if vector is not None else None, contribution=contribution,
            stationarity_change_inf=float(np.max(abs(gradient-original), initial=0.)),
            cone_violation=max(0., float(np.linalg.norm(vector))-weight) if vector is not None else max(0., -weight)))
    return alternatives


def capability_sensitivity(points, parameter, protocol, *, solver_options=None,
                           slope_rtol=.02, slope_atol=1e-7, face_atol=1e-6, progress=None):
    """Analyze baseline-first controlled model points. Parameter units are SI.

    Each point supplies value, parameters, model, requirements, initial_delta,
    context, source_reference, and optionally construction_s. No models are built.
    slope_atol is in score per internal parameter scale (|d0| or largest step),
    not an invented physical normalization or a finite-difference error bound.
    """
    started = time.perf_counter()
    out = dict(method_version=METHOD, status='not_applicable', direction_status='unresolved',
        parameter_identity=parameter, parameter_units=parameter.get('units'),
        control_treatment='baseline absolute tension held vs independent reoptimization',
        model_scope='Frozen local affine sampled models; controlled fixed topology only',
        unsupported_inferences=['Strict differentiability or gradient error bound', 'Regional descent',
            'MuJoCo/closed-loop improvement', 'Physical acceptance', 'Unique optimal primal or dual'],
        regularity=dict(differentiability_proven=False, LICQ='not_asserted', primal_uniqueness='unassessed'))
    try:
        if len(points) < 2 or any(not np.isfinite(v) or v <= 0 for v in (slope_rtol, slope_atol, face_atol)):
            raise ValueError('MULTIPLE_POINTS_AND_POSITIVE_NUMERICAL_OPTIONS_REQUIRED')
        prepared = _validate(points, parameter, protocol)
        values = np.array([p['value'] for p in points]); origin = values[0]
        parameter_scale = max(abs(origin), float(max(abs(values-origin))))
        absolute_tolerance = slope_atol/parameter_scale
        out.update(status='computed_diagnostic', task_scope=dict(binding=_plain(points[0]['requirements'].binding),
            requirement_identity=_identity(points[0]['requirements']), protocol_identity=_identity(protocol),
            coverage=prepared[0]['info']['coverage'], horizon=prepared[0]['scope']),
            source_references=[p['source_reference'] for p in points],
            numerical_options=dict(slope_rtol=slope_rtol, scaled_slope_atol=slope_atol,
                internal_parameter_scale=parameter_scale, face_atol=face_atol, solver_options=solver_options),
            parameter_normalization=(dict(definition='xi=(d-dmin)/(dmax-dmin)', bounds=parameter['bounds'],
                source=parameter['bounds_source']) if parameter.get('bounds') else
                dict(definition=None, reason='No authoritative range; SI sensitivities only')))
        solutions = []
        for i,p in enumerate(points):
            if progress:progress('capability','attempt',dict(point_index=i))
            solution=conic_capability(p['model'], p['requirements'], protocol,
                initial_delta=p['initial_delta'], solver_options=solver_options)
            solutions.append(solution)
            if progress:progress('capability','returned',dict(point_index=i,status=solution['status'],solver=solution.get('solver')))
        out['numerical_optimality'] = [dict(value=float(d), model_identity=_identity(p['model']),
            initial_delta=_plain(p['initial_delta']), result=s) for d,p,s in zip(values, points, solutions)]
        out['computation_cost'] = dict(model_count=len(points),
            construction_s=sum(p.get('construction_s', 0.) for p in points),
            conic_solves=len(solutions), conic_kernel_s=sum(s['kernel_elapsed_s'] for s in solutions),
            dual_face_solves=0, dual_face_wall_s=0.)
        if any(s['optimality_status'] != 'numerically_checked' for s in solutions):
            out['reason'] = 'NUMERICAL_OPTIMALITY_INSUFFICIENT'; return out
        base = solutions[0]; dual = base['dual_checks']; U = np.array(base['applied_input_n']).ravel()
        fixed = [_fixed_replay(p, d, U, protocol) for p,d in zip(points, prepared)]
        out['fixed_control_sensitivity'] = dict(points=fixed, baseline_absolute_input_n=U.tolist())
        if not all(f['replay_valid'] and f['score'] is not None for f in fixed):
            out['reason'] = 'FIXED_CONTROL_REPLAY_FAILED'; return out
        duplicates = _duplicates(prepared)
        out['regularity']['duplicate_groups_across_stencil'] = duplicates
        active = [[i for i,a in enumerate(s['dual_checks']['constraint_multipliers']) if a['epigraph_active']] for s in solutions]
        out['active_constraints'] = dict(epigraph=active,
            task_boundary=[[i for i,a in enumerate(s['dual_checks']['constraint_multipliers']) if a['task_boundary_active']] for s in solutions],
            identities=[{k:v for k,v in a.items() if k not in ('M','b')} for a in prepared[0]['atoms']])
        out['regularity']['active_set_changed'] = any(a != active[0] for a in active[1:])
        differences = []; used = set()
        for i in sorted(range(1, len(points)), key=lambda j: abs(values[j]-origin), reverse=True):
            if i in used: continue
            delta = values[i]-origin
            mate = next((j for j in range(1, len(points)) if j != i and
                         abs(values[j]-origin+delta) <= 1e-10*abs(delta)), None)
            left, right = (i, mate) if delta < 0 else (mate, i)
            if mate is None: left, right = (i, 0) if delta < 0 else (0, i)
            used.update([left, right]); width = values[right]-values[left]
            dr, dl, dh, contributions, box = _contributions(prepared[left], prepared[right], width, U, dual)
            envelope = sum(c['contribution'] for c in contributions)+box
            sv = [s['replayed_violation'] for s in solutions]
            lower = [s['dual_checks']['support_lower_estimate'] for s in solutions]
            fd = (sv[right]-sv[left])/width
            interval = [(lower[right]-sv[left])/width, (sv[right]-lower[left])/width]
            face = _dual_face(prepared[0], base, dr, dl, dh, parameter_scale, face_atol,**({'progress':progress} if progress else {}))
            out['computation_cost']['dual_face_solves'] += face['solve_count']
            out['computation_cost']['dual_face_wall_s'] += face['wall_s']
            row = dict(kind='central' if mate is not None else 'one_sided_secant',
                left_value=float(values[left]), right_value=float(values[right]), step=abs(float(delta)),
                reoptimized=fd, numerical_slope_interval=interval,
                interval_strength='Floating support estimates propagated through secant, not truncation/rigorous error bounds',
                fixed_control=(fixed[right]['score']-fixed[left]['score'])/width,
                fixed_control_legal=all(fixed[j]['input_legal'] for j in (left,right)),
                envelope=envelope, constraint_contributions=contributions, box_contribution=box,
                dual_face=face, duplicate_aggregates=[dict(atom_indices=g,
                    signed_multiplier_sum=sum(dual['constraint_multipliers'][j]['signed_multiplier'] for j in g),
                    contribution=sum(contributions[j]['contribution'] for j in g),
                    alternative_allocations=_redistribute(g, prepared[0]['atoms'], dr, dual['constraint_multipliers'])) for g in duplicates])
            if mate is not None:
                row['left_reoptimized'] = (sv[0]-sv[left])/(origin-values[left])
                row['right_reoptimized'] = (sv[right]-sv[0])/(values[right]-origin)
                row['left_fixed_control'] = (fixed[0]['score']-fixed[left]['score'])/(origin-values[left])
                row['right_fixed_control'] = (fixed[right]['score']-fixed[0]['score'])/(values[right]-origin)
            if parameter.get('bounds'):
                row['normalized_reoptimized'] = fd*(parameter['bounds'][1]-parameter['bounds'][0])
                row['normalized_envelope'] = envelope*(parameter['bounds'][1]-parameter['bounds'][0])
            differences.append(row)
        out['reoptimized_finite_difference'] = differences
        out['envelope_sensitivity'] = dict(values=[r['envelope'] for r in differences],
            coordinates='fixed baseline absolute U and raw conic dual; entire rebuilt maps and physical box',
            interpretation='conditional envelope estimate; regularity is not proven')
        slopes = [r['reoptimized'] for r in differences]
        tolerance = absolute_tolerance+slope_rtol*max(abs(v) for v in slopes)
        fd_stable = len(differences) >= 2 and max(slopes)-min(slopes) <= tolerance
        fd_stable &= not out['regularity']['active_set_changed']
        envelope_consistent = True; multiplier_stable = True
        for row in differences:
            interval, face = row['numerical_slope_interval'], row['dual_face']
            fd_stable &= 0 <= interval[1]-interval[0] <= tolerance
            envelope_consistent &= abs(row['envelope']-row['reoptimized']) <= tolerance
            multiplier_stable &= (face['range'] is not None and face['range'][1]-face['range'][0] <= tolerance
                and face['range'][0]-tolerance <= row['envelope'] <= face['range'][1]+tolerance)
            if row['kind'] == 'central':
                fd_stable &= abs(row['left_reoptimized']-row['right_reoptimized']) <= tolerance
        stable = fd_stable and envelope_consistent and multiplier_stable
        out['envelope_sensitivity'].update(
            finite_difference_agreement=bool(envelope_consistent),
            multiplier_robustness='numerically_checked_face_range' if multiplier_stable else 'unresolved')
        out['regularity'].update(step_and_envelope_checks_passed=bool(stable), slope_comparison_tolerance=tolerance,
            finite_difference_checks_passed=bool(fd_stable),
            dual_face_interpretation='Only near-optimal multipliers at this primal explored; no LICQ/uniqueness proof')
        if stable:
            slope = slopes[-1]
            out['direction_status'] = ('numerically_flat_at_resolution' if abs(slope) <= tolerance
                else 'numerically_stable_local_direction' if all(r['kind']=='central' for r in differences)
                else 'one_sided_numerical_direction')
            out['preferred_parameter_direction'] = 'unresolved' if abs(slope) <= tolerance else 'decrease' if slope > 0 else 'increase'
        elif fd_stable:
            slope = slopes[-1]
            out['direction_status'] = ('numerically_flat_fd_envelope_unresolved' if abs(slope) <= tolerance
                else 'stable_reoptimized_direction_envelope_unresolved')
            out['preferred_parameter_direction'] = 'unresolved' if abs(slope) <= tolerance else 'decrease' if slope > 0 else 'increase'
        else:
            out['direction_status'] = 'directional_comparisons_only'
            out['preferred_parameter_direction'] = 'unresolved'
        dominant = sorted(differences[-1]['constraint_contributions'], key=lambda c: abs(c['contribution']), reverse=True)[:3]
        out['summary'] = dict(parameter=parameter['path'], direction=out['preferred_parameter_direction'],
            baseline_parameter_value=float(origin), baseline_model_identity=_identity(points[0]['model']),
            task_binding=_plain(points[0]['requirements'].binding), baseline_source=points[0]['source_reference'],
            reliability=out['direction_status'], dominant_constraints=[dict(constraint_id=c['constraint_id'],
                sample_index=c['sample_index'], contribution=c['contribution']) for c in dominant],
            scope='Fixed task and topology, sampled affine model only',
            next_validation='Additional local steps/regularity and independent nonlinear execution before physical use')
        return out
    except (ValueError, KeyError, TypeError, FloatingPointError, np.linalg.LinAlgError) as exc:
        out.update(status='not_applicable', reason=str(exc)); return out
    finally:
        out['kernel_elapsed_s'] = time.perf_counter()-started
