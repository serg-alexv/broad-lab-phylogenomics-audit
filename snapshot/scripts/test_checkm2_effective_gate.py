"""Actual receipt schema plus in-memory negative fixtures; never import/mount models."""
from pathlib import Path
import copy
import datetime
import json
import checkm2_effective_gate as gate

R = Path(__file__).resolve().parents[1]
ready = R / 'state/checkm2_runtime_ready.json'
actual = gate.effective_gate(ready)
assert actual['production_acceptance'] == 'NOT_GRANTED' and actual['official_numeric_controls_tested'] is False
tests = [{'check': 'actual resource-only schema/hash chain accepted without production promotion', 'status': 'PASS_METADATA_ONLY'}]
original = gate.read
sidecar = R / 'state/checkm2_forward_ready.json'
spec = Path(actual['manifest_path'])
control = Path(actual['control_receipt_path'])


def reject(name, target, mutate, message):
    def fixture(path):
        data = original(path)
        if Path(path) == target:
            data = copy.deepcopy(data)
            mutate(data)
        return data
    gate.read = fixture
    try:
        try:
            gate.effective_gate(ready)
        except RuntimeError as error:
            assert message in str(error), str(error)
            tests.append({'check': name, 'status': 'PASS_REJECTED_FIXTURE'})
        else:
            raise AssertionError(name)
    finally:
        gate.read = original


reject('stale candidate hash', sidecar, lambda data: data.update(candidate_ready_sha256='0' * 64), 'current base/image/models')
reject('static manifest cannot authorize prediction', spec, lambda data: data.update(status='STATIC_PREPARED_NOT_RUNTIME_VALIDATED'), 'Static or production-promoted')
reject('unsupported effective scaler version', control, lambda data: data.update(effective_sklearn_version='1.9.1'), 'Matching-version forward controls')
reject('nonfinite diagnostic output', control, lambda data: data['synthetic_outputs']['general'].__setitem__(0, float('nan')), 'missing/nonfinite')
receipt = {'status': 'PASS', 'no_model_imports': True, 'no_mounts': True, 'no_prediction': True,
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tests': tests,
    'gate_source_sha256': gate.sha(R / 'scripts/checkm2_effective_gate.py'),
    'actual_effective_manifest_sha256': actual['manifest_sha256']}
path = R / 'evidence/checkm2_pilot/effective_gate_selftest.json'
path.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'checks': len(tests), 'no_prediction': True}))
