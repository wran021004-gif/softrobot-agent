"""Real batch stages use the existing receipt-backed execution continuation."""
from copy import deepcopy
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import digest
from tools.execution_completion import complete_execution
from extensions.tendon_family.gvs_profile import execution_scope


class LiveBatchExecution:
    mode='live'

    def __init__(self,host):self.host=host

    def candidate_host(self,candidate):
        host=Host(self.host.store.root,candidate['candidate_id'],actor=self.host.actor)
        prepared=self.host.store.artifact(candidate['configuration'])
        inp=deepcopy(prepared['effective']);inp['run_id']=host.run_id
        current=self.host.store.session(self.host.run_id)['snapshot']['input']['policy']
        inp['policy'].update(budget={**current['budget'],'model_calls':0},model=current['model'],route=None,allowed_tools=[],
            tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
            operation_allowances={n:dict(timeout_s=s,reserve_s=s) for n,s in
                [('simulation.run',900.),('evaluation.run',30.),('control.profile_report',60.)]})
        if execution_scope(inp)!=execution_scope(prepared['effective']):raise ValueError('BATCH_EXECUTOR_CHANGED_SCIENCE')
        try:session=host.store.session(host.run_id)
        except ValueError:session=host.create(inp)
        from tools.platform_tasks import compile_input
        if session['snapshot']['input']!=compile_input(inp,host.reg)['input']:raise ValueError('BATCH_EXECUTOR_INPUT_CHANGED')
        return host

    def stage(self,stage,candidate):
        host=self.candidate_host(candidate)
        batch=self.host.store.session(self.host.run_id)['state']['search_batch']
        baseline=self.host.store.artifact(batch['base_configuration'])['effective']
        if stage=='apply':return self.host.store.artifact(candidate['configuration'])
        result=complete_execution(host,baseline,candidate['candidate_id'],stop_after=stage)
        receipt=result.get('receipts',{}).get(stage)
        if receipt is None:
            return dict(execution_status='unknown',error=result.get('reason',result['status']),output=None)
        return receipt

    def facts(self,candidate):
        host=self.candidate_host(candidate)
        batch=self.host.store.session(self.host.run_id)['state']['search_batch']
        baseline=self.host.store.artifact(batch['base_configuration'])['effective']
        result=complete_execution(host,baseline,candidate['candidate_id'])
        if result['status']!='evaluated':raise ValueError('BATCH_COMPLETION_UNRESOLVED')
        expected=self.host.store.artifact(candidate['configuration'])['effective']
        actual=self.host.store.artifact(result['configuration'])['effective']
        if execution_scope(actual)!=execution_scope(expected) or actual['robot']!=expected['robot'] or actual['task']!=expected['task']:
            raise ValueError('BATCH_REAL_RESULT_CONFIGURATION_MISMATCH')
        return result
