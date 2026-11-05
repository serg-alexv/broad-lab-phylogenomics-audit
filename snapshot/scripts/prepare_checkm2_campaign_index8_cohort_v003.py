"""HELD metadata-only shared-profile data factory; not a search/model/queue dispatcher."""
from pathlib import Path
import argparse,hashlib,json,os,re,uuid
import checkm2_campaign_index8_common_v003 as c

def create(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 try:
  with temp.open('x',encoding='utf-8')as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(temp,path)
 finally:
  if temp.exists():temp.unlink()
 return c.row(path)

def materialize(a):
 authority_ref=c.row(c.path(a.cohort_authority));authority=c.read(c.bind(authority_ref));context_ref=c.row(c.path(a.queue_launch_context));context=c.read(c.bind(context_ref));queue_ref=context['canonical_QC_queue'];queue=c.read(c.bind(queue_ref));members={x['accession']:x for x in queue['rows']};registry=c.row(c.path(a.accepted_registry));accepted=c.accepted_gate(registry)
 names=authority['accessions'];remaining=[x for x in context['queue_ids']if x not in accepted];controls=authority['controls'];cohort=authority['cohort_id']
 if authority['status']!='ROOT_APPROVED_ONE_FUTURE_SHARED_INDEX8_COHORT'or not 1<=len(names)<=20 or not 1<=len(controls)<=2 or names!=remaining[:len(names)]or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',cohort):raise RuntimeError('Exact disjoint future Root queue/profile authority required')
 inputs=[]
 for acc in names:
  q=members[acc]
  if q['source_supported_scope']is not True or q['qc_execution_state']not in('READY_FRESH_QC','RESERVED_P20_UNSTARTED')or set(q['paired_accessions'])&accepted:raise RuntimeError('Source-held/accepted/historical input cannot run fresh')
  inputs.append({**q,'canonical_queue_row':q,'fasta_path':q['FNA_from_receipt']['path'],'fasta_sha256':q['FNA_from_receipt']['sha256'],'fasta_bytes':q['FNA_from_receipt']['bytes'],'source_masks':c.canonical_source_masks(q),'role':'FRESH_SHARED_QUERY_COHORT','selection_status':q['qc_execution_state'],'source_disposition':q['source_eligibility'],'source_taxonomy_gates':q['source_masks']})
 destination=c.R/'metadata/checkm2_campaign_index8_v003'/cohort;selected=create(destination/'selected_inputs.json',{'schema':'TREE2_SHARED_PROFILE_SELECTED_INPUTS_V003','inputs':inputs,'canonical_queue':queue_ref,'no_FNA_contents_read':True});template=c.row(c.R/'metadata/checkm2_phase_separated_recipe_P20.json')
 plan={'schema':'TREE2_CAMPAIGN_SHARED_INDEX8_INPUT_PLAN_V003','role':c.ROLE,'cohort_id':cohort,'accessions':names,'controls':controls,'limits':authority['limits'],'source_manifest':c.row(c.path(a.source_manifest)),'scientific_recipe':template,'runtime_binding':c.read(c.bind(template))['runtime_binding'],'feature_schema':c.row(c.R/'metadata/checkm2_feature_schema_v002.json'),'selected_inputs':selected,'canonical_queue':queue_ref,'queue_launch_context':context_ref,'accepted_registry':registry,'serial_index8_baseline_acceptance':c.row(c.path(a.serial_index8_baseline_acceptance)),'method_amendment':c.row(c.path(a.method_amendment)),'cohort_authority':authority_ref,'prior_debit_artifacts':authority['prior_debit_artifacts'],'annotation_reuse_by_accession':authority.get('annotation_reuse_by_accession',{}),'session_identity_sha256':hashlib.sha256((cohort+'|'+selected['sha256']+'|'+authority_ref['sha256']).encode()).hexdigest(),'scientific_execution_authorized':False}
 ref=create(destination/'input_plan.json',plan);c.plan_gate(c.bind(ref),ref['sha256'],require_admission=False);return ref
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in('cohort-authority','queue-launch-context','accepted-registry','source-manifest','serial-index8-baseline-acceptance','method-amendment'):p.add_argument('--'+name,required=True)
 print(materialize(p.parse_args()))
