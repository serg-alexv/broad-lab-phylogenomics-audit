"""Supervise the reviewed image helper; this module never performs mount operations."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import time
import uuid

R = Path(__file__).resolve().parents[1]
STATE = R / 'state/checkm2_pilot_progress.json'
CONTEXT = {}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(20):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.05)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def inside(value):
    path = Path(value)
    path = (path if path.is_absolute() else R / path).resolve()
    if not path.is_relative_to(R):
        raise RuntimeError('Image launch path escapes project')
    return path


def native_identity(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'parent_pid': int(fields[1]), 'process_group': int(fields[2]),
            'creation_ticks': int(fields[19]),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def publish(launch, detail, **extra):
    previous = read(STATE) if STATE.exists() else {}
    save(STATE, {**previous, 'status': 'PREPARING', 'done': 0, 'total': 1,
        'unit': 'pilot genomes', 'detail': detail, 'updated_utc': utc(),
        'started_utc': launch['started_utc'], 'model_compatibility_status': 'MATCHED_CONTROLS_RESOURCE_ONLY', 'production_acceptance': 'NOT_GRANTED',
        'pid': launch['pid'], 'creation_time_utc': launch['creation_time_utc'],
        'windows_launch_token': launch['token'], 'scientific_prediction': 'NOT_ACCEPTED',
        'native_linux_identity': native_identity(os.getpid()), 'worker_pid': None, 'worker_creation_identity': None, 'group_rss_bytes': None,
        **extra})


def linux_available_bytes():
    return int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024


def hash_closed_image(path, launch):
    digest = hashlib.sha256()
    count, last = 0, 0
    started = time.monotonic()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(2 * 1024**2), b''):
            if time.monotonic() - started > 600:
                raise TimeoutError('Closed-image verification exceeded 600 seconds')
            if (R / 'state/STOP').exists() or (launch.get('operation') == 'PREDICTION' and (R / 'state/STOP_CHECKM2_PILOT').exists()):
                raise InterruptedError('STOP during closed-image verification')
            available = linux_available_bytes()
            if available < 1024**3:
                raise RuntimeError('RESOURCE_GATE: Linux headroom below 1 GiB during closed-image verification')
            digest.update(block)
            count += len(block)
            if time.monotonic() - last > 3:
                publish(launch, f'Runtime unmounted; verifying sealed image {count:,}/{path.stat().st_size:,} bytes',
                        finalizing_namespace=True, image_bytes_hashed=count)
                last = time.monotonic()
    return digest.hexdigest(), count


def main():
    if os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED') != '1':
        raise RuntimeError('Private namespace wrapper missing')
    token = os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN', '')
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise RuntimeError('Native launcher token missing or malformed')
    CONTEXT['token'] = token
    request = read(R / 'state/checkm2_pilot_launch_requests' / (token + '.json'))
    if request.get('token') != token or request.get('operation') not in ('PREDICTION', 'MOUNT_SMOKE_ONLY'):
        raise RuntimeError('Immutable launch request differs')
    launch = None
    for _ in range(100):
        receipt = R / 'state/launch_checkm2_pilot.json'
        if receipt.exists():
            value = read(receipt)
            if value.get('token') == token:
                launch = value
                break
        time.sleep(.1)
    if launch is None:
        raise RuntimeError('Matching native WSL identity was not published')
    CONTEXT['launch'] = launch
    ready_path = inside(request['ready_receipt_path'])
    if sha(ready_path) != str(request['ready_receipt_sha256']).lower():
        raise RuntimeError('READY changed after native launch admission')
    ready = read(ready_path)
    if ready.get('status') != 'READY_FOR_RESOURCE_PILOT' or ready.get('requires_private_image_mount') is not True:
        raise RuntimeError('Recovery runtime is not READY')
    from checkm2_effective_gate import effective_gate
    effective = effective_gate(ready_path)
    ipc_proof_path = inside(request['ipc_proof_path'])
    if sha(ipc_proof_path) != request['ipc_proof_sha256']:
        raise RuntimeError('IPC capability proof changed after native admission')
    ipc_proof = read(ipc_proof_path)
    if (ipc_proof.get('status') != 'PRIVATE_SHORT_IPC_PROVEN'
        or ipc_proof.get('image_sha256') != ready['runtime_image']['sha256']
        or ipc_proof.get('effective_runtime_manifest_sha256') != effective['manifest_sha256']
        or ipc_proof.get('unchanged_effective_bootstrap_sha256') != effective['bootstrap_sha256']
        or ipc_proof.get('helper_sha256') != sha(R / 'scripts/checkm2_ipc_alias.py')
        or ipc_proof.get('target_bootstrap_sha256') != sha(R / 'scripts/checkm2_ipc_bootstrap.py')):
        raise RuntimeError('IPC capability/source/runtime admission failed')
    controls = effective['required_environment']
    helper_environment = os.environ.copy()
    helper_environment.update(controls)
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:2]))
    folder = R / 'evidence/checkm2_pilot/namespace_runs'
    folder.mkdir(parents=True, exist_ok=True)
    mount_receipt = folder / (token + '_mount.json')
    ipc_receipt = folder / (token + '_ipc.json')
    final_receipt = folder / (token + '.json')
    inner_command = ['/usr/bin/python3', '-B', str(R / 'scripts/checkm2_pilot.py'),
                     '--mount-smoke' if request['operation'] == 'MOUNT_SMOKE_ONLY' else '--run',
                     '--ready-receipt', str(ready_path), '--launch-token', token]
    if request.get('resume_from'):
        inner_command += ['--resume-from', str(inside(request['resume_from']))]
    command = ['/usr/bin/python3', '-B', str(R / 'scripts/checkm2_runtime_image.py'),
               '--receipt', str(mount_receipt), '--effective-runtime', effective['manifest_path'],
               '--effective-runtime-sha256', effective['manifest_sha256'], '--readonly-exec',
               '/usr/bin/python3', '-B', str(R / 'scripts/checkm2_ipc_alias.py'), '--receipt', str(ipc_receipt),
               '--proof', str(ipc_proof_path), '--proof-sha256', request['ipc_proof_sha256'],
               '--token', token, '--exec', *inner_command]
    publish(launch, 'Verifying sealed image and mounting runtime read-only; no prediction before preflight',
            operation=request['operation'], namespace_execution_receipt=str(final_receipt), log_path=launch['stderr'])
    child = subprocess.Popen(command, cwd=R, env=helper_environment)
    CONTEXT['helper'] = child
    try:
        CONTEXT['helper_identity'] = native_identity(child.pid)
    except FileNotFoundError:
        CONTEXT['helper_identity'] = None
    while child.poll() is None:
        current = read(STATE)
        # Once the inner controller publishes, it owns the scientific substep.
        if current.get('windows_launch_token') == token and current.get('native_linux_identity', {}).get('pid') not in (None, os.getpid()):
            pass
        else:
            publish(launch, 'Verifying sealed image and mounting runtime read-only; preflight pending',
                    operation=request['operation'], log_path=launch['stderr'])
        time.sleep(2)
    inner = read(STATE)
    CONTEXT['inner_progress'] = inner
    closure_path = mount_receipt.with_name(mount_receipt.stem + '_closure.json')
    closure = read(closure_path) if closure_path.exists() else {}
    ipc_closure_path = ipc_receipt.with_name(ipc_receipt.stem + '_closure.json')
    ipc_closure = read(ipc_closure_path) if ipc_closure_path.exists() else {}
    closed = (closure.get('status') == 'CLEAN_UNMOUNT_AND_LOOP_DETACH' and closure.get('readonly') is True
              and ipc_closure.get('status') == 'CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT'
              and ipc_closure.get('ordinary_unmount_only') is True and not ipc_closure.get('errors'))
    CONTEXT['closure'] = closure
    image = inside(ready['runtime_image']['path'])
    after_hash, image_bytes = hash_closed_image(image, launch) if closed else (None, None)
    unchanged = after_hash == ready['runtime_image']['sha256'] and image_bytes == ready['runtime_image']['bytes']
    status = 'NAMESPACE_CLOSED_AND_VERIFIED' if closed and unchanged else 'NAMESPACE_CLOSURE_OR_IMAGE_MISMATCH'
    envelope = {'status': status, 'operation': request['operation'], 'ended_utc': utc(),
        'native_windows_launch': launch, 'helper_exit_code': child.returncode,
        'helper_native_linux_identity': CONTEXT.get('helper_identity'),
        'mount_receipt_path': str(mount_receipt), 'mount_receipt_sha256': sha(mount_receipt) if mount_receipt.exists() else None,
        'closure_receipt_path': str(closure_path), 'closure_receipt_sha256': sha(closure_path) if closure_path.exists() else None,
        'closure': closure, 'image_sha256_after_clean_unmount': after_hash,
        'image_bytes': image_bytes, 'image_unchanged': unchanged,
        'production_acceptance': 'NOT_GRANTED', 'inner_progress': inner,
        'entry_source_sha256': sha(__file__), 'effective_runtime': effective,
        'ipc_proof_path': str(ipc_proof_path), 'ipc_proof_sha256': request['ipc_proof_sha256'],
        'ipc_receipt_path': str(ipc_receipt), 'ipc_receipt_sha256': sha(ipc_receipt) if ipc_receipt.exists() else None,
        'ipc_closure_path': str(ipc_closure_path), 'ipc_closure_sha256': sha(ipc_closure_path) if ipc_closure_path.exists() else None,
        'ipc_closure': ipc_closure}
    save(final_receipt, envelope)
    latest_path = R / 'analysis/checkm2_pilot/latest.json'
    if status == 'NAMESPACE_CLOSED_AND_VERIFIED' and child.returncode == 0 and request['operation'] == 'PREDICTION' and latest_path.exists():
        latest = read(latest_path)
        if latest.get('namespace_execution_receipt_path') == str(final_receipt):
            latest['namespace_execution_receipt_sha256'] = sha(final_receipt)
            save(latest_path, latest)
    final = {**inner, 'updated_utc': utc(), 'namespace_execution_receipt': str(final_receipt),
             'namespace_execution_receipt_sha256': sha(final_receipt)}
    if status != 'NAMESPACE_CLOSED_AND_VERIFIED':
        final.update(status='FAILED_RUNTIME_NAMESPACE_CLOSURE', detail='Runtime namespace closure or sealed-image hash failed; no acceptance')
    elif child.returncode == 0 and request['operation'] == 'MOUNT_SMOKE_ONLY':
        final.update(status='PREPARED', done=0, detail='Read-only namespace/tool preflight and clean closure passed; genome prediction not run')
    elif child.returncode == 0:
        final.update(status='COMPLETED', done=1, detail='One-genome numeric result and runtime closure verified; production QC review remains')
    else:
        final['detail'] = inner.get('detail', '') + '; runtime closed and image hash verified'
    save(STATE, final)
    return child.returncode if status == 'NAMESPACE_CLOSED_AND_VERIFIED' else 4


if __name__ == '__main__':
    try:
        code = main()
    except BaseException as error:
        token = CONTEXT.get('token')
        launch = CONTEXT.get('launch')
        if launch is None and token:
            candidate = R / 'state/launch_checkm2_pilot.json'
            if candidate.exists():
                value = read(candidate)
                if value.get('token') == token:
                    launch = value
        helper = CONTEXT.get('helper')
        helper_closed = helper is None or helper.poll() is not None
        status = 'STOPPED' if isinstance(error, InterruptedError) else 'INTERRUPTED_BUDGET' if isinstance(error, TimeoutError) else 'FAILED_PRECHECK'
        receipt = {'status': status, 'ended_utc': utc(), 'error': repr(error),
                   'helper_started': helper is not None, 'helper_closed': helper_closed,
                   'helper_pid': helper.pid if helper is not None else None,
                   'helper_native_linux_identity': CONTEXT.get('helper_identity'),
                   'closure': CONTEXT.get('closure'), 'native_windows_launch': launch,
                   'inner_progress': CONTEXT.get('inner_progress'),
                   'production_acceptance': 'NOT_GRANTED', 'scientific_absence_inference': 'NONE',
                   'entry_source_sha256': sha(__file__)}
        if token:
            path = R / 'evidence/checkm2_pilot/namespace_runs' / (token + '.json')
            save(path, receipt)
        if launch:
            current = read(STATE) if STATE.exists() else {}
            save(STATE, {**current, 'status': status, 'updated_utc': utc(), 'detail': repr(error),
                'pid': launch['pid'], 'creation_time_utc': launch['creation_time_utc'],
                'windows_launch_token': token, 'namespace_execution_receipt': str(path),
                'closure_unproven_no_relaunch': helper is not None and (CONTEXT.get('closure') or {}).get('status') != 'CLEAN_UNMOUNT_AND_LOOP_DETACH'})
        print(json.dumps(receipt), file=sys.stderr)
        code = 4
    raise SystemExit(code)
