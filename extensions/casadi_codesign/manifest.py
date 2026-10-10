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
        ('math.casadi_codesign_replay',Replay,'replay','Independent Radau forward integration of a returned bounded schedule.'))]
