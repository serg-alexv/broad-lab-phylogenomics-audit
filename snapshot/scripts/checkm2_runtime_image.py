"""Project-owned ext4 runtime; Linux loop ABI comes from /usr/include/linux/loop.h.

No device is ever formatted. LOOP_CONFIGURE atomically claims an existing node;
AUTOCLEAR and a held descriptor tie its association to this private mount lifetime.
"""
from pathlib import Path
import argparse,datetime as dt,errno,fcntl,hashlib,json,os,stat,struct,subprocess,time

R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
IMAGE=R/'tools/checkm2_runtime_ext4.img';MOUNT=R/'work/checkm2_runtime_mount'
PREFIX=R/'tools/checkm2_env';DB=R/'tools/databases/checkm2_v3/data/CheckM2_database/uniref100.KO.1.dmnd'
SIZE=16*1024**3

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 p=Path(p);h=hashlib.sha256();count=0;started=time.monotonic();last=0
 with Path(p).open('rb') as f:
  while chunk:=f.read(16*1024**2):
   h.update(chunk);count+=len(chunk)
   if p==IMAGE:
    if time.monotonic()-started>600:raise RuntimeError('Read-only image verification exceeded600s')
    if (R/'state/STOP').exists():raise RuntimeError('STOP during read-only image verification')
    if os.environ.get('TREE2_CHECKM2_IMAGE_HASH_PROGRESS')=='1' and time.monotonic()-last>3:
     owner=read(R/'state/launch_tool_setup.json')
     if owner.get('script') in ('scripts/checkm2_ext4_recovery_controller.py','scripts/checkm2_postinstall_smoke_controller.py','scripts/checkm2_matching_runtime_controller.py'):
      save(R/'state/tool_setup_progress.json',{'status':'RUNNING','done':4,'total':6,'unit':'recovery phases','detail':f'Verifying read-only image {count}/{SIZE} bytes; no user input required','updated_utc':utc(),'pid':owner['pid'],'creation_time_utc':owner['creation_time_utc'],'log_path':str(E/'ext4_image_seal.json')})
     last=time.monotonic()
 return h.hexdigest()
def save(p,x):
 p=Path(p);t=p.with_name(p.name+f'.{os.getpid()}.tmp')
 with t.open('w') as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def command(args,timeout=120):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError(f'{args[0]} exit {r.returncode}: {r.stderr[-1800:]}')
 return r.stdout.strip()
def private():
 if os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Private namespace missing')
 if not os.statvfs('/').f_flag&os.ST_RDONLY or os.statvfs(R).f_flag&os.ST_RDONLY:raise RuntimeError('Private mount flags invalid')
 proof=read(E/'namespace_mapping.json')
 if proof['mount_namespace']!=os.readlink('/proc/self/ns/mnt'):raise RuntimeError('Namespace proof identity mismatch')
def image_identity(fd=None):
 p=IMAGE.resolve(strict=True)
 if p!=IMAGE or not p.is_relative_to(R):raise RuntimeError('Image path escapes project or is symlink')
 a=os.lstat(IMAGE);b=os.fstat(fd) if fd is not None else a
 if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_size!=SIZE:raise RuntimeError('Image must be a sole-link regular 16GiB file')
 if (a.st_dev,a.st_ino,a.st_size)!=(b.st_dev,b.st_ino,b.st_size):raise RuntimeError('Image inode changed')
 return {'dev':a.st_dev,'ino':a.st_ino,'size':a.st_size,'nlink':a.st_nlink}
def filesystem(p):
 out=command(['/usr/sbin/blkid','-p','-o','export',p]);return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
