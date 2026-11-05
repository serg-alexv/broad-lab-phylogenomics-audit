"""Offline private-prefix installation and resource-bounded model-loading smoke.

No genome is predicted by this controller. Readiness is committed by the native
controller only after Linux children close and the outside-registry audit passes.
"""
from pathlib import Path, PurePosixPath
import datetime as dt, hashlib,json,os,shutil,signal,subprocess,tarfile,time
R=Path(__file__).resolve().parents[1]
E=R/'evidence/checkm2_runtime';P=R/'tools/checkm2_env';STATE=R/'state/tool_setup_progress.json'
EXPECTED='a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52'
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
OWNER=read(R/'state/launch_tool_setup.json');START=utc();PHASES=[]
def progress(detail,done,total,unit='setup phases',status='RUNNING',**extra):
 save(STATE,{'status':status,'done':done,'total':total,'unit':unit,'detail':detail,
             'pid':OWNER['pid'],'creation_time_utc':OWNER['creation_time_utc'],
             'started_utc':START,'updated_utc':utc(),'log_path':str(R/'logs/checkm2_install.log'),**extra})
def available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
def gate():
 if (R/'state/STOP').exists():raise RuntimeError('STOP requested')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Less than40GiB disk reserve')
 if available()<1024**3:raise RuntimeError('Less than1GiB Linux memory headroom')
def members(group):
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   fields=(p/'stat').read_text().rsplit(')',1)[1].split()
   if int(fields[2])==group:
    status=(p/'status').read_text();rss=int(next((x.split()[1] for x in status.splitlines() if x.startswith('VmRSS:')),'0'))*1024
    out.append({'pid':int(p.name),'start_ticks':int(fields[19]),'rss':rss,'state':fields[0]})
  except (OSError,ValueError,StopIteration,IndexError):pass
 return out
def close_group(child):
 if child.poll() is None:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
 for row in members(child.pid):
  try:os.kill(row['pid'],signal.SIGKILL)
  except ProcessLookupError:pass
 time.sleep(.2)
def run(label,cmd,timeout,maxrss=2*1024**3):
 gate();begin=utc();stem=label.replace(' ','_');out=R/f'logs/checkm2_{stem}.stdout.txt';err=R/f'logs/checkm2_{stem}.stderr.txt'
 peak=0;code=None;failure=None
 with out.open('w') as stdout,err.open('w') as stderr:
  child=subprocess.Popen(cmd,cwd=R,stdout=stdout,stderr=stderr,start_new_session=True)
  identity={'pid':child.pid,'start_ticks':int(Path(f'/proc/{child.pid}/stat').read_text().rsplit(')',1)[1].split()[19])}
  deadline=time.monotonic()+timeout;last=0
  try:
   while child.poll() is None:
    group=members(child.pid);rss=sum(x['rss'] for x in group);peak=max(peak,rss)
    gate()
    if rss>maxrss:raise RuntimeError(f'{label} process-group RSS exceeds2GiB')
    if time.monotonic()>deadline:raise RuntimeError(f'{label} deadline exceeded')
    if time.monotonic()-last>=3:
     progress(f'{label};2threads; sampled groupRSS{rss//1024**2}MiB; no user input required',len(PHASES),4,linux_process=identity,sampled_peak_group_rss_bytes=peak);last=time.monotonic()
    time.sleep(.5)
   code=child.returncode
   if code!=0:raise RuntimeError(f'{label} exited{code}; see {err.name}')
  except BaseException as exc:failure=repr(exc);close_group(child)
  finally:
   remaining=members(child.pid)
   if remaining:close_group(child);remaining=members(child.pid)
   receipt={'phase':label,'started_utc':begin,'ended_utc':utc(),'command':cmd,'process_creation_identity':identity,
            'exit_code':child.returncode,'sampled_peak_group_rss_bytes':peak,'process_group_empty':not remaining,
            'stdout':str(out.relative_to(R)),'stderr':str(err.relative_to(R)),'error':failure}
   PHASES.append(receipt);save(E/f'{stem}_exit.json',receipt)
 if remaining:raise RuntimeError(f'{label} descendants remain after closure')
 if failure:raise RuntimeError(failure)
 return receipt
def installed_set():
 result={}
 for p in (P/'conda-meta').glob('*.json'):
  r=read(p);result[r['name']]=(r['version'],r['build'],r.get('sha256'),r.get('md5'))
 return result
def package_matches(records):
 actual=installed_set()
 return len(actual)==len(records) and all(r['name'] in actual and actual[r['name']][:2]==(r['version'],r['build'])
     and actual[r['name']][2] in (None,r['sha256']) and actual[r['name']][3]==r['md5'] for r in records)
