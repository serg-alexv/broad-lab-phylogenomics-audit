"""T1 optional telemetry and retained helper ownership; no mount operations here."""
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
import checkm2_benchmark10_common_T1 as common
STATE = R / 'state/checkm2_benchmark10_protein_recovery_T1_step.json'
CONTEXT = {}
from checkm2_optional_telemetry_v001 import read_optional_telemetry, structured_exception
import checkm2_owned_cleanup_T1 as ownership


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


def committed_done(value=None):
    previous = CONTEXT.get('committed_done', 0)
    if type(value) is int and 0 <= value <= 10:
        previous = max(previous, value)
    CONTEXT['committed_done'] = previous
    return previous


def optional_snapshot(launch):
    value, diagnostic = read_optional_telemetry(STATE, launch['token'], CONTEXT.get('telemetry_cache'))
    value = dict(value)
    malformed = []
    if 'done' in value and not (type(value['done']) is int and 0 <= value['done'] <= 10):
        malformed.append('done')
    value['done'] = committed_done(value.get('done'))
    if 'native_linux_identity' in value and not isinstance(value['native_linux_identity'], dict):
        malformed.append('native_linux_identity')
        value['native_linux_identity'] = {}
    if 'detail' in value and not isinstance(value['detail'], str):
        malformed.append('detail')
        value['detail'] = 'Last optional operation text is unavailable'
    CONTEXT['telemetry_unavailable'] = diagnostic is not None or bool(malformed)
    CONTEXT['telemetry_malformed_fields'] = malformed
    scientific_identity = value.get('native_linux_identity')
    if (not CONTEXT['telemetry_unavailable'] and isinstance(scientific_identity, dict)
            and scientific_identity.get('pid') not in (None, os.getpid())):
        CONTEXT['last_scientific_detail'] = value.get('detail', 'unavailable')
    CONTEXT['telemetry_cache'] = value
    if diagnostic is not None:
        history = CONTEXT.setdefault('telemetry_errors', {'count': 0})
        history['count'] += 1
        history.setdefault('first', diagnostic)
        history['last'] = diagnostic
        history['last_utc'] = utc()
    return value


