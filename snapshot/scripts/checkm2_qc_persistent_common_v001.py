"""One saved-stock companion plan; no annotation/search replay or dispatcher replacement."""
from pathlib import Path
import os,json,math,hashlib,shutil,time
import checkm2_phase_separated_common_P20 as old
R=old.R;path=old.path;read=old.read;save=old.save;row=old.row
manifest=old.manifest;verify_manifest=old.verify_manifest;unit_closed=old.unit_closed;pending_is_current=old.pending_is_current
E=R/'work/checkm2_qc_persistent_native_v001';OUT=R/'analysis/checkm2_qc_persistent_session_v001';SCORE=OUT/'session'
STATE=E/'progress.json';STEP=E/'step.json';LAUNCH=E/'native_owner.json';ADMISSION=E/'Root_runtime_admission.json';STOP=R/'state/STOP_CHECKM2_QC_PERSISTENT_V001';UNRESOLVED_HANDOFF=E/'unresolved_ownership_handoff.json'
ROLE='CONTINUOUS_QC_QUEUE_SESSION_V001';PLAN=None;COLD=172800
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
 global PLAN,COLD
 stop();p=path(plan_path)
 if sha(p)!=expected_sha:raise RuntimeError('Continuous QC plan changed')
 plan=read(p);plan['_sha']=expected_sha;PLAN=plan;COLD=plan['cold_session_seconds']
 if plan.get('schema')!='TREE2_CONTINUOUS_QC_RUNTIME_PLAN_V001'or type(COLD)is not int or not 2400<=COLD<=604800:raise RuntimeError('Finite Root continuous-context plan required')
 for r in read(bind(plan['source_manifest']))['sources']:bind(r)
 for ref in(plan['campaign_data'],plan['saved_feature_repair']):bind(ref)
 if plan.get('conditional_shared_profile_authority'):bind(plan['conditional_shared_profile_authority'])
 if UNRESOLVED_HANDOFF.exists()or list((E/'unresolved_ownership').glob('*.json')):raise RuntimeError('Unresolved continuous owner blocks replay')
 if not closed_finalization and (SCORE/'once_claim.json').exists():raise RuntimeError('Continuous session claim consumed; no implicit replay')
 if not require_admission:return plan,{},None
 admitted=read(ADMISSION)
 if admitted.get('status')!='ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001'or admitted.get('input_plan_sha256')!=expected_sha or admitted.get('source_manifest')!=plan['source_manifest']or admitted.get('cold_session_seconds')!=COLD or admitted.get('campaign_data')!=plan['campaign_data']:raise RuntimeError('Exact Root continuous-session admission required')
 actual=read(bind(admitted['preflight_actual_exit']))
 if type(actual.get('actual_exit_code'))is not int or actual['actual_exit_code']!=0:raise RuntimeError('Fresh observed preflight0 required')
 bind(admitted['preflight_receipt']);return plan,{},admitted

def linux_available():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024

def linux_guard(fresh=False):
 import checkm2_owned_cleanup_T1 as own
 stop();available=linux_available()
 limits=active_resource_limits();minimum=limits['fresh_launch_available_minimum_bytes']if fresh else limits['linux_available_minimum_bytes']
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
 if rss>limits['linux_total_rss_bytes']:raise RuntimeError('RESOURCE_GATE: complete owned Linux RSS exceeds parallel budget')
 return{'linux_available_bytes':available,'owned_linux_rss_bytes':rss,'owned_identities':live,'cpu_affinity':[0]}

