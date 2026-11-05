"""Full stock protein-supported production with immutable C008 phase inheritance."""
from pathlib import Path
import os,sys,json,time,signal,hashlib,csv,shutil,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import marker_pilot_compute_v001 as g
import defence_supplied_gene_inputs_v001 as adapter
from defence_bulk_units_v002 import Runtime
from defence_cpu_configuration_v002 import configuration
from defence_padloc_output_v003 import classify, bound
from defence_prediction_scope_v001 import padloc_calls,defensefinder_calls

PLAN_SCHEMA = 'TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V003'
LEGACY_CPU_SCHEMA = 'TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V002'
INPUT_FILES = {
 'defensefinder_gembase.faa', 'padloc_canonical.faa', 'padloc_canonical.gff',
 'macsyfinder.conf', 'protein_identity_map.json',
}
UNCHANGED_RECOVERY_FIELDS = (
 'queue','reservation','scope_sha256','ready_packet','accepted_pilot',
 'previous_closed_campaign_genomes','selected_accessions','cohort_id',
 'stock_threads','cpu_affinity','cpu_upgrade_authority','native_reserved_bytes',
 'linux_RSS_plus_RAM_bytes','minimum_linux_available_bytes','unit_seconds',
 'science_seconds','cold_seconds','original_context_absolute_deadline_unix',
 'PADLOC_compiled_manifest','PADLOC_HMM_sha256','PADLOC_model_root','PADLOC_runtime_root',
 'PADLOC_rules','DF_model_root','DF_model_manifest','DF_rules','DF_profile_SHA256',
 'DF_runtime_root','DF_runtime_manifest','DF_bootstrap','python','numpy_overlay',
)


def checked(condition, reason):
 if not condition:
  raise RuntimeError('Defence production admission: ' + reason)


def read_bound(ref):
 return g.read(bound(ref))


def resume_context(plan):
 """Verify a single source-bound partition of C008 into saved and untouched phases."""
 runtime_plan = dict(plan, schema=LEGACY_CPU_SCHEMA)
 resume = plan.get('resume')
 if resume is None:
  return runtime_plan, None, None
 checked(plan['cohort_id']=='C008' and len(plan['selected_accessions'])==20,
         'remaining-only reservation is specific to the failed C008')
 old = read_bound(resume['source_plan'])
 checked(old['schema']==LEGACY_CPU_SCHEMA
         and all(plan[key]==old[key] for key in UNCHANGED_RECOVERY_FIELDS),
         'C008 immutable source settings differ')
 for key in ('work','output','ram_scratch','stop_path'):
  checked(g.inside(plan[key])!=g.inside(old[key]), 'C008 successor requires fresh '+key)
 checked(plan['PADLOC_stock_R'] in old['sources']+old['bound_inputs'],
         'C008 stock rule runner changed')
 failure = read_bound(resume['failed_disposition'])
 checked(failure['status']=='BLOCKED_SOURCE_OUTPUT_CONTRACT_FAILURE_NOT_SCIENTIFIC_ACCEPTANCE'
         and failure['source_plan']==resume['source_plan']
         and failure['snapshot']==resume['snapshot']
         and failure['whole_owned_closure']==resume['whole_closure']
         and failure['reservation']==plan['reservation']
         and failure['selected_accessions']==plan['selected_accessions']
         and failure['paired_genomes_accepted_from_this_cohort']==0,
         'C008 failure no longer matches the exact source context')
 closure = read_bound(resume['whole_closure'])
 snapshot = read_bound(resume['snapshot'])
 checked(closure['all_native_WSL_stock_HMMER_captured_descendant_group_private_mount_IPC_R_binding_RAM_FD_and_fourlease_closure'] is True
         and snapshot['whole_closure']==resume['whole_closure']
         and snapshot['archive_every_member_independently_hashed_and_paths_links_matched'] is True,
         'C008 original closure or snapshot verification missing')
 manifest = read_bound(resume['inherited_phase_manifest'])
 reservation = read_bound(resume['recovery_reservation'])
 checked(reservation['schema']=='TREE2_DEFENCE_IMMUTABLE_C008_RECOVERY_RESERVATION_V001'
         and reservation['status']=='RESERVED_SAME_C008_UNSTARTED_PHASES_ONLY'
         and reservation['cohort_id']==plan['cohort_id'] and reservation['source_queue']==plan['queue']
         and reservation['selected_accessions']==plan['selected_accessions']
         and reservation['original_reservation']==plan['reservation']
         and all(reservation[key]==resume[key] for key in
                 ('failed_disposition','whole_closure','snapshot','inherited_phase_manifest'))
         and reservation['remaining_unstarted_phases']==31
         and reservation['stock_threads']==plan['stock_threads']
         and reservation['replay_completed_phases'] is False,
         'C008 recovery reservation differs')
 checked(manifest['schema']=='TREE2_DEFENCE_INHERITED_PADLOC_PHASES_V003'
         and manifest['status']=='AUDITED_SAVED_PADLOC_PHASES_NO_SEARCH_REPLAY'
         and manifest['source_plan']==resume['source_plan']
         and manifest['selected_accessions']==plan['selected_accessions']
         and [row['accession'] for row in manifest['rows']]==plan['selected_accessions']
         and [row['accession'] for row in manifest['rows'] if row['phase'] is not None]
             ==plan['selected_accessions'][:9], 'C008 saved phase partition differs')
 prior_science = failure['scientific_seconds_consumed']
 prior_cold = failure['cold_seconds_consumed']
 for key,value,maximum in (('prior_scientific_seconds',prior_science,plan['science_seconds']),
                           ('prior_cold_seconds',prior_cold,plan['cold_seconds'])):
  checked(type(value) in (int,float) and math.isfinite(value) and 0<value<maximum
          and manifest[key]==reservation[key]==value, 'C008 prior debit differs: '+key)
 deadline=plan['recovery_operational_deadline_unix']
 checked(type(deadline) in (int,float) and math.isfinite(deadline)
         and time.time()<deadline and deadline>plan['original_context_absolute_deadline_unix'],
         'fresh bounded recovery operational window missing or expired')
 runtime_plan.update(science_seconds=plan['science_seconds']-prior_science,
                     cold_seconds=plan['cold_seconds']-prior_cold,
                     original_context_absolute_deadline_unix=deadline)
 saved_dispositions=read_bound(failure['partial_engine_dispositions'])
 checked([row['accession'] for row in saved_dispositions['rows']]==plan['selected_accessions']
         and all(row['DefenseFinder']=='NOT_RUN_UNKNOWN' for row in saved_dispositions['rows'])
         and all(row['PADLOC']=='NOT_RUN_UNKNOWN' for row in saved_dispositions['rows'][9:]),
         'saved disposition does not prove exactly 31 untouched phases')
 return runtime_plan, manifest, saved_dispositions


