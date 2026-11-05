"""Small synthetic request/closure fixtures; no data, pandas or NumPy import."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import checkm2_control_feature_validator_v002 as c


class GenericControlPreflightFixtures(unittest.TestCase):
    def test_request_checksum_is_verified_before_parsing_or_imports(self):
        folder = c.R / 'work/checkm2_control_feature_fixtures'
        folder.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            path = Path(temporary) / 'synthetic_request.json'
            path.write_text('not a pickle and not JSON')
            with self.assertRaisesRegex(RuntimeError, 'SHA256 differs'):
                c.read_request(path, '0' * 64)
            path.write_text(json.dumps({'request_schema': 'TREE2_CONTROL_FEATURE_REQUEST_V002'}))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(c.read_request(path, digest)['request_schema'], 'TREE2_CONTROL_FEATURE_REQUEST_V002')
        self.assertNotIn('numpy', c.sys.modules)
        self.assertNotIn('pandas', c.sys.modules)

    def test_closed_quality_unit_is_required_not_inferred(self):
        closed = {'status': 'UNIT_EXIT0_GROUP_CLOSED', 'exit_code': 0,
                  'owned_group_empty': True, 'remaining_owned_processes': []}
        c.closed_quality_unit(closed)
        for key, value in (('exit_code', None), ('exit_code', 1), ('owned_group_empty', False),
                           ('remaining_owned_processes', [123]), ('status', 'RUNNING')):
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                c.closed_quality_unit({**closed, key: value})


if __name__ == '__main__':
    unittest.main()
