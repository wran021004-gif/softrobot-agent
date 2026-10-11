"""Focused admission, ownership and accounting fixtures; no numerical experiments."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from tools import research_core as core
from tools import research_core_mechanics as mechanics


class NumericalTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(dir=core.ROOT/'runs',prefix='nd-fixture-')
        spec=core.read(core.ROOT/'examples/numerical_diagnosis/specification.json')
        spec.update(study_id=Path(self.temp.name).name,started_unix=time.time())
        path=Path(self.temp.name)/'spec.json';core.atomic_json(path,spec)
        self.host=core.prepare(path,Path(self.temp.name)/'s')
        core.update(self.host,freeze='fixture',core_hashes=core.core_hashes())
        self.source=core.save(self.host,dict(operation='solve',candidate=dict(d=spec['reference_parameters']['d'],tensions_n=[[.2]*6]*35),
            owning_study='sealed-original',trajectory_reference={'artifact_id':'a'*64,'media_type':'application/json'}))
        core.update(self.host,imported_mechanics_sources=[self.source])

    def tearDown(self):
        import gc
        gc.collect();self.temp.cleanup()

    def test_zero_model_guard_and_stop_pending_protection(self):
        with patch.object(self.host,'compatibility',return_value={'compatible':True}):
            core.guard(self.host,True)
            core.update(self.host,pending={'known':'fixture'})
            with self.assertRaisesRegex(ValueError,'PENDING'):core.guard(self.host,True)
            core.update(self.host,pending=None,research_status='stopped')
            with self.assertRaisesRegex(ValueError,'STOP'):core.guard(self.host,True)
        self.assertEqual(self.host.store.remaining()['used']['model_calls'],0)

    def test_each_configuration_counts_and_cached_import_keeps_ownership(self):
        def worker(args,**kwargs):
            req=core.read(args[-2]);core.atomic_json(args[-1],dict(status='completed',substeps=req['diagnostic_parameters']['substeps']))
            return SimpleNamespace(stdout=b'',returncode=0)
        with patch.object(core,'guard'),patch.object(mechanics.subprocess,'run',side_effect=worker):
            for substeps in (1,2,4):
                mechanics.dispatch(self.host,'integrate',dict(source=self.source,substeps=substeps),f'config-{substeps}')
        self.assertEqual(core.state(self.host)['bdf_replays'],3)
        self.assertEqual(self.host.store.artifact(self.source)['owning_study'],'sealed-original')
        self.assertEqual(core.state(self.host)['numerical_reserved_s'],0)

    def test_refinement_requires_and_retains_independent_verification(self):
        s=core.state(self.host);core.update(self.host,bdf_replays=6)
        with patch.object(core,'guard'):
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_INTEGRATION'):mechanics.dispatch(self.host,'solve',{},'no-job')
        core.update(self.host,bdf_replays=5,numerical_s=s['spec']['budgets']['numerical_s']-900-core.allowance(s)-449)
        with patch.object(core,'guard'):
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_INTEGRATION'):mechanics.dispatch(self.host,'solve',{},'no-time')
        core.update(self.host,numerical_s=s['numerical_s'])
        def worker(args,**kwargs):
            req=core.read(args[-2])
            value=dict(status='completed')
            if req['operation']=='solve':value['candidate']=dict(d=s['spec']['reference_parameters']['d'],tensions_n=[[.2]*6]*35)
            core.atomic_json(args[-1],value);return SimpleNamespace(stdout=b'',returncode=0)
        with patch.object(core,'guard'),patch.object(mechanics.subprocess,'run',side_effect=worker):
            result=mechanics.dispatch(self.host,'solve',{},'refine')
            self.assertEqual(core.state(self.host)['numerical_reserved_s'],450)
            with self.assertRaisesRegex(ValueError,'RESOURCE_CEILING'):
                mechanics.dispatch(self.host,'integrate',dict(source=self.source),'unrelated')
            mechanics.dispatch(self.host,'integrate',dict(source=result['reference']),'verify-refinement')
        self.assertEqual(core.state(self.host)['bdf_replays'],6)
        self.assertEqual(core.state(self.host)['offline_nlp'],1)
        self.assertIsNone(core.state(self.host)['validation_reservation'])
        self.assertEqual(core.state(self.host)['numerical_reserved_s'],0)

    def test_diagnostic_repetition_reserve_does_not_change_live_defaults(self):
        s=core.state(self.host)
        self.assertEqual(core.capacity(self.host,8)['confirmation_launch_reserve'],1)
        other=deepcopy(s['spec']);other.pop('mode');core.update(self.host,spec=other)
        self.assertEqual(core.capacity(self.host,8)['confirmation_launch_reserve'],2)
