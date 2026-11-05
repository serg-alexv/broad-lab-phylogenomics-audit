"""Pinned official Zenodo database; project-local, resumable, no redirects."""
from pathlib import Path, PurePosixPath
import datetime, gzip, hashlib, json, msvcrt, os, shutil, socket, sys, tarfile, time
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools/python_lib'))
import requests
SIZE=1735095710
MD5='07c10655620843b517d0df0c160d911f'
URL='https://zenodo.org/api/records/14897628/files/checkm2_database.tar.gz/content'
W=R/'work/models/checkm2_v3'; D=R/'tools/databases/checkm2_v3'
W.mkdir(parents=True,exist_ok=True); D.mkdir(parents=True,exist_ok=True)
P=R/'state/completeness_db_progress.json'; LOG=R/'logs/completeness_db.jsonl'
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def atomic(p,x):
 t=p.with_name(p.name+'.tmp')
 with t.open('w',encoding='utf-8') as f:
  json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(t,p)
START=utc(); CREATION=None
def state(status,done,detail,**kw):
 atomic(P,{'status':status,'done':done,'total':SIZE,'unit':'bytes','detail':detail,
 'pid':os.getpid(),'creation_time_utc':CREATION,'started_utc':START,'updated_utc':utc(),
 'log_path':str(LOG),'source_url':URL,**kw})
def event(kind,**kw):
 with LOG.open('a',encoding='utf-8') as f:
  f.write(json.dumps({'at':utc(),'kind':kind,**kw})+'\n');f.flush()
def admission():
 if (R/'state/STOP').exists(): raise InterruptedError('Project STOP requested')
 if shutil.disk_usage(R).free<40*1024**3: raise InterruptedError('Disk reserve below40GiB')
def verify(path):
 md5=hashlib.md5(); sha=hashlib.sha256(); done=0; last=0
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024**2),b''):
   admission();done+=len(chunk);md5.update(chunk);sha.update(chunk)
   if time.monotonic()-last>2:
    state('VERIFYING',done,'Verifying publishedMD5 and localSHA256');last=time.monotonic()
 if done!=SIZE or md5.hexdigest()!=MD5: raise ValueError('Pinned size/MD5 mismatch')
 members=[]; unpacked=0
 state('VERIFYING',SIZE,'Validating gzipCRC and safe archive paths')
 with gzip.open(path,'rb') as gz,tarfile.open(fileobj=gz,mode='r|') as tar:
  for member in tar:
   admission();rel=PurePosixPath(member.name)
   if rel.is_absolute() or '..' in rel.parts or '\\' in member.name or member.issym() or member.islnk() or member.isdev():
    raise ValueError('Unsafe archive member')
   unpacked+=member.size
   if unpacked>20*1024**3: raise ValueError('Unpacked database exceeds20GiB bound')
   members.append({'name':member.name,'bytes':member.size,'kind':'file' if member.isfile() else 'directory'})
   if member.isfile():
    with tar.extractfile(member) as f:
     for block in iter(lambda:f.read(4*1024**2),b''): admission()
  while gz.read(4*1024**2): admission()
 return {'source_url':URL,'record_doi':'10.5281/zenodo.14897628','database_version':'3',
 'compatible_diamond_pin':'2.1.11','bytes':done,'published_md5':md5.hexdigest(),
 'sha256':sha.hexdigest(),'unpacked_bytes':unpacked,'members':members,'gzip_crc':'PASS',
 'safe_archive_paths':'PASS','verified_utc':utc(),'archive_only_not_installed':True}
def main():
 global CREATION
 if socket.gethostname().upper()!='WD': raise RuntimeError('WD-only guard')
 for attempt in range(30):
  try:
   launch=read(R/'state/launch_completeness_db.json')
   if launch['pid']==os.getpid():CREATION=launch['creation_time_utc'];break
  except (FileNotFoundError,ValueError):pass
  time.sleep(.1)
 if not CREATION:raise RuntimeError('Missing matching process creation receipt')
 lock=(R/'state/completeness_db.lock').open('a+b')
 if lock.tell()==0:lock.write(b' ');lock.flush()
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 status='FAILED';error=None;part=W/'checkm2_database.tar.gz.part';http=W/'http_resume.json';dest=D/'checkm2_database.tar.gz'
 try:
  admission();event('start',pid=os.getpid(),creation_time_utc=CREATION)
  if not dest.exists():
   for attempt in range(1,4):
    admission();start=part.stat().st_size if part.exists() else 0;old=read(http) if http.exists() else {};headers={}
    if start and old.get('etag'):headers={'Range':f'bytes={start}-','If-Range':old['etag']}
    try:
     with requests.get(URL,headers=headers,stream=True,timeout=(20,90),allow_redirects=False) as response:
      if response.status_code not in (200,206):raise RuntimeError(f'Official Zenodo HTTP{response.status_code}; no redirect followed')
      append=start>0 and response.status_code==206 and response.headers.get('Content-Range','').startswith(f'bytes {start}-') and response.headers.get('ETag')==old.get('etag')
      if response.status_code==206 and not append:raise RuntimeError('Unvalidated byte range')
      atomic(http,{'url':URL,'etag':response.headers.get('ETag'),'status':response.status_code,'at':utc()})
      done=start if append else 0;last=0;event('response',attempt=attempt,http_status=response.status_code,resumed_at=done)
      with part.open('ab' if append else 'wb') as f:
       for chunk in response.iter_content(1024**2):
        admission();done+=len(chunk)
        if done>SIZE:raise ValueError('Download exceeds pinned size')
        f.write(chunk)
        if time.monotonic()-last>2:
         f.flush();state('RUNNING',done,'Downloading official CheckM2v3 database');last=time.monotonic()
       f.flush();os.fsync(f.fileno())
     break
    except (requests.RequestException,RuntimeError) as exc:
     event('retry',attempt=attempt,error=repr(exc))
     if attempt==3:raise
     time.sleep(min(2**attempt,8))
   receipt=verify(part);os.replace(part,dest)
  else:receipt=verify(dest)
  atomic(D/'acquisition_receipt.json',receipt);status='COMPLETE'
  state(status,SIZE,'Database archive verified; environment/runtime pilot pending',receipt_path=str(D/'acquisition_receipt.json'),unpacked_bytes=receipt['unpacked_bytes'])
  event('completed',sha256=receipt['sha256'])
 except InterruptedError as exc:
  status='STOPPED';error=repr(exc);state(status,part.stat().st_size if part.exists() else 0,str(exc));event('stopped',error=error)
 except BaseException as exc:
  error=repr(exc);state('FAILED',part.stat().st_size if part.exists() else 0,error);event('failed',error=error);raise
 finally:
  atomic(R/'state/completeness_db_exit.json',{'status':status,'error':error,'pid':os.getpid(),'creation_time_utc':CREATION,'ended_utc':utc()});lock.close()
if __name__=='__main__':main()
