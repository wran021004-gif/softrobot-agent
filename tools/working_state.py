"""One snapshot of authoritative records; no mutation, reads, aliases or charges."""
import json
from contextlib import closing
from schemas.working_state import WorkingState, ProductState, ActionState
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.platform_models import phase_tools, provider_name_map
from tools.platform_diagnosis_coordinator import recovery_status
from tools.acceptance_definitions import resolve_acceptance, feedback_acceptance
from tools.parameter_impacts import parameter_impacts
from tools.platform_registry import registry


def project_working_state(store, run_id):
    with closing(store.connect(readonly=True)) as db:
        db.execute('BEGIN')
        session=store.session(run_id,db);state=session['state'];snapshot=session['snapshot'];inp=snapshot['input']
        role=state.get('role_context',{});feedback=role.get('improvement_feedback_content')
        feedback_ref=None
        # Accepted business products are public workflow outputs. Never read a
        # sibling's catalog, drafts, reading history or private role context.
        products=[]
        for row in db.execute("SELECT body FROM events WHERE run_id IN (SELECT run_id FROM sessions) ORDER BY seq"):
            event=json.loads(row[0])
            if event['kind']=='role_transition':
                products.extend((event['status'],ref) for ref in event['outputs'])
        reports=[ref for kind,ref in products if kind=='diagnosis_report']
        initial=reports[0] if reports else None
        revision=next((ref for ref in reversed(reports) if store.artifact(ref,db=db).get('previous_report')),None)
        if revision:
            initial=store.artifact(revision,db=db)['previous_report']
        decisions=[ref for kind,ref in products if kind=='design_response']
        final_ref=next((ref for ref in reversed(decisions) if 'candidate_disposition' in store.artifact(ref,db=db)),None)
        final=store.artifact(final_ref,db=db) if final_ref else None
        if final:
            feedback_ref=final.get('feedback')
        if feedback_ref is None:
            for entry in reversed(state.get('read_ledger',[])):
                if entry.get('method')=='explicit_handoff' and entry.get('view')=='campaign_comparison':
                    feedback_ref=entry['result'];break
        if feedback is None and feedback_ref:
            feedback=store.artifact(feedback_ref,db=db)
        feedback=feedback or {}
        baseline=feedback.get('baseline_facts',{}).get('candidate') or role.get('identities')
        result=feedback.get('execution') or {}
        latest=result.get('factual_result',{}).get('candidate')
        preparation_ref=feedback.get('preparation')
        prepared=store.artifact(preparation_ref,db=db) if preparation_ref else role.get('preparation_content')
        # Before feedback exists, expose only preparation produced in this
        # context, and completion in this executor. No guessed execution.
        if prepared is None:
            for row in db.execute('SELECT body FROM events WHERE run_id=? ORDER BY seq DESC',(run_id,)):
                event=json.loads(row[0])
                if event['kind']=='improvement_preparation' and event['status']=='prepared_no_execution':
                    prepared=store.artifact(event['outputs'][-1],db=db);preparation_ref=event['outputs'][-1];break
        completion=state.get('execution_completion',{})
        if latest is None:
            stage=completion.get('stages',{}).get('simulation')
            if stage:
                latest=dict(candidate_id=stage['candidate_id'],configuration=stage['configuration'],
                            execution_id=stage['source_execution_id'],owner_run_id=stage['source_owner'])
        config_ref=(latest or baseline or {}).get('configuration')
        configuration=store.artifact(config_ref,db=db) if config_ref else inp
        effective=configuration.get('effective',configuration)
        from extensions.tendon_family.gvs_profile import execution_scope
        scope=execution_scope(effective) if effective['policy'].get('dynamics_model') else None
        profile_ref=result.get('receipts',{}).get('profile',{}).get('output')
        if profile_ref is None and completion.get('stages',{}).get('profile'):
            profile_ref=completion['stages']['profile']['receipt']['output']
        acceptance=(feedback_acceptance(store,feedback,db=db) if feedback else None) or resolve_acceptance(
            configuration,config_ref,profile=store.artifact(profile_ref,db=db) if profile_ref else None,profile_reference=profile_ref)
        stages=result.get('completion_stages') or completion.get('stages',{})
        stage_view={k:dict(status=v['status'],operation=v['operation'],source_execution_id=v['source_execution_id'],
                         configuration=v['configuration'],output=v['receipt'].get('output')) for k,v in stages.items()}
        unresolved=[]
        for key,stage in stages.items():
            row=db.execute('SELECT request_id,execution_id,status,reserved,receipt FROM calls WHERE execution_id=?',
                (stage['receipt']['execution_id'],)).fetchone()
            if row and not row['receipt']:
                stage_view[key]['status']='unresolved'
                unresolved.append(dict(request_id=row['request_id'],execution_id=row['execution_id'],
                    status='unresolved',ledger_status=row['status'],reserved=json.loads(row['reserved'])))
        for row in db.execute("SELECT request_id,execution_id,status,reserved,receipt FROM calls WHERE run_id=? ORDER BY rowid",(run_id,)):
            if not row['receipt'] and not any(u['execution_id']==row['execution_id'] for u in unresolved):
                unresolved.append(dict(request_id=row['request_id'],execution_id=row['execution_id'],
                    status='unresolved',ledger_status=row['status'],reserved=json.loads(row['reserved'])))
        spendable=store.spendable(run_id,db)
        active=phase_tools(state);bindings=inp['policy']['tool_bindings'];grant=state.get('role_grant')
        reg=registry();actions=[]
        relevant=set(bindings)|{'simulation.run','evaluation.run','control.profile_report','diagnosis.saved_state_check'}
        scheme='readable_v1' if inp['policy']['model'].get('adapter_version') in ('3.0.0','4.0.0','5.0.0') else 'legacy_hashed_v1'
        native_names=provider_name_map(bindings,scheme)
        for name in sorted(relevant):
            version=bindings.get(name);reasons=[]
            try:
                definition=reg.get(name,version or '1.0.0','tool')
                installed=True
                if version:
                    discovery=reg.inspect(definition,bindings)
                    if not discovery['executable']:reasons+=discovery['reasons']
            except ValueError:
                installed=False;reasons.append('capability_unavailable: registered implementation absent')
            if not version:reasons.append('execution_unauthorized: no frozen tool binding')
            if active is not None and name not in active:reasons.append('execution_unauthorized: outside active phase/read allowance')
            if grant and name not in grant['permitted_tools']:reasons.append('execution_unauthorized: outside role request grant')
            if session['status']!='running':reasons.append('session_not_running: explicit validated host resume required')
            if final_ref:reasons.append('workflow_delivered: no further work item authorized')
            if state.get('pending') or unresolved:reasons.append('unresolved_operation: host reconciliation/continuation required; no automatic replay')
            if spendable['remaining']['tool_calls']<1:reasons.append('budget_exhausted: tool_calls')
            allowance=inp['policy'].get('operation_allowances',{}).get(name)
            if allowance and allowance['reserve_s']>spendable['remaining']['wall_s']+1e-9:
                reasons.append('budget_exhausted: operation reservation exceeds spendable wall time')
            if spendable['remaining']['wall_s']<=0:reasons.append('budget_exhausted: wall_s')
            if name=='simulation.run' and spendable['remaining']['backend_solves']<1:
                reasons.append('budget_exhausted: backend_solves (fresh execution)')
            if name=='diagnosis.saved_state_check':
                request=role.get('request_content',{})
                if not request.get('saved_state_check'):reasons.append('execution_unauthorized: no saved-state numerical request scope')
            actions.append(ActionState(tool=name,native_function=native_names.get(name),version=version,installed=installed,permitted=not reasons,reasons=reasons))
        interface=state.get('reference_interface')
        catalog=state.get('fact_catalog',{})
        references={row['selector']['reference']['artifact_id']:row['selector']['reference'] for row in catalog.values()}
        facts=(result.get('factual_result') or {})
        evaluation_ref=(stage_view.get('evaluation') or {}).get('output')
        evaluation=store.artifact(evaluation_ref,db=db) if evaluation_ref else {}
        prepared_configuration=store.artifact(prepared['configuration'],db=db) if prepared and prepared.get('configuration') else None
        linked=(execution_scope(prepared_configuration.get('effective',prepared_configuration))==scope
                if prepared_configuration and latest and scope else None)
        proposed_ref=next((ref for kind,ref in reversed(products) if kind=='improvement_decision'),None)
        proposed=store.artifact(proposed_ref,db=db).get('decision') if proposed_ref else None
        plan=inp['policy'].get('search')
        work_row=db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()
        return WorkingState(run_id=run_id,
            task=dict(identity=role.get('identities',{}).get('task_identity') or (scope or {}).get('task',{}).get('identity'),
                task_id=effective['task']['task_id'],family=effective['task']['family'],configuration=config_ref,
                execution_model=effective['policy'].get('dynamics_model'),
                evaluator=effective['task']['evaluator'],acceptance_contract='platform.acceptance_definition@1.0.0'),
            workflow=dict(session_status=session['status'],role=role.get('role'),phase=role.get('phase'),
                computation_complete=all(stage_view.get(k,{}).get('status')=='completed' for k in ('simulation','evaluation','profile')),
                delivery_complete=final_ref is not None,execution_validity=facts.get('evaluation_validity',evaluation.get('validity')),
                physical_acceptance=dict(terminal=facts.get('task_accepted',evaluation.get('task_success')),joint=feedback.get('campaign_comparison',{}).get('candidate',{}).get('joint_reach_holding_passed'))),
            baseline=baseline,proposed=dict(reference=proposed_ref,decision=proposed) if proposed_ref else None,
            prepared=dict(reference=preparation_ref,candidate_id=prepared.get('candidate_id'),configuration=prepared.get('configuration'),
                status=prepared.get('status'),actual_diff=prepared.get('actual_diff'),
                executed_configuration=(latest or {}).get('configuration'),
                execution_link=result.get('preparation_configuration'),scientific_scope_matches_execution=linked) if prepared else None,
            latest_tested=latest,selection=dict(recorded=final is not None,selected_candidate=final.get('selected_candidate') if final else None,
                candidate_disposition=final.get('candidate_disposition') if final else None,
                recommendation_disposition=final.get('disposition') if final else None),
            products=ProductState(initial_report=initial,accepted_revision=revision,feedback=feedback_ref,final_decision=final_ref,
                unaccepted_draft=dict(status='unaccepted',tool=state['unaccepted_draft']['tool'],phase=state['unaccepted_draft']['phase']) if state.get('unaccepted_draft') else None),
            operations=dict(pending=state.get('pending'),unresolved=unresolved,completed_stages=stage_view),
            evidence=dict(context_id=run_id,scope=state.get('fact_scope'),permitted_references=list(references.values()),
                catalog_location='Current context fact_catalog/reference_view; exact selectors remain in the host.',
                catalog_count=len(catalog),alias_count=len((interface or {}).get('aliases',{})),
                compatibility='existing_alias_table' if interface else ('legacy_long_handles' if catalog else 'no_catalog'),
                interface_version=(interface or {}).get('version'),
                availability='not_read: retained inventory not queried; not_displayed: retained facts outside current page; not_retained: absent evidence; capability_unavailable and execution_unauthorized are separate action reasons'),
            budgets=dict(project=store.remaining(None,db),role=store.remaining(run_id,db),role_grant=grant,
                phase=store.phase_remaining(run_id,db),spendable=spendable,
                numerical=json.loads(work_row[0]) if work_row else None),
            recovery=recovery_status(state,inp['policy']['model']),actions=actions,acceptance=acceptance,
            parameter_impacts=parameter_impacts(effective,reference=config_ref),
            experiment_plan=dict(source='snapshot.input.policy.search',plan=plan) if plan else None)
