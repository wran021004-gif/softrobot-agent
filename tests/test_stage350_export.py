"""Only the observed post-campaign export closure regression; no live calls."""
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from tools.diagnostic_workflow import ROOT
from tools.improvement_workflow import archive_store
from tools.platform_store import Store
from tools.state_io import read


class ExportTests(TestCase):
    def test_improvement_grant_excludes_builder_material_choices(self):
        from tools.improvement_workflow import ImprovementWorkflow
        from tools.diagnostic_workflow import save
        from tools.diagnostic_improvement import prepare_improvement
        temp=TemporaryDirectory(dir=ROOT/'runs')
        try:
            config=read(ROOT/'examples/stage350_experiment.json')
            config.update(evidence_directory=str(Path(temp.name)/'exports'),baseline_facts={'fixture_only':True})
            workflow=ImprovementWorkflow(Path(temp.name)/'grant','dual_context',experiment=config)
            workflow.prepare(dict(test_fixture=True))
            host=workflow.host('diagnostic')
            report=save(workflow.store,dict(report=dict(source=workflow.binding)))
            with workflow.store.transaction() as db:
                state=workflow.store.session(host.run_id,db)['state']
                state['handoff_history']=[dict(kind='diagnosis_report',reference=report)]
                workflow.store.update_state(db,host.run_id,state)
            binding=workflow.store.artifact(workflow.binding)
            baseline=workflow.store.artifact(binding['configuration'])['effective']
            self.assertIn('stiff',baseline['policy']['candidate_builder']['parameters']['data']['parameters']['design/material_scenario']['options'])
            self.assertNotIn('design/material_scenario',baseline['policy']['editable'])
            before=workflow.store.remaining()['used']
            decision=dict(disposition='adopt',rationale='Offline grant fixture only',expected_measurable_effect='No physical prediction')
            with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED_IN_IMPROVEMENT_GRANT'):
                prepare_improvement(host,report,dict(**decision,changes={'design/material_scenario':'stiff'}))
            allowed=prepare_improvement(host,report,dict(**decision,changes={'components/near/length_m':.162}))
            self.assertEqual(allowed.status,'prepared_no_execution')
            self.assertEqual(workflow.store.artifact(allowed.configuration)['effective']['task'],baseline['task'])
            self.assertEqual(workflow.store.remaining()['used'],before)
        finally:
            gc.collect();temp.cleanup()

    def test_baseline_evaluation_reference_resolves_without_store_mutation(self):
        mode=Store(ROOT/'runs/stage350_physical_pilot_20261003/single_context')
        baseline=Store(ROOT/'runs/stage350_physical_pilot_20261003/baseline')
        ref=read(baseline.root/'outcome.json')['result']['receipts']['evaluation']['output']
        before=[s.remaining()['used'] for s in (mode,baseline)]
        with mode.connect(True) as db:
            self.assertIsNone(db.execute('SELECT id FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone())
        temp=TemporaryDirectory(dir=ROOT/'runs')
        try:
            output=Path(temp.name)/'portable'
            archive_store(mode,output,source_stores=[baseline.root])
            self.assertEqual((output/'artifacts'/(ref['artifact_id']+'.json')).read_bytes(),baseline.artifact(ref,raw=True))
            self.assertEqual(read(output/'artifact_owners.json')[ref['artifact_id']],str(baseline.root))
            self.assertEqual(read(output/'external_references.json'),[])
            self.assertEqual([s.remaining()['used'] for s in (mode,baseline)],before)
            with mode.connect(True) as db:
                self.assertIsNone(db.execute('SELECT id FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone())
        finally:
            gc.collect();temp.cleanup()
