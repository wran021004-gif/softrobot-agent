"""Compact prepared M5 interpretation; no provider traffic in prepare mode."""
from pathlib import Path
import sys,json,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from examples.milestone_bound_successor import M5,operation
from examples.milestone45_checkpoint import reporting_payload

def packet():
    assessment=read(M5/'development_assessment.json');facts={}
    for name in ('original075','original15'):
        source='measure8_'+name;r=read(M5/(source+'.json'));receipt=read(M5/(source+'_receipt.json'))
        for row in r['rows']:
            metrics=dict(complete_update_s=row['full_software_input_to_command_s'],warm_preparation_s=row['receipt']['warm_preparation_s'],
                optimization_s=row['diagnostics']['solve_s'],validation_s=row['diagnostics']['validation_s'],
                selected_iteration=row['diagnostics']['selected_feasible_iteration'],objective_improvement=row['improvement'],
                scaled_violation=row['receipt']['optimization_constraint_violation'])
            for metric,value in metrics.items():
                key=source+'_'+row['temperature']+'_'+metric
                facts[key]=dict(value=value,unit='s' if metric.endswith('_s') else '1',execution_id=receipt['execution_id'],
                    candidate=name,temperature=row['temperature'],metric=metric,controller=r['controller'],
                    scientific_configuration_identity=digest(r['configuration']),source_artifact=receipt['output'],
                    source_path=str((M5/(source+'.json')).relative_to(ROOT)).replace('\\','/'))
    for metric in ('timed_vs_work_command_linf_n','work_warm_only_command_linf_n'):
        facts[metric]=dict(value=assessment['diagnosis'][metric],unit='N',source='development_assessment.json#/diagnosis/'+metric)
    old=read(ROOT/'evidence/milestone5_matched_20261006/operational_assessment.json')
    return dict(version='m5_compact_bound_interpretation@1.0.0',bound_facts=facts,
        supported_cause=assessment['diagnosis']['supported_cause'],confounders=assessment['diagnosis']['confounders'],
        failed_gates=assessment['failed_gates'],unrun_gates=assessment['unrun_gates'],
        local_admitted=False,formal_admitted=False,m5_closed=False,
        old_negative_evidence=dict(scope='Stopped v7, never validation of redesigned v8',accuracy_passed=old['accuracy_passed'],
            cases=[{k:r[k] for k in ('candidate','predicted_metrics','actual_metrics','metric_accuracy','false_feasible','false_infeasible')} for r in old['cases']],
            ranking=old['ranking'],economics={k:v for k,v in old['economics'].items() if k not in ('metered_pair_boundary','own_pending_model_request_cost')},
            realtime={k:old['realtime'][k] for k in ('deadline_s','demonstrated','forecast_deadline_misses','backend_deadline_misses')}),
        new_screening_decision={k:v for k,v in assessment['screening'].items() if k not in ('historical_reference',)},
        next_technical_decision=assessment['next_technical_decision'],
        protected_slots_preserved=6,charges=read(M5/'accounting.json')['actual'],
        provider_own_call_cost='Receipt added after response; all interpretation/correction cost included before final economics. No positive new counterfactual claim.',
        maximum_evidence_access='Source paths and immutable artifacts retained; no prospective-case access, no hidden tools or numerical work.')

