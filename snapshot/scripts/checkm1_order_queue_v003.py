"""Distinct stock CheckM1 taxon-marker workflow, original supplied genes, resumable batches."""
from pathlib import Path
import os,sys,json,time,hashlib,subprocess,fcntl,csv,math,shutil,signal,ast
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import checkm1_owned_cleanup_v001 as own
from checkm1_owned_rss_sample_v001 import sample_owned_rss
from checkm1_raw_reuse_v001 import STATUS as REUSE_STATUS
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');
 with t.open('w')as f:json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def path(s):
 p=Path(s);p=p if p.is_absolute()else R/p;p=p.resolve()
 if not p.is_relative_to(R):raise RuntimeError('Path outside isolated project')
 return p
def bind(ref):
 p=path(ref['path'])
 if sha(p)!=ref['sha256']or p.stat().st_size!=ref['bytes']:raise RuntimeError('Bound artifact changed: '+str(p))
 return p
def ref(p):return{'path':str(Path(p).relative_to(R)),'sha256':sha(p),'bytes':Path(p).stat().st_size}
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
PLAN=read(sys.argv[1]);assert sha(sys.argv[1])==sys.argv[2]
E=path(PLAN['work']);OUT=path(PLAN['output']);RAM=path(PLAN['ram_scratch']);E.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
for r in PLAN['sources']:bind(r)
dataset=read(bind(PLAN['queue_manifest']));rows={r['accession']:r for r in dataset['rows']}
PY=path(PLAN['python']);CHECKM=path(PLAN['checkm_script']);MARKERS=OUT/'Lactobacillales.ms';STOP=path(PLAN['stop_path'])
started=time.monotonic();completed=[];batch_num=0;phase='PREPARING';logs=None;current_count=0
native=read(E/'native_owner.json')['native_owner'];save(E/'linux_owner.json',own.identity(os.getpid()))
def progress(detail,processing=False,**extra):
 v={'id':'04','name':'Independent biological QC','status':'RUNNING'if processing else'PREPARING_ALTERNATIVE_METHOD','method':'CHECKM1_1_2_5_LACTOBACILLALES','detail':detail,'done':len(completed),'total':len(rows),'unit':'CheckM1 measured completeness/contamination; panel acceptance separate','updated_utc':now(),'pid':native['pid'],'creation_time_utc':native['creation_time_utc'],'batch':batch_num+1,'batch_total':len(dataset['batches']),'batch_genomes':current_count,'genome_processing':processing,'source_taxonomy_or_final_panel_acceptance':False,**extra}
 for target in(E/'progress.json',R/'state/stages/04.json',R/'state/monitor_alternative_qc_v1/current.json'):
  try:save(target,v)
  except OSError as exc:
   # Optional display failure must not terminate a healthy scientific command.
   try:
    with(E/'optional_display_errors.jsonl').open('a')as log:log.write(json.dumps({'path':str(target),'error':repr(exc),'at':now()})+'\n')
   except OSError:pass
def guard():
 if STOP.exists()or(R/'state/STOP').exists():raise InterruptedError('Project or CheckM1 STOP')
 if time.time()>PLAN['original_context_absolute_deadline_unix'] or time.monotonic()-started>PLAN['cold_seconds']:raise TimeoutError('Explicit CheckM1 finite context allowance')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Backing disk below40GiB reserve')
 available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
 if available<1024**3:raise RuntimeError('Linux available memory below1GiB')
