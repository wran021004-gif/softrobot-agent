"""Explicit read-only historical replay; not a Main decision or study runner.

Usage: python -m tests.research.semantic_evidence_history ORIGINAL_STUDY OUTPUT
The output records interface coverage, never autonomous scientific success.
"""
from pathlib import Path
from contextlib import ExitStack
import argparse,hashlib,json
from unittest.mock import patch

from tools.platform_host import Host
from tools.research.core import read_tool_evidence,read_evidence
from tools.research.state import state
from tools.state_io import io_path


# Information needs manually attributed to the actual 22 original Main wires.
# These are regression cases, not model-generated hypotheses or action choices.
NEEDS=[['structure_parameters','structure'],['structure_parameters','mechanism_capabilities'],
    ['structure','task','research_history','research_opportunities'],['structure_parameters','reporter_explanations'],
    ['reporter_explanations','mechanism_capabilities','structure_parameters'],['reporter_explanations','mechanism_capabilities'],
    ['structure','mechanism_capabilities','structure_parameters'],['mechanism_capabilities','structure_parameters'],
    ['mechanism_capabilities'],['mechanism_capabilities'],['research_history','mechanism_capabilities'],
    ['mechanism_capabilities','structure_parameters'],['mechanism_capabilities','reporter_explanations'],
    ['mechanism_capabilities'],['structure_parameters','mechanism_capabilities'],['research_history','mechanism_capabilities'],
    [],[],['mechanism_capabilities','research_history'],
    ['mechanism_capabilities','structure_parameters','task','research_opportunities'],
    ['reporter_explanations','mechanism_capabilities'],['research_history','structure_parameters']]


def manifest(root):
    root=io_path(root)
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def replay(directory):
    directory=Path(directory);before=manifest(directory)
    h=Host(directory,directory.name,actor='read-only-interface-audit')
    connect=h.store.connect
    def readonly(required=False):
        if not required:raise AssertionError('ORIGINAL_STORE_WRITE_FORBIDDEN')
        return connect(True)
    h.store.connect=readonly
    result=[];pages_by_topic={}
    with ExitStack() as stack:
        for name in ('tools.service_execution._run_contained','mujoco.mj_step','tools.research.provider.credential'):
            stack.enter_context(patch(name,side_effect=AssertionError('NO_LIVE_EXECUTION')))
        stack.enter_context(h.store.read_snapshot())
        s=state(h);candidate=list(s['candidates'].values())[0]
        requests=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='r3_request']
        assert sum(r['purpose']=='conversation' for r in requests)==22
        assert sum(r['purpose']=='reporter' for r in requests)==4
        reporter_cases=[]
        for i,request in enumerate(requests,1):
            if request['purpose']!='reporter':continue
            wire=h.store.artifact(request['request']);payload=json.loads(wire['messages'][-1]['content'])
            reads=payload.get('selected_reads',[])
            reporter_cases.append(dict(provider_index=i,original_selected_reads=len(reads),
                unavailable_reads=sum(r.get('status')=='unavailable' for r in reads),
                original_raw_source_locations=len(payload.get('source_catalog',{})),
                semantic_information_needs=NEEDS[{4:2,7:4,10:6,24:19}[i]],new_reporter_requests=0))
        for topic in sorted({t for topics in NEEDS for t in topics}|{'mathematical_methods','mathematical_results','physical_results'}):
            q=dict(subject='reports' if topic=='reporter_explanations' else candidate,topic=topic)
            pages=[]
            while q:
                p=read_tool_evidence(h,q,record_read=False)
                assert p['status']=='available',p
                for source in p['sources']:read_evidence(h,source,record_read=False)
                pages.append(dict(items=len(p['facts']),content_identity=p['content_identity'],
                    source_count=len(p['sources']),formal_read_credit=p['formal_read_credit']))
                q=p.get('next_query')
                assert len(pages)<100
            pages_by_topic[topic]=pages
        # Explicit registered primitives/pages also reach the original passive
        # constraints; a category name is never guessed into a raw JSON key.
        q=dict(subject=candidate,topic='mechanism_capabilities',group='primitives');primitive_ids=[]
        while q:
            p=read_tool_evidence(h,q,record_read=False);primitive_ids.extend(p['facts']);q=p.get('next_query')
        assert 'constraint_length_residual' in primitive_ids
        for index,topics in enumerate(NEEDS,1):
            result.append(dict(main_index=index,topics=topics,interface_coverage='available' if topics else 'diagnose_not_an_evidence_query',
                first_page_queries=len(topics),all_page_queries=sum(len(pages_by_topic[t]) for t in topics),
                new_scientific_results=0,model_decision_replayed=False))
    assert manifest(directory)==before
    return dict(version='semantic_evidence_history_regression_v1',study_id=h.run_id,
        original_main_requests=22,original_reporter_requests=4,main_cases=result,reporter_cases=reporter_cases,topics=pages_by_topic,
        registered_passive_primitive_verified=True,all_raw_sources_readable=True,
        original_store_sdk_files_unchanged=len(before),new_provider_requests=0,new_workers=0,new_integrations=0,
        interpretation='Coverage of the same historical information needs; no claim about autonomous Main mathematics or design.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('original_study');parser.add_argument('output');args=parser.parse_args()
    value=replay(args.original_study)
    Path(args.output).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k not in ('main_cases','topics')}))