def inherited_phase(plan, manifest_row, disposition, record, source_output):
 phase_ref=manifest_row['phase']
 if phase_ref is None:
  return None, 0
 phase=read_bound(phase_ref)
 execution=phase['execution']
 folder=source_output/'rows'/record['source']['accession']/'PADLOC'
 checked(execution==disposition['stock_unit_actual_exit']
         and phase['accession']==record['source']['accession']
         and phase['source_queue_row']==record['source'] and phase['engine']=='PADLOC2_DB2'
         and phase['typed_scientific_HMMER_searches']==1,
         'inherited PADLOC execution/source differs')
 for artifact in phase['artifacts']:
  bound(artifact)
 bound(phase['cache_provenance'])
 stock,evidence=classify(folder,execution,record['prepared'],plan['PADLOC_compiled_manifest'],
                         plan['PADLOC_HMM_sha256'],plan['PADLOC_stock_R'],plan['stock_threads'])
 checked(evidence['typed_HMMER_receipt']==disposition['typed_HMMER_actual_exit'],
         'inherited PADLOC HMMER receipt differs')
 scoped=read_bound(phase['calls'])
 checked(scoped['all_original_masks']==record['source']['source_masks']
         and scoped['RNA51_unavailable_never_zero'] is True
         and scoped['no_final_panel_or_ring_acceptance'] is True,
         'inherited PADLOC masks differ')
 if 'phase_commit' in disposition:
  checked(phase_ref==disposition['phase_commit'] and bool(stock),
          'one of the original eight PADLOC commits differs')
 else:
  checked(phase['raw_phase_directory']==folder.relative_to(R).as_posix()
          and phase['padloc_output_classification']==evidence and not stock
          and scoped['calls']==[] and phase['model_relative_calls']==0
          and phase['eligible_primary_protein_predictions']==0,
          'ninth PADLOC phase lacks the independently derived no-report proof')
 return phase_ref,read_bound(execution)['elapsed_seconds']


