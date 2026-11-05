"""Fast foreground file/OS reconciliation for the current exact event CLI; no science."""
from pathlib import Path
import ctypes,json,math,msvcrt,os,shutil,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_campaign_index8_common_v004 as c
c.configure(Path(__file__).resolve().parents[1]/'metadata/checkm2_campaign_index8_v002/P20_remaining18_distinct_v005/input_plan.json', '94b744fcc7995cf3ba0e63b0d5c197ae23aae1042547867e938d0745163d80bd')
import checkm2_saved_P20_common_v001 as saved
import checkm2_production_preparation_P1 as p
R=c.R;E=c.E/'failure_closure_v002';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);b.exclusive(E/(role+'_stdout_capture.json'),{'stdout':out,'stderr':err,'actual_exit_code':child.returncode});assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);affinity=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
 event_path=R/'state/local_continuation_queue_v1/events/5acc3175b3d55f3ca8a52467e8f8e02fe6f623b4585326a0fce6024cfd05f06d/event.json';event_sha='ad7a3ed5a4b2731195610376964b07dc8907fa7c760c4a968f0b95ee5c0282a5';assert b.digest(event_path)==event_sha;event=b.read(event_path)
 assert event['actual_exit_code']==2 and event['retained_handle_identity_verified']is True
 actual=b.read(b.bind(R,event['actual_exit_receipt']));assert actual['actual_exit_code']==2 and actual['exact_birth_handle_retained']is True
 b.bind(R,event['launch_receipt'])
 previous=c.read(R/'evidence/checkm2_campaign_index8_v001/P20_production19_v003/failure_closure_v002/receipt.json')
 pointer=b.read(R/'state/local_continuation_current_runtime.json');roles=b.read(b.bind(R,pointer['actual_runtime_roles']))
 assert pointer['state_directory']=='state/local_continuation_queue_v1';b.bind(R,pointer['dispatcher_launch']);b.bind(R,pointer['detached_supervisor_launch'])
 role_ids={x['role']:x['identity']for x in roles['roles']};dispatch=b.read(b.bind(R,pointer['dispatcher_launch']));supervisor=b.read(b.bind(R,pointer['detached_supervisor_launch']))
 assert dispatch['dispatcher_owner']==role_ids['ROOT_LOCAL_RUNTIME_CONTROLLER'] and dispatch['supervisor_owner']==role_ids['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']==supervisor['native_owner']
 assert dispatch['core_source']==pointer['dispatcher_source'] and supervisor['entry_source']==pointer['supervisor_source'];b.bind(R,pointer['config']);b.bind(R,pointer['Root_operational_admission'])
 monitor=b.read(R/'state/monitor_current_roles.json');live=[{**monitor[k],'role':k}for k in('collector','publisher')]
 marker=b.read(R/'state/stages/06.json');marker_admission=R/'analysis/marker_discovery/pilot10_recovered_v001/Root_shared_resource_admission.json';ma=b.read(marker_admission);msource=R/'scripts/marker_pilot_compute_v001.py';assert b.digest(msource)==ma['script_sha256']=='b04aeeeb9e8d972b2d38ce1e5b6466913a4adaa1fb49507275ad0aab58a91cad'
 marker_identity={'pid':21868,'creation_time_utc':'2026-10-27T19:42:24.2305912Z','windows_creation_filetime_100ns':134376037442305912};assert marker['pid']==21868 and marker['creation_time_utc']==marker_identity['creation_time_utc'];live.append({**marker_identity,'role':'ROOT_ADMITTED_FOREGROUND_MARKER_NATIVE','script':msource.relative_to(R).as_posix(),'script_sha256':b.digest(msource)})
 presentation=b.read(R/'state/monitor_presentation_current.json');visible=b.read(b.bind(R,presentation['deployment_receipt']));assert visible['gui']==presentation['gui'];live.append({**presentation['gui'],'role':'CURRENT_VISIBLE_PRESENTATION_GUI'})
 b.bind(R,presentation['scientific_monitor_roles_unchanged']);verification=b.read(b.bind(R,presentation['current_verification']));assert verification['gui']==presentation['gui'] and verification['no_scientific_write_or_signal']is True
 b.bind(R,verification['executed_deployment_source'])
 for role in roles['roles']:
  b.bind(R,role['source']);live.append({**role['identity'],'role':role['role'],'script':role['source']['path'],'script_sha256':role['source']['sha256']})
 cli_path=event_path.parent/'cli_started.json';cli=b.read(cli_path);assert cli['event_sha256']==event_sha;live.append({**cli['identity'],'role':'CURRENT_EVENT_CLI','script':'codex.exe'})
 command="$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @("+','.join(str(x['pid'])for x in live)+") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe','codex.exe'))} | Select-Object @{N='pid';E={$_.ProcessId}},@{N='parent_pid';E={$_.ParentProcessId}},@{N='name';E={$_.Name}},@{N='command';E={$_.CommandLine}})|ConvertTo-Json -Compress"
 census=run(['pwsh','-NoProfile','-Command',command],'Windows_census');census=census if isinstance(census,list)else[census];verified=[]
 for expected in live:
  handle=K.open_worker(expected)
  try:assert not K.wait(handle,0);current=K.identity(handle,expected['pid'])
  finally:K.close(handle)
  rec=next(x for x in census if x['pid']==expected['pid']);assert Path(expected['script']).name in rec['command'] and (str(R)in rec['command'] or '/mnt/c/'+str(R)[3:].replace('\\','/')in rec['command'])
  if 'script_sha256'in expected:assert b.digest(R/expected['script'])==expected['script_sha256']
  if expected['role']=='CURRENT_EVENT_CLI':
   assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER') and str(event_path.parent)in rec['command'] and '--disable plugins'in rec['command']
  if expected['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_EXTERNAL_DISPATCHER_SUPERVISOR')
  verified.append({'role':expected['role'],'identity':current,'source_and_launch_verified':True})
 marker_native_bridges=[];marker_ancestry={marker_identity['pid']:marker_identity}
 for _ in range(4):
  for rec in census:
   if rec['pid']in marker_ancestry or rec['parent_pid']not in marker_ancestry:continue
   assert rec['name']=='wsl.exe' and 'marker_pilot_compute_v001.py'in rec['command']and '--native-pid 21868'in rec['command']and 'Root_shared_resource_admission.json'in rec['command']and 'candidate_manifest.json'in rec['command']
   handle=K.k.OpenProcess(0x00100000|0x1000,False,rec['pid']);assert handle
   try:identity=K.identity(handle,rec['pid']);assert not K.wait(handle,0) and identity['windows_creation_filetime_100ns']>=marker_ancestry[rec['parent_pid']]['windows_creation_filetime_100ns']
   finally:K.close(handle)
   marker_ancestry[identity['pid']]=identity;marker_native_bridges.append({'identity':identity,'parent_identity':marker_ancestry[rec['parent_pid']],'command_line':rec['command'],'same_pinned_marker_source_admission_inputs_and_native_root':True})
 assert {x['identity']['pid']for x in marker_native_bridges}=={23324,16292}
 allowed={x['pid']for x in live}|{OWNER['pid']}|{x['identity']['pid']for x in CHILDREN}|set(marker_ancestry);suspects=[x for x in census if x['pid']not in allowed];assert not suspects,('Unknown project Python/WSL/Codex',suspects)
 plan_path=R/'metadata/checkm2_campaign_index8_v002/P20_remaining18_distinct_v005/input_plan.json';plan,recipe,_=c.plan_gate(plan_path,c.sha(plan_path),require_admission=False,closed_finalization=True)
 execution=c.read(c.E/'execution_pending_owner_exit.json');launch=c.read(c.LAUNCH)
 assert execution['native_owner']==launch['native_owner']==event['worker_identity'] and execution['native_owner']['pid']==18312
 assert execution['wsl_child_closed_observed']is True and execution['wsl_child_exit_code']==1 and execution['all_started_unit_groups_closed']is True and execution['unresolved_ownership_handoff']is None and execution['host_registry_unchanged']is True and execution['biological_STOP_unchanged']is True
 envpath=c.E/'namespace_runs'/(launch['token']+'.json');env=c.read(envpath)
 assert env==execution['namespace_envelope'] and env['status']=='NAMESPACE_CLOSED_AND_VERIFIED' and env['helper_exit_code']==1 and env['image_unchanged']is True and env['image_sha256_after_clean_unmount']=='c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4'
 for name in('mount_receipt','closure_receipt','ipc_receipt','ipc_closure'):assert c.sha(c.path(env[name+'_path']))==env[name+'_sha256']
 assert env['closure']['status']=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and env['closure']['readonly']is True and not env['closure']['errors'] and env['ipc_closure']['status']=='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT' and env['ipc_closure']['ordinary_unmount_only']is True and not env['ipc_closure']['errors'] and env['ipc_closure']['remaining_entries']==[]
 mount=c.read(c.path(env['mount_receipt_path']));ipc=c.read(c.path(env['ipc_receipt_path']));runfolder=c.path(execution['run_directory']);failure=c.read(runfolder/'failure.json')
 assert failure['current_invocation_groups_closed']is True and failure['completed_qc_rows']==0 and failure['unknown_debit_blocker']is None
 paths=[c.path(x)for x in c.read(runfolder/'invocations.json')];assert len(paths)==4
 units=[c.read(x/'execution.json')for x in paths]
 for n,u in enumerate(units):
  assert u['exit_code']==(0 if n<3 else -15) and u['owned_group_empty']is True and not u['remaining_owned_processes'] and not u['unproven_numeric_group_members'] and not u['cleanup_errors'] and u['durable_terminal_receipt']is True
  assert u['budget_metric']=='SUM_PROCESS_RSS' and u['pss_substitution']is False and u['sampled_peak_summed_rss_bytes']<=2147483648 and u['sampled_min_linux_available_bytes']>=1073741824
  assert u['elapsed_seconds']<=u['timeout_seconds']
 folder=runfolder/'rows/GCF_900636715.1';annotation=c.read(folder/'annotation_commit.json');search=c.read(folder/'diamond_commit.json')
 assert c.unit_closed(c.read(c.bind(annotation['unit_execution']))) and c.unit_closed(c.read(c.bind(search['unit_execution']))) and c.unit_closed(c.read(c.bind(search['validation_unit_execution'])))
 for com in (annotation,search):c.verify_manifest(c.bind(com['manifest']).parent,c.read(c.bind(com['manifest'])))
 c.bind(annotation['selected_faa']);c.bind(search['raw_diamond'])
 failed=units[-1];assert failed['failure_kind']=='RUNTIME_OR_OBSERVER' and failed['error_details']['errno']==12 and failed['error_details']['operation_path']=='STOP/admission/WD/MemAvailable/backing_volume'
 assert not(folder/'prediction_commit.json').exists()and not(folder/'commit.json').exists()and not(folder/'resume_output/quality_report.tsv').exists()and not list((folder/'resume_output').glob('*.pkl'))
 assert failed['sampled_peak_summed_rss_bytes']==438820864 and failed['sampled_min_linux_available_bytes']==2956169216
 new=math.fsum(u['elapsed_seconds']for u in units);budget=failure['known_budget'];assert new==budget['cohort_scientific_seconds_debited']==964.1882817369915 and budget['prior_actual_scientific_seconds_retained']==3758.871184090007 and budget['prior_plus_new_actual_scientific_seconds']==4723.059465826998 and budget['known_limit_exceeded']is False
 from datetime import datetime
 cold=math.ceil((datetime.fromisoformat(event['observed_utc'])-datetime.fromisoformat(launch['native_owner']['creation_time_utc'])).total_seconds());assert cold==2011
 budget={**budget,'cold_session_conservative_actual_seconds_charged':cold,'cold_cap_seconds_preserved':38033,'remaining_from_that_cold_allocation_seconds':38033-cold,'no_prior_actuals_claims_or_failed_caps_reset':True}
 targets=c.read(R/'evidence/checkm2_campaign_index8_v002/P20_production19_split_v004/closed_context_audit_v002/historical_targets.json');ids=[env['helper_native_linux_identity'],env['inner_progress']['native_linux_identity']]
 for u in units:ids.extend([u['child_identity']]+u['captured_owned_creation_identities']+u['peak_per_pid_RSS_rows'])
 targets['Linux'].extend(ids);targets['namespace_targets'].extend([['mnt',mount['mount_namespace']],['net',ipc['network_namespace']]]);c.save(E/'historical_targets.json',targets)
 closed_creation_observations=[]
 for expected in(launch['native_owner'],launch['wsl_child']):
  handle=K.k.OpenProcess(0x00100000|0x00001000,False,expected['pid'])
  if not handle:
   error=ctypes.WinError(ctypes.get_last_error())
   if getattr(error,'winerror',None)!=87:raise error
   closed_creation_observations.append({'historical_identity':expected,'observation':'NO_PROCESS_WITH_THIS_NUMERIC_PID','historical_exit_inferred':False})
  else:
   try:
    observed=K.identity(handle,expected['pid'])
    if observed['windows_creation_filetime_100ns']==expected['windows_creation_filetime_100ns']:
     assert observed['creation_time_utc']==expected['creation_time_utc'] and K.wait(handle,0)
     closed_creation_observations.append({'historical_identity':expected,'observation':'SAME_CREATION_HANDLE_SIGNALED','historical_exit_inferred':False})
    else:
     closed_creation_observations.append({'historical_identity':expected,'observation':'PID_REUSED_DIFFERENT_CREATION_NOT_OLD_OWNER','observed_replacement_identity':observed,'replacement_not_signalled_or_modified':True,'historical_exit_inferred':False})
   finally:K.close(handle)

 assert b'\r'not in(R/'scripts/checkm2_P20_continue19_v001.sh').read_bytes()
 handles=[];leases=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,x)for x in leases]
 try:
  for name in leases:
   f=name.open('r+b');f.seek(0)
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except BaseException:f.close();raise
   handles.append(f)
  root='/mnt/c/'+str(R)[3:].replace('\\','/');targets=root+'/'+(E/'historical_targets.json').relative_to(R).as_posix();source=R/'work/checkm2_N5_actual_prelaunch_linux.py'
  bound=c.read(saved.E/'preflight_v001/Root_preflight_admission.json')['linux_observer_source'];c.bind(bound)
  code=source.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targets)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targets)+").read_text())['namespace_targets']");marker_linux=marker['linux_owner_identity'];assert marker_linux['pid']==6539 and marker_linux['start_ticks']==10537971
  marker_observer="\nallowed_marker={};marker_root="+repr(marker_linux)+"\nfor task in Path('/proc').iterdir():\n if not task.name.isdigit():continue\n try:\n  a=(task/'stat').read_text().rsplit(')',1)[1].split();allowed_marker[int(task.name)]={'pid':int(task.name),'parent_pid':int(a[1]),'creation_ticks':int(a[19]),'boot_id':boot}\n except(FileNotFoundError,ProcessLookupError):pass\nmr=allowed_marker.get(marker_root['pid']);assert mr and mr['creation_ticks']==marker_root['start_ticks'] and mr['boot_id']==marker_root['boot_id']\nallowed_ids={marker_root['pid']}\nwhile True:\n extra={pid for pid,row in allowed_marker.items() if row['parent_pid']in allowed_ids} - allowed_ids\n if not extra:break\n allowed_ids.update(extra)\nregistered_marker_project=[row for row in project if row['pid']in allowed_ids and row['creation_ticks']==allowed_marker[row['pid']]['creation_ticks']]\nregistered_marker_science=[row for row in science if row['pid']in allowed_ids and row['creation_ticks']==allowed_marker[row['pid']]['creation_ticks']]\nproject=[row for row in project if row not in registered_marker_project]\nscience=[row for row in science if row not in registered_marker_science]\nassert os.sched_getaffinity(marker_root['pid'])=={2}\n"
  code=code.replace('print(json.dumps(',marker_observer+'\nprint(json.dumps(').replace("'observer_identity':mine,","'registered_marker_project':registered_marker_project,'registered_marker_science':registered_marker_science,'observer_identity':mine,")
  compile(code,'<current-event-OS-observer>','exec');linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_closure_resources')
  assert not any(linux[x]for x in('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==previous['Linux']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==previous['Windows_image_anchor'] and shutil.disk_usage(R).free>=40*1024**3
 snapshot=E/'snapshot';snapshot.mkdir(exist_ok=False);records=[]
 for n,source in enumerate([p for p in runfolder.rglob('*')if p.is_file()]+[c.LAUNCH,c.ADMISSION,c.E/'execution_pending_owner_exit.json',envpath]+[c.path(env[k+'_path'])for k in('mount_receipt','closure_receipt','ipc_receipt','ipc_closure')]):
  dest=snapshot/(f'{n:04d}_'+source.name);original=c.row(source);shutil.copyfile(source,dest);assert c.sha(dest)==original['sha256'];records.append({'original':original,'snapshot':c.row(dest)})
 c.save(E/'snapshot_manifest.json',{'files':records,'opaque_bytes_only':True,'all_failed_search_partials_and_annotation_commit_preserved':True})
 assert time.monotonic()-START<90;p.native_rss()
 marker_rec=next(x for x in census if x['pid']==marker_identity['pid'])
 b.exclusive(E/'observed_marker_foreground_native_registration.json',{'schema':'TREE2_EXISTING_FOREGROUND_NATIVE_REGISTRATION_V001','status':'EXACT_EXISTING_ROOT_ADMITTED_FOREGROUND_MARKER_OWNER_VERIFIED','native_owner':marker_identity,'role':'EXPLORATORY_MARKER_ALIGNMENT_AND_PROFILE_BUILD','source':b.row(R,msource),'scientific_admission':b.row(R,marker_admission),'input_manifest':marker['input_manifest'],'command_line':marker_rec['command'],'original_launch_not_reexecuted':True,'origin':'Existing Root retained WSLEXEC foreground scientific handle, explicitly permitted by current AGENTS marker exception; not a new background controller or launch','source_and_exact_birth_and_Linux_ancestry_verified':True,'Linux_owner_identity':marker_linux,'verified_nested_native_bridges':marker_native_bridges,'maximum_per_unit_seconds':180,'maximum_candidate_count':281,'maximum_summed_RSS_bytes':268435456,'one_CPU':2,'stop_marker_only_below_linux_available_bytes':1342177280,'actual_exit':'UNKNOWN_UNTIL_RETAINED_HANDLE_OBSERVER','at_utc':b.utc()})
 result={'status':'QC_OBSERVER_ADMISSION_READ_ENOMEM_EXTERNALLY_CLOSED_SAVED_PHASES_PRESERVED','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':event_sha,'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'all_owner_context_and_lease_closure_verified':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'actual_native_exit_code':2,'actual_WSL_exit_code':1,'actual_helper_exit_code':1,'actual_native_exit_receipt':event['actual_exit_receipt'],'failed_resume_unit_exit_code':-15,'failed_resume_errno':12,'failure_operation':'hash admission file during STOP/admission gate; actual cause of ENOMEM remains UNKNOWN','historical_Windows_creation_observations':closed_creation_observations,'unchanged_RSS_ceiling_bytes':2147483648,'new_unit_executions':[c.row(x/'execution.json')for x in paths],'reusable_annotation_commit':c.row(folder/'annotation_commit.json'),'reusable_diamond_commit':c.row(folder/'diamond_commit.json'),'actual_annotation_search_raw_validation_all0_closed':True,'stock_prediction_completed':False,'features_or_biological_quality':'UNKNOWN_UNRUN','production_panel_acceptance':False,'budget':budget,'snapshot_manifest':c.row(E/'snapshot_manifest.json'),'no_successful_phase_replayed':True,'registered_light_marker_owner':b.row(R,E/'observed_marker_foreground_native_registration.json'),'not_a_new_QC_exclusivity_preflight':True,'new_production_admission_still_separate':True,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
