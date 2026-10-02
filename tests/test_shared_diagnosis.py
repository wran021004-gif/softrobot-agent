"""Focused new-wire and shared-flow checks; provider and numerical result are fixtures."""
from copy import deepcopy
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch
from schemas.platform import ModelResponse
from schemas.platform_handoff import WorkflowDesignResponse
from tools.diagnostic_native import FlatDiagnosticAdapter, BoundSavedStateAdapter
from tools.diagnostic_workflow import DiagnosticWorkflow, ROOT, PERMISSIONS, PHASES, save
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_models import payload_for, ToolProtocolError
from tools.platform_handoff import respond_workflow
from tools.state_io import atomic_json


def native(name,args):
    return dict(choices=[dict(finish_reason='tool_calls',message=dict(tool_calls=[dict(type='function',
        function=dict(name=name.replace('.','_'),arguments=json.dumps(args)))]))])


class SharedWorkflowTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.cleanup)
    def cleanup(self):gc.collect();self.temp.cleanup()
    def workflow(self,mode='dual_context',suffix='case'):
        w=DiagnosticWorkflow(Path(self.temp.name)/suffix,mode);w.prepare(dict(test_fixture=True));return w

    def test_flat_resolution_rejects_observed_patterns_and_unknown_fields(self):
        w=self.workflow();h=w.host('design')
        report=save(w.store,dict(recommendations=[]))
        configure_role(h,'design','fixture',report=report,native_fixed={'design.respond_diagnosis':dict(report=report)},evidence_turn_limit=0)
        adapter=FlatDiagnosticAdapter();payload=payload_for(h,adapter)
        args=dict(disposition='defer',reasoning='Need a check',next_action='request_check')
        decoded=adapter.decode(ModelResponse(raw=native('design.respond_diagnosis',args)),0,{'design.respond_diagnosis':'2.0.0'},payload['tools'])
        self.assertEqual(decoded['arguments']['report'],report);self.assertEqual(decoded['tool_version'],'2.0.0')
        self.assertNotIn('report',payload['tools'][0]['function']['parameters']['properties'])
        for bad in [dict(choices=[dict(message=dict(content=json.dumps(native('design.respond_diagnosis',args))))]),
                    native('design.respond_diagnosis',dict(arguments=json.dumps(args))),
                    native('design.respond_diagnosis',dict(arguments=args,reason='outer',tool_version='2.0.0')),
                    native('design.respond_diagnosis',{**args,'invented':True})]:
            with self.subTest(bad=bad),self.assertRaises(ToolProtocolError):
                adapter.decode(ModelResponse(raw=bad),0,{'design.respond_diagnosis':'2.0.0'},payload['tools'])

    def test_dispositions_and_finish_contract(self):
        w=self.workflow();h=w.host('design');ref=save(w.store,dict(recommendations=[dict(recommendation_id='p',action='control_parameter')]))
        configure_role(h,'design','fixture',report=ref)
        ctx=SimpleNamespace(store=w.store,run_id=h.run_id,artifact=w.store.artifact)
        for disposition in ('adopt','defer','reject'):
            for action in ('request_check','verify_adopted_change','finish'):
                args=WorkflowDesignResponse(report=ref,disposition=disposition,recommendation_id='p',reasoning='fixture',next_action=action)
                with self.subTest(disposition=disposition,action=action),patch('tools.platform_handoff.transition',return_value='accepted'):
                    if action=='verify_adopted_change' and disposition!='adopt':
                        with self.assertRaisesRegex(ValueError,'EXACT_CONTROL'):respond_workflow(ctx,args)
                    else:self.assertEqual(respond_workflow(ctx,args),'accepted')

    def test_host_binds_exact_state_and_operation_defined_input(self):
        w=self.workflow();h=w.host('diagnostic');w.chain['request']=w.summary
        configure_role(h,'diagnostic','fixture',binding=w.binding,native_store_root=str(w.directory),
            native_fixed=w.fixed('check'),phase_tools=['diagnosis.check_request'])
        adapter=BoundSavedStateAdapter();payload=payload_for(h,adapter)
        self.assertNotIn('native_store_root',payload['messages'][1]['content'])
        schema=payload['tools'][0]['function']['parameters']
        self.assertNotIn('initial_state',schema['properties']);self.assertNotIn('input',schema['properties'])
        reference=w.inventory['entries'][0]['reference'];updates=w.store.artifact(reference)
        business=dict(operation='prediction_braking',update_id=34,hypotheses=['a','b'],
            local_question='Can local endpoint speed decrease?',discriminating_observations=['endpoint speed difference'],unresolved=['closed-loop cause'],
            fixed_conditions=['state'],metrics=['speed'],work_limits=dict(wall_s=60,prediction_evaluations=2),acceptance_criteria=['local only'])
        for operation,index in [('prediction_braking',34),('local_comparison',33)]:
            args={**business,'operation':operation}
            decoded=adapter.decode(ModelResponse(raw=native('diagnosis.check_request',args)),0,{'diagnosis.check_request':'2.0.0'},payload['tools'])
            fixed=decoded['arguments']
            self.assertEqual(fixed['initial_state']['value'],updates[34]['measured_initial_state'])
            self.assertEqual(len(fixed['initial_state']['value']),24)
            self.assertEqual(fixed['input']['value'],updates[index]['actual_tension_n'])
            self.assertEqual(fixed['input']['pointer'],f'/{index}/actual_tension_n')
            self.assertEqual(fixed['model'],'model.gvs@1.0.0');self.assertEqual(fixed['horizon_s'],.01)
        for change in (dict(update_id=35),dict(initial_state={'value':[0]}),dict(input={'value':[8]*6})):
            with self.subTest(change=change),self.assertRaises(ToolProtocolError):
                adapter.decode(ModelResponse(raw=native('diagnosis.check_request',{**business,**change})),0,{'diagnosis.check_request':'2.0.0'},payload['tools'])

    def test_shared_flow_feedback_memory_permissions_inventory_and_accounting(self):
        totals=[]
        for mode in ('single_context','dual_context'):
            for finish in (False,True):
                with self.subTest(mode=mode,finish=finish):
                    w=self.workflow(mode,mode+str(finish));seen=[]
                    inv={e['type']:e for e in w.inventory['entries']}
                    self.assertEqual(inv['one_step_predictions']['record_count'],35)
                    self.assertEqual(inv['applied_tensions']['record_count'],35)
                    self.assertEqual([v['value'] for v in inv['force_limits']['values']],[8.]*6)
                    state_ref=inv['applied_tensions']['reference'];updates=w.store.artifact(state_ref)
                    def respond(adapter,payload,turn):
                        role=json.loads(payload['messages'][1]['content'])['role_context'];phase=role['phase'];seen.append((phase,role,payload))
                        if phase=='request':return native('diagnosis.request',dict(question='Which evidence distinguishes hypotheses?',scope=['saved evidence and bounded check only'],stopping_conditions=['finish or budget']))
                        if phase=='initial' and not role.get('evidence_views'):
                            a=native('diagnosis.inspect_evidence',dict(view='prediction'))
                            a['choices'][0]['message']['tool_calls']+=native('diagnosis.inspect_evidence',dict(view='plans'))['choices'][0]['message']['tool_calls'];return a
                        if phase in ('initial','revision'):
                            feedback=role.get('check_feedback',[])
                            ref=feedback[0]['result'] if feedback else w.summary
                            ptr='/detail/fixture_value' if feedback else '/detail/summary/deadline_misses';value=-.1 if feedback else 35
                            return native('diagnosis.submit',dict(report=dict(subject='control',source=w.binding,facts=[dict(fact_id='observation',statement='Fixture observation',evidence=[ref])],
                                attribution=[dict(cause='hypothesis',status='insufficient_evidence',fact_ids=['observation'],reason='Local fixture weakens broad attribution; full settling remains unresolved.')],
                                limitations=['Projected model, saved state/input and 10 ms horizon only; fixture not science']),
                                fact_selectors={'observation':[dict(reference=ref,pointer=ptr,value=value)]},missing_evidence=[],recommendations=[],check_results=[f['reference'] for f in feedback]))
                        if phase.startswith('response'):return native('design.respond_diagnosis',dict(disposition='defer',reasoning='Unresolved evidence',next_action='finish' if finish or phase=='response_final' else 'request_check'))
                        return native('diagnosis.check_request',dict(operation='prediction_braking',update_id=34,
                            local_question='Can local endpoint speed decrease?',discriminating_observations=['endpoint speed difference'],unresolved=['closed-loop cause'],
                            hypotheses=['local input sensitivity','model mismatch'],fixed_conditions=['state and model'],
                            metrics=['speed'],work_limits=dict(wall_s=60,prediction_evaluations=2),acceptance_criteria=['Local sensitivity only']))
                    def export(status,reason,elapsed):atomic_json(w.directory/'outcome.json',dict(status=status,stop_reason=reason))
                    with patch.object(FlatDiagnosticAdapter,'respond',respond),patch('extensions.tendon_family.diagnostic_math.execute',return_value=dict(detail=dict(fixture_value=-.1,rows=[]))),patch.object(w,'export',export):
                        result=w.run()
                    self.assertEqual(result['status'],'completed',result)
                    self.assertEqual('check' in w.chain,not finish)
                    if not finish:
                        self.assertEqual(w.store.artifact(w.chain['revised_report'])['check_results'],[w.chain['feedback']])
                        self.assertEqual(w.store.artifact(w.chain['final_response'])['report'],w.chain['revised_report'])
                    initial=next(r for p,r,_ in seen if p=='initial')
                    self.assertEqual(bool(initial['working_memory']),mode=='single_context')
                    for phase,role,payload in seen:
                        names={t['function']['name'] for t in payload['tools']}
                        self.assertTrue(names<={n.replace('.','_') for n in PERMISSIONS[phase]})
                        self.assertEqual(role['phase_budget']['limit'],PHASES[phase]['limit'])
                    if not finish:totals.append({k:v for k,v in w.store.remaining()['used'].items() if k!='wall_s'})
        self.assertEqual(totals[0],totals[1])

    def test_inventory_contradictions_and_unlisted_basis(self):
        from schemas.platform_handoff import InventoryGap
        from tools.diagnostic_inventory import validate_gaps
        w=self.workflow()
        def gap(**kw):return InventoryGap(needed='full velocity query',basis='retained q/qdot',**kw)
        with self.assertRaisesRegex(ValueError,'GAP_CONTRADICTS'):
            validate_gaps([gap(inventory_id='source.backend_motion',status='not_retained')],w.inventory)
        validate_gaps([gap(inventory_id='source.backend_motion',status='retained_unavailable'),
            gap(inventory_id='source.historical_full_plans',status='not_retained'),
            gap(source='hardware encoder measurement',status='not_retained')],w.inventory)
        with self.assertRaisesRegex(ValueError,'GAP_SOURCE_REQUIRED'):
            validate_gaps([gap(status='not_retained')],w.inventory)

    def test_recovery_transfers_and_provider_freeze(self):
        from tools.platform_diagnosis_coordinator import transfer_recovery,recovery_status
        w=self.workflow();source=w.host('design');dest=w.host('diagnostic')
        with w.store.transaction() as db:
            state=w.store.session(source.run_id,db)['state']
            state.update(repairs=2,business_failures_total=3,protocol_corrections_used=3,protocol_corrections_consecutive=1)
            w.store.update_state(db,source.run_id,state)
        transfer_recovery(source,dest)
        state=w.store.session(dest.run_id)['state'];config=w.store.session(dest.run_id)['snapshot']['input']['policy']['model']
        status=recovery_status(state,config)
        self.assertEqual(status['business']['remaining_repairs'],0)
        self.assertEqual(status['business']['total_failures'],3)
        self.assertEqual(status['protocol']['total_remaining'],1)
        configure_role(dest,'diagnostic','new phase')
        self.assertEqual(w.store.session(dest.run_id)['state']['repairs'],2)
        w.validate_frozen_configuration()
        w.freeze['host_provider_configurations']['diagnostic']['max_tokens']=1
        with self.assertRaisesRegex(ValueError,'FROZEN_PROVIDER'):w.validate_frozen_configuration()

    def test_accepted_business_rejections_exhaust_only_business_repairs(self):
        from tools.platform_models import run_loop
        w=self.workflow();h=w.host('design');report=save(w.store,dict(recommendations=[]))
        configure_role(h,'design','fixture',report=report,binding=w.binding,native_store_root=str(w.directory),
            native_fixed={'design.respond_diagnosis':dict(report=report)},evidence_turn_limit=0)
        def respond(adapter,payload,turn):
            return native('design.respond_diagnosis',dict(disposition='adopt',recommendation_id='absent',reasoning='fixture',next_action='finish'))
        with patch.object(FlatDiagnosticAdapter,'respond',respond):run_loop(h)
        state=w.store.session(h.run_id)['state']
        self.assertEqual(state['stop_reason'],'BOUNDED_REPAIR_LIMIT')
        self.assertEqual(state['repairs'],3)
        self.assertEqual(state['business_failures_total'],3)
        self.assertEqual(state.get('protocol_corrections_used',0),0)
        self.assertIn('UNKNOWN_RECOMMENDATION',state['business_feedback']['error'])


if __name__=='__main__':main()
