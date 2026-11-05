"""Fixture-only wrapper hash/stop/deadline checks; no mount or prediction."""
from pathlib import Path
import datetime
import importlib.util
import json

R = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('entry', R / 'scripts/checkm2_pilot_image_entry.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
base = R / 'work/checkm2_image_entry_selftest'
(base / 'state').mkdir(parents=True, exist_ok=True)
fixture = base / 'image_fixture.bin'
fixture.write_bytes(b'fixture only\n' * 100)
tests, published = [], []
saved = entry.R, entry.publish, entry.linux_available_bytes, entry.time.monotonic


def rejected(name, kind, callback):
    try:
        callback()
    except kind:
        tests.append({'check': name, 'status': 'PASS_REJECTED'})
    else:
        raise AssertionError(name)


try:
    entry.R = base
    entry.publish = lambda *args, **kwargs: published.append(kwargs)
    entry.linux_available_bytes = lambda: 2 * 1024**3
    entry.time.monotonic = lambda: 1000
    digest, count = entry.hash_closed_image(fixture, {'operation': 'MOUNT_SMOKE_ONLY'})
    assert digest == entry.sha(fixture) and count == fixture.stat().st_size and published
    tests.append({'check': 'small closed-image fixture hashes with progress', 'status': 'PASS'})
    flag = base / 'state/STOP'
    flag.write_text('owned fixture\n')
    rejected('global STOP interrupts closed-image hash', InterruptedError,
             lambda: entry.hash_closed_image(fixture, {'operation': 'MOUNT_SMOKE_ONLY'}))
    flag.unlink()
    flag = base / 'state/STOP_CHECKM2_PILOT'
    flag.write_text('owned fixture\n')
    rejected('task STOP interrupts prediction finalization', InterruptedError,
             lambda: entry.hash_closed_image(fixture, {'operation': 'PREDICTION'}))
    entry.hash_closed_image(fixture, {'operation': 'MOUNT_SMOKE_ONLY'})
    tests.append({'check': 'prediction hold permits explicitly prediction-free mount smoke', 'status': 'PASS'})
    flag.unlink()
    entry.linux_available_bytes = lambda: 1024**3 - 1
    rejected('less than one GiB headroom stops final hash', RuntimeError,
             lambda: entry.hash_closed_image(fixture, {'operation': 'MOUNT_SMOKE_ONLY'}))
    entry.linux_available_bytes = lambda: 2 * 1024**3
    times = iter([0, 601])
    entry.time.monotonic = lambda: next(times)
    rejected('600-second closed-image hash deadline', TimeoutError,
             lambda: entry.hash_closed_image(fixture, {'operation': 'MOUNT_SMOKE_ONLY'}))
finally:
    entry.R, entry.publish, entry.linux_available_bytes, entry.time.monotonic = saved
    for name in ('STOP', 'STOP_CHECKM2_PILOT'):
        flag = base / 'state' / name
        if flag.exists():
            flag.unlink()

receipt = {'status': 'PASS', 'fixture_only': True, 'no_mount_operations': True,
           'no_prediction': True, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'tests': tests, 'entry_source_sha256': entry.sha(R / 'scripts/checkm2_pilot_image_entry.py')}
entry.save(R / 'evidence/checkm2_pilot/image_entry_selftest.json', receipt)
print(json.dumps(receipt))
