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
    n=query.segment_counts[0];t=query.tendon_counts[0]
    p=dict(segment_count=n,tendon_count=t,span_strategy=query.span_strategies[0],segments={},routing={})
    return reshape(space,query,p,previous)


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
    p=point;n=p['segment_count'];t=p['tendon_count'];r=p['routing']
    if p['span_strategy']=='whole_chain':
        groups=[(0,n-1,1,j) for j in range(t)]
    elif p['span_strategy']=='distal':
        groups=[(n-1,n-1,1,j) for j in range(t)]
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
    if query.method=='normalized_joint_block_v1':
        # A deterministic direction in dimensionless coordinates. Blocked axes
        # are omitted, then a single scale respects every remaining bound.
        cycle=cursor//2; effective=step/(2**(cycle//2))
        sign=1 if cursor%2==0 else -1
        active=[]
        for index,(path,domain) in enumerate(moves):
            if domain is None:continue
            parent=p;parts=path.split('.')
            for key in parts[:-1]:parent=parent[int(key)] if isinstance(parent,list) else parent[key]
            key=int(parts[-1]) if isinstance(parent,list) else parts[-1]
            name,d=domain;lo,hi=interval(query,name,d)
            direction=sign*(1 if (index+cycle)%2==0 else -1)
            room=(hi-parent[key])/(hi-lo) if direction>0 else (parent[key]-lo)/(hi-lo)
            if room>1e-12:active.append((path,parent,key,lo,hi,direction,room))
        if active:
            component=effective/math.sqrt(len(active))
            component=min(component,min(v[-1] for v in active))
            for _,parent,key,lo,hi,direction,_ in active:
                parent[key]+=direction*component*(hi-lo)
            return p,[v[0] for v in active],effective
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
