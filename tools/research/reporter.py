"""A-line report delivery and short, accounted, read-only Reporter requests.

F0 owns facts and evidence admission. Reports are retrieval artifacts, never
registered evidence. Model interpretation runs only outside the main invocation.
"""
from copy import deepcopy
import json
import os
import httpx
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.research_reporting import (EvidenceLocation, EvidenceRelation,
    RecordedField, ReportedMetric, ReporterInterpretation, ScientificReport)
from tools.platform_store import plain
from tools.research.core import read_evidence
from tools.research.contracts import EvidenceQuery
from tools.research.evidence_views import result_card
from tools.research.evidence_policy import paired_evidence
from tools.research.state import state, protected


class InvestigationRequest(Contract):
    question: str = Field(min_length=1)
    references: list[EvidenceRef] = Field(min_length=1)
    focus: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=lambda: ['Use existing evidence only'])
    reads: list[EvidenceQuery] = Field(default_factory=list,
        description='Optional exact fields/range/JSON Pointer reads; never formal reading credit')


class InterpretationResponse(Contract):
    interpretations: list[ReporterInterpretation]


RESULT_KEYS=('results','physical_replays','mechanics_results','analysis_results',
    'matched_state_results','rl_evaluations','control_search_results')


def entries(host):
    references={e['outputs'][0]['artifact_id']:plain(e['outputs'][0])
        for e in host.store.events(host.run_id) if e['kind']=='research_report'}
    return [(ref,host.store.artifact(ref)) for ref in references.values()]


def _card(host, reference):
    """Adapt RL episode fields locally; F0 and mathematical methods stay frozen."""
    card=result_card(host,reference)
    value=read_evidence(host,dict(reference=reference),record_read=False)
    if 'mathematical_facts' in value:
        # Legacy mechanics predates scoped_claim. Copy its recorded solver facts
        # without manufacturing a MathematicalEvidence certificate or conclusion.
        facts=value['mathematical_facts'];summary=deepcopy(card.deterministic_summary)
        summary['recorded_mathematics']={k:facts[k] for k in ('status','converged','exitflag',
            'original_feasible','relaxed_feasible','physical_task_acceptance','objective_definition') if k in facts}
        summary['recorded_conclusions']=value.get('verified_conclusions',[])
        metrics=[*card.metrics,*[ReportedMetric(name=k,value=facts[k],scope='solver',
            source=EvidenceLocation(reference=reference,pointer='/mathematical_facts/'+k))
            for k in ('objective','initial_objective','iterations','function_evaluations','scaled_violation')
            if type(facts.get(k)) in (int,float)]]
        candidate=value.get('design_candidate');trajectory=value.get('trajectory') or {}
        identity=card.identity.model_copy(update=dict(candidate=EvidenceRef.model_validate(candidate) if candidate else None,
            task_identity=trajectory.get('task_identity'),design_identity=trajectory.get('design_identity'),
            model_identity=facts.get('model_identity')))
        details=[*card.detail_sources,*[EvidenceLocation(reference=reference,pointer='/'+k)
            for k in ('task_requirements','objective_definition','diagnostic','mathematical_facts') if k in value]]
        card=card.model_copy(update=dict(identity=identity,metrics=metrics,
            deterministic_summary=summary,detail_sources=details))
    if 'independent_evaluation_executed' in value:
        metrics=list(card.metrics)
        limits=value.get('acceptance') or {}
        for i,episode in enumerate(value.get('episodes',[])):
            for name,limit,unit in (
                    ('terminal_position_error_m','terminal_position_limit_m','m'),
                    ('holding_max_position_error_m','position_limit_m','m'),
                    ('holding_max_speed_m_s','holding_speed_limit_m_s','m/s')):
                if episode.get(name) is None:continue
                threshold=limits.get(limit)
                metrics.append(ReportedMetric(name=f'episode_{i}/{name}',value=episode[name],
                    unit=unit,threshold=threshold,scope='physical_task',
                    passed=episode[name]<=threshold if threshold is not None and episode.get('complete') else None,
                    source=EvidenceLocation(reference=reference,pointer=f'/episodes/{i}/{name}'),
                    threshold_source=EvidenceLocation(reference=reference,pointer='/acceptance/'+limit)
                        if threshold is not None else None))
        card=card.model_copy(update=dict(metrics=metrics))
    # A plan is intent, not a fact inferred from the eventual result.
    for ref in reversed(state(host).get('plans',[])):
        saved=host.store.artifact(ref);row=host.store.lookup(host.run_id,saved['request_id'])
        if not row or not row['receipt']:continue
        output=host.store.artifact(json.loads(row['receipt'])['output'])
        result=output.get('result',output)
        if result.get('reference')!=plain(reference):continue
        fields=[RecordedField(name='agent_intent/'+k,value=v,
            source=EvidenceLocation(reference=ref,pointer='/original_plan/'+k))
            for k,v in saved['original_plan'].items() if k in (
                'hypothesis','decision','expected_observation','weakening_observation',
                'fixed_conditions','interpretation','stopping_condition')]
        card=card.model_copy(update=dict(recorded_context=[*card.recorded_context,*fields],
            identity=card.identity.model_copy(update=dict(operation=card.identity.operation or saved['original_plan']['action']))))
        break
    return card


