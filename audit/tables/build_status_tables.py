"""Derive lightweight Tree2 cohort and defence tables from the saved WD evidence."""
import argparse
from collections import Counter
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
QUEUE = 'metadata/defence_preparation_queue_20261029/input_queue.json'
LEDGER = 'state/defence_campaign_v001/ledger.json'
SOURCE = 'qc/source_provenance_audit.tsv'
ACQUISITION = 'qc/acquisition_validation.tsv'
PROVISIONAL = 'metadata/provisional_panel.tsv'
CHECKM1 = 'qc/checkm1_lactobacillales_all919_v001.tsv'
PANEL = 'metadata/panel_critical_path_review_20261029/cohort_manifest_v001.json'
HELDS = 'metadata/panel_critical_path_review_20261029/held19_manifest_v001.json'
COMPOSITION = 'metadata/panel_critical_path_review_20261029/composition_review_v001.json'
C009 = 'analysis/defence_bulk_C009_v003/COHORT_COMPLETE.json'
C009_WSL = 'work/defence_bulk_C009_v003/WSL_actual_exit.json'
C009_NATIVE = ('state/local_continuation_v8/events/'
               '7111b588e3a5c92e03eb751c67d9f044a922f41fb3124da17d263d18cabcd625/'
               'early_worker_actual_exit.json')
