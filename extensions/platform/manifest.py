"""Application assembly for public default adapters; declaration imports only."""
from schemas.common import Contract
from schemas.platform import SessionInput, ModelResponse, ToolRequest
from schemas import platform_math as math_contracts
from schemas import platform_learning as learning_contracts
from schemas import platform_diagnostics as diagnostic_contracts
from tools.platform_registry import Extension


class Empty(Contract):
    pass


CONTRACTS = [('platform.empty', '1.0.0', Empty)]
from tools.investigation_contract import NativeInvestigationParameters
CONTRACTS += [('platform.' + name, '1.0.0', schema) for name, schema in [
    ('mathematical_model', math_contracts.MathematicalModel),
    ('model_use_assessment', math_contracts.ModelUseAssessment),
    ('model_agreement_evidence', math_contracts.ModelAgreementEvidence),
    ('dynamic_system', math_contracts.DynamicSystem),
    ('linearized_model', math_contracts.LinearizedModel),
    ('model_requirement', math_contracts.ModelRequirement),
    ('system_context', math_contracts.SystemContext),
    ('optimization_specification', math_contracts.OptimizationSpecification),
    ('optimization_problem', math_contracts.OptimizationProblem),
    ('optimization_result', math_contracts.OptimizationResult),
    ('rl_problem', learning_contracts.RLProblem),
    ('reward_definition', learning_contracts.RewardDefinition),
    ('rl_training_specification', learning_contracts.RLTrainingSpecification),
    ('training_job', learning_contracts.TrainingJob),
    ('training_metric', learning_contracts.TrainingMetric),
    ('policy_artifact', learning_contracts.PolicyArtifact),
    ('training_result', learning_contracts.TrainingResult),
    ('gate_result', diagnostic_contracts.GateResult),
    ('diagnostic_report', diagnostic_contracts.DiagnosticReport),
]]
EXTENSIONS = [
    Extension('deepseek', 'model_adapter', '7.0.0', NativeInvestigationParameters, ModelResponse,
        'tools.investigation_contract:BusinessFieldsAdapter', 'Native business fields from shared authoritative contracts; historical envelopes remain versioned',
        sources=('tools/investigation_contract.py','tools/platform_models.py','tools/model_transports/deepseek.py'),
        capabilities=dict(real_requests=True,text=True,images=False,timeout='network request deadline',cancellation='between requests')),
    Extension('candidate.controller', 'candidate_builder', '1.0.0', Empty, SessionInput,
        'tools.platform_candidates:apply_control', 'Apply existing typed controller parameters',
        sources=('tools/platform_candidates.py', 'schemas/platform_operations.py')),
    Extension('offline', 'model_adapter', '1.0.0', Empty, ModelResponse,
        'tools.platform_models:OfflineAdapter', 'Offline scripted compatibility fixture',
        sources=('tools/platform_models.py',), capabilities=dict(real_requests=False, text=True, images=False, timeout='synchronous local', cancellation='between decisions')),
    Extension('deepseek', 'model_adapter', '1.0.0', Empty, ModelResponse,
        'tools.platform_models:DeepSeekAdapter', 'Existing text/tool model service transport',
        sources=('tools/platform_models.py', 'tools/model_transports/deepseek.py'), capabilities=dict(real_requests=True, text=True, images=False, timeout='network request deadline', cancellation='between requests')),
    Extension('deepseek', 'model_adapter', '2.0.0', Empty, ModelResponse,
        'tools.platform_models:ReadableDeepSeekAdapter', 'Text/tool model service transport with frozen readable provider function names',
        sources=('tools/platform_models.py', 'tools/model_transports/deepseek.py'), capabilities=dict(real_requests=True, text=True, images=False, timeout='network request deadline', cancellation='between requests')),
    Extension('strategy.tool', 'strategy', '1.0.0', Empty, ToolRequest,
        'tools.platform_models:ToolStrategy', 'One typed tool request per decision', sources=('tools/platform_models.py',)),
]

from dataclasses import replace
EXTENSIONS = [replace(d, capabilities={**d.capabilities,
    'category': 'robot_design' if d.kind == 'candidate_builder' else 'platform_services',
    'role': 'adapter'}) for d in EXTENSIONS]

from tools.research_capabilities import CatalogRequest, CatalogResult
from tools.research_execution import CandidatePreparation, PreparedCandidate, ConfigurationAnalysis
from schemas.platform_analysis import AnalysisResult
from extensions.math_analysis.manifest import SOURCES as RESEARCH_MATH_SOURCES
for name,schema,output,binding,category in (
    ('research.prepare_candidate',CandidatePreparation,PreparedCandidate,'prepare_candidate_tool','research'),
    ('analysis.linearize_configuration',ConfigurationAnalysis,AnalysisResult,'linearize_configuration','analysis')):
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,output,'tools.research_execution:'+binding,
        'Shared owned candidate construction' if category=='research' else 'Existing candidate-local analysis on an owned prepared configuration; working-point equilibrium construction is scientific computation',
        sources=(*RESEARCH_MATH_SOURCES,'tools/research_execution.py','tools/platform_tools.py'),
        dependencies=('numpy','scipy','casadi'),capabilities=dict(category=category,role='public_tool',
            **(dict(task_families=['task.reach'],scientific_computation=True) if category=='analysis' else {}))))
