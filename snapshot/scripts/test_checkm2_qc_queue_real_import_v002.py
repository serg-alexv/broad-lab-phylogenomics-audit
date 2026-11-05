"""REAL source imports and two real configure/coordinator cycles, mock science."""
from pathlib import Path
import argparse,ast,hashlib,importlib,importlib.abc,importlib.util,json,os,sys,tempfile,types

R=Path(__file__).resolve().parents[1]
def main(a):
 root=R/a.candidate
 with tempfile.TemporaryDirectory(dir=R/'work',prefix='bulk_real_import_v002_')as temporary:
  allowed=Path(temporary).resolve();blocked=[];observed=[];written=[]
  # Only unavailable POSIX modules are substituted, not project dependencies.
  if os.name=='nt':
   for name in('fcntl','resource'):
    stub=types.ModuleType(name)
    for key in('LOCK_EX','LOCK_NB','LOCK_UN','RLIMIT_AS','RLIMIT_DATA','RLIMIT_CPU'):setattr(stub,key,0)
    def prohibited(*args,**kwargs):raise AssertionError('No POSIX locks/resources may execute in real-import fixture')
    stub.flock=prohibited;stub.setrlimit=prohibited;sys.modules[name]=stub
  class SourceFinder(importlib.abc.MetaPathFinder):
   def find_spec(self,fullname,path=None,target=None):
    if fullname.split('.')[0]in('numpy','pandas','tensorflow','keras','lightgbm','sklearn','checkm2'):
     blocked.append(fullname);raise AssertionError('Scientific import forbidden in source fixture: '+fullname)
    candidate=root/(fullname+'.py')
    if candidate.is_file():return importlib.util.spec_from_file_location(fullname,candidate)
    return None
  owner_plan=allowed/'owner_plan.json';owner_plan.write_text(json.dumps({'schema':'TREE2_CONTINUOUS_QC_RUNTIME_PLAN_V001'}))
  sys.meta_path.insert(0,SourceFinder());sys.path.insert(0,str(R/'scripts'));sys.dont_write_bytecode=True
  sys.argv=['real-import-fixture','--input-plan',owner_plan.relative_to(R).as_posix(),'--input-plan-sha256',hashlib.sha256(owner_plan.read_bytes()).hexdigest(),'--launch-token','TOY','--helper-deadline-unix','9999999999']
  def audit(event,args):
   if event in('subprocess.Popen','os.system','os.fork','os.exec','os.kill','os.killpg','socket.connect','socket.bind'):
    raise AssertionError('Process/network/signal operation forbidden: '+event)
   if event=='open'and isinstance(args[0],(str,bytes,os.PathLike)):
    p=Path(os.fsdecode(args[0]));text=str(p).lower().replace('\\','/')
    if '/codex_home/'in text or p.suffix.lower()in('.faa','.fna','.gff','.tsv','.pkl','.dmnd','.img'):raise AssertionError('Real scientific/private artifact read forbidden: '+str(p))
    mode=args[1];flags=args[2]
    writing=(isinstance(mode,str)and any(k in mode for k in('w','a','x','+')))or(isinstance(flags,int)and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if writing and not p.resolve().is_relative_to(allowed):raise AssertionError('Write outside isolated toy fixture: '+str(p))
  sys.addaudithook(audit)
  names=['common','inner','observer','shared_producer','shared_validate','shared_controls','feature_validator','serial_provider','batch_project'];modules={}
  for short in names:
   name='checkm2_qc_queue_'+short+'_v001';modules[short]=importlib.import_module(name);observed.append({'module':name,'actual_file':str(Path(modules[short].__file__).relative_to(R))})
  c=modules['common'];inner=modules['inner'];pilot=inner.pilot
  for name in('E','OUT','STATE','STEP','LAUNCH','ADMISSION','STOP','UNRESOLVED_HANDOFF'):assert isinstance(getattr(c,name),Path),name
  before_pilot=(pilot.OUT,pilot.STATE,pilot.legacy.OUT,pilot.legacy.STATE,pilot.legacy.stop_gate)
  assert pilot.legacy.stop_gate is inner.original_stop,'Import mutated the owner stop hook'
  synthetic={};root_request={'protocol_admission':{'path':str(allowed/'Root_phase.json'),'sha256':'phase','bytes':1}}
  common_phase_limits={'per_input_annotation_seconds':180,'per_input_resume_seconds':600,'per_input_validation_seconds':120,'per_input_scientific_seconds':900,'shared_search_seconds':10800,'shared_search_validation_seconds':3600,'shared_control_comparison_seconds':120,'batch_stock_seconds':600,'batch_projection_seconds':1200,'cohort_scientific_seconds':31620}
  c.path=lambda value:Path(value);c.sha=lambda p:synthetic[Path(p)]['sha'];c.bind=lambda ref:Path(ref['path'])
  c.read=lambda p:synthetic[Path(p)]['value'];c.row=lambda p:{'path':str(p),'sha256':'toy','bytes':1}
  c.save=lambda p,v:written.append((Path(p),v))
  c.budget=lambda run:{'known_limit_exceeded':False};c.manifest=lambda run:{'path':str(run/'manifest.json')}
  # The real plan-gate's scientific/authority checks are outside this import/path
  # test. The real configure implementation and full run_cohort are executed.
  def gate(p,sha,*args,**kwargs):return c.configure(p,sha),{'inputs':[]},{}
  c.plan_gate=gate;c.reset_closed_cohort=lambda run:(setattr(c,'PLAN_PATH',None),setattr(c,'PLAN_SHA',None))
  c.unit_closed=lambda unit:True
  pilot.legacy.stat=lambda pid:{'pid':pid,'creation_ticks':1,'boot_id':'TOY','parent_pid':1}
  def no_science(plan,recipe,runtime,run,state):
   assert all(p.resolve().is_relative_to(allowed)for p in(c.OUT,c.STEP,pilot.OUT,pilot.STATE,pilot.legacy.OUT,pilot.legacy.STATE))
   assert pilot.OUT==c.OUT and pilot.STATE==c.STEP and pilot.legacy.OUT==c.OUT and pilot.legacy.STATE==c.STEP
   assert pilot.LAUNCH is inner.LAUNCH and pilot.legacy.LAUNCH is inner.LAUNCH
   assert pilot.legacy.stop_gate is inner.stop
   request=inner.base_request(plan,recipe,allowed/'accepted_prefix')
   command=inner.command_for(allowed/'accepted_prefix','checkm2_qc_queue_feature_validator_v001.py',allowed/'request.json',run/'own_feature.json')
   assert request['input_plan']==plan['_row']and request['runtime_prefix']==str(allowed/'accepted_prefix')
   assert request['protocol_admission']['path']==str(c.ADMISSION)
   assert command[-1]==str(run/'own_feature.json')and '--request-sha256'in command
   state.update(shared_reference={},qualification={},initial_profile={})
  inner.execute_phases=no_science
  real_sha=c.sha;c.sha=lambda p:'toy'if Path(p)==allowed/'request.json'else real_sha(p)
  for index in range(2):
   p=allowed/f'plan{index}.json';run=allowed/f'cohort{index}';rootref={'path':str(allowed/'parent_request.json'),'sha256':'root','bytes':1}
   synthetic[Path(rootref['path'])]={'sha':'root','value':root_request};synthetic[allowed/'Root_phase.json']={'sha':'phase','value':{'scoped_stop':str(allowed/'STOP')}}
   synthetic[p]={'sha':'plan'+str(index),'value':{'schema':'TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003','cohort_id':'cohort00'+str(index),'cohort_index':index,'accessions':['GCF_000000001.1']*0+[f'GCF_{n:09d}.1'for n in range(17)],'controls':[{}],'limits':dict(common_phase_limits),'parent_runtime_request':rootref,'run_directory':str(run),'source_manifest':{},'selected_inputs':{},'method_amendment':{}}}
   launch={'token':'toy'+str(index),'pid':1,'creation_time_utc':'TOY','input_plan_sha256':'plan'+str(index),'protocol_admission_sha256':'phase'}
   inner.run_cohort({'path':str(p),'sha256':'plan'+str(index),'bytes':1},{},launch,1e20,lambda *a,**kw:None,lambda:None,lambda:1e20,lambda ref:None)
   assert c.OUT==run and pilot.OUT==run and pilot.legacy.OUT==run
  assert written and all(p.resolve().is_relative_to(allowed)for p,v in written)
  assert not blocked and not any(n.split('.')[0]in('numpy','pandas','tensorflow','keras','lightgbm','sklearn','checkm2')for n in sys.modules)
  print(json.dumps({'status':'REAL_COMPLETE_IMPORT_AND_TWO_CONFIGURE_COORDINATOR_CYCLES_PASS','modules':observed,'platform_stubs_only':['fcntl','resource']if os.name=='nt'else[],'configured_cycles':2,'command_request_output_step_destinations_verified':True,'writes_to_old_destinations':0,'model_or_biological_reads_or_processes':0,'frozen36_edited':False,'mocked_scientific_work':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',default='work/checkm2_bulk_import_repair_v002_r002');main(p.parse_args())
