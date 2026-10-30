"""Read-only original V1 audit plus actual R2 wire delivery; never steer Main."""
import json,runpy,sqlite3,sys
from pathlib import Path
from tools.research.config import ROOT
repo=ROOT
original_audit=runpy.run_module('tests.research.p63v1_audit',run_name='__main__')
original_audit['db'].close()
del original_audit
a=json.loads((repo/'runs/p63v1_latest_audit.json').read_text(encoding='utf-8'))
database=repo/'runs/research/p63v1-m3-autonomous-feasibility-sol-20261030/platform.sqlite'
with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=30) as db:
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    def art(ref):return json.loads(db.execute('select body from artifacts where id=?',(ref['artifact_id'],)).fetchone()[0])
    delivered=[]
    for row in a['requests']:
        if row['purpose']!='conversation':continue
        wire=art(row['wire_reference'])
        p=next((json.loads(m['content'].split('\n',1)[1])['research'] for m in reversed(wire['messages'])
            if m['role']=='user' and isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')),None)
        if p is None:continue
        facts=p.get('scientific_results');cards=[]
        if facts:
            cards.extend((facts.get('latest_search') or {}).get('fixed_result',{}).get('best_mathematical',[]))
            cards.extend(x['fact'] for x in facts['study_best_mathematical'] if x.get('fact'))
        delivered.append(dict(provider=row['number'],response_confirmed=row.get('http_status')==200,wire_reference=row['wire_reference'],
            result_view_present=bool(facts),cards=[{k:r.get(k) for k in ('candidate','reference','control_source','J','metrics','status','profile_identity',
                'valid_complete','executable_under_current_profile','current_profile_requires_new_construction','independent_evaluation_executed','citation')} for r in cards],
            search_scope=(facts.get('latest_search') or {}).get('fixed_result',{}).get('search_scope') if facts else None,
            latest_search=(facts.get('latest_search') or {}).get('reference') if facts else None,
            latest_evaluation=facts.get('latest_evaluation') if facts else None,
            best_independent_physical=facts.get('best_independent_physical') if facts else None,
            retained_fields=[k for k in ('research_trace','tool_continuation','knowledge','budget','capabilities','research_focus','evidence_access','post_result_decision') if k in p],
            wire_body_bytes=row['input_bytes']))
    current=json.loads(db.execute('select state from sessions').fetchone()[0])
a.update(schema='p63r_same_study_live_audit_v1',r2_baseline_provider=24,r2_added_provider=a['provider']['total']-24,
    result_delivery_wires=delivered,profile=current['profile'],
    original_searches_retained=current['search_results'][:2]==[
        dict(artifact_id='a9aefb737296f7419f0e0aa22de7dd2df8e8c8b8fb20ebe0e8b3420dbae8686a',media_type='application/json'),
        dict(artifact_id='61251b64d479c7f9994fac52510f2800ebc6a78a6f8b9d9e4ebcb7e4499d43c5',media_type='application/json')])
(repo/'runs/p63r_latest_audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(r2_added=a['r2_added_provider'],profile=current['profile']['version'],
    new_delivered_wires=sum(r['provider']>24 and r['result_view_present'] and r['response_confirmed'] for r in delivered))),flush=True)
