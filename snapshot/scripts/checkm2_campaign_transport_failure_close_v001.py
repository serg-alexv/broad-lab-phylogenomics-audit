"""Current-event file/OS proof for an exact pre-entry guard failure; no science."""
from pathlib import Path
import ctypes,datetime,json,math,msvcrt,os,shutil,subprocess,time
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as prep

R=Path(__file__).resolve().parents[1]
OLD=R/'evidence/checkm2_campaign_index8_v001/P20_production19_v002'
E=OLD/'transport_failure_closure_v001'
EV=R/'state/local_continuation_queue_v1/events/44a75ff9e314011adc8be59e71e1562c38ea42609c28350f37e7bf30ae9a219a/event.json'
SHA='554037fd1b1c153d56fc8c104b7a153e1b71543759f36b71fcb5ef3d9246244e'
K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());CHILDREN=[]

def run(argv,role):
    child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    row={'role':role,'identity':K.identity(int(child._handle),child.pid)};CHILDREN.append(row)
    try:out,err=child.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        b.exclusive(E/'UNRESOLVED_CHILD.json',row);raise
    row.update(actual_exit_code=child.returncode,actual_handle_reaped=True,stderr=err)
    b.exclusive(E/(role+'_exit.json'),row)
    assert child.returncode==0,(role,err)
    return json.loads(out)

def observe_closed(expected):
    handle=K.k.OpenProcess(0x00100000|0x1000,False,expected['pid'])
    if not handle:
        error=ctypes.WinError(ctypes.get_last_error())
        if getattr(error,'winerror',None)!=87:raise error
        return {'identity':expected,'observation':'NO_CURRENT_NUMERIC_PID','historical_exit_inferred':False}
    try:
        now=K.identity(handle,expected['pid'])
        if now['windows_creation_filetime_100ns']==expected['windows_creation_filetime_100ns']:
            assert now['creation_time_utc']==expected['creation_time_utc'] and K.wait(handle,0)
            return {'identity':expected,'observation':'EXACT_CREATION_HANDLE_SIGNALED','historical_exit_inferred':False}
        return {'identity':expected,'observation':'PID_REUSED_DIFFERENT_CREATION','replacement':now,'replacement_not_signalled':True,'historical_exit_inferred':False}
    finally:K.close(handle)

