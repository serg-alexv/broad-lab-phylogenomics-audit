"""Detached finite synthetic-only DIAMOND diagnostic owner; observes real child exits."""
from pathlib import Path
import argparse,ctypes,json,msvcrt,os,subprocess,sys,time
import local_tree2_dispatcher as b
import checkm2_production_preparation_P1 as p
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_phase_separated_P20/index_chunks_synthetic_review_R3_v001'
K=b.Windows();OWNER=K.identity(ctypes.c_void_p(-1),os.getpid());START=time.monotonic();BEGAN=b.utc();LAST=0
EVENT='419c208df27ec873c9e1c263eeecd95982b869d3da1a3e26d62fb775b2765db5'
def guard():
 if time.monotonic()-START>420:raise TimeoutError('Synthetic diagnostic finite420s native ceiling')
 if (R/'state/STOP').exists()or(R/'state/STOP_CHECKM2_PILOT').exists():raise InterruptedError('Project STOP')
 p.native_rss()
 if __import__('shutil').disk_usage(R).free<40*1024**3:raise RuntimeError('RESOURCE_GATE disk40GiB reserve')
def stage(detail,status='RUNNING',terminal=None):
 global LAST
 now=time.monotonic()
 if now-LAST<30 and status=='RUNNING':return
 LAST=now
 b.atomic(R/'state/stages/04.json',{'id':'04','name':'Independent biological QC','status':status,'operation':'SYNTHETIC_DIAMOND_INDEX_CHUNKS_REVIEW_ONLY','detail':detail,'done':0,'total':None,'unit':'synthetic resource review; genome queue remains pending','pid':OWNER['pid']if status=='RUNNING'else None,'creation_time_utc':OWNER['creation_time_utc']if status=='RUNNING'else None,'windows_creation_filetime_100ns':OWNER['windows_creation_filetime_100ns'],'started_utc':BEGAN,'updated_utc':b.utc(),'log_path':str(E/'WSL_stderr.txt'),'terminal_receipt':terminal,'genome_scientific_retry_admitted':False,'whole_stage_or_production_panel_acceptance':False})
