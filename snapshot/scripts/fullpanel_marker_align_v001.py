"""Align all saved qualifying copies in196 new-project families; no search or final marker acceptance."""
from pathlib import Path
import os,sys,json,time,csv,subprocess,shutil,hashlib,collections,math,signal
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import marker_owned_cleanup_v002 as own
from checkm1_owned_rss_sample_v001 import sample_owned_rss

def column_mask(aligned,genomes,threshold):
 lengths={len(s)for s in aligned.values()}
 if len(lengths)!=1:raise ValueError('Unequal alignment lengths')
 length=next(iter(lengths));columns=[];occupancy=[]
 for i in range(length):
  observed={name.split('|',1)[0]for name,seq in aligned.items()if seq[i]in'ACDEFGHIKLMNPQRSTVWY'}
  value=len(observed)/genomes;occupancy.append(value);columns.append(value>=threshold)
 return columns,occupancy

def validate_residues(original,aligned):
 if set(original)!=set(aligned):raise ValueError('Alignment changed original leaf IDs')
 for name,sequence in original.items():
  if aligned[name].replace('-','').replace('.','')!=sequence:raise ValueError('Alignment changed residues for '+name)

def group_members(group):
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   value=own.identity(int(p.name))
   if value['process_group']==group:result.append(value)
  except(FileNotFoundError,ProcessLookupError):pass
 return result

