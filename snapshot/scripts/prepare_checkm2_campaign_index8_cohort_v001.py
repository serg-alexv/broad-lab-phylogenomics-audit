"""Metadata-only data-plan factory. Never launches tools, reads genomes or admits science."""
from pathlib import Path
import argparse,hashlib,json,uuid,os,re
import checkm2_campaign_index8_common_v001 as c

def create(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 temporary=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 try:
  with temporary.open('x',encoding='utf-8',newline='\n')as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(temporary,p) # Atomic create, no overwrite of an existing immutable plan.
 finally:
  if temporary.exists():temporary.unlink()
 return c.row(p)

def materialize(args):
 authority=c.read(c.bind(c.row(c.path(args.cohort_authority))))
 mode=authority['mode'];qualification=c.row(c.path(args.qualification_acceptance))if args.qualification_acceptance else None
 conditional=c.row(c.path(args.conditional_method_authority))if args.conditional_method_authority else None
 if mode=='CLOSED_INDEX8_PROFILE':c.qualification_gate(qualification)
 elif mode!='CONDITIONAL_INDEX8_PROMOTION' or conditional is None:raise RuntimeError('Explicit conditional or closed-profile authority required')
 context_ref=c.row(c.path(args.queue_launch_context));context=c.read(c.bind(context_ref));queue_ref=context['canonical_QC_queue'];queue=c.read(c.bind(queue_ref));members={x['queue_id']:x for x in queue['rows']}
 registry=c.row(c.path(args.accepted_registry));accepted=c.accepted_gate(registry)
 
 if mode=='CLOSED_INDEX8_PROFILE':c.qualification_registry_gate(c.qualification_gate(qualification),registry)
 names=authority['accessions'];remaining=[n for n in context['queue_ids']if n not in accepted]
 if authority['status']!='ROOT_APPROVED_CAMPAIGN_INDEX8_COHORT_SELECTION_AND_BUDGET' or not 1<=len(names)<=20 or names!=remaining[:len(names)]:raise RuntimeError('Root current ordered cohort authority required')
 inputs=[]
 for name in names:
  q=members[name]
  if q['source_supported_scope']is not True or q['qc_execution_state']not in('READY_FRESH_QC','RESERVED_P20_UNSTARTED')or set(q['paired_accessions'])&accepted:raise RuntimeError('Only exact source-supported unstarted queue members may be materialized')
  inputs.append({**q,'canonical_queue_row':q,'fasta_path':q['FNA_from_receipt']['path'],'fasta_sha256':q['FNA_from_receipt']['sha256'],'fasta_bytes':q['FNA_from_receipt']['bytes'],'role':'FRESH_CANONICAL_QUEUE_MEMBER','selection_status':q['qc_execution_state'],'source_disposition':q['source_eligibility'],'source_taxonomy_gates':c.canonical_source_masks(q),'source_masks':c.canonical_source_masks(q)})
 cohort=authority['cohort_id']
 if not isinstance(cohort,str)or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',cohort):raise RuntimeError('Invalid contained cohort identifier')
 destination=c.R/'metadata/checkm2_campaign_index8_v001'/cohort
 selected=create(destination/'selected_inputs.json',{'schema':'TREE2_CAMPAIGN_OWN_SELECTED_INPUTS_V001','canonical_queue':queue_ref,'queue_launch_context':context_ref,'inputs':inputs,'no_FNA_bytes_read_by_factory':True})
 plan={'schema':'TREE2_CAMPAIGN_INDEX8_INPUT_PLAN_V001','role':c.ROLE,'cohort_id':cohort,'accessions':names,'limits':authority['limits'],'source_manifest':c.row(c.path(args.source_manifest)),'scientific_recipe':c.row(c.R/'metadata/checkm2_phase_separated_recipe_P20.json'),'feature_schema':c.row(c.R/'metadata/checkm2_feature_schema_v002.json'),'selected_inputs':selected,'canonical_queue':queue_ref,'queue_launch_context':context_ref,'accepted_registry':registry,'search_only_control':authority.get('search_only_control'),'mode':mode,'qualification_acceptance':qualification,'conditional_method_authority':conditional,'annotation_reuse_by_accession':authority.get('annotation_reuse_by_accession',{}),'method_amendment':c.row(c.path(args.method_amendment)),'cohort_authority':c.row(c.path(args.cohort_authority)),'prior_debit_artifacts':authority['prior_debit_artifacts'],'carried_cold_ceiling_seconds':authority.get('carried_cold_ceiling_seconds'),'session_identity_sha256':hashlib.sha256((cohort+'|'+selected['sha256']+'|'+authority['queue_proposal_sha256']).encode()).hexdigest(),'source_eligibility_is_biological_PASS':False,'scientific_execution_authorized':False}
 ref=create(destination/'input_plan.json',plan)
 c.plan_gate(c.bind(ref),ref['sha256'],require_admission=False)
 return ref
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in('cohort-authority','queue-launch-context','accepted-registry','source-manifest','method-amendment'):p.add_argument('--'+name,required=True)
 p.add_argument('--qualification-acceptance');p.add_argument('--conditional-method-authority')
 print(json.dumps(materialize(p.parse_args())))
