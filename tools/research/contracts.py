"""Native business fields for the bounded reach-and-hold research entry."""
from typing import Literal
from pydantic import Field, FiniteFloat, StrictInt, model_validator, model_serializer
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.platform_analysis import TaskAnalysisProtocol
from extensions.tendon_family.generated_serial import TopologyPatch
from extensions.tendon_family.family_space import GenerationRequest, GenerationRequestV2
from tools.research.capability import CapabilityComparison


class SegmentParameters(Contract):
    length_m: FiniteFloat = Field(gt=0)
    young_pa: FiniteFloat | None = Field(default=None,gt=0)
    material_scenario: Literal['baseline','compliant','stiff'] | None = None
    sections: dict[str,dict[str,FiniteFloat]]

    @model_validator(mode='after')
    def physical_authority(self):
        if (self.young_pa is None)==(self.material_scenario is None):
            raise ValueError('EXACTLY_ONE_CONTINUOUS_MODULUS_OR_NAMED_SCENARIO_REQUIRED')
        if any(v<=0 for station in self.sections.values() for v in station.values()):
            raise ValueError('POSITIVE_SECTION_DIMENSIONS_REQUIRED')
        return self


class Parameters(Contract):
    segments: dict[str,SegmentParameters]
    holding_tip_speed_weight: FiniteFloat = Field(ge=0)
    terminal_tip_speed_weight: FiniteFloat = Field(ge=0)


class TopologyParameters(Parameters):
    version: Literal['research_topology_parameters_v1']
    topology: TopologyPatch


class Search(Contract):
    variables: list[str] = Field(min_length=1)
    bounds: dict[str,tuple[FiniteFloat,FiniteFloat]]
    fixed: Parameters | TopologyParameters
    method: Literal['hierarchical_coordinate_v1_1'] = 'hierarchical_coordinate_v1_1'
    evaluation_mode: Literal['mathematical_proxy','backend_task'] = 'mathematical_proxy'
    objective: Literal['held_position_min_eigenvalue','target_equilibrium_residual','task_violation','joint_reach_hold','task_acceptance'] = Field(
        description='task_violation explicitly selects the authorized CONIC method on current task conditions; task_acceptance ranks independent physical acceptance. Other mathematical objectives remain diagnostics; joint_reach_hold is the legacy physical name.')
    operating_point: Literal['standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint']
    scoring_window_s: FiniteFloat = Field(gt=0)
    protocol: TaskAnalysisProtocol
    max_evaluations: int = Field(ge=1,strict=True)
    step: FiniteFloat = Field(default=.25,gt=0,le=.5)
    minimum_step: FiniteFloat = Field(default=.03125,gt=0,le=.5)

    @model_validator(mode='after')
    def domain(self):
        if len(set(self.variables))!=len(self.variables) or set(self.variables)!=set(self.bounds):
            raise ValueError('BOUNDS_MUST_MATCH_SELECTED_VARIABLES')
        from tools.research.design import parameter_value
        for key,(lo,hi) in self.bounds.items():
            if not lo<hi or not lo<=parameter_value(self.fixed.model_dump(),key)<=hi:
                raise ValueError('INITIAL_VALUE_OR_BOUNDS_INVALID: '+key)
        if (self.evaluation_mode=='backend_task')!=(self.objective in ('joint_reach_hold','task_acceptance')):
            raise ValueError('OBJECTIVE_EVALUATOR_MISMATCH')
        if self.evaluation_mode=='mathematical_proxy' and any('speed_weight' in k for k in self.variables):
            raise ValueError('CONTROL_VARIABLES_REQUIRE_BACKEND_TASK_EVALUATOR')
        if self.scoring_window_s not in self.protocol.windows_s:
            raise ValueError('EXPLICIT_DECLARED_SCORE_WINDOW_REQUIRED')
        return self


class FidelityLevel(Contract):
    cells_per_segment: int = Field(ge=1, le=32, strict=True)
    backend: str = Field(min_length=1)


class FidelityPolicy(Contract):
    version: Literal['numerical_fidelity_v1'] = 'numerical_fidelity_v1'
    screening: dict[str, FidelityLevel] = Field(min_length=1)
    final_evaluation: FidelityLevel
    require_exact_fidelity: Literal[True] = True
    alternative_runtimes: list[str] = Field(default_factory=list)
    runtime_preflight_limit: int = Field(default=2, ge=0, le=8, strict=True)