def publish(launch, detail, cached=None, **extra):
    previous = cached if isinstance(cached, dict) else CONTEXT.get('telemetry_cache', {})
    if previous.get('windows_launch_token') != launch['token']:
        previous = {}
    if CONTEXT.get('telemetry_unavailable'):
        detail = 'Optional progress stale/unavailable; actual helper supervision continues. ' + detail
    value = {**previous, 'status': 'PREPARING', 'done': committed_done(previous.get('done')), 'total': 10,
        'unit': 'benchmark annotation commits', 'detail': detail, 'updated_utc': utc(),
        'started_utc': launch['started_utc'], 'model_compatibility_status': 'MATCHED_CONTROLS_RESOURCE_ONLY', 'production_acceptance': 'NOT_GRANTED',
        'pid': launch['pid'], 'creation_time_utc': launch['creation_time_utc'],
        'windows_launch_token': launch['token'], 'scientific_prediction': 'NOT_ACCEPTED',
        'native_linux_identity': (previous.get('native_linux_identity')
            if isinstance(previous.get('native_linux_identity'), dict)
            else native_identity(os.getpid())), 'worker_pid': None,
        'worker_creation_identity': None, 'group_rss_bytes': None,
        'optional_telemetry_errors': CONTEXT.get('telemetry_errors'),
        'optional_telemetry_stale_or_unavailable': CONTEXT.get('telemetry_unavailable', False),
        'optional_malformed_fields': CONTEXT.get('telemetry_malformed_fields', []), **extra}
    # This consumes the matching cached snapshot; it never rereads STEP.
    save(STATE, value)
    CONTEXT['telemetry_cache'] = value


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
            if (R / 'state/STOP').exists() or common.STOP.exists() or (launch.get('operation') == 'PREDICTION' and (R / 'state/STOP_CHECKM2_PILOT').exists()):
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
    CONTEXT['operation_path'] = str(R / 'state/checkm2_benchmark10_protein_recovery_T1_launch_requests' / (token + '.json'))
    request = read(CONTEXT['operation_path'])
    if request.get('token') != token or request.get('operation') != 'PREDICTION' or request.get('role') != common.ROLE:
        raise RuntimeError('Immutable launch request differs')
    launch = None
    for _ in range(100):
        receipt = R / 'state/launch_checkm2_benchmark10_protein_recovery_T1.json'
        if receipt.exists():
            value = read(receipt)
            if value.get('token') == token:
                launch = value
                break
        time.sleep(.1)
    if launch is None:
        raise RuntimeError('Matching native WSL identity was not published')
    CONTEXT['launch'] = launch
    CONTEXT['operation_path'] = request['input_plan_path']
    plan, baseline, admitted = common.plan_gate(request['input_plan_path'],request['input_plan_sha256'])
    if admitted['phase'] != 'BOUNDARY_AFTER_FIRST_ANNOTATION':
        resume = common.resume_proof(admitted, plan['session_identity_sha256'])
        initial_done = len(resume['annotation_commit_sha256s'])
        if not 0 <= initial_done <= 10:
            raise RuntimeError('Required resume proof has an invalid annotation commit count')
        committed_done(initial_done)
    ready_path = inside(request['ready_receipt_path'])
    CONTEXT['operation_path'] = str(ready_path)
    if sha(ready_path) != str(request['ready_receipt_sha256']).lower():
        raise RuntimeError('READY changed after native launch admission')
    strategy_path = inside(request['protocol_admission_path'])
    CONTEXT['operation_path'] = str(strategy_path)
    if sha(strategy_path) != request['protocol_admission_sha256']:
        raise RuntimeError('Protein strategy changed after native admission')
    ready = read(ready_path)
    if ready.get('status') != 'READY_FOR_RESOURCE_PILOT' or ready.get('requires_private_image_mount') is not True:
        raise RuntimeError('Recovery runtime is not READY')
    from checkm2_effective_gate import effective_gate
    effective = effective_gate(ready_path)
    ipc_proof_path = inside(request['ipc_proof_path'])
    CONTEXT['operation_path'] = str(ipc_proof_path)
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
    folder = R / 'evidence/checkm2_benchmark10_protein_recovery_T1/namespace_runs'
    folder.mkdir(parents=True, exist_ok=True)
    mount_receipt = folder / (token + '_mount.json')
    ipc_receipt = folder / (token + '_ipc.json')
    final_receipt = folder / (token + '.json')
    CONTEXT['mount_receipt_path'] = mount_receipt
    CONTEXT['ipc_receipt_path'] = ipc_receipt
    inner_command = ['/usr/bin/python3', '-B', str(R / 'scripts/checkm2_benchmark10_inner_T1.py'),
                     '--input-plan', request['input_plan_path'], '--input-plan-sha256',request['input_plan_sha256'], '--launch-token', token]
    if request.get('resume_from'):
        raise RuntimeError('Resume forbidden in supported protein route')
    command = ['/usr/bin/python3', '-B', str(R / 'scripts/checkm2_runtime_image.py'),
               '--receipt', str(mount_receipt), '--effective-runtime', effective['manifest_path'],
               '--effective-runtime-sha256', effective['manifest_sha256'], '--readonly-exec',
               '/usr/bin/python3', '-B', str(R / 'scripts/checkm2_ipc_alias.py'), '--receipt', str(ipc_receipt),
               '--proof', str(ipc_proof_path), '--proof-sha256', request['ipc_proof_sha256'],
               '--token', token, '--exec', *inner_command]
    publish(launch, 'Verifying sealed image and mounting runtime read-only; no prediction before preflight',
            operation=request['operation'], namespace_execution_receipt=str(final_receipt), log_path=launch['stderr'])
    CONTEXT['operation_path'] = 'Popen accepted read-only image helper in its own Unix session'
    child = subprocess.Popen(command, cwd=R, env=helper_environment, start_new_session=True)
    CONTEXT['helper'] = child
    CONTEXT['owned_identities'] = {}
    try:
        CONTEXT['helper_identity'] = ownership.identity(child.pid)
        ownership.track_descendants(CONTEXT['helper_identity'], CONTEXT['owned_identities'])
    except FileNotFoundError:
        CONTEXT['helper_identity'] = None
    deadline=time.monotonic()+10200
    while child.poll() is None:
        CONTEXT['operation_path'] = '/proc creation-identity descendant census'
        ownership.track_descendants(CONTEXT.get('helper_identity'), CONTEXT['owned_identities'])
        if time.monotonic() > deadline:
            raise TimeoutError('Owned helper deadline; bounded scoped cleanup follows')
        CONTEXT['operation_path'] = str(STATE)
        current = optional_snapshot(launch)
        # Once the inner controller publishes, it owns the scientific substep.
        if current.get('windows_launch_token') == token and (current.get('native_linux_identity') or {}).get('pid') not in (None, os.getpid()):
            if CONTEXT.get('telemetry_unavailable'):
                publish(launch, 'Last recorded operation: ' + str(CONTEXT.get('last_scientific_detail', 'unavailable')),
                        cached=current, operation=request['operation'], log_path=launch['stderr'])
        else:
            publish(launch, 'Verifying sealed image and mounting runtime read-only; preflight pending',
                    cached=current, operation=request['operation'], log_path=launch['stderr'])
        time.sleep(2)
    CONTEXT['operation_path'] = str(STATE) + ' (strict terminal inner evidence)'
    inner = read(STATE)
    CONTEXT['inner_progress'] = inner
    closure_path = mount_receipt.with_name(mount_receipt.stem + '_closure.json')
    CONTEXT['operation_path'] = str(closure_path)
    closure = read(closure_path) if closure_path.exists() else {}
    ipc_closure_path = ipc_receipt.with_name(ipc_receipt.stem + '_closure.json')
    CONTEXT['operation_path'] = str(ipc_closure_path)
    ipc_closure = read(ipc_closure_path) if ipc_closure_path.exists() else {}
    closed = (closure.get('status') == 'CLEAN_UNMOUNT_AND_LOOP_DETACH' and closure.get('readonly') is True
              and ipc_closure.get('status') == 'CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT'
              and ipc_closure.get('ordinary_unmount_only') is True and not ipc_closure.get('errors'))
    CONTEXT['closure'] = closure
    image = inside(ready['runtime_image']['path'])
    CONTEXT['operation_path'] = str(image)
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
    latest_path = R / 'analysis/checkm2_benchmark10_protein_recovery_T1/latest_pending_native.json'
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
        final.update(status='CONTROL_CORE_PENDING_NATIVE_CLOSURE', done=inner.get('done',0), detail='Benchmark phase outputs and namespace closed; actual native exit/leases/root review pending')
    else:
        final['detail'] = inner.get('detail', '') + '; runtime closed and image hash verified'
    save(STATE, final)
    return child.returncode if status == 'NAMESPACE_CLOSED_AND_VERIFIED' else 4


