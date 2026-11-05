"""Claim the completed cache handoff, install privately, audit, commit readiness."""
from pathlib import Path
import ctypes,datetime as dt,hashlib,json,os,shutil,subprocess,time
from ctypes import wintypes
import checkm2_private_setup_driver as private
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
L='/mnt/c/'+str(R)[3:].replace('\\','/')
EXPECTED='a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52'
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
class FILETIME(ctypes.Structure):_fields_=[('low',wintypes.DWORD),('high',wintypes.DWORD)]
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetCurrentProcess.restype=wintypes.HANDLE
K.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(FILETIME)]*4
def identity():
 c,e,k,u=FILETIME(),FILETIME(),FILETIME(),FILETIME()
 if not K.GetProcessTimes(K.GetCurrentProcess(),ctypes.byref(c),ctypes.byref(e),ctypes.byref(k),ctypes.byref(u)):raise ctypes.WinError(ctypes.get_last_error())
 ticks=(c.high<<32)|c.low;seconds,remainder=divmod(ticks,10_000_000)
 value=dt.datetime(1601,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(seconds=seconds)
 return {'pid':os.getpid(),'creation_time_utc':value.strftime('%Y-%m-%dT%H:%M:%S')+f'.{remainder:07d}Z','windows_creation_filetime_100ns':ticks}
def gate():
 if (R/'state/STOP').exists():raise RuntimeError('STOP requested')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Less than40GiB disk reserve')
def cache_quiescent():
 import msvcrt
 f=(R/'state/checkm2_cache.lock').open('r+b')
 try:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
 finally:f.close()
def publish(detail,done=0,total=4,status='RUNNING',**extra):
 save(R/'state/tool_setup_progress.json',{'status':status,'done':done,'total':total,'unit':'setup phases','detail':detail,
     'started_utc':START,'updated_utc':utc(),'pid':OWNER['pid'],'creation_time_utc':OWNER['creation_time_utc'],
     'log_path':str(R/'logs/checkm2_install.log'),**extra})
OWNER=identity();START=utc()
def main():
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only installer')
 import msvcrt
 lock=(R/'state/checkm2_install.lock').open('a+b')
 if lock.tell()==0:lock.write(b'0');lock.flush()
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 save(R/'state/launch_checkm2_installer_waiter.json',{**OWNER,'script':'scripts/checkm2_private_install_controller.py','role':'wait_for_validated_cache_handoff'})
 # Do not take live-progress ownership away from the package cache worker.
 deadline=time.monotonic()+7200
 while True:
  gate()
  if (E/'cache_handoff.json').exists() and (E/'cache_execution_receipt.json').exists():
   handoff=read(E/'cache_handoff.json');cache_exit=read(E/'cache_execution_receipt.json')
   if handoff.get('status')=='CACHE_AND_ARCHIVE_INSPECTION_COMPLETE' and cache_exit.get('status')=='COMPLETE':
    try:cache_quiescent();break
    except OSError:pass
  if time.monotonic()>deadline:raise RuntimeError('Cache handoff wait exceeded2hours')
  time.sleep(3)
 if sha(E/'resolved_packages.json')!=EXPECTED or handoff['resolved_manifest_sha256']!=EXPECTED:raise RuntimeError('Closure manifest changed')
 if handoff['package_count']!=133 or handoff['compressed_bytes']!=727128168:raise RuntimeError('Unexpected closure count/bytes')
 if handoff['outside_prefix_links_count']!=0:raise RuntimeError('Package has outside-prefix links')
 for key,hashkey in [('notice_manifest','notice_manifest_sha256'),('explicit_offline_file','explicit_offline_file_sha256'),('cache_receipt','cache_receipt_sha256')]:
  if sha(R/handoff[key])!=handoff[hashkey]:raise RuntimeError('Cache handoff artifact hash mismatch:'+key)
 if handoff['case_collision_count']:
  proof=read(E/'case_sensitive_directory_proof.json')
  if proof.get('status')!='PASS_PROJECT_DIRECTORY_CASE_SENSITIVITY' or not all(x['case_sensitive'] and x['nested_case_pair_preserved'] for x in proof['directories']):raise RuntimeError('Case sensitivity proof missing')
 if shutil.disk_usage(R).free<40*1024**3+2*int(handoff['regular_unpacked_bytes']):raise RuntimeError('Insufficient prefix/cache expansion reserve')
 save(R/'state/launch_tool_setup.json',{**OWNER,'script':'scripts/checkm2_private_install_controller.py','phase':'PRIVATE_OFFLINE_INSTALL_AND_SMOKE'})
 publish('Verifying completed133-package CPU cache before private installation; no user input required')
 records=read(E/'resolved_packages.json');explicit=[]
 for i,row in enumerate(records):
  gate();p=R/'work/checkm2_resolution/channels'/row['channel_name']/row['subdir']/row['fn']
  if row['channel_name'] not in ('conda-forge','bioconda') or row['subdir'] not in ('linux-64','noarch') or Path(row['fn']).name!=row['fn']:raise RuntimeError('Invalid package path')
  if p.stat().st_size!=row['size'] or sha(p)!=row['sha256']:raise RuntimeError('Pinned archive mismatch:'+row['fn'])
  explicit.append('file://'+L+'/'+p.relative_to(R).as_posix()+'#'+row['md5'])
 (E/'checkm2_install_explicit_local.txt').write_text('@EXPLICIT\n'+'\n'.join(explicit)+'\n',encoding='utf-8')
 before=private.registry();save(E/'install_registry_before.json',before)
 status='FAILED';failure=None;childcode=None;candidate=None
 try:
  with (R/'logs/checkm2_install.log').open('w',encoding='utf-8') as out,(R/'logs/checkm2_install_controller.stderr.txt').open('w',encoding='utf-8') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_private_install.sh'],stdout=out,stderr=err)
   while child.poll() is None:time.sleep(2)
   childcode=child.returncode
   if childcode!=0:raise RuntimeError(f'Private install/smoke exited{childcode}; outputs preserved')
  candidate=read(E/'environment_candidate_receipt.json')
  if candidate.get('status')!='CANDIDATE_ENVIRONMENT_SMOKE_PASS':raise RuntimeError('Linux model/runtime smoke not passed')
  status='COMPLETE'
 except BaseException as exc:failure=repr(exc)
 finally:
  after=private.registry();same=before==after
  if not same:status='FAILED';failure='Outside host registry changed; no automatic restore'
  receipt={'status':status,'started_utc':START,'ended_utc':utc(),'native_process_identity':OWNER,'child_exit_code':childcode,
      'error':failure,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':same,
      'cache_handoff_sha256':sha(E/'cache_handoff.json'),'resolved_packages_sha256':EXPECTED,
      'candidate':candidate,'scientific_prediction':'NOT_RUN','controller_script_sha256':sha(__file__)}
  save(E/'tool_environment_receipt.json',receipt)
  if status=='COMPLETE':
   ready={'status':'READY_FOR_RESOURCE_PILOT','created_utc':utc(),'prefix_linux':candidate['prefix_linux'],'prefix_windows':str(R/'tools/checkm2_env'),
      'checkm2_version':candidate['checkm2_version'],'diamond_version':candidate['diamond_version'],
      'import_smoke_passed':True,'model_load_smoke_passed':True,'smoke_receipt_path':candidate['smoke_receipt_path'],
      'installed_manifest_path':candidate['installed_manifest']['path'],'installed_manifest_sha256':candidate['installed_manifest']['sha256'],
      'models_manifest_path':candidate['models_manifest']['path'],'models_manifest_sha256':candidate['models_manifest']['sha256'],
      'database_path':L+'/'+candidate['database']['database_path'],'database_receipt_path':'tools/databases/checkm2_v3/extracted_receipt.json',
      'environment_receipt_path':'evidence/checkm2_runtime/tool_environment_receipt.json','environment_receipt_sha256':sha(E/'tool_environment_receipt.json'),
      'heavy_linux_children_closed':True,'scientific_prediction':'NOT_RUN'}
   save(R/'state/checkm2_runtime_ready.json',ready)
  publish('Private CheckM2 runtime/model smoke passed; one-genome resource pilot next' if status=='COMPLETE' else failure,4 if status=='COMPLETE' else 0,4,status)
  lock.close();print(json.dumps(receipt),flush=True)
 return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
