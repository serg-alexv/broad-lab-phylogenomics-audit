"""Foreground file/OS/transport admission checks for one changed resource repair; no science."""
from pathlib import Path
import ctypes,json,msvcrt,os,shutil,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_P20_resource_repair_common_v001 as c
import checkm2_saved_P20_common_v001 as saved
import checkm2_production_preparation_P1 as p
R=c.R;E=c.E/'preflight_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
EVENT_SHA='3bda959e9814838d6e774779253d064dbb56dc7facbb37305017122f3e6e34b6'
EVENT=R/'state/local_continuation_queue_v1/events/10bc5144e2aebe0936dad8bd01e160f7c8850956c18f3262737f9beaadb8c59c/event.json'
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);mask=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':mask,'no_science':True})
 assert b.digest(EVENT)==EVENT_SHA;event=b.read(EVENT);assert event['actual_exit_code']==0 and event['retained_handle_identity_verified']is True
 actual=b.read(b.bind(R,event['actual_exit_receipt']));launched=b.read(b.bind(R,event['launch_receipt']))
 assert actual['actual_exit_code']==0 and actual['exact_birth_handle_retained']is True and launched['native_owner']==event['worker_identity']
 result=b.read(c.bind(c.read(c.E/'runtime_plan.json')['source_preparation_result']))
 assert result['source_preparation_owner']==event['worker_identity'] and result['exact_full_author_argv_fixture_equal']is True and result['exact_author_query_dictionary_and_writer_bytes_equal']is True
 for ref in result['new_sources']+result['author_sources']:b.bind(R,ref)
 closed=c.read(c.prior.E/'failure_closure_v001/receipt.json');closed_actual=c.read(c.prior.E/'failure_closure_v001/Root_actual_audit_exit.json');assert closed_actual['actual_exit_code']==0
 pointer=b.read(R/'state/local_continuation_current_runtime.json');roles=b.read(b.bind(R,pointer['actual_runtime_roles']))
 assert pointer['state_directory']=='state/local_continuation_queue_v1'
 dispatcher=b.read(b.bind(R,pointer['dispatcher_launch']));supervisor=b.read(b.bind(R,pointer['detached_supervisor_launch']))
 b.bind(R,pointer['dispatcher_source']);b.bind(R,pointer['supervisor_source']);b.bind(R,pointer['config']);b.bind(R,pointer['Root_operational_admission'])
 identities={x['role']:x['identity']for x in roles['roles']}
 assert dispatcher['dispatcher_owner']==identities['ROOT_LOCAL_RUNTIME_CONTROLLER'] and dispatcher['supervisor_owner']==identities['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']==supervisor['native_owner']
 assert dispatcher['core_source']==pointer['dispatcher_source'] and supervisor['entry_source']==pointer['supervisor_source'] and dispatcher['config']==pointer['config']
 monitor=b.read(R/'state/monitor_current_roles.json');live=[{**monitor[k],'role':k}for k in('gui','collector','publisher')]
 for k in('gui','collector','publisher'):
  receipt=b.read(R/monitor[k+'_launch']);assert receipt['pid']==monitor[k]['pid'] and receipt['creation_time_utc']==monitor[k]['creation_time_utc']
 for role in roles['roles']:
  b.bind(R,role['source']);live.append({**role['identity'],'role':role['role'],'script':role['source']['path'],'script_sha256':role['source']['sha256']})
 cli_path=EVENT.parent/'cli_started.json';cli=b.read(cli_path);assert cli['event_sha256']==EVENT_SHA
 live.append({**cli['identity'],'role':'CURRENT_EVENT_CLI','script':'codex.exe'})
 command="$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @("+','.join(str(x['pid'])for x in live)+") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe','codex.exe'))} | Select-Object @{N='pid';E={$_.ProcessId}},@{N='parent_pid';E={$_.ParentProcessId}},@{N='name';E={$_.Name}},@{N='command';E={$_.CommandLine}})|ConvertTo-Json -Compress"
 census=run(['pwsh','-NoProfile','-Command',command],'Windows_census');census=census if isinstance(census,list)else[census];verified=[]
 for expected in live:
  handle=K.open_worker(expected)
  try:assert not K.wait(handle,0);current=K.identity(handle,expected['pid'])
  finally:K.close(handle)
  rec=next(x for x in census if x['pid']==expected['pid']);assert Path(expected['script']).name in rec['command'] and str(R)in rec['command']
  if 'script_sha256'in expected:assert b.digest(R/expected['script'])==expected['script_sha256']
  if expected['role']=='CURRENT_EVENT_CLI':assert rec['parent_pid']==identities['ROOT_LOCAL_RUNTIME_CONTROLLER']['pid'] and str(EVENT.parent)in rec['command'] and '--disable plugins'in rec['command']
  if expected['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':assert rec['parent_pid']==identities['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']['pid']
  verified.append({'role':expected['role'],'identity':current,'source_and_launch_verified':True})
 allowed={x['pid']for x in live}|{OWNER['pid']}|{x['identity']['pid']for x in CHILDREN};suspects=[x for x in census if x['pid']not in allowed];assert not suspects,('Unknown project Python/WSL/Codex',suspects)
 # No PID disappearance becomes an exit; the event already carries actual0.
 for identity in (event['worker_identity'],c.read(c.prior.LAUNCH)['native_owner'],c.read(c.prior.LAUNCH)['wsl_child']):
  try:handle=K.open_worker(identity)
  except OSError as error:
   if getattr(error,'winerror',None)!=87:raise
  else:
   try:assert K.wait(handle,0)
   finally:K.close(handle)
 plan_path=c.E/'runtime_plan.json';plan,recipe,_=c.plan_gate(plan_path,c.sha(plan_path),require_admission=False,closed_finalization=True)
 assert not c.ADMISSION.exists() and not c.LAUNCH.exists() and not list((c.E/'native_phase_claims').glob('*.json')) and not list(c.OUT.glob('sessions/*/once_claim.json'))
 assert c.read(R/'state/checkm2_accepted_method_registry_current.json')['registry']==plan['accepted_registry']
 context=c.read(c.bind(plan['queue_launch_context']));reservation=c.read(c.bind(context['queue_reservation']));proposal=c.read(c.bind(plan['repair_proposal']))
 assert reservation['kind']=='RESERVED' and reservation['queue_ids']==proposal['queue_ids'] and context['queue_ids']==proposal['queue_ids']
 # The FAILED_CLOSED proposal is not reservable again; retain original single reservation.
 assert proposal['status']=='REPAIR_PENDING' and proposal['explicit_Root_repair_admission_required']is True
 handles=[];leases=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,x)for x in leases]
 try:
  for name in leases:
   f=name.open('r+b');f.seek(0)
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except BaseException:f.close();raise
   handles.append(f)
  root='/mnt/c/'+str(R)[3:].replace('\\','/');targets=root+'/'+(c.prior.E/'failure_closure_v001/historical_targets.json').relative_to(R).as_posix();source=R/'work/checkm2_N5_actual_prelaunch_linux.py'
  bound=c.read(saved.E/'preflight_v001/Root_preflight_admission.json')['linux_observer_source'];c.bind(bound)
  code=source.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targets)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targets)+").read_text())['namespace_targets']");compile(code,'<current-event-OS-observer>','exec')
  linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_closure_resources')
  assert not any(linux[x]for x in('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==closed['Linux']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 token='728650c9fa5448328bd4678e35d78207'
 code=("from pathlib import Path\nimport os,json,subprocess,hashlib\nroot=Path("+repr(root)+");token="+repr(token)+"\nassert os.environ.get('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN')==token\nos.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]))\nrows=[]\n"+
  "for name in ['checkm2_P20_resource_repair_v001.sh','checkm2_P20_diamond_exec_phase_v001.sh']:\n shell=root/'scripts'/name;raw=shell.read_bytes();assert bytes([13])not in raw\n result=subprocess.run(['/bin/bash','-n',str(shell)],capture_output=True,text=True,timeout=10);assert result.returncode==0\n rows.append({'name':name,'bash_n_actual_exit_code':result.returncode,'CR_bytes':raw.count(bytes([13])),'sha256':hashlib.sha256(raw).hexdigest()})\nprint(json.dumps({'explicit_env_token_matches':True,'shells':rows,'scripts_executed':False,'runtime_image_opened':False,'affinity_CPUs':len(os.sched_getaffinity(0))}))\n")
 transport=run(['wsl','-d','Ubuntu','--','/usr/bin/env','TREE2_CHECKM2_PILOT_LAUNCH_TOKEN='+token,'PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'actual_direct_env_and_bash_n')
 assert transport['explicit_env_token_matches']is True and transport['affinity_CPUs']<=2 and all(x['bash_n_actual_exit_code']==0 and x['CR_bytes']==0 and x['sha256']==c.sha(R/'scripts'/x['name'])for x in transport['shells'])
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==closed['Windows_image_anchor'] and shutil.disk_usage(R).free>=40*1024**3
 assert time.monotonic()-START<90;p.native_rss()
 output={'status':'ACTUAL_P20_RESOURCE_REPAIR_CURRENT_PREFLIGHT_PASS','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':EVENT_SHA,'source_preparation_actual_exit':event['actual_exit_receipt'],'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'actual_runtime_roles':pointer['actual_runtime_roles'],'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'new_shell_direct_env_and_bash_n':transport,'accepted_registry':plan['accepted_registry'],'reused_annotation_commit':plan['reused_annotation_commit'],'failed_closed_authority':plan['failed_closed_authority'],'source_manifest':plan['source_manifest'],'original_queue_reservation':context['queue_reservation'],'bound_repair_proposal':plan['repair_proposal'],'re_reservation_or_debit_reset':False,'remaining_reserved_count':18,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',output);print(json.dumps({'status':output['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
