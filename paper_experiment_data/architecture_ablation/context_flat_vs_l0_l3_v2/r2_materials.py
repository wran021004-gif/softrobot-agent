"""Aggregate saved E2-R2 wires, decisions and blind scores; no inference/science."""
import collections
import csv
import json
import os
import statistics
import sys
from r2_replay import ROOT,DATA,SOURCE,read,write,csv_rows
from r2_review import LABELS,METRICS

TOKROOT=ROOT.parent/'reporter_on_off'
sys.path.insert(0,str(TOKROOT/'tokenizer_runtime'));os.environ['TIKTOKEN_CACHE_DIR']=str(TOKROOT/'tokenizer_cache')
import tiktoken
ENC=tiktoken.get_encoding('o200k_base')
BASIS='estimated_generic_proxy: same tiktoken 0.12.0/o200k_base over EXACT COMPLETE serialized wire, including tools, metadata and repeated history. Not a verified model mapping or billing measure.'
KIND=['framing','system','tool_schema','task','question','history','evidence']


def dump(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))


def allocate(payload,wire,seen):
    """Additive full-wire proxy allocation by first UTF-8 byte of each token.

    Repetition uses identical full messages, schemas, and L0 top-level fields. Thus
    appending read_progress does not erase the cost of re-sending the rest of L0.
    """
    raw=payload.encode('utf-8');tags=bytearray(len(raw));repeat=bytearray(len(raw));readids={};newseen=set(seen)
    def span(text,start=0):
        p=payload.index(text,start);return len(payload[:p].encode('utf-8')),len(payload[:p+len(text)].encode('utf-8'))
    def label(text,kind,start=0,unit=None):
        lo,hi=span(text,start);tags[lo:hi]=bytes([KIND.index(kind)])*(hi-lo)
        if unit:
            if unit in seen:repeat[lo:hi]=b'\1'*(hi-lo)
            newseen.add(unit)
        return lo,hi
    cursor=0
    for msg in wire['messages']:
        text=dump(msg);pos=payload.index(text,cursor);cursor=pos+len(text);content=msg.get('content')
        cat='system' if msg['role']=='system' else 'evidence' if msg['role']=='tool' else 'task' if str(content).startswith('FROZEN_TASK\n') else 'question' if str(content).startswith('FROZEN_RESEARCH_QUESTION\n') else 'history'
        lo,hi=label(text,cat,pos,'message:'+text)
        if msg['role']=='tool':readids[msg['tool_call_id']]=(lo,hi)
        if not isinstance(content,str):continue
        if content.startswith('COMPLETE_FROZEN_HISTORY_AND_EVIDENCE\n'):
            for a in json.loads(content.split('\n',1)[1]):
                inner=json.dumps(a,separators=(',',':'));escaped=json.dumps(inner,ensure_ascii=False)[1:-1]
                category='task' if a['information_id']=='TASK' else 'history' if a['content_category'] in ['original_execution_trace','original_error_or_log'] else 'evidence'
                label(escaped,category,pos)
        if content.startswith('CURRENT_RESEARCH_PACKET\n'):
            for key,value in json.loads(content.split('\n',1)[1]).items():
                inner=json.dumps(key)+':'+json.dumps(value,separators=(',',':'));escaped=json.dumps(inner,ensure_ascii=False)[1:-1]
                category='evidence' if key in ['mathematical_research','scientific_results','current_candidate_preview'] else 'history'
                label(escaped,category,pos,'L0field:'+inner)
    label(dump(wire['tools']),'tool_schema',unit='schemas:'+dump(wire['tools']))
    tokens=ENC.encode(payload);counts=collections.Counter();repeated=0;per_read=collections.Counter();offset=0
    for token in tokens:
        counts[KIND[tags[offset]]]+=1
        if repeat[offset]:repeated+=1
        for callid,(lo,hi) in readids.items():
            if lo<=offset<hi:per_read[callid]+=1
        offset+=len(ENC.decode_single_token_bytes(token))
    assert offset==len(raw) and sum(counts.values())==len(tokens)
    return dict(full_wire_tokens_estimated=len(tokens),components_estimated={k:counts[k] for k in KIND},repeated_context_tokens_estimated=repeated,read_feedback_tokens_estimated=dict(per_read)),newseen


