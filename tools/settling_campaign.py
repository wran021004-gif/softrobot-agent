"""Stage 3.51 control-only grant and derived comparisons on the existing workflow."""
from copy import deepcopy
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.improvement_workflow import ImprovementWorkflow
from tools.diagnostic_improvement import actual_diff
from tools.diagnostic_workflow import INSTRUCTIONS
from tools.platform_diagnosis_coordinator import configure_role,feedback_content
from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
from extensions.tendon_family.contracts import GVSTrajectoryParameters
from extensions.tendon_family.gvs_profile import execution_scope

from tools.acceptance_definitions import RANKING


def control_grant(effective):
    result=deepcopy(plain(effective));policy=result['policy']
    if policy['controller']['extension_id']!='controller.gvs_nmpc' or policy['controller']['version'] not in ('3.0.0','4.0.0','6.0.0','7.0.0'):
        raise ValueError('COMPATIBLE_REACH_CONTROLLER_REQUIRED')
    # Freeze the actual replayed robot, including its existing semantic metadata.
    # No generic template or semantic re-expansion is needed for this campaign.
    space=policy['candidate_builder']['parameters']['data']
    space.update(parameters={},templates={},template_discretizations={},semantic_decisions={},semantic_source=None,
        model_parameters={},discretization_parameters={},control_parameters={
            path:dict(type='number',bounds=[0.,1.],unit='1',
                description=GVSTrajectoryParameters.model_fields[path.rsplit('/',1)[1]].description)
            for path in REACH_WEIGHT_PATHS})
    policy['editable']={path:[0.,1.] for path in REACH_WEIGHT_PATHS}
    result=plain(SessionInput.model_validate(result))
    if execution_scope(result)!=execution_scope(effective) or result['robot']!=plain(effective)['robot']:
        raise ValueError('GRANT_CHANGED_SCIENCE')
    return result


def campaign_metrics(facts):
    settling=facts['sampled_settling']
    if any(settling.get(k) is None for k in ('position_limit_m','speed_limit_m_s','window_s')):
        raise ValueError('CAMPAIGN_SOURCE_LIMITS_MISSING')
    # Official frozen reach result, never a second threshold/default evaluator.
    reach=facts['task_accepted']
    position=settling['max_error_m']<=settling['position_limit_m']
    speed=settling['max_speed_m_s']<=settling['speed_limit_m_s']
    valid=facts['evaluation_validity']=='valid' and facts['valid_complete_execution']
    return dict(source=dict(execution_id=facts['execution_id'],configuration=facts['configuration'],
            evaluation=facts['evaluation'],profile=facts['report']['reference'],simulation=facts['simulation']),
        coverage=dict(terminal='last execution sample',holding=f"all retained samples in final {settling['window_s']} s",continuous_time_guarantee=False),
        valid_complete_execution=valid,official_reach_task_success=facts['task_accepted'],
        terminal_error_m=facts['terminal_error_m'],holding_max_error_m=settling['max_error_m'],holding_max_speed_m_s=settling['max_speed_m_s'],
        terminal_reach_passed=reach,holding_position_passed=position,holding_speed_passed=speed,
        joint_reach_holding_passed=valid and reach and position and speed,
        mean_complete_update_s=facts['mean_complete_update_s'],deadline_misses=facts['deadline_misses'],
        control_updates=facts['control_updates'],control_period_s=facts['control_period_s'],
        real_time_demonstrated=facts['real_time_demonstrated'],solver_error_count=facts['solver_error_count'],
        force_bound_violation_n=facts['force_bound_violation_n'])


def compare_results(baseline,candidate):
    a,b=campaign_metrics(baseline),campaign_metrics(candidate)
    keys=RANKING['physical_metrics']+['mean_complete_update_s','deadline_misses']
    delta={k:b[k]-a[k] for k in keys};physical=[delta[k] for k in RANKING['physical_metrics']]
    eps=RANKING['tolerance']
    if not b['valid_complete_execution']:rank='invalid_or_incomplete'
    elif b['joint_reach_holding_passed'] and not a['joint_reach_holding_passed']:rank='joint_acceptance_gained'
    elif a['joint_reach_holding_passed'] and not b['joint_reach_holding_passed']:rank='joint_acceptance_lost'
    elif all(x<=eps for x in physical) and any(x < -eps for x in physical):rank='physical_pareto_improvement'
    elif all(x>=-eps for x in physical) and any(x>eps for x in physical):rank='physical_pareto_worsening'
    elif any(x>eps for x in physical) and any(x < -eps for x in physical):rank='physical_tradeoff'
    else:rank='physical_equivalent_within_tolerance'
    return dict(baseline=a,candidate=b,candidate_minus_baseline=delta,ranking_rule=RANKING,classification=rank,
        interpretation='Derived arithmetic from sealed complete evaluations/profile; source agreement does not certify scientific prose.')


