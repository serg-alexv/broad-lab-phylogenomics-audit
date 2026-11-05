"""V2 fixtures use only synthetic metadata and owned Python dummy processes, never Codex."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest,uuid
import local_tree2_dispatcher as b
import local_tree2_dispatcher_v002 as v
R=Path(__file__).resolve().parents[1]
class Cases(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=R/'work',prefix='dispatcher_v2_fixture_');self.root=Path(self.temp.name).resolve();self.assertTrue(self.root.is_relative_to(R/'work'));self.session=str(uuid.uuid4());self.objects=[]
 def tearDown(self):
  for obj in self.objects:
   if obj.handle is not None:obj.kernel.close(obj.handle);obj.handle=None
  self.assertTrue(self.root.is_relative_to(R/'work'));self.temp.cleanup()
 def obj(self,cli_fail=False):
  seed=self.root/'old_session.json';b.atomic(seed,{'session_id':self.session});config={'schema':'TREE2_EVENT_DISPATCHER_CONFIG_V1','project_root':str(self.root),'state_directory':'state/local_continuation_v2','handoff_path':'state/local_continuation_v2/handoff.json','required_complete_outputs':['tree2_full','tree2_representative'],'existing_session':b.row(self.root,seed),'cli_timeout_seconds':10};cp=self.root/'config.json';b.atomic(cp,config)
  # This fake CLI is an owned Python process, not the Codex executable or an AI service.
  fake=self.root/'fake_cli.py';fake.write_text("import sys,time,json,subprocess,os\\n".replace('\\n','\n')+f"sys.path.insert(0,{str(R/'scripts')!r})\n"+r"""
import local_tree2_dispatcher as b
from pathlib import Path
root=Path.cwd();event=b.read(root/'event_location.json');sha=b.digest(event['path']);session=event['session']
print(json.dumps({'type':'thread.started','thread_id':session}),flush=True)
child=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(0.8);raise SystemExit(17)'],cwd=root,creationflags=subprocess.CREATE_NO_WINDOW)
k=b.Windows();identity=k.identity(int(child._handle),child.pid);launch=root/'dummy_launch.json';b.atomic(launch,{'native_owner':identity});worker={**identity,'role':'OWNED_NON_GENOMIC_DUMMY','launch_receipt':b.row(root,launch)}
b.atomic(root/'state/local_continuation_v2/handoff.json',{'schema':b.SCHEMA,'status':'WAITING_WORKER','revision':'fresh-dummy','responding_to_event_sha256':sha,'worker':worker})
time.sleep(0.35 if event['fail']else 1.5)
ack=root/'state/local_continuation_v2/early_attach_ack.json';b.atomic(root/'ack_seen_by_fake_cli.json',{'exists':ack.exists(),'matching_worker':b.read(ack)['worker']==worker if ack.exists()else False})
if event['fail']:
 print(json.dumps({'type':'turn.failed'}),flush=True);raise SystemExit(4)
