"""Frozen first-study composition over existing SessionInput and evidence contracts."""
from copy import deepcopy
from pathlib import Path
from typing import Literal
import hashlib
import json
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef, SessionInput, Budget
from tools.platform_store import encode
from tools.state_io import atomic_json, digest, read

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'configs/research/reach_hold_v1.json'
VERSION = 'research.reach_hold_initial_variation@1.0.0'


class InitialCase(Contract):
    case_id: str
    total_angle_rad: dict[str, float]
    total_angle_rate_rad_s: dict[str, float]


class ResearchSpecification(Contract):
    version: Literal['research.reach_hold_initial_variation@1.0.0'] = VERSION
    question: str
    source: dict
    starting_configuration: dict
    execution_template: SessionInput
    parameter_pool_version: str
    parameter_grants: dict
    cases: list[InitialCase] = Field(min_length=1)
    repetitions: dict
    initial_state_mapping: dict
    acceptance: dict
    metrics: dict
    fixed_baseline: dict
    comparison_groups: dict
    formal_budget_per_group: Budget
    integration_validation: dict
    uncertainty: list[str]
    boundaries: dict

    @model_validator(mode='after')
    def frozen_bindings(self):
        ref = self.source['candidate']['configuration']
        if hashlib.sha256(encode(self.starting_configuration).encode('utf8')).hexdigest() != ref['artifact_id']:
            raise ValueError('STARTING_CONFIGURATION_BINDING_CHANGED')
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise ValueError('DUPLICATE_STUDY_CASE')
        if self.acceptance['real_time_required'] or self.repetitions['cache'] != 'new':
            raise ValueError('OFFLINE_STUDY_OR_FRESH_REPETITION_REQUIRED')
        original = self.starting_configuration['effective']
        template = self.execution_template.model_dump(mode='json')
        for field in ('task', 'robot'):
            if field == 'robot':
                a, b = deepcopy(original[field]), deepcopy(template[field])
                # New registered selectors retain the exact physical source.
                a['structure']['data']['metadata'] = {}; b['structure']['data']['metadata'] = {}
                if a != b: raise ValueError('STARTING_PHYSICAL_CONFIGURATION_CHANGED')
            elif original[field] != template[field]:
                raise ValueError('TASK_TIMING_OR_STANDARDS_CHANGED')
        for key in ('controller', 'backend', 'dynamics_model', 'discretization'):
            if original['policy'][key] != template['policy'][key]:
                raise ValueError('STARTING_EXECUTION_BINDING_CHANGED: ' + key)
        if set(self.parameter_grants) != set(template['policy']['candidate_builder']['parameters']['data']['parameters']) | set(template['policy']['candidate_builder']['parameters']['data']['control_parameters']):
            raise ValueError('POOL_GRANT_MISMATCH')
        return self


def load_spec(path=SPEC_PATH):
    value = read(path)
    claimed = value.pop('specification_identity', None)
    spec = ResearchSpecification.model_validate(value)
    if claimed != digest(spec.model_dump(mode='json')):
        raise ValueError('FROZEN_RESEARCH_SPECIFICATION_CHANGED')
    return spec.model_dump(mode='json')


def map_initial_state(effective, case):
    """Same normalized-arc principal bend profile and its time derivative.

    Total bending angle, rather than curvature per metre or tip displacement,
    is the external challenge. Same orientation/aspect ratios/topology are fixed.
    Length-dependent curvature, mass, tip position and energy necessarily vary.
    """
    from extensions.tendon_family.backends import physics_for
    case = InitialCase.model_validate(case).model_dump(mode='json')
    cells = effective['policy']['discretization']['data']['cells']
    dofs = physics_for(SessionInput.model_validate(effective))['dofs']
    q = dict.fromkeys(dofs, 0.); v = dict.fromkeys(dofs, 0.)
    for field, target in (('total_angle_rad', q), ('total_angle_rate_rad_s', v)):
        for axis, value in case[field].items():
            segment, principal = axis.rsplit('_', 1)
            if principal not in ('y', 'z') or segment not in cells:
                raise ValueError('UNSUPPORTED_INITIAL_PROFILE')
            for i in range(cells[segment]):
                target[f'{segment}_cell_{i}_{principal}'] = value / cells[segment]
    if max(map(abs, q.values())) > .05 or max(map(abs, v.values())) > .5:
        raise ValueError('INITIAL_MAPPING_OUTSIDE_INSTALLED_ENVELOPE')
    return dict(qpos_rad=q, qvel_rad_s=v, unspecified='zero')


