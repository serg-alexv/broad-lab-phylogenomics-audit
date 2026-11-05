"""Fresh READ-ONLY file/OS gate; exact marker companion permitted, no runtime/science."""
from pathlib import Path
import argparse,ctypes,datetime,json,os,subprocess,sys,time,traceback,msvcrt
import checkm2_parallel_saved_common_v001 as c

def win_identity(pid):
 from ctypes import wintypes
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE];k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
 class FT(ctypes.Structure):_fields_=[('low',wintypes.DWORD),('high',wintypes.DWORD)]
 k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(FT)]*4
 handle=k.OpenProcess(0x1000|0x100000,False,pid)
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 try:
  a,b,d,e=FT(),FT(),FT(),FT()
  if not k.GetProcessTimes(handle,ctypes.byref(a),ctypes.byref(b),ctypes.byref(d),ctypes.byref(e)):raise ctypes.WinError(ctypes.get_last_error())
  if k.WaitForSingleObject(handle,0)!=258:raise RuntimeError('Expected native owner is not live')
  return{'pid':pid,'windows_creation_filetime_100ns':(a.high<<32)|a.low}
 finally:k.CloseHandle(handle)

def main(a):
 started=time.monotonic();output=c.path(a.output)
 if os.name!='nt' or output.exists():raise RuntimeError('New WD-native readonly preflight output only')
 output.mkdir(parents=True);facts={};children=[];error=None;code=2
 def persist():c.save(output/'observations.json',facts)
 try:
  plan,_,_=c.plan_gate(a.input_plan,a.input_plan_sha256,require_admission=False);c.native_guard();facts['owner']=win_identity(os.getpid());facts['plan']=c.row(c.path(a.input_plan));persist()
  expected=plan['companion_marker']['native_owner'];actual=win_identity(expected['pid']);facts['marker_native']=actual;persist()
  if actual['windows_creation_filetime_100ns']!=expected['windows_creation_filetime_100ns']:raise RuntimeError('Exact marker native birth differs')
  # Bind exact launch/admission/source; no broad Python or heavy-science exemption.
  launch=c.read(c.bind(plan['companion_marker']['launch']));contract=c.read(c.bind(launch['contract']));c.bind(contract['entry_source']);wsl=c.read(c.bind(plan['companion_marker']['wsl_launch']))
  facts['marker_WSL']=win_identity(wsl['wsl_owner']['pid']);persist()
  if facts['marker_WSL']['windows_creation_filetime_100ns']!=wsl['wsl_owner']['windows_creation_filetime_100ns']:raise RuntimeError('Marker WSL birth differs')
  ps="$ErrorActionPreference='Stop';@(Get-CimInstance Win32_Process|Where-Object {$_.ProcessId -in @("+str(expected['pid'])+","+str(wsl['wsl_owner']['pid'])+") -or ($_.CommandLine -and $_.CommandLine.Contains('TREE2_WD_20261026') -and $_.Name -in @('python.exe','wsl.exe'))}|Select-Object ProcessId,ParentProcessId,Name,CommandLine)|ConvertTo-Json -Compress"
  active_kind='native_command_observer';child=subprocess.Popen(['pwsh','-NoProfile','-Command',ps],stdout=subprocess.PIPE,stderr=subprocess.PIPE);birth=win_identity(child.pid);out,err=child.communicate(timeout=15);children.append({'kind':'native_command_observer','identity':birth,'exit_code':child.returncode,'stdout':out.decode(),'stderr':err.decode()});facts['actual_children']=children;persist()
  if child.returncode!=0:raise RuntimeError('Actual native command observer failed')
  commands=json.loads(out);commands=commands if isinstance(commands,list)else[commands]
  native=next(x for x in commands if x['ProcessId']==expected['pid']);guest=next(x for x in commands if x['ProcessId']==wsl['wsl_owner']['pid'])
  if str(c.bind(contract['entry_source']))not in native['CommandLine']or 'fullpanel_marker_screen_v001.py'not in guest['CommandLine']or guest['ParentProcessId']!=expected['pid']:raise RuntimeError('Exact marker native/WSL command/parent chain differs')
  allowed={expected['pid'],wsl['wsl_owner']['pid'],os.getpid(),child.pid}
  pointer=c.read(c.R/'state/local_continuation_current_runtime.json');roles=c.read(c.bind(pointer['actual_runtime_roles']))
  for role in roles['roles']:
   identity=role['identity'];found=next((x for x in commands if x['ProcessId']==identity['pid']),None)
   if found is None:continue
   observed=win_identity(identity['pid']);source=c.bind(role['source'])
   if observed['windows_creation_filetime_100ns']!=identity['windows_creation_filetime_100ns']or source.name not in found['CommandLine']:raise RuntimeError('Exact non-scientific runtime role differs')
   allowed.add(identity['pid'])
  # Only source/birth-bound known monitor actors and identity-proved marker WSL proxies.
  monitor=c.read(c.bind(plan['known_monitor_roles']))
  monitor_evidence=[]
  for role_name in('publisher','collector'):
   role=monitor[role_name];item=next((x for x in commands if x['ProcessId']==role['pid']),None)
   if item is None:continue
   source=c.bind({'path':role['script'],'sha256':role['script_sha256']});observed=win_identity(role['pid'])
   if observed['windows_creation_filetime_100ns']!=role['windows_creation_filetime_100ns']or str(source)not in item['CommandLine']:raise RuntimeError('Known monitor source/birth/command differs: '+role_name)
   allowed.add(role['pid']);monitor_evidence.append({'role':role_name,'identity':observed,'source':c.row(source),'command':item['CommandLine']})
  chain={wsl['wsl_owner']['pid']:facts['marker_WSL']};proxy_evidence=[]
  def wsl_suffix(command):
   index=command.lower().find('wsl.exe')
   return None if index<0 else command[index+len('wsl.exe'):].lstrip('\" ')
  changed=True
  while changed:
   changed=False
   for item in commands:
    if item['ProcessId']in chain or item['ParentProcessId']not in chain:continue
    if item.get('Name','').lower()!='wsl.exe'or wsl_suffix(item['CommandLine'])!=wsl_suffix(guest['CommandLine']):raise RuntimeError('Unproved child of marker WSL owner')
    observed=win_identity(item['ProcessId']);parent=chain[item['ParentProcessId']]
    if observed['windows_creation_filetime_100ns']<parent['windows_creation_filetime_100ns']:raise RuntimeError('Marker WSL proxy creation precedes its parent')
    chain[item['ProcessId']]=observed;allowed.add(item['ProcessId']);proxy_evidence.append({'identity':observed,'parent_identity':parent,'command':item['CommandLine']});changed=True
  facts['known_source_birth_verified_monitors']=monitor_evidence;facts['exact_marker_WSL_proxy_chain']=proxy_evidence;persist()
  unexpected=[x for x in commands if x['ProcessId']not in allowed];facts['unapproved_native_workers']=unexpected;persist()
  if unexpected:raise RuntimeError('Another unapproved project native scientific owner exists')
  locks=[];lock_before={}
  try:
   for name in('checkm2_pilot_launcher.lock','checkm2_install.lock'):
    path=c.R/'state'/name;lock_before[name]=c.sha(path);f=path.open('r+b')
    try:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    except BaseException:f.close();raise
    locks.append(f)
   linux_root='/mnt/c/'+str(c.R)[3:].replace('\\','/');linux_plan=linux_root+'/'+c.path(a.input_plan).relative_to(c.R).as_posix()
   source="from pathlib import Path\nimport sys,json,fcntl,os\nsys.path.insert(0,"+repr(linux_root+'/scripts')+")\nimport checkm2_parallel_saved_common_v001 as c\nc.plan_gate("+repr(linux_plan)+","+repr(a.input_plan_sha256)+",require_admission=False)\nfacts={'resources':c.linux_guard(fresh=True),'companions':c.marker_and_exclusivity_gate()}\nlock=c.R/'state/checkm2_pilot.lock';before=c.sha(lock);f=lock.open('r+b')\ntry:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)\nfinally:f.close()\nfacts['compute_lease_reacquired_released_bytes_unchanged']=c.sha(lock)==before\nimage=c.R/'tools/checkm2_runtime_ext4.img';st=image.stat();facts['image_stat']={'dev':st.st_dev,'ino':st.st_ino,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns};assert (st.st_dev,st.st_ino,st.st_size)==(52,5348024557958676,17179869184)\nloops=[]\nfor p in Path('/sys/block').glob('loop*/loop/backing_file'):\n try:\n  v=p.read_text().strip()\n  if 'checkm2_runtime_ext4.img'in v:loops.append({'path':str(p),'backing':v})\n except FileNotFoundError:pass\nfacts['existing_CheckM2_image_loops']=loops;assert not loops\nprint(json.dumps(facts))\n"
   source="import signal\nsignal.signal(signal.SIGALRM,lambda *a:(_ for _ in()).throw(TimeoutError('Read-only Linux observer deadline')))\nsignal.alarm("+str(max(1,int(45-(time.monotonic()-started))))+")\n"+source
   source=source.replace('print(json.dumps(facts))\n','')
   source+="import hashlib\nregistry=Path('/root/.conda/environments.txt');registry_stat=registry.stat()\nfacts['host_registry']={'sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),'mtime_ns':registry_stat.st_mtime_ns,'size':registry_stat.st_size,'canary_exists':Path('/root/.conda/TREE2_PRIVATE_NAMESPACE_CANARY').exists()}\nassert facts['host_registry']==c.read(c.R/'evidence/checkm2_runtime/install_registry_before.json')\nprint(json.dumps(facts))\n"
   active_kind='readonly_Linux_OS_observer';child=subprocess.Popen(['wsl','-d','Ubuntu','--','/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1','/usr/bin/python3','-B','-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE);birth=win_identity(child.pid);out,err=child.communicate(timeout=max(1,50-(time.monotonic()-started)));children.append({'kind':'readonly_Linux_OS_observer','identity':birth,'exit_code':child.returncode,'stdout':out.decode(),'stderr':err.decode()});facts['actual_children']=children;persist()
   if child.returncode!=0:raise RuntimeError('Fresh Linux resource/exact-marker/exclusivity/lease gate failed')
   facts['Linux']=json.loads(out);persist()
  finally:
   errors=[]
   for f in reversed(locks):
    try:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
    except BaseException as e:errors.append(repr(e))
    finally:f.close()
   facts['native_leases']={'before':lock_before,'after':{k:c.sha(c.R/'state'/k)for k in lock_before},'release_errors':errors};persist()
   if errors or facts['native_leases']['before']!=facts['native_leases']['after']:raise RuntimeError('Native lease release/byte preservation failed')
  if time.monotonic()-started>60:raise TimeoutError('One bounded60s preflight expired')
  code=0
 except BaseException as e:
  error={'type':type(e).__name__,'error':str(e),'errno':getattr(e,'errno',None),'filename':getattr(e,'filename',None),'traceback':traceback.format_exc()}
  if 'child'in locals()and child.poll()is None:
   try:
    if active_kind=='native_command_observer':child.terminate()
    # The Linux guest has its own earlier alarm. Never kill wsl.exe as guest proof.
    out,err=child.communicate(timeout=max(.1,min(5,59-(time.monotonic()-started))))
    children.append({'kind':active_kind,'identity':birth,'exit_code':child.returncode,'actual_handle_reaped':True,'cleanup_stdout':out.decode(),'cleanup_stderr':err.decode()})
   except subprocess.TimeoutExpired:pass
   facts['actual_children']=children;persist()
  if 'child'in locals()and child.poll()is None:
   handoff={'status':'READONLY_PREFLIGHT_CHILD_CLOSURE_UNKNOWN_NO_SCIENTIFIC_RELAUNCH','child_identity':birth,'actual_poll':child.poll(),'error':error,'observer_is_non_genomic':True,'no_wsl_proxy_kill_as_guest_closure':True}
   c.save(c.UNRESOLVED_HANDOFF,handoff);facts['unresolved_child']=handoff;persist()
 c.save(output/'receipt.json',{'status':'PARALLEL_SAVED_STOCK_READONLY_PREFLIGHT_PASS_PENDING_OBSERVED_NATIVE_EXIT'if code==0 else'PARALLEL_SAVED_STOCK_PREFLIGHT_FAILED_NO_RETRY','actual_native_exit_code':'REQUIRES_ROOT_RETAINED_OBSERVER','actual_children':children,'error':error,'observations':c.row(output/'observations.json'),'elapsed_seconds':time.monotonic()-started,'marker_stopped_or_mutated':False,'runtime_image_opened_or_science_launched':False});return code
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--output',required=True);raise SystemExit(main(p.parse_args()))