child.wait(timeout=2);print(json.dumps({'type':'turn.completed'}),flush=True)
""",encoding='utf-8',newline='\n')
  env={name:str(self.root/name)for name in('CODEX_HOME','CODEX_SQLITE_HOME','TEMP','TMP','XDG_CACHE_HOME')};env['PYTHONDONTWRITEBYTECODE']='1';private={'project_root':str(self.root),'stdin_mode':'utf8_prompt_file','executable':sys.executable,'executable_sha256':b.digest(sys.executable),'initial_argv':['-B',str(fake)],'resume_argv':['-B',str(fake)],'environment':env,'remove_environment_names':[]};pp=self.root/'private_fake.json';b.atomic(pp,private);obj=v.Dispatcher(cp,pp);self.objects.append(obj);return obj
 def event(self,obj,fail=False):
  path=obj.event('ROOT_REVIEWED_RECOVERY_EVENT',None,no_live_worker_claimed=True);b.atomic(self.root/'event_location.json',{'path':str(path),'session':self.session,'fail':fail});return path
 def test_fast_worker_retained_before_longer_fake_cli_finishes(self):
  obj=self.obj();path=self.event(obj);after=obj.dispatch_once(path);handle=obj.handle
  self.assertTrue(b.read(self.root/'ack_seen_by_fake_cli.json')['matching_worker']);self.assertEqual(obj.kernel.exit_code(handle),17);self.assertIsNotNone(obj.early_worker_exit);self.assertTrue(obj.transition(after,b.read(path)));self.assertEqual(obj.handle,handle)
  # Accepted event recovery returns the saved result; it does not invoke any second process.
  self.assertEqual(obj.dispatch_once(path)['worker'],after['worker']);self.assertEqual(len(list(path.parent.glob('cli_attempt.json'))),1)
 def test_cli_error_preserves_actual_worker_exit_before_block_and_no_retry(self):
  obj=self.obj();path=self.event(obj,True)
  with self.assertRaises(RuntimeError):obj.dispatch_once(path)
  proof=b.read(b.bind(self.root,obj.early_worker_exit));self.assertEqual(proof['actual_exit_code'],17);p=path.parent/'cli_error_worker_observation.json';original=b.digest(p)
  with self.assertRaises(FileExistsError):obj.dispatch_once(path)
  self.assertEqual(b.digest(p),original);self.assertEqual(b.read(path.parent/'cli_actual_exit.json')['actual_exit_code'],4)
 def test_event_mismatch_and_changed_worker_rejected_before_attach(self):
  obj=self.obj();identity={'pid':123,'windows_creation_filetime_100ns':123,'creation_time_utc':'dummy'};launch=self.root/'metadata_launch.json';b.atomic(launch,identity);worker={**identity,'role':'METADATA_ONLY','launch_receipt':b.row(self.root,launch)};event={'kind':'ROOT_REVIEWED_RECOVERY_EVENT','worker_identity':None};sha='a'*64;after={'schema':b.SCHEMA,'status':'WAITING_WORKER','revision':'x','responding_to_event_sha256':'wrong','worker':worker};b.atomic(obj.handoff,after);calls=[];obj.attach=lambda value:calls.append(value)
  with self.assertRaises(RuntimeError):obj.early_handoff(None,event,sha)
  self.assertEqual(calls,[]);after['responding_to_event_sha256']=sha;b.atomic(obj.handoff,after);obj.early_handoff(None,event,sha);obj.worker=worker;obj.early_handoff(None,event,sha);self.assertEqual(len(calls),1)
  second={**identity,'pid':124};b.atomic(launch,second);after['worker']={**second,'role':'METADATA_ONLY','launch_receipt':b.row(self.root,launch)};b.atomic(obj.handoff,after)
  with self.assertRaises(RuntimeError):obj.early_handoff(None,event,sha)
 def test_transition_compares_event_worker_not_already_attached_next(self):
  obj=self.obj();old={'pid':1,'windows_creation_filetime_100ns':10};new={'pid':2,'windows_creation_filetime_100ns':20};obj.worker=new;obj.handle=object();obj.kernel.close=lambda value:None;obj.attach=lambda worker:self.assertEqual(worker,new);b.atomic(obj.handoff,{'synthetic':'metadata'});self.assertTrue(obj.transition({'status':'WAITING_WORKER','worker':new},{'kind':'WINDOWS_WORKER_EXIT_OBSERVED','worker_identity':old}))
  with self.assertRaises(RuntimeError):obj.transition({'status':'WAITING_WORKER','worker':old},{'kind':'WINDOWS_WORKER_EXIT_OBSERVED','worker_identity':old})
 def test_explicit_recovery_seed_requires_closed_binding_session_and_no_live_worker(self):
  review=self.root/'review.json';b.atomic(review,{'review':'synthetic'});seed={'schema':'TREE2_ROOT_REVIEWED_RECOVERY_EVENT_V2','recovery_event_authorized':True,'no_live_worker_claimed':True,'worker_identity':None,'existing_cli_session_id':self.session,'scientific_replay_authorized':False,'historical_claims_preserved':True,'reason':'Synthetic closed event','root_review':b.row(self.root,review),'closed_evidence':[b.row(self.root,review)]};p=self.root/'seed.json';b.atomic(p,seed);self.assertEqual(v.recovery_seed(self.root,p,b.digest(p),self.session),seed)
  seed['worker_identity']={'pid':123};b.atomic(p,seed)
  with self.assertRaises(RuntimeError):v.recovery_seed(self.root,p,b.digest(p),self.session)
if __name__=='__main__':unittest.main()
