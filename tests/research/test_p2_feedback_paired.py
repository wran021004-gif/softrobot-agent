"""Synthetic ledger tests; no real Provider, physics, T1, or study mutation."""
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from tools.platform_store import Store,zero
from tools.research.state import update
from tests.research import p2_feedback_paired as paired


class PairedAuthorizationTests(unittest.TestCase):
    def setUp(self):
        folder=Path('runs')/('p2-paired-fixture-'+uuid4().hex);self.addCleanup(shutil.rmtree,folder,ignore_errors=True)
        store=Store(folder/'store');budget=dict(model_calls=8,tool_calls=28,backend_solves=1,worker_calls=0,wall_s=None)
        run='p2-fixture';store.create(dict(project_id=run,grant_id=uuid4().hex,purpose='development',
            authorization_source='synthetic',budget=budget,exclusive_resources={'provider_request':1}))
        store.create_session(dict(input=dict(run_id=run,policy=dict(budget=budget))))
        self.h=SimpleNamespace(store=store,run_id=run)
        self.candidate={'artifact_id':'a'*64,'media_type':'application/json'};self.source={'artifact_id':'b'*64,'media_type':'application/json'}
        spec=dict(resolved_identity='fixture',budgets=dict(provider_requests=8,protected_provider_requests=2),
            configuration=dict(policy=dict(budget=budget)),runtime={})
        update(self.h,spec=spec,profile={'science_hashes':{}},freeze='fixture-old-commit',research_status='ready',pending=None,
            pilot={'provider':{},'live_model_requests':6},control_initializations=[dict(candidate=self.candidate,source=self.source,task_acceptance='unmeasured')])
        for i in range(6):
            row,_=store.reserve(run,str(i),'hash','fixture',{**zero(),'model_calls':1},resources=['provider_request'])
            store.complete(row,dict(request_id=str(i),execution_id=row['execution_id'],caller='fixture',tool_id='model.deepseek',tool_version='1.0.0',execution_status='completed',charged=zero()))
        for name,value in [('RUN',run),('BASELINE_ID','fixture'),('CANDIDATE',self.candidate),('SOURCE',self.source)]:
            p=patch.object(paired,name,value);p.start();self.addCleanup(p.stop)
        for name,value in [('clean_commit',lambda:'fixture-commit'),('science_hashes',lambda:{}),
                           ('execution_environment',lambda spec:{'status':'ready'}),('guard',lambda h:None)]:
            p=patch.object(paired,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(paired.core,'bind');p.start();self.addCleanup(p.stop)

    def test_authorization_extends_existing_grant_and_preserves_history(self):
        before=self.h.store.remaining()['used']
        result=paired.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],13)
        self.assertEqual(self.h.store.remaining('p2-fixture')['limit']['model_calls'],13)
        self.assertEqual(self.h.store.remaining()['used'],before)
        current=self.h.store.session('p2-fixture')['state']
        self.assertEqual(current['spec']['budgets']['protected_provider_requests'],4)
        self.assertEqual(self.h.store.artifact(result['addendum'])['original_protected'],2)
        self.assertEqual(self.h.store.artifact(result['addendum'])['previous_ledger']['used'],before)
        with self.assertRaisesRegex(ValueError,'NO_REPEAT'):paired.authorize(self.h)

    def test_pending_source_refuses_before_extension(self):
        update(self.h,pending={'fixture':'uncertain'})
        with self.assertRaisesRegex(ValueError,'SETTLED_SOURCE'):paired.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],8)
