"""Public research history projected from bound facts, never from prompt numbers."""
from tools.settling_campaign import campaign_metrics
from tools.state_io import digest
from extensions.tendon_family.candidate import candidate_facts


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
