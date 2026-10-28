"""Validate frozen PHS model, all saved states and CSVs, with no integration."""
import argparse
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from phs2d_io import (TASK_DIR, RESEARCH_SHA, read, write, sha, array_sha, require,
    forbid_integration, base_path, load_model, joint_mapping, material_point, point,
    apply_force, restore, initial_row, state_columns, csv_columns, csv_values, states, ramp_force)


def artifact(base, reference):
    identity = reference['artifact_id']
    path = base/'evidence/artifacts'/(identity+'.json')
    require(sha(path) == identity, 'ORIGINAL_ARTIFACT_HASH:'+identity)
    return read(path)


def validate_case_label(entry,protocol):
    if entry['condition']=='equilibrium':
        require(entry['s']==.5 and entry['force_n']==0. and entry['stage']=='unloaded_baseline','UNLOADED_CASE_LABEL')
    else:
        expected=f"s{round(entry['s']*100):03d}_{'positive' if entry['force_n']>0 else 'negative'}"
        require(entry['condition']==expected and abs(entry['force_n'])==protocol['force_n'],'CASE_NAME_FORCE_DIRECTION')
        require(entry['stage']==('search' if entry['s'] in protocol['search_s'] else 'holdout'),'CASE_SEARCH_HOLDOUT_STAGE')
    require(entry['directory']==entry['condition'],'CONDITION_DIRECTORY_BINDING')


