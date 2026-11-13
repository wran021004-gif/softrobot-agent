from extract_full import *
bindings=read(O/'SOURCE_DATA/MODEL_BINDINGS.json');catalog={};reads={}
for tid,bb in bindings.items():
    d=Path(bb[0]['source_directory']);paths=[d/'STUDY_TRACE.jsonl']
    if tid=='T04':paths=[FIVE/'T04_figure_eight_tracking/STUDY_TRACE.jsonl',d/'STUDY_TRACE.jsonl']
    if tid=='T10':paths=[FIVE/'T10_M7_impact_recovery/STUDY_TRACE.jsonl',d/'STUDY_TRACE.jsonl']
    entries=[]
    for p in paths:
        if not p.exists():continue
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            r=json.loads(line)
            if r.get('kind')!='decision':continue
            a=r.get('exact_input',{}).get('arguments',{})
            entries.append(dict(event_id=r['event_id'],question=r.get('research_question',a.get('research_question')),rationale=r.get('decision_summary',a.get('rationale_summary')),
                selected_tool=a.get('selected_tool'),next_action=a.get('next_operation'),evidence=a.get('evidence'),source=str(p),timestamp=r.get('timestamp')))
    catalog[tid]=entries
    if (d/'ACTUAL_KNOWLEDGE_READS.json').exists():reads[tid]=read(d/'ACTUAL_KNOWLEDGE_READS.json')
dump('SOURCE_DATA/DECISION_CATALOG.json',catalog);dump('SOURCE_DATA/KNOWLEDGE_READS.json',reads)
for tid,rr in catalog.items():
    print('\nTASK',tid)
    for r in rr:
        if any(k in r['event_id'] for k in ['read-','bind-','seed-','select-','report-','qualify-','stop-','complete-member']):continue
        print(r['event_id'],r['selected_tool'],(r.get('rationale') or '')[:160])
