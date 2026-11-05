"""S1R2 strict unit observer; only display I/O is optional. No scientific imports."""
from pathlib import Path
import datetime,os,signal,subprocess,time
import checkm2_owned_cleanup_T1 as guard
from checkm2_optional_telemetry_v001 import structured_exception
from checkm2_optional_progress_S1R2 import safe_call
LIMIT=2147483648;HEADROOM=1073741824
class UnitFailure(RuntimeError):
 def __init__(self,receipt):self.receipt=receipt;super().__init__(repr(receipt))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def strict_group(pgid,stat):
 rows=[]
 for entry in Path('/proc').iterdir():
  if entry.name.isdigit():
   try:row=stat(int(entry.name))
   except (FileNotFoundError,ProcessLookupError):continue
   if row['process_group']==pgid:rows.append(row)
 return rows

def owned_census(root,known,hooks,pgid):
 guard.track_descendants(root,known)
 group=hooks['group'](pgid);current_root=guard.current_matching(root) if root is not None else None
 if current_root is not None:
  for row in group:
   if row.get('boot_id')!=root['boot_id'] or row.get('creation_ticks',-1)<root['creation_ticks'] or row.get('process_group')!=pgid:raise RuntimeError('Numeric group membership has no owned creation evidence')
   prior=known.get(row['pid'])
   if prior is not None and not guard.same_identity(prior,row):raise RuntimeError('Captured unit PID was reused')
   known[row['pid']]={**row,'depth':(prior or {}).get('depth',1 if row['pid']!=pgid else 0)}
 unknown=[row for row in group if not guard.same_identity(known.get(row['pid']),row)]
 live=[]
 for row in list(known.values()):
  try:observed=hooks['stat'](row['pid'])
  except (FileNotFoundError,ProcessLookupError):continue
  if guard.same_identity(row,observed):live.append(observed)
 return live,unknown

