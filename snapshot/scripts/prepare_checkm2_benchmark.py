#!/usr/bin/env python3
"""Prepare a ten-genome follow-on benchmark. This script never starts prediction."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import uuid

R = Path(__file__).resolve().parents[1]
OUT = R / 'analysis/checkm2_benchmark10'


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def source_input(row, audit, role):
    accession = row['accession']
    if not re.fullmatch(r'GC[AF]_\d{9}\.\d+', accession):
        raise RuntimeError('Invalid versioned accession')
    folder = R / 'raw' / accession
    receipt_path = folder / 'acquisition_receipt.json'
    receipt = read(receipt_path)
    records = [entry for entry in receipt['files'] if entry['path'].endswith('.fna')]
    if len(records) != 1:
        raise RuntimeError('Exactly one acquired genomic FNA required')
    item = records[0]
    path = (folder / item['path']).resolve()
    if not path.is_relative_to(R.resolve()):
        raise RuntimeError('Input escapes project')
    if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise RuntimeError('Input does not match acquisition receipt')
    if sha(receipt_path) != audit['acquisition_receipt_sha256']:
        raise RuntimeError('Source audit acquisition binding differs')
    return {
        'accession': accession, 'species': row['species'], 'genus': row['genus'],
        'family': row['family'], 'role': role, 'metadata_qc': row['metadata_qc'],
        'selection_status': row.get('selection_status'),
        'source_disposition': audit['production_disposition'],
        'source_holds_preserved': audit['holds_or_exclusions'],
        'fasta_path': path.relative_to(R).as_posix(),
        'fasta_bytes': item['bytes'], 'fasta_sha256': item['sha256'],
        'acquisition_receipt_sha256': sha(receipt_path),
        'source_metadata_checkm': {
            'completeness': row.get('ncbi_checkm_completeness'),
            'contamination': row.get('ncbi_checkm_contamination'),
            'version': row.get('ncbi_checkm_version'),
            'role': 'CONTEXT_ONLY_NOT_TRUTH_OR_CALIBRATION'},
        'production_acceptance': 'NOT_GRANTED',
        'source_taxonomy_gates': 'REQUIRED_INDEPENDENTLY_OF_ANY_QC_SCORE',
    }


def main():
    panel_path = R / 'metadata/provisional_panel.json'
    audit_path = R / 'qc/source_provenance_audit.json'
    review_path = R / 'metadata/acquisition_qc_review_only.json'
    panel, report, review = read(panel_path), read(audit_path), read(review_path)
    source = {row['accession']: row for row in report['records']}
    supported = []
    review_supported = []
    for row in panel:
        audit = source.get(row['accession'])
        if (audit and audit['production_disposition'] == 'SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN'
                and (R / 'raw' / row['accession'] / 'acquisition_receipt.json').exists()):
            supported.append(row)
    for row in review:
        audit = source.get(row['accession'])
        # Metadata-only exclusions may be investigated, not promoted. Source/taxon holds may not.
        if (audit and row.get('selection_status') == 'QC_REVIEW_ONLY'
                and audit['source_report_integrity'] == 'PASS'
                and audit['isolate_source_supported'] is True
                and not any(audit.get(key) for key in ('is_mag', 'is_sag', 'is_uncultivated', 'source_conflict'))
                and set(audit['holds_or_exclusions']) == {'HOLD_EXISTING_METADATA_QC_EXCLUSION'}
                and (R / 'raw' / row['accession'] / 'acquisition_receipt.json').exists()):
            review_supported.append(row)
    chosen = []
    used_accessions, genera, families = set(), set(), set()

    def add(row, role):
        chosen.append(source_input(row, source[row['accession']], role))
        used_accessions.add(row['accession'])
        genera.add(row['genus'])
        families.add(row['family'])

    # Include metadata-sensitive controls deliberately: two low-completeness isolates and one high-contamination isolate.
    low = [row for row in review_supported if row.get('ncbi_checkm_completeness') is not None
           and row['ncbi_checkm_completeness'] < 95]
    high = [row for row in review_supported if row.get('ncbi_checkm_contamination') is not None
            and row['ncbi_checkm_contamination'] > 5]
    for pool, number, role in [(low, 2, 'ANCILLARY_METADATA_LOW_COMPLETENESS_REVIEW'),
                               (high, 1, 'ANCILLARY_METADATA_HIGH_CONTAMINATION_REVIEW')]:
        for _ in range(number):
            available = [row for row in pool if row['accession'] not in used_accessions]
            if not available:
                raise RuntimeError('Requested source-supported review control unavailable; no silent substitution')
            available.sort(key=lambda row: (row['genus'] in genera, row['family'] in families, row['accession']))
            add(available[0], role)
    # Avoid rerunning the first one-genome pilot solely for this benchmark.
    pilot_plan = R / 'analysis/checkm2_pilot/pilot_plan.json'
    first_pilot = read(pilot_plan)['input']['accession'] if pilot_plan.exists() else None
    normal = [row for row in supported if row['metadata_qc'] == 'QC_METADATA_PASS'
              and row['accession'] != first_pilot]
    while len(chosen) < 10:
        available = [row for row in normal if row['accession'] not in used_accessions]
        if not available:
            raise RuntimeError('Not enough eligible benchmark genomes')
        available.sort(key=lambda row: (row['family'] in families, row['genus'] in genera,
                                        row['contigs'] or 10**9, row['accession']))
        add(available[0], 'SOURCE_SUPPORTED_CURRENT_PANEL_METADATA_PASS')
    binding = {
        'source_files': {str(path.relative_to(R)): sha(path) for path in
                         (panel_path, audit_path, review_path)},
        'inputs': chosen,
        'follow_on_options_template': {'threads': 2, 'cpu_affinity_max': 2,
            'lowmem': True, 'author_diamond_blocksize': 0.5,
            'group_rss_limit_bytes': 2 * 1024**3, 'minimum_linux_available_bytes': 1024**3,
            'prediction_deadline_seconds': 600,
            'one_invocation_with_ten_genomes': True, 'author_internals_modified': False,
            'source_metadata_checkm_role': 'COMPARISON_ONLY',
            'model_tool_database_binding': 'REQUIRE_ACCEPTED_PILOT_EXACT_BINDING',
            'production_acceptance': 'NOT_GRANTED'},
        'cohort_scope': {
            'current_panel_source_supported_candidates': len(supported),
            'metadata_qc_counts': dict(collections.Counter(row['metadata_qc'] for row in supported)),
            'ancillary_source_supported_metadata_qc_review_only_candidates': len(review_supported),
            'scope_note': 'Metadata-only QC exclusion is investigable; source/taxonomy holds and MAG/SAG exclusion remain in force. Any later panel admission requires independent source, QC and taxonomy gates.'},
        'execution_state': 'TEMPLATE_ONLY_NOT_EXECUTABLE_NO_PREDICTION_RUN',
        'launch_gates': ['one-genome pilot model/resource/schema pass',
            'review emitted compatibility warnings and all numeric pilot outputs',
            'exact runtime/model/database/input binding reverified',
            'no other heavy worker; fresh Linux headroom and volume reserve',
            'native Windows launch identity, owned Linux process group and OS lock',
            'live stage04 registration before prediction starts',
            'validate exactly ten accession rows; no missing/nonfinite estimates',
            'preserve partial Prodigal/DIAMOND outputs; no absence from failed prediction'],
        'controller_preparation_sha256': sha(__file__),
    }
    key = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    target = OUT / 'plans' / key[:16]
    if target.exists():
        manifest = read(target / 'manifest.json')
        for entry in manifest['files']:
            if sha(target / entry['path']) != entry['sha256']:
                raise RuntimeError('Existing prepared benchmark artifact hash mismatch')
    else:
        target.mkdir(parents=True)
        save(target / 'plan.json', binding)
        files = [{'path': 'plan.json', 'sha256': sha(target / 'plan.json')}]
        save(target / 'manifest.json', {'files': files})
        save(target / 'commit.json', {'status': 'PREPARED_ONLY', 'binding_sha256': key,
             'manifest_sha256': sha(target / 'manifest.json'), 'prediction_run': False})
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pointer = {'status': 'PREPARED_NOT_RUN', 'prepared_utc': now, 'binding_sha256': key,
               'plan_path': str(target / 'plan.json'), 'manifest_sha256': sha(target / 'manifest.json'),
               'genomes': len(chosen), 'genera': len(genera), 'families': len(families),
               'production_acceptance': 'NOT_GRANTED'}
    save(OUT / 'latest_preparation.json', pointer)
    save(R / 'state/checkm2_benchmark_progress.json', {
        'status': 'PREPARED', 'done': 0, 'total': 10, 'unit': 'benchmark genomes',
        'detail': 'Ten-genome follow-on template prepared; awaits one-genome pilot gates. No benchmark worker launched.',
        'updated_utc': now, 'plan_path': str(target / 'plan.json'),
        'production_acceptance': 'NOT_GRANTED'})
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