def main():
 import fcntl
 def stopped(number,frame):raise InterruptedError('Defence production signal '+str(number))
 signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
 plan_path=Path(sys.argv[1]);expected=sys.argv[2];assert g.sha(plan_path)==expected;P=g.read(plan_path);E=R/P['work'];OUT=R/P['output'];RAM=R/P['ram_scratch'];OUT.mkdir(exist_ok=True)
 checked(P['schema']==PLAN_SCHEMA, 'wrong worker source-bound schema')
 for ref in P['sources']+P['bound_inputs']:g.bound(ref)
 checked(P['PADLOC_stock_R'] in P['sources']+P['bound_inputs'], 'stock PADLOC R source must be plan-bound')
 runtime_plan,inherited,saved_dispositions=resume_context(P)
 ready=g.read(g.bound(P['ready_packet']));assert ready['status']=='READY_FOR_AUTOMATIC_BOUNDED_PROTEIN_SUPPORTED_PILOT';scope=g.read(g.bound(P['scope_GO']))
 permitted_scope={'ROOT_GO_NOVEL_PROTEIN_SUPPORTED_DEFENCE_COHORT'}
 if inherited is not None:
  permitted_scope.add('ROOT_GO_C008_REMAINING_PROTEIN_SUPPORTED_DEFENCE_PHASES')
 assert scope['status'] in permitted_scope and scope['scope_sha256']==P['scope_sha256']
 threads,affinity=configuration(runtime_plan,os.sched_getaffinity(0));g.bound(P['cpu_upgrade_authority'])
 reservation=g.read(g.bound(P['reservation']));accepted=g.read(g.bound(P['accepted_pilot']))
 assert reservation['selected_accessions']==P['selected_accessions'] and reservation['cohort_id']==P['cohort_id']
 assert 1<=len(P['selected_accessions'])==len(set(P['selected_accessions']))<=20
 reused=g.read(g.bound(accepted['source_result']))['selected_accessions']
 assert set(P['selected_accessions']).isdisjoint(reused)
 with(OUT/'once_claim.json').open('x')as f:json.dump({'plan_sha256':expected,'selected_accessions':P['selected_accessions'],'reservation':P['reservation'],'resume':P.get('resume'),'no_automatic_retry':True,'started_utc':g.utc()},f)
 runtime=Runtime(runtime_plan);runtime.total=2*len(P['selected_accessions']);common=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB);lease=(OUT/'queue.lock').open('a+b');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);records={};completed=[];phase_commits=[];copied={}
 prior_science=0 if inherited is None else inherited['prior_scientific_seconds']
 prior_cold=0 if inherited is None else inherited['prior_cold_seconds']
 saved_count=0;new_padloc=0;new_df=0
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
  runtime.publish('Checking nine saved PADLOC phases and immutable inputs before remaining C008 work' if inherited
                  else 'Preparing reserved novel production genomes from accepted paired annotations; no gene calling',
                  True,cohort_novel_genomes=0 if inherited else len(P['selected_accessions']))
  queue=g.read(g.bound(P['queue']));byacc={q['accession']:q for q in queue['rows']};assert len(byacc)==919;accepted=adapter.closed_context(R,queue['closed_annotation_acceptance']);pad_rules={q['model_id']:q for q in g.read(g.bound(P['PADLOC_rules']))['models']};df_rules=g.read(g.bound(P['DF_rules']))['rows']
  saved_seconds=0.
  source_output=g.inside(read_bound(P['resume']['source_plan'])['output']) if inherited else None
  for index,accession in enumerate(P['selected_accessions']):
   runtime.guard();runtime.current=accession;folder=OUT/'rows'/accession;folder.mkdir(parents=True,exist_ok=False);row=byacc[accession]
   if inherited:
    manifest_row=inherited['rows'][index]
    inp_ref=manifest_row['input_provenance']
    checked(bound(inp_ref)==source_output/'rows'/accession/'supplied_inputs/COMMITTED.json',
            'inherited supplied input receipt path differs')
    prepared=read_bound(inp_ref)
   else:
    prepared=adapter.prepare(R,row['supplied_gene_request'],folder/'supplied_inputs',accepted_rows=accepted)
    inp_ref=g.ref(folder/'supplied_inputs/COMMITTED.json')
   checked(prepared['status']=='DEFENCE_SUPPLIED_GENE_INPUTS_COMMITTED_NOT_SEARCHED'
           and prepared['accession']==accession and prepared['input_request']==row['supplied_gene_request']
           and set(prepared['files'])==INPUT_FILES, 'supplied input receipt differs')
   inputs=RAM/'inputs'/accession;inputs.mkdir(parents=True)
   for name,ref in prepared['files'].items():
    source=bound(ref)
    if inherited:
     checked(source==source_output/'rows'/accession/'supplied_inputs'/name,
             'inherited supplied input file path differs')
    target=inputs/name;shutil.copyfile(source,target);assert g.sha(target)==ref['sha256']
   mapping=g.read(g.bound(prepared['files']['protein_identity_map.json']))
   record={'source':row,'prepared':prepared,'input_provenance':inp_ref,'inputs':inputs,
           'folder':folder,'mapping':mapping,'engines':{}}
   records[accession]=record
   if inherited:
    saved,elapsed=inherited_phase(P,manifest_row,saved_dispositions['rows'][index],record,source_output)
    if saved is not None:
     record['engines']['PADLOC']=saved;phase_commits.append(saved);saved_seconds+=elapsed;saved_count+=1
  checked(not inherited or (saved_count==9 and math.isclose(saved_seconds,prior_science,rel_tol=0,abs_tol=1e-6)),
          'verified inherited phase count or science debit differs')
  runtime.done=saved_count
  if inherited:
   runtime.publish('Nine saved PADLOC phases verified; only 11 PADLOC and 20 DefenseFinder phases remain',True,
                   cohort_novel_genomes=0,inherited_PADLOC_phases=saved_count)
  bin_dir=E/'bin';bin_dir.mkdir();(bin_dir/'hmmsearch').symlink_to(R/'scripts/defence_hmmer_receipt_v001.py')
  for name in('home','cache','emptylibs'):(E/name).mkdir()
  env={**os.environ,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','XDG_CACHE_HOME':str(E/'cache'),'XDG_DATA_HOME':str(E/'home'),'R_LIBS_USER':str(E/'emptylibs'),'R_PROFILE_USER':'/dev/null','R_ENVIRON_USER':'/dev/null','R_HISTFILE':str(E/'R_history'),'R_TMPDIR':'/tmp','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PATH':str(bin_dir)+':'+str(R/'tools/bioenv/bin')+':/usr/local/bin:/usr/bin:/bin','LD_LIBRARY_PATH':'/usr/local/lib:/usr/local/lib/R/lib'}
  pad_files=g.read(g.bound(P['PADLOC_compiled_manifest']));files=[{k:q[k]for k in('path','sha256','bytes')}for q in pad_files['outputs']]+pad_files['other_files'];pad_cache=cache(files,Path(P['PADLOC_model_root']),RAM/'PADLOC_models');runtime.phase='PADLOC_REAL_GENOME_FULL5027_PROTEIN_MODEL_SEARCH_AND_STOCK_RULES'
  for accession,record in records.items():
   if 'PADLOC' in record['engines']:
    continue
   runtime.current=accession;runtime.guard();folder=record['folder']/'PADLOC';folder.mkdir();output=folder/'stock_output';output.mkdir();query=record['inputs']/'padloc_canonical.faa';gff=record['inputs']/'padloc_canonical.gff';runtime.phase='PADLOC_REAL_GENOME_FULL5027_PROTEIN_MODEL_SEARCH_AND_STOCK_RULES';local={**env,'TREE2_DEFENCE_SEARCH_RECEIPTS':str(folder/'HMMER_receipts')};args=['/usr/local/bin/padloc','--data',str(pad_cache),'--faa',str(query),'--gff',str(gff),'--outdir',str(output),'--cpu',str(threads)];proof=runtime.run(folder/'unit',args,'PADLOC_STOCK_FULL_PROTEIN_SCOPE',[record['prepared']['files']['padloc_canonical.faa'],record['prepared']['files']['padloc_canonical.gff'],P['PADLOC_compiled_manifest']],environment=local)
   rows,evidence=classify(folder,proof,record['prepared'],P['PADLOC_compiled_manifest'],
                          P['PADLOC_HMM_sha256'],P['PADLOC_stock_R'],threads)
   calls,states=padloc_calls(rows,{q['canonical_id']:q for q in record['mapping']},pad_rules)
   g.save(folder/'scoped_predictions.json',{'calls':calls,'model_states':states,
          'RNA51_unavailable_never_zero':True,'all_stock_calls_preserved':True,
          'all_original_masks':record['source']['source_masks'],'no_final_panel_or_ring_acceptance':True})
   commit={
    'status':'PADLOC_STOCK0_TYPED_RAW0_SCOPED_REAL_GENOME_PHASE_COMMITTED_PENDING_OWNER_CLOSURE',
    'accession':accession,'engine':'PADLOC2_DB2','execution':proof,'typed_scientific_HMMER_searches':1,
    'calls':g.ref(folder/'scoped_predictions.json'),'artifacts':[g.ref(p) for p in folder.rglob('*') if p.is_file()],
    'source_queue_row':record['source'],'cache_provenance':g.ref(E/'cache_PADLOC_models.json'),
    'raw_phase_directory':folder.relative_to(R).as_posix(),'padloc_output_classification':evidence,
    'unavailable_RNA_model_count':sum(q['availability_and_prediction_state']=='UNKNOWN_RNA_FEATURES_UNAVAILABLE' for q in states),
    'model_relative_calls':len(calls),
    'eligible_primary_protein_predictions':sum(q['eligible_primary_predicted_protein_system'] for q in calls),
    'source_taxonomy_type_quality_holds_preserved':True,
   }
   g.save(folder/'COMMITTED.json',commit);record['engines']['PADLOC']=g.ref(folder/'COMMITTED.json')
   phase_commits.append(record['engines']['PADLOC']);new_padloc+=1;runtime.done+=1
   runtime.publish('Real PADLOC protein-supported genome phase durably committed; RNA-dependent states remain UNKNOWN',True,
                   inherited_PADLOC_phases=saved_count)
  verify_cache(pad_cache);shutil.rmtree(pad_cache);runtime.guard()
  df_files=g.read(g.bound(P['DF_model_manifest']))['files'];df_cache=cache(df_files,Path(P['DF_model_root']),RAM/'DF_models');overlay_files=g.read(g.bound(P['DF_runtime_manifest']))['files'];overlay=cache(overlay_files,Path(P['DF_runtime_root']),RAM/'DF_runtime');py=R/P['python'];bootstrap=g.bound(P['DF_bootstrap']);df_entry=overlay/'python-scripts/defense-finder'
  for accession,record in records.items():
   runtime.current=accession;runtime.guard();runtime.phase='DEFENSEFINDER_REAL_GENOME_DEFAULT_DF_RM_CAS_PROTEIN_SCOPE';folder=record['folder']/'DefenseFinder';folder.mkdir();output=folder/'stock_output';query=record['inputs']/'defensefinder_gembase.faa';(record['inputs']/'DF_indices').mkdir();local={**env,'LD_LIBRARY_PATH':'','PYTHONPATH':str(overlay/'site-packages')+':'+str(R/P['numpy_overlay']),'TREE2_DEFENCE_SEARCH_RECEIPTS':str(folder/'HMMER_receipts')};args=[str(py),'-B',str(bootstrap),'script',str(df_entry),'run','--out-dir',str(output),'--workers',str(threads),'--db-type','gembase','--models-dir',str(df_cache),'--skip-model-version-check','--preserve-raw','--index-dir',str(record['inputs']/'DF_indices'),str(query)];proof=runtime.run(folder/'unit',args,'DEFENSEFINDER_STOCK_FULL_DEFAULT_PROTEIN_SCOPE',[record['prepared']['files']['defensefinder_gembase.faa'],record['prepared']['files']['macsyfinder.conf'],P['DF_model_manifest']],environment=local,cwd=record['inputs'])
   reports=list(output.glob('*_defense_finder_systems.tsv'));assert len(reports)==1;count=searches(folder,record['prepared']['files']['defensefinder_gembase.faa']['sha256'],'DefenseFinder');rows=list(csv.DictReader(reports[0].open(),delimiter='\t'));calls,states=defensefinder_calls(rows,{q['DF_ID']:q for q in record['mapping']},df_rules);g.save(folder/'scoped_predictions.json',{'calls':calls,'model_states':states,'ADF156_excluded_and_genericCAS_clusters_separate':True,'source_masks':record['source']['source_masks'],'all_stock_calls_preserved':True,'no_final_panel_or_ring_acceptance':True});artifacts=[g.ref(p)for p in folder.rglob('*')if p.is_file()];commit={'status':'DF_STOCK0_TYPED_RAW0_SCOPED_REAL_GENOME_PHASE_COMMITTED_PENDING_OWNER_CLOSURE','accession':accession,'engine':'DefenseFinder3_models3.1_Cas3.1','execution':proof,'typed_scientific_HMMER_searches':count,'calls':g.ref(folder/'scoped_predictions.json'),'artifacts':artifacts,'source_queue_row':record['source'],'model_cache_provenance':g.ref(E/'cache_DF_models.json'),'runtime_cache_provenance':g.ref(E/'cache_DF_runtime.json'),'model_relative_calls':len(calls),'eligible_primary_protein_predictions':sum(q['eligible_primary_predicted_protein_system']for q in calls),'source_taxonomy_type_quality_holds_preserved':True};g.save(folder/'COMMITTED.json',commit);record['engines']['DefenseFinder']=g.ref(folder/'COMMITTED.json');phase_commits.append(record['engines']['DefenseFinder']);combined={'status':'REAL_GENOME_BOTH_STOCK_PROTEIN_DEFENCE_ENGINES_COMMITTED_PENDING_COHORT_EXTERNAL_ACCEPTANCE','accession':accession,'engines':record['engines'],'input_provenance':record['input_provenance'],'source_queue_row':record['source'],'RNA_feature_models_remain_UNKNOWN':True,'no_final_panel_or_ring_acceptance':True};g.save(record['folder']/'COMMITTED.json',combined);completed.append(g.ref(record['folder']/'COMMITTED.json'));new_df+=1;runtime.done+=1;runtime.publish('Real genome both protein-supported engines durably committed',True)
  verify_cache(df_cache);verify_cache(overlay)
  n=len(P['selected_accessions'])
  checked(new_df==len(completed)==n and saved_count+new_padloc==n
          and len({ref['path'] for ref in phase_commits})==len(phase_commits)==2*n,
          'missing or duplicate completed phases')
  runtime.guard();attempt_cold=time.monotonic()-runtime.started
  g.save(OUT/'COHORT_COMPLETE.json',{
   'status':'NOVEL_COHORT_BOTH_PROTEIN_SUPPORTED_ENGINES_COMPUTED_PENDING_EXTERNAL_CLOSURE_AND_VALIDATION',
   'selected_accessions':P['selected_accessions'],'genome_commits':completed,'engine_phase_commits':phase_commits,
   'source_plan':g.ref(plan_path),'actual_scientific_seconds':prior_science+runtime.science,
   'actual_cold_seconds':prior_cold+attempt_cold,'attempt_scientific_seconds':runtime.science,
   'attempt_cold_seconds':attempt_cold,'inherited_scientific_seconds':prior_science,
   'inherited_cold_seconds':prior_cold,'inherited_PADLOC_phases':saved_count,
   'new_PADLOC_phases':new_padloc,'new_DefenseFinder_phases':new_df,
   'inherited_phase_manifest':None if inherited is None else P['resume']['inherited_phase_manifest'],
   'peak_Linux_RSS_plus_private_RAM_bytes':runtime.peak,'throughput_is_real_genome_production_not_synthetic_control':True,
   'automatic_next_disjoint_cohort_after_closed_ledger_commit':True,'all919_scope_still_required':True,
   'no_complete_project_or_final_ring_acceptance':True,
  })
  runtime.publish('Production cohort computed; exact closure and independent phase validation precede ledger acceptance',
                  True,status='COMPUTED_PENDING_EXTERNAL_COHORT_ACCEPTANCE',inherited_PADLOC_phases=saved_count)
 except BaseException as error:
  g.save(E/'failure.json',{'error':repr(error),'current':runtime.current,'phase':runtime.phase,'completed_genomes':len(completed),'completed_engine_phases':phase_commits,'known_scientific_debit_seconds':runtime.science,'known_cold_debit_seconds':time.monotonic()-runtime.started,'prior_scientific_debit_seconds_already_charged':prior_science,'prior_cold_debit_seconds_already_charged':prior_cold,'inherited_PADLOC_phases':saved_count,'successful_typed_searches_and_stock_phases_preserved_no_replay':True,'RAM_caches_not_checkpoints_source_models_and_supplied_inputs_durable':True,'failed_unrun_or_unavailable_models_not_negative':True,'at_utc':g.utc()});raise
 finally:fcntl.flock(lease,fcntl.LOCK_UN);lease.close();fcntl.flock(common,fcntl.LOCK_UN);common.close()

if __name__=='__main__':main()
