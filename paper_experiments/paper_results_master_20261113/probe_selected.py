from extract_full import *
b=read(O/'SOURCE_DATA/MODEL_BINDINGS.json');v=b['T10'][0];c=db(v['store']);r=get(c,v['result_ref']);s=get(c,r['profile']['simulation']);print('SIMDAT',[(k, type(x).__name__,len(x) if isinstance(x,(list,dict)) else str(x)[:90]) for k,x in s['data']['data'].items()]);p=get(c,r['profile']['native_feedback_preparation']);print('PREPKEYS',list(p));print('PREPCOST',p.get('cost'),p.get('resources'))
owner=r['execution']['completion_stages']['simulation']['source_owner'];sd=Path(v['store']).parent/'executions'/owner;print('OWNER',sd,[(x.name,x.is_dir()) for x in sd.iterdir()][:15]);c.close()
for k in ['T02','T03','T04','T05','T06','T08','T09','T10']:
    rr=next(x for x in read(O/'SOURCE_DATA/FULL_TASKS.json') if x['task_id']==k)
    metrics=rr['primary_metrics'];print('METRIC',k, {case:{a:v for a,v in vs.items() if any(x in a for x in ['position','axis','tracking','rmse','error','recovery','stiffness','depth','release','force','low','high'])} for case,vs in metrics.items()})