def active_resource_limits():
 limits=dict(LIMITS);sidecar=path(PLAN['post_marker_resource_admission_path'])
 if not sidecar.exists():return limits
 proof=read(sidecar)
 if proof.get('status')!='ROOT_ADMITTED_QC_RESOURCE_RESTORE_AFTER_MARKER_ACTUAL_CLOSURE'or proof.get('input_plan_sha256')!=PLAN['_sha']or proof.get('marker_native_identity')!=PLAN['companion_marker']['native_owner']or type(proof.get('actual_native_exit_code'))is not int or proof['actual_native_exit_code']!=0 or type(proof.get('actual_WSL_exit_code'))is not int or proof['actual_WSL_exit_code']!=0 or proof.get('all_marker_groups_contexts_and_leases_closed')is not True:raise RuntimeError('Exact independently observed marker closure/resource admission required')
 for ref in proof['closure_and_fresh_resource_evidence']:bind(ref)
 fresh=read(bind(proof['fresh_preflight_actual_exit']))
 if type(fresh.get('actual_exit_code'))is not int or fresh['actual_exit_code']!=0:raise RuntimeError('Fresh observed resource preflight0 required for restored QC budget')
 new=proof['limits']
 if new.get('native_reserved_bytes')!=67108864 or new.get('cpu')!=0 or new.get('stock_threads')!=1 or not 1543503872<=new.get('linux_total_rss_bytes',0)<=2080374784 or new.get('total_owned_rss_bytes')!=new['linux_total_rss_bytes']+67108864 or new.get('linux_available_minimum_bytes',0)<1073741824 or new.get('disk_reserve_bytes')!=42949672960:raise RuntimeError('Restored resource policy exceeds original bounded QC envelope')
 import checkm2_owned_cleanup_T1 as own
 try:current=own.identity(PLAN['companion_marker']['linux_owner']['pid'])
 except(FileNotFoundError,ProcessLookupError):current=None
 if own.same_identity(PLAN['companion_marker']['linux_owner'],current):raise RuntimeError('Marker is still live; no resource restoration allowed')
 return {**limits,**new,'resource_restore_receipt':row(sidecar)}

def marker_and_exclusivity_gate():
 import checkm2_owned_cleanup_T1 as own
 expected=PLAN['companion_marker']['linux_owner']
 try:current=own.identity(expected['pid'])
 except(FileNotFoundError,ProcessLookupError):current=None
 live=own.same_identity(expected,current)
 if live:
  if os.sched_getaffinity(expected['pid'])!={2}:raise RuntimeError('Known live marker CPU2 changed')
  marker_cmd=Path('/proc/'+str(expected['pid'])+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
  if 'fullpanel_marker_screen_v001.py'not in marker_cmd or str(R)not in marker_cmd:raise RuntimeError('Known live marker command changed')
 else:
  policy=active_resource_limits()
  if 'resource_restore_receipt'not in policy:
   proof=read(bind(PLAN['marker_closed_authority']))
   if proof.get('status')!='CLOSED_VALIDATED_PROVISIONAL_FULL919_CANDIDATE_COVERAGE_COPY_AMBIGUITY'or proof.get('actual_native_exit_code')!=0 or proof.get('actual_wsl_exit_code')!=0 or proof.get('native_owner')!=PLAN['companion_marker']['native_owner']:raise RuntimeError('Exact actual marker closure authority required')
   for key in('actual_native_exit','actual_wsl_exit','Linux_owner_group_and_OS_flock_closure'):bind(proof[key])
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
 allowed=descendants(os.getpid())|(descendants(expected['pid'])if live else set());parent=os.getpid()
 while parent in table:allowed.add(parent);parent=table[parent]['parent_pid']
 suspects=[]
 for pid,ident in table.items():
  if pid in allowed:continue
  try:cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode();name=Path('/proc/'+str(pid)+'/comm').read_text().strip()
  except(FileNotFoundError,ProcessLookupError):continue
  if (str(R)in cmd and name.startswith('python'))or name in('diamond','prodigal','hmmsearch','hmmpress','mafft','iqtree','iqtree2','mmseqs','skani'):suspects.append({**ident,'command':cmd})
 if suspects:raise RuntimeError('Unapproved additional scientific owner: '+repr(suspects))
 return{'known_marker_live':live,'marker_identity':current,'no_other_scientific_owner':True,'active_resource_limits':active_resource_limits()}

def resource_policy(request):
 global PLAN
 parent=read(bind(request['parent_plan']));parent['_sha']=request['parent_plan']['sha256'];PLAN=parent
 authority=read(bind(request['protocol_admission']))
 if authority.get('status')!='ROOT_ADMITTED_ONE_CONTINUOUS_QC_QUEUE_CONTEXT_V001'or authority.get('input_plan_sha256')!=parent['_sha']or authority.get('source_manifest')!=request['source_manifest']:raise RuntimeError('Exact persistent Root resource authority/source changed')
 policy=active_resource_limits();return{**policy,'restore_ref':policy.get('resource_restore_receipt')}

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
 run=path(run);index=read(run/'invocations.json');commands={p.parent for p in run.rglob('command.json')}
 if {path(x)for x in index}!=commands:raise RuntimeError('Actual persistent invocation index differs')
 for folder in commands:
  u=read(folder/'execution.json')
  if type(u.get('exit_code'))is not int or u.get('owned_group_empty')is not True or u.get('remaining_owned_processes')!=[]:return False
 return True