def validate_model(base):
    structure, task, payout = (read(base/p) for p in ('structure.json','task.json','payout_lengths.json'))
    dataset = read(base/'dataset.json')
    require(structure['source_commit'] == task['source_commit'] == dataset['source_commit'] == RESEARCH_SHA, 'RESEARCH_COMMIT')
    require(sha(base/'robot.xml') == structure['xml_sha256'] == dataset['xml_sha256'] == task['compiled_model_xml_sha256'], 'FROZEN_XML_HASH')
    candidate = artifact(base, structure['source_candidate'])
    assembly = artifact(base, structure['source_assembly'])
    require(candidate['configuration']['robot']['structure']['data'] == structure['design'], 'FROZEN_STRUCTURE_BINDING')
    require(assembly['candidate'] == structure['source_candidate'] and assembly['generation'] == structure['generation'], 'FROZEN_GENERATION_BINDING')
    require(assembly['payout_lengths_m'] == dataset['fixed_payout_lengths_m'], 'FIXED_PAYOUT_IDENTITY')
    model = load_model(base/'robot.xml')
    physics = structure['physics']
    mapping = joint_mapping(model, physics)
    require(mapping == read(base/'joint_map.json'), 'JOINT_ORDER')
    require(model.nq == model.nv == 144 and model.nu == 0 and model.ntendon == 4 and model.neq == 0, 'PASSIVE_DIMENSIONS')
    cells = physics['discretization']['cells']
    require(len(cells) == 9 and set(cells.values()) == {8} and sum(cells.values()) == 72, 'NINE_SEGMENTS_72_CELLS')
    segments = [c for c in structure['design']['components'] if c['kind'] == 'flexible_segment']
    require(len(segments) == 9 and abs(sum(c['length_m'] for c in segments)-.28) < 1e-15, 'FLEXIBLE_LENGTH')
    require(len([p for p in physics['parts'] if p['component'].startswith('guide_')]) == 8, 'EIGHT_REAL_GUIDES')
    require(sum(bool(p['dofs']) for p in physics['parts']) == 72, 'FLEXIBLE_PART_COUNT')
    xml = ET.parse(base/'robot.xml').getroot()
    roots = xml.findall('./worldbody/body')
    require(len(roots) == 1 and roots[0].get('name') == 'fixed_base' and not xml.findall('./actuator/*') and
            not xml.findall('./equality/*'), 'NO_EXTRA_ANCHOR_ACTUATOR_OR_TIP_FIXATION')
    require(np.array_equal(model.opt.gravity, task['protocol']['gravity']) and model.opt.timestep == .000125,
            'FROZEN_GRAVITY_TIMESTEP')
    require(np.array_equal(model.body_pos[model.body('fixed_base').id], task['protocol']['mount_position']), 'TOP_BASE_POSE')
    base_rotation=np.empty(9)
    mujoco.mju_quat2Mat(base_rotation,model.body_quat[model.body('fixed_base').id])
    require(np.allclose(base_rotation.reshape(3,3),task['protocol']['mount_rotation'],atol=1e-15,rtol=0),'VERTICAL_DOWN_MOUNT')
    tip=model.site('tip_site').id
    require(model.site_bodyid[tip]==model.body(physics['parts'][physics['tip']['body']]['entity']).id and
            np.array_equal(model.site_pos[tip],physics['tip']['position_m']),'ORIGINAL_TIP_SITE')
    require(model.opt.iterations == task['numerical_runtime_overrides']['iterations'] == 100 and
            model.opt.tolerance == task['numerical_runtime_overrides']['tolerance'] == 1e-10, 'RUNTIME_SOLVER_SETTINGS')
    require(payout['tendon_order'] == mapping['tendon_order'], 'PAYOUT_CHANNEL_ORDER')
    expected_payout = [assembly['payout_lengths_m'][t] for t in mapping['tendon_order']]
    require(expected_payout == payout['fixed_lengths_m'] == payout['actual_xml_upper_limits_m'], 'PAYOUT_VALUES')
    require(np.array_equal(model.tendon_range[:,1], expected_payout) and np.all(model.tendon_limited) and
            np.all(model.tendon_stiffness == 0), 'UNILATERAL_PASSIVE_LENGTH_LIMITS')
    require(np.array_equal(model.tendon_solref_lim, np.tile(task['protocol']['solreflimit'], (4,1))) and
            np.array_equal(model.tendon_solimp_lim, np.tile(task['protocol']['solimplimit'], (4,1))), 'TENDON_SOLVER_PARAMETERS')
    for index, tendon in enumerate(physics['tendons']):
        points = tendon['points']
        require(tendon['entity'] == mapping['tendon_order'][index] and model.tendon_num[index] == len(points) == 10, 'TENDON_GUIDE_COUNT')
        require(points[0]['body'] == -1 and points[0]['physical_binding']['attachment']['part'] == 'fixed_base', 'BASE_ONLY_START')
        require(physics['parts'][points[-1]['body']]['component'] == 'payload', 'PAYLOAD_ANCHOR')
        for offset, route in enumerate(points):
            wrap = model.tendon_adr[index] + offset
            require(model.wrap_type[wrap] == mujoco.mjtWrap.mjWRAP_SITE, 'ACTUAL_ROUTE_SITE')
            sid = int(model.wrap_objid[wrap])
            name = 'fixed_base' if route['body'] < 0 else physics['parts'][route['body']]['entity']
            require(model.site_bodyid[sid] == model.body(name).id and np.array_equal(model.site_pos[sid], route['position_m']), 'ROUTE_POSITION_BODY')
            if 0 < offset < len(points)-1:
                guide = physics['parts'][route['body']]['component']
                hole = route['physical_binding']['hole']
                require(guide.startswith('guide_') and hole and
                        structure['generation']['guide_hole_positions_m'][guide][hole] == route['position_m'], 'OWNED_GUIDE_HOLE')
    for part in physics['parts']:
        body = model.body(part['entity']).id
        parent='fixed_base' if part['parent']<0 else physics['parts'][part['parent']]['entity']
        require(model.body_parentid[body]==model.body(parent).id and
                np.array_equal(model.body_pos[body],part['position_m']),'PART_PARENT_LOCAL_POSITION')
        part_rotation=np.empty(9)
        mujoco.mju_quat2Mat(part_rotation,model.body_quat[body])
        require(np.allclose(part_rotation.reshape(3,3),part['rotation'],atol=1e-15,rtol=0),'PART_LOCAL_ROTATION')
        require(abs(model.body_mass[body]-part['mass_kg']) < 1e-15 and
                np.allclose(model.body_ipos[body], part['com_local_m'], atol=1e-15, rtol=0), 'MASS_COM:'+part['entity'])
        matrix = np.empty(9)
        mujoco.mju_quat2Mat(matrix, model.body_iquat[body])
        rotation = matrix.reshape(3,3)
        expected_inertia=np.asarray(part['inertia_com_local_kg_m2'])
        inertial=xml.find('.//body[@name="'+part['entity']+'"]/inertial')
        xml_inertia=np.fromstring(inertial.get('fullinertia'),sep=' ')
        require(np.array_equal(xml_inertia,expected_inertia[[0,1,2,0,0,1],[0,1,2,1,2,2]]), 'EXACT_XML_FULL_INERTIA')
        # MuJoCo's principal-axis decomposition differs by ~2e-15 kg*m^2 for the payload.
        # The XML tensor is checked exactly; this is only a compiled-representation diagnostic.
        require(np.allclose(rotation@np.diag(model.body_inertia[body])@rotation.T,
                expected_inertia, atol=5e-15, rtol=1e-8), 'COMPILED_INERTIA_REPRESENTATION:'+part['entity'])
        for axis, dof in enumerate(part['dofs']):
            joint = model.joint(physics['dofs'][dof]).id
            require(model.jnt_stiffness[joint] == part['stiffness_nm_rad'][axis] and
                    model.dof_damping[model.jnt_dofadr[joint]] == part['damping_nm_s_rad'][axis] and
                    model.qpos_spring[model.jnt_qposadr[joint]] == part['natural_rad'][axis], 'MATERIAL_STIFFNESS_VISCOSITY_NATURAL_CURVATURE')
    require(abs(model.body_mass.sum()-structure['total_physical_mass_kg']) < 1e-15, 'TOTAL_MASS')
    require(task['classification'] == dataset['classification'] == 'development_pass_not_registered_SELECT' and
            task['registered_acceptance'] is False, 'NO_FORMAL_SELECT_CLAIM')
    return model, structure, task, mapping, np.asarray(expected_payout)


