from schemas.casadi_codesign import Check, Solve, Replay, Feedback
from tools.platform_registry import Extension

CONTRACTS = [('pilot.casadi_codesign_feedback','1.0.0',Feedback)]
EXTENSIONS = [Extension(name,'tool','1.0.0',schema,Feedback,
    'tools.casadi_codesign_service:'+binding,description,
    sources=('tools/casadi_codesign_service.py','tools/casadi_codesign_worker.py',
        'tools/research_casadi_codesign.py','schemas/casadi_codesign.py',
        'extensions/tendon_family/gvs_codesign.py','extensions/tendon_family/gvs_casadi.py',
        'extensions/tendon_family/gvs.py','extensions/tendon_family/gvs_basis.py',
        'extensions/tendon_family/generated_serial.py','extensions/tendon_family/sections.py',
        'extensions/optimization/ipopt.py','extensions/optimization/contracts.py'),
    assets=('examples/casadi_codesign/case_A.json','examples/casadi_codesign/case_B.json'),
    dependencies=('casadi','numpy','scipy'),
    extension_dependencies=(('model.gvs','1.0.0'),('solver.ipopt','1.0.0')),
    capabilities={'category':'analysis','preflight':'tools.casadi_codesign_service:preflight'},
    cache=False,side_effects='numerical solve or integration; retained evidence')
    for name,schema,binding,description in (
        ('math.casadi_codesign_check',Check,'check','Focused symbolic mechanics and constraint derivative verification.'),
        ('math.casadi_codesign_solve',Solve,'solve','Execute frozen fixed or joint length trajectory NLP with IPOPT.'),
        ('math.casadi_codesign_replay',Replay,'replay','Independent BDF forward integration of a returned bounded schedule.'))]

from schemas.casadi_feedback import Empty, Solve as ResearchSolve, Replay as ResearchReplay, ActivityPlan as Plan, Result
EXTENSIONS += [Extension('math.casadi_feedback_'+name,'tool','1.0.0',schema,Result,
    'tools.casadi_feedback_service:'+name,description,
    sources=EXTENSIONS[0].sources + ('tools/casadi_feedback_service.py','tools/casadi_feedback_worker.py',
        'tools/research_casadi_feedback.py','schemas/casadi_feedback.py','tests/test_casadi_feedback.py'),
    assets=EXTENSIONS[0].assets+('examples/casadi_feedback/specification.json',),
    dependencies=('casadi','numpy','scipy'),extension_dependencies=(('model.gvs','1.0.0'),('solver.ipopt','1.0.0')),
    capabilities={'category':'analysis','preflight':'tools.casadi_feedback_service:preflight'},
    cache=False,side_effects='new cumulative research activity; numerical evidence and model decision')
    for name,schema,description in (
        ('diagnose',Empty,'Prescribed corrected-A tight implicit and refined rollout, plus BDF precision check. No search.'),
        ('speed',Empty,'One local automatic-AD experiment; same saved inputs and exact derivatives. No NLP.'),
        ('solve',ResearchSolve,'Execute an accepted model plan candidate with shared task slacks, original acceptance and hard residuals.'),
        ('replay',ResearchReplay,'Independent BDF replay from physical zero; diagnostic schedules permitted.'),
        ('plan',Plan,'Record model hypothesis, evidence, bounded batch or diagnostic choice, or final STOP.'))]
