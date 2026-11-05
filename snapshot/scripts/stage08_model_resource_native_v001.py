"""WD-only CheckM1 owner; retained actual WSL exit, modest monitor footprint."""
from pathlib import Path
import os,sys,json,subprocess,time,msvcrt,ctypes
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import local_tree2_dispatcher as d
import checkm2_private_install_controller as b
from checkm2_native_rss_guard_v001 import summed_native_rss
plan=Path(sys.argv[1]);expected=sys.argv[2]
if os.name!='nt'or os.environ.get('COMPUTERNAME','').upper()!='WD'or g.sha(plan)!=expected:raise RuntimeError('Exact WD plan required')
j=g.read(plan);e=R/j['work'];e.mkdir(exist_ok=True);k=d.Windows();owner=b.OWNER;locks=[]
kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=ctypes.c_void_p;kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(),sum(1<<c for c in j['native_affinity_CPUs'])):raise ctypes.WinError(ctypes.get_last_error())
try:
 for name in('checkm2_pilot_launcher.lock','checkm2_install.lock'):
  f=(R/'state'/name).open('r+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);locks.append(f)
 g.save(e/'native_owner.json',{'native_owner':owner,'input_plan_sha256':expected,'input_plan':g.ref(plan),'started_utc':g.utc(),'method':'STAGE08_MODEL_RESOURCE_PILOT_UNCHANGED900x13071'})
 until=time.monotonic()+180
 while True:
  ack=e/'Root_companion_ack.json'
  if ack.exists():
   value=g.read(ack)
   if value.get('native_owner')==owner and value.get('exact_handle_retained')is True and value.get('input_plan_sha256')==expected:break
  if time.monotonic()>until:raise TimeoutError('Retained Root/controller OS handle ACK missing before science')
  time.sleep(.2)
 linux='/mnt/c/'+plan.as_posix()[3:];entry='/mnt/c/'+(R/'scripts/stage08_model_resource_namespace_v001.py').as_posix()[3:]
 with(e/'WSL.stdout.txt').open('wb')as out,(e/'WSL.stderr.txt').open('wb')as err:
  p=subprocess.Popen(['wsl','-d','Ubuntu','--exec','unshare','--mount','--ipc','--propagation','private','/usr/bin/python3','-B',entry,linux,expected],stdout=out,stderr=err)
  identity=k.identity(int(p._handle),p.pid);g.save(e/'WSL_owner.json',{'identity':identity,'argv_role':'STAGE08_MODEL_RESOURCE_PILOT_PRIVATE_IPC_ONLY'})
  failure=None;stop_started=None;peak=0
  while p.poll()is None:
   rss=summed_native_rss(p);peak=max(peak,rss)
   if rss>j['native_reserved_bytes'] or time.time()>j['original_context_absolute_deadline_unix']:
    failure=failure or 'Native RSS reservation or finite marker-stage context deadline exceeded'
    if stop_started is None:
     stop_started=time.monotonic();g.save(R/j['stop_path'],{'reason':failure,'native_owner':owner,'no_blind_retry':True})
   if stop_started is not None and time.monotonic()-stop_started>180:
    g.save(e/'unresolved_WSL_ownership.json',{'identity':identity,'actual_exit_code':None,'error':failure,'no_relaunch':True})
    raise RuntimeError('WSL did not close after scoped stop; closure UNKNOWN')
   time.sleep(.5)
  p.wait();g.save(e/'native_RSS_guard.json',{'peak_native_plus_retained_WSL_RSS_bytes':peak,'reservation_bytes':j['native_reserved_bytes'],'fatal_resource_reason':failure})
  g.save(e/'WSL_actual_exit.json',{'actual_exit_code':p.returncode,'identity':identity,'exact_birth_handle_retained':True,'waited_and_reaped':True,'observed_utc':g.utc()})
 print(json.dumps({'WSL_actual_exit':p.returncode,'native_owner_actual_exit':'REQUIRES_EXTERNAL_RETAINED_HANDLE'}),flush=True)
 raise SystemExit(p.returncode)
finally:
 for f in reversed(locks):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