def validate_trajectory(base, entry, model, structure, task, mapping, payout, baseline):
    validate_case_label(entry,task['protocol'])
    folder = base/entry['directory']
    require(folder.resolve().is_relative_to(base.resolve()), 'UNSAFE_TRAJECTORY_PATH')
    evidence = artifact(base, entry['raw_reference'])
    request = evidence['request']
    require(request['assembly'] == structure['source_assembly'] and request['replicate'] == 1 and
            request['record'] and request['perturbation'] == 0. and request['timestep'] == .000125, 'PRIMARY_CASE_IDENTITY')
    require(request['s'] == entry['s'] and request['force_n'] == entry['force_n'], 'FROZEN_FORCE_S')
    require(artifact(base, request['protocol']) == evidence['numerical_protocol'] == task['protocol'], 'TASK_PROTOCOL_IDENTITY')
    require(evidence['checks'] and all(evidence['checks'].values()), 'HISTORICAL_STABILITY_CHECKS')
    is_base = entry['condition'] == 'equilibrium'
    require(request['baseline'] == (None if is_base else read(base/'dataset.json')['common_baseline']), 'COMMON_BASELINE')
    if not is_base:
        evaluation = artifact(base, entry['evaluation_reference'])
        require(evaluation == read(folder/'original_evaluation.json') and evaluation['registered_acceptance'] == 'not_registered' and
                evaluation['status'] == 'development_pass' and evaluation['valid'], 'DEVELOPMENT_EVALUATION_IDENTITY')
        require(evaluation['loaded'] == entry['raw_reference'] and evaluation['assembly'] == request['assembly'] and
                evaluation['baseline'] == request['baseline'], 'EVALUATION_RECEIPT_BINDING')
        original = next(r for r in task['original_cases'] if r['s'] == entry['s'] and r['force_n'] == entry['force_n'])
        for name in ('s','force_n','point_dx_m','tip_xy_m','ratio','out_of_plane_m','worst_violation','status','valid'):
            require(original[name] == evaluation[name], 'FROZEN_RESULT_CHANGED:'+name)
    saved = states(folder/'states_timestep.npz')
    rows = saved['trajectory']
    require(rows.dtype == np.float64 and rows.shape == (32001,442) and np.isfinite(rows).all() and
            saved['columns'].tolist() == state_columns(), 'LOSSLESS_NPZ_SCHEMA')
    require(array_sha(rows[1:]) == entry['source_poststep_array_sha256'] == str(saved['source_poststep_array_sha256']), 'SOURCE_FLOAT64_ARRAY_IDENTITY')
    capacities=np.asarray([t['force_limit_n'] for t in structure['physics']['tendons']])
    require(np.all(rows[:,-4:]>=-1e-10) and np.all(rows[:,-4:]<=capacities), 'ORIGINAL_TENSION_DIRECTION_CAPACITY')
    require(evidence['every_timestep_trajectory']['reference'] == entry['raw_npz_reference'], 'NPZ_ARCHIVE_REFERENCE')
    first = read(folder/'initial_state.json')
    require(first['original_raw_reference'] == entry['raw_reference'] and first['snapshot_index'] == 0 and
            first['snapshot'] == evidence['samples'][0], 'REAL_T0_SOURCE')
    require(np.array_equal(rows[0], initial_row(first['snapshot'])), 'REAL_T0_VALUES')
    if not is_base:
        require(np.array_equal(rows[0,2:146], baseline['samples'][-1]['qpos']) and not np.any(rows[0,146:290]), 'UNLOADED_INITIAL_Q')
    dt = model.opt.timestep
    require(rows[0,0] == 0. and np.max(np.abs(rows[:,0]-np.arange(len(rows))*dt)) < 1e-10 and
            np.all(np.diff(rows[:,0]) > 0) and np.max(abs(np.diff(rows[:,0])-dt)) < 1e-11, 'CONTINUOUS_TRUE_TIME_GRID')
    for sample in evidence['samples']:
        index = round(sample['time_s']/dt)
        require(rows[index,0] == sample['time_s'] and np.array_equal(rows[index,2:146], sample['qpos']) and
                np.array_equal(rows[index,146:290], sample['qvel']), 'ORIGINAL_10MS_SAMPLES')
    binding = material_point(structure['physics'], entry['s'])
    spec=read(folder/'replay_spec.json')
    require(binding == entry['material_point_binding'] == spec['material_point_binding'], 'MATERIAL_POINT_BINDING')
    for key,target in [('robot_xml',base/'robot.xml'),('task',base/'task.json'),
                       ('payout_lengths',base/'payout_lengths.json'),('initial_state',folder/'initial_state.json')]:
        require((folder/spec[key]).resolve()==target.resolve() and target.is_file(),'PORTABLE_REPLAY_RELATIVE_PATH')
    data = mujoco.MjData(model)
    tip_id = model.site('tip_site').id
    expected_header = csv_columns(mapping)
    max_pose = 0.
    count = 0
    with (folder/'trajectory_timestep.csv').open(newline='',encoding='utf8') as stream, \
         (folder/'external_force_schedule.csv').open(newline='',encoding='utf8') as force_stream:
        reader, schedule = csv.reader(stream), csv.reader(force_stream)
        require(next(reader) == expected_header, 'CSV_COLUMNS')
        require(next(schedule) == ['step_index','interval_start_s','interval_end_s','force_world_x_n','force_world_y_n',
            'force_world_z_n','application_pre_state_x_m','application_pre_state_y_m','application_pre_state_z_m'], 'FORCE_SCHEDULE_COLUMNS')
        for index,row in enumerate(rows):
            csv_row = next(reader, None)
            require(csv_row is not None and len(csv_row) == len(expected_header), 'MISSING_CSV_ROW')
            values = np.asarray(csv_row,dtype=np.float64)
            require(np.isfinite(values).all(), 'CSV_NONFINITE')
            restore(model,data,row)
            tip = data.site_xpos[tip_id]
            rotation = data.site_xmat[tip_id].reshape(3,3)
            force_point = point(model,data,structure['physics'],binding)[0]
            error = max(np.max(np.abs(tip-saved['tip_position_m'][index])),
                        np.max(np.abs(rotation-saved['tip_rotation'][index])),
                        np.max(np.abs(force_point-saved['force_point_m'][index])))
            max_pose = max(max_pose,float(error))
            expected = np.asarray(csv_values(index,row,saved['tip_position_m'][index],saved['tip_rotation'][index],
                saved['force_point_m'][index],payout,saved['reconstructed_contact_count'][index]), dtype=np.float64)
            require(np.array_equal(values,expected), 'CSV_NPZ_SHARED_FLOAT64_FIELDS')
            require(data.ncon == saved['reconstructed_contact_count'][index], 'RECONSTRUCTED_CONTACTS')
            force = 0. if index == 0 else ramp_force(index-1,dt,entry['force_n'],task['protocol']['ramp_s'])
            require(row[1] == force, 'WORLD_X_SMOOTH_FORCE')
            previous = max(index-1,0)
            expected_force = np.asarray([index, rows[previous,0], row[0], force, 0., 0., *saved['force_point_m'][previous]])
            actual_force = next(schedule,None)
            require(actual_force is not None and np.array_equal(np.asarray(actual_force,dtype=np.float64),expected_force), 'FORCE_APPLICATION_PRE_STATE_PHASE')
            if index in (0,len(rows)-1):
                apply_force(model,data,structure['physics'],binding,entry['force_n'])
                position,bid = point(model,data,structure['physics'],binding)
                jac = np.zeros((3,model.nv))
                mujoco.mj_jac(model,data,jac,None,position,bid)
                require(np.max(abs(data.qfrc_applied-jac[0]*entry['force_n'])) < 1e-15, 'MOVING_MATERIAL_FORCE_MAP')
            count += 1
        require(next(reader,None) is None and next(schedule,None) is None, 'EXTRA_CSV_ROWS')
    require(max_pose <= 1e-12, 'SAVED_POSE_FORWARD_MISMATCH')
    require(count == entry['rows'] == 32001 and len(expected_header) == entry['csv_columns'], 'EXPORTED_ROW_COLUMN_COUNT')
    validation = read(folder/'validation.json')
    require(all(sha(folder/p) == identity for p,identity in validation['file_sha256'].items()), 'TRAJECTORY_FILE_HASHES')
    return dict(condition=entry['condition'], rows=count, csv_columns=len(expected_header), csv_bytes=entry['csv_bytes'],
                max_forward_pose_error=max_pose, max_csv_npz_shared_error=0., original_poststep_array_identity='passed',
                qacc_preserved=True, true_t0_snapshot=True, physics_steps=0)


