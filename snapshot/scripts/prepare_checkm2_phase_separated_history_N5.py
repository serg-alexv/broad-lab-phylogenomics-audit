"""N5 source/selection only. Bounded history and exactly five once-observed FNA checksums; no biology."""
from pathlib import Path
import json,hashlib,re,os,collections
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_phase_separated_N5'
ACC=re.compile(r'GC[AF]_\d{9}\.\d+')
AUTH='f2e4707ff9cb9648432502d0a1ea0d43d0c957b8729e8346bfa592980c239e7b'
REGISTRY='00f48092f8905cd80a8a8539fc7d92c9bdf2abc2661927c41b4976ff4fd815e6'
GENOMIC={'pilot10':'pilot','checkm2_pilot':'baseline','checkm2_protein_pilot_v001':'baseline','checkm2_protein_format_invariance_v002':'baseline','checkm2_posthoc_v002':'baseline','checkm2_benchmark10_protein_v002':'cohort','checkm2_benchmark10_protein_recovery_T1':'cohort','checkm2_single_faa_S1':'cohort','checkm2_single_faa_S1R2':'cohort','checkm2_phase_separated_N1':'n1'}
ENGINEERING={'checkm2_benchmark10','checkm2_runtime','checkm2_memory_diagnostic','checkm2_S1R2_observer_proof','checkm2_installer','checkm2_installer_waiter'}
FIELDS={'accession','source_accession','original_accession','baseline_accession','current_accession','paired_accession'}
def path(value):
 p=(R/value).resolve()
 if not p.is_relative_to(R):raise RuntimeError('History/input path escapes project')
 return p
def sha(p):
 with Path(p).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()
def ref(value):
 p=path(value);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def read(value):return json.loads(path(value).read_text(encoding='utf-8-sig'))
def write(value,data):
 p=path(value);p.parent.mkdir(parents=True,exist_ok=True);payload=(json.dumps(data,indent=2)+'\n').encode()
 if p.exists():
  if p.read_bytes()!=payload:raise RuntimeError('Existing selection differs; preserve it, no reselection')
  return ref(value)
 temporary=p.with_suffix(p.suffix+'.part')
 with temporary.open('xb') as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
 os.replace(temporary,p);return ref(value)
def accessions(value):
 result=set()
 if isinstance(value,dict):
  for key,item in value.items():
   if key=='command' and isinstance(item,list):result|={match for arg in item if isinstance(arg,str) for match in ACC.findall(arg)}
   if key in ('accessions','accepted_unique_cohort_accessions','query_genomes') and isinstance(item,list):result|={x for x in item if isinstance(x,str) and ACC.fullmatch(x)}
   if key in FIELDS and isinstance(item,str) and ACC.fullmatch(item):result.add(item)
   if isinstance(item,(dict,list)):result|=accessions(item)
 elif isinstance(value,list):
  for item in value:result|=accessions(item)
 return result

def inventory():
 found={}
 for branch in ('analysis','evidence'):
  for folder in (R/branch).iterdir():
   if not (folder.name.startswith('checkm2') or folder.name=='pilot10'):continue
   if not folder.is_dir():continue
   for p in folder.rglob('*.json'):
    rel=p.relative_to(R).as_posix()
    if any(mark in rel for mark in ('/files/','_snapshots/','/snapshots/')):continue # duplicate immutable copies; originals remain inventoried
    if any(mark in p.name for mark in ('claim','binding','command','commit','feature_request')) or p.name=='execution.json' and p.parent.name.startswith('unit_') or folder.name=='checkm2_phase_separated_N1' and p.parent.name=='requests' or folder.name=='pilot10' and (p.name=='plan.json' or p.name.endswith('.exit.json')):found[rel]=folder.name
 for p in (R/'state').glob('*checkm2*launch_requests/*.json'):found[p.relative_to(R).as_posix()]=p.parent.name.removesuffix('_launch_requests')
 for p in (R/'state').glob('launch_checkm2*.json'):
  name=p.stem.removeprefix('launch_');name=name.removesuffix('_outer');found[p.relative_to(R).as_posix()]=name
 if len(found)>5000:raise RuntimeError('Bounded history inventory exceeded5000')
 return sorted(found.items())

