"""One persistent, subordinate Round 9 experiment; numerical tools stay unchanged."""
import copy
import time

from tools.state_io import atomic_json, read


EXPERIMENT_ID = 'llm_reach_v1'
EXPERIMENT_LIMITS = dict(model_calls=24, matlab_dynamic=40, mujoco=3, active_wall_s=1800)


class ExperimentSupport:
    def experiment(self):
        return self.state.get('experiment')

    def start_experiment(self, experiment_id):
        if experiment_id != EXPERIMENT_ID:
            raise ValueError('Only llm_reach_v1 is authorized')
        old = self.experiment()
        if old:
            if old['experiment_id'] != experiment_id:
                raise ValueError('Another experiment is already bound')
            return old  # Repeated start never resets counters or positions.
        baseline = self.candidate('c032')
        if baseline['physics_version'] != 'equivalent_rod_v2':
            raise ValueError('Experiment baseline must be V2')
        for result in baseline['results'].values():
            self.check_evidence(result['result_ref'])
        self.state['experiment'] = dict(
            experiment_id=experiment_id, baseline_id='c032', status='NOT_RUN',
            start_model_index=len(self.state['model_calls']), start_decision_sequence=len(self.state['decisions']),
            existing_candidate_ids=[c['candidate_id'] for c in self.state['candidates']],
            starting_counters=copy.deepcopy(self.ledger['used']), limits=copy.deepcopy(EXPERIMENT_LIMITS),
            used={key: 0 for key in EXPERIMENT_LIMITS}, stop_decision_sequence=None,
            instruction='Informed local optimization from c032; historical success is not a new experiment.',
            historical_authorship='Development-time Codex selected the 40/24-trial MATLAB plans; deterministic tools generated proposals. c065/c066 are historical comparisons, not runtime DeepSeek discoveries.')
        self.tick = time.monotonic()
        self.save()
        return self.experiment()

    def experiment_remaining(self):
        exp = self.experiment()
        if not exp:
            return {}
        rem = {k: max(0, v-exp['used'][k]) for k, v in exp['limits'].items()}
        # Include this process's unsaved activity and conservative interrupted
        # reservations. Paused time between processes is never charged.
        if exp['status'] == 'RUNNING':
            rem['active_wall_s'] = max(0, rem['active_wall_s']-(time.monotonic()-self.tick))
        rem['active_wall_s'] = max(0, rem['active_wall_s']-sum(
            r.get('unsettled_wall_s', 0) for r in self.ledger['entries']
            if r.get('experiment_id') == exp['experiment_id']))
        return rem

    def action_provenance(self):
        row = getattr(self, 'current_model_row', None)
        provenance = dict(origin=getattr(self, 'decision_origin', 'codex_development'))
        if row is not None:
            provenance.update(model_request_index=row['index'], decision_sequence=row['decision_sequence'])
        if self.experiment():
            provenance['experiment_id'] = self.experiment()['experiment_id']
        if getattr(self, 'search_provenance', None):
            provenance['generator'] = copy.deepcopy(self.search_provenance)
        return provenance

    def experiment_candidates(self):
        exp = self.experiment()
        if not exp:
            return []
        return [c for c in self.state['candidates']
                if c['candidate_id'] not in exp['existing_candidate_ids']
                and c.get('provenance', {}).get('experiment_id') == exp['experiment_id']
                and c['provenance'].get('origin') == 'deepseek_api']

    def experiment_summary(self):
        exp = self.experiment()
        if not exp:
            return None
        candidates = self.experiment_candidates()
        decisions = [d for d in self.state['decisions'][exp['start_decision_sequence']:]
                     if d.get('provenance', {}).get('experiment_id') == exp['experiment_id']
                     and d.get('origin') == 'deepseek_api']
        searches = [d for d in decisions if d['tool'] == 'optimize_matlab' and d.get('status') == 'accepted']
        def fresh_receipts(c, resource, backend):
            result = c['results'].get(backend, {})
            return [r for r in self.ledger['entries'] if result.get('complete')
                and r['resource'] == resource and r['status'] == 'completed'
                and r.get('experiment_id') == exp['experiment_id'] and r.get('origin') == 'deepseek_api'
                and r.get('candidate_id') == c['candidate_id'] and r.get('result_ref') == result.get('result_ref')
                ]
        numerical = [c for c in candidates if any(
            r.get('generator', {}).get('type') == 'matlab_coordinate_search'
            and any(d['arguments']['search_id'] == r['generator']['search_id'] for d in searches)
            for r in fresh_receipts(c, 'matlab_dynamic', 'matlab'))]
        numerical_ids = {c['candidate_id'] for c in numerical}
        by_id = {c['candidate_id']: c for c in candidates}
        def from_fresh_search(c):
            # A later model-selected control/design adjustment can legitimately
            # verify a descendant of a fresh search trial without another search.
            seen = set()
            while c and c['candidate_id'] not in seen:
                if c['candidate_id'] in numerical_ids:return True
                seen.add(c['candidate_id']); c = by_id.get(c['parent_id'])
            return False
        validated = [c for c in candidates if from_fresh_search(c) and fresh_receipts(c, 'mujoco', 'mujoco')]
        claims = [c for c in self.state['verified_diagnoses']
                  if c.get('provenance', {}).get('experiment_id') == exp['experiment_id']
                  and c.get('origin') == 'deepseek_api'
                  and c.get('candidate_id') in [x['candidate_id'] for x in candidates]]
        best = min(validated, key=lambda c: c['results']['mujoco']['position_error_m'], default=None)
        phase = 'baseline_review' if not searches else 'optimization' if not numerical else 'verification' if not validated else 'diagnosis' if not claims else 'closeout'
        return dict(experiment_id=exp['experiment_id'], status=exp['status'], phase=phase,
                    baseline_id=exp['baseline_id'], objective='Improve c032 using a new model-led MATLAB search, then MuJoCo verification and a checked diagnosis; fixed 20 N, 2 s and 0.01 m threshold.',
                    remaining=self.experiment_remaining(), used=copy.deepcopy(exp['used']),
                    candidate_ids=[c['candidate_id'] for c in candidates],
                    fresh_matlab_ids=[c['candidate_id'] for c in numerical],
                    fresh_validated_ids=[c['candidate_id'] for c in validated],
                    best_id=best['candidate_id'] if best else None,
                    best_error_m=best['results']['mujoco']['position_error_m'] if best else None,
                    workflow_complete=exp['stop_decision_sequence'] is not None and bool(searches and claims and validated),
                    numerical_experiment_complete=bool(validated),
                    mujoco_task_success=any(c['results']['mujoco'].get('canonical_task_success') is True for c in validated),
                    verified_diagnosis_count=len(claims))

    def guard_experiment_action(self, name, args):
        exp = self.experiment()
        if not exp:
            return
        mutations = ('create_candidate', 'optimize_matlab', 'simulate_candidate', 'evaluate_candidate')
        if name in mutations:
            if getattr(self, 'decision_origin', None) != 'deepseek_api':
                raise ValueError('Experiment numerical actions must originate in a runtime DeepSeek decision')
            cid = args.get('parent_id', args.get('candidate_id'))
            eligible = [exp['baseline_id']] + [c['candidate_id'] for c in self.experiment_candidates()]
            if cid not in eligible:
                raise ValueError('Experiment mutations require c032 or its new experimental descendants')
            c = self.candidate(cid)
            if c['design']['exploration_physics']['tendon_force_limit_n'] != 20:
                raise ValueError('Experiment force limit is fixed at 20 N')
        if name == 'create_candidate':
            for key, value in args['changes'].items():
                if key == 'tendon_force_limit_n' and value != 20:
                    raise ValueError('Experiment force limit is fixed at 20 N')
                if key in ('mode', 'physics_version'):
                    if (key == 'mode' and value in ('C1', 'C2')) or (key == 'physics_version' and value == 'equivalent_rod_v2'):
                        continue
                bounds = self.state['request']['grant']['bounds'].get(key)
                if not bounds or not bounds[0] <= value <= bounds[1]:
                    raise ValueError('Experiment change must respect existing authorized bounds: '+key)
        if name == 'optimize_matlab':
            if 'tendon_force_limit_n' in args['variables']:
                raise ValueError('Do not optimize the fixed 20 N force limit')
            if not args['search_id'].startswith(exp['experiment_id']+'_'):
                raise ValueError('Use a new search_id prefixed with llm_reach_v1_')
            path = self.root / f"searches/{args['search_id']}.json"
            if path.exists() and read(path).get('provenance', {}).get('experiment_id') != exp['experiment_id']:
                raise ValueError('Existing search is not owned by this experiment')
            if not path.exists() and args['max_evaluations'] > min(24, self.experiment_remaining()['matlab_dynamic']):
                raise ValueError('Each new batch is at most 24 trials and cannot exceed experiment remainder')
        if name == 'stop_design':
            summary = self.experiment_summary()
            attempted = any(d['tool'] == 'optimize_matlab' for d in self.state['decisions'][exp['start_decision_sequence']:])
            if self.experiment_remaining()['model_calls'] > 1:
                if not attempted:
                    raise ValueError('Historical success cannot close this experiment: choose your own c032 optimization hypothesis first')
                if summary['fresh_validated_ids'] and not summary['verified_diagnosis_count']:
                    raise ValueError('Record a checked diagnosis for an experiment candidate before closeout')

    def render_experiment(self):
        if not self.experiment():
            return
        from tools.dynamic_view import render_candidate
        summary = self.experiment_summary()
        ids = {self.experiment()['baseline_id']}
        if summary['best_id']:
            ids.add(summary['best_id'])
        for cid in ids:
            c = self.candidate(cid)
            for backend, result in c['results'].items():
                if result.get('complete'):
                    path = self.root / f'observations/{cid}_{backend}.html'
                    if not path.exists():
                        render_candidate(self.root, c, backend)
        atomic_json(self.root / 'experiments' / EXPERIMENT_ID / 'summary.json', summary)