class SettlingWorkflow(ImprovementWorkflow):
    numerical_limits=dict(local_solves=2,prediction_evaluations=0)
    capabilities=dict(complete_execution='At most one model-selected changed candidate, complete simulation, unchanged reach evaluation and sampled holding/profile feedback.',
        local_comparison='Optional one paired local comparison, two solves, <=300 charged seconds, at a saved baseline update with effective horizon 0.01 s; select one changed positive weight. Existing previous-input cold seed and integration retained. Unavailable/inconclusive screening does not prohibit a justified complete experiment.')
    instructions={**ImprovementWorkflow.instructions,
        'request':'Inspect common baseline inventory and summary. Formulate an open question about terminal reach, sampled holding position, sampled holding speed and computation. This diagnostic request covers reading/reporting only; a separate improvement decision can propose one bounded controller-weight experiment. No predetermined cause or winning weight.',
        'initial':INSTRUCTIONS['initial']+' Diagnose the new common baseline. Only terminal_tip_speed_weight and holding_tip_speed_weight may later change under the explicit control grant. A reasonable testable hypothesis is enough to justify bounded exploration; proof of the dominant cause is not required. No geometry or material changes.',
        'improvement':'Read the accepted diagnosis and supplied two-path control grant. Independently select whether to change one or both weights and their values: adopt with a nonempty effective delta, or defer/reject with empty changes for a specific evidence, feasibility, scope or budget reason. Missing proof of causality alone does not prohibit this bounded experiment. State a concrete hypothesis, why the weight is relevant, expected effects separately on reach, holding position, holding speed and computation, possible adverse effects, and observations that would weaken the hypothesis. Both bounds are [0,1]; newly positive values must be >=0.0001. All other scientific fields are fixed. Preserve terminal speed cost as a single terminal scaled squared-speed term, and holding speed cost as an integration-step-weighted sum at scheduled holding nodes; scale and scheduling remain unchanged. Do not compare raw scalar objectives across weights. Optionally request local_comparison for one selected positive changed parameter and a legal saved update (effective horizon 0.01 s). The pair is advisory, at most two solves and 300 charged seconds. Unavailable/inconclusive local screening permits the complete experiment. Do not select a developer-prescribed value or force adoption.',
        'revision':ImprovementWorkflow.instructions['revision']+' Use campaign_comparison for exact candidate-minus-baseline arithmetic and frozen classification. Distinguish official reach-only task_success from joint reach-plus-holding success. State how actual measurements strengthen or weaken the hypothesis and change the final decision. A lower speed with worse position is a trade-off.',
        'response_final':ImprovementWorkflow.instructions['response_final']+' This is control-only exploration, not robot-structure optimization. Apply the frozen campaign comparison and distinguish joint acceptance from successful workflow completion. No real-time, continuous-time or hardware claim.'}

    def comparison(self,baseline,result):
        if result and result.get('factual_result'):return compare_results(baseline,result['factual_result'])
        return None

    def screen_improvement(self,intent):
        request=intent['decision'].get('local_comparison')
        if not request:return dict(status='not_requested',local_solves=0)
        from extensions.tendon_family.diagnostic_evidence import BoundReader
        reader=BoundReader(self.store,self.binding);source=reader.resolve(self.execution)
        updates=reader.read_file(source,'controller_observations.json');i=request['update_id']
        path='control/recipe/'+request['parameter'];value=intent['decision']['changes'].get(path)
        recipe=source['configuration']['policy']['controller']['parameters']['data']['recipe']
        if value is None or value<.0001 or value==recipe[request['parameter']]:
            return dict(status='unavailable',reason='Local pair requires one adopted, effective, positive weight change.',local_solves=0)
        if not 1<=i<len(updates) or abs(updates[i].get('effective_horizon',recipe['horizon'])*source['configuration']['task']['timing']['control_period_s']-.01)>1e-9:
            return dict(status='unavailable',reason='Selected saved effective horizon does not match existing 0.01 s local capability.',local_solves=0)
        executor=self.hosts['executor']
        configure_role(executor,'executor','One optional saved-state pair; advisory only',
            phase_budget=dict(limit=dict(tool_calls=1,wall_s=300.),protect_project=dict(model_calls=7,tool_calls=7,wall_s=2200.)))
        receipt=executor.invoke(dict(request_id='optional-local-pair',tool_id='diagnosis.saved_state_check',tool_version='1.0.0',cache='new',
            arguments=dict(binding=self.binding,update_id=i,operation='local_comparison',changed_parameter=request['parameter'],changed_value=value,
                horizon_s=.01,integration_step_s=.002,max_wall_s=300.),reason='Model-selected optional paired local comparison'))
        return dict(status=receipt['execution_status'],receipt=receipt,
            result_content=feedback_content(self.store,receipt['output']) if receipt.get('output') else None,
            applicability='Existing saved projected state, previous applied input, effective horizon, cold seed and numerical method; not full-task improvement.')
