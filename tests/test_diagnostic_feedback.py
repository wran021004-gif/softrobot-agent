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


class FeedbackTests(TestCase):
    setUp = HandoffTests.setUp
    cleanup_store = HandoffTests.cleanup_store

    def role_host(self, tools, turns=2, batch=None):
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
            payload=payload_for(self.host,ReadableDeepSeekAdapter())
            names=[t['function']['description'].split('@')[0] for t in payload['tools']]
            self.assertEqual(set(names),{'evidence.read',expected})
        host,_=self.role_host({'diagnosis.submit':'1.0.0','diagnosis.check_request':'1.0.0'})
        self.assertIn('diagnosis.submit',delivery_instruction(host));self.assertNotIn('route',delivery_instruction(host))

    def test_check_feedback_revised_report_link_and_counters(self):
        host,request=self.role_host({'diagnosis.submit':'1.0.0','diagnosis.check_request':'1.0.0'})
        source=self.bound.resolve(self.bound.binding['execution_id']);ref=source['files']['controller_observations.json']
        updates=self.store.artifact(ref);index=7
        with self.store.transaction() as db:
            prior=plain(self.store.put(db,dict(report='prior report preserved')))
            state=self.store.session(host.run_id,db)['state'];state['protocol_corrections_used']=2
            state['role_context'].update(previous_report=prior,check_execution_enabled=True)
            self.store.update_state(db,host.run_id,state)
        args=DiagnosticCheckRequest(check_id='selected-7',operation='prediction_braking',update_id=index,diagnosis_request=request,
            hypotheses=['input limitation','model mismatch'],initial_state=dict(reference=ref,pointer='/7/measured_initial_state',value=updates[index]['measured_initial_state']),
            input=dict(reference=ref,pointer='/7/actual_tension_n',value=updates[index]['actual_tension_n']),fixed_conditions=['saved state'],
            model='model.gvs@1.0.0',horizon_s=.01,integration='implicit_euler',metrics=['speed'],work_limits={'wall_s':60},acceptance_criteria=['model only'])
        with self.store.transaction() as db:check=plain(self.store.put(db,args))
        called=[]
        executor=SimpleNamespace(resume=lambda:None,invoke=lambda value:called.append(value) or dict(execution_status='failed',error='offline fixture, no numerical execution',output=None))
        feedback=execute_check_feedback(host,executor,check)
        self.assertEqual(called[0]['arguments']['update_id'],7)
        state=self.store.session(host.run_id)['state'];self.assertEqual(state['protocol_corrections_used'],2)
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


if __name__=='__main__':main()
