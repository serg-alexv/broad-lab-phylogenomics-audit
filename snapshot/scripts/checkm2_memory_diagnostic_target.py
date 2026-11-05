"""Engineering-only default-fork topology; module replay contains stdlib only."""
from pathlib import Path
import argparse,datetime,json,multiprocessing as mp,os,signal,sys,time,uuid

R=Path(__file__).resolve().parents[1]
STOP=False
class DiagnosticStop(Exception):pass
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main_identity():
 main=sys.modules.get('__main__');spec=getattr(main,'__spec__',None)
 return {'name':getattr(main,'__name__',None),'file':getattr(main,'__file__',None),'spec_name':getattr(spec,'name',None),'argv':list(sys.argv),'guard':'All scientific imports occur only inside explicitly called parent main; child target holds stdlib pipe only'}
def write(path,value):
 tmp=Path(path).with_name(Path(path).name+'.'+uuid.uuid4().hex+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def event(folder,sequence,name,**values):
 row={'at_utc':utc(),'sequence':sequence,'event':name,'pid':os.getpid(),**values}
 with (folder/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
 return row
def wait_command(folder,sequence):
 while True:
  if STOP:raise DiagnosticStop('Supervisor requested resource stop')
  p=folder/'command.json'
  if p.exists():
   value=json.loads(p.read_text())
   if value.get('command')=='STOP':raise DiagnosticStop('Supervisor requested resource stop')
   if value.get('sequence')==sequence and value.get('command')=='NEXT':return
  time.sleep(.05)
def stop_signal(*unused):
 global STOP
 STOP=True
def stdlib_hold_child(connection,role):
 """A process-topology proxy, never an author worker/writer or import probe."""
 try:
  connection.send({'status':'STDLIB_HOLD_CHILD_READY','role':role,'pid':os.getpid(),'main':main_identity(),'inherited_heavy_module_origins':{n:getattr(sys.modules.get(n),'__file__',None) for n in ('tensorflow','keras','sklearn','checkm2.predictQuality')},'author_callback_called':False,'scientific_imports_executed_by_child_target':False})
  if connection.recv()!='RELEASE':raise RuntimeError('Unexpected hold-child command')
 finally:connection.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=['nine_managers','protein_topology'],required=True);p.add_argument('--directory',required=True);a=p.parse_args()
 folder=Path(a.directory).resolve()
 if not folder.is_relative_to(R/'evidence/checkm2_memory_diagnostic/v001') or not folder.is_dir():raise RuntimeError('Dedicated arm workspace required')
 if mp.get_start_method(allow_none=True) is not None:raise RuntimeError('Unexpected preselected multiprocessing context')
 mp.set_start_method('fork');os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]))
 signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
 managers=[];proxies=[];children=[];sequence=0;outcome='ERROR';error=None;model=None
 event(folder,-1,'PARENT_START',arm=a.arm,start_method=mp.get_start_method(),main=main_identity(),no_genome_arguments=True)
 try:
  import checkm2_ipc_bootstrap as ipc_target
  import checkm2_effective_bootstrap as bootstrap
  import checkm2_ipc_alias as ipc
  warm=ipc_target.prewarm()
  scratch=R/'work/checkm2_memory_diagnostic'/a.arm;scratch.mkdir(parents=True,exist_ok=False)
  import tempfile
  tempfile.tempdir=str(scratch)
  proof=bootstrap.preload_and_verify();spec=bootstrap.specification()
  for row in spec['base_model_assets']:
   if ipc.sha(R/row['path'])!=row['sha256']:raise RuntimeError('Original author asset hash differs')
  from checkm2.modelProcessing import modelProcessor
  model=modelProcessor(threads=2)
  if model.general_model_comp.num_feature()!=21241 or model.model_cont.num_feature()!=21241 or model.minmax_scaler.n_features_in_!=21241 or list(model.specific_model_comp_nn.input_shape[1:])!=[20021,1]:raise RuntimeError('Exact model dimensions differ')
  event(folder,sequence,'MODELS_LOADED_HELD',bootstrap_provenance=proof,prewarmed_ipc=warm,model_types={name:type(getattr(model,name)).__name__ for name in ('general_model_comp','model_cont','specific_model_comp_nn','minmax_scaler')},models_retained=True,main=main_identity())
  wait_command(folder,sequence);sequence+=1
  maximum=9 if a.arm=='nine_managers' else 1
  for index in range(maximum):
   if STOP:raise DiagnosticStop('Resource stop before next Manager')
   manager=mp.Manager();managers.append(manager);proxy=manager.dict();proxies.append(proxy)
   proxy['tree2_engineering_sentinel']=61;assert proxy['tree2_engineering_sentinel']==61;del proxy['tree2_engineering_sentinel'];assert len(proxy)==0
   event(folder,sequence,'MANAGER_HELD',count=index+1,manager_pid=manager._process.pid,manager_address=manager.address,empty_proxy_roundtrip=True,main=main_identity())
   wait_command(folder,sequence);sequence+=1
  if a.arm=='protein_topology':
   for role in ('writer_equivalent_stdlib_hold','one_worker_equivalent_stdlib_hold'):
    parent,child=mp.Pipe();process=mp.Process(target=stdlib_hold_child,args=(child,role));process.start();child.close();children.append((process,parent))
    if not parent.poll(15):raise RuntimeError('Stdlib topology child failed ready handshake')
    ready=parent.recv()
    if ready.get('status')!='STDLIB_HOLD_CHILD_READY':raise RuntimeError('Stdlib hold-child handshake differs')
    event(folder,sequence,'STDLIB_TOPOLOGY_CHILD_HELD',count=len(children),child=ready);wait_command(folder,sequence);sequence+=1
  event(folder,sequence,'ALL_DECLARED_TOPOLOGY_HELD',managers=len(managers),stdlib_children=len(children),actual_author_worker_pickling_tested=False,full_checkm2_viability_tested=False)
  wait_command(folder,sequence);outcome='ALL_DECLARED_ENGINEERING_STEPS_RECORDED'
 except DiagnosticStop as ex:outcome='SUPERVISOR_RESOURCE_STOP_EXPECTED_ENGINEERING_OUTCOME';error=repr(ex)
 except BaseException as ex:error=repr(ex)
 finally:
  closure=[]
  for process,connection in reversed(children):
   try:connection.send('RELEASE');connection.close();process.join(5)
   except BaseException as ex:closure.append(repr(ex))
   if process.is_alive():process.terminate();process.join(3)
   if process.is_alive():process.kill();process.join(3)
   if process.exitcode!=0:closure.append('hold child exit '+str(process.exitcode))
  for manager in reversed(managers):
   try:manager.shutdown();manager._process.join(5)
   except BaseException as ex:closure.append(repr(ex))
  write(folder/'target_exit.json',{'status':outcome,'error':error,'ended_utc':utc(),'arm':a.arm,'managers_started':len(managers),'stdlib_children_started':len(children),'local_cleanup_errors':closure,'main':main_identity(),'models_retained_until_cleanup':model is not None,'author_worker_or_writer_called':False,'genomes_read':0,'prediction_or_quality_scores_produced':False,'production_acceptance':False})
 return 0 if outcome!='ERROR' else 2
if __name__=='__main__':raise SystemExit(main())
