"""Error routing before any paid correction; no transport replay or quota refund."""
from pydantic import ValidationError


def classify(exc, *, stage=None):
    code = str(exc).split(':', 1)[0]
    if code=='INVESTIGATION_REASONING_ONLY_LENGTH':
        category,action='reasoning_only_length','record_response_received_no_formal_decision_then_frozen_conditional_recovery'
    elif code=='INVESTIGATION_RESPONSE_TRUNCATED':
        category,action='truncated_formal_content','retain_original_execute_nothing_partial_then_frozen_conditional_recovery'
    elif code=='INVESTIGATION_NO_NATIVE_TOOL_CALL':
        category,action='model_protocol','retain_explanation_identify_missing_formal_submission'
    elif stage in ('response_evidence_save','response_parse','response_evidence_read') and code not in ('INVESTIGATION_NO_NATIVE_TOOL_CALL','EXACTLY_ONE_NATIVE_TOOL_CALL_REQUIRED'):
        category,action='received_local_failure','recover_safe_saved_material_revalidate_without_retransmission'
    elif code.startswith(('MODEL_NODE_INCOMPLETE','INVESTIGATION_MODEL_CALLS_BUDGET_EXHAUSTED','INVESTIGATION_ELAPSED_LIMIT')):
        category, action = 'bounded_stop', 'save_cumulative_limits_and_stop_dependent_stages'
    elif stage in ('program_expansion', 'report_evidence_save', 'settlement'):
        category, action = 'program_construction', 'local_repair_and_saved_raw_return_revalidation'
    elif stage == 'transport':
        category, action = 'transport_or_unknown', 'reconcile_original_receipt_keep_unknown_reservation'
    elif code.startswith('CONTEXT_SOURCE_NOT_RETRIEVABLE'):
        category, action = 'program_construction', 'import_exact_authorized_archive_reference_locally'
    elif code.startswith(('CONTEXT_', 'INPUT_', 'REQUEST_', 'INVESTIGATION_RETURN_TOO_LARGE', 'INVESTIGATION_RESPONSE_TRUNCATED')):
        category, action = 'capacity', 'inspect_exact_wire_or_saved_model_return_locally'
    elif isinstance(exc, ValidationError) or code.startswith(('RETURN_', 'CHILD_', 'INVESTIGATOR_', 'ONLY_', 'PRINCIPAL_', 'ACCEPT_', 'ADOPTED_', 'DISPOSITION_FACT_BINDING', 'INVESTIGATION_NO_NATIVE_', 'EXACTLY_ONE_NATIVE_')):
        category, action = 'model_protocol', 'precise_feedback_with_same_node_limits'
    elif code.startswith('MATERIAL_'):
        category, action = 'evidence_or_reasoning', 'independent_review_then_bounded_model_correction'
    else:
        category, action = 'program_construction', 'local_repair_and_saved_raw_return_revalidation'
    return dict(version='research.error_routing@1.0.0', category=category, action=action,
                paid_correction_eligible=category in ('model_protocol', 'evidence_or_reasoning'),
                cost_owner='Actual requests remain charged to original stage and node; no refunds. Local repair is engineering time.',
                automatic_transport_retry=False)
