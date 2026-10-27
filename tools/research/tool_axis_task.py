"""Task-specific views for position plus a directed tool axis; no new task registry."""
from tools.research_tasks import ResearchTaskAdapter
from tools.state_io import digest


class ToolAxisTaskAdapter(ResearchTaskAdapter):
    protocol_id='offline_position_tool_axis_v1'
    def condition_view(self):
        limits=self.task['evaluator']['parameters']['data'];rows=[]
        for name,metric,signal,limit,unit,meaning in (
            ('tool_position','max_position_error','tip_position','position_tolerance_m','m','Maximum sampled world tip distance to target'),
            ('tool_axis_direction','max_tool_axis_angle_error','tip_tool_axis','angle_tolerance_rad','rad','Maximum directed tool-axis angle; axial roll is unconstrained')):
            rows.append(dict(condition_id=name,metric=metric,limit=limits[limit],units=unit,meaning=meaning,
                signal=next(s for s in self.task['observations'] if s['name']==signal),
                sampling=dict(mode='inclusive_scored_post_step_grid',window_s=self.task['sampling']['window_s'],sample_period_s=self.task['timing']['sample_period_s']),
                provenance=['/task/goal','/task/evaluator/parameters','/task/sampling'],
                evaluation_binding=dict(source='EvaluationResult',constraint=name,metric=metric),
                mathematical_binding=dict(constraint_id=name,coverage='unsupported' if unit=='rad' else 'exact_sampled_expression'),
                expressibility='unsupported' if unit=='rad' else 'sampled_norm_bound',
                expression_reason='Native sequence response uses the equivalent unit-axis chord cone; existing affine/GVS tool-axis analysis is not applicable' if unit=='rad' else 'norm(p-target) <= position tolerance'))
        return dict(contract='research.task_conditions',version='1.0.0',task_identity=digest(self.task),task_status=self.task['status'],
            evaluator=self.task['evaluator'],conditions=rows,missing=[],continuous_time_guarantee=False,
            authority='registered evaluator plus frozen independent replay protocol')

    def control_reference(self):
        return dict(kind='constant',task_family=self.task['family'],frame='world',units='m',goal=self.task['goal'],
            evaluator=self.task['evaluator'],condition_source='ResearchTaskAdapter.analysis_requirements',
            error_signals=['position','tool_axis_direction'],horizon_semantics='numerical_prediction_only',
            supported_control='native_sequence_and_independent_physical_replay_only; no position-only NMPC substitution')

    def ranking_limits(self):
        limits=self.task['evaluator']['parameters']['data']
        return dict(max_position_error=limits['position_tolerance_m'],max_tool_axis_angle_error=limits['angle_tolerance_rad'])

    def control_search_options(self):
        dt=self.task['timing']['sample_period_s'];lo,hi=self.task['sampling']['window_s']
        return dict(tool_axis=dict(times_s=[i*dt for i in range(round(lo/dt),round(hi/dt)+1)],
            **self.task['goal']['data'],**self.task['evaluator']['parameters']['data']))

    def execution_requirements(self):
        from tools.research_tasks import _protocol_requirements
        task=self.task;complete={'robot','policy'}<=self.configuration.keys();protocol=self.protocol_id
        return dict(task_family=task['family'],task_status=task['status'],robot_families=task['robot_families'],
            actuator_channels=task['actuator_channels'],signals=task['observations'],environment=task['environment'],
            initializer=task['initializer'],timing=task['timing'],reference_kind='constant',protocol_id=protocol if complete else None,
            protocol_template_id=protocol,task_reviewed=task['status']!='draft',configuration_available=complete,
            physical_inputs=self._physical_inputs() if complete else None,missing=[] if complete else ['Effective configuration required'],
            configuration_check='not_checked',capability_check='not_checked',execution_admission='not_assessed',
            known_blockers=[] if complete and task['status']=='development_valid' else ['Reviewed effective configuration required'],
            protocol_components=sorted(_protocol_requirements(dict(protocol_id=protocol,task_family=task['family']))),
            selected_bindings={k:{f:self.configuration['policy'][k][f] for f in ('extension_id','version')}
                for k in ('controller','backend','dynamics_model') if complete},
            applicability='Native fixed-sequence execution only; independent evaluator requires both position and directed axis signals')

    def analysis_requirements(self,binding):
        from schemas.platform_analysis import TaskAnalysisRequirement
        task=self.task;dt=task['timing']['sample_period_s'];duration=task['timing']['duration_s'];count=round(duration/dt)
        options=self.control_search_options()['tool_axis'];indices=[round(t/dt) for t in options['times_s']]
        constraints=[]
        for c in self.condition_view()['conditions']:
            position=c['signal']['name']=='tip_position'
            reference=(options.get('reference_m') if position else options.get('target_axes_world'))
            if reference is None:reference=[task['goal']['data']['target_m' if position else 'target_axis_world'] for _ in indices]
            row=dict(constraint_id=c['mathematical_binding']['constraint_id'],signal=c['signal'],indices=indices,
                kind='norm_bound' if position else 'unsupported',reference=reference,provenance=c['provenance'])
            if position:row['radius']=c['limit']
            else:row['unsupported_requirement']=dict(kind='directed_unit_axis_cone',goal=task['goal'],angle_tolerance_rad=c['limit'],
                reason='Existing affine/GVS orientation analysis not applicable; native sequence uses real unit-axis observations')
            constraints.append(row)
        return TaskAnalysisRequirement(binding={**binding,'task_family':task['family'],'task_identity':digest(task),'effective_configuration_identity':digest(self.configuration),
             'task_id':task['task_id'],'task_version':task['task_version']},
            duration_s=duration,sample_period_s=dt,time_grid_s=[i*dt for i in range(count+1)],constraints=constraints,physical_inputs=self._physical_inputs())

    def describe(self):
        return dict(contract='research.task_adapter',version='1.0.0',family=self.task['family'],evaluator=self.task['evaluator'],
            reference=self.task['goal'],output=self.task['observations'],operating_point=self.operating_point(),
            metrics=[dict(name=c['metric'],unit=c['units'],meaning=c['meaning']) for c in self.condition_view()['conditions']],
            timing=self.task['timing'],scoring_interval_s=self.task['sampling']['window_s'],holding=None,
            continuous_time_guarantee=False,context='Position plus directed tool axis; no complete 3D orientation or axial-roll requirement')