class FamilyMixedSearch(Contract):
    version: Literal['family_mixed_search_v1']
    family_space_identity: str = Field(min_length=1)
    method: Literal['bounded_mixed_coordinate_v1'] = 'bounded_mixed_coordinate_v1'
    variable_groups: list[Literal['segment_count','tendon_count','spans','lengths','materials','sections','routing','control']] = Field(min_length=1)
    segment_counts: list[int] = Field(min_length=1)
    tendon_counts: list[int] = Field(min_length=1)
    span_strategies: list[Literal['whole_chain','distributed_consecutive','distal']] = Field(default_factory=lambda:['whole_chain'])
    section_types: list[Literal['circle','tube','rectangle','ellipse']] = Field(default_factory=list)
    bounds: dict[str, tuple[FiniteFloat, FiniteFloat]] = Field(default_factory=dict)
    screening_fidelity: str = Field(min_length=1)
    objective: Literal['target_equilibrium_residual','held_position_min_eigenvalue','task_violation'] = Field(
        description='task_violation selects CONIC reoptimization for current task conditions and requires its frozen grant. max_evaluations includes model builds and all internal solves. Static residual and Gramian remain explicit diagnostics.')
    operating_point: Literal['standardized_initial_pretension','controller_start_input','target_equilibrium']
    max_proposals: int = Field(ge=1, le=128, strict=True)
    max_evaluations: int = Field(ge=1, le=128, strict=True)
    previous_candidate_ref: EvidenceRef | None = None
    evidence_used: list[EvidenceRef] = Field(default_factory=list)
    step: FiniteFloat = Field(default=.25, gt=0, le=.5)
    minimum_step: FiniteFloat = Field(default=.03125, gt=0, le=.5)
    stop_score: FiniteFloat | None = None

    @model_validator(mode='after')
    def selected_coordinates(self):
        for values in (self.variable_groups,self.segment_counts,self.tendon_counts,self.span_strategies,self.section_types):
            if len(values)!=len(set(values)):
                raise ValueError('UNIQUE_SEARCH_CHOICES_REQUIRED')
        if not self.span_strategies or any(type(v) is not int or v<1 for v in [*self.segment_counts,*self.tendon_counts]):
            raise ValueError('POSITIVE_TOPOLOGY_AND_SPAN_CHOICES_REQUIRED')
        if any(not lo<hi for lo,hi in self.bounds.values()):
            raise ValueError('ORDERED_SEARCH_BOUNDS_REQUIRED')
        if 'control' in self.variable_groups:
            raise ValueError('CONTROL_VARIABLES_REQUIRE_CONTROL_DEPENDENT_EVALUATOR; STATIC_AND_GRAMIAN_PROXIES_DO_NOT_SCORE_WEIGHTS')
        if len(self.section_types)>1 and 'sections' not in self.variable_groups:
            raise ValueError('SECTION_CHOICES_REQUIRE_SELECTED_SECTIONS_GROUP')
        if (self.objective=='target_equilibrium_residual')!=(self.operating_point=='target_equilibrium'):
            raise ValueError('OBJECTIVE_OPERATING_POINT_MISMATCH')
        return self


class StaticDesignSensitivity(Contract):
    version: Literal['sorosim_static_ift_v1'] = 'sorosim_static_ift_v1'
    variable: str
    step: FiniteFloat = Field(gt=0)
    minus_candidate: EvidenceRef
    plus_candidate: EvidenceRef


class OptimalCapabilitySensitivity(Contract):
    """Existing registered models, baseline first; no implicit model construction."""
    variable: str
    model_results: list[EvidenceRef] = Field(min_length=3,max_length=5)
    steps: list[FiniteFloat] = Field(min_length=1,max_length=2)

    @model_validator(mode='after')
    def positive_steps(self):
        if any(h<=0 for h in self.steps) or len(set(self.steps))!=len(self.steps):
            raise ValueError('DISTINCT_POSITIVE_SENSITIVITY_STEPS_REQUIRED')
        if len(self.model_results)!=1+2*len(self.steps):
            raise ValueError('BASELINE_AND_TWO_EXISTING_MODELS_PER_STEP_REQUIRED')
        return self