def _comparison(host, left, right):
    """Recorded metric differences with explicit multi-factor scope, no attribution."""
    a=left.identity;b=right.identity
    factors=[];reasons=[];sources=[a.result,b.result]
    for field,factor in (('design_identity','structure'),('control_source','control'),
            ('model_identity','model'),('task_identity','task'),('evaluation_profile_identity','evaluator')):
        x=getattr(a,field);y=getattr(b,field)
        if x is None or y is None:reasons.append('Unknown '+field+'; no causal attribution')
        elif x!=y:factors.append(factor)
    if a.candidate and b.candidate:
        ca=host.store.artifact(a.candidate)['configuration']
        cb=host.store.artifact(b.candidate)['configuration']
        for key,factor in (('robot','structure'),('policy','control')):
            if ca.get(key)!=cb.get(key):factors.append(factor)
        sources += [EvidenceLocation(reference=c,pointer='/configuration') for c in (a.candidate,b.candidate)]
    comparable=paired_evidence(plain(left.evidence_summary),plain(right.evidence_summary),
        plain(a.result.reference))['verification_status']=='paired_observations'
    if not comparable:reasons.append('Complete physical outcomes, task, timing and original thresholds must match')
    reasons.append('Recorded differences do not identify a single-factor cause')
    relation=EvidenceRelation(kind='model_physics' if bool(left.mathematics)!=bool(right.mathematics)
        else 'structures' if 'structure' in factors else 'same_structure_controls',
        left=a,right=b,comparable=comparable,reasons=reasons,
        changed_factors=list(dict.fromkeys(factors)),sources=sources)
    changes=[]
    baseline={m.name:m for m in right.metrics}
    for m in left.metrics:
        old=baseline.get(m.name)
        if old and m.unit==old.unit and m.threshold==old.threshold and type(m.value) in (int,float) and type(old.value) in (int,float):
            changes.append(dict(metric=m.name,value=m.value,baseline=old.value,
                delta=m.value-old.value,unit=m.unit,threshold=m.threshold,
                source=plain(m.source),baseline_source=plain(old.source),comparable=comparable,
                scope='Descriptive arithmetic only; relation conditions govern comparison, no causal conclusion'))
    return relation,changes


def assemble(host, references, *, question=None):
    cards=[_card(host,plain(r)) for r in references]
    relations=[]
    for other in cards[1:]:
        relation,changes=_comparison(host,cards[0],other);relations.append(relation)
        cards[0].deterministic_summary.setdefault('comparisons',[]).append(dict(
            baseline=plain(other.identity.result),metrics=changes))
    if question is None and any(m.scope=='physical_task' for m in cards[0].metrics):
        # Reuse the existing complete-outcome ranking; at most one historical card.
        from tools.research.feedback import task_gap
        s=state(host)
        candidates=[*s.get('results',[]),*s.get('physical_replays',[]),
            *[r['reference'] for r in s.get('research_history',[])]]
        eligible=[r for r in candidates if r!=plain(references[0]) and task_gap(host.store.artifact(r))['valid_complete']
            and task_gap(host.store.artifact(r))['normalized_gap'] is not None]
        if eligible:
            baseline=min(eligible,key=lambda r:task_gap(host.store.artifact(r))['normalized_gap'])
            relation,changes=_comparison(host,cards[0],_card(host,baseline));relations.append(relation)
            cards[0].deterministic_summary['comparisons']=[dict(baseline=baseline,metrics=changes)]
    return ScientificReport(mode='investigation' if question is not None else 'result_summary',
        question=question,results=cards,relations=relations)


