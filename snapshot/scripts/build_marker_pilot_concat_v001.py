"""Concatenate completed exploratory pilot alignments; never infer accepted markers."""
from pathlib import Path
import argparse,collections,csv,datetime,hashlib,io,json,os,re,uuid

R=Path(__file__).resolve().parents[1]
AA=set('ACDEFGHIKLMNPQRSTVWY');ALLOWED=AA|set('BXZJUO-.')
MIN_COLUMNS=30;MIN_INFORMATIVE=10;OCCUPANCY=.8
SCOPE='EXPLORATORY_TEN_GENOME_METHOD_DEMONSTRATION_NOT_ACCEPTED_MARKERS_OR_PRODUCTION_TREE'
def inside(p):
 p=Path(p);p=(p if p.is_absolute()else R/p).resolve();p.relative_to(R);return p
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ref(p):
 p=inside(p);return {'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def bound(v):
 p=inside(v['path'])
 if sha(p)!=v['sha256']or('bytes'in v and p.stat().st_size!=v['bytes']):raise RuntimeError('Changed bound artifact '+str(p))
 return p
def create(p,data):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError('Immutable output already exists: '+str(p))
 t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 try:
  with t.open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.link(t,p)
 finally:
  if t.exists():t.unlink()
 return ref(p)
def jcreate(p,value):return create(p,(json.dumps(value,indent=2)+'\n').encode())
def fasta(p,taxa):
 records={};name=None;parts=[]
 def add():
  if name is None:return
  if not re.fullmatch(r'GC[AF]_\d+\.\d+\|gene\d+',name):raise ValueError('Expected versioned accession|gene FASTA ID '+name)
  acc=name.split('|')[0];s=''.join(parts)
  if acc in records or not s or set(s)-ALLOWED:raise ValueError('Duplicated taxon, empty sequence or unsupported residue '+name)
  records[acc]=s
 for line in Path(p).read_text().splitlines():
  if line.startswith('>'):add();name=line[1:].split()[0];parts=[]
  elif line.strip():
   if name is None:raise ValueError('Sequence before header')
   parts.append(line.strip())
 add()
 if len(records)!=10 or set(records)!=set(taxa)or len({len(x)for x in records.values()})!=1:raise ValueError('Alignment must have exact10taxa and equal lengths')
 return records
def columns(records):
 n=len(records);length=len(next(iter(records.values())));informative=constant=variable=0;minimum=1.0
 for i in range(length):
  c=collections.Counter(s[i]for s in records.values()if s[i]in AA);minimum=min(minimum,sum(c.values())/n)
  informative+=sum(v>=2 for v in c.values())>=2;constant+=len(c)==1;variable+=len(c)>1
 return {'retained_columns':length,'retained_parsimony_informative_columns':informative,'retained_constant_columns':constant,'retained_variable_columns':variable,'minimum_retained_unambiguous_column_occupancy':minimum}
def assemble(taxa,passed):
 seqs={t:[]for t in taxa};parts=[];start=1
 for marker,align,measure in passed:
  if set(align)!=set(taxa):raise ValueError('Taxon partition mismatch')
  lengths={len(v)for v in align.values()}
  if len(lengths)!=1:raise ValueError('Unequal alignment length')
  n=lengths.pop()
  if n!=measure['retained_columns']or n<MIN_COLUMNS or measure['retained_parsimony_informative_columns']<MIN_INFORMATIVE:raise ValueError('Unqualified passed locus')
  parts.append({'marker_id':marker,'start_1based':start,'end_1based_inclusive':start+n-1,'columns':n,**measure})
  for t in taxa:seqs[t].append(align[t])
  start+=n
 combined={t:''.join(s)for t,s in seqs.items()};total=start-1
 if not parts or not total or any(len(s)!=total for s in combined.values()):raise ValueError('Empty/incomplete concatenation')
 cursor=1
 for p in parts:
  if p['start_1based']!=cursor or p['end_1based_inclusive']-cursor+1!=p['columns']:raise ValueError('Gap, overlap or invalid partition')
  cursor=p['end_1based_inclusive']+1
 if cursor!=total+1 or sum(p['columns']for p in parts)!=total:raise ValueError('Site partition not exhaustive')
 return combined,parts,total
def execution(unit):
 x=read(bound(unit['execution']))
 if x.get('actual_exit_code')!=0 or x.get('owned_group_empty')is not True:raise RuntimeError('Unit lacks successful closed execution')
 return {'execution':unit['execution'],'output':unit['output']}
def main(a):
 result_path=inside(a.result);result=read(result_path)
 if result.get('status')!='EXPLORATORY_PILOT_COMPUTATION_COMPLETE':raise RuntimeError('All candidate computation must finish before concatenation')
 manifest_path=bound(result['input_manifest']);manifest=read(manifest_path);taxa=manifest['taxa']
 if len(taxa)!=10 or len(set(taxa))!=10:raise ValueError('Exact10taxa required')
 names=[c['id']for c in manifest['candidates']];rows=result['rows']
 if len(set(names))!=len(names)or result['processed_candidates']!=len(names)or len(rows)!=len(names)or[n['id']for n in rows]!=names:raise RuntimeError('Incomplete, duplicate or reordered candidate universe')
 overlay_path=inside(a.taxa_overlay);overlay=read(overlay_path);bytax={g['accession']:g for g in overlay['input_genomes']}
 if set(bytax)!=set(taxa):raise RuntimeError('Taxon source overlay differs')
 passed=[];loci=[];refs=[]
 for row in rows:
  name=row['id'];commit_path=result_path.parent/'candidates'/name/'candidate_commit.json'
  if read(commit_path)!=row:raise RuntimeError('Candidate row commit differs '+name)
  metrics_path=bound(row['metrics']);m=read(metrics_path)
  if m['candidate']!=name or m['taxa']!=10 or m['column_occupancy_threshold']!=OCCUPANCY:raise RuntimeError('Candidate metrics identity/occupancy differs '+name)
  if not all(isinstance(k,bool)for k in m['column_mask'])or len(m['column_mask'])!=m['alignment_columns']or sum(m['column_mask'])!=m['retained_columns']:raise RuntimeError('Invalid columnmask '+name)
  receipt={'candidate_commit':ref(commit_path),'metrics':ref(metrics_path),'mafft':execution(row['mafft'])}
  measurement={'marker_id':name,'upstream_status':row['status'],'retained_columns':m['retained_columns'],'pretrim_parsimony_informative_columns':m['parsimony_informative_columns'],'exclusion_reasons':[],'profile_and_alignment_acceptance':'EXPLORATORY_ONLY'}
  if row['status']!='ALIGNED_PROFILE_BUILT_EXPLORATORY':
   measurement['exclusion_reasons'].append('UPSTREAM_'+row['status']);measurement['retained_parsimony_informative_columns']=None
  else:
   receipt['profile']=execution(row['profile']);bound(row['profile']['output']);trim_path=bound(row['trimmed']);trim=fasta(trim_path,taxa)
   if m['alignment']!=row['mafft']['output']:raise RuntimeError('Metrics/alignment reference mismatch '+name)
   align=fasta(bound(m['alignment']),taxa)
   if any(''.join(c for c,keep in zip(align[t],m['column_mask'])if keep)!=trim[t]for t in taxa):raise RuntimeError('Trimmed sequence differs from committed columnmask '+name)
   measurement.update(columns(trim));receipt['trimmed']=ref(trim_path)
   if measurement['retained_columns']!=m['retained_columns']:raise RuntimeError('Retained length differs '+name)
   if measurement['minimum_retained_unambiguous_column_occupancy']<OCCUPANCY:raise RuntimeError('Retained column below original0.8mask '+name)
   if measurement['retained_columns']<MIN_COLUMNS:measurement['exclusion_reasons'].append('FEWER_THAN30_RETAINED_COLUMNS')
   if measurement['retained_parsimony_informative_columns']<MIN_INFORMATIVE:measurement['exclusion_reasons'].append('FEWER_THAN10_RETAINED_PARSIMONY_INFORMATIVE_COLUMNS')
   if not measurement['exclusion_reasons']:passed.append((name,trim,{k:v for k,v in measurement.items()if k.startswith('retained_')or k=='minimum_retained_unambiguous_column_occupancy'}))
  measurement['included']=not measurement['exclusion_reasons'];measurement['receipts']=receipt;loci.append(measurement);refs.append(receipt)
 combined,parts,total=assemble(taxa,passed);out=inside(a.output);out.mkdir(parents=True,exist_ok=True)
 fa=''.join('>'+t+'\n'+'\n'.join(s[i:i+80]for i in range(0,len(s),80))+'\n'for t,s in combined.items())
 fa_ref=create(out/'concatenated.faa',fa.encode('ascii'))
 nexus='#NEXUS\nbegin sets;\n'+''.join('  charset '+p['marker_id']+' = '+str(p['start_1based'])+'-'+str(p['end_1based_inclusive'])+';\n'for p in parts)+'end;\n'
 nx_ref=create(out/'partitions.nex',nexus.encode());tsv=io.StringIO(newline='');w=csv.DictWriter(tsv,fieldnames=list(parts[0]),delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(parts);ts_ref=create(out/'partitions.tsv',tsv.getvalue().encode())
 loci_ref=jcreate(out/'locus_metrics_and_exclusions.json',loci)
 flags=[{k:bytax[t].get(k)for k in('accession','species','genus','family','source_supported_scope','source_holds_preserved','source_pending_reasons','source_masks','accepted_method_estimate','independent_taxonomy','production_panel_acceptance')}for t in taxa]
 taxa_ref=jcreate(out/'taxa_source_flags.json',{'taxa':flags,'source_overlay':ref(overlay_path),'sourceheld_taxa_preserved_in_exploratory_pilot':True})
 data={'schema':'TREE2_EXPLORATORY_PILOT_CONCAT_V001','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'EXPLORATORY_CONCATENATION_READY','scope':SCOPE,'input_result':ref(result_path),'input_candidate_manifest':ref(manifest_path),'script':ref(Path(__file__).resolve()),'taxa':taxa,'candidate_universe':len(names),'included_loci':len(passed),'excluded_loci':len(names)-len(passed),'alignment_columns':total,'partition_site_coverage':'EXACT_NONOVERLAPPING_EXHAUSTIVE_1BASED','criteria':{'already_applied_column_unambiguous_occupancy':OCCUPANCY,'minimum_retained_columns':MIN_COLUMNS,'minimum_retained_parsimony_informative_columns':MIN_INFORMATIVE,'topology_based_selection':False},'concatenated':fa_ref,'partitions_nexus':nx_ref,'partitions_tsv':ts_ref,'locus_metrics':loci_ref,'taxa_source_flags':taxa_ref,'marker_acceptance':'NOT_GRANTED','orthology_acceptance':'NOT_GRANTED','final_species_tree_acceptance':'NOT_GRANTED','old_tree1_or_old105_used':False,'original_genomes_rehashed_or_modified':False,'scientific_tree_process_launched':False,'source_taxonomy_holds_preserved':True}
 r=jcreate(out/'data_receipt.json',data);print(json.dumps({'receipt':r,'included_loci':len(passed),'excluded_loci':len(names)-len(passed),'taxa':len(taxa),'sites':total},indent=2))
def fixture():
 taxa=['GCF_'+str(i).zfill(9)+'.1'for i in range(10)];a={t:'A'*20+('A'if i<5 else'C')*10 for i,t in enumerate(taxa)};m=columns(a)
 assert m['retained_columns']==30 and m['retained_parsimony_informative_columns']==10
 combined,parts,n=assemble(taxa,[('fixture1',a,m),('fixture2',a,m)])
 assert n==60 and parts[0]['end_1based_inclusive']==30 and parts[1]['start_1based']==31 and parts[1]['end_1based_inclusive']==60 and len(combined)==10
 rejected=False
 try:assemble(taxa,[('bad',a,{**m,'retained_parsimony_informative_columns':9})])
 except ValueError:rejected=True
 assert rejected
 print('PASS formatfixture: exact10taxa,30columns/10informative threshold,underthreshold rejection,exhaustive60site partitions; no actual data processed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--result',default='analysis/marker_discovery/pilot10_recovered_v001/compute/result.json');p.add_argument('--taxa-overlay',default='work/marker_discovery_start/saved_pilot10_inputs_with_qc_overlay.json');p.add_argument('--output',default='analysis/marker_discovery/pilot10_recovered_v001/concat_v001');p.add_argument('--fixture',action='store_true');a=p.parse_args();fixture()if a.fixture else main(a)
