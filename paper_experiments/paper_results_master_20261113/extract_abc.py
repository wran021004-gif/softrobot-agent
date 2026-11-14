"""Read existing summaries and exact immutable artifacts; never execute research.

Run from any directory with Python's standard library. Only the three ABC CSVs
are written. Store connections are read-only; trajectories are never traversed.
"""
import csv
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
B1 = HERE.parent / 'ab_batch1_20261114'
B2 = HERE.parent / 'ab_batch2_20261114'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def output(name, data, fields):
    with (HERE / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows({k: js(v) if isinstance(v, (dict, list)) else v for k, v in r.items()} for r in data)


def uri(store, ref):
    return str(store) + '#artifacts/' + (ref['artifact_id'] if isinstance(ref, dict) else ref)


def artifact(store, ref):
    p = Path(store)
    p = p if p.suffix == '.sqlite' else p / 'platform.sqlite'
    with sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True) as c:
        value = c.execute('SELECT body FROM artifacts WHERE id=?',
                          (ref['artifact_id'] if isinstance(ref, dict) else ref,)).fetchone()
    if value is None:
        raise KeyError((str(p), ref))
    return json.loads(value[0])


def source_result(source):
    store, ref = source.split('#artifacts/')
    return artifact(store, ref), store


def trace(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


HISTORY = {r['task_id']: r for r in rows(HERE / 'ALL_TASK_RESULTS.csv')}
CASES = rows(HERE / 'TASK_CASE_RESULTS.csv')
COSTS = rows(HERE / 'RESOURCE_COSTS.csv')
MAIN = {(r['task_id'], r['method']): r for r in rows(B2 / 'batch_results.csv')
        if r['record_role'] != 'targeted_supplement'}
# The repaired first batch is authoritative, even when duplicated in batch two.
MAIN.update({(r['task_id'], r['method']): r for r in rows(B1 / 'batch1_results_repaired.csv')})
assert len(MAIN) == 33
DATA = {}
for key, r in MAIN.items():
    if key[1] != 'C':
        folder = Path(r['final_artifact']).parent
        DATA[key] = (read(folder / 'result.json'), read(folder / 'config.json'), folder)


def version(key):
    r = MAIN[key]
    return js(dict(extraction_base_commit='94f3ae60c', snapshot_date='2026-11-14',
                   summary_scope='repaired_batch1' if key[0] in ['T01','T04','T07','PHS-2D'] else 'local_batch2_not_git_tracked',
                   original_version=json.loads(r['historical_version'])
                   if r['historical_version'] else dict(core_commit='56cc418', config=str(DATA[key][2] / 'config.json'))))


def build_status():
    result = []
    for key, r in sorted(MAIN.items()):
        tid, method = key
        science = r['scientific_result']
        status = {'PASS': 'PASS', 'VALID_FAILURE': 'EVALUATED_NOT_PASS',
                  'INITIAL_CONDITION_FAILED': 'EVALUATED_NOT_PASS',
                  'QUALIFICATION_FAILED': 'EVALUATED_NOT_PASS', 'INCOMPLETE': 'INCOMPLETE'}[science]
        passed, total = map(int, r['required_pass'].split('/'))
        assert status != 'PASS' or passed == total
        cp = ct = ''
        detail = dict(scientific_result=science, raw_run_status=r.get('raw_run_status') or r['status'])
        if method == 'C':
            assert r['run_id'] == HISTORY[tid]['run_id']
            exact = [x for x in COSTS if x['run_id'] == r['run_id']]
            embedded = json.loads(r.get('cost_records') or '[]')
            assert all(x['run_id'] == r['run_id'] for x in embedded)
            detail['cost_match_run_id'] = r['run_id'] if exact else None
            detail['cost_source'] = str(HERE / 'RESOURCE_COSTS.csv') + '#run_id=' + r['run_id']
            detail['cost_match_count'] = len(exact)
            detail['cost_missing_reason'] = '' if len(exact) == 1 else 'missing_or_ambiguous_exact_run_cost; no scalar imputation'
            controls = [x for x in CASES if x['run_id'] == r['run_id'] and x['condition_role'] == 'control']
            if controls:
                cp, ct = sum(x['passed'].lower() == 'true' for x in controls), len(controls)
            classification = HISTORY[tid]['source_classification']
            if tid == 'T08':
                classification = 'development_valid; development_not_registered_SELECT'
            if tid == 'PHS-2D':
                detail['structure_scope'] = 'seven_segment_four_tendon; independent nine-segment study excluded'
        else:
            raw, config, folder = DATA[key]
            detail.update(selection_origin=raw.get('selection_origin'), stop_reason=raw.get('stop_reason'),
                          block_reason=raw.get('block_reason'))
            if science == 'INCOMPLETE':
                detail['interpretation'] = 'No complete required-task conclusion; partial evaluated conditions retained, not a physical-failure count.'
            stages = raw.get('required_stage_outcomes', {})
            if stages:
                detail['stage_outcomes'] = stages
            if science == 'QUALIFICATION_FAILED':
                detail['interpretation'] = 'Qualification failure; measured stages retained separately from unexecuted or unqualified metrics.'
                detail['qualification_failures'] = {cid: {stage: [k for k,v in q.get('checks',{}).items() if v is False]
                    for stage,q in e.get('qualifications',{}).items() if q.get('passed') is False}
                    for cid,e in raw.get('required_case_results',{}).items()}
                detail['recorded_issue_codes'] = sorted({part for e in raw.get('evaluations',[]) for issue in e.get('diagnostics',{}).get('issues',[])
                    for part in issue.get('reason','').split(';') if part})
            if tid == 'T08' and method == 'A':
                detail['interpretation'] = 'Wall-clock stop before full confirmation; integration total unknown.'
            protocol = config.get('protocol') or {}
            control_ids = [x['condition_id'] for x in protocol.get('cases', []) if x['role'] == 'control']
            if control_ids:
                ct = len(control_ids)
                observed = raw.get('control_case_results', {})
                cp = sum((x or {}).get('accepted') is True for x in observed.values()) if any(observed.values()) else ''
                if not observed:
                    detail['control_missing_reason'] = 'No control evaluation for selected candidate'
            classification = 'formal_paired_ab; ' + protocol.get('source_status', 'historical_development')
        result.append(dict(task_id=tid, task_name=HISTORY[tid]['task_name'], method=method,
                           method_name={'A': 'LLM only', 'B': 'LLM + direct math tools', 'C': 'historical FULL'}[method],
                           status=status, status_detail=js(detail), required_pass=passed, required_total=total,
                           required_pass_ratio=passed / total, control_pass=cp, control_total=ct,
                           run_id=r['run_id'], source_classification=classification,
                           source_reference=js(dict(summary=str(B1 / 'batch1_results_repaired.csv') if tid in ['T01','T04','T07','PHS-2D'] else str(B2 / 'batch_results.csv'), result=r['final_artifact'])),
                           source_version=version(key)))
    return result


METRIC_FIELDS = 'task_id method run_id condition_id condition_role metric_name metric_value metric_unit acceptance_operator acceptance_threshold normalized_violation metric_pass evaluation_status source_artifact source_version missing_reason acceptance_tolerance normalization_source candidate_id'.split()


def operator(c):
    d = c.get('direction', c.get('bound_type'))
    return {'maximum': '<' if c.get('strict') else '<=', 'minimum': '>' if c.get('strict') else '>=',
            'upper': '<=', 'lower': '>='}.get(d, '')


def unit(name):
    for suffix, u in [('_m_s', 'm/s'), ('_nm', 'N.m'), ('_m', 'm'), ('_s', 's'), ('_n', 'N'), ('_rad', 'rad')]:
        if name.endswith(suffix):
            return u
    return {'max_position_error': 'm', 'max_tool_axis_angle_error': 'rad'}.get(name, '')


def measurements(acc):
    """Evaluator-owned constraints, then additional named scalar measurements."""
    found = {}
    for name, c in acc.get('constraint_margins', acc.get('constraints', {})).items():
        found[name] = dict(value=c.get('observed'), unit=c.get('units'), op=operator(c), threshold=c.get('limit'),
                           passed=acc.get('checks', {}).get(name, acc.get('components', {}).get('evaluator:' + name, {}).get('passed')),
                           tolerance=c.get('tolerance'), pointer='/constraint_margins/' + name)
    for ob in acc.get('constraint_observations', []):
        name = ob['constraint_id'].removeprefix('evaluator:')
        found[name] = dict(value=ob.get('observed_value'), unit=ob.get('unit'), op=operator(ob),
                           threshold=ob.get('bound'), passed=ob.get('passed'), normalized=ob.get('normalized_violation'),
                           normalization=ob.get('normalization_source'), pointer=ob.get('source_pointer'))
    for name, c in acc.get('components', {}).items():
        if not name.startswith('evaluator:'):
            continue
        name = name.removeprefix('evaluator:')
        if name not in found:
            found[name] = dict(value=c.get('value'), unit=c.get('unit'), threshold=c.get('limit'), passed=c.get('passed'),
                               op='', pointer='/components/evaluator:' + name, missing_reason=c.get('missing_reason'))
    for name, val in acc.get('metrics', {}).items():
        if not isinstance(val, (dict, list)) and name not in found:
            found[name] = dict(value=val, unit=unit(name), pointer='/metrics/' + name)
    return found


def build_metrics():
    result, templates = [], {}

    def emit(key, cid, role, name, m, source, status, candidate='', missing=''):
        value = m.get('value')
        result.append(dict(task_id=key[0], method=key[1], run_id=MAIN[key]['run_id'], condition_id=cid,
                           condition_role=role, metric_name=name, metric_value=value, metric_unit=m.get('unit'),
                           acceptance_operator=m.get('op'), acceptance_threshold=m.get('threshold'),
                           normalized_violation=m.get('normalized'), metric_pass=m.get('passed') if value is not None else None,
                           evaluation_status=status if value is not None else 'unavailable', source_artifact=source,
                           source_version=version(key), missing_reason=(m.get('missing_reason') or missing) if value is None else '',
                           acceptance_tolerance=m.get('tolerance'), normalization_source=m.get('normalization'), candidate_id=candidate))

    def qualification(key, cid, role, diag, source, candidate, status):
        for q in diag.get('qualification', []):
            if q.get('load_condition') != cid:
                continue
            stage = q.get('stage', 'unknown')
            for name, val in q.get('measurements', {}).items():
                emit(key, cid, role, 'qualification.' + stage + '.' + name,
                     dict(value=val.get('value'), unit=val.get('unit'), threshold=val.get('threshold'),
                          op='<=', passed=val.get('passed', q.get('qualification', {}).get('checks', {}).get(name))),
                     source + '; direction_source=extensions/reference/passive_program.py#qualification', status, candidate,
                     'Qualification measurement not returned')
            for name, val in q.get('qualification', {}).get('checks', {}).items():
                emit(key, cid, role, 'qualification.' + stage + '.check.' + name,
                     dict(value=val, unit='predicate'), source, status, candidate)

    # C: exact selected artifacts, not task-id cost or candidate lookup.
    for case in CASES:
        tid, cid = case['task_id'], case['condition_name']
        key = (tid, 'C')
        assert case['run_id'] == MAIN[key]['run_id']
        source = case['source_reference']
        if tid == 'PHS-2D':
            final = read(ROOT / 'runs/phs2d-paper-data-20261112/FINAL_METRICS.json')['codex_nominal']
            source = uri(ROOT / 'runs/psd2d-core-only-20261112/fresh-store', final['result'])
        rr, store = source_result(source)
        mm = measurements(rr['acceptance'])
        if tid in ['PHS-2D', 'T08']:
            mm = {n.removeprefix(cid + '_'): v for n, v in mm.items() if n.startswith(cid + '_') or n == 'no_contact'}
        templates[tid, cid] = mm
        for name, m in mm.items():
            pointer = m.get('pointer') or ''
            pointer = pointer if pointer.startswith('/acceptance') else '/acceptance' + pointer
            emit(key, cid, case['condition_role'], name, m, source + '#' + pointer, 'evaluated', case['candidate_id'],
                 'Original evaluator returned null; no imputation')
        if tid == 'T10':
            for name, u in [('maximum_error_m','m'),('terminal_tip_speed_m_s','m/s'),('force_bound_violation_n','N')]:
                if name in rr.get('profile', {}):
                    emit(key,cid,case['condition_role'],name,dict(value=rr['profile'][name],unit=u),
                         source + '#/profile/' + name,'evaluated',case['candidate_id'])
        if tid in ['PHS-2D', 'T08']:
            er = artifact(store, rr['evaluation_reference'])
            qualification(key, cid, case['condition_role'], er.get('diagnostics', {}),
                          uri(store, rr['evaluation_reference']) + '#/diagnostics/qualification', case['candidate_id'], 'evaluated')

    for key, (raw, config, folder) in sorted(DATA.items()):
        tid, method = key
        selected = raw.get('selected')
        store = folder / 'STORE/platform.sqlite'
        evals = {x['condition']: x for x in raw['evaluations'] if x.get('candidate') == selected}
        stages = raw.get('required_stage_outcomes', {})
        required = raw.get('required_case_results', {})
        controls = raw.get('control_case_results', {})
        passive_episodes = {}
        if tid == 'PHS-2D' and raw['evaluations']:
            selected_eval = next(x for x in reversed(raw['evaluations']) if x.get('candidate') == selected)
            passive_raw = artifact(store, selected_eval['raw'])
            passive_episodes = {x['load_condition']: (i,x) for i,x in enumerate(passive_raw['episodes'])}
        expected = [(x['condition_name'], x['condition_role']) for x in CASES if x['task_id'] == tid]
        for cid, role in expected:
            e = (controls.get(cid, {}) if role == 'control' else required.get(cid, stages.get(cid, evals.get(cid, {})))) or {}
            reference = e.get('reference')
            source = uri(store, reference) if reference else str(folder / 'result.json') + '#/' + ('required_stage_outcomes/' + cid if cid in stages else 'selected=' + str(selected))
            status = e.get('validity', 'not_executed')
            if reference:
                rr = artifact(store, reference)
                acc = rr.get('acceptance', rr.get('diagnostics', e.get('diagnostics', {})))
                if 'evaluation' in rr:
                    diag = rr['evaluation'].get('diagnostics', {})
                    acc = {**diag, 'components': diag.get('observations', {})}
            else:
                acc = e.get('diagnostics', {})
            mm = measurements(acc)
            if tid in ['PHS-2D', 'T08']:
                mm = {n.removeprefix(cid + '_'): v for n, v in mm.items() if n.startswith(cid + '_') or n == 'no_contact'}
            for name, m in mm.items():
                tm = templates[tid, cid].get(name, {})
                if not m.get('op') and m.get('threshold') == tm.get('threshold'):
                    m['op'] = tm.get('op')
            for name, m in mm.items():
                emit(key, cid, role, name, m, source, status, selected, 'Original evaluator returned null / qualification missing; no imputation')
            if reference and 'evaluation' in rr:
                qualification(key, cid, role, rr['evaluation'].get('diagnostics', {}), source + '#/evaluation/diagnostics/qualification', selected, status)
            # Expected metrics remain visible for unexecuted conditions and absent scalar outputs.
            for name, tm in templates[tid, cid].items():
                if name in mm:
                    continue
                m = {**tm, 'value': None, 'passed': None, 'normalized': None}
                reason = ('Initial qualification failed; 22-second trajectory not executed' if status == 'initial_condition_failed'
                          else 'Selected candidate has no complete evaluation for this condition' if not e
                          else 'Not returned by this evaluation; no substitute from other candidates')
                # A missing-row threshold is explicitly a protocol/reference template, not a measurement.
                emit(key, cid, role, name, m, source + '; threshold_template=' + next(x['source_reference'] for x in CASES if x['task_id'] == tid and x['condition_name'] == cid),
                     'unavailable', selected, reason)
            for stage, q in (e.get('qualifications', {}) if not reference else {}).items():
                for name, v in {'passed': q.get('passed'), **q.get('checks', {})}.items():
                    emit(key, cid, role, 'qualification.' + stage + '.' + name, dict(value=v, unit='predicate'),
                         str(folder / 'result.json') + '#/required_case_results/' + cid + '/qualifications/' + stage,
                         status, selected)
                if 'drift_m' in q:
                    emit(key, cid, role, 'qualification.' + stage + '.drift_m', dict(value=q['drift_m'], unit='m'),
                         str(folder / 'result.json') + '#/required_case_results/' + cid + '/qualifications/' + stage, status, selected)
            if 'static_balance_residual_nm' in e:
                emit(key, cid, role, 'qualification.static_balance_residual_nm', dict(value=e['static_balance_residual_nm'], unit='N.m'),
                     str(folder / 'result.json') + '#/required_stage_outcomes/' + cid, status, selected)
            if cid in passive_episodes:
                i, episode = passive_episodes[cid]
                src = uri(store, selected_eval['raw']) + '#/episodes/' + str(i)
                for name, raw_name, u in [('max_tension_n','maximum_tension_n','N'),('max_length_excess_m','maximum_length_excess_m','m'),
                    ('max_contacts','maximum_contacts','count'),('max_force_map_error_nm','maximum_force_map_error_nm','N.m'),
                    ('max_constraint_direction_error','maximum_constraint_direction_error','1')]:
                    emit(key,cid,role,name,dict(value=episode.get(raw_name),unit=u),src+'/'+raw_name,status,selected,
                         'Not returned in original episode summary')
                emit(key,cid,role,'route_status',dict(value=episode.get('route_geometry',{}).get('status'),unit='category'),
                     src+'/route_geometry/status',status,selected,'Route status not recorded')

    # Additional seven-segment nominal measurements, never the separate half-step run.
    phs = ROOT / 'runs/phs2d-paper-data-20261112/TEN_CASE_RESULTS.csv'
    for r in rows(phs):
        if r['run_id'] != MAIN['PHS-2D', 'C']['run_id'] or r['experiment'] != 'codex_nominal':
            continue
        for name in ['max_plane_y_m','max_tension_n','max_length_excess_m','max_force_map_error_nm',
                     'max_constraint_direction_error','max_contacts','route_status','loaded_static_residual_inf_nm']:
            u = unit(name) or ('count' if name == 'max_contacts' else 'category' if name == 'route_status' else '1')
            emit(('PHS-2D','C'), r['load_condition'], 'required', name, dict(value=r[name], unit=u),
                 str(phs) + '#experiment=codex_nominal&load_condition=' + r['load_condition'], 'evaluated')

    # Independent P3 mechanism/numerical confirmation never adds required passes.
    case = next(x for x in CASES if x['task_id'] == 'T08')
    rr, store = source_result(case['source_reference'])
    raw = artifact(store, rr['raw_reference'])  # targeted summary artifact; no physical CSV traversal
    rawsrc = uri(store, rr['raw_reference'])
    variants = [('baseline', raw, 'mechanism_confirmation'),
                ('ablation', raw['paired_ablation']['ablation'], 'mechanism_confirmation')]
    variants += [(name, v['raw'], 'numerical_confirmation') for name, v in raw['numerical_confirmation']['executions'].items()]
    for variant, variant_raw, role in variants:
        prefix = '' if variant == 'baseline' else '/paired_ablation/ablation' if variant == 'ablation' else '/numerical_confirmation/executions/' + variant + '/raw'
        for i, episode in enumerate(variant_raw['episodes']):
            cid = episode['load_condition'] + ':' + variant
            src = rawsrc + '#' + prefix + '/episodes/' + str(i)
            for name in ['maximum_tension_n','maximum_length_excess_m','maximum_contacts','maximum_force_map_error_nm','maximum_constraint_direction_error']:
                emit(('T08','C'), cid, role, name, dict(value=episode.get(name), unit=unit(name) or ('count' if name=='maximum_contacts' else '1')),
                     src + '/' + name, 'evaluated', case['candidate_id'])
            for stage, qual in episode['qualifications'].items():
                for name, v in {'passed': qual.get('passed'), **qual.get('checks', {})}.items():
                    emit(('T08','C'), cid, role, 'qualification.' + stage + '.' + name, dict(value=v, unit='predicate'), src + '/qualifications/' + stage, 'evaluated', case['candidate_id'])
                emit(('T08','C'), cid, role, 'qualification.' + stage + '.drift_m', dict(value=qual.get('drift_m'),unit='m'), src + '/qualifications/' + stage, 'evaluated', case['candidate_id'])
    for variant, v in raw['numerical_confirmation']['saved_state_replay'].items():
        for name, u in [('maximum_position_difference_m','m'),('rows_checked','count'),('integrations','count')]:
            emit(('T08','C'), 'saved_state_replay:' + variant, 'numerical_confirmation', name,
                 dict(value=v.get(name),unit=u), rawsrc + '#/numerical_confirmation/saved_state_replay/' + variant, 'evaluated', case['candidate_id'])
    # Concepts absent from stored evaluator scalars remain explicit gaps.
    for tid, names in {'T03': [('arrival_time_s','s'),('terminal_speed_m_s','m/s')],
                       'T10': [('maximum_error_m','m')]}.items():
        for method in 'ABC':
            for case in [x for x in CASES if x['task_id']==tid]:
                for name, u in names:
                    if any(x['task_id']==tid and x['method']==method and x['condition_id']==case['condition_name'] and x['metric_name']==name for x in result):
                        continue
                    emit((tid,method),case['condition_name'],case['condition_role'],name,dict(value=None,unit=u),
                         MAIN[tid,method]['final_artifact'], 'unavailable', missing='Not serialized as a scalar by the task evaluator; not substituted by holding error/speed or recomputed from trajectories')
    return result


EVIDENCE_FIELDS = 'task_id method run_id decision_id sequence_index hypothesis_before evidence_type evidence_source evidence_artifact evidence_summary observed_physical_phenomenon mathematical_result agent_interpretation decision action_type design_parameter_changed control_parameter_changed candidate_before candidate_after subsequent_evaluation evaluation_outcome action_effect evidence_linkage confidence source_trace study_id agent_attribution record_scope'.split()


def refs(value):
    if isinstance(value, dict):
        if 'artifact_id' in value:
            yield value['artifact_id']
        else:
            for v in value.values():
                yield from refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from refs(v)


def prune(value):
    """Compact returned results, keeping measurements and references, not physics arrays."""
    if isinstance(value, dict):
        return {k: prune(v) for k, v in value.items() if k not in
                {'configuration', 'effective_configuration', 'input_schema', 'physical_observations', 'samples',
                 'signals', 'qpos_rad', 'qvel_rad_s', 'coordinate_order', 'trace_files', 'trajectory', 'generation',
                 'jacobian', 'mass_matrix', 'stiffness_matrix', 'damping_matrix', 'messages', 'schema'}}
    if isinstance(value, list):
        return [prune(v) for v in value] if len(value) <= 12 else dict(item_count=len(value), source='See exact source artifact/Trace')
    return value


def brief(value):
    """Keep compact measured facts; larger payloads stay at the cited source."""
    v = prune(value)
    if len(js(v)) <= 5000:
        return v
    facts = {}

    def walk(x, path=''):
        if isinstance(x, dict):
            for k, z in x.items():
                walk(z, path + '/' + k)
        elif isinstance(x, list):
            for i, z in enumerate(x):
                walk(z, path + '/' + str(i))
        elif len(facts) < 60:
            facts[path] = x
    walk(v)
    return dict(saved_scalar_excerpt=facts, full_payload='See source artifact/Trace; excerpt is not a new evaluation')


def outcome(value):
    found = {}
    def walk(v, path=''):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ['status','validity','accepted','task_success','error','failure_reason','reason','task_acceptance','execution_status','solver_status'] and not isinstance(x, (dict,list)):
                    found[path + '/' + k] = x
                elif isinstance(x, (dict,list)):
                    walk(x, path + '/' + k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, path + '/' + str(i))
    walk(value)
    return found or 'No scientific conclusion returned by this operation'


def candidates(value):
    found = []
    def walk(v):
        if isinstance(v, dict):
            for k,x in v.items():
                if k in ['candidate','candidate_id','selected_candidate'] and x:
                    if isinstance(x,str):
                        found.append(x)
                    elif isinstance(x,dict) and x.get('artifact_id'):
                        found.append(x['artifact_id'])
                elif isinstance(x,(dict,list)) and k not in ['configuration','input_schema']:
                    walk(x)
        elif isinstance(v,list):
            for x in v:
                walk(x)
    walk(value)
    return sorted(set(found))


def kind_of(value):
    if not isinstance(value, dict):
        return None
    if any(k in value for k in ['acceptance', 'evaluation', 'constraint_observations', 'physical_result', 'diagnostics']):
        return 'task_evaluation'
    if any(k in value for k in ['mathematical_result', 'mathematical_evidence', 'jacobian', 'equilibrium', 'mathematics', 'analysis','native_analysis','nonlinear_capability']):
        return 'mathematical'
    tag = str(value.get('kind', '')) + str(value.get('contract', '')) + str(value.get('operation', ''))
    if re.search('math|equilibrium|mechanics|jacobian|lineariz|sensitivity|research.result', tag, re.I):
        return 'mathematical'
    if re.search('knowledge|experience', tag, re.I):
        return 'historical_knowledge'
    return None


def action_type(text, commands):
    t = text.lower()
    if re.search(r'rollback|roll back|revert|return to.*structure', t):
        return 'rollback'
    ops = [c.get('operation', c.get('action', '')) for c in commands]
    if any(o in ['select','finish','physical_replay'] for o in ops) or t.startswith('read complete'):
        return 'stop_or_confirm'
    if any(o in ['initialize_control'] for o in ops):
        return 'control_change'
    if 'generate' in ops:
        if re.search(r'topolog|segment.count|tendon.count|three.tendon|four.tendon|six.channel', t):
            return 'topology_change'
        if re.search(r'rout|guide|anchor|payout', t):
            return 'tendon_routing_change'
        if re.search(r'young|modul|material|mpa', t):
            return 'material_change'
        return 'geometry_change'
    if re.search(r'initial.pose|initial.state|initial.condition|initializ|preload', t):
        return 'initial_condition_change'
    if re.search(r'tension|control|lqr|feedforward|brak', t) and any(o in ['evaluate','control','execute','design'] for o in ops):
        return 'control_change'
    if 'math' in ops or re.search(r'jacobian|equilibrium|kkt|tangent|lineariz|lqr|mathematic|gvs', t):
        return 'mathematical_method_change'
    if 'finish' in ops or re.search(r'confirm|select|stop|close|accept|evaluat|replay', t):
        return 'stop_or_confirm'
    return 'research_question_change'


def build_evidence():
    result = []
    # These links were reviewed against both the public decision text and named
    # returned events; chronology alone is insufficient even when refs=[] upstream.
    reviewed_c = {
        'T04-216-construct-local-interior-reference-bank-decision': ['T04-211-construct-native-frozen-reference-bank'],
        'T04-217-qualify-local-interior-bank-time-zero-decision': ['T04-216-construct-local-interior-reference-bank'],
        'T04-219-seed-local-interior-formal-knots-decision': ['T04-216-construct-local-interior-reference-bank'],
        'T04-220-independent-full-local-interior-feedforward-decision': ['T04-217-qualify-local-interior-bank-time-zero','T04-219-seed-local-interior-formal-knots'],
        'T07-020-generate-smaller-radius-hypothesis-decision': ['T07-017-refine-startup-and-hold-knot-resolution'],
        'T07-060-test-isotropic-root-mechanism-decision': ['T07-35-refine-common-structure-M1-A','T07-42-native-common-structure-M1_C'],
        'T07-063-add-one-mm-root-reach-margin-decision': ['T07-062-native-isotropic-root-A'],
        'T07-074-test-original-radius-boundary-on-best-root-decision': ['T07-072-native-distributed-reach-A','T07-062-native-isotropic-root-A'],
        'T07-105-seed-C-from-current-A-pass-decision': ['T07-104-read-current-C-residual-conflict'],
    }

    def add(key, run, seq, ident, source, decision, evidence, etype, artifacts, commands,
            after, linkage, candidate_before='', candidate_after='', scope='selected_run', hypothesis=''):
        generation = [c.get('arguments', c).get('generation') for c in commands if c.get('arguments', c).get('generation')]
        controls = [{k: v for k, v in c.get('arguments', c).items() if k in ['controls','control','controller_recipe','initial_state','qpos_rad','tensions_n','options','plan']} for c in commands]
        controls = [x for x in controls if x]
        result.append(dict(task_id=key[0], method=key[1], run_id=run, decision_id=ident, sequence_index=seq,
                           hypothesis_before=hypothesis, evidence_type=etype, evidence_source=source,
                           evidence_artifact=artifacts or [source], evidence_summary=brief(evidence),
                           observed_physical_phenomenon=brief(evidence) if etype in ['physical','task_evaluation'] else '',
                           mathematical_result=brief(evidence) if etype == 'mathematical' else '',
                           agent_interpretation=decision, decision=decision,
                           action_type=action_type(decision, commands), design_parameter_changed=generation or '',
                           control_parameter_changed=controls or '', candidate_before=candidate_before,
                           candidate_after=candidate_after, subsequent_evaluation=brief(after),
                           evaluation_outcome=outcome(after),
                           action_effect='inconclusive' if after else 'no_followup_evaluation',
                           evidence_linkage=linkage, confidence='high' if linkage == 'explicit_trace' else 'limited',
                           source_trace=source, study_id=run, agent_attribution='formal_ab_llm' if key[1] != 'C' else 'historical_full_surrogate_main',
                           record_scope=scope))

    for key, (raw, config, folder) in sorted(DATA.items()):
        path = folder / 'TRACE.jsonl'
        rs = trace(path)
        decisions = [(i, r) for i, r in enumerate(rs) if r.get('kind') == 'research_decision']
        for seq, (i, r) in enumerate(decisions, 1):
            source = str(path) + '#L' + str(i + 1)
            # Only the feedback actually delivered before this decision is eligible.
            request = next((x for x in reversed(rs[:i]) if x.get('kind') == 'provider_request' and x.get('request_number') == r.get('request_number')), {})
            feedback = []
            for message in request.get('request', {}).get('messages', []):
                if message.get('role') != 'user':
                    continue
                try:
                    content = json.loads(message['content'])
                except (ValueError, TypeError):
                    continue
                feedback.extend(content.get('feedback', []))
            evidence = r.get('evidence', '')
            evidence = evidence if isinstance(evidence, str) else js(evidence)
            if not evidence:
                continue
            commands = r.get('commands', [])
            end = decisions[seq][0] if seq < len(decisions) else len(rs)
            follow = [dict(trace_line=j + 1, **prune(x)) for j, x in enumerate(rs[i+1:end], i+1)
                      if x.get('kind') in ['evaluation','operation_error','math','mathematical_result','initial_qualification']]
            for j, event in enumerate(rs[i+1:end], i+1):
                if event.get('kind') != 'provider_request':
                    continue
                for message in event.get('request', {}).get('messages', []):
                    if message.get('role') != 'user':
                        continue
                    try:
                        next_feedback = json.loads(message['content']).get('feedback', [])
                    except (ValueError, TypeError):
                        continue
                    if next_feedback:
                        follow.append(dict(source_trace=str(path)+'#L'+str(j+1), returned=brief(next_feedback)))
            ops = [x.get('command', {}).get('operation') for x in feedback]
            etype = 'mathematical' if 'math' in ops and re.search('mechanic|jacobian|equilibrium|kkt|stiffness|force.map|tangent', evidence, re.I) else 'task_evaluation' if feedback else 'historical_knowledge'
            # Conservative: textual evidence plus delivered feedback is recorded, but
            # only manually reviewed substantive examples get a direct-link label.
            linkage = 'chronology_only'
            reviewed = {('T01','B'): [4,5,7,8,9,10], ('T01','A'): [8,9,10],
                        ('T04','B'): [10,12,13,18,20,30,32],
                        ('T07','B'): [10,11,12,15,16,17,18,19], ('PHS-2D','B'): [5,7]}
            if r.get('request_number') in reviewed.get(key, []) and feedback:
                linkage = 'explicit_trace'
            artifacts = [uri(folder / 'STORE/platform.sqlite', x) for x in dict.fromkeys(refs(feedback))]
            # Provider payload is a fully locatable source even when math has no separate ref.
            reqline = next((j+1 for j,x in enumerate(rs) if x is request), None)
            if reqline:
                artifacts.append(str(path) + '#L' + str(reqline))
            add(key, raw['run_id'], seq, raw['run_id'] + ':request:' + str(r.get('request_number')),
                source, r['decision'], evidence, etype, artifacts, commands, follow, linkage,
                candidate_before=candidates(feedback), candidate_after=candidates(follow))
            actual_math = [brief(x.get('result')) for x in feedback if x.get('command', {}).get('operation') == 'math']
            if actual_math:
                result[-1]['mathematical_result'] = actual_math
            # Commands are intended actions, not proof that generation succeeded.
            result[-1]['design_parameter_changed'] = dict(requested_generation=generation) if (generation := result[-1]['design_parameter_changed']) else ''

    for tid, h in sorted(HISTORY.items()):
        if tid == 'PHS-2D':
            continue
        directory = Path(h['protocol_source']).parent
        paths = {directory / 'STUDY_TRACE.jsonl'}
        # Preserve earlier actual research routes as precursor runs, not final results.
        if tid in ['T04', 'T10']:
            parent = directory.parent
            paths.update(parent.glob('T*_RUN_*/STUDY_TRACE.jsonl'))
            if (parent / 'STUDY_TRACE.jsonl').exists():
                paths.add(parent / 'STUDY_TRACE.jsonl')
        for path in sorted(paths):
            rs = trace(path)
            seq = 0
            for i, r in enumerate(rs):
                if r.get('kind') != 'decision':
                    continue
                seq += 1
                args = r.get('exact_input', {}).get('arguments', {})
                decision = args.get('rationale_summary', r.get('decision_summary', ''))
                if not decision:
                    continue
                next_event = next((x for x in rs[i+1:] if x.get('kind') not in ['decision','preparation']), {})
                commands = [next_event.get('exact_input', {}).get('arguments', next_event.get('exact_input', {}))]
                evid_refs = args.get('evidence', [])
                store = r.get('store_id') or next_event.get('store_id')
                arts, types, measured = [], [], []
                for ref in evid_refs:
                    if not isinstance(ref, dict) or 'artifact_id' not in ref:
                        continue
                    ev = artifact(store, ref)
                    typ = kind_of(ev)
                    arts.append(uri(store, ref))
                    if typ:
                        types.append(typ)
                        measured.append(brief(ev))
                etype = 'mathematical' if 'mathematical' in types else 'task_evaluation' if 'task_evaluation' in types else 'historical_knowledge'
                # Candidate/configuration references alone never establish causal linkage.
                linkage = 'explicit_trace' if types and len(decision) > 60 else 'chronology_only'
                linked = []
                for event_id in reviewed_c.get(r['event_id'], []):
                    matches = [(j,x) for j,x in enumerate(rs[:i]) if x.get('event_id')==event_id]
                    if not matches:
                        continue
                    j, ev = matches[0]
                    arts.append(str(path) + '#L' + str(j+1))
                    linked.append(dict(event_id=event_id, returned=brief(ev.get('output')), status=ev.get('status')))
                if linked:
                    measured = linked
                    linkage = 'explicit_trace'
                    etype = 'mathematical'
                run = r.get('study_id', h['run_id'])
                add((tid, 'C'), run, seq, r['event_id'], str(path) + '#L' + str(i+1), decision,
                    measured or args.get('evidence', []) or 'No explicit prior evidence reference in this decision record',
                    etype, arts, commands, dict(event_id=next_event.get('event_id'), status=next_event.get('status'),
                    output=brief(next_event.get('output', {}))), linkage, r.get('parent_candidate_ids'),
                    next_event.get('candidate_id'), 'selected_run' if run == h['run_id'] else 'precursor_run',
                    args.get('research_question', ''))
                result[-1]['candidate_before'] = candidates(commands) or r.get('parent_candidate_ids') or ''
                result[-1]['candidate_after'] = candidates(next_event.get('output')) or next_event.get('candidate_id') or ''
                # Preserve the actual tool action for control/mathematics classification.
                if next_event.get('tool_name') == 'research.math':
                    result[-1]['action_type'] = 'mathematical_method_change'
                if next_event.get('tool_name') in ['task.initial_state.construct','task.initial_state.qualify']:
                    result[-1]['action_type'] = 'initial_condition_change'
                if r['event_id'].startswith('T07-074-'):
                    result[-1]['action_type'] = 'rollback'
                if r['event_id'].startswith('T10-210-'):
                    result[-1]['action_type'] = 'control_change'
                    case = next(x for x in CASES if x['task_id']=='T10' and x['condition_name']=='no_impulse')
                    evaluated, s = source_result(case['source_reference'])
                    ref = evaluated['profile']['native_feedback_preparation']
                    prep = artifact(s, ref)
                    result[-1]['mathematical_result'] = dict(method=prep['method'], scope=prep['scope'],
                        equilibrium_diagnostics=prep['equilibrium_diagnostics'], state_dimension=len(prep['A']),
                        input_dimension=len(prep['K']), native_cost=prep['native_cost'],
                        chronology='Preparation is subsequent execution evidence, not a prior mathematical cause of this decision')
                    result[-1]['subsequent_evaluation'] = dict(preparation=uri(s,ref),
                        required=[dict(condition=x['condition_name'],source=x['source_reference'],passed=x['passed']) for x in CASES if x['task_id']=='T10' and x['condition_role']=='required'])
                    result[-1]['control_parameter_changed'] = brief(commands)

    # Seven-segment FULL uses a different, original tool-Trace schema.
    path = ROOT / 'runs/psd2d-core-only-20261112/TOOL_TRACE.jsonl'
    for i, r in enumerate(trace(path)):
        context, reason = r.get('context', ''), r.get('reason', '')
        if not reason or not context or r.get('input', {}).get('store') == 'halfstep-store':
            continue
        refs_in_context = re.findall(r'\bC\d{3}\b', context)
        evidence_locations = [str(path) + '#call_id=' + x for x in dict.fromkeys(refs_in_context)]
        out = r.get('output', {})
        if out.get('stdout'):
            evidence_locations.append(str(path.parent / out['stdout']))
        etype = 'mathematical' if re.search('KKT|Jacobian|tangent|local.*ratio|row.*residual', context, re.I) else 'physical' if re.search('mm|physical|load|tail|route', context, re.I) else 'historical_knowledge'
        add(('PHS-2D', 'C'), HISTORY['PHS-2D']['run_id'], i+1, r['call_id'], str(path) + '#L' + str(i+1),
            reason, context, etype, evidence_locations, [dict(operation='math' if etype=='mathematical' else 'evaluate')],
            prune(out), 'explicit_trace' if refs_in_context else 'chronology_only', hypothesis=r.get('hypothesis',''))
    # Mirrored historical logs can contain the same actual event. Prefer final-run path.
    unique = {}
    for r in result:
        k = (r['run_id'], r['decision_id'])
        preferred = str(Path(HISTORY[r['task_id']]['protocol_source']).parent / 'STUDY_TRACE.jsonl')
        if k not in unique or r['source_trace'].startswith(preferred + '#'):
            unique[k] = r
    result = list(unique.values())
    # Empirical effects are scoped to the named observations, never causal isolation.
    for r in result:
        if r['task_id']=='T01' and r['method']=='B' and r['decision_id'].endswith(':request:9'):
            raw, _, folder = DATA['T01','B']
            evaluations = [x for x in trace(folder/'TRACE.jsonl') if x.get('kind')=='evaluation']
            before = next(x for x in evaluations if x.get('candidate')=='c2' and x.get('condition')=='central_high')
            after = next(x for x in evaluations if x.get('candidate')=='c6' and x.get('condition')=='central_high')
            r['action_effect'] = 'mixed'
            r['subsequent_evaluation'] = dict(comparison_scope='c2 to c6 central_high only; structure and controls both changed; not an isolated mathematical causal effect',
                before=before['diagnostics']['metrics'],after=after['diagnostics']['metrics'],
                before_reference=uri(folder/'STORE',before['reference']),after_reference=uri(folder/'STORE',after['reference']))
            r['evaluation_outcome'] = 'Terminal error improved; holding speed worsened; final required task remains 0/3.'
        if r['task_id']=='T07' and r['method']=='C' and r['decision_id'].startswith(('T07-060-','T07-070-','T07-074-')):
            path=Path(r['source_trace'].split('#')[0]); events=trace(path)
            prefix={'T07-060-':('T07-063-', 'improved'), 'T07-070-':('T07-074-', 'worsened'), 'T07-074-':('T07-078-', 'improved')}
            target,effect=next(v for k,v in prefix.items() if r['decision_id'].startswith(k))
            follow=next((x for x in events if x.get('kind')=='decision' and x.get('event_id','').startswith(target)), None)
            if follow:
                r['action_effect']=effect
                r['subsequent_evaluation']=dict(scope='M1_A only; finite empirical comparison, not all-task or isolated derivative effect',
                    source_trace=str(path)+'#event_id='+follow['event_id'],recorded_observation=follow['decision_summary'])
                r['evaluation_outcome']=follow['decision_summary']
    return result


def validate(status, metrics, evidence):
    assert len(status)==33 and len({(r['task_id'],r['method']) for r in status})==33
    assert set(r['status'] for r in status)=={'PASS','EVALUATED_NOT_PASS','INCOMPLETE'}
    assert all({r['method'] for r in status if r['task_id']==tid}==set('ABC') for tid in HISTORY)
    assert len({(r['task_id'],r['method'],r['condition_id'],r['condition_role'],r['metric_name']) for r in metrics})==len(metrics)
    for r in metrics:
        assert r['source_artifact'] and r['source_version']
        assert r['metric_value'] is not None or r['missing_reason']
        assert r['metric_value'] is None or r['metric_unit']
        assert r['acceptance_threshold'] is None or r['acceptance_operator']
        if r['condition_id'].endswith('_frozen'):
            assert r['condition_role']=='control'
    for tid in HISTORY:
        expected={r['condition_name'] for r in CASES if r['task_id']==tid and r['condition_role']=='required'}
        for method in 'ABC':
            assert {r['condition_id'] for r in metrics if r['task_id']==tid and r['method']==method and r['condition_role']=='required'}==expected
    assert len({(r['run_id'],r['decision_id']) for r in evidence})==len(evidence)
    for r in evidence:
        assert r['evidence_type'] in {'mathematical','physical','task_evaluation','historical_knowledge'}
        assert r['action_effect'] in {'improved','worsened','mixed','unchanged','inconclusive','no_followup_evaluation'}
        assert r['evidence_linkage'] in {'explicit_trace','chronology_only','inferred'}
        p,line=r['source_trace'].rsplit('#L',1)
        event=trace(p)[int(line)-1]
        assert event.get('event_id',event.get('call_id'))==r['decision_id'] or ':request:' in r['decision_id']
    nine=ROOT/'.audit-task-a/paper_experiments/paper_results_master_20261113'
    assert len(rows(nine/'PHS2D_9SEG_GRADIENT_VALIDATION.csv'))==6
    assert len(rows(nine/'PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv'))==18
    assert not any('PHS2D_9SEG' in r['run_id'] for r in status+metrics+evidence)


if __name__ == '__main__':
    status = build_status()
    metrics = build_metrics()
    evidence = build_evidence()
    validate(status, metrics, evidence)
    output('ABC_STATUS_MATRIX.csv', status, list(status[0]))
    output('ABC_CONDITION_METRICS.csv', metrics, METRIC_FIELDS)
    output('ABC_EVIDENCE_ACTIONS.csv', evidence, EVIDENCE_FIELDS)
    print('D1', len(status), Counter(x['status'] for x in status))
    print('D2', len(metrics), 'missing', sum(x['metric_value'] is None for x in metrics))
    print('D3', len(evidence), Counter(x['evidence_linkage'] for x in evidence))
