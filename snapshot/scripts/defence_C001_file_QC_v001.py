"""Independent saved-file rule/provenance audit derived from accepted pilot validator."""
from pathlib import Path
import sys,json,time,csv,hashlib,collections,math,gc
import local_tree2_dispatcher as b
import marker_pilot_compute_v001 as g
from defence_file_QC_sqlite_v001 import VerifiedFiles

def validate(R,Q,output,guard,notify):
 O=output;EVENT=Q['event']['sha256'];ED=b.bind(R,Q['event']).parent;D=R/'state/local_continuation_v7'
 cache=VerifiedFiles(output/'verified_files_and_births.sqlite');bytecount=0;last=0;start=time.monotonic();groups=set()
 def bound(q):
  nonlocal bytecount
  guard();p=b.inside(R,q['path'])
  if p in cache:assert cache[p]==(q['sha256'],q['bytes'])
  else:b.bind(R,q);cache[p]=(q['sha256'],q['bytes']);bytecount+=q['bytes']
  return p
 def read(q):return b.read(bound(q))
 def identity(i):
  cache.identity(i);groups.add(i['process_group'])
 def publish(detail):
  guard();notify(detail,len(summaries),20)
 assert b.digest(ED/'event.json')==EVENT;ev=b.read(ED/'event.json');h=read(Q['scientific_handoff']);assert Q['scientific_handoff']['sha256']==ev['handoff_sha256'];assert ev['actual_exit_code']==0 and ev['retained_handle_identity_verified']is True
 assert read(ev['launch_receipt'])['native_owner']==ev['worker_identity'];read(ev['actual_exit_receipt'])
 for k in('local_Root_scientific_admission','local_Root_source_review','source_bound_plan'):bound(h[k])
 P=read(h['source_bound_plan']);E=R/P['work'];OUT=R/P['output'];result=b.read(OUT/'COHORT_COMPLETE.json');assert result['source_plan']==h['source_bound_plan'];assert result['selected_accessions']==P['selected_accessions']
 w=b.read(E/'WSL_actual_exit.json');assert type(w['actual_exit_code'])is int and w['actual_exit_code']==0 and w['exact_birth_handle_retained']and w['waited_and_reaped'];memory=b.read(E/'native_RSS_guard.json');assert memory['fatal_resource_reason']is None and memory['peak_native_plus_retained_WSL_RSS_bytes']<=P['native_reserved_bytes']
 for q in P['sources']+P['bound_inputs']:bound(q)
 queue=read(P['queue']);queue_rows={q['accession']:q for q in queue['rows']};padmodels={q['model_id']:q for q in read(P['PADLOC_rules'])['models']};dfrules=read(P['DF_rules'])['rows'];dfmodels={q['namespace']+'/'+q['family']+'/'+q['model']:q for q in dfrules}
 assert len(padmodels)==385 and len(dfmodels)==710
 for name in('cache_PADLOC_models.json','cache_DF_models.json','cache_DF_runtime.json'):
  for q in b.read(E/name)['cached_files']:bound(q['original_source'])
 summaries=[];science=0.;peak=0;minimum=None;rawcount=0;phasecount=0
 for ref in result['genome_commits']:
  c=read(ref);acc=c['accession'];assert c['source_queue_row']==queue_rows[acc];src=queue_rows[acc]['supplied_gene_request'];inp=read(c['input_provenance']);assert inp['input_request']==src
  for q in src.values():
   if isinstance(q,dict)and all(k in q for k in('path','sha256','bytes')):bound(q)
  for q in inp['files'].values():bound(q)
  original=g.fasta(bound(src['canonical_FAA']));df=g.fasta(bound(inp['files']['defensefinder_gembase.faa']));assert inp['files']['padloc_canonical.faa']['sha256']==src['canonical_FAA']['sha256'];mapping=read(inp['files']['protein_identity_map.json']);byid={q['canonical_id']:q for q in mapping};bydf={q['DF_ID']:q for q in mapping};coord={q['protein_id']:q for q in read(src['protein_coordinate_map'])};assert set(original)==set(byid)==set(coord)and set(df)==set(bydf)and len(original)==inp['protein_count'];lines=bound(src['Prodigal_GFF']).read_text().splitlines()
  for m in mapping:
   n=m['canonical_id'];a=coord[n];assert all(m[k]==a[k]for k in('contig','start','end','strand'))and m['original_Prodigal_ID']==a['prodigal_gene_id'];assert original[n]==df[m['DF_ID']]and hashlib.sha256(original[n].encode()).hexdigest()==m['AA_sha256'];assert hashlib.sha256(lines[m['source_GFF_line_number']-1].encode()).hexdigest()==m['source_GFF_line_sha256']
  adapted=bound(inp['files']['padloc_canonical.gff']).read_text().splitlines();gffrows=[x.split('\t')for x in adapted if x and not x.startswith('#')];assert len(gffrows)==len(mapping)
  for fields in gffrows:
   attrs=dict(z.split('=',1)for z in fields[8].split(';')if'='in z);m=byid[attrs['ID']];assert (fields[0],int(fields[3]),int(fields[4]),fields[6])==(m['contig'],m['start'],m['end'],m['strand'])
  engines={}
  for engine,phase_ref in c['engines'].items():
   phase=read(phase_ref);assert phase['source_queue_row']==queue_rows[acc];folder=bound(phase_ref).parent;e=read(phase['execution']);assert type(e['actual_exit_code'])is int and e['actual_exit_code']==0 and e['actual_child_waited_and_reaped']and e['group_closed']and not e['remaining_owned_identities']and not e['remaining_group_members'];assert e['error']is None
   for i in e['captured_owned_identities']:identity(i)
   assert e['peak_summed_owned_Linux_RSS_plus_private_RAM_bytes']<=P['linux_RSS_plus_RAM_bytes']and e['minimum_Linux_available_bytes']>=P['minimum_linux_available_bytes'];science+=e['elapsed_seconds'];peak=max(peak,e['peak_summed_owned_Linux_RSS_plus_private_RAM_bytes']);minimum=e['minimum_Linux_available_bytes']if minimum is None else min(minimum,e['minimum_Linux_available_bytes']);phasecount+=1
   for q in phase['artifacts']:bound(q);publish(acc+' '+engine+' immutable artifacts and raw exits')
   searched=[];models=set();profile_paths=set()
   for rp in(folder/'HMMER_receipts').glob('*.json'):
    s=b.read(rp);assert s['status']=='ACTUAL_HMMER_EXIT_AND_RAW_CHECKPOINT_OBSERVED'and type(s['actual_exit_code'])is int and s['actual_exit_code']==0 and s['binary_handle_waited_and_reaped'];identity(s['binary_identity'])
    if s['probe_only']:continue
    assert s['query_faa_sha256']==inp['files']['padloc_canonical.faa'if engine=='PADLOC'else'defensefinder_gembase.faa']['sha256'];assert s['model_file_sha256']==P['PADLOC_HMM_sha256']if engine=='PADLOC'else s['model_file_sha256']in P['DF_profile_SHA256'];assert s['no_argument_or_threshold_changes']and s['raw_outputs'];models.add(s['model_file_sha256']);profile_paths.add(s['argv'][-2])
    for raw in s['raw_outputs']:
     p=bound(raw)
     with p.open('rb')as f:f.seek(max(0,p.stat().st_size-4096));assert b'[ok]'in f.read()
    searched.append(s)
   assert len(searched)==phase['typed_scientific_HMMER_searches'];rawcount+=len(searched);scope=read(phase['calls']);assert scope['all_stock_calls_preserved']and scope['no_final_panel_or_ring_acceptance']
   if engine=='PADLOC':
    stock=list(csv.DictReader((folder/'stock_output/padloc_canonical_padloc.csv').open(newline='',encoding='utf8')));expected=collections.defaultdict(list)
    for row in stock:
     m=byid[row['target.name']];assert(row['seqid'],int(row['start']),int(row['end']),row['strand'])==(m['contig'],m['start'],m['end'],m['strand']);expected[(row['seqid'],row['system.number'],row['system'])].append(row)
    assert len(expected)==len(scope['calls']);assert scope['all_original_masks']==src['source_masks'];observed=set()
    for call in scope['calls']:
     model=padmodels[call['model_id']];key=(call['contig'],call['stock_system_number'],call['model_id']);assert call['stock_rows']==expected[key]and call['canonical_protein_IDs']==sorted({q['target.name']for q in expected[key]});observed.add(call['model_id']);rna=any(model['RNA_feature_roles'].values());eligible=model['registered_search_enabled']and not rna and not any(model[k]for k in('explicit_HEC_PDC_candidate','relaxed_other_model','module_or_non_antiphage_function_review_flag'));assert call['eligible_primary_predicted_protein_system']==eligible and call['inferred_HEC_PDC']==model['explicit_HEC_PDC_candidate']and call['relaxed_model']==model['relaxed_other_model'];assert call['feature_availability_state']==('UNKNOWN_RNA_FEATURES_UNAVAILABLE'if rna else'COMPLETE_PROTEIN_MODEL_PREDICTION')
    assert len(scope['model_states'])==len(padmodels)
    for state in scope['model_states']:
     model=padmodels[state['model_id']];v='NOT_SEARCHED_UNREGISTERED'if not model['registered_search_enabled']else('UNKNOWN_RNA_FEATURES_UNAVAILABLE'if any(model['RNA_feature_roles'].values())else('COMPLETE_PROTEIN_MODEL_PREDICTION'if state['model_id']in observed else'NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE'));assert state['availability_and_prediction_state']==v
    assert sum(s['availability_and_prediction_state']=='UNKNOWN_RNA_FEATURES_UNAVAILABLE'for s in scope['model_states'])==51
   else:
    paths=list((folder/'stock_output').glob('*_defense_finder_systems.tsv'));assert len(paths)==1;stock=list(csv.DictReader(paths[0].open(newline='',encoding='utf8'),delimiter='\t'));assert [q['stock_call']for q in scope['calls']]==stock;observed=set();assert scope['source_masks']==src['source_masks']
    for call in scope['calls']:
     row=call['stock_call'];ids=row['protein_in_syst'].split(',');m=dfmodels[call['model_id']];contigs=sorted({bydf[n]['contig']for n in ids});repeat=len(ids)!=len(set(ids));anti=m['namespace']=='ADF'or m['functional_class']=='ANTI_DEFENCE_EXCLUDED_FROM_ANTIPHAGE_RING';generic=m['CAS_generic_cluster_requires_distinct_review'];assert call['DF_IDs']==ids and call['canonical_protein_IDs']==[bydf[n]['canonical_id']for n in ids]and call['original_contigs']==contigs and len(ids)==int(row['genes_count']);assert call['eligible_primary_predicted_protein_system']==(not anti and not generic and len(contigs)==1 and not repeat);assert call['repeated_gene_ID_role_assignments_preserved_for_review']==repeat and call['cross_contig_review_required']==(len(contigs)!=1)and call['anti_defence_excluded']==anti;observed.add(call['model_id'])
    assert len(scope['model_states'])==len(dfmodels)
    for state in scope['model_states']:
     model=dfmodels[state['model_id']];v='EXCLUDED_ANTI_DEFENCE_SCOPE'if model['namespace']=='ADF'else('COMPLETE_PROTEIN_MODEL_PREDICTION'if state['model_id']in observed else'NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE');assert state['availability_and_prediction_state']==v
   engines[engine]={'commit':phase_ref,'typed_HMMER0':len(searched),'distinct_searched_profile_paths':len(profile_paths),'stock_internal_repeated_profile_invocations_preserved':len(searched)-len(profile_paths),'stock0_seconds':e['elapsed_seconds'],'stock_model_relative_calls':len(scope['calls']),'eligible_primary_protein_predictions':sum(q['eligible_primary_predicted_protein_system']for q in scope['calls']),'unavailable_is_UNKNOWN':True,'no_biological_absence_or_final_ring_acceptance':True}
  summaries.append({'accession':acc,'original_proteins':len(original),'engines':engines,'source_masks':src['source_masks']});publish(acc+' both saved engine phases independently audited')
 assert len(summaries)==20 and phasecount==40 and math.isclose(science,result['actual_scientific_seconds'],abs_tol=1e-6)
 identity(b.read(E/'linux_owner.json'))
 assert science<=P['science_seconds'] and result['actual_cold_seconds']<=P['cold_seconds']
 for row in result['genome_commits']+result['engine_phase_commits']:bound(row)
 manifest=read(Q['closed_cohort_manifest']);assert manifest['source_result']==b.row(R,OUT/'COHORT_COMPLETE.json')
 cache.verify_all(R,guard,publish);files_hashed=len(cache);births=cache.birth_count();cache.close()
 for row in result['genome_commits']+result['engine_phase_commits']:b.bind(R,row)
 b.bind(R,Q['closed_cohort_manifest']);b.bind(R,Q['whole_computation_closure'])
 b.atomic(O/'validated_cohort_rows.json',{'rows':summaries,'all_masks_preserved':True,'no_prediction_search_annotation_replayed':True,'all919_still_required':True})
 summary={'status':'FORTY_SAVED_STOCK_PHASES_TYPED_RAW_EXITS_ORIGINAL_INPUTS_COMPLETE_SCOPE_RULES_AND_POSTHASH_VALIDATED_PENDING_QA_NATIVE_EXIT','event':Q['event'],'source_plan':h['source_bound_plan'],'source_result':b.row(R,OUT/'COHORT_COMPLETE.json'),'native_actual_exit':ev['actual_exit_receipt'],'WSL_actual_exit':b.row(R,E/'WSL_actual_exit.json'),'rows':b.row(R,O/'validated_cohort_rows.json'),'verified_files_and_births':b.row(R,O/'verified_files_and_births.sqlite'),'captured_Linux_births':births,'actual0_stock_phases':phasecount,'typed_HMMER0_searches':rawcount,'scientific_seconds':science,'cold_seconds':result['actual_cold_seconds'],'peak_Linux_RSS_plus_private_RAM_bytes':peak,'native_peak_RSS_bytes':memory['peak_native_plus_retained_WSL_RSS_bytes'],'minimum_sampled_Linux_available_bytes':minimum,'unique_files_hashed':files_hashed,'unique_bytes_hashed':bytecount,'every_saved_file_independently_posthashed_again':True,'elapsed_file_QA_seconds':time.monotonic()-start,'whole_scientific_computation_closure':Q['whole_computation_closure'],'no_child_process_predictor_model_annotation_or_search_executed_by_QA':True,'no_biological_absence_inferred':True,'final_panel_ring_or_tree_acceptance':False,'retained_phylogeny_holds':P['retained_phylogeny_scientific_holds'],'at_utc':b.utc()}
 b.atomic(O/'validation_summary.json',summary)
 return summary
