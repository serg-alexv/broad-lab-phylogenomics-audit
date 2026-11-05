# PREPARED SOURCE CANDIDATE ONLY: not admitted, not a memory guarantee.
# Requires effective-memory review and fresh exact retained custody before execution.
"""WD production native owner: retained WSL exit, seven-day production deadline, no pilot budget."""
from pathlib import Path
import ctypes, json, msvcrt, os, subprocess, sys, time
R = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / 'scripts'))
import marker_pilot_compute_v001 as g
import local_tree2_dispatcher as d
import checkm2_private_install_controller as b
from checkm2_native_rss_guard_v001 import summed_native_rss

plan = Path(sys.argv[1]); expected = sys.argv[2]
if os.name != 'nt' or os.environ.get('COMPUTERNAME', '').upper() != 'WD' or g.sha(plan) != expected:
    raise RuntimeError('Exact WD production plan required')
p = g.read(plan); e = R / p['work']; e.mkdir(exist_ok=True); kernel = d.Windows(); owner = b.OWNER; locks = []
if p['schema'] != 'TREE2_ROOT_FULL900_LOW_MEMORY_FINALIZATION_RESUME_V006': raise RuntimeError('Wrong production-resume schema')
if (p['status'] != 'ROOT_ADMITTED_LOW_MEMORY_FINALIZATION_RECOVERY' or
    p['compute_threads'] != 1 or p['cpu_affinity'] != [2] or p['IQTREE_memory_target'] != '500M' or
    p['attempt_id'] != 'attempt006_low_memory_finalization' or
    p['resource_fallback_count'] != 1 or p['resource_recovery_count'] != 1 or p['remaining_retries_allowed'] != 0 or
    p['pre_science_activation_correction_count'] != 1):
    raise RuntimeError('Only a separately admitted one-shot T1/500M finalization recovery; no old fallback or retry replay')
for row in p['sources'] + p['bound_inputs']: g.bound(row)
k = ctypes.WinDLL('kernel32', use_last_error=True); k.GetCurrentProcess.restype = ctypes.c_void_p
k.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
if not k.SetProcessAffinityMask(k.GetCurrentProcess(), sum(1 << c for c in p['native_affinity_CPUs'])):
    raise ctypes.WinError(ctypes.get_last_error())
try:
    for name in ('checkm2_pilot_launcher.lock', 'checkm2_install.lock'):
        f = (R / 'state' / name).open('r+b'); f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1); locks.append(f)
    g.save(e / 'native_owner.json', {'native_owner': owner, 'input_plan_sha256': expected,
        'input_plan': g.ref(plan), 'started_utc': g.utc(), 'method': 'FULL900_LOW_MEMORY_FINALIZATION_RESOURCE_RECOVERY'})
    until = time.monotonic() + 180
    while True:
        ack = e / 'Root_companion_ack.json'
        if ack.exists():
            value = g.read(ack)
            if value.get('native_owner') == owner and value.get('exact_handle_retained') is True and value.get('input_plan_sha256') == expected: break
        if time.monotonic() > until: raise TimeoutError('Retained Root/controller OS handle ACK missing before production')
        time.sleep(.2)
    linux_plan = '/mnt/c/' + plan.as_posix()[3:]
    entry = '/mnt/c/' + (R / 'scripts/full900_finalization_resume_v006.py').as_posix()[3:]
    with (e / 'WSL.stdout.txt').open('wb') as out, (e / 'WSL.stderr.txt').open('wb') as err:
        child = subprocess.Popen(['wsl', '-d', 'Ubuntu', '--exec', 'unshare', '--mount', '--ipc',
            '--propagation', 'private', '/usr/bin/python3', '-B', entry, '--namespace', linux_plan, expected], stdout=out, stderr=err)
        identity = kernel.identity(int(child._handle), child.pid)
        g.save(e / 'WSL_owner.json', {'identity': identity, 'argv_role': 'FULL900_PRODUCTION_PRIVATE_MOUNT_IPC'})
        failure = None; stop_started = None; peak = 0
        while child.poll() is None:
            rss = summed_native_rss(child); peak = max(peak, rss)
            if rss > p['native_reserved_bytes'] or time.time() > p['production_absolute_deadline_unix']:
                failure = failure or 'Native RSS reservation or explicit production deadline exceeded'
                if stop_started is None:
                    stop_started = time.monotonic()
                    g.save(R / p['stop_path'], {'reason': failure, 'native_owner': owner, 'no_blind_retry': True})
            if stop_started is not None and time.monotonic() - stop_started > 180:
                g.save(e / 'unresolved_WSL_ownership.json', {'identity': identity,
                    'actual_exit_code': None, 'error': failure, 'no_relaunch': True})
                raise RuntimeError('Production WSL did not close after scoped stop; closure UNKNOWN')
            time.sleep(.5)
        child.wait()
        g.save(e / 'native_RSS_guard.json', {'peak_native_plus_retained_WSL_RSS_bytes': peak,
            'reservation_bytes': p['native_reserved_bytes'], 'fatal_resource_reason': failure})
        g.save(e / 'WSL_actual_exit.json', {'actual_exit_code': child.returncode, 'identity': identity,
            'exact_birth_handle_retained': True, 'waited_and_reaped': True, 'observed_utc': g.utc()})
    print(json.dumps({'WSL_actual_exit': child.returncode, 'native_owner_actual_exit': 'REQUIRES_EXTERNAL_RETAINED_HANDLE'}), flush=True)
    raise SystemExit(child.returncode)
finally:
    for f in reversed(locks):
        f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1); f.close()