class LocalControlSearchSettings(Contract):
    version: Literal['local_control_search_v1','local_control_search_v2'] = 'local_control_search_v1'
    correction_window_s: tuple[FiniteFloat,FiniteFloat] | None = None
    safety_margin_fraction: FiniteFloat = Field(default=0.,ge=0,lt=.5,description='Optional v2 local model target margin inside every original norm bound; original physical acceptance is unchanged. Zero preserves boundary-seeking legacy behavior.')
    method: Literal['response','pattern'] = 'response'
    knots_s: list[FiniteFloat] = Field(default_factory=lambda:[0.,.18,.30],min_length=2,max_length=4)
    coefficient_limit_n: FiniteFloat = Field(default=2.,gt=0)
    difference_step_n: FiniteFloat = Field(default=.01,gt=0)
    initial_radius_n: FiniteFloat = Field(default=.1,gt=0)
    minimum_radius_n: FiniteFloat = Field(default=.0001,gt=0)
    evaluation_requests: int = Field(default=24,ge=1,le=1000,strict=True)
    iterations: int = Field(default=16,ge=1,le=100,strict=True)
    active_coefficients: list[StrictInt] | None = Field(default=None,min_length=1,description='Unique flat knot-major coefficient indices; omitted selects all. Each inactive offset remains exactly zero.')

    @model_serializer(mode='wrap')
    def preserve_legacy_settings(self,handler):
        result=handler(self)
        for key in ('version','correction_window_s','safety_margin_fraction','active_coefficients'):
            if key not in self.model_fields_set:result.pop(key,None)
        return result

    @model_validator(mode='after')
    def domain(self):
        if self.active_coefficients is not None and (self.version!='local_control_search_v2'
                or any(type(i) is not int or i<0 for i in self.active_coefficients)
                or len(set(self.active_coefficients))!=len(self.active_coefficients)):
            raise ValueError('UNIQUE_NONNEGATIVE_V2_ACTIVE_COEFFICIENTS_REQUIRED')
        if self.version=='local_control_search_v1' and self.safety_margin_fraction!=0:
            raise ValueError('SAFETY_MARGIN_REQUIRES_V2_SEARCH')
        if self.method=='pattern' and self.safety_margin_fraction!=0:
            raise ValueError('SAFETY_MARGIN_REQUIRES_RESPONSE_METHOD')
        if self.knots_s[0]<0 or (self.version=='local_control_search_v1' and self.knots_s[0]!=0) or any(b<=a for a,b in zip(self.knots_s,self.knots_s[1:])):
            raise ValueError('ORDERED_KNOTS_STARTING_AT_ZERO_REQUIRED' if self.version=='local_control_search_v1' else 'ORDERED_NONNEGATIVE_KNOTS_REQUIRED')
        if self.correction_window_s is not None:
            a,b=self.correction_window_s
            if self.version!='local_control_search_v2' or not 0<=a<=self.knots_s[0]<self.knots_s[-1]<=b or a>=b:
                raise ValueError('ORDERED_V2_CORRECTION_WINDOW_REQUIRED')
        if not self.minimum_radius_n<=self.initial_radius_n<=self.coefficient_limit_n or self.difference_step_n>self.coefficient_limit_n:
            raise ValueError('STEPS_MUST_FIT_COEFFICIENT_DOMAIN')
        return self



class NativeControlOptimization(Contract):
    source: EvidenceRef
    settings: LocalControlSearchSettings

    @model_validator(mode="after")
    def bounded_native_window(self):
        if self.settings.version!="local_control_search_v2" or self.settings.correction_window_s is None:
            raise ValueError("NATIVE_OPTIMIZATION_REQUIRES_V2_AND_EXPLICIT_WINDOW")
        return self


class NativeStructureResponse(Contract):
    variable: str
    candidates: list[EvidenceRef] = Field(min_length=1,max_length=2)


class NativeAnalysisOptions(Contract):
    tensions_n: list[FiniteFloat] | None = None
    horizon_s: FiniteFloat = Field(default=.01,gt=0,le=.05)
    difference_step_n: FiniteFloat = Field(default=.02,gt=0,le=.5)
    correction_radius_n: FiniteFloat = Field(default=0.,ge=0,le=.5)


