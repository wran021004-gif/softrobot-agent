"""Admission tools do not grant simulation or reopen an historical activity."""
from schemas.soromox_pilot import Operation, Solve, Replay, Feedback
from tools.platform_registry import Extension

CONTRACTS = [('pilot.soromox_feedback', '1.0.0', Feedback)]
EXTENSIONS = [
    Extension(name, 'tool', '1.0.0', schema, Feedback,
        'tools.soromox_service:' + binding, description,
        sources=('tools/soromox_service.py', 'tools/soromox_worker.py',
                 'extensions/tendon_family/soromox_mapping.py', 'schemas/soromox_pilot.py'),
        assets=('examples/soromox/case_A.json', 'examples/soromox/case_B.json'),
        capabilities={'category': 'mathematical_admission',
                      'preflight': 'tools.soromox_service:preflight'},
        side_effects='immutable evidence and cumulative accounting')
    for name, schema, binding, description in [
        ('math.soromox_describe', Operation, 'describe',
         'Resolve the frozen robot and inspect actual model-admission evidence'),
        ('math.soromox_solve', Solve, 'solve',
         'Request A/B; report the retained incompatible-model gate without dispatching an NLP'),
        ('math.soromox_replay', Replay, 'replay',
         'Inspect candidate provenance and reject replay when no admitted dynamics exist')]
]
