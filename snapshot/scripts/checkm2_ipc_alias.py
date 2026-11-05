"""Private, short-lived IPC alias; genome/model/output files never live here.

The context must run inside the existing project-only mount namespace. The
temporary /tmp bind is removed with ordinary umount before its backing mount.
"""
from pathlib import Path
import argparse,datetime as dt,errno,hashlib,json,multiprocessing,os,re,signal,socket,stat,subprocess,sys,tempfile,time,uuid

R=Path(__file__).resolve().parents[1]
E=R/'evidence/checkm2_runtime'
CAPACITY=32*1024**2
ALIAS=Path('/tmp')

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,value):
 p=project(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 with t.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def project(p):
 p=Path(p)
 if not p.is_absolute():p=R/p
 resolved=p.resolve()
 if p!=resolved or not resolved.is_relative_to(R):raise RuntimeError('IPC path must be a non-symlink project path')
 return p
def cmd(args,timeout=30):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(f'{args[0]} exit{p.returncode}: {p.stderr[-1500:]}')
 return p.stdout.strip()
def mount_record(path):
 return json.loads(cmd(['findmnt','-T',path,'-J','-o','TARGET,SOURCE,FSTYPE,VFS-OPTIONS,FS-OPTIONS']))['filesystems'][0]
def verify_private():
 if os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Private project namespace is required')
 ns=os.readlink('/proc/self/ns/mnt');proof=read(E/'namespace_mapping.json')
 if proof['mount_namespace']!=ns or not os.statvfs('/').f_flag&os.ST_RDONLY or os.statvfs(R).f_flag&os.ST_RDONLY:raise RuntimeError('Private namespace/mount protection differs')
 if not os.statvfs(ALIAS).f_flag&os.ST_RDONLY:raise RuntimeError('Expected the original private /tmp to be read-only')
 return ns
def identity(path):
 s=os.lstat(path)
 if not stat.S_ISDIR(s.st_mode):raise RuntimeError('IPC backing must be a directory')
 return {'dev':s.st_dev,'ino':s.st_ino,'uid':s.st_uid,'gid':s.st_gid}

class IpcAlias:
 def __init__(self,backing,mode,receipt):
  self.backing=project(backing);self.mode=mode;self.receipt=project(receipt);self.alias_bound=False;self.tmpfs_bound=False;self.created=[]
  if mode not in ('PROJECT_BIND','TMPFS_32M'):raise RuntimeError('Unsupported IPC backing')
 def __enter__(self):
  ns=verify_private();self.before=mount_record(ALIAS)
  if not self.backing.is_relative_to(R/'work/checkm2_ipc'):raise RuntimeError('IPC backing outside dedicated workspace')
  self.backing.mkdir(parents=False,exist_ok=False);self.initial_identity=identity(self.backing)
  if any(self.backing.iterdir()):raise RuntimeError('IPC backing must be new and empty')
  try:
   if self.mode=='TMPFS_32M':
    cmd(['mount','-t','tmpfs','-o','rw,size=32m,nr_inodes=1024,mode=0700,nodev,nosuid,noexec','tree2-checkm2-ipc',self.backing]);self.tmpfs_bound=True
    if os.statvfs(self.backing).f_blocks*os.statvfs(self.backing).f_frsize!=CAPACITY:raise RuntimeError('IPC tmpfs capacity differs from32MiB')
   self.marker='tree2-ipc-'+uuid.uuid4().hex
   marker=self.backing/self.marker;marker.write_text('Tree2 private IPC alias\n');self.created.append(marker)
   cmd(['mount','--bind',self.backing,ALIAS]);self.alias_bound=True
   cmd(['mount','-o','remount,bind,rw,nodev,nosuid,noexec',ALIAS])
   flags=os.statvfs(ALIAS).f_flag
   if flags&os.ST_RDONLY or not all(flags&x for x in (os.ST_NODEV,os.ST_NOSUID,os.ST_NOEXEC)):raise RuntimeError('IPC alias protection differs')
   if identity(ALIAS)!=identity(self.backing) or (ALIAS/self.marker).read_bytes()!=marker.read_bytes():raise RuntimeError('Short IPC alias does not map exact backing inode')
   canary=ALIAS/(self.marker+'.canary');canary.write_bytes(b'private-project-ipc');self.created.append(self.backing/canary.name)
   if (self.backing/canary.name).read_bytes()!=b'private-project-ipc':raise RuntimeError('Alias write did not map project backing')
   self.result={'status':'PRIVATE_SHORT_IPC_ACTIVE','created_utc':utc(),'mount_namespace':ns,'network_namespace':os.readlink('/proc/self/ns/net'),'mode':self.mode,'alias':'/tmp','backing_path':str(self.backing),'backing_identity':identity(self.backing),'underlying_project_directory_identity':self.initial_identity,'capacity_bytes':CAPACITY if self.tmpfs_bound else None,'alias_mount':mount_record(ALIAS),'backing_mount':mount_record(self.backing),'prior_alias_mount':self.before,'effective_tmp_environment':{'TMPDIR':'/tmp','TMP':'/tmp','TEMP':'/tmp'},'nodev_nosuid_noexec':True,'scientific_outputs_stored_here':False,'marker':self.marker,'helper_sha256':sha(__file__)}
   save(self.receipt,self.result);return self
  except BaseException:
   self.__exit__(None,None,None);raise
 def __exit__(self,*unused):
  errors=[]
  for p in self.created:
   try:
    if p.exists():p.unlink()
   except BaseException as e:errors.append('marker cleanup:'+repr(e))
  if self.alias_bound:
   try:cmd(['umount',ALIAS]);self.alias_bound=False
   except BaseException as e:errors.append('alias unmount:'+repr(e))
  if self.tmpfs_bound and not self.alias_bound:
   try:cmd(['umount',self.backing]);self.tmpfs_bound=False
   except BaseException as e:errors.append('tmpfs unmount:'+repr(e))
  try:
   after=mount_record(ALIAS)
   if after!=self.before or not os.statvfs(ALIAS).f_flag&os.ST_RDONLY:errors.append('Original private /tmp mount was not restored')
   if identity(self.backing)!=self.initial_identity:errors.append('Underlying project backing identity differs')
   remaining=[p.name for p in self.backing.iterdir()]
   if remaining:errors.append('Unexpected residual IPC entries:'+repr(remaining))
  except BaseException as e:errors.append(repr(e));after=None;remaining=None
  save(self.receipt.with_name(self.receipt.stem+'_closure.json'),{'status':'CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT' if not errors else 'IPC_CLOSURE_FAILED','closed_utc':utc(),'mode':self.mode,'mount_namespace':os.readlink('/proc/self/ns/mnt'),'alias_mount_after':after,'backing_path':str(self.backing),'backing_directory_identity':self.initial_identity,'remaining_entries':remaining,'ordinary_unmount_only':True,'errors':errors})
  if errors:raise RuntimeError('; '.join(errors))

def child_probe(receipt,nonce,scientific_scratch):
 """Exercise the same Python interpreter's AF_UNIX and SyncManager primitives."""
 if tempfile.gettempdir()!='/tmp' or any(os.environ.get(k)!='/tmp' for k in ('TMPDIR','TMP','TEMP')):raise RuntimeError('Short temporary environment was not present before Python startup')
 name='/tmp/tree2-'+nonce+'.sock'
 if len(os.fsencode(name))>=108:raise RuntimeError('Probe socket address is too long')
 result={'status':'FAILED','started_utc':utc(),'python_version':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(sys.executable),'temporary_directory':tempfile.gettempdir(),'socket_path':name,'socket_path_bytes':len(os.fsencode(name)),'manager_started':False,'model_or_scientific_imports':False}
 sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
 try:
  try:sock.bind(name)
  except OSError as e:
   result.update(status='PROJECT_SOCKET_UNSUPPORTED' if e.errno in (errno.EOPNOTSUPP,errno.ENOSYS) else 'SOCKET_BIND_FAILED',errno=e.errno,error=repr(e));save(receipt,result);return 8 if result['status']=='PROJECT_SOCKET_UNSUPPORTED' else 2
  sock.listen(1)
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
   client.settimeout(5);client.connect(name)
   server,_=sock.accept()
   with server:
    server.settimeout(5);client.sendall(b'TREE2_IPC');assert server.recv(32)==b'TREE2_IPC';server.sendall(b'OK');assert client.recv(8)==b'OK'
  import checkm2_ipc_bootstrap as target
  warm=target.prewarm()
  scratch=project(scientific_scratch)
  if not scratch.is_relative_to(R/'work/checkm2_ipc') or not scratch.is_dir():raise RuntimeError('Scientific scratch capability path differs')
  if len(os.fsencode(str(scratch)))<108:raise RuntimeError('Proof must preserve the real long scientific scratch path')
  # This is the exact relevant effect of upstream ChangeTempAction(--tmpdir).
  tempfile.tempdir=str(scratch)
  with tempfile.NamedTemporaryFile(prefix='scientific-probe-',delete=True) as durable:
   if not Path(durable.name).is_relative_to(scratch):raise RuntimeError('Ordinary scientific tempfile did not remain durable')
   result['scientific_tempfile_example']=durable.name
  result.update(prewarm=warm,scientific_tempfile_directory_after_author_action=tempfile.gettempdir(),durable_temp_directory_bytes=len(os.fsencode(str(scratch))))
  manager=multiprocessing.Manager();process=manager._process
  try:
   address=manager.address
   if not isinstance(address,str) or not address.startswith('/tmp/') or len(os.fsencode(address))>=108:raise RuntimeError('Manager did not use an admissible short AF_UNIX path')
   data=manager.dict();data['tree2']=61;assert data['tree2']==61
   result.update(manager_started=True,manager_address=address,manager_address_bytes=len(os.fsencode(address)),manager_pid=process.pid,manager_roundtrip_passed=True)
  finally:manager.shutdown();process.join(5)
  if process.is_alive() or process.exitcode!=0:raise RuntimeError('SyncManager server failed clean closure')
  if multiprocessing.util.get_temp_dir()!=warm['cached_ipc_directory']:raise RuntimeError('Cached IPC directory changed after scientific tmpdir override')
  result.update(status='PASS_SHORT_AF_UNIX_AND_SYNCMANAGER',manager_child_closed=True,manager_child_exit_code=process.exitcode,ipc_cache_survived_author_tmpdir_override=True,scientific_tempfiles_remain_project_durable=True,ended_utc=utc());save(receipt,result);return 0
 finally:
  sock.close()
  try:Path(name).unlink()
  except FileNotFoundError:pass

def launch_validated(a):
 proofpath=project(a.proof)
 if not a.proof_sha256 or sha(proofpath)!=a.proof_sha256:raise RuntimeError('IPC proof hash differs')
 proof=read(proofpath)
 if proof['status']!='PRIVATE_SHORT_IPC_PROVEN' or proof['helper_sha256']!=sha(__file__):raise RuntimeError('IPC capability/helper not admitted')
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Sealed read-only runtime is required')
 mount=read(project(os.environ['TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT']))
 if mount['image_sha256']!=proof['image_sha256'] or os.environ.get('TREE2_EFFECTIVE_RUNTIME_MANIFEST_SHA256')!=proof['effective_runtime_manifest_sha256']:raise RuntimeError('IPC proof runtime binding differs')
 token=a.token
 if not re.fullmatch('[a-f0-9]{32}',token):raise RuntimeError('Fresh32-hex launch token required')
 if not a.command:raise RuntimeError('A guarded command is required')
 receipt=project(a.receipt);backing=R/'work/checkm2_ipc'/('launch_'+token)
 with IpcAlias(backing,proof['selected_mode'],receipt) as ipc:
  ipc.result.update(proof_path=str(proofpath),proof_sha256=a.proof_sha256,target_bootstrap_sha256=proof['target_bootstrap_sha256'],effective_runtime_manifest_sha256=proof['effective_runtime_manifest_sha256'],image_sha256=proof['image_sha256'])
  save(receipt,ipc.result)
  env=os.environ.copy();env.update(TMPDIR='/tmp',TMP='/tmp',TEMP='/tmp',TREE2_CHECKM2_PRIVATE_IPC_VERIFIED='1',TREE2_CHECKM2_PRIVATE_IPC_RECEIPT=str(receipt),TREE2_CHECKM2_PRIVATE_IPC_PROOF_SHA256=a.proof_sha256)
  # The existing guarded controller owns its prediction group and stop deadline.
  # This wrapper retains the mount until that controller returns and closes it.
  code=subprocess.call(a.command,env=env)
 return code

def main():
 p=argparse.ArgumentParser();p.add_argument('--child-probe',action='store_true');p.add_argument('--nonce');p.add_argument('--scientific-scratch');p.add_argument('--receipt',required=True);p.add_argument('--proof');p.add_argument('--proof-sha256');p.add_argument('--token');p.add_argument('--exec',dest='command',nargs=argparse.REMAINDER);a=p.parse_args()
 if a.child_probe:
  if not a.nonce or not re.fullmatch('[a-f0-9]{16}',a.nonce):raise RuntimeError('Invalid probe nonce')
  return child_probe(project(a.receipt),a.nonce,a.scientific_scratch)
 return launch_validated(a)
if __name__=='__main__':raise SystemExit(main())
