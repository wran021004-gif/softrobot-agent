"""Three synthetic delivery associations; no provider, model build or rollout."""
import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path

spec=importlib.util.spec_from_file_location('stage322_audit',Path('runs/stage322_live_design_20260927/audit_design.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def trial(owner,changed=True,success=True):
    return dict(candidate_id='repeated-label',run_id=owner,execution_id='exec-'+owner,
        configuration={'artifact_id':'config-'+owner},evaluation={'artifact_id':'eval-'+owner},
        simulation={'artifact_id':'sim-'+owner},report={'reference':{'artifact_id':'report-'+owner},
            'owner_run_id':owner,'execution_id':'exec-'+owner},
        identity_checks=dict(provider_selected_build=True,meaningful_length_change=changed),
        design_execution_accepted=changed,
        summary=dict(valid_complete_execution=True,official_task_success=success))


def delivery(t):
    final=dict(run_id=t['run_id'],candidate_id=t['candidate_id'],configuration=t['configuration'],
        simulation=dict(execution_id=t['execution_id'],output=t['simulation']),
        evaluation_ref=t['evaluation'],profile_report=t['report'],explicit_delivery=True,stop_reason='Actual conclusion')
    finish=dict(request_id='finish-request',response={'artifact_id':'raw-response'})
    behavior=dict(actual_provider_response_received=True,context_deliveries=[dict(
        request_id=finish['request_id'],fresh_report=t['report'])])
    _,binding,_=audit.delivery_acceptance([t],final,behavior,None,finish)
    review=dict(binding=binding,correct_use_of_current_evidence=True,findings=['Read actual conclusion and current evidence.'])
    return final,behavior,review,finish


class DeliveryAssociationTests(unittest.TestCase):
    def test_repeated_labels_use_owner_and_execution_and_reject_mixed_refs(self):
        first=trial('first');last=trial('last');args=list(delivery(last))
        accepted,binding,issues=audit.delivery_acceptance([first,last],*args)
        self.assertTrue(accepted['final_delivery_accepted']);self.assertEqual(binding['run_id'],'last');self.assertFalse(issues)
        args[0]['evaluation_ref']=first['evaluation']
        accepted,_,issues=audit.delivery_acceptance([first,last],*args)
        self.assertFalse(accepted['final_delivery_accepted']);self.assertEqual(issues,['DELIVERED_EVIDENCE_MISMATCH'])

    def test_changed_failure_then_unchanged_success_is_not_design_success(self):
        failed=trial('modified',success=False);baseline=trial('baseline',changed=False)
        accepted,_,_=audit.delivery_acceptance([failed,baseline],*delivery(baseline))
        self.assertTrue(accepted['changed_design_execution']);self.assertTrue(accepted['delivered_original_reach'])
        self.assertTrue(accepted['real_call_chain']);self.assertFalse(accepted['final_delivery_accepted'])

    def test_valid_changed_delivery_requires_current_bound_interpretation(self):
        t=trial('changed');args=list(delivery(t))
        accepted,_,_=audit.delivery_acceptance([t],*args)
        self.assertTrue(accepted['final_delivery_accepted'])
        args[2]=deepcopy(args[2]);args[2]['binding']['provider_response']={'artifact_id':'old-response'}
        accepted,_,_=audit.delivery_acceptance([t],*args)
        self.assertFalse(accepted['provider_interpretation_accepted']);self.assertFalse(accepted['final_delivery_accepted'])
        args[2]=True
        accepted,_,_=audit.delivery_acceptance([t],*args)
        self.assertFalse(accepted['provider_interpretation_accepted'])


if __name__=='__main__':unittest.main()
