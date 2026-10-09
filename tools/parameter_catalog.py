"""Effective first-study catalog from trusted registered capability declarations."""
from copy import deepcopy
from tools.candidate_parameters import parameter_value
from tools.state_io import digest

CATALOG_VERSION = '1.0.0'
SOURCE_CONFIGURATION = '285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978'
STUDY_GRANTS = {
    'components/near/length_m': dict(bounds=[.15, .17]),
    'components/far/length_m': dict(bounds=[.11, .13]),
    'design/near_section_scale': dict(bounds=[.95, 1.05]),
    'design/far_section_scale': dict(bounds=[.95, 1.05]),
    'design/near_material_scenario': dict(options=['baseline', 'compliant', 'stiff']),
    'design/far_material_scenario': dict(options=['baseline', 'compliant', 'stiff']),
    'control/recipe/terminal_tip_speed_weight': dict(bounds=[.025, .1]),
    'control/recipe/holding_tip_speed_weight': dict(bounds=[.025, .1]),
}


def _declarations(effective, reg=None):
    from tools.platform_registry import registry
    binding = effective['policy']['candidate_builder']
    definition = (reg or registry()).get(binding['extension_id'], binding['version'], 'candidate_builder')
    hook = definition.hook('parameter_declarations')
    if hook is None:
        raise ValueError('REGISTERED_PARAMETER_DECLARATIONS_REQUIRED: '+definition.extension_id+'@'+definition.version)
    return definition, hook()


def study_input(effective, grants=None, *, builder_version='1.1.0'):
    """Project grants onto exact saved science without editing source/evidence.

    The archived robot bytes (including metadata) stay identical. New selectors'
    baseline values represent the incumbent's absolute source-relative choices.
    """
    if builder_version == '2.0.0':
        from extensions.tendon_family.finite_templates import study_input as finite_study_input
        return finite_study_input(effective,grants)
    from extensions.tendon_family.gvs_profile import execution_scope
    result = deepcopy(effective)
    original_scope = execution_scope(effective)
    builder = result['policy']['candidate_builder']
    builder.update(extension_id='candidate.family', version=builder_version)
    _, capability = _declarations(result)
    grants = deepcopy(STUDY_GRANTS if grants is None else grants)
    declared = {row['id']: row for row in capability['parameters']}
    if set(grants)-set(declared):
        raise ValueError('UNDECLARED_STUDY_GRANT')
    space = builder['parameters']['data']
    if not space.get('semantic_source'):
        raise ValueError('ORIGINAL_SEMANTIC_SOURCE_REQUIRED')
    previous = space.get('semantic_decisions', {})
    selected = result['robot']['structure']['data'].get('metadata', {}).get('design_decisions', {}).get('selections', {})
    provenance=result['robot']['structure']['data'].get('metadata', {}).get('design_decisions', {})
    if provenance.get('source_identity') != digest(space['semantic_source']):
        raise ValueError('ORIGINAL_SEMANTIC_SOURCE_IDENTITY_MISMATCH')
    # Choices remain anchored to the original declared physical source.
    values = {}
    for path, row in declared.items():
        operation = row['operation']
        if operation == 'routing_radius_scale':
            values[path] = selected.get(path, previous.get(path, {}).get('baseline_value', 1.))
        elif operation in ('section_scale', 'material_scenario'):
            old = 'design/'+operation
            values[path] = selected.get(path, selected.get(old, previous.get(path, previous.get(old, {})).get('baseline_value')))
            if values[path] is None:
                raise ValueError('INCUMBENT_SEMANTIC_SELECTION_MISSING: '+path)
    space.update(parameters={},control_parameters={},model_parameters={},discretization_parameters={},
        semantic_decisions={},templates={},template_discretizations={})
    result['policy']['editable'] = {}
    for path, grant in grants.items():
        row = declared[path]
        spec = dict(type=row['type'], unit=row['unit'], description=row['meaning'], **grant)
        category = 'control_parameters' if path.startswith('control/') else 'parameters'
        space[category][path] = spec
        if row['type']=='number': result['policy']['editable'][path] = deepcopy(grant['bounds'])
        if row['operation'] in ('section_scale', 'material_scenario', 'routing_radius_scale'):
            space['semantic_decisions'][path] = dict(operation=row['operation'],
                components=row['components'], baseline_value=values[path])
    if execution_scope(result) != original_scope:
        raise ValueError('PARAMETER_GRANT_CHANGED_SCIENCE')
    effective_catalog(result, grants)
    return result


