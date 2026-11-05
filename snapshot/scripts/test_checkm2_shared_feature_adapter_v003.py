"""Pure AST-extracted preflight tests; no adapter/science import or real data I/O."""
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import ast
import copy
import unittest

R = Path(__file__).resolve().parents[1]
SOURCE = R / 'scripts/checkm2_campaign_index8_feature_validator_v003.py'
ACC = 'GCF_000000001.1'
SCHEMA = '90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee'


class ToyPath(PurePosixPath):
    def read_text(self):
        return '>geneA\nAA\n'


def reference(name):
    return {'path': name, 'sha256': 'a' * 64, 'bytes': 2}


def unit():
    return {'status': 'UNIT_EXIT0_GROUP_CLOSED', 'exit_code': 0,
            'owned_group_empty': True, 'remaining_owned_processes': []}


def fixture():
    keys = ('raw_pickle', 'selected_faa', 'annotation_receipt', 'annotation_unit_execution',
            'annotation_commit', 'quality_report', 'quality_unit_execution',
            'shared_search_commit', 'global_search_execution',
            'global_search_validation_execution', 'split_commit', 'raw_shard')
    artifacts = {k: reference(k) for k in keys}
    plan = {'scientific_recipe': reference('recipe'), 'feature_schema': reference('schema')}
    item = {'accession': ACC, 'source_masks': {'production_acceptance': False}}
    request = {'request_schema': 'TREE2_CAMPAIGN_SHARED_ROW_FEATURE_REQUEST_V003',
               'accession': ACC, 'scientific_recipe': plan['scientific_recipe'],
               'schema': plan['feature_schema'], 'input_plan': reference('plan'),
               'source_manifest': reference('sources'), 'artifacts': artifacts,
               'resume_output': 'resume'}
    objects = {k: unit() for k in ('annotation_unit_execution', 'quality_unit_execution',
                                  'global_search_execution', 'global_search_validation_execution')}
    objects['annotation_commit'] = {
        'status': 'P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE',
        'accession': ACC, 'selected_faa': artifacts['selected_faa'],
        'annotation_receipt': artifacts['annotation_receipt'],
        'unit_execution': artifacts['annotation_unit_execution'],
        'input_plan_sha256': request['input_plan']['sha256'],
        'source_manifest_sha256': request['source_manifest']['sha256'],
        'manifest': reference('annotation_manifest')}
    objects['annotation_manifest'] = {'files': []}
    objects['shared_search_commit'] = {
        'status': 'GLOBAL_SHARED_SEARCH_SPLIT_VALIDATED_PENDING_CONTEXT_CLOSURE',
        'binary_execution': artifacts['global_search_execution'],
        'validation_execution': artifacts['global_search_validation_execution'],
        'split_commit': artifacts['split_commit']}
    objects['schema'] = {'source_files_and_assets': []}
    state = {'copy': reference('resume/diamond_output/DIAMOND_RESULTS.tsv'),
             'actual': {**artifacts['raw_shard'], 'rows': 1, 'query_genomes': [ACC]},
             'shard': {'accession': ACC, 'artifact': copy.deepcopy(artifacts['raw_shard']),
                       'search_binding_id': 'one-global-search'}}
    closed = lambda u: (u.get('status') == 'UNIT_EXIT0_GROUP_CLOSED'
                        and type(u.get('exit_code')) is int and u['exit_code'] == 0
                        and u.get('owned_group_empty') is True
                        and u.get('remaining_owned_processes') == [])
    bind = lambda r: ToyPath('/toy') / r['path']
    common = SimpleNamespace(
        request_gate=lambda r: (plan, {'input': item}, {'held': True}),
        unit_closed=closed, verify_manifest=lambda *args: None,
        global_commit_gate=lambda *args: state['shard'],
        path=lambda p: ToyPath('/toy') / p, row=lambda p: state['copy'])
    validator = SimpleNamespace(bind=bind, read=lambda p: objects[str(p.relative_to('/toy'))],
                                sha=lambda p: SCHEMA, inside=lambda p: ToyPath('/toy') / p)
    helper = SimpleNamespace(AA=set('A'), parse_fasta=lambda *args: [{'id': 'geneA'}])
    fresh = SimpleNamespace(validate_diamond=lambda *args: state['actual'],
                            exact_faa_inventory=lambda *args: None,
                            exact_diamond_inventory=lambda *args: None)
    node = next(n for n in ast.parse(SOURCE.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'preflight')
    namespace = {'c': common, 'v': validator, 'h': helper, 'fresh': fresh,
                 'SCHEMA_SHA': SCHEMA}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['preflight'], request, objects, state


class AdapterAssociationTests(unittest.TestCase):
    def test_valid_shared_parent_preserves_own_mask(self):
        preflight, request, _, _ = fixture()
        self.assertEqual(preflight(request)[2]['source_masks'], {'production_acceptance': False})

    def test_wrong_own_shard_rejected(self):
        f, r, _, s = fixture(); s['shard']['accession'] = 'GCF_000000002.1'
        with self.assertRaisesRegex(RuntimeError, 'association'): f(r)

    def test_bool_is_not_observed_binary_zero(self):
        f, r, o, _ = fixture(); o['global_search_execution']['exit_code'] = False
        with self.assertRaisesRegex(RuntimeError, 'typed'): f(r)

    def test_saved_validation_failure_is_not_a_pass(self):
        f, r, o, _ = fixture(); o['global_search_validation_execution']['exit_code'] = -15
        with self.assertRaisesRegex(RuntimeError, 'typed'): f(r)

    def test_other_faa_annotation_rejected(self):
        f, r, o, _ = fixture(); o['annotation_commit']['selected_faa'] = reference('otherFAA')
        with self.assertRaisesRegex(RuntimeError, 'annotation/FAA'): f(r)

    def test_copy_hash_must_equal_original_shard(self):
        f, r, _, s = fixture(); s['copy']['sha256'] = 'b' * 64
        with self.assertRaisesRegex(RuntimeError, 'copy differs'): f(r)

    def test_zero_hit_is_explicit_hold(self):
        f, r, _, s = fixture(); s['actual'].update(rows=0, query_genomes=[])
        with self.assertRaisesRegex(RuntimeError, 'no reported hits.*never a biological negative'): f(r)

    def test_own_request_name_mismatch_rejected(self):
        f, r, _, _ = fixture(); r['accession'] = 'GCF_000000002.1'
        with self.assertRaisesRegex(RuntimeError, 'own input'): f(r)

    def test_numerical_main_is_exact_previous_ast(self):
        def main(path):
            return next(n for n in ast.parse(path.read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'main')
        self.assertEqual(ast.dump(main(SOURCE), include_attributes=False),
                         ast.dump(main(R / 'scripts/checkm2_campaign_index8_feature_validator_v002.py'),
                                  include_attributes=False))


if __name__ == '__main__':
    unittest.main()