class AnalysisRequest(Contract):
    candidate: EvidenceRef
    operation: Literal['equilibrium','linearization','controllability','endpoint','braking','instantaneous_braking_v1','trajectory_feasibility','task_capability','input_sensitivity','design_sensitivity','native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','mujoco_direct_control_v1']
    model_source: Literal['controller','gvs','sorosim','mujoco'] = 'controller'
    native: NativeAnalysisOptions = Field(default_factory=NativeAnalysisOptions)
    structure_response: NativeStructureResponse | None = None
    control_optimization: NativeControlOptimization | None = None
    operating_point: Literal['standardized_initial_pretension','controller_start_input','target_equilibrium','halfway_waypoint','saved_state','fixed_input_equilibrium'] = 'halfway_waypoint'
    design_sensitivity: StaticDesignSensitivity | None = None
    capability_comparison: CapabilityComparison | None = None
    capability_method: Literal['sampled-affine-conic-minimax-v1'] | None = None
    optimal_sensitivity: OptimalCapabilitySensitivity | None = None
    saved_state: EvidenceRef | None = None
    execution: EvidenceRef | None = None
    update_id: int | None = Field(default=None,ge=0,strict=True)
    protocol: TaskAnalysisProtocol
    scoring_window_s: FiniteFloat | None = Field(default=None,gt=0)

    @model_validator(mode='after')
    def exact_state(self):
        native_operation=self.operation in ('native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','mujoco_direct_control_v1')
        if (self.model_source=='mujoco')!=native_operation:
            raise ValueError('MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE')
        if (self.operation=='mujoco_direct_control_v1')!=(self.control_optimization is not None):
            raise ValueError('NATIVE_CONTROL_OPTIMIZATION_REQUIRES_SOURCE_AND_SETTINGS')
        if self.control_optimization and self.native!=NativeAnalysisOptions():
            raise ValueError('NATIVE_CONTROL_USES_SEQUENCE_AND_SEARCH_SETTINGS')
        if native_operation and self.operating_point not in ('saved_state','standardized_initial_pretension'):
            raise ValueError('NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION')
        if not native_operation and self.native!=NativeAnalysisOptions():
            raise ValueError('NATIVE_OPTIONS_REQUIRE_NATIVE_METHOD')
        if (self.operation=='fixed_input_structure_v1')!=(self.structure_response is not None):
            raise ValueError('STRUCTURE_RESPONSE_REQUIRES_REGISTERED_COMPARISON_CANDIDATES')
        if self.capability_method is not None and (self.operation!='task_capability' or self.capability_comparison is not None):
            raise ValueError('CONIC_REQUIRES_TASK_CAPABILITY_WITHOUT_LEGACY_COMPARISON')
        if self.optimal_sensitivity is not None and (self.capability_method is None or self.operating_point not in ('controller_start_input','standardized_initial_pretension')):
            raise ValueError('OPTIMAL_SENSITIVITY_REQUIRES_CONIC_AND_INITIAL_OPERATING_POINT')
        if self.capability_comparison is not None and self.operation != "task_capability":
            raise ValueError("CAPABILITY_COMPARISON_REQUIRES_TASK_CAPABILITY")
        if self.operation=='equilibrium' and self.operating_point!='target_equilibrium':
            raise ValueError('EQUILIBRIUM_REQUIRES_TARGET_POINT: operating_point=target_equilibrium')
        if self.operation=='instantaneous_braking_v1' and self.operating_point!='saved_state':
            raise ValueError('INSTANTANEOUS_BRAKING_REQUIRES_EXACT_SAVED_STATE')
        if (self.operation=='design_sensitivity')!=(self.design_sensitivity is not None):
            raise ValueError('DESIGN_SENSITIVITY_REQUIRES_PAIRED_CANDIDATES')
        if self.operation in ('input_sensitivity','design_sensitivity') and self.operating_point!='fixed_input_equilibrium':
            raise ValueError('STATIC_SENSITIVITY_REQUIRES_FIXED_INPUT_EQUILIBRIUM')
        if self.operation in ('linearization','controllability') and self.scoring_window_s is None:
            raise ValueError('EXPLICIT_SCORE_WINDOW_REQUIRED')
        if self.scoring_window_s is not None and self.scoring_window_s not in self.protocol.windows_s:
            raise ValueError('SCORING_WINDOW_NOT_IN_PROTOCOL')
        if (self.execution is None)!=(self.update_id is None):
            raise ValueError('EXECUTION_REQUIRES_UPDATE_ID')
        sources=int(self.saved_state is not None)+int(self.execution is not None)
        if sources>1 or (self.operating_point=='saved_state')!=(sources==1):
            raise ValueError('SAVED_POINT_REQUIRES_UNAMBIGUOUS_STATE_SOURCE')
        return self

    @model_serializer(mode='wrap')
    def unchanged_legacy_serialization(self,handler):
        value=handler(self)
        if self.design_sensitivity is None:value.pop('design_sensitivity',None)
        if self.capability_comparison is None:value.pop('capability_comparison',None)
        for key in ('capability_method','optimal_sensitivity'):
            if getattr(self,key) is None:value.pop(key,None)
        if self.model_source=='controller':value.pop('model_source',None)
        if self.model_source!='mujoco':value.pop('native',None)
        for key in ('structure_response','control_optimization'):
            if getattr(self,key) is None:value.pop(key,None)
        return value


class LocalDiagnostic(Contract):
    execution: EvidenceRef
    update_id: int = Field(ge=0,strict=True)
    repetitions: int = Field(default=2,ge=1,le=2,strict=True)
    mode: Literal['research_policy', 'research_current'] = 'research_policy'


