"""A-line report delivery and short, accounted, read-only Reporter requests.

F0 owns facts and evidence admission. Reports are retrieval artifacts, never
registered evidence. Model interpretation runs at settled pre-decision boundaries.
"""
from copy import deepcopy
from typing import Literal
import json
import re
import httpx
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.research_reporting import (EvidenceLocation, EvidenceRelation,
    RecordedField, ReportedMetric, ReporterInterpretation, ScientificReport)
from tools.platform_store import plain
from tools.research.core import read_evidence
from tools.research.contracts import EvidenceQuery, EvidenceIntentQuery, ExperienceQuery
from tools.research.evidence_views import (result_card,recorded_math_summary,recorded_control_diagnostics,
    recorded_static_summary,metric_semantics,quantitative_facts,_resources)
from tools.research.evidence_policy import paired_evidence
from tools.research.state import state, protected


class InvestigationRequest(Contract):
    question: str = Field(min_length=1)
    references: list[EvidenceRef] = Field(default_factory=list)
    subject: Literal['current_candidate','registered_results','reports'] | EvidenceRef | None = Field(default=None,
        description='Owned candidate or saved results/reports only. Read the frozen task directly with evidence_read(subject=current_task, topic=task).')
    focus: list[str] = Field(default_factory=list,
        description='Scientific questions for interpretation; does not select automatic topics. Use reads for registered topic/group/selection detail.')
    constraints: list[str] = Field(default_factory=lambda: ['Use existing evidence only'])
    reads: list[EvidenceIntentQuery | EvidenceQuery] = Field(default_factory=list,
        description='Optional scientific subject/topic/group/selection queries. Exact old EvidenceQuery remains for deliberate raw review. Neither grants formal reading credit.')
    experience_queries: list[ExperienceQuery] = Field(default_factory=list,max_length=8,
        description='Optional curated procedural search/exact read. Guidance only; never scientific sources or formal reading credit.')


class InterpretationResponse(Contract):
    interpretations: list[ReporterInterpretation]


class SourceIdInterpretation(Contract):
    kind: ReporterInterpretation.model_fields['kind'].annotation
    text: str
    source_ids: list[str] = Field(min_length=1)
    knowledge_refs: list[str] = Field(default_factory=list)


class SourceIdResponse(Contract):
    interpretations: list[SourceIdInterpretation]


RESULT_KEYS=('results','physical_replays','mechanics_results','analysis_results',
    'matched_state_results','rl_evaluations','control_search_results','search_results')


def _knowledge_receipt(host, query):
    from tools.research.experience import retrieve
    if query.get('operation')=='read' and state(host)['spec'].get('knowledge',{}).get('organization')=='typed_knowledge_v1':
        for ref in reversed(state(host).get('retrievals',[])):
            receipt=host.store.artifact(ref);old=receipt['query']
            if (all(old.get(k)==query.get(k) for k in ('operation','entry_id','revision'))
                    and old.get('detail','full')==query.get('detail','full')
                    and any(r.get('content') is not None for r in receipt['results'])):return ref
    return retrieve(host,query,reader='reporter')['reference']


def entries(host, *, status_only=False):
    references={e['outputs'][0]['artifact_id']:plain(e['outputs'][0])
        for e in host.store.events(host.run_id) if e['kind']=='research_report'}
    return [(ref,host.store.artifact(ref,paths=('interpretation_for','interpretation_status'))
        if status_only else host.store.artifact(ref)) for ref in references.values()]


