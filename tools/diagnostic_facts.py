"""Receipt-derived fact handles and context-local reading history.

Values are copied only from successful query results or explicit handoffs.
Selectors remain exact and private to the host; the catalog makes no claims.
"""
from copy import deepcopy
from tools.platform_store import plain, encode
from tools.state_io import digest


POLICY = dict(version='1.0.0', handle='f + first 12 SHA256 digits of project/binding/selector',
    scope='Current project, source binding, and context receipt or explicit handoff',
    values='Retrieved scalar leaves and short scalar vectors; no invented derived values',
    memory='Context-local full ledger; compact catalog, no trajectories or cross-role memory merge')


def leaves(value, path='', field='', update=None):
    if isinstance(value, dict):
        if set(value)=={'artifact_id','media_type'}:return
        update=value.get('update_id',update)
        for key,child in value.items():
            yield from leaves(child,path+'/'+key.replace('~','~0').replace('/','~1'),
                (field+'.' if field else '')+key,update)
    elif isinstance(value,list):
        if len(value)<=24 and all(isinstance(x,(int,float,bool)) for x in value) and value:
            yield path,field,value,update
        else:
            for i,child in enumerate(value):yield from leaves(child,path+'/'+str(i),field+'['+str(i)+']',update)
    elif value is not None and isinstance(value,(str,int,float,bool)) and not (isinstance(value,str) and len(value)>180):
        if field.split('.')[-1] not in ('execution_id','owner_run_id','snapshot_id'):
            yield path,field,value,update


def semantics(field):
    units=next((u for suffix,u in [('_rad_m_s','rad/(m*s)'),('_rad_m','rad/m'),('_m_s2','m/s^2'),('_m_s','m/s'),('_m','m'),('_s','s'),('_n','N')]
        if field.endswith(suffix)),None)
    meaning='As recorded in query; no causal interpretation'
    if 'time_s' in field or field.endswith(('start_s','end_s')):
        meaning=('prediction endpoint time' if 'prediction' in field or field.endswith('end_s') else
                 'controller-update start time' if 'updates[' in field or field.endswith('start_s') else 'sampled execution time')
        if 'trajectory[' in field:meaning='Local rollout offset from saved controller-update start; not absolute execution time'
    if 'effective_horizon' in field:units='control intervals';meaning='Controller update evidence, not backend motion'
    if any(s in field for s in ('position','velocity','tip','motion')):meaning+='; world frame for tip vectors'
    return units,meaning


def add_fact(state, selector, field, update=None):
    handle='f'+digest(dict(scope=state['fact_scope'],selector=selector))[:12]
    units,meaning=semantics(field)
    row=dict(handle=handle,field=field,value=selector['value'],units=units,meaning=meaning,selector=selector)
    if update is not None:row['update_id']=update
    catalog=state.setdefault('fact_catalog',{})
    if handle in catalog and catalog[handle]['selector']!=selector:raise ValueError('FACT_HANDLE_COLLISION')
    catalog.setdefault(handle,row)
    return handle


def catalog_value(state, reference, content, prefix='', field=''):
    return [add_fact(state,dict(reference=reference,pointer=prefix+p,value=v),f,u)
            for p,f,v,u in leaves(content,field=field)]


def record_read(host, invocation, receipt):
    if invocation.get('tool_id') not in ('evidence.read','diagnosis.inspect_evidence'):return
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state']
        if not state.get('fact_scope'):return
        ledger=state.setdefault('read_ledger',[])
        if any((r.get('execution_id'),r.get('request_id'))==(receipt['execution_id'],receipt['request_id']) for r in ledger):return
        args=invocation.get('arguments',{});role=state.get('role_context',{})
        row=dict(execution_id=receipt['execution_id'],request_id=receipt['request_id'],context=host.run_id,
            role=role.get('role','executor'),phase=role.get('phase'),method=invocation['tool_id'],
            view=args.get('view'),source=args.get('reference'),pointer=args.get('pointer'),
            result=receipt.get('output'),status=receipt['execution_status'],error=receipt.get('error'),
            handles=[],inventory_ids=[],coverage={},provenance='execution_receipt')
        if receipt['execution_status']=='completed' and receipt.get('output'):
            value=host.store.artifact(receipt['output'])
            if invocation['tool_id']=='evidence.read':
                row['coverage']={k:value[k] for k in ('pointer','offset','returned_items','total_items','kind')}
                if value['kind']=='content':
                    # Page-relative selectors cite the immutable result page, so list offsets cannot drift.
                    row['handles']=catalog_value(state,receipt['output'],value['content'],'/content',value['pointer'])
                inventory=role.get('inventory',{}).get('entries',[])
                row['inventory_ids']=[e['inventory_id'] for e in inventory if e.get('reference')==value['source'] and
                    (not value['pointer'] or any(s in value['pointer'] for s in e.get('signals',[])))]
                parts=value['pointer'].strip('/').split('/')
                if value['kind']=='content' and parts[0].isdigit():row['coverage']['update_ids']=[int(parts[0])]
            else:
                detail=value['detail'];obs=detail.get('evidence',{}).get('observations',{})
                row['coverage']['update_ids']=[r['update_id'] for r in obs.get('updates',[])]
                motion=detail.get('late_motion',[])
                sample_times=[m['time_s'] for m in motion] or [r['end_s'] for r in obs.get('aligned_intervals',[]) if r.get('measured_tip_m') is not None]
                if sample_times:row['coverage'].update(sample_count=len(sample_times),sample_times_s=sample_times,time_coverage_s=[min(sample_times),max(sample_times)])
                ids=dict(prediction=['one_step_predictions','backend_motion','applied_tensions','plan_selection','solver_status','controller_horizon'],plans=['applied_tensions','plan_selection','solver_status','controller_horizon'],motion=['backend_motion'])
                row['inventory_ids']=['source.'+x for x in ids.get(args['view'],[])]
                row['handles']=catalog_value(state,receipt['output'],value)
        ledger.append(row)
        if state.get('fact_scope'):
            from tools.diagnostic_revision import ensure_aliases
            ensure_aliases(state)
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'evidence_read_ledger',row['status'],outputs=[host.store.put(db,row)])


