"""Update the complete eight-LLM factorial materials from saved decisions/reviews."""
import csv
import json
import os
import statistics
import sys
from pathlib import Path

RUN=Path(__file__).resolve().parent;ROOT=RUN.parent;sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from e1_replay import DATA,TASKS,PREVIOUS,read,write,csv_rows,messages_for,httpx
from complete_review import LABELS,METRICS
sys.path.insert(0,str(PREVIOUS/'tokenizer_runtime'));os.environ['TIKTOKEN_CACHE_DIR']=str(PREVIOUS/'tokenizer_cache')
import tiktoken
ENC=tiktoken.get_encoding('o200k_base')
ORDER=['K-S-','K+S-','K-S+','K+S+']
PROXY='estimated_generic_proxy: same local tiktoken 0.12.0/o200k_base on complete serialized HTTP request JSON, not verified model-matched framing, hidden reasoning or billing.'


def total_actual(requests,key):
    values=[(r.get('usage') or {}).get(key) for r in requests]
    return sum(values) if values and all(v is not None for v in values) else None


def finalize():
    lines=(DATA/'decision_results.jsonl').read_text('utf-8').splitlines()
    prior_lines=(RUN/'prior_figure_data/decision_results.jsonl').read_text('utf-8').splitlines()
    assert lines[:6]==prior_lines and len(lines)==8
    records=[json.loads(s) for s in lines]
    assert len({r['session_id'] for r in records})==8 and all(r['status']=='completed' for r in records)
    assert all(r[k]==0 for r in records for k in ['new_studies','new_reporter_requests','new_mathematical_solves','new_physics_runs','new_candidates'])
    cfg=read(ROOT/'replay_configuration.json');matrix=[];costs=[];requests=[];effects=[];interactions=[];structured={};engineering=[]
    for task in TASKS:
        snapshot=read(ROOT/'snapshots'/f'{task}.json')
        reviewfile=DATA/'blind_review/complete_four_llm'/task/'independent_model_review.json'
        review=read(reviewfile);evals={LABELS[task][e['label']]:e for e in review['review']['evaluations']}
        assert set(evals)==set(ORDER)
        taskrows=[];taskcost=[];rawdecisions={}
        for condition in ORDER:
            r=next(x for x in records if x['task_id']==task and x['condition']==condition);folder=ROOT/'sessions'/r['session_id']
            expected,available=messages_for(snapshot,condition)
            assert read(folder/'initial_messages.json')==expected
            assert read(folder/'request_1.json')['messages']==expected
            per=[];outputs=[]
            for q in r['requests']:
                wire=read(folder/f"request_{q['turn']}.json")
                assert set(wire)=={'model','stream','messages'} and wire['model']==cfg['provider']['model'] and wire['stream'] is False
                payload=httpx.Request('POST',cfg['provider']['base_url']+'/chat/completions',json=wire).content
                isnew=r['condition']=='K+S+'
                if isnew:assert payload==(folder/f"request_{q['turn']}.json").read_bytes()
                tokens=len(ENC.encode(payload.decode('utf-8')))
                body=read(folder/f"response_{q['turn']}.txt")
                usage=body.get('usage')
                assert q.get('usage')==usage
                output_message=json.dumps(body['choices'][0]['message'],ensure_ascii=False,separators=(',',':'))
                outputs.append(len(ENC.encode(output_message)))
                part=dict(task_id=task,condition=condition,session_id=r['session_id'],turn=q['turn'],http_status=q['http_status'],
                    input_tokens_actual=(usage or {}).get('prompt_tokens'),output_tokens_actual=(usage or {}).get('completion_tokens'),
                    input_full_wire_tokens_estimated=tokens,wire_bytes=len(payload),
                    wire_scope='Exact bytes captured for new supplement.' if isnew else 'Reconstructed compact HTTPX json=wire serialization from original saved request object; original transport bytes were not separately captured.',
                    request_file=(folder/f"request_{q['turn']}.json").as_posix(),response_file=(folder/f"response_{q['turn']}.txt").as_posix(),estimate_basis=PROXY)
                per.append(part);requests.append(part)
            actual_in=total_actual(r['requests'],'prompt_tokens');actual_out=total_actual(r['requests'],'completion_tokens')
            cost=dict(task_id=task,condition=condition,origin='Main_LLM_decision_replay',session_id=r['session_id'],model=cfg['provider']['model'],
                acquisition_phase='supplement_KplusSplus' if condition=='K+S+' else 'original_six_replays',
                input_tokens_actual=actual_in,output_tokens_actual=actual_out,total_tokens_actual=total_actual(r['requests'],'total_tokens'),
                actual_usage_status='provider_actual' if actual_in is not None and actual_out is not None else 'gateway_usage_missing_not_zero',
                provider_requests=r['provider_requests'],schema_or_parse_repairs=len(r['errors']),
                initial_context_tokens_estimate=per[0]['input_full_wire_tokens_estimated'],total_sent_input_full_wire_tokens_estimate=sum(p['input_full_wire_tokens_estimated'] for p in per),
                total_output_serialized_assistant_tokens_estimate=sum(outputs),legacy_initial_visible_text_tokens_estimate=sum(len(ENC.encode(m['content'])) for m in expected),
                context_estimate_scope='Complete wire JSON for every send; repeated context is counted repeatedly. Native tools are serialized inside the system prompt exactly as original E1.',
                estimate_basis=PROXY,wire_scope=per[0]['wire_scope'],effective_reasoning=r['effective_reasoning'],reporter_requests=0,
                delivered_entry_keys=[a['key'] for a in available],optional_experience_retrieve_calls=len(r['experience_reads']),
                experience_read_claim='Entry bodies were preloaded on real Main wire. Optional retrieval calls are separate; no fabricated tool-read claim.',
                source_directory=folder.as_posix())
            costs.append(cost);taskcost.append(cost)
            e=evals[condition];sc=e['scores'];baseline=evals['K-S-']['scores']
            row=dict(task_id=task,condition=condition,knowledge_on=condition.startswith('K+'),skill_on=condition.endswith('S+'),
                origin='Main_LLM_decision_replay',historical_reference_only=False,frozen_inputs_and_requested_settings_match=True,
                temporal_backend_matching='Unverified: new K+S+ acquired later; Gateway default reasoning/backend revision not exposed.',
                anonymous_label=next(l for l,c in LABELS[task].items() if c==condition),**sc,
                mean_of_four_scores=statistics.mean(sc.values()),**{m+'_delta_vs_KminusSminus':sc[m]-baseline[m] for m in METRICS},
                invalid_research_actions_count=len(e['invalid_research_actions']),invalid_research_actions=e['invalid_research_actions'],
                invalid_action_scope='Independent review of final proposed decision; parsing and future execution admission are separate.',
                schema_or_parse_repairs=len(r['errors']),knowledge_observations=e['knowledge_observations'],skill_observations=e['skill_observations'],
                experience_integration=e['experience_integration'],evidence_specific_rationale=e['evidence_specific_rationale'],
                action=r['decision']['action'],selected_method=(r['decision'].get('decision') or {}).get('selected_method'),
                experience_entries_delivered=cost['delivered_entry_keys'],provider_requests=r['provider_requests'],input_tokens_actual=actual_in,output_tokens_actual=actual_out,
                context_token_estimate=cost['initial_context_tokens_estimate'],cumulative_full_wire_input_token_estimate=cost['total_sent_input_full_wire_tokens_estimate'],
                decision_source_file=(folder/'result.json').as_posix(),decision_json_pointer='/decision',
                raw_decision_source=(folder/f"response_{r['requests'][-1]['turn']}.txt").as_posix()+'#/choices/0/message/content',
                score_source=reviewfile.as_posix(),judge_model=review['model'],human_verification='pending',
                interpretation_limit='One Main decision per cell, one joint independent-model review/task; no significance, population synergy or robot-success claim.')
            matrix.append(row);taskrows.append(row);rawdecisions[condition]=dict(decision=r['decision'],source=row['decision_source_file'],session_id=r['session_id'],evaluation=e)
        task_effects=[];task_interactions=[]
        for metric in METRICS+['mean_of_four_scores','invalid_research_actions_count']:
            y={r['condition']:r[metric] for r in taskrows};a,b,c,d=[y[k] for k in ORDER]
            main_k=((b-a)+(d-c))/2;main_s=((c-a)+(d-b))/2;inter=d-b-c+a
            erow=dict(task_id=task,metric=metric,y00_KminusSminus=a,y10_KplusSminus=b,y01_KminusSplus=c,y11_KplusSplus=d,
                K_effect_at_Soff=b-a,K_effect_at_Son=d-c,S_effect_at_Koff=c-a,S_effect_at_Kon=d-b,
                K_main_effect=main_k,S_main_effect=main_s,beta_K_plusminus1=main_k/2,beta_S_plusminus1=main_s/2,
                outcome_direction='lower_is_better' if metric=='invalid_research_actions_count' else 'higher_is_better',
                cell_origin='All four Main LLM outputs; no engineering Core Plan.',
                inference_scope='Descriptive within this four-cell sample; one observation/cell, unverified temporal/backend identity and overlapping entry contents.')
            irow=dict(task_id=task,metric=metric,interaction_difference_in_differences=inter,beta_KS_plusminus1=inter/4,
                K_effect_change_when_S_on=(d-c)-(b-a),S_effect_change_when_K_on=(d-b)-(c-a),
                joint_minus_best_single=d-(min(b,c) if metric=='invalid_research_actions_count' else max(b,c)),
                joint_minus_neither=d-a,algebra='I=y11-y10-y01+y00; +/-1 regression interaction coefficient=I/4.',
                interpretation='Ordinal/bounded score contrast only. Negative I can reflect overlapping benefits and score ceilings; it is not proof of harmful interaction or robot failure.',
                no_statistical_significance_claim=True)
            effects.append(erow);interactions.append(irow);task_effects.append(erow);task_interactions.append(irow)
        structured[task]=dict(conditions=rawdecisions,results=taskrows,token_costs=taskcost,main_effects=task_effects,interaction_effects=task_interactions,
            comparative_rationale=review['review']['comparative_rationale'],review_source=reviewfile.as_posix())
        historic=read(RUN/'engineering_reference'/f'{task}.json');write(DATA/'engineering_reference'/f'{task}.json',historic)
        engineering.append(dict(task_id=task,source=(DATA/'engineering_reference'/f'{task}.json').as_posix(),actor='codex_surrogate_main',historical_provider_calls=0,
            formal_main_executed=False,used_in_four_condition_scores=False,used_in_factorial_effects=False))
    csv_rows(DATA/'factorial_results.csv',matrix);csv_rows(DATA/'token_costs.csv',costs)
    csv_rows(DATA/'token_costs_per_request.csv',requests);csv_rows(DATA/'factorial_effects.csv',effects);csv_rows(DATA/'interaction_effects.csv',interactions)
    csv_rows(DATA/'engineering_reference_manifest.csv',engineering)
    csv_rows(ROOT/'scores_unblinded.csv',[{k:r[k] for k in ['task_id','condition','anonymous_label',*METRICS,'mean_of_four_scores','invalid_research_actions_count']} for r in matrix])
    # Update only the derived manifest, preserving original snapshot/source locators.
    with (DATA/'snapshot_manifest.csv').open(encoding='utf-8-sig',newline='') as f:manifest=list(csv.DictReader(f))
    for row in manifest:
        row.update(matching_status='All four cells now real Main LLM decisions from same frozen E1 inputs/settings; K+S+ acquired later, backend identity unverified.',
            historical_plan_scoring='Excluded; kept in engineering_reference/',new_KplusSplus_session_id=next(r['session_id'] for r in records if r['task_id']==row['task_id'] and r['condition']=='K+S+'))
    csv_rows(DATA/'snapshot_manifest.csv',manifest)
    quotes={
        'T04':[
            ('hypothesis','its historical 0.27 m single-segment hardware exceeds the current root-segment bound and cannot be transferred.'),
            ('interpretation','after generation, the plan should use the registered constructor, inspect the returned bank, independently qualify time zero, and only then initialize control and request a complete independent replay with interior tensions.')],
        'T07':[
            ('interpretation','it suggests that two root-only and two full-span tendons separate proximal and distal authority and identifies an in-domain simple geometry worth freshly reconstructing.'),
            ('interpretation','The shared-structure skill supports generating one owned structure, diagnosing the hardest case first, separating static authority from tendon-speed and braking limitations, and testing all required cases before aggregation.')],
    }
    clipdata=[];md=['# Complete E1: real Main LLM four-condition comparison','',
        'All eight scored decisions are Main LLM outputs. Original engineering Core Plans remain separate unscored references. The original six decisions were reused; exactly two K+S+ sessions were added. All later steps below are proposed, not executed.','']
    for task in TASKS:
        data=structured[task];joint=data['conditions']['K+S+'];rows={r['condition']:r for r in data['results']}
        md.extend([f'## {task}', '', '| Condition | Historical experience | Decision quality | Evidence consistency | Actionability | Invalid actions |',
            '| --- | ---: | ---: | ---: | ---: | ---: |'])
        for c in ORDER:
            r=rows[c];md.append(f"| {c} | {r['historical_experience_utilization']} | {r['decision_quality']} | {r['evidence_consistency']} | {r['research_actionability']} | {r['invalid_research_actions_count']} |")
        md.extend(['', 'K+S+ original wording (history fact linked to a proposed procedure):',''])
        for field,quote in quotes[task]:
            assert quote in joint['decision'][field]
            clipdata.append(dict(task_id=task,condition='K+S+',quote=quote,source=joint['source'],pointer='/decision/'+field,
                source_kind='New Main LLM raw response/validated Plan, not an authored Core Plan.'))
            md.extend(['> '+quote,'',f"Source: `{joint['source']}`, `/decision/{field}`.",''])
        h=next(x for x in data['interaction_effects'] if x['metric']=='historical_experience_utilization')
        md.extend([f"Experience-utilization interaction contrast I = {h['interaction_difference_in_differences']}; joint minus best single = {h['joint_minus_best_single']}. These describe this bounded-score sample; a qualitative connection between facts and methods does not establish positive additive synergy.",'',
            'Independent blind-review integration assessment: '+joint['evaluation']['experience_integration'],'',
            'Joint-decision weaknesses: '+json.dumps(joint['evaluation']['weaknesses'],ensure_ascii=False),''])
    md.extend(['## Interpretation and provenance','',
        'Use the original decision clips to illustrate a prospective facts-to-procedure connection. Do not claim K+S+ improves every dimension or exceeds both single factors unless the corresponding score contrast supports it. No subsequent research action was executed.','',
        'The primary scores are from one new anonymous four-LLM review per task with the unchanged original E1 rubric. Previous mixed-origin reviews are preserved under ks_completion/prior_figure_data and are superseded for the updated tables. Human forms are under blind_review/complete_four_llm/.','',
        'Gateway actual usage is missing and remains unknown, not zero. Full-wire token estimates are generic o200k_base proxies; old wire serialization was reconstructed from saved request objects and the original HTTPX client format. Legacy visible-text estimates remain separately labeled.','',
        'Knowledge and Skill bundles overlap semantically. Each cell has one sample, K+S+ was acquired later, and default reasoning/backend revision is unexposed. Do not claim statistical significance, pure semantic separation, population causal synergy, or improved robot success.'])
    (DATA/'knowledge_skill_clips.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    write(DATA/'knowledge_skill_clip_data.json',clipdata)
    limits=['One Main decision per cell and one independent model joint review/task; human verification pending.',
        'Same frozen inputs/prompts/schema/model/transport/permissions/budgets, but supplemental K+S+ was acquired later and backend/default reasoning identity is unexposed.',
        'Knowledge and Skill entries overlap; bounded ordinal score interactions do not prove statistical or causal synergy.',
        'No robot/mathematical follow-up executed; no task-success effect measured.',PROXY,
        'Original authored engineering Core Plans and their old scores are excluded from the four-LLM factorial tables and plots.']
    result=dict(experiment='E1_complete_four_Main_LLM_conditions',tasks=structured,condition_order=ORDER,metric_order=METRICS,
        new_Main_sessions_this_supplement=2,new_Main_requests_this_supplement=sum(r['provider_requests'] for r in records if r['condition']=='K+S+'),
        all_Main_sessions=8,all_Main_requests=sum(r['provider_requests'] for r in records),new_independent_review_requests=2,
        engineering_references=engineering,clips=clipdata,main_effect_definition='Average of conditional ON-minus-OFF differences over the other factor.',
        interaction_definition='Difference-in-differences y11-y10-y01+y00; +/-1 regression coefficient is contrast/4.',
        limitations=limits,prior_materials_archive=(RUN/'prior_figure_data').as_posix(),new_scientific_executions=0)
    write(DATA/'ks_four_condition_comparison.json',result)
    write(DATA/'factorial_results.json',result)
    notes=read(ROOT/'matching_and_leakage_notes.json')
    notes['superseded_previous_notes_archive']=(RUN/'prior_matching_and_leakage_notes.json').as_posix()
    notes['historical_reference_differences']=limits
    notes['current_four_cell_status']='All eight cells are real Main LLM decisions; engineering reference excluded.'
    write(ROOT/'matching_and_leakage_notes.json',notes)
    oldaccount=read(RUN/'prior_execution_accounting.json')
    account=dict(all_Main_sessions=8,all_Main_provider_requests=result['all_Main_requests'],supplement_Main_sessions=2,supplement_Main_requests=result['new_Main_requests_this_supplement'],
        original_six_reruns=0,supplement_joint_review_requests=2,all_review_requests_including_archived=oldaccount['independent_model_review_requests']+2,
        current_used_review_requests=2,engineering_Core_Plans_in_factorial=0,new_scientific_executions=0,new_Knowledge_or_Skill_entries=0,
        actual_Main_usage='Missing from Gateway, unknown not zero.',token_estimates=PROXY)
    write(ROOT/'execution_accounting.json',account);write(RUN/'completion_accounting.json',account)
    print(json.dumps(dict(completed=True,accounting=account,results=[{k:r[k] for k in ['task_id','condition',*METRICS,'invalid_research_actions_count']} for r in matrix],
        utilization_interactions=[r for r in interactions if r['metric']=='historical_experience_utilization']),ensure_ascii=False),flush=True)


if __name__=='__main__':finalize()
