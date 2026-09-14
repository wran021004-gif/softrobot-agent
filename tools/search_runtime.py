"""Durable search driver: proposal methods consume state, evaluators own solves."""
from tools.state_io import atomic_json,read,digest
from tools.optimization_interfaces import coordinate_proposal


def search(path, space, initial, evaluator, *, max_trials=2, proposal=coordinate_proposal, initial_step=.1):
    from tools.workbench import owner
    path=path.resolve()
    with owner(path.parent, '.search.lock'):
        import inspect
        from tools.artifact_tools import file_hash
        source=inspect.getsourcefile(proposal)
        if not source:raise ValueError('SEARCH_PROPOSAL_SOURCE_REQUIRED')
        identity=digest(dict(variables=space.variables,bounds=space.bounds,logs=sorted(space.logs),initial=initial,
            method=proposal.__module__+':'+proposal.__name__,method_source_sha256=file_hash(source),
            evaluator=evaluator.identity,max_trials=max_trials,initial_step=initial_step))
        if path.exists():
            state=read(path)
            if state['identity']!=identity:raise ValueError('SEARCH_IDENTITY_CHANGED')
        else:
            state=dict(identity=identity,best=space.encode(initial),best_score=None,iteration=0,step=initial_step,
                trials=[],actual_evaluations=0,cycle_improved=False)
        while state['iteration']<max_trials:
            if hasattr(evaluator,'charged_evaluations'):
                state['actual_evaluations']=evaluator.charged_evaluations('search:'+path.stem)
            pending=state.get('pending')
            if pending is None:
                x=state['best'] if not state['trials'] else proposal(state)['x']
                pending=dict(x=x,parameters=space.decode(x),index=state['iteration'])
                state['pending']=pending;atomic_json(path,state)
            # Exceptions retain pending and evaluator reservations. Resume returns
            # saved evaluation or INCOMPLETE, never an unaccounted replay.
            outcome=evaluator.evaluate(pending['parameters'],'search:'+path.stem)
            trial={**pending,**outcome.model_dump(mode='json')}
            state['trials'].append(trial);state['actual_evaluations']+=outcome.actual_evaluations
            if hasattr(evaluator,'charged_evaluations'):
                state['actual_evaluations']=evaluator.charged_evaluations('search:'+path.stem)
            if outcome.status=='VALID' and (state['best_score'] is None or outcome.score<state['best_score']):
                state.update(best=pending['x'],best_score=outcome.score,cycle_improved=True)
            state['iteration']+=1;state.pop('pending')
            if state['iteration']%(2*len(space.variables))==0:
                if not state['cycle_improved']:state['step']/=2
                state['cycle_improved']=False
            atomic_json(path,state)
        return state
