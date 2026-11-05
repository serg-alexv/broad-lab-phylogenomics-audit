"""Root's one-time 04R1 admission; no scientific imports or prediction launch."""
from pathlib import Path
import ctypes, datetime as dt, hashlib, json, os, shutil, subprocess
from ctypes import wintypes

R=Path(__file__).resolve().parents[1]
STOP=R/'state/STOP_CHECKM2_PILOT'
ADMIT=R/'state/checkm2_protein_strategy_ready_v001.json'
E=R/'evidence/checkm2_protein_pilot_v001/root_admission'
STOP_SHA='352c2cacb99a5ba33cd8e35da845a5a32c6404eb137ae0558ac112477e69db16'
OWNER='583d75993ca445fca988f7c7264e15e8'
PINS={
 'metadata/checkm2_protein_strategy_template_v001.json':'11671a5b3ddf9dca0c503c43d358b896959a256c0f1c3c9411258799c93421c2',
 'metadata/checkm2_protein_implementation_v001.json':'87ce9cec98b7d109f2d34df3ac1671941ceec01e64bfe0b4a64fa2389707ed47',
 'metadata/checkm2_protein_v001_source_admission_review.json':'66efc254f81f00ba37d1603ebbf3fac259575393c9d6395e84a524e8d3ece4e7',
 'evidence/checkm2_protein_pilot_v001/resource_lifecycle_source_review.json':'be10ce9adf4fe0b63efd37b1b4863a2b359e4dcf950e161bf1f3d2078d3dc516',
 'scripts/live_stage_publisher.py':'67ac44ef2e0fd04af64c3a517a2c5390401e12d6dd2f6082a5e720488be2fb37'}

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inside(p):
 p=str(p)
 if p.startswith('/mnt/c/'):p='C:/'+p[7:]
 p=Path(p);p=(p if p.is_absolute() else R/p).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Admission path escapes project')
 return p
def bound(row):
 p=inside(row['path'])
 if sha(p)!=row['sha256'] or ('bytes' in row and p.stat().st_size!=row['bytes']):raise RuntimeError('Binding mismatch: '+row['path'])
 return p
def save_new(p,data):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('Refusing existing admission artifact: '+str(p))
 t=p.with_name(p.name+'.pending')
 with t.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.rename(t,p)