def _card(host, reference):
    """Adapt RL episode fields locally; F0 and mathematical methods stay frozen."""
    card=result_card(host,reference)
    value=host.store.artifact(reference,paths=('profile.passive_program','mathematical_facts',
        'independent_evaluation_executed'))
    if 'mathematical_facts' in value or 'independent_evaluation_executed' in value:
        value=read_evidence(host,dict(reference=reference),record_read=False)
    if value.get('profile',{}).get('passive_program'):
        card=card.model_copy(update=dict(recorded_context=[*card.recorded_context,RecordedField(name='passive_program',
            value=value['profile']['passive_program'],source=EvidenceLocation(reference=reference,pointer='/profile/passive_program'))]))
    if 'mathematical_facts' in value:
        # Legacy mechanics predates scoped_claim. Copy its recorded solver facts
        # without manufacturing a MathematicalEvidence certificate or conclusion.
        facts=value['mathematical_facts'];summary=deepcopy(card.deterministic_summary)
        summary['recorded_mathematics']=recorded_math_summary(value,plain(reference))
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
        if a.candidate==b.candidate and ca['task'].get('physical_problem'):
            reasons=[r for r in reasons if not r.startswith(('Unknown design_identity;','Unknown control_source;'))]
            reasons.append('Exact same immutable passive candidate binds the structure, fixed payout, task and execution settings; no active control source exists. This does not establish a qualified working point or comparable complete outcomes.')
    if left.mathematics and right.mathematics:
        # B already owns the controlled mathematical comparison. Physical outcome
        # pairing cannot negate that narrower recorded comparison.
        comparable=None
        for current,baseline in ((a,b),(b,a)):
            comparison=host.store.artifact(current.result.reference,paths=('trajectory.structural_comparison',)).get('trajectory',{}).get('structural_comparison',{})
            if comparison.get('baseline_result')==plain(baseline.result.reference):
                comparable=comparison.get('status')=='computed_estimate'
                sources.append(EvidenceLocation(reference=current.result.reference,pointer='/trajectory/structural_comparison'))
                reasons=[comparison[k] for k in ('control_alignment','reoptimization','derivative_scope','attribution')]
                reasons.append('Comparable only as recorded computed model values; no certified optimal ranking or physical acceptance')
                break
        if comparable is None:reasons.append('No recorded controlled mathematical comparison binds these results')
    else:
        comparable=paired_evidence(plain(left.evidence_summary),plain(right.evidence_summary),
            plain(a.result.reference))['verification_status']=='paired_observations'
        if not comparable:reasons.append('Complete physical outcomes, task, timing and original thresholds must match')
        reasons.append('Recorded differences do not identify a single-factor cause')
    relation=EvidenceRelation(kind='model_physics' if bool(left.mathematics)!=bool(right.mathematics)
        else 'structures' if 'structure' in factors else 'same_structure_controls',
        left=a,right=b,comparable=comparable,reasons=reasons,
        changed_factors=list(dict.fromkeys(factors)),sources=sources)
    changes=[]
    current_raw=host.store.artifact(a.result.reference,paths=('task_analysis.constraints','acceptance'))
    baseline_raw=host.store.artifact(b.result.reference,paths=('task_analysis.constraints','acceptance'))
    baseline={m.name:m for m in right.metrics}
    for m in left.metrics:
        old=baseline.get(m.name)
        if old and m.unit==old.unit and m.threshold==old.threshold and type(m.value) in (int,float) and type(old.value) in (int,float):
            semantics=metric_semantics(current_raw,m.name)
            preference=semantics['preference'] if semantics==metric_semantics(baseline_raw,m.name) else 'unknown'
            delta=m.value-old.value
            changes.append(dict(metric=m.name,value=m.value,baseline=old.value,
                delta=delta,unit=m.unit,threshold=m.threshold,preference=preference,
                numeric_change='unchanged' if delta==0 else 'decrease' if delta<0 else 'increase',
                direction=('unchanged' if delta==0 else 'improved' if delta<0 else 'worsened') if preference=='lower' else 'unknown',
                metric_definition=semantics,passed=m.passed,baseline_passed=old.passed,
                source=plain(m.source),baseline_source=plain(old.source),comparable=comparable,
                scope='Descriptive arithmetic only; relation conditions govern comparison, no causal conclusion'))
    baseline_resources={(r.name,r.unit,r.time_basis,r.source.pointer if r.source else None):r for r in right.resources}
    for resource in left.resources:
        old=baseline_resources.get((resource.name,resource.unit,resource.time_basis,resource.source.pointer if resource.source else None))
        if old is None or resource.amount is None or old.amount is None:continue
        delta=resource.amount-old.amount
        changes.append(dict(resource=resource.name,value=resource.amount,baseline=old.amount,
            delta=delta,unit=resource.unit,time_basis=resource.time_basis,
            numeric_change='unchanged' if delta==0 else 'decrease' if delta<0 else 'increase',
            preference='unknown',direction='unknown',
            source=plain(resource.source),baseline_source=plain(old.source),comparable=comparable,
            scope='Recorded resource arithmetic only; no efficiency ranking, causal attribution or additive cost claim.'))
    return relation,changes


def assemble(host, references, *, question=None):
    cards=[_card(host,plain(r)) for r in references]
    relations=[]
    for other in cards[1:]:
        relation,changes=_comparison(host,cards[0],other);relations.append(relation)
        cards[0].deterministic_summary.setdefault('comparisons',[]).append(dict(
            baseline=plain(other.identity.result),metrics=[r for r in changes if 'metric' in r],
            resources=[r for r in changes if 'resource' in r]))
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
            cards[0].deterministic_summary['comparisons']=[dict(baseline=baseline,
                metrics=[r for r in changes if 'metric' in r],resources=[r for r in changes if 'resource' in r])]
    return ScientificReport(mode='investigation' if question is not None else 'result_summary',
        question=question,results=cards,relations=relations)


def _save(host, report, *, request=None, status='deferred', interpretation_for=None, error=None,rejection_details=None):
    from tools.research.provider import record
    if status=='deferred' and state(host)['spec'].get('knowledge',{}).get('organization')=='typed_knowledge_v1':
        from tools.research.experience import entries as knowledge_entries
        request=deepcopy(request or {})
        if not request.get('experience_receipts'):
            value=plain(report)
            focus=json.dumps([value.get('question'),request.get('focus',[])]).lower().replace('_',' ')
            findings=json.dumps([{k:c.get(k) for k in ('main_violations','evidence_summary','deterministic_summary')}
                for c in value['results']]).lower().replace('_',' ')
            def relevance(row,context):
                return sum(len(t) for t in row.get('trigger',[]) if
                    re.search(r'(?<!\w)'+re.escape(t.lower())+r'(?!\w)',context))
            candidates=[r for r in knowledge_entries(host) if r.get('resource_role')=='knowledge']
            context=focus if any(relevance(r,focus) for r in candidates) else findings
            relevant=[r for r in candidates if relevance(r,context)]
            relevant.sort(key=lambda r:(-relevance(r,context),r.get('type')!='diagnostic',r['entry_id']))
            # _wire explicitly delivers these owned receipts to Reporter.
            request['experience_receipts']=[_knowledge_receipt(host,dict(operation='read',
                entry_id=row['entry_id'],revision=row['revision'])) for row in relevant[:2]]
    return record(host,'research_report',dict(report=plain(report),request=plain(request),
        interpretation_status=status,interpretation_for=interpretation_for,error=error,rejection_details=rejection_details))


