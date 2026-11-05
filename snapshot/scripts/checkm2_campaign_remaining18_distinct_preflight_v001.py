"""Fast foreground file/OS reconciliation for the current exact event CLI; no science."""
from pathlib import Path
import ctypes,json,math,msvcrt,os,shutil,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_campaign_index8_common_v002 as c
c.configure(Path(__file__).resolve().parents[1]/'metadata/checkm2_campaign_index8_v002/P20_production19_split_v004/input_plan.json', 'e52e64c77a150964ab54f304b862d4f00064c2d4808e984e26e9535e61535352')
import checkm2_saved_P20_common_v001 as saved
import checkm2_production_preparation_P1 as p
R=c.R;E=R/'evidence/checkm2_campaign_index8_v002/P20_remaining18_distinct_v005/preflight_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);b.exclusive(E/(role+'_stdout_capture.json'),{'stdout':out,'stderr':err,'actual_exit_code':child.returncode});assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);affinity=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
 event_path=R/'state/local_continuation_queue_v1/events/bd7cb0496658a7718ff0305db5a1dbb20e85edbbb36dac2f21e420d3651df3ff/event.json';event_sha='3e2c7908b68d24b4a7d2116406308f3e94a8c3cae55dded16955ab2ae5b0ee18';assert b.digest(event_path)==event_sha;event=b.read(event_path)
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
  rec=next(x for x in census if x['pid']==expected['pid']);assert Path(expected['script']).name in rec['command'] and str(R)in rec['command']
  if 'script_sha256'in expected:assert b.digest(R/expected['script'])==expected['script_sha256']
  if expected['role']=='CURRENT_EVENT_CLI':
   assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER') and str(event_path.parent)in rec['command'] and '--disable plugins'in rec['command']
  if expected['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':assert rec['parent_pid']==next(x['identity']['pid']for x in roles['roles']if x['role']=='ROOT_EXTERNAL_DISPATCHER_SUPERVISOR')
  verified.append({'role':expected['role'],'identity':current,'source_and_launch_verified':True})
 allowed={x['pid']for x in live}|{OWNER['pid']}|{x['identity']['pid']for x in CHILDREN};suspects=[x for x in census if x['pid']not in allowed];assert not suspects,('Unknown project Python/WSL/Codex',suspects)
 plan_path=R/'metadata/checkm2_campaign_index8_v002/P20_production19_split_v004/input_plan.json';plan,recipe,_=c.plan_gate(plan_path,c.sha(plan_path),require_admission=False,closed_finalization=True)
 execution=c.read(c.E/'execution_pending_owner_exit.json');launch=c.read(c.LAUNCH)
 assert execution['native_owner']==launch['native_owner']==event['worker_identity'] and execution['native_owner']['pid']==8700
 assert execution['wsl_child_closed_observed']is True and execution['wsl_child_exit_code']==1 and execution['all_started_unit_groups_closed']is True and execution['unresolved_ownership_handoff']is None and execution['host_registry_unchanged']is True and execution['biological_STOP_unchanged']is True
 envpath=c.E/'namespace_runs'/(launch['token']+'.json');env=c.read(envpath)
 assert env==execution['namespace_envelope'] and env['status']=='NAMESPACE_CLOSED_AND_VERIFIED' and env['helper_exit_code']==1 and env['image_unchanged']is True and env['image_sha256_after_clean_unmount']=='c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4'
 for name in('mount_receipt','closure_receipt','ipc_receipt','ipc_closure'):assert c.sha(c.path(env[name+'_path']))==env[name+'_sha256']
 assert env['closure']['status']=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and env['closure']['readonly']is True and not env['closure']['errors'] and env['ipc_closure']['status']=='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT' and env['ipc_closure']['ordinary_unmount_only']is True and not env['ipc_closure']['errors'] and env['ipc_closure']['remaining_entries']==[]
 mount=c.read(c.path(env['mount_receipt_path']));ipc=c.read(c.path(env['ipc_receipt_path']));runfolder=c.path(execution['run_directory']);failure=c.read(runfolder/'failure.json')
 assert failure['current_invocation_groups_closed']is True and failure['completed_qc_rows']==0 and failure['unknown_debit_blocker']is None
 paths=[c.path(x)for x in c.read(runfolder/'invocations.json')];assert len(paths)==7
 units=[c.read(x/'execution.json')for x in paths]
 for n,u in enumerate(units):
  assert u['exit_code']==(0 if n<6 else 1) and u['owned_group_empty']is True and not u['remaining_owned_processes'] and not u['unproven_numeric_group_members'] and not u['cleanup_errors'] and u['durable_terminal_receipt']is True
  assert u['budget_metric']=='SUM_PROCESS_RSS' and u['pss_substitution']is False and u['sampled_peak_summed_rss_bytes']<=2147483648 and u['sampled_min_linux_available_bytes']>=1073741824
  assert u['elapsed_seconds']<=u['timeout_seconds']
 folder=runfolder/'rows/GCF_002993975.1';commit=c.read(folder/'commit.json');feature=c.read(c.bind(commit['feature_validation']))
 assert set(commit['unit_executions'])=={'unit_annotation','unit_diamond','unit_saved_search_validation','unit_resume','unit_feature_validation'}
 for name,ref in commit['unit_executions'].items():assert c.unit_closed(c.read(c.bind(ref)))
 for name in('annotation_commit','diamond_commit','prediction_commit'):c.bind(commit[name])
 c.verify_manifest(folder,c.read(c.bind(commit['manifest'])))
 assert feature['accession']==commit['accession']=='GCF_002993975.1' and feature['Completeness']==94.62 and feature['Contamination']==.06
 assert (feature['finite_domain_features'],feature['exact_FAA_metadata_features'],feature['independently_recomputed_membership_features'])==(21241,22,1220)
 assert commit['source_taxonomy_acceptance']is False and commit['production_panel_acceptance']is False
 new=math.fsum(u['elapsed_seconds']for u in units);budget=failure['known_budget'];assert new==budget['cohort_scientific_seconds_debited']==1838.4249724320107
 assert budget['prior_actual_scientific_seconds_retained']==1920.4462116579962 and budget['prior_plus_new_actual_scientific_seconds']==3758.871184090007 and budget['known_limit_exceeded']is False
 from datetime import datetime
 cold=math.ceil((datetime.fromisoformat(event['observed_utc'])-datetime.fromisoformat(launch['native_owner']['creation_time_utc'])).total_seconds());assert cold==2767
 budget={**budget,'cold_session_conservative_actual_seconds_charged':cold,'cold_cap_seconds_preserved':40800,'remaining_from_that_cold_allocation_seconds':40800-cold,'cold_charge_method':'ceil(retained native handle exit observed UTC minus exact birth); all prior cold debits preserved separately'}
 targets=c.read(R/'evidence/checkm2_campaign_index8_v001/P20_production19_v003/failure_closure_v002/historical_targets.json');ids=[env['helper_native_linux_identity'],env['inner_progress']['native_linux_identity']]
 for u in units:
  ids.extend([u['child_identity']]+u['captured_owned_creation_identities']+u['peak_per_pid_RSS_rows'])
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
  code=source.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targets)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targets)+").read_text())['namespace_targets']");compile(code,'<current-event-OS-observer>','exec');linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_closure_resources')
  assert not any(linux[x]for x in('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==previous['Linux']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==previous['Windows_image_anchor'] and shutil.disk_usage(R).free>=40*1024**3
 import checkm2_campaign_index8_common_v004 as current
 newp=R/'metadata/checkm2_campaign_index8_v002/P20_remaining18_distinct_v005/input_plan.json';newsha='94b744fcc7995cf3ba0e63b0d5c197ae23aae1042547867e938d0745163d80bd'
 newplan,newrecipe,_=current.plan_gate(newp,newsha,require_admission=False)
 assert newplan['mode']=='CLOSED_INDEX8_PROFILE' and newplan['search_only_control']is None and newplan['annotation_reuse_by_accession']=={} and len(newplan['accessions'])==18 and not({'GCF_000831485.1','GCF_002993975.1'}&set(newplan['accessions']))
 assert current.prior_debits(newplan)==3758.871184090007 and current.LIMITS['cold_session_seconds']==38033 and current.LIMITS['cohort_scientific_seconds']==37721
 verified_inputs=[]
 for item in newrecipe['inputs']:
  fna=R/item['fasta_path'];ref={'path':item['fasta_path'],'sha256':item['fasta_sha256'],'bytes':item['fasta_bytes']};b.bind(R,ref);verified_inputs.append(ref)
 manifest=current.read(current.bind(newplan['source_manifest']))
 for ref in manifest['sources']:b.bind(R,ref)
 # Every changed consumer has a reversible source-only redirect; no scientific body or argv change.
 review=b.read(R/'metadata/checkm2_campaign_index8_v004/mechanical_redirect_review.json')
 for pair in review['source_consumer_redirects']:b.bind(R,pair['original']);b.bind(R,pair['new']);assert pair['complete_reverse_normalization_exact']is True
 shell=R/'scripts/checkm2_campaign_index8_shell_v005.sh';assert b'\r'not in shell.read_bytes()
 envcheck={'TREE2_CHECKM2_PILOT_LAUNCH_TOKEN':'BENIGN_SOURCE_TRANSPORT_ONLY_NO_RUNTIME','TREE2_QC_BATCH_PLAN':root+'/'+newp.relative_to(R).as_posix(),'TREE2_QC_BATCH_PLAN_SHA256':newsha}
 code='import os,json; print(json.dumps({k:os.environ[k] for k in '+repr(list(envcheck))+'}))'
 observed=run(['wsl','-d','Ubuntu','--','/usr/bin/env',*[k+'='+v for k,v in envcheck.items()],'/usr/bin/python3','-B','-c',code],'new_direct_env_transport');assert observed==envcheck
 shellcode='import subprocess,json; p=subprocess.run(["/bin/bash","-n",'+repr(root+'/'+shell.relative_to(R).as_posix())+'],capture_output=True,text=True); print(json.dumps({"actual_bash_n_exit":p.returncode,"stderr":p.stderr})); raise SystemExit(p.returncode)'
 syntax=run(['wsl','-d','Ubuntu','--','/usr/bin/python3','-B','-c',shellcode],'new_shell_syntax');assert syntax['actual_bash_n_exit']==0
 sourceproof={'status':'NEW_DISTINCT_SERIAL_POLICY_INPUT_SOURCES_AND_CURRENT_OWNERS_PREFLIGHT_PASS','input_plan':b.row(R,newp),'source_manifest':newplan['source_manifest'],'source_count':len(manifest['sources']),'verified_acquired_inputs':verified_inputs,'no_accepted_input_or_phase_replayed':True,'current_CLI_launch':b.row(R,cli_path),'verified_current_roles':verified,'original17unit_seconds_retained':current.prior_debits(newplan),'scientific_seconds_remaining':37721,'cold_seconds_remaining':38033,'explicit_new_per_unstarted_binary_seconds':3600,'policy_qualification':newplan['qualification_acceptance'],'actual_benign_env_transport':observed,'actual_bash_n':syntax,'shell_actual_bytes_contain_no_CR':True,'original_failed_reference_stays_failed':True,'all_original_numerical_bodies_and_search_argv_unchanged':True,'no_science_runtime_model_pickle_or_image_content_read':True}
 b.exclusive(E/'new_source_input_preflight.json',sourceproof)
 assert time.monotonic()-START<90;p.native_rss()
 result={'status':'DISTINCT_REMAINING18_EXACT_CURRENT_SOURCE_INPUT_OWNER_RESOURCE_PREFLIGHT_PASS','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':event_sha,'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'all_owner_context_and_lease_closure_verified':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'actual_native_exit_code':2,'actual_WSL_exit_code':1,'actual_helper_exit_code':1,'actual_native_exit_receipt':event['actual_exit_receipt'],'failed_reference_comparison_exit_code':1,'historical_Windows_creation_observations':closed_creation_observations,'unchanged_RSS_ceiling_bytes':2147483648,'new_unit_executions':[c.row(x/'execution.json')for x in paths],'own_row_commit':c.row(folder/'commit.json'),'own_feature_validation':commit['feature_validation'],'own_method_Completeness':94.62,'own_method_Contamination':.06,'own_row_five_units_actual0_closed':True,'numeric95_5_quality_gate':'FAIL_COMPLETENESS_BELOW95','production_panel_acceptance':False,'failed_raw_equivalence_remains_failed':True,'raw_and_model_input_equivalence_to_default4':False,'budget':budget,'new_source_input_preflight':b.row(R,E/'new_source_input_preflight.json'),'no_successful_phase_replayed':True,'new_production_admission_still_separate':True,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
