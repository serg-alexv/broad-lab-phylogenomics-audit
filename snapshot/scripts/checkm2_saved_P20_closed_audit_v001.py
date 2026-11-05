"""Fast foreground file/OS reconciliation for the current exact event CLI; no science."""
from pathlib import Path
import ctypes,json,msvcrt,os,shutil,subprocess,sys,time,math
import local_tree2_dispatcher as b
import checkm2_saved_P20_common_v001 as c
import checkm2_production_preparation_P1 as p
R=c.R;E=c.E/'closed_success_audit_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);affinity=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
 event_path=R/'state/local_continuation_queue_v1/events/bd32d415c66b7e4e0796dc07ace8074ca71cada03f6cd966cd8fa51715cc7e15/event.json';event_sha='1db619191c3e9c2a08273fec38078925d6fea855f29bd9f43a1802202e8b7327';assert b.digest(event_path)==event_sha;event=b.read(event_path)
 assert event['actual_exit_code']==0 and event['retained_handle_identity_verified']is True
 actual=b.read(b.bind(R,event['actual_exit_receipt']));assert actual['actual_exit_code']==0 and actual['exact_birth_handle_retained']is True
 b.bind(R,event['launch_receipt']);terminal=b.read(c.E/'preflight_v001/terminal.json');receipt=b.read(b.bind(R,terminal['result']));assert terminal['native_owner']['pid']==25392 and terminal['error']is None and terminal['owner_lease_descriptor_released']is True
 assert all(x['actual_exit_code']==0 and x['actual_handle_reaped']is True for x in terminal['actual_children'])
 observations=b.read(b.bind(R,receipt['observations']));old_cli_exit=R/'state/local_continuation_queue_v1/events/b807b35bf88c172c081ec8d4df3741bdfda6c21b2a044d2a717f9b5b45c4cce8/cli_actual_exit.json';assert b.read(old_cli_exit)['actual_exit_code']==0
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
 execution=c.read(c.E/'execution_pending_owner_exit.json');launch=c.read(c.LAUNCH);assert execution['status']=='P20_SAVED_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW' and execution['native_owner']==launch['native_owner'] and execution['native_owner']['pid']==5532 and execution['wsl_child_exit_code']==0 and execution['wsl_child_closed_observed']is True and execution['all_started_unit_groups_closed']is True and execution['host_registry_unchanged']is True and execution['biological_STOP_unchanged']is True and not execution['unresolved_ownership_handoff'] and not execution['error']
 assert actual['worker_identity']['pid']==5532 and actual['worker_identity']['windows_creation_filetime_100ns']==launch['native_owner']['windows_creation_filetime_100ns']
 envpath=c.E/'namespace_runs'/(launch['token']+'.json');env=c.read(envpath);assert env==execution['namespace_envelope'] and env['status']=='NAMESPACE_CLOSED_AND_VERIFIED' and env['helper_exit_code']==0 and env['image_unchanged']is True and env['image_sha256_after_clean_unmount']=='c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4' and env['image_bytes']==17179869184
 for key in ('mount_receipt','closure_receipt','ipc_receipt','ipc_closure'):assert c.sha(c.path(env[key+'_path']))==env[key+'_sha256']
 assert env['closure']['status']=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and env['closure']['readonly']is True and not env['closure']['errors'] and env['ipc_closure']['status']=='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT' and env['ipc_closure']['ordinary_unmount_only']is True and not env['ipc_closure']['errors'] and env['ipc_closure']['remaining_entries']==[]
 mount=c.read(c.path(env['mount_receipt_path']));ipc=c.read(c.path(env['ipc_receipt_path']));assert all(mount[x]is True for x in('raw_image_readonly','canonical_prefix_readonly','canonical_database_readonly','loop_readonly','loop_autoclear'))
 latest=c.read(c.OUT/'latest_pending_native.json');assert c.pending_is_current(latest,launch['token'],c.sha(plan_path),c.sha(c.ADMISSION),envpath) and latest['namespace_execution_receipt_sha256']==c.sha(envpath)
 runfolder=c.path(latest['run_directory']);mf=c.path(latest['manifest_path']);assert c.sha(mf)==latest['manifest_sha256'];c.verify_manifest(runfolder,c.read(mf));result=c.read(runfolder/'result.json');assert result['status']=='P20_SAVED_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE' and result['completed_qc_rows']==1 and len(result['rows'])==1 and result['annotation_DIAMOND_or_ML_runs']==0 and result['previously_accepted_rows_recalculated']is False
 member=result['rows'][0];features=c.read(c.bind(member['feature_validation']));unit=c.read(c.bind(member['unit_execution']));assert c.unit_closed(unit) and features['status']=='P20_SAVED_FEATURES_REPAIR_PASS_PENDING_REPAIR_OWNER_CLOSURE' and features['accession']==member['accession']=='GCF_000831485.1' and features['finite_domain_features']==21241 and features['exact_FAA_metadata_features']==22 and features['independently_recomputed_membership_features']==1220 and features['membership_mismatches']==0 and features['forbidden_model_modules_loaded']==[]
 assert unit['elapsed_seconds']<=60 and unit['sampled_peak_summed_rss_bytes']<=2147483648 and unit['sampled_min_linux_available_bytes']>=1073741824 and unit['budget_metric']=='SUM_PROCESS_RSS' and unit['pss_substitution']is False
 item=recipe['inputs'][0]
 for name in('source_holds_preserved','source_pending_reasons','source_masks'):assert features[name]==member[name]==item[name]
 for ref in member['original_successful_units'].values():assert c.unit_closed(c.read(c.bind(ref)))
 failed=c.read(c.bind(member['preserved_failed_unit']));assert failed['exit_code']==1 and failed['elapsed_seconds']==22.79685944299854 and failed['owned_group_empty']is True
 budget=c.budget(runfolder);assert budget==result['budget'] and budget['new_saved_validation_seconds_debited']==unit['elapsed_seconds'] and budget['old_P20_scientific_seconds_charged']==340.5752029999858
 assert len(c.read(runfolder/'invocations.json'))==1 and c.group_receipts_closed(runfolder);commit=runfolder/'rows/GCF_000831485.1/commit.json';rowcommit=c.read(commit);assert rowcommit['feature_validation']==member['feature_validation'];c.verify_manifest(commit.parent,c.read(c.bind(rowcommit['manifest'])))
 targets=c.read(c.E/'preflight_v001/historical_targets.json');ids=[env['helper_native_linux_identity'],env['inner_progress']['native_linux_identity'],unit['child_identity']]+unit['captured_owned_creation_identities']+unit['peak_per_pid_RSS_rows'];targets['Linux'].extend(ids);targets['namespace_targets'].extend([['mnt',mount['mount_namespace']],['net',ipc['network_namespace']]]);c.save(E/'historical_targets.json',targets)
 for expected in (launch['native_owner'],launch['wsl_child']):
  try:handle=K.open_worker(expected)
  except OSError as error:
   if getattr(error,'winerror',None)!=87:raise
  else:
   try:assert K.wait(handle,0),('Original worker still live',expected)
   finally:K.close(handle)

 assert b'\r'not in(R/'scripts/checkm2_saved_P20_v001.sh').read_bytes() and c.sha(R/'scripts/checkm2_saved_P20_v001.sh')==receipt['direct_env_and_bash_n']['shell_sha256']
 handles=[];leases=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,x)for x in leases]
 try:
  for name in leases:
   f=name.open('r+b');f.seek(0)
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except BaseException:f.close();raise
   handles.append(f)
  root='/mnt/c/'+str(R)[3:].replace('\\','/');targets=root+'/'+(E/'historical_targets.json').relative_to(R).as_posix();source=R/'work/checkm2_N5_actual_prelaunch_linux.py'
  bound=c.read(c.E/'preflight_v001/Root_preflight_admission.json')['linux_observer_source'];c.bind(bound)
  code=source.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targets)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targets)+").read_text())['namespace_targets']");compile(code,'<current-event-OS-observer>','exec');linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_closure_resources')
  assert not any(linux[x]for x in('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==observations['Linux_full_raw_before_assertions']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==receipt['Windows_image_after'] and shutil.disk_usage(R).free>=40*1024**3
 snapshot=E/'snapshot';snapshot.mkdir(exist_ok=False);records=[]
 for n,source in enumerate([p for p in runfolder.rglob('*')if p.is_file()]+[c.LAUNCH,c.ADMISSION,c.E/'execution_pending_owner_exit.json',envpath,c.path(env['mount_receipt_path']),c.path(env['closure_receipt_path']),c.path(env['ipc_receipt_path']),c.path(env['ipc_closure_path'])]):
  dest=snapshot/(f'{n:04d}_'+source.name);original=c.row(source);shutil.copyfile(source,dest);assert c.sha(dest)==original['sha256'];records.append({'original':original,'snapshot':c.row(dest)})
 c.save(E/'snapshot_manifest.json',{'files':records,'opaque_bytes_only_no_deserialization':True,'original_three_upstream_and_failed_validation_preserved':True})
 assert time.monotonic()-START<90;p.native_rss()
 result={'status':'SAVED_P20_VALIDATION_NATIVE_GROUP_NAMESPACE_IMAGE_IPC_LEASE_CLOSED','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':event_sha,'preflight_actual_exit':event['actual_exit_receipt'],'preflight_receipt':terminal['result'],'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'previous_CLI_actual_exit':b.row(R,old_cli_exit),'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'saved_method_estimate':{'accession':features['accession'],'Completeness':features['Completeness'],'Contamination':features['Contamination'],'feature_validation':member['feature_validation'],'commit':c.row(commit),'original_successful_units':member['original_successful_units'],'failed_original_validation':member['preserved_failed_unit'],'repair_unit':member['unit_execution'],'source_masks':features['source_masks'],'source_pending_reasons':features['source_pending_reasons'],'source_holds_preserved':features['source_holds_preserved']},'snapshot_manifest':c.row(E/'snapshot_manifest.json'),'budget':budget,'actual_original_native_exit_code':0,'actual_WSL_exit_code':0,'actual_helper_exit_code':0,'actual_saved_validation_unit_exit_code':0,'acceptance_requires_external_audit_exit':True,'production_panel_acceptance':False,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
