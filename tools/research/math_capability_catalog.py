"""Read-only scientific classification, never an execution registry or admission gate.

Existing task_constraints declarations own executable method identity/meaning;
FamilySpace owns parameter domains. Cross-branch records describe audited source,
without importing its kernels, generating requests or granting execution.
"""
from copy import deepcopy


OPERATION_CATEGORIES = {
    'inspect': 'Inspect physical models, parameters, observables and mathematical capabilities.',
    'solve': 'Find equilibria, bounded feasible sequences or numerical optimization solutions.',
    'analyze': 'Analyze response, Jacobians, authority, constraints, modes and mechanisms.',
    'differentiate_optimize': 'Estimate parameter effects, local directions or applicable numerical optima.',
    'compare': 'Compare matched candidates, models, controls, ablations or saved evidence.',
}

# All audited records currently have readable source. These meanings also make
# absent/unconfirmed source explicit without inventing unsupported capabilities.
CAPABILITY_STATUS_MEANINGS = {
    'current_source': 'Current implementation; interface registration and candidate readiness are separate fields.',
    'source_available_unadapted': 'Audited computational source outside the current formal analysis interface.',
    'historical_helper': 'Only a historical helper/script interface; not a reusable formal execution entry.',
    'source_unconfirmed': 'Implementation or source cannot be confirmed; no execution claim.',
}


def _record(categories, source, models, inputs, outputs, prerequisites, limitation=None):
    return dict(generic_operations=categories.split(), implementation_locations=source.split(),
        model_scope=models, inputs=inputs, observables=outputs,
        prerequisites=prerequisites, limitations=[limitation] if limitation else [])


