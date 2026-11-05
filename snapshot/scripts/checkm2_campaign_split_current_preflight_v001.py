"""Fast foreground file/OS reconciliation for the current exact event CLI; no science."""
from pathlib import Path
import ctypes,json,math,msvcrt,os,shutil,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_campaign_index8_common_v001 as c
c.configure(Path(__file__).resolve().parents[1]/'metadata/checkm2_campaign_index8_v001/P20_production19_v003/input_plan.json', '5ff0a56577b5479d06f41a56d66f81d8e30915e21907ab7a864cb2db0acc516b')
import checkm2_saved_P20_common_v001 as saved
import checkm2_production_preparation_P1 as p
R=c.R;E=R/'evidence/checkm2_campaign_index8_v002/P20_production19_split_v004/preflight_v001';K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[];START=time.monotonic()
def run(argv,role):
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));record={'role':role,'identity':K.identity(int(child._handle),child.pid),'actual_exit_code':None,'actual_handle_reaped':False};CHILDREN.append(record)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:
  b.exclusive(E/'UNRESOLVED_CHILD.json',record);raise
 record.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err);b.exclusive(E/(role+'_exit.json'),record);b.exclusive(E/(role+'_stdout_capture.json'),{'stdout':out,'stderr':err,'actual_exit_code':child.returncode});assert child.returncode==0,(role,err);return json.loads(out)
