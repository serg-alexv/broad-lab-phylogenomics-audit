"""One source-bound finite WD native; current V007 custody precedes any WSL science."""
from pathlib import Path
import os,sys,json,subprocess,time,msvcrt,ctypes
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import local_tree2_dispatcher as d
from checkm2_native_rss_guard_v001 import summed_native_rss
plan=Path(sys.argv[1]);expected=sys.argv[2]
assert os.name=='nt' and os.environ.get('COMPUTERNAME','').upper()=='WD' and g.sha(plan)==expected
j=g.read(plan);assert j['schema']=='TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V001'
assert j['native_reserved_bytes']==134217728 and j['linux_RSS_plus_RAM_bytes']==1879048192 and j['minimum_linux_available_bytes']==1342177280 and j['cpu']==2
for row in j['sources']+j['bound_inputs']:d.bind(R,row)
e=d.inside(R,j['work']);e.mkdir(exist_ok=True);k=d.Windows();owner=k.identity(ctypes.c_void_p(-1),os.getpid());locks=[];started=time.monotonic()
try:
 for name in ('checkm2_pilot_launcher.lock','checkm2_install.lock'):
  f=(R/'state'/name).open('r+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);locks.append(f)
 g.save(e/'native_owner.json',{'native_owner':owner,'input_plan_sha256':expected,'input_plan':g.ref(plan),'started_utc':g.utc(),'method':'DEFENCE_STOCK_PROTEIN_SUPPORTED_NOVEL_COHORT'})
 until=time.monotonic()+180
 while True:
  if time.monotonic()>until or time.time()>j['original_context_absolute_deadline_unix']:raise TimeoutError('Exact retained V007 custody before deadline required; no WSL science started')
  assert summed_native_rss()<=j['native_reserved_bytes']
  ack=e/'Root_companion_ack.json'
  if ack.exists():
   value=g.read(ack)
   if value.get('native_owner')==owner and value.get('exact_handle_retained') is True and value.get('input_plan_sha256')==expected and value.get('current_state_namespace')=='state/local_continuation_v7':
    attached=g.read(d.bind(R,value['current_namespace_ACK']))
    assert attached['event_sha256']==j['current_event_sha256'] and attached['exact_handle_retained'] and all(attached['worker'][x]==owner[x] for x in owner)
    break
  time.sleep(.2)
 linux='/mnt/c/'+plan.as_posix()[3:];entry='/mnt/c/'+(R/'scripts/defence_bulk_namespace_v001.py').as_posix()[3:]
 args=['wsl','-d','Ubuntu','--exec','unshare','--mount','--ipc','--propagation','private','/usr/bin/python3','-B',entry,linux,expected]
 g.save(e/'WSL_command.json',{'argv':args,'source_bound_plan':g.ref(plan)})
 with (e/'WSL.stdout.txt').open('xb') as out,(e/'WSL.stderr.txt').open('xb') as err:
  p=subprocess.Popen(args,stdout=out,stderr=err);identity=k.identity(int(p._handle),p.pid);g.save(e/'WSL_owner.json',{'identity':identity,'argv_role':'NOVEL_DEFENCE_COHORT_PRIVATE_IPC_RAM_READONLY_R_RUNTIME'})
  failure=None;stop_started=None;peak=0
  while p.poll() is None:
   rss=summed_native_rss(p);peak=max(peak,rss)
   if rss>j['native_reserved_bytes'] or time.time()>j['original_context_absolute_deadline_unix'] or time.monotonic()-started>j['cold_seconds']+180:
    failure=failure or 'Native RSS or admitted finite cohort wall/deadline guard exceeded'
    if stop_started is None:stop_started=time.monotonic();g.save(R/j['stop_path'],{'reason':failure,'native_owner':owner,'no_blind_retry':True})
   if stop_started is not None and time.monotonic()-stop_started>180:
    g.save(e/'unresolved_WSL_ownership.json',{'identity':identity,'actual_exit_code':None,'error':failure,'no_relaunch':True});raise RuntimeError('Owned WSL cleanup unresolved; closure UNKNOWN, no relaunch')
   time.sleep(.5)
  code=p.wait();g.save(e/'native_RSS_guard.json',{'peak_native_plus_retained_WSL_RSS_bytes':peak,'reservation_bytes':j['native_reserved_bytes'],'fatal_resource_reason':failure})
  g.save(e/'WSL_actual_exit.json',{'actual_exit_code':code,'identity':identity,'exact_birth_handle_retained':True,'waited_and_reaped':True,'observed_utc':g.utc()})
 print(json.dumps({'WSL_actual_exit':code,'native_owner_actual_exit':'REQUIRES_EXTERNAL_RETAINED_HANDLE'}),flush=True)
 if failure:raise RuntimeError(failure+'; actual WSL exit retained separately')
 raise SystemExit(code)
finally:
 for f in reversed(locks):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