# Classification annotations only. Neither membership nor these categories add an
# operation to AnalysisRequest; registered_analysis_method_names remains its owner.
_METHOD_METADATA = {
    'mechanism_structure_v1': _record('inspect analyze differentiate_optimize compare',
        'tools/research/structure_research.py::calculate extensions/math_analysis/mechanism_registry.py::observe extensions/math_analysis/differentiation_router.py::differentiate',
        'Native instantaneous ideal-tension mechanics', 'Registered target, explicit point/input semantics, legal effective length and local evaluation cap',
        'Mechanism observation, two-scale secants and proposal-only structure direction', 'Explicit new V2 Study and method grant; original analysis admission'),
    'linearization': _record('analyze',
        'extensions/tendon_family/math_analysis.py::linear_model extensions/tendon_family/sorosim_analysis.py::calculate_candidate_configuration',
        'GVS / SoRoSim local continuous affine dynamics', 'Candidate, operating point, protocol and model',
        'A/B/C/D, affine drift, normalized spectra', 'Applicable model and declared working point/window'),
    'controllability': _record('analyze', 'extensions/math_analysis/tools.py::calculate_control_metrics',
        'Normalized local affine dynamics', 'Bound linear model, input scales and finite window',
        'Continuous and held-input Gramians, ranks and output authority', 'Consistent units and positive aligned window'),
    'equilibrium': _record('solve analyze',
        'extensions/tendon_family/math_analysis.py::_candidate_points extensions/tendon_family/sorosim_analysis.py::calculate_candidate_configuration',
        'Active bounded-input GVS / SoRoSim static construction', 'Candidate, constant target, bounded tensions',
        'Attempt tensions, target and static residuals', 'Constant reference and supported static physics'),
    'input_sensitivity': _record('differentiate_optimize analyze',
        'extensions/tendon_family/sorosim_analysis.py::calculate_candidate_configuration',
        'SoRoSim static implicit response', 'Fixed-input equilibrium and input perturbation protocol',
        'Equilibrium state and position response to tension', 'Verified regular fixed-input equilibrium'),
    'design_sensitivity': _record('differentiate_optimize compare',
        'extensions/tendon_family/sorosim_analysis.py::calculate_candidate_configuration',
        'SoRoSim fixed-input structural response', 'Baseline and two same-task single-parameter candidates',
        'Static state/position derivatives and re-equilibrium checks', 'Matched physical input and verified regularity'),
    'mujoco_direct_control_v1': _record('solve differentiate_optimize', 'tools/research/native_control.py::calculate',
        'Native MuJoCo bounded full-horizon sequence search', 'Candidate, exact state, full control source and search settings',
        'Best-found signed excess, sampled task quantities and explicit schedule', 'Owned source, supported complete task and bounded search budget'),
    'native_dynamics_v1': _record('analyze', 'extensions/tendon_family/mujoco_analysis.py::NativeModel.mechanics',
        'Native named hinges and ideal absolute SI tensions', 'Exact native checkpoint and physical input',
        'Mass, forces, acceleration, world tip and tendon Jacobians', 'Supported native physics and exact integration state'),
    'short_input_response_v1': _record('analyze differentiate_optimize', 'extensions/tendon_family/mujoco_analysis.py::input_response',
        'Native short integrated response', 'Exact state, legal input steps and short horizon',
        'Position/input and velocity/input FD Jacobians; optional checked correction', 'Physical input bounds and two declared FD scales'),
    'fixed_input_structure_v1': _record('analyze compare differentiate_optimize', 'extensions/tendon_family/mujoco_analysis.py::calculate',
        'Native paired structure response', 'Single-parameter candidates, matched named state and fixed input',
        'Mechanics and short trajectory contrasts', 'Comparable topology/state bindings and legal rebuilt candidates'),
    'endpoint': _record('solve', 'extensions/math_analysis/kernels.py::bounded_endpoint',
        'Bounded sampled affine model', 'Bound model, endpoint target and physical input box',
        'Terminal position witness and residual checks', 'Compatible terminal output and remaining horizon'),
    'braking': _record('solve analyze', 'extensions/math_analysis/kernels.py::bounded_endpoint',
        'Bounded sampled affine model', 'Bound model and terminal position/speed conditions',
        'Terminal braking witness and residual checks', 'Compatible position/velocity outputs and horizon'),
    'instantaneous_braking_v1': _record('solve analyze', 'extensions/math_analysis/kernels.py::instantaneous_braking',
        'Exact-instant affine acceleration and input box', 'Saved point, velocity and acceleration map',
        'Minimum instantaneous speed derivative and bounded input', 'Exact state and checked acceleration semantics'),
    'trajectory_feasibility': _record('solve analyze', 'extensions/math_analysis/trajectory.py::trajectory_feasibility',
        'Sampled affine held-input recurrence', 'Bound model, task constraints, actual grid and input box',
        'Sequence, independent recurrence replay and checked/unchecked samples', 'Compatible outputs and complete declared time scope'),
    'task_capability': _record('solve differentiate_optimize compare', 'extensions/math_analysis/task_capability.py::task_capability',
        'Sampled affine three-start SLSQP minimax', 'Bound model and normalized task constraints',
        'Best-found normalized signed excess and optional fixed-control contrast', 'Matched task/model/grid and comparable control for contrasts'),
    'sampled-affine-conic-minimax-v1': _record('solve differentiate_optimize', 'extensions/math_analysis/conic_capability.py::conic_capability',
        'Sampled affine SOCP, including supported free path progress', 'Bound model, supported constraints and physical box',
        'Numerical minimax value, primal/dual/gap estimates and replay', 'Compatible outputs, model and finite horizon; conic dependencies'),
    'controlled-capability-sensitivity-v1': _record('differentiate_optimize compare', 'extensions/math_analysis/capability_sensitivity.py::capability_sensitivity',
        'Matched affine conic model stencil', 'Saved baseline and +/-h models, optional half steps',
        'Reoptimized FD, fixed-control, envelope and dual-face responses', 'Authorized continuous variable and validated comparable model stencil'),
}


def _registered_metadata():
    from tools.research.nonlinear_capability import T1, T2
    rows=deepcopy(_METHOD_METADATA)
    rows[T1]=_record('solve differentiate_optimize', 'tools/research/native_control.py::calculate tools/research/nonlinear_capability.py::t1_summary',
        'Native Reach/Hold finite-budget nonlinear task response', 'Candidate, exact initial state, source and bounded search settings',
        'best_found_J, frozen task quantities, search quality and schedule', 'Current Reach task, complete source and original admission')
    rows[T2]=_record('differentiate_optimize compare', 'tools/research/nonlinear_capability.py::response',
        'Saved comparable Reach T1 evidence; no new integration', 'Baseline/minus/plus T1 results and admitted directions/scales',
        'Fixed-control and reoptimized secants, active-time switches and prediction checks', 'Completed same-task T1 stencil and matched search opportunities')
    return rows


_PHS_SOURCE = dict(branch='research/phs2d-inverse-passive-design',
    commit='9d6d160e050c836b87d0563a497fc0ec1c3761a8', availability='local_source_and_remote_ref_verified')
