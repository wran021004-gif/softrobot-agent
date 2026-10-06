"""Public research history projected from bound facts, never from prompt numbers."""
from tools.settling_campaign import campaign_metrics
from tools.state_io import digest
from extensions.tendon_family.candidate import candidate_facts


def execution_chronology(store, records):
    """Order this store's real attempts by reservation events, not presentation.

    latest_execution is the latest attempted simulation, including failures.
    latest_completed_evaluation is ordered by official evaluation completion;
    latest_complete_result additionally requires the retained full profile/facts.
    Imported history has no position in this campaign's local event sequence.
    """
    import json
    facts={}; builds={}
    for record in records:
        f=record.get('facts') or record.get('execution',{}).get('factual_result')
        if f:facts[f['execution_id']]=f
        if record.get('candidate_id'):builds[record['candidate_id']]=record
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
    reservations={e['event_id']:e for e in events}
    completions={(e['run_id'],e['execution_id']):e for e in events
                 if e['status'] in ('completed','failed','unknown') and e['parent_id']}
    attempts=[];missing=[];evaluated=[];complete=[]
    for call in calls:
        if json.loads(call['charged'])['backend_solves']==0:continue
        receipt=json.loads(call['receipt']) if call['receipt'] else None
        if receipt and (receipt['tool_id']!='simulation.run' or receipt.get('cache_hit')):continue
        start=reservations.get(call['parent_id']);eid=call['execution_id'];f=facts.get(eid)
        metadata=store.session(call['run_id'])['state'].get('result_executions',{}).get(eid,{})
        candidate=f['candidate'] if f else dict(candidate_id=metadata.get('candidate',call['run_id']),
            owner_run_id=call['run_id'],execution_id=eid,configuration=metadata.get('candidate_input'))
        if not start:missing.append(eid);continue
        attempts.append(dict(candidate=candidate,reservation_sequence=start['sequence'],
            reservation_event=start['event_id'],status=call['status'],
            configuration_binding='executed' if candidate['configuration'] else 'not retained yet'))
    by_id={r['candidate']['execution_id']:r for r in attempts}
    for call in calls:
        if not call['receipt']:continue
        r=json.loads(call['receipt'])
        if r['execution_status']!='completed' or not r.get('output'):continue
        if r['tool_id'] not in ('evaluation.run','control.profile_report'):continue
        value=store.artifact(r['output']);value=value.get('detail',value)
        eid=value.get('source_execution_id' if r['tool_id']=='evaluation.run' else 'execution_id')
        if eid not in by_id:continue
        end=completions.get((call['run_id'],call['execution_id']))
        if not end:missing.append(call['execution_id']);continue
        row=dict(candidate=by_id[eid]['candidate'],completion_sequence=end['sequence'],
            completion_event=end['event_id'],receipt=r['output'])
        if r['tool_id']=='evaluation.run':evaluated.append(row)
        elif eid in facts:complete.append(row)
    attempts.sort(key=lambda r:r['reservation_sequence'])
    evaluated.sort(key=lambda r:r['completion_sequence']);complete.sort(key=lambda r:r['completion_sequence'])
    return dict(scope='Real executions in this campaign store; imported records are historical evidence, not new attempts',
        ordering_authority='Store reservation and completion event sequence',attempts=attempts,
        latest_execution=attempts[-1]['candidate'] if attempts and not missing else None,
        latest_completed_evaluation=evaluated[-1]['candidate'] if evaluated and not missing else None,
        latest_complete_result=complete[-1]['candidate'] if complete and not missing else None,
        missing_chronology=missing,unordered_historical_executions=sorted(set(facts)-set(by_id)),
        semantics=dict(latest_execution='Latest attempted simulation by reservation event; may be failed/incomplete',
            latest_completed_evaluation='Latest official evaluation completion event; does not imply acceptance or complete profiling',
            latest_complete_result='Latest full profiled evaluation with retained bound facts, by profile completion event'))


