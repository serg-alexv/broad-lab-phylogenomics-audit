"""Synthetic-only resource-option diagnostic; no campaign sequence/database/model/image access."""
from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,os,random,shutil,subprocess,sys,time,uuid
import checkm2_unit_observer_S1R2 as observer
R=Path(__file__).resolve().parents[1]
E=R/'evidence/checkm2_phase_separated_P20/index_chunks_synthetic_review_R2_v001'
W=R/'work/checkm2_P20_index_chunks_synthetic_R2_v001'
BEGAN=time.monotonic();LAST=0
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 with tmp.open('x',encoding='utf-8')as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def inside(p):
 p=Path(p);p=(p if p.is_absolute()else R/p).resolve()
 if not p.is_relative_to(R):raise RuntimeError('Fixture path outside project')
 return p
def bind(x):
 p=inside(x['path'])
 if sha(p)!=x['sha256'] or p.stat().st_size!=x['bytes']:raise RuntimeError('Source/admission binding changed')
 return p
def row(p):return {'path':Path(p).relative_to(R).as_posix(),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def stat(pid):
 fields=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'parent_pid':int(fields[1]),'process_group':int(fields[2]),'creation_ticks':int(fields[19]),'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def available():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
def gate():
 if time.monotonic()-BEGAN>180:raise TimeoutError('Finite synthetic review controller')
 if (R/'state/STOP').exists()or(R/'state/STOP_CHECKM2_PILOT').exists():raise InterruptedError('Project scientific STOP')
 if shutil.disk_usage(R).free<40*1024**3 or available()<1024**3:raise RuntimeError('RESOURCE_GATE reserve/headroom')
def progress(status,detail,**extra):
 global LAST
 if time.monotonic()-LAST<30:return
 LAST=time.monotonic();save(E/'step.json',{'status':status,'detail':'Synthetic-only DIAMOND resource diagnostic: '+detail,'updated_utc':utc(),'native_linux_identity':stat(os.getpid()),'production_or_genome_acceptance':False,**extra})
def load_grant(a):
 path=inside(a.admission)
 if sha(path)!=a.admission_sha256:raise RuntimeError('Synthetic-only authority SHA differs')
 g=read(path)
 if g['status']!='ROOT_ADMITTED_ONE_SYNTHETIC_INDEX_CHUNKS_DIAGNOSTIC' or g['campaign_genome_or_database_access_authorized']is not False or g['runtime_image_mount_authorized']is not False:raise RuntimeError('Exact synthetic-only admission required')
 for x in g['bound_sources']:bind(x)
 bind(g['binary']);return g
def commands(a,g):
 # All nucleotide/protein text below is deterministic synthetic material generated here.
 gate();W.mkdir(exist_ok=False);(W/'tmp').mkdir()
 db_faa=W/'SYNTHETIC_TARGETS.faa';query=W/'SYNTHETIC_QUERY.faa'
 for key,dest in(('prior_synthetic_targets',db_faa),('prior_synthetic_query',query)):
  source=bind(g[key]);shutil.copyfile(source,dest)
  if sha(source)!=sha(dest):raise RuntimeError('Saved synthetic fixture copy differs')
 def fasta_ids(path):return [line[1:].split()[0]for line in path.read_text().splitlines()if line.startswith('>')]
 targets=[(x,None)for x in fasta_ids(db_faa)];queries=[(x,None)for x in fasta_ids(query)]
 if len(targets)!=50 or len(queries)!=36:raise RuntimeError('Exact previously generated synthetic inventory required')
 binary=bind(g['binary']);env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TMPDIR=str(W/'tmp'),TMP=str(W/'tmp'),TEMP=str(W/'tmp'),XDG_CACHE_HOME=str(W/'cache'),XDG_CONFIG_HOME=str(W/'config'))
 history=[{**rec,'reused_prior_source_probe':True}for rec in read(bind(g['prior_source_probes']))]
 for rec in history:
  if rec['actual_exit_code']!=0 or rec['name']not in ('version','help') or inside(rec['command'][0])!=binary:raise RuntimeError('Exact prior source-probe0 provenance required')
  bind(rec['stdout']);bind(rec['stderr'])
 def call(name,argv):
  gate();folder=W/name;folder.mkdir(exist_ok=False);outpath=folder/'stdout.txt';errpath=folder/'stderr.txt';start=utc()
  with outpath.open('w')as out,errpath.open('w')as err:
   child=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err);identity=stat(child.pid)
   try:code=child.wait(timeout=20)
   except subprocess.TimeoutExpired:
    save(E/'command_timeout.json',{'command':argv,'child_creation_identity':identity,'actual_exit':'UNKNOWN_PENDING_OBSERVER_OWNED_GROUP_CLEANUP'});raise
  rec={'name':name,'command':argv,'child_creation_identity':identity,'actual_exit_code':code,'retained_Popen_wait_observed':True,'started_utc':start,'ended_utc':utc(),'stdout':row(outpath),'stderr':row(errpath)};history.append(rec);save(E/'actual_command_exits.json',history)
  if code!=0:raise RuntimeError('Synthetic command failed '+name+' actual'+str(code))
  return outpath.read_text()
 # Keep the observed Python command group alive long enough for an actual RSS/birth sample.
 time.sleep(.4)
 version=bind(history[0]['stdout']).read_text();general_help=bind(history[1]['stdout']).read_text()
 if 'Possible [OPTIONS] for COMMAND can be seen with syntax: diamond COMMAND'not in general_help:raise RuntimeError('Saved actual general help contract differs')
 help_text=call('blastp_help',[str(binary),'blastp'])
 if '2.1.11'not in version or '--index-chunks'not in help_text or 'number of chunks for index processing'not in help_text:raise RuntimeError('Pinned binary/help resource-option authority differs')
 call('makedb',[str(binary),'makedb','--in',str(db_faa),'--db',str(W/'SYNTHETIC_DB'),'--threads','1','--quiet'])
 db=W/'SYNTHETIC_DB.dmnd'
 if not db.is_file():raise RuntimeError('Synthetic database missing')
 arms=[];canonical={};qids={name for name,seq in queries};tids={name for name,seq in targets}
 for name,chunks in(('original_default',None),('explicit4',4),('explicit8',8),('explicit16',16)):
  output=W/(name+'.tsv');scratch=W/(name+'_tmp');scratch.mkdir()
  argv=[str(binary),'blastp','--outfmt','6','--max-target-seqs','1','--query',str(query),'-o',str(output),'--threads','1','--db',str(db),'--query-cover','80','--subject-cover','80','--id','30','--evalue','1e-05','--block-size','0.5','--tmpdir',str(scratch),'--quiet']
  if chunks is not None:argv+=['--index-chunks',str(chunks)]
  call(name,argv);lines=[line.split('\t')for line in output.read_text().splitlines()if line.strip()]
  if not lines or any(len(x)!=12 or x[0]not in qids or x[1]not in tids for x in lines):raise RuntimeError('Synthetic own-ID full12field search output invalid')
  if {x[0]for x in lines}!=qids:raise RuntimeError('Synthetic exact and mutated positives were not all found; no absent-to-negative inference')
  for x in lines:
   for value in x[2:]:float(value)
  canonical[name]=sorted(tuple(x)for x in lines);arms.append({'name':name,'index_chunks':chunks,'all_other_scientific_arguments_unchanged':True,'output':row(output),'rows':len(lines),'own_synthetic_queries_found':len({x[0]for x in lines}),'canonical_12field_rows_sha256':hashlib.sha256(json.dumps(canonical[name],separators=(',',':')).encode()).hexdigest()})
 comparisons={name:{'all_full_12field_rows_equal':rows==canonical['original_default'],'difference_rows':len(set(rows)^set(canonical['original_default']))}for name,rows in canonical.items()}
 result={'schema':'TREE2_SYNTHETIC_DIAMOND_INDEX_CHUNKS_COMPARISON_V001','status':'SYNTHETIC_RESOURCE_OPTION_COMPARISON_RECORDED_REQUIRES_ROOT_REVIEW','at_utc':utc(),'binary':g['binary'],'native_DIAMOND_version_stdout':version.strip(),'binary_help':history[2]['stdout'],'prior_source_probes_reused':g['prior_source_probes'],'prior_failed_synthetic_unit':g['prior_failed_synthetic_unit'],'old_unit_seconds_charged':1.850778309002635,'new_unit_seconds_max':118.14922169099736,'synthetic_material_only':True,'seed':10272026,'synthetic_query':row(query),'synthetic_targets':row(db_faa),'synthetic_database':row(db),'duplicate_target_tie_cases_included':True,'own_synthetic_queries':len(queries),'arms':arms,'exact_full_field_comparisons_no_tolerance':comparisons,'all_actual_commands':history,'all_commands_actual0':all(x['actual_exit_code']==0 for x in history),'unchanged_block_size':0.5,'unchanged_threads':1,'no_author_model_or_real_database_loaded':True,'accepted_genome_phase_replay':False,'actual_genome_or_panel_numerical_equivalence':'NOT_ESTABLISHED_BY_SYNTHETIC_FIXTURE','full_own_feature_validation_still_required_for_each_future_genome':True,'production_method_amendment_or_genome_retry_admitted':False,'group_and_native_closure':'PENDING_OUTER_OBSERVER_AND_EXTERNAL_NATIVE_EXIT'}
 save(E/'comparison.json',result)
