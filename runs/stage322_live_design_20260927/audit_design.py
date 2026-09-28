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


def delivery_acceptance(trials, final, behavior, review, finish):
    """Labels are descriptive; immutable owner/execution/evidence identify delivery."""
    matches=[t for t in trials if t['run_id']==final.get('run_id') and
        t['execution_id']==final.get('simulation',{}).get('execution_id')]
    # A sealed execution can appear in several Route nodes after a replay.
    unique={(t['run_id'],t['execution_id'],digest(t['configuration']),
        digest(t['evaluation']),digest(t['report'])):t for t in matches}
    delivered=next(iter(unique.values())) if len(unique)==1 else None
    issues=[]
    if final and delivered is None:issues.append('DELIVERED_EXECUTION_NOT_UNAMBIGUOUS')
    if delivered and any((final.get('configuration')!=delivered['configuration'],
        final.get('evaluation_ref')!=delivered['evaluation'],
        final.get('profile_report')!=delivered['report'],
        final.get('simulation',{}).get('output')!=delivered['simulation'])):
        issues.append('DELIVERED_EVIDENCE_MISMATCH');delivered=None
    binding=None
    if delivered and finish:
        binding=dict(run_id=delivered['run_id'],execution_id=delivered['execution_id'],
            configuration=delivered['configuration'],evaluation=delivered['evaluation'],
            report=delivered['report'],provider_request_id=finish['request_id'],
            provider_response=finish['response'],conclusion_digest=digest(final['stop_reason']))
    in_context=bool(binding and any(d['request_id']==binding['provider_request_id'] and any(
        d.get(k)==delivered['report'] for k in ('fresh_report','incumbent_report'))
        for d in behavior['context_deliveries']))
    interpreted=bool(binding and isinstance(review,dict) and review.get('binding')==binding and
        review.get('correct_use_of_current_evidence') is True and review.get('findings'))
    explicit=bool(binding and final.get('explicit_delivery'))
    if final.get('explicit_delivery') and not finish:issues.append('PROVIDER_FINISH_RESPONSE_NOT_UNAMBIGUOUS')
    chain=False
    # Meaningful change is evaluated separately from identity/call-chain correctness.
    if delivered:
        identity={k:v for k,v in delivered['identity_checks'].items() if k!='meaningful_length_change'}
        chain=bool(behavior['actual_provider_response_received'] and all(identity.values()) and in_context and explicit)
    reach=bool(delivered and delivered['summary']['valid_complete_execution'] and delivered['summary']['official_task_success'])
    acceptance=dict(real_call_chain=chain,
        changed_design_execution=any(t['design_execution_accepted'] for t in trials),
        delivered_original_reach=reach,
        delivered_changed_design_reach=bool(delivered and delivered['design_execution_accepted'] and reach),
        current_report_delivered_to_provider=in_context,explicit_provider_delivery=explicit,
        provider_interpretation_accepted=interpreted,
        final_delivery_accepted=bool(chain and interpreted and reach and delivered['design_execution_accepted']),
        provider_interpretation_review=review)
    return acceptance,binding,issues


