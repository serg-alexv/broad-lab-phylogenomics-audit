"""Pure plus one owned non-genomic Windows child fixture; never runs Codex/WSL/science."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest,uuid
import local_tree2_dispatcher as d
R=Path(__file__).resolve().parents[1]
class Cases(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=R/'work',prefix='local_dispatcher_fixture_');self.root=Path(self.temp.name).resolve();assert self.root.is_relative_to(R/'work')
 def tearDown(self):self.assertTrue(self.root.is_relative_to(R/'work'));self.temp.cleanup()
 def launch(self):
  identity={'pid':123,'creation_time_utc':'2026-10-27T10:19:07.2151764Z','windows_creation_filetime_100ns':134375699472151764};p=self.root/'launch.json';d.atomic(p,{'native_owner':identity});return{**identity,'role':'DUMMY_METADATA_ONLY','launch_receipt':d.row(self.root,p)}
 def test_exact_launch_binding(self):
  worker=self.launch();h={'schema':d.SCHEMA,'status':'WAITING_WORKER','revision':'r1','worker':worker};self.assertEqual(d.validate_handoff(self.root,h,[])['worker'],worker)
  with self.assertRaises(RuntimeError):d.validate_handoff(self.root,{**h,'worker':{**worker,'windows_creation_filetime_100ns':1}},[])
 def test_blocked_and_both_output_completion(self):
  with self.assertRaises(RuntimeError):d.validate_handoff(self.root,{'schema':d.SCHEMA,'status':'BLOCKED','revision':'1'},[])
  outputs=[]
  for kind in('tree2_full','tree2_representative'):
   p=self.root/(kind+'.json');d.atomic(p,{'status':'VALIDATED'});outputs.append({'kind':kind,'status':'VALIDATED','validation_receipt':d.row(self.root,p)})
  h={'schema':d.SCHEMA,'status':'COMPLETE','revision':'r','outputs':outputs};self.assertEqual(d.validate_handoff(self.root,h,['tree2_full','tree2_representative'])['status'],'COMPLETE')
  with self.assertRaises(RuntimeError):d.validate_handoff(self.root,{**h,'outputs':outputs[:1]},['tree2_full','tree2_representative'])
 def test_actual_cli_json_terminal_and_session(self):
  p=self.root/'stdout.jsonl';session=str(uuid.uuid4());p.write_text(json.dumps({'type':'thread.started','thread_id':session})+'\n'+json.dumps({'type':'turn.completed'})+'\n');self.assertEqual(d.parse_cli_jsonl(p),session);self.assertEqual(d.parse_cli_jsonl(p,session),session)
  with self.assertRaises(RuntimeError):d.parse_cli_jsonl(p,str(uuid.uuid4()))
  p.write_text(json.dumps({'type':'turn.failed'})+'\n')
  with self.assertRaises(RuntimeError):d.parse_cli_jsonl(p,session)
 def test_once_claim_and_short_resume_argv(self):
  p=self.root/'claim.json';d.exclusive(p,{'event':'one'})
  with self.assertRaises(FileExistsError):d.exclusive(p,{'event':'one'})
  cfg={'executable':'codex.exe','initial_argv':['exec','-'],'resume_argv':['exec','resume','{session_id}','--output-last-message','{last_message_path}','-']};self.assertEqual(d.cli_argv(cfg,'same-session','last.txt'),['codex.exe','exec','resume','same-session','--output-last-message','last.txt','-'])
 def test_bootstrap_same_handle_and_exited_worker_no_repeat(self):
  worker=self.launch();obj=d.Dispatcher.__new__(d.Dispatcher);obj.worker=worker;obj.handle=999;obj.root=self.root;obj.directory=self.root;obj.handoff=self.root/'handoff.json';obj.checkpoint=self.root/'checkpoint.json';obj.session='S';d.atomic(obj.handoff,{'x':'y'});obj.attach=lambda value:self.assertEqual(d.worker_key(value),d.worker_key(worker));obj.status=lambda *a,**k:None
  after={'status':'WAITING_WORKER','worker':worker};self.assertTrue(obj.transition(after,{'kind':'INITIAL_USEFUL_HANDOFF'}));self.assertEqual(obj.handle,999)
  with self.assertRaises(RuntimeError):obj.transition(after,{'kind':'WINDOWS_WORKER_EXIT_OBSERVED'})
 def test_no_auth_home_artifact_reads(self):
  with self.assertRaises(RuntimeError):d.inside(self.root,'work/local_continuation/codex_home/auth.json')
 def test_windows_retained_dummy_handle_and_singleton(self):
  if os.name!='nt':self.skipTest('Windows native fixture')
  with d.ByteLock(self.root/'fixture.lock'):
   with self.assertRaises(OSError):
    with d.ByteLock(self.root/'fixture.lock'):pass
  with d.ByteLock(self.root/'fixture.lock'):pass
  env={**os.environ,'TEMP':str(self.root),'TMP':str(self.root),'PYTHONDONTWRITEBYTECODE':'1'};child=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(0.4);raise SystemExit(7)'],cwd=self.root,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
  kernel=d.Windows();identity=kernel.identity(int(child._handle),child.pid);worker={**identity,'role':'NON_GENOMIC_FIXTURE'};handle=kernel.open_worker(worker)
  try:
   self.assertTrue(kernel.wait(handle,10000));self.assertEqual(kernel.exit_code(handle),7);self.assertEqual(child.wait(timeout=1),7)
  finally:kernel.close(handle)
if __name__=='__main__':unittest.main()
