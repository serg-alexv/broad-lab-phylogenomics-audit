"""Twenty length-stratified exploratory MAFFT comparisons, never production selection."""
from pathlib import Path
import argparse,json,os,re,sys,time
import marker_pilot_compute_v001 as guard
R=guard.R
from marker_pilot_hmmsearch_v001 import write_tsv

def choose_strata(rows,count=20):
 """Equal-count strata over raw median protein length, deterministic lower midpoint."""
 ordered=sorted(rows,key=lambda r:(r['twice_median_length'],r['id']))
 if len(ordered)<count:raise ValueError('Not enough candidates for declared strata')
 selected=[]
 for i in range(count):
  lo=i*len(ordered)//count;hi=(i+1)*len(ordered)//count;rank=(lo+hi-1)//2
  selected.append({**ordered[rank],'stratum':i+1,'stratum_rank_start':lo+1,'stratum_rank_end':hi,'selected_rank':rank+1})
 return selected

def residue_pairs(aligned,original):
 """Pairs are (sequence indices, original residue positions), including ambiguity."""
 names=sorted(original)
 if set(aligned)!=set(original):raise ValueError('Aligned protein IDs differ from original input')
 lengths={len(s)for s in aligned.values()}
 if len(lengths)!=1:raise ValueError('Unequal alignment lengths')
 for name in names:
  if aligned[name].replace('-','').replace('.','')!=original[name]:raise ValueError('Alignment changed or lost original residues: '+name)
 positions=[0]*len(names);pairs=set()
 for col in range(next(iter(lengths))):
  occupied=[]
  for i,name in enumerate(names):
   if aligned[name][col]not in '-.':positions[i]+=1;occupied.append((i,positions[i]))
  for at,(i,p)in enumerate(occupied):
   for j,q in occupied[at+1:]:pairs.add((i,j,p,q))
 return pairs

def pair_comparison(fast,slow,original):
 a=residue_pairs(fast,original);b=residue_pairs(slow,original);inter=len(a&b);union=len(a|b)
 return {'fast_aligned_residue_pairs':len(a),'slow_aligned_residue_pairs':len(b),'shared_aligned_residue_pairs':inter,'union_aligned_residue_pairs':union,'fast_pair_fraction_recovered_by_slow':inter/len(a)if a else None,'slow_pair_fraction_present_in_fast':inter/len(b)if b else None,'paired_residue_jaccard':inter/union if union else None,'original_residue_identity_verified':True,'interpretation':'Agreement between two alignments, not alignment accuracy against biological truth'}