def investigate(host, request):
    """Typed synchronous tool: existing evidence only, no nested Provider send."""
    # Accept the previously advertised entry only to return an executable
    # alternative. A frozen input is not a scientific ResultCard.
    if request.get('subject')=='current_task':
        return dict(status='unsupported',reason='REPORTER_REQUIRES_CANDIDATE_OR_SAVED_RESULT',
            alternative_query=dict(subject='current_task',topic='task'),
            alternative_tool='evidence_read',scientific_result_created=False,formal_read_credit=False)
    q=InvestigationRequest.model_validate(request)
    from tools.research.evidence_intent import resolve_evidence_intent
    from tools.research.evidence_policy import registered_references
    s=state(host)
    if not q.references:
        subject=q.subject or 'current_candidate'
        if isinstance(subject,EvidenceRef):q.references.extend([subject])
        elif subject=='current_candidate':
            resolved=resolve_evidence_intent(host,dict(subject=subject,topic='structure'))
            if resolved['status']!='available':raise ValueError('INVESTIGATION_REQUIRES_REGISTERED_SUBJECT')
            q.references.extend([EvidenceRef.model_validate(resolved['subject'])])
        else:
            refs=[r for k in RESULT_KEYS for r in s.get(k,[])] if subject=='registered_results' else [r for r,_ in entries(host,status_only=True)]
            if not refs:raise ValueError('INVESTIGATION_REQUIRES_REGISTERED_SUBJECT')
            q.references.extend(EvidenceRef.model_validate(r) for r in refs)
    # An owned Plan records the requested construction/analysis, not its outcome.
    # Keep it in the same investigation as a raw provenance read, not a ResultCard.
    supporting_plans=[ref for ref in q.references if plain(ref) in s.get('plans',[])]
    q=q.model_copy(update=dict(references=[ref for ref in q.references if ref not in supporting_plans]))
    if not q.references:raise ValueError('INVESTIGATION_REQUIRES_CANDIDATE_OR_SAVED_RESULT: read owned Plans with evidence_read')
    allowed=[*s.get('candidates',{}).values(),*registered_references(host),*[r for r,_ in entries(host,status_only=True)]]
    if any(plain(r) not in allowed for r in q.references):raise ValueError('INVESTIGATION_SUBJECT_NOT_REGISTERED_IN_STUDY')
    # A prior report is a retrieval wrapper. Investigate its original results,
    # never recursively send the old full report as another scientific result.
    previous_reports=[];references=[]
    for ref in q.references:
        raw=host.store.artifact(ref,paths=('report.version','report.results'))
        if raw.get('report',{}).get('version')=='scientific_report_v1':
            previous_reports.append(plain(ref))
            references.extend(EvidenceRef.model_validate(c['identity']['result']['reference']) for c in raw['report']['results'])
        else:references.append(ref)
    q=q.model_copy(update=dict(references=list({r.artifact_id:r for r in references}.values())))
    q.reads.extend(EvidenceQuery.model_validate({k:c[k] for k in ('reference','pointer','view')})
        for c in applicable_corrections(host,[plain(r) for r in q.references]))
    report=assemble(host,q.references,question=q.question)
    automatic=[]
    if not q.reads:
        # Focus is authored scientific prose for Reporter, never a second field
        # router. Deterministic topic discovery uses the same compiler as Main.
        for reference in q.references:
            ref=plain(reference)
            topics=(('structure','task')
                if ref in s.get('candidates',{}).values() else
                ('mathematical_results',) if ref in [*s.get('analysis_results',[]),*s.get('mechanics_results',[])] else
                ('physical_results',) if ref in [r for k in RESULT_KEYS if k not in ('analysis_results','mechanics_results') for r in s.get(k,[])] else ())
            q.reads.extend(EvidenceIntentQuery(subject=reference,topic=topic) for topic in topics)
        automatic=[plain(query) for query in q.reads]
    for reference in supporting_plans:
        query=EvidenceQuery(reference=reference,view='full',pointer='/original_plan')
        if query not in q.reads:q.reads.append(query)
    # Investigation owns detailed cross-model reading; main Agent receives L1.
    for reference in q.references:
        raw=host.store.artifact(reference,paths=('candidate',))
        if not raw.get('candidate'):continue
        query=EvidenceQuery(reference=reference,view='working_set',pointer='/diagnostic_relations')
        if query not in q.reads:q.reads.append(query)
    # Validate explicit reads now; only selected subnodes enter the Reporter input.
    selected_reads=[]
    for query in q.reads:
        try:
            if isinstance(query,EvidenceIntentQuery):
                page=resolve_evidence_intent(host,plain(query))
                selected_reads.append(dict(query=plain(query),value=page))
                # Read bounded existing pages, without additional model calls.
                # A retained continuation permits exact future recovery.
                size=len(json.dumps(page).encode())
                while page.get('next_query') and size<12000:
                    next_query=page['next_query'];page=resolve_evidence_intent(host,next_query)
                    selected_reads.append(dict(query=next_query,value=page));size+=len(json.dumps(page).encode())
            else:selected_reads.append(dict(query=plain(query),value=read_evidence(host,plain(query),record_read=False)))
        except (ValueError,KeyError,IndexError) as exc:
            selected_reads.append(dict(query=plain(query),status='unavailable',reason=str(exc),
                navigation=getattr(exc,'evidence_navigation',None),
                suggested_query=plain(query) if isinstance(query,EvidenceIntentQuery) else
                    dict(reference=plain(query.reference),view='summary',pointer='')))
    request=plain(q)
    request['selected_reads']=selected_reads
    request['automatic_reads']=automatic
    request['previous_report_references']=previous_reports
    if supporting_plans:request['supporting_plan_references']=[plain(ref) for ref in supporting_plans]
    request['experience_receipts']=[_knowledge_receipt(host,plain(query)) for query in q.experience_queries]
    # Distinct explicit invocations may ask the identical question again.
    # Native receipt recovery reuses the saved report instead of calling here.
    request['invocation_step']=max((e['sequence'] for e in host.store.events(host.run_id)),default=0)+1
    ref=_save(host,report,request=request)
    return dict(delivery_version='scientific_delivery_v2',execution_status='completed',
        report_reference=ref,question=q.question,result_count=len(report.results),
        interpretation_status='deferred',
        detail_access='evidence_read(report_reference); L1 arrives before the next research decision')


