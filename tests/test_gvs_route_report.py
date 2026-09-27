"""Route plumbing with frozen historical exports; no dynamics rollout or provider calls."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from schemas.platform import BackendResult,SessionInput
from tools.platform_host import Host
from tools.platform_store import Store
from tools.state_io import read
from extensions.tendon_family.route import create,overview,view,control_profiles
from examples.gvs_nmpc_route_experiment import route_input

SOURCE=Path('runs/stage316_public_profile_20260927')


def saved_run(backend,folder,timeout_s):
    store=Store(SOURCE);run=read(SOURCE/'workflow.json')['run_id']
    receipt=json.loads(store.lookup(run,'simulate')['receipt'])
    folder.mkdir(parents=True,exist_ok=True)
    for event in store.events(run):
        if event['kind']=='simulation' and event['execution_id']==receipt['execution_id']:
            for ref in event['outputs']:
                if ref['media_type']!='application/json':continue
                data=store.artifact(ref)
                if 'files' in data:
                    for file in data['files']:
                        (folder/file['filename']).write_bytes(store.artifact(file['reference'],raw=True))
    return BackendResult.model_validate(store.artifact(receipt['output']))


class RouteReportTests(unittest.TestCase):
    def setup_route(self):
        root=Path('runs/gvs_route_checks')/uuid4().hex
        inp=route_input('route-check',True);host=Host(root,inp['run_id'])
        host.store.create(dict(project_id=uuid4().hex,grant_id=uuid4().hex,
            authorization_source='Synthetic saved-evidence plumbing test',budget=inp['policy']['budget']))
        create(root,inp)
        return host,inp

    def action(self,host,node,action,**kwargs):
        prior=[n['result'] for n in view(host)['route']['nodes'] if n.get('result')][-1:]
        request=dict(request_id=node,tool_id='route.advance',arguments=dict(node_id=node,action=action,
            reason='Saved-evidence fixture',next_step='Inspect',evidence=prior,**kwargs),reason='Fixture')
        receipt=host.invoke(request)
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        return host.store.artifact(host.store.artifact(receipt['output'])['detail']['result']),request,receipt

    def test_owning_report_delivery_and_sealed_recovery(self):
        host,inp=self.setup_route()
        with patch('extensions.tendon_family.backends.MujocoBackend.run',autospec=True,side_effect=saved_run) as backend:
            self.action(host,'built','build',combination='validated_gvs_nmpc')
            backend.assert_not_called()
            result,request,receipt=self.action(host,'executed','run',source_node='built')
            self.assertEqual(backend.call_count,1)
            child=Host(host.store.root,result['run_id'],actor='route-executor')
            report=json.loads(host.store.lookup(child.run_id,'single-profile-report')['receipt'])
            self.assertEqual(report['caller'],'route-executor')
            self.assertEqual(result['profile_report']['reference'],report['output'])
            self.assertEqual(result['profile_report']['execution_id'],result['simulation']['execution_id'])
            self.assertIsNone(host.store.lookup(host.run_id,'single-profile-report'))
            summary=overview(host)['selected_summary']['profile_report_summary']
            self.assertTrue(summary['official_task_success']);self.assertFalse(summary['sampled_settling']['passed'])
            self.assertEqual(summary['converged_updates'],0);self.assertEqual(summary['deadline_misses'],35)
            before=host.store.remaining()['used']
            self.assertEqual(host.invoke(request),receipt)
            self.assertEqual(host.store.remaining()['used'],before)
            repeated,_,_=self.action(host,'repeat','run',source_node='built')
            self.assertEqual(repeated['profile_report'],result['profile_report']);self.assertEqual(backend.call_count,1)
            final,_,_=self.action(host,'finish','finish')
            self.assertEqual(final['profile_report'],result['profile_report'])
            self.assertEqual(overview(host)['route']['final']['profile_report_summary'],summary)

    def test_scope_authorization_and_imported_skill(self):
        host,inp=self.setup_route();parsed=SessionInput.model_validate(inp)
        combinations=view(host)['combinations']
        self.assertTrue(control_profiles(host,parsed,combinations)[0]['report_authorized'])
        changed=parsed.model_copy(deep=True);changed.task.goal.data['target_m'][0]+=.01
        self.assertEqual(control_profiles(host,changed,combinations),[])
        changed=parsed.model_copy(deep=True);changed.policy.tool_bindings.pop('control.profile_report')
        self.assertFalse(control_profiles(host,changed,combinations)[0]['report_authorized'])
        changed.policy.tool_bindings.pop('simulation.run')
        self.assertFalse(control_profiles(host,changed,combinations)[0]['executable'])
        from tools.platform_skills import import_skill_history,applicable
        import_skill_history(host,SOURCE,read(SOURCE/'workflow.json')['run_id'])
        skills=applicable(host,None)
        self.assertEqual(skills[0]['status'],'validated');self.assertIsNone(skills[0]['human_approval'])
        self.assertTrue(skills[0]['scope_assessment']['validation_applies'])
        with host.store.connect(True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM calls').fetchone()[0],0)
        self.assertEqual(host.store.remaining()['used']['backend_solves'],0)


if __name__=='__main__':unittest.main()
