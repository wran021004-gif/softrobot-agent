"""Aggregate E1 saved decisions/reviews; no provider or scientific calls."""
import json
import os
import statistics
import sys
from e1_replay import ROOT, DATA, PREVIOUS, TASKS, read, write, csv_rows, messages_for
from e1_review import LABELS, METRICS

sys.path.insert(0, str(PREVIOUS/'tokenizer_runtime'))
os.environ['TIKTOKEN_CACHE_DIR']=str(PREVIOUS/'tokenizer_cache')
import tiktoken
ENC=tiktoken.get_encoding('o200k_base')
PROXY='Existing local tiktoken 0.12.0 / o200k_base; visible message text only, not model-specific framing, hidden reasoning or billing.'


def text_tokens(messages):
    return sum(len(ENC.encode(x['content'])) for x in messages)


def measured_sum(requests, key):
    values=[(x.get('usage') or {}).get(key) for x in requests]
    return sum(values) if values and all(v is not None for v in values) else None


def finalize():
    records=[json.loads(line) for line in (DATA/'decision_results.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(records)==6 and len({x['session_id'] for x in records})==6
    assert all(x['status']=='completed' and 1<=x['provider_requests']<=4 for x in records)
    assert all(x[k]==0 for x in records for k in ['new_studies','new_reporter_requests','new_mathematical_solves','new_physics_runs','new_candidates'])
    new={(x['task_id'],x['condition']):x for x in records}
    factorial=[];costs=[];effects=[];unblinded=[]
    structured={}
    for task in TASKS:
        historical=read(ROOT/'historical_reference'/f'{task}.json')
        snapshot=read(ROOT/'snapshots'/f'{task}.json')
        review_doc=read(DATA/'blind_review'/task/'independent_model_review.json')
        ev={LABELS[task][x['label']]:x for x in review_doc['review']['evaluations']}
        structured[task]=dict(historical_reference=historical['source'],conditions={},comparison_rationale=review_doc['review']['comparative_rationale'])
        control=ev['K-S-']['scores']
        for condition in ['K+S+','K+S-','K-S+','K-S-']:
            evaluation=ev[condition];sc=evaluation['scores'];is_history=condition=='K+S+'
            messages,_=messages_for(snapshot,condition)
            initial_est=text_tokens(messages)
            if is_history:
                plan=historical['decision'];session_id=None;requests=[];provider_requests=0
                last_est=None;sum_input=None;sum_output=None;repair_count=0
                origin='historical_authored_Core_Plan_not_LLM'
                input_actual=output_actual=total_actual=None
                usage_status='not_applicable_no_historical_Main_provider_calls'
                context_scope='hypothetical_pre_read_KplusSplus_reconstruction_not_an_executed_Main_context'
                source_file=historical['source_file'];source_pointer='/0/formal_arguments'
                raw_source=source_file+'#'+source_pointer
            else:
                record=new[(task,condition)];plan=record['decision'];session_id=record['session_id']
                requests=record['requests'];provider_requests=record['provider_requests']
                folder=ROOT/'sessions'/session_id
                wires=[read(folder/f"request_{q['turn']}.json") for q in requests if q['http_status']==200]
                bodies=[read(folder/f"response_{q['turn']}.txt") for q in requests if q['http_status']==200]
                sum_input=sum(text_tokens(w['messages']) for w in wires)
                sum_output=sum(len(ENC.encode(b['choices'][0]['message']['content'])) for b in bodies)
                last_est=text_tokens(wires[-1]['messages']);repair_count=len(record['errors'])
                input_actual=measured_sum(requests,'prompt_tokens');output_actual=measured_sum(requests,'completion_tokens');total_actual=measured_sum(requests,'total_tokens')
                usage_status='provider_measured' if input_actual is not None and output_actual is not None else 'gateway_usage_missing_not_zero'
                context_scope='actual_sent_initial_messages_visible_text_estimate'
                origin='new_gpt-5.6-sol_decision_only_replay'
                source_file=(folder/'result.json').as_posix();source_pointer='/decision'
                raw_source=(folder/f"response_{requests[-1]['turn']}.txt").as_posix()+'#/choices/0/message/content'
            cost=dict(task_id=task,condition=condition,origin=origin,session_id=session_id,
                      model='not_applicable_no_historical_provider' if is_history else 'gpt-5.6-sol',
                      input_tokens_actual=input_actual,output_tokens_actual=output_actual,total_tokens_actual=total_actual,
                      actual_usage_status=usage_status,provider_requests=provider_requests,
                      initial_context_tokens_estimate=initial_est,context_estimate_scope=context_scope,
                      last_request_context_tokens_estimate=last_est,total_sent_input_text_tokens_estimate=sum_input,
                      total_response_output_text_tokens_estimate=sum_output,estimate_basis=PROXY,
                      schema_or_parse_repairs=repair_count,reporter_requests=0,
                      historical_provider_requests_source=historical['final_results_file'] if is_history else None,
                      request_source_directory=(ROOT/'sessions'/session_id).as_posix() if session_id else None)
            costs.append(cost)
            row=dict(task_id=task,condition=condition,knowledge_on='K+' in condition,skill_on='S+' in condition,
                     origin=origin,historical_reference_only=is_history,strict_four_cell_matching=False,
                     anonymous_label=evaluation['label'],**sc,
                     mean_of_four_scores=statistics.mean(sc.values()),
                     **{k+'_delta_vs_KminusSminus':sc[k]-control[k] for k in METRICS},
                     invalid_research_actions_count=len(evaluation['invalid_research_actions']),
                     invalid_action_scope='Final submitted decision, independent-model judgment; schema repairs are separately counted.',
                     schema_or_parse_repairs=repair_count,
                     invalid_research_actions=evaluation['invalid_research_actions'],
                     knowledge_observations=evaluation['knowledge_observations'],skill_observations=evaluation['skill_observations'],
                     experience_integration=evaluation['experience_integration'],
                     evidence_specific_rationale=evaluation['evidence_specific_rationale'],
                     action=plan['action'],selected_method=plan['decision']['selected_method'],
                     experience_entries_delivered=[x['key'] for x in snapshot['experience_records'] if ('K+' in condition if x['role']=='knowledge' else 'S+' in condition)],
                     provider_requests=provider_requests,input_tokens_actual=input_actual,output_tokens_actual=output_actual,
                     context_token_estimate=initial_est,context_estimate_scope=context_scope,
                     decision_source_file=source_file,decision_json_pointer=source_pointer,raw_decision_source=raw_source,
                     score_source=(DATA/'blind_review'/task/'independent_model_review.json').as_posix(),
                     judge_model=review_doc['model'],human_verification='pending',
                     interpretation_limit='Single new replay per nonhistorical cell. K+S+ is authored historical reference; comparisons involving it and interaction are descriptive, not identifiable causal effects.')
            factorial.append(row)
            unblinded.append(dict(task_id=task,condition=condition,anonymous_label=evaluation['label'],**sc,
                                 invalid_research_actions_count=len(evaluation['invalid_research_actions']),judge_model=review_doc['model']))
            structured[task]['conditions'][condition]=dict(scores=sc,decision_source=raw_source,decision=plan,
                evaluation=evaluation,cost=cost,historical_reference_only=is_history)
        for metric in METRICS:
            f={condition:ev[condition]['scores'][metric] for condition in ev}
            effects.append(dict(task_id=task,metric=metric,
                K_effect_at_Soff_new_replays=f['K+S-']-f['K-S-'],
                S_effect_at_Koff_new_replays=f['K-S+']-f['K-S-'],
                K_effect_at_Son_historical_reference=f['K+S+']-f['K-S+'],
                S_effect_at_Kon_historical_reference=f['K+S+']-f['K+S-'],
                interaction_with_historical_reference_descriptive=f['K+S+']-f['K+S-']-f['K-S+']+f['K-S-'],
                joint_minus_best_single_descriptive=f['K+S+']-max(f['K+S-'],f['K-S+']),
                causal_interaction_identifiable=False,
                limit='Two tasks; one new replay per cell, one model judge. Historical K+S+ is an authored surrogate Plan. No statistical synergy or robot-success effect can be inferred.'))
    csv_rows(DATA/'token_costs.csv',costs)
    csv_rows(DATA/'factorial_results.csv',factorial)
    csv_rows(DATA/'factorial_effects.csv',effects)
    csv_rows(ROOT/'scores_unblinded.csv',unblinded)
    write(DATA/'factorial_results.json',dict(metric_definition='Four separate independent-model blind scores 0–4; mean is a derived plotting convenience, not another model rating.',
        conditions=structured,effects=effects,
        matching_notes=read(ROOT/'matching_and_leakage_notes.json')))
    review_files=list((DATA/'blind_review').glob('*/independent_model_review.json'))+list((DATA/'blind_review').glob('*/review_round_1/independent_model_review.json'))
    accounting=dict(new_main_sessions=len(records),new_main_provider_requests=sum(x['provider_requests'] for x in records),
                    independent_model_review_requests=sum(read(p)['provider_requests'] for p in review_files),
                    final_used_review_requests=2,retained_superseded_review_requests=len(review_files)-2,historical_KplusSplus_reruns=0,
                    new_robot_executions=0,new_math_worker_executions=0,new_reporter_requests=0,new_knowledge_or_skill_entries=0,
                    token_proxy=PROXY,actual_Main_usage='See token_costs.csv; missing values are not zero.',
                    historical_reference='Authored Core Plans with zero historical Main provider calls; not a strictly matched LLM factorial cell.')
    write(ROOT/'execution_accounting.json',accounting)
    print(json.dumps(accounting,ensure_ascii=False),flush=True)
    for row in factorial:
        print(json.dumps({k:row[k] for k in ['task_id','condition',*METRICS,'invalid_research_actions_count','provider_requests']},ensure_ascii=False),flush=True)


if __name__=='__main__':finalize()
