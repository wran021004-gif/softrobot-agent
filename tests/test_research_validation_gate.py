"""Focused gate regression checks; no providers or scientific construction."""
from copy import deepcopy
from unittest import TestCase
from tools.platform_store import zero
from tools.state_io import digest
from tools.research_validation_gate import generate


class SavedGateTests(TestCase):
    def bundle(self, role='investigator', novel=True, matched=True):
        source={'terminal_error_m':0.06,'deadline_misses':35}
        ref={'artifact_id':digest(source),'media_type':'application/json'}
        query=dict(reference=ref,pointer='/deadline_misses' if novel else '/terminal_error_m',offset=0,limit=8,byte_limit=4096)
        def page(pointer):
            return dict(reference=ref,pointer=pointer,query={**query,'pointer':pointer},
                page=dict(kind='content',content=source[pointer[1:]],offset=0,next_offset=None),metadata_only=False)
        first=page('/terminal_error_m');later=page(query['pointer'])
        import json
        response=dict(choices=[dict(message=dict(tool_calls=[dict(function=dict(name='evidence_read',
            arguments=json.dumps(dict(arguments=query if matched else {**query,'pointer':'/other'}))))]))])
        bodies=[first,dict(payload={}),response,later]
        artifacts={digest(x):x for x in bodies}
        artifacts[digest(source)]=source
        events=[dict(sequence=i+1,kind=k,status='completed',request_id='investigation-one',
            outputs=[{'artifact_id':digest(body)}]) for i,(k,body) in enumerate(zip(
                ['investigator_read','investigation_provider_attempt','investigation_provider_response','investigator_read'],bodies))]
        return dict(mode='direct',transport='real_configured_deepseek',events=events,artifacts=artifacts,
            state={'investigations':{'one':dict(order=dict(role=role,evidence=[ref]),status='completed',usage={**zero(),'model_calls':1})}},
            project={'budget':{**zero(),'model_calls':18,'tool_calls':512,'wall_s':2400}},
            calls=[dict(status='completed',charged={**zero(),'model_calls':1})])

    def test_prefetch_repeat_and_principal_reads_never_cover_investigator_followup(self):
        for role,novel in [('investigator',False),('principal',True),('coordinator',True)]:
            result=generate(self.bundle(role,novel))
            self.assertEqual(result['gates']['investigator_selected_followup'],'unverified')
            self.assertFalse(result['passed'])

    def test_novel_original_read_requires_same_node_native_request(self):
        self.assertEqual(generate(self.bundle())['gates']['investigator_selected_followup'],'pass')
        failed=generate(self.bundle(matched=False))
        self.assertEqual(failed['gates']['investigator_selected_followup'],'unverified')
        self.assertTrue(failed['errors'])

    def test_output_deterministic_and_status_alone_insufficient(self):
        bundle=self.bundle();bundle['status']='formal_dispositions_recorded'
        self.assertEqual(generate(bundle),generate(deepcopy(bundle)))
        self.assertFalse(generate(bundle)['passed'])
