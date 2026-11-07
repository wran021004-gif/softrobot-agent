"""Pure conditional mixed-coordinate moves; no Host, evidence, cost or worker ownership."""
from copy import deepcopy
from itertools import zip_longest
import math


def coupled_block(parameters, allowed_groups):
    """Reuse registry domains and the mathematics layer's four-point design."""
    from extensions.math_analysis.differentiation_router import matched_points
    if any(p.get('search_group') not in allowed_groups for p in parameters):
        raise ValueError('COUPLED_PARAMETER_OUTSIDE_FROZEN_SEARCH_GROUPS')
    return matched_points(parameters)


def interval(query, key, domain):
    bounds=query.bounds.get(key,(domain['minimum'],domain['maximum']))
    if None in bounds:raise ValueError('FINITE_SEARCH_BOUNDS_REQUIRED: '+key)
    return bounds


def default(query, key, domain, value=None):
    lo,hi=query.bounds.get(key,(domain['minimum'],domain['maximum']))
    value=domain['default'] if value is None else value
    return min(hi if hi is not None else value,max(lo if lo is not None else value,value))


def initial(space, query, previous=None):
    n=query.initial_segment_count or query.segment_counts[0];t=query.initial_tendon_count or query.tendon_counts[0]
    p=dict(segment_count=n,tendon_count=t,span_strategy=query.initial_span_strategy or query.span_strategies[0],segments={},routing={})
    return reshape(space,query,p,previous)