def handover(host, reference, content, *, origin, kind, selectors=None, inventory_ids=()):
    """An explicit transfer, never an implicit read of another role's memory."""
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state']
        if not state.get('fact_scope'):return
        identity=digest(dict(reference=reference,kind=kind,origin=origin))
        ledger=state.setdefault('read_ledger',[])
        if any(r.get('handoff_id')==identity for r in ledger):return
        handles=(catalog_value(state,reference,content) if selectors is None else
                 [add_fact(state,s,s['pointer'].strip('/').replace('/','.')) for s in selectors])
        row=dict(handoff_id=identity,context=host.run_id,role=state.get('role_context',{}).get('role'),
            method='explicit_handoff',view=kind,result=reference,status='completed',error=None,
            handles=handles,inventory_ids=list(inventory_ids),coverage='Only explicitly transferred content/selectors',
            provenance=origin)
        ledger.append(row)
        from tools.diagnostic_revision import ensure_aliases
        ensure_aliases(state)
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'evidence_handoff','transferred',inputs=[reference],outputs=[host.store.put(db,row)])


def context_view(state, *, max_catalog_bytes=75000, priority_handles=()):
    rows=[{k:v for k,v in row.items() if k!='selector'} for row in state.get('fact_catalog',{}).values()]
    # Catalog is bounded independently of trajectories. All mappings remain in the store.
    selected=[];size=0
    priority=set(priority_handles)
    ordered=[r for r in reversed(rows) if r['handle'] in priority]+[r for r in reversed(rows) if r['handle'] not in priority]
    for row in ordered:
        n=len(encode(row).encode())
        if size+n>max_catalog_bytes:continue
        selected.append(row);size+=n
    shown={r['handle'] for r in selected}
    ledger=[]
    for item in state.get('read_ledger',[]):
        r=deepcopy(item);r['displayed_handles']=[h for h in r['handles'] if h in shown]
        r['presentation']='explicitly_handed_over' if r['method']=='explicit_handoff' else ('displayed_catalog' if r['displayed_handles'] else 'available_by_reference')
        ledger.append(r)
    from tools.diagnostic_summary import read_coverage
    total=max((e.get('total_records',0) for e in state.get('role_context',{}).get('inventory',{}).get('entries',[]) if e.get('type')!='backend_motion'),default=0)
    return dict(fact_catalog=list(reversed(selected)),read_ledger=ledger,fact_catalog_policy=POLICY,
        queried_coverage=read_coverage({'current_context':state},total),
        additional_evidence='Use diagnosis.inspect_evidence views or evidence.read on JSON results. Compressed backend motion uses the motion view.')


def resolve_handles(state, selections):
    catalog=state.get('fact_catalog',{});resolved={}
    if not isinstance(selections,dict):raise ValueError('fact_handles must map each fact_id to a nonempty handle list')
    for fact_id,handles in selections.items():
        if not isinstance(handles,list) or not handles:raise ValueError('fact_handles.'+fact_id+': select at least one handle')
        resolved[fact_id]=[]
        for h in handles:
            if not isinstance(h,str) or h not in catalog:
                raise ValueError('UNKNOWN_OR_OUT_OF_SCOPE_FACT_HANDLE '+str(h)+': copy a handle from this context fact_catalog or query the needed evidence')
            resolved[fact_id].append(deepcopy(catalog[h]['selector']))
    return resolved