def scientific_feedback(host, value, before=None, *, receipt=None):
    """Deliver a saved deterministic report without jeopardizing completed science."""
    from tools.research.provider import record
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
        raw=host.store.artifact(references[0])
        from tools.research.feedback import task_gap
        independent=references[0] in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]
        gap=task_gap(raw) if independent else None
        return dict(delivery_version='scientific_delivery_v2',execution_status='completed',
            scientific_result_status=raw.get('status'),independent_physical_evaluation=independent,
            task_acceptance=('passed' if gap['accepted'] else 'measured_failure' if gap['valid_complete'] else 'invalid_or_incomplete') if gap else 'unmeasured',
            scientific_result_reference=references[0],report_reference=ref,interpretation_status='deferred',
            operation_outcome={k:result[k] for k in ('candidate','source','reference','status',
                'evaluation','selected','task_passed','stop_reason') if k in result},
            resource_use=value.get('resource_use'),
            formal_read_required='Reports do not satisfy SELECT/STOP/RL evidence_read obligations')
    except Exception as exc:
        record(host,'research_report_failure',dict(reference=reference,error=str(exc),science_preserved=True))
        return dict(operation_outcome=value,interpretation_status='unavailable',
            error='REPORT_ASSEMBLY_UNAVAILABLE: '+str(exc),scientific_results=references)


def interpretation_priority(report, previous, *, decision_v3=False):
    """Observable novelty only; no action selection or inferred importance score."""
    if report['mode']=='investigation':return 'explicit_investigation'
    old=[c for r in previous for c in r['results']]
    for card in report['results']:
        if (((card['deterministic_summary'].get('structure_research') or {}).get('interaction')
                or card['deterministic_summary'].get('coupled_block_search'))
                and not any(c['identity']['result']==card['identity']['result'] for c in old)):
            return 'new_matched_interaction_result'
        if ((card['deterministic_summary'].get('structure_research') or {}).get('effect_semantics')=='finite_time_task_response'
                and not any(c['identity']['result']==card['identity']['result'] for c in old)):
            return 'new_finite_time_structure_result'
    if decision_v3:
        def signature(card):
            mechanism=card['deterministic_summary'].get('structure_research') or {}
            return dict(operation=card['identity'].get('operation'),task=card['identity'].get('task_identity'),
                candidate=card['identity'].get('candidate'),status=card['evidence_summary'].get('verification_status'),
                gap=card['deterministic_summary'].get('task_gap'),
                metrics=[{k:m.get(k) for k in ('name','value','unit','threshold','passed','scope')} for m in card.get('metrics',[])],
                violations=card.get('main_violations',[]),
                mechanism={k:mechanism.get(k) for k in ('operation','effect_semantics','physical_problem',
                    'target','point_binding','constraint_state','baseline','parameter_sensitivities',
                    'load_comparison','comparison','local_search')})
        prior=[signature(card) for card in old]
        for card in report['results']:
            if signature(card) in prior:continue
            summary=card['deterministic_summary'];gap=summary.get('task_gap')
            if gap and not gap.get('valid_complete'):return 'new_incomplete_task_result'
            if any((summary.get(key) or {}).get('physical_failure_relation',{}).get('status')=='constraint_mismatch'
                    for key in ('task_capability','optimal_sensitivity')):return 'model_physical_constraint_mismatch'
            status=str(summary.get('status') or card['evidence_summary'].get('verification_status') or '').lower()
            if any(word in status for word in ('incomplete','numerical_failure','inconclusive')):
                return 'new_numerically_incomplete_result'
            if gap and gap.get('valid_complete'):return 'changed_complete_task_result'
            if summary.get('structure_research'):return 'new_mechanism_observation'
        # Fall through for previously supported meaningful mathematical novelty.
    for card in report['results']:
        summary=card['deterministic_summary'];math=summary.get('task_capability',{})
        if summary.get('passive_family_search'):return 'passive_family_search_result'
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


def current_reports(host, *, status_only=False, limit=None):
    """Latest saved revision for each base report, in original result order."""
    current={}
    for ref,saved in entries(host,status_only=True):
        base=saved['interpretation_for'] or ref
        current[base['artifact_id']]=(ref,saved)
    rows=list(current.values())
    if limit is not None:rows=rows[-limit:] if limit else []
    # Status gates and latest-report selection do not need historical raw reads.
    # Complete default views and selected report requests remain unchanged.
    return rows if status_only else [(ref,host.store.artifact(ref)) for ref,_ in rows]


