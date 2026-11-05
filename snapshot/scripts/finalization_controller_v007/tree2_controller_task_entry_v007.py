"""Fixed isolated Task child; one exact live wrapper may call launcher.launch()."""
import argparse
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(r'C:\Users\wheel\Documents\Codex\2026-10-26\referenced-chatgpt-conversation-this-is-an\outputs\TREE2_WD_20261026')
DIRECTORY = ROOT / 'metadata/finalization_recovery_20261103/controller_v007'
AUTHORITY = DIRECTORY / 'Root_authority.json'
CLAIM = DIRECTORY / 'task_wrapper_launch_claim.json'
SPEC = DIRECTORY / 'task_spec.json'
ENTRY = ROOT / 'scripts/finalization_controller_v007/tree2_controller_task_entry_v007.py'
WRAPPER = ROOT / 'scripts/finalization_controller_v007/tree2_controller_task_v007.ps1'
LAUNCHER = ROOT / 'scripts/finalization_controller_v007/tree2_controller_launcher_v007.py'
RUNTIME = Path(r'C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
RUNTIME_SHA = 'f8b45d63047da9d9adf09892e4cc4317b859e86a93a478cc9616bc69d3b176e5'
RECEIPT = ROOT / 'metadata/finalization_recovery_20261103/controller_v007/task_registration_receipt.json'
XML = ROOT / 'metadata/finalization_recovery_20261103/controller_v007/task.registered.xml'


def row(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def require_row(binding, path):
    if binding != row(path):
        raise RuntimeError('Fixed Task source/receipt pin differs: ' + str(path))


def arguments_template():
    return '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + str(WRAPPER) + '" -AuthoritySha256 {{AUTHORITY_SHA256}}'


def authority_gate(expected_sha):
    if (Path(__file__).resolve() != ENTRY or Path(sys.executable).resolve() != RUNTIME
            or not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode
            or row(RUNTIME) != {'path': str(RUNTIME), 'bytes': 107312, 'sha256': RUNTIME_SHA}):
        raise RuntimeError('Fixed isolated Task entry/runtime differs')
    raw = AUTHORITY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise RuntimeError('Exact Task authority bytes/hash differ')
    authority = json.loads(raw.decode('utf-8-sig'))
    if (authority.get('schema') != 'TREE2_CONTROLLER_FRESH_FINALIZATION_ACTIVATION_V007'
            or authority.get('status') != 'ROOT_ADMITTED_ATTACH_SEPARATELY_ADMITTED_FINALIZATION_WORKER_ONLY'
            or any(type(authority.get(k)) is not int or authority[k] != 0 for k in
                   ('initial_AI_calls', 'initial_science_launches', 'process_repairs_remaining'))):
        raise RuntimeError('Fixed attach-only Root authority required')
    for key, path in (('task_entry', ENTRY), ('task_wrapper', WRAPPER),
                      ('operator_launcher', LAUNCHER), ('task_spec', SPEC),
                      ('runtime', RUNTIME), ('python_runtime', RUNTIME)):
        require_row(authority[key], path)
    spec = read(SPEC)
    if (spec.get('schema') != 'TREE2_V007_FIXED_TASK_SPEC_V1'
            or spec.get('task_name') != 'CodexTree2CustodianV007-wheel'
            or spec.get('task_path') != '\\Codex\\'
            or spec.get('arguments_template') != arguments_template()
            or spec.get('working_directory') != str(ROOT)
            or type(spec.get('expected_job_limit_flags')) is not int
            or spec['expected_job_limit_flags'] != 0):
        raise RuntimeError('Fixed Task descriptor differs')
    return authority, spec


def retain_wrapper(authority, spec, expected_sha):
    claim = read(CLAIM)
    required = {'schema': 'TREE2_V007_TASK_WRAPPER_LAUNCH_CLAIM_V1',
        'authority_sha256': expected_sha, 'task_entry': authority['task_entry'],
        'task_wrapper': authority['task_wrapper'], 'operator_launcher': authority['operator_launcher'],
        'task_spec': authority['task_spec'], 'python_runtime': authority['runtime'],
        'task_name': spec['task_name'], 'task_path': spec['task_path'],
        'user_sid': spec['user_sid'], 'max_operator_starts': 1, 'no_retry': True}
    if (any(claim.get(k) != v for k, v in required.items())
            or type(claim.get('max_operator_starts')) is not int
            or claim.get('no_retry') is not True):
        raise RuntimeError('Permanent exact Task-wrapper claim differs')
    require_row(claim['task_registration_receipt'], RECEIPT)
    require_row(claim['task_registered_xml'], XML)
    parent = claim['wrapper_owner']
    if type(parent.get('pid')) is not int or os.getppid() != parent['pid']:
        raise RuntimeError('Task entry is not the claimed wrapper child')
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k.OpenProcess.restype = ctypes.c_void_p
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.POINTER(ctypes.c_uint64)] * 4)]
    k.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p,
                                          ctypes.POINTER(ctypes.c_uint32)]
    handle = k.OpenProcess(0x00100000 | 0x1000, False, parent['pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        born, ended, cpu_kernel, cpu_user = [ctypes.c_uint64() for _ in range(4)]
        if not k.GetProcessTimes(handle, *map(ctypes.byref, (born, ended, cpu_kernel, cpu_user))):
            raise ctypes.WinError(ctypes.get_last_error())
        seconds, fraction = divmod(born.value, 10000000)
        date = datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=seconds)
        birth = date.strftime('%Y-%m-%dT%H:%M:%S') + f'.{fraction:07d}Z'
        if born.value != parent['windows_creation_filetime_100ns'] or birth != parent['creation_time_utc']:
            raise RuntimeError('Task wrapper exact creation identity differs')
        text = ctypes.create_unicode_buffer(32768)
        length = ctypes.c_uint32(len(text))
        if not k.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        if Path(text.value).resolve() != powershell.resolve():
            raise RuntimeError('Claimed wrapper native executable differs')
        require_row(spec['powershell'], powershell)
        if k.WaitForSingleObject(handle, 0) != 258:
            raise RuntimeError('Exact Task wrapper must remain live before operator claim')
        return k, handle
    except BaseException:
        k.CloseHandle(handle)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authority-sha256', required=True)
    args = parser.parse_args(argv)
    if len(args.authority_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.authority_sha256):
        raise RuntimeError('A mandatory exact lowercase SHA256 is required')
    authority, task_spec = authority_gate(args.authority_sha256)
    kernel, parent = retain_wrapper(authority, task_spec, args.authority_sha256)
    try:
        sys.path.insert(0,str(ENTRY.parent))  # The sole lifecycle import directory.
        sys.path.insert(0,str(ROOT))
        source = LAUNCHER.read_bytes()
        if hashlib.sha256(source).hexdigest() != authority['operator_launcher']['sha256']:
            raise RuntimeError('Launcher changed before fixed import')
        spec = importlib.util.spec_from_file_location('tree2_controller_launcher_v007', LAUNCHER)
        launcher = importlib.util.module_from_spec(spec)
        exec(compile(source, str(LAUNCHER), 'exec'), launcher.__dict__)
        # Full deterministic public adapter gate precedes the permanent operator claim.
        checked, _, base = launcher.gate()
        launcher.wiring.require_authority(launcher.wiring.CONFIG,
            launcher.wiring.TREE2 / checked['private_config']['path'], base)
        job = launcher.job_observation()
        if job.get('in_any_job') is not True or job.get('limit_flags') != 0:
            raise RuntimeError('Only the actually proven Task job flags0 context is admitted')
        if kernel.WaitForSingleObject(parent, 0) != 258:
            raise RuntimeError('Wrapper custody ended before permanent operator creation')
        result = launcher.launch()
        if type(result) is not int:
            raise RuntimeError('Fixed launcher returned no typed outcome')
        return result
    finally:
        kernel.CloseHandle(parent)


if __name__ == '__main__':
    raise SystemExit(main())
