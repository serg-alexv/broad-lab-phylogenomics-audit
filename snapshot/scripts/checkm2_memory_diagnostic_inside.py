"""One primary and one comparison engineering arm; summed RSS remains the gate."""
from pathlib import Path
import datetime,fcntl,hashlib,json,os,shutil,signal,subprocess,time
import checkm2_runtime_image as image
import checkm2_ipc_alias as ipc
R=image.R;E=R/'evidence/checkm2_memory_diagnostic/v001'
RSS_LIMIT=2*1024**3;HEADROOM=1024**3;ARM_SECONDS=600
OBSERVER_PGID=None

def available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
def stop():return (R/'state/STOP').exists() or (R/'state/STOP_CHECKM2_MEMORY_DIAGNOSTIC').exists()
def step(detail,arm=None,**extra):ipc.save(R/'state/checkm2_memory_step.json',{'updated_utc':ipc.utc(),'detail':detail,'arm':arm,'biological_prediction':'NOT_RUN',**extra})
def process_rows(pgid):
 rows=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   fields=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(fields[2])!=pgid:continue
   row={'pid':int(path.name),'parent_pid':int(fields[1]),'process_group':int(fields[2]),'creation_ticks':int(fields[19]),'state':fields[0],'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
   again=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(again[19])!=row['creation_ticks']:continue
   rows.append(row)
  except (FileNotFoundError,ProcessLookupError):continue
 return sorted(rows,key=lambda x:x['pid'])
def sample(pgid,arm,started):
 start=time.monotonic();rows=process_rows(pgid)
 if OBSERVER_PGID:
  for value in process_rows(OBSERVER_PGID):value['role']='bounded_optional_metrics_observer';rows.append(value)
 resident=sum(x['rss_bytes'] for x in rows)
 return {'at_utc':ipc.utc(),'elapsed_seconds':time.monotonic()-started,'collection_seconds':time.monotonic()-start,'arm':arm,'processes':rows,'process_count':len(rows),'sum_rss_bytes':resident,'linux_available_bytes':available(),'gate_metric':'SUM_PROC_STAT_RSS_PAGES_BYTES','bounded_metrics_observer_included_in_rss':True,'pss_used_for_gate':False}
def command(folder,sequence,value):ipc.save(folder/'command.json',{'sequence':sequence,'command':value,'at_utc':ipc.utc()})
def gate(row):
 if row['sum_rss_bytes']>RSS_LIMIT:return 'STOPPED_AT_DECLARED_SUMMED_RSS_GATE'
 if row['linux_available_bytes']<HEADROOM:return 'STOPPED_AT_DECLARED_HEADROOM_GATE'
 if row['elapsed_seconds']>ARM_SECONDS:return 'STOPPED_AT_DECLARED_600_SECOND_GATE'
 if stop():return 'STOPPED_BY_PROJECT_STOP'
 return None
def describe_held(folder,sequence,row,pgid,arm,started,telemetry):
 global OBSERVER_PGID
 snapshot=folder/f'held_{sequence}_fast.json';ipc.save(snapshot,row);output=folder/f'held_{sequence}_descriptive.json';error=folder/f'held_{sequence}_metrics.stderr.txt'
 with output.open('w') as out,error.open('w') as err:
  observer=subprocess.Popen(['/usr/bin/python3','-B',str(R/'scripts/checkm2_memory_diagnostic_metrics.py'),'--snapshot',str(snapshot)],stdout=out,stderr=err,start_new_session=True);OBSERVER_PGID=observer.pid;deadline=time.monotonic()+3;stop_reason=None;observed_peak=0;observed_minimum=2**63;samples=0
  try:
   while observer.poll() is None:
    current=sample(pgid,arm,started);telemetry.write(json.dumps(current)+'\n');telemetry.flush();stop_reason=gate(current);observed_peak=max(observed_peak,current['sum_rss_bytes']);observed_minimum=min(observed_minimum,current['linux_available_bytes']);samples+=1
    if stop_reason or time.monotonic()>deadline:break
    time.sleep(.1)
  finally:
   if observer.poll() is None:observer.kill()
   observer.wait(timeout=2)
   if process_rows(observer.pid):raise RuntimeError('Optional metrics observer group failed closure')
   OBSERVER_PGID=None
 descriptive=None
 if observer.returncode==0:
  try:descriptive=ipc.read(output)
  except ValueError:pass
 if descriptive is None:descriptive={'status':'UNKNOWN_OPTIONAL_METRICS_TIMEOUT_OR_ERROR','sum_pss_bytes':None,'sum_private_resident_bytes':None,'used_for_resource_gate':False}
 ipc.save(folder/f'held_{sequence}_metrics_receipt.json',{'at_utc':ipc.utc(),'observer_pid':observer.pid,'observer_exit_code':observer.returncode,'observer_group_closed':True,'deadline_seconds':3,'descriptive':descriptive,'safety_stop':stop_reason})
 return stop_reason,descriptive,{'peak_rss_bytes':observed_peak,'minimum_available_bytes':observed_minimum,'samples':samples}

def run_arm(arm,env):
 if stop() or available()<HEADROOM or shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Pre-arm STOP/headroom/disk admission gate')
 folder=E/arm;folder.mkdir(exist_ok=False);args=[str(image.PREFIX/'bin/python'),'-B',str(R/'scripts/checkm2_memory_diagnostic_target.py'),'--arm',arm,'--directory',str(folder)]
 with (folder/'stdout.txt').open('w') as out,(folder/'stderr.txt').open('w') as err,(folder/'telemetry.jsonl').open('w') as telemetry:
  child=subprocess.Popen(args,env=env,start_new_session=True,stdout=out,stderr=err);started=time.monotonic();reason=None;last_sequence=-1;pending=None;stable=0;peak=0;minimum=2**63;observations=0;terminal=False
  step('Loading exact original models; collecting per-process RSS/PSS without genome input',arm,pid=child.pid)
  try:
   while child.poll() is None:
    row=sample(child.pid,arm,started);peak=max(peak,row['sum_rss_bytes']);minimum=min(minimum,row['linux_available_bytes']);observations+=1
    telemetry.write(json.dumps(row)+'\n');telemetry.flush()
    reason=gate(row)
    if reason:break
    events=folder/'events.jsonl'
    if events.exists():
     complete=events.read_text().splitlines();last=None
     if complete:
      try:last=json.loads(complete[-1])
      except ValueError:pass
     if last and last['sequence']>=0 and last['sequence']>last_sequence:
      if pending!=last['sequence']:pending=last['sequence'];stable=0
      stable+=1
      if stable>=2:
       reason,descriptive,observed=describe_held(folder,last['sequence'],row,child.pid,arm,started,telemetry)
       peak=max(peak,observed['peak_rss_bytes']);minimum=min(minimum,observed['minimum_available_bytes']);observations+=observed['samples']
       if reason:break
       current=sample(child.pid,arm,started);telemetry.write(json.dumps(current)+'\n');telemetry.flush();reason=gate(current);peak=max(peak,current['sum_rss_bytes']);minimum=min(minimum,current['linux_available_bytes']);observations+=1
       if reason:break
       step('Holding '+last['event']+'; fast RSS gate and bounded descriptive metrics recorded',arm,event=last,group_rss_bytes=current['sum_rss_bytes'],group_pss_bytes=descriptive['sum_pss_bytes'],managers=last.get('count'),observations=observations)
       command(folder,last['sequence'],'NEXT');last_sequence=last['sequence'];pending=None
       if last['event']=='ALL_DECLARED_TOPOLOGY_HELD':terminal=True
    time.sleep(.2)
  except BaseException as ex:reason='OBSERVER_ERROR:'+repr(ex)
  measurement_seconds=time.monotonic()-started
  if reason:
   command(folder,last_sequence+1,'STOP')
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:child.wait(timeout=25)
   except subprocess.TimeoutExpired:
    os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
  else:child.wait(timeout=5)
  remaining=process_rows(child.pid)
  if remaining:
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   deadline=time.monotonic()+5
   while remaining and time.monotonic()<deadline:time.sleep(.1);remaining=process_rows(child.pid)
   if remaining:
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    deadline=time.monotonic()+5
    while remaining and time.monotonic()<deadline:time.sleep(.1);remaining=process_rows(child.pid)
  event_rows=[]
  if (folder/'events.jsonl').exists():
   for line in (folder/'events.jsonl').read_text().splitlines():
    try:event_rows.append(json.loads(line))
    except ValueError:pass
  result={'status':reason or ('ALL_DECLARED_ENGINEERING_STEPS_RECORDED' if child.returncode==0 and terminal else 'TARGET_ERROR'),'arm':arm,'started_pid':child.pid,'target_exit_code':child.returncode,'owned_group_empty':not remaining and OBSERVER_PGID is None,'remaining_owned_processes':remaining,'models_loaded_hold_observed':any(x['event']=='MODELS_LOADED_HELD' for x in event_rows),'peak_summed_rss_bytes':peak,'minimum_linux_available_bytes':minimum,'observations':observations,'measurement_seconds':measurement_seconds,'closure_seconds':time.monotonic()-started-measurement_seconds,'elapsed_seconds':time.monotonic()-started,'limits':{'cpu_affinity_count':2,'summed_rss_bytes':RSS_LIMIT,'headroom_bytes':HEADROOM,'arm_seconds':ARM_SECONDS},'pss_or_private_used_for_gate':False,'target_exit_receipt':ipc.read(folder/'target_exit.json') if (folder/'target_exit.json').exists() else None,'science_or_genome_prediction':False,'qc_acceptance':False,'biological_route_viability_tested':False}
  ipc.save(folder/'execution.json',result)
  if not result['owned_group_empty']:raise RuntimeError('Owned engineering or metrics group not closed; comparison forbidden')
  return result

def main():
 image.private();E.mkdir(parents=True,exist_ok=False);(R/'work/checkm2_memory_diagnostic').mkdir(exist_ok=False)
 with (E/'once_claim.json').open('x') as f:json.dump({'at_utc':ipc.utc(),'scope':'ONE_DEFAULT_FORK_PRIMARY_AND_ONE_DEFAULT_FORK_PROTEIN_TOPOLOGY_COMPARISON_NO_BIOLOGY'},f);f.flush();os.fsync(f.fileno())
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 own=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
 ipc.save(R/'state/checkm2_memory_linux_owner.json',{'pid':os.getpid(),'parent_pid':int(own[1]),'process_group':int(own[2]),'creation_ticks':int(own[19]),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'inside_source_sha256':ipc.sha(__file__),'biological_workflow':False})
 os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));effective_path=R/'evidence/checkm2_runtime/sklearn161_effective_runtime_validated.json';effective=ipc.read(effective_path);proof_path=R/'evidence/checkm2_runtime/ipc_capability_proof.json';proof=ipc.read(proof_path);results=[];error=None
 try:
  step('Verifying unchanged read-only runtime before engineering memory measurement')
  with image.RuntimeImage(True,True,E/'runtime_mount.json') as mounted:
   import checkm2_effective_bootstrap as bootstrap
   bootstrap.bind_overlay(mounted)
   if mounted.result['image_sha256']!=proof['image_sha256'] or ipc.sha(effective_path)!=proof['effective_runtime_manifest_sha256']:raise RuntimeError('Engineering runtime/IPC proof bindings differ')
   with ipc.IpcAlias(R/'work/checkm2_ipc/memory_diagnostic_v001',proof['selected_mode'],E/'ipc_mount.json') as alias:
    alias.result.update(proof_path=str(proof_path),proof_sha256=ipc.sha(proof_path),target_bootstrap_sha256=proof['target_bootstrap_sha256'],effective_runtime_manifest_sha256=ipc.sha(effective_path),image_sha256=mounted.result['image_sha256']);ipc.save(alias.receipt,alias.result)
    env={**os.environ,**effective['required_runtime_environment'],'TMPDIR':'/tmp','TMP':'/tmp','TEMP':'/tmp','TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED':'1','TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT':str(mounted.receipt),'TREE2_EFFECTIVE_RUNTIME_MANIFEST':str(effective_path),'TREE2_EFFECTIVE_RUNTIME_MANIFEST_SHA256':ipc.sha(effective_path),'TREE2_CHECKM2_PRIVATE_IPC_VERIFIED':'1','TREE2_CHECKM2_PRIVATE_IPC_RECEIPT':str(alias.receipt),'TREE2_CHECKM2_PRIVATE_IPC_PROOF_SHA256':ipc.sha(proof_path)}
    results.append(run_arm('nine_managers',env))
    step('Primary engineering arm closed; evaluating predeclared comparison admission',completed_arm_count=1)
    admitted={'ALL_DECLARED_ENGINEERING_STEPS_RECORDED','STOPPED_AT_DECLARED_SUMMED_RSS_GATE','STOPPED_AT_DECLARED_HEADROOM_GATE','STOPPED_AT_DECLARED_600_SECOND_GATE'}
    if results[0]['status'] not in admitted:raise RuntimeError('Primary target/model/observer error; comparison not admitted')
    if results[0]['models_loaded_hold_observed'] and not stop() and available()>=HEADROOM:
     results.append(run_arm('protein_topology',env));step('Both declared engineering arms closed; unmounting private runtime',completed_arm_count=2)
    else:step('Comparison not started: exact model hold, STOP or headroom prerequisite unmet',comparison_disposition='NOT_RUN_MODEL_HOLD_STOP_OR_HEADROOM',completed_arm_count=1)
    if any(x['status'] not in admitted for x in results):raise RuntimeError('Comparison target/model/observer error; engineering observations remain partial')
 except BaseException as ex:error=repr(ex)
 finally:
  ipc.save(E/'inside_execution.json',{'status':'ENGINEERING_OBSERVATIONS_RECORDED_NOT_QC' if not error else 'ENGINEERING_DIAGNOSTIC_ERROR','ended_utc':ipc.utc(),'error':error,'arms':results,'comparison_disposition':'RECORDED' if len(results)==2 else 'NOT_RUN_PREREQUISITE_OR_PROTOCOL_ERROR','all_started_arm_groups_closed':bool(results) and all(x['owned_group_empty'] for x in results),'base_image_sha256':effective['base_image']['sha256'],'effective_runtime_manifest_sha256':ipc.sha(effective_path),'source_hashes':{name:ipc.sha(R/'scripts'/name) for name in ('checkm2_memory_diagnostic_inside.py','checkm2_memory_diagnostic_target.py','checkm2_memory_diagnostic_metrics.py')},'genome_inputs_used':0,'production_acceptance':False,'supported_protein_route_validated':False,'actual_private_bound_method_pickling_tested':False,'forkserver_not_executed':True})
  lock.close()
 return 0 if not error else 2
if __name__=='__main__':raise SystemExit(main())
