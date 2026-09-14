"""Trusted code registration. A declaration, a binding and a grant are distinct.

Extensions register here, never in the dispatcher. Imports are lazy and only
resolve repository-owned paths; tool arguments cannot select Python code.
"""
from dataclasses import dataclass
from importlib import import_module
from schemas.public_tools import PCCJacobian, SavedDiagnosis


@dataclass(frozen=True)
class ServiceTool:
    tool_id: str
    schema: type
    permission: str
    description: str
    binding: str | None
    adapter: str = 'context'
    version: str = '1.1.0'
    compatible_versions: tuple[str,...] = ('1.0.0',)
    cache: bool = False
    timeout_s: float = 30.
    isolation: str = 'process'
    sources: tuple[str, ...] = ()
    input_refs: tuple[str, ...] = ()
    resources: tuple[tuple[str, int], ...] = (('tool_calls',1),)
    output_contract: str = 'saved JSON detail + PublicResult@1.0'
    output_schema: type | None = None
    analysis_scope: str = 'not_assessed'
    process_tree: bool = False

    def __post_init__(self):
        if self.permission not in ('analysis','read_evidence','derived_artifacts'):
            raise ValueError('Services cannot grant numerical execution or model access')
        if self.adapter not in ('context','arguments','keywords') or self.isolation not in ('inline','process'):
            raise ValueError('Invalid executor adapter')
        if self.resources != (('tool_calls',1),) or self.timeout_s <= 0:
            raise ValueError('Unsupported service resource declaration; use numerical evaluator ledger')

    def resolve(self):
        if not self.binding:raise ValueError('IMPLEMENTATION_REQUIRED: '+self.tool_id)
        module, name = self.binding.split(':')
        return getattr(import_module(module),name)


def service_tools():
    from schemas.dynamic_workbench import Read, RenderVideo
    from schemas.framework import PCCCondition, RuleQuery, PCCConditionResult, SignalRuleResult
    from schemas.pcc_tolerance import PCCTolerance, PCCToleranceResult
    definitions = [
        ServiceTool('analysis.pcc_jacobian',PCCJacobian,'analysis',
            'Single section inextensible PCC tip/Jacobian, m and m/rad, base +x, yz bending; norm(bend)<=pi. Geometry only.',
            'tools.public_services:pcc_jacobian',adapter='arguments',isolation='inline',sources=('tools/pcc_math.py',)),
        ServiceTool('evidence.read_json',Read,'read_evidence','Read hash-verified saved JSON using bounded JSON Pointer pages.',
            'tools.public_services:read_json',input_refs=('evidence_ref',),isolation='inline',sources=('tools/dynamic_context.py',)),
        ServiceTool('diagnostics.saved_trajectory',SavedDiagnosis,'read_evidence','Legacy reach signal rules; saved physical time, no simulation or scoring.',
            'tools.public_services:saved_diagnosis',input_refs=('result_ref',),sources=('tools/trajectory_diagnosis.py',)),
        ServiceTool('visualization.render_simulation_video',RenderVideo,'derived_artifacts','Render saved trajectory; native cache and bounded encoder, zero solves.',
            'tools.simulation_video:_render_simulation_video',adapter='keywords',input_refs=('result_ref',),timeout_s=180.,process_tree=True,
            version='1.2.0',compatible_versions=('1.0.0','1.1.0'),
            sources=('tools/simulation_video.py',)),
        ServiceTool('analysis.pcc_condition',PCCCondition,'analysis','Singular values/rank of the local PCC tip Jacobian; geometric conditioning, no controllability or task claim.',
            'tools.math_extensions:pcc_condition',adapter='arguments',cache=True,isolation='process',
            compatible_versions=(),output_schema=PCCConditionResult,analysis_scope='geometry',
            sources=('tools/model_provider.py','tools/pcc_math.py','schemas/framework.py')),
        ServiceTool('diagnostics.signal_rule',RuleQuery,'read_evidence','Run a versioned saved-signal rule; distinguish missing, no event, inapplicable and failure.',
            'tools.diagnostic_rules:run_saved_rule',input_refs=('result_ref',),
            compatible_versions=(),output_schema=SignalRuleResult,analysis_scope='sampled_rules',
            sources=('tools/observation_contract.py','tools/rules/contact_presence.py','schemas/framework.py')),
        ServiceTool('analysis.pcc_tolerance',PCCTolerance,'analysis',
            'Propagate independent length/bend standard deviations to first-order tip covariance, principal error directions and ranked tolerance contributions. Geometric approximation, no task assessment.',
            'tools.pcc_tolerance:analyze',adapter='arguments',version='1.0.0',compatible_versions=(),
            cache=True,output_schema=PCCToleranceResult,analysis_scope='geometry',
            sources=('schemas/pcc_tolerance.py','tools/model_provider.py','tools/pcc_math.py')),
    ]
    result={d.tool_id:d for d in definitions}
    if len(result)!=len(definitions):raise ValueError('Duplicate tool ID')
    return result


def execute_binding(definition, root, registry, arguments):
    fn=definition.resolve()
    if definition.adapter=='arguments':return fn(arguments)
    if definition.adapter=='keywords':return fn(root,registry,**arguments)
    return fn(root,registry,arguments)