def format_new_image():
 private();creation=read(E/'ext4_image_creation.json')
 if creation['status']!='EXCLUSIVELY_CREATED_SPARSE_IMAGE' or creation['linux_path']!=str(IMAGE):raise RuntimeError('Exclusive creation receipt missing')
 marker=creation['marker'].encode();fd=os.open(IMAGE,os.O_RDWR|os.O_NOFOLLOW)
 try:
  before=image_identity(fd)
  if before!=creation['linux_identity']:raise RuntimeError('Exclusive-creation image inode differs')
  if os.pread(fd,len(marker),0)!=marker:raise RuntimeError('Fresh image marker differs; never format an existing filesystem')
  probe=subprocess.run(['/usr/sbin/blkid','-p',str(IMAGE)],capture_output=True,text=True,timeout=20)
  if probe.returncode!=2:raise RuntimeError('New image unexpectedly has a filesystem/signature')
  save(E/'ext4_preformat_identity.json',{'status':'VERIFIED_EXCLUSIVELY_CREATED_REGULAR_IMAGE','at_utc':utc(),'identity':before,'marker':creation['marker'],'format_target':str(IMAGE),'never_a_device':True})
  command(['/usr/sbin/mkfs.ext4','-F','-m','0','-L','TREE2_CHKM2','-E','lazy_itable_init=0,lazy_journal_init=0',IMAGE],180)
  if image_identity(fd)!=before:raise RuntimeError('Image identity changed during format')
  fs=filesystem(IMAGE)
  if fs.get('TYPE')!='ext4' or not fs.get('UUID'):raise RuntimeError('New filesystem type/UUID invalid')
  result={'status':'FORMATTED_NEW_PROJECT_REGULAR_IMAGE','at_utc':utc(),'identity':before,'filesystem':fs,'format_target':str(IMAGE),'direct_file_only':True,'loop_header_sha256':sha('/usr/include/linux/loop.h')}
  save(E/'ext4_format_receipt.json',result);return result
 finally:os.close(fd)