def effective_catalog(effective, grant=None, validation_evidence=None, reg=None):
    """Keep technical support, study permissions, and validation evidence separate."""
    from extensions.tendon_family.candidate import check_value
    from tools.platform_store import plain
    effective = plain(effective)
    if effective['policy']['candidate_builder'].get('version')=='3.0.0':
        from extensions.tendon_family.generated_serial import check_robot
        design=effective['robot']['structure']['data'];check_robot(design,effective['policy']['discretization']['data'])
        recipe=design['metadata']['recipe'];rows=[]
        values={**recipe,'tendon_count':len(design['tendons']),'actuator_count':len(design['actuators'])}
        values.update({f'length/{i}':l for i,l in enumerate(recipe['lengths_m'])})
        values.update({f'control/recipe/{k}':effective['policy']['controller']['parameters']['data']['recipe'][k]
            for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
        for key,value in values.items():
            rows.append(dict(id=key,current_value=value,technical_support=dict(supported=True,reasons=[]),
                study_permission=dict(permitted=False,reason='Resolved execution recipe; free/fixed domains belong to typed design problem'),
                validation_evidence=dict(status='constructed',scientific_claim='Exact closed-loop receipts required for physical validation')))
        return dict(version=CATALOG_VERSION,capability_version='3.0.0',builder=effective['policy']['candidate_builder'],
            parameters=rows,usable_pool=[],search='search.design_mixed@1.0.0',
            supported=dict(physical_segments=[2,4],group_tendons=[3,4],independent_actuators='one per tendon'),
            integration_backlog=['coupled_actuation','arbitrary_graphs','motor_mass'],identity=digest(values))
    definition, capability = _declarations(effective, reg)
    policy = effective['policy']
    support = definition.capabilities['parameter_support']
    reasons = []
    for kind, field in (('controller','controller'),('backend','backend'),('model','dynamics_model')):
        binding = policy.get(field) or {}
        key = binding.get('extension_id','missing')+'@'+binding.get('version','missing')
        if key not in support[kind]: reasons.append(kind+' pairing '+key+' lacks this pool adapter validation')
    if effective['task']['family'] not in support['task_families']:
        reasons.append('Task family has no registered first-study parameter/control adapter')
    space = policy['candidate_builder']['parameters']['data']
    # Structural compatibility is checked against the declared physical source,
    # independently of matching a frozen historical task or performance record.
    from extensions.tendon_family.design_decisions import normalize_supported
    design=deepcopy(effective['robot']['structure']['data'])
    source=deepcopy(space.get('semantic_source'))
    if not source:
        reasons.append('Source-relative physical decision source is missing')
    else:
        try:
            if definition.version=='2.0.0':
                from extensions.tendon_family.finite_templates import check_robot
                check_robot(design,policy['discretization']['data'])
            elif [c['id'] for c in design['components']] != [c['id'] for c in source['components']]:
                raise ValueError('SEGMENT_TOPOLOGY_CHANGED')
            if policy['controller']['version'] == '9.0.0':
                from extensions.tendon_family.routing_radius import normalize
                normalize(design,source)
            if definition.version!='2.0.0':
                normalize_supported(design,source)
                for data in (design,source):data.pop('metadata',None)
                if design!=source:raise ValueError('FIXED_TOPOLOGY_ROUTING_OR_SECTION_LAYOUT_CHANGED')
        except (ValueError,KeyError,IndexError,TypeError) as exc:
            reasons.append('Structural projection/compatibility unavailable: '+str(exc))
    configured = {**space.get('parameters',{}), **space.get('control_parameters',{})}
    if grant is None:
        grant = {p:{k:v for k,v in spec.items() if k in ('bounds','options')} for p,spec in configured.items()}
    rows = []
    for declaration in capability['parameters']:
        row = deepcopy(declaration); path = row['id']; spec = configured.get(path)
        domain = deepcopy(grant.get(path))
        reason = list(reasons)
        if definition.version=='2.0.0' and path!='template':
            from extensions.tendon_family.finite_templates import specifications,template_id
            active=specifications(template_id(effective['robot']['structure']['data'])).get(path)
            if active is None:
                reason.append('Parameter inactive for selected finite template')
            elif domain is not None:
                if active['type']=='number':
                    domain['bounds']=[max(domain['bounds'][0],active['bounds'][0]),min(domain['bounds'][1],active['bounds'][1])]
                    if domain['bounds'][0]>domain['bounds'][1]:reason.append('Grant has no selected-template domain intersection')
                else:domain['options']=[v for v in domain['options'] if v in active['options']]
        if effective['task']['family'] not in row.get('task_families', support['task_families']):
            reason.append('Incompatible task: this parameter is outside the tracking length-only envelope')
        if policy['controller']['version'] not in row.get('controller_versions', [policy['controller']['version']]):
            reason.append('Routing mutation requires reach controller.gvs_nmpc@9.0.0')
        if not spec: reason.append('Candidate builder has no connected mutation declaration for this effective input')
        supported = not reason
        try:current = parameter_value(effective,path) if spec else None
        except ValueError:current = None  # Explicit inactive component in a finite template.
        permitted = supported and domain is not None
        if domain is not None and spec:
            if row['type']=='choice':
                if set(domain.get('options',()))-set(spec.get('options',())):raise ValueError('GRANT_EXCEEDS_BUILDER_OPTIONS: '+path)
                if set(domain.get('options',()))-set(row['legal_domain']['options']):raise ValueError('GRANT_EXCEEDS_LEGAL_OPTIONS: '+path)
            else:
                lo,hi=domain['bounds']
                if lo>hi:raise ValueError('INVALID_STUDY_RANGE: '+path)
                for value in (lo,hi):check_value(path,value,spec,policy.get('editable',{}))
                legal=row['legal_domain']
                if row['operation'] == 'routing_radius_scale':
                    from extensions.tendon_family.routing_radius import envelope
                    routing_source=space['semantic_source']
                    if definition.version=='2.0.0':
                        from extensions.tendon_family.finite_templates import catalog,template_id
                        applicable=row.get('applicable_templates',list(catalog()['templates']))
                        routing_source=catalog()['templates'][template_id(effective['robot']['structure']['data']) if current is not None else applicable[0]]['design']
                    legal = envelope(routing_source, row['components'][0])
                    row['legal_domain'] = legal
                    if lo <= legal['exclusive_minimum'] or (legal['exclusive_maximum'] is not None and hi >= legal['exclusive_maximum']):
                        raise ValueError('GRANT_EXCEEDS_ROUTING_GEOMETRY: '+path)
                if 'exclusive_minimum' in legal and lo<=legal['exclusive_minimum']:raise ValueError('GRANT_EXCEEDS_LEGAL_MINIMUM: '+path)
                if 'intervals' in legal and not any(a<=lo<=hi<=b for a,b in legal['intervals']) and not lo==hi==0:
                    raise ValueError('GRANT_EXCEEDS_LEGAL_INTERVAL: '+path)
            # Current incumbent may sit outside a deliberately narrowed mutation grant.
        physical = row['kind']=='physical_design'
        row.update(current_value=current, experiment_granted_domain=domain,
            builder_domain={k:v for k,v in (spec or {}).items() if k in ('bounds','options')},
            technical_support=dict(supported=supported, reasons=reason),
            study_permission=dict(permitted=permitted, reason=None if permitted else 'Outside this frozen study grant' if supported else '; '.join(reason)),
            validation_evidence=deepcopy((validation_evidence or {}).get(path, dict(status='pending_changed_radius_closed_loop' if row['operation']=='routing_radius_scale' else 'offline_mutation_resolved_compiler_and_mjcf_checked',
                reference='tests/test_research_mainline3.py::Mainline3EngineeringTests' if row['operation']=='routing_radius_scale' else 'tests/test_parameter_catalog.py::ParameterCatalogTests',
                exact_start_configuration='3ae03b4e4ddac2e5099ae5823fc0dd7dd9d338dfba6b7d435729d4e5ab41665b' if row['operation']=='routing_radius_scale' else SOURCE_CONFIGURATION,
                scientific_claim='No robustness or closed-loop outcome is inferred from capability.'))),
            mutation_mechanism=definition.extension_id+'@'+definition.version+': '+row['operation'],
            required_rebuilds=(['resolved physics','backend robot mesh/model','reduced geometry and structural basis','state projection','controller graph/solver','candidate initializer and warm-state regeneration'] if physical else ['controller graph/solver','warm-state regeneration']),
            reuse=dict(allowed=['Frozen task/reference/evaluator/timing/environment and unchanged topology/input order',
                    'Compatible bounded historical tensions as numerical guesses only'],
                invalidated=['candidate-specific equilibrium/linearization/endpoint/screen','controller plans and warm states',
                    'trajectories, evaluation, profiles, acceptance and comparisons'],
                rule='Exact configuration identity and provenance bind every result; rebuild after relevant edits. Cache/replay is not a repetition.'))
        if definition.version=='2.0.0' and path not in (validation_evidence or {}):
            from extensions.tendon_family.finite_templates import catalog as finite_catalog
            row['validation_evidence']=dict(
                status='finite_template_focused_offline_checked' if path=='template' else 'declared_domain_not_exhaustively_validated',
                reference='tests/test_research_v2.py::FiniteV2Tests',
                exact_start_configuration=finite_catalog()['t0_configuration'],
                scientific_claim='Selected templates and mutations have focused checks; completed closed-loop receipts apply only to their exact configurations. No full continuous-domain validation or robustness is inferred.')
        rows.append(row)
    result=dict(version=CATALOG_VERSION, capability_version=capability['version'],
        builder=dict(extension_id=definition.extension_id,version=definition.version),
        effective_identity=digest(effective),parameters=rows,
        usable_pool=[r['id'] for r in rows if r['study_permission']['permitted']],
        integration_backlog=deepcopy(capability['integration_backlog']),
        subset_selection='All comparison groups may choose any subset of usable_pool within frozen domains; no per-batch permission.',
        version_rule='Newly connected capability requires a new shared capability/study version.',
        execution_permission='Parameter permission does not consume or override the separate frozen execution budget.')
    if definition.version=='2.0.0':
        from extensions.tendon_family.finite_templates import catalog,template_id
        result.update(templates=capability['templates'],selected_template=template_id(effective['robot']['structure']['data']),
            selection=dict(path='template',syntax={'template':'T1'},method='search.family_explicit@1.0.0'),
            execution_model=catalog()['execution_model'],unsupported=catalog()['unsupported'])
    result['identity']=digest(result)
    return result
