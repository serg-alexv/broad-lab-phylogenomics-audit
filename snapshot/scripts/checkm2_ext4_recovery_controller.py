"""One bounded project-image recovery. Native identity, sparse creation and sealing."""
from pathlib import Path
import argparse,ctypes,hashlib,json,msvcrt,os,shutil,subprocess,time,uuid
from ctypes import wintypes
import checkm2_private_install_controller as base
R=base.R;E=base.E;L=base.L;IMAGE=R/'tools/checkm2_runtime_ext4.img';SIZE=16*1024**3
OWNER=base.OWNER;START=base.START

def progress(detail,done=0,status='RUNNING'):
 base.save(R/'state/tool_setup_progress.json',{'status':status,'done':done,'total':6,'unit':'recovery phases','detail':detail,'started_utc':START,'updated_utc':base.utc(),'pid':OWNER['pid'],'creation_time_utc':OWNER['creation_time_utc'],'log_path':str(R/'logs/checkm2_ext4_recovery.log')})
def gate():
 base.gate()
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only recovery')
def closure_gate():
 x=base.read(E/'installation_closure_proof.json');a=base.read(E/'cache_post_install_timeout_audit.json')
 if not x['native_pid_absent'] or not x['installation_os_lock_released'] or not x['linux_group_independently_empty'] or not x['linux_namespace_main_pid1412_absent']:raise RuntimeError('Prior attempt is not closed')
 if a['status']!='PASS_SOURCE_ARCHIVES_PRESERVED_AFTER_INSTALL_TIMEOUT' or a['package_count']!=133:raise RuntimeError('Closed-attempt source-cache audit missing')
 if (R/'state/checkm2_runtime_ready.json').exists():raise RuntimeError('A ready runtime already exists')
def archive_prior():
 d=E/'history/ntfs_attempt_20261026T194928Z';d.mkdir(exist_ok=False);rows=[]
 names=['evidence/checkm2_runtime/'+n for n in ('install_exit.json','private_install_linux_failure.json','tool_environment_receipt.json','namespace_mapping.json','installation_closure_proof.json','cache_post_install_timeout_audit.json')]
 names += ['logs/'+n for n in ('checkm2_install.stdout.txt','checkm2_install.stderr.txt','checkm2_install.log','checkm2_install_controller.stderr.txt','checkm2_private_install_controller.stdout.txt','checkm2_private_install_controller.stderr.txt')]
 for rel in names:
  p=R/rel
  if p.exists():
   dest=d/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
   rows.append({'original':rel,'preserved':dest.relative_to(R).as_posix(),'sha256':base.sha(dest),'bytes':dest.stat().st_size})
 base.save(d/'manifest.json',{'created_utc':base.utc(),'artifacts':rows,'old_partial_prefix_untouched':True})
def create_sparse():
 if IMAGE.resolve()!=IMAGE or not IMAGE.is_relative_to(R) or IMAGE.exists():raise RuntimeError('New image target is not exclusively available inside project')
 if shutil.disk_usage(R).free<40*1024**3+SIZE:raise RuntimeError('Host lacks40GiB reserve plus16GiB image capacity')
 fd=os.open(IMAGE,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_BINARY,0o600)
 try:
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID];k.DeviceIoControl.restype=wintypes.BOOL
  returned=wintypes.DWORD()
  if not k.DeviceIoControl(wintypes.HANDLE(msvcrt.get_osfhandle(fd)),0x900C4,None,0,None,0,ctypes.byref(returned),None):raise ctypes.WinError(ctypes.get_last_error())
  marker='TREE2_NEW_EXT4_IMAGE:'+str(uuid.uuid4())+'\n';os.write(fd,marker.encode());os.ftruncate(fd,SIZE);os.fsync(fd);s=os.fstat(fd)
  code="import os,json; s=os.lstat("+repr(L+'/tools/checkm2_runtime_ext4.img')+"); print(json.dumps({'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'nlink':s.st_nlink}))"
  identity=json.loads(subprocess.check_output(['wsl','-d','Ubuntu','--','/usr/bin/python3','-B','-c',code],text=True))
  receipt={'status':'EXCLUSIVELY_CREATED_SPARSE_IMAGE','at_utc':base.utc(),'windows_path':str(IMAGE),'linux_path':L+'/tools/checkm2_runtime_ext4.img','marker':marker,'linux_identity':identity,'windows_identity':{'ino':s.st_ino,'dev':s.st_dev,'nlink':s.st_nlink,'size':s.st_size,'file_attributes':s.st_file_attributes},'logical_bytes':SIZE,'native_owner':OWNER,'file_descriptor_held_through_prepare':True}
  if not s.st_file_attributes&512:raise RuntimeError('New image is not marked sparse')
  base.save(E/'ext4_image_creation.json',receipt);return fd
 except BaseException:os.close(fd);raise
