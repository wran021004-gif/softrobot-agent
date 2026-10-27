"""Task-specific views for position plus a directed tool axis; no new task registry."""
from tools.research_tasks import ResearchTaskAdapter
from tools.state_io import digest


class ToolAxisTaskAdapter(ResearchTaskAdapter):
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
        task=self.task;complete={'robot','policy'}<=self.configuration.keys();protocol='offline_position_tool_axis_v1'
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
            position=c['condition_id']=='tool_position';reference=task['goal']['data']['target_m' if position else 'target_axis_world']
            row=dict(constraint_id=c['condition_id'],signal=c['signal'],indices=indices,
                kind='norm_bound' if position else 'unsupported',reference=[reference for _ in indices],provenance=c['provenance'])
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