def main():
 E.mkdir(exist_ok=False);affinity=p.affinity(K)
 b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'maximum_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
 event_path=R/'state/local_continuation_queue_v1/events/10639a9b76a831a8e0c56d45a6c8fad3d5c4c8b45f5f8caed2929e565635272d/event.json';event_sha='534dc035acc2d6410f3ac741406175035ba748668c439a36c26076a2c70eba26';assert b.digest(event_path)==event_sha;event=b.read(event_path)
 assert event['actual_exit_code']==0 and event['retained_handle_identity_verified']is True
 actual=b.read(b.bind(R,event['actual_exit_receipt']));assert actual['actual_exit_code']==0 and actual['exact_birth_handle_retained']is True
 boundary=R/'evidence/checkm2_campaign_index8_v002/source_publication_boundary_v002';metadata_terminal=b.read(boundary/'result_pending_actual_exit.json');assert metadata_terminal['native_owner']==event['worker_identity'] and metadata_terminal['error']is None and metadata_terminal['no_subprocess_science_runtime_image_genome_or_pickle_read']is True
 b.bind(R,event['launch_receipt']);terminal=b.read(saved.E/'preflight_v001/terminal.json');receipt=b.read(b.bind(R,terminal['result']));assert terminal['native_owner']['pid']==25392 and terminal['error']is None and terminal['owner_lease_descriptor_released']is True
 assert all(x['actual_exit_code']==0 and x['actual_handle_reaped']is True for x in terminal['actual_children'])
 observations=b.read(b.bind(R,receipt['observations']));old_cli_exit=R/'state/local_continuation_queue_v1/events/09997f7b7ae612c477c14a8594f3a95f2267d07e469e40a476f2209796be2d57/cli_actual_exit.json';assert type(b.read(old_cli_exit)['actual_exit_code'])is int
 pointer=b.read(R/'state/local_continuation_current_runtime.json');roles=b.read(b.bind(R,pointer['actual_runtime_roles']))
 assert pointer['state_directory']=='state/local_continuation_queue_v1';b.bind(R,pointer['dispatcher_launch']);b.bind(R,pointer['detached_supervisor_launch'])
 role_ids={x['role']:x['identity']for x in roles['roles']};dispatch=b.read(b.bind(R,pointer['dispatcher_launch']));supervisor=b.read(b.bind(R,pointer['detached_supervisor_launch']))
 assert dispatch['dispatcher_owner']==role_ids['ROOT_LOCAL_RUNTIME_CONTROLLER'] and dispatch['supervisor_owner']==role_ids['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']==supervisor['native_owner']
 assert dispatch['core_source']==pointer['dispatcher_source'] and supervisor['entry_source']==pointer['supervisor_source'];b.bind(R,pointer['config']);b.bind(R,pointer['Root_operational_admission'])
 monitor=b.read(R/'state/monitor_current_roles.json');live=[{**monitor[k],'role':k}for k in('gui','collector','publisher')]
 presentation=b.read(R/'state/monitor_presentation_current.json');visible=b.read(b.bind(R,presentation['gui_launch']));assert visible['native_owner']==presentation['gui'];live.append({**presentation['gui'],'role':'CURRENT_VISIBLE_PRESENTATION_GUI'})
 b.bind(R,presentation['overlay']);assert b.digest(R/presentation['gui']['classifier'])==presentation['gui']['classifier_sha256']
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
 plan_path=R/'metadata/checkm2_campaign_index8_v001/P20_production19_v003/input_plan.json';plan,recipe,_=c.plan_gate(plan_path,c.sha(plan_path),require_admission=False,closed_finalization=True)
 execution=c.read(c.E/'execution_pending_owner_exit.json');launch=c.read(c.LAUNCH);assert execution['native_owner']==launch['native_owner'] and execution['native_owner']['pid']==12452 and execution['wsl_child_closed_observed']is True and execution['wsl_child_exit_code']==1 and execution['all_started_unit_groups_closed']is True and execution['unresolved_ownership_handoff']is None and execution['host_registry_unchanged']is True and execution['biological_STOP_unchanged']is True
 scientific_actual=b.read(R/'state/local_continuation_queue_v1/worker_exits/12452_134375954432665714.json');assert scientific_actual['actual_exit_code']==2 and scientific_actual['exact_birth_handle_retained']is True and scientific_actual['worker_identity']['windows_creation_filetime_100ns']==launch['native_owner']['windows_creation_filetime_100ns']
 envpath=c.E/'namespace_runs'/(launch['token']+'.json');env=c.read(envpath);assert env==execution['namespace_envelope'] and env['status']=='NAMESPACE_CLOSED_AND_VERIFIED' and env['helper_exit_code']==1 and env['image_unchanged']is True and env['image_sha256_after_clean_unmount']=='c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4'
 for name in('mount_receipt','closure_receipt','ipc_receipt','ipc_closure'):assert c.sha(c.path(env[name+'_path']))==env[name+'_sha256']
 assert env['closure']['status']=='CLEAN_UNMOUNT_AND_LOOP_DETACH' and env['closure']['readonly']is True and not env['closure']['errors'] and env['ipc_closure']['status']=='CLEAN_IPC_ALIAS_AND_BACKING_UNMOUNT' and env['ipc_closure']['ordinary_unmount_only']is True and not env['ipc_closure']['errors'] and env['ipc_closure']['remaining_entries']==[]
 mount=c.read(c.path(env['mount_receipt_path']));ipc=c.read(c.path(env['ipc_receipt_path']));runfolder=c.path(execution['run_directory']);failure=c.read(runfolder/'failure.json');assert failure['current_invocation_groups_closed']is True and failure['completed_qc_rows']==0
 paths=[c.path(x)for x in c.read(runfolder/'invocations.json')];assert len(paths)==1 and paths[0].name=='unit_diamond'
 failed=c.read(paths[0]/'execution.json');annotation=c.annotation_reuse_gate(plan,'GCF_002993975.1',recipe['inputs'][0]);commit=c.bind(plan['annotation_reuse_by_accession']['GCF_002993975.1']['commit']);ann=c.read(c.bind(annotation['unit_execution']))
 assert c.unit_closed(ann) and failed['exit_code']==-15 and failed['failure_kind']=='TIMEOUT' and failed['owned_group_empty']is True and failed['remaining_owned_processes']==[] and failed['unproven_numeric_group_members']==[] and not failed['cleanup_errors'] and failed['durable_terminal_receipt']is True and failed['budget_metric']=='SUM_PROCESS_RSS' and failed['pss_substitution']is False
 assert failed['sampled_peak_summed_rss_bytes']==1426886656 and failed['sampled_peak_summed_rss_bytes']<=2147483648 and failed['elapsed_seconds']==900.3112721330108 and ann['elapsed_seconds']==36.03804357199988
 allocation=c.read(paths[0].parent/'unit_diamond_budget.json');assert allocation['allowed_seconds']==900 and failed['elapsed_seconds']>allocation['allowed_seconds']
 budget={'known_actual_elapsed_seconds':failed['elapsed_seconds'],'failed_original_cap_seconds':allocation['allowed_seconds'],'known_limit_exceeded':True,'termination_overshoot_seconds':failed['elapsed_seconds']-allocation['allowed_seconds'],'prior_two_search_seconds':600.2386157629953,'all_three_search_seconds_charged':math.fsum([600.2386157629953,failed['elapsed_seconds']]),'original_annotation_seconds_charged':ann['elapsed_seconds'],'old_P20_scientific_seconds_charged':340.5752029999858,'saved_metadata_validation_seconds_charged':43.283077190004406,'unknown_actual_elapsed':False,'old_failed_deadline_preserved':True}
 assert max(x['rss_bytes']for x in failed['peak_per_pid_RSS_rows'])<=2147483648
 folder=runfolder/'rows/GCF_002993975.1';assert not(folder/'annotation_commit.json').exists() and not(folder/'diamond_commit.json').exists() and not(folder/'prediction_commit.json').exists() and not(folder/'commit.json').exists();raw=folder/'resume_output/diamond_output/DIAMOND_RESULTS.tsv';assert raw.is_file()  # Preserved opaque bytes never establish binary actual0 or completeness.
 prepared=c.read(folder/'search_receipts/search_exec_prepared.json');request=c.read(folder/'requests/diamond.json');assert prepared['request_sha256']==c.sha(folder/'requests/diamond.json') and prepared['selected_faa']==annotation['selected_faa'] and prepared['database']==request['database'] and prepared['diamond_binary']==request['diamond_binary'] and prepared['no_model_modules']==[] and prepared['original_DiamondRunner_executed']is False
 c.bind(prepared['query']);assert prepared['argv'][1:4]==['blastp','--outfmt','6'] and prepared['argv'][prepared['argv'].index('--block-size')+1]=='0.5' and prepared['argv'][prepared['argv'].index('--threads')+1]=='1'
 targets=c.read(c.E/'preflight_v002/historical_targets.json');ids=[env['helper_native_linux_identity'],env['inner_progress']['native_linux_identity']]
 ids.extend([failed['child_identity']]+failed['captured_owned_creation_identities']+failed['peak_per_pid_RSS_rows'])
 targets['Linux'].extend(ids);targets['namespace_targets'].extend([['mnt',mount['mount_namespace']],['net',ipc['network_namespace']]]);c.save(E/'historical_targets.json',targets)
 closed_creation_observations=[]
 for expected in(launch['native_owner'],launch['wsl_child'],event['worker_identity']):
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
  assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==c.read(R/'evidence/checkm2_runtime/install_registry_before.json') and linux['image_before']==linux['image_after']==observations['Linux_full_raw_before_assertions']['image_after'] and linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in leases]
 image=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(image,k)for k in('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')};assert anchor==receipt['Windows_image_after'] and shutil.disk_usage(R).free>=40*1024**3
 snapshot=E/'snapshot';snapshot.mkdir(exist_ok=False);records=[]
 for n,source in enumerate([p for p in runfolder.rglob('*')if p.is_file()]+[c.LAUNCH,c.ADMISSION,c.E/'execution_pending_owner_exit.json',envpath]+[c.path(env[k+'_path'])for k in('mount_receipt','closure_receipt','ipc_receipt','ipc_closure')]):
  dest=snapshot/(f'{n:04d}_'+source.name);original=c.row(source);shutil.copyfile(source,dest);assert c.sha(dest)==original['sha256'];records.append({'original':original,'snapshot':c.row(dest)})
 c.save(E/'snapshot_manifest.json',{'files':records,'opaque_bytes_only':True,'all_failed_search_partials_and_annotation_commit_preserved':True})
 import checkm2_campaign_index8_common_v002 as campaign
 new_plan=R/'metadata/checkm2_campaign_index8_v002/P20_production19_split_v004/input_plan.json';fresh,fresh_recipe,_=campaign.plan_gate(new_plan,b.digest(new_plan),require_admission=False)
 assert len(fresh_recipe['inputs'])==19 and fresh['limits']['cold_session_seconds']==40800 and fresh['limits']['cohort_scientific_seconds']==39560 and campaign.phase_cap('unit_diamond','GCF_002993975.1')==3600
 for item in fresh_recipe['inputs']:
  fna=campaign.path(item['fasta_path']);assert b.digest(fna)==item['fasta_sha256'] and fna.stat().st_size==item['fasta_bytes']
 for ref in b.read(b.bind(R,fresh['source_manifest']))['sources']:b.bind(R,ref)
 old_shell=R/'scripts/checkm2_campaign_index8_env_transport_v002.sh';new_shell=R/'scripts/checkm2_campaign_index8_shell_v003.sh'
 assert new_shell.read_bytes()==old_shell.read_bytes().replace(b'checkm2_campaign_index8_entry_v001.py',b'checkm2_campaign_index8_entry_v002.py')
 old_transport=R/'evidence/checkm2_campaign_index8_v001/P20_production19_v003/preflight_v002/new_transport_inputs_source_proof.json';old_transport_proof=b.read(old_transport);assert old_transport_proof['actual_benign_WSL_exit_code']==0 and old_transport_proof['all_three_leases_reacquired_released_bytes_unchanged']is True
 root_plan=root+'/'+new_plan.relative_to(R).as_posix();nonce='161492fed66f4ab292e48de3c3045802'
 code="import os,json,subprocess,hashlib\nfrom pathlib import Path\nr=Path("+repr(root)+");p=Path(os.environ['TREE2_QC_BATCH_PLAN'])\nassert str(p)=="+repr(root_plan)+" and hashlib.sha256(p.read_bytes()).hexdigest()==os.environ['TREE2_QC_BATCH_PLAN_SHA256']=="+repr(b.digest(new_plan))+"\nassert os.environ['TREE2_CHECKM2_PILOT_LAUNCH_TOKEN']=="+repr(nonce)+"\nmanifest=json.loads((r/"+repr(fresh['source_manifest']['path'])+").read_text());rows=[]\nfor ref in manifest['sources']:\n p=r/ref['path'];raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256']\n if p.suffix in('.py','.sh'):assert bytes([13])not in raw\n if p.suffix=='.py':compile(raw,str(p),'exec')\n if p.suffix=='.sh':\n  child=subprocess.Popen(['/bin/bash','-n',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);o,e=child.communicate(timeout=10);assert child.returncode==0,(str(p),e);rows.append({'source':ref,'actual_syntax_exit_code':child.returncode,'retained_Popen_wait_observed':True})\nprint(json.dumps({'explicit_new_plan_SHA_token_verified':True,'all_python_compiled_without_target_import':True,'actual_LF_shell_syntax':rows,'runtime_image_or_models_not_opened':True}))\n"
 transport=run(['wsl','-d','Ubuntu','--','/usr/bin/env','TREE2_CHECKM2_PILOT_LAUNCH_TOKEN='+nonce,'TREE2_QC_BATCH_PLAN='+root_plan,'TREE2_QC_BATCH_PLAN_SHA256='+b.digest(new_plan),'PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'actual_new_source_LF_and_env')
 b.exclusive(E/'new_split_source_input_preflight.json',{'status':'EXACT19_INPUT_MASKS_ANNOTATION_FOUR_DEBITS_NEW_SPLIT_SOURCE_AND_CURRENT_OWNERS_GATES_PASS','input_plan':b.row(R,new_plan),'source_manifest':fresh['source_manifest'],'actual_explicit_env_new_plan_and_LF_syntax':transport,'new_shell_exact_entry_name_redirect_only':True,'unchanged_zero_arg_boundary_actual_transport_proof':b.row(R,old_transport),'current_CLI':b.row(R,cli_path),'verified_current_roles':verified,'all_three_leases_reacquired_released_bytes_unchanged':True,'binary_saved_V003_exit_still_unknown':True,'new_sources_or_runtime_imports_not_executed':True,'no_runtime_image_mount_or_pickle_model_read':True})
 assert time.monotonic()-START<90;p.native_rss()
 result={'status':'CAMPAIGN_SPLIT_V2_CURRENT_EVENT_FILE_OS_SOURCE_INPUT_PREFLIGHT_PASS','native_owner':OWNER,'actual_native_exit':'PENDING_EXTERNAL_FOREGROUND_TOOL_EXIT','event_sha256':event_sha,'preflight_actual_exit':event['actual_exit_receipt'],'preflight_receipt':terminal['result'],'verified_current_roles':verified,'current_CLI_launch':b.row(R,cli_path),'previous_CLI_actual_exit':b.row(R,old_cli_exit),'runtime_plan':b.row(R,plan_path),'three_common_leases_reacquired_released':True,'Windows_image_anchor':anchor,'Linux':linux,'actual_children':CHILDREN,'no_science_model_pickle_mount_or_image_content':True,'actual_original_native_exit_code':2,'actual_WSL_exit_code':1,'actual_helper_exit_code':1,'annotation_unit_exit_code':0,'failed_DIAMOND_actual_exit_code':-15,'failure_kind':'TIMEOUT','observed_peak_summed_owned_RSS_bytes':1426886656,'historical_Windows_creation_observations':closed_creation_observations,'unchanged_RSS_ceiling_bytes':2147483648,'Linux_available_at_failure_bytes':failed['sampled_min_linux_available_bytes'],'resource_gate_enforced_not_waived':True,'failed_genome_quality_status':'UNKNOWN_NOT_A_NEGATIVE','saved_first_row_acceptance':b.row(R,R/'evidence/checkm2_phase_separated_P20/metadata_ABI_repair_runtime_v001/closed_success_audit_v001/Root_closed_method_acceptance.json'),'annotation_commit_reusable_after_Root_review':c.row(commit),'annotation_FAA':annotation['selected_faa'],'failed_DIAMOND_receipt':c.row(folder/'unit_diamond/execution.json'),'failed_search_partial':c.row(raw),'failed_pilot_search_cap_consumed':True,'all_failed_search_seconds':600.2386157629953+failed['elapsed_seconds'],'no_unchanged_retries_after_second_failure':True,'search_exec_prepared':c.row(folder/'search_receipts/search_exec_prepared.json'),'budget':budget,'snapshot_manifest':c.row(E/'snapshot_manifest.json'),'saved_binary_exit_code':'UNKNOWN_NO_SEPARATELY_RETAINED_BINARY_TERMINAL','composite_actual_exit_code':-15,'raw_TSV_not_reused_or_accepted_here':True,'new_production_admission_still_separate':True,'elapsed_seconds':time.monotonic()-START}
 b.exclusive(E/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)
if __name__=='__main__':main()