def call_wsl(stage):
 script=L+'/scripts/checkm2_ext4_'+stage+'.sh'
 with (R/f'logs/checkm2_ext4_{stage}.stdout.txt').open('w') as out,(R/f'logs/checkm2_ext4_{stage}.stderr.txt').open('w') as err:
  p=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',script],stdout=out,stderr=err)
  while p.poll() is None:time.sleep(1)
  if p.returncode:raise RuntimeError(f'Private ext4 {stage} failed exit{p.returncode}; logs preserved')
 return p.returncode
def seal(stage):
 closure=base.read(E/f'ext4_{stage}_mount_closure.json')
 if closure['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH':raise RuntimeError('Image is not cleanly unmounted/detached')
 progress('Hashing cleanly closed image; no user input required',4);h=hashlib.sha256();count=0;beg=time.monotonic();last=0
 with IMAGE.open('rb') as f:
  while data:=f.read(16*1024**2):
   gate();h.update(data);count+=len(data)
   if time.monotonic()-beg>600:raise RuntimeError('Closed-image sealing exceeded600s')
   if time.monotonic()-last>3:progress(f'Sealing closed image {count}/{SIZE} bytes; no user input required',4);last=time.monotonic()
 x={'status':'SEALED_AFTER_CLEAN_UNMOUNT','stage':stage,'at_utc':base.utc(),'path':IMAGE.relative_to(R).as_posix(),'bytes':count,'sha256':h.hexdigest(),'closure_receipt':f'evidence/checkm2_runtime/ext4_{stage}_mount_closure.json','filesystem_uuid':base.read(E/'ext4_format_receipt.json')['filesystem']['UUID']}
 if count!=SIZE:raise RuntimeError('Sealed image size differs')
 base.save(E/'ext4_image_seal.json',x);return x
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--install',action='store_true');args=ap.parse_args()
 if args.prepare==args.install:raise ValueError('Choose exactly one phase')
 gate();closure_gate();lock=(R/'state/checkm2_install.lock').open('r+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 fd=None;before=base.private.registry();stage='prepare' if args.prepare else 'install';status='FAILED';error=None;sealed=None;candidate=None;smoke=None
 base.save(R/'state/launch_tool_setup.json',{**OWNER,'script':'scripts/checkm2_ext4_recovery_controller.py','phase':'EXT4_'+stage.upper()})
 progress('Preparing private project-image proof; no user input required',0)
 try:
  if args.prepare:
   archive_prior();(R/'work/checkm2_runtime_mount').mkdir(exist_ok=False);fd=create_sparse();call_wsl('prepare');sealed=seal('prepare');call_wsl('proof_ro');status='PREPARED_NOT_RUNTIME_READY'
  else:
   prepared=base.read(E/'ext4_prepare_execution.json')
   if prepared['status']!='PREPARED_NOT_RUNTIME_READY' or not prepared['host_registry_unchanged']:raise RuntimeError('Image preparation proof not accepted')
   claim=E/'ext4_single_recovery_claim.json'
   if claim.exists():raise RuntimeError('The single recovery attempt has already been claimed; do not inspect/reuse an unknown active image')
   current=seal('prepare')
   if current['sha256']!=prepared['sealed_image']['sha256']:raise RuntimeError('Prepared image changed after its RO persistence proof')
   with claim.open('x') as f:
    json.dump({'at_utc':base.utc(),'owner':OWNER,'exactly_one_recovery':True,'conda_deadline_seconds':3600,'outer_linux_deadline_seconds':5400},f);f.flush();os.fsync(f.fileno())
   fd=os.open(IMAGE,os.O_RDWR|os.O_BINARY);s=os.fstat(fd);created=base.read(E/'ext4_image_creation.json')['windows_identity']
   if (s.st_ino,s.st_dev,s.st_size,s.st_nlink)!=(created['ino'],created['dev'],created['size'],1):raise RuntimeError('Existing prepared image identity changed')
   call_wsl('install');sealed=seal('install');call_wsl('verify_ro')
   candidate=base.read(E/'environment_candidate_receipt.json');smoke=base.read(E/'ext4_readonly_validation.json')
   if candidate.get('status')!='CANDIDATE_ENVIRONMENT_SMOKE_PASS' or smoke.get('status')!='PASS_READONLY_RUNTIME_PERSISTENCE' or not smoke.get('all_smoke_children_closed'):raise RuntimeError('Final runtime/RO receipts not accepted')
   for key in ('installed_manifest','models_manifest'):
    if base.sha(R/candidate[key]['path'])!=candidate[key]['sha256']:raise RuntimeError('Final candidate artifact manifest hash differs')
   if not base.read(E/'ext4_driver_exit.json')['all_owned_children_closed']:raise RuntimeError('Recovery driver descendants remain')
   status='RUNTIME_RO_VERIFIED'
 except BaseException as ex:error=repr(ex)
 finally:
  if fd is not None:os.close(fd)
  after=base.private.registry();same=before==after
  if not same:status='FAILED';error='Outside host registry changed; no automatic restore'
  receipt={'status':status,'started_utc':START,'ended_utc':base.utc(),'native_owner':OWNER,'error':error,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':same,'sealed_image':sealed,'scientific_prediction':'NOT_RUN','controller_sha256':base.sha(__file__)}
  base.save(E/f'ext4_{stage}_execution.json',receipt)
  if status=='RUNTIME_RO_VERIFIED':
   env={'status':'COMPLETE','storage':'PROJECT_OWNED_EXT4_IMAGE','native_process_identity':OWNER,'host_registry_unchanged':same,'candidate':candidate,'image_seal':sealed,'read_only_validation':smoke,'scientific_prediction':'NOT_RUN'}
   base.save(E/'tool_environment_receipt.json',env)
   ready={'status':'READY_FOR_RESOURCE_PILOT','created_utc':base.utc(),'storage':'PROJECT_OWNED_EXT4_IMAGE','prefix_linux':candidate['prefix_linux'],'prefix_windows':str(R/'tools/checkm2_env'),'outside_prefix_is_preserved_unaccepted_ntfs_partial':True,'checkm2_version':'1.1.0','diamond_version':'2.1.11','import_smoke_passed':True,'model_load_smoke_passed':True,'smoke_receipt_path':candidate['smoke_receipt_path'],'installed_manifest_path':candidate['installed_manifest']['path'],'installed_manifest_sha256':candidate['installed_manifest']['sha256'],'models_manifest_path':candidate['models_manifest']['path'],'models_manifest_sha256':candidate['models_manifest']['sha256'],'database_path':L+'/'+candidate['database']['database_path'],'database_receipt_path':'tools/databases/checkm2_v3/extracted_receipt.json','environment_receipt_path':'evidence/checkm2_runtime/tool_environment_receipt.json','environment_receipt_sha256':base.sha(E/'tool_environment_receipt.json'),'image_path':str(IMAGE),'image_relative_path':IMAGE.relative_to(R).as_posix(),'image_sha256':sealed['sha256'],'filesystem_uuid':sealed['filesystem_uuid'],'image_seal_receipt_path':'evidence/checkm2_runtime/ext4_image_seal.json','readonly_mount_helper_path':'scripts/checkm2_runtime_image.py','heavy_linux_children_closed':True,'scientific_prediction':'NOT_RUN'}
   ready['requires_private_image_mount']=True
   ready['runtime_image']={'path':L+'/tools/checkm2_runtime_ext4.img','windows_path':str(IMAGE),'relative_path':IMAGE.relative_to(R).as_posix(),'sha256':sealed['sha256'],'bytes':sealed['bytes'],'filesystem_uuid':sealed['filesystem_uuid'],'seal_receipt_path':'evidence/checkm2_runtime/ext4_image_seal.json','seal_receipt_sha256':base.sha(E/'ext4_image_seal.json')}
   base.save(R/'state/checkm2_runtime_ready.json',ready)
  progress('Private image proof complete; bounded installation next' if status=='PREPARED_NOT_RUNTIME_READY' else ('Read-only runtime persistence passed; scientific pilot next' if status=='RUNTIME_RO_VERIFIED' else error),2 if args.prepare else 6,'RECOVERY_PREPARED' if status=='PREPARED_NOT_RUNTIME_READY' else ('COMPLETE' if status=='RUNTIME_RO_VERIFIED' else 'FAILED'))
  lock.close();print(json.dumps(receipt),flush=True)
 return 0 if status!='FAILED' else 2
if __name__=='__main__':raise SystemExit(main())