class MechanicsRequest(Contract):
    candidate: EvidenceRef
    substeps: int = Field(default=1,ge=1,le=4,strict=True)
    initialization: Literal['constant_0_2','ramp_0_2_to_0_4','saved_candidate_trajectory','saved_candidate_controls'] = 'constant_0_2'
    warm_source: EvidenceRef | None = None
    objective_mode: Literal['task_gap','task_gap_with_effort','maximum_original_violation','minimum_signed_task_excess','task_capability','task_feasible_effort'] = 'task_gap'
    check_only: bool = False
    diagnostic_source: EvidenceRef | None = None
    diagnostic_mode: Literal['regularity','lagrangian'] | None = None
    max_iterations: int = Field(default=120,ge=1,le=120,strict=True)
    position_weight: FiniteFloat = Field(default=1,gt=0)
    speed_weight: FiniteFloat = Field(default=1,gt=0)
    secondary_coefficient: FiniteFloat = Field(default=.001,ge=0)

    @model_validator(mode='after')
    def warm_binding(self):
        if (self.diagnostic_source is None)!=(self.diagnostic_mode is None) or (self.diagnostic_mode and not self.check_only):
            raise ValueError('RAW_POINT_DIAGNOSTIC_REQUIRES_CHECK_ONLY_AND_EXACT_SOURCE')
        if (self.warm_source is not None)!=(self.initialization in ('saved_candidate_trajectory','saved_candidate_controls')):
            raise ValueError('SAVED_CANDIDATE_INITIALIZATION_REQUIRES_WARM_SOURCE')
        return self


class CrossReplayRequest(Contract):
    candidate: EvidenceRef
    source: EvidenceRef


class PhysicalReplayRequest(Contract):
    candidate: EvidenceRef
    source: EvidenceRef


class ControlCorrectionSettings(Contract):
    knots_s: list[FiniteFloat] = Field(min_length=2,max_length=4)
    coefficient_limit_n: FiniteFloat = Field(gt=0)
    model_difference_step_n: FiniteFloat = Field(gt=0)
    simulation_difference_step_n: FiniteFloat = Field(gt=0)
    guided_step_limit_n: FiniteFloat = Field(gt=0)
    optimizer_iterations: int = Field(ge=1,le=32,strict=True)

    @model_validator(mode='after')
    def ordered_domain(self):
        if self.knots_s[0]!=0 or any(b<=a for a,b in zip(self.knots_s,self.knots_s[1:])):
            raise ValueError('ORDERED_CORRECTION_KNOTS_STARTING_AT_ZERO_REQUIRED')
        if max(self.guided_step_limit_n,self.simulation_difference_step_n,self.model_difference_step_n)>self.coefficient_limit_n:
            raise ValueError('CORRECTION_STEPS_MUST_FIT_COEFFICIENT_DOMAIN')
        return self




class EvidenceSummary(Contract):
    version: Literal['evidence_policy_v1'] = 'evidence_policy_v1'
    claim_kind: Literal['MODEL_WITNESS','MODEL_EXCLUSION','NUMERICAL_DIAGNOSTIC',
        'PHYSICAL_OBSERVATION','EMPIRICAL_COMPARISON','STATISTICAL_EVIDENCE','UNVERIFIED_HYPOTHESIS']
    verification_status: str
    model_identity: str | None = None
    candidate_identity: dict | str | None = None
    design_identity: str | None = None
    task_identity: str | None = None
    operating_point: dict = Field(default_factory=dict)
    covered_samples: dict = Field(default_factory=dict)
    assumptions: dict = Field(default_factory=dict)
    supported_inferences: list[str] = Field(default_factory=list)
    unsupported_inferences: list[str] = Field(default_factory=list)
    evidence_reference: EvidenceRef | None = None
    numerical_evidence_pointer: str = ''
    prospective_guarantee: Literal[False] = False
    unresolved: list[str] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)


class FixedSequenceRefinement(Contract):
    candidate: EvidenceRef
    source: EvidenceRef
    substeps: Literal[2,4,8,16,32,64]


class MatchedStateProbe(Contract):
    candidate: EvidenceRef
    source: EvidenceRef
    physical_source: EvidenceRef
    indices: tuple[Literal[0],Literal[15],Literal[29]] = (0,15,29)
    resolutions: tuple[Literal[4],Literal[8]] = (4,8)


class NMPCPredictionDiagnostic(Contract):
    candidate: EvidenceRef
    source: EvidenceRef
    update_index: Literal[0,19,29]
    substeps: Literal[1,4,8,16,32]


class ControlSearchStart(Contract):
    candidate: EvidenceRef
    source: EvidenceRef
    adaptation_from: EvidenceRef | None = None