def run(name,args,folder,env,limit):
 global phase
 folder.mkdir(parents=True,exist_ok=False);phase=name;save(folder/'command.json',{'argv':args,'started_utc':now()});t=time.monotonic();p=None;identity=None;known={};error=None;peak=0;peak_rss=0;peak_ram=0
 try:
  guard()
  with(folder/'stdout.txt').open('wb')as out,(folder/'stderr.txt').open('wb')as err:
   p=subprocess.Popen(args,env=env,cwd=R,stdout=out,stderr=err,start_new_session=True);identity=own.identity(p.pid);known[p.pid]=identity;last=0
   while p.poll()is None:
    guard();own.track_descendants(identity,known)
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=identity['boot_id']:raise RuntimeError('Boot identity changed')
    rss=sample_owned_rss([*known.values(),own.identity(os.getpid())])
    ram_used=sum(shutil.disk_usage(p).used for p in(RAM,Path('/tmp'),Path('/dev/shm')))
    combined=rss+ram_used;peak_rss=max(peak_rss,rss);peak_ram=max(peak_ram,ram_used);peak=max(peak,combined)
    if combined>PLAN['linux_total_RSS_bytes']-PLAN['native_reserved_bytes']:raise RuntimeError('Owned CheckM1 RSS plus private RAM scratch exceeds2GiB')
    if time.monotonic()-t>limit:raise TimeoutError(name+' finite unit allowance')
    if time.monotonic()-last>=30:progress(name,processing=name=='analyze',batch_elapsed_seconds=time.monotonic()-t,group_rss_bytes=rss,private_RAM_used_bytes=ram_used,combined_memory_bytes=combined,log_path=str(folder/'stderr.txt'));last=time.monotonic()
    time.sleep(.5)
   code=p.wait()
  if code!=0:raise RuntimeError(name+' actual exit '+str(code))
 except BaseException as exc:
  error=repr(exc)
  if p is not None:
   cleanup=own.cleanup_linux_helper(p,identity,known,STOP,'CHECKM1_'+str(os.getpid()))
   save(folder/'failure_cleanup.json',cleanup)
  raise
 finally:
  remaining=[x for x in known.values()if own.current_matching(x)is not None]
  save(folder/'execution.json',{'actual_exit_code':p.returncode if p is not None else None,'child_identity':identity,'actual_child_waited_and_reaped':p is not None and p.poll()is not None,'captured_owned_identities':list(known.values()),'remaining_owned_identities':remaining,'group_closed':not remaining,'elapsed_seconds':time.monotonic()-t,'peak_sampled_group_RSS_bytes':peak_rss,'peak_sampled_private_RAM_used_bytes':peak_ram,'peak_sampled_RSS_plus_private_RAM_bytes':peak,'error':error,'ended_utc':now()})
  if remaining and error is None:raise RuntimeError('Owned descendants remain after command')
def table(p,names,out):
 extended={}
 for line in(out/'storage/bin_stats_ext.tsv').read_text().splitlines():
  acc,payload=line.split('\t',1)
  if acc in extended:raise RuntimeError('Duplicate unrounded stock quality row')
  extended[acc]=ast.literal_eval(payload)
 if set(extended)!=set(names):raise RuntimeError('Unrounded stock quality rows differ from batch')
 with p.open()as f:records=list(csv.DictReader(f,delimiter='\t'))
 result=[]
 for q in records:
  if not q.get('Bin Id'):continue
  acc=q['Bin Id'];reported_c=float(q['Completeness']);reported_x=float(q['Contamination']);stock=extended[acc];c=float(stock['Completeness']);x=float(stock['Contamination'])
  if not math.isfinite(reported_c)or not math.isfinite(reported_x)or abs(c-reported_c)>.0050001 or abs(x-reported_x)>.0050001:raise RuntimeError('Rounded QA differs from original stock unrounded score')
  if acc not in names or not math.isfinite(c)or not 0<=c<=100 or not math.isfinite(x)or x<0:raise RuntimeError('Invalid CheckM1 report row')
  if int(q['# markers'])!=335 or int(q['# marker sets'])!=183:raise RuntimeError('Unexpected stock order marker domain')
  result.append({'accession':acc,'Completeness':c,'Contamination':x,'reported_rounded_QA':{'Completeness':reported_c,'Contamination':reported_x},'classification_uses_original_stock_unrounded_scores':True,'method':'CheckM1_1.2.5_order_Lactobacillales','QC_95_5':'PASS'if c>=95 and x<=5 else'FAIL','source_masks':rows[acc]['source_masks'],'independent_taxonomy':'UNRESOLVED_SEPARATE','final_panel_acceptance':False})
 if len(result)!=len(names)or{q['accession']for q in result}!=set(names):raise RuntimeError('Incomplete or duplicate QC report')
 return result
