"""Serial, provisional 281-profile assessment of the new uniform919 proteomes.

No annotation, profile construction, previous search, QC model or tree is replayed.
Per-genome searches retain the frozen original29133-target reference calibration.
Exact previously searched protein sequences reuse their actual closed raw search.
"""
from pathlib import Path
import argparse, collections, fcntl, hashlib, json, os, signal, sys, time
import marker_pilot_compute_v001 as g
import marker_pilot_hmmsearch_v001 as h

R=g.R
SCOPE='PROVISIONAL_FULL919_CANDIDATE_MARKER_COVERAGE_NOT_FINAL_ORTHOLOGY_OR_PANEL_ACCEPTANCE'

def bound(v):
 p=g.bound(v)
 if p.stat().st_size!=v['bytes']:raise RuntimeError('Bound size differs '+str(p))
 return p

def summarize(profile_lengths,groups,accession):
 copies=collections.defaultdict(list);targets=collections.defaultdict(list);hits=[]
 for (query,target),v in sorted(groups.items()):
  if v['hmm_coverage']<.7 or v['target_coverage']<.5:continue
  copies[query].append(target);targets[target].append(query)
  hits.append({'profile':query,'accession':accession,'target_id':target,**v})
 ambiguous={k:v for k,v in targets.items()if len(v)>1}
 cells=[]
 for query in profile_lengths:
  identifiers=copies[query];amb=[p for p in identifiers if p in ambiguous]
  cells.append({'profile':query,'accession':accession,'search_state':'SEARCHED_COMPLETE','qualifying_copy_count':len(identifiers),'target_ids':';'.join(identifiers),'cross_profile_ambiguous_targets':';'.join(amb),'unambiguous_single_copy':int(len(identifiers)==1 and not amb),'biological_absence_claimed':False})
 return hits,cells,ambiguous

