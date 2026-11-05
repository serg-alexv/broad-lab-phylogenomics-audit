"""Bounded source-gated breakaway launch. No scheduler, credentials or science method logic."""
from pathlib import Path
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import subprocess
import sys
import uuid

import local_tree2_dispatcher as b

R=Path(__file__).resolve().parents[1]
BREAKAWAY=0x01000000
NEW_PROCESS_GROUP=0x00000200
NO_WINDOW=0x08000000
ROLES=('LOCAL_TREE2_RUNTIME_CONTROLLER','SCIENTIFIC_NATIVE_WORKER','BENIGN_PERSISTENCE_FIXTURE')

class BASIC(ctypes.Structure):
    _fields_=[('process_user',ctypes.c_int64),('job_user',ctypes.c_int64),('flags',wintypes.DWORD),
      ('minimum_working',ctypes.c_size_t),('maximum_working',ctypes.c_size_t),('active_process_limit',wintypes.DWORD),
      ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
class IO(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint64) for name in ('read_count','write_count','other_count','read_bytes','write_bytes','other_bytes')]
class EXTENDED(ctypes.Structure):
    _fields_=[('basic',BASIC),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
      ('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]

def argv_hash(arguments):
    return hashlib.sha256(json.dumps(arguments,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()

def relinquish_child_handle(child):
    # This intentionally relinquishes lifetime ownership without inventing an exit.
    if child is not None:
        handle=getattr(child,'_handle',None)
        if handle is not None:
            handle.Close();child._handle=None
        child._child_created=False

def in_job(kernel,handle):
    value=wintypes.BOOL()
    kernel.k.IsProcessInJob.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(wintypes.BOOL)]
    if not kernel.k.IsProcessInJob(handle,None,ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bool(value.value)

def current_job(kernel):
    current=ctypes.c_void_p(-1)
    associated=in_job(kernel,current)
    if not associated:return {'in_any_job':False,'explicit_breakaway_allowed_or_unneeded':True}
    info=EXTENDED();length=wintypes.DWORD()
    kernel.k.QueryInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    if not kernel.k.QueryInformationJobObject(None,9,ctypes.byref(info),ctypes.sizeof(info),ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    flags=int(info.basic.flags)
    return {'in_any_job':True,'limit_flags':flags,'kill_on_job_close':bool(flags&0x2000),
      'breakaway_ok':bool(flags&0x800),'silent_breakaway_ok':bool(flags&0x1000),
      'explicit_breakaway_allowed_or_unneeded':bool(flags&0x800)}

class PID_LIST(ctypes.Structure):
    _fields_=[('assigned',wintypes.DWORD),('listed',wintypes.DWORD),('pids',ctypes.c_size_t*4096)]

def current_job_snapshot(kernel):
    result=current_job(kernel)
    result['query_scope']='IMMEDIATE_CURRENT_JOB_AND_ITS_DESCENDANT_JOBS'
    result['all_ancestor_jobs_enumerated']=False
    if not result['in_any_job']:
        result.update(process_ids=[],process_list_complete=True)
        return result
    values=PID_LIST();length=wintypes.DWORD()
    if not kernel.k.QueryInformationJobObject(None,3,ctypes.byref(values),ctypes.sizeof(values),ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    if values.assigned!=values.listed or values.listed>4096:
        raise RuntimeError('Incomplete current-job PID list; isolation remains unproven')
    pids=[int(values.pids[index]) for index in range(values.listed)]
    if os.getpid() not in pids:
        raise RuntimeError('Current caller missing from its own job census')
    result.update(process_ids=pids,process_list_complete=True)
    return result

def isolation_verdict(job,child_pid,child_in_any_job,child_still_live):
    if child_still_live is not True:
        return {'verified':False,'basis':'CHILD_NOT_OBSERVED_LIVE','all_ancestor_jobs_enumerated':False}
    if child_in_any_job is False:
        return {'verified':True,'basis':'CHILD_HAS_NO_JOB','all_ancestor_jobs_enumerated':False}
    complete=(job.get('in_any_job') is True and job.get('process_list_complete') is True
      and isinstance(job.get('process_ids'),list) and child_pid not in job['process_ids'])
    return {'verified':bool(complete),'basis':'CHILD_ABSENT_FROM_COMPLETE_CALLER_JOB_AND_DESCENDANTS' if complete
      else 'CURRENT_CALLER_JOB_ESCAPE_UNPROVEN','all_ancestor_jobs_enumerated':False}


def validate_contract(contract,root):
    if contract.get('schema')!='TREE2_DETACHED_NATIVE_LAUNCH_CONTRACT_V001':
        raise RuntimeError('Unknown detached launch contract')
    if Path(contract.get('project_root','')).resolve()!=root:
        raise RuntimeError('Detached child CWD must be the exact project')
    role=contract.get('role')
    if role not in ROLES:raise RuntimeError('Unknown detached launch role')
    arguments=contract.get('arguments')
    if not isinstance(arguments,list) or not all(isinstance(x,str) and '\0' not in x for x in arguments):
        raise RuntimeError('Explicit native argv string list required')
    if contract.get('argument_vector_sha256')!=argv_hash(arguments):
        raise RuntimeError('Approved argument vector hash differs')
    if contract.get('no_automatic_duplicate_or_retry') is not True:
        raise RuntimeError('Once-only detached launch scope required')
    if role=='SCIENTIFIC_NATIVE_WORKER' and not isinstance(contract.get('scientific_admission'),dict):
        raise RuntimeError('Scientific launch requires its separate source-bound admission')
    return role

def launch(contract_path,contract_sha,execute=False):
    if os.name!='nt' or os.environ.get('COMPUTERNAME','').upper()!='WD':
        raise RuntimeError('WD Windows native launcher required')
    contract_path=b.bind(R,{'path':contract_path,'sha256':contract_sha})
    contract=b.read(contract_path);role=validate_contract(contract,R)
    entry=b.bind(R,contract['entry_source'])
    executable=Path(contract['executable']['path'])
    if not executable.is_absolute():raise RuntimeError('Approved executable must use an absolute path')
    executable=executable.resolve()
    if not executable.is_file() or b.digest(executable)!=contract['executable']['sha256']:
        raise RuntimeError('Approved native executable differs')
    arguments=contract['arguments']
    linux_entry='/mnt/'+entry.drive[0].lower()+'/'+entry.relative_to(entry.anchor).as_posix() if entry.drive else ''
    if str(entry) not in arguments and linux_entry not in arguments and executable!=entry:
        raise RuntimeError('Hash-bound entry source is not the invoked native argv entry')
    grant=b.read(b.bind(R,contract['caller_grant']))
    if (grant.get('detached_launch_authorized') is not True
      or grant.get('entry_source_sha256')!=contract['entry_source']['sha256']
      or grant.get('argument_vector_sha256')!=contract['argument_vector_sha256']
      or grant.get('role')!=role):
        raise RuntimeError('Separate reviewed caller grant does not bind this exact source/argv/role')
    if role=='SCIENTIFIC_NATIVE_WORKER':b.bind(R,contract['scientific_admission'])
    for item in contract.get('bound_configurations',[]):b.bind(R,item)
    if contract.get('launcher_source_sha256')!=b.digest(Path(__file__).resolve()):
        raise RuntimeError('Reviewed detached launcher source changed')
    directory=b.inside(R,contract['registration_directory'])
    stdout=b.inside(R,contract['stdout_path']);stderr=b.inside(R,contract['stderr_path'])
    if stdout==stderr:raise RuntimeError('Separate project-owned stdout/stderr files required')
    if not execute:return {'status':'SOURCE_CONTRACT_VERIFIED_LAUNCH_HELD','role':role,'no_child_launched':True}
    if contract.get('status')!='ROOT_ADMITTED_ONE_DETACHED_NATIVE_LAUNCH':
        raise RuntimeError('Actual detached launch requires separate Root admission, not a held contract')
    kernel=b.Windows();owner=kernel.identity(ctypes.c_void_p(-1),os.getpid());job=current_job(kernel)
    if not job['explicit_breakaway_allowed_or_unneeded']:
        raise RuntimeError('Current job forbids explicit breakaway; no automatic fallback or child start')
    directory.mkdir(parents=True,exist_ok=True)
    claim=directory/('contract_'+contract_sha+'_once.json')
    b.exclusive(claim,{'contract':b.row(R,contract_path),'role':role,'launcher_owner':owner,
      'current_job':job,'claimed_utc':b.utc(),'actual_child_started':False,'no_automatic_retry':True})
    child=None;identity=None;child_job=None
    try:
        for path in (stdout,stderr):path.parent.mkdir(parents=True,exist_ok=True)
        with stdout.open('xb') as out,stderr.open('xb') as err:
            child=subprocess.Popen([str(executable),*arguments],cwd=R,stdin=subprocess.DEVNULL,
              stdout=out,stderr=err,creationflags=BREAKAWAY|NEW_PROCESS_GROUP|NO_WINDOW)
            identity=kernel.identity(int(child._handle),child.pid)
            child_job=in_job(kernel,int(child._handle))
            code=wintypes.DWORD()
            if not kernel.k.GetExitCodeProcess(int(child._handle),ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            child_live=code.value==259
            post_job=current_job_snapshot(kernel)
            isolation=isolation_verdict(post_job,child.pid,child_job,child_live)
            status='DETACHED_NATIVE_CREATION_REGISTERED' if isolation['verified'] else 'CHILD_JOB_ISOLATION_UNPROVEN_NO_RETRY'
            receipt={'schema':'TREE2_DETACHED_NATIVE_REGISTRATION_V002','status':status,
              'role':role,'native_owner':identity,'worker_identity':identity,'worker':{**identity,'role':role},
              'pid':identity['pid'],'creation_time_utc':identity['creation_time_utc'],
              'windows_creation_filetime_100ns':identity['windows_creation_filetime_100ns'],
              'launcher_owner':owner,'contract':b.row(R,contract_path),'entry_source':contract['entry_source'],
              'argument_vector_sha256':contract['argument_vector_sha256'],'caller_grant':contract['caller_grant'],
              'scientific_admission':contract.get('scientific_admission'),'creation_flags':BREAKAWAY|NEW_PROCESS_GROUP|NO_WINDOW,
              'parent_current_job':job,'caller_job_after_spawn':post_job,'child_in_any_job_at_registration':child_job,
              'child_still_live_at_registration':child_live,'isolation':isolation,
              'remaining_ancestor_job_lifetime':'NOT_ENUMERATED_REQUIRES_BOUND_BENIGN_PERSISTENCE_PROOF',
              'stdout_path':stdout.relative_to(R).as_posix(),'stderr_path':stderr.relative_to(R).as_posix(),
              'actual_child_exit':'UNKNOWN_UNTIL_SEPARATE_RETAINED_OS_OBSERVER',
              'registration_is_not_actual_exit_or_scientific_acceptance':True,
              'fast_helpers_require_their_own_ACK_or_retained_exit_recorder':True,'registered_utc':b.utc()}
            b.exclusive(directory/'launch.json',receipt)
        return {'status':status,'launch_receipt':b.row(R,directory/'launch.json'),'native_owner':identity,
          'child_in_any_job_at_registration':child_job,'isolation':isolation,'actual_child_exit':'UNKNOWN'}
    except BaseException as error:
        value={'status':'DETACHED_LAUNCH_FAILED_OR_REGISTRATION_UNPROVEN_NO_RETRY','launcher_owner':owner,
          'known_child_pid':child.pid if child else None,'known_creation_identity':identity,
          'child_in_any_job':child_job,'error_type':type(error).__name__,'error':str(error),
          'original_child_exit':'UNKNOWN','no_process_signal_or_duplicate_launch_authorized':True,'at_utc':b.utc()}
        try:b.exclusive(directory/'UNRESOLVED_LAUNCH.json',value)
        except OSError:sys.stderr.write(json.dumps(value)+'\n');sys.stderr.flush()
        raise
    finally:
        relinquish_child_handle(child)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--contract',required=True);parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();result=launch(args.contract,args.contract_sha256,args.execute)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['status'] in ('SOURCE_CONTRACT_VERIFIED_LAUNCH_HELD','DETACHED_NATIVE_CREATION_REGISTERED') else 2

if __name__=='__main__':raise SystemExit(main())
