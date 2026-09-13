"""Persist exactly one corrective request for a rejected tool-call count."""
from tools.state_io import read


class ToolCountRecovery:
    def count_corrections(self):
        return self.state.get('tool_call_corrections', {})

    def reject_tool_count(self, row, calls, *, preserve_row=False):
        count = len(calls)
        error = f'TOOL_CALL_COUNT_ERROR: expected 1, observed {count}; dispatched none'
        if not preserve_row:
            row.update(status='failed', error=error, observed_tool_call_count=count)
        correction_for = row.get('correction_for')
        if correction_for is not None:
            record = self.count_corrections()[str(correction_for)]
            record.update(outcome='malformed', correction_observed_count=count, error=error,
                          correction_response_ref=f"model_calls/{row['index']:03d}/response.json")
            self.state.update(status='PAUSED', stop_reason=error+'; the single correction is exhausted')
            return
        records = self.state.setdefault('tool_call_corrections', {})
        if str(row['index']) not in records:
            ref = f"model_calls/{row['index']:03d}/response.json"
            records[str(row['index'])] = dict(rejected_request_index=row['index'],
                decision_sequence=row['decision_sequence'], original_response_ref=ref,
                observed_count=count, proposed_tools=[str(c.get('function', {}).get('name', 'unknown'))[:80] for c in calls[:5]],
                correction_request_index=None, outcome='pending', original_error=error, error=error)
            if (self.root / ref).exists():
                self.register(self.root / ref)

    def correction_for_decision(self):
        return next((r for r in self.count_corrections().values()
                     if r['decision_sequence'] == len(self.state['decisions'])), None)

    def correction_context(self):
        record = self.correction_for_decision()
        if not record or record['outcome'] != 'pending':
            return None
        count = record['observed_count']
        return dict(instruction=f'Your previous response contained {count} tool calls. Return exactly one tool call. If you intend to finish, call stop_design with evidence and a reason.',
                    rejected_request_index=record['rejected_request_index'],
                    original_response_ref=record['original_response_ref'], proposed_tools=record['proposed_tools'],
                    correction_limit=1)

    def settle_correction(self, row):
        if row.get('correction_for') is None:
            return
        record = self.count_corrections()[str(row['correction_for'])]
        if record['outcome'] == 'malformed':
            return
        record.update(outcome='completed' if row['status'] == 'completed' else 'failed',
                      correction_request_index=row['index'],
                      correction_response_ref=f"model_calls/{row['index']:03d}/response.json",
                      feedback_ref=row.get('feedback_ref'), error=row.get('error'))
        if row['status'] != 'completed':
            self.state.update(status='PAUSED', stop_reason='Corrective request failed; its single allowance remains consumed: '+str(row.get('error')))

    def recover_model_responses(self):
        # In particular, discover the reviewed failed 046 without changing its
        # record or repeating either of its proposed tools/API request.
        for row in self.state['model_calls']:
            path = self.root / f"model_calls/{row['index']:03d}/response.json"
            if row['status'] == 'failed' and row.get('error') == 'One tool call per decision required':
                if row['decision_sequence'] == len(self.state['decisions']) and path.exists():
                    calls = read(path)['choices'][0]['message'].get('tool_calls') or []
                    if len(calls) != 1:
                        self.reject_tool_count(row, calls, preserve_row=True)
                continue
            if row['status'] not in ('reserved', 'responded'):
                continue
            was_reserved = row['status'] == 'reserved'
            try:
                if path.exists():
                    self.apply_model_response(row, read(path))
                else:
                    row.update(status='failed', error='Interrupted request remains charged; no response recorded')
            except Exception as exc:
                row.update(status='failed', error=str(exc))
            self.settle_correction(row)
            receipt = next((r for r in self.ledger['entries'] if r['resource'] == 'model_calls' and r['key'] == str(row['index'])), None)
            if receipt:
                if path.exists():
                    if was_reserved:
                        # response.json may precede the state save that accounts
                        # for the wait. Account it once when recovering that gap.
                        elapsed = max(0, path.stat().st_mtime-receipt.get('started_at_epoch_s', path.stat().st_mtime))
                        elapsed = min(elapsed, receipt.get('reserved_wall_s', elapsed))
                        self.ledger['used']['active_wall_s'] += elapsed
                        if self.experiment() and receipt.get('experiment_id') == self.experiment()['experiment_id']:
                            self.experiment()['used']['active_wall_s'] += elapsed
                    receipt['unsettled_wall_s'] = 0
                else:
                    # No timing artifact: keep the conservative reservation;
                    # do not refund unknown activity on each resume.
                    receipt['unsettled_wall_s'] = receipt.get('reserved_wall_s', 0)
                receipt['status'] = 'completed' if row['status'] == 'completed' else 'failed'
        # A correction reservation/link that survived without its row must not
        # become a new permission to send on the next resume.
        for record in self.count_corrections().values():
            if record['outcome'] == 'reserved' and not any(r['index'] == record['correction_request_index'] for r in self.state['model_calls']):
                record.update(outcome='failed', error='Interrupted correction reservation; allowance consumed')
        self.save()