def main():
 def interrupted(number,frame):raise InterruptedError('Owned marker controller signal '+str(number))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 plan_path=Path(sys.argv[1]);expected=sys.argv[2];assert g.sha(plan_path)==expected;P=g.read(plan_path);E=R/P['work'];OUT=R/P['output'];STOP=R/P['stop_path'];OUT.mkdir(exist_ok=True)
 with(OUT/'once_claim.json').open('x')as claim:json.dump({'input_plan_sha256':expected,'started_utc':g.utc(),'no_automatic_retry':True},claim)
 for row in P['sources']:g.bound(row)
 admission=g.read(g.bound(P['scientific_admission_scope']))
 assert admission['status']=='ROOT_GO_SOURCE_SCOPE_FULL919_SAVED196_FAMILY_ALIGNMENT'and admission['plan_scope_sha256']==P['scientific_scope_sha256']
 for row in P['tool_files']:
  path=Path(row['path']);assert path.stat().st_size==row['bytes']and g.sha(path)==row['sha256']
 native=g.read(E/'native_owner.json')['native_owner'];owner=own.identity(os.getpid());g.save(E/'linux_owner.json',owner);os.sched_setaffinity(0,{P['cpu']})
 marker_manifest=g.read(g.bound(P['screen_manifest']));screen=g.read(g.bound(P['screen_result']));qc=g.read(g.bound(P['QC_measurements']));qrows={q['accession']:q for q in qc['rows']};taxa=[q['accession']for q in marker_manifest['rows']];assert len(taxa)==919 and set(taxa)==set(qrows)
 selected=P['selected_profiles'];assert len(selected)==196 and len(set(selected))==196
 families={name:{}for name in selected};metadata={name:{}for name in selected};dispositions={name:[]for name in selected};commits=[];start=time.monotonic();last=0;phase='EXTRACTING_SAVED_HITS';done=0;current=None;science=0.;controller_peak=0
 def guard(known=()):
  nonlocal controller_peak
  if STOP.exists()or(R/'state/STOP').exists():raise InterruptedError('Scoped marker/global STOP')
  if time.monotonic()-start>P['cold_seconds']or science>P['science_seconds']:raise TimeoutError('Finite new marker stage allocation exhausted')
  if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Backing disk below40GiB')
  mem=g.available()
  if mem<P['minimum_linux_available_bytes']:raise MemoryError('Linux available headroom stop')
  if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=owner['boot_id']:raise RuntimeError('Boot identity changed')
  rss=sample_owned_rss([owner,*known]);ram=sum(shutil.disk_usage(p).used for p in(Path('/tmp'),Path('/dev/shm')));controller_peak=max(controller_peak,rss+ram)
  if rss+ram>P['linux_RSS_plus_RAM_bytes']:raise MemoryError('Summed owned RSS plus private RAM exceeds admitted partition')
  return rss,ram,mem
 def publish(detail,force=False,**extra):
  nonlocal last
  if not force and time.monotonic()-last<30:return
  rss,ram,mem=guard();v={'id':'06','name':'Marker discovery and orthology','status':'RUNNING','operation':phase,'detail':detail,'done':done,'total':196,'unit':'full919 candidate-family alignments; all qualifying copies and uncertainty retained','pid':native['pid'],'creation_time_utc':native['creation_time_utc'],'current_profile':current,'owned_Linux_RSS_bytes':rss,'private_RAM_used_bytes':ram,'Linux_available_bytes':mem,'source_taxonomy_type_QC_and_paralogy_holds_preserved':True,'marker_set_acceptance':'NOT_GRANTED','final_panel_acceptance':False,'gene_tree_validation':'NOT_YET_RUN','updated_utc':g.utc(),**extra}
  for target in(E/'progress.json',R/'state/stages/06.json'):
   try:g.save(target,v)
   except OSError as error:
    try:
     with(E/'optional_display_errors.jsonl').open('a')as log:log.write(json.dumps({'path':str(target),'error':repr(error),'at_utc':g.utc()})+'\n')
    except OSError:pass
  last=time.monotonic()
 def align(folder,source):
  nonlocal science
  unit=folder/'mafft_unit';unit.mkdir();args=[P['mafft'],'--amino','--retree','2','--maxiterate','0','--thread','1','--inputorder','--quiet',str(source)];g.save(unit/'command.json',{'argv':args,'input':g.ref(source),'started_utc':g.utc()});p=None;identity=None;known={};error=None;peak=0;minmem=None;t=time.monotonic()
  env={**os.environ,'TMPDIR':str(unit/'tmp'),'MAFFT_TMPDIR':str(unit/'tmp'),'XDG_CACHE_HOME':str(unit/'cache'),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'};(unit/'tmp').mkdir();result=unit/'alignment.faa'
  try:
   with result.open('xb')as out,(unit/'stderr.txt').open('xb')as err:
    p=subprocess.Popen(args,cwd=unit,env=env,stdout=out,stderr=err,start_new_session=True);identity=own.identity(p.pid);known[p.pid]=identity
    while p.poll()is None:
     own.track_descendants(identity,known);rss,ram,mem=guard(known.values());peak=max(peak,rss+ram);minmem=mem if minmem is None else min(minmem,mem)
     if time.monotonic()-t>P['unit_seconds']or science+time.monotonic()-t>P['science_seconds']:raise TimeoutError('MAFFT finite unit or stage allocation')
     publish('Actual MAFFT alignment '+str(current),unit_peak_RSS_plus_RAM=peak);time.sleep(.5)
    code=p.wait()
   if code!=0:raise RuntimeError('MAFFT actual exit '+str(code))
  except BaseException as e:
   error=repr(e)
   if p is not None:g.save(unit/'failure_cleanup.json',own.cleanup_linux_helper(p,identity,known,STOP,'MARKER_FULL919_'+str(os.getpid())))
   raise
  finally:
   left=[q for q in known.values()if own.current_matching(q)is not None];members=group_members(identity['process_group'])if identity is not None else[];elapsed=time.monotonic()-t;science+=elapsed;g.save(unit/'execution.json',{'actual_exit_code':p.returncode if p is not None else None,'actual_child_waited_and_reaped':p is not None and p.poll()is not None,'child_identity':identity,'captured_owned_identities':list(known.values()),'remaining_owned_identities':left,'remaining_group_members':members,'group_closed':not left and not members,'elapsed_seconds':elapsed,'peak_summed_owned_Linux_RSS_plus_private_RAM_bytes':peak,'minimum_Linux_available_bytes':minmem,'error':error,'ended_utc':g.utc()})
   if(left or members)and error is None:raise RuntimeError('MAFFT left owned descendants')
  return result,unit/'execution.json'
 common=(R/'state/checkm2_pilot.lock').open('r+b');__import__('fcntl').flock(common,__import__('fcntl').LOCK_EX|__import__('fcntl').LOCK_NB)
 lease=(OUT/'queue.lock').open('a+b');__import__('fcntl').flock(lease,__import__('fcntl').LOCK_EX|__import__('fcntl').LOCK_NB)
 try:
  publish('Validating closed saved marker/QC inputs; extracting original sequences',True)
  commits_by_acc={g.read(g.bound(row))['accession']:row for row in screen['row_commits']}
  assert set(commits_by_acc)==set(taxa)
  for index,row in enumerate(marker_manifest['rows']):
   guard();acc=row['accession'];c=g.read(g.bound(commits_by_acc[acc]));assert c['source_annotation_commit']==row['commit'];g.bound(row['commit']);outputs={Path(q['path']).name:q for q in c['outputs']}
   copies=list(csv.DictReader(g.bound(outputs['profile_copy_counts.tsv']).open(),delimiter='\t'));cells={q['profile']:q for q in copies};assert len(cells)==281
   seqs=g.fasta(g.bound(row['proteins']));coordinates={q['protein_id']:q for q in g.read(g.bound(row['coordinates']))};assert set(seqs)==set(coordinates)
   for name in selected:
    cell=cells[name];targets=cell['target_ids'].split(';')if cell['target_ids']else[];ambiguous=set(cell['cross_profile_ambiguous_targets'].split(';'))if cell['cross_profile_ambiguous_targets']else set();assert len(targets)==int(cell['qualifying_copy_count'])
    dispositions[name].append({'accession':acc,'search_state':cell['search_state'],'qualifying_copy_count':len(targets),'cross_profile_ambiguous_targets':sorted(ambiguous),'unambiguous_single_copy':int(cell['unambiguous_single_copy']),'no_qualifying_hit_is_not_biological_absence':True,'QC_95_5':qrows[acc]['unrounded_QC_95_5'],'source_masks':qrows[acc]['source_masks']})
    for target in targets:
     assert target not in families[name]and target in seqs;coordinate=coordinates[target];assert coordinate['accession']==acc and coordinate['aa_length']==len(seqs[target]);families[name][target]=seqs[target]
     metadata[name][target]={'accession':acc,'original_prodigal_header':coordinate['original_prodigal_header'],'prodigal_gene_id':coordinate['prodigal_gene_id'],'contig':coordinate['contig'],'start':coordinate['start'],'end':coordinate['end'],'strand':coordinate['strand'],'canonical_protein_id':target,'sequence_sha256':hashlib.sha256(seqs[target].encode()).hexdigest(),'original_coordinates_source':row['coordinates'],'source_annotation':row['commit'],'source_proteome':row['proteins'],'cross_profile_ambiguous':target in ambiguous,'candidate_copy_count_in_genome':len(targets),'QC_95_5':qrows[acc]['unrounded_QC_95_5'],'source_masks':qrows[acc]['source_masks'],'independent_taxonomy':'UNRESOLVED_SEPARATE'}
   publish('Extracting saved qualifying proteins '+str(index+1)+'/919')
  phase='ALIGNING_FULL919_CANDIDATE_FAMILIES'
  for name in selected:
   guard();current=name;folder=OUT/'families'/name;folder.mkdir(parents=True,exist_ok=False);source=folder/'all_qualifying_copies.faa';g.write_fasta(source,families[name]);g.save(folder/'leaf_provenance.json',metadata[name]);g.save(folder/'genome_dispositions.json',dispositions[name]);original=families.pop(name);metadata.pop(name);dispositions.pop(name)
   alignment,execution=align(folder,source);aligned=g.fasta(alignment,aligned=True);validate_residues(original,aligned);mask,occupancy=column_mask(aligned,919,P['column_genome_occupancy']);trimmed={n:''.join(c for c,k in zip(seq,mask)if k)for n,seq in aligned.items()};empty=[n for n,seq in trimmed.items()if not seq or all(c not in'ACDEFGHIKLMNPQRSTVWY'for c in seq)]
   if sum(mask)>0:g.write_fasta(folder/'trimmed_all_copies.faa',trimmed)
   metrics={'profile':name,'sequences':len(aligned),'genomes_with_qualifying_hits':len({n.split('|',1)[0]for n in aligned}),'original_alignment_columns':len(mask),'retained_columns':sum(mask),'genome_occupancy_threshold':P['column_genome_occupancy'],'column_genome_occupancy':occupancy,'column_mask':mask,'copy_number_never_inflates_genome_occupancy':True,'empty_after_mask_leaf_IDs':empty,'input_leaf_IDs_and_all_residues_preserved':True,'marker_acceptance':'NOT_GRANTED','orthology_paralogy_gene_tree_sensitivity_broader_discovery_still_required':True};g.save(folder/'metrics.json',metrics)
   artifacts=[g.ref(source),g.ref(alignment),g.ref(execution),g.ref(folder/'leaf_provenance.json'),g.ref(folder/'genome_dispositions.json'),g.ref(folder/'metrics.json')]
   if(folder/'trimmed_all_copies.faa').exists():artifacts.append(g.ref(folder/'trimmed_all_copies.faa'))
   commit={'status':'FULL919_CANDIDATE_ALL_COPY_ALIGNMENT0_VALIDATED_PENDING_EXTERNAL_CLOSURE','profile':name,'artifacts':artifacts,'input_plan_sha256':expected,'native_owner':native,'usable_alignment_ge30_columns_no_empty_leaf':sum(mask)>=30 and not empty,'all_qualifying_copies_retained':True,'source_QC_taxonomy_type_and_paralogy_holds_preserved':True,'marker_set_acceptance':'NOT_GRANTED','gene_trees':'NOT_RUN'};g.save(folder/'COMMITTED.json',commit);commits.append(g.ref(folder/'COMMITTED.json'));done+=1;publish('Candidate-family alignment checkpoint committed',True)
  g.save(OUT/'result.json',{'status':'ALL196_FULL919_CANDIDATE_FAMILIES_ALIGNED_PENDING_EXTERNAL_CLOSURE','family_commits':commits,'families':196,'genomes':919,'QC_closed_authority':P['QC_closed_authority'],'screen_closed_authority':P['screen_closed_authority'],'input_plan':g.ref(plan_path),'science_seconds':science,'cold_elapsed_seconds':time.monotonic()-start,'peak_controller_and_owned_sample_RSS_plus_private_RAM_bytes':controller_peak,'all_original_leaf_IDs_residues_copies_and_masks_preserved':True,'orthology_paralogy_gene_tree_sensitivity_broader_discovery_still_required':True,'final_marker_or_panel_or_full_or_representative_tree_acceptance':False});publish('All196 full919 candidate-family alignments completed; external verification and gene-tree assessment next',True,status='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as e:
  g.save(E/'failure.json',{'error':repr(e),'current_profile':current,'completed_families':done,'science_seconds_actual_debit':science,'cold_seconds_actual_debit':time.monotonic()-start,'accepted_input_searches_not_replayed':True,'unknown_or_unrun_not_negative':True,'at_utc':g.utc()});raise
 finally:
  __import__('fcntl').flock(lease,__import__('fcntl').LOCK_UN);lease.close();__import__('fcntl').flock(common,__import__('fcntl').LOCK_UN);common.close()

if __name__=='__main__':main()
