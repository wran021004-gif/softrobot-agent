"""Source-bound arithmetic over retained updates and context-local read records."""
from collections import defaultdict


def update_facts(reader, source, update_ids=None):
    updates=reader.read_file(source,'controller_observations.json',[])
    ids=list(range(len(updates))) if update_ids is None else sorted(set(update_ids))
    if any(i<0 or i>=len(updates) for i in ids):raise ValueError('SUMMARY_UPDATE_NOT_RETAINED')
    raw=defaultdict(list);policy=defaultdict(list);iterations=defaultdict(list)
    for i in ids:
        row=updates[i];raw[str(row.get('optimization_raw_status'))].append(i)
        policy[str(row.get('policy_stop_reason'))].append(i)
        n=row.get('optimization_selected_iteration')
        kind='iteration_zero' if n==0 else 'synthetic_initialization' if n==-1 else 'positive_iteration' if n is not None and n>0 else 'unavailable'
        iterations[kind].append(i)
    def counts(groups):return {k:dict(count=len(v),update_ids=v) for k,v in sorted(groups.items())}
    physics=reader.read_file(source,'resolved_physics.json')
    channels=[]
    for j,tendon in enumerate(physics['tendons']):
        limit=tendon['force_limit_n'];series={}
        for label,key in [('requested_input','requested_tension_n'),('applied_input_backend_readback','actual_tension_n')]:
            values=[dict(update_id=i,value_n=updates[i][key][j],distance_to_upper_bound_n=limit-updates[i][key][j],
                         upper_bound_violation_n=max(0.,updates[i][key][j]-limit),lower_bound_violation_n=max(0.,-updates[i][key][j]))
                    for i in ids if updates[i].get(key) is not None]
            margin=min((v['distance_to_upper_bound_n'] for v in values),default=None)
            series[label]=dict(minimum_distance_to_upper_bound_n=margin,
                minimum_distance_update_ids=[v['update_id'] for v in values if v['distance_to_upper_bound_n']==margin],
                queried_update_ids=[v['update_id'] for v in values],
                maximum_bound_violation_n=max((max(v['upper_bound_violation_n'],v['lower_bound_violation_n']) for v in values),default=None))
        channels.append(dict(channel=tendon['entity'],channel_index=j,upper_bound_n=limit,**series))
    return dict(execution_id=source['execution_id'],configuration=source['metadata']['candidate_input'],manifest=source['manifest'],
        sources={k:source['files'][k] for k in ('controller_observations.json','resolved_physics.json','actual_commands.json')},
        scope=dict(update_ids=ids,total_retained_updates=len(updates)),raw_optimizer_termination=counts(raw),
        controller_policy_stop=counts(policy),selected_iterations=counts(iterations),tension_channels=channels,
        input_semantics=dict(requested_input='Controller requested command from requested_tension_n.',
            applied_input_backend_readback='actual_tension_n: MuJoCo -actuator_force readback at the pre-step update boundary; simulated force, not hardware measurement.',
            backend_motion='Recorded serial backend q/qdot and tip position are distinct from input commands.',
            bounds='Distance to upper bound and actual violation are separate quantities. Legal near-bound tension need not violate a bound.'),
        interpretation='Counts cover exactly listed update IDs. Observations do not identify a dominant cause or establish ineffectiveness throughout a parameter range.')


def read_coverage(states, total_updates):
    """Merge successful read receipts; explicit transfers never imply private reads."""
    contexts=[];shared=set()
    for context,state in states.items():
        groups=defaultdict(set);unique=set();receipts=[]
        for row in state.get('read_ledger',[]):
            coverage=row.get('coverage')
            if row.get('status')!='completed' or not isinstance(coverage,dict):continue
            ids=set(coverage.get('update_ids',[]))
            if not ids:continue
            unique.update(ids);groups[(row.get('role'),row.get('view'),row.get('method'))].update(ids)
            receipts.append(dict(request_id=row.get('request_id'),result=row.get('result'),update_ids=sorted(ids)))
        shared.update(unique)
        contexts.append(dict(context=context,views=[dict(role=k[0],view=k[1],method=k[2],update_ids=sorted(v),count=len(v)) for k,v in groups.items()],
            unique_update_ids=sorted(unique),queried_count=len(unique),unread_update_ids=sorted(set(range(total_updates))-unique),sources=receipts))
    return dict(contexts=contexts,shared_workflow=dict(unique_update_ids=sorted(shared),queried_count=len(shared),
        unread_update_ids=sorted(set(range(total_updates))-shared)),
        scope='Union of successful retained query/read receipts in the supplied workflow. Each context has its own coverage; shared union does not mean any role read another role private context. Explicit handoffs are excluded from queried coverage.')
