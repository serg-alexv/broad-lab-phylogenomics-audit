"""Build an immutable planning queue from existing receipts, never launch science.

Importing this module performs no I/O. Eligibility, execution and final panel
acceptance are independent fields. Accepted results are never fresh-work inputs.
"""
from pathlib import Path
import argparse
import collections
import copy
import csv
import datetime
import hashlib
import io
import json
import os
import uuid

R = Path(__file__).resolve().parents[1]
PREFIX = 'metadata/tree2_qc_campaign_queue_v001'
P20_RUN = 'analysis/checkm2_phase_separated_P20/runs/20261027T130834Z-901be135bb90'


def inside(value):
    value = Path(value)
    value = (value if value.is_absolute() else R / value).resolve()
    if not value.is_relative_to(R) or value.is_relative_to(R / 'work/local_continuation/codex_home'):
        raise ValueError('Queue artifact outside public project scope')
    return value


def artifact(value):
    value = inside(value)
    with value.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    return {'path': value.relative_to(R).as_posix(), 'sha256': digest, 'bytes': value.stat().st_size}


def read(value):
    return json.loads(inside(value).read_text(encoding='utf-8-sig'))


def bind(value):
    actual = artifact(value['path'])
    if actual['sha256'] != value['sha256'] or ('bytes' in value and actual['bytes'] != value['bytes']):
        raise ValueError('Bound queue evidence changed: ' + value['path'])
    return inside(value['path'])


def execution_state(accession, source_supported, acquired, declared_accepted,
                    verified_accepted, historical, partial, reserved):
    """Pure facts-to-state projection; re-evaluation never consumes an attempt."""
    if accession in declared_accepted:
        return 'ACCEPTED_METHOD_REUSE_VERIFIED' if accession in verified_accepted else 'HOLD_ACCEPTED_HASH_FAILURE_NO_REPLAY'
    if not acquired:
        return 'NOT_ACQUIRED_OPTIONAL_MAIN_STRAIN'
    if accession in partial:
        return 'SAVED_VALIDATION_PENDING_NO_UPSTREAM_REPLAY'
    if accession in historical:
        return 'HISTORICAL_DONOR_REVIEW_REUSE_ONLY'
    if not source_supported:
        return 'NOT_RUN_SOURCE_HELD'
    if accession in reserved:
        return 'RESERVED_P20_UNSTARTED'
    return 'READY_FRESH_QC'


def permitted_work(state):
    return {
        'ACCEPTED_METHOD_REUSE_VERIFIED': 'REVERIFY_BOUND_ACCEPTANCE_HASHES_AND_SKIP_RECALCULATION',
        'SAVED_VALIDATION_PENDING_NO_UPSTREAM_REPLAY': 'ROOT_REPAIR_SAVED_VALIDATION_ONLY_AFTER_CLOSURE',
        'RESERVED_P20_UNSTARTED': 'ROOT_CONTINUATION_ADMISSION_REQUIRED_NO_DUPLICATE_COHORT',
        'HISTORICAL_DONOR_REVIEW_REUSE_ONLY': 'ROOT_REVIEW_ACTUAL_PHASE_HISTORY_AND_REUSE_AUTHORITY',
        'READY_FRESH_QC': 'PROPOSE_FRESH_BOUNDED_QC_AFTER_ROOT_ADMISSION',
    }.get(state, 'HOLD_NO_SCIENTIFIC_EXECUTION')


