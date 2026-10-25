"""Read-only C3 wire/cost audit; never creates a Study or sends a request."""
from copy import deepcopy
import json
from pathlib import Path
import tarfile
import httpx
from tests.research.test_c1_method_context import C1Archive
from tools.platform_store import plain
from tools.research.agent import DeepSeekModel,plan_schema
from tools.research.research_context import compact_scientific_delivery
from tools.research.session_handoff import initial_messages


class C3Archive(C1Archive):
    def __init__(self,path=None):
        path=path or Path(__file__).resolve().parents[2]/'evidence/c3_blank_autonomous_softarm/immutable_artifacts.tar.gz'
        self.archive=tarfile.open(path)
        self.snapshot=json.load(self.archive.extractfile(next(m for m in self.archive.getmembers() if m.name.startswith('snapshot/'))))

    def host(self,events=None):
        host,s=super().host(events)
        host.store.lookup.side_effect=lambda run,key:next((r for r in self.snapshot['calls'] if r['request_id']==key),None)
        return host,s


def serialized(value):
    return httpx.Request('POST','https://offline.invalid',json=value).content


def context_audit():
    archive=C3Archive();requests=archive.requests();rows=[]
    from tools.research.provider_context import official_tokenizer
    try:tokenizer=official_tokenizer()
    except ImportError:tokenizer=None
    for index in (0,12,24):
        event,meta,wire,packet,events=requests[index]
        after=deepcopy(wire);packet=deepcopy(packet)
        from tools.research.budget import decision_budget
        host,s=archive.host(events);old_budget=packet['research']['budget']
        from tools.research.research_context import research_intent,research_action_trace,compact_action_trace,compact_intent
        packet['research']['research_intent']=compact_intent(research_intent(host))
        query=packet['research']['action_trace'].get('full_trace_query')
        packet['research']['action_trace']=compact_action_trace(research_action_trace(host,limit=None))
        if query:packet['research']['action_trace']['full_trace_query']=query
        packet['research']=compact_scientific_delivery(packet['research'],decision_only=True)
        old_budget=packet['research']['budget']
        ledger=host.store.remaining.return_value
        ledger['remaining']['model_calls']=old_budget['provider_budget']['remaining_total']
        ledger['remaining']['backend_solves']=old_budget['science_budget']['remaining_physical']
        s['mathematical_evaluations']=s['spec']['budgets']['mathematical_evaluations']-old_budget['science_budget']['remaining_mathematical']
        s['count_closeout']=old_budget['closeout']['active']
        projected=decision_budget(host)['provider_budget']
        old_budget['provider_budget'].update({k:v for k,v in projected.items() if k not in old_budget['provider_budget']})
        from tools.research.search import request_guidance
        packet['research']['structure_actions']=request_guidance(archive.snapshot['session']['state']['spec'])
        for tool in after.get('tools',[]):
            if tool['function']['name']=='research_plan':
                tool['function']['parameters']=plan_schema(packet['research']['actions'],decision_required=True,
                    family_version='serial_family_space_v2')
        after['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
        short=deepcopy(after)
        short['messages']=[wire['messages'][0],*DeepSeekModel.format_request_messages(initial_messages(packet['study_id'])),after['messages'][-1]]
        variants={'original':wire,'same_session':after,'verified_handoff_projection':short}
        # Count actual repeated numerical payloads, not evidence references.
        probes=('0.19304308687570046','61.52347153119494')
        rows.append(dict(boundary=index+1,request_reference=meta['request'],
            sizes={k:dict(bytes=len(serialized(v)),offline_tokens=len(tokenizer.encode(serialized(v).decode(),add_special_tokens=False).ids) if tokenizer else None)
                for k,v in variants.items()},
            contributions=dict(system_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='system'),
                historical_assistant_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='assistant'),
                tool_feedback_bytes=sum(len(serialized(m)) for m in wire['messages'] if m['role']=='tool'),
                packet_bytes=len(serialized(json.loads(wire['messages'][-1]['content'].split('\n',1)[1]))),
                schema_bytes=len(serialized(wire.get('tools',[])))),
            payload_occurrences={k:{p:serialized(v).decode().count(p) for p in probes} for k,v in variants.items()},
            history_preserved=wire['messages'][:-1]==after['messages'][:-1],
            trace_nodes=len(packet['research']['action_trace']['recent']),
            original_hypothesis_visible=bool((packet['research']['research_intent'].get('latest_decision') or {}).get('agent_hypothesis')),
            stop_and_select_rules_preserved=packet['guidance']==json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['guidance'],
            original_budget_fields_preserved=all(old_budget['provider_budget'][k]==v for k,v in json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']['budget']['provider_budget'].items()),
            handoff_status='Offline complete-wire projection only; actual rotation requires existing live admission and settled boundary verification'))
        for report in packet['research'].get('latest_reports',[]):
            archive.artifact(report['report_reference'])
            for ref in report['result_references']:archive.artifact(ref)
    archive.archive.close()
    return dict(boundaries=rows,provider_requests=0,scientific_workers=0,
        token_scope='Pinned local tokenizer over serialized JSON; not Provider prompt usage',
        contributions_scope='Serialized components include their own framing, not an additive partition')


