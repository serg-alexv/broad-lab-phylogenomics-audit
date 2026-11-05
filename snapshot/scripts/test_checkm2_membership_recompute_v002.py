"""Three source/data-only fixtures; no saved run, science packages or pickle."""
from pathlib import Path
import hashlib
import json
import unittest
from checkm2_membership_recompute_v002 import recompute_membership_features

R = Path(__file__).resolve().parents[1]


class MembershipSourceFixtures(unittest.TestCase):
    def tiny(self):
        order = {'KO_Genes': ['K1', 'K2', 'K3'], 'KO_Pathways': ['P1', 'P2'],
                 'KO_Modules': ['M1'], 'KO_Categories': ['C1', 'C2']}
        mapping = {'Kegg_ID': {'a': 'K1', 'b': 'K1', 'c': 'K2', 'd': 'K3'},
                   'KO_Pathways': {'d': 'P2', 'c': 'P1', 'a': 'P1', 'b': 'P1'},
                   'KO_Categories': {'b': 'C1', 'a': 'C1', 'd': 'C2', 'c': 'C1'}}
        return order, mapping, {'M1': ['K1', 'K1', 'K2', 'MISSING_KO']}

    def test_actual_variable_bug_duplicates_rows_and_prefilter_denominator(self):
        order, mapping, modules = self.tiny()
        got = recompute_membership_features({'K1': 4, 'K2': 2, 'K3': 0}, order, mapping, modules)
        self.assertEqual(list(got), ['P1', 'P2', 'M1', 'C1', 'C2'])
        self.assertEqual(got, {'P1': 1.0, 'P2': 0.0, 'M1': 2.5, 'C1': 1.0, 'C2': 0.0})
        self.assertNotEqual(got['M1'], 0.75)  # Incorrect clipped-copy result.
        self.assertNotEqual(got['M1'], 10 / 3)  # Incorrect filtered denominator.

    def test_missing_known_count_is_not_filled_with_zero(self):
        order, mapping, modules = self.tiny()
        with self.assertRaises(ValueError):
            recompute_membership_features({'K1': 4, 'K2': 2}, order, mapping, modules)

    def test_full_bound_official_assets_with_synthetic_counts_only(self):
        schema_path = R / 'metadata/checkm2_feature_schema_v002.json'
        self.assertEqual(hashlib.sha256(schema_path.read_bytes()).hexdigest(),
                         '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee')
        schema = json.loads(schema_path.read_text())
        assets = {}
        for row in schema['source_files_and_assets']:
            name = Path(row['cached_path']).name
            if name in ('feature_ordering.json', 'kegg_path_category_mapping.json', 'module_definitions.json'):
                data = (R / row['cached_path']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'])
                assets[name] = json.loads(data)
        order = assets['feature_ordering.json']
        expected_names = order['KO_Pathways'] + order['KO_Modules'] + order['KO_Categories']
        got = recompute_membership_features(dict.fromkeys(order['KO_Genes'], 2), order,
                assets['kegg_path_category_mapping.json'], assets['module_definitions.json'])
        self.assertEqual(len(got), 1220)
        self.assertEqual(list(got), expected_names)
        self.assertEqual((len(order['KO_Pathways']), len(order['KO_Modules']), len(order['KO_Categories'])),
                         (416, 757, 47))
        self.assertTrue(all(got[name] == 1 for name in order['KO_Pathways'] + order['KO_Categories']))
        self.assertEqual(got['M00001'], 2.0)


if __name__ == '__main__':
    unittest.main()