def main(a):
 if os.name!='posix':raise RuntimeError('Linux scientific execution required')
 def interrupted(signum,frame):raise InterruptedError('Fullpanel marker controller signal '+str(signum))
 signal.signal(signal.SIGTERM,interrupted)
 manifest_path=g.inside(a.manifest);admission_path=g.inside(a.admission)
 m=g.read(manifest_path);ad=g.read(admission_path);out=g.inside(a.output);out.mkdir(parents=True,exist_ok=True)
 for k,p in [('script',Path(__file__).resolve()),('guard',Path(g.__file__).resolve()),('parser',Path(h.__file__).resolve())]:
  if g.ref(p)!=m[k]:raise RuntimeError('Scientific source changed '+k)
 if ad.get('status')!='ROOT_ADMITTED_PROVISIONAL_FULL919_MARKER_SCREEN' or ad['manifest']!=g.ref(manifest_path) or ad['script']!=m['script'] or not ad['annotation_closed_verified'] or not ad['resource_and_exclusivity_preflight_pass']:raise RuntimeError('Exact Root scientific admission required')
 if ad['cpu']!=2 or ad['max_rss_bytes']!=192*1024**2 or ad['native_rss_reserve_bytes']!=64*1024**2 or ad['linux_available_stop_bytes']!=1342177280 or ad['unit_timeout_seconds']!=600 or ad['cold_timeout_seconds']!=43200 or ad['science_timeout_seconds']!=39600:raise RuntimeError('Finite reviewed resource/budget contract differs')
 if m['genomes']!=919 or len(m['rows'])!=919 or len({x['accession']for x in m['rows']})!=919 or m['proteins']!=sum(x['protein_count']for x in m['rows']):raise RuntimeError('Frozen full919 scope differs')
 if m['policy']['reference_target_count']!=29133 or m['policy']['full_sequence_evalue_max']!=1e-5 or m['policy']['independent_domain_evalue_max']!=1e-5 or m['policy']['minimum_union_hmm_coverage']!=.7 or m['policy']['minimum_union_target_coverage']!=.5:raise RuntimeError('Frozen original search calibration/thresholds differ')
 for k in ('annotation_closed_authority','verified_annotation_rows','profile_manifest','profile_closed_authority','hmmsearch','hmmsearch_manual'):bound(m[k])
 if 2 not in os.sched_getaffinity(0):raise RuntimeError('CPU2 unavailable')
 os.sched_setaffinity(0,{2});lease=(out/'queue.lock').open('a+');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
 owner=g.proc(os.getpid());g.save(out/'owner.json',{'identity':owner,'manifest':g.ref(manifest_path),'admission':g.ref(admission_path),'native_owner':{'pid':a.native_pid,'creation_time_utc':a.native_creation_utc},'started_utc':g.utc()})
 start=time.monotonic();started=g.utc();last=0;done=0;science=0.;phase='validating existing281 profiles';current=None
 old_stop=g.stop_requested;g.stop_requested=lambda:old_stop()or(R/'state/STOP_FULLPANEL_MARKER_SCREEN').exists()or g.inside(a.stop_file).exists()
 def gates():
  if g.stop_requested():raise InterruptedError('Project/marker/fullpanel stop requested')
  if time.monotonic()-start>ad['cold_timeout_seconds'] or science>ad['science_timeout_seconds']:raise TimeoutError('Finite fullpanel marker allocation exhausted; preserve all unit debits')
  if g.proc(os.getpid())['rss_bytes']>ad['max_rss_bytes']:raise MemoryError('Controller Linux RSS limit')
  if g.available()<ad['linux_available_stop_bytes']:raise MemoryError('Fullpanel preferential headroom stop')
  import shutil
  if shutil.disk_usage(R).free<40*1024**3:raise OSError('Project disk reserve below40GiB')
 def publish(unit,peak=None,mem=None,terminal=None):
  nonlocal last
  if terminal is None:gates()
  if terminal is None and time.monotonic()-last<30:return
  s={'id':'06','name':'Marker discovery and orthology','status':terminal or'RUNNING','operation':'PREPARING_FULL919_PROFILE_SEARCH'if current is None else'ACTUAL_FULL919_SERIAL_PROFILE_SEARCH','detail':str(current)+' / '+phase+' / '+unit,'done':done,'total':919,'unit':'uniform provisional proteomes searched against281 candidate profiles','started_utc':started,'updated_utc':g.utc(),'pid':a.native_pid,'creation_time_utc':a.native_creation_utc,'linux_owner_identity':owner,'cpu_affinity':[2],'summed_owned_linux_rss_bytes':peak,'native_rss_reserved_bytes':ad['native_rss_reserve_bytes'],'linux_available_bytes':mem,'science_seconds_committed':science,'scope':SCOPE,'quality_PASS_claimed':False,'marker_set_acceptance':'NOT_GRANTED','final_panel_acceptance':False,'log_path':str(out/'progress.json'),'admission':g.ref(admission_path)}
  g.save(out/'progress.json',s);g.save(R/'state/stages/06.json',s);last=time.monotonic()
 publish('source validation',terminal='RUNNING')
 try:
  gates();profiles,qlen=h.verified_profiles(bound(m['profile_manifest']))
  if len(profiles)!=281 or list(qlen)!=m['profile_ids']:raise RuntimeError('Exact281 newly discovered profile identities required')
  query=out/'all281_profiles.hmm';h.combine_profiles(query,profiles)
  g.TOOLCHAIN_SHA=hashlib.sha256(json.dumps({'tool':m['hmmsearch'],'script':m['script'],'guard':m['guard'],'parser':m['parser'],'policy':m['policy']},sort_keys=True).encode()).hexdigest()
  query_ref=g.ref(query);tool=bound(m['hmmsearch']);commits=[]
  for row in m['rows']:
   gates();current=row['accession'];dest=out/'rows'/current;dest.mkdir(parents=True,exist_ok=True);commit=dest/'commit.json'
   if commit.exists():
    c=g.read(commit)
    if c['manifest']!=g.ref(manifest_path) or c['accession']!=current or c['source_annotation_commit']!=row['commit']:raise RuntimeError('Existing marker row differs')
    for v in c['outputs']:bound(v)
    e=g.read(bound(c['search']['execution']))
    if e['actual_exit_code']!=0 or e['owned_group_empty']is not True:raise RuntimeError('Existing search closure differs')
    bound(c['search']['output']);science+=c['new_science_seconds'];commits.append(g.ref(commit));done+=1;continue
   unitdir=out/'units'/current
   if unitdir.exists()and any(unitdir.glob('hmmsearch_attempt_*')):raise RuntimeError('Prior incomplete attempt requires separately reviewed saved-phase recovery; no automatic retry')
   annotation=g.read(bound(row['commit']))
   if annotation['artifacts']['proteins.faa']!=row['proteins'] or annotation['source_metadata']!=row['source_metadata'] or annotation['protein_count']!=row['protein_count'] or annotation['biological_QC_PASS']is not False or annotation['final_panel_acceptance']is not False:raise RuntimeError('Provisional annotation join differs')
   fasta=bound(row['proteins']);seqs=g.fasta(fasta)
   if len(seqs)!=row['protein_count'] or any(n!=current+'|gene'+str(i).zfill(6)or'*'in s for i,(n,s)in enumerate(seqs.items(),1)):raise RuntimeError('Exact canonical uniform protein identity/count required')
   lengths={n:len(s)for n,s in seqs.items()};del seqs
   if row.get('prior_search_reuse'):
    phase='reusing exact previously searched sequences and closed raw domains';publish('saved search reuse',terminal='RUNNING')
    saved=g.read(bound(row['prior_search_reuse']))
    if saved['proteins']!=row['proteins']or saved['source_annotation_commit']!=row['commit']or saved['reference_target_count']!=m['policy']['reference_target_count']or saved['combined_query_sha256']!=query_ref['sha256']:raise RuntimeError('Exact saved search/query/protein/calibration join differs')
    result=saved['search'];e=g.read(bound(result['execution']));bound(result['output'])
    if e['actual_exit_code']!=0 or e['owned_group_empty']is not True:raise RuntimeError('Saved search lacks actual0/closed unit')
    groups={(v['profile'],v['target_id']):v['values']for v in saved['groups']};raw=saved['raw_domains_for_genome'];new_seconds=0.
    if any(t not in lengths or q not in qlen for q,t in groups):raise RuntimeError('Saved target/profile not in exact uniform proteome')
    search_action='REUSED_EXACT_PROTEIN_SEQUENCES_CLOSED_RAW_SEARCH'
   else:
    argv=[str(tool),'--cpu','1','--seed','42','--noali','-Z',str(m['policy']['reference_target_count']),'-E','1e-5','--domE','1e-5','--domtblout','{OUTPUT}',str(query),str(fasta)]
    inputs=[g.ref(manifest_path),row['commit'],row['proteins'],query_ref,m['script'],m['guard'],m['parser'],g.ref(admission_path)]
    phase='actual281-profile HMMsearch';publish('search',terminal='RUNNING')
    result=g.run_unit(unitdir,'hmmsearch',argv,inputs,'domains.tsv',ad,publish)
    e=g.read(bound(result['execution']));new_seconds=e['elapsed_seconds'];science+=new_seconds;gates()
    phase='validating domains, copies and cross-profile ambiguity';groups,raw=h.parse_domains(bound(result['output']),lengths,qlen,1e-5)
    search_action='NEW_UNIFORM_PROTEOME_PROFILE_SEARCH'
   hits,cells,amb=summarize(qlen,groups,current)
   h.write_tsv(dest/'qualifying_hits.tsv',['profile','accession','target_id','best_domain_ievalue','full_sequence_evalue','best_domain_bits','qualifying_domains','hmm_coverage','target_coverage'],hits)
   h.write_tsv(dest/'profile_copy_counts.tsv',['profile','accession','search_state','qualifying_copy_count','target_ids','cross_profile_ambiguous_targets','unambiguous_single_copy','biological_absence_claimed'],cells)
   g.save(dest/'cross_profile_ambiguity.json',{'ambiguous_targets':amb,'policy':'Preserve every qualifying alternative; do not choose by score alone','final_orthology':'NOT_ACCEPTED'})
   c={'schema':'TREE2_PROVISIONAL_FULL919_MARKER_SCREEN_ROW_V001','status':'ACTUAL0_CLOSED_DOMAINS_COPY_COUNTS_COMMITTED_PROVISIONAL','accession':current,'manifest':g.ref(manifest_path),'source_annotation_commit':row['commit'],'source_metadata':row['source_metadata'],'source_taxonomy_QC_holds_preserved':True,'search':result,'search_action':search_action,'prior_search_reuse':row.get('prior_search_reuse'),'new_science_seconds':new_seconds,'reference_target_count':m['policy']['reference_target_count'],'raw_domain_rows':raw,'qualifying_profile_protein_hits':len(hits),'searched_profiles':281,'searched_proteins':len(lengths),'cross_profile_ambiguous_targets':len(amb),'outputs':[g.ref(dest/n)for n in ('qualifying_hits.tsv','profile_copy_counts.tsv','cross_profile_ambiguity.json')],'quality_PASS_claimed':False,'marker_set_acceptance':'NOT_GRANTED','final_panel_acceptance':False,'defence_status':'UNKNOWN_UNSEARCHED','completed_utc':g.utc()}
   g.save(commit,c);commits.append(g.ref(commit));done+=1;g.save(out/'checkpoint.json',{'done':done,'total':919,'science_seconds_committed':science,'latest_commit':commits[-1],'updated_utc':g.utc()});publish('per-genome commit')
  phase='whole-panel candidate occupancy and paralogy summaries';counts={q:collections.Counter()for q in qlen}
  import csv
  for reference in commits:
   gates();c=g.read(bound(reference))
   with bound(c['outputs'][1]).open()as f:
    cells=list(csv.DictReader(f,delimiter='\t'))
   if len(cells)!=281 or {x['profile']for x in cells}!=set(qlen):raise RuntimeError('Incomplete final copy matrix')
   for x in cells:
    z=counts[x['profile']];n=int(x['qualifying_copy_count']);z['zero'if n==0 else'single'if n==1 else'multiple']+=1;z['unambiguous_single']+=int(x['unambiguous_single_copy'])
  summary=[{'profile':q,'profile_length':qlen[q],'genomes_searched':919,'genomes_zero_qualifying_hits':c['zero'],'genomes_single_hit':c['single'],'genomes_multiple_hits':c['multiple'],'genomes_unambiguous_single_hit':c['unambiguous_single'],'single_copy_occupancy':c['single']/919,'unambiguous_single_copy_occupancy':c['unambiguous_single']/919,'marker_set_acceptance':'NOT_GRANTED'}for q,c in counts.items()]
  h.write_tsv(out/'profile_summary.tsv',list(summary[0]),summary)
  g.save(out/'result.json',{'status':'PROVISIONAL_FULL919_MARKER_SCREEN_COMPUTED_PENDING_EXTERNAL_VALIDATION_AND_CLOSURE','manifest':g.ref(manifest_path),'admission':g.ref(admission_path),'row_commits':commits,'genomes_searched':919,'profiles_searched':281,'proteins_searched':m['proteins'],'reused_exact_previously_searched_proteomes':m['prior_search_reuse_count'],'new_proteome_searches':919-m['prior_search_reuse_count'],'profile_genome_pairs':919*281,'summary':g.ref(out/'profile_summary.tsv'),'science_seconds_committed':science,'elapsed_seconds':time.monotonic()-start,'scope':SCOPE,'full_panel_orthology_gene_tree_validation':'STILL_REQUIRED','additional_candidate_discovery':'REMAINS_SEPARATE_FROM_ASSESSING_PILOT_DERIVED_CANDIDATES','quality_PASS_claimed':False,'marker_set_acceptance':'NOT_GRANTED','final_panel_acceptance':False,'defence_status':'UNKNOWN_UNSEARCHED'})
  publish('all919 profile searches and matrix committed',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as ex:
  g.save(out/'failure.json',{'status':'STOPPED_PRESERVE_SUCCESSFUL_SEARCHES_AND_DEBITS','error':repr(ex),'current':current,'completed':done,'science_seconds_committed':science,'unfinished':'UNKNOWN_UNSEARCHED','no_automatic_retry':True,'updated_utc':g.utc()});publish(str(ex),terminal='STOPPED');raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--admission',required=True);p.add_argument('--output',required=True);p.add_argument('--native-pid',type=int,required=True);p.add_argument('--native-creation-utc',required=True);p.add_argument('--stop-file',required=True);main(p.parse_args())
