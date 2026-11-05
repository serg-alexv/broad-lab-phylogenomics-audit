"""HELD retained Windows owner for ONE <=60s non-genomic proof; no monitor changes."""
from pathlib import Path
import argparse,ctypes,datetime,hashlib,json,msvcrt,os,shutil,subprocess,sys,time
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[1]
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    with tmp.open('x',encoding='utf-8',newline='\n') as handle:json.dump(value,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    os.replace(tmp,path)
def inside(value):
    value=(ROOT/Path(value)).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    if not value.is_relative_to(ROOT):raise RuntimeError('Proof path escapes project')
    return value
def linux(path):return '/mnt/c/'+str(inside(path))[3:].replace('\\','/')
class FILETIME(ctypes.Structure):_fields_=[('low',wintypes.DWORD),('high',wintypes.DWORD)]
def identity(handle,pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(FILETIME)]*4
    created,ended,kern,user=FILETIME(),FILETIME(),FILETIME(),FILETIME()
    if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kern),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
    ticks=(created.high<<32)|created.low;sec,rem=divmod(ticks,10000000)
    born=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=sec)
    return {'pid':pid,'creation_time_utc':born.strftime('%Y-%m-%dT%H:%M:%S')+f'.{rem:07d}Z','windows_creation_filetime_100ns':ticks}
def main(args):
    started=time.monotonic()
    if os.name!='nt' or os.environ.get('COMPUTERNAME','').upper()!='WD' or not Path(sys.argv[0]).is_absolute():raise RuntimeError('Absolute WD native proof invocation required')
    plan_path=inside(args.source_plan)
    if sha(plan_path)!=args.source_plan_sha256:raise RuntimeError('Proof plan SHA differs')
    plan=read(plan_path)
    for item in plan['sources']:
        path=inside(item['path'])
        if sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:raise RuntimeError('Exact proof source mismatch')
    admission_path=inside(args.admission);admission=read(admission_path);token=admission['token']
    if (admission.get('schema')!='TREE2_S1R2_OBSERVER_PROOF_ADMISSION_V001' or admission.get('status')!='ADMITTED_ONE_NON_GENOMIC_PERMISSION_OBSERVER_PROOF' or admission.get('non_genomic_proof_execution_authorized') is not True or admission.get('source_plan_sha256')!=args.source_plan_sha256):raise RuntimeError('No exact Root proof execution admission')
    if len(token)!=32 or any(char not in '0123456789abcdef' for char in token):raise RuntimeError('Proof token differs')
    if shutil.disk_usage(ROOT).free<42949672960:raise RuntimeError('40GiB reserve required')
    folder=ROOT/'evidence/checkm2_S1R2_observer_proof'/token;folder.mkdir(parents=True,exist_ok=False)
    with (folder/'once_claim.json').open('x',encoding='utf-8') as handle:json.dump({'token':token,'admission_sha256':sha(admission_path),'source_plan_sha256':args.source_plan_sha256,'at_utc':utc()},handle);handle.flush();os.fsync(handle.fileno())
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
    owner=identity(kernel.GetCurrentProcess(),os.getpid());child=None;child_id=None;error=None;locks=[];actual_code=None;result=None;release_errors=[]
    try:
        for name in ('checkm2_pilot_launcher.lock','checkm2_install.lock'):
            handle=(ROOT/'state'/name).open('r+b')
            try:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except BaseException:handle.close();raise
            locks.append(handle)
        command=['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B',linux(ROOT/'scripts/checkm2_S1R2_observer_proof.py'),'--mode','supervise','--source-plan',linux(plan_path),'--source-plan-sha256',args.source_plan_sha256,'--admission',linux(admission_path),'--run-directory',linux(folder),'--token',token]
        save(folder/'native_launch.json',{'native_owner':owner,'command':command,'started_utc':utc(),'role':'NON_GENOMIC_FAULT_INJECTION_ONLY','standard04_changed':False})
        with (folder/'wsl_stdout.txt').open('w') as out,(folder/'wsl_stderr.txt').open('w') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err);child_id=identity(int(child._handle),child.pid)
            save(folder/'wsl_child_identity.json',child_id)
            while child.poll() is None:
                if time.monotonic()-started>58:raise TimeoutError('58s native proof bound; WSL is not a Linux-closure proxy')
                time.sleep(.1)
            actual_code=child.wait()
        result=read(folder/'linux_result.json')
        for item in plan['sources']:
            if sha(inside(item['path']))!=item['sha256']:raise RuntimeError('Proof source bytes changed during run')
        if actual_code!=0 or result['status']!='S1R2_NON_GENOMIC_PROOF_PASS_CLOSED' or result['owned_cleanup'].get('closure_proven') is not True or result['owned_cleanup'].get('forced_action') is not False:raise RuntimeError('Proof did not actually close/pass')
    except BaseException as exception:
        import traceback
        error={'type':type(exception).__name__,'str':str(exception),'repr':repr(exception),'errno':getattr(exception,'errno',None),'filename':getattr(exception,'filename',None),'traceback':traceback.format_exc()}
        if child is not None and child.poll() is None:
            try:save(folder/'OWNED_PROOF_STOP',{'owner_token':token,'reason':'NATIVE_PROOF_ERROR','at_utc':utc()})
            except BaseException as secondary:error['secondary_STOP_write_error']={'type':type(secondary).__name__,'str':str(secondary),'errno':getattr(secondary,'errno',None),'traceback':traceback.format_exc()}
    finally:
        if child is not None and child.poll() is not None:actual_code=child.wait();child._handle.Close()
        for handle in reversed(locks):
            try:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            except BaseException as release_error:release_errors.append({'type':type(release_error).__name__,'str':str(release_error),'operation':'required common Windows lease release'})
            finally:handle.close()
    success=error is None and not release_errors and type(actual_code) is int and actual_code==0
    receipt={'status':'S1R2_NON_GENOMIC_PROOF_PENDING_EXTERNAL_NATIVE_EXIT' if success else 'FAILED_OR_UNKNOWN_DO_NOT_RELAUNCH','at_utc':utc(),'elapsed_seconds':time.monotonic()-started,'native_owner':owner,'actual_native_exit':'NOT_OBSERVABLE_BY_SELF','wsl_child_identity':child_id,'actual_wsl_exit_code':actual_code,'wsl_actual_handle_reaped':actual_code is not None,'error':error,'common_Windows_lease_release_errors':release_errors,'linux_result_sha256':sha(folder/'linux_result.json') if (folder/'linux_result.json').exists() else None,'linux_result':result,'source_plan_sha256':args.source_plan_sha256,'no_science_or_runtime_mounts':True,'no_standard04_or_S1R2_Ready_writes':True}
    save(folder/'native_result_pending_owner_exit.json',receipt)
    if not success:
        with (folder/'native_unresolved_owner_handoff.json').open('x',encoding='utf-8') as handle:handle.write(json.dumps(receipt)+'\n');handle.flush();os.fsync(handle.fileno())
    return 0 if success else 1
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('source-plan','source-plan-sha256','admission'):parser.add_argument('--'+name,required=True)
    raise SystemExit(main(parser.parse_args()))
