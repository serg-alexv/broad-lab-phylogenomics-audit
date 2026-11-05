"""One reviewed Tree2 controller custody root; never launches or signals science.

launch reserves one detached custodian. custody retains the single supervisor
through its actual exit. No timeout or unknown outcome admits another process.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from tree2_activation_common_v008 import ROOT, atomic_json, load_json, now, win_identity, NativeProcess, source_status
from tree2_activation_common_v008 import exclusive_json as exclusive
import tree2_dispatcher_v008 as wiring

RUNTIME = Path(r'C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
RUNTIME_SHA = '17e6b9d2e702b43fd88154d9df419d32eab10728151f81d921bf32684ffd459e'
DIRECTORY = ROOT / 'metadata/defence_C008_recovery_20261105/controller_v008'
SUPERVISOR = ROOT / 'scripts/defence_controller_v008/tree2_supervisor_v008.py'
DISPATCHER = ROOT / 'scripts/defence_controller_v008/tree2_dispatcher_v008.py'
AUTHORITY = DIRECTORY / 'Root_authority.json'
OPERATOR_CLAIM = DIRECTORY / 'operator_launch_claim.json'
CREATION_CLAIM = DIRECTORY / 'supervisor_creation_claim.json'
REGISTRATION = DIRECTORY / 'custodian_registration.json'
READY = DIRECTORY / 'actual/custody_ready.json'
TERMINAL = DIRECTORY / 'actual/supervisor_terminal.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_row(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def runtime_row():
    return {'path':str(RUNTIME),'bytes':107312,'sha256':RUNTIME_SHA}


def gate():
    if (ROOT.resolve()!=wiring.HARNESS.resolve() or Path(__file__).resolve()!=ROOT/'scripts/defence_controller_v008/tree2_controller_launcher_v008.py'
        or Path(sys.executable).resolve()!=RUNTIME.resolve() or RUNTIME.stat().st_size!=107312 or digest(RUNTIME)!=RUNTIME_SHA):
        raise RuntimeError('Fixed root/launcher/runtime admission differs')
    authority=load_json(AUTHORITY)
    if (authority.get('schema')!='TREE2_CONTROLLER_FRESH_DEFENCE_ACTIVATION_V008'
        or authority.get('status')!='ROOT_ADMITTED_ATTACH_SEPARATELY_ADMITTED_DEFENCE_WORKER_ONLY'
        or authority.get('operator_launcher')!=public_row(Path(__file__))
        or authority.get('runtime')!=runtime_row()):
        raise RuntimeError('Reviewed controller launcher/authority/runtime differs')
    if any(type(authority.get(k)) is not int or authority[k]!=0 for k in
           ('initial_AI_calls','initial_science_launches','process_repairs_remaining')):
        raise RuntimeError('Attach-only source authority is required')
    wiring.require_runtime_sources(authority)
    admitted=source_status(ROOT)  # Current harness helper/runtime pins, no scientific state adoption.
    modules=wiring.load_reviewed_sources()
    b=modules['local_tree2_dispatcher']
    if digest(wiring.HANDOFF)!=authority['handoff']['sha256']:
        raise RuntimeError('Initial public handoff changed; no replay')
    handoff=b.validate_handoff(wiring.TREE2,b.read(wiring.HANDOFF),b.read(wiring.CONFIG)['required_complete_outputs'])
    if handoff.get('status')!='WAITING_WORKER' or handoff.get('worker')!=authority.get('expected_worker'):
        raise RuntimeError('Exact initial existing-worker handoff is required')
    if win_identity(handoff['worker']['pid'],handoff['worker']['windows_creation_filetime_100ns'])['state']!='LIVE_EXACT_IDENTITY':
        raise RuntimeError('Initial scientific worker is not exact and live; no replacement or exit inference')
    return authority,admitted,b


def own_identity(b):
    return b.Windows().identity(-1,os.getpid())


def retain(identity):
    return NativeProcess.open(identity['pid'],str(identity['windows_creation_filetime_100ns']))


def fixed_start(script, arguments):
    # -I -S excludes ambient PYTHONPATH, site/customize and user packages.
    # The only inserted directory is this reviewed project's fixed source root.
    directory=script.parent
    code=('import sys,runpy;sys.path.insert(0,'+repr(str(directory))+');'
          'sys.path.insert(0,'+repr(str(ROOT))+');sys.argv=['+repr(str(script))+']+sys.argv[1:];'
          'runpy.run_path('+repr(str(script))+',run_name="__main__")')
    return [str(RUNTIME),'-I','-S','-B','-c',code,*arguments]


def start_detached(argv, folder):
    configuration=creation_configuration()
    folder.mkdir(parents=True,exist_ok=False)
    with (folder/'stdout.log').open('xb') as out,(folder/'stderr.log').open('xb') as err:
        return subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
            close_fds=True,creationflags=configuration['flags'])


def job_observation(handle=None):
    from tree2_activation_common_v008 import kernel,ExtendedLimits
    k=kernel();k.GetCurrentProcess.restype=wintypes.HANDLE
    process=k.GetCurrentProcess() if handle is None else handle
    member=wintypes.BOOL()
    if not k.IsProcessInJob(process,None,ctypes.byref(member)):
        raise ctypes.WinError(ctypes.get_last_error())
    value={'in_any_job':bool(member.value)}
    if handle is None and member.value:
        limits=ExtendedLimits()
        if not k.QueryInformationJobObject(None,9,ctypes.byref(limits),ctypes.sizeof(limits),None):
            raise ctypes.WinError(ctypes.get_last_error())
        value.update(limit_flags=limits.Basic.Flags,kill_on_close=bool(limits.Basic.Flags&0x2000),
                     breakaway_allowed=bool(limits.Basic.Flags&0x800),silent_breakaway=bool(limits.Basic.Flags&0x1000))
        class PID_LIST(ctypes.Structure):
            _fields_=[('assigned',wintypes.DWORD),('listed',wintypes.DWORD),('pids',ctypes.c_size_t*4096)]
        pids=PID_LIST()
        if not k.QueryInformationJobObject(None,3,ctypes.byref(pids),ctypes.sizeof(pids),None):
            raise ctypes.WinError(ctypes.get_last_error())
        if pids.assigned!=pids.listed or pids.listed>4096:
            raise RuntimeError('Current caller job census is incomplete')
        values=[int(pids.pids[i]) for i in range(pids.listed)]
        if os.getpid() not in values:raise RuntimeError('Caller missing from its own current-job census')
        value.update(process_ids=values,process_list_complete=True,
            scope='CURRENT_CALLER_JOB_AND_DESCENDANT_JOBS',all_ancestor_jobs_enumerated=False)
    return value


def creation_configuration():
    caller=job_observation();flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP
    if not caller['in_any_job']:
        basis='CALLER_HAS_NO_JOB';flags|=subprocess.CREATE_BREAKAWAY_FROM_JOB
    elif caller.get('breakaway_allowed'):
        basis='EXPLICIT_CALLER_JOB_BREAKAWAY';flags|=subprocess.CREATE_BREAKAWAY_FROM_JOB
    elif caller.get('limit_flags')==0:
        # The known remaining host ancestor has no resource/kill-on-close flags.
        # It is shared deliberately; no claim of all-ancestor isolation is made.
        basis='SHARED_UNCONSTRAINED_CURRENT_JOB'
    else:raise RuntimeError('Current job cannot admit this bounded detached controller; no process: '+
        json.dumps({key:caller.get(key) for key in ('limit_flags','kill_on_close','breakaway_allowed','silent_breakaway')}))
    return {'caller':caller,'flags':flags,'basis':basis}


def isolation_proof(native,configuration):
    child=job_observation(native.handle);post=job_observation()
    if not child['in_any_job']:basis='CHILD_HAS_NO_JOB'
    elif (configuration['basis']=='EXPLICIT_CALLER_JOB_BREAKAWAY'
          and post.get('process_list_complete') and native.pid not in post['process_ids']):
        basis='CHILD_ABSENT_FROM_COMPLETE_CALLER_JOB_AND_DESCENDANTS'
    elif (configuration['basis']=='SHARED_UNCONSTRAINED_CURRENT_JOB'
          and post.get('limit_flags')==0 and post.get('process_list_complete')
          and native.pid in post['process_ids']):
        basis='SHARED_UNCONSTRAINED_JOB_NOT_KILL_ON_CLOSE'
    else:raise RuntimeError('Actual child job-lifetime isolation is unproved; no retry or signal')
    if native.exit_code() is not None:raise RuntimeError('Detached child already ended; no lifetime claim')
    return {'verified':True,'basis':basis,'configuration':configuration,'caller_after_spawn':post,
            'child_in_any_job':child['in_any_job'],'all_ancestor_jobs_enumerated':False,
            'remaining_ancestor_lifetime':'NOT_ENUMERATED; bounded benign caller-exit fixture required'}


def locks_contended():
    """Read-only fail-immediate observations, never creation or lock-file writes."""
    paths=[wiring.TREE2/'state/local_continuation_dispatcher.lock',
           wiring.STATE/'dispatcher.lock',wiring.STATE/'supervisor.lock']
    class OVERLAPPED(ctypes.Structure):
        _fields_=[('Internal',ctypes.c_size_t),('InternalHigh',ctypes.c_size_t),
                  ('Offset',wintypes.DWORD),('OffsetHigh',wintypes.DWORD),('hEvent',wintypes.HANDLE)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    k.CreateFileW.restype=wintypes.HANDLE
    k.LockFileEx.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(OVERLAPPED)]
    k.LockFileEx.restype=wintypes.BOOL
    k.UnlockFileEx.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(OVERLAPPED)]
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    result=[]
    for path in paths:
        handle=k.CreateFileW(str(path),0x80000000,7,None,3,0,None)
        if handle in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
        try:
            ov=OVERLAPPED()
            if k.LockFileEx(handle,3,0,1,0,ctypes.byref(ov)):
                k.UnlockFileEx(handle,0,1,0,ctypes.byref(ov))
                raise RuntimeError('A required controller lease is not retained: '+str(path))
            error=ctypes.get_last_error()
            if error!=33:raise ctypes.WinError(error)
            result.append({'path':str(path),'exclusive_probe':'CONTENDED','winerror':error,'file_content_modified':False})
        finally:k.CloseHandle(handle)
    return result


def validate_ack(ack,authority,supervisor,b):
    if (ack.get('schema')!='TREE2_V008_EXACT_RETAINED_ATTACH_ACK'
        or ack.get('worker_identity')!=authority['expected_worker']
        or ack.get('supervisor_owner')!=supervisor
        or ack.get('authority')!=public_row(AUTHORITY)
        or ack.get('core_source')!=public_row(DISPATCHER)
        or ack.get('retained_handle_identity_verified') is not True
        or ack.get('handle_unsignaled_at_attachment') is not True
        or type(ack.get('initial_AI_calls')) is not int or ack['initial_AI_calls']!=0
        or type(ack.get('initial_science_launches')) is not int or ack['initial_science_launches']!=0):
        raise RuntimeError('Required exact retained-attachment ACK differs')
    identity=ack['dispatcher_owner'];native=retain(identity)
    try:
        if native.exit_code() is not None:raise RuntimeError('Acknowledged dispatcher already exited')
        rows=wiring.process_rows_for_review() if hasattr(wiring,'process_rows_for_review') else None
        # The frozen module's native metadata census supplies exact current parent relation.
        if rows is None:
            modules=wiring.load_reviewed_sources();rows=modules['local_tree2_dispatcher_v003'].process_rows(b.Windows())
        matches=[row for row in rows if row['pid']==identity['pid']]
        if len(matches)!=1 or matches[0]['parent_pid']!=supervisor['pid']:
            raise RuntimeError('Dispatcher is not the current owned supervisor child')
        worker=retain(authority['expected_worker'])
        try:
            if worker.exit_code() is not None:raise RuntimeError('Scientific worker exited before operational acceptance')
        finally:worker.close()
        return locks_contended()
    finally:native.close()


def verify_custodian_origin(claim,owner,b):
    parent=claim['operator_owner']
    if os.getppid()!=parent['pid']:
        raise RuntimeError('Direct custody invocation is not the claimed operator child')
    retained=retain(parent)
    try:
        deadline=time.monotonic()+5
        path=DIRECTORY/'actual/custodian_started.json'
        while not path.exists():
            if retained.exit_code() is not None:
                raise RuntimeError('Operator ended before custody creation proof; no supervisor creation')
            if time.monotonic()>=deadline:
                raise RuntimeError('No exact custodian creation proof within5s; no retry')
            time.sleep(.05)
        proof=load_json(path)
        if (proof.get('custodian_owner')!=owner or proof.get('authority_sha256')!=digest(AUTHORITY)
            or proof.get('operator_claim')!=public_row(OPERATOR_CLAIM)
            or proof.get('creation_handle_retained') is not True
            or proof.get('job_isolation',{}).get('verified') is not True
            or retained.exit_code() is not None):
            raise RuntimeError('Actual operator/custodian creation binding differs')
    finally:retained.close()


def dispatcher_closure(supervisor,b):
    """Bind available exact direct-child receipts; never equate them to science closure."""
    directory=wiring.STATE/'supervisor_attempts'
    paths=list(directory.glob('*_started.json'))
    if len(paths)>128:raise RuntimeError('Controller attempt inventory exceeds fixed bound')
    matches=[]
    for path in paths:
        started=load_json(path)
        if started.get('supervisor_owner')!=supervisor:continue
        end=path.with_name(path.name.removesuffix('_started.json')+'_actual_exit.json')
        if not end.exists():
            matches.append({'started':public_row(path),'state':'UNKNOWN_NO_ACTUAL_EXIT_RECEIPT'});continue
        terminal=load_json(end)
        valid=(terminal.get('schema')=='TREE2_RETAINED_DISPATCHER_ACTUAL_EXIT_V003'
            and terminal.get('supervisor_owner')==supervisor
            and terminal.get('dispatcher_owner')==started.get('dispatcher_owner')
            and terminal.get('core_source')==public_row(DISPATCHER)
            and terminal.get('config')==started.get('config')
            and terminal.get('private_config')==started.get('private_config')
            and type(terminal.get('actual_exit_code')) is int
            and terminal.get('retained_handle_reaped') is True
            and terminal.get('child_handles_closed') is True
            and terminal.get('science_killed_or_replayed') is False)
        matches.append({'started':public_row(path),'actual_exit':public_row(end),
            'dispatcher_owner':terminal.get('dispatcher_owner'),'actual_exit_code':terminal.get('actual_exit_code'),
            'state':'RECORDED_EXACT_DIRECT_CHILD_EXIT' if valid else 'UNKNOWN_RECEIPT_JOIN_FAILED'})
    return {'state':'RECORDED_EXACT_DIRECT_CHILD_EXIT' if len(matches)==1 and matches[0]['state']=='RECORDED_EXACT_DIRECT_CHILD_EXIT' else 'UNKNOWN',
        'attempts':matches,'all_descendant_or_scientific_scope_closed':False,
        'limitation':'Direct controller receipt only; no inferred CLI,guest,namespace,FD or scientific lease closure'}


def custodian():
    authority,admitted,b=gate();authority_hash=digest(AUTHORITY)
    claim=load_json(OPERATOR_CLAIM)
    if claim.get('authority_sha256')!=authority_hash or claim.get('launcher_source')!=public_row(Path(__file__)):
        raise RuntimeError('One-shot outer launch claim differs')
    owner=own_identity(b)
    verify_custodian_origin(claim,owner,b)
    exclusive(REGISTRATION,{'schema':'TREE2_V008_CUSTODIAN_REGISTRATION_V1','at':now(),
        'custodian_owner':owner,'authority_sha256':authority_hash,'launcher_source':public_row(Path(__file__)),
        'runtime':runtime_row(),'harness_source_admission_sha256':admitted['admission_sha256'],
        'custodian_own_terminal_after_operator_release':'UNKNOWN_UNLESS_INDEPENDENTLY_OBSERVED','automatic_retry':False})
    exclusive(CREATION_CLAIM,{'schema':'TREE2_V008_SUPERVISOR_CREATION_CLAIM_V1',
        'authority_sha256':authority_hash,'custodian_owner':owner,'supervisor_source':public_row(SUPERVISOR),
        'runtime':runtime_row(),'mode':'ONE_REVIEWED_SUPERVISOR_CREATION','at':now()})
    private=wiring.TREE2/authority['private_config']['path']
    arguments=['--config',str(wiring.CONFIG),'--cli-config',str(private),
               '--core-source',str(DISPATCHER),'--core-sha256',digest(DISPATCHER)]
    child=None;native=None;publication_error=None
    try:
        configuration=creation_configuration()
        child=start_detached(fixed_start(SUPERVISOR,arguments),ROOT/'work/defence_controller_v008/supervisor_native')
        native=NativeProcess.child(child)
        supervisor=b.Windows().identity(int(child._handle),child.pid)
        if native.executable.resolve()!=RUNTIME.resolve():raise RuntimeError('Owned supervisor runtime differs')
        isolation=isolation_proof(native,configuration)
        try:
            exclusive(DIRECTORY/'actual/supervisor_started.json',{'schema':'TREE2_V008_OWNED_SUPERVISOR_STARTED_V1',
                'at':now(),'custodian_owner':owner,'supervisor_owner':supervisor,
                'authority_sha256':authority_hash,'creation_claim':public_row(CREATION_CLAIM),
                'argv':fixed_start(SUPERVISOR,arguments),'creation_configuration':configuration,'job_isolation':isolation,
                'source':public_row(SUPERVISOR),'runtime':runtime_row(),'no_scientific_process_started':True})
        except Exception as exc:
            publication_error=repr(exc)  # Do not abandon a live retained child on required IO failure.
        while native.exit_code() is None:
            if not READY.exists() and publication_error is None:
                candidates=list((DIRECTORY/'actual').glob('dispatcher_*_attach.json'))
                if len(candidates)>4:publication_error='Ambiguous attachment evidence inventory'
                elif candidates:
                    try:
                        ack=load_json(candidates[0]);leases=validate_ack(ack,authority,supervisor,b)
                        exclusive(READY,{'schema':'TREE2_V008_CUSTODY_READY_V1','at':now(),
                            'custodian_owner':owner,'supervisor_owner':supervisor,'dispatcher_owner':ack['dispatcher_owner'],
                            'worker_identity':authority['expected_worker'],'attach_ack':public_row(candidates[0]),
                            'authority_sha256':authority_hash,'retained_supervisor_handle':True,
                            'three_controller_lease_probes':leases,'initial_AI_calls':0,'initial_science_launches':0})
                    except Exception as exc:publication_error=repr(exc)
            native.wait(1)
        actual=native.exit_code();popen_code=child.wait()
        if actual!=(popen_code & 0xffffffff):raise RuntimeError('Owned supervisor native/Popen exits differ')
        try:closure=dispatcher_closure(supervisor,b)
        except Exception as exc:closure={'state':'UNKNOWN','reason':repr(exc)}
        exclusive(TERMINAL,{'schema':'TREE2_V008_SUPERVISOR_ACTUAL_EXIT_V1','at':now(),
            'custodian_owner':owner,'supervisor_owner':supervisor,'actual_exit_code':actual,
            'retained_handle_waited':True,'popen_waited':True,'publication_error':publication_error,
            'authority_sha256':authority_hash,'source':public_row(SUPERVISOR),
            'recorded_dispatcher_closure':closure,
            'owned_descendant_scope':'NOT_ESTABLISHED_BY_SUPERVISOR_EXIT',
            'scientific_processes_signalled':False,'automatic_retry':False})
    finally:
        # A handle acquisition/receipt failure after creation does not permit a
        # replacement. Keep any creation handle until actual exit, even if ACK is held.
        if child is not None and child.poll() is None:
            child.wait()
        if native is not None:native.close()
    return 0


def launch():
    authority,admitted,b=gate();authority_hash=digest(AUTHORITY)
    configuration=creation_configuration()
    exclusive(OPERATOR_CLAIM,{'schema':'TREE2_V008_OPERATOR_CREATION_CLAIM_V1','at':now(),
        'authority_sha256':authority_hash,'operator_owner':own_identity(b),
        'launcher_source':public_row(Path(__file__)),'runtime':runtime_row(),
        'max_custodian_creations':1,'initial_AI_calls':0,'initial_science_launches':0,'retry_on_timeout':False})
    child=start_detached(fixed_start(Path(__file__),['custody']),ROOT/'work/defence_controller_v008/custodian_native')
    native=NativeProcess.child(child)
    created=b.Windows().identity(int(child._handle),child.pid)
    deadline=time.monotonic()+45
    try:
        isolation=isolation_proof(native,configuration)
        exclusive(DIRECTORY/'actual/custodian_started.json',{'schema':'TREE2_V008_CUSTODIAN_CREATED_V1',
            'at':now(),'custodian_owner':created,'creation_handle_retained':True,'authority_sha256':authority_hash,
            'launcher_source':public_row(Path(__file__)),'runtime':runtime_row(),
            'operator_claim':public_row(OPERATOR_CLAIM),'job_isolation':isolation})
        while time.monotonic()<deadline:
            actual=native.exit_code()
            if actual is not None:raise RuntimeError('Custodian exited during startup; actual code='+str(actual)+'; no retry')
            if READY.exists():
                ready=load_json(READY)
                if ready.get('custodian_owner')!=created or ready.get('authority_sha256')!=authority_hash:
                    raise RuntimeError('Custody ACK belongs to a different source/creation')
                supervisor=retain(ready['supervisor_owner'])
                try:
                    if supervisor.exit_code() is not None:raise RuntimeError('Supervisor ended before operator acceptance')
                    ack=load_json(Path(ready['attach_ack']['path']))
                    if public_row(Path(ready['attach_ack']['path']))!=ready['attach_ack']:
                        raise RuntimeError('Attachment ACK pin differs')
                    validate_ack(ack,authority,ready['supervisor_owner'],b)
                finally:supervisor.close()
                exclusive(DIRECTORY/'actual/operator_acceptance.json',{'schema':'TREE2_V008_OPERATOR_ACCEPTANCE_V1',
                    'at':now(),'custodian_owner':created,'custody_ready':public_row(READY),
                    'authority_sha256':authority_hash,'supervisor_lifetime_custody':'RETAINED_BY_CUSTODIAN_UNTIL_ACTUAL_EXIT',
                    'custodian_own_future_exit':'UNKNOWN_FROM_RELEASED_OPERATOR_HANDLE',
                    'scientific_processes_signalled':False,'initial_AI_calls':0,'initial_science_launches':0})
                print(json.dumps({'status':'EXACT_ATTACHED_AND_RETAINED','ready':ready},indent=2))
                return 0
            time.sleep(.25)
        raise RuntimeError('Custody observation exceeded45s; exact process may remain live; no retry or signal')
    finally:native.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('launch','custody'))
    action=parser.parse_args().action
    return launch() if action=='launch' else custodian()


if __name__=='__main__':
    raise SystemExit(main())
