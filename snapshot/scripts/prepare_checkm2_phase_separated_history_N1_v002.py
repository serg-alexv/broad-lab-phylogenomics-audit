"""N1 source/selection only. Bounded project JSON history and one FNA checksum; no biology."""
from pathlib import Path
import json,hashlib,re,os,collections
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_phase_separated_N1'
ACC=re.compile(r'GC[AF]_\d{9}\.\d+')
AUTH='115ab6f4fb8e17f9da84c5a3d599aa48a3751c246e4ccc67e4504bdaf577be5d'
REGISTRY='54e96afed0c1f16819f6c96d048a7185abd4e79d79d68df34e6a0a3cf2f0c514'
GENOMIC={'pilot10':'pilot','checkm2_pilot':'baseline','checkm2_protein_pilot_v001':'baseline','checkm2_protein_format_invariance_v002':'baseline','checkm2_posthoc_v002':'baseline','checkm2_benchmark10_protein_v002':'cohort','checkm2_benchmark10_protein_recovery_T1':'cohort','checkm2_single_faa_S1':'cohort','checkm2_single_faa_S1R2':'cohort'}
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
   if key in ('accessions','accepted_unique_cohort_accessions') and isinstance(item,list):result|={x for x in item if isinstance(x,str) and ACC.fullmatch(x)}
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
    if any(mark in p.name for mark in ('claim','binding','command','commit','feature_request')) or folder.name=='pilot10' and (p.name=='plan.json' or p.name.endswith('.exit.json')):found[rel]=folder.name
 for p in (R/'state').glob('*checkm2*launch_requests/*.json'):found[p.relative_to(R).as_posix()]=p.parent.name.removesuffix('_launch_requests')
 for p in (R/'state').glob('launch_checkm2*.json'):
  name=p.stem.removeprefix('launch_');name=name.removesuffix('_outer');found[p.relative_to(R).as_posix()]=name
 if len(found)>5000:raise RuntimeError('Bounded history inventory exceeded5000')
 return sorted(found.items())

def known_shape(relative,item):
 if not isinstance(item,dict):raise RuntimeError('Nonobject history body: '+relative)
 name=Path(relative).name;keys=set(item)
 if item.get('status')=='PREPARED_NOT_RUN' and keys=={'status','manifest_sha256'}:
  valid=True
 elif item.get('status')=='PREPARED_ONLY' and item.get('prediction_run') is False and {'binding_sha256','manifest_sha256'}<=keys:
  valid=True
 elif 'command' in name or name.endswith('.exit.json'):
  valid=isinstance(item.get('command'),list) and bool(item['command']) or relative.startswith('evidence/checkm2_memory_diagnostic/') and {'command','sequence','at_utc'}<=keys and item['command'] in ('STOP','NEXT')
 elif 'feature_request' in name:
  valid=item.get('request_schema') in ('TREE2_CONTROL_FEATURE_REQUEST_V002','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1','TREE2_SINGLE_FAA_FEATURE_REQUEST_S1R2','TREE2_BENCHMARK10_FEATURE_REQUEST_V002') and isinstance(item.get('artifacts'),dict)
 elif 'commit' in name:
  valid=item.get('status') in ('PASS_PILOT_GENE_CALLING','ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT','SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','SINGLE_FAA_S1R2_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE','SINGLE_FAA_EXIT0_RAW_PREDICTION_COMMITTED_VALIDATION_PENDING') and bool(ACC.fullmatch(str(item.get('accession') or item.get('binding',{}).get('input',{}).get('accession',''))))
 elif name=='plan.json':valid={'mode','accessions','prodigal'}<=keys and isinstance(item['accessions'],list)
 elif 'binding' in name:
  valid=any(set(x)<=keys for x in (('input','runtime','options'),('plan','runtime','launch'),('role','selected_FAA_sha256'),('role','original_FNA_sha256','derived_FNA_sha256'),('status','prior_input_binding','closure_sha256')))
 elif 'claim' in name:
  valid=any(set(x)<=keys for x in (('accession','binding','native_launch_token'),('input_plan_sha256','protocol_admission_sha256','native_launch_token'),('admission_sha256','input_plan_sha256','launch'),('token','input_plan_sha256'),('token','admission_sha256'),('native_owner','closure_sha256'),('native_owner','token','closure_sha256'),('owner','actual_exit_observation_sha256'),('owner','actual_foreground_observation_sha256'),('owner','closed_control_proof_sha256'),('at_utc','scope'),('at_utc','owner'),('absence','claims')))
 elif relative.startswith('state/'):
  valid=any(set(x)<=keys for x in (('pid','script'),('native_owner','token'),('token','operation','ready_receipt_path'))) or {'native_owner','wsl_child','script','biological_prediction'}<=keys and item['biological_prediction'] is False
 else:valid=False
 if not valid:raise RuntimeError('Unknown history body schema: '+relative+' keys='+repr(sorted(keys)))
 return {'reader':'EXPLICIT_REQUIRED_FIELD_SHAPE_V002','keys':sorted(keys),'declared_schema':item.get('schema'),'status':item.get('status')}