def study_history(store, records, *, retained_baseline=None, selected_source=None,
                  latest_tested=None, selection=None):
    rows=[]; seen=set()
    for record in records:
        facts=record.get('facts'); candidate=(facts or {}).get('candidate') or record.get('candidate')
        if not candidate:raise ValueError('STUDY_CANDIDATE_IDENTITY_REQUIRED')
        key=(candidate.get('execution_id'), candidate['configuration']['artifact_id'])
        if key in seen:continue
        seen.add(key)
        configuration=store.artifact(candidate['configuration'])
        effective=configuration.get('effective',configuration)
        decisions=candidate_facts(effective,configuration,candidate['configuration'],candidate['candidate_id'])
        status=('completed_evaluation' if facts and facts.get('valid_complete_execution') else
                'attempted_incomplete' if candidate.get('execution_id') else 'proposed_unexecuted')
        recipe=effective['policy']['controller']['parameters']['data'].get('recipe',{})
        rows.append(dict(candidate=candidate,configuration_identity=digest(effective),status=status,
            decisions={r['path']:r['effective_value'] for r in decisions['parameters']},
            physical_structure=[dict(component=c['id'],length_m=c.get('length_m'),sections=c.get('sections'),physics=c.get('physics'))
                for c in effective['robot']['structure']['data']['components']],
            structure_identity=digest(effective['robot']),
            controller=effective['policy']['controller']['extension_id']+'@'+effective['policy']['controller']['version'],
            weights=dict(holding=recipe.get('holding_tip_speed_weight'),terminal=recipe.get('terminal_tip_speed_weight')),
            metrics=campaign_metrics(facts) if status=='completed_evaluation' else None,
            references=dict(source_store=record.get('source_store'),receipts=record.get('receipts'),
                configuration=candidate['configuration'],sources=(facts or {}).get('report'))))
    complete=[r for r in rows if r['status']=='completed_evaluation']
    branches={name:[r['candidate']['execution_id'] for r in complete if predicate(r['weights'])]
        for name,predicate in dict(zero_zero=lambda w:w['holding']==0 and w['terminal']==0,
            holding_only=lambda w:w['holding'] is not None and w['holding']>0 and w['terminal']==0,
            terminal_only=lambda w:w['terminal'] is not None and w['terminal']>0 and w['holding']==0,
            joint_positive=lambda w:all(w[k] is not None and w[k]>0 for k in ('holding','terminal'))).items()}
    return dict(rows=rows,tested_branches=branches,joint_positive_weight_tested=bool(branches['joint_positive']),
        identities=dict(retained_baseline=retained_baseline,selected_source=selected_source,
            latest_tested=latest_tested,selected_deliverable=selection),
        qualification='Completed evaluations, incomplete attempts and unexecuted proposals are distinct; physical failure is completed evidence.')


def select_source(records, requested, fallback=None):
    if requested is None:return fallback
    matches=[r['facts']['candidate'] for r in records if r.get('facts') and
             r['facts'].get('valid_complete_execution') and r['facts']['candidate']==requested]
    matches=list({digest(c):c for c in matches}.values())
    if len(matches)!=1:raise ValueError('PLAN_SOURCE_NOT_VERIFIED_COMPLETE_OR_AMBIGUOUS')
    return matches[0]


def reporting_summary(history, *, new_execution_ids, replication_pairs, selected, latest, usage, stop):
    """Compact bound reporting facts; explicit repeats never imply broad variance."""
    by_id={r['candidate']['execution_id']:r for r in history['rows'] if r.get('metrics')}
    fields=('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
    if len(set(new_execution_ids))!=len(new_execution_ids):raise ValueError('DUPLICATE_NEW_EXECUTION')
    if len({new for _,new in replication_pairs})!=len(replication_pairs):raise ValueError('DUPLICATE_REPLICATION')
    repetitions=[]
    for source,new in replication_pairs:
        a,b=by_id[source],by_id[new]
        if new not in new_execution_ids or source in new_execution_ids or source==new:
            raise ValueError('REPLICATION_SOURCE_NEW_BINDING')
        if a['structure_identity']!=b['structure_identity'] or a['weights']!=b['weights'] or a['controller']!=b['controller']:
            raise ValueError('REPLICATION_CONFIGURATION_MISMATCH')
        repetitions.append(dict(source=a['candidate'],new=b['candidate'],weights=b['weights'],
            measured_differences={k:b['metrics'][k]-a['metrics'][k] for k in fields},
            comparison_scope='Only the three retained aggregate metrics; not full trajectories or timing'))
    new=[by_id[e] for e in new_execution_ids]
    return dict(new_execution_count=len(new),novel_configuration_count=len(new)-len(repetitions),
        replication_count=len(repetitions),replications=repetitions,
        results=[dict(candidate=r['candidate'],weights=r['weights'],metrics=r['metrics'],
            structure_identity=r['structure_identity'],controller=r['controller'],decisions=r['decisions'],
            comparison_scope='new execution' if r['candidate']['execution_id'] in new_execution_ids else 'frozen historical')
            for r in by_id.values()],selected=selected,latest=latest,usage=usage,stop=stop,
        limits=['One matching repeat does not establish general repeatability, variance, identical trajectories or identical timing.',
                'Sampled acceptance does not establish a continuous-time guarantee, realtime, superiority or a unique physical cause.'])
