"""HELD non-genomic S1R2 permission observer proof; explicit Root admission required."""
from pathlib import Path
import argparse,ast,datetime,hashlib,io,json,os,re,shutil,subprocess,sys,time,types,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
CAP=2147483648;HEADROOM=1073741824;RESERVE=42949672960

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with tmp.open('x',encoding='utf-8',newline='\n') as handle:json.dump(value,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    os.replace(tmp,path)
def inside(value):
    value=(ROOT/Path(value)).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    if not value.is_relative_to(ROOT):raise RuntimeError('Proof path escapes project')
    return value
def preflight(args):
    if os.name!='posix' or not re.fullmatch('[a-f0-9]{32}',args.token):raise RuntimeError('Explicit Linux proof owner required')
    plan_path=inside(args.source_plan)
    if sha(plan_path)!=args.source_plan_sha256:raise RuntimeError('Proof source plan changed')
    plan=read(plan_path)
    for item in plan['sources']:
        path=inside(item['path'])
        if sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:raise RuntimeError('Proof source mismatch: '+str(path))
    admission=read(inside(args.admission))
    if (admission.get('schema')!='TREE2_S1R2_OBSERVER_PROOF_ADMISSION_V001' or admission.get('status')!='ADMITTED_ONE_NON_GENOMIC_PERMISSION_OBSERVER_PROOF' or admission.get('non_genomic_proof_execution_authorized') is not True or admission.get('source_plan_sha256')!=args.source_plan_sha256 or admission.get('token')!=args.token):raise RuntimeError('No exact Root proof admission')
    folder=ROOT/'evidence/checkm2_S1R2_observer_proof'/args.token
    if inside(args.run_directory)!=folder:raise RuntimeError('Proof output binding differs')
    cpus=sorted(os.sched_getaffinity(0))[:2]
    if not cpus:raise RuntimeError('No available proof CPU')
    os.sched_setaffinity(0,set(cpus))
    return plan,folder,cpus
def available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
def proc(pid):
    fields=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'parent_pid':int(fields[1]),'process_group':int(fields[2]),'creation_ticks':int(fields[19]),'state':fields[0],'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def group(pgid):
    rows=[]
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():continue
        try:value=proc(int(item.name))
        except (FileNotFoundError,ProcessLookupError):continue
        if value['process_group']==pgid:rows.append(value)
    return rows
def resource_gate(folder,extra_rows=()):
    if available()<HEADROOM or shutil.disk_usage(folder).free<RESERVE:raise RuntimeError('Proof headroom/reserve gate')
    own=group(os.getpgrp());ids={row['pid']:row for row in [*own,*extra_rows]}
    if sum(row['rss_bytes'] for row in ids.values())>CAP:raise RuntimeError('Proof summed RSS gate')
    return {'summed_RSS_bytes':sum(row['rss_bytes'] for row in ids.values()),'linux_available_bytes':available()}

def publication_ast_checks(folder):
    # Execute only the actual display functions with fake paths/writes, never whole OPS modules.
    from checkm2_optional_progress_S1R2 import safe_call
    events=[]
    def denied(path,value):events.append({'path':str(path),'value':dict(value)});raise PermissionError(13,'INJECTED_OPTIONAL_DISPLAY_WRITE',str(path))
    native_path=ROOT/'scripts/checkm2_single_faa_native_S1R2.py'
    selected=[node for node in ast.parse(native_path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name in ('committed_done','record_display_error','progress')]
    if len(selected)!=3:raise RuntimeError('Native display function boundary changed')
    ns={'safe_call':safe_call,'json':json,'sys':types.SimpleNamespace(stderr=io.StringIO()),'base':types.SimpleNamespace(OWNER={'pid':123,'creation_time_utc':'DUMMY_CREATION_ONLY'},utc=utc),'R':folder/'mock_native','c':types.SimpleNamespace(STATE=folder/'mock_native/STATE.json',E=folder,save=denied),'START':utc(),'COMMAND':'PROOF_MOCK_ONLY','TOKEN':'PROOF_MOCK_ONLY','COMMITTED_DONE':0,'TELEMETRY_UNAVAILABLE':False,'TELEMETRY_BAD_FIELDS':[],'DISPLAY_WRITE_UNAVAILABLE':False,'DISPLAY_WRITE_ERRORS':{'count':0},'TELEMETRY_ERRORS':{'count':0}}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(native_path),'exec'),ns)
    ns['committed_done'](1);ns['progress']('RUNNING','dummy optional publication')
    if ns['DISPLAY_WRITE_ERRORS']['count']!=2 or ns['DISPLAY_WRITE_UNAVAILABLE'] is not True or ns['COMMITTED_DONE']!=1:raise RuntimeError('Native optional display failure escaped or counter changed')
    ns['progress']('RUNNING','dummy continuing owner')
    if 'stale/unavailable' not in events[-1]['value']['detail']:raise RuntimeError('Native failed-display stale label absent')
    entry_path=ROOT/'scripts/checkm2_single_faa_entry_S1R2.py'
    selected=[node for node in ast.parse(entry_path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name in ('record_display_error','save_display')]
    ens={'safe_call':safe_call,'save':denied,'STATE':folder/'mock_entry/STEP.json','CONTEXT':{},'sys':types.SimpleNamespace(stderr=io.StringIO()),'json':json}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(entry_path),'exec'),ens);ens['save_display']({'done':1})
    if ens['CONTEXT']['display_write_errors']['count']!=1 or ens['CONTEXT']['display_write_unavailable'] is not True:raise RuntimeError('Entry optional display boundary failed')
    return {'status':'MOCKED_ACTUAL_DISPLAY_FUNCTION_AST_PASS','native_source_sha256':sha(native_path),'entry_source_sha256':sha(entry_path),'all_paths_mocked_no_standard04_write':True,'native_error_count':ns['DISPLAY_WRITE_ERRORS']['count'],'entry_error_count':1,'scope':'DISPLAY_FUNCTIONS_ONLY_NOT_NATIVE_COLD_LIFECYCLE'}

