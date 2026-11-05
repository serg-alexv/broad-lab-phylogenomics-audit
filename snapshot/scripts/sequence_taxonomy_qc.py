#!/usr/bin/env python3
"""Bounded local DNA ANI/AF consistency screen; not biological-QC acceptance."""
from pathlib import Path
import argparse,collections,csv,datetime,fcntl,hashlib,json,os,shutil,signal,socket,subprocess,sys,time,uuid
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import pilot10
OUT=R/'analysis/sequence_qc'; STATE=R/'state/sequence_qc_progress.json'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp-'+uuid.uuid4().hex[:8])
 with tmp.open('w',encoding='utf-8') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def verify_artifact_manifest(folder):
 manifest=read(folder/'artifact_manifest.json')
 for row in manifest['files']:
  p=folder/row['path']
  if not p.resolve().is_relative_to(folder.resolve()):raise RuntimeError('Unsafe output manifest path')
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Committed output hash mismatch '+str(p))
def make_artifact_manifest(folder):
 snapshot=folder/'controller_source_at_execution.py'
 if not snapshot.exists():shutil.copyfile(__file__,snapshot)
 files=[{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json']
 save(folder/'artifact_manifest.json',{'created_utc':utc(),'scope':'Sequence-QC outputs and exact controller source; no raw genome rewrite','files':files})
def progress(status,done,total,detail,**kw):
 save(STATE,{'status':status,'done':done,'total':total,'unit':'phases','detail':detail,'started_utc':START,'updated_utc':utc(),'pid':os.getpid(),'process_creation_identity':pilot10.process_stat(os.getpid()),'log_path':str(LOG),'stage':'04 DNA sequence consistency screen','genome_quality_status':'NOT_RUN','taxonomy_acceptance':'NOT_GRANTED',**kw})
def gate():
 if socket.gethostname().upper()!='WD':raise RuntimeError('WD-only guard')
 if (R/'state/STOP').exists() or (R/'state/STOP_SEQUENCE_QC').exists():raise InterruptedError('STOP requested')
 if pilot10.available()<1024**3:raise RuntimeError('RESOURCE_GATE: Linux available RAM below1GiB')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('RESOURCE_GATE: C volume below40GiB')
def cohort():
 p=read(R/'metadata/provisional_panel.json'); a=read(R/'qc/source_provenance_audit.json')
 supported={r['accession'] for r in a['records'] if r['production_disposition']=='SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN'}
 result=[]
 for row in p:
  if row['accession'] not in supported or row['metadata_qc']!='QC_METADATA_PASS':continue
  folder=R/'raw'/row['accession']; rp=folder/'acquisition_receipt.json'
  if not rp.exists():continue
  rec=read(rp);dna=[x for x in rec['files'] if x['path'].endswith('.fna')]
  if len(dna)!=1:raise RuntimeError('Expected one genomic FNA '+row['accession'])
  f=folder/dna[0]['path']
  if f.stat().st_size!=dna[0]['bytes'] or sha(f)!=dna[0]['sha256']:raise RuntimeError('Genomic input receipt mismatch '+row['accession'])
  result.append({**row,'fasta':str(f),'fasta_sha256':dna[0]['sha256'],'acquisition_receipt_sha256':sha(rp),'type_anchor_from_metadata':row.get('type_material_label')=='TYPE_MATERIAL'})
 return result

def launch(command,stem,timeout,env,phase,cohort_size):
 gate();stdout=Path(str(stem)+'.stdout');stderr=Path(str(stem)+'.stderr');proc=None;error=None;peak=0;started=utc();tick=time.monotonic()
 receipt={'command':command,'started_utc':started,'threads':2,'group_rss_limit_bytes':2*1024**3,'available_headroom_bytes':1024**3,'timeout_seconds':timeout}
 with stdout.open('wb') as out,stderr.open('wb') as err:
  try:
   proc=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True,preexec_fn=pilot10.child_limits)
   receipt['process_creation_identity']=pilot10.process_stat(proc.pid)
   while proc.poll() is None:
    gate();rss=sum(x['rss_bytes'] for x in pilot10.group_snapshot(proc.pid));peak=max(peak,rss)
    progress('RUNNING',phase,3,f'{cohort_size} genomes: skani ANI/AF comparisons; pair-level percent unavailable',active_command=command,worker_pid=proc.pid,worker_creation_identity=receipt['process_creation_identity'],sampled_group_rss_bytes=rss,log_path=str(stderr))
    if rss>2*1024**3:raise RuntimeError('RESOURCE_GATE: group RSS above2GiB')
    if time.monotonic()-tick>timeout:raise RuntimeError('Time budget reached')
    time.sleep(1)
   if proc.returncode:raise RuntimeError('skani exit '+str(proc.returncode))
  except BaseException as exc:
   error=repr(exc)
   if proc and proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
  finally:
   rem=pilot10.group_snapshot(proc.pid) if proc else []
   if rem and proc:
    os.killpg(proc.pid,signal.SIGKILL);time.sleep(.1);rem=pilot10.group_snapshot(proc.pid)
   receipt.update(ended_utc=utc(),elapsed_seconds=time.monotonic()-tick,sampled_peak_group_rss_bytes=peak,exit_code=proc.returncode if proc else None,error=error,owned_group_empty=not rem)
   save(str(stem)+'.exit.json',receipt)
 if error:raise RuntimeError(error)
 if rem:raise RuntimeError('Owned group closure unresolved')
 return receipt

def parse_pairs(path,rows,prefix):
 byf={r['fasta']:r for r in rows};flags=[];assessed=collections.Counter();anchored=collections.defaultdict(set);selfs=set();pairs=0;header=[]
 with path.open() as f:
  reader=csv.DictReader(f,delimiter='\t');header=reader.fieldnames or []
  required={'Ref_file','Query_file','ANI','Align_fraction_ref','Align_fraction_query'}
  if not required.issubset(header):raise ValueError('Unrecognized skani output schema '+str(header))
  for v in reader:
   ref=byf.get(v['Ref_file']);query=byf.get(v['Query_file'])
   if not ref or not query:raise ValueError('Unexpected input path in skani output')
   ani=float(v['ANI']);afr=float(v['Align_fraction_ref']);afq=float(v['Align_fraction_query'])
   if not(0<=ani<=100 and 0<=afr<=100 and 0<=afq<=100):raise ValueError('ANI/AF outside0..100')
   if ref['accession']==query['accession']:selfs.add(ref['accession']);continue
   pairs+=1;assessed[ref['accession']]+=1;assessed[query['accession']]+=1
   sufficient=min(afr,afq)>=65
   if sufficient and ani>=95:
    if ref['type_anchor_from_metadata']:anchored[query['accession']].add(ref['accession'])
    if query['type_anchor_from_metadata']:anchored[ref['accession']].add(query['accession'])
   same=ref['species_taxid']==query['species_taxid'];reasons=[]
   if sufficient and ani>=99.99:reasons.append('NEAR_IDENTICAL_DNA_REVIEW')
   if sufficient and ani>=95 and not same:reasons.append('CROSS_LABEL_HIGH_ANI_REVIEW')
   if sufficient and ani<95 and same:reasons.append('WITHIN_LABEL_LOW_ANI_REVIEW')
   if reasons:flags.append({'reference':ref['accession'],'query':query['accession'],'reference_species':ref['species'],'query_species':query['species'],'ANI':ani,'AF_reference':afr,'AF_query':afq,'review_flags':reasons})
  
 save(prefix/'pair_review_flags.json',flags)
 genome_rows=[{'accession':r['accession'],'species':r['species'],'reported_nonself_pairs':assessed[r['accession']],'type_anchors_with_ANI_ge95_AFboth_ge65':sorted(anchored[r['accession']]),'self_comparison_reported':r['accession'] in selfs,'assessment':'CONSISTENCY_SCREEN_ONLY_NOT_TAXONOMY_ACCEPTANCE','type_anchor_metadata_only':r['type_anchor_from_metadata'],'completeness_contamination':'NOT_RUN'} for r in rows]
 save(prefix/'genome_assessment.json',genome_rows)
 summary={'genomes':len(rows),'potential_nonself_pairs':len(rows)*(len(rows)-1)//2,'reported_nonself_pairs':pairs,'self_rows_reported':len(selfs),'review_flag_pairs':len(flags),'review_flags':dict(collections.Counter(x for r in flags for x in r['review_flags'])),'genomes_with_nonself_type_anchor_match':sum(bool(anchored[r['accession']]) for r in rows),'ANI_review_threshold':95,'both_directional_AF_review_minimum_percent':65,'near_identity_review_threshold':99.99,'limitations':['A95% ANI rule is a screening convention, not universal species adjudication.','Skani screens pairs; unreported pairs remain unassessed and are not stored as zero ANI.','Same-source type material/self comparison cannot independently validate a species label.','No completeness/contamination,source provenance or defence acceptance is granted.'],'output_header':header,'output_sha256':sha(path)}
 save(prefix/'summary.json',summary);return summary

def main():
 gate();OUT.mkdir(parents=True,exist_ok=True);rows=cohort()
 if len(rows)<2:raise RuntimeError('Fewer than2 eligible acquired genomes')
 tool=R/'tools/bioenv/bin/skani';spec={'rows':rows,'panel_sha256':sha(R/'metadata/provisional_panel.json'),'source_audit_sha256':sha(R/'qc/source_provenance_audit.json'),'tool_sha256':sha(tool),'tool_version':subprocess.check_output([str(tool),'--version'],text=True).strip(),'parameters':['triangle','--sparse','--detailed','--diagonal','--ci','-t','2','--min-af','15'],'biological_qc':'NOT_RUN'}
 key=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:16];dest=OUT/key;dest.mkdir(exist_ok=True)
 if (dest/'commit.json').exists():
  old=read(dest/'commit.json')
  if old['input_spec_sha256']!=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest():raise RuntimeError('Cache spec mismatch')
  verify_artifact_manifest(dest)
  progress('COMPLETED',3,3,'Verified existing ANI consistency screen; biological QC still not accepted',result_path=str(dest/'commit.json'),genomes=len(rows));return
 save(dest/'input_manifest.json',spec)
 env=os.environ.copy();tmp=R/'work/sequence_qc';tmp.mkdir(parents=True,exist_ok=True)
 env.update(TMPDIR=str(tmp),XDG_CACHE_HOME=str(tmp/'cache'),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
 receipts=[];start=time.monotonic()
 for phase,name,subset,budget in [(0,'pilot100',rows[:min(100,len(rows))],600),(1,'full_cohort',rows,3600)]:
  prefix=dest/name;prefix.mkdir(exist_ok=True);fl=prefix/'fasta_list.txt';fl.write_text(''.join(r['fasta']+'\n' for r in subset));part=prefix/'ani.tsv.part';final=prefix/'ani.tsv'
  if final.exists() and (prefix/'summary.json').exists() and (prefix/'skani.exit.json').exists():
   receipt=read(prefix/'skani.exit.json')
   if receipt.get('exit_code')!=0 or read(prefix/'summary.json')['output_sha256']!=sha(final):raise RuntimeError('Invalid cached completed screen')
  else:
   cmd=[str(tool),'triangle','-l',str(fl),'-o',str(part),'--sparse','--detailed','--diagonal','--ci','-t','2','--min-af','15']
   receipt=launch(cmd,prefix/'skani',budget,env,phase,len(subset));summary=parse_pairs(part,subset,prefix);os.replace(part,final)
  receipts.append(receipt)
  if phase==0:
   estimate=receipt['sampled_peak_group_rss_bytes']*len(rows)/len(subset)
   runtime_estimate=receipt['elapsed_seconds']*(len(rows)/len(subset))**2
   save(dest/'resource_pilot.json',{'linear_memory_scaling_estimate_bytes':estimate,'quadratic_runtime_estimate_seconds':runtime_estimate,'actual_pilot':receipt,'interpretation':'Admission estimate only; full run remains watchdog bounded'})
   if estimate>1.75*1024**3 or runtime_estimate>3600:raise RuntimeError('RESOURCE_GATE: full cohort admission estimate exceeds budget')
 summary=read(dest/'full_cohort/summary.json');commit={'status':'COMPLETED_CONSISTENCY_SCREEN_ONLY','created_utc':utc(),'input_spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'genomes':len(rows),'summary':summary,'process_receipts':receipts,'script_sha256':sha(__file__),'genome_quality_status':'NOT_RUN','taxonomy_acceptance':'NOT_GRANTED','defence':'NOT_RUN'}
 save(dest/'commit.json',commit);make_artifact_manifest(dest);save(OUT/'latest.json',{'commit_path':str(dest/'commit.json'),'summary':summary});progress('COMPLETED',3,3,f'ANI/AF consistency screen complete for{len(rows)} genomes; candidate flags require curation',result_path=str(dest/'commit.json'),genomes=len(rows),summary=summary)

if __name__=='__main__':
 START=utc();LOG=R/'logs/sequence_qc_controller.log';LOG.parent.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 lock=open(R/'state/sequence_qc.lock','a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 identity=pilot10.process_stat(os.getpid());save(R/'state/sequence_qc_owner.json',{'pid':os.getpid(),'process_creation_identity':identity,'started_utc':START,'script_sha256':sha(__file__)})
 try:
  progress('RUNNING',0,3,'Preparing source-supported DNA inputs and verifying acquisition hashes');main()
 except BaseException as exc:
  status='STOPPED' if isinstance(exc,InterruptedError) else 'BLOCKED_RESOURCE' if 'RESOURCE_GATE' in str(exc) else 'FAILED'
  progress(status,0,3,repr(exc));save(OUT/'last_exit.json',{'status':status,'error':repr(exc),'ended_utc':utc(),'process_creation_identity':identity,'lock_released':True});raise
 else:save(OUT/'last_exit.json',{'status':'COMPLETE','ended_utc':utc(),'process_creation_identity':identity,'lock_released':True})
 finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