def species_balanced_order(rows, accepted):
    """One unmeasured label before another strain; deterministic family/genus balance."""
    accepted_rows = sorted((r for r in rows if r['accession'] in accepted), key=lambda r: r['accession'])
    rest = [r for r in rows if r['accession'] not in accepted]
    groups = collections.defaultdict(list)
    assembly_rank = {'Complete Genome': 0, 'Chromosome': 1, 'Scaffold': 2, 'Contig': 3}
    for item in rest:
        groups[str(item['species_taxid'])].append(item)
    for values in groups.values():
        values.sort(key=lambda r: (assembly_rank.get(r.get('assembly_level'), 9), r['accession']))
    species = collections.Counter(str(r['species_taxid']) for r in accepted_rows)
    families = collections.Counter(r['family'] for r in accepted_rows)
    genera = collections.Counter(r['genus'] for r in accepted_rows)
    output = [(r, None) for r in accepted_rows]
    while groups:
        candidate = min((v[0] for v in groups.values()), key=lambda r: (
            species[str(r['species_taxid'])],
            0 if r.get('priority92_label') else 1,
            0 if r.get('priority95_lane') else 1,
            families[r['family']], genera[r['genus']], r['family'], r['genus'],
            str(r['species_taxid']).zfill(12), r['accession']))
        label = str(candidate['species_taxid'])
        output.append((candidate, species[label]))
        species[label] += 1; families[candidate['family']] += 1; genera[candidate['genus']] += 1
        groups[label].pop(0)
        if not groups[label]: del groups[label]
    return output