class RuntimeImage:
 def __init__(self,readonly=False,bind_runtime=True,receipt=None):
  self.ro=readonly;self.bind_runtime=bind_runtime;self.receipt=Path(receipt) if receipt else E/'ext4_current_mount.json';self.mounts=[];self.loopfd=None;self.backfd=None;self.node=None;self.raw_bound=False
  if not self.receipt.resolve().is_relative_to(R):raise RuntimeError('Mount receipt must remain inside project')
 def __enter__(self):
  private()
  try:
   fmt=read(E/'ext4_format_receipt.json')
   if image_identity()!=fmt['identity']:raise RuntimeError('Created image identity differs')
   if self.ro:
    seal=read(E/'ext4_image_seal.json')
    command(['mount','--bind',IMAGE,IMAGE]);self.mounts.append(IMAGE);self.raw_bound=True
    command(['mount','-o','remount,bind,ro',IMAGE])
    if not os.statvfs(IMAGE).f_flag&os.ST_RDONLY:raise RuntimeError('Raw image bind is not read-only')
    if seal['status']!='SEALED_AFTER_CLEAN_UNMOUNT' or sha(IMAGE)!=seal['sha256']:raise RuntimeError('Clean-unmount image seal mismatch')
   self.backfd=os.open(IMAGE,(os.O_RDONLY if self.ro else os.O_RDWR)|os.O_NOFOLLOW|os.O_CLOEXEC)
   identity=image_identity(self.backfd)
   for n in range(8):
    node=Path(f'/dev/loop{n}')
    if not node.exists():continue
    mode=node.stat()
    if not stat.S_ISBLK(mode.st_mode) or os.major(mode.st_rdev)!=7 or os.minor(mode.st_rdev)!=n:raise RuntimeError('Unexpected existing loop node identity')
    fd=os.open(node,os.O_RDWR|os.O_CLOEXEC)
    try:
     buf=bytearray(232)
     try:fcntl.ioctl(fd,0x4C05,buf,True)
     except OSError as ex:
      if ex.errno!=errno.ENXIO:raise
     else:os.close(fd);continue
     cfg=bytearray(304);struct.pack_into('=II',cfg,0,self.backfd,0);struct.pack_into('=I',cfg,60,4|(1 if self.ro else 0))
     try:fcntl.ioctl(fd,0x4C0A,cfg)
     except OSError as ex:
      if ex.errno==errno.EBUSY:os.close(fd);continue
      raise
     self.loopfd=fd;self.node=node;break
    except BaseException:os.close(fd);raise
   if self.loopfd is None:raise RuntimeError('No existing free loop node could be atomically configured')
   buf=bytearray(232);fcntl.ioctl(self.loopfd,0x4C05,buf,True);v=struct.unpack('=5Q4I64s64s32s2Q',buf)
   if (v[0],v[1],v[3],v[4])!=(identity['dev'],identity['ino'],0,0) or not v[8]&4 or bool(v[8]&1)!=self.ro:raise RuntimeError('Loop backing inode/flags/offset differs')
   capacity=bytearray(8);fcntl.ioctl(self.loopfd,0x80081272,capacity,True)
   if struct.unpack('=Q',capacity)[0]!=SIZE:raise RuntimeError('Loop capacity differs from exclusive image size')
   backing=Path(f'/sys/block/{self.node.name}/loop/backing_file').read_text().strip()
   if backing!=str(IMAGE):raise RuntimeError('Loop backing path differs')
   fs=filesystem(self.node)
   if fs.get('TYPE')!='ext4' or fs.get('UUID')!=fmt['filesystem']['UUID']:raise RuntimeError('Loop filesystem UUID/type differs')
   if MOUNT.is_symlink() or MOUNT.resolve()!=MOUNT or not MOUNT.is_relative_to(R) or any(MOUNT.iterdir()):raise RuntimeError('Mountpoint must be an empty project directory')
   opts='ro,noload,nodev,nosuid,noatime' if self.ro else 'rw,nodev,nosuid,noatime'
   command(['mount','-t','ext4','-o',opts,self.node,MOUNT]);self.mounts.append(MOUNT)
   if bool(os.statvfs(MOUNT).f_flag&os.ST_RDONLY)!=self.ro:raise RuntimeError('Image mount protection differs')
   flags=os.statvfs(MOUNT).f_flag
   if not flags&os.ST_NODEV or not flags&os.ST_NOSUID or flags&os.ST_NOEXEC:raise RuntimeError('Runtime mount device/suid/exec flags differ')
   fs_options=command(['findmnt','-T',MOUNT,'-n','-o','FS-OPTIONS'])
   if self.ro and not any(x in fs_options.split(',') for x in ('noload','norecovery')):raise RuntimeError('Read-only mount lacks journal-replay suppression')
   if self.bind_runtime:
    for source,target,force_ro in [(MOUNT/'env',PREFIX,self.ro),(MOUNT/'db/uniref100.KO.1.dmnd',DB,True)]:
     if not source.exists() or not target.exists():raise RuntimeError('Runtime bind source/target missing')
     if source.resolve()!=source or target.resolve()!=target or not source.is_relative_to(MOUNT) or not target.is_relative_to(R):raise RuntimeError('Runtime bind symlink/containment violation')
     if (source==MOUNT/'env' and (not source.is_dir() or not target.is_dir())) or (source!=MOUNT/'env' and (not source.is_file() or not target.is_file())):raise RuntimeError('Runtime bind source/target type mismatch')
     command(['mount','--bind',source,target]);self.mounts.append(target)
     if force_ro:command(['mount','-o','remount,bind,ro',target])
     if bool(os.statvfs(target).f_flag&os.ST_RDONLY)!=force_ro:raise RuntimeError('Canonical runtime bind protection differs')
   mounts={str(p):command(['findmnt','-T',p,'-n','-o','TARGET,SOURCE,FSTYPE,VFS-OPTIONS,FS-OPTIONS']) for p in self.mounts}
   self.result={'status':'READONLY_RUNTIME_MOUNT_VERIFIED' if self.ro else 'PRIVATE_RW_IMAGE_MOUNT_VERIFIED','at_utc':utc(),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'image_path':str(IMAGE),'image_identity':identity,'filesystem_uuid':fs['UUID'],'loop_node':str(self.node),'loop_flags':v[8],'loop_autoclear':True,'loop_readonly':self.ro,'loop_offset':v[3],'loop_sizelimit':v[4],'loop_backing_path':backing,'mountpoint':str(MOUNT),'prefix_linux':str(PREFIX),'database_path':str(DB),'mounts':mounts,'raw_image_readonly':bool(os.statvfs(IMAGE).f_flag&os.ST_RDONLY),'canonical_prefix_readonly':bool(os.statvfs(PREFIX).f_flag&os.ST_RDONLY) if self.bind_runtime else None,'canonical_database_readonly':bool(os.statvfs(DB).f_flag&os.ST_RDONLY) if self.bind_runtime else None,'image_sha256':read(E/'ext4_image_seal.json')['sha256'] if self.ro else None}
   self.result['bind_runtime']=self.bind_runtime;self.result['filesystem_options']=fs_options
   save(self.receipt,self.result);return self
  except BaseException:
   self.__exit__(None,None,None);raise
 def __exit__(self,*unused):
  errors=[]
  for target in reversed(self.mounts):
   if target==IMAGE:continue
   try:command(['umount',target],60)
   except BaseException as ex:errors.append(repr(ex))
  self.mounts=[]
  if self.loopfd is not None:os.close(self.loopfd);self.loopfd=None
  if self.backfd is not None:os.close(self.backfd);self.backfd=None
  if self.node:
   p=Path(f'/sys/block/{self.node.name}/loop/backing_file')
   for _ in range(30):
    if not p.exists() or p.read_text().strip()!=str(IMAGE):break
    time.sleep(.1)
   else:errors.append('Owned loop association did not autoclear')
  if self.raw_bound:
   try:command(['umount',IMAGE],60)
   except BaseException as ex:errors.append(repr(ex))
   self.raw_bound=False
  save(self.receipt.with_name(self.receipt.stem+'_closure.json'),{'at_utc':utc(),'status':'CLEAN_UNMOUNT_AND_LOOP_DETACH' if not errors else 'MOUNT_CLOSURE_FAILED','errors':errors,'image_path':str(IMAGE),'loop_node':str(self.node),'readonly':self.ro})
  if errors:raise RuntimeError('; '.join(errors))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--format-new',action='store_true');ap.add_argument('--readonly-exec',nargs=argparse.REMAINDER);ap.add_argument('--receipt');ap.add_argument('--effective-runtime');ap.add_argument('--effective-runtime-sha256');a=ap.parse_args()
 if a.format_new:print(json.dumps(format_new_image()));return
 if not a.readonly_exec:raise ValueError('Specify a readonly command')
 with RuntimeImage(True,True,a.receipt) as mounted:
  env=os.environ.copy();env['TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED']='1';env['TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT']=str(mounted.receipt)
  if a.effective_runtime:
   effective_path=Path(a.effective_runtime)
   if not effective_path.resolve().is_relative_to(R) or not a.effective_runtime_sha256 or sha(effective_path)!=a.effective_runtime_sha256:raise RuntimeError('Validated effective-runtime manifest binding differs')
   effective=read(effective_path)
   if effective.get('status')!='MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY' or effective['base_image']['sha256']!=mounted.result['image_sha256']:raise RuntimeError('Effective-runtime admission/image differs')
   bootstrap_path=R/effective['launch_protocol']['bootstrap_path']
   if sha(bootstrap_path)!=effective['launch_protocol']['bootstrap_sha256']:raise RuntimeError('Effective launch bootstrap changed')
   import checkm2_effective_bootstrap as bootstrap
   bootstrap.bind_overlay(mounted)
   if sha(bootstrap.SPEC)!=effective['static_candidate_manifest_sha256']:raise RuntimeError('Effective static candidate differs')
   env.update(effective['required_runtime_environment']);env['TREE2_EFFECTIVE_RUNTIME_MANIFEST']=str(effective_path);env['TREE2_EFFECTIVE_RUNTIME_MANIFEST_SHA256']=a.effective_runtime_sha256
   mounted.result['validated_effective_runtime_manifest']={'path':str(effective_path),'sha256':a.effective_runtime_sha256};save(mounted.receipt,mounted.result)
  code=subprocess.call(a.readonly_exec,env=env)
 if code:raise SystemExit(code)
if __name__=='__main__':main()
