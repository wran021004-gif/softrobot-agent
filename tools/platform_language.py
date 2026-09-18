"""English presentation of known legacy prose; immutable source records stay intact."""
import re


LEGACY_ENGLISH = {
    '串联多段软臂独立开发验证': 'Independent development validation of a serial multi-segment soft arm',
    '本轮开发任务；固定目标、容差与评分；不覆盖历史任务': 'Development task with fixed target, tolerance and scoring; historical tasks are unchanged',
    '独立开发接口验证，不是正式科研批准': 'Independent development interface validation; not formal research approval',
}


def english_projection(value, pointer=''):
    """Translate known descriptive values, retaining all fields and numerical data.

    Unknown prose requires an explicit local translation rather than silently
    deleting task information or sending mixed-language instructions.
    """
    if isinstance(value, dict):
        return {k: english_projection(v, pointer+'/'+k) for k,v in value.items()}
    if isinstance(value, list):
        return [english_projection(v, pointer+'/'+str(i)) for i,v in enumerate(value)]
    if isinstance(value, str):
        if value in LEGACY_ENGLISH:
            return LEGACY_ENGLISH[value]
        if re.search(r'[\u4e00-\u9fff]', value):
            raise ValueError('ENGLISH_PROJECTION_REQUIRED at '+pointer+': add an equivalent English presentation for the retained source text')
    return value
