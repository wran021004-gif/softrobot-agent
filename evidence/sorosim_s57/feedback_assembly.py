"""Evidence-only S5.7 interpretation and closeout; performs no new dynamics."""
from pathlib import Path
import numpy as np
from tools.platform_host import Host
from tools.state_io import read, atomic_json
from tools.research.state import state
from tests.research.sorosim_s57_prediction import close

ROOT=Path.cwd();DEST=ROOT/'evidence/sorosim_s57'


def run():
    summary=read(DEST/'summary.json')
    assert summary['costs']['actual_integrations']==15 and summary['costs']['actual_roots']==183
    host=Host(ROOT/'runs/research'/summary['study_id'],summary['study_id'])
    index=host.store.artifact(summary['source_index']);compact=[]
    for c in summary['cases']:
        source=next(r for r in index['cases'] if r['update_index']==c['update_index'])
        rows={}
        for n,r in c['resolutions'].items():
            v=r['comparison'];assert r['complete']
            rows[n]=dict(reference=r['reference'],position=v['position'],velocity=v['velocity'])
            if n=='1':
                d=v['archived_prediction_difference']
                rows[n]['archive_replay']=dict(position_norm_m=float(np.linalg.norm(d['tip_position_m'])),
                    velocity_norm_m_s=float(np.linalg.norm(d['tip_velocity_m_s'])),
                    state_max_absolute=float(np.max(np.abs(d['state']))),same_original_experiment=v['same_original_experiment'])
        compact.append(dict(update_index=c['update_index'],time_s=c['time_s'],applied_tension_n=source['applied_tension_n'],
            projection_curvature_residual_rad_m=source['projection_residual_max_rad_m'],
            projection_rate_residual_rad_m_s=source['projection_reconstruction']['rate_projection_residual_max_rad_m_s'],
            archived_mujoco_only_world_reconstruction_residual=None,resolutions=rows,
            grid_differences=c['grid_differences'],grid_norms_decrease=c['grid_norms_decrease'],
            controller_comparison=c['controller_comparison']))
    next_step=dict(direction='E',name='Further discriminating diagnosis',
        experiment='MuJoCo-only forward-kinematic reconstruction of the archived S5.6 NMPC k=19 and k=29 states before/after the existing GVS projection/discretization. Zero physics steps and zero full NLPs. Compare its signed world tip position/velocity residuals with S5.7 initial cross-model residuals.',
        why='The 16/32 initial-interval velocity difference still exceeds the engineering screen; later position has a large initial offset and later incremental velocity disagreement persists on screened fine grids. Pure projection loss versus cross-model kinematics/dynamics has not been isolated.',
        nonduplicate='S5.5 reconstructed different S5-A open-loop states; S5.7 used actual NMPC archives but did not calculate their MuJoCo-only world reconstruction residuals or any 64-substep local integration.',
        deferred='No new complete NMPC, morphology search, direct/residual PPO or provider campaign until these confounders are qualified.')
    hypotheses={
      'H1':dict(support='At k=0, 1->32 substeps reduces position error .003276853 to .000093981 m and velocity error .168852444 to .019350887 m/s.',
        weakening='At k=19/29 refinement does not reduce velocity mismatch; k=0 velocity error is nonmonotone versus MuJoCo.',
        resolved='Coarse discretization contribution established at k=0; no unique allocation over the closed loop.',
        confounders='k=0 16/32 velocity difference .007160190 m/s exceeds .002 screen; no continuous-time certificate.',
        smallest_next='One explicit 64-substep k=0 interval, using the same archived state/action.'),
      'H2':dict(support='Later initial position offsets are material; see each initial vector and projection residual below.',
        weakening='k=0 initial position offset is 1.67e-16 m and velocity is zero, so projection cannot explain its coarse error.',
        resolved='Cross-model initial output mismatch established; pure least-squares projection share unresolved.',
        confounders='No archived MuJoCo-only world reconstruction residual for these NMPC states; joint residual has different units.',
        smallest_next='Read-only MuJoCo projection/discretization forward-kinematic audit of these exact k=19/29 states.'),
      'H3':dict(support='Material late incremental velocity mismatch persists with exact same physical tension; vectors and task-scale ratios below.',
        weakening='Initial velocity mismatch is nonzero; projection removes physical state components. At k=0 discretization explains much of the coarse gap.',
        resolved='Different local responses supported; isolated intrinsic dynamics error unresolved.',
        confounders='Finite-grid uncertainty, state loss and cross-model kinematics; no model calibration guarantee.',
        smallest_next='After the reconstruction audit, compare both model responses from the physically reconstructed representable state under the same frozen tension in a separately authorized bounded probe.'),
      'H4':dict(support='Historical accumulated S5-A maxima .056479582 m / 1.299509910 m/s exceed these local errors.',
        weakening='Those trajectories have different controls and histories; local errors already remain material.',
        resolved='History contribution supported qualitatively; no unique additive share or controlled magnitude allocation.',
        confounders='Nonlinear divergent states, different control sequences and numerical fidelity.',
        smallest_next='Analyze a declared short frozen prefix only after the local representation/numerical ambiguity is resolved; avoid another full campaign.'),
      'H5':dict(support='No observed supporting evidence in the three admitted accepted plans.',
        weakening='All fresh N=1 results reproduce their archived accepted outputs to numerical precision; exact residuals below.',
        resolved='No prediction/replay inconsistency detected for these three cases; not a universal guarantee.',
        confounders='Only three accepted plans checked; final fallback excluded and other recovery-selection paths untested.',
        smallest_next='No repeat warranted for these cases; audit a distinct accepted recovery-selected plan only if another archive exposes inconsistent output.')}
    failed=read(DEST/'admission_failure/summary.json')['costs']
    costs=dict(summary['costs'],failed_admission_slots=failed['one_interval_allocations'],
        failed_admission_numerical_s=failed['numerical_s'],total_consumed_admission_slots=30,
        cumulative_recorded_numerical_s=summary['costs']['numerical_s']+failed['numerical_s'],
        setup_scalar_fmincon_smoke_solves=15,actual_integration_cap=20,remaining_actual_integrations_under_cap=5)
    packet=dict(schema='sorosim_s57_prediction_feedback_v1',source_freeze=summary['source_freeze'],
        task=dict(identity=index['task_identity'],duration_s=.35,control_period_s=.01,physics_timestep_s=.0005,
            position_scale_m=.01,holding_speed_scale_m_s=.02,holding_window_s=[.30,.35],new_physical_evaluation=False),
        candidate=summary['candidate'],source_candidate=index['candidate'],model_identity=index['model_identity'],
        source_execution=index['source_execution'],source_study=index['source_study'],source_index=summary['source_index'],
        resolutions=[1,4,8,16,32],checkpoints=compact,screen=summary['screen'],hypotheses=hypotheses,
        historical_equivalents=dict(S55='Different S5-A states/commands; not equivalent local integrations.',
            S56='Full-horizon fixed-sequence refinement is distinct; only archived S5.6 physical outputs reused.',
            failed_stage='15 completed pre-MATLAB admission failures; zero mathematical integrations; sealed costs retained.'),
        critical_times=dict(largest_original_velocity_innovation_time_s=.01,innovation_m_s=.16885244364876997,
            holding_scale_ratio=8.442622182438498,meaning='diagnostic scale before holding, not task violation',
            historical_first_holding_speed_failure_s=.33,historical_worst_holding_speed_time_s=.35,
            historical_worst_holding_speed_m_s=.04181409404195048,historical_speed_ratio=2.090704702097524),
        unsupported=['unique physical cause','continuous-time error certificate','new task pass','Agent superiority','real-time control'],
        agent_benefit='Unmeasured: packet available to later Harness study; no live Agent/provider call.',
        costs=costs,next_experiment=next_step,evidence='evidence/sorosim_s57/study/archive_manifest.json')
    summary.update(costs=costs,recommended_direction='E',next_experiment=next_step)
    atomic_json(DEST/'summary.json',summary)
    close(packet)


if __name__=='__main__':run()
