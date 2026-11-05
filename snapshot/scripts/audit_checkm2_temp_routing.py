"""Read-only source audit; no target Python, models, mounts or analyses are run."""
from pathlib import Path
import datetime
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'tools/checkm2_runtime_pkgs'
TARGETS = {
    'checkm2-1.1.0-pyhdfd78af_2': [
        'site-packages/checkm2/main.py',
        'site-packages/checkm2/diamond.py',
        'site-packages/checkm2/prodigal.py',
        'site-packages/checkm2/predictQuality.py'],
    'python-3.12.16-h5f976f7_0_cpython': [
        'lib/python3.12/multiprocessing/util.py',
        'lib/python3.12/multiprocessing/connection.py',
        'lib/python3.12/multiprocessing/process.py',
        'lib/python3.12/tempfile.py']}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for package, files in TARGETS.items():
        folder = CACHE / package
        metadata_path = folder / 'info/paths.json'
        metadata = json.loads(metadata_path.read_text())
        paths = {row['_path']: row for row in metadata['paths']}
        for rel in files:
            path = folder / rel
            digest = sha(path)
            row = paths[rel]
            if digest != row['sha256'] or path.stat().st_size != row['size_in_bytes']:
                raise RuntimeError('Cached source differs from package payload metadata: ' + rel)
            rows.append(dict(package=package, path=path.relative_to(ROOT).as_posix(),
                bytes=path.stat().st_size, sha256=digest,
                cached_package_paths_json_sha256=sha(metadata_path), payload_hash_match=True,
                source_lines=[dict(line=n, text=text) for n, text in enumerate(path.read_text().splitlines(),1)
                    if any(needle in text for needle in (
                        'tempfile.tempdir = newtmpdir', 'def get_temp_dir(',
                        "_config.get('tempdir')", "_config['tempdir'] = tempdir",
                        "mkdtemp(prefix='pymp-')", "dir=util.get_temp_dir()",
                        'tempfile.NamedTemporaryFile()', 'tempfile.TemporaryDirectory()',
                        'tempfile.mkdtemp()', 'free // (2**20) < 500',
                        'self._config = _current_process._config.copy()',
                        'mp.Manager().dict()'))]))
    main_sha = next(row['sha256'] for row in rows if row['path'].endswith('/checkm2/main.py'))
    assert main_sha == '28bb95e55b3878f2f35f40231d0a254b45f9864c8490d547909616b74d015160'
    result = dict(status='STATIC_SOURCE_REVIEW_NOT_RUNTIME_PASS',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), files=rows,
        findings=[
            'Author --tmpdir changes tempfile.tempdir directly; environment-only short TMPDIR is insufficient.',
            'DIAMOND uses ordinary tempfile for scientific input/scratch and requires at least500MiB free;32MiB tmpfs must remain IPC-only.',
            'CPython util.get_temp_dir caches a separate process-config path; connection.arbitrary_address(AF_UNIX) uses that path explicitly.',
            'A same-interpreter IPC prewarm before unchanged author CLI parsing can be capability-tested without source or binary patches.'],
        required_real_proof=[
            'Actual pinned image Python3.12, private mapped /tmp, all three environment variables set before process start.',
            'Real short pathname AF_UNIX bind/connect; encoded pathname length at most107bytes.',
            'Prewarm multiprocessing.util.get_temp_dir before emulating author long durable tempfile.tempdir.',
            'Real Manager dictionary roundtrip; actual manager address remains in short cached IPC directory.',
            'Ordinary tempfile after author setting lands in durable project scratch; no scientific output is mapped into ephemeral IPC.',
            'Manager/descendant closure, mount restoration, raw RO image closure/hash, registry unchanged.'],
        no_scientific_import_or_execution=True, no_mounts=True,
        no_new_downloads=True, no_runtime_or_biological_acceptance=True,
        fresh_archive_rehash_performed=False, source_controller_sha256=sha(Path(__file__)))
    path = ROOT / 'evidence/checkm2_runtime/ipc_temp_routing_source_review.json'
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    print(json.dumps(dict(status=result['status'], files=len(rows), receipt_sha256=sha(path))))


if __name__ == '__main__':
    main()
