"""Read-only replay of the P6-F report problem and M1 parameter registration.

Only saved JSON/SQLite evidence and metadata projections; no model or solver runs.
"""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock
from tools.platform_store import plain
from tools.research.config import ROOT
from tools.research.core import read_evidence
from tools.research.evidence_views import quantitative_facts,_resources
from tools.research import reporter
from schemas.research_reporting import ResultCard


def size(value):return len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())
def connect(path):return sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)


def report_audit():
    source=ROOT.parent/'p6-2f-scientific-information-repair/runs/research/p62f-luna-20261029/platform.sqlite'
    record=json.loads((ROOT/'docs/research/p62f_luna_results.json').read_text(encoding='utf8'))
    with connect(source) as db:
        def artifact(ref):return json.loads(db.execute('select body from artifacts where id=?',(plain(ref)['artifact_id'],)).fetchone()[0])
        event=json.loads(db.execute('select body from events where seq=96').fetchone()[0])
        handoff=artifact(event['outputs'][0]);s=artifact(handoff['source_state'])
        store=Mock();store.root=source.parent;store.artifact.side_effect=artifact
        store.session.return_value=dict(state=s)
        store.events.side_effect=lambda run:[json.loads(row[0]) for row in db.execute('select body from events where run_id=? and seq<=96 order by seq',(run,))]
        store.remaining.return_value=handoff['budget']
        store.connect.side_effect=ValueError('READ_ONLY_AUDIT_NO_EXTERNAL_LOG_RECONSTRUCTION')
        store.transaction.side_effect=AssertionError('READ_ONLY_NO_WRITES')
        store.reserve.side_effect=AssertionError('ZERO_PROVIDER_AND_SCIENCE')
        host=SimpleNamespace(store=store,run_id=record['study'])
        reference=record['reports'][-1]['reference'];before=deepcopy(s)
        full=read_evidence(host,dict(reference=reference,view='full'),record_read=False)
        compact=read_evidence(host,dict(reference=reference,view='summary'),record_read=False)
        constraints=0;failures=0
        for card in full['report']['results']:
            ref=card['identity']['result']['reference']
            finding=next(f for f in compact['findings'] if f['result_reference']==ref)
            for metric in card['metrics']:
                match=next(m for m in finding['metrics'] if m['name']==metric['name'])
                for field in ('value','threshold','passed','source','threshold_source'):
                    assert match[field]==metric[field],(metric['name'],field)
            constraints+=len(card['metrics']);failures+=sum(m['passed'] is False for m in card['metrics'])
            assert finding['quantitative_facts']==quantitative_facts(artifact(ref),ref)
            scope=next(r for r in compact['scope'] if r['result']==card['identity']['result'])
            for field in ('claim_kind','verification_status','supported_inferences'):
                assert scope[field]==card['evidence_summary'][field]
        text=read_evidence(host,compact['restore_query'],record_read=False)
        assert text==full['report']['interpretations']
        assert full==artifact(reference) and s==before
        physical=[ResultCard.model_validate(c) for c in full['report']['results'] if any(m['scope']=='physical_task' for m in c['metrics'])]
        physical=[c.model_copy(update=dict(resources=_resources(artifact(plain(c.identity.result.reference)),plain(c.identity.result.reference)))) for c in physical]
        _,changes=reporter._comparison(host,physical[0],physical[-1])
        resources=[r for r in changes if 'resource' in r]
        row=next(r for r in record['rows'] if r['sequence']==53)
        rejected=next(t['arguments'] for t in row['tool_calls'] if t['name']=='research_plan')
        return dict(source_store=str(source),source_study=record['study'],report_reference=reference,
            historical_state=handoff['source_state'],historical_handoff_event=96,
            original_full_read_event=99,original_rejected_plan_event=53,
            rejected_action=rejected['action'],rejected_method=rejected['decision']['selected_method'],
            rejected_selected_candidate=rejected['decision'].get('selected_candidate'),
            requested_budget=rejected['decision']['requested_budget'],
            original_max_main_input_tokens=record['efficiency']['main_max_input_tokens'],
            full_bytes=size(full),summary_bytes=size(compact),interpretations_bytes=size(text),
            summary_fraction=size(compact)/size(full),result_count=len(compact['findings']),
            original_metrics_preserved=constraints,failed_metrics_preserved=failures,
            quantitative_facts_equal=True,conclusion_scopes_equal=True,all_original_sources_retained=True,
            interpretation_non_authoritative=True,full_read_unchanged=True,formal_read_credit=False,
            resource_comparisons=resources,provider_requests=0,scientific_executions=0)


def parameter_audit():
    from extensions.tendon_family.family_space import parameter_capabilities
    trace=json.loads((ROOT/'memory/cases/m1_research_v1/success_trace.json').read_text(encoding='utf8'))
    identity=trace['source_identity']
    with connect(identity['original_store']) as db:
        s=json.loads(db.execute('select state from sessions where run_id=?',(identity['original_study_id'],)).fetchone()[0])
        def artifact(ref):return json.loads(db.execute('select body from artifacts where id=?',(ref['artifact_id'],)).fetchone()[0])
        selected=artifact(identity['selected'])
        assert selected['aggregation']['all_scheduled_accepted']
        candidate=selected['candidate']
        c=artifact(candidate)
        rows=parameter_capabilities(s['spec']['family_space'],c['parameters'])
        if isinstance(rows,dict):rows=rows['parameters']
        paths=['segments.0.length_m','segments.1.length_m']
        parameters=[]
        for path in paths:
            row=next(r for r in rows if r['parameter_id']==path)
            assert row['continuous_perturbation'] and row['effective_in_current_execution']
            parameters.append({k:row[k] for k in ('parameter_id','unit','minimum','maximum','domain_source','continuous_perturbation')})
        return dict(source_case='M1',source_study=identity['original_study_id'],
            candidate=candidate,candidate_owned_in_original_study=candidate in s['candidates'].values(),
            source_store=identity['original_store'],source_selected=identity['selected'],
            task_family=s['spec']['canonical_task']['family'],parameters=parameters,
            metric='best_found_J: maximum normalized signed task excess under fixed finite T1 budget',
            methods=['mujoco-nonlinear-task-capability-v1','mujoco-reoptimized-structure-response-v1'],
            no_new_parameter_samples=True,no_new_worker_or_gradient=True,
            scope='Declared continuous parameter domains only; perturbed candidates still require existing compilation/admission and fresh scientific authorization. No derivative or improved design is claimed.')


if __name__=='__main__':
    result=dict(report=report_audit(),minimum_problem=parameter_audit())
    output=ROOT/'docs/research/p62k_information_audit.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:v for k,v in result['report'].items() if k!='resource_comparisons'}))
    print(json.dumps(result['minimum_problem']))
