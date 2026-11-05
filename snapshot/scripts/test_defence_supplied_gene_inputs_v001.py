"""Synthetic metadata/stock-parser tests; no original genome or defence search."""
from pathlib import Path
from argparse import Namespace
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))
from defence_supplied_gene_inputs_v001 import transform, fasta_records, attributes, closed_context


def fixture():
    # Deliberately unsorted source FAA; a two-gene contig precedes a singleton.
    # Original contig names ending i/b must not collide through stock rstrip('ib').
    records = [('GCF_TEST.1|gene000002', 'c_i', 101, 124, '-', '1_2', 'MCCCCCCC'),
               ('GCF_TEST.1|gene000001', 'c_i', 5, 28, '+', '1_1', 'MAAAAAAA'),
               ('GCF_TEST.1|gene000003', 'c_b', 8, 31, '+', '2_1', 'MGGGGGGG')]
    faa = ''.join('>' + q[0] + '\n' + q[6] + '\n' for q in records).encode()
    rows, gff = [], ['##gff-version 3', '# SYNTHETIC METADATA ONLY']
    for identifier, contig, start, end, strand, original_id, sequence in records:
        attrs = {'ID': original_id, 'partial': '00', 'note': 'original_value'}
        rows.append({'protein_id': identifier, 'accession': 'GCF_TEST.1', 'contig': contig,
                     'start': start, 'end': end, 'strand': strand, 'prodigal_gene_id': original_id,
                     'gff_attributes': attrs, 'aa_length': len(sequence)})
        gff.append('\t'.join([contig, 'SYNTHETIC_ANNOTATION', 'CDS', str(start), str(end), '.', strand, '0',
                              ';'.join(k + '=' + v for k, v in attrs.items()) + ';']))
    return faa, ('\n'.join(gff) + '\n').encode(), rows


class Adapter(unittest.TestCase):
    def test_lossless_sequences_and_original_fields(self):
        faa, gff, rows = fixture()
        before = hashlib.sha256(faa + gff + json.dumps(rows).encode()).hexdigest()
        result = transform('GCF_TEST.1', faa, gff, rows)
        self.assertEqual(result['PADLOC_canonical_FAA'], faa)
        original = {x[0]: x[2] for x in fasta_records(faa)}
        renamed = {x[0]: x[2] for x in fasta_records(result['DF_gembase_FAA'])}
        self.assertEqual(len(result['mapping']), len(rows))
        for row in result['mapping']:
            self.assertEqual(original[row['canonical_id']], renamed[row['DF_ID']])
            self.assertEqual(row['DF_ID'].rsplit('_', 1)[0], row['DF_replicon'])
        derived = [q.split('\t') for q in result['PADLOC_canonical_GFF'].decode().splitlines() if q and not q.startswith('#')]
        source = [q.split('\t') for q in gff.decode().splitlines() if q and not q.startswith('#')]
        for old, new in zip(source, derived):
            self.assertEqual(old[:8], new[:8])
            old_attrs, new_attrs = attributes(old[8]), attributes(new[8])
            for k in old_attrs:
                if k != 'ID':
                    self.assertEqual(old_attrs[k], new_attrs[k])
            self.assertEqual(new_attrs['ID'], new_attrs['protein_id'])
        self.assertEqual(before, hashlib.sha256(faa + gff + json.dumps(rows).encode()).hexdigest())

    def test_contig_blocks_singletons_first_and_coordinate_order(self):
        result = transform('GCF_TEST.1', *fixture())
        self.assertEqual([q['contig'] for q in result['mapping']], ['c_b', 'c_i', 'c_i'])
        self.assertEqual([q['start'] for q in result['mapping']], [8, 5, 101])
        self.assertEqual([q['DF_contig_rank'] for q in result['mapping']], [1, 1, 2])
        self.assertEqual(len({q['DF_replicon'] for q in result['mapping']}), 2)

    def test_original_coordinate_tamper_veto(self):
        faa, gff, rows = fixture()
        rows[0]['start'] += 1
        with self.assertRaisesRegex(ValueError, 'Coordinate map differs'):
            transform('GCF_TEST.1', faa, gff, rows)

    def test_missing_duplicate_and_length_veto(self):
        faa, gff, rows = fixture()
        with self.assertRaises(ValueError):
            transform('GCF_TEST.1', faa + faa, gff, rows)
        with self.assertRaises(ValueError):
            transform('GCF_TEST.1', faa, gff, rows[:-1])
        rows[0]['aa_length'] += 1
        with self.assertRaisesRegex(ValueError, 'sequence length'):
            transform('GCF_TEST.1', faa, gff, rows)

    def test_original_attribute_tamper_veto(self):
        faa, gff, rows = fixture()
        rows[0]['gff_attributes']['note'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'attributes differ'):
            transform('GCF_TEST.1', faa, gff, rows)

    def test_stock_gembase_parser_ranges_and_linear_config(self):
        from macsypy.database import RepliconDB
        from macsypy.config import Config, MacsyDefaults
        result = transform('GCF_TEST.1', *fixture())
        db = RepliconDB.__new__(RepliconDB)
        db._idx = [(q['DF_ID'], q['AA_length'], q['DF_global_file_rank']) for q in result['mapping']]
        db._DB = {}
        db._fill_gembase_min_max({}, 'linear')
        for row in result['mapping']:
            matching = [q for q in result['mapping'] if q['DF_replicon'] == row['DF_replicon']]
            actual = db._DB[row['DF_replicon']]
            self.assertEqual(actual.min, min(q['DF_global_file_rank'] for q in matching))
            self.assertEqual(actual.max, max(q['DF_global_file_rank'] for q in matching))
            self.assertEqual(actual.topology, 'linear')
        # Metadata-only integration: exact stock config reads supported project CWD file.
        folder = R / 'metadata/defence_input_adapter_20261029/fixture_work'
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temp:
            previous = Path.cwd()
            try:
                os.chdir(temp)
                Path('macsyfinder.conf').write_bytes(result['macsyfinder_conf'])
                cfg = Config(MacsyDefaults(), Namespace())
                self.assertEqual(cfg.replicon_topology(), 'linear')
            finally:
                os.chdir(previous)

    def test_demonstrate_stock_late_singleton_bug_without_mutating_stock(self):
        from macsypy.database import RepliconDB
        db = RepliconDB.__new__(RepliconDB)
        db._idx = [('rep1_000001', 8, 1), ('rep1_000002', 8, 2), ('rep2_000001', 8, 3)]
        db._DB = {}
        db._fill_gembase_min_max({}, 'linear')
        self.assertEqual((db._DB['rep2'].min, db._DB['rep2'].max), (3, 2))
        # Production adapter singleton-first ranges are separately asserted above.


if __name__ == '__main__':
    unittest.main()
