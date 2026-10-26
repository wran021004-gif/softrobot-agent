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


class FrozenDecisionBoundary(C3Archive):
    """C3 only: use a saved Handoff source state, never the final snapshot host."""
    def __init__(self, root, case, *, source=None):
        import gzip, io
        from unittest.mock import Mock
        from types import SimpleNamespace
        self.root=Path(root)
        folder,sequence=source or {
            'A':('b3_r1_history_assisted_050',425),
            'B':('b3_r1_history_assisted_050',2110),
            'C':('b3_t2_pilot_050_c',425),
        }[case]
        self.folder=folder
        self.archive=tarfile.open(fileobj=io.BytesIO(gzip.decompress(
            (self.root/'evidence'/folder/'immutable_artifacts.tar.gz').read_bytes())))
        self.snapshot=json.load(self.archive.extractfile(next(m for m in self.archive.getmembers() if m.name.startswith('snapshot/'))))
        event=next(e for e in self.snapshot['events'] if e['sequence']==sequence)
        self.preparation_reference=event['outputs'][0]
        self.preparation=self.artifact(self.preparation_reference)
        self.saved_state=self.artifact(self.preparation['source_state'])
        self.events=[e for e in self.snapshot['events'] if e['sequence']<sequence]
        self.next_request=next(r for r in self.requests() if r[0]['sequence']>sequence)
        # The archive's final state is used only by requests() to locate original
        # wire artifacts. No state fields or final ledger feed this host.
        current=deepcopy(self.saved_state)
        store=Mock();store.session.return_value=dict(state=current)
        store.events.return_value=self.events
        store.remaining.return_value=deepcopy(self.preparation['budget'])
        store.transaction.side_effect=AssertionError('C3_ARCHIVE_NO_WRITES')
        store.reserve.side_effect=AssertionError('C3_NO_SCIENTIFIC_EXECUTION')
        store.connect.side_effect=ValueError('C3_ARCHIVE_NO_LIVE_SQLITE')
        store.lookup.return_value=None
        self.host=SimpleNamespace(store=store,run_id=self.preparation['study_id'],actor='c3-read-only')
        # Follow references already saved at this boundary, including execution
        # receipts. The final archive can contain later artifacts: deny those.
        self.allowed=set();queue=[self.saved_state,*self.events]
        def refs(value):
            if isinstance(value,dict):
                if isinstance(value.get('artifact_id'),str) and isinstance(value.get('media_type'),str):yield value
                for v in value.values():yield from refs(v)
            elif isinstance(value,list):
                for v in value:yield from refs(v)
        while queue:
            for ref in refs(queue.pop()):
                key=ref['artifact_id']
                if key in self.allowed:continue
                self.allowed.add(key)
                if ref.get('media_type','application/json')=='application/json':
                    try:queue.append(self.artifact(ref))
                    except KeyError:pass  # Some saved metadata names absent optional artifacts.
        def bounded(ref,raw=False):
            ref=plain(ref)
            if ref['artifact_id'] not in self.allowed:raise ValueError('C3_FUTURE_OR_UNPUBLISHED_REFERENCE')
            return self.artifact(ref,raw=raw)
        store.artifact.side_effect=bounded

    def projection(self):
        from tools.research.research_context import agent_decision_brief
        from tools.research import agent
        from tools.research.contracts import EvidenceQuery, AnalysisRequest
        packet=deepcopy(self.next_request[3])
        packet['research']=agent_decision_brief(self.host)
        tools=deepcopy(self.next_request[2]['tools'])
        # Keep the existing production definitions; refresh only the interventions.
        for tool in tools:
            f=tool['function'];name=f['name']
            if name=='research_plan':
                f.update(description=getattr(agent,'PLAN_TOOL_DESCRIPTION',f['description']),parameters=plan_schema(packet['research']['actions'],
                    decision_required=True,family_version=self.saved_state['spec']['family_space']['version']))
            elif name=='evidence_read':f['parameters']=EvidenceQuery.model_json_schema()
            elif name=='research_analysis':f['parameters']=AnalysisRequest.model_json_schema()
        return packet,tools


