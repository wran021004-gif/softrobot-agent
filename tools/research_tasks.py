"""Future research task adapters and one evidence-bound offline acceptance result.

Archived evaluators, kernels and campaigns retain their original semantics.
The new reach/hold protocol composes their outputs rather than replacing them.
"""
from dataclasses import dataclass
import math

from tools.state_io import digest, effective_input


@dataclass(frozen=True)
class ResearchTaskAdapter:
    configuration: dict

    @property
    def task(self):
        return self.configuration['task']

    def _require_configuration(self):
        if not {'policy', 'robot'} <= self.configuration.keys():
            raise ValueError('EFFECTIVE_CONFIGURATION_REQUIRED: frozen policy and robot snapshot')

    def condition_view(self):
        """Generate hard conditions on demand from task + legacy frozen protocol.

        Task-only calls retain known conditions and explicitly report missing
        Reach hold requirements. No optimization weight supplies a hard limit.
        """
        from schemas.platform import TaskConditionView
        from tools.platform_store import plain
        task = self.task
        signal = next(s for s in task['observations'] if s['name'] == 'tip_position')
        timing = task['timing']
        missing, rows = [], []
        if task['family'] == 'task.tracking':
            from extensions.reference.implementation import tracking_condition_specs
            timed = task['goal']['data']['time_requirement'] == 'timed'
            sampling = (dict(mode='inclusive_scored_post_step_grid', window_s=task['sampling']['window_s'],
                             sample_period_s=timing['sample_period_s'], reference='r(t)',
                             complete_record_grid='post_step from sample_period_s through duration_s') if timed else
                        dict(mode='saved_polyline_geometry', geometry_step_m=task['evaluator']['parameters']['data']['geometry_step_m'],
                             time_semantics='ordered recording only; no speed bound or arrival deadline',
                             first_sample='first saved post_step measurement',
                             acquisition_duration_s=timing['duration_s']))
            for row in tracking_condition_specs(task):
                rows.append(dict(**row, signal=signal, sampling=sampling,
                    mathematical_binding=(dict(constraint_id='timed_tracking', coverage='exact_sampled_expression') if timed else
                        dict(constraint_id=row['condition_id'], coverage='unsupported', proxy_constraint_id='geometric_path')),
                    provenance=['/task/goal', '/task/evaluator/parameters', '/task/sampling'],
                    expressibility='sampled_norm_bound' if timed else 'proxy_only',
                    expression_reason=('norm(p_k-r(t_k)) <= limit on scored samples; no velocity hard bound' if timed else
                        'geometric_path is a sampled free-progress proxy; it does not establish this saved-polyline condition')))
        else:
            rows.append(dict(condition_id='terminal_error_m', metric='position_error',
                evaluation_binding=dict(source='EvaluationResult', constraint='task_bound', metric='position_error'),
                mathematical_binding=dict(constraint_id='terminal_error_m', coverage='exact_sampled_expression'),
                meaning='Distance from final saved position at task endpoint to target',
                limit=task['evaluator']['parameters']['data']['tolerance_m'], units='m', signal=signal,
                sampling=dict(mode='task_endpoint', time_s=timing['duration_s']),
                provenance=['/task/evaluator/parameters/data/tolerance_m', '/task/timing', '/task/goal'],
                expressibility='sampled_norm_bound', expression_reason='norm(p(T)-target) <= limit in the sampled local model'))
            control = self.configuration.get('policy', {}).get('controller', {}).get('parameters', {}).get('data', {})
            settling = control.get('settling')
            if settling is None:
                missing.append('frozen Reach settling and acceptance protocol require effective configuration')
            else:
                for name, output, unit, field, meaning in (
                        ('holding_max_error_m', 'tip_position', 'm', 'position_limit_m', 'Maximum sampled final-window distance to target'),
                        ('holding_max_speed_m_s', 'tip_velocity', 'm/s', 'speed_limit_m_s', 'Maximum sampled final-window absolute world tip speed')):
                    rows.append(dict(condition_id=name, metric=name, meaning=meaning,
                        evaluation_binding=dict(source='research.task_acceptance', metric=name,
                            component='holding_position' if output == 'tip_position' else 'holding_speed',
                            profile_source='ProfileOutput.detail', profile_pointer='/sampled_settling/'+
                                ('max_error_m' if output == 'tip_position' else 'max_speed_m_s')),
                        mathematical_binding=dict(constraint_id=name, coverage='exact_sampled_expression'),
                        limit=settling[field], units=unit, signal={**signal, 'name': output, 'units': unit},
                        sampling=dict(mode='inclusive_final_window', window_s=[timing['duration_s']-settling['window_s'], timing['duration_s']],
                            sample_period_s=timing['sample_period_s']),
                        provenance=['/policy/controller/parameters/data/settling/'+field, '/task/timing', '/task/goal',
                            '/policy/controller/parameters/data/settling/window_s'],
                        expressibility='sampled_norm_bound', expression_reason='Sampled norm bound; actual holding coverage belongs to independent protocol'))
        return dict(contract='research.task_conditions', version='1.0.0', task_identity=digest(task),
            task_status=task['status'], evaluator=task['evaluator'],
            conditions=[plain(TaskConditionView.model_validate(row)) for row in rows], missing=missing,
            authority='registered evaluator plus frozen acceptance protocol; this derived view grants no approval',
            continuous_time_guarantee=False)

    def execution_requirements(self):
        """Required signals/registered capabilities, not a claim of executability."""
        task = self.task
        reach = task['family'] == 'task.reach'
        timed = not reach and task['goal']['data']['time_requirement'] == 'timed'
        complete = {'robot', 'policy'} <= self.configuration.keys()
        protocol = 'offline_reach_hold_v1' if reach else 'offline_timed_tracking_v1' if timed else 'development_tracking_v1'
        signals = list(task['observations'])
        if reach:
            position = next(s for s in signals if s['name'] == 'tip_position')
            velocity = {**position, 'name': 'tip_velocity', 'units': 'm/s'}
            if velocity not in signals:
                signals.append(velocity)
        policy = self.configuration.get('policy', {})
        bindings = {key: {field: policy[key][field] for field in ('extension_id', 'version')}
                    for key in ('controller', 'backend', 'dynamics_model') if policy.get(key)}
        missing = [] if complete else ['Frozen effective configuration is required for execution/protocol requirements']
        blockers = list(missing)
        if task['status'] != 'development_valid':
            blockers.append('Development execution requires development_valid; drafts cannot execute and formal approval needs an independent policy')
        return dict(task_family=task['family'], task_status=task['status'],
            robot_families=task['robot_families'], actuator_channels=task['actuator_channels'],
            signals=signals, environment=task['environment'], initializer=task['initializer'],
            timing=task['timing'], reference_kind=self.control_reference()['kind'],
            protocol_id=protocol if complete else None,
            protocol_template_id=protocol,
            task_reviewed=task['status'] != 'draft',
            configuration_check='not_checked', capability_check='not_checked', execution_admission='not_assessed',
            known_blockers=blockers,
            protocol_components=sorted(_protocol_requirements(dict(protocol_id=protocol, task_family=task['family'])) or []),
            selected_bindings=bindings,
            physical_inputs=self._physical_inputs() if complete else None,
            configuration_available=complete,
            missing=missing,
            applicability='protocol_id selects a known template only. Configuration presence is not validation. '
                'This view does not run admission checks; known_blockers is not exhaustive. Use check_compatibility(), '
                'compile_input(), Registry and route hooks for actual capability; frozen Study grants and budgets still govern execution')

    def _physical_inputs(self):
        self._require_configuration()
        tendons = self.configuration['robot']['structure']['data']['tendons']
        return dict(signal='tendon_tension', units='N', frame='tendon_path', phase='pre_step',
            control_period_s=self.task['timing']['control_period_s'], tendon_order=[t['id'] for t in tendons],
            lower=[0.]*len(tendons), upper=[t['force_limit_n'] for t in tendons],
            provenance=['/robot/structure/data/tendons', '/task/timing/control_period_s'])

    def holding_start_s(self):
        if self.task['family']=='task.tracking':raise ValueError('TRACKING_HAS_NO_HOLDING_WINDOW')
        self._require_configuration()
        settling=self.configuration['policy']['controller']['parameters']['data']['settling']
        return self.task['timing']['duration_s']-settling['window_s']

    def ranking_limits(self):
        if self.task['family']=='task.tracking':
            names=['max_position_error']
            if self.task['goal']['data']['time_requirement']=='none':
                names+=['path_coverage_error','terminal_position_error','progress_regression']
            return dict.fromkeys(names,self.task['evaluator']['parameters']['data']['max_error_m'])
        self._require_configuration()
        settling=self.configuration['policy']['controller']['parameters']['data']['settling']
        return dict(terminal_error_m=self.task['evaluator']['parameters']['data']['tolerance_m'],
            holding_max_error_m=settling['position_limit_m'],holding_max_speed_m_s=settling['speed_limit_m_s'])

    def control_search_options(self):
        """The registered task's norm constraints for the existing sequence search."""
        if self.task['family'] == 'task.tracking':
            if self.task['goal']['data']['time_requirement'] != 'timed':
                raise ValueError('UNTIMED_CONTROL_SEARCH_UNSUPPORTED: saved-polyline conditions required')
            period = self.task['timing']['sample_period_s']
            lo, hi = self.task['sampling']['window_s']
            times = [i*period for i in range(round(lo/period), round(hi/period)+1)]
            reference, _ = self.reference_at(times)
            return dict(tracking=dict(times_s=times, reference_m=reference.tolist(),
                max_error_m=self.task['evaluator']['parameters']['data']['max_error_m']))
        limits = self.ranking_limits()
        return dict(target=self.task['goal']['data']['target_m'], holding_start=self.holding_start_s(),
            position_limit=limits['holding_max_error_m'], terminal_position_limit=limits['terminal_error_m'],
            speed_limit=limits['holding_max_speed_m_s'])

    def reference_at(self, times):
        """Reach has a constant timed reference; geometric Tracking has none."""
        import numpy as np
        times = np.asarray(times, dtype=float)
        if self.task['family']=='task.tracking':
            from extensions.reference.contracts import TrackingGoal
            goal=TrackingGoal.model_validate(self.task['goal']['data'])
            rows=[goal.at_time(float(t)) for t in times.flat]
            return tuple(np.asarray([r[i] for r in rows]).reshape(times.shape+(3,)) for i in (0,1))
        target = self.task['goal']['data']['target_m']
        return (np.broadcast_to(target, times.shape + (3,)).copy(), np.zeros(times.shape + (3,)))

    def control_reference(self):
        """Small view of the authoritative task; no acceptance state is copied."""
        task = self.task
        kind = ('constant' if task['family'] == 'task.reach' else
                'timed' if task['goal']['data']['time_requirement'] == 'timed' else 'free_progress')
        return dict(kind=kind, task_family=task['family'], frame='world', units='m',
                    parameter='arc_length_m' if kind == 'free_progress' else 'time_s',
                    goal=task['goal'], evaluator=task['evaluator'],
                    condition_source='ResearchTaskAdapter.analysis_requirements',
                    error_signals=['position'] + (['relative_velocity'] if kind == 'timed' else []),
                    horizon_semantics='numerical_prediction_only' if kind == 'free_progress' else 'task_time')

    def local_path_reference(self, position, segment, lookahead_m, capture_m):
        """Ordered state projection and local lookahead, never a timed schedule.

        A corner must be approached before advancing to the next segment. The
        projected progress itself may regress; the independent evaluator owns
        regression/coverage acceptance. This is not joint optimal progress NMPC.
        """
        import numpy as np
        if self.control_reference()['kind'] != 'free_progress':
            raise ValueError('FREE_PROGRESS_REFERENCE_REQUIRED')
        vertices = np.asarray(self.task['goal']['data']['vertices_m'])
        lengths = np.linalg.norm(np.diff(vertices, axis=0), axis=1)
        if segment < len(lengths)-1 and np.linalg.norm(position-vertices[segment+1]) <= capture_m:
            segment += 1
        tangent = (vertices[segment+1]-vertices[segment])/lengths[segment]
        local = float(np.clip(np.dot(position-vertices[segment], tangent), 0, lengths[segment]))
        anchor = vertices[segment]+local*tangent
        target = vertices[segment]+min(local+lookahead_m, lengths[segment])*tangent
        return dict(segment=segment, progress_m=float(sum(lengths[:segment])+local),
                    anchor_m=anchor.tolist(), tangent=tangent.tolist(), position_m=target.tolist())

    def analysis_requirements(self, binding):
        """Translate each registered task's own sampled constraints and references."""
        from schemas.platform_analysis import TaskAnalysisRequirement
        from extensions.math_analysis.kernels import aligned_steps
        self._require_configuration()
        task, cfg = self.task, self.configuration
        conditions = self.condition_view()['conditions']
        duration, period = task['timing']['duration_s'], task['timing']['sample_period_s']
        last, _ = aligned_steps(duration, period)
        signal = next(s for s in task['observations'] if s['name'] == 'tip_position')
        if task['family']=='task.tracking':
            radius=conditions[0]['limit']
            provenance=['/task/goal','/task/evaluator/parameters']
            if task['goal']['data']['time_requirement']=='timed':
                lo,hi=task['sampling']['window_s'];indices=list(range(round(lo/period),round(hi/period)+1))
                reference,_=self.reference_at([i*period for i in indices])
                constraints=[dict(constraint_id='timed_tracking',signal=signal,indices=indices,kind='norm_bound',
                    reference=reference.tolist(),radius=radius,provenance=provenance+['/task/sampling'])]
            else:
                constraints=[dict(constraint_id='geometric_path',signal=signal,indices=list(range(last+1)),kind='path_bound',
                    path_vertices_m=task['goal']['data']['vertices_m'],reference=[],radius=radius,provenance=provenance)]
                # Sampled free progress is a proxy, not the saved-polyline evaluator.
                # Retain every independent acceptance condition in the existing
                # unsupported contract so downstream coverage cannot omit it.
                for condition in conditions:
                    name, meaning = condition['condition_id'], condition['meaning']
                    constraints.append(dict(constraint_id=name, signal=signal, indices=list(range(last+1)),
                        kind='unsupported', reference=[[0.]*signal['dimension'] for _ in range(last+1)],
                        provenance=provenance, unsupported_requirement=dict(
                            evaluator=task['evaluator'], condition=name, meaning=meaning,
                            limit=radius, units='m', goal=task['goal'],
                            scope='Complete saved polyline; indices mark the numerical witness grid, not an arrival deadline',
                            reason='path_bound does not independently evaluate this saved-polyline condition')))
        elif task['family'] != 'task.reach':
            constraints = [dict(constraint_id='unsupported_task', signal=signal, indices=[last],
                kind='unsupported', reference=[[0.]*signal['dimension']], provenance=['/task'],
                unsupported_requirement=task)]
        else:
            count, _ = aligned_steps(cfg['policy']['controller']['parameters']['data']['settling']['window_s'], period)
            holding = list(range(last-count, last+1))
            goal = task['goal']['data']['target_m']
            constraints = []
            for condition in conditions:
                name = condition['condition_id']
                indices = [last] if name == 'terminal_error_m' else holding
                reference = [0.]*3 if condition['signal']['name'] == 'tip_velocity' else goal
                provenance = condition['provenance'] + (['/policy/controller/parameters/data/settling/window_s']
                    if name == 'terminal_error_m' else [])
                constraints.append(dict(constraint_id=name, signal=condition['signal'], indices=indices,
                    kind='norm_bound', reference=[reference for _ in indices], radius=condition['limit'],
                    provenance=provenance))
        return TaskAnalysisRequirement(binding={**binding,
            **({'task_family':'task.tracking'} if task['family']=='task.tracking' else {}), 'task_identity':digest(task),
            'effective_configuration_identity':digest(cfg), 'task_id':task['task_id'], 'task_version':task['task_version']},
            duration_s=duration, sample_period_s=period, time_grid_s=[i*period for i in range(last+1)], constraints=constraints,
            horizon_semantics=('numerical_witness_horizon_inclusive_samples'
                if task['family']=='task.tracking' and task['goal']['data']['time_requirement']=='none'
                else 'absolute_task_time_inclusive_samples'),
            physical_inputs=self._physical_inputs())

    def operating_point(self, time_s=0.0):
        if self.task['family']=='task.tracking' and self.task['goal']['data']['time_requirement']=='none':
            return dict(reference_position_m=self.task['goal']['data']['vertices_m'][0],reference_velocity_m_s=None,
                frame='world',state_source='Named task initializer',reference_is_equilibrium=False,time_reference='none')
        position, velocity = self.reference_at(time_s)
        return dict(time_s=time_s, reference_position_m=position.tolist(), reference_velocity_m_s=velocity.tolist(), frame='world', state_source='Named task initializer; subsequent measured backend state', reference_is_equilibrium=False)

    def describe(self):
        task = self.task
        reach = task['family'] == 'task.reach'
        timed=not reach and task['goal']['data']['time_requirement']=='timed'
        metrics = [dict(name='terminal_error_m', unit='m', meaning='Sealed endpoint evaluator position error'), dict(name='holding_max_error_m', unit='m', meaning='Maximum sampled final-window tip error'), dict(name='holding_max_speed_m_s', unit='m/s', meaning='Maximum sampled world translational tip speed')] if reach else [dict(name=name, unit='m', meaning=meaning) for name, meaning in (('max_position_error', 'Maximum saved-polyline distance to geometric reference'), ('rms_position_error', 'RMS on uniform geometric arc-length samples; diagnostic'), ('terminal_position_error', 'Distance to path endpoint, no arrival deadline'), ('path_coverage_error','Reference path coverage by saved polyline'))]
        controller = self.configuration['policy']['controller']
        if timed:metrics=[dict(name=n,unit='m',meaning=m) for n,m in (
            ('max_position_error','Maximum sampled timed-reference error'),('rms_position_error','Arithmetic RMS over inclusive scored samples'),('terminal_position_error','Error against timed terminal reference'))]
        return dict(contract='research.task_adapter', version='1.0.0', family=task['family'], evaluator=task['evaluator'], output=next((s for s in task['observations'] if s['name'] == 'tip_position')), reference=task['goal'], operating_point=self.operating_point(), metrics=metrics, scoring_interval_s=task['sampling']['window_s'] if reach or timed else None, holding=controller['parameters']['data'].get('settling') if reach else None, timing=task['timing'], continuous_time_guarantee=False, context='Endpoint reach and final-window position/speed are distinct components. Offline deployment timing is diagnostic.' if reach else 'Explicit timed-reference tracking; no absolute-speed holding requirement.' if timed else 'Ordered geometric path and spatial coverage only; no timed reference, speed bound or arrival deadline. Timing config describes acquisition only.')

    def violation_samples(self, raw):
        """Task-specific diagnostic samples; independent acceptance stays authoritative."""
        if self.task['family']!='task.reach':return dict(status='unsupported',samples=[])
        limits=self.ranking_limits();rows=[];samples=raw.get('samples',[])
        for i,sample in enumerate(samples):
            tests=[]
            if i==len(samples)-1:tests.append(('terminal_error_m','position_error_m'))
            if sample['time_s']>=self.holding_start_s()-1e-12:
                tests.extend([('holding_max_error_m','position_error_m'),('holding_max_speed_m_s','speed_m_s')])
            for constraint,field in tests:
                derivation={}
                source_field=field
                if field=='position_error_m' and field not in sample:
                    import numpy as np
                    reference=self.reference_at([sample['time_s']])[0][0]
                    value=float(np.linalg.norm(np.asarray(sample['tip_m'])-reference))
                    source_field='tip_m'
                    derivation=dict(operation='euclidean_distance_to_task_reference',reference_m=reference.tolist())
                else:value=sample[field]
                limit=limits[constraint]
                if value>limit:
                    rows.append(dict(constraint=constraint,time_s=sample['time_s'],value=value,limit=limit,
                        normalized_excess=value/limit-1,raw_pointer='/samples/'+str(i)+'/'+source_field,
                        **(dict(derivation=derivation) if derivation else {})))
        return dict(status='sampled_diagnostic',samples=rows)

    def check_compatibility(self):
        """Check the actual registered pairing, separately from historical matches."""
        from schemas.platform import SessionInput
        from tools.platform_tasks import compile_input
        from tools.platform_registry import registry
        self._require_configuration()
        inp = SessionInput.model_validate(self.configuration)
        reg = registry()
        definition = reg.get(inp.policy.controller.extension_id, inp.policy.controller.version, 'controller')
        try:
            compile_input(inp.model_dump(mode='json'), reg)
            hook = definition.hook('route_applicability')
            if hook:
                hook(inp)
        except (ValueError, TypeError) as exc:
            return dict(technical_compatibility=dict(status='unsupported', reason=str(exc)), historical_evidence=dict(status='not_assessed'))
        return dict(technical_compatibility=dict(status='supported', reason='Registered task, evaluator, signals, initializer, controller and backend checks passed'), historical_evidence=dict(status='not_assessed', reason='Technical support does not establish exact frozen experiment identity or performance'))

    def lifecycle(self):
        from tools.platform_registry import registry
        policy = self.configuration['policy']
        caps = registry().get(policy['controller']['extension_id'], policy['controller']['version'], 'controller').capabilities
        return dict(initialization='Each new execution compiles its candidate and applies all named qpos/qvel from the task initializer once; measured warm states are regenerated', controller_reset_supported=caps.get('reset', False), controller_restore_supported=caps.get('restore', False), new_execution='New isolated controller/backend instances; task seed and initial state remain frozen', cache='New request_id with cache:new; only a distinct non-cache simulation receipt charged one backend solve is a repetition', restore='Restore research evidence and pending work from Store; do not resume a partial physical trajectory or controller warm state', unsupported=['In-place GVS controller reset', 'Controller/backend trajectory checkpoint continuation'], failure='Retain the original failed/incomplete slot; any deliberately authorized replacement is a separately labelled attempt')


