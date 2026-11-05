"""Pure classification/order fixtures; no runtime, science or queue/state writes."""
import copy
import build_tree2_qc_campaign_queue_v001 as q


def state(**changes):
    values = dict(accession='A', source_supported=True, acquired=True,
                  declared_accepted=set(), verified_accepted=set(), historical=set(),
                  partial=set(), reserved=set())
    values.update(changes)
    return q.execution_state(**values)


def run():
    assert state() == 'READY_FRESH_QC'
    pending = state(partial={'A'}, reserved={'A'})
    assert pending == 'SAVED_VALIDATION_PENDING_NO_UPSTREAM_REPLAY'
    assert q.permitted_work(pending) == 'ROOT_REPAIR_SAVED_VALIDATION_ONLY_AFTER_CLOSURE'
    assert state(partial={'A'}, reserved={'A'}) == pending  # resume is idempotent
    accepted = state(partial={'A'}, declared_accepted={'A'}, verified_accepted={'A'})
    assert accepted == 'ACCEPTED_METHOD_REUSE_VERIFIED'
    assert q.permitted_work(accepted) == 'REVERIFY_BOUND_ACCEPTANCE_HASHES_AND_SKIP_RECALCULATION'
    assert state(declared_accepted={'A'}) == 'HOLD_ACCEPTED_HASH_FAILURE_NO_REPLAY'
    assert state(reserved={'A'}) == 'RESERVED_P20_UNSTARTED'
    assert state(historical={'A'}) == 'HISTORICAL_DONOR_REVIEW_REUSE_ONLY'
    assert state(source_supported=False) == 'NOT_RUN_SOURCE_HELD'
    assert state(acquired=False) == 'NOT_ACQUIRED_OPTIONAL_MAIN_STRAIN'
    rows = [dict(accession=acc, species_taxid=taxid, family=family, genus=genus,
                 assembly_level='Complete Genome', priority95_lane=False, priority92_label=False)
            for acc, taxid, family, genus in [('A1', 1, 'F1', 'G1'), ('A2', 1, 'F1', 'G1'), ('B1', 2, 'F2', 'G2')]]
    before = copy.deepcopy(rows)
    ordered = q.species_balanced_order(rows, set())
    assert [value['accession'] for value, _ in ordered] == ['A1', 'B1', 'A2']
    assert rows == before
    with_prior = q.species_balanced_order(rows, {'A1'})
    assert [value['accession'] for value, _ in with_prior] == ['A1', 'B1', 'A2']
    assert [round_number for _, round_number in with_prior] == [None, 0, 1]
    return {'status': 'PURE_QUEUE_CLASSIFICATION_TRANSITION_RESUME_AND_SPECIES_ORDER_FIXTURES_PASS',
            'fresh_to_partial_to_verified_acceptance_no_replay': True,
            'accepted_hash_failure_remains_hold_not_fresh': True,
            'reserved_history_source_hold_and_missing_input_explicit': True,
            'one_species_label_before_extra_strain': True,
            'accepted_measurement_seeds_coverage_not_new_work': True,
            'idempotent_no_input_mutation': True,
            'scientific_execution_or_runtime_or_state_writes': False}


if __name__ == '__main__':
    import json
    print(json.dumps(run()))
