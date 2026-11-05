"""One finite metadata-publication boundary; no dispatch, subprocess or science."""
from pathlib import Path
import argparse,ctypes,json,os,re,shutil,sys,time
from ctypes import wintypes
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as prep

R=Path(__file__).resolve().parents[1]

def refs(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str)and isinstance(value.get('sha256'),str):yield value
        for item in value.values():yield from refs(item)
    elif isinstance(value,list):
        for item in value:yield from refs(item)

def candidates():
    out=list((R/'metadata').glob('checkm2_campaign_index8*.json'))
    for folder in (R/'metadata').glob('checkm2_campaign_index8*'):
        if folder.is_dir():out.extend(folder.glob('*.json'))
    return sorted(set(out))

def inspect(candidate):
    if candidate.stat().st_size>2*1024*1024:return None
    value=b.read(candidate);status=str(value.get('status','')).upper()
    if not any(x in status for x in ('FROZEN','SOURCE_READY','GO_SOURCE','REVIEW_PASS'))or any(x in status for x in ('FAIL','UNKNOWN','BLOCK')):return None
    found={};visited=set()
    def collect(body,depth=0):
        for ref in refs(body):
            path=ref['path'].replace('\\','/')
            if path.startswith('scripts/checkm2_campaign'):
                target=b.bind(R,ref)
                if target.stat().st_size>2*1024*1024:raise ValueError('Unexpected source size')
                found[path]=b.row(R,target)
            elif depth<2 and path.endswith('.json')and path not in visited and path.startswith(('metadata/checkm2_campaign','evidence/checkm2_campaign'))and any(word in Path(path).name for word in ('source','manifest','delivery')):
                visited.add(path);target=b.bind(R,ref)
                if target.stat().st_size<=2*1024*1024:collect(b.read(target),depth+1)
    collect(value)
    roles=set()
    for path in found:
        m=re.fullmatch(r'scripts/checkm2_campaign_index8_(common|inner|observer)_v([0-9]{3})\.py',path)
        if m and int(m[2])>=2:roles.add(m[1])
    if roles!={'common','inner','observer'}:return None
    return {'publication':b.row(R,candidate),'publication_status':value['status'],'source_bindings':[found[k]for k in sorted(found)],'publication_is_not_Root_scientific_admission':True}

def published():
    for candidate in candidates():
        try:
            result=inspect(candidate)
            if result:return result
        except (OSError,ValueError,KeyError,RuntimeError):continue
    return None

