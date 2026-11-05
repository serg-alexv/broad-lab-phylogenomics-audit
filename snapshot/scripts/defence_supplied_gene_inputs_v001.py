"""Lossless supplied-gene adapters; coordinates must join original verified GFF rows.

No gene prediction, defence search, threshold changes or biological classification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inside(root, value):
    path = Path(value)
    path = path if path.is_absolute() else root / path
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path leaves the isolated project')
    return path


def bind(root, ref):
    path = inside(root, ref['path'])
    data = path.read_bytes()
    if len(data) != ref['bytes'] or digest(data) != ref['sha256']:
        raise ValueError('Bound input changed: ' + str(path))
    return path, data


def fasta_records(data):
    records = []
    seen = set()
    title, chunks = None, []
    for line in data.decode('ascii').splitlines() + ['>']:
        if line.startswith('>'):
            if title is not None:
                if not title.strip():
                    raise ValueError('Empty canonical protein header')
                identifier = title.split()[0]
                sequence = ''.join(chunks)
                if not sequence or identifier in seen or re.search(r'[^A-Za-z*]', sequence):
                    raise ValueError('Duplicate, empty or malformed canonical protein')
                seen.add(identifier)
                records.append((identifier, title, sequence))
            title, chunks = line[1:], []
        elif line:
            if title is None:
                raise ValueError('FASTA sequence precedes its header')
            chunks.append(line)
    return records


def attributes(text):
    values = {}
    for piece in text.split(';'):
        if not piece:
            continue
        key, value = piece.split('=', 1)
        if not key or key in values:
            raise ValueError('Duplicate or missing GFF attribute name')
        values[key] = value
    return values


def transform(accession, faa_bytes, gff_bytes, coordinate_rows):
    """Pure metadata/sequence rearrangement; all emitted coordinates remain source values."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', accession):
        raise ValueError('Unsafe accession')
    proteins = fasta_records(faa_bytes)
    maps = {}
    original_keys = {}
    for q in coordinate_rows:
        identifier = q['protein_id']
        if identifier in maps or q['accession'] != accession:
            raise ValueError('Duplicate coordinate row or wrong accession')
        if not re.fullmatch(r'[A-Za-z0-9_.|:-]+', identifier):
            raise ValueError('Canonical ID needs explicit reversible GFF escaping')
        key = (q['contig'], q['prodigal_gene_id'])
        if key in original_keys:
            raise ValueError('Ambiguous original GFF coordinate join')
        original_keys[key] = identifier
        maps[identifier] = q
    if {q[0] for q in proteins} != set(maps):
        raise ValueError('Canonical FAA and coordinate-map IDs differ')
    source_rows, source_order, original_comments = {}, [], []
    for line_number, line in enumerate(gff_bytes.decode('utf-8').splitlines(), 1):
        if not line or line.startswith('#'):
            original_comments.append(line)
            continue
        fields = line.split('\t')
        if len(fields) != 9 or fields[2] != 'CDS':
            raise ValueError('Unexpected non-CDS or malformed original annotation row')
        attr = attributes(fields[8])
        key = (fields[0], attr.get('ID'))
        if key not in original_keys:
            raise ValueError('Original GFF has an unmapped CDS')
        identifier = original_keys[key]
        q = maps[identifier]
        if identifier in source_rows:
            raise ValueError('Original GFF CDS maps more than once')
        if (fields[0], int(fields[3]), int(fields[4]), fields[6]) != (q['contig'], q['start'], q['end'], q['strand']):
            raise ValueError('Coordinate map differs from the original GFF fields')
        if attr != q['gff_attributes'] or attr.get('ID') != q['prodigal_gene_id']:
            raise ValueError('Original GFF attributes differ from verified coordinate map')
        if not 1 <= q['start'] <= q['end'] or q['strand'] not in ('+', '-') or fields[7] not in ('0', '1', '2'):
            raise ValueError('Invalid original CDS coordinate domain')
        source_rows[identifier] = (fields, line_number, digest(line.encode('utf-8')))
        source_order.append(identifier)
    if set(source_rows) != set(maps):
        raise ValueError('Not all mapped proteins have an original GFF row')
    by_contig = {}
    for identifier in source_order:
        by_contig.setdefault(maps[identifier]['contig'], []).append(identifier)
    contig_order = list(by_contig)
    replicons = {contig: accession + '_ctg' + str(i + 1).zfill(6) for i, contig in enumerate(contig_order)}
    # Stock MacSyFinder2.1.4 retains `rank` from an earlier multigene group when
    # a later group contains one gene. Singleton blocks first avoid that bug
    # without changing stock code, gene content or within-contig order.
    block_order = sorted(contig_order, key=lambda c: (len(by_contig[c]) != 1, contig_order.index(c)))
    original = {p[0]: (i, p[1], p[2]) for i, p in enumerate(proteins)}
    mapping, output_faa = [], []
    for contig in block_order:
        ordered = sorted(by_contig[contig], key=lambda identifier: (maps[identifier]['start'], maps[identifier]['end'], source_rows[identifier][1]))
        for rank, identifier in enumerate(ordered, 1):
            q = maps[identifier]
            input_index, title, sequence = original[identifier]
            if len(sequence) != q['aa_length']:
                raise ValueError('Canonical sequence length differs from verified coordinate map')
            gembase_id = replicons[contig] + '_' + str(rank).zfill(6)
            output_faa.append('>' + gembase_id + '\n' + sequence + '\n')
            mapping.append({'canonical_id': identifier, 'canonical_title': title,
                            'input_faa_index': input_index, 'contig': contig,
                            'start': q['start'], 'end': q['end'], 'strand': q['strand'],
                            'original_Prodigal_ID': q['prodigal_gene_id'],
                            'source_GFF_line_number': source_rows[identifier][1],
                            'source_GFF_line_sha256': source_rows[identifier][2],
                            'AA_length': len(sequence), 'AA_sha256': digest(sequence.encode('ascii')),
                            'DF_ID': gembase_id, 'DF_replicon': replicons[contig],
                            'DF_contig_rank': rank, 'DF_global_file_rank': len(mapping) + 1})
    gff_lines = list(original_comments)
    for identifier in source_order:
        fields = list(source_rows[identifier][0])
        attr = attributes(fields[8])
        attr['ID'] = identifier
        attr['protein_id'] = identifier
        fields[8] = ';'.join(k + '=' + v for k, v in attr.items()) + ';'
        gff_lines.append('\t'.join(fields))
    return {'DF_gembase_FAA': ''.join(output_faa).encode('ascii'),
            'PADLOC_canonical_FAA': faa_bytes,
            'PADLOC_canonical_GFF': ('\n'.join(gff_lines) + '\n').encode('utf-8'),
            'mapping': mapping, 'contig_order': block_order,
            'macsyfinder_conf': b'[base]\nreplicon_topology = linear\n',
            'all_source_coordinates_preserved': True,
            'all_proteins_preserved_exact_AA_sequences': True,
            'singletons_first_stock_gembase_boundary_workaround': True}