class ControlSearchRequest(ControlSearchStart):
    settings: LocalControlSearchSettings
    additional_starts: list[ControlSearchStart] = Field(default_factory=list,max_length=7)

    @model_serializer(mode='wrap')
    def preserve_single_start(self,handler):
        result=handler(self)
        if not self.additional_starts:result.pop('additional_starts',None)
        return result


class ControlSeedRequest(Contract):
    candidate: EvidenceRef
    source: EvidenceRef | None = Field(default=None,description='Explicit schedule or a registered complete NMPC execution result. NMPC uses measured applied SI interval tensions; parent must equal candidate, without channel_map. New open-loop schedule inherits no acceptance.')
    parent: EvidenceRef | None = None
    channel_map: dict[str, str] | None = None
    tensions_n: list[list[FiniteFloat]] | None = None
    method: Literal['baseline','mathematical_response','physical_response','capability_sequence'] = 'baseline'
    response_evidence: EvidenceRef | None = None
    channels: list[str] | None = Field(default=None,min_length=1)
    difference_step_n: FiniteFloat = Field(default=.02,gt=0)
    trust_radius_n: FiniteFloat = Field(default=.2,gt=0)
    regularization: FiniteFloat = Field(default=.000001,gt=0)
    evaluation_requests: int = Field(default=8,ge=1,le=64,strict=True)

    @model_serializer(mode='wrap')
    def preserve_baseline(self,handler):
        result=handler(self)
        for key in ('method','response_evidence','channels','difference_step_n','trust_radius_n','regularization','evaluation_requests'):
            if key not in self.model_fields_set:result.pop(key,None)
        return result

    @model_validator(mode='after')
    def paired_source(self):
        if (self.method in ('mathematical_response','capability_sequence'))!=(self.response_evidence is not None):
            raise ValueError('MATHEMATICAL_SEED_REQUIRES_REGISTERED_RESPONSE_EVIDENCE')
        if self.method=='capability_sequence' and (self.source is not None or self.parent is not None
                or self.channel_map is not None or self.tensions_n is not None or self.channels is not None):
            raise ValueError('CAPABILITY_SEQUENCE_REQUIRES_ONLY_CANDIDATE_AND_RESULT_REFERENCE')
        if self.channels is not None and len(set(self.channels))!=len(self.channels):
            raise ValueError('UNIQUE_SEED_CHANNELS_REQUIRED')
        if (self.source is None) != (self.parent is None):
            raise ValueError('CONTROL_SOURCE_REQUIRES_EXACT_PARENT')
        if self.channel_map is not None and self.source is None:
            raise ValueError('CHANNEL_MAP_REQUIRES_SOURCE')
        if self.tensions_n is not None and self.source is not None:
            raise ValueError('CHOOSE_EXPLICIT_INPUTS_OR_SOURCE')
        return self


class ResearchDecision(Contract):
    version: Literal['research_decision_v1'] = 'research_decision_v1'
    hypothesis_id: str = Field(min_length=1)
    claimed_inference: str = Field(default='empirical_search',min_length=1,description='Use empirical_search for a proposed falsifiable experiment, including testing a mathematical prediction in physics. This is not a proven inference. Any stronger claim must match supported_inferences of registered supporting_evidence with the required identity and scope.')
    research_intent: Literal['DIAGNOSE','MATHEMATICAL_ANALYSIS','CONTROL_SEARCH','DESIGN_MODIFICATION','NMPC_EXECUTION','RL_TRAINING','PHYSICAL_VALIDATION','SELECT','STOP']
    selected_method: str = Field(min_length=1)
    selected_variables: list[str] = Field(default_factory=list)
    selected_candidate: EvidenceRef | None = None
    requested_budget: int = Field(default=0,ge=0,strict=True,description='Physical request cap for control search; otherwise declared operation units')


# Payload ownership belongs to Plan; the provider schema projects this contract.
PLAN_PAYLOADS = dict(initialize_control='control_seed',generate='generation',propose='parameters',
    execute='candidate',search='search',control_search='control_search',mechanics='mechanics',
    replay='mechanics_source',cross_replay='cross_replay',physical_replay='physical_replay',
    refine='refinement',matched_state='matched_state',nmpc_prediction_diagnostic='nmpc_prediction_diagnostic',
    diagnose='diagnostic',confirm='selected_execution',select='selected_execution')
PLAN_OPTIONAL_PAYLOADS = dict(propose=('mechanics_source',),diagnose=('diagnostic',))