_P3_SOURCE = dict(branch='codex/passive-progressive-stiffness',
    commit='83d9b8f35b4015a924e0f8c32d073607247f92b9', availability='local_source_only_remote_ref_not_returned')


def _unintegrated_metadata():
    """Audited source descriptions; never executable templates or solver imports."""
    rows={
        'passive_equilibrium_v1': _record('solve analyze', 'extensions/tendon_family/passive_equilibrium.py::solve',
            'Native hard unilateral fixed-payout static model', 'Passive assembly, payout lengths, material-point load, initial pose',
            'Equilibrium, tensions, residuals, LICQ, complementarity and reduced spectrum', 'No actuators; actual gravity, material-point and payout bindings',
            'Qualified local minimum only; hard static constraints differ from soft-constraint dynamics.'),
        'passive_constrained_compliance_v2': _record('analyze', 'extensions/tendon_family/passive_equilibrium.py::tangent',
            'Constrained tangent Hessian and one-sided cone QP', 'Qualified equilibrium, material-point locations and load increment',
            'Local displacement, tip response, active rank and Hessian', 'Qualified equilibrium and actual positive/boundary multiplier sets',
            'Finite loads or slack/taut switches require nonlinear re-equilibrium and independent dynamics.'),
        'passive_modal_target_v1': _record('analyze', 'extensions/tendon_family/passive_inverse.py::modal_target',
            'Native passive Jacobians, nullspaces and unilateral force response', 'Qualified equilibrium and material-point locations',
            'Tip/point/length Jacobians, ideal null modes, feasible cone and actual force response', 'Qualified equilibrium, native coordinates and geometric Hessian',
            'Ideal kinematic modes, unilateral feasibility and force excitation are separate tests.'),
        'tendon_jacobian_matching_v1': _record('analyze differentiate_optimize',
            'extensions/tendon_family/passive_inverse.py::matching tools/research/phs2d_inverse.py::optimize_matching',
            'Native geometric Jacobian row-space matching', 'Actual routing and supplied geometric pose',
            'Row residuals, singular values, coefficients and low-dimensional prototype', 'Actual tendon and tip Jacobians in the same coordinates',
            'Perfect row matching does not imply positive tension activation or finite-force performance; geometry optimization stays in its historical runner.'),
        'route_geometry_validation_v1': _record('inspect analyze', 'extensions/tendon_family/route_validation.py::validate_routes',
            'Straight tendon segments and compiled solid convex hulls', 'Native physical assembly, cable radii and saved poses',
            'Owned-hole/anchor exceptions and legal/illegal checked-pose geometry', 'Actual physical guide holes, anchors and solid ownership',
            'Saved poses only; no continuous collision, rope friction or manufacturing certification.'),
        'passive_design_sensitivity_v1': _record('differentiate_optimize compare',
            'extensions/tendon_family/passive_inverse.py::design_sensitivity extensions/tendon_family/passive_inverse.py::task_design_sensitivity',
            'Fixed-topology passive KKT implicit response with re-equilibrium FD', 'Baseline/loaded equilibria and +/- normalized-parameter assemblies',
            'State, tension, slack and baseline-relative task derivatives; resolved FD checks', 'Qualified equilibria, LICQ, strict complementarity, regular KKT and unchanged point binding',
            'Generic supplied perturbation models; only modulus was validated in the cited six branches. No dynamic gradient or discrete-topology derivative.'),
        'passive_multicase_design_v1': _record('compare analyze',
            'extensions/tendon_family/passive_inverse.py::multicase_metrics tools/research/phs2d_inverse.py::screen',
            'Passive multi-load static screening composition', 'Valid unloaded baseline and loaded equilibria under frozen thresholds',
            'Point/tip/ratio/plane violations and validity-first worst case', 'Every compared load must be valid; raw ratios retained',
            'screen is task orchestration; retain reusable metric arithmetic, not the whole runner. No formal task acceptance.'),
        'passive_load_response_metrics_v1': _record('analyze compare', 'tools/research/passive_evaluation.py::response_metrics',
            'Saved passive progressive load-response observations', 'Forces, settled displacements, uncertainty and frozen precision thresholds',
            'Secant/interval stiffness and stiffness ratio', 'Positive displacement increments above uncertainty floor',
            'Local historical P3 helper; 1/2 cells passed, 4 cells INVALID. No spatial convergence claim.'),
        'passive_mechanism_ablation_v1': _record('compare', 'tools/research/passive_evaluation.py::mechanism',
            'Paired passive constrained/unrestricted saved evaluations', 'Matched load protocols and independently valid settled observations',
            'High-load displacement and late-stiffness ratios', 'Both runs valid/stable; disable tendon limits only and preserve physical solids/mass',
            'Invalid or unsettled pairs remain UNKNOWN; development evaluator is not a formal Agent interface.'),
    }
    for key,row in rows.items():
        row.update(source=deepcopy(_P3_SOURCE if key.startswith(('passive_load_', 'passive_mechanism_')) else _PHS_SOURCE),
            implementation_status='historical_helper' if key.startswith(('passive_load_', 'passive_mechanism_')) else 'source_available_unadapted',
            capability_kind='historical_helper' if key.startswith(('passive_load_', 'passive_mechanism_')) else
                'task_orchestration_with_reusable_metrics' if key=='passive_multicase_design_v1' else 'reusable_kernel')
    return rows