def _save(host, report, *, request=None, status='deferred', interpretation_for=None, error=None):
    from tools.research.agent import record
    return record(host,'research_report',dict(report=plain(report),request=plain(request),
        interpretation_status=status,interpretation_for=interpretation_for,error=error))


def investigate(host, request):
    """Typed synchronous tool: existing evidence only, no nested Provider send."""
    q=InvestigationRequest.model_validate(request)
    report=assemble(host,q.references,question=q.question)
    # Validate explicit reads now; only selected subnodes enter the Reporter input.
    for query in q.reads:read_evidence(host,plain(query),record_read=False)
    ref=_save(host,report,request=q)
    return dict(report_reference=ref,**host.store.artifact(ref))


def scientific_feedback(host, value, before=None, *, receipt=None):
    """Deliver a saved deterministic report without jeopardizing completed science."""
    from tools.research.agent import record
    s=state(host);result=value.get('result',value)
    reference=result.get('reference') if isinstance(result,dict) else None
    known=[r for key in RESULT_KEYS for r in s.get(key,[])]
    references=value.get('scientific_results')
    if references==[]:return None  # This receipt explicitly recorded no new science.
    if references is None:
        references=[reference] if reference in known else []
        if receipt and receipt['output'] in known:references=[receipt['output']]
        if not references and before is not None:
            references=[r for r in known if all(r not in before.get(key,[]) for key in RESULT_KEYS)]
    if not references:
        if receipt:
            return dict(operation_outcome=value,interpretation_status='unavailable',
                error='EXACT_SCIENTIFIC_RESULT_BINDING_UNAVAILABLE',receipt=receipt)
        return None
    if any(r not in known for r in references):
        return dict(operation_outcome=value,interpretation_status='unavailable',
            error='UNREGISTERED_SCIENTIFIC_RESULT_BINDING',receipt=receipt)
    if len(references)>1:
        deliveries=[scientific_feedback(host,{**value,'scientific_results':[r]},receipt=receipt) for r in references]
        main=references.index(reference) if reference in references else len(references)-1
        return dict(**deliveries[main],scientific_result_index=[dict(reference=r,
            report_reference=d.get('report_reference'),interpretation_status=d['interpretation_status'])
            for r,d in zip(references,deliveries)])
    try:
        # A crash after report persistence must reuse that exact report as well.
        saved=next(((r,v) for r,v in entries(host) if not v['interpretation_for']
            and v['report']['mode']=='result_summary' and
            [c['identity']['result']['reference'] for c in v['report']['results']]==references),None)
        if saved:ref,stored=saved;report=ScientificReport.model_validate(stored['report'])
        else:report=assemble(host,references);ref=_save(host,report)
        return dict(report_reference=ref,report=plain(report),interpretation_status='deferred',
            operation_outcome={k:result[k] for k in ('candidate','source','reference','status',
                'evaluation','selected','task_passed','stop_reason') if k in result},
            resource_use=value.get('resource_use'),
            formal_read_required='Reports do not satisfy SELECT/STOP/RL evidence_read obligations')
    except Exception as exc:
        record(host,'research_report_failure',dict(reference=reference,error=str(exc),science_preserved=True))
        return dict(operation_outcome=value,interpretation_status='unavailable',
            error='REPORT_ASSEMBLY_UNAVAILABLE: '+str(exc),scientific_results=references)


def interpretation_priority(report, previous):
    """Observable novelty only; no action selection or inferred importance score."""
    if report['mode']=='investigation':return 'explicit_investigation'
    old=[c for r in previous for c in r['results']]
    for card in report['results']:
        summary=card['deterministic_summary'];math=summary.get('task_capability',{})
        if math.get('structural_comparison'):return 'structure_control_comparison'
        if card['mathematics'] and not any(c['identity']['operation']==card['identity']['operation'] for c in old):
            return 'first_mathematical_method'
        gap=summary.get('task_gap',{})
        if gap.get('accepted') and not any(c['deterministic_summary'].get('task_gap',{}).get('accepted') for c in old):
            return 'first_complete_task_pass'
        if gap.get('valid_complete') and gap.get('normalized_gap') is not None:
            prior=[c['deterministic_summary']['task_gap']['normalized_gap'] for c in old
                if c['deterministic_summary'].get('task_gap',{}).get('valid_complete')
                and c['deterministic_summary']['task_gap'].get('normalized_gap') is not None
                and c['identity']['task_identity']==card['identity']['task_identity']]
            if not prior or gap['normalized_gap']<min(prior):return 'best_complete_result_changed'
        if set(card['main_violations'])-{v for c in old for v in c['main_violations']}:
            return 'new_task_bottleneck'
    return 'routine_or_repeated_result'


