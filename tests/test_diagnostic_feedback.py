"""Focused protocol/feedback checks; numerical execution is mocked, never an experiment."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from tests.test_diagnostic_handoff import HandoffTests
from schemas.platform import ModelResponse
from schemas.platform_handoff import DiagnosticCheckRequest, DiagnosisSubmission
from tools.platform_models import DeepSeekAdapter, ReadableDeepSeekAdapter, ToolProtocolError, run_loop, payload_for, delivery_instruction
from tools.platform_diagnosis_coordinator import configure_role, bind_diagnostic_grant, execute_check_feedback
from tools.platform_handoff import submit
from tools.platform_host import Host, InvocationContext
from tools.platform_store import plain
from pathlib import Path


class FeedbackTests(TestCase):
    setUp = HandoffTests.setUp
    cleanup_store = HandoffTests.cleanup_store

    def role_host(self, tools, turns=2, batch=None, numerical_scope=False):
        from examples.stage342_diagnostic_cycle import input_for_role
        host=Host(self.temp.name,self.run+'-role')
        inp=input_for_role(self.source['configuration'],host.run_id,tools)
        inp['policy']['budget']=self.budget
        inp['policy']['timeout_s']=5.
        inp['policy']['model'].update(max_turns=turns,timeout_s=600.)
        if batch:inp['policy']['model']['readonly_batch_limit']=batch
        host.create(inp)
        b=self.store.artifact(self.binding)
        request=dict(question='Inspect saved evidence and submit',subject='control',binding=self.binding,
            **{k:b[k] for k in ('candidate_id','execution_id','task_identity','controller_identity','evidence_manifest')},
            permitted_tools=list(tools),scope=['saved evidence'],budget={**self.budget,'wall_s':60.},stopping_conditions=['grant exhausted'])
        if numerical_scope:
            from examples.stage345_diagnostic_feedback import SAVED_STATE_SCOPE,SUBLIMITS
            from tools.platform_store import encode
            request['saved_state_check']=SAVED_STATE_SCOPE
            with self.store.transaction() as db:
                db.execute("INSERT INTO meta VALUES ('diagnostic_work',?)",(encode(dict(limits=SUBLIMITS,used={k:0 for k in SUBLIMITS})),))
        with self.store.transaction() as db:ref=plain(self.store.put(db,request))
        bind_diagnostic_grant(host,ref)
        configure_role(host,'diagnostic','Read evidence',request=ref,binding=self.binding)
        return host,ref

    def response(self, payload, names):
        available={t['function']['description'].split('@')[0]:t['function']['name'] for t in payload['tools']}
        return ModelResponse(raw=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[
            dict(type='function',function=dict(name=available[n],arguments=json.dumps(dict(arguments=dict(reference=self.binding,pointer='/execution_id'),
                reason='Read exact saved identity',tool_version='1.0.0')))) for n in names]))]))

    def test_two_requests_share_effective_reservation_transport_and_budget(self):
        host,_=self.role_host({'evidence.read':'1.0.0'})
        outer=self
        class Replay(ReadableDeepSeekAdapter):
            def respond(adapter,payload,turn):
                row=host.store.lookup(host.run_id,f'model-{turn}')
                reserved=json.loads(row['reserved'])['wall_s']
                outer.assertEqual(reserved,adapter.timeout_s)
                outer.assertLessEqual(reserved,60.)
                if turn:outer.assertLess(reserved,60.)
                context=json.loads(payload['messages'][-1]['content'])
                outer.assertIn('remaining',context['role_budget'])
                outer.assertEqual(context['role_budget']['used']['model_calls'],turn)
                return outer.response(payload,['evidence.read'])
        run_loop(host,Replay())
        self.assertEqual(self.store.remaining()['used']['model_calls'],2,self.store.session(host.run_id)['state'])
        self.assertEqual(self.store.remaining()['used']['tool_calls'],2,self.store.session(host.run_id)['state'])
        self.assertLess(self.store.remaining()['used']['wall_s'],60.)

    def test_batch_executes_all_reads_and_old_decoder_stays_strict(self):
        host,_=self.role_host({'evidence.read':'1.0.0'},turns=1,batch=3)
        outer=self
        class Replay(ReadableDeepSeekAdapter):
            def respond(adapter,payload,turn):return outer.response(payload,['evidence.read','evidence.read'])
        run_loop(host,Replay())
        self.assertEqual(self.store.remaining()['used']['model_calls'],1)
        self.assertEqual(self.store.remaining()['used']['tool_calls'],2,self.store.session(host.run_id)['state'])
        self.assertEqual(len(host.context()['batch_observations']),2)
        adapter=ReadableDeepSeekAdapter();payload=payload_for(host,adapter)
        response=self.response(payload,['evidence.read','evidence.read'])
        with self.assertRaisesRegex(ToolProtocolError,'EXACTLY_ONE'):
            ReadableDeepSeekAdapter().decode(response,0,{'evidence.read':'1.0.0'})
        response.raw['choices'][0]['message']['tool_calls'][1]['function']['name']='diagnosis_submit'
        with self.assertRaises(ToolProtocolError):adapter.decode(response,0,{'evidence.read':'1.0.0','diagnosis.submit':'1.0.0'})

    def test_corrections_and_advertised_delivery_follow_phase(self):
        for role,context,expected in [('design',{},'diagnosis.request'),('design',{'report':self.binding},'design.respond_diagnosis'),
            ('design',{'verification':self.binding},'design.review_verification')]:
            configure_role(self.host,role,'phase',**context)
            self.assertIn(expected,delivery_instruction(self.host));self.assertNotIn('route.advance',delivery_instruction(self.host))
            if expected=='design.respond_diagnosis':
                self.assertIn('defer or reject requires next_action=stop',delivery_instruction(self.host))
                self.assertIn('inside arguments, never at the top level',delivery_instruction(self.host))
            payload=payload_for(self.host,ReadableDeepSeekAdapter())
            if expected=='design.respond_diagnosis':
                self.assertIn('defer or reject requires next_action=stop',payload['messages'][0]['content'])
            names=[t['function']['description'].split('@')[0] for t in payload['tools']]
            self.assertEqual(set(names),{'evidence.read',expected})
        host,_=self.role_host({'diagnosis.submit':'1.0.0','diagnosis.check_request':'1.0.0'})
        self.assertIn('diagnosis.submit',delivery_instruction(host));self.assertNotIn('route',delivery_instruction(host))

    def test_design_read_allowance_preserves_delivery_capacity(self):
        configure_role(self.host,'design','Use the supplied summary and deliver',summary_content={'reach_passed':True},evidence_turn_limit=2)
        with self.store.transaction() as db:
            state=self.store.session(self.run,db)['state'];state['turn']=2
            self.store.update_state(db,self.run,state,'running')
        payload=payload_for(self.host,ReadableDeepSeekAdapter())
        self.assertEqual([t['function']['name'] for t in payload['tools']],['diagnosis_request'])
        h=Host(self.temp.name,self.run,actor='model')
        receipt=h.invoke(dict(request_id='late-read',tool_id='evidence.read',tool_version='1.0.0',arguments={'reference':self.binding},reason='test phase limit'))
        self.assertEqual(receipt['error'],'TOOL_NOT_IN_ACTIVE_ROLE_PHASE')
        self.assertEqual(h.context()['phase_progress']['turns_used'],2)

    def test_phase_counts_successful_batch_once_not_protocol_correction(self):
        from tools.platform_models import phase_tools
        host,request=self.role_host({'evidence.read':'1.0.0','diagnosis.submit':'1.0.0'},turns=2,batch=3)
        configure_role(host,'diagnostic','Inspect then submit',request=request,binding=self.binding,
            phase_tools=['evidence.read','diagnosis.submit'],evidence_turn_limit=1,
            phase_budget=dict(limit=dict(model_calls=2)))
        outer=self
        class Replay(ReadableDeepSeekAdapter):
            def respond(adapter,payload,turn):
                if turn==0:
                    return ModelResponse(raw=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[]))]))
                outer.assertEqual(host.context()['phase_progress']['successful_read_turns'],0)
                return outer.response(payload,['evidence.read','evidence.read'])
        run_loop(host,Replay())
        state=self.store.session(host.run_id)['state']
        self.assertEqual(state['role_context']['successful_read_turns'],1)
        self.assertEqual(state['protocol_corrections_used'],1)
        self.assertEqual(self.store.remaining()['used']['model_calls'],2)
        self.assertEqual(self.store.remaining()['used']['tool_calls'],2)
        self.assertEqual(phase_tools(state),['diagnosis.submit'])
        self.assertNotIn('diagnosis.check_request',delivery_instruction(host))
        host.resume()
        receipt=Host(self.temp.name,host.run_id,actor='model').invoke(dict(request_id='closed-read',tool_id='evidence.read',
            tool_version='1.0.0',arguments={'reference':self.binding},reason='Try closed reading'))
        self.assertEqual(receipt['error'],'TOOL_NOT_IN_ACTIVE_ROLE_PHASE')
        self.assertEqual(self.store.remaining()['used']['tool_calls'],3)

    def test_phase_protects_attempts_tools_time_and_effective_timeout(self):
        from tools.platform_models import effective_config
        from tools.platform_store import zero
        host,request=self.role_host({'evidence.read':'1.0.0'})
        configure_role(host,'diagnostic','bounded',request=request,
            phase_budget=dict(limit=dict(model_calls=1),protect_project=dict(model_calls=1,tool_calls=2,wall_s=20.),
                protect_role=dict(tool_calls=1,wall_s=30.)))
        phase=self.store.phase_remaining(host.run_id)
        self.assertEqual(phase['remaining']['model_calls'],1)
        self.assertEqual(phase['remaining']['tool_calls'],3)
        self.assertEqual(effective_config(host)['timeout_s'],30.)
        for key,value in [('model_calls',2),('tool_calls',4),('wall_s',31.)]:
            with self.assertRaisesRegex(ValueError,'protected downstream'):
                self.store.reserve(host.run_id,'too-'+key,'hash','model-transport',{**zero(),key:value})
        row,_=self.store.reserve(host.run_id,'attempt','hash','model-transport',{**zero(),'model_calls':1,'wall_s':10.})
        self.assertEqual(self.store.phase_remaining(host.run_id)['remaining']['model_calls'],0)
        self.assertEqual(effective_config(host)['timeout_s'],20.)

    def test_check_feedback_revised_report_link_and_counters(self):
        host,request=self.role_host({'diagnosis.submit':'1.0.0','diagnosis.check_request':'1.0.0'},numerical_scope=True)
        source=self.bound.resolve(self.bound.binding['execution_id']);ref=source['files']['controller_observations.json']
        updates=self.store.artifact(ref);index=7
        with self.store.transaction() as db:
            prior=plain(self.store.put(db,dict(report='prior report preserved')))
            state=self.store.session(host.run_id,db)['state'];state['protocol_corrections_used']=2
            state['role_context'].update(previous_report=prior,check_execution_enabled=True,max_checks=1)
            self.store.update_state(db,host.run_id,state)
        args=DiagnosticCheckRequest(check_id='selected-7',operation='prediction_braking',update_id=index,diagnosis_request=request,
            hypotheses=['input limitation','model mismatch'],initial_state=dict(reference=ref,pointer='/7/measured_initial_state',value=updates[index]['measured_initial_state']),
            input=dict(reference=ref,pointer='/7/actual_tension_n',value=updates[index]['actual_tension_n']),fixed_conditions=['saved state'],
            model='model.gvs@1.0.0',horizon_s=.01,integration='implicit_euler',metrics=['speed'],work_limits={'wall_s':60,'prediction_evaluations':2},acceptance_criteria=['model only'])
        with self.store.transaction() as db:check=plain(self.store.put(db,args))
        called=[]
        executor=SimpleNamespace(resume=lambda:None,invoke=lambda value:called.append(value) or dict(execution_status='failed',error='offline fixture, no numerical execution',output=None))
        feedback=execute_check_feedback(host,executor,check)
        self.assertEqual(called[0]['arguments']['update_id'],7)
        state=self.store.session(host.run_id)['state'];self.assertEqual(state['protocol_corrections_used'],2)
        self.assertEqual(state['role_context']['phase_tools'],['diagnosis.submit'])
        self.assertNotIn('diagnosis.check_request',delivery_instruction(host))
        self.assertEqual(state['role_grant']['budget']['wall_s'],60.)
        ctx=SimpleNamespace(store=self.store,run_id=host.run_id,host=SimpleNamespace(actor='model'),artifact=self.store.artifact)
        def save(value,kind):
            with self.store.transaction() as db:return self.store.put(db,value)
        ctx.save_artifact=save
        report=DiagnosisSubmission(request=request,previous_report=prior,report=dict(subject='control',source=self.binding),fact_selectors={},
            missing_evidence=['Numerical check failed'],check_results=[feedback],recommendations=[])
        result=submit(ctx,report)
        self.assertEqual(self.store.artifact(result.reference)['previous_report'],prior)
        self.assertEqual(self.store.artifact(feedback)['check_request'],check)
        with self.assertRaisesRegex(ValueError,'FEEDBACK_REQUIRED'):submit(ctx,report.model_copy(update={'check_results':[]}))
        from tools.platform_diagnosis_coordinator import validate_check
        with self.assertRaisesRegex(ValueError,'CHECK_LIMIT'):validate_check(self.store,state['role_context'],args)
        from schemas.platform_handoff import DesignResponse
        from tools.platform_handoff import respond
        configure_role(self.host,'design','Respond to revised report',report=plain(result.reference),evidence_turn_limit=0)
        ctx.run_id=self.run
        response=respond(ctx,DesignResponse(report=result.reference,disposition='defer',reasoning='Failed check leaves uncertainty',next_action='stop'))
        self.assertEqual(self.store.artifact(response.reference)['report'],plain(result.reference))
        with self.assertRaisesRegex(ValueError,'DESIGN_REPORT_LINK'):
            respond(ctx,DesignResponse(report=prior,disposition='defer',reasoning='Stale report',next_action='stop'))

    def test_initial_report_requires_both_view_categories(self):
        host,request=self.role_host({'diagnosis.submit':'1.0.0'})
        configure_role(host,'diagnostic','initial',request=request,require_initial_views=True)
        ctx=SimpleNamespace(store=self.store,run_id=host.run_id,artifact=self.store.artifact)
        report=DiagnosisSubmission(request=request,report=dict(subject='control',source=self.binding),
            fact_selectors={},missing_evidence=['Missing views'],recommendations=[])
        with self.assertRaisesRegex(ValueError,'REQUIRES_PREDICTION'):submit(ctx,report)

    def test_successful_feedback_requires_exact_numeric_result_citation(self):
        host,request=self.role_host({'diagnosis.submit':'1.0.0'})
        with self.store.transaction() as db:
            prior=plain(self.store.put(db,dict(report='prior')))
            result=plain(self.store.put(db,dict(detail=dict(speed_change_m_s=-.1))))
            feedback=plain(self.store.put(db,dict(result=result)))
        configure_role(host,'diagnostic','Revise from offline numerical fixture',request=request,previous_report=prior,
            check_feedback=[dict(reference=feedback,result=result,receipt=dict(execution_status='completed'))])
        ctx=SimpleNamespace(store=self.store,run_id=host.run_id,host=SimpleNamespace(actor='model'),artifact=self.store.artifact)
        def save(value,kind):
            with self.store.transaction() as db:return self.store.put(db,value)
        ctx.save_artifact=save
        report=dict(request=request,previous_report=prior,report=dict(subject='control',source=self.binding),
            fact_selectors={},missing_evidence=['Offline fixture, no physical inference'],check_results=[feedback],recommendations=[])
        with self.assertRaisesRegex(ValueError,'NUMERICAL_RESULT_SELECTOR'):submit(ctx,DiagnosisSubmission.model_validate(report))
        report['report']['facts']=[dict(fact_id='fixture.speed',statement='Offline model fixture speed change',evidence=[result],
            observed=dict(name='speed_change',value=-.1,units='m/s'))]
        report['fact_selectors']={'fixture.speed':[dict(reference=result,pointer='/detail/speed_change_m_s',value=-.1)]}
        revised=submit(ctx,DiagnosisSubmission.model_validate(report))
        self.assertEqual(self.store.artifact(revised.reference)['check_results'],[feedback])
        report['fact_selectors']['fixture.speed'][0]['value']=-.2
        with self.assertRaisesRegex(ValueError,'VALUE_MISMATCH'):submit(ctx,DiagnosisSubmission.model_validate(report))

    def test_stage345_observed_native_call_and_double_encoding_failures(self):
        from tools.platform_models import call_structure_example
        folder=Path(__file__).resolve().parents[1]/'evidence/stage345_diagnostic_cycle_20261002/artifacts'
        configure_role(self.host,'design','Respond',report=self.binding,evidence_turn_limit=0)
        adapter=ReadableDeepSeekAdapter();payload=payload_for(self.host,adapter)
        self.assertIn('do not print this wrapper as assistant content',payload['messages'][0]['content'])
        self.assertIn('nested arguments value must be an object',delivery_instruction(self.host))
        bindings={'design.respond_diagnosis':'1.0.0'}
        for artifact in ('42230e64d05c2335ac3bd2cbcd0dc3f623e9374898eb9c8a3e05fd1014884a54',
                'b093082aadc07162e2055b8efce92ae36e2e7e9b966c2d2deb1abadcea6b8471',
                '4ef7538ce74603c13a55efb34b393d3593853217e726ce5335096de41d0b3e11'):
            response=ModelResponse.model_validate(json.loads((folder/(artifact+'.json')).read_text(encoding='utf-8')))
            with self.assertRaises(ToolProtocolError):adapter.decode(response,0,bindings,payload['tools'])
        tool=payload['tools'][0];example=call_structure_example(tool)
        envelope=json.loads(example['function']['arguments'])
        self.assertIsInstance(envelope['arguments'],dict)
        envelope['arguments']=dict(report=self.binding,disposition='defer',next_action='stop',reasoning='Offline valid call; no decision fabricated for the live run')
        envelope['reason']='Offline structure regression'
        example['function']['arguments']=json.dumps(envelope)
        response=ModelResponse(raw=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[example]))]))
        decision=adapter.decode(response,0,bindings,payload['tools'])
        self.assertIsInstance(decision['arguments'],dict)
        self.assertEqual(decision['arguments']['disposition'],'defer')

    def test_stage344_fixture_response_combinations_and_continuation(self):
        from schemas.platform_handoff import DesignResponse
        from tools.platform_handoff import respond
        from tools.platform_diagnosis_coordinator import adopted_check_parameter
        fixture=json.loads((Path(__file__).resolve().parents[1]/'evidence/stage344_diagnostic_cycle_20261002/saved_diagnosis_report.json').read_text())
        with self.store.transaction() as db:ref=plain(self.store.put(db,fixture))
        configure_role(self.host,'design','Respond to fixture',report=ref,evidence_turn_limit=0)
        ctx=SimpleNamespace(store=self.store,run_id=self.run,host=SimpleNamespace(actor='model'),artifact=self.store.artifact)
        def save(value,kind):
            with self.store.transaction() as db:return self.store.put(db,value)
        ctx.save_artifact=save
        for disposition in ('adopt','defer','reject'):
            for action in ('stop','bounded_verification'):
                response=DesignResponse(report=ref,disposition=disposition,next_action=action,
                    recommendation_id=fixture['recommendations'][1]['recommendation_id'],reasoning='Offline contract fixture')
                if disposition!='adopt' and action=='bounded_verification':
                    with self.assertRaisesRegex(ValueError,'arguments.disposition=.*arguments.next_action=.*next_action=stop.*complete provider envelope'):
                        respond(ctx,response)
                else:
                    result=respond(ctx,response)
                    self.assertEqual(self.store.artifact(result.reference)['disposition'],disposition)
                    adopted=adopted_check_parameter(self.store,ref,plain(result.reference))
                    if disposition!='adopt' or action=='stop':self.assertIsNone(adopted)
                    else:self.assertEqual(adopted,dict(parameter='terminal_tip_speed_weight',value=.0001))
        with self.assertRaisesRegex(ValueError,'ADOPTION_REQUIRES_NAMED'):
            respond(ctx,DesignResponse(report=ref,disposition='adopt',next_action='stop',reasoning='Missing recommendation'))

    def test_saved_state_request_scope_and_executor_revalidation(self):
        from schemas.platform_handoff import DiagnosisRequest
        from tools.platform_diagnosis_coordinator import validate_check,validate_request_scope
        from examples.stage345_diagnostic_feedback import SAVED_STATE_SCOPE,DIAGNOSTIC
        host,request=self.role_host(DIAGNOSTIC,numerical_scope=True)
        req=DiagnosisRequest.model_validate(self.store.artifact(request))
        validate_request_scope(req,dict(saved_state_check=SAVED_STATE_SCOPE))
        for mutation,error in [({'saved_state_check':None},'SAVED_STATE_SCOPE_REQUIRED'),
                ({'permitted_tools':['diagnosis.submit']},'REQUEST_TOOLS')]:
            with self.assertRaisesRegex(ValueError,error):validate_request_scope(req.model_copy(update=mutation),dict(saved_state_check=SAVED_STATE_SCOPE))
        source=self.bound.resolve(self.bound.binding['execution_id']);ref=source['files']['controller_observations.json'];updates=self.store.artifact(ref)
        args=DiagnosticCheckRequest(check_id='scope-check',operation='prediction_braking',update_id=7,diagnosis_request=request,
            hypotheses=['limited braking','objective mismatch'],initial_state=dict(reference=ref,pointer='/7/measured_initial_state',value=updates[7]['measured_initial_state']),
            input=dict(reference=ref,pointer='/7/actual_tension_n',value=updates[7]['actual_tension_n']),fixed_conditions=['saved state'],
            model='model.gvs@1.0.0',horizon_s=.01,integration='implicit_euler',metrics=['speed'],
            work_limits={'wall_s':60,'prediction_evaluations':2},acceptance_criteria=['model only'])
        role=self.store.session(host.run_id)['state']['role_context']
        self.assertEqual(validate_check(self.store,role,args).update_id,7)
        for mutation,error in [({'horizon_s':.02},'CHECK_OUTSIDE_REQUEST_SCOPE'),
                ({'work_limits':{'wall_s':301,'prediction_evaluations':2}},'CHECK_TIME'),
                ({'work_limits':{'wall_s':60,'prediction_evaluations':25}},'CHECK_NUMERICAL'),
                ({'changed_parameter':'terminal_tip_speed_weight'},'DOES_NOT_CHANGE'),
                ({'diagnosis_request':self.binding},'CHECK_REQUEST_LINK')]:
            with self.assertRaisesRegex(ValueError,error):validate_check(self.store,role,args.model_copy(update=mutation))
        for disposition in ('defer','reject'):
            # No adoption blocks a local pair but never the independent prediction probe.
            independent={**role,'adopted_parameter':None,'design_disposition':disposition}
            self.assertEqual(validate_check(self.store,independent,args).operation,'prediction_braking')
            pair=args.model_copy(update=dict(operation='local_comparison',changed_parameter='terminal_tip_speed_weight',changed_value=.0001,
                input=args.input.model_copy(update=dict(pointer='/6/actual_tension_n',value=updates[6]['actual_tension_n'])),work_limits={'wall_s':60,'local_solves':2}))
            with self.assertRaisesRegex(ValueError,'MATCHED_DESIGN_ADOPTION'):validate_check(self.store,independent,pair)
        # Execution revalidates the immutable request even if selection was saved externally.
        with self.store.transaction() as db:
            historical=plain(self.store.put(db,req.model_copy(update={'saved_state_check':None})))
            state=self.store.session(host.run_id,db)['state'];state['role_context']['request']=historical
            self.store.update_state(db,host.run_id,state)
            check=plain(self.store.put(db,args.model_copy(update={'diagnosis_request':historical})))
        executor=SimpleNamespace(resume=lambda:self.fail('must reject before executor'),invoke=lambda _:self.fail('must not execute'))
        with self.assertRaisesRegex(ValueError,'SAVED_STATE_SCOPE_REQUIRED'):execute_check_feedback(host,executor,check)

    def test_frozen_stage345_allocation_recovers_twice_with_downstream_capacity(self):
        from examples.stage345_diagnostic_feedback import LIMITS,PHASES,DESIGN,DIAGNOSTIC,EXECUTOR,input_for_role
        from tools.platform_store import Store,zero
        from tools.platform_diagnosis_coordinator import transfer_recovery
        from tools.platform_models import call_structure_example,effective_config
        store=Store(Path(self.temp.name)/'allocation');project=self.run+'-allocation'
        store.create(dict(project_id=project,grant_id=project,budget=LIMITS,authorization_source='Offline frozen phase regression'))
        hosts={}
        for name,bindings in [('design',DESIGN),('diagnostic',DIAGNOSTIC),('executor',EXECUTOR)]:
            h=Host(store.root,project+'-'+name);h.create(input_for_role(self.source['configuration'],h.run_id,bindings));hosts[name]=h
        design=hosts['design'];diagnostic=hosts['diagnostic']
        def charge(host,name,models,tools,wall):
            store.reserve(host.run_id,name,name,'offline-fixture',{**zero(),'model_calls':models,'tool_calls':tools,'wall_s':wall})
        configure_role(design,'design','request',phase_budget=PHASES['request'])
        charge(design,'request-capacity',3,7,600.)
        self.assertEqual(store.phase_remaining(design.run_id)['remaining']['model_calls'],0)
        with store.transaction() as db:
            state=store.session(diagnostic.run_id,db)['state']
            state['role_grant']=dict(budget={**LIMITS,'model_calls':10,'tool_calls':18,'wall_s':900.},permitted_tools=list(DIAGNOSTIC))
            store.update_state(db,diagnostic.run_id,state)
            fixture=json.loads((Path(__file__).resolve().parents[1]/'evidence/stage344_diagnostic_cycle_20261002/saved_diagnosis_report.json').read_text())
            report=plain(store.put(db,fixture))
        configure_role(diagnostic,'diagnostic','initial',phase_budget=PHASES['initial'])
        self.assertEqual(store.phase_remaining(diagnostic.run_id)['remaining']['model_calls'],4)
        charge(diagnostic,'initial-capacity',4,8,300.)
        configure_role(design,'design','respond',report=report,evidence_turn_limit=0,phase_budget=PHASES['response_initial'])
        outer=self
        class Replay(ReadableDeepSeekAdapter):
            def respond(adapter,payload,turn):
                outer.assertEqual(adapter.timeout_s,json.loads(store.lookup(design.run_id,f'model-{turn}')['reserved'])['wall_s'])
                tool=payload['tools'][0];example=call_structure_example(tool)
                outer.assertEqual(set(json.loads(example['function']['arguments'])),{'arguments','reason','tool_version'})
                args=dict(report=report,disposition='defer',reasoning='Wait for independent saved-state check',next_action='stop')
                envelope=dict(arguments=args,reason='Offline repair regression',tool_version='1.0.0')
                if turn==0:args['next_action']='bounded_verification'
                elif turn==1:envelope['next_action']=args.pop('next_action')
                else:
                    context=json.loads(payload['messages'][-1]['content'])
                    outer.assertIn('complete',context['protocol_correction']['requirement'])
                    outer.assertIn('inside arguments',payload['messages'][0]['content'])
                return ModelResponse(raw=dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[dict(type='function',function=dict(name=tool['function']['name'],arguments=json.dumps(envelope)))]))]))
        run_loop(design,Replay())
        state=store.session(design.run_id)['state']
        self.assertIn('design_response',state.get('handoffs',{}),state)
        self.assertEqual(store.remaining(design.run_id)['used']['model_calls'],6)
        self.assertEqual(state['protocol_corrections_used'],1)
        transfer_recovery(design,diagnostic)
        configure_role(diagnostic,'diagnostic','select',phase_budget=PHASES['check_revision'])
        self.assertEqual(store.phase_remaining(diagnostic.run_id)['remaining']['model_calls'],3)
        charge(diagnostic,'selection-capacity',3,7,360.)
        configure_role(hosts['executor'],'executor','execute',phase_budget=PHASES['executor_check'])
        charge(hosts['executor'],'check-capacity',0,1,300.)
        with store.transaction() as db:
            state=store.session(diagnostic.run_id,db)['state'];state['role_context']['phase_budget'].update(PHASES['after_feedback'])
            store.update_state(db,diagnostic.run_id,state)
        self.assertEqual(store.phase_remaining(diagnostic.run_id)['remaining']['model_calls'],3)
        charge(diagnostic,'revision-capacity',3,3,240.)
        transfer_recovery(diagnostic,design)
        configure_role(design,'design','final',report=report,phase_budget=PHASES['response_final'])
        self.assertEqual(store.phase_remaining(design.run_id)['remaining']['model_calls'],4)
        self.assertEqual(effective_config(design)['timeout_s'],300.)
        charge(design,'final-capacity',4,4,300.)
        self.assertEqual(store.remaining()['used']['model_calls'],20)
        self.assertEqual(store.remaining(design.run_id)['used']['model_calls'],10)
        self.assertEqual(store.remaining(diagnostic.run_id)['used']['model_calls'],10)
        self.assertEqual(store.session(design.run_id)['state']['protocol_corrections_used'],1)


if __name__=='__main__':main()