def task_adapter(configuration):
    value = effective_input(configuration)
    if 'family' in value and 'goal' in value:
        value = dict(task=value)
    if value['task']['family'] not in ('task.reach', 'task.tracking','task.position_tool_axis','task.oriented_tracking'):
        raise ValueError('RESEARCH_TASK_ADAPTER_REQUIRED: '+value['task']['family'])
    # Validate the registered task itself before extracting task-specific meanings.
    from tools.platform_tasks import check_definition
    check_definition(value['task'])
    if value['task']['family']=='task.position_tool_axis':
        from tools.research.tool_axis_task import ToolAxisTaskAdapter
        return ToolAxisTaskAdapter(value)
    if value['task']['family']=='task.oriented_tracking':
        from tools.research.tool_axis_task import OrientedTrackingTaskAdapter
        return OrientedTrackingTaskAdapter(value)
    return ResearchTaskAdapter(value)


def _component(value, passed, unit=None, limit=None, reason=None):
    return dict(value=value, passed=passed, unit=unit, limit=limit, reason=reason)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _protocol_requirements(result):
    """Required meanings come from the supported protocol, never submitted keys."""
    common = {'evaluation_validity', 'execution_complete', 'task_evaluator', 'solver_errors', 'force_bounds'}
    protocol, family = (result.get('protocol_id'), result.get('task_family'))
    if (protocol, family) == ('offline_reach_hold_v1', 'task.reach'):
        return common | {'holding_coverage', 'holding_position', 'holding_speed', 'evaluator:task_bound'}
    if (protocol, family) == ('development_tracking_v1', 'task.tracking'):
        return common | {'tracking_sampling', 'evaluator:tracking_max_error', 'evaluator:path_coverage',
                         'evaluator:path_start', 'evaluator:path_end', 'evaluator:path_progress_regression'}
    if (protocol, family) == ('offline_timed_tracking_v1', 'task.tracking'):
        return common | {'tracking_sampling', 'evaluator:tracking_max_error'}
    if (protocol,family)==('offline_position_tool_axis_v1','task.position_tool_axis'):
        return common | {'tool_axis_sampling','evaluator:tool_position','evaluator:tool_axis_direction'}
    if (protocol,family)==('offline_oriented_tracking_v1','task.oriented_tracking'):
        return common | {'tool_axis_sampling','evaluator:tracking_max_error','evaluator:tool_axis_direction','rigid_tool_binding'}
    if (protocol,family)==('offline_oriented_tracking_v2','task.oriented_tracking'):
        return common | {'tool_axis_sampling','evaluator:tracking_max_error','evaluator:tool_axis_direction','rigid_tool_binding','no_environment_contact'}
    return None


