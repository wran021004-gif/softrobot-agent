"""Recover comparison conditions from immutable candidate/result evidence, never filenames."""
from tools.platform_store import Store, plain
from tools.state_io import digest
from schemas.platform import SessionInput
from .execution import resolve_execution


def comparison_basis(root,record):
    from tools.platform_registry import registry
    store=Store(root); receipt=record['receipts']['simulation']
    state=store.session(record['run_id'])['state']
    metadata=state['result_executions'][receipt['execution_id']]
    if metadata['artifact_id']!=receipt['output']['artifact_id']: raise ValueError('RESULT_IDENTITY_MISMATCH')
    candidate=store.artifact(metadata['candidate_input'])
    inp=SessionInput.model_validate(candidate['effective'])
    result=store.artifact(receipt['output'])
    execution=result['data']['data'].get('execution_plan')
    if execution is None:
        # These exact legacy bindings implement the registered fixed equations.
        if (inp.policy.backend.extension_id,inp.policy.backend.version,result['model_id']) not in (
            ('backend.matlab_spatial','1.0.0','matlab_serial_bending_v1'),
            ('backend.family_mujoco','1.0.0','mujoco_serial_bending_v1')):
            raise ValueError('LEGACY_MODEL_EVIDENCE_INSUFFICIENT')
        execution=resolve_execution(inp,registry())
    from .contracts import Control
    from .compiler import normalize_inputs
    design,mesh,_=normalize_inputs(inp.robot.structure.data,inp.policy.discretization.data if inp.policy.discretization else None)
    return dict(task=digest(plain(inp.task)),seed=inp.seed,design=digest(plain(design)),
        discretization=digest(plain(mesh)),control=digest(plain(Control.model_validate(inp.policy.controller.parameters.data))),
        model=execution['dynamics_model_identity'])


def comparable(root,records):
    try:
        bases=[comparison_basis(root,r) for r in records]
    except (ValueError,KeyError,OSError) as exc:
        return dict(comparable=False,reason='COMPARISON_EVIDENCE_INSUFFICIENT: '+str(exc))
    different=[key for key in bases[0] if bases[0][key]!=bases[1][key]]
    return dict(comparable=not different,reason='CONDITIONS_MISMATCH: '+','.join(different) if different else None,bases=bases)
