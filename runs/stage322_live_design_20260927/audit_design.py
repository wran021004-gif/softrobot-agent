"""Read-only audit of a real Route design experiment; no new executions."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_host import Host
from tools.state_io import read,atomic_json,digest
from examples.gvs_nmpc_route_experiment import inspect


def lengths(robot):
    return {c['id']:c['length_m'] for c in robot['structure']['data']['components'] if c['kind']=='flexible_segment'}


def audit(root):
    host=Host(root,read(root/'workflow.json')['run_id']);store=host.store
    behavior=inspect(host);status=read(root/'route_status.json');inp=read(root/'input.json')
    choices=[a['decision'] for a in behavior['actions'] if a.get('decision') and a['decision'].get('tool_id')=='route.advance']
    trials=[]
    for node in status['route']['nodes']:
        if node['action']!='run' or node['status']!='completed':continue
        trial=store.artifact(node['result']);effective=store.artifact(trial['configuration'])['effective']
        report=store.artifact(trial['profile_report']['reference'])['detail']
        preparation=report['numerical_preparation'];evaluation=store.artifact(trial['evaluation'])
        result=store.artifact(trial['simulation']['output']);exports={};export_refs={}
        for event in store.events(trial['run_id']):
            if event['kind']=='simulation' and event['execution_id']==trial['simulation']['execution_id']:
                for ref in event['outputs']:
                    if ref.get('media_type')!='application/json':continue
                    data=store.artifact(ref)
                    if 'files' in data:
                        for f in data['files']:
                            if f['filename'] in ('resolved_physics.json','control_spec.json','robot_description.json','experiment_scene.json'):
                                exports[f['filename']]=json.loads(store.artifact(f['reference'],raw=True))
                                export_refs[f['filename']]=f['reference']
        physics=exports['resolved_physics.json'];plan=exports['control_spec.json']
        build=next(n for n in status['route']['nodes'] if n['node_id']==node['selection']['source_node'])
        selected=next((c for c in choices if c['arguments'].get('node_id')==build['node_id']),None)
        before=lengths(inp['robot']);after=lengths(effective['robot'])
        changed={k:dict(before_m=before[k],after_m=after[k],delta_mm=1000*(after[k]-before[k])) for k in before if before[k]!=after[k]}
        facts=dict(provider_selected_build=selected is not None,
            provider_changes_match_build=selected is not None and selected['arguments'].get('changes',{})==build['selection']['changes'],
            meaningful_length_change=any(abs(v['delta_mm'])>=1.-1e-9 for v in changed.values()),
            task_unchanged=effective['task']==inp['task'],controller_unchanged=effective['policy']['controller']==inp['policy']['controller'],
            design_matches_export=effective['robot']['structure']==exports['robot_description.json'],
            design_matches_compiled_physics=digest(effective['robot']['structure']['data'])==physics['design_identity'],
            candidate_predictor=plan['robot']==effective['robot'],
            preparation_matches_physics=preparation['physics_identity']==physics['identity']==result['data']['data']['physics_identity'],
            preparation_matches_design=preparation['execution_scope']['robot']['identity']==digest(effective['robot']),
            candidate_order=preparation['tendon_order']==[t['entity'] for t in physics['tendons']],
            candidate_limits=preparation['force_limits_n']==[t['force_limit_n'] for t in physics['tendons']],
            evaluation_matches_execution=evaluation['source_execution_id']==trial['simulation']['execution_id'],
            report_matches_execution=report['execution_id']==trial['simulation']['execution_id'] and report['evaluation']==trial['evaluation'])
        trials.append(dict(node_id=node['node_id'],candidate_id=trial['candidate_id'],run_id=trial['run_id'],
            changes=changed,provider_choice=selected,identity_checks=facts,configuration=trial['configuration'],
            execution_id=trial['simulation']['execution_id'],simulation=trial['simulation']['output'],evaluation=trial['evaluation'],
            report=trial['profile_report'],exports=export_refs,summary=trial['profile_report_summary'],
            design_execution_accepted=all(facts.values()) and report['valid_complete_execution']))
    final=behavior['final'] or {};review_path=root/'provider_interpretation_review.json'
    review=read(review_path) if review_path.exists() else None
    delivered=next((t for t in trials if t['candidate_id']==final.get('candidate_id')),None)
    delivered_to_context=bool(delivered and any(
        d.get(k) and d[k]['reference']==delivered['report']['reference']
        for d in behavior['context_deliveries'] for k in ('fresh_report','incumbent_report')))
    acceptance=dict(
        real_call_chain=bool(behavior['actual_provider_response_received'] and delivered and delivered['identity_checks']['provider_selected_build']
            and delivered_to_context and final.get('explicit_delivery') and review and review['correct_use_of_current_evidence']),
        changed_design_execution=any(t['design_execution_accepted'] for t in trials),
        delivered_original_reach=bool(delivered and delivered['summary']['valid_complete_execution'] and delivered['summary']['official_task_success']),
        current_report_delivered_to_provider=delivered_to_context,
        explicit_provider_delivery=bool(final.get('explicit_delivery')),
        provider_interpretation_review=review)
    out=dict(acceptance=acceptance,trials=trials,provider_choices=choices,
        counts={k:behavior[k] for k in ('real_model_requests','tool_calls','backend_executions')},
        project_usage=behavior['project_usage'],provider_responses=behavior['provider_responses'],
        frozen_input_identity=digest(inp),final=final)
    atomic_json(root/'design_audit.json',out)
    print(json.dumps(dict(acceptance=acceptance,counts=out['counts'],trials=len(trials)),indent=2))
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    audit(parser.parse_args().output.resolve())