def search_audit():
    """Frozen-incumbent coverage fixture, with the real generator, no scores/worker."""
    from tools.research.config import ROOT,resolve
    from tools.research.contracts import FamilyMixedSearch
    from tools.research import mixed_moves
    from tools.research.optimal_capability import conic_subproblems
    from tools.research.task_constraints import describe_analysis_requirements
    from tools.state_io import digest
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    spec=resolve(ROOT/'configs/research/study_c3_blank_autonomous.json');space=spec['family_space']
    cost=1+conic_subproblems(describe_analysis_requirements(spec['configuration'],{}));result=[]
    for groups in (spec['family_search']['variable_groups'],['lengths','materials'],['routing','sections']):
        q=FamilyMixedSearch(version='family_mixed_search_v1',family_space_identity=digest(space),variable_groups=groups,
            segment_counts=[1,2,3] if 'segment_count' in groups else [3],
            tendon_counts=[3,4] if 'tendon_count' in groups else [3],screening_fidelity='coarse',
            objective='task_violation',operating_point='controller_start_input',max_proposals=16,max_evaluations=12)
        incumbent=mixed_moves.initial(space,q);seen=set();rows=[];evaluations=0
        for i in range(q.max_proposals):
            point,paths,h=(incumbent,['initial'],q.step) if i==0 else mixed_moves.next_move(space,q,incumbent,i-1,q.step)
            params=mixed_moves.generation(space,q,point);identity=digest(params);duplicate=identity in seen;seen.add(identity)
            try:
                generate_family(parse_build(dict(space=space,request=params)));legal=True;error=None
            except ValueError as exc:legal=False;error=str(exc)
            if legal and not duplicate:evaluations+=cost
            rows.append(dict(proposal=i+1,paths=paths,legal=legal,duplicate=duplicate,step=h,error=error))
            if evaluations>=12:break
        result.append(dict(groups=groups,trajectory=rows,mathematical_evaluations=evaluations,
            conic_solves=evaluations//cost,model_preparations=evaluations//cost,physical_launches=0))
    return dict(scenarios=result,scope='Engineering geometry/coverage fixture with fixed incumbent, not scientific scores or task importance. Actual incumbent updates alter conditional coordinates.')


def compare_exports(paths):
    """Read recorded acceptance/cost only; never rerun the task evaluator."""
    from tools.research.reporter import provider_usage
    archives=[C3Archive(Path(p)/'immutable_artifacts.tar.gz') for p in paths]
    rows=[];shared=[]
    for archive in archives:
        snapshot=archive.snapshot;s=snapshot['session']['state'];spec=s['spec'];host,_=archive.host()
        shared.append({k:spec.get(k) for k in ('canonical_task','family_space_identity','budgets','fidelity_policy',
            'nmpc_limits','rl_limits','native_control_limits','confirmation','analysis_protocol','runtime','capabilities')})
        plans=[archive.artifact(r)['original_plan'] for r in s['plans']]
        first=next((p for p in plans if p['action'] in ('generate','search')),None)
        rows.append(dict(study_id=spec['study_id'],strategy=spec.get('initial_structure_strategy'),
            first_structure_plan=first,ledger=snapshot['ledger'],provider=provider_usage(host),
            mathematical_evaluations=s.get('mathematical_evaluations'),
            analysis_costs=[dict(reference=r,charged_evaluations=archive.artifact(r).get('charged_analysis_evaluations'),
                internal_calculations=archive.artifact(r).get('internal_calculations'),
                numerical_failure=archive.artifact(r).get('numerical_failure')) for r in s.get('analysis_results',[])],
            independent_results=[dict(reference=r,status=archive.artifact(r).get('status'),
                acceptance=archive.artifact(r).get('acceptance')) for k in ('results','physical_replays','rl_evaluations') for r in s.get(k,[])],
            selected=s.get('selected'),stopped=s['research_status']=='stopped'))
        archive.archive.close()
    return dict(common_conditions_equal=all(s==shared[0] for s in shared),studies=rows,
        scope='Original recorded acceptance and costs, not new evidence or an independent scientific ranking. Missing internal costs remain unknown; do not add ledger wall time to kernel wall time.')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--compare-exports',nargs=2,type=Path)
    args=parser.parse_args()
    print(json.dumps(compare_exports(args.compare_exports) if args.compare_exports else dict(context=context_audit(),search=search_audit()),indent=2))