def cases(args):
    plan,folder,cpus=preflight(args)
    from checkm2_unit_observer_S1R2 import run_unit,UnitFailure
    from checkm2_optional_telemetry_v001 import structured_exception
    rows=[];dummy_stop=folder/'OWNED_PROOF_STOP';peak=0;minimum=None
    for mode in ('optional_permission','required_permission'):
        calls=0;injected=False;child_pgid=None
        def observe(pgid):
            nonlocal calls,injected,child_pgid
            child_pgid=pgid;calls+=1
            if mode=='required_permission' and calls==2:
                injected=True
                raise PermissionError(13,'INJECTED_REQUIRED_GROUP_OBSERVATION',f'/proc/{pgid}/injected_required_observation')
            return group(pgid)
        def stop_gate():
            nonlocal peak,minimum
            if dummy_stop.exists():raise InterruptedError('Proof-owned STOP')
            sample=resource_gate(folder,group(child_pgid) if child_pgid else ())
            peak=max(peak,sample['summed_RSS_bytes']);minimum=sample['linux_available_bytes'] if minimum is None else min(minimum,sample['linux_available_bytes'])
        def display(*unused,**kwargs):
            if mode=='optional_permission':raise PermissionError(13,'INJECTED_OPTIONAL_PROGRESS_WRITE',str(folder/'MOCK_OPTIONAL_STEP.json'))
        hooks={'save':save,'stop_gate':stop_gate,'stat':proc,'group':observe,'mem_available':available,'progress':display}
        command=[sys.executable,'-B','-c','import time;time.sleep('+('0.8' if mode=='optional_permission' else '10')+')']
        try:
            receipt=run_unit(mode,command,os.environ.copy(),folder,6,hooks=hooks)
            if mode!='optional_permission':raise AssertionError('Required observer PermissionError became success')
        except UnitFailure as error:
            receipt=error.receipt
            if mode!='required_permission':raise
        if mode=='optional_permission':
            if receipt['status']!='UNIT_EXIT0_GROUP_CLOSED' or type(receipt['exit_code']) is not int or receipt['exit_code']!=0 or receipt['owned_group_empty'] is not True or receipt['optional_progress_error_count']<1 or receipt['optional_progress_errors_first16'][0].get('errno')!=13:raise AssertionError('Optional failure did not preserve actual0/closed child')
        else:
            original=receipt.get('error_details') or {}
            if not injected or receipt['status']=='UNIT_EXIT0_GROUP_CLOSED' or receipt['exit_code']!=-15 or receipt['owned_group_empty'] is not True or original.get('errno')!=13 or original.get('last_operation')!='required_owned_group_RSS' or not original.get('filename') or not original.get('traceback'):raise AssertionError('Required failure lost original operation/errno or actual child closure')
        rows.append({'arm':mode,'receipt':receipt})
    result={'status':'S1R2_INJECTED_OBSERVER_BOUNDARY_PASS_NOT_HISTORICAL_CAUSE_PROOF','at_utc':utc(),'owner_identity':proc(os.getpid()),'arms':rows,'publication_AST_checks':publication_ast_checks(folder),'cpu_affinity':cpus,'sampled_peak_protocol_group_RSS_bytes':peak,'sampled_min_linux_available_bytes':minimum,'source_plan_sha256':args.source_plan_sha256,'no_genomes_models_mounts_or_image_reads':True,'existing_wrong_identity_sentinel_test_repeated':False,'limitations':['Deterministic injections do not identify the old PermissionError operation.','Display AST fixtures do not execute native cold lifecycle.','No CheckM2/scientific module, genome, model, runtime mount or source58 mutation.']}
    save(folder/'cases_result.json',result)
    return 0