def main():
 authority='evidence/checkm2_phase_separated_N1/root_scope_source_selection_authority.json';registry_path='metadata/checkm2_accepted_method_result_registry_v001.json'
 assert sha(path(authority))==AUTH and sha(path(registry_path))==REGISTRY
 a=read(authority);registry=read(registry_path);assert a['candidate_selection_authorized'] is True and a['maximum_selected_control_genomes']==1 and a['scientific_genome_annotation_search_model_execution_authorized'] is False
 accepted={x['accession'] for x in registry['rows']}|{registry['additional_baseline']['accession']};assert len(accepted)==11
 baseline={registry['additional_baseline']['accession']};cohort=set(registry['accepted_unique_cohort_accessions']);pilot_plans=sorted((R/'analysis/pilot10/runs').glob('*/plan.json'));pilot=set()
 for p in pilot_plans:
  value=read(p.relative_to(R).as_posix());assert isinstance(value.get('accessions'),list) and {'mode','prodigal'}<=set(value);pilot|=set(value['accessions'])
 assert len(pilot)==10
 prior_inputs=accepted|pilot
 pilot_baseline=read('analysis/checkm2_pilot/pilot_plan.json');assert pilot_baseline['input']['accession'] in baseline and registry['additional_baseline']['format_control_same_donor'] in baseline
 candidates={x['accession']:x for x in read('metadata/candidates_qc.json')};aliases={candidates[x]['paired_accession'] for x in prior_inputs if candidates[x].get('paired_accession')};expected=prior_inputs|aliases
 records=[];excluded=set(prior_inputs);unresolved=[]
 for rel,namespace in inventory():
  item=read(rel);shape=known_shape(rel,item);extracted=accessions(item)
  if namespace in GENOMIC:
   bound=baseline if GENOMIC[namespace]=='baseline' else pilot if GENOMIC[namespace]=='pilot' else cohort
   if extracted-expected:unresolved.append({'path':rel,'unknown_accessions':sorted(extracted-expected)})
   excluded|=bound|extracted;kind='KNOWN_GENOMIC_NAMESPACE_WITH_BOUND_INPUT_SET'
  elif namespace in ENGINEERING:
   if extracted-expected:unresolved.append({'path':rel,'unknown_engineering_input':sorted(extracted-expected)})
   excluded|=extracted;bound=set();kind='KNOWN_NO_GENOME_ENGINEERING_WITH_PRIOR_CONTEXT_ONLY'
  else:unresolved.append({'path':rel,'unknown_namespace':namespace});bound=set();kind='UNKNOWN_BLOCKS_SELECTION'
  records.append({'artifact':ref(rel),'namespace':namespace,'validated_body_shape':shape,'schema_reader':kind,'direct_schema_field_accessions':sorted(extracted),'conservatively_bound_claim_input_accessions':sorted(bound),'schema':item.get('schema') if isinstance(item,dict) else None})
 if unresolved:raise RuntimeError('Unresolved history blocks novelty: '+repr(unresolved))
 excluded|={candidates[x]['paired_accession'] for x in list(excluded) if x in candidates and candidates[x].get('paired_accession')}
 dna={};donors=[]
 for accession in sorted(prior_inputs):
  name='raw/'+accession+'/acquisition_receipt.json';receipt=read(name);genomic=[x for x in receipt['files'] if x['path'].endswith('_genomic.fna') and 'cds_from' not in x['path']];assert len(genomic)==1
  dna[accession]=genomic[0]['sha256'];donors.append({'accession':accession,'acquisition_receipt':ref(name),'genomic_FNA_sha256_from_receipt':genomic[0]['sha256'],'paired_alias':candidates[accession].get('paired_accession')})
 history=write('metadata/checkm2_phase_separated_history_index_N1_v002.json',{'schema':'TREE2_N1_BOUNDED_KNOWN_NAMESPACE_HISTORY_V001','status':'SOURCE_SELECTION_HISTORY_COMPLETE_NO_NEW_SCIENCE','scope_authority':ref(authority),'registry':ref(registry_path),'schema_mapping':GENOMIC,'no_genome_engineering_namespaces':sorted(ENGINEERING),'claim_inventory':records,'inventory_count':len(records),'archive_duplicate_policy':'Project snapshot/files copies are duplicates, not independent claims; authoritative original claims/bindings/commands and state requests/launches are enumerated. No older/external folders.','control_mapping':'All pilot/format/posthoc namespaces bind exact baseline donor; accepted registry explicitly identifies format_control_same_donor. No renamed donor is fresh.','baseline_plan':ref('analysis/checkm2_pilot/pilot_plan.json'),'prior_pilot10_plans':[ref(x.relative_to(R).as_posix()) for x in pilot_plans],'prior_annotation_only_accessions':sorted(pilot-accepted),'accepted_method_accessions':sorted(accepted),'excluded_prior_accessions_and_paired_aliases':sorted(excluded),'known_DNA_donors':donors,'unresolved_history':[]})
 audit={x['accession']:x for x in read('qc/source_provenance_audit.json')['records']};scope=read('metadata/checkm2_post_benchmark_qc_scope_addendum_v002.json');priorities=set(scope['priority92_species_taxids']);assert len(scope['deferred95_accessions'])==95 and len(priorities)==92
 measured=[candidates[x] for x in accepted];family=collections.Counter(x['family'] for x in measured);genus=collections.Counter(x['genus'] for x in measured);rank={'Complete Genome':0,'Chromosome':1,'Scaffold':2,'Contig':3}
 queue=[]
 for accession in scope['deferred95_accessions']:
  item=candidates[accession];source=audit[accession];receipt_path='raw/'+accession+'/acquisition_receipt.json';receipt=read(receipt_path);assert ref(receipt_path)['sha256']==source['acquisition_receipt_sha256']
  assert source['production_disposition']=='SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN' and source['holds_or_exclusions']==[] and item['metadata_qc']=='QC_PENDING' and not item['exclusion_reasons']
  files=[x for x in receipt['files'] if x['path'].endswith('_genomic.fna') and 'cds_from' not in x['path']];assert len(files)==1 and receipt['acquisition_status']=='PASS'
  claimed=accession in excluded or item.get('paired_accession') in excluded or files[0]['sha256'] in dna.values()
  key=[0 if item['species_taxid'] in priorities else 1,family[item['family']],genus[item['genus']],item['family'].casefold(),item['genus'].casefold(),item['species_taxid'],rank.get(item['assembly_level'],4),accession]
  queue.append({'accession':accession,'species':item['species'],'species_taxid':item['species_taxid'],'family':item['family'],'genus':item['genus'],'queue_key':key,'excluded_prior_claim_or_DNA_alias':claimed,'source_pending_reasons':item['pending_reasons'],'source_masks':{'source_holds':source['holds_or_exclusions'],'source_ANI_status':item['ncbi_ani_taxonomy_status'],'independent_taxonomy':'UNRESOLVED_NOT_ACCEPTED','independent_biology':'NOT_PREDICTED_BY_PRIOR_HISTORY','source_type_assertion_not_independently_accepted':item.get('type_material',False),'production_acceptance':False},'acquisition_receipt':ref(receipt_path),'FNA_from_receipt':{'path':'raw/'+accession+'/'+files[0]['path'],'sha256':files[0]['sha256'],'bytes':files[0]['bytes']},'candidate_record':item,'source_audit_record':source})
 queue.sort(key=lambda x:x['queue_key']);representatives={}
 for x in queue:
  if x['queue_key'][0]==0 and not x['excluded_prior_claim_or_DNA_alias']:representatives.setdefault(x['species_taxid'],x['accession'])
 for x in queue:x['queue_key']=[0 if representatives.get(x['species_taxid'])==x['accession'] else 1,*x['queue_key'][1:]]
 queue.sort(key=lambda x:x['queue_key']);eligible=[x for x in queue if x['queue_key'][0]==0 and not x['excluded_prior_claim_or_DNA_alias']];assert eligible
 selected=eligible[0];old_selected=read('metadata/checkm2_phase_separated_selected_input_N1.json')
 if selected['accession']!=old_selected['input']['accession']:raise RuntimeError('Corrected queue changes sole selected input; Root must approve alternative before another FNA read')
 qref=write('metadata/checkm2_phase_separated_queue_N1_v002.json',{'schema':'TREE2_N1_IMMUTABLE_QUEUE_V001','scope_authority':ref(authority),'history':history,'source_snapshots':[ref(x) for x in ('qc/source_provenance_audit.json','metadata/candidates_qc.json','metadata/provisional_panel.json','metadata/checkm2_post_benchmark_qc_scope_addendum_v002.json','analysis/sequence_qc/d64e016face251f1/input_manifest.json')],'accepted_measurement_counts_family':dict(family),'accepted_measurement_counts_genus':dict(genus),'assembly_preference':rank,'queue_count':len(queue),'priority_labels':92,'rows':queue,'selected_one_accession':selected['accession'],'no_other_input_checksum_or_staging':True,'first_novel_representative_per_label_before_extra_strains':True,'novel_priority_representatives':len(representatives)})
 actual=old_selected['actual_selected_FNA'];assert actual==selected['FNA_from_receipt'] # exactly one authorized local FNA integrity read; no sequence parsing
 output=write('metadata/checkm2_phase_separated_selected_input_N1_v002.json',{'schema':'TREE2_N1_ONE_SELECTED_INPUT_V001','status':'SELECTED_INTEGRITY_BOUND_NO_SCIENTIFIC_EXECUTION','scope_authority':ref(authority),'history':history,'queue':qref,'input':selected,'actual_selected_FNA':actual,'exactly_one_selected_genome':True,'models_annotation_search_or_scientific_probe_executed':False,'scientific_admission':None})
 print(json.dumps({'history':history,'queue':qref,'selected_input':output,'accession':selected['accession'],'family':selected['family'],'genus':selected['genus']}))
if __name__=='__main__':main()
