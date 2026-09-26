"""Versioned, fixed-scope control recipe and explicit historical numerical data.

Loading is solve-free. The imported plan is a guess; execution regenerates its
states from measurements and independently validates every delivered plan.
"""
import json
import time
from pathlib import Path
from typing import Literal
import numpy as np
from schemas.common import Contract
from schemas.platform import EvidenceRef, Payload, SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import GVSTrajectoryParameters
from .gvs_basis import resolve_basis

PROFILE_ID = 'gvs_nmpc_free_reach_v1'
ASSET = 'extensions/tendon_family/profiles/gvs_nmpc_free_reach_v1.json'


class ProfileControl(Contract):
    profile_id: Literal['gvs_nmpc_free_reach_v1'] = PROFILE_ID


class ProfileOutput(Contract):
    detail: dict


class ProfileReportRequest(Contract):
    simulation_request_id: str
    evaluation_request_id: str


class ProfileStrategyRequest(Contract):
    skill_ref: str


def load_profile():
    from tools.spec_tools import ROOT
    return json.loads((ROOT / ASSET).read_text(encoding='utf8'))


def execution_scope(value):
    """Facts that bound performance evidence; run IDs and budgets are excluded."""
    inp = SessionInput.model_validate(value)
    return dict(robot=dict(family=inp.robot.family,identity=digest(plain(inp.robot))),
        task=dict(family=inp.task.family,identity=digest(plain(inp.task)),
            environment=digest(plain(inp.task.environment)),goal=digest(plain(inp.task.goal)),
            timing=plain(inp.task.timing),initializer=digest(plain(inp.task.initializer))),backend=plain(inp.policy.backend),
        execution_model=plain(inp.policy.dynamics_model), discretization=plain(inp.policy.discretization),
        controller=plain(inp.policy.controller), seed=inp.seed)


def checked_profile(inp):
    profile = load_profile()
    if execution_scope(inp) != profile['scope']:
        raise ValueError('GVS_PROFILE_SCOPE_MISMATCH: fixed design, task, initialization, execution and timing required')
    numerical = profile['numerical']
    if digest(numerical) != profile['numerical_reference']['artifact_id']:
        raise ValueError('GVS_PROFILE_NUMERICAL_IDENTITY_MISMATCH')
    p = GVSTrajectoryParameters.model_validate(profile['parameters'])
    order = list(resolve_basis(inp.robot.structure.data, p.basis).coordinate_order)
    tendons = [t['id'] for t in inp.robot.structure.data['tendons']]
    if (numerical['coordinate_order'] != order or numerical['tendon_order'] != tendons
            or numerical['units'] != dict(q='rad/m', qdot='rad/(m*s)', tension='N')):
        raise ValueError('GVS_PROFILE_ORDER_OR_UNITS_MISMATCH')
    n, m = len(order), len(tendons)
    point, seed = numerical['nominal'], numerical['warm_guess']
    X, U = np.asarray(seed['states']), np.asarray(seed['tensions'])
    limits = np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']])
    if (len(point['q0']) != n or len(point['u0']) != m
            or X.shape != (p.horizon*p.substeps+1, 2*n) or U.shape != (p.horizon, m)
            or not np.isfinite(X).all() or not np.isfinite(U).all()
            or np.any(U < -1e-6) or np.any(U > limits+1e-6)):
        raise ValueError('GVS_PROFILE_NUMERICAL_DIMENSIONS_OR_BOUNDS')
    return profile


def profile_input(run_id):
    """Public Python configuration entry point; no Store or process cache needed."""
    value = load_profile()['session_input']
    value['run_id'] = run_id
    return SessionInput.model_validate(value).model_dump(mode='json')


def summary(profile=None):
    p = profile or load_profile()
    return {k:p[k] for k in ('profile_id','predictor','execution','initialization_policy',
        'scope_description','limitations','historical_cost','historical_evidence','numerical_reference')}


def describe(ctx, args):
    profile = load_profile()
    numerical = ctx.save_artifact(profile['numerical'], 'historical_numerical_import')
    reference = ctx.save_artifact(profile, 'control_profile')
    return ProfileOutput(detail=dict(**{k:v for k,v in summary(profile).items() if k!='numerical_reference'},
        profile_reference=plain(reference), numerical_reference=plain(numerical),
        controller=profile['session_input']['policy']['controller'],
        applicability='matching' if execution_scope(ctx.input)==profile['scope'] else 'incompatible',
        invocation='Select the declared controller Binding and frozen profile configuration; simulation.run then evaluation.run. Python: profile_input(new_run_id).'))


def prepare_execution(ctx, controller, inp):
    """Budgeted public execution hook. Imports data, never injects a cache."""
    started = time.perf_counter()
    try:
        profile = checked_profile(inp)
        ref = ctx.save_artifact(profile['numerical'], 'historical_numerical_import')
        if plain(ref) != profile['numerical_reference']:
            raise ValueError('GVS_PROFILE_IMPORT_REFERENCE_MISMATCH')
        controller.preparation = dict(status='completed', wall_s=time.perf_counter()-started,
            source=plain(ref), source_kind='explicit_historical_numerical_import',
            warm_guess_is_execution_evidence=False,
            current_state='backend measurement at each control interval',
            previous_input='declared initial nominal tension, then last applied bounded command',
            regeneration='entire warm state trajectory; independently checked in each update')
        ctx.save_artifact(controller.preparation, 'control_preparation')
    except ValueError as exc:
        ctx.save_artifact(dict(status='failed', wall_s=time.perf_counter()-started, reason=str(exc)), 'control_preparation')
        raise


def declare_strategy(ctx, args):
    from tools.platform_skills import library
    from tools.skill_policy import strategy_hash
    skill = library(ctx.host).get(args.skill_ref)
    checked_profile(ctx.input)
    if skill.applicability.execution_scope != execution_scope(ctx.input):
        raise ValueError('STRATEGY_SCOPE_MISMATCH')
    with ctx.store.transaction() as db:
        session = ctx.store.session(ctx.run_id, db)
        if session['state'].get('result_executions'):
            raise ValueError('STRATEGY_MUST_PRECEDE_EXECUTION')
        state = session['state']
        declaration = dict(skill_ref=skill.reference, strategy_sha256=strategy_hash(skill))
        state['control_profile_strategy'] = declaration
        ctx.store.update_state(db, ctx.run_id, state)
    return ProfileOutput(detail=declaration)
