"""Acquire/inspect one exact official wheel; no pip, scientific imports or base writes."""
from pathlib import Path,PurePosixPath
import base64,csv,ctypes,datetime as dt,email.parser,hashlib,io,json,msvcrt,os,shutil,stat,struct,sys,time,uuid,zipfile
from ctypes import wintypes
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime';W=R/'work/sklearn161_overlay';FINAL=R/'tools/sklearn161_overlay';SITE=FINAL/'site-packages';SOURCES=R/'tools/sklearn161_overlay_sources'
sys.path.insert(0,str(R/'tools/python_lib'))
import requests
FN='scikit_learn-1.6.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
EXPECTED='2e69fab4ebfc9c9b580a7a80111b43d214ab06250f8a7ef590a4edf72464dd86';BYTES=13147700
URL='https://files.pythonhosted.org/packages/29/7a/8bce8968883e9465de20be15542f4c7e221952441727c4dad24d534c6d99/'+FN
STATE={};LAST=0
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 for _ in range(20):
  try:os.replace(tmp,p);return
  except PermissionError:time.sleep(.1)
 raise RuntimeError('Atomic overlay receipt busy')
def linux(p):return '/mnt/c/'+str(p)[3:].replace('\\','/')
class FileTime(ctypes.Structure):_fields_=[('lo',wintypes.DWORD),('hi',wintypes.DWORD)]
def identity():
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=wintypes.HANDLE;k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(FileTime)]*4
 c,e,u,s=FileTime(),FileTime(),FileTime(),FileTime()
 if not k.GetProcessTimes(k.GetCurrentProcess(),ctypes.byref(c),ctypes.byref(e),ctypes.byref(u),ctypes.byref(s)):raise ctypes.WinError(ctypes.get_last_error())
 ticks=(c.hi<<32)|c.lo;seconds,part=divmod(ticks,10_000_000);stamp=dt.datetime(1601,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(seconds=seconds)
 return {'pid':os.getpid(),'creation_time_utc':stamp.strftime('%Y-%m-%dT%H:%M:%S')+f'.{part:07d}Z','windows_creation_filetime_100ns':ticks}
def gate():
 if (R/'state/STOP').exists():raise InterruptedError('STOP requested')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Less than40GiB host reserve')
def progress(detail,done=0,total=1,unit='overlay preparation phases',status='RUNNING'):
 global LAST
 STATE.update(status=status,detail=detail,done=done,total=total,unit=unit,updated_utc=utc());atomic(R/'state/tool_setup_progress.json',STATE);atomic(R/'state/sklearn_overlay_progress.json',STATE);LAST=time.monotonic()
def safe(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or '\0' in name or not p.parts:raise RuntimeError('Unsafe wheel member '+name)
 if p.parts[0] not in ('sklearn','scikit_learn.libs','scikit_learn-1.6.1.dist-info'):raise RuntimeError('Unexpected wheel layout '+name)
 return p
def elf(data):
 if data[:6]!=b'\x7fELF\x02\x01':raise RuntimeError('Native member is not ELF64 little-endian')
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);ph=[]
 if h[2]!=62 or h[9]!=56 or h[5]+h[9]*h[10]>len(data):raise RuntimeError('Native ELF machine/header mismatch')
 for i in range(h[10]):ph.append(struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9]))
 dynamic=next((p for p in ph if p[0]==2),None);needed=[]
 if dynamic:
  entries=[]
  for pos in range(dynamic[2],dynamic[2]+dynamic[5],16):
   tag,value=struct.unpack_from('<QQ',data,pos)
   if not tag:break
   entries.append((tag,value))
  string_address=next((v for tag,v in entries if tag==5),None)
  segment=next((p for p in ph if p[0]==1 and string_address is not None and p[3]<=string_address<p[3]+p[5]),None)
  if segment:
   strings=segment[2]+string_address-segment[3]
   for tag,value in entries:
    if tag==1:
     start=strings+value;end=data.index(b'\0',start);needed.append(data[start:end].decode('ascii'))
 # These are actual symbol-version requirements from .gnu.version_r, not a guess from strings.
 versions=[]
 if h[6] and h[11]==64:
  sections=[struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*64) for i in range(h[12])]
  for section in sections:
   if section[1]!=0x6ffffffe:continue
   linked=sections[section[6]];strings=data[linked[4]:linked[4]+linked[5]];pos=section[4];limit=section[4]+section[5]
   for _ in range(1000):
    if pos>=limit:break
    _,count,_,aux,nxt=struct.unpack_from('<HHIII',data,pos);ap=pos+aux
    for _ in range(count):
     _,_,_,index,anext=struct.unpack_from('<IHHII',data,ap);versions.append(strings[index:strings.index(b'\0',index)].decode('ascii'))
     if not anext:break
     ap+=anext
    if not nxt:break
    pos+=nxt
 glibc=[tuple(map(int,v.split('_',1)[1].split('.'))) for v in versions if v.startswith('GLIBC_') and v.split('_',1)[1].replace('.','').isdigit()]
 if glibc and max(glibc)>(2,43):raise RuntimeError('Wheel needs newer glibc than host')
 return {'machine':62,'needed_shared_libraries':needed,'symbol_versions_required':sorted(set(versions)),'maximum_glibc_required':'.'.join(map(str,max(glibc))) if glibc else None,'gnu_stack_flags':[p[1] for p in ph if p[0]==0x6474e551]}
