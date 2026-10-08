from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.platform_host import Host
from tools.research_investigations import InvestigationDispatcher,SourceFact
out=Path('evidence/research_mainline3_v1_complete_20261009');m=read(out/'validation_manifest.json');store=Store(Path(m['phases']['coordinated']['output']));state=store.session('mainline3-coordinated')['state'];node=state['investigations']['timing-integrity-limits'];report=store.artifact(node['result']);dispatcher=InvestigationDispatcher(Host(store.root,'mainline3-coordinated'))
exact=[]
for group in ('facts','counterevidence'):
 for i,f in enumerate(report[group]):
  dispatcher._validate_fact(SourceFact.model_validate(f),'RETURN')
  exact.append(dict(group=group,index=i,reference=f['reference'],pointer=f['pointer'],exact_value_type_identity=True))
source=m['historical_parent']['order']['evidence'][0];historical=read('runs/stage336_manual_20261001_090616/stage336_audit.json')['execution']['factual_result'];assert store.artifact(source)==historical
atomic_json(out/'timing_report.json',report)
atomic_json(out/'timing_material_audit.json',dict(version='coding_agent.material_audit@1.0.0',report=node['result'],formal_validity='pass',exact_source_bindings=exact,source_factual_result_unchanged=True,
 material_correctness='fail_for_unqualified_entire_report',
 supported=['Historical 35/35 misses, mean complete update 18.34727874570526 s vs 0.01 s; real_time_demonstrated=false','Valid complete recorded execution, zero solver errors and zero force violation','Recorded reach and sampled holding failures remain; one-step agreement does not replace task acceptance','No dominant physical cause or real-robot claim is established'],
 defects=[dict(location='/counterevidence/2/statement',issue='Says independent recomputation was not performed because recomputed_result=false. The stored Boolean is a failed recomputed threshold result, not a performed flag.',original_source_pointer='/holding/position/recomputed_result',implementation='tools/research_metric_view.py:57'),
 dict(location='/interpretation',issue='Extends availability and recomputed_result to /official although that object contains recorded_result, source and definition only.'),
 dict(location='/unknowns/3',issue='Treats whether recomputation happened as unresolved. The archived available result and metric-view construction identify an actually recomputed false result; the investigator did not itself rerun it.')],
 independent_review_method='Read saved model report, exact original source objects, untouched Stage336 factual result, and existing metric-view construction. No paid judge, provider request or scientific backend/analysis execution.',
 consequences='Do not adopt the report unqualified. Principal may adopt exact supported narrow observations, defer or reject; its actual decision remains separate. Missing reach report blocks full B and C.',
 historical_vs_current='All scientific numbers here belong to historical Stage336, not this activity or the unexecuted fixed C design.'))
for filename in ('research_mainline3_v1_completion.md','research_mainline3_v2_handoff.md'):
 p=Path('docs')/filename;dst=out/('previous_'+filename)
 if not dst.exists():dst.write_bytes(p.read_bytes())
print(dict(exact_bound_items=len(exact),report=node['result'],material='unqualified report fails'))
