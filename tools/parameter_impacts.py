"""Demonstrated two-weight builder mapping; other dependencies remain unmapped."""
from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
from extensions.tendon_family.contracts import GVSTrajectoryParameters


def parameter_impacts(effective, *, reference=None):
    policy=effective['policy'];controller=policy['controller']
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
    return dict(version='1.0.0',mapped=mapped,unmapped='All other parameter dependencies, including geometry/material/model changes.',
        authorization='Installed controller support and parameter grants do not authorize an execution; working_state.actions and existing host rules apply.')
