"""Immutable selectable facts; deterministic expansion, never scientific decisions."""
from copy import deepcopy
import re
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.platform import EvidenceRef
from tools.platform_store import plain, encode
from tools.state_io import digest

VERSION = 'selectable_facts_v3'
CATALOG_VERSION = '1.0.0'


class FactSelection(Contract):
    handle: str
    projection: str = Field(default='', description='Relative JSON Pointer into this original fact; extraction only, no calculations or conversions.')


class SelectedSourceFact(FactSelection):
    statement: str = Field(min_length=1)
    catalog: EvidenceRef
    catalog_version: Literal['1.0.0']


def investigator_catalog(dispatcher,order):
    """All authorized root fields; selecting a handle still requires inspection."""
    entries=[]
    for ref in order.evidence:
        source=dispatcher.store.artifact(ref)
        fields=source.items() if isinstance(source,dict) else [('',source)]
        for key,value in fields:
            pointer='/'+str(key).replace('~','~0').replace('/','~1') if key!='' else ''
            entry=dict(reference=plain(ref),pointer=pointer,value=deepcopy(value),
                value_type=type(value).__name__,source_identity=source_identity(source))
            entry['handle']='source-'+digest(entry)
            entries.append(entry)
    body=dict(kind='investigator_fact_catalog',version=CATALOG_VERSION,activity_run_id=dispatcher.run_id,
        investigation_id=order.investigation_id,order_identity=digest(plain(order)),entries=entries,
        rules='Select a root handle with an extraction-only relative projection. Exact original values and identities are expanded by the program. Only fields in inspected content pages may support facts or counterevidence; availability is not inspection.')
    with dispatcher.store.transaction() as db:ref=plain(dispatcher.store.put(db,body))
    return ref,body


def expand_source(dispatcher,selected,node,*,path):
    from tools.research_investigations import SourceFact
    selected=SelectedSourceFact.model_validate(selected)
    if plain(selected.catalog)!=node.get('source_fact_catalog'):
        raise BindingError(path+'/catalog',selected.catalog,'unknown or stale investigator catalog')
    body=dispatcher.store.artifact(selected.catalog)
    if (body['version']!=selected.catalog_version or body['investigation_id']!=node['order']['investigation_id']
        or body['order_identity']!=digest(node['order']) or body['activity_run_id'] not in {dispatcher.run_id,node.get('source_catalog_origin_run_id')}):
        raise BindingError(path+'/catalog',selected.catalog,'investigator ownership, source version or authorization changed')
    entry=next((e for e in body['entries'] if e['handle']==selected.handle),None)
    if not entry or entry['reference'] not in node['order']['evidence']:
        raise BindingError(path+'/handle',selected,'unknown or unauthorized source handle')
    try:value=project(entry['value'],selected.projection)
    except (ValueError,KeyError,IndexError,TypeError):
        raise BindingError(path+'/projection',selected,'invalid extraction-only projection') from None
    fact=SourceFact(statement=selected.statement,reference=entry['reference'],pointer=entry['pointer']+selected.projection,
        value=value,source_identity=entry['source_identity'])
    dispatcher._validate_fact(fact,'RETURN')
    if not any(dispatcher._visible(fact,r) for r in node['reads']):
        raise BindingError(path,selected,'selected original field has not been inspected',dict(query=dict(reference=entry['reference'],pointer=fact.pointer)))
    link=dict(model_selection=plain(selected),expanded_fact=plain(fact),value_type=type(value).__name__)
    # Units remain exact source evidence, when the selected object declares them.
    if isinstance(value,dict):
        link['declared_units']={k:deepcopy(value[k]) for k in ('unit','units') if k in value}
    return fact,link


class SelectedClaim(Contract):
    statement: str = Field(min_length=1)
    supporting_facts: list[FactSelection] = Field(min_length=1, max_length=12)
    additional_support: list[FactSelection] = Field(default_factory=list, max_length=12, description='Principal supplemental original-source facts, never attributed to the investigator report.')
    scope: list[FactSelection] = Field(min_length=1, max_length=8)
    support_explanation: str = Field(min_length=1)