def reporter_handoff_summary(host, reference, saved):
    """L1: bounded facts plus explicitly non-authoritative saved interpretation."""
    from tools.research.research_context import mathematical_decision_view
    report=saved['report'];findings=[];scope=[];limitations=[];unresolved=[]
    corrections=applicable_corrections(host,[c['identity']['result']['reference'] for c in report['results']])
    for card in report['results']:
        # Refresh projections from the same immutable source, preserving old reports.
        card=deepcopy(card)
        raw=host.store.artifact(card['identity']['result']['reference'])
        if raw.get('native_analysis'):
            projected=plain(result_card(host,card['identity']['result']['reference']))
            card['mathematics']=projected['mathematics']
            card['deterministic_summary']['native_analysis']=projected['deterministic_summary']['native_analysis']
        if card['deterministic_summary'].get('passive_family_search'):
            from tools.research.evidence_views import passive_search_summary
            card['deterministic_summary']['passive_family_search']=passive_search_summary(host,card['identity']['result']['reference'],raw['result'])
        recorded=recorded_math_summary(raw,card['identity']['result']['reference'])
        if recorded is not None:card['deterministic_summary']['recorded_mathematics']=recorded
        if raw.get('execution_id'):card['deterministic_summary']['recorded_control_diagnostics']=recorded_control_diagnostics(host,raw)
        construction=recorded_static_summary(raw,card['identity']['result']['reference'])
        if construction:card['deterministic_summary']['recorded_static_construction']=construction
        evidence=card['evidence_summary'];math=mathematical_decision_view(card)
        metrics=sorted(card['metrics'],key=lambda m:m['passed'] is not False)
        fact=dict(result=card['identity']['result'],operation=card['identity']['operation'],
            result_reference=card['identity']['result']['reference'],
            metrics=[{k:m[k] for k in ('name','value','unit','threshold','passed','scope','source','threshold_source','time_s','window_s')}
                for m in metrics],main_violations=card['main_violations'])
        candidate=card['identity'].get('candidate')
        if candidate:
            from tools.research.object_choices import reference_choices
            fact['candidate']=candidate
            fact['candidate_aliases']=[name for name,ref in reference_choices(host,include_all=True).items() if ref==candidate]
        if (raw.get('structure_research') or {}).get('records'):
            from tools.research.evidence_views import data_access
            access=data_access(host,card['identity']['result']['reference'],raw)
            if access.get('recorded_executions'):fact['recorded_data_access']=access
        fact['quantitative_facts']=quantitative_facts(raw,card['identity']['result']['reference'])
        from tools.research.evidence_views import task_diagnosis
        diagnosis=task_diagnosis(raw,card['identity']['result']['reference'])
        if diagnosis:fact['task_diagnosis']=diagnosis
        fact['critical_observations']=card.get('critical_observations',[])
        for metric in fact['metrics']:metric['semantics']=metric_semantics(raw,metric['name'])
        fact['resources']=[plain(r) for r in _resources(raw,card['identity']['result']['reference']) if r.amount is not None]
        if card['deterministic_summary'].get('comparisons'):
            fact['comparisons']=card['deterministic_summary']['comparisons']
        if math:fact['mathematics']=math
        else:
            fact['recorded_summary']={k:v for k,v in card['deterministic_summary'].items()
                if k in ('task_gap','status','conclusion','recorded_mathematics','recorded_conclusions','recorded_control_diagnostics','passive_family_search','coupled_block_search')}
        if card.get('control_search'):
            search=card['control_search'];best=search.get('best')
            fact['control_search']=dict(stop_reason=search['stop_reason'],all_steps=search['all_steps'],
                best={k:v for k,v in best.items() if k!='metrics'} if best else None)
            if best:fact['metrics']=best['metrics']
        if raw.get('native_dynamics',{}).get('optimization'):
            from tools.research.evidence_views import bottleneck_diagnosis
            fact['bottleneck_diagnosis']=bottleneck_diagnosis(host,card['identity']['result']['reference'])
        if raw.get('nonlinear_capability') or raw.get('nonlinear_response'):
            from tools.research.nonlinear_capability import preparation_view
            preparation=preparation_view(host,card['identity']['result']['reference'])
            fact['t2_preparation']={k:preparation[k] for k in ('baseline_T1_available',
                'excluded_historical_or_incomplete_T1','executable_T2_count','aggregation_mathematical_evaluations','detail_query','scope')}
        task_family=(raw.get('acceptance') or {}).get('task_family')
        if task_family=='task.reach':
            names={'evaluator:task_bound':'terminal_position_error','holding_position':'holding_max_position_error',
                'holding_speed':'holding_max_speed'}
            for metric in fact['metrics']:
                if metric['name'] in names:metric['scientific_metric']=names[metric['name']]
        findings.append(fact)
        scope.append(dict(result=card['identity']['result'],claim_kind=evidence['claim_kind'],
            verification_status=evidence['verification_status'],supported_inferences=evidence['supported_inferences']))
        limitations.extend(evidence['unsupported_inferences']);unresolved.extend(evidence['unresolved'])
    interpretations=report['interpretations'] if saved['interpretation_status']=='available' else []
    reads=(saved.get('request') or {}).get('reads',[])
    pending=[c for c in corrections if not any(q.get('reference')==c['reference'] and
        (not q.get('pointer') or q['pointer']==c['pointer']) and q.get('view','full')=='full' for q in reads)]
    if pending:interpretations=[]
    # The full revision remains readable; hypotheses retain their original kind.
    if state(host)['spec'].get('research_decisions',{}).get('role_policy',{}).get('version')!='research_roles_v2':
        interpretations=interpretations[:3]
    return dict(delivery_version='scientific_handoff_v1',report_reference=reference,
        result_references=[c['identity']['result']['reference'] for c in report['results']],
        mode=report['mode'],question=report['question'],reporter_status=saved['interpretation_status'],
        delivery_mode='reporter_interpreted' if interpretations else 'deterministic_only',
        findings=findings,result_count=len(findings),scope=scope,
        comparisons=[{k:r[k] for k in ('kind','comparable','reasons','changed_factors','sources')} for r in report['relations'][:2]],
        limitations=list(dict.fromkeys(limitations)),unresolved=list(dict.fromkeys(unresolved)),
        interpretations=interpretations,interpretation_sources=[s for i in interpretations for s in i['sources']],
        selected_reads=[dict(query=r['query'],status=r.get('status','available'))
            for r in (saved.get('request') or {}).get('selected_reads',[])],
        restore_query=dict(reference=reference,view='full',pointer='/report/interpretations'),
        summary_query=dict(reference=reference,view='summary'),
        full_report_query=dict(reference=reference,view='full'),
        applicable_corrections=corrections,
        current_interpretation_status='superseded_pending_reinterpretation' if pending else saved['interpretation_status'],
        historical_interpretations_query=dict(reference=reference,view='full',pointer='/report/interpretations'),
        interpretation_scope='Non-authoritative interpretations; hypothesis and further_investigation are unconfirmed questions, not decisions',
        error=saved['error'],rejection_details=saved.get('rejection_details'))