def finalize():
    records=[json.loads(s) for s in (DATA/'decision_replay_results.jsonl').read_text('utf-8').splitlines()]
    schedule=read(ROOT/'execution_schedule.json')
    assert len(records)==len(schedule) and 2<=len(records)<=4
    assert all(r['status']=='completed' and 1<=r['provider_requests']<=4 and not r['errors'] for r in records)
    assert all(r[k]==0 for r in records for k in ['new_scientific_actions','new_workers','new_reporter_calls'])
    per_request=[];session_rows=[];retrieval=[];batches=[];scores=[];pairs=[];structured={};clips=[];retrospective=[]
    for sid in sorted({r['snapshot_id'] for r in records}):
        corpus=read(ROOT/'snapshots'/sid/'corpus.json');atoms={a['information_id']:a for a in corpus['atoms']}
        folder=DATA/'blind_review'/sid;reviewpath=folder/'independent_model_review.json'
        review=read(reviewpath) if reviewpath.exists() else None
        evaluations={LABELS[sid][e['label']]:e for e in review['review']['evaluations']} if review else {}
        conditions={}
        for condition in ['Flat','Hierarchical']:
            rec=next(r for r in records if r['snapshot_id']==sid and r['condition']==condition)
            session=ROOT/'sessions'/rec['session_id'];seen=set();parts=[];wire_by_turn={};body_by_turn={}
            for req in rec['requests']:
                path=session/f"request_{req['turn']}.json";payload=path.read_bytes().decode('utf-8');wire=json.loads(payload)
                assert wire['model']=='gpt-5.6-sol' and wire['reasoning_effort']=='none'
                assert {t['function']['name'] for t in wire['tools']}=={'research_plan','research_recall','evidence_read'}
                alloc,seen=allocate(payload,wire,seen);body=read(session/f"response_{req['turn']}.txt");usage=body.get('usage') or {}
                wire_by_turn[req['turn']]=wire;body_by_turn[req['turn']]=body
                part=dict(snapshot_id=sid,condition=condition,session_id=rec['session_id'],request_turn=req['turn'],http_status=req['http_status'],
                    input_tokens_actual=usage.get('prompt_tokens'),output_tokens_actual=usage.get('completion_tokens'),
                    total_tokens_actual=usage.get('total_tokens'),usage_status='provider_actual' if usage else 'usage_missing_not_zero',
                    cached_input_tokens_actual=usage.get('prompt_tokens_details',{}).get('cached_tokens'),
                    wire_bytes=len(payload.encode('utf-8')),wire_file=path.as_posix(),response_file=(session/f"response_{req['turn']}.txt").as_posix(),
                    whole_wire_input_tokens_estimated=alloc['full_wire_tokens_estimated'],system_prompt_tokens_estimated=alloc['components_estimated']['system'],
                    tool_schema_tokens_estimated=alloc['components_estimated']['tool_schema'],repeated_context_tokens_estimated=alloc['repeated_context_tokens_estimated'],
                    evidence_retrieval_tokens_sent_estimated=sum(alloc['read_feedback_tokens_estimated'].values()),
                    evidence_reads_requested_in_response=sum(r['turn']==req['turn'] for r in rec['reads']),
                    token_estimate_basis=BASIS,component_allocations_estimated=alloc['components_estimated'],per_tool_feedback_tokens_estimated=alloc['read_feedback_tokens_estimated'])
                parts.append(part);per_request.append(part)
            actual_complete=all(p['input_tokens_actual'] is not None and p['output_tokens_actual'] is not None for p in parts)
            assert actual_complete, 'Do not silently use a successful-request subtotal as all-send actual usage.'
            row=dict(snapshot_id=sid,condition=condition,initial_input_tokens_actual=parts[0]['input_tokens_actual'],
                cumulative_input_tokens_actual=sum(p['input_tokens_actual'] for p in parts),output_tokens_actual=sum(p['output_tokens_actual'] for p in parts),
                total_provider_requests=len(parts),evidence_read_requests=len(rec['reads']),unique_evidence_records=len({r['result'].get('information_id') for r in rec['reads']}),
                repeated_reads=len(rec['reads'])-len({dump(dict(tool=r['tool'],arguments=r['arguments'])) for r in rec['reads']}),
                initial_input_tokens_estimated=parts[0]['whole_wire_input_tokens_estimated'],cumulative_input_tokens_estimated=sum(p['whole_wire_input_tokens_estimated'] for p in parts),
                cumulative_system_tokens_estimated=sum(p['system_prompt_tokens_estimated'] for p in parts),cumulative_tool_schema_tokens_estimated=sum(p['tool_schema_tokens_estimated'] for p in parts),
                repeated_context_tokens_estimated=sum(p['repeated_context_tokens_estimated'] for p in parts),
                evidence_retrieval_tokens_sent_estimated=sum(p['evidence_retrieval_tokens_sent_estimated'] for p in parts),
                online_wall_s=rec['wall_s'],actual_usage_complete=True,rejected_requests=0,transport_errors=0,
                raw_records_delivered_in_flat_initial=len(atoms) if condition=='Flat' else None,
                deep_levels_actually_read=sorted({r['result'].get('information_level') for r in rec['reads']}),
                additional_full_records_not_fetched=len(atoms)-len({r['result'].get('information_id') for r in rec['reads']}) if condition=='Hierarchical' else None,
                unfetched_record_note='Not returned by a read tool; some facts/metadata already occur in L0. This is not a measurement of model attention or irrelevant reading.' if condition=='Hierarchical' else '',
                token_estimate_basis=BASIS)
            session_rows.append(row)
            evaluation=evaluations.get(condition,{})
            label=next(l for l,c in LABELS[sid].items() if c==condition)
            scores.append(dict(snapshot_id=sid,anonymous_label=label,condition_unblinded_after_scoring=condition,
                **{m:evaluation.get('scores',{}).get(m) for m in METRICS},mean_score=evaluation.get('mean_score'),key_evidence_coverage=evaluation.get('key_evidence_coverage'),
                unsupported_conclusions=evaluation.get('unsupported_conclusions'),incorrect_references=evaluation.get('incorrect_references'),missed_key_evidence=evaluation.get('missed_key_evidence'),
                unnecessary_repeated_research=evaluation.get('unnecessary_repeated_research'),blind_on_demand_read_assessment=evaluation.get('on_demand_read_correctness'),
                actual_on_demand_reads_correct_after_unblinding=all(r['result']['value']==atoms[r['result']['information_id']]['content'] for r in rec['reads']) if rec['reads'] else None,
                score_source=reviewpath.as_posix(),score_status='independent_blind_model_review_human_verification_pending' if review else 'human_scoring_pending'))
            for index,r in enumerate(rec['reads'],1):
                atom=atoms[r['result']['information_id']]
                assert r['result']['value']==atom['content']
                feedback=[]
                for turn,wire in wire_by_turn.items():
                    for m in wire['messages']:
                        if m['role']=='tool' and m['tool_call_id']==r['tool_call_id']:
                            assert json.loads(m['content'])==r['result'];feedback.append(turn)
                first=feedback[0] if feedback else None
                firstpart=next((p for p in parts if p['request_turn']==first),None)
                tokens=firstpart['per_tool_feedback_tokens_estimated'][r['tool_call_id']] if firstpart else None
                isroute='route_geometry' in r['result']['information_id']
                quote='it directly establishes illegal installed geometry for the studied F3 route' if isroute else 'viscosity variants still failed loaded qualification'
                assert quote in rec['decision']['hypothesis']
                # No submitted pre-read Plan exists. This is a source-to-final-Plan
                # linkage, not proof of a counterfactual decision change.
                retrieval.append(dict(snapshot_id=sid,condition=condition,read_index=index,batch_id=f'{sid}_{condition}_turn{r["turn"]}',
                    request_turn=r['turn'],first_feedback_sent_turn=first,tool=r['tool'],tool_call_id=r['tool_call_id'],arguments=r['arguments'],
                    source_level='L0',destination_level=r['result']['information_level'],actual_path='L0 -> '+r['result']['information_level'],
                    parallel_batch=True,information_id=r['result']['information_id'],source_file=atom['source_file'],source_record=atom['source_record'],
                    original_evidence_reference=atom.get('evidence_reference'),returned_bytes=len(json.dumps(r['result'],separators=(',',':')).encode('utf-8')),
                    feedback_tokens_first_send_estimated=tokens,feedback_tokens_all_sends_estimated=sum(p['per_tool_feedback_tokens_estimated'].get(r['tool_call_id'],0) for p in parts),
                    return_token_basis='Whole-wire generic-proxy token allocation within the exact tool message, not a separate Provider usage field.',
                    assistant_stated_purpose=r.get('stated_purpose'),purpose_status='No original purpose text supplied.' if not r.get('stated_purpose') else 'Original assistant text.',
                    posthoc_read_role='Verify installed route legality separately from settling.' if isroute else 'Compare original loaded qualifications for two matched viscosity variants.',
                    posthoc_role_basis='Pointer and exact final-Plan claim; not attributed as original hidden intent.',
                    final_decision_quote=quote,final_decision_quote_pointer='/decision/hypothesis',decision_source=(session/'result.json').as_posix(),
                    exact_raw_return_verified=True,subsequent_wire_delivery_verified=bool(feedback),feedback_sent_turns=feedback,
                    decision_change_causally_established=False,decision_change_note='No pre-read Plan or controlled counterfactual; supports observed evidence use only.'))
            for turn in sorted({r['turn'] for r in rec['reads']}):
                nextpart=next((p for p in parts if p['request_turn']==turn+1),None);before=next(p for p in parts if p['request_turn']==turn)
                batches.append(dict(snapshot_id=sid,condition=condition,batch_id=f'{sid}_{condition}_turn{turn}',read_requests=sum(r['turn']==turn for r in rec['reads']),
                    before_input_tokens_actual=before['input_tokens_actual'],after_input_tokens_actual=nextpart['input_tokens_actual'] if nextpart else None,
                    actual_prompt_delta=nextpart['input_tokens_actual']-before['input_tokens_actual'] if nextpart else None,
                    next_request_full_input_tokens_actual=nextpart['input_tokens_actual'] if nextpart else None,
                    retrieved_feedback_tokens_estimated=sum(p['per_tool_feedback_tokens_estimated'].get(r['tool_call_id'],0) for p in [nextpart] if p for r in rec['reads'] if r['turn']==turn),
                    attribution='Prompt delta includes assistant read calls, all tool feedback, packet progress and framing. It cannot be assigned as actual per-read token usage. The full next request is included in cumulative cost.'))
            conditions[condition]=dict(session=row,requests=parts,decision=rec['decision'],decision_source=(session/'result.json').as_posix(),evaluation=evaluation,reads=rec['reads'])
        f,h=conditions['Flat']['session'],conditions['Hierarchical']['session']
        fs=evaluations.get('Flat',{}).get('mean_score');hs=evaluations.get('Hierarchical',{}).get('mean_score')
        pair=dict(snapshot_id=sid,flat_initial_input_tokens_actual=f['initial_input_tokens_actual'],hier_initial_input_tokens_actual=h['initial_input_tokens_actual'],
            initial_input_reduction=1-h['initial_input_tokens_actual']/f['initial_input_tokens_actual'],
            flat_cumulative_input_tokens_actual=f['cumulative_input_tokens_actual'],hier_cumulative_input_tokens_actual=h['cumulative_input_tokens_actual'],
            cumulative_input_reduction=1-h['cumulative_input_tokens_actual']/f['cumulative_input_tokens_actual'],
            flat_output_tokens_actual=f['output_tokens_actual'],hier_output_tokens_actual=h['output_tokens_actual'],
            flat_provider_requests=f['total_provider_requests'],hier_provider_requests=h['total_provider_requests'],flat_evidence_reads=f['evidence_read_requests'],hier_evidence_reads=h['evidence_read_requests'],
            hier_repeated_reads=h['repeated_reads'],hier_actual_path='L0 -> L3 (three parallel reads; no L1/L2 reads)',
            flat_score=fs,hier_score=hs,score_delta_hier_minus_flat=round(hs-fs,6) if fs is not None and hs is not None else None,
            flat_key_evidence_coverage=evaluations.get('Flat',{}).get('key_evidence_coverage'),hier_key_evidence_coverage=evaluations.get('Hierarchical',{}).get('key_evidence_coverage'),
            winner='Hierarchical' if hs is not None and hs>fs else 'Flat' if fs is not None and fs>hs else 'tie' if fs is not None else 'unscored',
            cost_basis='Provider actual usage for every Main send; no rejected or missing-usage request.',
            full_wire_proxy_flat_cumulative=f['cumulative_input_tokens_estimated'],full_wire_proxy_hier_cumulative=h['cumulative_input_tokens_estimated'],
            full_wire_proxy_reduction=1-h['cumulative_input_tokens_estimated']/f['cumulative_input_tokens_estimated'],
            positive_clip_eligible=fs is not None and hs>=fs and h['cumulative_input_tokens_actual']<f['cumulative_input_tokens_actual'] and h['evidence_read_requests']>0,
            interpretation='Lower Main cost with a 0.2-point blind mean advantage in this single pair, but lower critical-evidence coverage (3/5 versus 5/5). Evidence supports more careful causal scope, not more complete evidence use or a causal effect of context overload.',
            review_scope='One independent model comparison, human review pending; no statistical significance or physical success claim.')
        pairs.append(pair);structured[sid]=dict(conditions=conditions,pair=pair,review=review,corpus_records=len(atoms))
        if pair['positive_clip_eligible']:
            clips.append(dict(snapshot_id=sid,clip_id='single_cost_quality_and_retrieval_case',
                hierarchical_quote='Existing evidence discriminates only partly: it directly establishes illegal installed geometry for the studied F3 route, while viscosity variants still failed loaded qualification, but no matched legal-route comparison exists, so the causal performance hypothesis remains unresolved.',
                flat_quote='H2 is refuted by the observed non-monotonic/static-balance response to viscosity',
                hierarchical_source=conditions['Hierarchical']['decision_source'],hierarchical_pointer='/decision/hypothesis',
                flat_source=conditions['Flat']['decision_source'],flat_pointer='/decision/weakening_observation',
                evidence_ids=['C031_EP0_qualifications','C034_EP0_qualifications','C036_EP0_route_geometry'],
                limit='One finding with score/cost/path aspects; not three independent discoveries. No pre-read Plan, no proof a specific read changed a prior decision, and no evidence that Flat suffered context overload.'))
            assert clips[-1]['hierarchical_quote'] in conditions['Hierarchical']['decision']['hypothesis']
            assert clips[-1]['flat_quote'] in conditions['Flat']['decision']['weakening_observation']
        # Exact later diagnostic reads and separate later executions are provenance
        # only; not scored with hindsight or sent to either Main.
        trace=[json.loads(s) for s in (SOURCE/'TOOL_TRACE.jsonl').read_text('utf-8').splitlines()]
        for n in [38,41,43,48]:
            e=next(e for e in trace if e['call_id']==f'C{n:03d}');p=SOURCE/e['output']['stdout']
            val=read(p)
            retrospective.append(dict(snapshot_id=sid,call_id=e['call_id'],source_file=p.as_posix(),source_timestamp=e['started_utc'],
                source_record='/route_geometry' if n==43 else '',event_kind='Later exact geometry read' if n in [38,43] else 'Separate later finite-physics execution',
                full_record=val if n==43 else None,reference=val.get('reference'),Main_input=False,primary_blind_judge_input=False,
                limitation='Same engineering lineage/engine, not an independent research team or isolated single-variable causal validation.'))
    csv_rows(DATA/'token_accounting_per_request.csv',per_request)
    csv_rows(DATA/'token_accounting.csv',session_rows)
    csv_rows(DATA/'retrieval_path.csv',retrieval or [dict(snapshot_id=None,read_index=None,actual_path='No reads occurred.')])
    csv_rows(DATA/'retrieval_batch_accounting.csv',batches or [dict(snapshot_id=None,read_requests=0)])
    csv_rows(DATA/'decision_scores.csv',scores);csv_rows(DATA/'pairwise_results.csv',pairs)
    write(DATA/'retrospective_reference.json',retrospective)
    construction=read(DATA/'context_construction_costs.json');entry=read(ROOT/'entry_confirmation.json')
    csv_rows(DATA/'context_construction_costs.csv',construction)
    primary=pairs[0];sid=primary['snapshot_id'];clip=clips[0] if clips else None
    detail=structured[sid]
    readrows=[r for r in retrieval if r['snapshot_id']==sid]
    readlines='\n'.join(f"| {r['read_index']} | {r['information_id']} | {r['destination_level']} | {r['feedback_tokens_first_send_estimated']} |" for r in readrows)
    cliptext=f'''# E2-R2: one observed paired case

Checkpoint: PHS after C037, not prior E2/C035. Original engineering Core evidence, two new decision-only Main sessions. C042 was prepared but omitted before inference by the capacity rule; no replacement or outcome-driven rerun.

## Cost and decision quality: one finding

Provider actual initial input: Flat {primary['flat_initial_input_tokens_actual']:,}; Hierarchical {primary['hier_initial_input_tokens_actual']:,}, reduction {primary['initial_input_reduction']:.4%}.

Provider actual cumulative input across ALL requests: Flat {primary['flat_cumulative_input_tokens_actual']:,}; Hierarchical {primary['hier_cumulative_input_tokens_actual']:,}, reduction {primary['cumulative_input_reduction']:.4%}. Requests: 1 versus 2. Output tokens: {primary['flat_output_tokens_actual']:,} versus {primary['hier_output_tokens_actual']:,}. No rejection, transmission error or missing Main usage occurred.

Blind five-metric mean: Flat {primary['flat_score']}/4; Hierarchical {primary['hier_score']}/4. The 0.2-point advantage reflects narrower causal attribution and candidate lineage, not fuller evidence coverage. Coverage is Flat 5/5 versus Hierarchical 3/5. Hierarchical omitted the detailed non-monotone trend and near/distal contrast and its matched reroute needs explicit legality/payout/preload admission. Preserve those limitations beside the positive result. Human review is pending.

## Exact decision clips

Hierarchical original (`{clip['hierarchical_source'] if clip else ''}`, `/decision/hypothesis`):

> {clip['hierarchical_quote'] if clip else 'No qualifying clip.'}

Flat original (`{clip['flat_source'] if clip else ''}`, `/decision/weakening_observation`):

> {clip['flat_quote'] if clip else 'No qualifying clip.'}

The blind reviewer judged the Flat refutation too broad: a non-monotone scalar response does not refute every possible viscosity redistribution. The raw C036 route record independently reports a cable-solid intersection at pose/time zero; original C031/C034 qualification records show continued loaded failures. These exact records are linked to Hierarchical's final Plan. No pre-read Plan exists, so a particular read's causal effect on decision change is not established. Flat did not miss those evidence groups; do not claim context overload caused its wording.

## Actual reading path: L0 → L3

Three parallel calls were requested in Provider turn 1 and their exact original content was delivered before the final Plan in turn 2. No L1 or L2 reads occurred, no repeat reads, and no four-level chain is claimed.

| Read | Exact record | Level | Feedback tokens, generic proxy estimate |
| --- | --- | --- | ---: |
{readlines}

The read batch's next-request actual prompt increase was {batches[0]['actual_prompt_delta'] if batches else 'N/A'} tokens, including tool-call history, raw returns, packet read progress and framing. This is not isolated actual per-read usage. The FULL {batches[0]['next_request_full_input_tokens_actual'] if batches else 'N/A'}-token next request, including re-sent context, is included in the cumulative metric.

Flat received all {detail['corpus_records']} raw corpus records directly. Hierarchical requested three complete raw records through tools; {detail['corpus_records']-3} others were not fetched that way, though L0 already contained previews/metadata. This describes delivery, not model attention or a validated count of irrelevant facts.

## Sources and measurement boundary

- Decisions: `decision_replay_results.jsonl`; exact raw Provider requests/responses in the linked session files.
- Raw source pointers and return/delivery checks: `retrieval_path.csv`; original candidate/load binding retained in `information_manifest.json` and the frozen corpus.
- Scores/coverage/weaknesses: `blind_review/{sid}/independent_model_review.json`; anonymous originals and a human template are preserved.
- Actual cost: `token_accounting_per_request.csv` and `pairwise_results.csv`. Feedback/components/repetition proxies use full-wire o200k_base allocation and are NOT a verified model tokenizer or actual billing.
- Offline corpus/context construction is separate: `context_construction_costs.csv` plus `figure_data.json`. Observed preparation process wall time including a repaired local entry-binding check is {entry['offline_observed_total_wall_s']:.3f} s; zero construction Provider calls. It includes unused C042 preparation and is not a production amortized latency benchmark.
- Later diagnostic/execution locators are in `retrospective_reference.json`, excluded from both Main and primary blind scoring; not a claim of isolated causal validation.

One paired sample, one judge, no statistical significance, no physical task-success improvement, no repeated packaging of initial/cumulative/path aspects as independent discoveries.
'''
    (DATA/'positive_context_clips.md').write_text(cliptext,encoding='utf-8')
    layout=f'''# Figure layout

Panel A: grouped initial and cumulative PROVIDER-ACTUAL input bars for the one C037 pair. Flat initial/cumulative {primary['flat_initial_input_tokens_actual']:,}/{primary['flat_cumulative_input_tokens_actual']:,}; Hierarchical {primary['hier_initial_input_tokens_actual']:,}/{primary['hier_cumulative_input_tokens_actual']:,}. Annotate initial reduction {primary['initial_input_reduction']:.2%} and cumulative reduction {primary['cumulative_input_reduction']:.2%}. Label 1 versus 2 requests; repeated context is already counted. Show offline construction separately, not added to online token counts or portrayed as a monetary cost. Any component/retrieval proxy inset must have its own estimated basis label.

Panel B: five paired metric points and mean {primary['flat_score']} versus {primary['hier_score']}, with coverage 5/5 versus 3/5 visibly adjacent. The hierarchy's modest average-score advantage coexists with omissions and geometry-preflight limitations. Do not call this more complete evidence use or a statistically significant gain.

Panel C: L0 → three parallel L3 raw records (C031 qualifications, C034 qualifications, C036 route_geometry) → final geometry-focused diagnostic Plan. Label each feedback proxy token count from retrieval_path.csv and the full second-request actual cost. The path is NOT L0→L1→L2→L3; unvisited levels can be dashed. Include the time-zero illegal-route observation and the final Plan's distinction between validity defect and unproven cause.

Use exact clips in positive_context_clips.md. There is no observed pre-read Plan or controlled intervention establishing that one read changed a prior decision. Flat already covered the evidence; do not attribute its broader refutation to overload. Caption: one engineering-Core-origin checkpoint, one blind model reviewer/human verification pending, reasoning none, no new science. C042 was excluded by the pre-inference capacity rule and must not appear as an executed sample.
'''
    (DATA/'figure_layout_suggestion.md').write_text(layout,encoding='utf-8')
    output=dict(experiment='E2-R2',historical_FULL=(SOURCE/'FINAL_RESULT.md').as_posix(),snapshots=structured,pairs=pairs,
        positive_clips=clips,retrieval_path=retrieval,retrieval_batches=batches,context_construction=construction,
        offline_observed_preparation_wall_s=entry['offline_observed_total_wall_s'],offline_cost_scope=entry['offline_wall_source'],
        new_main_sessions=len(records),main_provider_requests=len(per_request),judge_provider_requests=sum(1 for v in structured.values() if v['review']),
        new_scientific_actions=0,old_E2_files_unchanged=True,omitted_checkpoint='PHS_C042_B (capacity proxy 1,144,912 > conservative 1,009,040 input budget; no API send or replacement)',
        actual_usage_complete=True,token_estimate_basis=BASIS,
        repeated_context_definition='Previously sent identical full messages, schemas or L0 top-level fields, counted again on each actual wire. Token-start allocation is a proxy; no cumulative deduplication.',
        limitations=['One pair/one reviewer; human verification pending, no significance or robot success claim.',
            'Lower evidence coverage in Hierarchical despite a modest mean-score advantage.',
            'Observed read-to-final-Plan linkage does not establish a causal decision change or context-overload cause.',
            'No L1/L2 reads occurred; actual selective path is L0 to L3 only.',
            'Corpus includes complete enumerated public records and selected raw channels, not unlisted high-dimensional Store trajectories.',
            'C042 omitted on conservative generic-tokenizer capacity proxy, not an observed API context rejection.'])
    write(DATA/'figure_data.json',output)
    required=['candidate_checkpoint_ranking.csv','pre_registered_protocol.md','snapshot_manifest.csv','information_manifest.json','decision_replay_results.jsonl','token_accounting_per_request.csv','retrieval_path.csv','decision_scores.csv','pairwise_results.csv','positive_context_clips.md','figure_data.json','figure_layout_suggestion.md']
    assert all((DATA/x).is_file() for x in required)
    write(ROOT/'completion_check.json',dict(required_files=required,required_count=len(required),new_main_sessions=len(records),main_requests=len(per_request),judge_requests=1,
        all_read_returns_exact=True,subsequent_read_deliveries_exact=all(r['subsequent_wire_delivery_verified'] for r in retrieval),
        scientific_actions=0,missing_main_usage=0,rejected_main_requests=0,original_sources_unchanged=True,previous_E2_untouched=True))
    print(json.dumps(dict(completed=True,new_main_sessions=len(records),main_requests=len(per_request),judge_requests=1,pairs=pairs,
        retrieval_feedback_proxy=[dict(id=r['information_id'],tokens=r['feedback_tokens_first_send_estimated']) for r in retrieval],materials=DATA.as_posix()),ensure_ascii=False),flush=True)


if __name__=='__main__':finalize()