def _outcome_issue(result):
    required = _protocol_requirements(result)
    if required is None:
        return 'TASK_PROTOCOL_REQUIREMENTS_UNAVAILABLE'
    components = result.get('components') or {}
    if required - components.keys() or any(type(c.get('passed')) is not bool for c in components.values()):
        return 'PROTOCOL_REQUIRED_COMPONENT_MISSING_OR_UNKNOWN'
    # Invalidity and absent coverage are not ordinary physical failures.
    coverage = ('holding_coverage' if result['task_family']=='task.reach' else
        'tool_axis_sampling' if result['task_family'] in ('task.position_tool_axis','task.oriented_tracking') else 'tracking_sampling')
    if any(components[n]['passed'] is not True for n in ('evaluation_validity', 'execution_complete', coverage)):
        return 'PROTOCOL_VALIDITY_OR_COVERAGE_UNRESOLVED'
    passed = all(c['passed'] for c in components.values())
    if (result.get('status') != ('accepted' if passed else 'valid_failure') or
            result.get('accepted') is not passed):
        return 'ACCEPTANCE_COMPONENT_OUTCOME_INCONSISTENT'
    return None


def _source_issue(result, evidence=None):
    """Check presence before equality; reach profile links stay reach-specific."""
    sources = result.get('sources') or {}
    evidence = evidence if evidence is not None else result.get('evidence_binding') or {}
    for kind in ('evaluation', 'profile'):
        ref = sources.get(kind)
        if not isinstance(ref, dict) or not ref.get('artifact_id'):
            return 'PROTOCOL_REQUIRED_SOURCE_MISSING:' + kind
        if evidence.get(kind) is None:
            return 'PROTOCOL_REQUIRED_SOURCE_MISSING:' + kind + '_evidence'
        if ref != evidence[kind]:
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    execution = result.get('execution_id')
    if not execution or not evidence.get('simulation'):
        return 'PROTOCOL_REQUIRED_SOURCE_MISSING:execution'
    binding = evidence.get('profile_binding') or {}
    if binding.get('execution_id') is not None and binding['execution_id'] != execution:
        return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    evaluation_binding = evidence.get('evaluation_binding') or {}
    if (evaluation_binding.get('source_execution_id') not in (None,execution) or
            evaluation_binding.get('original_execution_id') not in (None,execution) or
            evaluation_binding.get('source') not in (None,evidence['simulation'])):
        return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    if result['protocol_id'] in ('offline_reach_hold_v1', 'offline_timed_tracking_v1','offline_position_tool_axis_v1','offline_oriented_tracking_v1','offline_oriented_tracking_v2'):
        for kind in ('evaluation', 'simulation', 'execution_id'):
            if not binding.get(kind):
                return 'PROTOCOL_REQUIRED_SOURCE_MISSING:profile_' + kind
        if (binding['evaluation'] != sources['evaluation'] or binding['simulation'] != evidence['simulation'] or
                binding['execution_id'] != execution):
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    for kind, tool in (('evaluation', 'evaluation.run'), ('profile', 'control.profile_report')):
        receipts = [r for r in evidence.get('receipts', []) if r.get('tool_id')==tool]
        if receipts and (len(receipts)!=1 or receipts[0].get('output')!=sources[kind] or
                         receipts[0].get('execution_status')!='completed'):
            return 'ACCEPTANCE_SOURCE_BINDING_MISMATCH'
    return None


