"""Pure conditional mixed-coordinate moves; no Host, evidence, cost or worker ownership."""
from copy import deepcopy
from itertools import zip_longest
import math


def interval(query, key, domain):
    return query.bounds.get(key,(domain['minimum'],domain['maximum']))


def default(query, key, domain):
    lo,hi=interval(query,key,domain)
    return min(hi,max(lo,domain['default']))


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
    for i,v in r['segments'].items():
        if v.get('physical_parameters')!=defaults['segments'][i].get('physical_parameters') or len({str((s['kind'],s['parameters'])) for s in v['sections']})!=1:
            raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: station-dependent sections or extra physics')
        s=v['sections'][0]
        if [s.get('angle_rad',0) for s in v['sections']]!=[s.get('angle_rad',0) for s in defaults['segments'][i]['sections']]:raise ValueError('SEARCH_SEED_NOT_REPRESENTABLE_USE_GENERATE: section rotation')
        segments[i]=dict(length_m=v['length_m'],young_pa=v['young_pa'],section_kind=s['kind'],section_dimensions=s['parameters'])
    routing={k:v['default'] for k,v in space['routing_domains'].items()}
    phase=expanded[0]['angle']%(2*math.pi);routing.update(phase_rad=phase,guide_s=expanded[0]['guide'],anchor_s=expanded[0]['anchor'],radius_m=expanded[0]['radius'])
    return dict(segment_count=n,tendon_count=t,span_strategy=strategy,segments=segments,routing=routing,
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
            lo,hi=interval(query,k,d[k]);values[k]=min(hi,max(lo,prior.get(k,default(query,k,d[k]))))
        for k,v in d['section_dimensions_m'][kind].items():
            lo,hi=interval(query,'section.'+kind+'.'+k,v)
            values['section_dimensions'][k]=min(hi,max(lo,prior.get('section_dimensions',{}).get(k,default(query,'section.'+kind+'.'+k,v))))
        p['segments'][str(i)]=values
    p['routing']={k:old.get('routing',{}).get(k,default(query,'routing.'+k,v)) for k,v in space['routing_domains'].items()}
    p['angular_offsets_rad']=(old.get('angular_offsets_rad',[])+[p['routing']['angular_offset_rad']]*p['tendon_count'])[:p['tendon_count']]
    p['radii_m']=(old.get('radii_m',[])+[p['routing']['radius_m']]*p['tendon_count'])[:p['tendon_count']]
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
        request['segments'][i]=dict(length_m=v['length_m'],young_pa=v['young_pa'],sections=sections)
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
        parent[key]=min(hi,max(lo,parent[key]+direction*effective*(hi-lo)))
    return p,[path],effective