def extract_database():
 base=R/'tools/databases/checkm2_v3';archive=base/'checkm2_database.tar.gz';receipt=read(base/'acquisition_receipt.json')
 if sha(archive)!=receipt['sha256']:raise RuntimeError('CheckM2 database archive SHA mismatch')
 final=base/'data';done=base/'extracted_receipt.json'
 if done.exists():
  prior=read(done);db=R/prior['database_path']
  if db.is_file() and db.stat().st_size==prior['bytes'] and sha(db)==prior['sha256']:return prior
  raise RuntimeError('Committed extracted database mismatch')
 if final.exists():raise RuntimeError('Uncommitted extracted database path exists')
 staging=base/f'.extracting-{os.getpid()}';staging.mkdir()
 expected={x['name']:x for x in receipt['members']};seen=set();last=0
 with tarfile.open(archive,'r:gz') as tar:
  for item in tar:
   gate();rel=PurePosixPath(item.name)
   if rel.is_absolute() or '..' in rel.parts or item.name not in expected:raise RuntimeError('Unexpected database archive path')
   if item.name in seen:raise RuntimeError('Duplicate archive member')
   seen.add(item.name);target=staging.joinpath(*rel.parts)
   if item.isdir():target.mkdir(parents=True,exist_ok=True);continue
   if not item.isfile() or item.size!=expected[item.name]['bytes']:raise RuntimeError('Unexpected database archive member kind/size')
   target.parent.mkdir(parents=True,exist_ok=True);count=0
   with tar.extractfile(item) as src,target.open('wb') as dst:
    for chunk in iter(lambda:src.read(1024**2),b''):
     gate();count+=len(chunk);dst.write(chunk)
     if time.monotonic()-last>3:
      progress(f'Extracting verified CheckM2 database: {count:,}/{item.size:,}bytes',len(PHASES),4);last=time.monotonic()
    dst.flush();os.fsync(dst.fileno())
   if count!=item.size:raise RuntimeError('Truncated database member')
 if seen!=set(expected):raise RuntimeError('Missing database member')
 db=staging/'CheckM2_database/uniref100.KO.1.dmnd';digest=sha(db)
 os.replace(staging,final);db=final/'CheckM2_database/uniref100.KO.1.dmnd'
 obj={'status':'EXTRACTED_ARCHIVE_VERIFIED','at_utc':utc(),'database_version':'3','archive_sha256':receipt['sha256'],
      'database_path':db.relative_to(R).as_posix(),'bytes':db.stat().st_size,'sha256':digest,'genomic_prediction':'NOT_RUN'}
 save(done,obj);return obj
def manifest(folder,target):
 rows=[]
 for parent,dirs,files in os.walk(folder,followlinks=False):
  for name in list(dirs)+files:
   p=Path(parent)/name;rel=p.relative_to(R).as_posix()
   if p.is_symlink():
    value=os.readlink(p);rows.append({'path':rel,'kind':'symlink','target':value,'sha256':hashlib.sha256(value.encode()).hexdigest()})
   elif p.is_file():rows.append({'path':rel,'kind':'file','bytes':p.stat().st_size,'sha256':sha(p)})
 obj={'created_utc':utc(),'root':folder.relative_to(R).as_posix(),'artifacts':rows}
 save(target,obj);return {'path':target.relative_to(R).as_posix(),'sha256':sha(target),'files':len(rows)}
def main():
 if os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Private namespace gate missing')
 if not bool(os.statvfs('/').f_flag&os.ST_RDONLY) or bool(os.statvfs(R).f_flag&os.ST_RDONLY):raise RuntimeError('Effective mount gate failed')
 allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,set(allowed[:2]))
 gate();records_path=E/'resolved_packages.json'
 if sha(records_path)!=EXPECTED:raise RuntimeError('Pinned closure hash mismatch')
 records=read(records_path);handoff=read(E/'cache_handoff.json')
 if handoff.get('status')!='CACHE_AND_ARCHIVE_INSPECTION_COMPLETE':raise RuntimeError('Package cache handoff not accepted')
 db=extract_database();progress('Verified database extracted; installing exact offline CPU package closure',0,4)
 if P.exists() and any(P.iterdir()):
  if not package_matches(records):raise RuntimeError('Existing unaccepted prefix differs/incomplete; preserve for explicit bounded recovery')
  PHASES.append({'phase':'install','status':'VERIFIED_COMPLETE_PREFIX_REUSE','at_utc':utc()})
 else:
  run('install',['/root/miniconda3/bin/conda','create','--offline','--json','--solver','classic','--no-default-packages','--copy','-y','-p',str(P),'--file',str(E/'checkm2_install_explicit_local.txt')],3600)
 if not package_matches(records):raise RuntimeError('Installed package set/version/build/SHA mismatch')
 progress('Installed133 pinned CPU packages; version and model-loading smoke next',1,4)
 run('cli_smoke',[str(P/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--cli'],600)
 run('model_smoke',[str(P/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--models','--database',str(R/db['database_path'])],600)
 progress('All smoke children closed; recording installed files/model hashes',3,4)
 installed=manifest(P,R/'manifests/checkm2_environment_files.json')
 modelroot=next((P/'lib').glob('python*/site-packages/checkm2'))/'models'
 models=manifest(modelroot,R/'manifests/checkm2_model_files.json')
 obj={'status':'CANDIDATE_ENVIRONMENT_SMOKE_PASS','created_utc':utc(),'prefix_linux':str(P),'checkm2_version':'1.1.0','diamond_version':'2.1.11',
      'package_count':len(records),'resolved_packages_sha256':EXPECTED,'installed_manifest':installed,'models_manifest':models,
      'database':db,'phases':PHASES,'import_smoke_passed':True,'model_load_smoke_passed':True,
      'smoke_receipt_path':'evidence/checkm2_runtime/runtime_smoke_receipt.json','scientific_prediction':'NOT_RUN'}
 save(E/'environment_candidate_receipt.json',obj);progress('Private runtime smoke complete; outside-registry audit pending',4,4,status='COMPLETE')
 print(json.dumps(obj),flush=True)
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  save(E/'private_install_linux_failure.json',{'at_utc':utc(),'error':repr(exc),'phases':PHASES,'prefix_preserved':P.exists(),'scientific_prediction':'NOT_RUN'})
  progress(repr(exc),len(PHASES),4,status='FAILED');raise