class OrientedTrackingTaskAdapter(ToolAxisTaskAdapter):
    protocol_id='offline_oriented_tracking_v1'

    def condition_view(self):
        task=self.task;limits=task['evaluator']['parameters']['data'];rows=[]
        for name,metric,signal,limit,unit,binding in (
            ('tracking_max_error','max_position_error','tip_position','max_error_m','m','timed_tracking'),
            ('tool_axis_direction','max_tool_axis_angle_error','tip_tool_axis','angle_tolerance_rad','rad','tool_axis_direction')):
            rows.append(dict(condition_id=name,metric=metric,limit=limits[limit],units=unit,
                meaning='Maximum error against timed r(t) at every scored sample' if unit=='m' else 'Maximum directed tool-axis error against the timed unit-axis reference',
                signal=next(s for s in task['observations'] if s['name']==signal),
                sampling=dict(mode='inclusive_scored_post_step_grid',window_s=task['sampling']['window_s'],sample_period_s=task['timing']['sample_period_s']),
                provenance=['/task/goal','/task/evaluator/parameters','/task/sampling'],
                evaluation_binding=dict(source='EvaluationResult',constraint=name,metric=metric),
                mathematical_binding=dict(constraint_id=binding,coverage='unsupported' if unit=='rad' else 'exact_sampled_expression'),
                expressibility='unsupported' if unit=='rad' else 'sampled_norm_bound',
                expression_reason='Native response uses the equivalent unit-axis chord cone; affine/GVS orientation is not applicable' if unit=='rad' else 'Original BF4 timed norm(p_k-r(t_k)) <= limit semantics'))
        return dict(contract='research.task_conditions',version='1.0.0',task_identity=digest(task),task_status=task['status'],
            evaluator=task['evaluator'],conditions=rows,missing=[],continuous_time_guarantee=False,
            authority='registered timed position/axis evaluator plus independent rigid-tool binding protocol')

    def reference_at(self,times):
        import numpy as np
        from extensions.reference.contracts import OrientedTrackingGoal
        goal=OrientedTrackingGoal.model_validate(self.task['goal']['data']);times=np.asarray(times,dtype=float)
        rows=[goal.at_time(float(t)) for t in times.flat]
        return tuple(np.asarray([r[i] for r in rows]).reshape(times.shape+(3,)) for i in (0,1))

    def control_reference(self):
        value=super().control_reference();value.update(kind='timed',horizon_semantics='task_time')
        return value

    def ranking_limits(self):
        limits=self.task['evaluator']['parameters']['data']
        return dict(max_position_error=limits['max_error_m'],max_tool_axis_angle_error=limits['angle_tolerance_rad'])

    def control_search_options(self):
        from extensions.reference.contracts import OrientedTrackingGoal
        task=self.task;dt=task['timing']['sample_period_s'];lo,hi=task['sampling']['window_s']
        times=[i*dt for i in range(round(lo/dt),round(hi/dt)+1)];goal=OrientedTrackingGoal.model_validate(task['goal']['data'])
        return dict(tool_axis=dict(times_s=times,reference_m=self.reference_at(times)[0].tolist(),
            target_axes_world=[goal.axis_at_time(t) for t in times],axis_local=list(goal.axis_local),
            position_tolerance_m=task['evaluator']['parameters']['data']['max_error_m'],
            angle_tolerance_rad=task['evaluator']['parameters']['data']['angle_tolerance_rad']))

    def describe(self):
        value=super().describe();value.update(context='Timed position and directed tool-axis tracking with a rigid inertial sensor tool; no contact or complete 3D pose',
            rigid_tool=self.task['goal']['data']['rigid_tool'])
        return value