def _compact_reads(reads, automatic):
    """Keep explicit focused reads; broad repeats become exact recovery entries."""
    result=[]
    for row in reads:
        query=row['query']
        if row.get('status')=='unavailable':result.append(row);continue
        if query in automatic and 'topic' not in query:
            result.append(dict(query=query,status='projected_in_result_facts'));continue
        value=row.get('value')
        if len(json.dumps(value,separators=(',',':')).encode())>12000:
            result.append(dict(query=query,status='detail_not_included',
                available_fields=list(value) if isinstance(value,dict) else None,
                recovery_query=query,reason='Broad read exceeds compact input; request a focused field or range. No conclusion from omitted detail.'))
        else:result.append(row)
    return result


def applicable_corrections(host, references):
    """Link recorded corrections by exact result identity; do not judge prose truth."""
    ref=state(host).get('engineering_feedback_correction')
    if not ref:return []
    value=host.store.artifact(ref)
    return [dict(reference=ref,pointer=f'/{key}/{i}',view='full',result=row['reference'])
        for key in ('mathematics','historical_control_updates','static_constructions','route_qualifications')
        for i,row in enumerate(value.get(key,[])) if row.get('reference') in references]


def _source_catalog(host, report, queries, *, semantic_sources=()):
    """Request-local raw locations; never infer paths from summary field names."""
    catalog={};seen=set()
    def add(source):
        key=(source.reference.artifact_id,source.pointer)
        if key in seen:return
        read_evidence(host,plain(source),record_read=False)
        seen.add(key);catalog['S'+str(len(catalog)+1)]=plain(source)
    def collect(value):
        if isinstance(value,EvidenceLocation):add(value)
        elif isinstance(value,Contract):
            for name in type(value).model_fields:collect(getattr(value,name))
        elif isinstance(value,list):
            for item in value:collect(item)
        # Untyped dicts contain derived summaries, not provenance contracts.
    for card in report.results:
        collect(card)
        coupled=card.deterministic_summary.get('coupled_block_search') or {}
        if coupled.get('mathematical_analysis'):
            add(EvidenceLocation(reference=coupled['mathematical_analysis'],pointer='/structure_research'))
        from tools.research.evidence_views import task_diagnosis
        ref=plain(card.identity.result.reference)
        diagnosis=task_diagnosis(host.store.artifact(ref),ref)
        if diagnosis:
            add(EvidenceLocation.model_validate(diagnosis['source']))
            for route in diagnosis['route_geometry']:
                add(EvidenceLocation.model_validate(route['source']))
        passive=card.deterministic_summary.get('passive_family_search') or {}
        if passive.get('search_scope',{}).get('evaluation_mode')=='passive_task_response':
            for row in passive.get('structures',[]):
                for condition in row['conditions'].values():
                    if condition.get('analysis'):
                        for pointer in ('/diagnostic_layers','/structure_research/baseline'):
                            add(EvidenceLocation(reference=condition['analysis'],pointer=pointer))
        capability=card.deterministic_summary.get('task_capability')
        if capability:
            pointers=[capability[k] for k in ('problem_pointer','solver_starts_pointer','sample_records_pointer')]
            comparison=capability.get('structural_comparison')
            if comparison:
                pointers.extend(comparison[k] for k in ('comparison_pointer','fixed_control_value_pointer'))
                from tools.research.capability import signed_score_comparisons
                values=signed_score_comparisons(capability,plain(card.identity.result.reference))
                for row in values.get('comparisons',[]):
                    for source in row['source_references']:add(EvidenceLocation.model_validate(source))
            for pointer in pointers:add(EvidenceLocation(reference=card.identity.result.reference,pointer=pointer))
    for relation in report.relations:collect(relation.sources)
    for query in queries:
        if 'topic' in query:continue
        # These pointers address a projection, not the immutable raw document.
        # Keep the exact view in selected_reads; cite its raw artifact root.
        pointer='' if query.get('view') in ('working_set','mathematical_capabilities','summary') else query.get('pointer','')
        add(EvidenceLocation(reference=query['reference'],pointer=pointer))
    for location in semantic_sources:add(EvidenceLocation.model_validate(location))
    return catalog


