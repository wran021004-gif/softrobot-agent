"""Export only the frozen PHS witness; immutable SQLite reads, zero integration."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from phs2d_io import (TASK_DIR, RESEARCH_SHA, read, write, sha, array_sha, require,
    forbid_integration, load_model, joint_mapping, material_point, point, restore,
    initial_row, state_columns, csv_columns, csv_values, ramp_force)


class FrozenSource:
    """No Store constructor, dispatch, mutable connection, or scientific execution."""
    def __init__(self, root, cache):
        self.root = Path(root).resolve()
        self.evidence = self.root/'evidence/phs2d_round3_20261028'
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root).decode().strip() == RESEARCH_SHA,
                'FROZEN_RESEARCH_HEAD_CHANGED')
        self.design = json.loads(self.file('solution/design.json'))
        self.study = json.loads(self.file('study_v2.json'))
        manifest = json.loads(self.file('store_v2/archive_manifest.json'))
        self.members = {r['name']: r for r in manifest['members']}
        path = self.root/'runs/phs2d-round3b/store/platform.sqlite'
        self.db = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)

    def file(self, relative):
        path = self.evidence/relative
        committed = subprocess.check_output(['git', 'show', RESEARCH_SHA+':'+path.relative_to(self.root).as_posix()], cwd=self.root)
        require(path.read_bytes() == committed, 'SOURCE_FILE_CHANGED:'+relative)
        return committed

    def artifact(self, ref, destination=None):
        aid = ref['artifact_id']
        suffix = '.json' if ref['media_type'] == 'application/json' else '.bin'
        member = self.members['artifacts/'+aid+suffix]
        row = self.db.execute('SELECT rowid,length(body),media FROM artifacts WHERE id=?', (aid,)).fetchone()
        require(row is not None and row[1] == member['bytes'] and row[2] == ref['media_type'], 'SOURCE_ARTIFACT_METADATA')
        if suffix == '.json':
            data = self.db.execute('SELECT body FROM artifacts WHERE id=?', (aid,)).fetchone()[0]
            require(hashlib.sha256(data).hexdigest() == member['sha256'] == aid, 'SOURCE_ARTIFACT_HASH')
            if destination:
                destination.mkdir(parents=True, exist_ok=True)
                (destination/(aid+suffix)).write_bytes(data)
            return json.loads(data)
        target = self.cache/(aid+'.npz')
        if not target.exists():
            with self.db.blobopen('artifacts', 'body', row[0], readonly=True) as blob, target.open('xb') as stream:
                while block := blob.read(4*1024*1024):
                    stream.write(block)
        require(sha(target) == member['sha256'] == aid, 'SOURCE_NPZ_HASH')
        return target


def fixed_structure(source, base):
    d = source.design
    (base/'robot.xml').write_bytes(source.file('solution/model.xml'))
    require(sha(base/'robot.xml') == d['exact_model_sha256'], 'EXACT_XML_SHA')
    model = load_model(base/'robot.xml')
    mapping = joint_mapping(model, d['physics'])
    payout = [d['payout_lengths_m'][t] for t in mapping['tendon_order']]
    require(model.nq == model.nv == 144 and model.nu == 0 and model.ntendon == 4, 'PASSIVE_MODEL_DIMENSIONS')
    require(np.array_equal(model.tendon_range[:, 1], payout) and np.all(model.tendon_limited), 'XML_FIXED_UPPER_LIMITS')
    write(base/'joint_map.json', mapping)
    structure = dict(version='phs2d_structure_v1', source_commit=RESEARCH_SHA,
        source_design_sha256=hashlib.sha256(source.file('solution/design.json')).hexdigest(),
        label=d['label'], source_assembly=d['reference'], source_candidate=d['candidate'],
        design=d['configuration']['robot']['structure']['data'], generation=d['generation'], physics=d['physics'],
        total_physical_mass_kg=d['total_physical_mass_kg'], xml_sha256=d['exact_model_sha256'],
        interpretation='Discrete flexible mechanism ideal MuJoCo model; not manufacturing CAD.')
    structure['native_compiled_bodies'] = [dict(entity=part['entity'],
        mass_kg=float(model.body(part['entity']).mass[0]),
        com_local_m=model.body(part['entity']).ipos.tolist(),
        inertia_principal_kg_m2=model.body(part['entity']).inertia.tolist(),
        inertia_frame_quaternion_wxyz=model.body(part['entity']).iquat.tolist()) for part in d['physics']['parts']]
    write(base/'structure.json', structure)
    write(base/'payout_lengths.json', dict(version='passive_fixed_payout_v1',
        tendon_order=mapping['tendon_order'], fixed_lengths_m=payout,
        actual_xml_upper_limits_m=model.tendon_range[:, 1].tolist(), offsets_m=d['offsets_m'],
        convention='Unilateral tendon length upper limit; no active actuator or applied pretension.'))
    task = dict(version='phs2d_benchmark_task_v1', source_commit=RESEARCH_SHA,
        classification='development_pass_not_registered_SELECT', registered_acceptance=False,
        protocol=d['protocol'], effective_discretization=d['physics']['discretization'],
        compiled_model_xml_sha256=d['exact_model_sha256'], source_assembly=d['reference'],
        numerical_runtime_overrides=dict(iterations=100, tolerance=1e-10),
        observation_phase=dict(raw='Post mj_step and following mj_forward; generalized force mapped at preceding state. '
            'At 10 ms snapshots original sampler additionally remaps force after recording.',
            initial='Exact saved original t=0 snapshot; qacc, lengths, tensions are original snapshot observations.',
            pose='Independent mj_forward on detached saved qpos/qvel; recomputed reactions are never exported as original tension.'),
        original_cases=[{k:v for k,v in case.items() if k not in ('qpos','positions','baseline_positions','every_timestep_trajectory')}
                        for case in d['cases']],
        coordinate_frame='World SI; fixed Base at [0,0,0.5], local +x points down under frozen mount_rotation; force along world x.',
        material_coordinate='Cumulative flexible length only, excludes rigid spacers; Tip measured at original tip_site.')
    task['native_compiled_options'] = {}
    for key in dir(model.opt):
        if key.startswith('_'): continue
        value = getattr(model.opt,key)
        if isinstance(value,np.ndarray): value = value.tolist()
        elif isinstance(value,(int,float,np.integer,np.floating)): value = value.item() if hasattr(value,'item') else value
        else: continue
        task['native_compiled_options'][key] = value
    write(base/'task.json', task)
    for relative, target in [('numerical_comparison.json','evidence/numerical_comparison.json'),
                             ('curvature_evidence.json','evidence/curvature_evidence.json'),
                             ('solution_mechanism.png','previews/source_solution_mechanism.png'),
                             ('task_validation.png','previews/source_task_validation.png'),
                             ('math_vs_physics.png','previews/source_math_vs_physics.png')]:
        path = base/target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.file(relative))
    checks = [x for x in source.study['dynamic_sets'] if x['label'] == d['label'] and x.get('replicate') in (2,3)]
    write(base/'evidence/numerical_validation.json', dict(source_commit=RESEARCH_SHA,
        source_study_sha256=hashlib.sha256(source.file('study_v2.json')).hexdigest(),
        classification='Historical half-step and perturbation checks; not primary presentation trajectories.',
        results=[{k:v for k,v in x.items() if k!='rows'} | dict(rows=[{k:v for k,v in r.items()
            if k not in ('qpos','positions','baseline_positions','every_timestep_trajectory')} for r in x['rows']]) for x in checks]))
    return model, mapping


def export_case(source, base, entry, model, mapping, baseline):
    name = entry['condition']
    folder = base/entry['directory']
    if (folder/'validation.json').exists():
        saved = read(folder/'validation.json')
        require(all(sha(folder/p) == identity for p,identity in saved['file_sha256'].items()), 'PARTIAL_EXPORT_CHANGED')
        return saved['entry']
    folder.mkdir(parents=True, exist_ok=True)
    artifacts = base/'evidence/artifacts'
    raw = source.artifact(entry['raw_reference'], artifacts)
    d, physics = source.design, source.design['physics']
    request = raw['request']
    require(request['assembly'] == d['reference'] and request['replicate'] == 1 and request['record'] and
            request['perturbation'] == 0 and request['timestep'] == .000125, 'PRIMARY_TRAJECTORY_BINDING')
    require(raw['numerical_protocol'] == d['protocol'], 'FROZEN_NUMERICAL_PROTOCOL')
    require(request['s'] == entry['s'] and request['force_n'] == entry['force_n'], 'CASE_LOAD_BINDING')
    require(request['baseline'] == (None if name == 'equilibrium' else baseline['reference']), 'COMMON_BASELINE_BINDING')
    for ref in (request['assembly'], request['protocol'], request['source']):
        source.artifact(ref, artifacts)
    original = source.artifact(raw['every_timestep_trajectory']['reference'])
    with np.load(original, allow_pickle=False) as archive:
        post = archive['trajectory']
        columns = archive['columns']
    require(post.dtype == np.float64 and post.shape == (32000,442) and
            columns.tolist() == state_columns() and np.isfinite(post).all(), 'ORIGINAL_NPZ_SCHEMA')
    snapshot = raw['samples'][0]
    require(snapshot['time_s'] == 0. and snapshot['force_n'] == 0., 'TRUE_T0_SNAPSHOT_REQUIRED')
    if name != 'equilibrium':
        np.testing.assert_array_equal(snapshot['qpos'], baseline['final']['qpos'])
        require(not np.any(snapshot['qvel']), 'LOADED_INITIAL_VELOCITY')
        evaluation = source.artifact(entry['evaluation_reference'], artifacts)
        require(evaluation['loaded'] == entry['raw_reference'] and evaluation['baseline'] == baseline['reference'] and
                evaluation['assembly'] == d['reference'] and evaluation['status'] == 'development_pass' and
                evaluation['registered_acceptance'] == 'not_registered', 'ORIGINAL_DEVELOPMENT_EVALUATION')
        write(folder/'original_evaluation.json', evaluation)
    trajectory = np.vstack([initial_row(snapshot), post])
    source_array_sha = array_sha(post)
    del post
    np.testing.assert_array_equal(trajectory[-1, 2:146], raw['samples'][-1]['qpos'])
    write(folder/'initial_state.json', dict(original_raw_reference=entry['raw_reference'],
        snapshot_index=0, snapshot=snapshot, source_commit=RESEARCH_SHA))
    binding = material_point(physics, entry['s'])
    write(folder/'replay_spec.json', dict(version='phs2d_explicit_replay_v1', s=entry['s'],
        force_n=entry['force_n'], material_point_binding=binding, initial_state='initial_state.json',
        robot_xml='../robot.xml', task='../task.json', payout_lengths='../payout_lengths.json',
        source_raw_reference=entry['raw_reference'], source_npz_reference=raw['every_timestep_trajectory']['reference']))
    data = mujoco.MjData(model)
    tip_id = model.site('tip_site').id
    positions = np.empty((32001,3), dtype=np.float64)
    rotations = np.empty((32001,3,3), dtype=np.float64)
    force_points = np.empty((32001,3), dtype=np.float64)
    contacts = np.empty(32001, dtype=np.int32)
    payout = np.array([d['payout_lengths_m'][t] for t in mapping['tendon_order']])
    begin = time.monotonic()
    with (folder/'trajectory_timestep.csv').open('w', newline='', encoding='utf8') as stream, \
         (folder/'external_force_schedule.csv').open('w', newline='', encoding='utf8') as forces:
        writer = csv.writer(stream)
        writer.writerow(csv_columns(mapping))
        schedule = csv.writer(forces)
        schedule.writerow(['step_index','interval_start_s','interval_end_s','force_world_x_n','force_world_y_n',
                           'force_world_z_n','application_pre_state_x_m','application_pre_state_y_m','application_pre_state_z_m'])
        for index, row in enumerate(trajectory):
            expected = 0. if index == 0 else ramp_force(index-1, model.opt.timestep, entry['force_n'], d['protocol']['ramp_s'])
            require(row[1] == expected, 'ORIGINAL_FORCE_RAMP')
            restore(model, data, row)
            positions[index] = data.site_xpos[tip_id]
            rotations[index] = data.site_xmat[tip_id].reshape(3,3)
            force_points[index] = point(model, data, physics, binding)[0]
            contacts[index] = data.ncon
            values = csv_values(index, row, positions[index], rotations[index], force_points[index], payout, contacts[index])
            writer.writerow([format(float(v), '.17g') if not isinstance(v,int) else v for v in values])
            previous = max(index-1, 0)
            force_values = [index, trajectory[previous,0], row[0], row[1], 0., 0., *force_points[previous]]
            schedule.writerow([format(float(v), '.17g') for v in force_values])
            if index and index%8000 == 0:
                print(json.dumps(dict(condition=name, forwarded_rows=index, elapsed_s=round(time.monotonic()-begin,1), physics_steps=0)), flush=True)
    np.savez_compressed(folder/'states_timestep.npz', trajectory=trajectory, columns=columns,
        tip_position_m=positions, tip_rotation=rotations, force_point_m=force_points,
        reconstructed_contact_count=contacts, source_poststep_array_sha256=np.array(source_array_sha))
    with np.load(folder/'states_timestep.npz', allow_pickle=False) as saved:
        require(array_sha(saved['trajectory'][1:]) == source_array_sha, 'LOSSLESS_SOURCE_EXPORT')
        np.testing.assert_array_equal(saved['trajectory'][0], initial_row(snapshot))
    result = dict(entry, rows=32001, csv_columns=len(csv_columns(mapping)),
        csv_bytes=(folder/'trajectory_timestep.csv').stat().st_size,
        npz_bytes=(folder/'states_timestep.npz').stat().st_size,
        timestep_s=model.opt.timestep, duration_s=4., actual_last_engine_time_s=float(trajectory[-1,0]),
        raw_npz_reference=raw['every_timestep_trajectory']['reference'],
        raw_npz_archive_member='artifacts/'+raw['every_timestep_trajectory']['reference']['artifact_id']+'.bin',
        source_poststep_array_sha256=source_array_sha, material_point_binding=binding)
    validation = dict(status='exported_losslessly', source_commit=RESEARCH_SHA, entry=result,
        true_t0_snapshot=True, original_poststep_float64_array_unchanged=True, qacc_preserved_in_npz=True,
        physics_steps=0, forward_reconstructions=32001, csv_float_format='.17g (binary64 round-trip safe)',
        file_sha256={p:sha(folder/p) for p in ('trajectory_timestep.csv','states_timestep.npz','external_force_schedule.csv',
                                             'initial_state.json','replay_spec.json')})
    write(folder/'validation.json', validation)
    print(json.dumps(dict(condition=name, status='exported', csv_bytes=result['csv_bytes'], physics_steps=0)), flush=True)
    return result


def export(source_root, package, cache, only=None):
    forbid_integration()
    require(not (Path(package)/'phs2d_delivery_report.json').exists(),'EXPORT_REQUIRES_UNPUBLISHED_STAGING')
    source = FrozenSource(source_root, cache)
    base = Path(package).resolve()/TASK_DIR
    base.mkdir(parents=True, exist_ok=True)
    require(shutil.disk_usage(base).free >= 12*1024**3, 'INSUFFICIENT_STAGING_SPACE')
    model, mapping = fixed_structure(source, base)
    d = source.design
    primary = [x for x in source.study['dynamic_sets'] if x['label'] == d['label'] and x.get('replicate') == 1]
    require(len(primary) == 2 and primary[0]['baseline'] == primary[1]['baseline'], 'ONE_FROZEN_BASELINE')
    base_ref = primary[0]['baseline']
    raw_base = source.artifact(base_ref, base/'evidence/artifacts')
    np.testing.assert_array_equal(raw_base['samples'][-1]['qpos'], d['baseline']['qpos'])
    baseline = dict(reference=base_ref, final=raw_base['samples'][-1])
    entries = [dict(condition='equilibrium', directory='equilibrium', s=.5, force_n=0., stage='unloaded_baseline', raw_reference=base_ref)]
    for case in sorted(d['cases'], key=lambda r:(r['s'],-r['force_n'])):
        name = f"s{round(case['s']*100):03d}_{'positive' if case['force_n']>0 else 'negative'}"
        entries.append(dict(condition=name, directory=name, s=case['s'], force_n=case['force_n'],
            stage='search' if case['s'] in d['protocol']['search_s'] else 'holdout',
            raw_reference=case['reference'], evaluation_reference=case['evaluation']))
    results = []
    for entry in entries:
        if only and entry['condition'] != only:
            continue
        results.append(export_case(source, base, entry, model, mapping, baseline))
    source.artifact(d['candidate'], base/'evidence/artifacts')
    write(base/'dataset.json', dict(version='phs2d_saved_witness_v1', source_commit=RESEARCH_SHA,
        xml_sha256=d['exact_model_sha256'], source_assembly=d['reference'],
        common_baseline=base_ref, fixed_payout_lengths_m=d['payout_lengths_m'],
        classification='development_pass_not_registered_SELECT', actual_mj_step_calls=0,
        trajectories=results, complete=len(results)==11))
    source.db.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--only')
    args = p.parse_args()
    export(args.source, args.package, args.cache, args.only)


if __name__ == '__main__':
    main()