def assemble_acceptance(configuration, evaluation, profile, *, evaluation_reference=None, profile_reference=None, motion=None, protocol_id=None):
    """Compose sealed evaluator and profile, preserving missing and failed components.

    `profile` is control.profile_report's detail or the enclosing ProfileOutput.
    Optional sealed motion verifies the exact holding grid without recomputing
    physics. The profile's `available` is otherwise the existing coverage authority.
    """
    from schemas.platform import EvaluationResult
    from tools.platform_store import plain
    adapter = task_adapter(configuration)
    cfg, task = (adapter.configuration, adapter.task)
    preview_only=task['status']=='draft' and evaluation is None and profile is None
    if task['family']=='task.tracking' and ((task['status']!='development_valid' and not preview_only) or
            cfg['policy']['controller']['version']!='12.0.0'):
        raise ValueError('TRACKING_COMPOSITE_ACCEPTANCE_UNSUPPORTED: independent evaluator available; execution/force protocol not implemented')
    expected_protocol = adapter.execution_requirements()['protocol_template_id']
    if protocol_id is None:
        protocol_id = expected_protocol
    if protocol_id != expected_protocol:
        raise ValueError('TASK_ACCEPTANCE_PROTOCOL_MISMATCH')
    ev = plain(evaluation) if evaluation is not None else None
    if ev is not None:
        ev = plain(EvaluationResult.model_validate(ev))
    report = plain(profile) if profile is not None else {}
    report = report.get('detail', report)
    components = {}
    issues = []
    controller = cfg['policy']['controller']
    validity = None if ev is None else ev['validity']
    components['evaluation_validity'] = _component(validity, None if ev is None else validity == 'valid')
    complete = report.get('complete')
    components['execution_complete'] = _component(complete, complete)
    components['task_evaluator'] = _component(None if ev is None else ev['task_success'], None if ev is None else ev['task_success'])
    if ev and ev['evaluator'] != task['evaluator']['extension_id']:
        issues.append('EVALUATOR_IDENTITY_MISMATCH')
    if ev and ev.get('source_execution_id') and (report.get('execution_id') != ev['source_execution_id']):
        issues.append('EVALUATION_PROFILE_EXECUTION_MISMATCH')
    if ev and report.get('evaluation') and evaluation_reference and (report['evaluation'] != plain(evaluation_reference)):
        issues.append('EVALUATION_REFERENCE_MISMATCH')
    if ev and report.get('simulation') and (report['simulation'] != ev['source']):
        issues.append('EVALUATION_SOURCE_MISMATCH')
    if ev and 'official_task_success' in report and (report['official_task_success'] != ev['task_success']):
        issues.append('PROFILE_EVALUATOR_OUTCOME_MISMATCH')
    if report.get('task') and digest(report['task']) != digest(task):
        issues.append('PROFILE_TASK_MISMATCH')
    if report.get('execution_scope'):
        from extensions.tendon_family.gvs_profile import execution_scope
        if report['execution_scope'] != execution_scope(cfg):
            issues.append('PROFILE_EXECUTION_SCOPE_MISMATCH')
    metrics = {m['name']: m['value'] for m in (ev or {}).get('metrics', [])}
    constraints = (ev or {}).get('constraints', [])
    for constraint in constraints:
        components['evaluator:' + constraint['name']] = _component(constraint['observed'], constraint['satisfied'], constraint['units'], constraint['limit'])
    errors = report.get('solver_error_count')
    components['solver_errors'] = _component(errors, errors == 0 if _number(errors) else None, 'count', 0)
    violation = report.get('force_bound_violation_n')
    components['force_bounds'] = _component(violation, 0 <= violation <= 1e-08 if _number(violation) else None, 'N', 1e-08)
    if task['family'] == 'task.reach':
        metrics = dict(terminal_error_m=metrics.get('position_error'), holding_max_error_m=None, holding_max_speed_m_s=None)
        settling = report.get('sampled_settling', {})
        limits = cfg['policy']['controller']['parameters']['data']['settling']
        matched = all((settling.get(k) == limits[k] for k in ('window_s', 'position_limit_m', 'speed_limit_m_s')))
        covered = settling.get('available')
        if covered and (not matched):
            issues.append('HOLDING_DEFINITION_MISMATCH')
        duration, period = (task['timing']['duration_s'], task['timing']['sample_period_s'])
        expected = round(limits['window_s'] / period) + 1
        if motion is not None:
            selected = [r for r in plain(motion) if duration - limits['window_s'] - 1e-09 <= r['time_s'] <= duration + 1e-09]
            grid = [duration - limits['window_s'] + i * period for i in range(expected)]
            covered = bool(covered and len(selected) == expected and all((abs(r['time_s'] - t) <= 1e-08 for r, t in zip(selected, grid))))
        components['holding_coverage'] = _component(covered, covered, 'inclusive uniform samples', expected)
        for name, field, threshold, unit in (('holding_position', 'max_error_m', 'position_limit_m', 'm'), ('holding_speed', 'max_speed_m_s', 'speed_limit_m_s', 'm/s')):
            value = settling.get(field)
            components[name] = _component(value, 0 <= value <= limits[threshold] if covered and matched and _number(value) else None, unit, limits[threshold])
        if covered and matched and all((components[n]['passed'] is not None for n in ('holding_position', 'holding_speed'))):
            calculated = components['holding_position']['passed'] and components['holding_speed']['passed']
            if settling.get('passed') is not calculated:
                issues.append('PROFILE_HOLDING_OUTCOME_MISMATCH')
        metrics.update(holding_max_error_m=settling.get('max_error_m'), holding_max_speed_m_s=settling.get('max_speed_m_s'))
    elif task['family'] in ('task.position_tool_axis','task.oriented_tracking'):
        covered=report.get('tool_axis_sampling_complete')
        components['tool_axis_sampling']=_component(covered,covered,reason='Both real world position and unit tool-axis signals on the complete post-step grid')
        if task['family']=='task.oriented_tracking':
            bound=report.get('rigid_tool_binding')
            components['rigid_tool_binding']=_component(bound,bound,reason='Compiled MuJoCo payload mass, COM, inertia and tool site match frozen task; no external-force substitution')
            if protocol_id=='offline_oriented_tracking_v2':
                contact_free=report.get('no_environment_contact')
                components['no_environment_contact']=_component(contact_free,contact_free,reason='Every independent physics step checked for environment contact; the frozen task does not permit contact')
    else:
        covered = report.get('tracking_sampling_complete')
        components['tracking_sampling'] = _component(covered, covered, reason=(
            'Full post-step motion and pre-step tension grids; r(t) is scored on the frozen inclusive window'
            if protocol_id == 'offline_timed_tracking_v1' else
            'Profile verifies recorded post-step motion and pre-step tension grids; acquisition completeness is not a task deadline'))
    required = _protocol_requirements(dict(protocol_id=protocol_id, task_family=task['family']))
    for name in sorted(required - components.keys()):
        components[name] = _component(None, None, reason='Required registered protocol component absent')
    missing = [name for name, c in components.items() if c['passed'] is None]
    if issues or validity == 'invalid':
        status, accepted = ('invalid', None)
    elif validity == 'incomplete' or complete is False:
        status, accepted = ('incomplete', None)
    elif missing or not components['holding_coverage' if task['family']=='task.reach' else 'tool_axis_sampling' if task['family'] in ('task.position_tool_axis','task.oriented_tracking') else 'tracking_sampling']['passed']:
        status, accepted = ('missing_evidence', None)
    else:
        accepted = all((c['passed'] for c in components.values()))
        status = 'accepted' if accepted else 'valid_failure'
    return dict(contract='research.task_acceptance', version='1.0.0', protocol_id=protocol_id, task_family=task['family'], task_identity=digest(task), status=status, accepted=accepted, components=components, metrics=metrics, missing=missing, issues=issues, execution_id=report.get('execution_id'), sources=dict(evaluation=plain(evaluation_reference), profile=plain(profile_reference)), evidence_binding=dict(evaluation=plain(evaluation_reference), profile=plain(profile_reference), simulation=(ev or {}).get('source'), evaluation_binding={k: (ev or {}).get(k) for k in ('source', 'source_execution_id', 'original_execution_id')}, profile_binding={k: report[k] for k in ('evaluation', 'simulation', 'execution_id') if k in report}), evaluator_tension_channels=[t['id'] for t in cfg['robot']['structure']['data']['tendons']] if task['family'] == 'task.tracking' else None, timing=dict(**task['timing'], real_time_required=False, real_time_demonstrated=report.get('real_time_demonstrated'), deadline_misses=report.get('deadline_misses'), mean_update_s=report.get('mean_update_s'), simulation_wall_s=report.get('simulation_wall_s')), continuous_time_guarantee=False)


