"""Small synthetic metadata-only tests; no stock package, runtime or sequence inputs."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest

SOURCE = Path(__file__).with_name('checkm1_pilot_marker_arithmetic_v001.py')
spec = importlib.util.spec_from_file_location('independent_pilot_arithmetic', SOURCE)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class Arithmetic(unittest.TestCase):
    def test_weighting_and_monotonicity(self):
        groups = [{'a', 'b'}, {'c'}]
        self.assertEqual(qa.weighted(groups, dict(a=1, b=1, c=1))[:2], (100, 0))
        self.assertEqual(qa.weighted(groups, dict(a=1, b=0, c=1))[:2], (75, 0))
        self.assertEqual(qa.weighted(groups, dict(a=1, b=3, c=1))[:2], (100, 50))
        self.assertEqual(qa.weighted(groups, dict(a=1, b=1, c=5))[:2], (100, 200))

    def test_multiple_retained_intervals_are_not_deduplicated(self):
        counts = qa.counts_from_filtered_stats({'gene': {'a': [[1, 3], [5, 7]], 'b': [[1, 4]]}}, {'a', 'b'})
        self.assertEqual(counts, {'a': 2, 'b': 1})
        self.assertEqual(qa.weighted([{'a', 'b'}], counts)[:2], (100, 50))

    def test_invalid_marker_or_interval_veto(self):
        for stats in ({'gene': {'unknown': [[1, 2]]}}, {'gene': {'a': [[9, 2]]}}, {'gene': {'a': []}}):
            with self.assertRaises(ValueError):
                qa.counts_from_filtered_stats(stats, {'a'})

    def test_complete_synthetic18_and_commit_tamper_veto(self):
        saved_root, saved_pilot, saved_audit = qa.ROOT, qa.PILOT, qa.MODEL_AUDIT
        work = saved_root / 'work'
        with tempfile.TemporaryDirectory(prefix='checkm1_arithmetic_toy_', dir=work) as directory:
            qa.ROOT = Path(directory)
            try:
                def store(relative, payload, as_json=True):
                    candidate = qa.ROOT / relative
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    candidate.write_text(json.dumps(payload) if as_json else payload)
                    data = candidate.read_bytes()
                    return {'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                names = ['toy' + str(i) for i in range(18)]
                markers = ['PF' + str(i).zfill(5) + '.1' for i in range(335)]
                groups = [set(markers[i:i + 2]) for i in range(0, 304, 2)] + [{m} for m in markers[304:]]
                pilot = {'ordered_accessions': names, 'rows': [{'accession': n, 'family': 'ToyFamily', 'CheckM2_diagnostic_comparator': None, 'source_masks': {}, 'source_holds_preserved': [], 'source_pending_reasons': []} for n in names]}
                qa.PILOT = store('pilot.json', pilot)
                marker = store('marker.ms', '# [Taxon Marker File]\nLactobacillales\t1\t3\tLactobacillales\t490\t' + repr(groups) + '\n', False)
                qa.MODEL_AUDIT = store('model_audit.json', {'marker_file': marker})
                genes = {n: {'gene' + str(i): {m: [[1, 5]]} for i, m in enumerate(markers)} for n in names}
                extended = {n: {'marker lineage': 'Lactobacillales', '# genomes': 490, '# markers': 335, '# marker sets': 183, 'Completeness': 100, 'Contamination': 0, **{k: 335 if k == '1' else 0 for k in ['0', '1', '2', '3', '4', '5+']}, **{'GCN' + k: [m.split('.')[0] for m in markers] if k == '1' else [] for k in ['0', '1', '2', '3', '4', '5+']}} for n in names}
                artifacts = []
                for unit in ('unit_analyze', 'unit_qa'):
                    artifacts.append(store('batch/' + unit + '/execution.json', {'actual_exit_code': 0, 'group_closed': True, 'remaining_owned_identities': [], 'actual_child_waited_and_reaped': True}))
                for relative, data in [('checkm_output/storage/marker_gene_stats.tsv', genes), ('checkm_output/storage/bin_stats_ext.tsv', extended)]:
                    artifacts.append(store('batch/' + relative, ''.join(n + '\t' + repr(data[n]) + '\n' for n in names), False))
                report = '\t'.join(qa.HEADER) + '\n' + ''.join('\t'.join([n, 'Lactobacillales (3)', '490', '335', '183', '0', '335', '0', '0', '0', '0', '100.00', '0.00', '0.00']) + '\n' for n in names)
                artifacts.append(store('batch/quality.tsv', report, False))
                commit = store('batch/COMMITTED.json', {'status': 'CHECKM1_BATCH_MEASURED_VALIDATED', 'accessions': names, 'rows': [{'accession': n} for n in names], 'marker_file': marker, 'artifacts': artifacts})
                result = qa.validate(commit)
                self.assertEqual(result['completed_method_measurements'], 18)
                self.assertFalse(result['whole_owner_closure_proved_by_this_file_only_check'])
                (qa.ROOT / 'batch/quality.tsv').write_text(report + 'tampered')
                with self.assertRaises(ValueError):
                    qa.validate(commit)
            finally:
                qa.ROOT, qa.PILOT, qa.MODEL_AUDIT = saved_root, saved_pilot, saved_audit


if __name__ == '__main__':
    unittest.main()