def main():
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only overlay preparation')
 if FINAL.exists():raise RuntimeError('Overlay destination already exists; preserve without overwrite')
 lock=(R/'state/checkm2_install.lock').open('r+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 owner=identity();STATE.update(owner,started_utc=utc(),log_path=str(E/'sklearn161_overlay_preparation.json'))
 atomic(R/'state/launch_tool_setup.json',{**owner,'script':'scripts/prepare_sklearn161_overlay.py','phase':'STATIC_MATCHING_SKLEARN_OVERLAY_PREPARATION'})
 status='FAILED';failure=None;receipt={};W.mkdir(parents=True,exist_ok=True);SOURCES.mkdir(parents=True,exist_ok=True)
 try:
  gate();progress('Fetching official release metadata for the exact matching-version wheel; no imports')
  with requests.Session() as session:
   response=session.get('https://pypi.org/pypi/scikit-learn/1.6.1/json',timeout=(15,45),allow_redirects=False)
   if response.status_code!=200:raise RuntimeError('Official metadata HTTP '+str(response.status_code))
   raw=response.content;metadata=response.json();row=next(x for x in metadata['urls'] if x['filename']==FN)
   if row['digests']['sha256']!=EXPECTED or row['size']!=BYTES or row['url']!=URL or row['yanked']:raise RuntimeError('Official exact-wheel metadata mismatch')
   (SOURCES/'pypi_scikit_learn_1.6.1.json').write_bytes(raw)
   wheel=SOURCES/FN;part=W/(FN+'.part')
   if wheel.exists():
    if wheel.stat().st_size!=BYTES or sha(wheel)!=EXPECTED:raise RuntimeError('Existing wheel bytes mismatch')
   else:
    progress('Downloading one exact official scikit-learn1.6.1 wheel',0,BYTES,'bytes')
    with session.get(URL,timeout=(15,60),stream=True,allow_redirects=False) as response:
     if response.status_code!=200:raise RuntimeError('Wheel HTTP '+str(response.status_code)+'; redirects forbidden')
     count=0
     with part.open('wb') as out:
      for block in response.iter_content(1024**2):
       gate();count+=len(block)
       if count>BYTES:raise RuntimeError('Wheel exceeds pinned bytes')
       out.write(block)
       if time.monotonic()-LAST>2:progress('Acquiring exact official wheel; no runtime imports',count,BYTES,'bytes')
      out.flush();os.fsync(out.fileno())
    if count!=BYTES or sha(part)!=EXPECTED:raise RuntimeError('Wheel compressed bytes/SHA mismatch')
    os.replace(part,wheel)
  source={'status':'EXACT_OFFICIAL_WHEEL_VERIFIED','created_utc':utc(),'metadata_source':'https://pypi.org/pypi/scikit-learn/1.6.1/json','metadata_sha256':hashlib.sha256(raw).hexdigest(),'wheel':row,'wheel_path':str(wheel.relative_to(R)),'no_redirects_followed':True}
  atomic(E/'sklearn161_wheel_acquisition.json',source)
  stage=W/('staging_'+uuid.uuid4().hex);site=stage/'site-packages';site.mkdir(parents=True);files=[];native=[];notices=[]
  with zipfile.ZipFile(wheel) as archive:
   members=archive.infolist();names={};total=sum(m.file_size for m in members)
   if len(members)>10000 or total>256*1024**2:raise RuntimeError('Unexpected wheel extraction bound')
   for item in members:
    rel=safe(item.filename);key=str(rel).casefold()
    if key in names:raise RuntimeError('Duplicate/case-colliding wheel paths')
    names[key]=item.filename
    mode=(item.external_attr>>16)&0xffff
    if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):raise RuntimeError('Wheel contains non-regular payload')
   if archive.testzip() is not None:raise RuntimeError('Wheel ZIP checksum failure')
   meta_name='scikit_learn-1.6.1.dist-info/METADATA';wheel_name='scikit_learn-1.6.1.dist-info/WHEEL';record_name='scikit_learn-1.6.1.dist-info/RECORD'
   meta_bytes=archive.read(meta_name)
   if hashlib.sha256(meta_bytes).hexdigest()!=row['core-metadata']['sha256']:raise RuntimeError('Official core-metadata hash mismatch')
   meta=email.parser.BytesParser().parsebytes(meta_bytes);wmeta=email.parser.BytesParser().parsebytes(archive.read(wheel_name))
   if meta['Name']!='scikit-learn' or meta['Version']!='1.6.1' or wmeta['Root-Is-Purelib']!='false':raise RuntimeError('Wheel identity/purelib mismatch')
   tags=wmeta.get_all('Tag')
   if not tags or not set(tags).issubset({'cp312-cp312-manylinux_2_17_x86_64','cp312-cp312-manylinux2014_x86_64'}):raise RuntimeError('Wrong wheel ABI tags')
   records={r[0]:r[1:] for r in csv.reader(io.StringIO(archive.read(record_name).decode()))}
   if set(records)!={m.filename for m in members if not m.is_dir()}:raise RuntimeError('RECORD/file inventory mismatch')
   for item in members:
    gate();rel=safe(item.filename)
    if item.is_dir():continue
    data=archive.read(item);digest=hashlib.sha256(data).hexdigest();record_hash,record_size=records[item.filename]
    if item.filename!=record_name:
     if not record_hash.startswith('sha256=') or base64.urlsafe_b64decode(record_hash[7:]+'='*((-len(record_hash[7:]))%4)).hex()!=digest or int(record_size)!=len(data):raise RuntimeError('RECORD payload mismatch '+item.filename)
    target=site.joinpath(*rel.parts);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
    entry={'path':str(PurePosixPath('site-packages')/rel),'bytes':len(data),'sha256':digest,'original_mode':(item.external_attr>>16)&0xffff};files.append(entry)
    if data.startswith(b'\x7fELF'):native.append({'path':entry['path'],**elf(data)})
    if any(x in rel.name.lower() for x in ('license','licence','copying','notice','copyright','authors')):notices.append(entry)
    if time.monotonic()-LAST>2:progress('Verifying and preserving all wheel payload/notices; no imports',len(files),len(records),'wheel files')
  manifest={'status':'COMPLETE_EXACT_WHEEL_PAYLOAD_STATIC_ONLY','created_utc':utc(),'wheel_sha256':EXPECTED,'files':files,'file_count':len(files),'unpacked_bytes':sum(x['bytes'] for x in files),'native_members':native,'original_notices':notices,'metadata':{'Name':meta['Name'],'Version':meta['Version'],'Requires-Python':meta['Requires-Python'],'Requires-Dist':meta.get_all('Requires-Dist'),'wheel_tags':tags},'runtime_import_tested':False,'abi_execution_tested':False}
  atomic(stage/'manifest.json',manifest);os.replace(stage,FINAL)
  ready=read(R/'state/checkm2_runtime_ready.json');base_manifest=read(E/'resolved_packages.json');runtime_model=read(E/'runtime_smoke_receipt.json')
  effective={'schema':'TREE2_EFFECTIVE_RUNTIME_OVERLAY_V1','status':'STATIC_PREPARED_NOT_RUNTIME_VALIDATED','created_utc':utc(),'base_ready_receipt':{'path':'state/checkm2_runtime_ready.json','sha256':sha(R/'state/checkm2_runtime_ready.json')},'base_environment_receipt':{'path':ready['environment_receipt_path'],'sha256':ready['environment_receipt_sha256']},'base_candidate_receipt':{'path':'evidence/checkm2_runtime/environment_candidate_receipt.json','sha256':sha(E/'environment_candidate_receipt.json')},'base_image':ready['runtime_image'],'base_installed_manifest':{'path':ready['installed_manifest_path'],'sha256':ready['installed_manifest_sha256']},'base_models_manifest':{'path':ready['models_manifest_path'],'sha256':ready['models_manifest_sha256']},'base_model_assets':runtime_model['model_files'],'base_resolved_packages':{'path':'evidence/checkm2_runtime/resolved_packages.json','sha256':sha(E/'resolved_packages.json')},'base_versions':{x['name']:x['version'] for x in base_manifest},'shadowed_packages':[{'name':'scikit-learn','base_version':'1.9.1','effective_version':'1.6.1','base_files_and_metadata_modified':False}],'overlay':{'root_windows':str(FINAL),'root_linux':linux(FINAL),'site_packages_windows':str(SITE),'site_packages_linux':linux(SITE),'manifest_path':str((FINAL/'manifest.json').relative_to(R)),'manifest_sha256':sha(FINAL/'manifest.json'),'wheel_path':str(wheel.relative_to(R)),'wheel_sha256':EXPECTED,'wheel_bytes':BYTES,'effective_distribution':'scikit-learn','effective_version':'1.6.1'},'required_runtime_environment':{**ready.get('runtime_environment_overrides',{}),'PYTHONPATH':linux(SITE),'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1'},'readonly_binding_required':True,'effective_import_provenance_and_native_runtime_tested':False,'scaler_equivalence_tested':False,'official_numeric_controls_tested':False,'production_acceptance':'NOT_GRANTED','base_image_bytes_modified':False,'no_pip_solver_or_dependency_installation':True}
  # Serialized project-relative paths use POSIX separators for Linux consumers.
  for field in ('manifest_path','wheel_path'):effective['overlay'][field]=effective['overlay'][field].replace('\\','/')
  effective['launch_protocol']={'bootstrap_required':True,'bootstrap_status':'NOT_YET_PROVIDED_OR_TESTED','reason':'Unchanged CheckM2 main prepends its base site-packages before sklearn imports; PYTHONPATH alone is insufficient','requirements':['Preload and verify overlay sklearn1.6.1/package __path__ before unchanged CheckM2 entrypoint','Recheck effective sklearn submodule origins after upstream sys.path prepend','Read effective distribution metadata directly from pinned overlay dist-info; generic discovery can still find shadowed base1.9.1 first'],'author_entrypoint_source_modified':False}
  effective['effective_packages']=[{'name':x['name'],'version':'1.6.1' if x['name']=='scikit-learn' else x['version'],'origin':'pypi-wheel-overlay' if x['name']=='scikit-learn' else 'immutable-base-conda-prefix','artifact_sha256':EXPECTED if x['name']=='scikit-learn' else x['sha256']} for x in base_manifest]
  atomic(E/'sklearn161_effective_runtime.json',effective)
  receipt={'status':'STATIC_OVERLAY_PREPARED_NOT_RUNTIME_VALIDATED','created_utc':utc(),'native_owner':owner,'wheel_path':str(wheel.relative_to(R)),'wheel_sha256':EXPECTED,'wheel_bytes':BYTES,'overlay_path':str(FINAL.relative_to(R)),'manifest_path':str((FINAL/'manifest.json').relative_to(R)),'manifest_sha256':sha(FINAL/'manifest.json'),'effective_runtime_manifest_path':'evidence/checkm2_runtime/sklearn161_effective_runtime.json','effective_runtime_manifest_sha256':sha(E/'sklearn161_effective_runtime.json'),'files':len(files),'unpacked_bytes':manifest['unpacked_bytes'],'native_elf_members':len(native),'notices_preserved':len(notices),'base_image_writes':False,'imports_performed':False,'installation_performed':False,'production_acceptance':'NOT_GRANTED'}
  for field in ('wheel_path','overlay_path','manifest_path'):receipt[field]=receipt[field].replace('\\','/')
  status='COMPLETE';atomic(E/'sklearn161_overlay_preparation.json',receipt);progress('Exact matching-version overlay prepared; controlled import/numerical/controls validation next',len(files),len(files),'wheel files',status)
 except BaseException as exc:failure=repr(exc);status='STOPPED' if isinstance(exc,InterruptedError) else 'FAILED';progress(failure,status=status)
 finally:
  lock.close();atomic(E/'sklearn161_overlay_execution.json',{'status':status,'error':failure,'native_owner':owner,'ended_utc':utc(),'static_only':True,'no_imports_mounts_predictions_or_base_writes':True,'preparation_receipt':receipt});print(json.dumps({'status':status,'error':failure,'receipt':receipt}),flush=True)
 return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
