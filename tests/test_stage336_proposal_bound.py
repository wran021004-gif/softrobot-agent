"""Focused Stage 3.36 proposal/import replay; no provider, math, backend or worker work."""
import hashlib
import json
from pathlib import Path
import unittest
from uuid import uuid4

from extensions.tendon_family.candidate_analysis import scientific_configuration, scientific_configuration_identity
from extensions.tendon_family.route import check_run_eligibility, create
from schemas.platform import ModelResponse
from tools.platform_host import Host
from tools.platform_models import DeepSeekAdapter, payload_for, provider_name
from tools.platform_store import Store, plain


SOURCE_ROOT=Path('runs/stage335_math_route_retry_20260930_live')
SOURCE_RUN='gvs-stage335-81350ebec934'
OPTIMIZER={'artifact_id':'9e408e81d706b22246e1d856d122bdcffaa605308ed975cbfa0ade0c563c7245','media_type':'application/json'}
PROPOSAL_ID='math-compliant-4795c8184616'
BUILD_LABEL='mathsel_c1_n0p15_f0p11_s0p95_compliant'
NAMED={
    'linearization':{'artifact_id':'fecccc31a1f81a66e76ed3484e80cf2ecbf74fd27875bb25ea445460ca370cf5','media_type':'application/json'},
    'metrics':{'artifact_id':'c95db3eb25e6286562329cd8a8ad51419347177391f1a2150635beead37a1e9b','media_type':'application/json'},
    'endpoint':{'artifact_id':'bcae2da3662e176688a48f8b94a93d6abbc7e02b78e076ca2c294d1dc96c8085','media_type':'application/json'},
    'screen':{'artifact_id':'73bef851229f297f586e3c9c42e08eaeb02be61e57e356a6aec531f2b50ba890','media_type':'application/json'},
}


def import_tree(sources,destination,roots):
    seen=set()
    def visit(ref):
        key=(ref['artifact_id'],ref.get('media_type','application/json'))
        if key in seen:return
        raw=None
        for source in sources:
            try:raw=source.artifact(dict(artifact_id=key[0],media_type=key[1]),raw=True);break
            except ValueError:pass
        if raw is None:raise ValueError('ESSENTIAL_HISTORICAL_ARTIFACT_MISSING: '+key[0])
        with destination.transaction() as db:
            saved=destination.put(db,raw,key[1])
        if plain(saved)!=dict(artifact_id=key[0],media_type=key[1]):
            raise AssertionError('content identity changed during import')
        seen.add(key)
        if key[1]=='application/json':
            value=json.loads(raw)
            def scan(item):
                if isinstance(item,dict):
                    if set(item)=={'artifact_id','media_type'}:visit(item)
                    else:
                        for child in item.values():scan(child)
                elif isinstance(item,list):
                    for child in item:scan(child)
            scan(value)
    for root in roots:visit(root)
    return seen


