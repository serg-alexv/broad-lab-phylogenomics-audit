"""One read-only P20 prelaunch: LF/bash/env, current owners, resources and leases.

No runtime mount, image content, scientific/model import, prediction, or retry.
"""
from pathlib import Path
import argparse
import ctypes
import importlib.util
import json
import msvcrt
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid
import checkm2_production_preparation_P1 as p
import checkm2_phase_separated_common_P20 as c
import checkm2_saved_P20_common_v001 as repair

R = p.R
L = '/mnt/c/' + str(R)[3:].replace('\\', '/')
E = repair.E / 'preflight_v001'
ROLE = 'SAVED_P20_ACTUAL_READ_ONLY_PREFLIGHT_V001'
EVENT = '294d0c9f5a5e93e69b0054e73efb5f6fb3d03bbcdb620a7f5d117d2e04ab4995'
p.E = E
p.EVENT = EVENT
p.ROLE = ROLE
CHILDREN = []
OBS = {}
HELPERS = None
WIN = None
OWNER = None
DEADLINE = None


def checkpoint(key, value):
    OBS[key] = value
    p.dispatcher.atomic(E / 'observations.json', OBS)
    return value


def bounded():
    p.gate(DEADLINE)
    c.stop()


def image_stat():
    s = (R / 'tools/checkm2_runtime_ext4.img').stat()
    return {k: getattr(s, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_nlink')}


def publish(detail, status='RUNNING', terminal=None):
    p.dispatcher.atomic(R / 'state/stages/04.json', {
        'id': '04', 'name': 'Independent biological QC', 'status': status,
        'started_utc': p.START, 'updated_utc': p.dispatcher.utc(), 'ended_utc': None,
        'pid': OWNER['pid'], 'creation_time_utc': OWNER['creation_time_utc'],
        'windows_creation_filetime_100ns': OWNER['windows_creation_filetime_100ns'],
        'operation': ROLE, 'done': 0, 'total': 1, 'unit': 'actual read-only P20 prelaunch gate',
        'detail': detail, 'log_path': str(E / 'owner.stdout.txt'), 'terminal_receipt': terminal,
        'scientific_execution_authorized': False, 'whole_stage_QC_acceptance': False, 'production_panel_acceptance': False})


def run(argv, role):
    bounded()
    child = subprocess.Popen(argv, cwd=R, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    identity = WIN.identity(int(child._handle), child.pid)
    record = {'role': role, 'identity': identity, 'actual_exit_code': None, 'actual_handle_reaped': False}
    CHILDREN.append(record)
    p.create(E / (role + '_launch.json'), {'identity': identity, 'argv': argv, 'started_utc': p.dispatcher.utc()})
    try:
        stdout, stderr = child.communicate(timeout=max(1, DEADLINE - time.monotonic()))
    except subprocess.TimeoutExpired:
        p.create(E / 'UNRESOLVED_READONLY_CHILD.json', {'identity': identity, 'role': role,
                 'actual_exit_code': None, 'closure': 'UNKNOWN_NO_RETRY_NO_SCIENCE_OR_PROXY_KILL'})
        raise
    record.update(actual_exit_code=child.wait(), actual_handle_reaped=True)
    p.create(E / (role + '_child.json'), record)
    for suffix, value in (('stdout', stdout), ('stderr', stderr)):
        with (E / (role + '_' + suffix + '.txt')).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(value)
    if type(child.returncode) is not int or child.returncode != 0:
        raise RuntimeError('Actual read-only child nonzero: ' + role + ' exit' + str(child.returncode))
    return json.loads(stdout)


def historical_targets(recipe):
    linux, windows, namespaces, receipts = [], [], [], []
    files = set((R / 'state').glob('launch_checkm2*.json'))
    history = c.read(c.bind(recipe['history']))
    for record in history['claim_inventory']:
        target = R / record['artifact']['path']
        if target.name == 'execution.json' and target.parent.name.startswith('unit_'):
            files.add(target)
    for namespace in (R / 'evidence').glob('checkm2*/namespace_runs'):
        if namespace.parent.name != 'checkm2_phase_separated_P20':
            files.update(namespace.glob('*.json'))
    closure=c.read(c.bind(recipe['_saved_original_closure']))
    files.update(c.bind(u['receipt'])for u in closure['units'])
    files.add(R/'evidence/checkm2_phase_separated_P20/namespace_runs/901be135bb904653b9b8a6ef8c5f19e5.json')
    for file in sorted(files):
        bounded()
        body = p.read(file)
        if file.parent == R / 'state':
            for key in ('native_owner', 'wsl_child', 'wsl_child_identity'):
                if isinstance(body.get(key), dict):
                    HELPERS.collect_identities(body[key], linux, windows, namespaces)
            if all(k in body for k in ('pid', 'windows_creation_filetime_100ns')):
                HELPERS.collect_identities({k: body[k] for k in ('pid', 'windows_creation_filetime_100ns')}, linux, windows, namespaces)
        else:
            HELPERS.collect_identities(body, linux, windows, namespaces)
        receipts.append(p.row(file))
    linux = list({(x['pid'], x['creation_ticks'], x['boot_id']): x for x in linux}.values())
    windows = list({(x['pid'], x['windows_creation_filetime_100ns']): x for x in windows}.values())
    namespaces = sorted(set(namespaces))
    value = {'Linux': linux, 'Windows': windows, 'namespace_targets': namespaces, 'source_receipts': receipts}
    p.create(E / 'historical_targets.json', value)
    return value


def checks(spec):
    bounded()
    plan, recipe, _ = c.plan_gate(c.bind(spec['input_plan']), spec['input_plan']['sha256'], require_admission=False, closed_finalization=True)
    repair.plan_gate(c.bind(spec['saved_runtime_plan']),spec['saved_runtime_plan']['sha256'],require_admission=False,closed_finalization=True)
    recipe={**recipe,'_saved_original_closure':spec['original_closure']}
    for value in spec['bound_inputs']:
        bounded(); p.bind(value)
    for value in c.read(c.bind(plan['source_manifest']))['sources']:
        bounded(); c.bind(value)
    checkpoint('source_plan_and_twenty_acquired_FNA_integrity', {'plan': spec['input_plan'], 'all190_sources': True,
               'twenty_distinct_novel_inputs': len(recipe['inputs']) == 20, 'no_raw_sequence_parse_or_science': True})
    if repair.ADMISSION.exists() or repair.LAUNCH.exists() or repair.STOP.exists() or repair.UNRESOLVED_HANDOFF.exists() or list((repair.E/'native_phase_claims').glob('*.json')) or list(repair.OUT.glob('sessions/*/once_claim.json')):
        raise RuntimeError('A saved-validation native admission/attempt already exists; no duplicate')
    if c.sha(c.ADMISSION)!='13e0f282c55acc605e958a9034d85ffe7bb46151d81d50e1f312691ebb543723':raise RuntimeError('Original consumed Ready changed')
    checkpoint('original_claims_debits_preserved_saved_native_not_admitted',{'original_Ready_present_unchanged':True,'old_attempt_preserved':True,'saved_native_claim_absent':True})
    before_image = checkpoint('Windows_image_before', image_stat())
    anchor = c.read(c.bind(spec['N5_closure_proof']))
    if before_image != anchor['Windows_image_metadata_anchor']:
        raise RuntimeError('Image metadata changed since actual accepted N5 pre/post full hash')
    targets = historical_targets(recipe)
    runtime_pointer=p.read('state/local_continuation_current_runtime.json')
    runtime_roles=p.read(p.bind(runtime_pointer['actual_runtime_roles']))
    if runtime_pointer['state_directory']!='state/local_continuation_queue_v1' or runtime_roles.get('status')!='ACTUAL_OWNERS_VERIFIED':raise RuntimeError('Current exact queue runtime roles missing')
    for role in runtime_roles['roles']:p.bind(role['source'])
    current_cli=p.read(p.bind(spec['current_event_CLI_launch']))
    if current_cli['event_sha256']!=EVENT or current_cli['identity']!=runtime_roles['current_CLI']['identity']:raise RuntimeError('Exact current event CLI differs')
    checkpoint('current_runtime_roles_and_event_CLI',{'roles':runtime_pointer['actual_runtime_roles'],'CLI_launch':spec['current_event_CLI_launch']})
    publish('Actual read-only Linux owner/group/namespace/loop/resource/registry and three-lease checks; no runtime opened')
    handles = []
    locks = [R / 'state/checkm2_pilot_launcher.lock', R / 'state/checkm2_install.lock']
    before = {x.relative_to(R).as_posix(): c.sha(x) for x in locks}
    try:
        for path in locks:
            handle = path.open('r+b'); handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except BaseException:
                handle.close(); raise
            handles.append(handle)
        linux_source = p.bind(spec['linux_observer_source']).read_text()
        input_linux = L + '/' + (E/'historical_targets.json').relative_to(R).as_posix()
        linux_code = linux_source.replace('__ROOT__', repr(L)).replace('__IDS__', 'json.loads(Path(' + repr(input_linux) + ").read_text())['Linux']").replace('__NS__', 'json.loads(Path(' + repr(input_linux) + ").read_text())['namespace_targets']")
        compile(linux_code, '<P20-read-only-resource-owner-lease-observer>', 'exec')
        linux = run(['wsl', '-d', 'Ubuntu', '--', '/usr/bin/env', 'PYTHONDONTWRITEBYTECODE=1', 'PYTHONNOUSERSITE=1',
                     '/usr/bin/python3', '-B', '-c', linux_code], 'actual_Linux_gates')
        checkpoint('Linux_full_raw_before_assertions', linux)
        if any(linux[k] for k in ('same_old_identities', 'old_groups', 'old_namespace_tasks', 'image_loop_associations', 'other_project_workers', 'other_scientific_workers')):
            raise RuntimeError('Existing Linux scientific owner/group/context/loop or project worker remains')
        if (linux['compute_lease_reacquired_released_bytes_unchanged'] is not True
                or linux['host_registry'] != c.read(R / 'evidence/checkm2_runtime/install_registry_before.json')
                or linux['image_before'] != linux['image_after'] or linux['image_before'] != anchor['Linux']['image_stat']
                or linux['linux_available_bytes'] < 1073741824 or len(linux['cpu_eligible']) < 2 or len(linux['observer_affinity']) > 2):
            raise RuntimeError('Linux lease/registry/image/headroom/CPU resource gate failed')
        shell = R / 'scripts/checkm2_saved_P20_v001.sh'
        raw = shell.read_bytes()
        if b'\r' in raw:
            raise RuntimeError('P20 actual shell contains CR bytes; do not admit')
        token = spec['benign_transport_token']
        observer = ("from pathlib import Path\nimport os,json,subprocess,hashlib\n"
                    "root=Path(" + repr(L) + ");token=" + repr(token) + "\n"
                    "assert os.environ.get('TREE2_P20_PRELAUNCH_TOKEN')==token\n"
                    "shell=root/'scripts/checkm2_saved_P20_v001.sh';raw=shell.read_bytes();assert bytes([13])not in raw\n"
                    "result=subprocess.run(['/bin/bash','-n',str(shell)],capture_output=True,text=True,timeout=10)\n"
                    "print(json.dumps({'token_matches':True,'explicit_env_transport':'/usr/bin/env','bash_n_exit_code_observed':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'shell_sha256':hashlib.sha256(raw).hexdigest(),'CR_bytes':raw.count(bytes([13])),'script_executed':False,'runtime_image_opened':False,'genome_or_model_work':False}))\n"
                    "assert result.returncode==0\n")
        transport = run(['wsl', '-d', 'Ubuntu', '--', '/usr/bin/env', 'TREE2_P20_PRELAUNCH_TOKEN=' + token,
                         'PYTHONDONTWRITEBYTECODE=1', 'PYTHONNOUSERSITE=1', '/usr/bin/python3', '-B', '-c', observer], 'actual_direct_env_and_bash_n')
        checkpoint('direct_env_and_bash_n_raw', transport)
        if (transport['token_matches'] is not True or type(transport['bash_n_exit_code_observed']) is not int
                or transport['bash_n_exit_code_observed'] != 0 or transport['CR_bytes'] != 0
                or transport['shell_sha256'] != c.sha(shell) or transport['script_executed'] is not False):
            raise RuntimeError('Actual no-CR/bash-n/direct explicit env observer failed')
    finally:
        for handle in reversed(handles):
            try:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                handle.close()
    after = {name: c.sha(R / name) for name in before}
    checkpoint('Windows_common_leases', {'before': before, 'after': after, 'both_reacquired_released': len(handles) == 2})
    if after != before:
        raise RuntimeError('Windows common lease bytes changed')
    roles = p.read('state/monitor_current_roles.json')
    live = [{**roles[name], 'role': name} for name in ('gui', 'collector', 'publisher')]
    for item in runtime_roles['roles']:
        expected={**item['identity'],'role':item['role'],'script':item['source']['path'],'script_sha256':item['source']['sha256']}
        live.append(expected)
    live.append({**current_cli['identity'],'role':'THIS_EVENT_HEADLESS_CLI','script':'codex.exe'})
    ids = sorted({x['pid'] for x in live + targets['Windows']})
    command = ("$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(" + ','.join(map(str, ids))
               + ") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe','powershell.exe','pwsh.exe','codex.exe'))} | ForEach-Object {$p=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue;if($p){[pscustomobject]@{pid=$_.ProcessId;parent_pid=$_.ParentProcessId;name=$_.Name;birth=$_.CreationDate.ToUniversalTime().ToString('o');command=$_.CommandLine;responding=$p.Responding;window_handle=[int64]$p.MainWindowHandle}}})|ConvertTo-Json -Compress")
    windows = run(['pwsh', '-NoProfile', '-Command', command], 'actual_Windows_GUI_and_owner_gates')
    windows = windows if isinstance(windows, list) else [windows]
    checkpoint('Windows_raw_CIM_before_birth_assertions', windows)
    for value in windows:
        retained = HELPERS.retained_child_at_cim(value, CHILDREN)
        if retained is not None:
            value['exact_native_identity'] = retained['captured_exact_identity']
            value['retained_child_exit_evidence'] = retained
            continue
        handle = HELPERS.K.OpenProcess(0x1000, False, value['pid'])
        if handle:
            try:
                value['exact_native_identity'] = HELPERS.identity(handle, value['pid'])
            finally:
                HELPERS.K.CloseHandle(handle)
        else:
            value['protected_old_pid_reuse_evidence'] = HELPERS.protected_old_pid_reuse(value, targets['Windows'], {x['pid'] for x in live}, ctypes.get_last_error())
    checkpoint('Windows_exact_owner_observations', windows)
    for expected in live:
        current = next(x for x in windows if x['pid'] == expected['pid'])
        observed = current.get('exact_native_identity', {})
        marker = Path(expected['script']).name
        if (observed.get('creation_time_utc') != expected['creation_time_utc']
                or observed.get('windows_creation_filetime_100ns') != expected['windows_creation_filetime_100ns']
                or marker not in (current.get('command') or '') or 'TREE2_WD_20261026' not in current['command']
                or current['responding'] is not True):
            raise RuntimeError('Current mandatory monitor/controller exact birth/command gate failed: ' + expected['role'])
        if expected['role'] == 'gui' and current['window_handle'] == 0:
            raise RuntimeError('Mandatory visible GUI window absent')
        if 'script_sha256' in expected and c.sha(R / expected['script']) != expected['script_sha256']:
            raise RuntimeError('Current monitor script hash changed')
        if expected['role']=='THIS_EVENT_HEADLESS_CLI':
            dispatcher=next(x for x in runtime_roles['roles']if x['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER')
            if current['parent_pid']!=dispatcher['identity']['pid'] or str(c.path(spec['current_event_CLI_launch']['path']).parent)not in current['command'] or '--disable plugins'not in current['command']:
                raise RuntimeError('This event CLI ancestry/argv/launch differs; no generic Codex exemption')
        if expected['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':
            supervisor=next(x for x in runtime_roles['roles']if x['role']=='ROOT_EXTERNAL_DISPATCHER_SUPERVISOR')
            if current['parent_pid']!=supervisor['identity']['pid']:raise RuntimeError('Current dispatcher supervisor ancestry differs')
    if any(now['pid'] == old['pid'] and now.get('exact_native_identity', {}).get('windows_creation_filetime_100ns') == old['windows_creation_filetime_100ns'] for now in windows for old in targets['Windows']):
        raise RuntimeError('Historical native scientific/source owner remains live at its original birth')
    excluded = {OWNER['pid']} | {x['pid'] for x in live} | {x['identity']['pid'] for x in CHILDREN}
    suspects = [x for x in windows if x['pid'] not in excluded and x['name'].lower() in ('python.exe', 'wsl.exe', 'codex.exe') and 'TREE2_WD_20261026' in (x.get('command') or '')]
    checkpoint('unexpected_current_native_workers', suspects)
    if suspects:
        raise RuntimeError('Another project native worker is active; no competing scientific launch')
    if before_image != image_stat():
        raise RuntimeError('Windows image metadata changed during read-only preflight')
    for value in spec['bound_inputs']:
        bounded(); p.bind(value)
    c.plan_gate(c.bind(spec['input_plan']), spec['input_plan']['sha256'], require_admission=False,closed_finalization=True)
    repair.plan_gate(c.bind(spec['saved_runtime_plan']),spec['saved_runtime_plan']['sha256'],require_admission=False,closed_finalization=True)
    bounded()
    if any(x.split('.')[0] in ('numpy', 'pandas', 'tensorflow', 'sklearn', 'lightgbm', 'checkm2') for x in sys.modules):
        raise RuntimeError('Forbidden scientific/model library imported by read-only preflight')
    return {'status': 'ACTUAL_SAVED_P20_PREFLIGHT_PASS_REQUIRES_NATIVE_ADMISSION', 'native_owner': OWNER,
            'completed_utc': p.dispatcher.utc(), 'actual_children': CHILDREN, 'input_plan': spec['input_plan'],
            'source_manifest': plan['source_manifest'], 'all190_sources_and20_FNA_integrity_pass': True,
            'full_novelty_history_and_masks_preserved': True, 'old_identity_group_namespace_and_loop_targets_absent': True,
            'three_common_leases_freshly_reacquired_released_stable_bytes': True,
            'Linux_minimum_available_bytes_observed': linux['linux_available_bytes'],
            'direct_env_and_bash_n': transport, 'mandatory_current_monitor_and_dispatcher_roles_exact': True,
            'Windows_image_before': before_image, 'Windows_image_after': image_stat(),
            'Windows_C_free_bytes': shutil.disk_usage(R).free, 'no_image_content_model_pickle_runtime_or_science': True,
            'scientific_Ready_or_claim_issued': False, 'scientific_execution_authorized': False}


def main(args):
    global WIN, OWNER, HELPERS, DEADLINE
    if os.name != 'nt' or os.environ.get('COMPUTERNAME', '').upper() != 'WD':
        raise RuntimeError('WD-only actual preflight')
    if p.dispatcher.digest(p.inside(args.admission)) != args.admission_sha256:
        raise RuntimeError('Read-only preflight admission hash mismatch')
    spec = p.read(args.admission)
    if spec['status']!='ROOT_ADMITTED_ONE_SAVED_P20_READ_ONLY_PREFLIGHT_V001' or spec['event_sha256']!=EVENT or spec['scientific_execution_authorized']is not False or p.bind(spec['preflight_source'])!=Path(__file__).resolve():
        raise RuntimeError('Separate current source-bound preflight grant required')
    for value in spec['bound_inputs']:
        p.bind(value)
    module = importlib.util.spec_from_file_location('accepted_N5_preflight_OS_helpers', p.bind(spec['Windows_helpers_source']))
    HELPERS = importlib.util.module_from_spec(module); module.loader.exec_module(HELPERS)
    WIN = p.dispatcher.Windows(); mask = p.affinity(WIN)
    OWNER = WIN.identity(WIN.k.GetCurrentProcess(), os.getpid())
    lock = (R / 'state/checkm2_phase_separated_P20_preflight.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0'); lock.flush()
    lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    error = None; result = None; code = 2
    try:
        p.create(E / 'launch.json', {'schema': 'TREE2_SAVED_P20_ACTUAL_PREFLIGHT_LAUNCH_V001', 'native_owner': OWNER,
            **OWNER, 'role': ROLE, 'script': str(Path(__file__).resolve()), 'source': p.row(Path(__file__).resolve()),
            'admission': p.row(args.admission), 'started_utc': p.START, 'affinity_mask': mask,
            'attach_timeout_seconds': 180, 'actual_preflight_timeout_seconds': 90, 'scientific_execution_authorized': False,
            'stdout': str(E / 'owner.stdout.txt'), 'stderr': str(E / 'owner.stderr.txt')})
        publish('Fresh saved-P20 file/OS preflight; waiting for exact current-namespace retained-handle ACK', 'RUNNING')
        attach_deadline=time.monotonic()+180
        directory=R/p.read('state/local_continuation_current_runtime.json')['state_directory']
        while True:
            try:
                ack=p.dispatcher.read(directory/'early_attach_ack.json')
                if ack.get('event_sha256')==EVENT and ack.get('exact_handle_retained')is True and all(ack['worker'].get(k)==v for k,v in OWNER.items()):break
            except FileNotFoundError:pass
            if time.monotonic()>attach_deadline:raise TimeoutError('Exact current-namespace ACK absent; no observer dispatched')
            time.sleep(.25)
        DEADLINE = time.monotonic() + 90
        result = checks(spec)
        result['observations'] = p.row(E / 'observations.json')
        p.create(E / 'receipt.json', result)
        code = 0
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'error': str(failure), 'traceback': traceback.format_exc()}
    finally:
        try:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            lock.close()
        terminal = {'schema': 'TREE2_SAVED_P20_PREFLIGHT_TERMINAL_V001',
            'status': result['status'] if result else 'P20_ACTUAL_PREFLIGHT_FAILED_PRESERVE_NO_RETRY_NO_SCIENCE',
            'native_owner': OWNER, 'actual_native_exit': 'PENDING_CURRENT_DISPATCHER_RETAINED_HANDLE_OBSERVATION', 'ended_utc': p.dispatcher.utc(),
            'actual_children': CHILDREN, 'error': error, 'result': p.row(E / 'receipt.json') if result else None,
            'owner_lease_descriptor_released': True, 'maximum_native_RSS_bytes': p.PEAK_NATIVE_RSS,
            'elapsed_seconds': time.monotonic() - p.STARTED, 'scientific_Ready_issued_or_execution_authorized': False,
            'runtime_image_content_mount_model_pickle_annotation_search_or_prediction_run': False}
        p.create(E / 'terminal.json', terminal)
        publish('Actual prelaunch checks passed; retained native exit and separate Root scientific admission still required' if code == 0 else 'Read-only preflight failed; precise observations/owned child identities preserved; no retry or science',
                'PENDING_PREFLIGHT_NATIVE_EXIT_AND_ROOT_ADMISSION' if code == 0 else 'FAILED_PREFLIGHT_NO_RETRY', p.row(E / 'terminal.json'))
        print(json.dumps(terminal), flush=True)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission', required=True)
    parser.add_argument('--admission-sha256', required=True)
    raise SystemExit(main(parser.parse_args()))