def candidate_seed(space, query, candidate):
    """Preserve the existing coordinate representation, or reject lossy seeding."""
    from extensions.tendon_family.family_space import resolved_request
    r=resolved_request(space,candidate['parameters']);n=r['segment_count'];t=r['tendon_count']
    if r.get('route_overrides') or r.get('tendon_parameters')!= {k:v['default'] for k,v in space['tendon_domains'].items()}:
        raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: route overrides or tendon parameters')
    expanded=[]
    for span in r['spans']:
        if (len(span['guide_s'])!=1 or span['guide_angle_offset_rad'] or span['anchor_angle_offset_rad']):
            raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: guide geometry')
        for j in range(span['count']):
            expanded.append(dict(first=span['first_segment'],last=span['last_segment'],radius=span['radius_m'],
                angle=span['phase_rad']+2*math.pi*j/span['count']+span['angular_offsets_rad'][j],
                guide=span['guide_s'][0],anchor=span['anchor_s']))
    patterns=dict(whole_chain=[(0,n-1)]*t,distal=[(n-1,n-1)]*t,
        base_to_distributed_anchors=[(0,j%n) for j in range(t)],
        distributed_consecutive=[(j%n,min(n-1,j%n+max(1,n//2))) for j in range(t)])
    strategy=next((k for k in query.span_strategies if patterns[k]==[(v['first'],v['last']) for v in expanded]),None)
    if strategy is None or len({(v['guide'],v['anchor']) for v in expanded})!=1:
        raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: span strategy or stations')
    defaults=resolved_request(space,dict(version='serial_family_generation_v2',family_space_identity=r['family_space_identity'],segment_count=n,tendon_count=t))
    segments={}
    passive=query.evaluation_mode.startswith('passive_')
    for i,v in r['segments'].items():
        rule=space['serial_assembly']
        prototype=next(c for c in space['assembly']['components'] if c['id']==rule['root_segment' if i=='0' else 'repeated_segment'])
        if v.get('interpolation',prototype['interpolation'])!=prototype['interpolation']:
            raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: segment interpolation')
        # Fixed prototype station rotations are reproduced by generation() and
        # checked separately below. They do not make uniform section dimensions
        # unrepresentable; arbitrary station shapes/rotations still reject.
        section_shape=lambda section:{k:item for k,item in section.items() if k!='angle_rad'}
        if (not passive and v.get('physical_parameters')!=defaults['segments'][i].get('physical_parameters')) or any(
                section_shape(s)!=section_shape(v['sections'][0]) for s in v['sections']):
            raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: station-dependent sections or extra physics')
        s=v['sections'][0]
        if [s.get('angle_rad',0) for s in v['sections']]!=[s.get('angle_rad',0) for s in defaults['segments'][i]['sections']]:raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: section rotation')
        segments[i]=dict(length_m=v['length_m'],young_pa=v['young_pa'],section_kind=s['kind'],section_dimensions=s['parameters'])
        if passive:segments[i].update(physical_parameters=v.get('physical_parameters',{}),cells=v['cells'])
        if s['kind']=='polygon':
            a=s['outer_yz_m'][1][0] if len(s['outer_yz_m'])==4 else None
            if a is None or a<=0 or s['outer_yz_m']!=[[-a,-a],[a,-a],[a,a],[-a,a]] or s['holes_yz_m']:
                raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: arbitrary polygon contours')
            segments[i]['polygon_scale_m']=a
    routing={k:v['default'] for k,v in space['routing_domains'].items()}
    phase=expanded[0]['angle']%(2*math.pi);routing.update(phase_rad=phase,guide_s=expanded[0]['guide'],anchor_s=expanded[0]['anchor'],radius_m=expanded[0]['radius'])
    return dict(segment_count=n,tendon_count=t,span_strategy=strategy,segments=segments,routing=routing,
        **(dict(payout_lengths_m=r['payout_lengths_m']) if passive else {}),
        radii_m=[v['radius'] for v in expanded],
        angular_offsets_rad=[(v['angle']-phase-2*math.pi*j/t+math.pi)%(2*math.pi)-math.pi for j,v in enumerate(expanded)])


def reshape(space, query, point, previous=None):
    p=deepcopy(point);old=previous or point
    prototypes={c['id']:c for c in space['assembly']['components']}
    rule=space['serial_assembly']
    p['segments']={}
    for i in range(p['segment_count']):
        d=space['segment_domains'].get(str(i),space['segment_domain'])
        proto=prototypes[rule['root_segment'] if i==0 else rule['repeated_segment']]
        prior=old.get('segments',{}).get(str(i),{})
        kinds=query.section_types or [proto['sections'][0]['section']['kind']]
        kind=prior.get('section_kind',kinds[0])
        if kind not in kinds:kind=kinds[0]
        values=dict(section_kind=kind,section_dimensions={})
        for k in ('length_m','young_pa'):
            values[k]=default(query,k,d[k],prior.get(k))
        for k,v in d['section_dimensions_m'][kind].items():
            values['section_dimensions'][k]=default(query,'section.'+kind+'.'+k,v,prior.get('section_dimensions',{}).get(k))
        if query.evaluation_mode.startswith('passive_'):
            values['physical_parameters']={k:prior.get('physical_parameters',{}).get(k,default(query,'physical.'+k,v))
                for k,v in d.get('physical_domains',{}).items()}
            values['cells']=prior.get('cells',rule['default_cells'])
        if kind=='polygon':
            v=d['polygon_coordinate_m']
            values['polygon_scale_m']=prior.get('polygon_scale_m',query.bounds.get('polygon_scale_m',(v['default'],))[0])
        p['segments'][str(i)]=values
    p['routing']={k:old.get('routing',{}).get(k,default(query,'routing.'+k,v)) for k,v in space['routing_domains'].items()}
    p['angular_offsets_rad']=(old.get('angular_offsets_rad',[])+[p['routing']['angular_offset_rad']]*p['tendon_count'])[:p['tendon_count']]
    p['radii_m']=(old.get('radii_m',[])+[p['routing']['radius_m']]*p['tendon_count'])[:p['tendon_count']]
    if query.evaluation_mode.startswith('passive_'):
        from extensions.tendon_family.family_space import payout_domains,parse_space
        domains=payout_domains(parse_space(space),p['tendon_count'])
        p['payout_lengths_m']=({k:old.get('payout_lengths_m',{}).get(k,default(query,'payout',v.model_dump())) for k,v in domains.items()}
            if not space.get('payout_initialization') or 'payout' in query.variable_groups else
            {k:v for k,v in old.get('payout_lengths_m',{}).items() if k in domains})
    return p


def generation(space, query, point):
    from extensions.tendon_family.family_space import span_strategies
    p=point;n=p['segment_count'];t=p['tendon_count'];r=p['routing']
    if p['span_strategy'] not in span_strategies(space):
        raise ValueError('SPAN_STRATEGY_NOT_APPLICABLE_TO_FROZEN_FAMILY_RULE')
    if p['span_strategy']=='whole_chain':
        groups=[(0,n-1,1,j) for j in range(t)]
    elif p['span_strategy']=='distal':
        groups=[(n-1,n-1,1,j) for j in range(t)]
    elif p['span_strategy']=='base_to_distributed_anchors':
        groups=[(0,j%n,1,j) for j in range(t)]
    else:
        groups=[(j%n,min(n-1,j%n+max(1,n//2)),1,j) for j in range(t)]
    spans=[]
    for first,last,count,j in groups:
        # A common phase is optimized; deterministic angular spacing separates channels.
        phase=(r['phase_rad']+2*math.pi*j/t)%(2*math.pi)
        spans.append(dict(first_segment=first,last_segment=last,count=count,phase_rad=phase,
            angular_offsets_rad=p['angular_offsets_rad'][j:j+count],radius_m=p['radii_m'][j],
            guide_s=[r['guide_s']],anchor_s=r['anchor_s']))
    request=dict(version='serial_family_generation_v2',family_space_identity=query.family_space_identity,
        segment_count=n,tendon_count=t,spans=spans,segments={},control_weights={k:v['default'] for k,v in space['control_domains'].items()})
    prototypes={c['id']:c for c in space['assembly']['components']};rule=space['serial_assembly']
    for i,v in p['segments'].items():
        proto=prototypes[rule['root_segment'] if i=='0' else rule['repeated_segment']]
        sections=[dict(st['section'],kind=v['section_kind'],parameters=v['section_dimensions']) for st in proto['sections']]
        for section in sections:
            section['outer_yz_m']=[];section['holes_yz_m']=[]
            if v['section_kind']=='polygon':
                a=v['polygon_scale_m']
                section['outer_yz_m']=[[-a,-a],[a,-a],[a,a],[-a,a]]
        request['segments'][i]=dict(length_m=v['length_m'],young_pa=v['young_pa'],sections=sections)
        if query.evaluation_mode.startswith('passive_'):
            request['segments'][i].update(physical_parameters=v['physical_parameters'],cells=v['cells'])
    if query.evaluation_mode.startswith('passive_'):
        if space.get('payout_initialization') and not p['payout_lengths_m']:
            from extensions.tendon_family.generated_serial import generate_family
            design,_,_=generate_family(dict(space=space,request=request))
            p['payout_lengths_m']=design['fixed_payout_lengths_m']
        request['payout_lengths_m']=p['payout_lengths_m']
    return request


def next_move(space, query, best, cursor, step):
    """Rebuild active coordinates from the incumbent, then take one bounded move."""
    groups={k:[] for k in query.variable_groups};p=deepcopy(best)
    choices={'segment_count':query.segment_counts,'tendon_count':query.tendon_counts,'span_strategy':query.span_strategies}
    for group,key in (('segment_count','segment_count'),('tendon_count','tendon_count'),('spans','span_strategy')):
        if group in groups and len(choices[key])>1:groups[group].append((key,None))
    for i,v in p['segments'].items():
        domain=space['segment_domains'].get(i,space['segment_domain'])
        for group,key in (('lengths','length_m'),('materials','young_pa')):
            if group in groups:groups[group].append((f'segments.{i}.{key}',(key,domain[key])))
        if 'sections' in groups:
            if len(query.section_types)>1:groups['sections'].append((f'segments.{i}.section_kind',None))
            for k,d in domain['section_dimensions_m'][v['section_kind']].items():
                groups['sections'].append((f'segments.{i}.section_dimensions.{k}',('section.'+v['section_kind']+'.'+k,d)))
            if v['section_kind']=='polygon':
                d=domain['polygon_coordinate_m'];scale=(dict(minimum=max(1e-5,d['maximum']/1000),maximum=min(-d['minimum'],d['maximum']),default=d['default']) if d['minimum'] is not None and d['maximum'] is not None else dict(minimum=0.,maximum=None,default=d['default']))
                groups['sections'].append((f'segments.{i}.polygon_scale_m',('polygon_scale_m',scale)))
        if query.evaluation_mode.startswith('passive_'):
            if 'materials' in groups:
                for k,d in domain.get('physical_domains',{}).items():
                    groups['materials'].append((f'segments.{i}.physical_parameters.{k}',('physical.'+k,d)))
    if 'payout' in groups:
        from extensions.tendon_family.family_space import payout_domains,parse_space
        for k,d in payout_domains(parse_space(space),p['tendon_count']).items():
            groups['payout'].append(('payout_lengths_m.'+k,('payout',d.model_dump())))
    if 'routing' in groups:
        for k in ('phase_rad','guide_s','anchor_s'):
            groups['routing'].append(('routing.'+k,('routing.'+k,space['routing_domains'][k])))
        for j in range(p['tendon_count']):
            groups['routing'].append(('angular_offsets_rad.'+str(j),('routing.angular_offset_rad',space['routing_domains']['angular_offset_rad'])))
            groups['routing'].append(('radii_m.'+str(j),('routing.radius_m',space['routing_domains']['radius_m'])))
    moves=[v for row in zip_longest(*groups.values()) for v in row if v is not None]
    if not moves:return None,[],step
    axis=cursor%len(moves);cycle=cursor//len(moves)
    direction=1 if cycle%2==0 else -1
    effective=step/(2**(cycle//2))
    path,domain=moves[axis];parts=path.split('.');parent=p
    for k in parts[:-1]:parent=parent[int(k)] if isinstance(parent,list) else parent[k]
    key=int(parts[-1]) if isinstance(parent,list) else parts[-1]
    if domain is None:
        values=query.section_types if parts[-1]=='section_kind' else choices[path]
        index=values.index(parent[key]);parent[key]=values[(index+direction)%len(values)]
        if parts[-1]=='section_kind':p['segments'][parts[1]]['section_dimensions']={}
        p=reshape(space,query,p)
    else:
        name,d=domain;lo,hi=interval(query,name,d)
        parent[key]=(math.exp(min(math.log(hi),max(math.log(lo),math.log(parent[key])+direction*effective*math.log(hi/lo))))
            if name=='payout' else min(hi,max(lo,parent[key]+direction*effective*(hi-lo))))
    return p,[path],effective