def freeze_first_study(path=SPEC_PATH):
    """Resolve bytes from the retained incumbent, never rounded reconstruction."""
    from tools.platform_store import Store
    from tools.parameter_catalog import study_input, effective_catalog
    if Path(path).exists(): return load_spec(path)
    store = Store(ROOT / 'runs/milestone4_autonomous_20261006')
    state = read(store.root / 'scheduler_state.json')
    candidate = state['selected']
    if candidate['execution_id'] != '91c3ba1b01d6499fb26df8f95409401b':
        raise ValueError('FROZEN_INCUMBENT_CHANGED')
    configuration = store.artifact(candidate['configuration'])
    source_facts = next(r['facts'] for r in state['records'] if r['facts']['execution_id'] == candidate['execution_id'])
    source_evaluation = store.artifact(source_facts['evaluation'])
    store.artifact(source_facts['report']['reference'])
    if not source_evaluation['task_success'] or not source_facts['sampled_settling']['passed']:
        raise ValueError('COMMON_START_MUST_HAVE_JOINT_HISTORICAL_PASS')
    template = study_input(configuration['effective'])
    catalog = effective_catalog(template)
    grants = {p: deepcopy(s.get('bounds', s.get('options'))) for group in ('parameters', 'control_parameters')
              for p, s in template['policy']['candidate_builder']['parameters']['data'][group].items()}
    cases = [dict(case_id='nominal', total_angle_rad={}, total_angle_rate_rad_s={})]
    for axis in ('near_z', 'far_y'):
        for sign, suffix in ((1, 'plus'), (-1, 'minus')):
            cases.append(dict(case_id=axis + '_' + suffix, total_angle_rad={axis: sign * .01},
                              total_angle_rate_rad_s={axis: sign * .02}))
    outcomes = []
    for record in state['records']:
        f = record['facts']
        outcomes.append({k: deepcopy(f.get(k)) for k in ('candidate', 'evaluation', 'report', 'terminal_error_m',
            'sampled_settling', 'force_bound_violation_n', 'solver_error_count', 'mean_complete_update_s')})
    structural = [p for p in grants if not p.startswith('control/')]
    controls = [p for p in grants if p.startswith('control/')]
    spec = dict(version=VERSION, question='Can design and control adaptation improve joint reach-and-hold robustness under predefined small initial-state variation around an already successful configuration?',
        source=dict(store_root=store.root.relative_to(ROOT).as_posix(), candidate=candidate,
            evaluation=source_facts['evaluation'], profile=source_facts['report']['reference'],
            historical_outcomes=outcomes, incumbent_not_promoted=True),
        starting_configuration=configuration, execution_template=template,
        parameter_pool_version=catalog['version'], parameter_grants=grants, cases=cases,
        repetitions=dict(count_per_case=2, seeds=[17,18], order='case order as listed, then repetition 1 seed 17, repetition 2 seed 18',
            cache='new', request_identity='Unique candidate/case/repetition request in a fresh session; no automatic replay of unknown reservations.',
            independence='Fresh MuJoCo model/data and controller workspace each execution. Initial profiles are deterministic; seeds label scheduled instances and do not create a stochastic population.',
            failure_rule='Every scheduled instance remains in denominator; invalid, missing, incomplete and failed results remain visible; no retries to obtain a pass.',
            inference_limit='Acceptance fraction is descriptive on this fixed five-case set, not a population success probability.'),
        initial_state_mapping=dict(version='normalized_arc_total_principal_angle@1.0.0', quantities=['total principal bend angle', 'total principal bend angular rate'],
            units=['rad','rad/s'], angle_range_rad=[-.01,.01], angle_rate_range_rad_s=[-.02,.02],
            support='initialize.family@1.0.0 + controller.gvs_nmpc@7.0.0 + backend.family_mujoco@1.1.0; named cell joints |q|<=.05 rad, |v|<=.5 rad/s.',
            equation='q[segment_cell_i_axis]=total_angle/N; qvel[segment_cell_i_axis]=total_angle_rate/N, for i=0..N-1.',
            comparable='Uniform principal-axis angle/rate profile versus normalized arc; segment integrated bend and angular rate; fixed orientations, station fractions, mesh and routing.',
            changes='Curvature theta/L and its rate, tip offset/velocity, mass and mechanical energy change with structure; equal tip perturbation or energy is not claimed.',
            conservatism='0.01 rad total bend is ~0.57 degree; each of 12 cell angles is 0.000833 rad. Velocity is nonzero, 0.001667 rad/s per cell, far below the technical maxima. Fixed before new outcomes.',
            reset='Fresh backend and controller; apply both named qpos and qvel once; no relaxation, easier regeneration or repeated initialization.',
            restore='Store restores sealed results and reservations, not live MuJoCo/controller state; full in-flight checkpoint resume is unsupported.'),
        acceptance=dict(protocol_id='offline_reach_hold_v1', version='1.0.0', real_time_required=False,
            authority='tools.research_tasks.assemble_acceptance; unchanged evaluate.reach plus sealed profile/motion.',
            terminal_position_limit_m=.01, holding_position_limit_m=.01, holding_speed_limit_m_s=.02,
            holding_window_s=.05, holding_interval_s=[.30,.35], expected_hold_samples=6,
            force_limits_n=[8.]*6, force_minimum_n=0., complete=True, validity='valid',
            requirements='Full execution; finite required signals; terminal reach and both holding components and applied force bounds. Missing evidence is unavailable, not physical infeasibility.',
            historical_protocol='All historical real-time failures retain original labels; new offline acceptance does not rescore sealed historical results.'),
        metrics=dict(primary='Number of jointly accepted fresh executions / ten scheduled case-repetition executions per finalist',
            secondary=['terminal_error_m','holding_max_error_m','holding_max_speed_m_s','force_bound_violation_n','measured_computation_s','mean_complete_update_s','backend_solves'],
            aggregation='Acceptance count first; retain per-case/per-repetition status and component values; max position/speed and total cost separately; no arbitrary weighted score.',
            reference='Fixed world tip target [0.29,0.035,0.19] m; post_step position and Jacobian-derived world translational speed in final closed interval.',
            actuator='Ideal nonnegative tendon tensions, same six inputs and 8 N limits; hardware actuator dynamics and force safety guarantees are outside scope.'),
        fixed_baseline=dict(version='fixed_coordinate_reach_hold@1.0.0', structural_variables=structural, control_variables=controls,
            method='Existing ParameterSpace and bounded coordinate_proposal kernels; discrete scenarios enumerated, never interpolated.',
            max_structures=4, control_evaluations_per_structure=2, max_finalists=2, normalized_step=.25,
            structure_policy='Start from exact incumbent; numeric coordinate +/- .25 of granted width in catalog order, skip unchanged/duplicates; enumerate remaining discrete options in declared order. Advance centre only on joint acceptance then componentwise dominance. Stop at four structures; unvisited dimensions remain untested.',
            control_policy='Each structure starts incumbent two control weights; one extra bounded coordinate proposal in catalog control order at nominal case/seed17. Advance only on joint acceptance then componentwise dominance; incomparable ties keep earlier proposal.',
            validation='After adaptation, select up to two nondominated nominal candidates in proposal order; schedule all five cases x two fresh independent repetitions. Adaptation nominal execution does not count as a robustness repetition.',
            final_selection='Maximize joint accepted count; then componentwise physical dominance; incomparable ties retain earliest candidate and report tradeoff.',
            stopping='Bounded allocations, no novel legal proposals, or all remaining proposed work cannot be completely reserved. Budget is ceiling. No success-based pruning of frozen scheduled repetitions.',
            failure='Preserve failures; unknown reservations not replayed; inadequate adaptation and incomplete runs are not structural infeasibility proofs.',
            mathematical_analysis=dict(enabled=False,reason='No additional local affine analysis is needed to validate this integrated path. Future uses must predeclare decision question and outcomes that change or retain selection.')),
        comparison_groups=dict(groups=['fixed_mathematical','one_shot_llm','feedback_llm'], launch_status='prepared_not_launched',
            common='Identical source/cases/acceptance/pool/budgets, including allocation for complete validation. No group receives newly connected variables mid-version.',
            one_shot='Freeze complete native model plan and executable branches before new outcomes. Optimizer-internal adaptation and predeclared branches allowed; no later model rewriting or branch addition.',
            feedback='Later model changes consume same cumulative ceilings; decisions retain predecessor evidence and exact state.',
            model_configuration=read(store.root/'freeze.json')['provider_configuration'],
            model_validation='Revised context live input cost/response quality pending; no paid call for compression.',
            stop_assessment='Legality and factual support are recorded separately from unproven optimality.'),
        formal_budget_per_group=dict(tool_calls=100,model_calls=8,backend_solves=28,worker_calls=0,wall_s=30000.),
        integration_validation=dict(budget=dict(tool_calls=12,model_calls=0,backend_solves=2,worker_calls=0,wall_s=2100.),
            historical_cost=dict(execution_id=candidate['execution_id'],measured_computation_s=source_facts['measured_computation_s'],reserve_per_backend_s=900.,evaluation_reserve_s=30.,profile_reserve_s=60.),
            normal_executions=1,repair_execution='Second slot only for a material versioned repair; failed first result retained.',
            case_id='near_z_plus',seed=17,repetition=1,changes={'design/near_section_scale':.96},
            scope='One generated changed structure with incumbent control seed, actual closed-loop control adaptation, simulation, joint evaluation, comparison and delivery. Not full robustness, research superiority or three-group evidence.'),
        uncertainty=['Frozen cases have not yet been evaluated as a complete suite.', 'Timed solver-plan selection can vary; observed historical exact replication does not prove repeatability.',
            'Local affine proxy does not establish nonlinear reach or global optimality.', 'Other passing geometry/control configurations show tradeoffs; incumbent retained deliberately.'],
        boundaries=dict(physical_design=structural,control_parameters=controls,
            numerical_settings='Exact incumbent recipe/basis/mesh/backend; solver max_cpu30s/max_iterations120 and feasible-return5/15s unchanged.',
            task_conditions='Frozen initializer cases, target, timing, gravity, frame and acceptance; excluded from candidate design.',
            unavailable='See generated catalog integration_backlog; dimension-changing edits require new engineering and shared study version.',
            old_milestones='M4 qualified closed, old M5 open and sealed negative successor; six protected old M5 slots untouched; no roadmap changes.'))
    validated = ResearchSpecification.model_validate(spec).model_dump(mode='json')
    atomic_json(path,dict(**validated,specification_identity=digest(validated)))
    return validated
