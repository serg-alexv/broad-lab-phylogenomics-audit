"""Finite source-publication observer for the current QC repair, no science/dispatch."""
from pathlib import Path
import argparse,ctypes,json,os,re,shutil,sys,time
from ctypes import wintypes
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as prep
R=Path(__file__).resolve().parents[1]

def references(value):
 if isinstance(value,dict):
  if isinstance(value.get('path'),str)and isinstance(value.get('sha256'),str):yield value
  for x in value.values():yield from references(x)
 elif isinstance(value,list):
  for x in value:yield from references(x)

def source_roles(sources):
 roles=set();new_inner=False
 for path in sources:
  m=re.fullmatch(r'scripts/checkm2_[A-Za-z0-9_]*_(native|entry|common|inner|observer)_v([0-9]{3})\.py',path)
  if not m:continue
  roles.add(m[1])
  if m[1]=='inner'and('continuous'in path or'queue'in path or int(m[2])>=5):new_inner=True
 return roles,new_inner

def inspect(candidate,scope):
 if candidate.stat().st_size>2*1024**2:return None
 v=b.read(candidate);status=str(v.get('status','')).upper()
 if not any(x in status for x in ('FROZEN','SOURCE_READY','GO_SOURCE','REVIEW_PASS'))or any(x in status for x in ('FAILED','REJECT','UNKNOWN','BLOCKED')):return None
 found={};seen=set()
 def collect(body,depth=0):
  for ref in references(body):
   p=ref['path'].replace('\\','/')
   if p.startswith('scripts/')and p.endswith(('.py','.sh')):
    f=b.bind(R,ref)
    if f.stat().st_size>2*1024**2:raise RuntimeError('Unexpected source size')
    found[p]=b.row(R,f)
   elif depth<3 and p.endswith('.json')and p not in seen and p.startswith(scope+'/')and any(k in Path(p).name for k in ('source','manifest','contract','delivery')):
    seen.add(p);f=b.bind(R,ref)
    if f.stat().st_size<=2*1024**2:collect(b.read(f),depth+1)
 collect(v);roles,new_inner=source_roles(found)
 if not {'native','entry','common','inner','observer'}<=roles or not new_inner:return None
 return {'publication':b.row(R,candidate),'status':v['status'],'sources':[found[k]for k in sorted(found)],'scientific_admission':'NOT_GRANTED_REQUIRES_EXACT_RESERVATION_SOURCE_RESOURCE_AND_METHOD_REVIEW','all_old_attempts_and_accepted_results_must_remain_preserved':True}

def publication(scope):
 folder=b.inside(R,scope)
 if not folder.exists():return None
 for p in sorted(folder.rglob('*.json')):
  if len(p.relative_to(folder).parts)>4 or not any(k in p.name for k in ('source','contract','delivery')):continue
  try:
   x=inspect(p,scope)
   if x:return x
  except(OSError,ValueError,KeyError,RuntimeError):continue
 return None

