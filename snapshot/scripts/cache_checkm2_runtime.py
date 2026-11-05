"""Single-worker exact-source CheckM2 runtime cache, then archive inspection."""
from pathlib import Path
import datetime as dt,hashlib,json,os,shutil,subprocess,sys,time
from urllib.parse import urlparse
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools/python_lib'))
import requests
EXPECTED='a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52'
E=R/'evidence/checkm2_runtime';CACHE=R/'work/checkm2_resolution/channels'
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 for _ in range(20):
  try:os.replace(tmp,p);return
  except PermissionError:time.sleep(.1)
 raise RuntimeError('Atomic state publication remained busy')
class StopRequested(Exception):pass
def gate():
 if (R/'state/STOP').exists():raise StopRequested('STOP requested')
 if shutil.disk_usage(R).free<40*1024**3:raise StopRequested('Less than 40GiB reserve')
def event(kind,**kw):
 row={'at_utc':utc(),'kind':kind,**kw}
 with (R/'logs/cache_checkm2_runtime.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(row),flush=True)
STATE={};LAST=0
def progress(**kw):
 global LAST
 STATE.update(kw);STATE['updated_utc']=utc();atomic(R/'state/tool_setup_progress.json',STATE);LAST=time.monotonic()
def checked(row):
 u=urlparse(row['url']);parts=u.path.strip('/').split('/')
 if u.scheme!='https' or u.netloc!='conda.anaconda.org' or u.query or u.fragment or len(parts)!=3:
  raise ValueError('Nonofficial or malformed package URL')
 channel,subdir,fn=parts
 if channel not in ('conda-forge','bioconda') or subdir not in ('linux-64','noarch') or fn!=row['fn'] or '..' in fn:
  raise ValueError('Package path mismatch')
 return channel,subdir,fn
def cache_one(session,row,done,total,done_bytes,total_bytes):
 gate();channel,subdir,fn=checked(row);dest=CACHE/channel/subdir/fn;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  if dest.stat().st_size==row['size'] and sha(dest)==row['sha256']:return dest,'VERIFIED_CACHE'
  raise RuntimeError('Existing committed package hash mismatch: '+fn)
 for source in (R/'work/conda_channels'/channel/subdir/fn,R/'tools/conda_pkgs'/fn,R/'evidence/completeness_qc'/fn):
  if source.exists() and source.stat().st_size==row['size'] and sha(source)==row['sha256']:
   part=dest.with_name(fn+'.copy.part');shutil.copyfile(source,part)
   if sha(part)!=row['sha256']:raise RuntimeError('Copied cache hash mismatch')
   os.replace(part,dest);return dest,'VERIFIED_LOCAL_REUSE'
 part=dest.with_name(fn+'.part');http=dest.with_name(fn+'.http.json')
 for attempt in range(1,5):
  gate();old=load(http) if http.exists() else {};size=part.stat().st_size if part.exists() else 0
  if size==row['size'] and sha(part)==row['sha256']:
   os.replace(part,dest);return dest,'VERIFIED_COMPLETE_PARTIAL'
  headers={};etag=old.get('etag')
  if size and etag and old.get('expected_sha256')==row['sha256']:
   headers={'Range':f'bytes={size}-','If-Range':etag}
  try:
   with session.get(row['url'],headers=headers,timeout=(20,90),stream=True,allow_redirects=False) as response:
    if response.status_code not in (200,206):raise RuntimeError(f'HTTP{response.status_code}; redirects forbidden')
    append=(size>0 and response.status_code==206 and response.headers.get('Content-Range','').startswith(f'bytes {size}-') and response.headers.get('ETag')==etag)
    if response.status_code==206 and not append:raise RuntimeError('Unverified byte range')
    if size and not append:os.replace(part,part.with_name(part.name+'.superseded-'+str(time.time_ns())))
    atomic(http,{'url':row['url'],'etag':response.headers.get('ETag'),'expected_sha256':row['sha256'],'expected_bytes':row['size'],'http_status':response.status_code,'at_utc':utc()})
    count=size if append else 0
    with part.open('ab' if append else 'wb') as f:
     for chunk in response.iter_content(1024**2):
      gate()
      if not chunk:continue
      count+=len(chunk)
      if count>row['size']:raise ValueError('Package exceeds pinned size')
      f.write(chunk)
      if time.monotonic()-LAST>=2:
       f.flush();progress(status='RUNNING',done=done,total=total,unit='packages',detail=f'Caching {row["name"]}: {count:,}/{row["size"]:,} bytes; no user input required',bytes_done=done_bytes+count,bytes_total=total_bytes,current_package=fn)
     f.flush();os.fsync(f.fileno())
   if count!=row['size'] or sha(part)!=row['sha256']:
    os.replace(part,part.with_name(part.name+'.rejected-'+str(time.time_ns())))
    raise ValueError('Pinned compressed size or SHA256 mismatch')
   os.replace(part,dest);return dest,'DOWNLOADED_VERIFIED'
  except StopRequested:raise
  except (requests.RequestException,RuntimeError,ValueError) as exc:
   event('package_retry',package=fn,attempt=attempt,error=str(exc))
   if attempt==4:raise
   time.sleep(min(2**attempt,16))
 raise RuntimeError('Unreachable retry state')
def main():
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only cache')
 import msvcrt
 lock=(R/'state/checkm2_cache.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 manifest=E/'resolved_packages.json'
 if sha(manifest)!=EXPECTED:raise RuntimeError('Resolved manifest changed; stop before acquisition')
 rows=load(manifest);assert len(rows)==133 and sum(x['size'] for x in rows)==727128168
 for row in rows:checked(row)
 for _ in range(40):
  owner=load(R/'state/launch_tool_setup.json') if (R/'state/launch_tool_setup.json').exists() else {}
  if owner.get('pid')==os.getpid():break
  time.sleep(.1)
 else:raise RuntimeError('No matching native launch identity')
 STATE.update(status='RUNNING',done=0,total=len(rows),unit='packages',detail='Caching exact CPU-only CheckM2 runtime; no user input required',pid=os.getpid(),creation_time_utc=owner['creation_time_utc'],started_utc=utc(),log_path=str(R/'logs/cache_checkm2_runtime.jsonl'))
 progress();event('cache_start',pid=os.getpid(),manifest_sha256=EXPECTED,packages=len(rows),bytes=sum(x['size'] for x in rows))
 receipts=[];done_bytes=0;status='FAILED';error=None
 try:
  with requests.Session() as session:
   session.headers['User-Agent']='Tree2-WD-local-verified-runtime/1.0'
   for row in rows:
    path,action=cache_one(session,row,len(receipts),len(rows),done_bytes,sum(x['size'] for x in rows))
    receipt={k:row[k] for k in ('name','version','build','fn','url','sha256','size','subdir','channel_name')}
    receipt.update(path=str(path.relative_to(R)),action=action,verified_utc=utc());receipts.append(receipt);done_bytes+=row['size']
    atomic(E/'package_cache_progress.json',{'manifest_sha256':EXPECTED,'packages':receipts,'cached':len(receipts),'bytes':done_bytes})
    progress(done=len(receipts),bytes_done=done_bytes,bytes_total=sum(x['size'] for x in rows),detail=f'Cached and SHA256 verified {len(receipts)}/{len(rows)} packages')
    event('package_cached',name=row['name'],bytes=row['size'],action=action,cumulative_packages=len(receipts))
  atomic(E/'package_cache_receipt.json',{'status':'ALL_ARCHIVES_CACHED_SHA256_VERIFIED','manifest_sha256':EXPECTED,'packages':receipts,'total_bytes':done_bytes,'completed_utc':utc()})
  progress(done=0,total=len(rows),unit='packages inspected',detail='Inspecting archive safety, unpacked bytes and original notices')
  linux='/mnt/c/'+str(R)[3:].replace('\\','/')
  with (R/'logs/checkm2_archive_inspection.stdout.jsonl').open('w') as out,(R/'logs/checkm2_archive_inspection.stderr.txt').open('w') as err:
   child=subprocess.Popen(['wsl','-d','Ubuntu','--','/usr/bin/python3','-B',linux+'/scripts/inspect_checkm2_archives.py'],stdout=out,stderr=err)
   while child.poll() is None:
    p=R/'state/checkm2_inspection_progress.json'
    if p.exists():
     q=load(p);progress(done=q.get('done',0),total=q.get('total',len(rows)),unit='packages inspected',detail=q.get('detail','Inspecting archives'))
    else:progress()
    time.sleep(2)
   if child.returncode==130:raise StopRequested('Archive inspection acknowledged STOP')
   if child.returncode:raise RuntimeError('Archive inspection failed; see inspection stderr')
  handoff=load(E/'cache_handoff.json');assert handoff['status']=='CACHE_AND_ARCHIVE_INSPECTION_COMPLETE'
  status='COMPLETE';progress(status=status,done=len(rows),total=len(rows),unit='packages',detail='133 exact CPU archives verified and inspected; private installation next',receipt_path=str(E/'cache_handoff.json'))
 except StopRequested as exc:status='STOPPED';error=str(exc);progress(status=status,detail=error)
 except Exception as exc:error=repr(exc);progress(status=status,detail=error)
 finally:
  atomic(E/'cache_execution_receipt.json',{'status':status,'error':error,'pid':os.getpid(),'creation_time_utc':owner['creation_time_utc'],'ended_utc':utc(),'cached_packages':len(receipts),'cached_bytes':done_bytes,'manifest_sha256':EXPECTED,'environment_installed':False,'biological_qc_run':False})
  lock.close();event('cache_exit',status=status,error=error,cached_packages=len(receipts))
 return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