def _wire(host, reference, saved):
    from tools.research.config import role_provider
    s=state(host)
    provider=role_provider(s['spec'],s['pilot']['provider'],'reporter')
    q=saved.get('request') or {};reads=[]
    guidance=[host.store.artifact(ref) for ref in q.get('experience_receipts',[])]
    if 'selected_reads' in q:reads=q['selected_reads']
    else:
        for query in q.get('reads',[]):
            reads.append(dict(query=query,value=read_evidence(host,query,record_read=False)))
    report=ScientificReport.model_validate(saved['report'])
    available=[r for r in reads if r.get('status')!='unavailable']
    catalog=_source_catalog(host,report,[r['query'] for r in available],
        semantic_sources=[loc for r in available if 'topic' in r['query'] for loc in (r.get('value') or {}).get('sources',[])])
    from tools.research.capability import signed_score_comparisons
    comparisons=[dict(result=plain(card.identity.result),values=signed_score_comparisons(
        card.deterministic_summary['task_capability'],plain(card.identity.result.reference)))
        for card in report.results if 'task_capability' in card.deterministic_summary]
    from tools.research.provider import request_settings
    summary=reporter_handoff_summary(host,reference,{**saved,'report':plain(report)})
    findings=deepcopy(summary['findings'])
    for finding in findings:
        # Static initializer dictionaries may include every joint. The exact
        # construction stays recoverable; its scalar semantics have one owner.
        if finding.get('mathematics'):finding['mathematics'].pop('recorded_static_construction',None)
        mathematics=finding.get('mathematics') or {};native=mathematics.get('native_analysis') or {}
        search=(finding.get('bottleneck_diagnosis') or {}).get('control_search')
        comparison=native.get('comparison',{})
        if search and all('holding_max_speed_m_s' in comparison.get(k,{}) for k in ('baseline','best')):
            # These are the same immutable values already owned by the complete
            # baseline/best comparison. Keep distinct deltas, numerical error
            # bounds, physical domains, mechanisms and provenance in full.
            quantities=[]
            for quantity in mathematics['quantities']:
                pointer=(quantity.get('source') or {}).get('pointer','')
                phase=('baseline' if pointer.startswith('/native_dynamics/optimization/candidates/0/measure/') else
                    'best' if pointer.startswith('/native_dynamics/optimization/best/measure/') else None)
                field=pointer.rsplit('/',1)[-1]
                if phase is None or field not in comparison[phase] or quantity['value']!=comparison[phase][field]:quantities.append(quantity)
            mathematics['quantities']=quantities
            for key in ('baseline','best'):search.pop(key,None)
            search['metrics_at']='mathematics.native_analysis.comparison'
            capability=mathematics.get('nonlinear_capability')
            if capability:
                for key in ('J','initial_J','improvement','stop_reason','callbacks','physics_steps','worst_constraint'):
                    capability.pop(key,None)
                capability['search_facts_at']='bottleneck_diagnosis.control_search'
            if native.get('cost'):
                cost_fields={'native_model_builds','native_rollouts','native_physics_steps','native_optimization_evaluations'}
                finding['resources']=[r for r in finding['resources'] if r['name'] not in cost_fields]
    compact_report=dict(mode=report.mode,question=report.question,results=findings,
        relations=summary['comparisons'],scope=summary['scope'],limitations=summary['limitations'])
    return dict(**request_settings(provider),
        messages=[dict(role='system',content=(
            'You are a read-only scientific Reporter. Write directly in English. Return JSON with only interpretations, a list '
            'using this schema: '+json.dumps(SourceIdResponse.model_json_schema())+
            '. Every item requires source_ids selected only from source_catalog. '
            + ('Give concise scientific conclusions with supporting values, sources, uncertainty and discriminating observations. '
                if s['spec'].get('research_decisions',{}).get('role_policy',{}).get('version')=='research_roles_v2' else
                'For a substantive interpretation target approximately 200–400 English words in total; expand only when needed. Return 1-3 important interpretations; more only for an explicitly complex investigation. ')
            +             'Use the deterministic score_comparisons for deltas, normalized secants and recovery fractions. '
            'Explain quantitative new information with exact values, units and valid comparison scope. '
            'Use selected diagnostic_relations to assess possible failure mechanisms and observations '
            'that support or weaken them; explicitly state what cannot be concluded. '
            'supported/weakened hypotheses, unresolved questions and discriminating observations. '
            'Respect focus and constraints as evidence scope. Request missing evidence in further_investigation. '
            'Facts, identities, metrics, costs and relations are frozen. '
            'Registered mechanism values, parameter directions and numerical consistency are authoritative; a structure direction is a proposal, with task improvement unmeasured. Do not reinterpret active tension channels as fixed-length constraints. Multi-factor differences do not '
            'identify causes. Do not choose experiments or parameters for the main Agent. '
            'Organize the existing interpretation items into Observation (new_information), Hypotheses (hypothesis), '
            'Evidence (supported_explanation/weakened_explanation), Discriminating Evidence (further_investigation), '
            'and Unresolved (unresolved_question) when relevant. For competing hypotheses state distinct predictions '
            'and observations that would weaken each, including parameter coupling and confounders; never select the next action. '
            'Use task_diagnosis to retain per-condition actual values, bounds, units, small failures and source locations. '
            'Use recorded route_geometry first_issue times and checked poses directly. Contact/length preflight does not certify cable/body route clearance; a recorded time_s=0 failure is not a later-onset defect. '
            'Distinguish observed facts, computed model results, competing hypotheses and unresolved questions. '
            'State uncertainty when evidence is insufficient. '
            'quantitative_facts and comparison direction are authoritative derived facts. Do not reverse them. '
            'For resources use numeric_change for increase/decrease; preference and direction are separate. Unknown preference cannot justify an improvement or efficiency claim. '
            'Retain every failed constraint, including tiny strict violations. valid_failure means valid evaluation with failed task. '
            'Solver failure is not infeasibility; target distance is not mechanical equilibrium residual. '
            'Historical procedural_guidance is advisory only; it is excluded from source_catalog. '
            'If used for explanation, cite its exact entry_id@revision in knowledge_refs; only actually delivered reads are allowed. '
            'Keep recorded facts in new_information, interpretations in supported_explanation/weakened_explanation, '
            'competing hypotheses in hypothesis and unknowns in unresolved_question. Do not promote contextual knowledge to observed facts. '
            'Ground every interpretation in this Study evidence; advice grants no scientific evidence or permission. '
            'No scientific actions or evidence registration are available.')),
            dict(role='user',content=json.dumps(dict(report_reference=reference,
                report=compact_report,request={k:q[k] for k in ('question','focus','constraints') if k in q},
                selected_reads=_compact_reads(reads,q.get('automatic_reads',[])),source_catalog=catalog,procedural_guidance=guidance,
                score_comparisons=comparisons),separators=(',',':')))])


