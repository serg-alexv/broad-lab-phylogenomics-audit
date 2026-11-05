"""V2 event dispatcher: retain next worker during the CLI turn; no scientific dispatch."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time,uuid
import local_tree2_dispatcher as b

BASE_SHA256='d87584a33086593b773ef7f2478ae56a970eb62985b0c2a7161349e453bc32f1'

def recovery_seed(root,path,sha,session):
 path=b.inside(root,path)
 if b.digest(path)!=sha:raise RuntimeError('Recovery seed SHA mismatch')
 seed=b.read(path)
 if seed.get('schema')!='TREE2_ROOT_REVIEWED_RECOVERY_EVENT_V2' or seed.get('recovery_event_authorized')is not True or seed.get('no_live_worker_claimed')is not True or seed.get('worker_identity')is not None:raise RuntimeError('Explicit Root-reviewed recovery event required; no invented live worker')
 if seed.get('existing_cli_session_id')!=session or seed.get('scientific_replay_authorized')is not False or seed.get('historical_claims_preserved')is not True:raise RuntimeError('Recovery session/claim/no-replay binding mismatch')
 if not seed.get('reason')or not seed.get('closed_evidence'):raise RuntimeError('Recovery reason and actual closed evidence required')
 b.bind(root,seed['root_review'])
 for evidence in seed['closed_evidence']:b.bind(root,evidence)
 return seed

class Dispatcher(b.Dispatcher):
 def __init__(self,*args,**kwargs):
  if b.digest(Path(b.__file__))!=BASE_SHA256:raise RuntimeError('Original dispatcher helpers changed')
  super().__init__(*args,**kwargs)
  if self.config['state_directory']!='state/local_continuation_v2'or self.config['handoff_path']!='state/local_continuation_v2/handoff.json':raise RuntimeError('V2 requires a separate immutable-history namespace')
  seed=b.read(b.bind(self.root,self.config['existing_session']))
  existing=str(uuid.UUID(seed['session_id']))
  if self.session and self.session!=existing:raise RuntimeError('V2 cannot replace the explicit retained CLI session')
  self.session=existing;self.early_event_sha=None;self.early_handoff_sha=None;self.early_worker_exit=None
 def early_handoff(self,before,event,event_sha):
  if not self.handoff.exists():return
  current=b.digest(self.handoff)
  if current==before or current==self.early_handoff_sha:return
  after=self.accept_changed_handoff(before,event_sha)
  if after['status']!='WAITING_WORKER':return
  worker=after['worker'];previous=event.get('worker_identity')
  if previous and b.worker_key(worker)==b.worker_key(previous)and event['kind']!='INITIAL_USEFUL_HANDOFF':raise RuntimeError('Event handed back its already-exited worker')
  if event['kind']=='INITIAL_USEFUL_HANDOFF'and previous and b.worker_key(worker)!=b.worker_key(previous):raise RuntimeError('Initial observation cannot change scientific owner')
  if self.early_event_sha==event_sha and self.worker and b.worker_key(worker)!=b.worker_key(self.worker):raise RuntimeError('One event cannot publish two different next-worker identities')
  self.attach(worker);self.early_event_sha=event_sha;self.early_handoff_sha=current
  acknowledgment={'schema':'TREE2_DISPATCHER_EARLY_ATTACH_ACK_V2','status':'WAITING_WORKER','event_sha256':event_sha,'handoff_sha256':current,'worker':worker,'dispatcher_pid':os.getpid(),'observed_utc':b.utc(),'CLI_turn_still_active':True,'exact_handle_retained':True}
  b.atomic(self.directory/'early_attach_ack.json',acknowledgment)
  self.status('WAITING_WORKER',worker=worker,event_sha256=event_sha,handoff_sha256=current,CLI_turn_still_active=True,exact_handle_retained=True,session_id=self.session)
  self.log('NEXT_WORKER_RETAINED_DURING_CLI',**acknowledgment)
 def observe_early_exit(self,folder,event_sha):
  if self.early_event_sha!=event_sha or self.handle is None or not self.kernel.wait(self.handle,0):return None
  if self.early_worker_exit is None:
   proof={'schema':'TREE2_RETAINED_WORKER_ACTUAL_EXIT_V2','worker_identity':self.worker,'actual_exit_code':self.kernel.exit_code(self.handle),'exact_birth_handle_retained':True,'observed_utc':b.utc(),'during_cli_event_sha256':event_sha}
   p=folder/'early_worker_actual_exit.json';b.atomic(p,proof);self.early_worker_exit=b.row(self.root,p);self.log('EARLY_RETAINED_WORKER_ACTUAL_EXIT',**proof)
  return self.early_worker_exit
 def drain_after_cli_error(self,folder,event_sha,error):
  if self.early_event_sha!=event_sha or self.handle is None:return
  self.status('PASSIVE_WAITING_WORKER_AFTER_CLI_ERROR',worker=self.worker,reason=repr(error),AI_retry_authorized=False)
  while not self.kernel.wait(self.handle,30000):pass
  proof=self.observe_early_exit(folder,event_sha)
  evidence_path=folder/'cli_error_worker_observation.json'
  if not evidence_path.exists():b.exclusive(evidence_path,{'status':'CLI_ERROR_WORKER_ACTUAL_EXIT_PRESERVED_NO_RETRY','original_error':{'type':type(error).__name__,'message':str(error)},'worker_actual_exit':proof,'science_killed':False,'AI_retry_authorized':False})
  self.status('BLOCKED_NO_AI_RETRY_AFTER_ACTUAL_WORKER_EXIT',worker=self.worker,worker_actual_exit=proof,reason=repr(error))
 def dispatch_once(self,event_path):
  event=b.read(event_path);event_sha=b.digest(event_path);folder=event_path.parent
  try:return self._dispatch_once(event_path,event,event_sha,folder)
  except BaseException as error:
   self.drain_after_cli_error(folder,event_sha,error)
   raise
 def _dispatch_once(self,event_path,event,event_sha,folder):
  result_path=folder/'cli_result.json';before=b.digest(self.handoff)if self.handoff.exists()else None
  if result_path.exists():
   result=b.read(result_path)
   if result.get('status')!='CLI_TURN_ACCEPTED'or result.get('event_sha256')!=event_sha or not self.handoff.exists()or b.digest(self.handoff)!=result.get('handoff_sha256'):raise RuntimeError('Prior CLI result/handoff cannot be recovered')
   if result['session_id']!=self.session:raise RuntimeError('Prior turn used a different CLI session')
   return self.load_handoff()
  b.exclusive(folder/'cli_attempt.json',{'claimed_utc':b.utc(),'event_sha256':event_sha,'session_id':self.session,'no_retry_if_start_or_exit_unknown':True})
  if b.digest(Path(self.private['executable']))!=self.private['executable_sha256']:raise RuntimeError('Pinned CLI executable changed')
  prompt_path=folder/'prompt.txt';prompt_path.write_text(self.prompt(event_path,event_sha),encoding='utf-8',newline='\n');last=folder/'last-message.txt';argv=b.cli_argv(self.private,self.session,last);environment=os.environ.copy()
  for name in self.private['remove_environment_names']:environment.pop(name,None)
  environment.update(self.private['environment'])
  for key in('CODEX_HOME','CODEX_SQLITE_HOME','TEMP','TMP','XDG_CACHE_HOME'):
   if not Path(environment[key]).resolve().is_relative_to(self.root):raise RuntimeError('CLI writable path leaves project')
  self.status('AI_TURN_ACTIVE',event_sha256=event_sha,session_id=self.session);self.log('CLI_STARTING',event_sha256=event_sha,session_id=self.session)
  with prompt_path.open('rb')as stdin,(folder/'stdout.jsonl').open('wb')as stdout,(folder/'stderr.txt').open('wb')as stderr:
   child=subprocess.Popen(argv,stdin=stdin,stdout=stdout,stderr=stderr,cwd=self.root,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));identity=self.kernel.identity(int(child._handle),child.pid);b.atomic(folder/'cli_started.json',{'identity':identity,'event_sha256':event_sha,'started_utc':b.utc()});deadline=time.monotonic()+self.config['cli_timeout_seconds']
   while child.poll()is None:
    self.early_handoff(before,event,event_sha);self.observe_early_exit(folder,event_sha)
    if time.monotonic()>=deadline:raise TimeoutError('CLI deadline; no duplicate/retry or science termination')
    self.kernel.wait(int(child._handle),min(250,max(1,int((deadline-time.monotonic())*1000))))
   code=child.returncode;b.atomic(folder/'cli_actual_exit.json',{'identity':identity,'actual_exit_code':code,'observed_utc':b.utc(),'event_sha256':event_sha})
  self.early_handoff(before,event,event_sha);self.observe_early_exit(folder,event_sha)
  if type(code)is not int or code!=0:raise RuntimeError('CLI actual nonzero exit; no automatic retry')
  session=b.parse_cli_jsonl(folder/'stdout.jsonl',self.session);after=self.accept_changed_handoff(before,event_sha)
  session_file=self.directory/'cli_session.json'
  if not session_file.exists():b.exclusive(session_file,{'session_id':session,'existing_session_seed':self.config['existing_session'],'first_V2_event_sha256':event_sha})
  b.atomic(result_path,{'status':'CLI_TURN_ACCEPTED','event_sha256':event_sha,'actual_exit_code':0,'session_id':session,'handoff_sha256':b.digest(self.handoff),'accepted_utc':b.utc(),'early_worker_actual_exit':self.early_worker_exit});self.log('CLI_TURN_ACCEPTED',event_sha256=event_sha,session_id=session);return after
 def transition(self,after,event):
  if after['status']!='WAITING_WORKER':return super().transition(after,event)
  next_worker=after['worker'];previous=event.get('worker_identity')
  if event['kind']=='INITIAL_USEFUL_HANDOFF':
   if previous and b.worker_key(next_worker)!=b.worker_key(previous):raise RuntimeError('Initial turn must keep the event worker')
  elif previous and b.worker_key(next_worker)==b.worker_key(previous):raise RuntimeError('Agent handed back the event already-exited worker')
  self.attach(next_worker)
  b.atomic(self.checkpoint,{'status':'WAITING_WORKER','handoff_sha256':b.digest(self.handoff),'session_id':self.session})
  return True
 def run(self,recovery_path=None,recovery_sha=None):
  with b.ByteLock(self.directory/'dispatcher.lock'):
   self.owns_lock=True
   if recovery_path:
    seed=recovery_seed(self.root,recovery_path,recovery_sha,self.session)
    if self.checkpoint.exists():raise RuntimeError('Recovery namespace already claimed; no second recovery event')
    event_path=self.event('ROOT_REVIEWED_RECOVERY_EVENT',b.digest(self.handoff)if self.handoff.exists()else None,recovery_seed=b.row(self.root,Path(recovery_path).resolve()),reason=seed['reason'],no_live_worker_claimed=True)
    after=self.dispatch_once(event_path)
    if not self.transition(after,b.read(event_path)):return
   else:
    if self.checkpoint.exists()and b.read(self.checkpoint).get('pending_event'):raise RuntimeError('Interrupted V2 event requires separate Root-reviewed recovery; no AI replay')
    after=self.load_handoff()
    if after['status']!='WAITING_WORKER':self.status(after['status'],reason=after.get('reason'));return
    self.attach(after['worker'])
   while True:
    self.status('WAITING_WORKER',worker=self.worker,session_id=self.session,AI_tokens_used_by_wait=0)
    if not self.kernel.wait(self.handle,30000):continue
    code=self.kernel.exit_code(self.handle);event_path=self.event('WINDOWS_WORKER_EXIT_OBSERVED',b.digest(self.handoff),actual_exit_code=code,launch_receipt=self.worker['launch_receipt'],retained_handle_identity_verified=True);self.log('WORKER_ACTUAL_EXIT',worker=self.worker,actual_exit_code=code,event_sha256=b.digest(event_path))
    self.early_event_sha=None;self.early_handoff_sha=None;self.early_worker_exit=None
    after=self.dispatch_once(event_path)
    if not self.transition(after,b.read(event_path)):return

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--cli-config',required=True);p.add_argument('--recovery-event');p.add_argument('--recovery-event-sha256');args=p.parse_args();dispatcher=None
 if bool(args.recovery_event)!=bool(args.recovery_event_sha256):p.error('Recovery event path and SHA are required together')
 try:
  dispatcher=Dispatcher(args.config,args.cli_config);dispatcher.run(args.recovery_event,args.recovery_event_sha256)
 except BaseException as error:
  if dispatcher and dispatcher.owns_lock:dispatcher.status('BLOCKED_UNKNOWN_NO_RETRY',reason=repr(error));dispatcher.log('DISPATCHER_STOPPED_NO_RETRY',error_type=type(error).__name__,reason=str(error))
  raise
 finally:
  if dispatcher and dispatcher.handle is not None:dispatcher.kernel.close(dispatcher.handle)
if __name__=='__main__':main()
