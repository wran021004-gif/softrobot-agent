"""Read-only PHS trace diagnostics; no integration or Store ownership."""
import gzip,json
import numpy as np


def historical_tail(path):
    package=json.loads(gzip.decompress(path.read_bytes()));v=package['state'];art=package['artifacts']
    rows=[]
    for ref in v['results'].values():
        raw=art[ref['artifact_id']]
        if raw['request']['kind']!='equilibrium' or raw['request']['protocol']!=v['protocol']:continue
        tail=[r for r in raw['samples'] if r['time_s']>=3.75-1e-8]
        t=np.array([r['time_s'] for r in tail]);res=np.array([r['static_balance_inf_nm'] for r in tail])
        q=np.array([r['qpos'] for r in tail]);vel=np.array([r['qvel'] for r in tail])
        peak=int(np.argmax(res));freq=np.fft.rfftfreq(len(t),np.median(np.diff(t)))
        spectrum=abs(np.fft.rfft(res-res.mean()));order=np.argsort(spectrum[1:])[-3:]+1
        tensions=np.array([r['tensions_n'] for r in tail]);active=tensions>1e-6
        rows.append(dict(force_n=raw['request']['force_n'],reference=ref,tail_count=len(t),peak_time_s=float(t[peak]),
            peak_residual_nm=float(res[peak]),terminal_residual_nm=float(res[-1]),median_residual_nm=float(np.median(res)),
            sampled_spectral_peaks_hz=freq[order].tolist(),sample_frequency_hz=100.,nyquist_hz=50.,
            frequency_limitation='10ms saved grid aliases faster oscillations; cannot infer true high frequency',
            peak_qvel_joint=int(np.argmax(abs(vel[peak]))),peak_qvel_rad_s=float(np.max(abs(vel[peak]))),
            max_joint_position_span_rad=float(np.max(np.ptp(q,axis=0))),
            top_velocity_joints=np.argsort(np.max(abs(vel),axis=0))[-6:].tolist(),
            sampled_acceleration_proxy_max_rad_s2=float(np.max(abs(np.diff(vel,axis=0)/np.diff(t)[:,None]))),
            actual_acceleration='not saved in old evidence; do not relabel finite differences as actual acceleration',
            active_switches=np.sum(np.diff(active.astype(int),axis=0)!=0,axis=0).tolist(),
            tension_ranges_n=np.array([tensions.min(axis=0),tensions.max(axis=0)]).tolist(),
            length_excess_ranges_m=np.array([[min(r['length_change'][i] for r in tail),max(r['length_change'][i] for r in tail)] for i in range(tensions.shape[1])]).tolist(),
            solver_iterations=[int(max(r['solver_iterations'])) for r in tail],
            unavailable=['per-joint old static residual','original qacc_warmstart','actual saved qacc','solver cost history']))
    return dict(status='read_only_historical_diagnostic',rows=rows,old_verdict='unchanged_failed_P0',
        residual_definition='At fixed q set qvel=0 and recompute MuJoCo soft constraint force; qpassive + qapplied - qbias + qconstraint. This is soft forward acceleration residual, not ideal KKT residual.',
        caveat='Original snapshot copied warmstart into the zero-velocity shadow. Reconstructing cold states cannot recover that exact hidden solver state.')