def validate(package):
    forbid_integration()
    base = base_path(package)
    model, structure, task, mapping, payout = validate_model(base)
    dataset = read(base/'dataset.json')
    require(dataset['complete'] and len(dataset['trajectories']) == 11, 'ELEVEN_COMPLETE_TRAJECTORIES')
    expected = {'equilibrium', *[f's{round(s*100):03d}_{sign}' for s in (.3,.4,.5,.6,.7) for sign in ('positive','negative')]}
    require({e['condition'] for e in dataset['trajectories']} == expected, 'TEN_LOAD_CASES_PLUS_BASELINE')
    require(task['protocol']['search_s'] == [.3,.5,.7] and task['protocol']['holdout_s'] == [.4,.6], 'SEARCH_HOLDOUT_SPLIT')
    baseline = artifact(base, dataset['common_baseline'])
    results, failures = [], []
    for entry in dataset['trajectories']:
        try:
            result = validate_trajectory(base,entry,model,structure,task,mapping,payout,baseline)
            results.append(result)
            print(json.dumps(dict(condition=entry['condition'], validation='passed', physics_steps=0)), flush=True)
        except Exception as exc:
            failures.append(dict(condition=entry['condition'],error=str(exc)))
    return dict(status='passed' if not failures else 'failed', results=results, failures=failures, physics_steps=0,
        classification='development_pass_not_registered_SELECT', xml_sha256=sha(base/'robot.xml'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--report',type=Path)
    args = p.parse_args()
    try: result = validate(args.package)
    except Exception as exc: result = dict(status='failed', failures=[str(exc)], physics_steps=0)
    if args.report: write(args.report,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status'] != 'passed': raise SystemExit(1)


if __name__ == '__main__': main()
