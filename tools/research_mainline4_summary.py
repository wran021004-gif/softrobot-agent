"""Factual delivery projection; model reasoning is preserved verbatim upstream."""
import argparse
import json
import platform
import time
from importlib.metadata import version
from collections import Counter
from pathlib import Path
from tools import research_mainline4 as study
from tools.state_io import atomic_json,read
from tools.platform_store import plain


def summarize(w):
    with w.store.connect(True) as db:calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
    receipts=[json.loads(r['receipt']) for r in calls if r['receipt']]
    provider=[]
    for e in w.store.events(w.host.run_id):
        if e['kind']=='model_raw_response' and e['outputs']:
            response=w.store.artifact(e['outputs'][0]);raw=response.get('raw',{})
            provider.append(dict(request_id=e['request_id'],response=e['outputs'][0],usage=raw.get('usage'),
                finish_reason=(raw.get('choices') or [{}])[0].get('finish_reason')))
    totals={k:sum((r['usage'] or {}).get(k,0) for r in provider) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    totals['reasoning_tokens']=sum((r['usage'] or {}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in provider)
    searches=[];mathematical_influence=[];feedback_consumed=[]
    for row in w.rounds:
        decision=row['decision']['decision'];plan=decision.get('plan')
        if plan and row.get('result'):
            result=w.store.artifact(row['result'])
            evaluated=[p for p in result['proposals'] if p.get('actual_changes') and not p.get('reused') and
                any(c.get('execution') and c.get('identity')==p['identity'] for c in result['candidates'])]
            searches.append(dict(decision=row['accepted_decision'],method=plan['method'],variables=plan['variables'],
                result=row['result'],evaluated_changed_proposals=evaluated,status=result['status'],
                enumeration=plan['method']=='search.family_explicit@1.0.0'))
        text=json.dumps({k:decision.get(k) for k in ('reasoning','interpretations','plan')},ensure_ascii=False)
        if any(word in text.lower() for word in ('affine','lineariz','endpoint','local model','local-model','gramian')):
            mathematical_influence.append(dict(decision=row['accepted_decision'],model_text=decision,
                review_required='A model-authored reference to mathematical results; see material review for its decision influence and scope.'))
        for previous in w.rounds[:row['index']]:
            ref=previous.get('feedback_result')
            if ref and any(s['reference']==ref for s in row['decision']['evidence_selectors']):
                feedback_consumed.append(dict(decision=row['accepted_decision'],feedback=ref))
    selected=next((r for r in w.records if r['facts']['candidate']==w.selected),None)
    numerical=any(s['method']=='search.family_coordinate@1.0.0' and s['evaluated_changed_proposals'] for s in searches)
    attempts=[r for r in receipts if r['tool_id']=='simulation.run' and r['charged']['backend_solves']]
    new_records=[r for r in w.records if r['source_store']==str(w.directory)]
    internal_updates=sum(w.store.artifact(r['receipts']['profile']['output'])['detail']['updates'] for r in new_records)
    for v in w.verification:
        execution=w.store.artifact(v['result']);internal_updates+=w.store.artifact(execution['profile_report']['reference'])['detail']['updates']
    from tools.study_history import execution_chronology
    chronology=execution_chronology(w.store,[*w.records,*[dict(facts=w.store.artifact(v['result'])['factual_result']) for v in w.verification]])
    outputs=[]
    for r in new_records:
        cfg=w.store.artifact(r['facts']['configuration'])['effective'];recipe=cfg['policy']['controller']['parameters']['data']['recipe']
        outputs.append(dict(candidate=r['facts']['candidate'],template=cfg['robot']['structure']['data'].get('metadata',{}).get('finite_template','T0'),
            acceptance=r['acceptance'],metrics=r['acceptance']['metrics'],controller=cfg['policy']['controller']['version'],
            applied_values={k:recipe[k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')}))
    failures=[dict(request_id=r['request_id'],tool_id=r['tool_id'],status=r['execution_status'])
        for r in receipts if r['execution_status']!='completed']
    development_attempts=sum(json.loads(c['charged'])['backend_solves'] for c in calls if 'verification' not in c['run_id'])
    return dict(activity=w.spec['activity_id'],status=w.status,stop_reason=w.stop_reason,
        dimensions=dict(research_workflow_completed=w.status=='model_stopped',
            mathematical_evidence_used_in_decisions=bool(mathematical_influence),numerical_search_actually_executed=numerical,
            new_feedback_consumed_by_principal=bool(feedback_consumed),
            physical_joint_acceptance_achieved=any(r['acceptance']['accepted'] for r in new_records) or any(v['acceptance']['accepted'] for v in w.verification),
            selected_joint_acceptance=selected['acceptance']['accepted'] if selected else None,
            fresh_repeat_verification_executed=bool(w.verification),
            improvement_demonstrated='See material review; no automatic promotion or scalar-score improvement claim'),
        entry='T1',source=w.source,latest_tested=chronology['latest_complete_result'],latest_development_candidate=w.latest,
        execution_chronology=chronology,retained_reference=w.baseline['candidate'],selected_candidate=w.selected,
        selected_acceptance=selected['acceptance'] if selected else None,verification=w.verification,
        final_model_decision=w.rounds[-1]['decision']['decision'] if w.rounds else None,
        outcomes=outputs,searches=searches,mathematical_decision_evidence=mathematical_influence,
        feedback_consumption=feedback_consumed,original_model_decisions=[r['accepted_decision'] for r in w.rounds],
        resources=dict(usage=w.store.remaining(),provider_requests=w.store.remaining()['used']['model_calls'],
            provider_reported_tokens=totals,responses=provider,provider_monetary_cost=None,
            development_backend_attempts=development_attempts,
            verification_backend_attempts=len(attempts)-development_attempts,
            technical_replacement_attempts=0,
            overall_backend_attempts=len(attempts),public_mathematical_calls=sum(r['tool_id'].startswith('analysis.') for r in receipts),
            search_method_invocations=len(searches),completed_search_batches=sum(s['status']=='completed' for s in searches),
            failed_or_rejected_calls=failures,failure_counts_by_tool=dict(Counter(r['tool_id'] for r in failures)),
            internal_nmpc_updates=internal_updates,elapsed_from_original_start_s=time.time()-w.spec['started_unix'],
            budget_note='The cumulative ledger includes initial engineering, provider and workflow charges. The original elapsed deadline also covers intervening repair/review/delivery time; no clock or grant was reset.',
            engineering_interventions=w.spec['engineering_interventions']),
        limitations=['One nominal condition, sampled holding criteria, ideal tension only.',
            'Historical T0 executed controller9; current preparation/execution uses controller10.',
            'Cross-template force capacity, guide/routing and initialization differences prevent isolated attribution.',
            'Affine local witnesses do not certify nonlinear feasibility; curvature projection residuals are rad/m.',
            'No real-time, robustness, variance, statistical superiority or global incumbent promotion claim.'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=study.RUN);args=p.parse_args()
    w=study.restore(args.directory);study.export(w)
    result=summarize(w)
    review=study.OUT/'material_review.json'
    if review.exists():
        checked=read(review);result['dimensions'].update(checked['reviewed_dimensions'])
        result['material_review']='material_review.json';result['mainline5_question']=checked['next_question_in_report']
        result['original_model_mainline5_question']=checked['model_authored_mainline5_question']
    atomic_json(study.OUT/'result_summary.json',result)
    atomic_json(study.OUT/'environment.json',dict(python=platform.python_version(),
        packages={name:version(name) for name in ('numpy','scipy','casadi','mujoco','pydantic')},environment_changed=False))
    print(json.dumps(dict(status=result['status'],dimensions=result['dimensions'],resources={k:v for k,v in result['resources'].items() if k in ('provider_requests','provider_reported_tokens','overall_backend_attempts','public_mathematical_calls','internal_nmpc_updates')})))


if __name__=='__main__':main()
