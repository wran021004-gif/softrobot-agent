"""Family-specific rebuild obligations for authorized control and physical edits."""
from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
from extensions.tendon_family.contracts import GVSTrajectoryParameters


def parameter_impacts(effective, *, reference=None):
    policy=effective['policy'];controller=policy['controller']
    builder=policy.get('candidate_builder',{})
    if builder.get('extension_id')=='candidate.family' and builder.get('version') in ('1.1.0','1.2.0'):
        from tools.parameter_catalog import effective_catalog
        catalog=effective_catalog(effective)
        space=builder['parameters']['data']
        specifications={**space.get('parameters',{}),**space.get('control_parameters',{})}
        mapped=[]
        for row in catalog['parameters']:
            domain=row['experiment_granted_domain'] or {}
            mapped.append(dict(parameter=row['id'],meaning=row['meaning'],unit=row['unit'],
                legal_domain=row['legal_domain'],granted_range=domain.get('bounds',domain.get('options')),
                builder_spec=specifications.get(row['id']),authorized_parameter=row['study_permission']['permitted'],
                implementation_supported=row['technical_support']['supported'],current_value=row['current_value'],
                source=reference,controller={k:controller[k] for k in ('extension_id','version')},
                candidate_builder=builder['extension_id'],effective_locations=row['effective_locations'],
                reconstruct=row['required_rebuilds'],reusable=row['reuse']['allowed'],cannot_rebind=row['reuse']['invalidated'],
                evidence_rule=row['reuse']['rule'],validation_evidence=row['validation_evidence'],
                coupled_constraints=row['coupled_constraints'],
                fresh_steps=['candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison']))
        return dict(version=catalog['version'],capability_version=catalog['capability_version'],
            mapped=mapped,unmapped=catalog['integration_backlog'],authorization=catalog['execution_permission'])
    specs=policy.get('candidate_builder',{}).get('parameters',{}).get('data',{}).get('control_parameters',{})
    mapped=[]
    for path in REACH_WEIGHT_PATHS:
        name=path.rsplit('/',1)[1]
        supported=controller['extension_id']=='controller.gvs_nmpc' and controller['version'] in ('3.0.0','4.0.0','6.0.0','7.0.0')
        mapped.append(dict(parameter=path,meaning=GVSTrajectoryParameters.model_fields[name].description,
            scaling=dict(speed_scale_m_s=controller['parameters']['data'].get('recipe',{}).get('tip_speed_scale_m_s'),
                semantics='Squared world tip speed divided by speed scale squared; terminal node cost.' if name.startswith('terminal') else 'Squared normalized world tip speed integrated over holding-cost nodes; per-second weight.'),
            legal_domain='Schema nonnegative finite; reach builder requires zero or [0.0001, 1].',
            granted_range=policy.get('editable',{}).get(path),builder_spec=specs.get(path),
            authorized_parameter=path in policy.get('editable',{}) and path in specs,
            implementation_supported=supported,controller=controller,
            candidate_builder=policy.get('candidate_builder',{}).get('extension_id'),
            effective_pointer='/effective/policy/controller/parameters/data/recipe/'+name,
            source=reference,current_value=controller['parameters']['data'].get('recipe',{}).get(name),
            reusable=['Fixed task/goal/evaluator/timing and robot definition','Compatible historical tensions as numerical guesses only; states regenerated under candidate dynamics'],
            reconstruct=['CandidateInput effective controller and content identity','Candidate-specific controller plan and TrajectoryWorkspace symbolic graph/solver','Warm states from measured candidate initial state; execution manifests and receipts'],
            cannot_rebind=['Previous candidate trajectories, local linearizations, endpoint analyses, optimized controller plans, evaluations, profiles and comparisons'],
            fresh_steps=['Validated candidate preparation and actual_diff','simulation.run','evaluation.run','control.profile_report','Bound comparison and diagnostic revision'],
            evidence_rule='Historical evidence stays valid for its original candidate; a changed effective configuration needs new exact bindings.',
            references=['extensions/tendon_family/candidate.py::apply','tools/diagnostic_improvement.py::prepare_improvement',
                'extensions/tendon_family/gvs_profile.py::prepare_execution','extensions/tendon_family/gvs_nmpc.py::GVSNMPCController.configure',
                'extensions/tendon_family/gvs_trajectory.py::TrajectoryWorkspace']))
    # Do not duplicate the entire controller recipe in each row.
    for row in mapped:
        row['controller']={k:controller[k] for k in ('extension_id','version')}
    from tools.candidate_parameters import STRUCTURAL_PATHS,parameter_value
    space=policy.get('candidate_builder',{}).get('parameters',{}).get('data',{})
    for path in STRUCTURAL_PATHS:
        spec=space.get('parameters',{}).get(path)
        if not spec:continue
        mapped.append(dict(parameter=path,meaning='Source-relative '+spec.get('category','structural')+' decision.',
            granted_range=policy.get('editable',{}).get(path,spec.get('options')),builder_spec=spec,
            authorized_parameter=spec['type']=='choice' or path in policy.get('editable',{}),
            implementation_supported=controller['extension_id']=='controller.gvs_nmpc' and controller['version']=='7.0.0',
            current_value=parameter_value(effective,path),source=reference,
            reconstruct=['Resolved section/material/mass/stiffness/damping and backend robot geometry',
                'Reduced geometry and structural basis resolution; candidate state projection',
                'Candidate-specific graph/solver workspace; initializer metadata; warm-state regeneration',
                'Owned configuration, execution, evaluator, profile and comparison bindings'],
            reusable=['Frozen task/evaluator/timing/environment/topology/routing/force limits',
                'Compatible historical tensions as bounded numerical guesses only'],
            cannot_rebind=['Historical states, equilibria, trajectories, evaluations, profiles or prediction evidence'],
            fresh_steps=['candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison'],
            evidence_rule='Changed structure needs a complete new result; no unconditional equilibrium or separate analysis solve.',
            references=['extensions/tendon_family/design_decisions.py::expand','extensions/tendon_family/gvs_profile.py::candidate_numerical',
                'extensions/tendon_family/gvs_profile.py::prepare_execution']))
    return dict(version='1.0.0',mapped=mapped,unmapped='Undeclared model/discretization/topology/routing and other numerical edits.',
        authorization='Installed controller support and parameter grants do not authorize an execution; working_state.actions and existing host rules apply.')