def main():
 if os.name!='nt' or os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only root admission')
 if ADMIT.exists() or E.exists() or (R/'state/STOP').exists():raise RuntimeError('Existing admission/root stop; preserve state')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Backing-volume reserve below40GiB')
 for rel,digest in PINS.items():
  if sha(R/rel)!=digest:raise RuntimeError('Root-reviewed pin changed: '+rel)
 strategy=read(R/'metadata/checkm2_protein_strategy_template_v001.json')
 contract=read(R/'metadata/checkm2_protein_implementation_v001.json')
 for row in strategy['sources']:bound(row)
 if strategy['sources']!=contract['sources']:raise RuntimeError('Contract/template source sets differ')
 for key in ('engineering_execution','engineering_native_closure','engineering_linux_closure','feature_schema'):bound(strategy[key])
 bound(contract['fixture_report'])
 item=read(R/'analysis/checkm2_pilot/pilot_plan.json')['input']
 canon=hashlib.sha256(json.dumps(item,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 if canon!=strategy['input_binding_sha256']:raise RuntimeError('Original input binding changed')
 source=inside(item['fasta_path'])
 if sha(source)!=item['fasta_sha256'] or source.stat().st_size!=item['fasta_bytes']:raise RuntimeError('Original FNA changed')
 for p,digest in [(R/'raw'/item['accession']/'acquisition_receipt.json',item['acquisition_receipt_sha256']),(R/'qc/source_provenance_audit.json',item['source_provenance_audit_sha256']),(R/'metadata/provisional_panel.json',item['provisional_panel_sha256'])]:
  if sha(p)!=digest:raise RuntimeError('Source/selection binding changed')
 original=STOP.read_bytes()
 if hashlib.sha256(original).hexdigest()!=STOP_SHA or read(STOP)['owner_token']!=OWNER:raise RuntimeError('Owned hold changed; preserve user state')
 publication=read(R/'state/launch_live_publisher.json');console=read(R/'state/launch_live_console.json')
 ps="$ErrorActionPreference='Stop'; $rows=@(); foreach($n in @("+str(publication['pid'])+','+str(console['pid'])+")){$p=Get-Process -Id $n; $rows+=@{pid=$p.Id;birth=$p.StartTime.ToUniversalTime().ToString('o');responding=$p.Responding}}; $rows|ConvertTo-Json -Compress"
 observed=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps],text=True,creationflags=0x08000000))
 by={x['pid']:x for x in observed}
 for identity in (publication,console):
  if by[identity['pid']]['birth']!=identity['creation_time_utc']:raise RuntimeError('Monitor/publisher birth differs')
 journal=read(R/'state/live_stages.json')
 if journal['publisher_pid']!=publication['pid'] or 'checkm2_protein_pilot_v001' not in journal['stages'][4]['substeps']:raise RuntimeError('New monitor adapter is not live')
 native=ctypes.WinDLL('kernel32',use_last_error=True)
 native.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];native.CreateFileW.restype=wintypes.HANDLE
 native.CloseHandle.argtypes=[wintypes.HANDLE];handles=[];published=False;removed=False
 try:
  for name in ('checkm2_pilot_launcher.lock','checkm2_install.lock'):
   handle=native.CreateFileW(str(R/'state'/name),0xC0000000,0,None,3,0x80,None)
   if handle in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
   handles.append(handle)
  linux='/mnt/'+R.drive[0].lower()+'/'+str(R)[3:].replace('\\','/')
  code="import fcntl,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); f=(p/'state/checkm2_pilot.lock').open('rb'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print(json.dumps({'status':'CURRENT_LINUX_COMPUTE_LOCK_REACQUIRED_RELEASED','boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()})); f.close()"
  linux_probe=json.loads(subprocess.check_output(['wsl','-d','Ubuntu','--','/usr/bin/python3','-B','-c',code,linux],text=True,timeout=30,creationflags=0x08000000))
  E.mkdir(parents=True,exist_ok=False)
  with (E/'original_owned_resource_STOP.json').open('xb') as f:f.write(original);f.flush();os.fsync(f.fileno())
  proof={'at_utc':utc(),'decision':'04R1','reviewed_pins':PINS,'all12_executed_sources_rehashed':True,'original_FNA_sha256':item['fasta_sha256'],'current_native_locks_exclusively_owned':True,'current_linux_compute_probe':linux_probe,'monitor_observations':observed,'publisher_script_sha256':PINS['scripts/live_stage_publisher.py'],'production_acceptance':False}
  save_new(E/'root_validation.json',proof)
  if STOP.read_bytes()!=original or (R/'state/STOP').exists():raise RuntimeError('Hold/global stop changed before transition')
  STOP.unlink();removed=True
  transition={'authorized_by_decision':'04R1','at_utc':utc(),'removed_marker_sha256':STOP_SHA,'removed_owner_token':OWNER,'old_marker_removed':True,'preserved_marker_path':(E/'original_owned_resource_STOP.json').relative_to(R).as_posix(),'validation_receipt_path':(E/'root_validation.json').relative_to(R).as_posix(),'validation_receipt_sha256':sha(E/'root_validation.json'),'scope':'Exactly one stock supported-protein diagnostic; no production acceptance'}
  save_new(E/'owned_hold_transition.json',transition)
  strategy.update(status='ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT',biological_dispatch_authorized=True,monitor_adapter_ready=True,created_utc=utc(),root_decision='04R1',source_review_receipt={'path':'metadata/checkm2_protein_v001_source_admission_review.json','sha256':PINS['metadata/checkm2_protein_v001_source_admission_review.json']},resource_review_receipt={'path':'evidence/checkm2_protein_pilot_v001/resource_lifecycle_source_review.json','sha256':PINS['evidence/checkm2_protein_pilot_v001/resource_lifecycle_source_review.json']},owned_resource_hold_transition={'path':(E/'owned_hold_transition.json').relative_to(R).as_posix(),'sha256':sha(E/'owned_hold_transition.json')})
  save_new(ADMIT,strategy);published=True
  print(json.dumps({'status':strategy['status'],'admission_path':ADMIT.relative_to(R).as_posix(),'admission_sha256':sha(ADMIT),'source_count':len(strategy['sources']),'monitor_publisher_pid':publication['pid'],'biological_run_launched':False,'production_acceptance':False}))
 finally:
  if removed and not published and not STOP.exists():
   with STOP.open('xb') as f:f.write(original);f.flush();os.fsync(f.fileno())
  for handle in handles:native.CloseHandle(handle)

if __name__=='__main__':main()