def known_shape(relative,item):
 if not isinstance(item,dict):raise RuntimeError('Nonobject history body: '+relative)
 name=Path(relative).name;keys=set(item)
 allowed={'TREE2_CONTROL_FEATURE_REQUEST_V002','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1R2','TREE2_BENCHMARK10_FEATURE_REQUEST_V002','TREE2_PHASE_SEPARATED_N1_ANNOTATION_REQUEST_V001','TREE2_PHASE_SEPARATED_N1_DIAMOND_REQUEST_V001','TREE2_PHASE_SEPARATED_N1_FEATURE_REQUEST_V001'}
 for key in ('schema','request_schema'):
  declared=item.get(key)
  if isinstance(declared,str) and declared not in allowed:raise RuntimeError('Unknown declared history schema: '+relative)
  if declared is not None and not isinstance(declared,(str,dict)):raise RuntimeError('Untyped history schema: '+relative)
  if isinstance(declared,dict):
   if key!='schema' or not {'path','sha256'}<=set(declared) or declared['sha256']!='90e482515c6924386a888aa14a036f7659acf9ad0c49814cb08a3a7e1f76f5ee' or ref(declared['path'])['sha256']!=declared['sha256']:raise RuntimeError('Unknown schema artifact binding: '+relative)
 if item.get('status')=='PREPARED_NOT_RUN' and keys=={'status','manifest_sha256'}:
  valid=True
 elif item.get('status')=='PREPARED_ONLY' and item.get('prediction_run') is False and {'binding_sha256','manifest_sha256'}<=keys:
  valid=True
 elif name=='execution.json' and Path(relative).parent.name.startswith('unit_'):
  valid=item.get('status') in ('UNIT_EXIT0_GROUP_CLOSED','UNIT_FAILED_OR_CLOSURE_UNPROVEN') and {'declared_unit','elapsed_seconds','exit_code','owned_group_empty','remaining_owned_processes'}<=keys
 elif item.get('request_schema','').startswith('TREE2_PHASE_SEPARATED_N1_'):
  required={'input_plan','source_manifest','protocol_admission','selected_input','runtime_prefix','request_schema'}
  extra={'TREE2_PHASE_SEPARATED_N1_ANNOTATION_REQUEST_V001':{'staged_fna'},'TREE2_PHASE_SEPARATED_N1_DIAMOND_REQUEST_V001':{'selected_faa','annotation_receipt','annotation_unit_execution','database','diamond_binary'},'TREE2_PHASE_SEPARATED_N1_FEATURE_REQUEST_V001':{'accession','scientific_recipe','schema','artifacts'}}
  valid=item['request_schema'] in extra and required|extra[item['request_schema']]<=keys
 elif 'command' in name or name.endswith('.exit.json'):
  valid=isinstance(item.get('command'),list) and bool(item['command']) or relative.startswith('evidence/checkm2_memory_diagnostic/') and {'command','sequence','at_utc'}<=keys and item['command'] in ('STOP','NEXT')
 elif 'feature_request' in name:
  valid=item.get('request_schema') in ('TREE2_CONTROL_FEATURE_REQUEST_V002','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1R2','TREE2_BENCHMARK10_FEATURE_REQUEST_V002') and isinstance(item.get('artifacts'),dict)
 elif 'commit' in name:
  valid=item.get('status') in ('PASS_PILOT_GENE_CALLING','ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT','SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','SINGLE_FAA_S1R2_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','SINGLE_FAA_EXIT0_RAW_PREDICTION_COMMITTED_VALIDATION_PENDING','N1_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE','N1_DIAMOND_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE','N1_STOCK_RESUME_EXIT0_FEATURE_VALIDATION_PENDING','N1_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE') and bool(ACC.fullmatch(str(item.get('accession') or item.get('binding',{}).get('input',{}).get('accession',''))))
 elif name=='plan.json':valid={'mode','accessions','prodigal'}<=keys and isinstance(item['accessions'],list)
 elif 'binding' in name:
  valid=any(set(x)<=keys for x in (('input','runtime','options'),('plan','runtime','launch'),('role','selected_FAA_sha256'),('role','original_FNA_sha256','derived_FNA_sha256'),('status','prior_input_binding','closure_sha256')))
 elif 'claim' in name:
  valid=any(set(x)<=keys for x in (('accession','binding','native_launch_token'),('input_plan_sha256','protocol_admission_sha256','native_launch_token'),('admission_sha256','input_plan_sha256','launch'),('token','input_plan_sha256'),('token','admission_sha256'),('native_owner','closure_sha256'),('native_owner','token','closure_sha256'),('owner','actual_exit_observation_sha256'),('owner','actual_foreground_observation_sha256'),('owner','closed_control_proof_sha256'),('at_utc','scope'),('at_utc','owner'),('absence','claims'),('accession','native_launch_token','source_manifest_sha256','input_plan_sha256','phase'),('owner','actual_Root_exit_observation_sha256')))
 elif relative.startswith('state/'):
  valid=any(set(x)<=keys for x in (('pid','script'),('native_owner','token'),('token','operation','ready_receipt_path'))) or {'native_owner','wsl_child','script','biological_prediction'}<=keys and item['biological_prediction'] is False
 else:valid=False
 if not valid:raise RuntimeError('Unknown history body schema: '+relative+' keys='+repr(sorted(keys)))
 return {'reader':'EXPLICIT_REQUIRED_FIELD_SHAPE_V002','keys':sorted(keys),'declared_schema':item.get('schema'),'status':item.get('status')}