def main(a):
 ap=b.bind(R,{'path':a.admission,'sha256':a.admission_sha256});ad=b.read(ap)
 if ad['status']!='ROOT_ADMITTED_ONE_CURRENT_QC_SOURCE_BOUNDARY'or ad['source']!=b.row(R,Path(__file__).resolve())or ad['maximum_wall_seconds']!=1800:raise RuntimeError('Exact operational admission required')
 state=b.inside(R,b.read(R/'state/local_continuation_current_runtime.json')['state_directory']);out=b.inside(R,ad['evidence_directory']);out.mkdir(parents=True,exist_ok=True)
 k=b.Windows();owner=k.identity(ctypes.c_void_p(-1),os.getpid());mask=prep.affinity(k);started=time.monotonic();start_utc=b.utc();notify=None;found=None;error=None;ack=None;last=-30.
 b.exclusive(out/'owner_started.json',{'native_owner':owner,'source':ad['source'],'admission':b.row(R,ap),'affinity_mask':mask,'at_utc':start_utc,'scientific_execution_authorized':False})
 def progress():
  if prep.native_rss()>128*1024**2:raise MemoryError('File-only observer native128MiB ceiling')
  if shutil.disk_usage(R).free<40*1024**3:raise OSError('Project disk reserve below40GiB')
  s={'id':'04','name':'Independent biological QC','status':'PREPARING','operation':'WAITING_FOR_BOUND_CURRENT_QC_RUNTIME_SOURCES','detail':'Marker919searches externally validated/closed. Saved stock0 needs feature-only validation; complete reviewed runtime/own-FAA provenance adapter is pending. No scientific unit runs.','done':16,'total':919,'unit':'source-supported accepted method estimates; not panel passes','started_utc':start_utc,'updated_utc':b.utc(),**owner,'log_path':str(out/'progress.json'),'scientific_units_running':False,'saved_feature_allowance_remaining_seconds':113.89114030799828,'saved_score_provisional':{'Completeness':99.97,'Contamination':.14},'source_taxonomy_acceptance':False,'production_panel_acceptance':False,'unsearched_defence':'UNKNOWN'}
  b.atomic(out/'progress.json',s);b.atomic(R/'state/stages/04.json',s)
 try:
  while time.monotonic()-started<120:
   if(R/'state/STOP').exists():raise InterruptedError('Global STOP')
   try:
    x=b.read(state/'early_attach_ack.json')
    if x.get('event_sha256')==ad['event_sha256']and x.get('exact_handle_retained')is True and all(x['worker'][key]==val for key,val in owner.items()):ack=x;break
   except(OSError,ValueError,KeyError):pass
   time.sleep(.1)
  if ack is None:raise TimeoutError('Exact current dispatcher retained-handle ACK missing')
  b.exclusive(out/'exact_dispatcher_ack.json',ack)
  kernel=k.k;kernel.FindFirstChangeNotificationW.argtypes=[wintypes.LPCWSTR,wintypes.BOOL,wintypes.DWORD];kernel.FindFirstChangeNotificationW.restype=wintypes.HANDLE;kernel.FindNextChangeNotification.argtypes=[wintypes.HANDLE];kernel.FindNextChangeNotification.restype=wintypes.BOOL;kernel.FindCloseChangeNotification.argtypes=[wintypes.HANDLE];kernel.FindCloseChangeNotification.restype=wintypes.BOOL
  notify=kernel.FindFirstChangeNotificationW(str(R/'metadata'),True,0x1|0x8|0x10)
  if not notify or notify==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
  changed=True
  while time.monotonic()-started<1800:
   if(R/'state/STOP').exists():raise InterruptedError('Global STOP')
   if changed:
    found=publication(ad['publication_directory'])
    if found:
     time.sleep(.2)
     if publication(ad['publication_directory'])==found:break
     found=None
   if time.monotonic()-last>=30:progress();last=time.monotonic()
   ms=max(1,min(30000,int((1800-(time.monotonic()-started))*1000)));changed=k.wait(notify,ms)
   if changed and not kernel.FindNextChangeNotification(notify):raise ctypes.WinError(ctypes.get_last_error())
  if found is None:raise TimeoutError('One finite source-publication boundary expired; no automatic observer repeat')
 except BaseException as e:error={'type':type(e).__name__,'error':str(e)}
 finally:
  if notify and notify!=ctypes.c_void_p(-1).value:
   if not k.k.FindCloseChangeNotification(notify):error={'type':'NotificationClosureError','prior':error,'winerror':ctypes.get_last_error()}
 code=0 if found and error is None else 3
 result={'status':'CURRENT_QC_RUNTIME_SOURCE_PUBLICATION_REACHED_PENDING_REVIEW'if code==0 else'FINITE_SOURCE_PUBLICATION_BOUNDARY_FAILED_NO_AUTOMATIC_REPEAT','native_owner':owner,'publication':found,'error':error,'current_event_sha256':ad['event_sha256'],'exact_dispatcher_ACK_observed':ack is not None,'elapsed_seconds':time.monotonic()-started,'actual_native_exit':'UNKNOWN_UNTIL_EXTERNAL_RETAINED_HANDLE','intended_exit_code':code,'no_scientific_subprocess_model_input_image_or_pickle_access':True,'no_model_polling':True,'scientific_execution_authorized':False,'at_utc':b.utc()}
 b.exclusive(out/'result_pending_native_exit.json',result)
 b.atomic(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC','status':'WAITING_AT_GATE','operation':'CURRENT_QC_SOURCE_REVIEW_BOUNDARY','detail':result['status'],'done':16,'total':919,'unit':'source-supported accepted method estimates, not panel passes','updated_utc':b.utc(),'ended_utc':b.utc(),'terminal_receipt':b.row(R,out/'result_pending_native_exit.json'),'log_path':str(out/'result_pending_native_exit.json'),'source_taxonomy_acceptance':False,'production_panel_acceptance':False})
 return code

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True);raise SystemExit(main(p.parse_args()))