EXTENSIONS.append(Extension('research.capabilities','tool','1.0.0',CatalogRequest,CatalogResult,
    'tools.research_capabilities:discover','Effective registry, parameter, compatibility, authority and evidence catalog',
    sources=('tools/research_capabilities.py','tools/parameter_catalog.py','tools/research_tasks.py'),
    capabilities=dict(category='research',role='public_tool')))
from tools.research_investigations import (InvestigationOrder,InvestigationResult,InvestigationStatus,PrincipalDisposition)
from schemas.platform_operations import ReadEvidence,EvidencePage
from tools.investigation_handoff import HistoricalHandoff
EXTENSIONS.append(Extension('research.investigation_handoff','tool','1.0.0',HistoricalHandoff,InvestigationResult,
    'tools.investigation_handoff:bind','Explicit stopped historical report reuse, preserving original execution and validation; never executes an investigator.',
    sources=('tools/investigation_handoff.py','tools/investigation_contract.py','tools/research_investigations.py'),
    capabilities=dict(category='diagnostics',role='public_tool')))
for name,schema,output,binding in (
    ('research.investigate',InvestigationOrder,InvestigationResult,'dispatch'),
    ('research.investigation_status',InvestigationStatus,InvestigationResult,'status'),
    ('research.investigation_disposition',PrincipalDisposition,InvestigationResult,'disposition'),
    ('research.investigation_read',ReadEvidence,EvidencePage,'read_source')):
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,output,
        'tools.research_investigations:'+binding,('Accept a durable bounded investigation submission; the actual model request includes a source metadata directory with original references, purpose, versions and paged evidence.read discovery. Collect through research.investigation_status. Discovery and body reads share node limits and separately checked permissions; no scientific execution.' if binding=='dispatch' else 'Collect bounded reports, inspect scoped evidence/directory pages, or record explicit principal claims and disposition. Current activity/deadline authority is checked; source checks do not prove semantic correctness.'),
        sources=('tools/research_investigations.py','tools/investigation_contract.py','tools/platform_workers.py','tools/platform_store.py','tools/context_assembly.py','tools/platform_tools.py','tools/platform_models.py','schemas/platform_operations.py'),
        capabilities=dict(category='diagnostics',role='public_tool',
            **(dict(delegated_execution=True,preflight='tools.research_investigations:dispatch_preflight',interactive_evidence=True,submission_only=True) if binding=='dispatch' else {}))))

