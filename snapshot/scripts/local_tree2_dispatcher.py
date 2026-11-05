"""Local event-driven Tree2 continuation. No science dispatch, scheduled chat or polling AI turns."""
from pathlib import Path
import argparse,ctypes,datetime,hashlib,json,os,subprocess,sys,time,uuid

SCHEMA='TREE2_LOCAL_CONTINUATION_HANDOFF_V1'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def atomic(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.partial')
 with tmp.open('x',encoding='utf-8',newline='\n')as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def exclusive(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n')as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def inside(root,value):
 p=Path(value);p=(p if p.is_absolute()else root/p).resolve()
 if not p.is_relative_to(root):raise RuntimeError('Dispatcher artifact leaves project')
 auth=root/'work/local_continuation/codex_home'
 if p.is_relative_to(auth):raise RuntimeError('Dispatcher never reads/hashes/logs/indexes the auth home')
 return p
def bind(root,row):
 p=inside(root,row['path'])
 if digest(p)!=row['sha256']or('bytes'in row and p.stat().st_size!=row['bytes']):raise RuntimeError('Bound dispatcher artifact changed: '+str(p))
 return p
def row(root,p):return{'path':Path(p).relative_to(root).as_posix(),'sha256':digest(p),'bytes':Path(p).stat().st_size}
def worker_key(worker):return(worker['pid'],worker['windows_creation_filetime_100ns'])
def validate_handoff(root,data,required):
 if data.get('schema')!=SCHEMA or not isinstance(data.get('revision'),str)or not data['revision']:raise RuntimeError('Missing typed/revised continuation handoff')
 status=data.get('status')
 if status=='WAITING_WORKER':
  worker=data.get('worker',{})
  if type(worker.get('pid'))is not int or worker['pid']<=0 or type(worker.get('windows_creation_filetime_100ns'))is not int or not worker.get('creation_time_utc')or not worker.get('role'):raise RuntimeError('Missing exact worker creation identity')
  receipt=read(bind(root,worker['launch_receipt']));identity=receipt.get('native_owner',receipt)
  if worker_key(identity)!=worker_key(worker)or identity.get('creation_time_utc')!=worker['creation_time_utc']:raise RuntimeError('Handoff worker differs from bound launch identity')
 elif status=='BLOCKED':
  if not isinstance(data.get('reason'),str)or not data['reason'].strip():raise RuntimeError('BLOCKED handoff requires actual reason')
 elif status=='COMPLETE':
  outputs=data.get('outputs',[])
  if len(outputs)!=len(required)or{v.get('kind')for v in outputs}!=set(required):raise RuntimeError('Both Tree2 full and representative validation receipts required')
  for output in outputs:
   if output.get('status')!='VALIDATED':raise RuntimeError('Unvalidated output cannot complete continuation')
   bind(root,output['validation_receipt'])
 else:raise RuntimeError('Unknown handoff status')
 return data

def parse_cli_jsonl(path,expected_session=None):
 ids=[];completed=0
 with Path(path).open(encoding='utf-8-sig')as f:
  for line in f:
   if not line.strip():continue
   item=json.loads(line);kind=item.get('type')
   if kind in('error','turn.failed'):raise RuntimeError('CLI emitted '+kind)
   if kind=='thread.started':ids.append(str(uuid.UUID(item['thread_id'])))
   if kind=='turn.completed':completed+=1
 if completed!=1:raise RuntimeError('Exactly one actual completed CLI turn required')
 if expected_session:
  if any(value!=expected_session for value in ids):raise RuntimeError('CLI resumed a different session')
  return expected_session
 if len(set(ids))!=1:raise RuntimeError('Initial CLI session ID missing/ambiguous')
 return ids[0]
def cli_argv(private,session,last_message):
 args=private['resume_argv']if session else private['initial_argv'];values={'session_id':session or'','last_message_path':str(last_message)}
 return[private['executable'],*[x.format(**values)for x in args]]

class ByteLock:
 def __init__(self,path):self.path=Path(path);self.file=None
 def __enter__(self):
  import msvcrt
  self.path.parent.mkdir(parents=True,exist_ok=True);self.file=self.path.open('a+b')
  if self.path.stat().st_size==0:self.file.write(b'0');self.file.flush()
  self.file.seek(0)
  try:msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
  except BaseException:self.file.close();raise
  return self
 def __exit__(self,*args):
  import msvcrt
  try:self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
  finally:self.file.close()

class Windows:
 def __init__(self):
  if os.name!='nt':raise RuntimeError('WD Windows dispatcher required')
  self.k=ctypes.WinDLL('kernel32',use_last_error=True);k=self.k;k.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];k.OpenProcess.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p];k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];k.WaitForSingleObject.restype=ctypes.c_uint32;k.GetProcessTimes.argtypes=[ctypes.c_void_p,*([ctypes.POINTER(ctypes.c_uint64)]*4)];k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
 def identity(self,handle,pid):
  born,exited,kernel,user=[ctypes.c_uint64()for _ in range(4)]
  if not self.k.GetProcessTimes(handle,ctypes.byref(born),ctypes.byref(exited),ctypes.byref(kernel),ctypes.byref(user)):raise ctypes.WinError(ctypes.get_last_error())
  seconds,fraction=divmod(born.value,10000000);date=datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=seconds)
  return{'pid':pid,'windows_creation_filetime_100ns':born.value,'creation_time_utc':date.strftime('%Y-%m-%dT%H:%M:%S')+f'.{fraction:07d}Z'}
 def open_worker(self,worker):
  handle=self.k.OpenProcess(0x00100000|0x00001000,False,worker['pid'])
  if not handle:raise ctypes.WinError(ctypes.get_last_error())
  try:
   actual=self.identity(handle,worker['pid'])
   if worker_key(actual)!=worker_key(worker)or actual['creation_time_utc']!=worker['creation_time_utc']:raise RuntimeError('Worker PID reused or exact birth differs')
   return handle
  except BaseException:self.k.CloseHandle(handle);raise
 def wait(self,handle,milliseconds=30000):
  result=self.k.WaitForSingleObject(handle,milliseconds)
  if result==0:return True
  if result==258:return False
  raise ctypes.WinError(ctypes.get_last_error())
 def exit_code(self,handle):
  if not self.wait(handle,0):raise RuntimeError('Exit requested before retained handle signaled')
  code=ctypes.c_uint32()
  if not self.k.GetExitCodeProcess(handle,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
  return int(code.value)
 def close(self,handle):self.k.CloseHandle(handle)

class Dispatcher:
 def __init__(self,config_path,private_path,kernel=None):
  self.config=read(config_path);self.root=Path(self.config['project_root']).resolve();self.private=read(private_path)
  if self.config.get('schema')!='TREE2_EVENT_DISPATCHER_CONFIG_V1'or Path(self.private['project_root']).resolve()!=self.root or self.private.get('stdin_mode')!='utf8_prompt_file':raise RuntimeError('Dispatcher/CLI config mismatch')
  self.directory=inside(self.root,self.config['state_directory']);self.directory.mkdir(parents=True,exist_ok=True);self.handoff=inside(self.root,self.config['handoff_path']);self.kernel=kernel or Windows();self.worker=None;self.handle=None;self.session=None
  session_file=self.directory/'cli_session.json'
  if session_file.exists():self.session=str(uuid.UUID(read(session_file)['session_id']))
  self.checkpoint=self.directory/'checkpoint.json';self.status_file=self.directory/'dispatcher_status.json';self.required=self.config['required_complete_outputs'];self.owner={'pid':os.getpid()};self.owns_lock=False
 def log(self,event,**facts):
  with(self.directory/'dispatcher.jsonl').open('a',encoding='utf-8',newline='\n')as f:f.write(json.dumps({'at_utc':utc(),'event':event,**facts})+'\n');f.flush();os.fsync(f.fileno())
 def status(self,status,**facts):atomic(self.status_file,{'status':status,'updated_utc':utc(),'dispatcher_pid':os.getpid(),'AI_calls_during_wait':0,**facts})
 def load_handoff(self):return validate_handoff(self.root,read(self.handoff),self.required)
 def attach(self,worker):
  if self.handle is not None and worker_key(worker)==worker_key(self.worker):return
  new=self.kernel.open_worker(worker)
  if self.handle is not None:self.kernel.close(self.handle)
  self.handle=new;self.worker=worker;self.log('WORKER_HANDLE_RETAINED',worker=worker)
 def event(self,kind,handoff_sha,**facts):
  key={'kind':kind,'handoff_sha256':handoff_sha,'worker_identity':{k:self.worker[k]for k in('pid','creation_time_utc','windows_creation_filetime_100ns')}if self.worker else None}
  identifier=hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest();folder=self.directory/'events'/identifier;folder.mkdir(parents=True,exist_ok=True);path=folder/'event.json'
  if not path.exists():exclusive(path,{'schema':'TREE2_LOCAL_CONTINUATION_EVENT_V1','observed_utc':utc(),**key,**facts})
  result=row(self.root,path);atomic(self.checkpoint,{'status':'EVENT_PENDING','pending_event':result,'session_id':self.session});return path
 def prompt(self,event_path,event_sha):
  if self.session:
   template=self.config.get('resume_prompt_template')
   if template:text=bind(self.root,template).read_text(encoding='utf-8')
   else:text='Continue the authorized Tree2 local task from the retained session. Meaningful event: {{EVENT_PATH}} (SHA256 {{EVENT_SHA256}}). Verify its evidence, carry the authorized work to the next real worker/boundary, then atomically write a fresh event-acknowledging handoff at {{HANDOFF_PATH}}. No workchat messages, periodic polling turns, science replay or relaxed gates.'
  else:text=bind(self.root,self.config['prompt_template']).read_text(encoding='utf-8')
  for marker,value in{'{{EVENT_PATH}}':str(event_path),'{{EVENT_SHA256}}':event_sha,'{{HANDOFF_PATH}}':str(self.handoff),'{{PROJECT_ROOT}}':str(self.root)}.items():text=text.replace(marker,value)
  return text
 def accept_changed_handoff(self,before,event_sha):
  if digest(self.handoff)==before:raise RuntimeError('CLI left unchanged handoff; no automatic repeat')
  after=self.load_handoff()
  if after.get('responding_to_event_sha256')!=event_sha:raise RuntimeError('Handoff does not acknowledge exact event')
  return after
 def dispatch_once(self,event_path):
  event=read(event_path);event_sha=digest(event_path);folder=event_path.parent;result_path=folder/'cli_result.json';before=digest(self.handoff)
  if result_path.exists():
   result=read(result_path)
   if result.get('status')!='CLI_TURN_ACCEPTED'or result.get('event_sha256')!=event_sha or digest(self.handoff)!=result.get('handoff_sha256'):raise RuntimeError('Prior CLI result/handoff cannot be safely recovered')
   self.session=result['session_id'];return self.load_handoff()
  exclusive(folder/'cli_attempt.json',{'claimed_utc':utc(),'event_sha256':event_sha,'session_id':self.session,'no_retry_if_start_or_exit_unknown':True})
  exe=Path(self.private['executable'])
  if digest(exe)!=self.private['executable_sha256']:raise RuntimeError('Pinned CLI executable changed')
  prompt_path=folder/'prompt.txt';prompt_path.write_text(self.prompt(event_path,event_sha),encoding='utf-8',newline='\n');last=folder/'last-message.txt';argv=cli_argv(self.private,self.session,last);environment=os.environ.copy()
  for name in self.private['remove_environment_names']:environment.pop(name,None)
  environment.update(self.private['environment'])
  for key in('CODEX_HOME','CODEX_SQLITE_HOME','TEMP','TMP','XDG_CACHE_HOME'):
   value=Path(environment[key]).resolve()
   if not value.is_relative_to(self.root):raise RuntimeError('CLI writable path leaves project')
  self.status('AI_TURN_ACTIVE',event_sha256=event_sha,session_id=self.session);self.log('CLI_STARTING',event_sha256=event_sha,session_id=self.session)
  with prompt_path.open('rb')as stdin,(folder/'stdout.jsonl').open('wb')as stdout,(folder/'stderr.txt').open('wb')as stderr:
   child=subprocess.Popen(argv,stdin=stdin,stdout=stdout,stderr=stderr,cwd=self.root,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));identity=self.kernel.identity(int(child._handle),child.pid);atomic(folder/'cli_started.json',{'identity':identity,'event_sha256':event_sha,'started_utc':utc()});deadline=time.monotonic()+self.config['cli_timeout_seconds']
   while child.poll()is None:
    if time.monotonic()>=deadline:raise TimeoutError('CLI deadline; identity remains UNKNOWN/inflight, no duplicate/retry or science termination')
    self.kernel.wait(int(child._handle),min(30000,max(1,int((deadline-time.monotonic())*1000))))
   code=child.returncode;atomic(folder/'cli_actual_exit.json',{'identity':identity,'actual_exit_code':code,'observed_utc':utc(),'event_sha256':event_sha})
  if type(code)is not int or code!=0:raise RuntimeError('CLI actual nonzero exit; no automatic retry')
  session=parse_cli_jsonl(folder/'stdout.jsonl',self.session);after=self.accept_changed_handoff(before,event_sha);self.session=session;atomic(self.directory/'cli_session.json',{'session_id':session,'initial_event_sha256':event_sha if not(self.directory/'cli_session.json').exists()else read(self.directory/'cli_session.json')['initial_event_sha256']})
  atomic(result_path,{'status':'CLI_TURN_ACCEPTED','event_sha256':event_sha,'actual_exit_code':0,'session_id':session,'handoff_sha256':digest(self.handoff),'accepted_utc':utc()});self.log('CLI_TURN_ACCEPTED',event_sha256=event_sha,session_id=session);return after
 def transition(self,after,event):
  status=after['status']
  if status!='WAITING_WORKER':
   if event['kind']=='INITIAL_USEFUL_HANDOFF'and status=='COMPLETE':raise RuntimeError('Initial observation turn cannot finish active scientific task')
   self.status(status,reason=after.get('reason'),outputs=after.get('outputs'));atomic(self.checkpoint,{'status':status,'handoff_sha256':digest(self.handoff),'session_id':self.session});return False
  next_worker=after['worker']
  if event['kind']=='INITIAL_USEFUL_HANDOFF':
   if worker_key(next_worker)!=worker_key(self.worker):raise RuntimeError('Initial turn must keep same active worker; no concurrent science')
  elif worker_key(next_worker)==worker_key(self.worker):raise RuntimeError('Agent handed back the already-exited worker; no repeated wake')
  self.attach(next_worker);atomic(self.checkpoint,{'status':'WAITING_WORKER','handoff_sha256':digest(self.handoff),'session_id':self.session});return True
 def run(self,initial=False):
  with ByteLock(self.directory/'dispatcher.lock'):
   self.owns_lock=True
   pending=read(self.checkpoint).get('pending_event')if self.checkpoint.exists()else None
   if pending:
    path=bind(self.root,pending);event=read(path);self.worker=event['worker_identity'];after=self.dispatch_once(path)
    if not self.transition(after,event):return
   else:
    handoff=self.load_handoff()
    if handoff['status']!='WAITING_WORKER':self.status(handoff['status'],reason=handoff.get('reason'));return
    self.attach(handoff['worker'])
   if initial and not self.session:
    if self.config.get('allow_initial_useful_handoff')is not True:raise RuntimeError('Initial useful turn not granted')
    path=self.event('INITIAL_USEFUL_HANDOFF',digest(self.handoff),purpose='Verify private CLI authentication/context and same-worker handoff; no new science while worker active');after=self.dispatch_once(path)
    if not self.transition(after,read(path)):return
   while True:
    self.status('WAITING_WORKER',worker=self.worker,session_id=self.session,AI_tokens_used_by_wait=0)
    if not self.kernel.wait(self.handle,30000):continue
    code=self.kernel.exit_code(self.handle);path=self.event('WINDOWS_WORKER_EXIT_OBSERVED',digest(self.handoff),actual_exit_code=code,launch_receipt=self.worker['launch_receipt'],retained_handle_identity_verified=True);self.log('WORKER_ACTUAL_EXIT',worker=self.worker,actual_exit_code=code,event_sha256=digest(path));after=self.dispatch_once(path)
    if not self.transition(after,read(path)):return

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--cli-config',required=True);p.add_argument('--initial-turn',action='store_true');args=p.parse_args();dispatcher=None
 try:
  dispatcher=Dispatcher(args.config,args.cli_config);dispatcher.run(args.initial_turn)
 except BaseException as error:
  if dispatcher and dispatcher.owns_lock:
   dispatcher.status('BLOCKED_UNKNOWN_NO_RETRY',reason=repr(error));dispatcher.log('DISPATCHER_STOPPED_NO_RETRY',error_type=type(error).__name__,reason=str(error))
  raise
 finally:
  if dispatcher and dispatcher.handle is not None:dispatcher.kernel.close(dispatcher.handle)
if __name__=='__main__':main()