if __name__ == '__main__':
    try:
        code = main()
    except BaseException as error:
        failure = structured_exception(error, CONTEXT.get('operation_path', str(STATE)))
        token, launch = CONTEXT.get('token'), CONTEXT.get('launch')
        helper = CONTEXT.get('helper')
        cleanup = None
        handoff = None
        ordinary = {'verified': False, 'status': 'UNKNOWN_NOT_INSPECTED'}
        if helper is not None:
            try:
                cleanup = ownership.cleanup_linux_helper(helper, CONTEXT.get('helper_identity'),
                    CONTEXT.setdefault('owned_identities', {}), common.STOP, token)
            except BaseException as cleanup_error:
                cleanup = {'closure_proven': False, 'forced_action': False,
                    'helper_poll': helper.poll(),
                    'tracked_creation_identities': list(CONTEXT.get('owned_identities', {}).values()),
                    'exception': structured_exception(cleanup_error, 'bounded Linux owned cleanup')}
            if helper.poll() is not None and not cleanup.get('forced_action'):
                try:
                    mount_path = CONTEXT['mount_receipt_path']
                    ipc_path = CONTEXT['ipc_receipt_path']
                    mount_closed = mount_path.with_name(mount_path.stem + '_closure.json')
                    ipc_closed = ipc_path.with_name(ipc_path.stem + '_closure.json')
                    mount_value, ipc_value = read(mount_closed), read(ipc_closed)
                    verified = (mount_value.get('status') == 'CLEAN_UNMOUNT_AND_LOOP_DETACH'
                        and mount_value.get('readonly') is True
                        and ipc_value.get('status') == 'CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT'
                        and ipc_value.get('ordinary_unmount_only') is True and not ipc_value.get('errors'))
                    ordinary = {'verified': verified, 'mount_closure': mount_value,
                        'mount_closure_sha256': sha(mount_closed), 'ipc_closure': ipc_value,
                        'ipc_closure_sha256': sha(ipc_closed), 'image_hash_after_fatal_cleanup': 'NOT_PERFORMED'}
                except BaseException as closure_error:
                    ordinary = {'verified': False, 'status': 'UNKNOWN_MISSING_OR_INVALID_RECEIPTS',
                        'exception': structured_exception(closure_error, 'strict fatal-path ordinary closure receipts')}
            if not cleanup.get('closure_proven') or cleanup.get('forced_action') or not ordinary['verified']:
                try:
                    handoff = ownership.immutable_handoff(common.E, common.UNRESOLVED_HANDOFF, token,
                        'linux_helper', {'cleanup': cleanup, 'original_exception': failure,
                        'helper_identity': CONTEXT.get('helper_identity'),
                        'actual_helper_poll': helper.poll(), 'native_windows_launch': launch,
                        'ordinary_runtime_closure': ordinary})
                except BaseException as handoff_error:
                    handoff = {'unresolved_handoff_write_failed':
                        structured_exception(handoff_error, common.UNRESOLVED_HANDOFF)}
        helper_closed = helper is None or helper.poll() is not None
        if helper is not None:
            status = ('FAILED_OWNED_WORK_UNKNOWN_CLOSURE' if not (cleanup or {}).get('closure_proven')
                      or (cleanup or {}).get('forced_action') or not ordinary['verified']
                      else 'FAILED_OWNED_WORK_CLOSED_NOT_ACCEPTED')
        else:
            status = 'STOPPED' if isinstance(error, InterruptedError) else 'FAILED_PRECHECK'
        receipt = {'status': status, 'ended_utc': utc(), 'exception': failure,
            'helper_started': helper is not None, 'helper_closed': helper_closed,
            'actual_helper_exit_code': helper.returncode if helper_closed and helper is not None else None,
            'helper_pid': helper.pid if helper is not None else None,
            'helper_native_linux_identity': CONTEXT.get('helper_identity'),
            'cleanup': cleanup, 'ordinary_closure_evidence': ordinary, 'unresolved_ownership_handoff': handoff,
            'closure': CONTEXT.get('closure'), 'native_windows_launch': launch,
            'inner_progress': CONTEXT.get('inner_progress'),
            'optional_telemetry_errors': CONTEXT.get('telemetry_errors'),
            'production_acceptance': 'NOT_GRANTED', 'scientific_absence_inference': 'NONE',
            'entry_source_sha256': sha(__file__)}
        if token:
            path = common.E / 'namespace_runs' / (token + '.json')
            save(path, receipt)
        if launch:
            current = CONTEXT.get('telemetry_cache', {})
            save(STATE, {**current, 'status': status, 'updated_utc': utc(),
                'detail': 'Owned work failed; exact exception and cleanup disposition preserved in namespace receipt',
                'pid': launch['pid'], 'creation_time_utc': launch['creation_time_utc'],
                'done': committed_done(current.get('done')),
                'windows_launch_token': token, 'namespace_execution_receipt': str(path),
                'closure_unproven_no_relaunch': status == 'FAILED_OWNED_WORK_UNKNOWN_CLOSURE'})
        print(json.dumps(receipt), file=sys.stderr)
        code = 4
    raise SystemExit(code)
