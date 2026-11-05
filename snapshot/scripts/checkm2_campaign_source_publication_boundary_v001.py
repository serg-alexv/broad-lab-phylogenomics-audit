"""Bounded metadata publication observer. No dispatcher, science, subprocess or retry."""
from pathlib import Path
import ctypes,json,os,sys,time
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as p

R=Path(__file__).resolve().parents[1]
E=R/'evidence/checkm2_campaign_index8_v001/source_publication_boundary_v001'
EVENT='9a83d802d5ee9726d7bf879598abdb9fbaaacc4ec1cf72280429b9b0ab699c09'
STATE=R/'state/local_continuation_queue_v1'
REQUIRED={'scripts/checkm2_campaign_index8_common_v001.py','scripts/checkm2_campaign_index8_inner_v001.py','scripts/prepare_checkm2_campaign_index8_cohort_v001.py'}

def candidates():
    return sorted(set((R/'metadata').glob('checkm2_campaign_index8*.json'))|set((R/'metadata/checkm2_campaign_index8_v001').glob('*.json')))

def references(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
            yield value
        for v in value.values():yield from references(v)
    elif isinstance(value,list):
        for v in value:yield from references(v)

def published():
    for candidate in candidates():
        if candidate.stat().st_size>2*1024*1024:continue
        try:
            value=b.read(candidate)
            refs={v['path']:v for v in references(value) if v['path'].startswith(('scripts/','docs/'))}
            if not REQUIRED.issubset(refs):continue
            bound=[]
            for ref in refs.values():
                target=b.bind(R,ref)
                if target.stat().st_size>2*1024*1024:raise RuntimeError('Unexpected large source artifact')
                bound.append(b.row(R,target))
            return {'publication':b.row(R,candidate),'source_bindings':bound,'publication_status':value.get('status'),'acceptance_or_science_authorized':False}
        except (OSError,ValueError,KeyError,RuntimeError):continue
    return None

def main():
    started=time.monotonic();k=b.Windows();owner=k.identity(ctypes.c_void_p(-1),os.getpid());p.affinity(k)
    grant=b.read(E/'Root_observer_admission.json')
    if grant['source']!=b.row(R,Path(__file__)) or grant['event_sha256']!=EVENT or grant['maximum_wall_seconds']!=900:raise RuntimeError('Observer admission differs')
    b.exclusive(E/'owner_started.json',{'native_owner':owner,'at_utc':b.utc(),'source':grant['source'],'maximum_wall_seconds':900,'scientific_execution_authorized':False})
    status='UNKNOWN';found=None;error=None;acknowledged=False;last=0
    try:
        while time.monotonic()-started<180:
            if (STATE/'early_attach_ack.json').exists():
                ack=b.read(STATE/'early_attach_ack.json')
                worker=ack.get('worker',{})
                if ack.get('responding_to_event_sha256')==EVENT and worker.get('pid')==owner['pid'] and worker.get('windows_creation_filetime_100ns')==owner['windows_creation_filetime_100ns']:
                    acknowledged=True;break
            if (R/'state/STOP').exists():raise InterruptedError('Global STOP')
            time.sleep(.25)
        if not acknowledged:raise TimeoutError('Exact current-namespace retained-handle ACK absent after180s')
        while time.monotonic()-started<900:
            if (R/'state/STOP').exists():raise InterruptedError('Global STOP')
            p.native_rss()
            found=published()
            if found:
                time.sleep(.25)
                again=published()
                if again==found:
                    status='GENERIC_SOURCE_CONTRACT_PUBLISHED_PENDING_ROOT_REVIEW';break
            if time.monotonic()-last>=30:
                stage={'id':'04','name':'Independent biological QC','status':'PREPARING','operation':'PREPARATION','detail':'Waiting for final generic source contract after a closed metadata-only mask mismatch; no genome processing.','done':0,'total':19,'unit':'reserved method commits','started_utc':b.read(E/'owner_started.json')['at_utc'],'updated_utc':b.utc(),**owner,'log_path':str(E/'progress.json'),'campaign_accepted_method_estimates':15,'campaign_source_supported_total':919,'campaign_pending_method_estimates':904,'production_panel_acceptance':False}
                b.atomic(E/'progress.json',stage);b.atomic(R/'state/stages/04.json',stage);last=time.monotonic()
            time.sleep(1)
        else:status='FINITE_SOURCE_PUBLICATION_WAIT_EXPIRED_REQUIRES_ROOT_RECONCILIATION'
    except BaseException as ex:
        status='SOURCE_PUBLICATION_OBSERVER_FAILED';error={'type':type(ex).__name__,'error':str(ex)}
    code=0 if found is not None and error is None else 3
    b.exclusive(E/'result_pending_actual_exit.json',{'status':status,'native_owner':owner,'actual_native_exit':'PENDING_EXTERNAL_RETAINED_HANDLE','intended_exit_code':code,'error':error,'exact_ACK_observed':acknowledged,'publication':found,'elapsed_seconds':time.monotonic()-started,'scientific_execution_authorized':False,'no_subprocess_mount_model_genome_read_or_dispatch':True,'no_retry_or_accepted_phase_replay':True,'at_utc':b.utc()})
    b.atomic(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC','status':'WAITING_AT_GATE','operation':'PREPARATION','detail':status,'done':0,'total':19,'unit':'reserved method commits','updated_utc':b.utc(),'ended_utc':b.utc(),'log_path':str(E/'result_pending_actual_exit.json'),'terminal_receipt':b.row(R,E/'result_pending_actual_exit.json'),'production_panel_acceptance':False})
    return code

if __name__=='__main__':raise SystemExit(main())
