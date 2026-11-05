"""Fast foreground file/OS reconciliation for the current exact event CLI; no science."""
from pathlib import Path
import ctypes,json,msvcrt,os,shutil,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_saved_P20_common_v001 as c
import checkm2_production_preparation_P1 as p
R=c.R;E=c.E/'current_event_reconciliation_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);affinity=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
 event_path=R/'state/local_continuation_queue_v1/events/b807b35bf88c172c081ec8d4df3741bdfda6c21b2a044d2a717f9b5b45c4cce8/event.json';event_sha='b8f9eaf465027e09ac3e009a4728cd35637819d7a6d43a7fa1ebc2fba9ff8dd7';assert b.digest(event_path)==event_sha;event=b.read(event_path)
 assert event['actual_exit_code']==0 and event['retained_handle_identity_verified']is True
 actual=b.read(b.bind(R,event['actual_exit_receipt']));assert actual['actual_exit_code']==0 and actual['exact_birth_handle_retained']is True
 b.bind(R,event['launch_receipt']);terminal=b.read(c.E/'preflight_v001/terminal.json');receipt=b.read(b.bind(R,terminal['result']));assert terminal['native_owner']['pid']==25392 and terminal['error']is None and terminal['owner_lease_descriptor_released']is True
 assert all(x['actual_exit_code']==0 and x['actual_handle_reaped']is True for x in terminal['actual_children'])
 observations=b.read(b.bind(R,receipt['observations']));old_cli_exit=R/'state/local_continuation_queue_v1/events/4eb0bd07ce99260e64df83ea03ceba4da32d7304cdf2331ec311036f6f385c9a/cli_actual_exit.json';assert b.read(old_cli_exit)['actual_exit_code']==0
 pointer=b.read(R/'state/local_continuation_current_runtime.json');roles=b.read(b.bind(R,pointer['actual_runtime_roles']))
 assert pointer['state_directory']=='state/local_continuation_queue_v1';b.bind(R,pointer['dispatcher_launch']);b.bind(R,pointer['detached_supervisor_launch'])
 monitor=b.read(R/'state/monitor_current_roles.json');live=[{**monitor[k],'role':k}for k in('gui','collector','publisher')]
 for role in roles['roles']:
  b.bind(R,role['source']);live.append({**role['identity'],'role':role['role'],'script':role['source']['path'],'script_sha256':role['source']['sha256']})
 cli_path=event_path.parent/'cli_started.json';cli=b.read(cli_path);assert cli['event_sha256']==event_sha;live.append({**cli['identity'],'role':'CURRENT_EVENT_CLI','script':'codex.exe'})
 command="$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @("+','.join(str(x['pid'])for x in live)+") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe','codex.exe'))} | Select-Object @{N='pid';E={$_.ProcessId}},@{N='parent_pid';E={$_.ParentProcessId}},@{N='name';E={$_.Name}},@{N='command';E={$_.CommandLine}})|ConvertTo-Json -Compress"
 census=run(['pwsh','-NoProfile','-Command',command],'Windows_census');census=census if isinstance(census,list)else[census];verified=[]
 for expected in live:
  handle=K.open_worker(expected)
  try:assert not K.wait(handle,0);current=K.identity(handle,expected['pid'])
  finally:K.close(handle)
  rec=next(x for x in census if x['pid']==expected['pid']);assert Path(expected['script']).name in rec['command'] and str(R)in rec['command']
  if 'script_sha256'in expected:assert b.digest(R/expected['script'])==expected['script_sha256']
  if expected['role']=='CURRENT_EVENT_CLI':
   assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER') and str(event_path.parent)in rec['command'] and '--disable plugins'in rec['command']
  if expected['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_EXTERNAL_DISPATCHER_SUPERVISOR')
  verified.append({'role':expected['role'],'identity':current,'source_and_launch_verified':True})
 allowed={x['pid']for x in live}|{OWNER['pid']}|{x['identity']['pid']for x in CHILDREN};suspects=[x for x in census if x['pid']not in allowed];assert not suspects,('Unknown project Python/WSL/Codex',suspects)
 plan_path=c.E/'runtime_plan.json';plan,recipe,_=c.plan_gate(plan_path,c.sha(plan_path),require_admission=False,closed_finalization=True)
 assert not c.ADMISSION.exists() and not c.LAUNCH.exists() and not list((c.E/'native_phase_claims').glob('*.json')) and not list(c.OUT.glob('sessions/*/once_claim.json'))
 assert b'\r'not in(R/'scripts/checkm2_saved_P20_v001.sh').read_bytes() and c.sha(R/'scripts/checkm2_saved_P20_v001.sh')==receipt['direct_env_and_bash_n']['shell_sha256']
 handles=[];leases=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,x)for x in leases]
 try:
  for name in leases:
   f=name.open('r+b');f.seek(0)
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except BaseException:f.close();raise
   handles.append(f)
  root='/mnt/c/'+str(R)[3:].replace('\\','/');targets=root+'/'+(c.E/'preflight_v001/historical_targets.json').relative_to(R).as_posix();source=R/'work/checkm2_N5_actual_prelaunch_linux.py'
  bound=c.read(c.E/'preflight_v001/Root_preflight_admission.json')['linux_observer_source'];c.bind(bound)
  code=source.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targets)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targets)+").read_text())['namespace_targets']");compile(code,'<current-event-OS-observer>','exec');linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_closure_resources')
  assert not any(linux[x]for x in('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==observations['Linux_full_raw_before_assertions']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==receipt['Windows_image_after'] and shutil.disk_usage(R).free>=40*1024**3
 assert time.monotonic()-START<90;p.native_rss()
 result={'status':'CURRENT_EVENT_SAVED_P20_RECONCILIATION_PASS','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':event_sha,'preflight_actual_exit':event['actual_exit_receipt'],'preflight_receipt':terminal['result'],'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'previous_CLI_actual_exit':b.row(R,old_cli_exit),'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'runtime_native_admission_created':False,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
