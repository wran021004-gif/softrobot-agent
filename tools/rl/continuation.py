"""Exact published checkpoint compatibility and new-stage PPO initialization."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path


def config_digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def published_checkpoint(directory, config, generation):
    """Metadata alone is insufficient: require publication, hashes and schedule."""
    from tools.rl.run import read_json
    directory = Path(directory)
    if not generation or Path(generation).name != generation:
        raise ValueError('EXACT_PUBLISHED_GENERATION_REQUIRED')
    pointer = read_json(directory/'checkpoint.json')
    if generation not in (pointer.get('current'), pointer.get('previous')):
        raise ValueError('CHECKPOINT_NOT_PUBLISHED')
    path = directory/'checkpoints'/generation
    metadata = read_json(path/'metadata.json')
    if metadata['config_sha256'] != config_digest(config):
        raise ValueError('SOURCE_CONFIGURATION_MISMATCH')
    if metadata['policy_file_sha256'] != hashlib.sha256((path/'policy.zip').read_bytes()).hexdigest():
        raise ValueError('PARTIAL_OR_CHANGED_CHECKPOINT')
    saved = metadata['inherited']
    horizon = config['budget']['actions']
    if (saved['schedule']['total_timesteps'] != horizon or not 0 <= saved['num_timesteps'] <= horizon or
        not math.isclose(saved['schedule']['progress_remaining'], 1-saved['num_timesteps']/horizon, abs_tol=1e-12)):
        raise ValueError('SOURCE_STAGE_SCHEDULE_MISMATCH')
    return path, metadata


def validate_compatibility(source, selected):
    """Only declared training/reward settings and allocation may change."""
    stable = ('candidate', 'control_object', 'task', 'mode', 'reference', 'observation', 'action', 'seed')
    if any(source[k] != selected[k] for k in stable):
        raise ValueError('CONTINUATION_REQUIRES_IDENTICAL_CANDIDATE_TASK_ACTION_OBSERVATION_NORMALIZATION_REFERENCE')
    allowed = {'learning_rate', 'n_steps', 'batch_size', 'n_epochs', 'ent_coef'}
    if any(source['ppo'][k] != selected['ppo'][k] for k in source['ppo'] if k not in allowed):
        raise ValueError('CONTINUATION_REJECTS_INITIALIZATION_ONLY_OR_UNSUPPORTED_PPO_CHANGES')


def initialize(model_class, env, config, directory):
    """Preserve weights/Adam moments; start the declared schedule at stage progress 1."""
    from tools.rl.run import read_json, write_json, worker_alive
    from tools.rl.train import schedule_setting, snapshot, digest
    lineage = config['lineage']
    parent = Path(lineage['directory'])
    if worker_alive(parent):
        raise ValueError('PARENT_WORKER_MUST_HAVE_EXITED')
    source = read_json(parent/'config.json')
    validate_compatibility(source, config)
    path, metadata = published_checkpoint(parent, source, lineage['checkpoint'])
    if metadata['policy_file_sha256'] != lineage['policy_sha256'] or config_digest(source) != lineage['config_sha256']:
        raise ValueError('PINNED_PARENT_CHANGED')
    model = model_class.load(path/'policy.zip', env=env, device=config['ppo']['device'], force_reset=True)
    before = snapshot(model)
    if before != metadata['inherited']:
        raise ValueError('PARENT_POLICY_OPTIMIZER_COUNTERS_MISMATCH')
    moments_before = digest(model.policy.optimizer.state)
    settings = config['ppo']
    for name in ('n_steps', 'batch_size', 'n_epochs', 'ent_coef'):
        setattr(model, name, settings[name])
    model.learning_rate = schedule_setting(settings['learning_rate'])
    model._setup_lr_schedule()
    for group in model.policy.optimizer.param_groups:
        group['lr'] = float(model.lr_schedule(1.))
    model.rollout_buffer = model.rollout_buffer_class(model.n_steps, model.observation_space,
        model.action_space, device=model.device, gamma=model.gamma, gae_lambda=model.gae_lambda,
        n_envs=model.n_envs, **model.rollout_buffer_kwargs)
    model.runtime_lifetime_offset = before.get('lifetime_timesteps', before['num_timesteps'])
    model.num_timesteps = 0
    model._total_timesteps = config['budget']['actions']
    model._current_progress_remaining = 1.
    model.runtime_config_sha256 = config_digest(config)
    after = snapshot(model)
    record = dict(parent=lineage, source_snapshot=before, stage_initial_snapshot=after,
        policy_preserved=before['policy_sha256'] == after['policy_sha256'],
        optimizer_moments_preserved=moments_before == digest(model.policy.optimizer.state),
        optimizer_steps_preserved=before['optimizer_steps'] == after['optimizer_steps'],
        optimizer_reset=False, stage_schedule=config['ppo']['learning_rate'],
        optimizer_learning_rates=[g['lr'] for g in model.policy.optimizer.param_groups],
        rollout_buffer_size=model.rollout_buffer.buffer_size,
        schedule_semantics='stage-local num_timesteps/progress; lifetime offset and optimizer/epoch counters retained')
    if not record['policy_preserved'] or not record['optimizer_moments_preserved'] or not record['optimizer_steps_preserved']:
        raise RuntimeError('CONTINUATION_DID_NOT_PRESERVE_PARENT_STATE')
    write_json(Path(directory)/'continuation.json', record)
    return model