C008_FAILURE = 'work/defence_C008_failed_c2ad/Root_C008_failed_disposition.json'
STAGE09 = 'work/stage09_accept_defence_1f62/Root_closed_stage09_computational_acceptance.json'
DETECTORS = ('PADLOC', 'DefenseFinder')
ACCESSION = re.compile(r'GC[AF]_\d+\.\d+')
ACCEPTED = 'CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED'
PENDING = 'COMPUTED_PENDING_INDEPENDENT_QA'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def keyed(rows):
    result = {row['accession']: row for row in rows}
    require(len(rows) == len(result), 'Duplicate accession in an authoritative input')
    return result


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class Project:
    def __init__(self, root):
        self.root = root.resolve()

    def path(self, relative):
        path = (self.root / relative).resolve()
        require(path.is_relative_to(self.root), 'Evidence reference leaves Tree2')
        require(not any(part.casefold() == 'codex_home' or 'private_invocation' in part.casefold()
                        for part in path.relative_to(self.root).parts), 'Private runtime reference refused')
        return path

    def ref(self, relative):
        path = self.path(relative)
        with path.open('rb') as stream:
            return {'path': path.relative_to(self.root).as_posix(), 'bytes': path.stat().st_size,
                    'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}

    def read(self, relative):
        return json.loads(self.path(relative).read_text(encoding='utf-8-sig'))

    def bound(self, row):
        ref = self.ref(row['path'])
        require(ref['sha256'] == row['sha256'] and ref['bytes'] == row['bytes'],
                'Evidence hash or size changed: ' + ref['path'])
        return self.read(row['path'])

    def tsv(self, relative):
        with self.path(relative).open(encoding='utf-8-sig', newline='') as stream:
            return keyed(list(csv.DictReader(stream, delimiter='\t')))


def accepted_inputs(project, ledger):
    grouped = {}
    for accession, entry in ledger['entries'].items():
        if entry['state'] == ACCEPTED:
            grouped.setdefault(entry['acceptance']['path'], (entry['acceptance'], set()))[1].add(accession)
    result = {}
    receipts = []
    for acceptance_ref, accessions in grouped.values():
        acceptance = project.bound(acceptance_ref)
        cohort = acceptance.get('cohort_id', 'ACCEPTED_PILOT_5')
        pilot = cohort == 'ACCEPTED_PILOT_5'
        require(acceptance['status'].startswith('ROOT_ACCEPTED_CLOSED_')
                and acceptance['genomes'] == len(accessions), 'Acceptance does not match its ledger cohort')
        typed_exit_ref = acceptance['validation_actual_exit' if pilot else 'QA_native_actual_exit']
        typed_exit = project.bound(typed_exit_ref)
        require(typed_exit.get('actual_exit_code') == 0, 'Independent QA actual exit zero is missing')
        source_result = project.bound(acceptance['source_result'])
        validated = keyed(project.bound(acceptance['validated_rows'])['rows'])
        require(set(validated) == accessions, 'Independent QA rows differ from accepted accessions')
        if pilot:
            require(acceptance['all_captured_children_groups_private_mount_IPC_RAM_Rbinding_FDs_closed']
                    and project.bound(acceptance['native_actual_exit'])['actual_exit_code'] == 0
                    and project.bound(acceptance['WSL_actual_exit'])['actual_exit_code'] == 0,
                    'Accepted pilot has no science closure')
        else:
            require(acceptance['all_native_WSL_stock_search_descendant_group_namespace_IPC_RAM_Rbinding_FD_and_fourlease_closure_verified']
                    and acceptance['complete_protein_supported_stock_model_scope_rules_independently_reconstructed'],
                    'Accepted production cohort is missing closure or validation scope')
            project.bound(acceptance['science_whole_closure'])
            require(source_result['selected_accessions'] == acceptance['selected_accessions'],
                    'Accepted computation and QA cohort differ')
        for accession, row in validated.items():
            result[accession] = (cohort, acceptance_ref, row)
        receipts.append({'cohort': cohort, 'acceptance': acceptance_ref, 'typed_QA_actual_exit': typed_exit_ref,
                         'validated_rows': acceptance['validated_rows']})
    require(len(result) == ledger['closed_paired_protein_scope_genomes'], 'Closed ledger count does not reconcile')
    return result, receipts


def computed_c009(project, ledger):
    summary = project.read(C009)
    plan = project.bound(summary['source_plan'])
    native = project.read(C009_NATIVE)
    wsl = project.read(C009_WSL)
    require(native['actual_exit_code'] == wsl['actual_exit_code'] == 0
            and native['exact_birth_handle_retained'] and wsl['waited_and_reaped'],
            'Typed native and WSL C009 exit 0 required')
    launch = project.bound(native['worker_identity']['launch_receipt'])
    require(launch['native_owner']['pid'] == native['worker_identity']['pid']
            and launch['native_owner']['windows_creation_filetime_100ns']
            == native['worker_identity']['windows_creation_filetime_100ns'], 'C009 creation identity differs')
    reserved = {accession for accession, row in ledger['entries'].items() if row['state'] == 'RESERVED'}
    reservation = project.bound(ledger['reservation'])
    require(ledger['cohort_id'] == plan['cohort_id'] == reservation['cohort_id'] == 'C009'
            and set(summary['selected_accessions']) == set(reservation['selected_accessions']) == reserved
            and len(reserved) == len(summary['genome_commits']) == 20
            and len(summary['engine_phase_commits']) == 40, 'C009 saved outputs and live ledger reservation differ')
    computed = keyed([project.bound(item) for item in summary['genome_commits']])
    require(set(computed) == reserved, 'C009 genome commit membership differs')
    return computed


def detector_counts(project, detector, phase_ref, accepted_qa=None):
    phase = project.bound(phase_ref)
    execution = project.bound(phase['execution'])
    scoped = project.bound(phase['calls'])
    calls = scoped['calls']
    stock = len(calls)
    complete = sum(item['complete_model_relative_prediction'] is True for item in calls)
    primary = [item for item in calls if item['eligible_primary_predicted_protein_system'] is True]
    require(execution['actual_exit_code'] == 0
            and execution['actual_child_waited_and_reaped'] and execution['group_closed']
            and phase['typed_scientific_HMMER_searches'] > 0,
            'Detector phase lacks successful typed execution: ' + phase_ref['path'])
    require(stock == phase['model_relative_calls'] and len(primary) == phase['eligible_primary_protein_predictions'],
            'Detector phase counts differ: ' + phase_ref['path'])
    if accepted_qa is not None:
        require(stock == accepted_qa['stock_model_relative_calls']
                and len(primary) == accepted_qa['eligible_primary_protein_predictions']
                and accepted_qa['typed_HMMER0'] == phase['typed_scientific_HMMER_searches']
                and accepted_qa['unavailable_is_UNKNOWN'],
                'Independently validated counts differ: ' + phase_ref['path'])
    require(scoped['RNA51_unavailable_never_zero' if detector == 'PADLOC'
                   else 'ADF156_excluded_and_genericCAS_clusters_separate'] is True
            and all(item['complete_model_relative_prediction'] is True for item in primary),
            'Expected feature masks or complete-system rule is absent')
    return {'stock': stock, 'complete': complete, 'primary': len(primary),
            'models': sorted({item['model_id'] for item in primary}), 'phase': phase_ref}


def build(project):
    originals = {name: project.ref(name) for name in (
        QUEUE, LEDGER, SOURCE, ACQUISITION, PROVISIONAL, CHECKM1, PANEL, HELDS, COMPOSITION,
        C009, C009_WSL, C009_NATIVE, C008_FAILURE, STAGE09)}
    ledger, queue = project.read(LEDGER), keyed(project.read(QUEUE)['rows'])
    require(ledger['source_queue'] == originals[QUEUE] and set(ledger['entries']) == set(queue),
            'Frozen defence queue membership differs from the live ledger')
    acquisitions, sources = project.tsv(ACQUISITION), project.tsv(SOURCE)
    provisional, checkm = project.tsv(PROVISIONAL), project.tsv(CHECKM1)
    primary, held = keyed(project.read(PANEL)['rows']), keyed(project.read(HELDS)['rows'])
    composition = keyed(project.read(COMPOSITION)['flagged_rows'])
    require(len(acquisitions) == 1170 and set(acquisitions) == set(sources)
            and len(queue) == len(checkm) == 919 and set(queue) == set(checkm) == set(primary) | set(held)
            and len(primary) == 900 and len(held) == 19 and not (set(primary) & set(held))
            and set(composition) <= set(primary), 'Acquisition, QC, defence and tree cohort sizes disagree')
    require(project.read(STAGE09)['exact900tips_and1000bootstrap_tree_validation'],
            'Computational tree validation evidence is missing')
    accepted, closed_receipts = accepted_inputs(project, ledger)
    c009 = computed_c009(project, ledger)
    c008_failed = set(project.read(C008_FAILURE)['selected_accessions'])
    require(len(c008_failed) == 20 and c008_failed <= set(accepted), 'C008 historical failure is not reconciled')
    source_counts = Counter(row['production_disposition'] for row in sources.values())
    acquisition_rows, defence_rows = [], []
    status_counts = Counter()
    detector_statuses = {key: Counter() for key in DETECTORS}

    for accession in sorted(acquisitions):
        require(ACCESSION.fullmatch(accession) is not None, 'Unversioned assembly accession')
        receipt_path = f'raw/{accession}/acquisition_receipt.json'
        receipt = project.read(receipt_path)
        source, acquisition = sources[accession], acquisitions[accession]
        receipt_ref = project.ref(receipt_path)
        require(receipt['accession'] == accession
                and receipt_ref['sha256'] == acquisition['receipt_sha256'] == source['acquisition_receipt_sha256'],
                'Acquisition receipt differs from independently recorded source evidence')
        metadata = receipt['metadata_record']
        qrow, mrow = queue.get(accession, {}), checkm.get(accession, {})
        tree = 'IN_FULL900_COMPUTATIONAL_TREE' if accession in primary else (
            'HELD_FROM_FULL900' if accession in held else 'OUTSIDE_FROZEN919')
        c2 = qrow.get('CheckM2_diagnostic_comparator') or {}
        if qrow:
            c1 = qrow['CheckM1_method_estimate']
            require(float(mrow['unrounded_Completeness']) == c1['Completeness']
                    and float(mrow['unrounded_Contamination']) == c1['Contamination']
                    and mrow['QC_95_5'] == c1['QC_95_5'] == 'PASS', 'CheckM1 estimate sources differ')
        row = {'accession': accession, 'source_species': source['species'], 'source_genus': metadata.get('genus'),
               'source_family': qrow.get('family', metadata.get('family')), 'source_species_taxid': source['species_taxid'],
               'source_database': metadata.get('source_database'), 'assembly_level': metadata.get('assembly_level'),
               'BioSample': source['biosample'], 'source_audit_disposition': source['production_disposition'],
               'source_provenance': source['source_provenance_status'], 'source_holds_or_exclusions': source['holds_or_exclusions'],
               'source_ANI_status': metadata.get('ncbi_ani_taxonomy_status'), 'source_type_assertion': metadata.get('type_material_label'),
               'acquisition_integrity': acquisition['acquisition_validation'], 'nucleotide_length_bp': acquisition['total_bp'],
               'fasta_records': acquisition['fasta_records'], 'record_n50_bp': acquisition['record_n50'],
               'ambiguous_bases': acquisition['ambiguous_bases'], 'ambiguous_fraction': acquisition['ambiguous_fraction'],
               'provisional_1000_membership': accession in provisional,
               'provisional_selection_phase': provisional.get(accession, {}).get('selection_phase'),
               'frozen_919_defence_target': accession in queue, 'defence_queue_position': qrow.get('position'),
               'CheckM1_method': mrow.get('method'), 'CheckM1_completeness_pct': mrow.get('unrounded_Completeness'),
               'CheckM1_contamination_pct': mrow.get('unrounded_Contamination'), 'CheckM1_95_5_method_result': mrow.get('QC_95_5'),
               'CheckM2_diagnostic_completeness_pct': c2.get('Completeness'),
               'CheckM2_diagnostic_contamination_pct': c2.get('Contamination'),
               'full900_status': tree, 'full900_hold_reasons': compact(held[accession]['exclusion_or_hold_reasons']) if accession in held else None,
               'full900_composition_flag': accession in composition,
               'independent_taxonomy': 'UNRESOLVED_NOT_ACCEPTED',
               'final_panel_accepted': False, 'acquisition_receipt_path': receipt_path,
               'acquisition_receipt_sha256': receipt_ref['sha256']}
        acquisition_rows.append(row)
        if not qrow:
            continue
        ledger_row = ledger['entries'][accession]
        status = ACCEPTED if accession in accepted else PENDING if accession in c009 else ledger_row['state']
        status_counts[status] += 1
        overview = {'accession': accession, 'source_species': qrow['species'], 'source_genus': row['source_genus'],
                    'source_family': qrow['family'], 'queue_position': qrow['position'], 'full900_status': tree,
                    'ledger_state': ledger_row['state'], 'defence_current_state': status,
                    'cohort': accepted[accession][0] if accession in accepted else ledger_row.get('cohort_id'),
                    'historical_C008_failed_adapter_recovered': accession in c008_failed,
                    'PADLOC_RNA_scope': 'UNKNOWN_UNAVAILABLE',
                    'DefenseFinder_Cas_array_scope': 'UNKNOWN_UNAVAILABLE_WHERE_REQUIRED',
                    'complete_ring_final_accepted': False,
                    'acceptance_evidence_path': accepted[accession][1]['path'] if accession in accepted else None,
                    'acceptance_evidence_sha256': accepted[accession][1]['sha256'] if accession in accepted else None,
                    'computation_only_evidence_path': C009 if accession in c009 else None,
                    'computation_only_evidence_sha256': originals[C009]['sha256'] if accession in c009 else None}
        for detector in DETECTORS:
            phase, counts, qa = None, None, None
            if accession in accepted:
                qa = accepted[accession][2]['engines'][detector]
                phase = qa['commit']
            if accession in c009:
                phase = c009[accession]['engines'][detector]
            if phase:
                counts = detector_counts(project, detector, phase, qa)
            if qa is not None:
                label = ('ACCEPTED_PRIMARY_COMPLETE_PREDICTIONS' if counts['primary']
                         else 'ACCEPTED_ZERO_PRIMARY_WITH_OTHER_COMPLETE_STOCK_CALLS' if counts['complete']
                         else 'ACCEPTED_ZERO_COMPLETE_PREDICTIONS_IN_ASSESSED_SCOPE')
            else:
                label = status
            detector_statuses[detector][label] += 1
            overview.update({
                f'{detector}_status': label,
                f'{detector}_accepted_stock_calls': counts['stock'] if qa is not None else None,
                f'{detector}_accepted_complete_model_relative_predictions': counts['complete'] if qa is not None else None,
                f'{detector}_accepted_primary_complete_predictions': counts['primary'] if qa is not None else None,
                f'{detector}_accepted_primary_model_ids': compact(counts['models']) if qa is not None else None,
                f'{detector}_computed_pending_QA_stock_calls': counts['stock'] if accession in c009 else None,
                f'{detector}_computed_pending_QA_complete_model_relative_predictions': counts['complete'] if accession in c009 else None,
                f'{detector}_computed_pending_QA_primary_complete_predictions': counts['primary'] if accession in c009 else None,
                f'{detector}_phase_commit_path': phase['path'] if phase else None,
                f'{detector}_phase_commit_sha256': phase['sha256'] if phase else None,
            })
        defence_rows.append(overview)

    require(len(acquisition_rows) == 1170 and len(defence_rows) == 919
            and len(accepted) == 165 and len(c009) == 20, 'Snapshot row counts differ')
    require(all(project.ref(name) == expected for name, expected in originals.items()),
            'An authoritative input changed during export')
    return acquisition_rows, defence_rows, {
        'source_artifacts': originals, 'accepted_cohort_evidence': closed_receipts,
        'counts': {'acquired': len(acquisition_rows), 'provisional_selection_total': len(provisional),
                   'acquired_in_provisional_selection': len(set(acquisitions) & set(provisional)),
                   'source_audit_dispositions': dict(source_counts), 'CheckM1_method_PASS_95_5': len(checkm),
                   'frozen_defence_target': len(queue), 'full900_computational_tree': len(primary),
                   'full900_source_species': len({row['source_species_label'] for row in primary.values()}),
                   'held_from_full900': len(held), 'full900_hold_reasons': dict(Counter(
                       reason for row in held.values() for reason in row['exclusion_or_hold_reasons'])),
                   'full900_composition_flags': len(composition), 'CheckM2_diagnostic_rows': sum(
                       bool(row.get('CheckM2_diagnostic_comparator')) for row in queue.values()),
                   'defence_current_states': dict(status_counts),
                   'detector_states': {key: dict(value) for key, value in detector_statuses.items()}},
        'publication_limits': ['No genome nucleotide payload', 'Accepted results are model-relative predicted systems',
                               'Numerical CheckM1 method pass is separate from taxonomy or final panel acceptance',
                               'C009 actual native/WSL exits zero establish computed output only',
                               'Blank counts are unavailable or outside accepted scope, never zeros',
                               'RNA and other unavailable or excluded model scope stays UNKNOWN',
                               'C008 failed adapter output is historical and independently recovered'],
    }


def write_tsv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, delimiter='\t', fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[3])
    parser.add_argument('--output', type=Path, default=HERE)
    args = parser.parse_args()
    acquired, defence, summary = build(Project(args.source_root))
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = {'acquired_genomes.tsv': acquired, 'defence_status.tsv': defence}
    files = {}
    for name, rows in outputs.items():
        path = args.output / name
        write_tsv(path, rows)
        with path.open('rb') as stream:
            files[name] = {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                           'bytes': path.stat().st_size, 'rows': len(rows)}
    summary.update({'schema': 'TREE2_LIGHTWEIGHT_COHORT_DEFENCE_TABLES_V001', 'status': 'PASS',
                    'outputs': files, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    with (args.output / 'table_manifest.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summary['counts']))


if __name__ == '__main__':
    main()
