"""Synthetic metadata-only queue tests: no genome reads, runtime or process launch."""
from pathlib import Path
import tempfile, unittest
import checkm2_bulk_queue_control_v001 as q

R = Path(__file__).resolve().parents[1]


def member(name, order, state, supported=True, **values):
    return {'queue_id': name, 'accession': name, 'frozen_order': order, 'qc_execution_state': state,
            'source_supported_scope': supported, 'source_holds_preserved': [],
            'source_pending': ['QC_NOT_RUN'], 'source_masks': {'contamination': None},
            'method_estimate_hashes_verified': state == 'ACCEPTED_METHOD_REUSE_VERIFIED', **values}


class Cases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=R / 'work', prefix='queue_control_fixture_')
        self.root = Path(self.temp.name).resolve(); self.assertTrue(self.root.is_relative_to(R / 'work'))
        self.rows = [member('fresh1.1', 0, 'READY_FRESH_QC'),
                     member('reserved.1', 1, 'RESERVED_P20_UNSTARTED', reserved_P20_order=1),
                     member('accepted.1', 2, 'ACCEPTED_METHOD_REUSE_VERIFIED'),
                     member('saved.1', 3, 'SAVED_VALIDATION_PENDING_NO_UPSTREAM_REPLAY', reserved_P20_order=0),
                     member('held.1', 4, 'READY_FRESH_QC', False, source_holds_preserved=['TYPE_UNKNOWN']),
                     member('fresh2.1', 5, 'READY_FRESH_QC'), member('fresh3.1', 6, 'READY_FRESH_QC')]
        queue = {'schema': q.QUEUE_SCHEMA, 'rows': self.rows}; queue_path = self.root / 'queue.json'; q.create(queue_path, queue)
        intent = {'schema': q.INTENT_SCHEMA, 'queue': q.row(self.root, queue_path), 'state_directory': 'state/qc_campaign_queue_v1',
                  'automatic_boundary_advancement_authorized': True, 'science_execution_authorized': False, 'max_fresh_cohort_size': 2}
        p = self.root / 'intent.json'; q.create(p, intent); self.control = q.Control(self.root, p, q.sha(p))
        self.counter = 0

    def tearDown(self):
        self.assertTrue(self.root.is_relative_to(R / 'work')); self.temp.cleanup()

    def authority(self, proposal_ref, ids, success=True, **extra):
        self.counter += 1; evidence = self.root / f'evidence{self.counter}.json'; q.create(evidence, {'synthetic_owned_evidence': True})
        value = {'schema': 'TREE2_ROOT_QC_QUEUE_COHORT_CLOSURE_V001', 'queue_sha256': self.control.queue_ref['sha256'],
                 'proposal_sha256': proposal_ref['sha256'], 'queue_ids': ids,
                 'status': 'ROOT_ACCEPTED_CLOSED_COHORT_FOR_QUEUE_ADVANCE' if success else 'ROOT_FAILED_CLOSED_COHORT_REPAIR_REQUIRED',
                 'owned_group_namespace_image_lease_closure_verified': True, 'prior_claims_and_debits_preserved': True,
                 'scientific_validation_passed': success, 'actual_native_exit_code': 0 if success else 2,
                 'closure_and_result_evidence': [q.row(self.root, evidence)], **extra}
        p = self.root / f'authority{self.counter}.json'; q.create(p, value); return q.row(self.root, p)

    def repair_done(self):
        proposal, value = self.control.reconcile(); self.control.reserve(proposal)
        authority = self.authority(proposal, value['queue_ids']); self.control.close(authority)
        return proposal, authority

    def test_current_P20_repair_precedes_fresh_and_preserves_original_order(self):
        _, value = self.control.reconcile()
        self.assertEqual(value['action'], 'REPAIR_CURRENT_P20'); self.assertEqual(value['queue_ids'], ['saved.1', 'reserved.1'])
        self.assertFalse(value['upstream_phase_replay_authorized']); self.assertFalse(value['science_execution_authorized'])

    def test_accepted_event_automatically_proposes_disjoint_next_cohorts(self):
        self.repair_done(); first, value = self.control.reconcile()
        self.assertEqual(value['queue_ids'], ['fresh1.1', 'fresh2.1']); self.control.reserve(first)
        accepted = self.authority(first, value['queue_ids']); next_ref, next_value = self.control.close(accepted)
        self.assertEqual(next_value['queue_ids'], ['fresh3.1'])
        head = q.sha(self.control.head_path); repeat_ref, repeat = self.control.close(accepted)
        self.assertEqual(next_ref, repeat_ref); self.assertEqual(q.sha(self.control.head_path), head)
        self.assertEqual(repeat['queue_ids'], ['fresh3.1'])

    def test_duplicate_reservation_and_active_cohort_do_not_select_again(self):
        proposal, _ = self.control.reconcile(); self.control.reserve(proposal)
        _, value = self.control.reconcile(); self.assertEqual(value['status'], 'ACTIVE_RESERVED_COHORT')
        with self.assertRaises(RuntimeError):
            self.control.reserve(proposal)

    def test_closed_failure_requires_exact_root_repair_authority(self):
        proposal, value = self.control.reconcile(); self.control.reserve(proposal)
        failure = self.authority(proposal, value['queue_ids'], False); self.control.close(failure)
        _, held = self.control.reconcile(); self.assertEqual(held['action'], 'REPAIR_CLOSED_LEDGER_COHORT')
        wrong = self.authority(proposal, value['queue_ids'], prior_failed_authority_sha256='wrong', repaired_without_replaying_accepted_phases=True)
        with self.assertRaises(RuntimeError):
            self.control.close(wrong)
        accepted = self.authority(proposal, value['queue_ids'], prior_failed_authority_sha256=failure['sha256'], repaired_without_replaying_accepted_phases=True)
        _, next_value = self.control.close(accepted); self.assertEqual(next_value['action'], 'RUN_FRESH_COHORT')

    def test_unknown_exit_or_missing_validation_cannot_advance(self):
        proposal, value = self.control.reconcile(); self.control.reserve(proposal)
        for invalid in (None, False, 1):
            proof = self.authority(proposal, value['queue_ids'], actual_native_exit_code=invalid)
            with self.assertRaises(RuntimeError):
                self.control.close(proof)
        proof = self.authority(proposal, value['queue_ids'], scientific_validation_passed=False)
        with self.assertRaises(RuntimeError):
            self.control.close(proof)

    def test_masks_accepted_and_nonsupported_members_never_become_fresh(self):
        self.repair_done(); _, value = self.control.reconcile()
        self.assertEqual(value['rows'][0]['source_masks'], {'contamination': None})
        self.assertNotIn('held.1', value['queue_ids']); self.assertNotIn('accepted.1', value['queue_ids'])

    def test_partial_ledger_commit_stops_instead_of_replaying(self):
        proposal, _ = self.control.reconcile(); self.control.reserve(proposal)
        self.control.head_path.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Incomplete ledger'):
            self.control.reconcile()

    def test_complete_queue_keeps_explicit_nonrunnable_masks(self):
        queue = {'schema': q.QUEUE_SCHEMA, 'rows': [member('ok.1', 0, 'ACCEPTED_METHOD_REUSE_VERIFIED'), member('held.1', 1, 'NOT_RUN_SOURCE_HELD', False)]}
        value = q.decide(queue, [], 20)
        self.assertEqual(value['status'], 'CANDIDATE_QUEUE_DRAIN_REQUIRES_REGISTRY_RECONCILIATION')
        self.assertFalse(value['tree_or_panel_completion_claimed']); self.assertEqual(value['nonrunnable_inventory_rows'], 1)

    def test_unknown_queue_state_cannot_silently_exhaust(self):
        with self.assertRaises(RuntimeError):
            q.decide({'schema': q.QUEUE_SCHEMA, 'rows': [member('unknown.1', 0, 'UNKNOWN_FAILURE')]}, [], 20)

    def test_missing_reserved_metadata_rebuilt_without_new_claim(self):
        proposal, _ = self.control.reconcile(); context_ref = self.control.reserve(proposal)
        head = q.sha(self.control.head_path); q.bind(self.root, context_ref).unlink()
        _, value = self.control.reconcile()
        self.assertEqual(value['status'], 'ACTIVE_RESERVED_COHORT'); self.assertEqual(q.sha(self.control.head_path), head)
        self.assertEqual(value['launch_contexts'], [context_ref])

    def test_no_final_exhaustion_without_current_registry_closed_scope_authority(self):
        self.repair_done()
        for _ in range(2):
            proposal, value = self.control.reconcile(); self.control.reserve(proposal)
            self.control.close(self.authority(proposal, value['queue_ids']))
        _, candidate = self.control.reconcile()
        self.assertEqual(candidate['status'], 'CANDIDATE_QUEUE_DRAIN_REQUIRES_REGISTRY_RECONCILIATION')
        registry = self.root / 'accepted_registry.json'; q.create(registry, {'synthetic_verified_results': True})
        proof = {'schema': 'TREE2_ROOT_QC_QUEUE_REGISTRY_RECONCILIATION_V001', 'status': 'ROOT_VERIFIED_ELIGIBLE_QC_QUEUE_DRAIN_WITH_MASKS',
                 'queue_sha256': self.control.queue_ref['sha256'], 'ledger_head_sha256': self.control.ledger()[1],
                 'verified_qc_queue_ids': [r['queue_id'] for r in self.rows if r['source_supported_scope']],
                 'scientific_validation_and_closed_receipts_reconciled': True, 'source_taxonomy_and_unknown_masks_preserved': True,
                 'tree_or_panel_completion_claimed': False, 'current_accepted_registry': q.row(self.root, registry),
                 'closure_validation_evidence': [q.row(self.root, registry)]}
        p = self.root / 'final_authority.json'; q.create(p, proof)
        _, final = self.control.finalize(q.row(self.root, p))
        self.assertEqual(final['status'], 'ELIGIBLE_QC_QUEUE_EXHAUSTED_WITH_EXPLICIT_MASKS')
        registry.write_text('changed')
        with self.assertRaises(RuntimeError):
            self.control.reconcile()

    def test_changed_or_missing_accepted_authority_holds_instead_of_next(self):
        _, authority = self.repair_done(); path = q.bind(self.root, authority); original = path.read_bytes()
        path.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):
            self.control.reconcile()
        path.write_bytes(original); path.unlink()
        with self.assertRaises(RuntimeError):
            self.control.reconcile()


if __name__ == '__main__':
    unittest.main()