def generic_operations(method):
    """Annotations for existing registered methods; never infer a new method."""
    return _registered_metadata()[method]['generic_operations']


def capability_inventory(methods=None, reference=None):
    """Join audited metadata to original candidate readiness without recomputing it.

    Omitted methods have unknown candidate availability, even when formally
    integrated. Unadapted source always has no current formal execution entry.
    """
    from tools.research.task_constraints import METHOD_MEANINGS, registered_analysis_method_names
    from tools.research.nonlinear_capability import LIMITATIONS
    methods={} if methods is None else methods
    registered=set(registered_analysis_method_names());rows=_registered_metadata()
    for method,row in rows.items():
        meaning=METHOD_MEANINGS.get(method)
        detail=methods.get(method)
        row['limitations']=[meaning[1]] if meaning else list(LIMITATIONS)
        row.update(method_id=method, implementation_status='current_source', capability_kind='registered_analysis',
            interface_status='registered' if method in registered else 'unregistered',
            has_formal_execution_entry=method in registered, source=dict(scope='current_checkout'),
            scientific_purpose=meaning[0] if meaning else 'Finite-budget nonlinear research diagnostic',
            result_meaning=meaning[1] if meaning else ' '.join(LIMITATIONS),
            current_execution=dict(assessed=detail is not None,
                **({k:deepcopy(detail[k]) for k in ('planning_status','execution_status','executable','missing') if k in detail} if detail else {}),
                requires_original_admission=True))
        if detail:row['current_method_query']=deepcopy(detail['detail_query'])
    for method,row in _unintegrated_metadata().items():
        row.update(method_id=method,interface_status='not_integrated',has_formal_execution_entry=False,
            result_meaning=row['observables'],current_execution=dict(assessed=True,executable=False,
                reason='No current AnalysisRequest/TaskAdapter adaptation; source existence is not execution permission.'))
        rows[method]=row
    for method,row in rows.items():
        row['detail_query']=dict(reference=reference,view='mathematical_capabilities',pointer='/capability_inventory/'+method) if reference else None
    return rows


def parameter_sensitivity_scope(parameter):
    """Classify original parameter facts, retaining their domain and method owner."""
    category=parameter['category'];path=parameter['parameter_id']
    if category=='discretization':kind='numerical_resolution'
    elif category=='topology' or parameter['data_type'] in ('integer','enum','routing_topology','route_points'):kind='discrete_comparison'
    elif category=='controller':kind='controller_performance'
    elif path.endswith('pretension_n'):kind='initialization_dependent'
    elif not parameter['effective_in_current_execution'] or not parameter['continuous_perturbation']:kind='inactive_or_unresolved'
    else:kind='continuous_conditional'
    return dict(parameter_kind=kind,methods=parameter.get('applicable_mathematical_methods',[]),
        derivative_validated='not_established_by_catalog',
        scope='Use original effectiveness, authorization, domain and method_links; continuity alone grants neither a derivative nor execution.',
        prerequisites=['Rebuild legal perturbation candidates and preserve physical/model bindings.',
            'Static response requires re-equilibrium and regular active sets; dynamic performance requires matched trajectories or reoptimized control.',
            'Damping, controller weights and discrete topology cannot use a static equilibrium gradient as dynamic performance sensitivity.'])
