"""Verify six protein payloads that a conservative alphabet check set aside."""
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import unquote


BUNDLE = Path(__file__).resolve().parent
PROJECT = BUNDLE.parents[1]
ACCESSIONS = (
    'GCF_001434395.1', 'GCF_001437125.1', 'GCF_003885105.1', 'GCF_005405125.1', 'GCF_045862785.1',
)
NT = set(b'ACGTRYSWKMBDHVNU')
AA = set(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ*?.-')
GAPS = set(b'*?.-')


def fasta(path):
    identifier = None
    sequence = bytearray()
    with path.open('rb') as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith(b'>'):
                if identifier is not None:
                    yield identifier, bytes(sequence)
                identifier = line[1:].split(None, 1)[0].decode('ascii')
                sequence.clear()
            elif line and not line.startswith(b';'):
                if identifier is None:
                    raise ValueError('FASTA payload before first header')
                sequence.extend(line.upper())
    if identifier is not None:
        yield identifier, bytes(sequence)


def ref(path):
    with path.open('rb') as stream:
        return {'path': path.relative_to(PROJECT).as_posix(),
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                'bytes': path.stat().st_size}


def verify_provider(accession):
    root = PROJECT / 'raw' / accession
    relative = f'ncbi_dataset/data/{accession}/protein.faa'
    protein = root / relative
    gff = protein.parent / 'genomic.gff'
    md5_path = root / 'md5sum.txt'
    receipt_path = root / 'acquisition_receipt.json'
    manifest = dict((line.split(None, 1)[1].strip(), line.split(None, 1)[0])
                    for line in md5_path.read_text().splitlines() if line.strip())
    receipt = json.loads(receipt_path.read_text())
    expected = next(row for row in receipt['files'] if row['path'] == relative)
    artifact = ref(protein)
    with protein.open('rb') as stream:
        md5 = hashlib.file_digest(stream, 'md5').hexdigest()
    if (md5 != manifest[relative] or receipt['accession'] != accession
            or any(artifact[key] != expected[key] for key in ('sha256', 'bytes'))):
        raise RuntimeError('Provider protein receipt does not match: ' + accession)
    records = list(fasta(protein))
    if not records or any(not seq or not set(seq) <= AA for _, seq in records):
        raise RuntimeError('Provider protein FASTA structure does not match: ' + accession)
    ambiguous = [{'protein_id': identifier, 'length': len(seq)}
                 for identifier, seq in records if len(seq) >= 100 and set(seq) - GAPS <= NT]
    cds_ids = set()
    with gff.open(encoding='utf-8') as stream:
        for line in stream:
            fields = line.split('\t')
            if len(fields) != 9 or fields[2] != 'CDS':
                continue
            attributes = dict(item.split('=', 1) for item in fields[8].strip().split(';') if '=' in item)
            if 'protein_id' in attributes:
                cds_ids.add(unquote(attributes['protein_id']))
    if not ambiguous or any(row['protein_id'] not in cds_ids for row in ambiguous):
        raise RuntimeError('Alphabet-ambiguous record lacks a matching CDS protein ID: ' + accession)
    artifact['reason'] = 'NCBI protein FASTA verified by provider MD5, acquisition SHA256 and CDS protein IDs'
    proof = {'accession': accession, 'provider_md5': md5, 'provider_md5_manifest': ref(md5_path),
             'acquisition_receipt': ref(receipt_path), 'genomic_gff': ref(gff), 'protein_records': len(records),
             'alphabet_ambiguous_CDS_protein_records': ambiguous}
    return artifact, proof


def verify_pilot():
    run = PROJECT / 'analysis/pilot10/runs/20261026T161747Z-cluster-resume-f688a380'
    original = run / 'all_proteins.faa'
    cluster = run / 'cluster_all_seqs.fasta'
    mapping = run / 'cluster_cluster.tsv'
    exit_path = run / 'mmseqs_easy_cluster.exit.json'
    manifest = PROJECT / 'analysis/marker_discovery/pilot10_recovered_v001/candidate_manifest.json'
    recorded_exit = json.loads(exit_path.read_text())
    if (recorded_exit['exit_code'] != 0 or recorded_exit['owned_group_empty'] is not True
            or recorded_exit['command'][1] != 'easy-cluster'
            or not recorded_exit['command'][2].endswith('/all_proteins.faa')):
        raise RuntimeError('MMseqs run lacks the exact closed protein-clustering receipt')
    expected = {row['path']: row for row in json.loads(manifest.read_text())['source_inputs']}
    for source in (original, mapping, exit_path):
        actual = ref(source)
        if expected.get(actual['path']) != actual:
            raise RuntimeError('MMseqs source does not match the marker manifest')
    reference = Counter((name, hashlib.sha256(seq).digest()) for name, seq in fasta(original))
    observed, empty = Counter(), []
    for name, seq in fasta(cluster):
        if seq:
            observed[name, hashlib.sha256(seq).digest()] += 1
        else:
            empty.append(name)
    representatives = {line.split('\t', 1)[0] for line in mapping.read_text().splitlines()}
    if reference != observed or len(empty) != len(representatives) or set(empty) != representatives:
        raise RuntimeError('MMseqs clustered records or representative sentinels differ')
    artifact = ref(cluster)
    artifact['reason'] = 'Exact protein identifier and sequence-hash multiset with verified MMseqs representative sentinels'
    proof = {'original_protein_fasta': ref(original), 'cluster_mapping': ref(mapping),
             'marker_manifest': ref(manifest), 'MMseqs_exit_receipt': ref(exit_path), 'MMseqs_exit_code': 0,
             'owned_group_empty': True, 'nonempty_protein_records': sum(observed.values()),
             'empty_cluster_representative_headers': len(empty), 'exact_ID_and_protein_SHA256_multiset_equal': True}
    return artifact, proof


def main():
    verified = [verify_provider(accession) for accession in ACCESSIONS]
    cluster, pilot = verify_pilot()
    result = {'status': 'PASS', 'proteins': [item[0] for item in verified] + [cluster],
              'provider_proof': [item[1] for item in verified], 'pilot_clustering_proof': pilot,
              'source': ref(Path(__file__).resolve()),
              'no_nucleotide_files_or_sequence_contents_printed_or_exported': True,
              'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    target = BUNDLE / 'verified_provider_proteins.json'
    if target.exists():
        raise RuntimeError('Existing protein verification receipt stays immutable')
    temporary = target.with_suffix('.json.partial')
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, target)
    print(json.dumps(ref(target)))


if __name__ == '__main__':
    main()
