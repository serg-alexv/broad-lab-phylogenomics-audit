"""Exploratory all-profile/all-target search; complete execution is not absence proof."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,math,os,re,sys,time,uuid
import marker_pilot_compute_v001 as guard

R=guard.R

def intervals_length(intervals):
 total=0;right=0
 for lo,hi in sorted(intervals):
  total+=max(0,hi-max(right,lo-1));right=max(right,hi)
 return total

def parse_domains(path,target_lengths,query_lengths,evalue):
 """Validate complete HMMER3 domtbl, then combine qualifying domains per protein."""
 groups={};rows=0;finished=False;header=False
 with Path(path).open(encoding='utf-8')as f:
  for raw in f:
   line=raw.strip()
   if not line:continue
   if line.startswith('#'):
    header|='target name'in line and'query name'in line
    finished|=line=='# [ok]'
    continue
   fields=line.split(maxsplit=22)
   if len(fields)<22:raise ValueError('Malformed HMMER domtbl row')
   target,query=fields[0],fields[3]
   if target not in target_lengths or query not in query_lengths:raise ValueError('Unknown target or query in HMMER output')
   tlen,qlen=int(fields[2]),int(fields[5])
   if tlen!=target_lengths[target]or qlen!=query_lengths[query]:raise ValueError('Target/query length mismatch in HMMER output')
   full_e,independent_e=float(fields[6]),float(fields[12]);bits=float(fields[13])
   if not all(math.isfinite(v)for v in(full_e,independent_e,bits))or min(full_e,independent_e)<0:raise ValueError('Non-finite/negative HMMER score')
   hf,ht,af,at=map(int,(fields[15],fields[16],fields[17],fields[18]))
   if not(1<=hf<=ht<=qlen and 1<=af<=at<=tlen):raise ValueError('Out-of-range HMMER coordinates')
   rows+=1
   if full_e>evalue or independent_e>evalue:continue
   item=groups.setdefault((query,target),{'hmm':[],'target':[],'best_domain_ievalue':independent_e,'full_sequence_evalue':full_e,'best_domain_bits':bits,'qualifying_domains':0})
   item['hmm'].append((hf,ht));item['target'].append((af,at));item['best_domain_ievalue']=min(item['best_domain_ievalue'],independent_e);item['best_domain_bits']=max(item['best_domain_bits'],bits);item['qualifying_domains']+=1
 if not header or not finished:raise ValueError('HMMER domtbl lacks header or final [ok] closure')
 for(query,target),v in groups.items():
  v['hmm_coverage']=intervals_length(v.pop('hmm'))/query_lengths[query]
  v['target_coverage']=intervals_length(v.pop('target'))/target_lengths[target]
 return groups,rows

def write_tsv(path,fields,rows):
 path=guard.inside(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.partial')
 with temp.open('x',encoding='utf-8',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(rows);f.flush();os.fsync(f.fileno())
 os.replace(temp,path)

def verified_profiles(manifest_path):
 manifest=guard.read(manifest_path)
 if manifest.get('status')!='EXPLORATORY_PILOT_COMPUTATION_COMPLETE':raise ValueError('Profile computation not complete')
 profiles=[];lengths={}
 for row in manifest['rows']:
  if row['status']!='ALIGNED_PROFILE_BUILT_EXPLORATORY':continue
  name=row['id']
  if not re.fullmatch(r'[A-Za-z0-9_.-]+',name)or name in lengths:raise ValueError('Unsafe/duplicate profile ID')
  for unit in('mafft','profile'):
   item=row[unit];receipt=guard.read(guard.bound(item['execution']))
   if receipt.get('actual_exit_code')!=0 or receipt.get('owned_group_empty')is not True:raise ValueError('Profile input lacks actual0/closed group')
   guard.bound(item['output'])
   for reference in receipt['signature']['inputs']:guard.bound(reference)
  path=guard.bound(row['profile']['output']);model_name=None;length=None;ends=0;first=None
  with path.open(encoding='utf-8')as f:
   for line in f:
    if first is None:first=line
    if line.startswith('NAME '):model_name=line.split()[1]
    elif line.startswith('LENG '):length=int(line.split()[1])
    elif line.strip()=='//':ends+=1
  if not first or not first.startswith('HMMER3/')or model_name!=name or not length or ends!=1:raise ValueError('Invalid single HMMER3 profile')
  profiles.append({'id':name,'hmm':guard.ref(path),'execution':row['profile']['execution'],'mafft_execution':row['mafft']['execution'],'trimmed':row['trimmed']});lengths[name]=length
 if not profiles or len(profiles)!=manifest['profiles']:raise ValueError('Profile count mismatch')
 return profiles,lengths

def combine_profiles(path,profiles):
 path=guard.inside(path);digest=hashlib.sha256()
 for profile in profiles:
  with guard.bound(profile['hmm']).open('rb')as f:
   while chunk:=f.read(65536):digest.update(chunk)
 if path.exists():
  if guard.sha(path)!=digest.hexdigest():raise ValueError('Existing combined query differs; preserve previous search')
  return
 temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.partial')
 with temp.open('xb')as out:
  for profile in profiles:
   with guard.bound(profile['hmm']).open('rb')as f:
    while chunk:=f.read(65536):out.write(chunk)
  out.flush();os.fsync(out.fileno())
 if guard.sha(temp)!=digest.hexdigest():raise ValueError('Combined profile hash differs')
 os.replace(temp,path)

def validate_targets(manifest):
 target_path=guard.bound(manifest['targets']);map_path=guard.bound(manifest['target_map']);records=guard.fasta(target_path)
 if any('*'in s for s in records.values()):raise ValueError('HMM targets still contain stops')
 taxa=[row['accession']for row in manifest['per_genome']]
 if len(taxa)!=14 or len(set(taxa))!=14:raise ValueError('Expected fourteen unique declared taxa')
 counts=collections.Counter();mapped=set();lengths={n:len(s)for n,s in records.items()}
 with map_path.open(encoding='utf-8-sig',newline='')as f:
  for row in csv.DictReader(f,delimiter='\t'):
   name=row['target_id'];accession=row['accession']
   if name in mapped or name not in records or accession not in taxa or not name.startswith(accession+'|t')or row['hmm_target_status']!='WRITTEN_HMM_TARGET':raise ValueError('Target map not an exact FASTA partition')
   sequence=records[name]
   if int(row['target_length'])!=len(sequence)or hashlib.sha256(sequence.encode()).hexdigest()!=row['target_sequence_sha256']:raise ValueError('Mapped target sequence hash/length differs')
   mapped.add(name);counts[accession]+=1
 if mapped!=set(records)or len(records)!=manifest['counts']['written_target_proteins']:raise ValueError('Target FASTA/map count mismatch')
 for row in manifest['per_genome']:
  guard.bound(row['source_faa'])
  if counts[row['accession']]!=row['written_targets']:raise ValueError('Per-genome target partition differs')
 return target_path,map_path,taxa,lengths

def main(a):
 if os.name!='posix':raise RuntimeError('Actual HMMER computation requires Linux')
 manifest_path=guard.inside(a.input_manifest);profile_manifest=guard.inside(a.profile_manifest);admission_path=guard.inside(a.admission);admission=guard.read(admission_path);out=guard.inside(a.output);out.mkdir(parents=True,exist_ok=True)
 if admission.get('status')!='ROOT_ADMITTED_EXPLORATORY_MARKER_SEARCH'or admission.get('input_manifest_sha256')!=guard.sha(manifest_path)or admission.get('profile_manifest_sha256')!=guard.sha(profile_manifest)or admission.get('script_sha256')!=guard.sha(__file__)or admission.get('guard_script_sha256')!=guard.sha(guard.__file__):raise RuntimeError('Fresh exact Root shared-resource admission required')
 if not 0<admission.get('max_rss_bytes',0)<=256*1024**2 or admission.get('linux_available_stop_bytes',0)<int(1.25*1024**3)or not 0<admission.get('unit_timeout_seconds',0)<=1200:raise RuntimeError('Search resource bounds differ')
 cpu=admission['cpu']
 if type(cpu)is not int or cpu not in os.sched_getaffinity(0)or cpu in(0,1):raise RuntimeError('One QC-unused CPU2/3 required')
 os.sched_setaffinity(0,{cpu});spec=admission['tools']['hmmsearch'];tool=Path(spec['path']).resolve()
 if guard.sha(tool)!=spec['sha256']:raise RuntimeError('Pinned hmmsearch changed')
 guard.TOOLCHAIN_SHA=hashlib.sha256(json.dumps({'tool':spec,'guard_script_sha256':guard.sha(guard.__file__),'search_script_sha256':guard.sha(__file__)},sort_keys=True).encode()).hexdigest()
 started=guard.utc();owner=guard.proc(os.getpid());last=0;phase='validating existing profiles and targets';done=0;total=0
 def publish(unit,peak=None,mem=None,terminal=None):
  nonlocal last
  if terminal is None and time.monotonic()-last<30:return
  stage={'id':'06','name':'Marker discovery and orthology','status':terminal or'RUNNING','operation':'EXPLORATORY_PILOT14_ALL_PROFILE_HMMSEARCH','detail':phase+' / '+unit,'done':done,'total':total,'unit':'searched profile/genome pairs','started_utc':started,'updated_utc':guard.utc(),'pid':a.native_pid or os.getpid(),'creation_time_utc':a.native_creation_utc or None,'linux_owner_identity':owner,'cpu_affinity':[cpu],'summed_owned_rss_bytes':peak,'linux_available_bytes':mem,'source_taxonomy_and_final_panel_acceptance':'NOT_GRANTED','marker_set_acceptance':'NOT_GRANTED','log_path':str(out/'progress.json'),'input_manifest':guard.ref(manifest_path),'admission':guard.ref(admission_path)}
  guard.save(out/'progress.json',stage);guard.save(R/'state/stages/06.json',stage);last=time.monotonic()
 publish('preparation',terminal='RUNNING')
 try:
  manifest=guard.read(manifest_path);target_path,map_path,taxa,target_lengths=validate_targets(manifest);profiles,query_lengths=verified_profiles(profile_manifest);total=len(profiles)*len(taxa)
  query_path=out/'all_pilot_profiles.hmm';combine_profiles(query_path,profiles)
  policy={'full_sequence_evalue_max':a.evalue,'independent_domain_evalue_max':a.evalue,'minimum_union_hmm_coverage':a.hmm_coverage,'minimum_union_target_coverage':a.target_coverage,'coverage_method':'union of inclusive coordinates over domains passing both E-value bounds','copy_count':'unique qualifying target protein identifiers per profile and declared genome','zero_interpretation':'No qualifying hit in this completed exploratory search; not biological absence','failed_unsearched_state':'UNKNOWN','marker_set_acceptance':'NOT_GRANTED'}
  query_manifest={'profile_manifest':guard.ref(profile_manifest),'profiles':profiles,'combined_profiles':guard.ref(query_path),'targets':manifest['targets'],'target_map':manifest['target_map'],'policy':policy,'guard_source':guard.ref(guard.__file__),'search_source':guard.ref(__file__),'toolchain_sha256':guard.TOOLCHAIN_SHA};guard.save(out/'query_manifest.json',query_manifest)
  inputs=[guard.ref(p)for p in(manifest_path,profile_manifest,query_path,target_path,map_path,out/'query_manifest.json',Path(__file__),Path(guard.__file__))]
  phase='actual HMMER search: '+str(len(profiles))+' profiles against '+str(len(target_lengths))+' proteins / 14 genomes';publish('hmmsearch',terminal='RUNNING')
  result=guard.run_unit(out/'search','hmmsearch',[str(tool),'--cpu','1','--noali','-E',str(a.evalue),'--domE',str(a.evalue),'--domtblout','{OUTPUT}',str(query_path),str(target_path)],inputs,'domains.tsv',admission,publish)
  phase='parsing completed search and copy counts';groups,domain_rows=parse_domains(guard.bound(result['output']),target_lengths,query_lengths,a.evalue)
  hits=[];copies=collections.defaultdict(list)
  for(query,target),v in sorted(groups.items()):
   if v['hmm_coverage']<a.hmm_coverage or v['target_coverage']<a.target_coverage:continue
   accession=target.split('|',1)[0];copies[(query,accession)].append(target);hits.append({'profile':query,'accession':accession,'target_id':target,**v})
  cells=[]
  for query in query_lengths:
   for accession in taxa:
    proteins=copies[(query,accession)];cells.append({'profile':query,'accession':accession,'search_state':'SEARCHED_COMPLETE','qualifying_copy_count':len(proteins),'copy_status':'NO_QUALIFYING_HIT_EXPLORATORY'if not proteins else'SINGLE_QUALIFYING_HIT_EXPLORATORY'if len(proteins)==1 else'MULTIPLE_QUALIFYING_HITS_EXPLORATORY','target_ids':';'.join(proteins)})
  summaries=[]
  for query in query_lengths:
   ns=[len(copies[(query,accession)])for accession in taxa];summaries.append({'profile':query,'genomes_searched':len(taxa),'genomes_zero_hits':ns.count(0),'genomes_single_hit':ns.count(1),'genomes_multiple_hits':sum(n>1 for n in ns),'single_copy_occupancy':ns.count(1)/len(taxa),'any_hit_occupancy':sum(n>0 for n in ns)/len(taxa),'profile_length':query_lengths[query],'marker_set_acceptance':'NOT_GRANTED'})
  write_tsv(out/'qualifying_hits.tsv',['profile','accession','target_id','best_domain_ievalue','full_sequence_evalue','best_domain_bits','qualifying_domains','hmm_coverage','target_coverage'],hits)
  write_tsv(out/'profile_genome_copy_counts.tsv',['profile','accession','search_state','qualifying_copy_count','copy_status','target_ids'],cells)
  write_tsv(out/'profile_summary.tsv',['profile','genomes_searched','genomes_zero_hits','genomes_single_hit','genomes_multiple_hits','single_copy_occupancy','any_hit_occupancy','profile_length','marker_set_acceptance'],summaries)
  done=total;summary={'status':'EXPLORATORY_PILOT14_HMM_SEARCH_COMPLETE','search':result,'query_manifest':guard.ref(out/'query_manifest.json'),'profiles_searched':len(profiles),'genomes_searched':len(taxa),'target_proteins_searched':len(target_lengths),'domtbl_domain_rows':domain_rows,'qualifying_profile_protein_hits':len(hits),'profile_genome_pairs':len(cells),'single_copy_in_all14':sum(r['genomes_single_hit']==14 for r in summaries),'outputs':[guard.ref(out/p)for p in('qualifying_hits.tsv','profile_genome_copy_counts.tsv','profile_summary.tsv')],'policy':policy,'full_panel_search':'NOT_RUN','production_panel_acceptance':'NOT_GRANTED','marker_set_acceptance':'NOT_GRANTED','source_scope':manifest['scope'],'source_holds_preserved':True}
  guard.save(out/'result.json',summary);publish('complete search and copy-count output committed',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as ex:
  guard.save(out/'failure.json',{'status':'EXPLORATORY_MARKER_SEARCH_STOPPED_PRESERVE_CHECKPOINTS','error':repr(ex),'all_unfinished_search_states':'UNKNOWN','no_new_zero_or_absence_calls':True});publish(str(ex),terminal='STOPPED');raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-manifest',required=True);p.add_argument('--profile-manifest',required=True);p.add_argument('--admission',required=True);p.add_argument('--output',required=True);p.add_argument('--evalue',type=float,default=1e-5);p.add_argument('--hmm-coverage',type=float,default=.7);p.add_argument('--target-coverage',type=float,default=.5);p.add_argument('--native-pid',type=int);p.add_argument('--native-creation-utc');a=p.parse_args()
 if not 0<a.evalue<=1e-3 or not 0<a.hmm_coverage<=1 or not 0<a.target_coverage<=1:p.error('Invalid explicit search criteria')
 main(a)