def _wire(host, reference, saved):
    provider=state(host)['pilot']['provider']
    q=saved.get('request') or {};reads=[]
    for query in q.get('reads',[]):
        reads.append(dict(query=query,value=read_evidence(host,query,record_read=False)))
    return dict(model=provider['model'],thinking=dict(type=provider['thinking']),
        reasoning_effort=provider['reasoning_effort'],max_tokens=provider['max_tokens'],stream=False,
        messages=[dict(role='system',content=(
            'You are a read-only scientific Reporter. Return JSON with only interpretations, a list '
            'of ReporterInterpretation objects using this schema: '+json.dumps(InterpretationResponse.model_json_schema())+
            '. Every item requires at least one exact evidence source. Explain quantitative new information, '
            'supported/weakened hypotheses, unresolved questions and discriminating observations. '
            'Respect focus and constraints as evidence scope. Request missing evidence in further_investigation. '
            'Facts, identities, metrics, costs and relations are frozen. Multi-factor differences do not '
            'identify causes. Do not choose experiments or parameters for the main Agent. '
            'No scientific actions or evidence registration are available.')),
            dict(role='user',content=json.dumps(dict(report_reference=reference,
                report=saved['report'],request=q,selected_reads=reads),separators=(',',':')))])


def _finish(host, boundary, wire, response):
    from tools.research.agent import record
    payload=json.loads(wire['messages'][-1]['content']);base=payload['report_reference']
    saved=host.store.artifact(base);report=ScientificReport.model_validate(saved['report'])
    status='available';error=None
    try:
        body=response.json();choice=body['choices'][0]
        if response.status_code not in range(200,300) or choice['finish_reason']!='stop':
            raise ValueError('REPORTER_OUTPUT_INCOMPLETE_OR_HTTP_FAILURE')
        interpretations=InterpretationResponse.model_validate_json(choice['message']['content']).interpretations
        allowed={loc['reference']['artifact_id'] for card in report.results
            for loc in [plain(card.identity.result),*map(plain,card.detail_sources)]}
        allowed.update(f.source.reference.artifact_id for card in report.results for f in card.recorded_context)
        for relation in report.relations:allowed.update(s.reference.artifact_id for s in relation.sources)
        allowed.update(q['reference']['artifact_id'] for q in (saved.get('request') or {}).get('reads',[]))
        for item in interpretations:
            if not item.sources:raise ValueError('REPORTER_INTERPRETATION_REQUIRES_SOURCE')
            for source in item.sources:
                if source.reference.artifact_id not in allowed:raise ValueError('REPORTER_SOURCE_OUTSIDE_SCOPE')
                read_evidence(host,plain(source),record_read=False)
        # The model is allowed to fill only the interpretation field.
        report=report.model_copy(update=dict(interpretations=interpretations))
    except Exception as exc:
        status='unavailable';error=str(exc)
    ref=_save(host,report,request=saved.get('request'),status=status,interpretation_for=base,error=error)
    record(host,'reporter_completed',dict(report_reference=ref,base_report=base,
        provider_request=boundary.last_request,status=status))
    # A Reporter has no executable output: even malformed/truncated text can be
    # archived and consumed after its real HTTP receipt is saved and settled.
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        if s['pilot'].get('unconsumed_response')==boundary.last_request:
            s['pilot'].pop('unconsumed_response');host.store.update_state(db,host.run_id,s)
            host.store.event(db,host.run_id,'r3_response_processing','reporter_archived',request=boundary.last_request)
    return ref