def main(a):
 if os.name!='posix':raise RuntimeError('Actual sensitivity computation requires Linux')
 source_path=guard.inside(a.input_manifest);fast_path=guard.inside(a.fast_manifest);admission_path=guard.inside(a.admission);admission=guard.read(admission_path);out=guard.inside(a.output);out.mkdir(parents=True,exist_ok=True)
 bindings={'input_manifest_sha256':guard.sha(source_path),'fast_manifest_sha256':guard.sha(fast_path),'script_sha256':guard.sha(__file__),'guard_script_sha256':guard.sha(guard.__file__),'table_helper_script_sha256':guard.sha(Path(__file__).with_name('marker_pilot_hmmsearch_v001.py'))}
 if admission.get('status')!='ROOT_ADMITTED_EXPLORATORY_ALIGNMENT_SENSITIVITY'or any(admission.get(k)!=v for k,v in bindings.items()):raise RuntimeError('Fresh exact Root shared-resource admission required')
 if not 0<admission.get('max_rss_bytes',0)<=256*1024**2 or admission.get('linux_available_stop_bytes',0)<int(1.25*1024**3)or not 0<admission.get('unit_timeout_seconds',0)<=180:raise RuntimeError('Sensitivity resource bounds differ')
 cpu=admission['cpu']
 if type(cpu)is not int or cpu not in os.sched_getaffinity(0)or cpu in(0,1):raise RuntimeError('One QC-unused CPU2/3 required')
 os.sched_setaffinity(0,{cpu});spec=admission['tools']['mafft'];tool=Path(spec['path']).resolve()
 if guard.sha(tool)!=spec['sha256']:raise RuntimeError('Pinned MAFFT changed')
 files=[{'path':str(tool),'sha256':guard.sha(tool)}];helpers=tool.parent.parent/'libexec/mafft'
 if helpers.is_dir():
  for p in sorted(helpers.rglob('*')):
   if p.is_file():files.append({'path':str(p),'sha256':guard.sha(p)})
 guard.TOOLCHAIN_SHA=guard.hashlib.sha256(json.dumps({'files':files,'sources':bindings},sort_keys=True).encode()).hexdigest();guard.save(out/'toolchain_snapshot.json',{'files':files,'sources':bindings,'canonical_sha256':guard.TOOLCHAIN_SHA})
 source=guard.read(source_path);fast=guard.read(fast_path)
 if fast.get('status')!='EXPLORATORY_PILOT_COMPUTATION_COMPLETE':raise ValueError('Fast comparison input has not completed')
 guard.bound(fast['input_manifest'])
 if fast['input_manifest']['sha256']!=guard.sha(source_path):raise ValueError('Fast/source input manifest differs')
 taxa=source['taxa']
 if len(taxa)!=10 or len(set(taxa))!=10:raise ValueError('Ten unique exploratory taxa required')
 inventory=[];source_by_id={}
 for row in source['candidates']:
  name=row['id']
  if not re.fullmatch(r'[A-Za-z0-9_.-]+',name)or name in source_by_id:raise ValueError('Unsafe/duplicate candidate ID')
  path=guard.bound({'path':row['fasta_path'],'sha256':row['sha256']});records=guard.fasta(path);lengths=sorted(len(s.rstrip('*'))for s in records.values());guard.validate_alignment({n:'A'for n in records},taxa)
  inventory.append({'id':name,'twice_median_length':lengths[4]+lengths[5],'length_min':lengths[0],'length_max':lengths[-1],'source':guard.ref(path)});source_by_id[name]=row
 selection=choose_strata(inventory,20);fast_by_id={r['id']:r for r in fast['rows']}
 if len(fast_by_id)!=len(inventory)or set(fast_by_id)!=set(source_by_id):raise ValueError('Fast/source candidate set differs')
 guard.save(out/'selection.json',{'rule':'20 equal-count strata sorted by median raw sequence length, ID tie-break, lower midpoint within each stratum; no tree/informativity-based selection','candidate_count':len(inventory),'selected':selection,'input_manifest':guard.ref(source_path),'fast_manifest':guard.ref(fast_path),'marker_set_acceptance':'NOT_GRANTED'})
 started=guard.utc();owner=guard.proc(os.getpid());done=0;last=0;current=None;rows=[]
 def publish(unit,peak=None,mem=None,terminal=None):
  nonlocal last
  if terminal is None and time.monotonic()-last<30:return
  stage={'id':'06','name':'Marker discovery and orthology','status':terminal or'RUNNING','operation':'EXPLORATORY20_ALIGNMENT_SENSITIVITY','detail':str(current)+' / '+unit,'done':done,'total':20,'unit':'length-stratified slow alignments compared','started_utc':started,'updated_utc':guard.utc(),'pid':a.native_pid or os.getpid(),'creation_time_utc':a.native_creation_utc or None,'linux_owner_identity':owner,'cpu_affinity':[cpu],'summed_owned_rss_bytes':peak,'linux_available_bytes':mem,'marker_set_acceptance':'NOT_GRANTED','log_path':str(out/'progress.json')};guard.save(out/'progress.json',stage);guard.save(R/'state/stages/06.json',stage);last=time.monotonic()
 publish('length-stratified candidates selected',terminal='RUNNING')
 try:
  for selected in selection:
   name=current=selected['id'];folder=out/'candidates'/name;folder.mkdir(parents=True,exist_ok=True);f=fast_by_id[name];execution=guard.read(guard.bound(f['mafft']['execution']))
   if execution.get('actual_exit_code')!=0 or execution.get('owned_group_empty')is not True:raise ValueError('Fast alignment lacks actual0/closed group')
   original={n:s.rstrip('*')for n,s in guard.fasta(guard.bound(selected['source'])).items()};normalized=folder/'original.faa'
   if normalized.exists():
    if guard.fasta(normalized)!=original:raise ValueError('Normalized input changed on resume')
   else:guard.write_fasta(normalized,original)
   fast_alignment=guard.fasta(guard.bound(f['mafft']['output']),aligned=True);residue_pairs(fast_alignment,original)
   inputs=[guard.ref(p)for p in(normalized,source_path,fast_path,out/'selection.json',Path(__file__),Path(guard.__file__),Path(__file__).with_name('marker_pilot_hmmsearch_v001.py'))]
   slow=guard.run_unit(folder,'mafft',[str(tool),'--amino','--localpair','--maxiterate','1000','--thread','1','--inputorder','--quiet',str(normalized)],inputs,'slow_alignment.faa',admission,publish)
   slow_alignment=guard.fasta(guard.bound(slow['output']),aligned=True);comparison=pair_comparison(fast_alignment,slow_alignment,original);fm,_=guard.metrics(fast_alignment,taxa,a.occupancy);sm,_=guard.metrics(slow_alignment,taxa,a.occupancy)
   review=comparison['paired_residue_jaccard']is None or comparison['paired_residue_jaccard']<a.review_jaccard
   result={'id':name,'stratum':selected['stratum'],'median_raw_sequence_length':selected['twice_median_length']/2,**comparison,'fast_alignment_columns':fm['alignment_columns'],'slow_alignment_columns':sm['alignment_columns'],'fast_retained_columns':fm['retained_columns'],'slow_retained_columns':sm['retained_columns'],'fast_informative_columns':fm['parsimony_informative_columns'],'slow_informative_columns':sm['parsimony_informative_columns'],'fast_mean_unambiguous_occupancy':fm['mean_unambiguous_occupancy'],'slow_mean_unambiguous_occupancy':sm['mean_unambiguous_occupancy'],'review_status':'REVIEW_ALIGNMENT_SENSITIVITY'if review else'NO_REVIEW_FLAG_FROM_THIS_COMPARISON','review_jaccard_threshold':a.review_jaccard,'marker_set_acceptance':'NOT_GRANTED'}
   guard.save(folder/'comparison.json',{'comparison':result,'source':selected['source'],'fast_alignment':f['mafft']['output'],'fast_execution':f['mafft']['execution'],'slow_alignment':slow,'fast_metrics':fm,'slow_metrics':sm,'review_is_not_automatic_acceptance_or_exclusion':True});rows.append(result);done+=1;guard.save(out/'completed_comparisons.json',{'rows':rows,'processed':done,'total':20});publish('alignment comparison checkpoint')
  write_tsv(out/'comparisons.tsv',list(rows[0]),rows);guard.save(out/'result.json',{'status':'EXPLORATORY20_ALIGNMENT_SENSITIVITY_COMPLETE','compared':len(rows),'review_flagged':sum(r['review_status']=='REVIEW_ALIGNMENT_SENSITIVITY'for r in rows),'selection':guard.ref(out/'selection.json'),'table':guard.ref(out/'comparisons.tsv'),'rows':rows,'alignment_accuracy_claimed':False,'automatic_marker_acceptance_or_exclusion':False,'marker_set_acceptance':'NOT_GRANTED','full_panel_validation':'NOT_RUN'});publish('twenty alignment comparisons complete',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as ex:
  guard.save(out/'failure.json',{'status':'SENSITIVITY_STOPPED_PRESERVE_CHECKPOINTS','error':repr(ex),'processed':done,'current':current,'unfinished_states':'UNKNOWN_OR_NOT_RUN'});publish(str(ex),terminal='STOPPED');raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-manifest',required=True);p.add_argument('--fast-manifest',required=True);p.add_argument('--admission',required=True);p.add_argument('--output',required=True);p.add_argument('--occupancy',type=float,default=.8);p.add_argument('--review-jaccard',type=float,default=.9);p.add_argument('--native-pid',type=int);p.add_argument('--native-creation-utc');a=p.parse_args()
 if not 0<a.occupancy<=1 or not 0<a.review_jaccard<=1:p.error('Invalid comparison criteria')
 main(a)
