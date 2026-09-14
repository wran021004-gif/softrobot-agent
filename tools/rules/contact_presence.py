"""Minimal new rule over an existing count signal; no force/causal inference."""
import math


def evaluate(query, metadata):
    events=[]
    for sample in query['samples']:
        value=sample['value']
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or value!=int(value):
            raise ValueError('INVALID_CONTACT_COUNT')
        if value>0:
            events.append(dict(entity='contact',sample_index=sample['sample_index'],time_s=sample['time_s'],
                observation=dict(contact_count=value,units='1'),judgment='CONTACT_PRESENT_AT_SAVED_SAMPLE',
                causal_hypotheses=[],evidence_ref=query['evidence_ref'],time_phase=query['specification']['phase']))
    return events