def c3_frozen_audit(root,case,output,tool_input=None,*,source=None):
    """Run in either frozen checkout; no Provider or dispatch is reachable here."""
    from tools.research.core import read_evidence
    from tools.research.agent import error_feedback
    from unittest.mock import patch
    from tools.state_io import atomic_json
    boundary=FrozenDecisionBoundary(root,case,source=source);host=boundary.host
    try:
        packet,tools=boundary.projection()
        if tool_input is not None:
            uses=json.loads(Path(tool_input).read_text(encoding='utf8'));results=[]
            from tools.research.contracts import Plan,AnalysisRequest
            from tools.research.evidence_policy import admit_decision
            from tools.research.design import verify_candidate
            from jsonschema import Draft202012Validator
            definitions={t['function']['name']:t['function']['parameters'] for t in tools}
            for use in uses:
                name=use['function']['name'];value=None;args={}
                try:
                    args=json.loads(use['function']['arguments'])
                    Draft202012Validator(definitions[name]).validate(args)
                    if name=='evidence_read':value=read_evidence(host,{'view':'summary',**args},record_read=False)
                    elif name=='research_plan':
                        plan=Plan.model_validate(args);admission=admit_decision(host,plan)
                        value=dict(status='proposal_recorded',action=plan.action,decision_admission=admission,
                            scientific_execution='not_dispatched_by_C3',new_scientific_computations=0,
                            observation=None,proposed_budget=plain(plan.decision).get('requested_budget'),
                            limitation='Plan contract and evidence admission checked. Execution-specific admission was not run. An explicit local_diagnostic would compute in production; C3 does not execute it.')
                    elif name=='research_analysis':
                        q=AnalysisRequest.model_validate(args);verify_candidate(host,q.candidate)
                        value=dict(status='proposal_recorded',operation=q.operation,
                            scientific_execution='not_dispatched_by_C3',observation=None,
                            limitation='Schema and candidate identity checked; worker admission, numerical applicability and results are untested.')
                    else:raise ValueError('C3_TOOL_NOT_EXPOSED')
                    results.append(dict(tool_call_id=use['id'],name=name,status='success',result=value))
                except (ValueError,KeyError,IndexError,TypeError) as exc:
                    with patch('tools.research.agent.record',return_value=boundary.preparation['source_state']):
                        feedback=error_feedback(host,dict(name=name,input=args),exc,boundary.saved_state)
                    feedback.pop('full_error_reference',None)
                    results.append(dict(tool_call_id=use['id'],name=name,status='error',result=feedback))
                except Exception as exc:
                    # jsonschema's ValidationError is not a ValueError.
                    from jsonschema.exceptions import ValidationError
                    if not isinstance(exc,ValidationError):raise
                    results.append(dict(tool_call_id=use['id'],name=name,status='error',result=dict(
                        code='SCHEMA_VALIDATION_ERROR',message=exc.message,scientific_execution='not_dispatched_by_C3')))
            atomic_json(Path(output),results);return
        from tools.research.provider_context import official_tokenizer
        tokenizer=official_tokenizer()
        def measure(value):
            body=serialized(value)
            return dict(bytes=len(body),offline_serialized_tokens=len(tokenizer.encode(body.decode(),add_special_tokens=False).ids))
        wire=deepcopy(boundary.next_request[2]);wire['tools']=tools
        tail=dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':')))
        wire['messages'][-1]=tail
        handoff={**wire,'messages':[wire['messages'][0],*DeepSeekModel.format_request_messages(initial_messages(host.run_id)),tail]}
        checks=[]
        def queries(value,path=''):
            if isinstance(value,dict):
                if isinstance(value.get('reference'),dict) and 'view' in value and set(value)<= {'reference','view','pointer','fields','start','count'}:
                    yield value,path
                else:
                    for k,v in value.items():yield from queries(v,path+'/'+k)
            elif isinstance(value,list):
                for i,v in enumerate(value):yield from queries(v,path+'/'+str(i))
        for q,path in queries(packet['research']):
            metadata=dict(query=q,path=path,historical_read_query='/read_state/recent/' in path)
            try:
                answer=read_evidence(host,q,record_read=False)
                checks.append(dict(**metadata,status='readable',bytes=len(serialized(answer))))
            except (ValueError,KeyError,IndexError,TypeError) as exc:checks.append(dict(**metadata,status='failed',error=str(exc)))
        # Replay actual errors only when their tool inputs existed at this boundary.
        errors=[]
        for event in boundary.events:
            if event['kind']!='tool_request_error':continue
            original=boundary.artifact(event['outputs'][0]);use=original.get('tool_use',{})
            if use.get('name')!='evidence_read':continue
            q=use['input']
            if not (q.get('pointer','').startswith(('/result/','/control_result_links')) or q.get('view')=='range'):continue
            try:read_evidence(host,q,record_read=False)
            except (ValueError,KeyError,IndexError) as exc:
                with patch('tools.research.agent.record',return_value=event['outputs'][0]):
                    feedback=error_feedback(host,use,exc,boundary.saved_state)
                correction=(feedback.get('evidence_navigation') or {}).get('corrected_query')
                readable=False
                if correction:
                    try:read_evidence(host,correction,record_read=False);readable=True
                    except (ValueError,KeyError,IndexError):pass
                errors.append(dict(event=event['sequence'],query=q,code=feedback.get('error_code'),corrected_query=correction,correction_readable=readable))
        result=dict(case=case,source_archive=boundary.folder,preparation=boundary.preparation_reference,
            source_state=boundary.preparation['source_state'],event_boundary=boundary.events[-1]['sequence'],
            original_next_request=boundary.next_request[1]['request'],
            sizes=dict(brief=measure(packet['research']),same_session=measure(wire),handoff=measure(handoff),
                schema=measure(tools),fixed_system=measure(wire['messages'][0]),
                history=measure(wire['messages'][1:-1]),dynamic=measure(tail)),
            packet=packet,tools=tools,handoff_wire=handoff,query_checks=checks,error_replay=errors,
            state_unchanged=host.store.session()['state']==boundary.saved_state,
            methods=list(packet['research']['mathematical_capabilities'].get('methods',{})),
            allowed_artifact_count=len(boundary.allowed),provider_requests=0,scientific_workers=0)
        result['source_facts']={k:deepcopy(boundary.saved_state.get(k)) for k in
            ('mathematical_evaluations','physical_calls','nmpc_calls','research_status')}
        result['source_facts']['counts']={k:len(boundary.saved_state.get(k,[])) for k in
            ('candidates','results','physical_replays','analysis_results','control_initializations')}
        sequence=next(e['sequence'] for e in boundary.snapshot['events'] if boundary.preparation_reference in e['outputs'])
        future={r['artifact_id'] for e in boundary.snapshot['events'] if e['sequence']>=sequence
            for r in e['outputs']}-boundary.allowed
        result['future_only_outputs']=len(future)
        denied=0
        for key in future:
            try:host.store.artifact(dict(artifact_id=key,media_type='application/json'))
            except ValueError as exc:
                if str(exc)!='C3_FUTURE_OR_UNPUBLISHED_REFERENCE':raise
                denied+=1
        result['future_only_outputs_denied']=denied
        # Final R1 success artifacts must be inaccessible even if present in archive.
        audit=json.loads((Path(root)/'evidence/b3_r1_history_assisted_050/final_audit.json').read_text())
        result['final_r1_refs_absent']=all(r['artifact_id'] not in boundary.allowed and r['artifact_id'] not in serialized(handoff).decode()
            for r in (audit['selected'],audit['selected_solution'],audit['final_disposition']))
        atomic_json(Path(output),result)
    finally:boundary.archive.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--compare-exports',nargs=2,type=Path)
    parser.add_argument('--decision-efficiency',choices=('A','B','C'))
    parser.add_argument('--evidence-root',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--tool-input',type=Path)
    parser.add_argument('--source-archive')
    parser.add_argument('--source-sequence',type=int)
    args=parser.parse_args()
    if args.decision_efficiency:c3_frozen_audit(args.evidence_root,args.decision_efficiency,args.output,args.tool_input,
        source=(args.source_archive,args.source_sequence) if args.source_archive else None)
    else:print(json.dumps(compare_exports(args.compare_exports) if args.compare_exports else dict(context=context_audit(),search=search_audit()),indent=2))