def audit(root):
    host=Host(root,read(root/'workflow.json')['run_id']);store=host.store
    behavior=inspect(host);status=read(root/'route_status.json');inp=read(root/'input.json')
    real_requests={r['request_id'] for r in behavior['provider_responses']}
    choices=[a['decision'] for a in behavior['actions'] if a['request_id'] in real_requests and a.get('decision') and a['decision'].get('tool_id')=='route.advance']
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
        built=store.artifact(build['result']);built_input=store.artifact(built['configuration'])
        selected=next((c for c in choices if c['arguments'].get('node_id')==build['node_id']),None)
        before=lengths(inp['robot']);after=lengths(effective['robot'])
        changed={k:dict(before_m=before[k],after_m=after[k],delta_mm=1000*(after[k]-before[k])) for k in before if before[k]!=after[k]}
        facts=dict(provider_selected_build=selected is not None,
            provider_changes_match_build=selected is not None and selected['arguments'].get('changes',{})==build['selection']['changes'],
            meaningful_length_change=any(abs(v['delta_mm'])>=1.-1e-9 for v in changed.values()),
            authorized_lengths=all(inp['policy']['editable']['components/'+k+'/length_m'][0]<=v<=inp['policy']['editable']['components/'+k+'/length_m'][1] for k,v in after.items()),
            build_matches_execution=trial['build_configuration']==built['configuration'] and built_input['run_id']==trial['run_id'] and built_input['robot']==effective['robot'],
            task_unchanged=effective['task']==inp['task'],controller_unchanged=effective['policy']['controller']==inp['policy']['controller'],
            design_matches_export=effective['robot']['structure']==exports['robot_description.json'],
            design_matches_compiled_physics=digest(effective['robot']['structure']['data'])==physics['design_identity'],
            candidate_predictor=plan['robot']==effective['robot'],
            preparation_matches_physics=preparation['physics_identity']==physics['identity']==result['data']['data']['physics_identity'],
            preparation_matches_design=preparation['execution_scope']['robot']['identity']==digest(effective['robot']),
            candidate_order=preparation['tendon_order']==[t['entity'] for t in physics['tendons']],
            candidate_limits=preparation['force_limits_n']==[t['force_limit_n'] for t in physics['tendons']],
            evaluation_matches_execution=evaluation['source_execution_id']==trial['simulation']['execution_id'],
            report_matches_execution=report['execution_id']==trial['simulation']['execution_id'] and report['evaluation']==trial['evaluation'] and trial['profile_report']['owner_run_id']==trial['run_id'] and trial['profile_report']['execution_id']==trial['simulation']['execution_id'])
        trials.append(dict(node_id=node['node_id'],candidate_id=trial['candidate_id'],run_id=trial['run_id'],
            changes=changed,provider_choice=selected,identity_checks=facts,configuration=trial['configuration'],
            execution_id=trial['simulation']['execution_id'],simulation=trial['simulation']['output'],evaluation=trial['evaluation'],
            report=trial['profile_report'],exports=export_refs,summary=trial['profile_report_summary'],
            design_execution_accepted=all(facts.values()) and report['valid_complete_execution']))
    final=behavior['final'] or {};review_path=root/'provider_interpretation_review.json'
    review=read(review_path) if review_path.exists() else None
    finishes=[]
    for action in behavior['actions']:
        decision=action.get('decision') or {};args=decision.get('arguments',{})
        if decision.get('tool_id')!='route.advance' or args.get('action')!='finish':continue
        nodes=[n for n in status['route']['nodes'] if n['node_id']==args.get('node_id') and n['status']=='completed' and n['action']=='finish']
        responses=[r for r in behavior['provider_responses'] if r['request_id']==action['request_id']]
        if len(nodes)==1 and len(responses)==1 and store.artifact(nodes[0]['result'])==final and args.get('reason')==final.get('stop_reason'):
            finishes.append(dict(request_id=action['request_id'],response=responses[0]['reference']))
    acceptance,binding,issues=delivery_acceptance(trials,final,behavior,review,finishes[0] if len(finishes)==1 else None)
    out=dict(acceptance=acceptance,trials=trials,provider_choices=choices,
        counts={k:behavior[k] for k in ('real_model_requests','tool_calls','backend_executions')},
        project_usage=behavior['project_usage'],provider_responses=behavior['provider_responses'],
        frozen_input_identity=digest(inp),final=final,delivery_binding=binding,identity_inconsistencies=issues)
    atomic_json(root/'design_audit.json',out)
    print(json.dumps(dict(acceptance=acceptance,counts=out['counts'],trials=len(trials)),indent=2))
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    audit(parser.parse_args().output.resolve())