def hmmer_receipts_ok(receipts):
 for q in receipts:
  args=q['argv'];code=q.get('actual_exit_code')
  if q.get('status')==REUSE_STATUS and q.get('actual_exit_code')is None and q.get('effective_original_search_exit_code')==0 and q.get('no_new_HMMsearch_binary_started')is True and q.get('reuse_manifest_sha256')==PLAN['partial_raw_reuse_manifest']['sha256']:continue
  if code==0:continue
  if len(args)==1 and code==1:continue # Stock checkProgramExists probes normal no-argument usage.
  if Path(args[0]).name=='hmmalign'and code==1 and'--allcol'in args:
   retried=[x for x in args if x!='--allcol']
   if any(v.get('actual_exit_code')==0 and v.get('argv')==retried and v.get('ended_unix',0)>q.get('ended_unix',0)for v in receipts):continue
  raise RuntimeError('HMMER scientific command failed: '+repr(q))
env=os.environ.copy();env.update(PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',CHECKM_DATA_PATH=str(path(PLAN['database'])),PYTHONPATH=str(path(PLAN['wheel_overlay']))+':'+str(path(PLAN['package_site'])),MPLCONFIGDIR=str(E/'mpl'),MPLBACKEND='Agg',XDG_CACHE_HOME=str(E/'cache'),TMPDIR='/tmp',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
for sub in('mpl','cache','tmp','bin'): (E/sub).mkdir(exist_ok=True)
for name in('hmmsearch','hmmfetch','hmmalign'):
 p=E/'bin'/name
 if not p.exists():p.symlink_to(R/'scripts/checkm1_hmmer_receipt_v003.py')
env['PATH']=str(E/'bin')+':'+str(R/'tools/bioenv/bin')+':'+env['PATH']
lock=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
CLI=[str(PY),'-B',str(R/'scripts/checkm1_stock_bootstrap_v001.py'),str(CHECKM)]
def pilot_review(commit):
 progress('Representative18 benchmark complete; Root method review before automatic full queue',False)
 until=time.monotonic()+1800;approval=path(PLAN['bulk_approval'])
 while not approval.exists():
  guard()
  if time.monotonic()>until:raise TimeoutError('Bounded pilot method review window expired')
  time.sleep(2)
 gate=read(approval)
 if gate.get('status')!='ROOT_GO_CHECKM1_FULL_QUEUE'or gate.get('pilot_commit')!=ref(commit):raise RuntimeError('Exact pilot-based full queue approval required')
try:
 os.sched_setaffinity(0,set(range(PLAN['threads'])))
 marker_receipts=E/'marker_hmmer_receipts';env['TREE2_HMMER_RECEIPTS']=str(marker_receipts)
 if(E/'actual_marker_file.json').exists():bind(read(E/'actual_marker_file.json'))
 else:
  run('taxon_set',CLI+['taxon_set','order','Lactobacillales',str(MARKERS)],E/'unit_taxon_set',env,180)
  save(E/'actual_marker_file.json',ref(MARKERS))
 for part in dataset['batches']:
  batch_num=part['batch_index'];names=part['ordered_accessions'];current_count=len(names);folder=OUT/f'batch_{batch_num:03d}'
  reuse_raw=batch_num==PLAN['partial_recovery_batch']
  if reuse_raw:
   folder=folder/'recovery_v003'
   manifest=read(bind(PLAN['partial_raw_reuse_manifest']))
   if set(manifest['rows'])!=set(names):raise RuntimeError('Partial recovery must reuse every original successful search')
   env['TREE2_HMMER_RAW_REUSE_MANIFEST']=str(bind(PLAN['partial_raw_reuse_manifest']));env['TREE2_HMMER_RAW_REUSE_MANIFEST_SHA']=PLAN['partial_raw_reuse_manifest']['sha256']
  else:
   env.pop('TREE2_HMMER_RAW_REUSE_MANIFEST',None);env.pop('TREE2_HMMER_RAW_REUSE_MANIFEST_SHA',None)
  folder.mkdir(exist_ok=True);commit=folder/'COMMITTED.json'
  if commit.exists():
   previous=read(commit)
   for proof in previous['artifacts']:bind(proof)
   if previous.get('accessions')!=names or [q['accession']for q in previous['rows']]!=names or previous.get('marker_file')!=ref(MARKERS):raise RuntimeError('Reused commit does not match current exact batch/marker')
   for unit in('unit_analyze','unit_qa'):
    proof=read(folder/unit/'execution.json')
    if proof.get('actual_exit_code')!=0 or proof.get('group_closed')is not True or proof.get('remaining_owned_identities')!=[]:raise RuntimeError('Reused command lacks actual0/complete captured closure')
   staged=read(folder/'staged_input_manifest.json')
   if {q['accession']:q['source']for q in staged}!={a:rows[a]['CheckM1_scoring_FAA']for a in names}:raise RuntimeError('Reused original input provenance differs')
   if previous.get('native_owner')!=native:
    authority=read(bind(PLAN['resume_authority']))
    if authority.get('status')!='ROOT_ADMITTED_CHECKM1_REUSE_ACCEPTED_BATCHES_AFTER_CLOSED_PARENT'or ref(commit)not in authority.get('batch_commits',[]):raise RuntimeError('Cross-owner resume requires bound accepted batches/closed parent authority')
   completed.extend(previous['rows'])
   if batch_num==0:pilot_review(commit)
   continue
  if(folder/'once_claim.json').exists():raise RuntimeError('Unclosed batch claim requires explicit preserved-phase recovery; no blind retry')
  save(folder/'once_claim.json',{'accessions':names,'method_plan_sha256':sys.argv[2],'started_utc':now()});inputs=folder/'inputs';inputs.mkdir();staged=[]
  for acc in names:
   q=rows[acc];original=bind(q['CheckM1_scoring_FAA']);dest=inputs/(acc+'.faa');shutil.copyfile(original,dest)
   if sha(dest)!=q['CheckM1_scoring_FAA']['sha256']:raise RuntimeError('Original FAA byte-copy changed')
   staged.append({'accession':acc,'source':q['CheckM1_scoring_FAA'],'copy':ref(dest),'original_header_preserved':True})
  save(folder/'staged_input_manifest.json',staged);env['TREE2_HMMER_RECEIPTS']=str(folder/'HMMER_receipts');env['TREE2_HMMER_DURABLE_DIR']=str(folder/'HMMER_checkpoints');env['TREE2_MARKER_FILE_SHA']=sha(MARKERS);scratch=RAM/f'batch_{batch_num:03d}';scratch.mkdir();out=scratch/'checkm_output';report=scratch/'quality.tsv'
  run('analyze',CLI+['analyze','-g','-x','faa','-t',str(PLAN['threads']),'--tmpdir',str(E/'tmp'),str(MARKERS),str(inputs),str(out)],folder/'unit_analyze',env,PLAN['partial_recovery_analyze_seconds']if reuse_raw else PLAN['batch_seconds'])
  hmm=list((folder/'HMMER_receipts').glob('*.json'));receipts=[read(p)for p in hmm];searches=[q for q in receipts if Path(q['argv'][0]).name=='hmmsearch'and'--domtblout'in q['argv']]
  if len(searches)!=len(names):raise RuntimeError('Wrong count of per-input search phase receipts')
  for q in searches:
   if reuse_raw:
    if q.get('status')!=REUSE_STATUS or q.get('actual_exit_code')is not None or q.get('effective_original_search_exit_code')!=0 or q.get('no_new_HMMsearch_binary_started')is not True or q.get('reuse_manifest_sha256')!=PLAN['partial_raw_reuse_manifest']['sha256']:raise RuntimeError('Recovery must use typed original0 raw phases without starting search binaries')
   elif q.get('actual_exit_code')!=0 or q.get('status')!='ACTUAL_HMMER_EXIT_OBSERVED':raise RuntimeError('Missing actual HMMER0')
   if not q.get('durable_raw_checkpoint'):raise RuntimeError('Missing durable original raw phase')
  raw=[]
  for acc in names:
   p=out/'bins'/acc/'hmmer.analyze.txt'
   if not p.exists()or'# [ok]'not in p.read_text()[-4000:]:raise RuntimeError('Incomplete raw HMMER table: '+acc)
   matches=[q for q in searches if Path(q['argv'][q['argv'].index('--domtblout')+1]).parent.name==acc]
   if len(matches)!=1:raise RuntimeError('Nonunique per-bin actual HMM search')
   proof=matches[0]['durable_raw_checkpoint'];saved=bind(proof)
   if sha(saved)!=sha(p)or proof.get('query_faa_sha256')!=rows[acc]['CheckM1_scoring_FAA']['sha256']or proof.get('marker_file_sha256')!=sha(MARKERS):raise RuntimeError('Durable raw HMM checkpoint provenance differs')
   raw.append(ref(p))
  run('qa',CLI+['qa','-t',str(PLAN['threads']),'--tab_table','-f',str(report),str(MARKERS),str(out)],folder/'unit_qa',env,180)
  hmm=list((folder/'HMMER_receipts').glob('*.json'));hmmer_receipts_ok([read(p)for p in hmm])
  measured=table(report,names,out)
  # Durable copies precede every COMMITTED record; RAM is never the checkpoint.
  guard();durable=folder/'checkm_output';shutil.copytree(out,durable);guard();durable_report=folder/'quality.tsv';shutil.copyfile(report,durable_report)
  for original in out.rglob('*'):
   guard()
   if original.is_file()and sha(original)!=sha(durable/original.relative_to(out)):raise RuntimeError('RAM-to-disk output changed')
  if sha(report)!=sha(durable_report):raise RuntimeError('RAM-to-disk report changed')
  out=durable;report=durable_report;artifacts=[ref(report),ref(folder/'staged_input_manifest.json'),ref(folder/'unit_analyze/execution.json'),ref(folder/'unit_qa/execution.json'),*[ref(p)for p in out.rglob('*')if p.is_file()],*[ref(p)for p in hmm],*[ref(p)for p in(folder/'HMMER_checkpoints').glob('*')if p.is_file()]]
  if reuse_raw:
   artifacts.extend([PLAN['partial_raw_reuse_manifest'],PLAN['closed_parent_and_recovery']])
   for q in manifest['rows'].values():artifacts.extend([q['actual_original_HMMER_receipt'],q['raw_checkpoint']])
  measured.sort(key=lambda q:names.index(q['accession']));guard()
  save(commit,{'status':'CHECKM1_BATCH_MEASURED_VALIDATED','rows':measured,'accessions':names,'artifacts':artifacts,'marker_file':ref(MARKERS),'native_owner':native,'original_successful_raw_searches_reused':len(names)if reuse_raw else 0,'new_genomic_searches':0 if reuse_raw else len(names),'original_method_plan_sha256':sys.argv[2],'queue_manifest':PLAN['queue_manifest'],'no_source_taxonomy_or_final_panel_acceptance':True,'ended_utc':now()});completed.extend(measured);save(OUT/'completed_rows.json',{'method':'CHECKM1_1.2.5_LACTOBACILLALES','rows':completed,'completed':len(completed),'total':len(rows),'last_batch_commit':ref(commit)})
  if not scratch.resolve().is_relative_to(RAM.resolve()):raise RuntimeError('Scratch cleanup escapes private RAM root')
  shutil.rmtree(scratch)
  progress('CheckM1 batch validated; next batch is automatic',False)
  if batch_num==0:
   pilot_review(commit)
 save(OUT/'COMPLETE.json',{'status':'ALL_CHECKM1_METHOD_MEASUREMENTS_COMPLETED','completed':len(completed),'rows':completed,'final_panel_acceptance':False,'ended_utc':now()});progress('All CheckM1 measurements complete; final panel/taxonomy review remains',False)
except BaseException as exc:
 try:
  if 'scratch'in globals()and scratch.exists():
   recovery=folder/('RECOVERY_UNACCEPTED_'+str(os.getpid()));shutil.copytree(scratch,recovery)
   save(recovery/'RECOVERY_MANIFEST.json',{'status':'UNACCEPTED_BEST_EFFORT_RAM_SNAPSHOT','files':[ref(p)for p in recovery.rglob('*')if p.is_file()],'actual_error':repr(exc),'not_a_completed_QC_batch':True})
 except BaseException as recovery_error:save(E/'RAM_recovery_error.json',{'error':repr(recovery_error),'per_bin_raw_checkpoints_remain_durable':True})
 save(E/'failure.json',{'error':repr(exc),'completed':len(completed),'phase':phase,'batch':batch_num,'actual_failed_work_is_not_biological_absence':True,'ended_utc':now()});progress('CheckM1 stopped; actual failure and completed batch checkpoints preserved',False);raise
finally:
 fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