def main(a):
    admission_path=b.bind(R,{'path':a.admission,'sha256':a.admission_sha256});grant=b.read(admission_path)
    assert grant['status']=='ROOT_ADMITTED_ONE_METADATA_PUBLICATION_BOUNDARY' and grant['source']==b.row(R,Path(__file__))and grant['maximum_wall_seconds']==1800
    pointer=b.read(R/'state/local_continuation_current_runtime.json');state=b.inside(R,pointer['state_directory']);assert state.relative_to(R).as_posix()==grant['runtime_state_directory']
    e=b.inside(R,grant['evidence_directory']);e.mkdir(parents=True,exist_ok=True);event_sha=grant['event_sha256']
    k=b.Windows();owner=k.identity(ctypes.c_void_p(-1),os.getpid());affinity=prep.affinity(k);started=time.monotonic();birth=b.utc();found=None;error=None;ack_ok=False;last=-30;notify=None
    b.exclusive(e/'owner_started.json',{'native_owner':owner,'source':grant['source'],'admission':b.row(R,admission_path),'at_utc':birth,'affinity_mask':affinity,'maximum_wall_seconds':1800,'scientific_execution_authorized':False})
    def progress(detail):
        prep.native_rss();assert shutil.disk_usage(R).free>=40*1024**3
        row={'id':'04','name':'Independent biological QC','status':'PREPARING','operation':'PREPARATION','detail':detail,'done':0,'total':19,'unit':'reserved inputs awaiting repaired source admission','started_utc':birth,'updated_utc':b.utc(),**owner,'full_command_line':sys.executable+' '+str(Path(__file__).resolve()),'log_path':str(e/'progress.json'),'campaign_accepted_method_estimates':15,'campaign_source_supported_total':919,'campaign_pending_method_estimates':904,'production_panel_acceptance':False,'scientific_units_running':False}
        b.atomic(e/'progress.json',row);b.atomic(R/'state/stages/04.json',row)
    try:
        while time.monotonic()-started<180:
            if (R/'state/STOP').exists():raise InterruptedError('Global STOP')
            try:
                ack=b.read(state/'early_attach_ack.json');worker=ack.get('worker',{})
                ack_ok=(ack.get('event_sha256')==event_sha and ack.get('status')=='WAITING_WORKER'and ack.get('exact_handle_retained')is True and all(worker.get(key)==owner[key]for key in ('pid','creation_time_utc','windows_creation_filetime_100ns')))
            except (OSError,ValueError):ack_ok=False
            if ack_ok:break
            time.sleep(.2)
        if not ack_ok:raise TimeoutError('Exact current-event dispatcher retained-handle ACK absent after180seconds')
        kernel=k.k;kernel.FindFirstChangeNotificationW.argtypes=[wintypes.LPCWSTR,wintypes.BOOL,wintypes.DWORD];kernel.FindFirstChangeNotificationW.restype=wintypes.HANDLE
        kernel.FindNextChangeNotification.argtypes=[wintypes.HANDLE];kernel.FindNextChangeNotification.restype=wintypes.BOOL
        kernel.FindCloseChangeNotification.argtypes=[wintypes.HANDLE];kernel.FindCloseChangeNotification.restype=wintypes.BOOL
        notify=kernel.FindFirstChangeNotificationW(str(R/'metadata'),True,0x1|0x8|0x10)
        if not notify or notify==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        while time.monotonic()-started<1800:
            if (R/'state/STOP').exists():raise InterruptedError('Global STOP')
            found=published()
            if found:
                time.sleep(.2)
                if published()==found:break
                found=None
            if time.monotonic()-last>=30:
                progress('V003 composite timeout fully closed; waiting for the team final V2 binary-search/file-validation source contract. No scientific unit runs; saved binary exit remains UNKNOWN.');last=time.monotonic()
            ms=max(1,min(30000,int((1800-(time.monotonic()-started))*1000)))
            if k.wait(notify,ms)and not kernel.FindNextChangeNotification(notify):raise ctypes.WinError(ctypes.get_last_error())
        if found is None:raise TimeoutError('Finite1800second final-source publication boundary expired; no automatic repeat')
    except BaseException as ex:error={'type':type(ex).__name__,'error':str(ex)}
    finally:
        if notify and notify!=ctypes.c_void_p(-1).value:
            if not k.k.FindCloseChangeNotification(notify):error={'type':'NotificationClosureError','previous':error,'winerror':ctypes.get_last_error()}
    code=0 if found and error is None else 3
    terminal={'status':'TEAM_V2_SOURCE_PUBLICATION_BOUNDARY_REACHED_PENDING_ROOT_REVIEW'if code==0 else'METADATA_PUBLICATION_BOUNDARY_FAILED_NO_AUTOMATIC_RETRY','native_owner':owner,'actual_native_exit':'PENDING_EXTERNAL_RETAINED_HANDLE','intended_exit_code':code,'publication':found,'error':error,'current_event_sha256':event_sha,'exact_ACK_observed':ack_ok,'elapsed_seconds':time.monotonic()-started,'OS_metadata_change_notification_no_model_polling':True,'no_subprocess_science_runtime_image_genome_or_pickle_read':True,'scientific_execution_authorized':False,'at_utc':b.utc()}
    b.exclusive(e/'result_pending_actual_exit.json',terminal)
    b.atomic(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC','status':'WAITING_AT_GATE','operation':'PREPARATION','detail':terminal['status'],'done':0,'total':19,'unit':'reserved inputs','updated_utc':b.utc(),'ended_utc':b.utc(),'log_path':str(e/'result_pending_actual_exit.json'),'terminal_receipt':b.row(R,e/'result_pending_actual_exit.json'),'production_panel_acceptance':False})
    return code

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True);raise SystemExit(main(p.parse_args()))