class SelectedDisposition(Contract):
    investigation_id: str
    report: EvidenceRef
    catalog: EvidenceRef
    catalog_version: Literal['1.0.0']
    disposition: Literal['accept', 'defer', 'reject']
    evidence_used: list[FactSelection] = Field(default_factory=list, max_length=12)
    adopted_claims: list[SelectedClaim] = Field(default_factory=list, max_length=8)
    semantic_claims_unassessed: list[str] = Field(default_factory=list, max_length=12)
    remaining_unknowns: list[str] = Field(default_factory=list, max_length=12)
    reason: str = Field(min_length=1)


class BindingError(ValueError):
    def __init__(self, path, selection, reason, legal=None):
        self.issue = dict(path=path, selection=plain(selection), reason=reason, legal=legal)
        super().__init__('DISPOSITION_FACT_BINDING: ' + encode(self.issue))


def project(value, pointer):
    """RFC6901 extraction with canonical array indices and exact JSON types."""
    if pointer == '': return deepcopy(value)
    if not isinstance(pointer, str) or not pointer.startswith('/'): raise ValueError('relative JSON Pointer required')
    for raw in pointer[1:].split('/'):
        if re.search(r'~(?![01])', raw): raise ValueError('invalid pointer escape')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict): value = value[key]
        elif isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', key): raise ValueError('canonical nonnegative array index required')
            value = value[int(key)]
        else: raise ValueError('cannot project a scalar')
    return deepcopy(value)


def source_identity(source):
    keys = ('candidate_id','owner_run_id','run_id','execution_id','source_execution_id','configuration',
            'scientific_configuration_identity','coordinate_frame','result_type')
    return {k:deepcopy(source[k]) for k in keys if isinstance(source,dict) and k in source}


def report_binding(dispatcher,target):
    node=dispatcher._reports()[target['investigation_id']]
    binding=dict(investigation_id=target['investigation_id'],report=target['report'],
        original_identity=digest(node['original']) if node.get('original') else None,
        original_execution_id=node.get('original_execution_id'),
        order_identity=digest(node['order']) if node.get('order') else None,execution_id=None)
    if node.get('order'):
        call=dispatcher.store.lookup(node.get('request_run_id',dispatcher.run_id),node.get('active_request_id','investigation-'+target['investigation_id']))
        binding['execution_id']=call['execution_id'] if call else None
    return binding


def catalog(dispatcher, targets, source_refs, *, source_reads=None):
    entries = []
    for target in targets:
        report = dispatcher.store.artifact(target['report'])
        # This immutable node binding excludes later dispositions and mutable reads.
        binding=report_binding(dispatcher,target)
        for area in ('facts','counterevidence'):
            for index, fact in enumerate(report[area]):
                from tools.research_investigations import SourceFact
                dispatcher._validate_fact(SourceFact.model_validate(fact),'PRINCIPAL')
                entries.append(dict(origin='report', report_binding=binding,
                    report_item_pointer=f'/{area}/{index}', fact=deepcopy(fact),
                    name=fact['statement'], purpose='Supporting report judgment or explicitly selected scope. Counterevidence retains its original label.'))
    # Expose exact original root fields as supplemental facts, with no pretense
    # that the child report contains them. Availability is not an inspection.
    for ref in source_refs:
        source = dispatcher.store.artifact(ref)
        if not isinstance(source,dict) or source.get('kind') in ('human_engineering_review','disposition_fact_catalog'): continue
        fields=[('/'+key.replace('~','~0').replace('/','~1'),value,key) for key,value in source.items()]
        if source_reads is not None:
            fields=[]
            for observed in source_reads:
                if observed['reference']!=plain(ref) or observed['page']['kind']!='content':continue
                prefix=observed['pointer'];content=observed['page']['content']
                if isinstance(content,dict):
                    fields.extend((prefix+'/'+k.replace('~','~0').replace('/','~1'),v,prefix+'/'+k) for k,v in content.items())
                elif not observed['page'].get('offset',0) and observed['page'].get('next_offset') is None:
                    fields.append((prefix,content,prefix))
            fields=list({pointer:(pointer,value,name) for pointer,value,name in fields}.values())
        for pointer, value, key in fields:
            if encode(project(source,pointer))!=encode(value):raise ValueError('DISPOSITION_CATALOG_INSPECTED_VALUE_MISMATCH')
            entries.append(dict(origin='principal_additional', report_binding=None, report_item_pointer=None,
                fact=dict(statement='Original source field '+key, reference=plain(ref),
                    pointer=pointer, value=deepcopy(value), source_identity=source_identity(source)),
                name=key, purpose='Principal supplemental evidence or applicability scope; independent public inspection required.'))
    for entry in entries:
        entry['value_type'] = type(entry['fact']['value']).__name__
        entry['handle'] = 'fact-'+digest(entry)
    body = dict(kind='disposition_fact_catalog',version=CATALOG_VERSION,activity_run_id=dispatcher.run_id,
        targets=deepcopy(targets),entries=entries,
        rules='Select report handles for supporting_facts; principal_additional handles belong in additional_support or scope/evidence_used. Relative projection extracts original content only. Catalog availability never substitutes original-source/public report inspection; no scientific conclusion is automatically accepted.')
    with dispatcher.store.transaction() as db: ref=plain(dispatcher.store.put(db,body))
    return ref,body