def supervise(args):
    plan,folder,cpus=preflight(args)
    import fcntl
    from checkm2_optional_telemetry_v001 import structured_exception
    import checkm2_owned_cleanup_T1 as ownership
    folder.mkdir(parents=True,exist_ok=True)
    child=None;root_identity=None;known={};cleanup=None;error=None;started=time.monotonic();peak=0;minimum=None
    lock=(ROOT/'state/checkm2_pilot.lock').open('r+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--mode','cases','--source-plan',args.source_plan,'--source-plan-sha256',args.source_plan_sha256,'--admission',args.admission,'--run-directory',str(folder),'--token',args.token]
        with (folder/'cases_stdout.txt').open('w') as out,(folder/'cases_stderr.txt').open('w') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
            root_identity=ownership.identity(child.pid)
            if root_identity is None:raise RuntimeError('Proof worker creation identity unavailable')
            known[child.pid]=root_identity
            while child.poll() is None:
                ownership.track_descendants(root_identity,known)
                captured=[]
                for expected in known.values():
                    current=ownership.current_matching(expected)
                    if current is not None:captured.append(proc(current['pid']))
                sample=resource_gate(folder,captured);peak=max(peak,sample['summed_RSS_bytes']);minimum=sample['linux_available_bytes'] if minimum is None else min(minimum,sample['linux_available_bytes'])
                if time.monotonic()-started>8:raise TimeoutError('Proof worker8s; exact874 finite cleanup follows')
                time.sleep(.1)
            if child.returncode!=0:raise RuntimeError('Proof cases actual exit '+str(child.returncode))
    except BaseException as exception:error=structured_exception(exception,'required proof supervision')
    finally:
        if child is not None:
            try:cleanup=ownership.cleanup_linux_helper(child,root_identity,known,folder/'OWNED_PROOF_STOP',args.token)
            except BaseException as exception:cleanup={'closure_proven':False,'exception':structured_exception(exception,'exact874 proof child cleanup')}
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    success=error is None and cleanup and cleanup.get('closure_proven') is True and cleanup.get('forced_action') is False and child.returncode==0
    if success:
        try:
            cases_result=read(folder/'cases_result.json')
            success=cases_result['status']=='S1R2_INJECTED_OBSERVER_BOUNDARY_PASS_NOT_HISTORICAL_CAUSE_PROOF'
        except BaseException as exception:error=structured_exception(exception,'required cases result');success=False;cases_result=None
    else:cases_result=None
    result={'status':'S1R2_NON_GENOMIC_PROOF_PASS_CLOSED' if success else 'FAILED_OR_UNKNOWN_NO_AUTOMATIC_RELAUNCH','started_utc':utc(),'elapsed_seconds':time.monotonic()-started,'supervisor_identity':proc(os.getpid()),'actual_cases_exit_code':child.returncode if child is not None else None,'cases_result_sha256':sha(folder/'cases_result.json') if (folder/'cases_result.json').exists() else None,'error':error,'owned_cleanup':cleanup,'sampled_peak_protocol_group_RSS_bytes':peak,'sampled_min_linux_available_bytes':minimum,'source_plan_sha256':args.source_plan_sha256,'no_genomes_models_mounts_or_image_reads':True}
    save(folder/'linux_result.json',result)
    if not success:ownership.immutable_handoff(folder,folder/'UNRESOLVED_PROOF_OWNER.json',args.token,'non_genomic_proof',result)
    return 0 if success else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('supervise','cases'),required=True)
    for name in ('source-plan','source-plan-sha256','admission','run-directory','token'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();raise SystemExit(supervise(args) if args.mode=='supervise' else cases(args))