from schemas import platform_handoff as handoff
EXTENSIONS.append(Extension('research.decide','tool','1.0.0',handoff.ResearchDecision,handoff.HandoffResult,
    'tools.research_scheduler:decide','Choose an evidence-bound control search, structure search, bounded diagnosis or voluntary stop.',
    sources=('schemas/platform_handoff.py','tools/research_scheduler.py','tools/platform_search.py'),
    capabilities=dict(category='research',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
from tools.diagnostic_improvement import ImprovementDecision
from schemas.diagnostic_revision import FinalDesignResponse
EXTENSIONS.append(Extension('deepseek','model_adapter','6.0.0',Empty,ModelResponse,
    'tools.diagnostic_reference_adapter:EvidenceDrivenAdapter','Recorded diagnostic checks, evidence-dependent revisions and future batch plans using the existing host.',
    sources=('tools/diagnostic_reference_adapter.py','tools/diagnostic_handoff.py','tools/platform_search.py'),
    capabilities=dict(real_requests=True,text=True,images=False,timeout='network request deadline',cancellation='between requests')))
from schemas.diagnostic_revision import CheckedRevision
for name,schema,binding in (
    ('design.assess_diagnosis',handoff.WorkflowDesignResponse,'tools.platform_handoff:respond_workflow'),
    ('diagnosis.propose_check',handoff.CheckProposal,'tools.diagnostic_handoff:propose_check'),
    ('diagnosis.revise_assessment',CheckedRevision,'tools.diagnostic_handoff:revise_assessment'),
    ('design.submit_search_plan',handoff.SearchBatchPlan,'tools.platform_search:submit_batch_plan'),
):
    CONTRACTS.append(('platform.'+name.replace('.','_'),'1.0.0',schema))
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,handoff.HandoffResult,binding,
        'Evidence-driven milestone handoff. No production execution or search batch authorization.',
        sources=('schemas/platform_handoff.py','schemas/diagnostic_revision.py','tools/diagnostic_handoff.py','tools/platform_search.py'),
        capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
EXTENSIONS.append(Extension('design.respond_diagnosis','tool','4.0.0',FinalDesignResponse,handoff.HandoffResult,
    'tools.diagnostic_handoff:final_decision','Final decision requiring the accepted revision and valid future batch plan.',
    sources=('tools/diagnostic_handoff.py','schemas/diagnostic_revision.py'),
    capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
EXTENSIONS.append(Extension('deepseek','model_adapter','5.0.0',Empty,ModelResponse,
    'tools.diagnostic_reference_adapter:ScopedReferenceAdapter','Scoped exact aliases and concise revisions over existing handoff contracts',
    sources=('tools/diagnostic_reference_adapter.py','tools/diagnostic_revision.py','schemas/diagnostic_revision.py','tools/diagnostic_native.py','tools/platform_models.py','tools/model_transports/deepseek.py'),
    capabilities=dict(real_requests=True,text=True,images=False,timeout='network request deadline',cancellation='between requests')))
EXTENSIONS.append(Extension('design.respond_diagnosis','tool','3.0.0',FinalDesignResponse,handoff.HandoffResult,
    'tools.platform_handoff:respond_workflow','Final recommendation disposition and explicit candidate selection bound to sealed feedback.',
    sources=('schemas/diagnostic_revision.py','tools/platform_handoff.py'),
    capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
EXTENSIONS.append(Extension('design.decide_improvement','tool','1.0.0',ImprovementDecision,handoff.HandoffResult,
    'tools.diagnostic_improvement:decide','Record separate improvement intent from an accepted diagnosis. No build or simulation executes through this decision.',
    sources=('tools/diagnostic_improvement.py','tools/platform_handoff.py'),
    capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
EXTENSIONS.append(Extension('deepseek','model_adapter','3.0.0',Empty,ModelResponse,
    'tools.diagnostic_native:FlatDiagnosticAdapter','Flat business arguments for the shared diagnostic workflow',
    sources=('tools/diagnostic_native.py','tools/platform_models.py','tools/model_transports/deepseek.py'),
    capabilities=dict(real_requests=True,text=True,images=False,timeout='network request deadline',cancellation='between requests')))
EXTENSIONS.append(Extension('deepseek','model_adapter','4.0.0',Empty,ModelResponse,
    'tools.diagnostic_native:BoundSavedStateAdapter','Flat diagnostic decisions with host-bound saved state/input for the model-selected update',
    sources=('tools/diagnostic_native.py','tools/platform_models.py','tools/model_transports/deepseek.py','extensions/tendon_family/diagnostic_evidence.py'),
    capabilities=dict(real_requests=True,text=True,images=False,timeout='network request deadline',cancellation='between requests')))
EXTENSIONS.append(Extension('design.respond_diagnosis','tool','2.0.0',handoff.WorkflowDesignResponse,handoff.HandoffResult,
    'tools.platform_handoff:respond_workflow','Record recommendation disposition and independent next workflow action. finish ends workflow; adoption alone executes nothing.',
    sources=('schemas/platform_handoff.py','tools/platform_handoff.py'),
    capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
for name, schema, function in (
    ('diagnosis.submit',handoff.InventoryDiagnosisSubmission,'submit'),
    ('diagnosis.check_request',handoff.ScopedDiagnosticCheckRequest,'check'),
):
    CONTRACTS.append(('platform.'+name.replace('.','_'),'2.0.0',schema))
    EXTENSIONS.append(Extension(name,'tool','2.0.0',schema,handoff.HandoffResult,
        'tools.platform_handoff:'+function,'Inventory-linked gaps and scientifically scoped saved-state questions; no causal certification.',
        sources=('schemas/platform_handoff.py','tools/platform_handoff.py','tools/diagnostic_inventory.py'),
        capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,preflight='tools.platform_handoff:preflight')))
for name, schema, function, description in (
    ('diagnosis.request',handoff.DiagnosisRequest,'request','Request a separate diagnostic context: distinguish evidence reading from an explicit saved_state_check numerical grant. Production changes and backend execution require separate authority.'),
    ('diagnosis.check_request',handoff.DiagnosticCheckRequest,'check','Submit a typed discriminating check; enabled feedback sessions yield to the fixed coordinator. Other sessions save an advisory request.'),
    ('diagnosis.submit',handoff.DiagnosisSubmission,'submit','Submit evidence-selected deterministic facts separately from attribution. Selector validation does not establish causality.'),
    ('design.respond_diagnosis',handoff.DesignResponse,'respond','Record adopt (accept named recommendation), defer (pending evidence), or reject. defer/reject requires next_action=stop; bounded_verification requires named adoption. stop declines recommendation verification, not independent diagnostic continuation. No backend comparison executes automatically.'),
    ('design.review_verification',handoff.DiagnosticReview,'review','Review actual verification against frozen gates and decide whether to retain the modification.'),
):
    CONTRACTS.append(('platform.'+name.replace('.','_'),'1.0.0',schema))
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,handoff.HandoffResult,
        'tools.platform_handoff:'+function,description,
        sources=('schemas/platform_handoff.py','tools/platform_handoff.py','schemas/platform_diagnostics.py','tools/platform_diagnosis_coordinator.py'),
        capabilities=dict(category='diagnostics',role='public_tool',route_visible=True,
            preflight='tools.platform_handoff:preflight')))