async def complete_reports(host, transport, *, recover_only=False):
    """One attempt per report, at settled outer boundaries. Unknown sends block."""
    from tools.research.agent import LiveBoundary, pending, received, record
    class ReporterBoundary(LiveBoundary):
        purpose='reporter'
    boundary=ReporterBoundary(host,transport,allow_truncated_response=True)
    s=state(host);saved_response=s['pilot'].get('unconsumed_response')
    if saved_response:
        reception=received(host,saved_response)
        if not reception or reception['purpose']!='reporter':return
        event=next(e for e in host.store.events(host.run_id) if e['kind']=='r3_request' and e['request_id']==saved_response)
        wire=host.store.artifact(host.store.artifact(event['outputs'][0])['request'])
        response=await boundary.handle_async_request(httpx.Request('POST',s['pilot']['provider']['base_url'].rstrip('/')+'/chat/completions',json=wire))
        _finish(host,boundary,wire,response)
    if recover_only:return
    if s.get('pending') or pending(host) or state(host)['pilot'].get('unconsumed_response'):
        raise ValueError('REPORTER_REQUIRES_SETTLED_MAIN_REQUEST')
    if any(e.get('active_reservation') or e.get('status',{}).get('worker_alive',True) for e in s.get('rl_runs',{}).values()):return
    attempted={host.store.artifact(e['outputs'][0])['base_report'] for e in host.store.events(host.run_id) if e['kind']=='reporter_attempt'}
    reports=entries(host)
    finished={saved['interpretation_for']['artifact_id'] for _,saved in reports if saved['interpretation_for']}
    for ref,saved in reports:
        if saved['interpretation_status']!='deferred' or ref['artifact_id'] in finished:continue
        if ref['artifact_id'] in attempted:
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='unavailable',interpretation_for=ref,error='REPORTER_INTERRUPTED_NO_AUTOMATIC_RETRY')
            continue
        previous=[v['report'] for r,v in reports[:reports.index((ref,saved))] if not v['interpretation_for']]
        priority=interpretation_priority(saved['report'],previous)
        record(host,'reporter_priority',dict(base_report=ref,reason=priority,
            requested=priority!='routine_or_repeated_result'))
        if priority=='routine_or_repeated_result':
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='skipped',interpretation_for=ref,error='REPORTER_LOW_PRIORITY_DETERMINISTIC_REPORT_RETAINED')
            continue
        # Keep protected closure capacity and at least one main decision request.
        reserve=s['spec']['budgets'].get('protected_provider_requests',0)
        if protected(host) or s['research_status']=='stopped' or host.store.remaining()['remaining']['model_calls']<=reserve+1:
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='unavailable',interpretation_for=ref,error='REPORTER_SKIPPED_TO_PRESERVE_CLOSEOUT')
            continue
        wire=_wire(host,ref,saved)
        record(host,'reporter_attempt',dict(base_report=ref['artifact_id']))
        attempted.add(ref['artifact_id'])
        try:
            request=httpx.Request('POST',s['pilot']['provider']['base_url'].rstrip('/')+'/chat/completions',
                headers={'Authorization':'Bearer '+os.environ.get('DEEPSEEK_API_KEY','')},json=wire,
                extensions={'timeout':{k:s['pilot']['provider']['timeout_s'] for k in ('connect','read','write','pool')}})
            response=await boundary.handle_async_request(request)
            _finish(host,boundary,wire,response)
        except Exception as exc:
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='unavailable',interpretation_for=ref,error=type(exc).__name__+': '+str(exc))
            if pending(host) or state(host)['pilot'].get('unconsumed_response'):raise


def provider_usage(host):
    """Audit actual response usage by role over the existing Provider ledger."""
    requests={};responses={}
    for event in host.store.events(host.run_id):
        if event['kind']=='r3_request':requests[event['request_id']]=host.store.artifact(event['outputs'][0])
        if event['kind']=='r3_response':responses[event['request_id']]=host.store.artifact(event['outputs'][0])
    totals={}
    for key,request in requests.items():
        role=request['purpose'];result=responses.get(key,{})
        group=totals.setdefault(role,dict(requests=0,usage_missing=0,prompt_tokens=0,
            completion_tokens=0,total_tokens=0,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=0,
            cost_usd='unknown',input_bytes=[]))
        group['requests']+=1;group['input_bytes'].append(request.get('input_bytes'))
        usage=result.get('usage') or {}
        if not usage:group['usage_missing']+=1
        for field in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
            if usage.get(field) is None:group[field]=None
            elif group[field] is not None:group[field]+=usage[field]
    return totals