def aggregate_acceptance(records, scheduled, *, schedule=None, evidence_policy=None, comparison_scope=None):
    """The frozen scheduled denominator includes absent, incomplete and replay slots."""
    from tools.platform_store import plain
    if not isinstance(scheduled, int) or scheduled<=0 or len(records)>scheduled:
        raise ValueError('POSITIVE_FROZEN_SCHEDULE_REQUIRED')
    if schedule is not None and len(schedule)!=scheduled:
        raise ValueError('SCHEDULE_COUNT_MISMATCH')
    policy = evidence_policy or {'require_fresh_repetitions':True, 'allow_historical_reuse':False}
    if any(type(policy.get(k,default)) is not bool for k,default in (
            ('require_fresh_repetitions',True),('allow_historical_reuse',False))):
        raise ValueError('DECLARED_FRESHNESS_POLICY_REQUIRED')
    if any('fresh_required' in s and type(s['fresh_required']) is not bool for s in (schedule or [])):
        raise ValueError('DECLARED_SLOT_FRESHNESS_REQUIRED')
    def slot_key(row):
        return (row.get('case_id'),row.get('seed'),row.get('repetition'))
    if schedule is not None and len({slot_key(s) for s in schedule}) != scheduled:
        raise ValueError('DUPLICATE_SCHEDULE_SLOT')
    results = [r['acceptance'] for r in records if r.get('acceptance')]
    families = {r['task_family'] for r in results}
    protocols = {r['protocol_id'] for r in results}
    if len(families)>1 or len(protocols)>1:
        raise ValueError('AGGREGATION_TASK_PROTOCOL_MISMATCH')
    family = next(iter(families), None)
    metric_names = (('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
                    if family=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error')
                    if family=='task.tracking' else ())
    slots, seen, entries = set(), set(), []
    accepted = 0
    for record in records:
        slot = (record.get('case_id'), record.get('seed'), record.get('repetition'))
        if slot in slots:
            raise ValueError('DUPLICATE_SCHEDULE_SLOT')
        slots.add(slot)
        if schedule is not None and not any(slot==(s.get('case_id'),s.get('seed'),s.get('repetition')) for s in schedule):
            raise ValueError('UNSCHEDULED_REPETITION')
        receipt = plain(record.get('receipt') or {})
        result = record.get('acceptance')
        execution = receipt.get('execution_id')
        fresh = bool(not record.get('historical_reuse') and execution and execution not in seen and receipt.get('cache_hit') is False
                     and receipt.get('charged',{}).get('backend_solves')==1
                     and receipt.get('tool_id') in ('simulation.run','research.physical_replay')
                     and (receipt.get('tool_id')!='research.physical_replay' or receipt.get('execution_status')=='completed')
                     and receipt.get('original_execution_id') in (None,execution))
        if execution:
            seen.add(execution)
        binding_matches = bool(result and execution == result.get('execution_id'))
        source_issues=[]
        for kind in ('evaluation','profile'):
            expected=((result or {}).get('sources') or {}).get(kind)
            if record.get(kind) and record[kind]!=expected:
                source_issues.append(kind)
        declaration=next((s for s in (schedule or []) if slot==slot_key(s)), {})
        fresh_required=declaration.get('fresh_required', policy.get('require_fresh_repetitions', True))
        # Reuse is protocol evidence, never a fresh repetition. An explicit
        # policy and source binding are both required for a nonfresh slot.
        reuse = bool(not fresh and policy.get('allow_historical_reuse') and
            record.get('historical_reuse') and binding_matches and execution and
            receipt.get('tool_id')=='simulation.run')
        evidence_eligible = fresh or (not fresh_required and reuse)
        count = bool(evidence_eligible and binding_matches and result['accepted'] is True)
        accepted += count
        entries.append(dict(case_id=slot[0], seed=slot[1], repetition=slot[2],
            fresh_execution=fresh, acceptance_execution_matches=binding_matches,
            fresh_required=fresh_required,
            historical_reuse=bool(record.get('historical_reuse') or receipt.get('cache_hit')),
            reuse_permitted=reuse,
            evidence_eligible=evidence_eligible, receipt=receipt,
            source_binding_issues=source_issues,
            source_evidence=dict(evaluation=record.get('evaluation'), profile=record.get('profile'),
                simulation=record.get('simulation',receipt.get('output')), receipts=record.get('receipts', []),
                evaluation_binding=(record.get('evaluation_data') or
                    (result or {}).get('evidence_binding', {}).get('evaluation_binding') or {}),
                profile_binding={k:record.get('profile_summary', {}).get(k)
                    for k in ('evaluation','simulation','execution_id')}),
            counted_accepted=count, acceptance=result,
            status=('not_new_repetition' if receipt and not fresh else
                    'acceptance_identity_mismatch' if result and result.get('execution_id') and not binding_matches else
                    result['status'] if result else 'pending_or_incomplete')))
    return dict(contract='research.task_aggregation',version='1.0.0',accepted=accepted,scheduled=scheduled,
        task_family=family,protocol_id=next(iter(protocols), None),
        schedule_identity=digest(schedule) if schedule is not None else None,
        schedule=schedule, evidence_policy=policy, comparison_scope=comparison_scope,
        recorded=len(records),unrecorded=scheduled-len(records),joint_acceptance_fraction=accepted/scheduled,
        all_scheduled_accepted=accepted==scheduled,entries=entries,
        interpretation='Deterministic frozen-case observed fraction; not a population success probability',
        metrics={name:max(r['metrics'][name] for r in results)
                 if len(results)==scheduled and all(_number(r['metrics'].get(name)) for r in results) else None
                 for name in metric_names})


def comparison_prerequisites(candidate, incumbent):
    """Check complete interpretable slots before any aggregate ranking.

    Task identity is compared per declared slot; robot/control identity may
    differ. Historical aggregates remain readable, but raw receipts are needed
    to re-establish executable comparison prerequisites.
    """
    issues=[]
    seen=set()
    if candidate.get('comparison_scope') != incumbent.get('comparison_scope'):
        issues.append(dict(reason='INCOMPATIBLE_COMPARISON_SCOPE'))
    if candidate.get('evidence_policy') != incumbent.get('evidence_policy'):
        issues.append(dict(reason='INCOMPATIBLE_EVIDENCE_POLICY'))
    indexed=[]
    for role, group in [('candidate',candidate),('incumbent',incumbent)]:
        schedule=group.get('schedule')
        entries=group.get('entries',[])
        key=lambda r:(r.get('case_id'),r.get('seed'),r.get('repetition'))
        required={key(r) for r in (schedule or [])}
        actual={key(r) for r in entries}
        if schedule is None or len(required)!=group['scheduled'] or digest(schedule)!=group.get('schedule_identity'):
            issues.append(dict(role=role,reason='DECLARED_SCHEDULE_REQUIRED'))
        for slot in sorted(required-actual, key=str):
            issues.append(dict(role=role,slot=list(slot),reason='MISSING_SLOT'))
        if len(actual)!=len(entries) or actual-required:
            issues.append(dict(role=role,reason='DUPLICATE_OR_UNDECLARED_SLOT'))
        counted=0
        for entry in entries:
            slot=key(entry)
            result=entry.get('acceptance') or {}
            receipt=entry.get('receipt') or {}
            eid=receipt.get('execution_id')
            fresh=bool(not entry.get('historical_reuse') and eid and eid not in seen and receipt.get('cache_hit') is False and
                receipt.get('charged',{}).get('backend_solves')==1 and receipt.get('tool_id')=='simulation.run' and
                receipt.get('original_execution_id') in (None,eid))
            if eid:
                seen.add(eid)
            declaration=next((s for s in (schedule or []) if key(s)==slot), {})
            policy=group.get('evidence_policy') or {}
            fresh_required=declaration.get('fresh_required',policy.get('require_fresh_repetitions',True))
            reuse=bool(not fresh_required and policy.get('allow_historical_reuse') and entry.get('historical_reuse'))
            reason=None
            if not eid or eid!=result.get('execution_id') or receipt.get('tool_id')!='simulation.run':
                reason='EXECUTION_RECEIPT_BINDING_MISMATCH'
            elif entry.get('source_binding_issues'):
                reason='ACCEPTANCE_SOURCE_BINDING_MISMATCH'
            elif receipt.get('execution_status')!='completed':
                reason='EXECUTION_NOT_COMPLETE'
            elif not fresh and not reuse:
                reason='REQUIRED_FRESH_REPETITION_ABSENT'
            elif result.get('status') not in ('accepted','valid_failure') or result.get('accepted') is not (result.get('status')=='accepted'):
                reason='OUTCOME_NOT_INTERPRETABLE'
            elif result.get('task_family')!=group['task_family'] or result.get('protocol_id')!=group['protocol_id']:
                reason='TASK_PROTOCOL_MISMATCH'
            elif _outcome_issue(result):
                reason=_outcome_issue(result)
            elif _source_issue(result, entry.get('source_evidence')):
                reason=_source_issue(result, entry.get('source_evidence'))
            elif any(not _number(result['metrics'].get(n)) for n in group.get('metrics',{})):
                reason='METRIC_MISSING_OR_UNINTERPRETABLE'
            if reason:
                issues.append(dict(role=role,slot=list(slot),reason=reason))
            else:
                counted+=result['accepted'] is True
        if counted!=group['accepted'] or group['joint_acceptance_fraction']!=group['accepted']/group['scheduled']:
            issues.append(dict(role=role,reason='AGGREGATE_COUNT_MISMATCH'))
        indexed.append({key(e):e.get('acceptance') or {} for e in entries})
    for slot in indexed[0].keys() & indexed[1].keys():
        a,b=indexed[0][slot],indexed[1][slot]
        semantics=lambda r:(r.get('task_identity'),r.get('protocol_id'),
            {k:(v.get('unit'),v.get('limit')) for k,v in r.get('components',{}).items()})
        if not a.get('task_identity') or semantics(a)!=semantics(b):
            issues.append(dict(slot=list(slot),reason='INCOMPATIBLE_TASK_OR_METRIC_MEANINGS'))
    return issues


def compare_acceptance(candidate, incumbent, tolerance=1e-9):
    """Primary acceptance followed by componentwise physical comparison, no score."""
    if candidate['contract'] != incumbent['contract']:
        return dict(relation='unavailable',reason='ACCEPTANCE_CONTRACT_MISMATCH')
    aggregate = candidate['contract']=='research.task_aggregation'
    if aggregate:
        if candidate['scheduled'] != incumbent['scheduled']:
            return dict(relation='unavailable',reason='SCHEDULE_COUNT_MISMATCH')
        if (candidate['task_family'],candidate['protocol_id'],candidate['schedule_identity']) != (incumbent['task_family'],incumbent['protocol_id'],incumbent['schedule_identity']):
            return dict(relation='unavailable',reason='TASK_ACCEPTANCE_SCHEDULE_MISMATCH')
        unresolved=comparison_prerequisites(candidate,incumbent)
        if unresolved:
            return dict(relation='unavailable',reason='Comparison prerequisites unresolved',unresolved=unresolved)
        left, right = candidate['joint_acceptance_fraction'], incumbent['joint_acceptance_fraction']
    else:
        if (candidate['task_identity'],candidate['protocol_id']) != (incumbent['task_identity'],incumbent['protocol_id']):
            return dict(relation='unavailable',reason='TASK_ACCEPTANCE_IDENTITY_MISMATCH')
        if candidate['accepted'] is None or incumbent['accepted'] is None:
            return dict(relation='unavailable',reason='Missing, invalid or incomplete acceptance is not a physical failure')
        for result in (candidate, incumbent):
            issue = _outcome_issue(result) or _source_issue(result)
            if issue:
                return dict(relation='unavailable',reason=issue)
        left,right = int(candidate['accepted']),int(incumbent['accepted'])
    if left != right:
        names=(('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
               if candidate['task_family']=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error'))
        components={n:dict(candidate=candidate['metrics'].get(n),incumbent=incumbent['metrics'].get(n),
            change=candidate['metrics'][n]-incumbent['metrics'][n]) for n in names
            if all(_number(v['metrics'].get(n)) for v in (candidate,incumbent))}
        return dict(relation='improved' if left>right else 'worse',basis='primary_joint_acceptance',
                    componentwise=components)
    names = (('terminal_error_m','holding_max_error_m','holding_max_speed_m_s')
             if candidate['task_family']=='task.reach' else ('max_position_error','rms_position_error','terminal_position_error'))
    if any(not _number(v['metrics'].get(n)) for v in (candidate,incumbent) for n in names):
        return dict(relation='unavailable',reason='Component metrics missing')
    changes = {n:candidate['metrics'][n]-incumbent['metrics'][n] for n in names}
    better, worse = any(v < -tolerance for v in changes.values()), any(v > tolerance for v in changes.values())
    return dict(relation='tradeoff' if better and worse else 'improved' if better else 'worse' if worse else 'equivalent',
                basis='componentwise_physical_metrics',changes=changes,
                componentwise={n:dict(candidate=candidate['metrics'][n],incumbent=incumbent['metrics'][n],change=changes[n]) for n in names},
                computation='reported separately')


def stop_interpretation(result, reason, *, budget_exhausted=False, remaining_work=0, operational=None, assertions=()):
    """A legal stop and a supported success claim do not prove an optimal stop."""
    aggregate = result.get('contract')=='research.task_aggregation'
    accepted = result.get('all_scheduled_accepted',False) if aggregate else result.get('accepted') is True
    legal = ((reason=='budget_exhausted' and budget_exhausted) or
             (reason=='completed_schedule' and remaining_work==0) or
             reason in ('predeclared_policy','voluntary_stop','limited_value','engineering_blocker'))
    checked=[]
    for assertion in assertions:
        resource=assertion.get('resource')
        field=assertion.get('field')
        values=(operational or {}).get(field) if field in (
            'executable_capacity','plan_shortfall','actual_shortfall') else None
        observed=values.get(resource) if isinstance(values,dict) else None
        checked.append(dict(assertion=assertion,observed=observed,
            support='not_assessed' if observed is None else 'supported' if observed==assertion.get('value') else 'unsupported'))
    explanation=('unsupported' if any(r['support']=='unsupported' for r in checked) else
        'supported' if checked and all(r['support']=='supported' for r in checked) else 'not_assessed')
    return dict(legal=legal,reason=reason,success_claim_supported=accepted,
                explanation_support=explanation,checked_assertions=checked,
                optimality='not_assessed',acceptance_result=result,
                budget_is_upper_bound=True)
