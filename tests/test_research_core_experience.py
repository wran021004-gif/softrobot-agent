from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace
from tools import research_core as core
from tools.research_core_experience import disposition_bindings
from tools.state_io import digest


class ExactExperienceTests(TestCase):
    def setUp(self):
        self.state={'retrievals':[]};self.artifacts={}
        self.host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:self.artifacts[ref['artifact_id']]))
        def save(host,value,kind):
            identity=digest(value);self.artifacts[identity]=value
            return dict(artifact_id=identity,media_type='application/json')
        self.patches=[patch.object(core,'state',return_value=self.state),patch.object(core,'save',side_effect=save),
            patch.object(core,'update',side_effect=lambda host,**values:self.state.update(values))]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in self.patches:p.stop()

    def test_exact_revision_and_legacy_keys(self):
        old=core.experience(self.host,dict(operation='read',key='case'))
        exact=core.experience(self.host,dict(operation='read',entry_id='nmpc-feasibility-case',revision='draft'))
        self.assertEqual(old['results'][0]['content_sha256'],exact['results'][0]['content_sha256'])
        bound=disposition_bindings(self.host,{'nmpc-feasibility-case@draft':'adopted'})[0]
        self.assertEqual(bound['read_receipt'],exact['reference'])
        self.assertEqual(bound['revision'],'draft')
        with self.assertRaisesRegex(ValueError,'ONE_ENTRY'):
            core.experience(self.host,dict(operation='read',entry_id='nmpc-feasibility-case',revision='missing'))

    def test_search_and_supplied_context_cannot_prove_read(self):
        search=core.experience(self.host,dict(key='procedure'))
        for key in (search['reference']['artifact_id'],'nmpc-feasibility-procedure@draft','startup-context'):
            with self.assertRaisesRegex(ValueError,'EXACT_ACTUAL_READ'):
                disposition_bindings(self.host,{key:'adopted'})
        read=core.experience(self.host,dict(operation='read',key='procedure'))
        bound=disposition_bindings(self.host,{read['reference']['artifact_id']:'context_only'})[0]
        self.assertEqual(bound['entry_id'],'nmpc-feasibility-procedure')

    def test_read_requires_unambiguous_entry(self):
        with self.assertRaisesRegex(ValueError,'ONE_ENTRY'):
            core.experience(self.host,dict(operation='read'))