def atomic_new(path, raw):
    """Atomic create without replacing an existing version or receipt."""
    path = inside(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.partial')
    with temporary.open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    try:
        os.link(temporary, path)  # fails atomically if the final name already exists
    finally:
        temporary.unlink()


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def verified_registry(registry):
    verified, evidence = set(), {}
    for member in registry['rows']:
        refs = []
        for value in member.values():
            if isinstance(value, dict) and {'path', 'sha256'} <= value.keys():
                bind(value); refs.append(artifact(value['path']))
        if not refs: raise ValueError('Accepted method has no bound result evidence')
        if 'feature_validation' in member:
            value = read(member['feature_validation']['path'])
            if value.get('accession') != member['accession'] or value.get('finite_domain_features') != 21241 or value.get('membership_mismatches') != 0:
                raise ValueError('Accepted feature identity/complete receipt differs')
        for key in ('quality_unit_execution', 'validation_unit_execution'):
            if key in member:
                unit = read(member[key]['path'])
                if type(unit.get('exit_code')) is not int or unit['exit_code'] != 0 or unit.get('owned_group_empty') is not True:
                    raise ValueError('Accepted method unit is not actually zero/group closed')
        verified.add(member['accession']); evidence[member['accession']] = refs
    baseline = registry['additional_baseline']; bind(baseline['authority'])
    authority = read(baseline['authority']['path'])
    pointer = inside(authority['latest_pointer_path'])
    if artifact(pointer)['sha256'] != authority['latest_pointer_sha256']:
        raise ValueError('Accepted recovered baseline pointer changed')
    latest = read(pointer)
    refs = [artifact(baseline['authority']['path']), artifact(pointer)]
    for prefix in ('validation', 'execution', 'closed_manifest', 'full_native_closure'):
        value = {'path': latest[prefix + '_path'], 'sha256': latest[prefix + '_sha256']}
        bind(value); refs.append(artifact(value['path']))
    verified.add(baseline['accession']); evidence[baseline['accession']] = refs
    return verified, evidence


def build(prefix=PREFIX):
    inputs = ['metadata/checkm2_production_preparation_P1/coverage_and_queue.json',
              'metadata/checkm2_production_preparation_P1/history.json',
              'metadata/provisional_panel.json', 'qc/source_provenance_audit.json',
              'metadata/acquisition_gap9_reconciliation_v001.json',
              'metadata/checkm2_accepted_method_result_registry_v003.json',
              'metadata/checkm2_phase_separated_execution_plan_P20.json',
              'metadata/checkm2_phase_separated_recipe_P20.json', P20_RUN + '/failure.json',
              P20_RUN + '/invocations.json']
    before = [artifact(value) for value in inputs]
    coverage, history, panel, source, gap, registry, plan, recipe = [read(value) for value in inputs[:8]]
    supported = {value['accession']: value for value in coverage['rows']}
    held = {value['accession']: value for value in coverage['other_source_dispositions_preserved_for_separate_review']}
    source_records = {value['accession']: value for value in source['records']}
    main = {value['accession']: value for value in panel}
    gap_records = {value['original_provisional_accession']: value for value in gap['records']}
    assert len(supported) == 919 and len(held) == 251 and len(main) == 1000
    verified, accepted_evidence = verified_registry(registry)
    declared = set(registry['accepted_unique_method_accessions'])
    assert verified == declared and len(verified) == 17
    historical = {value['accession'] for value in history['DNA_donors_from_receipts_only']}
    reserved = set(plan['accessions'])
    assert len(reserved) == 20 and plan['accessions'] == recipe['inference_order']
    first = plan['accessions'][0]
    failure = read(P20_RUN + '/failure.json')
    assert failure['completed_qc_rows'] == 0 and failure['rows'] == []
    partial = {first}; partial_units = []
    for name in ('unit_annotation', 'unit_diamond', 'unit_resume', 'unit_feature_validation'):
        path = f'{P20_RUN}/rows/{first}/{name}/execution.json'; value = read(path)
        assert value['owned_group_empty'] is True and value['remaining_owned_processes'] == []
        assert value['exit_code'] == (1 if name == 'unit_feature_validation' else 0)
        partial_units.append({'unit': name, 'execution': artifact(path), 'actual_exit_code': value['exit_code'], 'elapsed_seconds': value['elapsed_seconds']})
        before.append(artifact(path))
    receipt_paths = sorted((R / 'raw').glob('*/acquisition_receipt.json'))
    assert len(receipt_paths) == 1170
    acquisition, receipt_refs, aliases, fna_hash_groups = {}, {}, {}, collections.defaultdict(list)
    rows, metadata_issues = [], []
    for path in receipt_paths:
        value = read(path); accession = value['accession']; reference = artifact(path)
        assert path.parent.name == accession and value['acquisition_status'] == 'PASS'
        source_item = source_records[accession]
        assert reference['sha256'] == source_item['acquisition_receipt_sha256']
        fasta = [item for item in value['files'] if item['path'].lower().endswith('.fna')]
        assert len(fasta) == 1
        fasta = {**fasta[0], 'path': (path.parent / fasta[0]['path']).relative_to(R).as_posix()}
        if not inside(fasta['path']).is_file() or inside(fasta['path']).stat().st_size != fasta['bytes']:
            metadata_issues.append(accession)
        acquisition[accession] = value; receipt_refs[accession] = reference
        fna_hash_groups[fasta['sha256']].append(accession)
        context = value['metadata_record']; original = supported.get(accession)
        pair = context.get('paired_accession'); aliases[accession] = [pair] if pair else []
        source_supported = accession in supported
        assert (source_item['production_disposition']=='SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN') == source_supported
        if original:
            assert original['acquisition_receipt']==reference and original['FNA_from_receipt']==fasta
        state = execution_state(accession, source_supported, True, declared, verified, historical, partial, reserved)
        source_masks = copy.deepcopy(original['source_masks']) if original else {
            'independent_taxonomy': 'UNRESOLVED_NOT_ACCEPTED', 'production_acceptance': False,
            'source_ANI_status': context.get('ncbi_ani_taxonomy_status'),
            'source_holds': copy.deepcopy(source_item['holds_or_exclusions'])}
        item = {'queue_id': accession, 'accession': accession, 'species': context['species'],
                'species_taxid': context['species_taxid'], 'family': context['family'], 'genus': context['genus'],
                'assembly_level': context['assembly_level'], 'biosample': context.get('biosample'), 'strain': context.get('strain'),
                'main_panel_member': accession in main, 'acquired': True, 'source_supported_scope': source_supported,
                'source_eligibility': source_item['production_disposition'], 'source_eligibility_is_biological_PASS': False,
                'source_holds_preserved': copy.deepcopy(original['source_holds_preserved']) if original else copy.deepcopy(source_item['holds_or_exclusions']),
                'source_pending_reasons': copy.deepcopy(original['source_pending_reasons']) if original else copy.deepcopy(context.get('pending_reasons', [])),
                'source_masks': source_masks, 'metadata_qc': context['metadata_qc'],
                'source_metadata_checkm': {'value': copy.deepcopy(source_item['ncbi_checkm_info']), 'availability': 'SOURCE_CONTEXT_ONLY_NOT_MEASURED_QC_TRUTH'},
                'source_provenance_record': {'source': before[3], 'accession': accession, 'source_report_sha256': source_item['source_report_sha256']},
                'paired_accessions': aliases[accession], 'FNA_from_receipt': fasta, 'acquisition_receipt': reference,
                'input_payload_sha256_required_before_consumption': True,
                'qc_execution_state': state, 'next_permitted_work': permitted_work(state),
                'priority95_lane': original.get('priority95_lane', False) if original else False,
                'priority92_label': original.get('priority92_label', False) if original else False,
                'method_estimate_hashes_verified': accession in verified,
                'accepted_result_bindings': accepted_evidence.get(accession, []),
                'accepted_result_verification_scope': 'Registry/authority/commit/feature/unit JSON SHA256; payloads reverify before downstream consumption',
                'reserved_P20_order': plan['accessions'].index(accession) if accession in reserved else None,
                'prior_evidence': {'historical_DNA_donor': accession in historical,
                                   'P1_history': before[1], 'P20_partial_units': partial_units if accession in partial else [],
                                   'upstream_replay_forbidden': accession in partial or accession in verified,
                                   'reused_phase_authority_required': accession in historical or accession in partial},
                'defence_status': 'UNKNOWN_UNSEARCHED', 'final_panel_acceptance': False}
        if accession in metadata_issues:
            item['qc_execution_state'] = 'HOLD_ACQUIRED_FILE_METADATA_CHANGED_NO_REPLAY'; item['next_permitted_work'] = 'HOLD_NO_SCIENTIFIC_EXECUTION'
        rows.append(item)
    assert set(acquisition) == set(supported) | set(held) == set(source_records)
    duplicate_hashes = [values for values in fna_hash_groups.values() if len(values) > 1]
    duplicate_pairs = [(a, b) for a, values in aliases.items() for b in values if b in acquisition]
    if duplicate_hashes or duplicate_pairs:
        raise ValueError('Previously unrecorded acquired DNA/pair duplicates require explicit alias authority')
    acquired_set = set(acquisition)
    for accession in sorted(set(main) - acquired_set):
        context = main[accession]; record = gap_records[accession]
        rows.append({'queue_id': accession, 'accession': accession, 'species': context['species'],
                     'species_taxid': context['species_taxid'], 'family': context['family'], 'genus': context['genus'],
                     'assembly_level': context['assembly_level'], 'main_panel_member': True, 'acquired': False,
                     'source_supported_scope': False, 'source_eligibility': 'NOT_ACQUIRED_OPTIONAL_MAIN_STRAIN',
                     'source_eligibility_is_biological_PASS': False, 'source_holds_preserved': context.get('exclusion_reasons', []),
                     'source_pending_reasons': context.get('pending_reasons', []),
                     'source_masks': {'independent_taxonomy': 'UNRESOLVED_NOT_ACCEPTED', 'production_acceptance': False},
                     'paired_accessions': [context['paired_accession']] if context.get('paired_accession') else [],
                     'qc_execution_state': 'NOT_ACQUIRED_OPTIONAL_MAIN_STRAIN', 'next_permitted_work': 'HOLD_OPTIONAL_STRAIN_ALREADY_REPRESENTED',
                     'gap9_reconciliation': {'source': before[4], 'record': record},
                     'method_estimate_hashes_verified': False, 'accepted_result_bindings': [], 'FNA_from_receipt': None,
                     'acquisition_receipt': None, 'reserved_P20_order': None, 'prior_evidence': {},
                     'defence_status': 'UNKNOWN_UNSEARCHED', 'final_panel_acceptance': False})
    eligible = [item for item in rows if item['source_supported_scope']]
    ordered = species_balanced_order(eligible, verified)
    ordered.extend((item, None) for item in sorted((r for r in rows if not r['source_supported_scope']), key=lambda r: r['accession']))
    for number, (item, round_number) in enumerate(ordered):
        item['frozen_order'] = number; item['species_round'] = round_number
    rows = [item for item, _ in ordered]
    after = [artifact(value['path']) for value in before]
    assert after == before and not metadata_issues
    state_counts = dict(collections.Counter(r['qc_execution_state'] for r in rows))
    supported_counts = dict(collections.Counter(r['qc_execution_state'] for r in eligible))
    summary = {'inventory_rows': len(rows), 'acquired_rows': len(acquisition), 'main_panel_rows': len(main),
               'main_panel_acquired': len(set(main) & acquired_set), 'optional_main_strain_not_acquired': len(set(main) - acquired_set),
               'source_supported_scope': len(eligible), 'source_held_or_excluded_acquired': len(held),
               'source_eligibility_counts': dict(collections.Counter(r['source_eligibility'] for r in rows)),
               'execution_state_counts': state_counts, 'source_supported_execution_state_counts': supported_counts,
               'accepted_method_all_sources': len(verified), 'accepted_method_source_supported': len(verified & set(supported)),
               'source_supported_still_needing_QC_work_or_history_review': 919 - len(verified & set(supported)),
               'P1_fresh900_reconciles_as': {'partial_validation_pending': 1, 'reserved_unstarted': 19, 'other_ready_fresh': 880},
               'acquired_duplicate_FNA_hash_groups': duplicate_hashes, 'acquired_pair_collisions': duplicate_pairs,
               'all_source_supported_species_labels': len({r['species_taxid'] for r in eligible}),
               'biological_panel_PASS_count_claimed': 0}
    assert len(rows) == 1179 and supported_counts['READY_FRESH_QC'] == 880
    value = {'schema': 'TREE2_CANONICAL_QC_QUEUE_V001', 'version': 1, 'status': 'IMMUTABLE_PLANNING_QUEUE_NOT_EXECUTION_ADMISSION',
             'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'builder': artifact(__file__),
             'summary': summary, 'source_bindings': before, 'acquisition_receipt_manifest': list(receipt_refs.values()),
             'rows': rows, 'order_policy': 'Accepted source-supported measurements seed counts and skip; each unmeasured species label precedes another strain, priority95/92 then deterministic family/genus balancing and assembly/accession tie breaks.',
             'scope_policy': 'All919 acquired source-supported chosen records; retain251 held/excluded acquired and9 optional unacquired main-panel slots as non-runnable inventory. Source eligibility is not biological PASS.',
             'event_overlay_policy': 'Immutable base; only separately verified append-only Root events/intents under state/qc_campaign_queue_v1 may project later states. Never rewrite old queue or original scientific receipts.',
             'new_scientific_execution_authorized': False, 'unknown_failed_or_unrun_as_negative': False,
             'local_runtime_ownership_or_handoff_changed': False}
    stream = io.StringIO(newline=''); writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
    columns = ['frozen_order','queue_id','species','species_taxid','family','genus','source_supported_scope','source_eligibility','qc_execution_state','next_permitted_work','main_panel_member','acquired','species_round','reserved_P20_order','method_estimate_hashes_verified']
    writer.writerow(columns)
    for item in rows: writer.writerow([item.get(key) for key in columns])
    atomic_new(prefix + '.json', json_bytes(value)); atomic_new(prefix + '.tsv', stream.getvalue().encode())
    manifest = {'schema': 'TREE2_CANONICAL_QC_QUEUE_MANIFEST_V001', 'status': 'PLANNING_ARTIFACTS_COMMITTED_NO_EXECUTION',
                'files': [artifact(prefix + '.json'), artifact(prefix + '.tsv')], 'builder': artifact(__file__),
                'input_bindings': before, 'receipt_manifest_rows': len(receipt_refs), 'summary': summary}
    atomic_new(prefix + '.manifest.json', json_bytes(manifest))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output-prefix', default=PREFIX)
    print(json.dumps(build(parser.parse_args().output_prefix)))