class Stage336ProposalBoundTests(unittest.TestCase):
    def setUp(self):
        self.root=Path('runs/stage336_focused_tests')/uuid4().hex
        self.source=Store(SOURCE_ROOT);self.store=Store(self.root)
        budget=dict(tool_calls=20,model_calls=1,backend_solves=1,worker_calls=1,wall_s=300.)
        self.store.create(dict(project_id='stage336-test',grant_id=uuid4().hex,
            authorization_source='Focused offline proposal replay.',budget=budget))
        source_input=json.loads((SOURCE_ROOT/'frozen_input.json').read_text(encoding='utf8'))
        optimizer=self.source.artifact(OPTIMIZER)
        proposal=next(row for row in optimizer['proposals'] if row['candidate_id']==PROPOSAL_ID)
        roots=[OPTIMIZER,proposal['configuration'],*NAMED.values(),source_input['policy']['route']['data']['analysis_protocol'],
            source_input['policy']['route']['data']['endpoint_target']]
        imported=import_tree([self.source,Store('runs/stage333_bounded_recovery_independent_lengths_20260929_114923/live')],self.store,roots)
        db_path=SOURCE_ROOT/'platform.sqlite'
        manifest=dict(kind='historical_math_import_manifest',historical_computation=True,
            source_stage='Stage 3.35',source_run_id=SOURCE_RUN,source_implementation_commit='28488eda598ad669cb5d610e370ff94bfee13e7e',
            source_store=dict(path=str(db_path.resolve()),size=db_path.stat().st_size,
                sha256=hashlib.sha256(db_path.read_bytes()).hexdigest()),
            import_created_by='focused Stage 3.36 fixture',optimizer_tool_version='1.0.0',
            optimizer_result=OPTIMIZER,optimizer_candidate_id=PROPOSAL_ID,
            proposal_configuration=proposal['configuration'],scientific_configuration_identity=scientific_configuration_identity(
                self.source.artifact(proposal['configuration'])),source_build_node='b_mathsel_c1_n0p15_f0p11_s0p95_compliant',
            protocol=optimizer['protocol'],target=optimizer['target'],historical_mathematical_evaluations=16,
            references={name:dict(reference=ref,tool_id={'linearization':'analysis.linearize_candidate',
                'metrics':'analysis.control_metrics','endpoint':'analysis.bounded_endpoint','screen':'design.screen'}[name],
                tool_version='1.0.0') for name,ref in NAMED.items()},
            imported_artifact_count=len(imported),applicability=optimizer['limitations'])
        with self.store.transaction() as db:self.manifest=plain(self.store.put(db,manifest))
        source_input['run_id']='stage336-'+uuid4().hex
        source_input['policy']['budget']=budget;source_input['policy']['timeout_s']=30.
        bindings=source_input['policy']['tool_bindings']
        bindings.update({'design.build_proposal':'1.0.0','analysis.bind_historical_math':'1.0.0'})
        bindings.pop('design.optimize_math',None)
        route=source_input['policy']['route']['data'];route['historical_case']=None
        route['historical_math']=self.manifest;route['math_evaluation_limit']=0;route['max_trials']=1
        create(self.root,source_input);self.host=Host(self.root,source_input['run_id'],actor='model')

    def provider_call(self,turn,tool,arguments):
        payload=payload_for(self.host,DeepSeekAdapter());bindings=self.host.store.session(self.host.run_id)['snapshot']['input']['policy']['tool_bindings']
        advertised=next(row['function'] for row in payload['tools'] if row['function']['name']==provider_name(tool))
        raw=dict(choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
            tool_calls=[dict(id='offline-'+str(turn),type='function',function=dict(name=advertised['name'],arguments=json.dumps(
                dict(arguments=arguments,reason='Offline production-boundary replay.',tool_version=bindings[tool]))))]))])
        decoded=DeepSeekAdapter().decode(ModelResponse(raw=raw),turn,bindings)
        return self.host.invoke(decoded)

    def test_actual_identifier_failure_then_proposal_build_import_report_and_gate(self):
        payload=payload_for(self.host,DeepSeekAdapter())
        names={row['function']['name']:row['function']['description'] for row in payload['tools']}
        self.assertIn(provider_name('design.build_proposal'),names)
        self.assertIn(provider_name('analysis.bind_historical_math'),names)
        wrong=self.provider_call(0,'design.build_proposal',dict(node_id='wrong-build',optimizer_result=OPTIMIZER,
            optimizer_candidate_id=BUILD_LABEL,reason='Replay the Stage 3.35 identifier mistake.',next_step='Use the exact proposal identity.'))
        self.assertEqual(wrong['execution_status'],'failed',wrong)
        self.assertIn("submitted='"+BUILD_LABEL+"'",wrong['error'])
        self.assertIn(PROPOSAL_ID,wrong['error']);self.assertIn('math-stiff-cccc020c6300',wrong['error'])
        built=self.provider_call(1,'design.build_proposal',dict(node_id='proposal-build',optimizer_result=OPTIMIZER,
            optimizer_candidate_id=PROPOSAL_ID,reason='Construct the exact selected Stage 3.35 proposal.',next_step='Bind historical mathematics.'))
        self.assertEqual(built['execution_status'],'completed',built)
        built_result=self.store.artifact(built['output'])['detail'];build=self.store.artifact(built_result['result'])
        proposal=self.source.artifact(build['proposal_configuration'])
        effective=self.store.artifact(build['configuration'])
        self.assertEqual(scientific_configuration(effective),scientific_configuration(proposal))
        self.assertEqual(build['build_candidate_id'],'proposal-build')
        self.assertEqual(build['optimizer_candidate_id'],PROPOSAL_ID)
        bound=self.provider_call(2,'analysis.bind_historical_math',dict(source_node='proposal-build',import_manifest=self.manifest))
        self.assertEqual(bound['execution_status'],'completed',bound)
        wrapper=self.store.artifact(bound['output'])
        self.assertEqual(set(wrapper['references']),set(NAMED))
        self.assertEqual(wrapper['usage']['new_mathematical_evaluations'],0)
        conflict=self.provider_call(3,'route.record_analysis',dict(node_id='conflicting-report',source_node='proposal-build',
            evidence=[built_result['result']],historical_math_binding=bound['output'],selected_optimizer_candidate_id='math-stiff-cccc020c6300',
            validation_disposition='recommended',reason='Deliberate conflict.',next_step='Reject.'))
        self.assertEqual(conflict['execution_status'],'failed',conflict)
        self.assertIn('field=selected_optimizer_candidate_id',conflict['error'])
        self.assertIn('build_stored_original',conflict['error'])
        report=self.provider_call(4,'route.record_analysis',dict(node_id='proposal-report',source_node='proposal-build',
            evidence=[built_result['result']],historical_math_binding=bound['output'],validation_disposition='recommended',
            reason='Reuse the exact candidate-bound historical computations.',next_step='Decide whether to run once.'))
        self.assertEqual(report['execution_status'],'completed',report)
        report_detail=self.store.artifact(report['output'])['detail'];analysis=report_detail['summary']
        self.assertEqual(set(analysis['references']),set(NAMED))
        self.assertTrue(analysis['math_selection_trace']['provenance_inherited_from_build'])
        self.assertTrue(analysis['math_selection_trace']['historical_computation'])
        eligible=check_run_eligibility(self.host,'proposal-build')
        self.assertTrue(eligible['eligible'])
        altered=self.provider_call(5,'route.advance',dict(node_id='altered-build',action='build',combination='candidate_gvs_nmpc',
            changes={'components/near/length_m':.17},variables={},max_trials=1,source_node=None,candidate_id='altered',
            evidence=[report_detail['result']],reason='Deliberately alter the scientific configuration.',next_step='Verify historical binding rejection.',
            design_statement=None,result_statement=None))
        self.assertEqual(altered['execution_status'],'completed',altered)
        altered_binding=self.provider_call(6,'analysis.bind_historical_math',dict(source_node='altered-build',import_manifest=self.manifest))
        self.assertEqual(altered_binding['execution_status'],'failed',altered_binding)
        self.assertIn('HISTORICAL_MATH_ALTERED_SCIENTIFIC_CONFIGURATION_REJECTED',altered_binding['error'])
        used=self.store.remaining(self.host.run_id)['used']
        self.assertEqual(used['model_calls'],0);self.assertEqual(used['backend_solves'],0);self.assertEqual(used['worker_calls'],0)
        self.assertEqual(self.store.session(self.host.run_id)['state']['route']['math_evaluations']['used'],0)


if __name__=='__main__':unittest.main()
