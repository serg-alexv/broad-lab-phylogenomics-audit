"""Pure synthetic receipt fixtures; no file, variant, FAA, pickle or model I/O."""
import copy
import unittest
import checkm2_protein_invariance_v002 as c


class CorrectedFeatureReceiptFixtures(unittest.TestCase):
    def result(self, control=False):
        return {'status': ('PROTEIN_CONTROL_FEATURES_V002_PASS_PENDING_CLOSURE' if control else
                'PRESERVED_04R1_FEATURES_AND_MEMBERSHIP_V002_PASS_PENDING_CLOSURE'),
                'accession': 'GCF_013267415.1', 'raw_pickle_sha256': 'a' * 64,
                'schema_v002_sha256': c.FEATURE_SCHEMA_SHA, 'source_FAA_sha256': 'b' * 64,
                'ordered_dataframe_columns_sha256': 'c' * 64, 'dataframe_shape': [1, 21242],
                'actual_ML_cast_dtype': 'float64', 'canonical_float64_le_row_sha256': 'd' * 64,
                'finite_domain_features': 21241, 'exact_FAA_metadata_features': 22,
                'independently_recomputed_membership_features': 1220, 'membership_mismatches': 0}

    def chain(self, control=False):
        value = '2' if control else '1'
        return {'status': 'HASH_VERIFIED_VALIDATION_AND_NATIVE_CLOSED',
                'role': 'FORMAT_CONTROL' if control else 'POSTHOC_BASELINE',
                'validation_sha256': value * 64, 'manifest_sha256': value * 64,
                'execution_sha256': value * 64, 'native_and_lease_closure_sha256': value * 64,
                'root_authority_sha256': value * 64, 'owned_group_empty': True,
                'native_exit_observed': True, 'native_exit_code': 0,
                'ordinary_runtime_closed': True, 'image_unchanged': True,
                'common_leases_released': True, 'original_artifacts_unchanged': True}

    def test_pending_target_requires_current_closure_and_root_authority(self):
        result = self.result()
        with self.assertRaises(c.NotEvaluable):
            c.feature_evidence_from_closed_validation(result, {})
        for key in ('native_exit_observed', 'common_leases_released', 'original_artifacts_unchanged'):
            chain = self.chain(); chain[key] = False
            with self.subTest(key=key), self.assertRaises(c.NotEvaluable):
                c.feature_evidence_from_closed_validation(result, chain)
        chain = self.chain(); chain['root_authority_sha256'] = None
        with self.assertRaises(c.NotEvaluable):
            c.feature_evidence_from_closed_validation(result, chain)

    def test_full_corrected_feature_hash_is_required_but_pickle_bytes_may_differ(self):
        baseline = c.feature_evidence_from_closed_validation(self.result(), self.chain())
        control = c.feature_evidence_from_closed_validation(self.result(True), self.chain(True))
        control['raw_pickle_sha256'] = 'e' * 64
        self.assertTrue(c.compare_feature_receipts(baseline, control)['equal'])
        control['canonical_float64_le_row_sha256'] = 'f' * 64
        self.assertFalse(c.compare_feature_receipts(baseline, control)['equal'])

    def test_old_schema_missing_evidence_and_baseline_substitution_are_not_evaluable(self):
        with self.assertRaises(c.NotEvaluable):
            c.compare_feature_receipts({}, {})
        old = self.result(); old['schema_v002_sha256'] = '2be7bda6589a445a8b70023d9cf84ffadc76a380db112b34a70ce0094fc53adb'
        with self.assertRaises(c.NotEvaluable):
            c.feature_evidence_from_closed_validation(old, self.chain())
        baseline = c.feature_evidence_from_closed_validation(self.result(), self.chain())
        with self.assertRaises(c.NotEvaluable):
            c.compare_feature_receipts(baseline, copy.deepcopy(baseline))

    def test_diamond_counts_and_duplicate_multiset_are_required(self):
        reference = {'rows': 3, 'unique_rows': 2, 'multiset_sha256': 'a' * 64}
        self.assertTrue(c.compare_diamond_receipts(reference, dict(reference))['equal'])
        self.assertFalse(c.compare_diamond_receipts(reference, {**reference, 'rows': 2})['equal'])
        with self.assertRaises(c.NotEvaluable):
            c.compare_diamond_receipts({}, {})


if __name__ == '__main__':
    unittest.main()
