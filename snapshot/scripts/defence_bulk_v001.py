"""Full stock protein-supported PADLOC/DefenseFinder production cohort; durable phases, no annotations/controls replayed."""
from pathlib import Path
import os,sys,json,time,signal,fcntl,hashlib,csv,shutil,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import defence_supplied_gene_inputs_v001 as adapter
from defence_bulk_units_v001 import Runtime
from defence_prediction_scope_v001 import padloc_calls,defensefinder_calls

def main():
 def stopped(number,frame):raise InterruptedError('Defence pilot signal '+str(number))
 signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
 plan_path=Path(sys.argv[1]);expected=sys.argv[2];assert g.sha(plan_path)==expected;P=g.read(plan_path);E=R/P['work'];OUT=R/P['output'];RAM=R/P['ram_scratch'];OUT.mkdir(exist_ok=True)
 for ref in P['sources']+P['bound_inputs']:g.bound(ref)
 ready=g.read(g.bound(P['ready_packet']));assert ready['status']=='READY_FOR_AUTOMATIC_BOUNDED_PROTEIN_SUPPORTED_PILOT';scope=g.read(g.bound(P['scope_GO']));assert scope['status']=='ROOT_GO_NOVEL_PROTEIN_SUPPORTED_DEFENCE_COHORT'and scope['scope_sha256']==P['scope_sha256']
 assert P['schema']=='TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V001'
 reservation=g.read(g.bound(P['reservation']));accepted=g.read(g.bound(P['accepted_pilot']))
 assert reservation['selected_accessions']==P['selected_accessions'] and reservation['cohort_id']==P['cohort_id']
 assert len(P['selected_accessions'])==len(set(P['selected_accessions']))==20
 reused=g.read(g.bound(accepted['source_result']))['selected_accessions']
 assert set(P['selected_accessions']).isdisjoint(reused)
 with(OUT/'once_claim.json').open('x')as f:json.dump({'plan_sha256':expected,'selected_accessions':P['selected_accessions'],'reservation':P['reservation'],'no_automatic_retry':True,'started_utc':g.utc()},f)
 runtime=Runtime(P);runtime.total=2*len(P['selected_accessions']);common=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB);lease=(OUT/'queue.lock').open('a+b');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);records={};completed=[];phase_commits=[];copied={}
 def cache(files,source_prefix,dest):
  runtime.phase='BYTE_VERIFIED_PRIVATE_RAM_CACHE_PREPARATION';dest.mkdir(parents=True,exist_ok=False);local=[]
  for ref in files:
   runtime.guard();source=R/ref['path'];rel=Path(ref['path']).relative_to(source_prefix);target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
   with source.open('rb')as inp,target.open('xb')as out:
    for block in iter(lambda:inp.read(8*1024**2),b''):out.write(block);h.update(block);runtime.guard()
   if h.hexdigest()!=ref['sha256']or target.stat().st_size!=ref['bytes']:raise RuntimeError('Cache copy byte mismatch '+str(source))
   target.chmod(0o444);local.append({'cached_path':str(target),'original_source':{k:ref[k]for k in('path','sha256','bytes')}});runtime.publish('Preparing exact-byte privateRAM model/runtime cache')
  manifest={'cached_files':local,'source_bytes_unchanged':True,'cache_is_not_checkpoint':True};g.save(E/('cache_'+dest.name+'.json'),manifest);copied[str(dest)]=manifest;return dest
 def verify_cache(dest):
  for q in copied[str(dest)]['cached_files']:
   runtime.guard();assert g.sha(q['cached_path'])==q['original_source']['sha256']
 def searches(folder,query_sha,engine):
  proofs=[g.read(p)for p in(folder/'HMMER_receipts').glob('*.json')];scientific=[]
  for q in proofs:
   if q['status']!='ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED'or q['actual_exit_code']!=0 or not q['binary_handle_waited_and_reaped']:raise RuntimeError('Incomplete/failed typed HMMER child')
   if q['probe_only']:continue
   if not q['raw_outputs']or q['query_faa_sha256']!=query_sha:raise RuntimeError('Wrong queried genome or missing per-search raw phase')
   allowed=P['PADLOC_HMM_sha256']if engine=='PADLOC'else None
   if allowed is not None and q['model_file_sha256']!=allowed:raise RuntimeError('PADLOC full compiled model bytes differ')
   if engine=='DefenseFinder'and q['model_file_sha256']not in P['DF_profile_SHA256']:raise RuntimeError('DF search used unpinned profile')
   for raw in q['raw_outputs']:
    p=g.bound(raw)
    with p.open('rb')as f:f.seek(max(0,p.stat().st_size-4096));assert b'[ok]'in f.read()
   scientific.append(q)
  if not scientific or(engine=='PADLOC'and len(scientific)!=1):raise RuntimeError('Missing full-catalogue scientific search phase')
  return len(scientific)
 try:
  runtime.publish('Preparing reserved novel production genomes from accepted paired annotations; no gene calling',True)
  queue=g.read(g.bound(P['queue']));byacc={q['accession']:q for q in queue['rows']};assert len(byacc)==919;accepted=adapter.closed_context(R,queue['closed_annotation_acceptance']);pad_rules={q['model_id']:q for q in g.read(g.bound(P['PADLOC_rules']))['models']};df_rules=g.read(g.bound(P['DF_rules']))['rows']
  for accession in P['selected_accessions']:
   runtime.guard();runtime.current=accession;folder=OUT/'rows'/accession;folder.mkdir(parents=True,exist_ok=False);row=byacc[accession];prepared=adapter.prepare(R,row['supplied_gene_request'],folder/'supplied_inputs',accepted_rows=accepted);inputs=RAM/'inputs'/accession;inputs.mkdir(parents=True)
   for name,ref in prepared['files'].items():
    source=g.bound(ref);target=inputs/name;shutil.copyfile(source,target);assert g.sha(target)==ref['sha256']
   mapping=g.read(g.bound(prepared['files']['protein_identity_map.json']));records[accession]={'source':row,'prepared':prepared,'inputs':inputs,'folder':folder,'mapping':mapping,'engines':{}}
  bin_dir=E/'bin';bin_dir.mkdir();(bin_dir/'hmmsearch').symlink_to(R/'scripts/defence_hmmer_receipt_v001.py')
  for name in('home','cache','emptylibs'):(E/name).mkdir()
  env={**os.environ,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','XDG_CACHE_HOME':str(E/'cache'),'XDG_DATA_HOME':str(E/'home'),'R_LIBS_USER':str(E/'emptylibs'),'R_PROFILE_USER':'/dev/null','R_ENVIRON_USER':'/dev/null','R_HISTFILE':str(E/'R_history'),'R_TMPDIR':'/tmp','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PATH':str(bin_dir)+':'+str(R/'tools/bioenv/bin')+':/usr/local/bin:/usr/bin:/bin','LD_LIBRARY_PATH':'/usr/local/lib:/usr/local/lib/R/lib'}
  pad_files=g.read(g.bound(P['PADLOC_compiled_manifest']));files=[{k:q[k]for k in('path','sha256','bytes')}for q in pad_files['outputs']]+pad_files['other_files'];pad_cache=cache(files,Path(P['PADLOC_model_root']),RAM/'PADLOC_models');runtime.phase='PADLOC_REAL_GENOME_FULL5027_PROTEIN_MODEL_SEARCH_AND_STOCK_RULES'
  for accession,record in records.items():
   runtime.current=accession;runtime.guard();folder=record['folder']/'PADLOC';folder.mkdir();output=folder/'stock_output';output.mkdir();query=record['inputs']/'padloc_canonical.faa';gff=record['inputs']/'padloc_canonical.gff';runtime.phase='PADLOC_REAL_GENOME_FULL5027_PROTEIN_MODEL_SEARCH_AND_STOCK_RULES';local={**env,'TREE2_DEFENCE_SEARCH_RECEIPTS':str(folder/'HMMER_receipts')};args=['/usr/local/bin/padloc','--data',str(pad_cache),'--faa',str(query),'--gff',str(gff),'--outdir',str(output),'--cpu','1'];proof=runtime.run(folder/'unit',args,'PADLOC_STOCK_FULL_PROTEIN_SCOPE',[record['prepared']['files']['padloc_canonical.faa'],record['prepared']['files']['padloc_canonical.gff'],P['PADLOC_compiled_manifest']],environment=local)
   raw=output/'padloc_canonical.domtblout';report=output/'padloc_canonical_padloc.csv'
   if not raw.exists()or not report.exists():raise RuntimeError('PADLOC0 missing complete raw/report; preserve unit and no search replay')
   with raw.open('rb')as f:f.seek(max(0,raw.stat().st_size-4096));assert b'[ok]'in f.read()
   count=searches(folder,record['prepared']['files']['padloc_canonical.faa']['sha256'],'PADLOC');rows=list(csv.DictReader(report.open()));calls,states=padloc_calls(rows,{q['canonical_id']:q for q in record['mapping']},pad_rules);g.save(folder/'scoped_predictions.json',{'calls':calls,'model_states':states,'RNA51_unavailable_never_zero':True,'all_stock_calls_preserved':True,'all_original_masks':record['source']['source_masks'],'no_final_panel_or_ring_acceptance':True});artifacts=[g.ref(p)for p in folder.rglob('*')if p.is_file()];commit={'status':'PADLOC_STOCK0_TYPED_RAW0_SCOPED_REAL_GENOME_PHASE_COMMITTED_PENDING_OWNER_CLOSURE','accession':accession,'engine':'PADLOC2_DB2','execution':proof,'typed_scientific_HMMER_searches':count,'calls':g.ref(folder/'scoped_predictions.json'),'artifacts':artifacts,'source_queue_row':record['source'],'cache_provenance':g.ref(E/'cache_PADLOC_models.json'),'unavailable_RNA_model_count':sum(q['availability_and_prediction_state']=='UNKNOWN_RNA_FEATURES_UNAVAILABLE'for q in states),'model_relative_calls':len(calls),'eligible_primary_protein_predictions':sum(q['eligible_primary_predicted_protein_system']for q in calls),'source_taxonomy_type_quality_holds_preserved':True};g.save(folder/'COMMITTED.json',commit);record['engines']['PADLOC']=g.ref(folder/'COMMITTED.json');phase_commits.append(record['engines']['PADLOC']);runtime.done+=1;runtime.publish('Real PADLOC protein-supported genome phase durably committed; RNA-dependent states remainUNKNOWN',True)
  verify_cache(pad_cache);shutil.rmtree(pad_cache);runtime.guard()
  df_files=g.read(g.bound(P['DF_model_manifest']))['files'];df_cache=cache(df_files,Path(P['DF_model_root']),RAM/'DF_models');overlay_files=g.read(g.bound(P['DF_runtime_manifest']))['files'];overlay=cache(overlay_files,Path(P['DF_runtime_root']),RAM/'DF_runtime');py=R/P['python'];bootstrap=g.bound(P['DF_bootstrap']);df_entry=overlay/'python-scripts/defense-finder'
  for accession,record in records.items():
   runtime.current=accession;runtime.guard();runtime.phase='DEFENSEFINDER_REAL_GENOME_DEFAULT_DF_RM_CAS_PROTEIN_SCOPE';folder=record['folder']/'DefenseFinder';folder.mkdir();output=folder/'stock_output';query=record['inputs']/'defensefinder_gembase.faa';(record['inputs']/'DF_indices').mkdir();local={**env,'LD_LIBRARY_PATH':'','PYTHONPATH':str(overlay/'site-packages')+':'+str(R/P['numpy_overlay']),'TREE2_DEFENCE_SEARCH_RECEIPTS':str(folder/'HMMER_receipts')};args=[str(py),'-B',str(bootstrap),'script',str(df_entry),'run','--out-dir',str(output),'--workers','1','--db-type','gembase','--models-dir',str(df_cache),'--skip-model-version-check','--preserve-raw','--index-dir',str(record['inputs']/'DF_indices'),str(query)];proof=runtime.run(folder/'unit',args,'DEFENSEFINDER_STOCK_FULL_DEFAULT_PROTEIN_SCOPE',[record['prepared']['files']['defensefinder_gembase.faa'],record['prepared']['files']['macsyfinder.conf'],P['DF_model_manifest']],environment=local,cwd=record['inputs'])
   reports=list(output.glob('*_defense_finder_systems.tsv'));assert len(reports)==1;count=searches(folder,record['prepared']['files']['defensefinder_gembase.faa']['sha256'],'DefenseFinder');rows=list(csv.DictReader(reports[0].open(),delimiter='\t'));calls,states=defensefinder_calls(rows,{q['DF_ID']:q for q in record['mapping']},df_rules);g.save(folder/'scoped_predictions.json',{'calls':calls,'model_states':states,'ADF156_excluded_and_genericCAS_clusters_separate':True,'source_masks':record['source']['source_masks'],'all_stock_calls_preserved':True,'no_final_panel_or_ring_acceptance':True});artifacts=[g.ref(p)for p in folder.rglob('*')if p.is_file()];commit={'status':'DF_STOCK0_TYPED_RAW0_SCOPED_REAL_GENOME_PHASE_COMMITTED_PENDING_OWNER_CLOSURE','accession':accession,'engine':'DefenseFinder3_models3.1_Cas3.1','execution':proof,'typed_scientific_HMMER_searches':count,'calls':g.ref(folder/'scoped_predictions.json'),'artifacts':artifacts,'source_queue_row':record['source'],'model_cache_provenance':g.ref(E/'cache_DF_models.json'),'runtime_cache_provenance':g.ref(E/'cache_DF_runtime.json'),'model_relative_calls':len(calls),'eligible_primary_protein_predictions':sum(q['eligible_primary_predicted_protein_system']for q in calls),'source_taxonomy_type_quality_holds_preserved':True};g.save(folder/'COMMITTED.json',commit);record['engines']['DefenseFinder']=g.ref(folder/'COMMITTED.json');phase_commits.append(record['engines']['DefenseFinder']);combined={'status':'REAL_GENOME_BOTH_STOCK_PROTEIN_DEFENCE_ENGINES_COMMITTED_PENDING_COHORT_EXTERNAL_ACCEPTANCE','accession':accession,'engines':record['engines'],'input_provenance':g.ref(record['folder']/'supplied_inputs/COMMITTED.json'),'source_queue_row':record['source'],'RNA_feature_models_remain_UNKNOWN':True,'no_final_panel_or_ring_acceptance':True};g.save(record['folder']/'COMMITTED.json',combined);completed.append(g.ref(record['folder']/'COMMITTED.json'));runtime.done+=1;runtime.publish('Real genome both protein-supported engines durably committed',True)
  verify_cache(df_cache);verify_cache(overlay);g.save(OUT/'COHORT_COMPLETE.json',{'status':'NOVEL_COHORT_BOTH_PROTEIN_SUPPORTED_ENGINES_COMPUTED_PENDING_EXTERNAL_CLOSURE_AND_VALIDATION','selected_accessions':P['selected_accessions'],'genome_commits':completed,'engine_phase_commits':phase_commits,'source_plan':g.ref(plan_path),'actual_scientific_seconds':runtime.science,'actual_cold_seconds':time.monotonic()-runtime.started,'peak_Linux_RSS_plus_private_RAM_bytes':runtime.peak,'throughput_is_real_genome_production_not_synthetic_control':True,'automatic_next_disjoint_cohort_after_closed_ledger_commit':True,'all919_scope_still_required':True,'no_complete_project_or_final_ring_acceptance':True});runtime.publish('Novel production cohort computed; exact closure and independent phase validation precede queue commit and next disjoint cohort',True,status='COMPUTED_PENDING_EXTERNAL_COHORT_ACCEPTANCE')
 except BaseException as error:
  g.save(E/'failure.json',{'error':repr(error),'current':runtime.current,'phase':runtime.phase,'completed_genomes':len(completed),'completed_engine_phases':phase_commits,'known_scientific_debit_seconds':runtime.science,'known_cold_debit_seconds':time.monotonic()-runtime.started,'successful_typed_searches_and_stock_phases_preserved_no_replay':True,'RAM_caches_not_checkpoints_source_models_and_supplied_inputs_durable':True,'failed_unrun_or_unavailable_models_not_negative':True,'at_utc':g.utc()});raise
 finally:fcntl.flock(lease,fcntl.LOCK_UN);lease.close();fcntl.flock(common,fcntl.LOCK_UN);common.close()

if __name__=='__main__':main()
