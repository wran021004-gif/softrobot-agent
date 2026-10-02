"""Compact inventory computed from immutable execution files, never from prose."""
from tools.platform_store import plain


def evidence_inventory(reader, source):
    updates=reader.read_file(source,'controller_observations.json',[])
    motion=reader.read_file(source,'trajectory.json.gz',[])
    physics=reader.read_file(source,'resolved_physics.json')
    rows=[]
    for kind,key,units,view in [
        ('one_step_predictions','one_step_prediction','m; m/s','prediction'),
        ('applied_tensions','actual_tension_n','N','plans'),
        ('saved_projected_states','measured_initial_state','rad/m; rad/(m*s)','plans'),
        ('plan_selection','optimization_selected_iteration','iteration index','plans'),
        ('solver_status','optimization_raw_status','status string','plans')]:
        present=[(i,u) for i,u in enumerate(updates) if u.get(key) is not None]
        rows.append(dict(type=kind,reference=source['files']['controller_observations.json'],
            record_count=len(present),total_records=len(updates),
            time_coverage_s=[present[0][1]['time_s'],present[-1][1]['time_s']] if present else None,
            signals=[key],units=units,frame='world for tip vectors; projected GVS coordinates for state',
            timestamps='controller start time; prediction endpoint is next execution timestamp',
            query=dict(tool='diagnosis.inspect_evidence',view=view,update_ids='0..'+str(len(updates)-1),max_ids_per_query=8),
            raw_query=dict(tool='evidence.read',pointer='/{update_id}/'+key),
            coverage='complete retained record inventory; derived queries select samples',
            missing_update_ids=[i for i,u in enumerate(updates) if u.get(key) is None]))
    rows.append(dict(type='controller_horizon',reference=source['files']['controller_observations.json'],
        record_count=sum(u.get('effective_horizon') is not None for u in updates),total_records=len(updates),
        signals=['effective_horizon'],units='control intervals',
        query=dict(tool='diagnosis.inspect_evidence',view='plans'),
        raw_query=dict(tool='evidence.read',pointer='/{update_id}/effective_horizon'),
        coverage='Per-update effective horizon; configured horizon is in summary controller.parameters.data.recipe.horizon'))
    rows.append(dict(type='force_limits',reference=source['files']['resolved_physics.json'],
        record_count=len(physics['tendons']),signals=['entity','force_limit_n'],units='N',
        values=[dict(pointer=f'/tendons/{i}/force_limit_n',value=t['force_limit_n']) for i,t in enumerate(physics['tendons'])],
        query=dict(tool='evidence.read',pointer='/tendons'),coverage='complete channel list'))
    rows.append(dict(type='backend_motion',reference=source['files']['trajectory.json.gz'],record_count=len(motion),
        time_coverage_s=[motion[0]['time_s'],motion[-1]['time_s']],
        sample_times_s=[r['time_s'] for r in motion],
        signals=sorted(motion[0]),units='s; rad; rad/s; m',frame='world tip; serial backend joint coordinates',
        timestamps='sampled post-step execution times',query=dict(tool='diagnosis.inspect_evidence',view='motion'),
        raw_access='gzip bytes cannot be read as JSON via evidence.read; use the derived motion view',
        endpoint_query=dict(tool='diagnosis.inspect_evidence',view='prediction',update_ids='Chosen controller updates, at most 8 per query',
            meaning='Includes measured backend position/velocity at each matched next timestamp; controller-update time is different'),
        coverage='sampled trajectory; motion query displays final settling window',
        capability_gap='motion displays the final window; prediction can query other matched endpoint samples in batches. No continuous-time reconstruction or closed-loop counterfactual replay.'))
    snapshots='control_snapshots.json' in source['files']
    rows.append(dict(type='historical_full_plans',retained=snapshots,
        signals=['full_warm_plans','optimizer_iteration_traces'],
        coverage='control_snapshots.json present' if snapshots else 'control_snapshots.json not retained'))
    for row in rows:
        row['inventory_id']='source.'+row['type']
        row.setdefault('retained',row.get('record_count',0)>0)
    return dict(schema_version='2.0.0',execution_id=source['execution_id'],manifest=source['manifest'],entries=rows,
        missing_data=[] if snapshots else ['Full historical warm plans and optimizer iteration traces are not retained as control_snapshots.json.'],
        capability_gaps=['No closed-loop counterfactual replay or causal attribution tool. Full trajectories are not in every request.',
            'Existing numerical checks use a projected GVS state and bounded horizon, not a full backend replay.'],
        claim_policy='Use inventory plus your receipt ledger: not_displayed, not_read in this context, queried with stated coverage, not_retained, or retained_unavailable through a named capability. A sampled view or failed raw gzip read does not prove absence.')


