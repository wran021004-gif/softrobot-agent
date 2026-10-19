"""Create additive evidence-policy views from sealed results; no computations."""
import json
from tools.research.numerics import archived
from tools.research.candidate_portfolio import historical_records,compatible_schedule
from tools.research.evidence_policy import summarize_evidence,check_inference,hypothesis_catalog
from tools.state_io import read,atomic_json,digest
from tests.research.control_search_pilot import source_hashes


def main():
    before=source_hashes();views=[]
    histories=historical_records();controls=[]
    original={r['source_result']['artifact_id']:r for g in read('evidence/control_search_p0/portfolio.json')['groups'] for r in g['ranked']}
    for row in histories:
        assert row['schedule']['trajectory']==original[row['source_result']['artifact_id']]['schedule']['trajectory']
        cfg=archived(row['source_folder'],row['source_candidate'])['configuration']
        compatible_schedule(row,cfg)
        controls.append(dict(source=row['source_result'],sequence_hash=row['sequence_hash'],
            bound_schedule_identity=row['bound_schedule_identity'],engine_time_and_model_checked=True))
    folder='evidence/sorosim_s59/study'
    for call in read(folder+'/calls.json'):
        receipt=json.loads(call['receipt']) if call['receipt'] else {}
        if receipt.get('tool_id')!='research.candidate_analysis':continue
        ref=receipt['output'];value=archived(folder,ref);identity=digest(value)
        summary=summarize_evidence(value,ref)
        assert digest(value)==identity and not summary['prospective_guarantee']
        assert not check_inference(summary,'whole_horizon_from_instantaneous_braking')['allowed']
        views.append(dict(source_folder=folder,summary=summary))
    p1=read('evidence/control_search_p1/summary.json');seen=set()
    for method in p1['methods']:
        for row in method['candidates']:
            ref=row['reference']
            if ref['artifact_id'] in seen:continue
            seen.add(ref['artifact_id']);value=archived('evidence/control_search_p1/study',ref)
            source=archived('evidence/control_search_p1/study',value['source_reference'])
            summary=summarize_evidence(dict(value,**{k:source['trajectory'][k] for k in ('model_identity','design_identity')}),ref)
            assert summary['claim_kind']=='PHYSICAL_OBSERVATION'
            assert not check_inference(summary,'observed_task_pass')['allowed']
            views.append(dict(source_folder='evidence/control_search_p1/study',summary=summary))
    validation=read('evidence/sorosim_s510/reference_validation.json')
    coarse=archived('evidence/sorosim_s510/study',validation['independent_4'])
    fine=archived('evidence/sorosim_s510/study',validation['independent_32'])
    refined=summarize_evidence(coarse,validation['independent_4'],refinement=fine)
    assert not check_inference(refined,'model_sampled_feasibility')['allowed']
    assert fine['original_task_satisfied'] is False
    assert source_hashes()==before
    atomic_json('evidence/control_search_p2/saved_evidence_views.json',dict(views=views,control_binding_audit=controls,
        refined_reference=refined,refinement_evidence=validation['independent_32'],hypotheses=hypothesis_catalog(),
        scientific_launches=0,provider_requests=0,source_files_unchanged=True,
        note='Additive deterministic views. Existing claims and sealed raw values are unchanged.'))
    print(f'{len(views)} saved evidence views; refinement failure remains uncertified; zero scientific launches')


if __name__=='__main__':main()
