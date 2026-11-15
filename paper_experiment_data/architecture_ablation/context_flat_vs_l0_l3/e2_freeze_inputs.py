"""One pre-inference routing/serialization check, without source mutation or inference."""
import json
import os
import random
import sys
from e2_replay import ROOT,DATA,read,write,recall,initial_messages,tools,request_settings

assert not list((ROOT/'sessions').glob('*/request_*.json')), 'Inference has already started.'
assert not (ROOT/'input_preflight.json').exists(), 'Do not refreeze executed inputs.'
corpus=read(ROOT/'corpus.json');l0=read(ROOT/'L0_current_research_packet.json')
cfg=read(ROOT/'replay_configuration.json');cfg['tools']=tools()
cfg['packet_delivery']='Existing Core provider.live_model_class.format_request semantics: append current L0 only to each wire request, not to saved conversation history.'
cfg['archive_adapter']='ResearchRecallQuery pointer /information/<information_id> selects a complete frozen archived record; remaining pointer/fields select within it. Identical read rights in both conditions.'
cfg['guard_scope']='Decision-only archived replay uses the same serialized request ceiling, model and reasoning for both conditions; no live Host or scientific admission is invoked.'
for entry in l0['information_directory']:
    entry['query']['arguments']['pointer']='/information/'+entry['information_id']
    atom=next(x for x in corpus['atoms'] if x['information_id']==entry['information_id'])
    assert recall(corpus,entry['query']['arguments'])['value']==atom['content']
write(ROOT/'L0_current_research_packet.json',l0);write(ROOT/'replay_configuration.json',cfg)
schedule=read(ROOT/'execution_schedule.json');random.SystemRandom().shuffle(schedule)
for i,item in enumerate(schedule,1):item.update(ordinal=i,order_assignment='One unseeded SystemRandom shuffle before any inference; no resampling.')
write(ROOT/'execution_schedule.json',schedule)
previous=ROOT.parent/'reporter_on_off'
sys.path.insert(0,str(previous/'tokenizer_runtime'))
os.environ['TIKTOKEN_CACHE_DIR']=str(previous/'tokenizer_cache')
import tiktoken
enc=tiktoken.get_encoding('o200k_base')
try:registered=tiktoken.encoding_for_model(cfg['provider']['model']).name
except KeyError:registered=None
sizes=[]
for item in schedule:
    messages=initial_messages(cfg,corpus,l0,item['condition'])
    write(ROOT/'sessions'/item['session_id']/'initial_messages.json',messages)
    wire=dict(**request_settings(cfg['provider']),messages=messages,tools=cfg['tools'],tool_choice='auto')
    payload=json.dumps(wire,ensure_ascii=False,separators=(',',':'))
    sizes.append(dict(condition=item['condition'],wire_bytes=len(payload.encode('utf-8')),generic_proxy_full_wire_tokens_estimated=len(enc.encode(payload))))
manifest=read(DATA/'information_manifest.json')
manifest['readability_check']=dict(records_verified=len(corpus['atoms']),method='Every directory query resolves to exactly the same complete frozen content supplied to Flat, before inference.',archive_namespace=cfg['archive_adapter'])
manifest['flat_presentation']='All complete atoms in original order; level and condition flags omitted from the delivered flat metadata, content unchanged.'
write(DATA/'information_manifest.json',manifest)
write(ROOT/'input_preflight.json',dict(no_provider_requests=True,raw_corpus_unchanged=True,all_records_readable=len(corpus['atoms']),initial_sizes=sizes,model_registered_tokenizer=registered,
    proxy_tokenizer='tiktoken 0.12.0 o200k_base; NOT a verified mapping for gpt-5.6-sol. Capacity/component proxy only; Provider usage is primary.',
    packet_owner_source='D:/softrobot-agent-core/tools/research/provider.py:live_model_class.format_request',order=[x['condition'] for x in schedule]))
print(json.dumps(read(ROOT/'input_preflight.json')),flush=True)