def validate_gaps(gaps, inventory, ledger=None, displayed_handles=None):
    entries={row['inventory_id']:row for row in inventory['entries']}
    for gap in gaps:
        if gap.inventory_id is None:
            if not gap.source:raise ValueError('GAP_SOURCE_REQUIRED: name unlisted evidence and explicit basis')
            continue
        row=entries.get(gap.inventory_id)
        if row is None:raise ValueError('UNKNOWN_INVENTORY_ID: use a listed ID or source plus basis')
        if gap.status=='not_retained' and row['retained']:
            raise ValueError('GAP_CONTRADICTS_INVENTORY: '+gap.inventory_id+' is retained; use not_read or retained_unavailable and name the missing capability')
        if gap.status in ('not_read','queried','not_displayed','retained_unavailable') and not row['retained']:
            raise ValueError('GAP_CONTRADICTS_INVENTORY: '+gap.inventory_id+' is not retained')
        if ledger is not None:
            reads=[r for r in ledger if r['status']=='completed' and gap.inventory_id in r['inventory_ids']]
            scoped=gap.update_ids is not None or gap.time_range_s is not None
            all_requested_read=bool(reads)
            if gap.update_ids is not None:
                if gap.inventory_id=='source.backend_motion' or 'total_records' not in row:
                    raise ValueError('GAP_UPDATE_SCOPE_UNSUPPORTED: use update_ids only for controller update entries')
                requested=set(gap.update_ids)
                if max(requested)>=row['total_records']:raise ValueError('GAP_UPDATE_OUTSIDE_INVENTORY: choose retained update IDs')
                covered=set().union(*(set(r.get('coverage',{}).get('update_ids',[])) for r in reads if isinstance(r.get('coverage'),dict)))
                all_requested_read=requested<=covered
                reads=[r for r in reads if isinstance(r.get('coverage'),dict) and requested & set(r['coverage'].get('update_ids',[]))]
            elif gap.time_range_s is not None:
                if gap.inventory_id!='source.backend_motion':raise ValueError('GAP_TIME_SCOPE_UNSUPPORTED: time_range_s addresses sampled backend_motion')
                start,end=gap.time_range_s;bounds=row['time_coverage_s']
                if start<bounds[0]-1e-9 or end>bounds[1]+1e-9:raise ValueError('GAP_TIME_OUTSIDE_INVENTORY: choose a range inside retained sample coverage')
                requested=[t for t in row['sample_times_s'] if start-1e-9<=t<=end+1e-9]
                if not requested:raise ValueError('GAP_TIME_HAS_NO_RETAINED_SAMPLES: select a sampled time')
                def times(receipt):
                    coverage=receipt.get('coverage',{})
                    return coverage.get('sample_times_s',[]) if isinstance(coverage,dict) else []
                covered=[t for r in reads for t in times(r)]
                all_requested_read=all(any(abs(t-c)<1e-9 for c in covered) for t in requested)
                reads=[r for r in reads if any(start-1e-9<=t<=end+1e-9 for t in times(r))]
            if gap.status=='not_read' and reads:
                raise ValueError('GAP_CONTRADICTS_READ_LEDGER: '+gap.inventory_id+' includes queried coverage; use queried for the entry, or explicit update_ids/time_range_s for an unread subset')
            if gap.status=='queried' and (not reads or (scoped and not all_requested_read)):
                raise ValueError('GAP_WITHOUT_READ_RECEIPT: '+gap.inventory_id+'; use not_read or perform the supported query')
            if gap.status=='not_displayed' and any(set(r['handles']) & set(displayed_handles or []) for r in reads):
                raise ValueError('GAP_CONTENT_DISPLAYED: '+gap.inventory_id+' has facts currently displayed in the catalog; use queried and describe any missing coverage')
            if gap.status=='retained_unavailable' and not row.get('capability_gap'):
                raise ValueError('GAP_CAPABILITY_AVAILABLE: '+gap.inventory_id+' has supported access '+str(row.get('query'))+'; name genuinely unlisted evidence separately')