def main():
    started=time.monotonic();E.mkdir(exist_ok=False);affinity=prep.affinity(K)
    b.exclusive(E/'launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'finite_foreground_seconds':90,'affinity_mask':affinity,'no_science':True})
    assert b.digest(EV)==SHA;event=b.read(EV);actual=b.read(b.bind(R,event['actual_exit_receipt']));detached=b.read(b.bind(R,event['launch_receipt']))
    assert event['actual_exit_code']==actual['actual_exit_code']==2 and event['retained_handle_identity_verified']is True and actual['exact_birth_handle_retained']is True and detached['native_owner']==event['worker_identity']
    execution=b.read(OLD/'execution_pending_owner_exit.json');launch=b.read(OLD/'native_scientific_launch.json')
    assert launch['native_owner']==event['worker_identity']==execution['native_owner'] and execution['wsl_child_closed_observed']is True and execution['wsl_child_exit_code']==4 and execution['wsl_child_identity']==launch['wsl_child']
    assert execution['run_directory']is None and execution['namespace_envelope']is None and execution['host_registry_unchanged']is True and execution['biological_STOP_unchanged']is True
    plan=b.read(R/'metadata/checkm2_campaign_index8_v001/P20_production19_v002/input_plan.json')
    for ref in b.read(b.bind(R,plan['source_manifest']))['sources']:b.bind(R,ref)
    shell=R/'scripts/checkm2_campaign_index8_v001.sh';wrapper=R/'scripts/checkm2_private_setup_ns.sh'
    assert b.digest(wrapper)=='0dce7c1d87e3f417e76c5d800a6ea8282d3cada8cf1ffbd31bad8ffb39c98f5a'
    assert 'exec /bin/bash "$SCRIPT"\n' in wrapper.read_text() and 'exec /bin/bash "$SCRIPT" "$@"'not in wrapper.read_text()
    raw=shell.read_bytes();guard=b'[[ "$#" == 4';entry=b'exec /usr/bin/python3 -B '
    assert raw.index(guard)<raw.index(entry) and b'Exact cohort plan arguments required' in raw
    assert (OLD/'namespace_stderr.txt').read_text().strip()=='Exact cohort plan arguments required'
    assert (OLD/'owner.stderr.txt').read_bytes()==b''
    mapping=json.loads((OLD/'namespace_stdout.txt').read_text());assert mapping['status']=='PASS_PRIVATE_MOUNT_MAPPING' and mapping['root_and_C_read_only_project_and_private_registry_writable']is True
    output=R/'analysis/checkm2_campaign_index8_v001/P20_production19_v002'
    assert not output.exists() and not (OLD/'namespace_runs').exists() and not (OLD/'step.json').exists()
    unresolved=b.read(OLD/'unresolved_ownership_handoff.json');b.bind(R,{'path':str(Path(unresolved['immutable_handoff_path']).relative_to(R)),'sha256':unresolved['immutable_handoff_sha256']})
    pointer=b.read(R/'state/local_continuation_current_runtime.json');roles=b.read(b.bind(R,pointer['actual_runtime_roles']))
    assert pointer['state_directory']=='state/local_continuation_queue_v1'
    dispatcher=b.read(b.bind(R,pointer['dispatcher_launch']));supervisor=b.read(b.bind(R,pointer['detached_supervisor_launch']))
    for key in ('config','Root_operational_admission','dispatcher_source','supervisor_source'):b.bind(R,pointer[key])
    ids={x['role']:x['identity']for x in roles['roles']}
    assert dispatcher['dispatcher_owner']==ids['ROOT_LOCAL_RUNTIME_CONTROLLER'] and dispatcher['supervisor_owner']==supervisor['native_owner']==ids['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']
    assert dispatcher['core_source']==pointer['dispatcher_source'] and supervisor['entry_source']==pointer['supervisor_source']
    monitor=b.read(R/'state/monitor_current_roles.json');live=[{**monitor[x],'role':x}for x in ('gui','collector','publisher')]
    for item in roles['roles']:
        b.bind(R,item['source']);live.append({**item['identity'],'role':item['role'],'script':item['source']['path'],'script_sha256':item['source']['sha256']})
    cli=b.read(EV.parent/'cli_started.json');assert cli['event_sha256']==SHA
    live.append({**cli['identity'],'role':'CURRENT_EVENT_CLI','script':'codex.exe'})
    command="$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @("+','.join(str(x['pid'])for x in live)+") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe','codex.exe'))} | Select-Object @{N='pid';E={$_.ProcessId}},@{N='parent_pid';E={$_.ParentProcessId}},@{N='command';E={$_.CommandLine}})|ConvertTo-Json -Compress"
    census=run(['pwsh','-NoProfile','-Command',command],'Windows_current_census');census=census if isinstance(census,list)else[census];verified=[]
    for item in live:
        handle=K.open_worker(item)
        try:assert not K.wait(handle,0);identity=K.identity(handle,item['pid'])
        finally:K.close(handle)
        row=next(x for x in census if x['pid']==item['pid']);assert str(R)in row['command'] and Path(item['script']).name in row['command']
        if 'script_sha256'in item:assert b.digest(R/item['script'])==item['script_sha256']
        if item['role']=='CURRENT_EVENT_CLI':assert row['parent_pid']==ids['ROOT_LOCAL_RUNTIME_CONTROLLER']['pid'] and str(EV.parent)in row['command'] and '--disable plugins'in row['command']
        if item['role']=='ROOT_LOCAL_RUNTIME_CONTROLLER':assert row['parent_pid']==ids['ROOT_EXTERNAL_DISPATCHER_SUPERVISOR']['pid']
        verified.append({'role':item['role'],'identity':identity,'source_launch_and_ancestry_verified':True})
    allowed={x['pid']for x in live}|{OWNER['pid']}|{x['identity']['pid']for x in CHILDREN}
    assert not [x for x in census if x['pid']not in allowed]
    native_closed=[observe_closed(x)for x in (launch['native_owner'],launch['wsl_child'])]
    prior=R/'evidence/checkm2_phase_separated_P20/resource_repair_v002/failure_closure_v001'
    targets=b.read(prior/'historical_targets.json');targets['namespace_targets'] += [['mnt',mapping['mount_namespace']],['net',mapping['network_namespace']]]
    b.exclusive(E/'historical_targets.json',targets)
    locks=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,p)for p in locks];held=[]
    try:
        for name in locks:
            f=name.open('r+b');f.seek(0)
            try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except BaseException:f.close();raise
            held.append(f)
        root='/mnt/c/'+str(R)[3:].replace('\\','/');targetpath=root+'/'+(E/'historical_targets.json').relative_to(R).as_posix()
        observer=R/'work/checkm2_N5_actual_prelaunch_linux.py';observer_ref=b.read(R/'evidence/checkm2_phase_separated_P20/metadata_ABI_repair_runtime_v001/preflight_v001/Root_preflight_admission.json')['linux_observer_source'];b.bind(R,observer_ref)
        code=observer.read_text().replace('__ROOT__',repr(root)).replace('__IDS__',"json.loads(Path("+repr(targetpath)+").read_text())['Linux']").replace('__NS__',"json.loads(Path("+repr(targetpath)+").read_text())['namespace_targets']")
        linux=run(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',code],'Linux_OS_closure')
        assert linux['same_boot_as_original_targets']is True and not any(linux[x]for x in ('same_old_identities','old_groups','old_namespace_tasks','image_loop_associations','other_project_workers','other_scientific_workers'))
        assert linux['compute_lease_reacquired_released_bytes_unchanged']is True and linux['host_registry']==b.read(R/'evidence/checkm2_runtime/install_registry_before.json')
        old_linux=b.read(prior/'receipt.json')['Linux'];assert linux['image_before']==linux['image_after']==old_linux['image_after']
        assert linux['linux_available_bytes']>=1024**3 and len(linux['observer_affinity'])<=2
    finally:
        for f in reversed(held):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
    assert before==[b.row(R,p)for p in locks]
    stat=(R/'tools/checkm2_runtime_ext4.img').stat();anchor={k:getattr(stat,k)for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_nlink')}
    assert anchor==b.read(OLD/'preflight_v001/receipt.json')['Windows_image_anchor'] and shutil.disk_usage(R).free>=40*1024**3
    snapshot=[]
    for source in [x for x in OLD.rglob('*')if x.is_file()and not x.is_relative_to(E)]+[shell,wrapper]:
        dest=E/'snapshot'/source.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);assert b.digest(dest)==b.digest(source);snapshot.append({'original':b.row(R,source),'snapshot':b.row(R,dest)})
    b.exclusive(E/'snapshot_manifest.json',{'files':snapshot,'all_preentry_attempt_and_unresolved_reports_preserved':True})
    birth=datetime.datetime.fromisoformat(launch['native_owner']['creation_time_utc']);observed=datetime.datetime.fromisoformat(actual['observed_utc']);cold=math.ceil((observed-birth).total_seconds());assert cold==11
    assert time.monotonic()-started<90;prep.native_rss()
    value={'status':'CAMPAIGN_EXACT_PRE_ENTRY_TRANSPORT_FAILURE_EXTERNALLY_CLOSED','event_sha256':SHA,'native_owner':OWNER,'external_audit_actual_exit':'PENDING_FOREGROUND_TOOL_EXIT','actual_native_exit_code':2,'actual_WSL_exit_code':4,'actual_native_exit':event['actual_exit_receipt'],'native_closed_observations':native_closed,'verified_current_roles':verified,'current_CLI_launch':b.row(R,EV.parent/'cli_started.json'),'pinned_old_sources':plan['source_manifest'],'wrapper_source':b.row(R,wrapper),'mapping_evidence':b.row(R,OLD/'namespace_stdout.txt'),'guard_stderr':b.row(R,OLD/'namespace_stderr.txt'),'old_unresolved_report':b.row(R,OLD/'unresolved_ownership_handoff.json'),'old_unresolved_report_newly_resolved_for_exact_token':launch['token'],'scientific_units_groups_runtime_image_models_and_IPC':'NOT_STARTED_PROVEN_PRE_ENTRY_ARGUMENT_GUARD','new_scientific_debit_seconds':0,'no_scientific_run_or_once_claim_created':True,'private_setup_namespaces_absent_by_boot_qualified_census':True,'Linux':linux,'three_common_leases_reacquired_released_bytes_unchanged':True,'Windows_image_anchor':anchor,'image_never_opened_or_mounted_by_this_attempt':True,'prior_closed_runtime_image_hash_authority':b.row(R,prior/'Root_closed_known_timeout.json'),'known_native_recorded_wall_seconds':(datetime.datetime.fromisoformat(execution['ended_utc'])-datetime.datetime.fromisoformat(execution['started_utc'])).total_seconds(),'conservative_cold_actual_upper_charge_seconds':cold,'carried_cold_remaining_seconds':38400-cold,'old_claims_and_caps_unchanged':True,'snapshot_manifest':b.row(R,E/'snapshot_manifest.json'),'actual_children':CHILDREN,'new_attempt_or_science_admitted_here':False,'elapsed_seconds':time.monotonic()-started}
    b.exclusive(E/'receipt.json',value);print(json.dumps({'status':value['status'],'receipt':b.row(R,E/'receipt.json'),'owner':OWNER}),flush=True)

if __name__=='__main__':main()
