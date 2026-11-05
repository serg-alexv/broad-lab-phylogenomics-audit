"""Call provenance and feature/evidence masks. Stock predictors alone decide model calls."""
import collections

def padloc_model_state(model,observed):
 if not model['registered_search_enabled']:return 'NOT_SEARCHED_UNREGISTERED'
 if any(model['RNA_feature_roles'].values()):return 'UNKNOWN_RNA_FEATURES_UNAVAILABLE'
 return 'COMPLETE_PROTEIN_MODEL_PREDICTION'if observed else'NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE'

def padloc_primary_eligible(model):
 return model['registered_search_enabled']and not any(model['RNA_feature_roles'].values())and not model['explicit_HEC_PDC_candidate']and not model['relaxed_other_model']and not model['module_or_non_antiphage_function_review_flag']

def padloc_calls(rows,mapping,models):
 groups=collections.defaultdict(list)
 for row in rows:
  target=row['target.name'];assert target in mapping;source=mapping[target]
  assert row['seqid']==source['contig']and int(row['start'])==source['start']and int(row['end'])==source['end']and row['strand']==source['strand']
  assert row['system']in models;groups[(row['seqid'],row['system.number'],row['system'])].append(row)
 calls=[]
 for (contig,number,model_id),hits in groups.items():
  model=models[model_id];ids=sorted({q['target.name']for q in hits});calls.append({'stock_system_number':number,'model_id':model_id,'contig':contig,'canonical_protein_IDs':ids,'stock_rows':hits,'complete_model_relative_prediction':True,'feature_availability_state':padloc_model_state(model,True),'eligible_primary_predicted_protein_system':padloc_primary_eligible(model),'evidence_class':model['evidence_class'],'inferred_HEC_PDC':model['explicit_HEC_PDC_candidate'],'relaxed_model':model['relaxed_other_model'],'biological_truth_or_final_ring_acceptance':False})
 observed={q['model_id']for q in calls};states=[{'model_id':name,'availability_and_prediction_state':padloc_model_state(model,name in observed),'evidence_class':model['evidence_class'],'stock_rule_source':model['definition']}for name,model in models.items()]
 return calls,states

def defensefinder_calls(rows,mapping,rules):
 calls=[];observed=set()
 for row in rows:
  ids=[s.strip()for s in row['protein_in_syst'].split(',')if s.strip()];assert ids and len(ids)==int(row['genes_count'])and all(n in mapping for n in ids);contigs={mapping[n]['contig']for n in ids};repeated=len(ids)!=len(set(ids))
  candidates=[q for q in rules if q['model']==row['subtype']]
  if len(candidates)>1:candidates=[q for q in candidates if q['family']==row['type']]
  if len(candidates)!=1:raise RuntimeError('Unresolved stock DefenseFinder model identity: '+row['type']+'/'+row['subtype'])
  model=candidates[0];key=model['namespace']+'/'+model['family']+'/'+model['model'];observed.add(key);anti=model['namespace']=='ADF'or model['functional_class']=='ANTI_DEFENCE_EXCLUDED_FROM_ANTIPHAGE_RING';generic=model['CAS_generic_cluster_requires_distinct_review'];eligible=not anti and not generic and len(contigs)==1 and not repeated
  calls.append({'model_id':key,'stock_call':row,'canonical_protein_IDs':[mapping[n]['canonical_id']for n in ids],'DF_IDs':ids,'original_contigs':sorted(contigs),'complete_model_relative_prediction':True,'eligible_primary_predicted_protein_system':eligible,'evidence':model['evidence'],'functional_class':model['functional_class'],'generic_CAS_cluster_not_complete_subtype':generic,'anti_defence_excluded':anti,'CRISPR_array_feature_state':'UNKNOWN_UNAVAILABLE'if model['namespace']=='CasFinder'else'NOT_REQUIRED_BY_THIS_PROTEIN_MODEL','cross_contig_review_required':len(contigs)!=1,'repeated_gene_ID_role_assignments_preserved_for_review':repeated,'biological_truth_or_final_ring_acceptance':False})
 states=[]
 for model in rules:
  key=model['namespace']+'/'+model['family']+'/'+model['model'];state='EXCLUDED_ANTI_DEFENCE_SCOPE'if model['namespace']=='ADF'else('COMPLETE_PROTEIN_MODEL_PREDICTION'if key in observed else'NO_COMPLETE_PROTEIN_MODEL_CALL_AFTER_SUCCESS_NOT_BIOLOGICAL_ABSENCE');states.append({'model_id':key,'availability_and_prediction_state':state,'functional_class':model['functional_class'],'generic_CAS_cluster_not_complete_subtype':model['CAS_generic_cluster_requires_distinct_review']})
 return calls,states