def expand(dispatcher, selected, catalog_ref, *, path='disposition'):
    from tools.research_investigations import PrincipalDisposition, SourceFact
    selected=SelectedDisposition.model_validate(selected)
    if plain(selected.catalog)!=plain(catalog_ref): raise BindingError(path+'/catalog',selected.catalog,'unknown or stale catalog')
    body=dispatcher.store.artifact(catalog_ref)
    authorized_runs={dispatcher.run_id,*[n.get('catalog_origin_run_id') for n in dispatcher.store.session(dispatcher.run_id)['state'].get('investigations',{}).values()
        if n.get('fact_catalog')==plain(catalog_ref)]}
    if body['version']!=selected.catalog_version or body['activity_run_id'] not in authorized_runs:
        raise BindingError(path+'/catalog',selected.catalog,'catalog version or activity mismatch')
    target=dict(investigation_id=selected.investigation_id,report=plain(selected.report))
    if target not in body['targets'] or dispatcher._reports().get(selected.investigation_id,{}).get('result')!=plain(selected.report):
        raise BindingError(path+'/report',selected.report,'wrong report ownership or immutable report identity')
    entries={e['handle']:e for e in body['entries']};links=[]
    def resolve(s,location,role):
        e=entries.get(s.handle)
        if not e: raise BindingError(location,s,'unknown fact handle',dict(selection=dict(handle='one of catalog.entries.handle',projection='')))
        if e['origin']=='report' and (e['report_binding']['report']!=plain(selected.report) or e['report_binding']['investigation_id']!=selected.investigation_id):
            raise BindingError(location,s,'fact belongs to another report',dict(report=plain(selected.report)))
        if e['origin']=='report' and e['report_binding']!=report_binding(dispatcher,target):
            raise BindingError(location,s,'report execution or version binding changed')
        if role=='report_support' and e['origin']!='report': raise BindingError(location,s,'supplemental fact cannot impersonate report evidence',dict(use='additional_support'))
        if role=='additional_support' and e['origin']!='principal_additional': raise BindingError(location,s,'report fact must use supporting_facts')
        f=deepcopy(e['fact'])
        if e['origin']=='principal_additional':
            report=dispatcher.store.artifact(selected.report)
            execution_ids={dispatcher.store.artifact(r['reference']).get('execution_id') for r in (*report['facts'],*report['counterevidence'])}
            source_execution=f['source_identity'].get('execution_id')
            if source_execution and execution_ids-{None} and source_execution not in execution_ids:
                raise BindingError(location,s,'supplemental fact crosses the report source execution')
        try: f['value']=project(f['value'],s.projection)
        except (ValueError,KeyError,IndexError,TypeError): raise BindingError(location,s,'invalid extraction-only projection',dict(root_type=e['value_type'],root_value=e['fact']['value'])) from None
        f['pointer']+=s.projection
        dispatcher._validate_fact(SourceFact.model_validate(f),'PRINCIPAL')
        link=dict(selection=plain(s),decision_path=location,role=role,origin=e['origin'],report_binding=e['report_binding'],
            report_item_pointer=e['report_item_pointer'],original_fact=e['fact'],expanded_fact=f)
        links.append(link)
        return f
    value=plain(selected)
    for key in ('catalog','catalog_version'):value.pop(key)
    value['evidence_used']=[resolve(s,path+f'/evidence_used/{i}','evidence') for i,s in enumerate(selected.evidence_used)]
    value['adopted_claims']=[]
    for i,c in enumerate(selected.adopted_claims):
        prefix=path+f'/adopted_claims/{i}';claim=plain(c)
        for area,role in [('supporting_facts','report_support'),('additional_support','additional_support'),('scope','scope')]:
            claim[area]=[resolve(s,prefix+f'/{area}/{j}',role) for j,s in enumerate(getattr(c,area))]
        value['adopted_claims'].append(claim)
    provenance=dict(catalog=plain(catalog_ref),catalog_version=body['version'],expansion_path=path,model_selection=plain(selected),links=links)
    with dispatcher.store.transaction() as db:provenance_ref=plain(dispatcher.store.put(db,provenance))
    value['selection_provenance']=dict(reference=provenance_ref)
    return PrincipalDisposition.model_validate(value)


