"""Finite creation-bound units shared only by the separately admitted defence production cohort."""
from pathlib import Path
import os,time,subprocess,shutil,json
import marker_pilot_compute_v001 as g
import defence_owned_cleanup_v001 as own
from checkm1_owned_rss_sample_v001 import sample_owned_rss

class Runtime:
 def __init__(self,plan):
  self.p=plan;self.e=g.R/plan['work'];self.stop=g.R/plan['stop_path'];self.owner=own.identity(os.getpid());self.started=time.monotonic();self.science=0.;self.peak=0;self.last=0;self.done=0;self.total=len(plan['selected_accessions'])*2;self.phase='PREPARING_NOVEL_PRODUCTION_DEFENCE_COHORT';self.current=None;self.native=g.read(self.e/'native_owner.json')['native_owner'];g.save(self.e/'linux_owner.json',self.owner);os.sched_setaffinity(0,{plan['cpu']})
 def guard(self,known=(),unit_elapsed=0):
  if self.stop.exists()or(g.R/'state/STOP').exists():raise InterruptedError('Scoped defence pilot/global STOP')
  if time.time()>self.p['original_context_absolute_deadline_unix']:raise TimeoutError('Source-bound production-cohort absolute deadline')
  if time.monotonic()-self.started>self.p['cold_seconds']or self.science+unit_elapsed>self.p['science_seconds']:raise TimeoutError('Finite admitted defence pilot budget')
  if shutil.disk_usage(g.R).free<42949672960:raise RuntimeError('Backing disk below40GiB reserve')
  available=g.available()
  if available<self.p['minimum_linux_available_bytes']:raise MemoryError('Linux available headroom below admitted threshold')
  if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=self.owner['boot_id']:raise RuntimeError('Boot identity changed')
  rss=sample_owned_rss([self.owner,*known]);ram=sum(shutil.disk_usage(p).used for p in(g.R/self.p['ram_scratch'],Path('/tmp'),Path('/dev/shm')));self.peak=max(self.peak,rss+ram)
  if rss+ram>self.p['linux_RSS_plus_RAM_bytes']:raise MemoryError('Owned Linux RSS plus used private RAM exceeds allocation')
  return rss,ram,available
 def publish(self,detail,force=False,status='RUNNING',**extra):
  if not force and time.monotonic()-self.last<30:return
  rss,ram,available=self.guard();v={'id':'10','name':'Predicted antiphage defence systems','status':status,'operation':self.phase,'detail':detail,'done':self.done,'total':self.total,'unit':'real-input genome engine phases; unavailable features UNKNOWN','pid':self.native['pid'],'creation_time_utc':self.native['creation_time_utc'],'current_profile':self.current,'owned_Linux_RSS_bytes':rss,'private_RAM_used_bytes':ram,'Linux_available_bytes':available,'previous_closed_pilot_genomes_reused':5,'campaign_total_genomes':919,'cohort_novel_genomes':20,'cohort_id':self.p['cohort_id'],'all_source_taxonomy_type_QC_paralogy_holds_preserved':True,'marker_set_acceptance':'NOT_GRANTED','full_or_representative_tree_acceptance':False,'updated_utc':g.utc(),**extra}
  for target in(self.e/'progress.json',g.R/'state/stages/10.json'):
   try:g.save(target,v)
   except OSError as error:
    try:
     with(self.e/'optional_display_errors.jsonl').open('a')as log:log.write(json.dumps({'error':repr(error),'path':str(target),'at_utc':g.utc()})+'\n')
    except OSError:pass
  self.last=time.monotonic()
 def run(self,folder,args,name,input_refs,environment=None,cwd=None):
  folder.mkdir(parents=True,exist_ok=False);tmp=folder/'tmp';tmp.mkdir();g.save(folder/'command.json',{'argv':args,'inputs':input_refs,'unit':name,'started_utc':g.utc()});p=None;identity=None;known={};error=None;t=time.monotonic();peak=0;minmem=None
  env={**os.environ,'TMPDIR':str(tmp),'MAFFT_TMPDIR':str(tmp),'XDG_CACHE_HOME':str(tmp/'cache'),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
  if environment:env.update(environment)
  try:
   self.guard()
   with(folder/'stdout.txt').open('xb')as out,(folder/'stderr.txt').open('xb')as err:
    p=subprocess.Popen(args,cwd=cwd or folder,env=env,stdout=out,stderr=err,start_new_session=True);identity=own.identity(p.pid);known[p.pid]=identity
    while p.poll()is None:
     own.track_descendants(identity,known);elapsed=time.monotonic()-t;rss,ram,mem=self.guard(known.values(),elapsed);peak=max(peak,rss+ram);minmem=mem if minmem is None else min(mem,minmem)
     if elapsed>self.p['unit_seconds']:raise TimeoutError(name+' finite unit allocation')
     self.publish(name+' '+str(self.current),unit_peak_Linux_RSS_plus_RAM_bytes=peak);time.sleep(.5)
    code=p.wait()
   if code!=0:raise RuntimeError(name+' actual exit '+str(code))
  except BaseException as exc:
   error=repr(exc)
   if p is not None:g.save(folder/'failure_cleanup.json',own.cleanup_linux_helper(p,identity,known,self.stop,'DEFENCE_PILOT_'+str(os.getpid())))
   raise
  finally:
   left=[q for q in known.values()if own.current_matching(q)is not None];members=[]
   if identity is not None:
    for path in Path('/proc').iterdir():
     if not path.name.isdigit():continue
     try:
      q=own.identity(int(path.name))
      if q['process_group']==identity['process_group']:members.append(q)
     except(FileNotFoundError,ProcessLookupError):pass
   elapsed=time.monotonic()-t;self.science+=elapsed;g.save(folder/'execution.json',{'unit':name,'actual_exit_code':p.returncode if p is not None else None,'actual_child_waited_and_reaped':p is not None and p.poll()is not None,'child_identity':identity,'captured_owned_identities':list(known.values()),'remaining_owned_identities':left,'remaining_group_members':members,'group_closed':not left and not members,'elapsed_seconds':elapsed,'peak_summed_owned_Linux_RSS_plus_private_RAM_bytes':peak,'minimum_Linux_available_bytes':minmem,'error':error,'ended_utc':g.utc()})
   if(left or members)and error is None:raise RuntimeError('Owned group/descendants remain after unit')
  return g.ref(folder/'execution.json')