class Plan(Contract):
    action: Literal['initialize_control', 'generate', 'propose', 'execute', 'search', 'control_search', 'mechanics', 'replay', 'cross_replay', 'physical_replay', 'refine', 'matched_state', 'nmpc_prediction_diagnostic', 'diagnose', 'confirm', 'select', 'stop']
    control_seed: ControlSeedRequest | None = None
    decision: ResearchDecision | None = None
    control_search: ControlSearchRequest | None = None
    next_step: Literal['adjust_training','revise_design','diagnose','stop'] | None = None
    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    expected_observation: str = Field(min_length=1)
    weakening_observation: str = Field(min_length=1)
    fixed_conditions: str = Field(min_length=1)
    stopping_condition: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    parameters: Parameters | TopologyParameters | None = None
    generation: GenerationRequest | GenerationRequestV2 | None = None
    search: Search | FamilyMixedSearch | None = None
    candidate: EvidenceRef | None = None
    selected_execution: EvidenceRef | None = Field(default=None, description='Exact immutable publicly read passing NMPC, fixed-tension physical_replay or independent RL evaluation; freezes the complete solution')
    revise_selection: bool = Field(default=False, description='Explicitly replace a failed selection with a scientifically changed, freshly passing development solution; retain all confirmation records and cumulative costs')
    diagnostic: LocalDiagnostic | None = None
    mechanics: MechanicsRequest | None = None
    cross_replay: CrossReplayRequest | None = None
    physical_replay: PhysicalReplayRequest | None = None
    refinement: FixedSequenceRefinement | None = None
    matched_state: MatchedStateProbe | None = None
    nmpc_prediction_diagnostic: NMPCPredictionDiagnostic | None = None
    mechanics_source: EvidenceRef | None = None
    experience_disposition: dict[str, Literal['adopted', 'rejected', 'context_only']] = Field(default_factory=dict)

    @model_serializer(mode='wrap')
    def preserve_legacy_plan(self, handler):
        result=handler(self)
        if self.generation is None:
            result.pop('generation',None)
        for key in ('decision','control_search','control_seed'):
            if getattr(self,key) is None:result.pop(key,None)
        return result

    @model_validator(mode='after')
    def required(self):
        if self.revise_selection and self.action not in ('confirm','select'):
            raise ValueError('REVISE_SELECTION_REQUIRES_CONFIRM_ACTION')
        active = PLAN_PAYLOADS.get(self.action)
        for field in set(PLAN_PAYLOADS.values())-{'mechanics_source','diagnostic'}:
            if (getattr(self, field) is not None) != (field == active):
                raise ValueError('ACTION_REQUIRES_ONLY_' + str(active))
        if self.action=='replay' and self.mechanics_source is None:
            raise ValueError('REPLAY_REQUIRES_OWNED_MECHANICS_RESULT')
        if self.mechanics_source is not None and self.action not in ('propose','replay'):
            raise ValueError('MECHANICS_SOURCE_REQUIRES_PROPOSE_OR_REPLAY; SEARCH_HAS_ITS_OWN_SOURCE')
        if self.diagnostic is not None and self.action!='diagnose':
            raise ValueError('LOCAL_DIAGNOSTIC_REQUIRES_DIAGNOSE_ACTION')
        return self


class ExperienceQuery(Contract):
    operation: Literal['search', 'read'] = 'search'
    key: str | None = Field(default=None,min_length=1)
    entry_id: str | None = Field(default=None,min_length=1)
    revision: str | None = Field(default=None,min_length=1)
    task: str | None = None
    structure: str | None = None
    failure_type: str | None = None
    version: str | None = None


class EvidenceQuery(Contract):
    reference: EvidenceRef
    pointer: str = ''
    view: Literal['full','summary','fields','range','capabilities','mathematical_capabilities','working_set'] = 'full'
    fields: list[str] = Field(default_factory=list, max_length=32)
    start: int = Field(default=0, ge=0, strict=True)
    count: int = Field(default=20, ge=1, le=100, strict=True)


class PPOOverrides(Contract):
    """Sparse changes. Effective numeric defaults belong to control.json."""
    learning_rate: FiniteFloat | dict | None = None
    n_steps: int | None = Field(default=None,ge=2,strict=True)
    batch_size: int | None = Field(default=None,ge=2,strict=True)
    n_epochs: int | None = Field(default=None,ge=1,strict=True)
    gamma: FiniteFloat | None = Field(default=None,ge=0,le=1)
    gae_lambda: FiniteFloat | None = Field(default=None,ge=0,le=1)
    clip_range: FiniteFloat | dict | None = None
    clip_range_vf: FiniteFloat | dict | None = None
    normalize_advantage: bool | None = None
    ent_coef: FiniteFloat | None = Field(default=None,ge=0)
    vf_coef: FiniteFloat | None = Field(default=None,ge=0)
    max_grad_norm: FiniteFloat | None = Field(default=None,gt=0)
    target_kl: FiniteFloat | None = Field(default=None,gt=0)
    policy_kwargs: dict | None = None