def provenance_body(dispatcher,value):
    return dispatcher.store.artifact(value['reference']) if set(value)=={'reference'} else value


def diagnose(bundle):
    """Compare saved invalid responses to their actual reports, without mutation."""
    rows=[]
    for event in bundle['events']:
        if event['kind']!='investigation_provider_response':continue
        raw=bundle['artifacts'][event['outputs'][0]['artifact_id']]
        import json
        for call in raw.get('choices',[{}])[0].get('message',{}).get('tool_calls',[]):
            if call['function']['name']!='investigation_return':continue
            decisions=json.loads(call['function']['arguments']).get('dispositions',[])
            for di,d in enumerate(decisions):
                r=bundle['artifacts'][d['report']['artifact_id']]
                for ci,c in enumerate(d.get('adopted_claims',[])):
                    for fi,f in enumerate(c['supporting_facts']):
                        candidates=[];classification='new_fact_absent_from_report'
                        for area in ('facts','counterevidence'):
                            for index,rf in enumerate(r[area]):
                                if rf['reference']!=f['reference']:continue
                                if rf['pointer']==f['pointer']:
                                    candidates.append(dict(report_item=f'/{area}/{index}',fact=rf))
                                    classification='exact_report_fact' if encode(rf['value'])==encode(f['value']) else 'value_or_type_mismatch'
                                elif f['pointer'].startswith(rf['pointer']+'/'):
                                    try: v=project(rf['value'],f['pointer'][len(rf['pointer']):])
                                    except (ValueError,KeyError,IndexError,TypeError):continue
                                    candidates.append(dict(report_item=f'/{area}/{index}',fact=rf,projected_value=v,projected_type=type(v).__name__))
                                    classification='verified_object_projection' if encode(v)==encode(f['value']) else 'value_or_type_mismatch'
                        source=bundle['artifacts'].get(f['reference']['artifact_id'])
                        try:
                            original=project(source,f['pointer']);correct=encode(original)==encode(f['value'])
                        except (ValueError,KeyError,IndexError,TypeError):original=None;correct=False
                        identity_ok=all(isinstance(source,dict) and encode(source.get(k))==encode(v) for k,v in f.get('source_identity',{}).items())
                        if not correct or not identity_ok:classification='source_identity_path_type_or_value_mismatch'
                        rows.append(dict(response=event['outputs'][0],report=d['report'],investigation_id=d['investigation_id'],
                            decision_path=f'/dispositions/{di}/adopted_claims/{ci}/supporting_facts/{fi}',claim=c['statement'],
                            fact=f,value_type=type(f['value']).__name__,original_value=original,original_type=type(original).__name__,
                            source_value_matches=correct,source_identity_matches=identity_ok,report_correspondence=candidates,classification=classification))
    return dict(rows=rows,counts={k:sum(r['classification']==k for r in rows) for k in sorted({r['classification'] for r in rows})},
        original_evidence_unchanged=True,scientific_support='Requires separate review; absence from report does not mean fabrication.')
