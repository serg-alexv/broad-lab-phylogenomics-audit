"""One saved-stock companion plan; no annotation/search replay or dispatcher replacement."""
from pathlib import Path
import os,json,math,hashlib,shutil,time
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;read=old.read;save=old.save;row=old.row
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;pending_is_current=old.pending_is_current
E=R/'work/checkm2_parallel_saved_native_v001';OUT=R/'analysis/checkm2_parallel_saved_stock_v001';SCORE=OUT/'score'
STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_owner.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state/STOP_CHECKM2_PARALLEL_SAVED_STOCK_V001';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
ROLE='PARALLEL_SAVED_STOCK_SCORE_ONLY_V001';PLAN=None
LIMITS={'cpu':0,'stock_threads':1,'linux_total_rss_bytes':1543503872,'native_reserved_bytes':67108864,'total_owned_rss_bytes':1610612736,'linux_available_minimum_bytes':1879048192,'fresh_launch_available_minimum_bytes':3100000000,'disk_reserve_bytes':42949672960,'stock_seconds':548.0189570170041,'feature_seconds':120}

def sha(p):
 h=hashlib.sha256()
 with path(p).open('rb')as f:
  for data in iter(lambda:f.read(4096),b''):h.update(data)
 return h.hexdigest()
def bind(ref):
 p=path(ref['path'])
 if sha(p)!=ref['sha256']or('bytes'in ref and p.stat().st_size!=ref['bytes']):raise RuntimeError('Bound source/artifact changed: '+str(p))
 return p
def stop():
 if any(p.exists()for p in(STOP,R/'state/STOP',R/'state/STOP_CHECKM2_PILOT')):raise InterruptedError('QC scoped/global STOP')
def plan_gate(plan_path,expected_sha,require_admission=True,closed_finalization=False):
 global PLAN
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Parallel scoring plan changed')
 plan=read(p);PLAN=plan
 if plan.get('schema')!='TREE2_PARALLEL_SAVED_STOCK_RUNTIME_PLAN_V001':raise RuntimeError('Wrong one-target saved-stock plan')
 if plan['limits']!=LIMITS:raise RuntimeError('Final reviewed native/Linux/phase limits differ')
 if plan['saved_phase_authority']['sha256']!='8f95dce8536471676c08a9b045c31a1833dd37931e7d55fb438238e7718c0f19':raise RuntimeError('Exact closed saved-phase authority required')
 bind(plan['saved_phase_authority'])
 for r in read(bind(plan['source_manifest']))['sources']:bind(r)
 for k in('launch','admission'):bind(plan['companion_marker'][k])
 if plan['companion_marker']['native_owner']!={'pid':25068,'windows_creation_filetime_100ns':134376161790353810,'creation_time_utc':'2026-10-27T23:09:39.0353810Z'}or plan['companion_marker']['linux_owner']!={'pid':44402,'creation_ticks':11781228,'boot_id':'36042473-9bf3-466d-a2f5-bc314c3358c6'}:raise RuntimeError('Only the exact Root-known marker companion is permitted')
 if UNRESOLVED_HANDOFF.exists()or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unresolved QC owner blocks launch')
 if not closed_finalization and (SCORE/'once_claim.json').exists():raise RuntimeError('Saved scoring once claim consumed, no implicit retry')
 if not require_admission:return plan,{},None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_PARALLEL_SAVED_STOCK_RECOVERY_V001'or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('limits')!=LIMITS or admitted.get('saved_stock_execution_authorized')is not True or admitted.get('no_annotation_or_search_replay')is not True:raise RuntimeError('Separate exact parallel scoring admission required')
 if path(admitted.get('output_root',''))!=SCORE or path(admitted.get('scoped_stop',''))!=STOP or admitted.get('helper_max_seconds')!=900:raise RuntimeError('Own output/stop/core deadline differs')
 actual=read(bind(admitted['preflight_actual_exit']))
 if type(actual.get('actual_exit_code'))is not int or actual.get('actual_exit_code')!=0 or actual.get('exact_birth_handle_retained')is not True:raise RuntimeError('Fresh read-only preflight observed0 required')
 bind(admitted['preflight_receipt']);return plan,{},admitted

def linux_available():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024