def linux(p):return '/mnt/c/'+str(Path(p).resolve())[3:].replace('\\','/')
def main(a):
 guard();grant=b.read(b.bind(R,{'path':a.admission,'sha256':a.admission_sha256}))
 assert grant['status']=='ROOT_ADMITTED_ONE_SYNTHETIC_INDEX_CHUNKS_DIAGNOSTIC' and grant['event_sha256']==EVENT
 assert grant['campaign_genome_or_database_access_authorized']is False and grant['runtime_image_mount_authorized']is False
 for ref in grant['bound_sources']+[grant['binary'],grant['closed_repeated_resource_failure'],grant['current_CLI_launch'],grant['current_runtime_roles']]:b.bind(R,ref)
 mask=p.affinity(K);b.exclusive(E/'owner_launch.json',{'native_owner':OWNER,'source':b.row(R,Path(__file__)),'admission':b.row(R,Path(a.admission)),'maximum_native_seconds':420,'maximum_ACK_wait_seconds':180,'affinity_mask':mask,'no_genome_or_runtime_image_access':True})
 directory=R/b.read(R/'state/local_continuation_current_runtime.json')['state_directory']
 stage('Repeated genome search retries stopped. Waiting for exact current-namespace ACK before a bounded synthetic index-chunks diagnostic.')
 while True:
  guard()
  try:
   ack=b.read(directory/'early_attach_ack.json')
   if ack.get('event_sha256')==EVENT and ack.get('exact_handle_retained')is True and all(ack['worker'].get(k)==v for k,v in OWNER.items()):break
  except FileNotFoundError:pass
  if time.monotonic()-START>180:raise TimeoutError('Exact current namespace ACK absent; no diagnostic started')
  time.sleep(.25)
 # Reverify exact controller and current event CLI identities; no blanket Python exclusion.
 roles=b.read(b.bind(R,grant['current_runtime_roles']));cli=b.read(b.bind(R,grant['current_CLI_launch']));assert cli['event_sha256']==EVENT
 verified=b.read(b.bind(R,grant['preflight_receipt']))['verified_current_roles']
 assert next(x['identity']for x in verified if x['role']=='CURRENT_EVENT_CLI')==cli['identity']
 for identity in [x['identity']for x in roles['roles']]:
  handle=K.open_worker(identity)
  try:assert not K.wait(handle,0)
  finally:K.close(handle)
 handles=[];locks=[R/'state/checkm2_pilot_launcher.lock',R/'state/checkm2_install.lock'];before=[b.row(R,x)for x in locks];child=None;child_id=None
 try:
  for lock in locks:
   f=lock.open('r+b');f.seek(0)
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except BaseException:f.close();raise
   handles.append(f)
  argv=['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B',linux(R/'scripts/checkm2_P20_index_chunks_fixture_linux_v003.py'),'--phase','observe','--admission',linux(a.admission),'--admission-sha256',a.admission_sha256]
  with(E/'WSL_stdout.txt').open('x')as out,(E/'WSL_stderr.txt').open('x')as err:
   child=subprocess.Popen(argv,cwd=R,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));child_id=K.identity(int(child._handle),child.pid)
   b.exclusive(E/'WSL_launch.json',{'native_owner':OWNER,'WSL_child':child_id,'argv':argv,'admission':b.row(R,Path(a.admission)),'maximum_WSL_seconds':220})
   deadline=time.monotonic()+220
   while child.poll()is None:
    guard()
    if time.monotonic()>deadline:
     b.exclusive(E/'UNRESOLVED_WSL.json',{'native_owner':OWNER,'WSL_child':child_id,'actual_WSL_exit':'UNKNOWN','no_numeric_PID_kill_or_duplicate_authorized':True});raise TimeoutError('Owned synthetic WSL child exceeded deadline; preserve exact owner')
    stage('Synthetic-only pinned DIAMOND help/default/index4/index8/index16 diagnostic; no campaign FAA, DB, model, pickle or image opened.');time.sleep(.25)
   code=child.wait();b.exclusive(E/'WSL_actual_exit.json',{'native_owner':OWNER,'WSL_child':child_id,'actual_exit_code':code,'retained_handle_reaped':True,'at_utc':b.utc()})
  if code!=0:raise RuntimeError('Synthetic WSL actual exit'+str(code)+'; no automatic retry')
  terminal=b.read(E/'linux_terminal.json');unit=b.read(b.bind(R,terminal['unit_execution']));assert unit['status']=='UNIT_EXIT0_GROUP_CLOSED' and unit['exit_code']==0 and unit['owned_group_empty']is True and unit['remaining_owned_processes']==[]
  assert b.read(E/'linux_lease_release.json')['status']=='COMPUTE_LEASE_RELEASED_BYTES_UNCHANGED'
 finally:
  for f in reversed(handles):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
 assert before==[b.row(R,x)for x in locks]
 result={'schema':'TREE2_NATIVE_SYNTHETIC_INDEX_CHUNKS_DIAGNOSTIC_PENDING_EXIT_V001','status':'SYNTHETIC_DIAGNOSTIC_GROUPS_AND_THREE_LEASES_CLOSED_NATIVE_EXIT_PENDING','native_owner':OWNER,'actual_native_exit':'NOT_YET_OBSERVABLE_BY_SELF','actual_WSL_exit':b.row(R,E/'WSL_actual_exit.json'),'linux_terminal':b.row(R,E/'linux_terminal.json'),'compute_lease_release':b.row(R,E/'linux_lease_release.json'),'comparison':b.row(R,E/'comparison.json'),'Windows_lease_bytes_unchanged':True,'runtime_image_mount_and_IPC_created':False,'genome_method_or_biological_acceptance':False,'genome_retry_admitted':False,'elapsed_native_seconds':time.monotonic()-START,'ended_utc':b.utc()}
 b.exclusive(E/'result_pending_owner_exit.json',result);stage('Synthetic resource-option diagnostic recorded; actual native exit and local Root method review pending.','WAITING_REVIEW',b.row(R,E/'result_pending_owner_exit.json'));print(json.dumps({'status':result['status'],'native_owner':OWNER}),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--admission',required=True);a.add_argument('--admission-sha256',required=True);args=a.parse_args()
 try:main(args)
 except BaseException as error:
  b.exclusive(E/'FAILED.json',{'status':'SYNTHETIC_DIAGNOSTIC_FAILED_NO_AUTOMATIC_RETRY','native_owner':OWNER,'error':repr(error),'at_utc':b.utc(),'actual_native_exit':'NOT_YET_OBSERVABLE_BY_SELF','no_genome_quality_inference':True});stage('Synthetic review failed; preserve exact receipts and owned children for local reconciliation.','FAILED',b.row(R,E/'FAILED.json'));raise