def closed_context(root, closure_ref):
    _, payload = bind(root, closure_ref)
    closure = json.loads(payload)
    if (closure.get('status') != 'CLOSED_VALIDATED_PROVISIONAL_PAIRED_ANNOTATION919'
            or closure.get('actual_native_exit_code') != 0 or closure.get('actual_wsl_exit_code') != 0
            or closure.get('all_1827_captured_identity_entries_and_914_owned_groups_closed') is not True
            or closure.get('annotation_OS_flock_released') is not True):
        raise ValueError('Closed accepted annotation authority required')
    _, payload = bind(root, closure['verified_rows'])
    rows = json.loads(payload)['rows']
    index = {q['accession']: q for q in rows}
    if len(index) != len(rows) or len(rows) != 919:
        raise ValueError('Closed annotation row inventory is incomplete or ambiguous')
    return index


def atomic_bytes(path, data):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def prepare(root, request, output, accepted_rows=None):
    root = root.resolve()
    output = inside(root, output)
    accepted = accepted_rows if accepted_rows is not None else closed_context(root, request['closed_annotation_acceptance'])
    accession = request['accession']
    row = accepted[accession]
    if (row['commit'] != request['uniform_annotation_commit'] or row['proteins'] != request['canonical_FAA']
            or row['coordinates'] != request['protein_coordinate_map']):
        raise ValueError('Supplied inputs differ from closed accepted annotation row')
    _, commit_data = bind(root, request['uniform_annotation_commit'])
    commit = json.loads(commit_data)
    if commit.get('status') != 'COMMITTED_PROVISIONAL_PAIRED_COORDINATE_ANNOTATION' or commit.get('accession') != accession:
        raise ValueError('Wrong annotation commit')
    for name, key in [('proteins.faa', 'canonical_FAA'), ('prodigal.gff', 'Prodigal_GFF'), ('protein_coordinate_map.json', 'protein_coordinate_map')]:
        if commit['artifacts'][name] != request[key]:
            raise ValueError('Input reference differs from original committed artifact')
    _, faa = bind(root, request['canonical_FAA'])
    _, gff = bind(root, request['Prodigal_GFF'])
    _, coordinates = bind(root, request['protein_coordinate_map'])
    result = transform(accession, faa, gff, json.loads(coordinates))
    if len(result['mapping']) != row['protein_count'] or len(result['mapping']) != commit['protein_count']:
        raise ValueError('Prepared protein count differs from closed annotation')
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, payload in [('defensefinder_gembase.faa', result['DF_gembase_FAA']),
                          ('padloc_canonical.faa', result['PADLOC_canonical_FAA']),
                          ('padloc_canonical.gff', result['PADLOC_canonical_GFF']),
                          ('macsyfinder.conf', result['macsyfinder_conf']),
                          ('protein_identity_map.json', (json.dumps(result['mapping'], indent=2) + '\n').encode())]:
        path = output / name
        atomic_bytes(path, payload)
        files[name] = {'path': path.relative_to(root).as_posix(), 'sha256': digest(payload), 'bytes': len(payload)}
    receipt = {'status': 'DEFENCE_SUPPLIED_GENE_INPUTS_COMMITTED_NOT_SEARCHED',
               'accession': accession, 'input_request': request, 'files': files,
               'protein_count': len(result['mapping']), 'contigs': len(result['contig_order']),
               'sequences_lossless': True, 'coordinates_only_from_original_verified_GFF': True,
               'default_linear_topology': True, 'singleton_contig_blocks_first': True,
               'DF_required_db_type': 'gembase', 'PADLOC_fix_Prodigal_flag': 'OMIT; canonical IDs are explicitly supplied',
               'original_annotation_source_masks': row.get('source_metadata', {}).get('source_masks'),
               'additional_caller_source_QC_taxonomy_masks': request.get('source_masks'),
               'defence_status': 'UNKNOWN_UNSEARCHED',
               'source_taxonomy_or_final_panel_acceptance': False}
    atomic_bytes(output / 'COMMITTED.json', (json.dumps(receipt, indent=2) + '\n').encode())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    request = inside(root, args.request).read_bytes()
    if digest(request) != args.request_sha256:
        raise ValueError('Exact supplied-input request SHA256 required')
    prepare(root, json.loads(request), args.output)


if __name__ == '__main__':
    main()