def main(a):
 os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));g=load_grant(a)
 if a.phase=='commands':commands(a,g);return
 gate();lock=(R/'state/checkm2_pilot.lock').open('r+b');oldsha=sha(R/'state/checkm2_pilot.lock');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  run=E/'Linux_unit';run.mkdir(exist_ok=False);parent_peak=0;combined_peak=0
  def group(pgid):
   nonlocal parent_peak,combined_peak
   rows=observer.strict_group(pgid,stat);own=stat(os.getpid())['rss_bytes'];parent_peak=max(parent_peak,own);combined_peak=max(combined_peak,own+sum(x['rss_bytes']for x in rows))
   if combined_peak>2147483648:raise RuntimeError('RESOURCE_GATE combined fixture observer and owned group RSS exceeds2GiB')
   return rows
  cmd=['/usr/bin/python3','-B',str(Path(__file__).resolve()),'--phase','commands','--admission',str(inside(a.admission)),'--admission-sha256',a.admission_sha256]
  unit=observer.run_unit('synthetic_index_chunks',cmd,os.environ.copy(),run,118.14922169099736,hooks={'save':save,'stop_gate':gate,'stat':stat,'group':group,'mem_available':available,'progress':progress})
  if unit['status']!='UNIT_EXIT0_GROUP_CLOSED' or unit['exit_code']!=0 or not unit['owned_group_empty']:raise RuntimeError('Synthetic unit actual0/group closure required')
  comparison=read(E/'comparison.json');assert comparison['all_commands_actual0']is True
  save(E/'linux_terminal.json',{'status':'SYNTHETIC_UNIT0_GROUP_CLOSED_PENDING_EXTERNAL_NATIVE_EXIT','linux_controller_identity':stat(os.getpid()),'unit_execution':row(run/'synthetic_index_chunks/execution.json'),'comparison':row(E/'comparison.json'),'controller_peak_RSS_bytes':parent_peak,'sampled_peak_combined_observer_and_group_RSS_bytes':combined_peak,'compute_lease_will_release_in_finally':True,'image_loop_mount_or_private_IPC_created':False,'campaign_genomes_models_database_or_pickle_opened':False})
 finally:
  fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 if sha(R/'state/checkm2_pilot.lock')!=oldsha:raise RuntimeError('Compute lease bytes changed')
 save(E/'linux_lease_release.json',{'status':'COMPUTE_LEASE_RELEASED_BYTES_UNCHANGED','at_utc':utc(),'sha256_before_and_after':oldsha})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=('observe','commands'),required=True);p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True);args=p.parse_args()
 try:main(args)
 except BaseException as error:
  save(E/('linux_failure_'+args.phase+'.json'),{'status':'SYNTHETIC_DIAGNOSTIC_FAILED_NO_AUTOMATIC_RETRY','error':repr(error),'at_utc':utc(),'scope':'SYNTHETIC_ONLY_NO_GENOME_QUALITY_INFERENCE'});raise