def linux_guard(fresh=False):
 import checkm2_owned_cleanup_T1 as own
 stop();available=linux_available()
 minimum=LIMITS['fresh_launch_available_minimum_bytes']if fresh else LIMITS['linux_available_minimum_bytes']
 if available<minimum:raise RuntimeError('RESOURCE_GATE: QC headroom below '+str(minimum))
 if shutil.disk_usage(R).free<LIMITS['disk_reserve_bytes']:raise RuntimeError('Disk reserve below40GiB')
 if 0 not in os.sched_getaffinity(0):raise RuntimeError('CPU0 not eligible')
 os.sched_setaffinity(0,{0});root=own.identity(os.getpid());known={root['pid']:root};own.track_descendants(root,known);rss=0;live=[]
 for identity in known.values():
  current=own.current_matching(identity)
  if current is None:continue
  fields=Path('/proc/'+str(identity['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
  if int(fields[19])!=identity['creation_ticks']:raise RuntimeError('Owned PID changed during RSS sample')
  n=max(0,int(fields[21]))*os.sysconf('SC_PAGE_SIZE');rss+=n;live.append({**current,'rss_bytes':n})
 if rss>LIMITS['linux_total_rss_bytes']:raise RuntimeError('RESOURCE_GATE: complete owned Linux RSS exceeds parallel budget')
 return{'linux_available_bytes':available,'owned_linux_rss_bytes':rss,'owned_identities':live,'cpu_affinity':[0]}

def marker_and_exclusivity_gate():
 import checkm2_owned_cleanup_T1 as own
 expected=PLAN['companion_marker']['linux_owner'];current=own.identity(expected['pid'])
 if not own.same_identity(expected,current)or os.sched_getaffinity(expected['pid'])!={2}:raise RuntimeError('Exact known marker identity/CPU2 no longer matches')
 marker_cmd=Path('/proc/'+str(expected['pid'])+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
 if 'fullpanel_marker_screen_v001.py'not in marker_cmd or str(R)not in marker_cmd:raise RuntimeError('Known marker command differs')
 table={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:table[int(p.name)]=own.identity(int(p.name))
  except(FileNotFoundError,ProcessLookupError):pass
 def descendants(root):
  allowed={root};changed=True
  while changed:
   before=len(allowed);allowed.update(pid for pid,r in table.items()if r['parent_pid']in allowed);changed=len(allowed)!=before
  return allowed
 allowed=descendants(expected['pid'])|descendants(os.getpid());parent=os.getpid()
 while parent in table:allowed.add(parent);parent=table[parent]['parent_pid']
 suspects=[]
 for pid,ident in table.items():
  if pid in allowed:continue
  try:cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode();name=Path('/proc/'+str(pid)+'/comm').read_text().strip()
  except(FileNotFoundError,ProcessLookupError):continue
  if (str(R)in cmd and name.startswith('python'))or name in('diamond','prodigal','hmmsearch','hmmpress','mafft','iqtree','iqtree2','mmseqs','skani'):suspects.append({**ident,'command':cmd,'comm':name})
 if suspects:raise RuntimeError('Unapproved scientific companion(s): '+repr(suspects))
 if not own.same_identity(expected,own.identity(expected['pid'])):raise RuntimeError('Marker identity changed during preflight')
 return{'exact_marker_identity':current,'marker_command':marker_cmd,'marker_cpu':[2],'allowed_marker_descendants':[table[x]for x in descendants(expected['pid'])if x in table],'unapproved_science':suspects}

def native_guard(child=None):
 import ctypes
 from ctypes import wintypes
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=wintypes.HANDLE;k.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t]
 if not k.SetProcessAffinityMask(k.GetCurrentProcess(),1):raise ctypes.WinError(ctypes.get_last_error())
 class MEM(ctypes.Structure):_fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t)for n in('peak','rss','peakPaged','paged','peakNonpaged','nonpaged','pagefile','peakPagefile','private')]
 api=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo;api.argtypes=[wintypes.HANDLE,ctypes.POINTER(MEM),wintypes.DWORD]
 handles=[k.GetCurrentProcess()]+([int(child._handle)]if child is not None and child.poll()is None else[]);rss=0
 for handle in handles:
  m=MEM();m.cb=ctypes.sizeof(m)
  if not api(handle,ctypes.byref(m),m.cb):raise ctypes.WinError(ctypes.get_last_error())
  rss+=m.rss
 if rss>67108864:raise RuntimeError('Native owner plus retained WSL client exceeds64MiB reserve')
 if shutil.disk_usage(R).free<42949672960:raise RuntimeError('Disk reserve below40GiB')
 stop();return rss

def current_failed_run(step,token,input_plan_sha,protocol_sha):
 loc=OUT/'runs_by_token'/(token+'.json')
 if not loc.exists():return None
 item=read(loc)
 if(item['launch_token'],item['input_plan_sha256'],item['protocol_admission_sha256'])!=(token,input_plan_sha,protocol_sha):raise RuntimeError('Required saved-stock locator changed')
 bind(item['binding']);return path(item['run_directory'])


def group_receipts_closed(run):
 run=path(run);index=read(run/'invocations.json');commands={p.parent for p in run.glob('unit_*/command.json')}
 if {path(x)for x in index}!=commands or any(p.name not in('unit_resume','unit_feature_validation')for p in commands):raise RuntimeError('Exact actual-started scoring/feature unit index differs')
 for folder in commands:
  receipt=read(folder/'execution.json')
  if type(receipt.get('exit_code'))is not int or receipt.get('owned_group_empty')is not True or receipt.get('remaining_owned_processes')!=[]:return False
 return True
