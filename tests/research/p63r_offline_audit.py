"""Read-only audit of R0 projections and existing targeted test receipts."""
import ast,json,re,time
from pathlib import Path
from tools.platform_host import Host
from tools.research.state import state,science_hashes
from tools.research.feedback import scientific_result_delivery
from tools.research.config import ROOT

RUN='p63v1-m3-autonomous-feasibility-sol-20261030'


def main():
    h=Host(ROOT/'runs/research'/RUN,RUN,actor='r0-read-only-audit');before=state(h)
    assert before['pilot']['live_model_requests']==24 and len(before['analysis_results'])==94
    paths=('candidate','design_candidate','operation','implementation','status','model','protocol',
        'requested_operation.model_source','native_dynamics.cost','nonlinear_response.cost','native_progress.cost','native_diagnostic.cost')
    full_s=projection_s=0.
    for ref in before['analysis_results']:
        start=time.perf_counter();raw=h.store.artifact(ref);full_s+=time.perf_counter()-start
        start=time.perf_counter();projected=h.store.artifact(ref,paths=paths);projection_s+=time.perf_counter()-start
        expected={}
        for path in paths:
            value=raw;keys=path.split('.')
            for key in keys:
                if not isinstance(value,dict) or key not in value:break
                value=value[key]
            else:
                target=expected
                for key in keys[:-1]:target=target.setdefault(key,{})
                target[keys[-1]]=value
        assert projected==expected,ref
    start=time.perf_counter();delivery=scientific_result_delivery(h);summary_s=time.perf_counter()-start
    assert delivery['study_best_mathematical'][0]['fact']['J']==-.014355323230259676
    assert delivery['latest_search']['fixed_result']['best_mathematical'][0]['J']==-.0069635885347172355
    assert state(h)==before
    tests={}
    logs=['p63r_targeted_tests.log','p63r_intent_regressions.log','p63r_followup_tests.log',
        'p63r_final_projection_tests.log','p63r_knowledge_fixture_retest.log','p63r_last_unit_tests.log','p63r_materialization_test.log']
    for name in logs:
        path=ROOT/'runs'/name
        if not path.exists():continue
        text=path.read_text(encoding='utf-8-sig');entries=list(re.finditer(r'^test_\S+ \(([^)]+)\) \.\.\.',text,re.M))
        for i,entry in enumerate(entries):
            segment=text[entry.end():entries[i+1].start() if i+1<len(entries) else len(text)]
            identity=entry[1];module,cls,method=identity.rsplit('.',2);file=ROOT/(module.replace('.','/')+'.py')
            source=file.read_text(encoding='utf-8');tree=ast.parse(source)
            test=next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method)
            assertions=[ast.get_source_segment(source,n) for n in ast.walk(test) if isinstance(n,ast.Call)
                and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert')]
            tests[identity]=dict(result='passed' if re.search(r'\bok\s*$',segment,re.M) else 'failed',
                log='runs/'+name,input_source=str(file.relative_to(ROOT)),line=test.lineno,
                test_input_and_assertions=ast.get_source_segment(source,test),key_assertions=assertions)
    assert tests and all(t['result']=='passed' for t in tests.values()),[k for k,v in tests.items() if v['result']!='passed']
    base=ROOT.parent
    baseline=json.loads((base/'r_context_baseline_packet.json').read_text())
    optimized=json.loads((base/'r_context_optimized_packet.json').read_text());optimized['research'].pop('scientific_results',None)
    assert baseline==optimized
    result=dict(schema='p63r_offline_validation_v1',real_provider_requests=0,scientific_workers=0,
        live_store_unchanged=True,source_provider=24,source_math=94,source_profile=before['profile']['version'],
        science_hashes_unchanged=science_hashes()==before['profile']['science_hashes'],
        all_94_sparse_projections_equal_original_fields=True,old_packet_fields_identical=True,
        timings=dict(full_blob_decode_94_s=full_s,sparse_fields_94_s=projection_s,search_summary_s=summary_s,
            baseline_profiled_packet_s=604.1590125000221,warm_filtered_profiled_packet_s=270.52707089998876,
            optimized_profiled_packet_s=88.76369230001),
        tests=list(tests.values()),test_count=len(tests),
        stage_one_isolated_recovery=json.loads((ROOT/'runs/p63r_recovery_probe.json').read_text()),
        fixed_delivery=delivery,scope='Offline tests and read-only saved results, not a new scientific result or formal acceptance.')
    assert result['science_hashes_unchanged']
    (ROOT/'docs/research/p63r_offline_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,tests=len(tests),source_provider=24,projections=94,timings=result['timings'])),flush=True)


if __name__=='__main__':main()
