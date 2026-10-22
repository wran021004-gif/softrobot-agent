"""Local capacity estimates for the accounted DeepSeek transport; never sends."""
from functools import lru_cache
import hashlib
from tools.research.config import ROOT

TOKENIZER_PATH=ROOT/'configs/research/provider/deepseek_v4_tokenizer.json'
TOKENIZER_SHA256='89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614'


@lru_cache(maxsize=1)
def official_tokenizer():
    from tokenizers import Tokenizer
    body=TOKENIZER_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest()!=TOKENIZER_SHA256:
        raise ValueError('DEEPSEEK_OFFLINE_TOKENIZER_HASH_MISMATCH')
    return Tokenizer.from_str(body.decode('utf-8'))


def capacity_estimate(content,provider):
    """Keep the byte bound fast path, refining false rejections with pinned data.

    Serialized-request tokenization includes history/reasoning, tools and the L0
    tail. The frozen output reservation and framing headroom remain additional.
    This is an offline estimate, not a Provider-reported prompt-token count.
    """
    context=provider['context_guard']
    reserved=provider['max_tokens']+context['framing_headroom_tokens']
    estimate=dict(method='serialized_utf8_byte_upper_estimate',input_estimate=len(content),
        serialized_bytes=len(content),reserved_output_tokens=provider['max_tokens'],
        framing_headroom_tokens=context['framing_headroom_tokens'],
        context_limit_tokens=context['context_limit_tokens'])
    if len(content)+reserved>context['context_limit_tokens']:
        if provider['adapter']!='deepseek' or provider['model'] not in ('deepseek-flash','deepseek-v4-pro'):
            raise ValueError('R3_CONTEXT_CAPACITY_EXCEEDED_CONSERVATIVE_UTF8_ESTIMATE')
        encoded=official_tokenizer().encode(content.decode('utf-8'),add_special_tokens=False)
        estimate.update(method='pinned_official_deepseek_v4_serialized_token_estimate',
            input_estimate=len(encoded.ids),tokenizer_sha256=TOKENIZER_SHA256)
    if estimate['input_estimate']+reserved>context['context_limit_tokens']:
        raise ValueError('R3_CONTEXT_CAPACITY_EXCEEDED_OFFLINE_TOKEN_ESTIMATE')
    return estimate
