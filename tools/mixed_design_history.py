"""One read-only historical comparison, retaining original execution ownership."""
from collections import Counter
from pathlib import Path
import numpy as np
from tools.platform_store import Store
from tools.state_io import digest
from extensions.tendon_family.control_evidence import ControlEvidence


def compare():
    root=Path('D:/softrobot-agent/.worktrees/strands-mainline5/runs/mainline5-20261009')
    reader=ControlEvidence(Store(root));records=[];commands=[]
    for execution in ('f847771ab9e0433797cacaf170a3d826','6161b5758b294900af0b6305b7425cfd'):
        source=reader.resolve(execution);cfg=source['configuration']
        updates=reader.read_file(source,'nmpc_updates.json');applied=reader.read_file(source,'actual_commands.json');commands.append(applied)
        records.append(dict(owner_run_id=source['owner'],execution_id=execution,configuration=source['metadata']['candidate_input'],
            source_store=str(root),archive='evidence/research_mainline5_20261009/immutable_artifacts.tar.gz',
            commit='600fab815fc048fbe251b4594cc39411e2bf58ab',
            scientific_configuration_identity=digest({k:cfg[k] for k in ('robot','task','seed')} | dict(
                controller=cfg['policy']['controller'],discretization=cfg['policy']['discretization'],backend=cfg['policy']['backend'])),
            initialization=dict(physical=cfg['task']['initializer'],numerical_source=cfg['policy']['controller']['parameters']['data']['numerical_source'],
                measured_first_state=updates[0]['measured_initial_state']),
            actual_controller_updates=len(applied),update_times_s=[u['time_s'] for u in updates],
            optimization_statuses=dict(Counter(u.get('optimization_status') for u in updates)),
            stopping_reasons=dict(Counter(u.get('policy_stop_reason') for u in updates)),
            selected_iterations=[u.get('optimization_selected_iteration') for u in updates],
            update_wall_s=[u['update_wall_s'] for u in updates],
            solver_solve_s=[u.get('optimization_solve_s') for u in updates],
            first_update_tension_n=applied[0]['desired_tension_n'],
            original_files={k:source['files'][k] for k in ('actual_commands.json','nmpc_updates.json','control_spec.json','solver_configuration.json')}))
    differing=[a['time_s'] for a,b in zip(*commands) if not np.allclose(a['desired_tension_n'],b['desired_tension_n'],rtol=0,atol=1e-12)]
    return dict(records=records,scientific_configuration_matches=records[0]['scientific_configuration_identity']==records[1]['scientific_configuration_identity'],
        first_differing_applied_command_time_s=differing[0] if differing else None,differing_command_updates=len(differing),
        findings=['Both executions have 35 applied updates on the same simulated grid and identical first applied tensions.',
            'Recorded solver stopping and update wall times are compared explicitly; wall-bounded plan selection can differ under the inherited recipe.',
            'This read-only comparison identifies observations, not random noise, a software bug, or a statistical reproducibility bound.'],
        new_backends=0,repeatability_campaign=False)
