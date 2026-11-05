"""Pure accession/report/hold fixtures; no actual data or scientific imports."""
import copy
import sys
import unittest
import checkm2_benchmark10_feature_validator_v002 as c


class ExactTenJoinFixtures(unittest.TestCase):
    def names(self):
        return ['GCF_' + str(index).zfill(9) + '.1' for index in range(1, 11)]

    def report(self):
        return [{'Name': name, 'Completeness': str(70 + index), 'Contamination': '0.25',
                 'Completeness_Model_Used': 'Synthetic model', 'Additional_Notes': ''}
                for index, name in enumerate(self.names())]

    def source(self, holds=True):
        return {'accession': self.names()[0], 'species': 'Synthetic species', 'genus': 'Synthetic',
                'family': 'Synthetic family', 'role': 'ANCILLARY_METADATA_LOW_COMPLETENESS_REVIEW',
                'metadata_qc': 'EXCLUDED', 'selection_status': 'QC_REVIEW_ONLY',
                'source_disposition': 'HOLD',
                'source_holds_preserved': ['HOLD_EXISTING_METADATA_QC_EXCLUSION'] if holds else [],
                'source_metadata_checkm': {'completeness': 85.0, 'contamination': 8.0,
                    'version': 'synthetic', 'role': 'CONTEXT_ONLY_NOT_TRUTH_OR_CALIBRATION'},
                'source_taxonomy_gates': 'REQUIRED_INDEPENDENTLY_OF_ANY_QC_SCORE'}

    def test_multirow_feature_and_report_order_join_by_name_not_position(self):
        expected = self.names()
        positions = c.exact_names(list(reversed(expected)), expected, 'synthetic features')
        joined = c.join_report_rows(c.REPORT_COLUMNS, list(reversed(self.report())), expected)
        self.assertEqual(positions[expected[0]], 9)
        self.assertEqual(joined[expected[0]]['Completeness'], 70.0)
        self.assertEqual(joined[expected[-1]]['Completeness'], 79.0)

    def test_missing_duplicate_or_eleventh_name_is_not_filled(self):
        expected = self.names()
        for names in (expected[:-1], expected[:-1] + [expected[0]], expected + ['EXTRA']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                c.exact_names(names, expected, 'synthetic inventory')

    def test_unknown_or_extra_report_cells_cannot_become_zero_scores(self):
        for value in (None, 'NaN'):
            rows = self.report(); rows[0]['Completeness'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.join_report_rows(c.REPORT_COLUMNS, rows, self.names())
        rows = self.report(); rows[0][None] = ['unexpected sixth cell']
        with self.assertRaises(ValueError):
            c.join_report_rows(c.REPORT_COLUMNS, rows, self.names())

    def test_ideal_numeric_score_preserves_holds_context_and_no_panel_pass(self):
        source = self.source(); original = copy.deepcopy(source)
        report = {'raw_report': {**self.report()[0], 'Completeness': '100', 'Contamination': '0'},
                  'Completeness': 100.0, 'Contamination': 0.0}
        result = c.measured_row_with_original_holds(source, report)
        self.assertTrue(result['source_hold_active'])
        self.assertEqual(result['source_holds_preserved'], source['source_holds_preserved'])
        self.assertEqual(result['original_source_context']['source_metadata_checkm'], source['source_metadata_checkm'])
        self.assertEqual(result['production_acceptance'], 'NOT_GRANTED')
        self.assertNotIn('panel_pass', result)
        result['source_holds_preserved'].clear()
        self.assertEqual(source, original)
        self.assertEqual(c.measured_row_with_original_holds(self.source(False), report)['production_acceptance'], 'NOT_GRANTED')

    def test_boundary_phase_cannot_call_validator_or_import_scientific_runtime(self):
        with self.assertRaises(RuntimeError):
            c.validation_phase({'phase': 'BOUNDARY_AFTER_FIRST_ANNOTATION'})
        c.validation_phase({'phase': 'CONTINUE'})
        c.validation_phase({'phase': 'VALIDATE_COMMITTED_BATCH'})
        self.assertNotIn('numpy', sys.modules)
        self.assertNotIn('pandas', sys.modules)


if __name__ == '__main__':
    unittest.main()
