"""Offline saved-wire projections; SQLite immutable reads, no Provider/worker API."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from tools.platform_store import Store,plain
from tools.research.research_context import (compact_intent, compact_action_trace,
    current_evidence_corrections, research_intent)
from tools.research.task_constraints import mathematical_method_view, mathematical_catalog
from tools.research.reporter import reporter_handoff_summary
from tokenizers import Tokenizer

ROOT=Path(__file__).resolve().parents[2]
SAMPLES=('87ce80cbc09643da967d107345631fcb','f8fb8f978ed846349da58ccfe0b165b5',
    '24dce98e120f4d3c8466553666b33fca','9dc07ec34fac4c679eb8fad553390358')


class FrozenStore(Store):
    """Test adapter enforcing immutable connections even for legacy read callers."""
    def connect(self,readonly=False):
        db=sqlite3.connect(self.db.as_uri()+'?mode=ro&immutable=1',uri=True)
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');return db

    @contextmanager
    def transaction(self):
        raise AssertionError('Offline comparison forbids Store writes')
        yield

    def session(self,run_id,db=None):
        return dict(state=deepcopy(self.snapshot)) if hasattr(self,'snapshot') else super().session(run_id,db)


def serial(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(directory,run_id):
    store=FrozenStore(directory);initial=sha(store.db)
    host=SimpleNamespace(store=store,run_id=run_id)
    final=store.session(run_id)['state'];events=store.events(run_id)
    tokenizer_path=ROOT/'configs/research/provider/deepseek_v4_tokenizer.json'
    tokenizer=Tokenizer.from_file(str(tokenizer_path))
    def size(value):
        text=serial(value)
        return dict(bytes=len(text.encode()),estimated_tokens=len(tokenizer.encode(text,add_special_tokens=False).ids))
    def segments(wire):
        packet=wire['messages'][-1];content=json.loads(packet['content'].split('\n',1)[1]);brief=content['research']
        return dict(total=size(wire),system=size([m for m in wire['messages'][:-1] if m['role']=='system']),
            sdk_history=size([m for m in wire['messages'][:-1] if m['role']!='system']),
            native_schemas=size(wire['tools']),packet=size(packet),
            sections={key:size(brief.get(key)) for key in ('action_trace','research_intent','mathematical_capabilities',
                'optimal_sensitivity_readiness','selected_mathematical_method','latest_reports',
                'recorded_evidence_corrections','additional_mathematical_evidence')})
    responses={e['request_id']:store.artifact(e['outputs'][0]) for e in events if e['kind']=='r3_response'}
    results=[]
    for event in events:
        if event['kind']!='r3_request' or event['request_id'].removeprefix('r3-request-') not in SAMPLES:continue
        metadata=store.artifact(event['outputs'][0]);original=store.artifact(metadata['request'])
        packet=json.loads(original['messages'][-1]['content'].split('\n',1)[1]);brief=packet['research']
        # The historical packet stays authoritative for facts/actions/budgets.
        # Rebuild only method descriptions at its candidate/profile/implementation.
        store.snapshot=deepcopy(final)
        store.snapshot.update(freeze=packet['implementation'],profile=packet['evaluation_profile'],
            research_status='stopped' if not brief.get('actions') else 'ready')
        emitted={r['artifact_id'] for e in events if e['sequence']<event['sequence'] for r in e['outputs']}
        for key in ('analysis_results','mechanics_results','plans'):
            store.snapshot[key]=[r for r in final.get(key,[]) if r['artifact_id'] in emitted]
        remaining=brief['mathematical_capabilities'][-1].get('remaining_evaluations')
        if remaining is not None:store.snapshot['mathematical_evaluations']=final['spec']['budgets']['mathematical_evaluations']-remaining
        current=deepcopy(packet);correction=store.snapshot['engineering_feedback_correction']
        current['research']['recorded_evidence_corrections']=current_evidence_corrections(store.artifact(correction),correction)
        changed=deepcopy(current);new=changed['research']
        new['action_trace']=compact_action_trace(brief['action_trace'])
        intent=research_intent(host);latest=intent['latest_decision']
        assert latest['plan_reference']==brief['research_intent']['latest_decision']['plan_reference']
        assert latest['agent_hypothesis']==brief['research_intent']['latest_decision']['agent_hypothesis']
        new['research_intent']=compact_intent(intent)
        candidate=next((r['candidate'] for r in (latest,intent['last_research']) if r and r.get('candidate')),None)
        candidate=candidate or (brief.get('latest_scientific_feedback') or {}).get('candidate')
        if candidate:
            view=mathematical_method_view(host,candidate)
            new['mathematical_capabilities']=mathematical_catalog(view)
            new.pop('optimal_sensitivity_readiness',None)
            selected=(latest['agent_hypothesis'].get('decision') or {}).get('selected_method')
            if selected in view['methods']:new['selected_mathematical_method']=view['methods'][selected]
        for i,report in enumerate(brief['latest_reports']):
            ref=report['report_reference']
            new['latest_reports'][i]=reporter_handoff_summary(host,ref,store.artifact(ref))
        def wire(p):
            w=deepcopy(original);w['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+serial(p);return w
        baseline=wire(current);projected=wire(changed)
        assert projected['tools']==original['tools']
        assert projected['messages'][:-1]==original['messages'][:-1]
        for key in ('budget','actions','task','task_identity','task_accepted','available_research_actions'):
            assert new.get(key)==brief.get(key)
        assert new['recorded_evidence_corrections']==current['research']['recorded_evidence_corrections']
        assert len(new['action_trace']['recent'])==len(brief['action_trace']['recent'])
        for old,row in zip(brief['action_trace']['recent'],new['action_trace']['recent']):
            for key in ('source','result_references','receipt_output','execution_status','outcome'):assert row.get(key)==old.get(key)
        for report in new['latest_reports']:
            for fact in report['findings']:
                raw=store.artifact(fact['result']['reference'])
                expected={k for k,v in (raw.get('acceptance') or {}).get('components',{}).items() if type(v.get('value')) in (int,float)}
                assert expected <= {m['name'] for m in fact['metrics']}
        results.append(dict(request_id=event['request_id'],wire_reference=metadata['request'],
            original=segments(original),current_S132_correction_baseline=segments(baseline),s134=segments(projected),
            historical_provider_usage=responses.get(event['request_id'],{}).get('usage'),
            bound_candidate=candidate,schemas_history_unchanged=True,
            current_hypothesis=latest['agent_hypothesis'].get('decision',{}).get('hypothesis_id'),
            source_fact_checks='trace refs/status/outcome preserved; every numeric acceptance component in L1',
            scientific_decision_quality='not measured; no Provider request'))
    assert len(results)==4
    assert sha(store.db)==initial
    return dict(scope='Static archived-wire comparison; only listed packet sections replaced. Not a replay of historical model decisions.',
        source_db_sha256=initial,source_unchanged=True,tokenizer_sha256=sha(tokenizer_path),
        new_provider_requests=0,new_scientific_executions=0,requests=results,
        caveat='Local JSON token estimates exclude the Provider chat template; independent section token counts are not additive. Historical actual usage is unchanged; no realized saving or quality gain claimed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',type=Path,required=True);parser.add_argument('--run-id',default='f3-autonomous-20261022-01')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=compare(args.store,args.run_id)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in result['requests']:print(row['request_id'],row['original']['total'],row['s134']['total'])
