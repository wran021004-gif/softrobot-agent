"""Affected native wire, strict parser and historical source regressions only."""
import json
from copy import deepcopy
from tools.investigation_contract import contract, VERSION
from tools.state_io import read
from tests.test_research_v1_capacity import CapacityBindingTests


class NativeInvestigationTests(CapacityBindingTests):
    def setUp(self):
        super().setUp()
        with self.host.store.transaction() as db:
            session=self.host.store.session(self.host.run_id,db)
            # Fixture snapshot only; no live frozen session is rewritten.
            snapshot=deepcopy(session['snapshot'])
            snapshot['input']['policy']['model']['parameters']['investigation_contract']=VERSION
            ref=self.host.store.put(db,snapshot)
            db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,self.host.run_id))

    def test_shared_wire_and_strict_business_parser(self):
        c=contract();_,wire,_,_=self.dispatch.prepare(self.order)
        self.assertEqual(wire['tools'],c.tools())
        args=dict(reference=self.ref,pointer='/scalar')
        decision=c.request('evidence_read',json.dumps(args),0)
        self.assertEqual(decision['tool_id'],'evidence.read')
        self.assertEqual(decision['arguments']['reference'],self.ref)
        for bad in (dict(arguments=args,reason='Wrapped',tool_version='1.0.0'),dict(args,unknown=1),dict(args,offset='0')):
            with self.assertRaises(ValueError):c.request('evidence_read',json.dumps(bad),0)
        c.parse('investigation_return',json.dumps(dict(interpretation='Valid business report')))
        with self.assertRaises(ValueError):c.parse('investigation_return',json.dumps(dict(interpretation='Valid',unexpected=True)))

    def test_saved_historical_invalid_response_stays_invalid(self):
        raw=read('evidence/research_v1_completion_20261008/stages/principal_invalid_response.json')
        with self.assertRaises(ValueError):self.dispatch._decode(raw)
        self.assertEqual(raw['choices'][0]['finish_reason'],'tool_calls')

    def test_public_handoff_preserves_old_state_and_checks_identity(self):
        from tools.research_v1_resume import OLD, ROOT
        from tools.research_single_validation import sha
        from tools.platform_store import Store,plain
        from tools.state_io import digest
        from tools.research_execution import invoke
        from tools.investigation_handoff import HistoricalHandoff,bind
        from types import SimpleNamespace
        m=read(OLD/'validation_manifest.json');old=Store(ROOT/m['phases']['direct']['output'])
        old_hash=sha(old.db);source_run='mainline3-direct-repair1'
        node=old.session(source_run)['state']['investigations']['reach-question']
        with self.host.store.transaction() as db:
            report=plain(self.host.store.put(db,old.artifact(node['result'])))
            validation=plain(self.host.store.put(db,dict(historical_node_identity=digest(node),old_report_valid=True)))
            args=dict(source_directory=m['phases']['direct']['output'],source_run_id=source_run,
                source_project_id=old.config()['project_id'],source_database_sha256=old_hash,
                source_node='reach-question',report=report,historical_validation=validation)
            state=self.host.store.session(self.host.run_id,db)['state'];grant=state['role_context']['investigation_grant']
            grant['historical_handoffs']=[args];state['investigation_grant_identity']=digest(grant)
            self.host.store.update_state(db,self.host.run_id,state)
        ctx=SimpleNamespace(host=self.host,store=self.host.store,run_id=self.host.run_id)
        with self.assertRaisesRegex(ValueError,'NOT_GRANTED'):bind(ctx,HistoricalHandoff.model_validate(dict(args,source_run_id='wrong')))
        result=bind(ctx,HistoricalHandoff.model_validate(args))
        self.assertEqual(plain(result.result),report)
        state=self.host.store.session(self.host.run_id)['state']
        self.assertNotIn('reach-question',state.get('investigations',{}))
        self.assertFalse(state['historical_investigations']['reach-question']['new_investigation_executed'])
        self.assertEqual(sha(old.db),old_hash)