def request(index,prepare_only=False):
    from tools.runtime_identity import require_softagent_runtime
    require_softagent_runtime()
    if index not in (0,1,2):raise ValueError('AT_MOST_TWO_CONSECUTIVE_CORRECTIONS')
    config=read(ROOT/'evidence/milestone4_autonomous_20261006/freeze.json')['provider_configuration'];p=packet()
    if index:
        p['correction']=read(M5/f'interpretation_review{index-1}.json');p['previous']=read(M5/f'interpretation{index-1}.json')
        if p['correction']['passed']:raise ValueError('NO_CORRECTION_AFTER_PASS')
    instructions='''Interpret this bounded controller-development result and recommend continuation, limited diagnostic use or stopping. Do not override a failed numerical/timing/economic gate. Distinguish termination intervention at one saved snapshot from unique causality; minute warm/state differences and original later divergence remain confounders. A deterministic diagnostic cap was not adopted as production merely for agreement. Experimental bounded controller changes scientific behavior; old v7 cannot validate it. All complete local intervals miss the unchanged realtime deadline, and feasible initialization lacks improvement. No matched pair, cheaper screening family or formal prospective case ran. Preserve negative development evidence and unused protected slots. Assess accuracy, component classification, qualified ranking and operational economics separately, with unrun gates honest. Do not invent amortization or savings. Include all material failures. Every quantitative claim must cite an exact bound_facts key using {{key}} in report/recommendation/unresolved. Renderer inserts exact referenced value and unit, never changes reference or interpretation. Avoid other literal numeric digits in prose. Submit report_interpretation once.'''
    payload=reporting_payload(config,p,instructions)
    atomic_json(M5/f'interpretation{index}_request.json',dict(provider_configuration=config,payload=payload))
    if prepare_only:return
    def call(ctx):
        from examples.gvs_nmpc_route_experiment import load_credential
        from tools.model_transports.deepseek import request_completion
        load_credential(Path(os.environ['SOFTAGENT_CONFIGURATION_PATH']))
        raw=request_completion(config,payload,os.environ['DEEPSEEK_API_KEY']);atomic_json(M5/f'interpretation{index}_raw.json',raw)
        choice=raw['choices'][0];calls=choice['message'].get('tool_calls',[])
        if choice.get('finish_reason')=='length' or len(calls)!=1 or calls[0]['function']['name']!='report_interpretation':raise ValueError('ONE_COMPLETE_INTERPRETATION_REQUIRED')
        return dict(model_authored=True,interpretation=json.loads(calls[0]['function']['arguments']),request_identity=digest(payload),raw_identity=digest(raw))
    operation(M5,f'interpretation{index}',call,reserve=config['timeout_s'],provider=True)

def render(index):
    from tools.bound_reporting import render_text
    def run(ctx):
        source=read(M5/f'interpretation{index}.json')['interpretation']
        sent=json.loads(read(M5/f'interpretation{index}_request.json')['payload']['messages'][1]['content'])
        result=render_text(source,sent['bound_facts']);atomic_json(M5/f'rendering{index}.json',result)
        body=result['rendered'];(M5/f'rendered_interpretation{index}.md').write_text(body['report']+'\n\n'+body['recommendation']+'\n\n'+'\n'.join(body['unresolved']),encoding='utf-8')
        return result
    return operation(M5,f'rendering{index}',run,reserve=30.)

def close(index):
    from examples.milestone_bound_successor import host,export
    from tools.bound_reporting import render_text
    def run(ctx):
        review=read(M5/f'interpretation_review{index}.json');raw=read(M5/f'interpretation{index}.json')['interpretation']
        assert review['model_report_identity']==digest(raw) and review['passed']
        assert all(c['passed'] for c in review['claim_checks'])
        sent=json.loads(read(M5/f'interpretation{index}_request.json')['payload']['messages'][1]['content'])
        assert render_text(raw,sent['bound_facts'])==read(M5/f'rendering{index}.json')
        assessment=read(M5/'development_assessment.json');assert not assessment['local_admitted'] and not assessment['formal_admitted']
        h=host(M5)
        with h.store.transaction() as db:
            session=h.store.session(h.run_id,db);session['state']['status']='stopped'
            h.store.update_state(db,h.run_id,session['state'],status='stopped')
        return dict(status='stopped_negative_development_with_reviewed_model_interpretation',milestone5_closed=False,
            formal_admitted=False,actual_backend_attempts=0,forecast_attempts=0,standalone_updates=9,
            controller_versions_used=['controller.gvs_nmpc@8.0.0'],screening_families_used=0,
            protected_pairs_used=0,protected_backend_slots_preserved=6,incumbent_unchanged=True,
            model_recommendation='Stop production advancement; limited saved-state diagnostic use only.',
            failed_gates=assessment['failed_gates'],unrun_gates=assessment['unrun_gates'],
            review_reference=f'interpretation_review{index}.json',report_reference=f'rendered_interpretation{index}.md',
            actual_savings_s=0.,new_campaign_not_authorized=True)
    result=operation(M5,'final_delivery',run,reserve=30.)
    atomic_json(M5/'checkpoint_seal.json',result);export(M5)

if __name__=='__main__':
    action=sys.argv[1];index=int(sys.argv[2])
    if action=='render':render(index)
    elif action=='close':close(index)
    else:request(index,prepare_only=action=='prepare')
