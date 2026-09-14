"""Saved signal authority: names, units, phase, entities and evidence location."""
import math
from tools.state_io import read
from tools.artifact_tools import file_hash

SIGNALS={
    'solver_contact_count':dict(units='1',phase='solver',time_field='solver_time_s',entity='contact'),
    'qpos_rad':dict(units='rad',phase='post_step_state',time_field='time_s',entity='joint'),
    'qvel_rad_s':dict(units='rad/s',phase='post_step_state',time_field='time_s',entity='joint'),
    'solver_actuator_force_n':dict(units='N',phase='solver',time_field='solver_time_s',entity='tendon',tension_sign=-1),
    'solver_tendon_length_m':dict(units='m',phase='solver',time_field='solver_time_s',entity='tendon'),
    'command_m':dict(units='m',phase='solver',time_field='solver_time_s',entity='tendon'),
    'tip_m':dict(units='m',phase='post_step_state',time_field='time_s',entity='tip',frame='world'),
}


class SavedObservation:
    def __init__(self, root, registry, result_ref, backend):
        from tools.public_services import checked_path
        from tools.trajectory_diagnosis import load_rows
        from tools.model_provider import SharedModel
        path=checked_path(root,registry,result_ref);self.result=read(path)
        if self.result.get('backend')!=backend:raise ValueError('BACKEND_MISMATCH')
        refs=[result_ref]+[(path.parent/name).relative_to(root).as_posix() for name in ('shared_input.json','trajectory.json.gz')]
        paths=[checked_path(root,registry,ref) for ref in refs]
        self.hashes={ref:file_hash(p) for ref,p in zip(refs,paths)}
        self.shared=read(paths[1]);self.rows=load_rows(paths[2]);self.trajectory_ref=refs[2]
        self.backend=backend;self.model=SharedModel(self.shared,backend,self.hashes[refs[1]],self.result.get('model_id'))

    def query(self, signal, start=None, end=None):
        if signal not in SIGNALS:raise ValueError('UNKNOWN_SIGNAL: '+signal)
        if start is not None and end is not None and end<start:raise ValueError('REVERSED_TIME_INTERVAL')
        spec=dict(SIGNALS[signal]);field=spec['time_field'];samples=[];missing=[]
        if self.backend=='matlab':spec['phase']='sampled_interpolated_'+('solver' if field=='solver_time_s' else 'state')
        for i,row in enumerate(self.rows):
            if field not in row:missing.append(i);continue
            t=row[field]
            if not isinstance(t,(int,float)) or not math.isfinite(t):raise ValueError('INVALID_SIGNAL_TIME')
            if (start is not None and t<start-1e-10) or (end is not None and t>end+1e-10):continue
            if signal not in row:missing.append(i);continue
            samples.append(dict(sample_index=i,time_s=t,value=row[signal]))
        return dict(status='MISSING_DATA' if missing or not samples else 'AVAILABLE',signal=signal,
            specification=spec,samples=samples,missing_sample_indices=missing,
            evidence_ref=self.trajectory_ref,source_hashes=self.hashes)
