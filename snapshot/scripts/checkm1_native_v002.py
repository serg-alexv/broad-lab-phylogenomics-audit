"""WD-only CheckM1 owner; retained actual WSL exit, modest monitor footprint."""
from pathlib import Path
import os,sys,json,subprocess,time,msvcrt
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import local_tree2_dispatcher as d
import checkm2_private_install_controller as b
plan=Path(sys.argv[1]);expected=sys.argv[2]
if os.name!='nt'or os.environ.get('COMPUTERNAME','').upper()!='WD'or g.sha(plan)!=expected:raise RuntimeError('Exact WD plan required')
j=g.read(plan);e=R/j['work'];e.mkdir(exist_ok=True);k=d.Windows();owner=b.OWNER;locks=[]
try:
 for name in('checkm2_pilot_launcher.lock','checkm2_install.lock'):
  f=(R/'state'/name).open('r+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);locks.append(f)
 g.save(e/'native_owner.json',{'native_owner':owner,'input_plan_sha256':expected,'input_plan':g.ref(plan),'started_utc':g.utc(),'method':'CheckM1_order_Lactobacillales'})
 until=time.monotonic()+180
 while True:
  ack=e/'Root_companion_ack.json'
  if ack.exists():
   value=g.read(ack)
   if value.get('native_owner')==owner and value.get('exact_handle_retained')is True and value.get('input_plan_sha256')==expected:break
  if time.monotonic()>until:raise TimeoutError('Retained Root/controller OS handle ACK missing before science')
  time.sleep(.2)
 linux='/mnt/c/'+plan.as_posix()[3:];entry='/mnt/c/'+(R/'scripts/checkm1_private_namespace_v002.py').as_posix()[3:]
 with(e/'WSL.stdout.txt').open('wb')as out,(e/'WSL.stderr.txt').open('wb')as err:
  p=subprocess.Popen(['wsl','-d','Ubuntu','--exec','unshare','--mount','--ipc','--propagation','private','/usr/bin/python3','-B',entry,linux,expected],stdout=out,stderr=err)
  identity=k.identity(int(p._handle),p.pid);g.save(e/'WSL_owner.json',{'identity':identity,'argv_role':'CheckM1_private_IPC_only'});p.wait()
  g.save(e/'WSL_actual_exit.json',{'actual_exit_code':p.returncode,'identity':identity,'exact_birth_handle_retained':True,'waited_and_reaped':True,'observed_utc':g.utc()})
 print(json.dumps({'WSL_actual_exit':p.returncode,'native_owner_actual_exit':'REQUIRES_EXTERNAL_RETAINED_HANDLE'}),flush=True)
 raise SystemExit(p.returncode)
finally:
 for f in reversed(locks):f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1);f.close()
