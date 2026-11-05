"""One finite native, read-only Stage09 output validator; exact custody before work."""
from pathlib import Path
from ctypes import wintypes
import ctypes,json,os,sys,time,shutil
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import local_tree2_dispatcher as b
from checkm2_native_rss_guard_v001 import MemoryCounters


def main():
    plan=Path(sys.argv[1]);expected=sys.argv[2]
    assert os.name=='nt' and os.environ.get('COMPUTERNAME','').upper()=='WD'
    assert b.digest(plan)==expected;p=b.read(plan)
    assert p['schema']=='TREE2_DEFENCE_C003_READ_ONLY_QA_PLAN_V001' and Path(p['project_root'])==R
    assert p['native_RSS_limit_bytes']==134217728 and p['native_affinity_CPUs']==[2] and p['maximum_wall_seconds']==7200
    for row in p['sources']+p['bound_inputs']:b.bind(R,row)
    W=b.inside(R,p['work']);out=b.inside(R,p['output']);W.mkdir(exist_ok=True)
    kernel=b.Windows();owner=kernel.identity(ctypes.c_void_p(-1),os.getpid());started=time.monotonic();peak=0;last=0
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t]
    assert k.SetProcessAffinityMask(ctypes.c_void_p(-1),1<<2)
    ps=ctypes.WinDLL('psapi',use_last_error=True);ps.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(MemoryCounters),wintypes.DWORD];ps.GetProcessMemoryInfo.restype=wintypes.BOOL
    def guard():
        nonlocal peak
        if (R/p['stop_path']).exists() or (R/'state/STOP').exists():raise InterruptedError('Scoped file-validation STOP')
        if time.monotonic()-started>7200 or time.time()>p['absolute_deadline_unix']:raise TimeoutError('Finite file-QA budget/deadline reached')
        if shutil.disk_usage(R).free<42949672960:raise OSError('File-QA backing reserve below40GiB')
        c=MemoryCounters();c.cb=ctypes.sizeof(c)
        if not ps.GetProcessMemoryInfo(ctypes.c_void_p(-1),ctypes.byref(c),c.cb):raise ctypes.WinError(ctypes.get_last_error())
        peak=max(peak,c.rss)
        if c.rss>p['native_RSS_limit_bytes']:raise MemoryError('Read-only QA native RSS guard exceeded')
    def publish(detail,done=0,total=20,force=False,status='RUNNING'):
        nonlocal last
        guard()
        if not force and time.monotonic()-last<30:return
        row={'id':'10','name':'Independent defence output QC','status':status,'detail':detail,'scope':'SAVED_C003_STOCK_PHASES_RAW_EXITS_ORIGINAL_COORDINATES_AND_COMPLETE_MODEL_SCOPE_RULES','pid':owner['pid'],'creation_time_utc':owner['creation_time_utc'],'done':done,'total':total,'unit':'independently audited C003 paired genome rows; broader campaign incomplete','native_RSS_peak_bytes':peak,'elapsed_QC_wall_seconds':time.monotonic()-started,'C003_scientific_seconds_unchanged':p['C003_scientific_seconds_preserved'],'no_scientific_inference_or_model_replay':True,'full_panel_final_acceptance':False,'updated_utc':b.utc()}
        b.atomic(W/'progress.json',row)
        try:b.atomic(R/'state/stages/10.json',row)
        except OSError as exc:
            with (W/'optional_stage_display_errors.jsonl').open('a') as f:f.write(json.dumps({'error':str(exc),'at_utc':b.utc()})+'\n')
        last=time.monotonic()
    try:
        b.exclusive(W/'once_claim.json',{'plan':b.row(R,plan),'native_owner':owner,'file_only_no_science_replay':True,'no_automatic_retry':True,'at_utc':b.utc()})
        b.atomic(W/'native_owner.json',{'native_owner':owner,'input_plan_sha256':expected,'input_plan':b.row(R,plan),'at_utc':b.utc()})
        until=time.monotonic()+180
        while True:
            guard();ack_path=W/'Root_companion_ack.json';ack=b.read(ack_path) if ack_path.exists() else {}
            if ack.get('native_owner')==owner and ack.get('exact_handle_retained') is True and ack.get('input_plan_sha256')==expected and ack.get('current_state_namespace')=='state/local_continuation_v7':
                attached=b.read(b.bind(R,ack['current_namespace_ACK']))
                assert attached['event_sha256']==p['current_event_sha256'] and attached['exact_handle_retained'] is True
                assert all(attached['worker'][key]==owner[key] for key in owner)
                break
            if time.monotonic()>until:raise TimeoutError('Exact existing V007 retained custody ACK absent; no validation work started')
            time.sleep(.2)
        out.mkdir(parents=True,exist_ok=False)
        publish('Checking closed C003 inputs, raw exits, exact system scopes and immutable saved outputs',force=True)
        from defence_C001_file_QC_v001 import validate
        result=validate(R,p,out,guard,publish);guard()
        result.update(plan=b.row(R,plan),native_owner=owner,peak_native_RSS_bytes=peak,QC_wall_seconds=time.monotonic()-started,C003_scientific_seconds_unchanged=p['C003_scientific_seconds_preserved'],file_QA_absolute_deadline_unix=p['absolute_deadline_unix'],actual_native_exit='REQUIRES_EXTERNAL_RETAINED_HANDLE_EVENT',no_child_processes_or_private_Linux_namespace_created=True,at_utc=b.utc())
        b.exclusive(out/'COMMITTED.json',result)
        publish('C003 saved-output file QA passed; actual native exit and independent review required before closed ledger commit',20,20,True,'COMPUTED_QC_PASS_PENDING_EXTERNAL_NATIVE_EXIT_REVIEW')
        b.atomic(W/'native_file_QC_guard.json',{'peak_native_RSS_bytes':peak,'limit_bytes':134217728,'elapsed_wall_seconds':time.monotonic()-started,'budget_seconds':7200,'CPU_affinity':[2],'no_child_processes':True,'all_input_artifacts_read_only':True,'at_utc':b.utc()})
        print(json.dumps({'status':result['status'],'commit':b.row(R,out/'COMMITTED.json'),'native_exit_requires_retained_observer':True}),flush=True)
        return 0
    except BaseException as exc:
        failed={'error':repr(exc),'at_utc':b.utc(),'peak_native_RSS_bytes':peak,'elapsed_QC_wall_seconds':time.monotonic()-started,'scientific_outputs_unchanged':True,'failed_QC_is_not_biological_absence':True,'no_automatic_retry':True}
        b.atomic(W/'failure.json',failed)
        # A terminal display row is advisory; it never substitutes for retained exit.
        try:b.atomic(R/'state/stages/10.json',{'id':'10','name':'Independent defence output QC','status':'QC_VALIDATOR_FAILED_PENDING_EXACT_EXIT_REVIEW','detail':str(exc),'worker':owner,'failure':b.row(R,W/'failure.json'),'full_panel_final_acceptance':False,'updated_utc':b.utc()})
        except OSError:pass
        raise


if __name__=='__main__':raise SystemExit(main())