def main():
 authority='metadata/checkm2_N5_source_selection_implementation_authority_v001.json';registry_path='metadata/checkm2_accepted_method_result_registry_v002.json'
 assert sha(path(authority))==AUTH and sha(path(registry_path))==REGISTRY
 a=read(authority);registry=read(registry_path);assert a['source_implementation_authorized']is True and a['local_metadata_history_selection_authorized']is True and a['maximum_selected_inputs']==5 and a['scientific_execution_authorized']is False
 n1authority=a['N1_closed_acceptance'];assert ref(n1authority['path'])==n1authority
 accepted={x['accession']for x in registry['rows']}|{registry['additional_baseline']['accession']};assert len(accepted)==12
 baseline={registry['additional_baseline']['accession']};old_ten_registry='metadata/checkm2_accepted_method_result_registry_v001.json';assert ref(old_ten_registry)['sha256']=='54e96afed0c1f16819f6c96d048a7185abd4e79d79d68df34e6a0a3cf2f0c514';cohort=set(read(old_ten_registry)['accepted_unique_cohort_accessions']);assert len(cohort)==10;n1={'GCF_900636575.1'};pilot_plans=sorted((R/'analysis/pilot10/runs').glob('*/plan.json'));pilot=set()
 for p in pilot_plans:
  value=read(p.relative_to(R).as_posix());assert isinstance(value.get('accessions'),list)and {'mode','prodigal'}<=set(value);pilot|=set(value['accessions'])
 assert len(pilot)==10;prior_inputs=accepted|pilot
 candidates={x['accession']:x for x in read('metadata/candidates_qc.json')};aliases={candidates[x]['paired_accession']for x in prior_inputs if candidates[x].get('paired_accession')};expected=prior_inputs|aliases;records=[];excluded=set(prior_inputs);unresolved=[]
 for rel,namespace in inventory():
  item=read(rel);shape=known_shape(rel,item);extracted=accessions(item)
  if namespace in GENOMIC:
   bound=baseline if GENOMIC[namespace]=='baseline'else pilot if GENOMIC[namespace]=='pilot'else n1 if GENOMIC[namespace]=='n1'else cohort
   if extracted-expected:unresolved.append({'path':rel,'unknown_accessions':sorted(extracted-expected)})
   excluded|=bound|extracted;kind='KNOWN_GENOMIC_NAMESPACE_WITH_BOUND_INPUT_SET'
  elif namespace in ENGINEERING:
   if extracted-expected:unresolved.append({'path':rel,'unknown_engineering_input':sorted(extracted-expected)})
   excluded|=extracted;bound=set();kind='KNOWN_NO_GENOME_ENGINEERING_WITH_PRIOR_CONTEXT_ONLY'
  else:unresolved.append({'path':rel,'unknown_namespace':namespace});bound=set();kind='UNKNOWN_BLOCKS_SELECTION'
  records.append({'artifact':ref(rel),'namespace':namespace,'validated_body_shape':shape,'schema_reader':kind,'direct_schema_field_accessions':sorted(extracted),'conservatively_bound_claim_input_accessions':sorted(bound)})
 if unresolved:raise RuntimeError('Unresolved history blocks novelty: '+repr(unresolved))
 excluded|={candidates[x]['paired_accession']for x in list(excluded)if x in candidates and candidates[x].get('paired_accession')};dna={};donors=[]
 for accession in sorted(prior_inputs):
  name='raw/'+accession+'/acquisition_receipt.json';receipt=read(name);genomic=[x for x in receipt['files']if x['path'].endswith('_genomic.fna')and 'cds_from'not in x['path']];assert len(genomic)==1
  dna[accession]=genomic[0]['sha256'];donors.append({'accession':accession,'acquisition_receipt':ref(name),'genomic_FNA_sha256_from_receipt':genomic[0]['sha256'],'paired_alias':candidates[accession].get('paired_accession')})
 history=write('metadata/checkm2_phase_separated_history_index_N5_v002.json',{'schema':'TREE2_N5_BOUNDED_KNOWN_NAMESPACE_HISTORY_V001','status':'SOURCE_SELECTION_HISTORY_COMPLETE_NO_NEW_SCIENCE','scope_authority':ref(authority),'registry':ref(registry_path),'N1_closed_acceptance':n1authority,'schema_mapping':GENOMIC,'no_genome_engineering_namespaces':sorted(ENGINEERING),'claim_inventory':records,'inventory_count':len(records),'archive_duplicate_policy':'Authoritative originals only; snapshot/files copies are not independent donors','prior_pilot10_plans':[ref(x.relative_to(R).as_posix())for x in pilot_plans],'prior_annotation_only_accessions':sorted(pilot-accepted),'accepted_method_accessions':sorted(accepted),'excluded_prior_accessions_and_paired_aliases':sorted(excluded),'known_DNA_donors':donors,'unresolved_history':[]})
 audit={x['accession']:x for x in read('qc/source_provenance_audit.json')['records']};scope=read('metadata/checkm2_post_benchmark_qc_scope_addendum_v002.json');priorities=set(scope['priority92_species_taxids']);assert len(scope['deferred95_accessions'])==95 and len(priorities)==92
 measured=[candidates[x]for x in accepted];family=collections.Counter(x['family']for x in measured);genus=collections.Counter(x['genus']for x in measured);rank={'Complete Genome':0,'Chromosome':1,'Scaffold':2,'Contig':3};queue=[]
 for accession in scope['deferred95_accessions']:
  item=candidates[accession];source=audit[accession];receipt_path='raw/'+accession+'/acquisition_receipt.json';receipt=read(receipt_path);assert ref(receipt_path)['sha256']==source['acquisition_receipt_sha256']and source['production_disposition']=='SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN'and source['holds_or_exclusions']==[]and item['metadata_qc']=='QC_PENDING'and not item['exclusion_reasons']
  files=[x for x in receipt['files']if x['path'].endswith('_genomic.fna')and 'cds_from'not in x['path']];assert len(files)==1 and receipt['acquisition_status']=='PASS'
  claimed=accession in excluded or item.get('paired_accession')in excluded or files[0]['sha256']in dna.values();key=[0 if item['species_taxid']in priorities else 1,family[item['family']],genus[item['genus']],item['family'].casefold(),item['genus'].casefold(),item['species_taxid'],rank.get(item['assembly_level'],4),accession]
  queue.append({'accession':accession,'species':item['species'],'species_taxid':item['species_taxid'],'family':item['family'],'genus':item['genus'],'queue_key':key,'excluded_prior_claim_or_DNA_alias':claimed,'source_pending_reasons':item['pending_reasons'],'source_masks':{'source_holds':source['holds_or_exclusions'],'source_ANI_status':item['ncbi_ani_taxonomy_status'],'independent_taxonomy':'UNRESOLVED_NOT_ACCEPTED','independent_biology':'NOT_PREDICTED_BY_PRIOR_HISTORY','source_type_assertion_not_independently_accepted':item.get('type_material',False),'production_acceptance':False},'acquisition_receipt':ref(receipt_path),'FNA_from_receipt':{'path':'raw/'+accession+'/'+files[0]['path'],'sha256':files[0]['sha256'],'bytes':files[0]['bytes']},'candidate_record':item,'source_audit_record':source})
 queue.sort(key=lambda x:x['queue_key']);representatives={}
 for x in queue:
  if x['queue_key'][0]==0 and not x['excluded_prior_claim_or_DNA_alias']:representatives.setdefault(x['species_taxid'],x['accession'])
 for x in queue:x['queue_key']=[0 if representatives.get(x['species_taxid'])==x['accession']else 1,*x['queue_key'][1:]]
 queue.sort(key=lambda x:x['queue_key']);eligible=[x for x in queue if x['queue_key'][0]==0 and not x['excluded_prior_claim_or_DNA_alias']];assert len(eligible)>=5;selected=eligible[:5];assert len({x['species_taxid']for x in selected})==5
 qref=write('metadata/checkm2_phase_separated_queue_N5_v002.json',{'schema':'TREE2_N5_IMMUTABLE_QUEUE_V001','scope_authority':ref(authority),'history':history,'source_snapshots':[ref(x)for x in('qc/source_provenance_audit.json','metadata/candidates_qc.json','metadata/provisional_panel.json','metadata/checkm2_post_benchmark_qc_scope_addendum_v002.json','analysis/sequence_qc/d64e016face251f1/input_manifest.json')],'accepted_measurement_counts_family':dict(family),'accepted_measurement_counts_genus':dict(genus),'assembly_preference':rank,'queue_count':len(queue),'priority_labels':92,'rows':queue,'selected_accessions':[x['accession']for x in selected],'first_novel_representative_per_label_before_extra_strains':True,'novel_priority_representatives':len(representatives),'no_original_FNA_read_before_selection_frozen':True})
 claim='metadata/checkm2_N5_selection_integrity/selected_set_claim.json'
 if path(claim).exists():
  original_claim=read(claim)
  if original_claim['authority_sha256']!=AUTH or original_claim['selected_accessions']!=[x['accession']for x in selected]or original_claim['FNA_receipt_rows']!=[x['FNA_from_receipt']for x in selected]:raise RuntimeError('History revision changes previously observed top five; hold without another FNA read')
 else:write(claim,{'authority_sha256':AUTH,'history':history,'queue':qref,'selected_accessions':[x['accession']for x in selected],'FNA_receipt_rows':[x['FNA_from_receipt']for x in selected]})
 actual=[]
 for item in selected:
  acc=item['accession'];observation='metadata/checkm2_N5_selection_integrity/'+acc+'.json'
  if path(observation).exists():
   observed=read(observation)
   if observed.get('status')!='HASHED_ONCE_SHA256_SIZE_MATCH' or observed['expected']!=item['FNA_from_receipt']:raise RuntimeError('Unknown/interrupted integrity observation; no second cohort or silent rehash')
  else:
   write(observation,{'status':'HASH_IN_PROGRESS_DO_NOT_AUTO_RETRY','accession':acc,'expected':item['FNA_from_receipt']})
   p=path(item['FNA_from_receipt']['path']);observed={'status':'HASHED_ONCE_SHA256_SIZE_MATCH','accession':acc,'expected':item['FNA_from_receipt'],'actual_sha256':sha(p),'actual_bytes':p.stat().st_size,'source_only_no_sequence_parse':True}
   if observed['actual_sha256']!=item['FNA_from_receipt']['sha256']or observed['actual_bytes']!=item['FNA_from_receipt']['bytes']:raise RuntimeError('Selected acquired FNA integrity differs')
   temporary=path(observation+'.complete.part')
   with temporary.open('xb')as f:f.write((json.dumps(observed,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
   os.replace(temporary,path(observation))
  actual.append({'accession':acc,'FNA':item['FNA_from_receipt'],'integrity_observation':ref(observation)})
 output=write('metadata/checkm2_phase_separated_selected_inputs_N5_v002.json',{'schema':'TREE2_N5_FIVE_SELECTED_INPUTS_V001','status':'FIVE_SELECTED_INTEGRITY_BOUND_NO_SCIENTIFIC_EXECUTION','scope_authority':ref(authority),'history':history,'queue':qref,'inputs':selected,'actual_selected_FNAs':actual,'selection_claim':ref(claim),'exactly_five_selected_genomes':True,'five_distinct_novel_missing_labels':True,'models_annotation_search_or_scientific_probe_executed':False,'scientific_admission':None})
 print(json.dumps({'history':history,'queue':qref,'selected_inputs':output,'selected':[{'accession':x['accession'],'species':x['species'],'family':x['family'],'genus':x['genus']}for x in selected],'prior_dna_donors':len(dna),'excluded_accessions_and_aliases':len(excluded)}))
if __name__=='__main__':main()
