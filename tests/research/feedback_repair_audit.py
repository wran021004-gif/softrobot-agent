"""Read existing private evidence and export derived review artifacts outside it."""
from pathlib import Path
from types import SimpleNamespace
import json,time
from tools.platform_store import Store,plain
from tools.state_io import digest
from tools.research.feedback import diagnostic_task_gap
from tools.research.evidence_views import task_diagnosis,compact_task_diagnosis,result_card
from tools.research.research_context import trace_entry,mathematical_decision_view
from tests.research.test_diagnostic_feedback_repair import ROOT,STORE,REF


def main():
    started=time.perf_counter();host=SimpleNamespace(store=Store(STORE),run_id='passive-base-only-full-autonomous-study-20261108-02')
    out=ROOT/'docs/research/feedback-repair-p3-preparation-20261109'
    def write(name,value):(out/name).write_text(json.dumps(plain(value),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    db=STORE/'platform.sqlite';stat_before=(db.stat().st_size,db.stat().st_mtime_ns)
    before=digest(host.store.session(host.run_id)['state']);budget=host.store.remaining()
    # Export one actual original request, without decoding every historical wire
    # or retaining a snapshot's parsed copy of the 8 GB historical database.
    value=host.store.artifact(REF);original=digest(value)
    diagnostic=diagnostic_task_gap(value,REF);diagnosis=task_diagnosis(value,REF)
    manual=json.loads((ROOT/'docs/research/passive-study-review-20261109/result75-original-task-diagnostic.json').read_text())
    expected={r['name']:r['value'] for r in manual['diagnostic_measurements']}
    errors=[abs(row['observed_value']-expected[row['constraint_id'].removeprefix('evaluator:')]) for row in diagnostic['constraints']]
    assert len(errors)==251 and max(errors)<1e-14
    write('result75-readonly-regression.json',dict(source=REF,candidate=value['candidate'],
        diagnostic=diagnostic,summary=compact_task_diagnosis(diagnosis),
        qualification=value['structure_research']['baseline']['qualification_diagnosis'],
        formal_acceptance='unchanged invalid DYNAMIC_STAGE_NOT_QUALIFIED:loaded; no SELECT/Replay promotion',
        compared_metrics=len(errors),maximum_absolute_error=max(errors),result_hash_unchanged=digest(value)==original))
    use_id=value['operation_key'].removeprefix('native-').removesuffix('-analysis')
    event=next(e for e in host.store.events(host.run_id) if e['kind']=='model_original_tool_request' and
        host.store.artifact(e['outputs'][0],paths=('tool_use.toolUseId',))['tool_use']['toolUseId']==use_id)
    plan=host.store.artifact(value['plan_reference'])['original_plan']
    receipt=json.loads(host.store.lookup(host.run_id,value['operation_key'])['receipt'])
    row=dict(step=event['sequence'],action='research_analysis',method=value['operation'],candidate=value['candidate'],
        source=dict(reference=event['outputs'][0],pointer='/tool_use/input'),result_references=[REF],
        execution_status=receipt['execution_status'],execution_kind='scientific_result_recorded',outcome=dict(status=value['status']),
        agent_hypothesis=plan,receipt_output=receipt['output'])
    milestone=trace_entry(row,host)
    write('compact-memory-example.json',milestone)
    card=plain(result_card(host,REF))
    main_view=mathematical_decision_view(card)
    assert main_view['task_diagnosis']['diagnostic_status']=='complete'
    write('main-decision-example.json',dict(source=REF,projection='actual mathematical_decision_view(result_card) used by Main and Reporter',
        sent_to_provider=False,historical_main_read_claimed=False,decision_view=main_view))
    unchanged=(digest(host.store.session(host.run_id)['state'])==before and host.store.remaining()==budget
        and (db.stat().st_size,db.stat().st_mtime_ns)==stat_before)
    assert unchanged
    write('read-only-audit.json',dict(store_state_and_ledger_unchanged=unchanged,
        database_size_and_mtime_unchanged=True,source_result_hash_verified=True,
        physical_workers=0,mathematical_workers=0,integrations=0,provider_requests=0,replay_launches=0,
        new_p3_stores=0,original_study_status='paused_by_human; untouched',
        elapsed_s=time.perf_counter()-started,diagnostic_metrics=251,
        scientific_cost='No new scientific experiment. Local saved-data arithmetic and projections only.'))
    print(json.dumps(dict(status='passed',metrics=251,max_absolute_error=max(errors),
        readonly=unchanged,milestone_step=row['step'],elapsed_s=time.perf_counter()-started)))


if __name__=='__main__':main()
