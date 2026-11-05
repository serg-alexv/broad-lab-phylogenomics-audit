"""Bounded local extraction of a checksum-pinned official Biocontainer layer; no execution."""
from pathlib import Path,PurePosixPath
import tarfile,hashlib,json,time,os,shutil,ctypes
R=Path(__file__).resolve().parents[1];E=R/'work/padloc_R_case_extract_20261029';E.mkdir(exist_ok=True);D=R/'tools/padloc_oci_case_runtime_20261029';D.mkdir(exist_ok=True)
A=R/'metadata/defence_R_runtime_preparation_20261029/PADLOC2_Biocontainer_environment_layer.tar.gz';expected='173df309f3ec87036b3da10fc382b22b0537e351e3abfc793ec418a065ff17f2'
ctypes.windll.kernel32.SetProcessAffinityMask(ctypes.windll.kernel32.GetCurrentProcess(),1)
started=time.monotonic();entries=[];links=[];total=0

def save(name,value):
 p=E/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2));os.replace(t,p)

def digest(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()

assert digest(A)==expected,'Pinned OCI layer differs'
save('started.json',{'archive_sha256':expected,'PID':os.getpid(),'no_R_or_science_executed':True,'max_seconds':600,'CPU_affinity':1})
with tarfile.open(A,mode='r|gz')as tar:
 for member in tar:
  if time.monotonic()-started>600:raise TimeoutError('Bounded runtime extraction600s')
  if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Backing reserve40GiB')
  name=PurePosixPath(member.name)
  if name.is_absolute()or'..'in name.parts:raise RuntimeError('Unsafe archive path')
  if name.parts[:2]!=('usr','local'):continue
  dest=D.joinpath(*name.parts)
  if not dest.resolve().is_relative_to(D):raise RuntimeError('Extraction target escapes dedicated runtime')
  if member.isdir():dest.mkdir(parents=True,exist_ok=True);continue
  if member.issym()or member.islnk():
   links.append({'path':name.as_posix(),'target':member.linkname,'kind':'symlink'if member.issym()else'hardlink'});continue
  if not member.isfile():raise RuntimeError('Special runtime entry refused '+str(name))
  dest.parent.mkdir(parents=True,exist_ok=True);f=tar.extractfile(member);h=hashlib.sha256();size=0
  if dest.exists():
   for data in iter(lambda:f.read(1024**2),b''):h.update(data);size+=len(data)
   if size!=dest.stat().st_size or h.hexdigest()!=digest(dest):raise RuntimeError('Existing partial payload differs; preserve for review '+str(name))
  else:
   temp=dest.with_name(dest.name+'.extract_tmp')
   with temp.open('xb')as out:
    for data in iter(lambda:f.read(1024**2),b''):out.write(data);h.update(data);size+=len(data)
   if size!=member.size:raise RuntimeError('Truncated runtime payload')
   os.replace(temp,dest)
  entries.append({'path':name.as_posix(),'sha256':h.hexdigest(),'bytes':size,'mode':member.mode});total+=size
  if len(entries)%250==0:save('progress.json',{'files':len(entries),'bytes':total,'elapsed_seconds':time.monotonic()-started,'phase':'EXTRACTING_RUNTIME_ONLY'})
save('payload_manifest.json',{'status':'REGULAR_FILES_EXTRACTED_LINKS_PENDING_NO_RUNTIME_EXECUTED','source_archive_sha256':expected,'root':str(D.relative_to(R)),'files':entries,'links':links,'bytes':total,'elapsed_seconds':time.monotonic()-started,'R_executed':False})
print(json.dumps({'status':'REGULAR_FILES_EXTRACTED_LINKS_PENDING','files':len(entries),'links':len(links),'bytes':total,'elapsed_seconds':time.monotonic()-started}),flush=True)