def _finish(host, boundary, wire, response):
    from tools.research.provider import record
    payload=json.loads(wire['messages'][-1]['content']);base=payload['report_reference']
    saved=host.store.artifact(base);report=ScientificReport.model_validate(saved['report'])
    status='available';error=None;rejection=None
    try:
        body=response.json();choice=body['choices'][0]
        if response.status_code not in range(200,300) or choice['finish_reason']!='stop':
            raise ValueError('REPORTER_OUTPUT_INCOMPLETE_OR_HTTP_FAILURE')
        if 'source_catalog' in payload:
            output=SourceIdResponse.model_validate_json(choice['message']['content'])
            catalog=payload['source_catalog'];interpretations=[]
            delivered_knowledge={r['entry_id']+'@'+r['revision']
                for receipt in payload.get('procedural_guidance',[]) if receipt['query']['operation']=='read'
                for r in receipt['results'] if r.get('status')!='source_unavailable'}
            for index,item in enumerate(output.interpretations):
                invalid=[key for key in item.source_ids if key not in catalog]
                if invalid:
                    rejection=dict(code='REPORTER_UNKNOWN_SOURCE_ID',interpretation_index=index,invalid_source_ids=invalid)
                    raise ValueError('REPORTER_UNKNOWN_SOURCE_ID')
                if set(item.knowledge_refs)-delivered_knowledge:
                    raise ValueError('REPORTER_KNOWLEDGE_NOT_READ')
                interpretations.append(ReporterInterpretation(kind=item.kind,text=item.text,
                    sources=[catalog[key] for key in item.source_ids],knowledge_refs=item.knowledge_refs))
        else:
            # Replay uses the persisted request contract, never today's _wire().
            interpretations=InterpretationResponse.model_validate_json(choice['message']['content']).interpretations
        allowed={loc['reference']['artifact_id'] for card in report.results
            for loc in [plain(card.identity.result),*map(plain,card.detail_sources)]}
        allowed.update(f.source.reference.artifact_id for card in report.results for f in card.recorded_context)
        for relation in report.relations:allowed.update(s.reference.artifact_id for s in relation.sources)
        allowed.update(q['reference']['artifact_id'] for q in (saved.get('request') or {}).get('reads',[]) if 'reference' in q)
        # The exact persisted request catalog already contains typed metric,
        # critical-sample and input sources. They are part of this request scope.
        allowed.update(loc['reference']['artifact_id'] for loc in payload.get('source_catalog',{}).values())
        for index,item in enumerate(interpretations):
            if not item.sources:raise ValueError('REPORTER_INTERPRETATION_REQUIRES_SOURCE')
            for source in item.sources:
                if source.reference.artifact_id not in allowed:
                    rejection=dict(code='REPORTER_SOURCE_OUTSIDE_SCOPE',interpretation_index=index,invalid_locations=[plain(source)])
                    raise ValueError('REPORTER_SOURCE_OUTSIDE_SCOPE')
                try:
                    read_evidence(host,plain(source),record_read=False)
                except Exception as exc:
                    rejection=dict(code='REPORTER_SOURCE_READ_INVALID',interpretation_index=index,
                        invalid_locations=[plain(source)],navigation=getattr(exc,'evidence_navigation',None))
                    raise
        from tools.research.evidence_policy import english_native
        if english_native(state(host)['spec']) and not interpretations:
            raise ValueError('REPORTER_INTERPRETATION_REQUIRED')
        # The model is allowed to fill only the interpretation field.
        report=report.model_copy(update=dict(interpretations=interpretations))
    except Exception as exc:
        status='unavailable';error=str(exc)
        rejection=dict(rejection or dict(code=str(exc)),exception_type=type(exc).__name__,
            catalog=payload.get('source_catalog'),provider_request=boundary.last_request)
        from tools.research.provider import received
        reception=received(host,boundary.last_request)
        rejection['raw_response_reference']=(reception or {}).get('body')
    ref=_save(host,report,request=saved.get('request'),status=status,interpretation_for=base,error=error,rejection_details=rejection)
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


async def complete_reports(host, transport, *, recover_only=False, max_model_calls=None):
    """One attempt per report, at settled pre-decision/outer boundaries. Unknown sends block."""
    from tools.research.provider import LiveBoundary, pending, received, record, credential
    class ReporterBoundary(LiveBoundary):
        purpose='reporter'
    boundary=ReporterBoundary(host,transport,allow_truncated_response=True,max_model_calls=max_model_calls)
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
    reports=entries(host,status_only=True)
    finished={saved['interpretation_for']['artifact_id'] for _,saved in reports if saved['interpretation_for']}
    for index,(ref,meta) in enumerate(reports):
        if meta['interpretation_status']!='deferred' or ref['artifact_id'] in finished:continue
        saved=host.store.artifact(ref)
        if ref['artifact_id'] in attempted:
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='unavailable',interpretation_for=ref,error='REPORTER_INTERRUPTED_NO_AUTOMATIC_RETRY')
            continue
        # An operator invocation pause is renewable, not scientific closeout.
        # Keep the deferred report for the next invocation, without an attempt.
        reserve=s['spec']['budgets'].get('protected_provider_requests',0)
        if (max_model_calls is not None and host.store.remaining()['used']['model_calls']>=max_model_calls
                and not protected(host) and s['research_status']!='stopped'
                and host.store.remaining()['remaining']['model_calls']>reserve+1):return
        previous=[host.store.artifact(r,paths=('report',))['report']
            for r,v in reports[:index] if not v['interpretation_for']]
        from tools.research.evidence_policy import english_native
        priority=interpretation_priority(saved['report'],previous,decision_v3=english_native(s['spec']))
        record(host,'reporter_priority',dict(base_report=ref,reason=priority,
            requested=priority!='routine_or_repeated_result'))
        if priority=='routine_or_repeated_result':
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='skipped',interpretation_for=ref,error='REPORTER_LOW_PRIORITY_DETERMINISTIC_REPORT_RETAINED')
            continue
        # Keep protected closure capacity and at least one main decision request.
        if protected(host) or s['research_status']=='stopped' or host.store.remaining()['remaining']['model_calls']<=reserve+1:
            _save(host,ScientificReport.model_validate(saved['report']),request=saved.get('request'),
                status='unavailable',interpretation_for=ref,error='REPORTER_SKIPPED_TO_PRESERVE_CLOSEOUT')
            continue
        try:
            wire=_wire(host,ref,saved)
            record(host,'reporter_attempt',dict(base_report=ref['artifact_id']))
            attempted.add(ref['artifact_id'])
            request=httpx.Request('POST',s['pilot']['provider']['base_url'].rstrip('/')+'/chat/completions',
                headers={'Authorization':'Bearer '+credential(s['pilot']['provider'],s['spec']['runtime']['credentials_reference'])},json=wire,
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