def run_unit(name,cmd,env,run,timeout,*,hooks):
 if not 0<timeout<=10800:raise ValueError('Finite remaining unit time within10800s required')
 folder=Path(run)/name;started_utc=utc();started=time.monotonic();child=None;identity=None;cleanup_root=None;known={}
 error=None;details=None;kind=None;peak_total=0;peak=0;minimum=None;peak_rows=[];remaining=None;unknown=None;samples=0;signals=[]
 last_operation='prepare_unit_directory';operation_path=str(folder);optional_errors=[];optional_total=0;cleanup_errors=[];created=False
 def note_optional(value):
  nonlocal optional_total
  optional_total+=1
  if len(optional_errors)<16:optional_errors.append(value)
  sink=hooks.get('optional_error_sink')
  if sink is not None:
   try:sink(value)
   except OSError:pass
 def record_cleanup(exception,operation):
  nonlocal error,details,kind
  value=structured_exception(exception,operation);value['last_operation']=operation;cleanup_errors.append(value)
  if error is None:error=repr(exception);details=value;kind='CLOSURE'
 def refresh():return owned_census(cleanup_root,known,hooks,child.pid)
 def signal_matching(number):
  # Same unchanged874 creation/pidfd primitives; immediate TERM5/KILL5, no bare PID/PGID.
  for row in sorted(known.values(),key=lambda x:(x.get('depth',0),x['pid']),reverse=True):
   descriptor=None
   try:
    current=guard.current_matching(row)
    if current is None:continue
    if row['pid']<=1 or row['pid']==os.getpid():raise RuntimeError('Refused unsafe captured unit identity')
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):raise RuntimeError('No exact-task pidfd signaling; no numeric fallback')
    descriptor=os.pidfd_open(row['pid'],0)
    if not guard.same_identity(row,guard.identity(row['pid'])):continue
    signal.pidfd_send_signal(descriptor,number,None,0);signals.append({'signal':int(number),'captured_identity':row,'observed_identity':current,'method':'pidfd_send_signal'})
   except (FileNotFoundError,ProcessLookupError):pass
   except BaseException as exception:record_cleanup(exception,'required owned identity/pidfd signal')
   finally:
    if descriptor is not None:os.close(descriptor)
 try:
  folder.mkdir(exist_ok=False);created=True
  last_operation='write_required_command';operation_path=str(folder/'command.json')
  hooks['save'](folder/'command.json',{'command':cmd,'environment':{k:env.get(k) for k in ('TMPDIR','TMP','TEMP','KERAS_HOME','XDG_CACHE_HOME','XDG_CONFIG_HOME','MPLCONFIGDIR','NUMBA_CACHE_DIR','GLIBC_TUNABLES','PYTHONPATH','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},'HOME_unchanged':env.get('HOME')==os.environ.get('HOME'),'declared_unit':name,'timeout_seconds':timeout})
  last_operation='required_stop_admission_disk_gate';operation_path='STOP/admission/WD/MemAvailable/backing_volume';hooks['stop_gate']()
  last_operation='open_required_child_logs';operation_path=str(folder)
  with (folder/'stdout.txt').open('w') as out,(folder/'stderr.txt').open('w') as err:
   last_operation='start_owned_child';operation_path=str(cmd[0]);child=subprocess.Popen(cmd,env=env,stdout=out,stderr=err,start_new_session=True)
   last_operation='required_child_identity';operation_path='/proc/'+str(child.pid)+'/stat';identity=hooks['stat'](child.pid)
   if not guard.same_identity(identity,identity) or identity.get('pid')!=child.pid or identity.get('process_group')!=child.pid:raise RuntimeError('Owned child creation identity unproved')
   cleanup_root=identity;known[identity['pid']]={**identity,'depth':0}
   while child.poll() is None:
    last_operation='required_owned_group_RSS';operation_path='/proc owned creation/descendant/group census';rows,unowned=refresh()
    if unowned:raise RuntimeError('Unproved numeric group members; no ownership substitution')
    rss=sum(x['rss_bytes'] for x in rows)
    last_operation='required_linux_headroom';operation_path='/proc/meminfo';available=hooks['mem_available']();samples+=int(bool(rows));minimum=available if minimum is None else min(minimum,available)
    if rss>peak:peak=rss;peak_rows=rows
    policy=hooks['resource_policy']();total_rows={x['pid']:x for x in [*rows,*hooks['controller_rows']()]}
    total=sum(x['rss_bytes']for x in total_rows.values());peak_total=max(peak_total,total)
    if total>policy['linux_total_rss_bytes']:raise RuntimeError('RESOURCE_GATE complete owned Linux RSS exceeds actual Root resource policy')
    if available<policy['linux_available_minimum_bytes']:raise RuntimeError('RESOURCE_GATE protective Linux headroom')
    last_operation='required_unit_deadline';operation_path='monotonic unit clock'
    if time.monotonic()-started>timeout:raise TimeoutError('Declared scientific unit deadline')
    last_operation='required_stop_admission_disk_gate';operation_path='STOP/admission/WD/MemAvailable/backing_volume';hooks['stop_gate']()
    last_operation='optional_progress_callback';operation_path='callback-owned STEP only'
    safe_call(hooks['progress'],'RUNNING',name,error_sink=note_optional,declared_unit=name,declared_unit_limit_seconds=timeout,worker_pid=child.pid,worker_creation_identity=identity,group_rss_bytes=rss,linux_available_bytes=available,elapsed_seconds=time.monotonic()-started,log_path=str(folder/'stderr.txt'),run_directory=str(run));time.sleep(.25)
   last_operation='required_direct_child_exit';operation_path='owned subprocess wait status'
   if child.returncode!=0:raise RuntimeError('Scientific unit exit '+str(child.returncode))
   if samples==0:raise RuntimeError('No owned creation/resource sample before child exit')
 except BaseException as exception:
  error=repr(exception);details=structured_exception(exception,operation_path);details['last_operation']=last_operation
  kind='RESOURCE' if 'RESOURCE_GATE' in str(exception) else 'STOP' if isinstance(exception,InterruptedError) else 'TIMEOUT' if isinstance(exception,TimeoutError) else 'RUNTIME_OR_OBSERVER'
 finally:
  if child is not None:
   # If the initial read failed, a still-owned direct child may be captured only for cleanup.
   if cleanup_root is None:
    try:
     candidate=guard.identity(child.pid)
     if candidate['parent_pid']!=os.getpid() or candidate['process_group']!=child.pid:raise RuntimeError('No actual direct-child ownership for cleanup')
     cleanup_root=candidate;known[candidate['pid']]={**candidate,'depth':0}
    except (FileNotFoundError,ProcessLookupError):pass
    except BaseException as exception:record_cleanup(exception,'required cleanup-only direct-child creation observation')
   try:remaining,unknown=refresh()
   except BaseException as exception:remaining=None;unknown=None;record_cleanup(exception,'required owned cleanup census')
   try:
    if child.poll() is None or remaining or unknown or remaining is None:
     if error is None:error='Direct child/group needed forced cleanup; scientific success forbidden';kind='CLOSURE'
     for number in (signal.SIGTERM,signal.SIGKILL):
      signal_matching(number);deadline=time.monotonic()+5
      while time.monotonic()<deadline:
       code=child.poll()
       try:remaining,unknown=refresh()
       except BaseException as exception:remaining=None;unknown=None;record_cleanup(exception,'required owned cleanup census');break
       if code is not None and remaining==[] and unknown==[]:break
       time.sleep(.1)
      if child.poll() is not None and remaining==[] and unknown==[]:break
    if child.poll() is not None:child.wait(timeout=0)
    remaining,unknown=refresh()
   except BaseException as exception:remaining=None;unknown=None;record_cleanup(exception,'required owned cleanup completion')
  closed=child is not None and cleanup_root is not None and child.returncode is not None and remaining==[] and unknown==[] and not cleanup_errors
  receipt={'status':'UNIT_EXIT0_GROUP_CLOSED' if error is None and identity is not None and samples>0 and child is not None and child.returncode==0 and closed else 'UNIT_FAILED_OR_CLOSURE_UNPROVEN','declared_unit':name,'started_utc':started_utc,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-started,'error':error,'error_details':details,'failure_kind':kind,'last_operation':last_operation,'operation_path':operation_path,'child_identity':identity,'cleanup_only_root_identity':cleanup_root if identity is None else None,'exit_code':child.returncode if child is not None else None,'owned_group_empty':closed,'remaining_owned_processes':remaining,'unproven_numeric_group_members':unknown,'sampled_peak_summed_rss_bytes':peak,'peak_per_pid_RSS_rows':peak_rows,'sampled_min_linux_available_bytes':minimum,'resource_sample_count':samples,'timeout_seconds':timeout,'sampled_peak_complete_linux_rss_bytes':peak_total,'budget_metric':'SUM_PROCESS_RSS','pss_substitution':False,'optional_progress_error_count':optional_total,'optional_progress_errors_first16':optional_errors,'cleanup_errors':cleanup_errors,'captured_owned_creation_identities':list(known.values()),'identity_pinned_signals':signals,'cleanup_policy_seconds':{'immediate_TERM':5,'then_KILL':5},'durable_terminal_receipt':False}
  try:
   if not created:raise RuntimeError('Existing unit directory preserved; no terminal overwrite')
   hooks['save'](folder/'execution.json',{**receipt,'durable_terminal_receipt':True});receipt['durable_terminal_receipt']=True
  except BaseException as exception:receipt.update(status='UNIT_FAILED_OR_CLOSURE_UNPROVEN',terminal_write_error=structured_exception(exception,folder/'execution.json'),durable_terminal_receipt=False)
 if receipt['status']!='UNIT_EXIT0_GROUP_CLOSED' or not receipt['durable_terminal_receipt']:raise UnitFailure(receipt)
 return receipt
