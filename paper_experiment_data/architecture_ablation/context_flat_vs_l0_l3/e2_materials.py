"""Serialize the completed pair and blind scores; no provider/science requests."""
import bisect
import collections
import json
import os
import statistics
import sys
from e2_replay import ROOT,DATA,SOURCE,read,write,csv_rows
from e2_review import LABELS,METRICS

PREVIOUS=ROOT.parent/'reporter_on_off'
sys.path.insert(0,str(PREVIOUS/'tokenizer_runtime'))
os.environ['TIKTOKEN_CACHE_DIR']=str(PREVIOUS/'tokenizer_cache')
import tiktoken
ENC=tiktoken.get_encoding('o200k_base')
PROXY='estimated_generic_proxy: tiktoken 0.12.0 o200k_base on the exact complete serialized wire payload. No registered mapping for gpt-5.6-sol; NOT a verified model-matched tokenizer or billing measure.'
KINDS=['framing','system','task','history','evidence','tool_schema']

def dumps(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def estimate(x):return len(ENC.encode(x if isinstance(x,str) else dumps(x)))

def wire_components(payload,wire,condition,previous_messages,previous_tools):
    """Partition WHOLE-wire proxy tokens by their first UTF-8 byte, never dedup totals.

    Initial delivery categories are a deterministic allocation of serialized JSON,
    not an inferred decomposition of Provider usage. Token boundary allocation makes
    these estimates additive including explicit wire framing.
    """
    raw=payload.encode('utf-8');tags=bytearray(len(raw));repeated=bytearray(len(raw))
    def span(literal,start=0):
        pos=payload.index(literal,start)
        return len(payload[:pos].encode('utf-8')),len(payload[:pos+len(literal)].encode('utf-8'))
    def fill(literal,category,start=0):
        lo,hi=span(literal,start);tags[lo:hi]=bytes([KINDS.index(category)])*(hi-lo)
        return lo,hi
    next_messages=set(previous_messages)
    cursor=0
    for msg in wire['messages']:
        text=dumps(msg);pos=payload.index(text,cursor);cursor=pos+len(text)
        category='system' if msg['role']=='system' else 'evidence' if msg['role']=='tool' else 'task' if str(msg.get('content','')).startswith('FROZEN_TASK\n') else 'history'
        lo,hi=fill(text,category,pos)
        if text in previous_messages:repeated[lo:hi]=b'\1'*(hi-lo)
        next_messages.add(text)
        content=msg.get('content')
        if not isinstance(content,str):continue
        if content.startswith('COMPLETE_FROZEN_HISTORY_AND_EVIDENCE\n'):
            atoms=json.loads(content.split('\n',1)[1])
            for atom in atoms:
                # Match escaped inner JSON exactly as it occurs inside content.
                inner=json.dumps(atom,separators=(',',':'))
                escaped=json.dumps(inner,ensure_ascii=False)[1:-1]
                cat='task' if atom['information_id'] in ['TASK','EXPERIENCE_POLICY'] else 'history' if atom['content_category'] in ['original_Codex_execution_record','original_error_or_log'] else 'evidence'
                fill(escaped,cat,pos)
        elif content.startswith('CURRENT_RESEARCH_PACKET\n'):
            packet=json.loads(content.split('\n',1)[1])
            for key,value in packet.items():
                inner=json.dumps(key)+':'+json.dumps(value,separators=(',',':'))
                escaped=json.dumps(inner,ensure_ascii=False)[1:-1]
                cat='task' if key in ['task','task_identity','experience_policy'] else 'evidence' if key in ['mathematical_research','scientific_results','current_candidate_preview','latest_scientific_feedback','current_candidate'] else 'history'
                fill(escaped,cat,pos)
    tooltext=dumps(wire['tools']);lo,hi=fill(tooltext,'tool_schema')
    if tooltext in previous_tools:repeated[lo:hi]=b'\1'*(hi-lo)
    counts=collections.Counter();repeat_count=0;offset=0
    token_ids=ENC.encode(payload)
    for token in token_ids:
        counts[KINDS[tags[offset]]]+=1
        if repeated[offset]:repeat_count+=1
        offset+=len(ENC.decode_single_token_bytes(token))
    assert offset==len(raw) and sum(counts.values())==len(token_ids)
    return dict(whole_wire_tokens_estimated=len(token_ids),components_estimated={k:counts[k] for k in KINDS},
        repeated_context_tokens_estimated=repeat_count),next_messages,previous_tools|{tooltext}

def finalize():
    records=[json.loads(x) for x in (DATA/'context_replay_results.jsonl').read_text('utf-8').splitlines()]
    assert len(records)==2 and {x['condition'] for x in records}=={'Flat','Hierarchical'}
    assert all(x['status']=='completed' and 1<=x['provider_requests']<=4 for x in records)
    assert all(x[k]==0 for x in records for k in ['new_scientific_actions','new_workers','new_reporter_calls'])
    by={x['condition']:x for x in records};corpus=read(ROOT/'corpus.json')
    assert len(corpus['atoms'])==66
    for a in corpus['atoms']:assert a['flat_included'] and a['hierarchical_accessible']
    folder=DATA/'blind_review';review_path=folder/'independent_model_review.json'
    review=read(review_path) if review_path.exists() else None
    evaluations={LABELS[e['label']]:e for e in review['review']['evaluations']} if review else {}
    score_rows=[]
    for label,condition in LABELS.items():
        e=evaluations.get(condition,{})
        score_rows.append(dict(snapshot_id='PHS_C035',anonymous_label=label,condition_unblinded_after_review=condition,
            **{m:e.get('scores',{}).get(m) for m in METRICS},mean_score=e.get('mean_score'),
            score_status='independent_blind_model_review_human_verification_pending' if review else 'human_scoring_pending',
            judge_model=review['model'] if review else None,score_source=review_path.as_posix() if review else (folder/'human_scoring_template.csv').as_posix(),
            score_pointer='/review/evaluations/'+str(next((i for i,x in enumerate(review['review']['evaluations']) if x['label']==label),0)) if review else None,
            strengths=e.get('strengths',[]),weaknesses=e.get('weaknesses',[]),rationale=e.get('evidence_specific_rationale')))
    csv_rows(DATA/'decision_scores.csv',score_rows)
    accounting=[];per_requests=[];read_costs=[];details={}
    for condition in ['Flat','Hierarchical']:
        record=by[condition];session=ROOT/'sessions'/record['session_id']
        seen_messages=set();seen_tools=set();parts=[];success=[];outputs=[]
        for req in record['requests']:
            path=session/f"request_{req['turn']}.json"
            payload=path.read_bytes().decode('utf-8');wire=json.loads(payload)
            alloc,seen_messages,seen_tools=wire_components(payload,wire,condition,seen_messages,seen_tools)
            body=read(session/f"response_{req['turn']}.txt")
            usage=body.get('usage')
            part=dict(snapshot_id='PHS_C035',condition=condition,session_id=record['session_id'],turn=req['turn'],
                http_status=req['http_status'],model=wire['model'],reasoning_effort=wire.get('reasoning_effort'),
                exact_wire_file=path.as_posix(),wire_bytes=len(payload.encode('utf-8')),**alloc,
                input_tokens_actual=(usage or {}).get('prompt_tokens'),output_tokens_actual=(usage or {}).get('completion_tokens'),
                cached_input_tokens_actual=(usage or {}).get('prompt_tokens_details',{}).get('cached_tokens'),
                cache_write_tokens_actual=(usage or {}).get('prompt_tokens_details',{}).get('cache_write_tokens'),
                usage_status='provider_actual' if usage else 'missing_on_rejected_request_not_zero',
                full_wire_proxy_basis=PROXY)
            parts.append(part);per_requests.append(part)
            if req['http_status']==200:
                assert wire['reasoning_effort']=='none'
                success.append(part)
                outputs.append(estimate(body['choices'][0]['message']))
        all_covered=all(p['input_tokens_actual'] is not None for p in parts)
        output_covered=all(p['output_tokens_actual'] is not None for p in parts)
        initial=success[0];c=initial['components_estimated']
        readkeys=[]
        for i,x in enumerate(record['reads'],1):
            key=dumps(dict(tool=x['tool'],arguments=x['arguments']))
            resultmsg=dict(role='tool',tool_call_id=x['tool_call_id'],content=json.dumps(x['result'],separators=(',',':')))
            read_costs.append(dict(condition=condition,read_ordinal=i,turn=x['turn'],tool=x['tool'],arguments=x['arguments'],
                information_id=x['result'].get('information_id'),information_level=x['result'].get('information_level'),
                tool_result_message_tokens_estimated=estimate(resultmsg),repeated_read=key in readkeys,token_basis=PROXY))
            readkeys.append(key)
        row=dict(snapshot_id='PHS_C035',condition=condition,session_id=record['session_id'],
            initial_system_tokens=c['system'],initial_task_tokens=c['task'],initial_history_tokens=c['history'],
            initial_evidence_tokens=c['evidence'],initial_tool_schema_tokens=c['tool_schema'],initial_wire_framing_tokens=c['framing'],
            initial_components_basis=PROXY+' Components assign each token by its first byte in the full serialization; sum includes framing.',
            initial_total_input_tokens=initial['input_tokens_actual'],initial_total_basis='provider_actual_first_accepted_decision_request',
            initial_accepted_request_turn=initial['turn'],initial_total_input_tokens_estimated=initial['whole_wire_tokens_estimated'],
            first_attempt_input_tokens_actual=parts[0]['input_tokens_actual'],first_attempt_input_tokens_estimated=parts[0]['whole_wire_tokens_estimated'],
            total_input_tokens=sum(p['input_tokens_actual'] for p in parts) if all_covered else None,
            total_output_tokens=sum(p['output_tokens_actual'] for p in parts) if output_covered else None,
            all_attempts_actual_usage_complete=all_covered and output_covered,
            accepted_total_input_tokens_actual=sum(p['input_tokens_actual'] for p in success),
            accepted_total_output_tokens_actual=sum(p['output_tokens_actual'] for p in success),
            accepted_total_input_basis='Provider actual usage summed for every HTTP200 inference; rejected attempt has no usage and is separately retained.',
            total_input_tokens_estimated_all_attempts=sum(p['whole_wire_tokens_estimated'] for p in parts),
            accepted_total_input_tokens_estimated=sum(p['whole_wire_tokens_estimated'] for p in success),
            total_output_tokens_estimated_accepted_assistant_messages=sum(outputs),output_estimate_scope='Complete serialized assistant message; API envelope/error body/hidden reasoning excluded; not billing.',
            repeated_context_tokens=sum(p['repeated_context_tokens_estimated'] for p in parts),
            repeated_context_tokens_basis='estimated_generic_proxy: re-sent identical messages and tool schemas, allocated in each complete wire. Includes the rejected send; initial context is NOT deduplicated from cumulative totals.',
            evidence_read_tokens=sum(x['tool_result_message_tokens_estimated'] for x in read_costs if x['condition']==condition),
            evidence_read_tokens_basis='estimated_generic_proxy_complete_tool_result_message; zero because no evidence reads occurred.',
            number_of_provider_requests=len(parts),number_of_accepted_provider_requests=len(success),
            number_of_rejected_provider_requests=len(parts)-len(success),number_of_requests_with_usage=sum(p['input_tokens_actual'] is not None for p in parts),
            number_of_evidence_reads=len(record['reads']),number_of_repeated_reads=len(readkeys)-len(set(readkeys)),
            read_levels=sorted({x['result'].get('information_level') for x in record['reads'] if x['result'].get('information_level')}),
            model=success[0]['model'],effective_reasoning='none',provider_usage_source=[(session/f"response_{q['turn']}.txt").as_posix() for q in record['requests']],
            missing_usage_note='One initial HTTP400 incompatible reasoning/tool request has no usage. All-attempt actual cumulative usage is unknown; not assigned zero.' if not all_covered else '',
            estimated_tokenizer_model_match_verified=False,estimate_basis=PROXY)
        accounting.append(row);details[condition]=dict(accounting=row,requests=parts,decision=record['decision'],
            decision_source=(session/'result.json').as_posix(),decision_pointer='/decision',reads=record['reads'],evaluation=evaluations.get(condition))
    csv_rows(DATA/'token_accounting.csv',accounting)
    write(DATA/'token_request_accounting.json',dict(requests=per_requests,evidence_reads=read_costs,allocation_method=PROXY,
        caveat='Provider actual total usage is primary. Component and repeated-context allocation uses a generic proxy, never a model-matched claim. Every actual send is included in full-wire estimated totals.'))
    f,h=accounting
    initial_reduction=1-h['initial_total_input_tokens']/f['initial_total_input_tokens']
    accepted_reduction=1-h['accepted_total_input_tokens_actual']/f['accepted_total_input_tokens_actual']
    proxy_reduction=1-h['total_input_tokens_estimated_all_attempts']/f['total_input_tokens_estimated_all_attempts']
    proxy_accepted_reduction=1-h['accepted_total_input_tokens_estimated']/f['accepted_total_input_tokens_estimated']
    strict_reduction=1-h['total_input_tokens']/f['total_input_tokens'] if all(x['total_input_tokens'] is not None for x in accounting) else None
    fs=evaluations.get('Flat',{}).get('mean_score');hs=evaluations.get('Hierarchical',{}).get('mean_score')
    comparison=dict(snapshot_id='PHS_C035',task_id='PHS-2D',flat_initial_input_tokens_actual=f['initial_total_input_tokens'],
        hierarchical_initial_input_tokens_actual=h['initial_total_input_tokens'],initial_measurement_scope='First accepted inference in each condition; initial Hier HTTP400 reported separately.',
        initial_input_reduction_actual=initial_reduction,flat_accepted_cumulative_input_tokens_actual=f['accepted_total_input_tokens_actual'],
        hierarchical_accepted_cumulative_input_tokens_actual=h['accepted_total_input_tokens_actual'],accepted_cumulative_input_reduction_actual=accepted_reduction,
        flat_all_attempts_input_tokens_actual=f['total_input_tokens'],hierarchical_all_attempts_input_tokens_actual=h['total_input_tokens'],all_attempts_input_reduction_actual=strict_reduction,
        flat_all_attempts_input_tokens_estimated=f['total_input_tokens_estimated_all_attempts'],hierarchical_all_attempts_input_tokens_estimated=h['total_input_tokens_estimated_all_attempts'],
        all_attempts_input_reduction_estimated_generic_proxy=proxy_reduction,accepted_input_reduction_estimated_generic_proxy=proxy_accepted_reduction,
        flat_output_tokens_actual=f['accepted_total_output_tokens_actual'],hierarchical_output_tokens_actual=h['accepted_total_output_tokens_actual'],
        flat_provider_requests=f['number_of_provider_requests'],hierarchical_provider_requests=h['number_of_provider_requests'],
        flat_accepted_provider_requests=f['number_of_accepted_provider_requests'],hierarchical_accepted_provider_requests=h['number_of_accepted_provider_requests'],
        flat_reads=f['number_of_evidence_reads'],hierarchical_reads=h['number_of_evidence_reads'],
        flat_score=fs,hierarchical_score=hs,score_delta_hier_minus_flat=round(hs-fs,6) if fs is not None and hs is not None else None,
        paired_winner='Flat' if fs is not None and fs>hs else 'Hierarchical' if hs is not None and hs>fs else 'tie' if fs is not None else 'unscored',
        positive_quality_preservation_clip_eligible=bool(fs is not None and hs>=fs and accepted_reduction>0),
        decision_difference='Flat proposes an intermediate 1.5e-4 N m^2 s viscosity candidate; Hier proposes a read-only F2/F3/F4 comparison of already recorded trends.',
        interpretation='Large input reduction with a 0.2-point mean-score decrease in this single pair; four of five dimensions remain equal. No overall quality-preservation claim.',
        actual_usage_caveat='All-attempt actual reduction is unavailable because initial Hier rejection has no usage. Accepted-inference and generic whole-wire all-send estimates remain separate.',
        sample_scope='One checkpoint, one decision per condition, one blind model reviewer; human review pending; no statistical significance or physical success claim.')
    csv_rows(DATA/'context_comparison_table.csv',[comparison])
    clips=[]
    # The literal quotations below are extracted, never paraphrased as original text.
    quote_h='hard-equilibrium mathematics does not transfer to dynamic success, and no independent full ten-case acceptance exists.'
    quote_f='At 2e-4, drift and qvel improved further, but tip/monitor speeds did not and static balance regressed to 0.00371 N m.'
    for cond,quote in [('Hierarchical',quote_h),('Flat',quote_f)]:
        assert quote in by[cond]['decision']['interpretation']
        clips.append(dict(condition=cond,quote=quote,source=details[cond]['decision_source'],pointer='/decision/interpretation'))
    text=f'''# PHS_C035: observed cost–quality tradeoff

No qualifying Clip A (quality tie), Clip B (quality improvement), or on-demand L1–L3 reading clip was observed. Do not present this pair as overall quality preservation. Both conditions made zero extra evidence reads; this does not test selective read effectiveness or repeated-read avoidance.

## Limited positive observation: evidence boundaries retained with a smaller delivered input

- Provider actual first accepted input: Flat {f['initial_total_input_tokens']:,}; Hierarchical {h['initial_total_input_tokens']:,}; reduction {initial_reduction:.4%}.
- Accepted cumulative input is the same in this one-inference-per-condition pair. These are not two independent findings.
- Blind mean: Flat {fs}; Hierarchical {hs}. Hierarchical minus Flat = {round(hs-fs,6) if fs is not None else 'unscored'}.
- Evidence consistency, limitation recognition, actionability and reference accuracy are 4/4 for both. Research decision quality is 4 for Flat and 3 for Hierarchical. The retained boundary below illustrates only that narrower strength.

Hierarchical original (`sessions/{by['Hierarchical']['session_id']}/result.json`, `/decision/interpretation`):

> {quote_h}

Flat original (`sessions/{by['Flat']['session_id']}/result.json`, `/decision/interpretation`):

> {quote_f}

The reviewer favored Flat because it uses the already observed non-monotone trend to propose an untested intermediate candidate. Hierarchical instead proposes a sound but partly redundant saved-response comparison. No proposed action was executed.

## Token accounting boundary

An initial Hierarchical HTTP400 rejected medium reasoning with function tools. Both successful conditions then used reasoning=none. This one failed send remains in the raw request count: Flat 1 send, Hierarchical 2 sends (1 accepted each). Its usage is absent, not zero.

Accepted inference usage reduction is {accepted_reduction:.4%}. **Strict all-send actual cumulative reduction is unavailable.** Full-wire generic-proxy totals including the rejected send are Flat {f['total_input_tokens_estimated_all_attempts']:,} and Hierarchical {h['total_input_tokens_estimated_all_attempts']:,}, reduction {proxy_reduction:.4%}. The proxy is not verified for this model and is supplemental; it must not be merged with actual usage.

## Traceable references

- Main decisions: `context_replay_results.jsonl`, condition/session fields, original `/decision/interpretation`; session raw responses preserve exact function arguments.
- Blind scores: `blind_review/independent_model_review.json`, `/review/evaluations/0` (anonymous A) and `/review/evaluations/1` (anonymous B); map opened after review in `decision_scores.csv`.
- Shared corpus: `information_manifest.json` resolves C031/C032 (F3), C034/C035 (F4) and CURRENT_CANDIDATE to unchanged source files. C035 `/observation/qualification_diagnosis` contains loaded qualification and incomplete task scope; detailed F3/F4 metrics are in C032/C035 observations.
- Token sources: `token_request_accounting.json` links every exact wire and original response. No length/read-count/reference-count bonus was used.

This is one engineering-Core-origin checkpoint with two fresh Main decisions, not a recovered historical Main conversation. Later FULL acceptance is provenance only, never decision or reviewer input. No robot success-rate result or statistical significance is claimed.
'''
    (DATA/'positive_context_clips.md').write_text(text,encoding='utf-8')
    layout='''# Figure material layout

Panel A: paired accepted-inference cumulative input, Flat 675,802 and L0–L3 78,785 Provider tokens. Annotate 88.3420% reduction, with “accepted inference only” beside the label. An outlined inset may show all-send generic-proxy totals, including the failed initial send. Never combine actual and proxy bars on one unlabeled measurement basis. Strict all-send actual usage is unavailable.

Panel B: five paired blind scores and the equal-weight means (Flat 4.0, L0–L3 3.8). Display the 0.2-point decline; do not label the result quality-equivalent. Four matched 4/4 dimensions can be shown alongside research-decision-quality 4 versus 3.

Optional evidence-flow inset: frozen 66-record corpus → Flat full delivery → intermediate-viscosity generation proposal; same corpus → automatic Core L0 and directory → saved-response-comparison proposal. Both made zero extra reads. Use a dashed arrow for available L1/L2/L3 access, not a solid arrow implying it occurred.

Use the exact clips and decision pointers in positive_context_clips.md. The narrower positive observation is retained evidence boundaries with much less input, accompanied by a small decision-quality loss. There is no qualifying overall quality-preservation/improvement clip and no demonstrated selective-read mechanism in this pair.

No confidence intervals, significance tests, general robot success claims, or duplicated “initial”/“cumulative” findings: each condition had one accepted inference. Caption-level qualifications: one engineering-Core-origin checkpoint, reasoning none after one logged API parameter rejection, independent model review with human verification pending, and absent rejected-request usage.
'''
    (DATA/'figure_layout_suggestion.md').write_text(layout,encoding='utf-8')
    limitations=[comparison['actual_usage_caveat'],PROXY,comparison['sample_scope'],
        'The replay context uses existing Core pure projections and ephemeral CURRENT_RESEARCH_PACKET delivery with a minimal read-only archive adapter, not a live historical Host or recovered Main dialogue.',
        'No additional evidence reads occurred; L1–L3 accessibility was checked on all 66 records before inference, but behavior here only tests direct full delivery versus automatic L0 delivery.',
        'A first incompatible API request was rejected before inference; subsequent successful requests in both conditions use reasoning none.']
    write(DATA/'figure_data.json',dict(experiment='E2',snapshot_id='PHS_C035',source=(SOURCE/'FINAL_RESULT.md').as_posix(),
        snapshot_manifest=(DATA/'snapshot_manifest.csv').as_posix(),information_manifest=(DATA/'information_manifest.json').as_posix(),
        conditions=details,comparison=comparison,clips=clips,qualifying_overall_positive_clip=False,
        blind_review_source=review_path.as_posix(),blind_review=review,limitations=limitations,
        actual_new_main_sessions=2,actual_main_provider_sends=sum(x['number_of_provider_requests'] for x in accounting),
        accepted_main_provider_requests=2,independent_review_requests=1 if review else 0,new_scientific_executions=0,
        component_allocation='Every token of the exact serialized wire is allocated by its first byte into system/task/history/evidence/tool_schema/framing. This partitions only generic-proxy estimates; Provider actual totals are not apportioned.'
    ))
    # Add only factual provenance to the new derived snapshot manifest.
    import csv
    with (DATA/'snapshot_manifest.csv').open(encoding='utf-8-sig',newline='') as stream:snap=list(csv.DictReader(stream))
    snap[0].update(historical_FULL_result='From-scratch F8 accepted in original ten cases and identical-structure half-timestep ten-case confirmation; later than checkpoint and excluded from both decision/review inputs.',
        historical_FULL_closeout_boundary='Original engineering Main SELECT was not completed; physical evaluator acceptance is separate from formal Main selection.',
        effective_replay_model='gpt-5.6-sol',effective_replay_reasoning='none',replay_order='Hierarchical then Flat (single pre-inference random shuffle)',
        api_parameter_repair='One initial Hierarchical HTTP400; medium -> none for BOTH conditions before successful inference. Retained with missing usage.')
    csv_rows(DATA/'snapshot_manifest.csv',snap)
    required=['snapshot_manifest.csv','information_manifest.json','context_replay_results.jsonl','token_accounting.csv','decision_scores.csv','context_comparison_table.csv','positive_context_clips.md','figure_data.json','figure_layout_suggestion.md']
    assert all((DATA/name).is_file() for name in required)
    print(json.dumps(dict(completed=True,new_main_sessions=2,provider_sends=3,accepted_main_requests=2,independent_review_requests=1,
        comparison=comparison,required_files=required),ensure_ascii=False),flush=True)

if __name__=='__main__':finalize()