class RewardConfiguration(Contract):
    """Finite registered reward terms; weights never change task acceptance."""
    position: FiniteFloat = Field(default=1.,ge=0)
    holding_speed: FiniteFloat = Field(default=1.,ge=0)
    smoothness: FiniteFloat = Field(default=.001,ge=0)
    failure_penalty: FiniteFloat = Field(default=-10000.,le=0)
    path_error: FiniteFloat = Field(default=0.,ge=0)
    progress: FiniteFloat = Field(default=0.,ge=0)
    regression: FiniteFloat = Field(default=0.,ge=0)


class RewardOverrides(Contract):
    position: FiniteFloat | None = Field(default=None,ge=0)
    holding_speed: FiniteFloat | None = Field(default=None,ge=0)
    smoothness: FiniteFloat | None = Field(default=None,ge=0)
    failure_penalty: FiniteFloat | None = Field(default=None,le=0)
    path_error: FiniteFloat | None = Field(default=None,ge=0)
    progress: FiniteFloat | None = Field(default=None,ge=0)
    regression: FiniteFloat | None = Field(default=None,ge=0)


class RLAllocation(Contract):
    actions: int = Field(ge=1,strict=True)
    active_seconds: FiniteFloat | None = Field(default=None,gt=0)


class RLReference(Contract):
    path: str
    sha256: str
    candidate_identity: str
    task_identity: str
    tendon_order: list[str]
    control_period_s: FiniteFloat = Field(gt=0)


class RLRequest(Contract):
    operation: Literal['start','continue','status','stop','resume','evaluate','diagnose']
    candidate: EvidenceRef | None = None
    task: EvidenceRef | None = None
    mode: Literal['direct','residual'] | None = None
    reference: RLReference | None = None
    training_overrides: PPOOverrides = Field(default_factory=PPOOverrides)
    reward_overrides: RewardOverrides = Field(default_factory=RewardOverrides)
    allocation: RLAllocation | None = None
    rationale: str = Field(min_length=1)
    run_id: str | None = None
    checkpoint: str | None = None
    failure: str | None = None
    replay: bool = False
    force: bool = False
    initial_tension_n: FiniteFloat | None = Field(default=None,ge=0,description='Initialization only, direct RL: set the initial policy mean to this physical tension; continuation/resume retain parent weights')

    @model_validator(mode='after')
    def operation_contract(self):
        if self.operation=='start':
            if self.candidate is None or self.run_id:
                raise ValueError('START_REQUIRES_CANDIDATE; OMITTED_MODE_AND_ALLOCATION_INHERIT_CONFIGURED_DEFAULTS')
            if any(k in self.model_fields_set and getattr(self,k) is None for k in ('mode','allocation')):
                raise ValueError('EXPLICIT_NULL_CANNOT_CLEAR_MODE_OR_STEP_ALLOCATION')
            if (self.mode=='residual')!=(self.reference is not None):
                raise ValueError('RESIDUAL_REQUIRES_REFERENCE_DIRECT_REQUIRES_NONE')
        elif self.operation=='continue':
            if not self.run_id or not self.checkpoint or not self.allocation:
                raise ValueError('CONTINUE_REQUIRES_EXACT_PARENT_RUN_CHECKPOINT_AND_ADDITIONAL_STEPS')
            if self.candidate or self.task or self.mode or self.reference:
                raise ValueError('CONTINUATION_RETAINS_CANDIDATE_TASK_AND_CONTROL_MEANINGS')
        else:
            if not self.run_id:
                raise ValueError('RECORDED_RUN_ID_REQUIRED')
            if self.candidate or self.task or self.mode or self.reference or self.allocation or self.training_overrides.model_fields_set or self.reward_overrides.model_fields_set:
                raise ValueError('SUBSEQUENT_OPERATIONS_RETAIN_FROZEN_CONFIGURATION')
        if self.checkpoint and self.operation not in ('evaluate','continue'):
            raise ValueError('CHECKPOINT_ONLY_FOR_EVALUATE_OR_CONTINUE')
        if (self.failure or self.replay) and self.operation!='diagnose':
            raise ValueError('FAILURE_REPLAY_ONLY_FOR_DIAGNOSE')
        if self.force and self.operation!='stop':
            raise ValueError('FORCE_ONLY_FOR_OWNED_PROCESS_STOP')
        if 'initial_tension_n' in self.model_fields_set and self.operation!='start':
            raise ValueError('POLICY_MEAN_INITIALIZATION_REQUIRES_NEW_START')
        return self
