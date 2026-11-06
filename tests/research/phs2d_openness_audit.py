"""Read-only live evidence and geometric audit; no Provider sends or dynamics."""
import json
from copy import deepcopy
from pathlib import Path
import subprocess
from jsonschema import Draft202012Validator
from tools.platform_host import Host
from tools.research.state import state
from tools.state_io import atomic_json, digest
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.geometry import geometry
from extensions.tendon_family.family_space import parameter_capabilities


def audit():
    root=Path(__file__).resolve().parents[2]
    h=Host(root/'runs/research/phs2d-topology-successor-20261106','phs2d-topology-successor-20261106')
    s=state(h); spec=s['spec']; space=spec['family_space']; events=h.store.events(h.run_id)
    with h.store.connect(True) as db:
        unsettled=db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]
    requests=[]
    for event in events:
        if event['kind']!='r3_request':continue
        meta=h.store.artifact(event['outputs'][0])
        if meta.get('purpose')!='conversation':continue
        wire=h.store.artifact(meta['request'])
        packets=[json.loads(m['content'].split('\n',1)[1]) for m in wire['messages']
            if isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')]
        packet=packets[-1] if packets else {}; research=packet.get('research',{})
        serialized=json.dumps(packet)
        for tool in wire.get('tools',[]):
            Draft202012Validator.check_schema(tool['function']['parameters'])
        requests.append(dict(sequence=event['sequence'],request_id=event['request_id'],
            packet_count=len(packets),packet_bytes=len(serialized.encode()),packet_keys=list(packet),
            research_keys=list(research),tool_names=[t['function']['name'] for t in wire.get('tools',[])],
            knowledge=research.get('knowledge'),capabilities=research.get('capabilities'),
            provider_schemas_valid=True,
            field_bytes={k:len(json.dumps(v).encode()) for k,v in research.items()},
            expert_process_in_request='Early research could not qualify its unloaded baseline' in json.dumps(wire),
            full_family_assembly_in_packet='assembly' in research.get('family_space',{})))
    cases=[]
    domain=space['passive_payout_domain_m']
    for n,t,last in ((1,1,0),(1,12,0),(5,6,4),(9,4,8),(9,12,8),(9,1,0)):
        for extent in ('minimum','default','maximum'):
            q=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                segment_count=n,tendon_count=t,spans=[dict(first_segment=0,last_segment=last,count=t)],
                segments={str(i):dict(length_m=space.get('segment_domains',{}).get(str(i),space['segment_domain'])['length_m'][extent]) for i in range(n)})
            row=dict(segments=n,tendons=t,anchor_segment=last,length_selection=extent)
            try:
                _,_,physics=generate_family(dict(space=space,request=q))
                lengths=geometry(physics,[0.]*len(physics['dofs']))['lengths'].tolist()
                row.update(generated=True,lengths_m=lengths,
                    outside_payout_domain=any(not domain['minimum']<=x<=domain['maximum'] for x in lengths))
            except Exception as exc:row.update(generated=False,reason=str(exc))
            cases.append(row)
    q=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=9,tendon_count=4)
    catalog=parameter_capabilities(space,q)
    extensions=[]
    # Disposable in-memory engineering proposals, never written into live spec.
    for kind in ('density_curvature','polygon','nonbase_start','mesh4','mesh16'):
        proposal=deepcopy(space)
        request=dict(version='serial_family_generation_v2',segment_count=2,tendon_count=1)
        if kind=='density_curvature':
            for d in [proposal['segment_domain'],*proposal['segment_domains'].values()]:
                d['physical_domains'].update(density_kg_m3=dict(minimum=500.,maximum=2500.,default=1100.),
                    curvature_y_rad_m=dict(minimum=-10.,maximum=10.,default=0.))
            request['segments']={'0':dict(physical_parameters=dict(density_kg_m3=1200,curvature_y_rad_m=.1))}
        elif kind=='polygon':
            for d in [proposal['segment_domain'],*proposal['segment_domains'].values()]:
                d['section_dimensions_m']['polygon']={}
            prototype=next(p for p in proposal['assembly']['components'] if p['id']==proposal['serial_assembly']['root_segment'])
            request['segments']={'0':dict(sections=[dict(kind='polygon',parameters={},angle_rad=0,
                outer_yz_m=[[-.004,-.004],[.004,-.004],[.004,.004],[-.004,.004]]) for _ in prototype['sections']])}
        elif kind=='nonbase_start':
            proposal['conditional_rules']='selected_segments_and_consecutive_spans_v1'
            request['spans']=[dict(first_segment=1,last_segment=1,count=1)]
        else:
            cells=int(kind[4:]);proposal['serial_assembly']['cell_count_bounds']=[4,16]
            request['segments']={str(i):dict(cells=cells) for i in range(2)}
        request['family_space_identity']=digest(proposal)
        try:
            design,mesh,physics=generate_family(dict(space=proposal,request=request))
            extensions.append(dict(proposal=kind,generated=True,dofs=len(physics['dofs']),
                mesh=mesh,task_acceptance='unmeasured; no rollout',
                first_route_part=design['tendons'][0]['points'][0]['attachment']['part']))
        except Exception as exc:extensions.append(dict(proposal=kind,generated=False,reason=str(exc)))
    result=dict(scope='Read-only engineering audit; no scientific evaluation or Provider rehearsal',
        state=dict(study=h.run_id,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            freeze=s['freeze'],resolved_identity=spec['resolved_identity'],
            handoff_admitted=s.get('pilot',{}).get('session_handoff_live_admitted'),
            formal_authorization=[e['outputs'][0] for e in events if e['kind']=='formal_study_authorization'],
            usage=h.store.remaining(),mathematical_evaluations=s.get('mathematical_evaluations'),
            independent_physical_replays=len(s.get('physical_replays',[])),pending=s.get('pending'),
            unconsumed_response=s.get('pilot',{}).get('unconsumed_response'),unsettled_receipts=unsettled,
            decisions=len(s.get('plans',[]))),
        frozen_knowledge=spec.get('knowledge_manifest'),request_observations=requests,
        payout_domain=domain,geometry_cases=cases,parameter_catalog=catalog,
        isolated_engineering_proposals=extensions,
        frozen_design_domains={k:v for k,v in space.items() if k!='assembly'})
    target=root/'evidence/phs2d_openness_audit_20261106/audit.json'
    atomic_json(target,result)
    print(json.dumps(dict(output=str(target),requests=len(requests),geometry_cases=len(cases),
        outside=sum(r.get('outside_payout_domain',False) for r in cases),failures=[r for r in cases if not r['generated']]),ensure_ascii=False))


if __name__=='__main__':audit()
