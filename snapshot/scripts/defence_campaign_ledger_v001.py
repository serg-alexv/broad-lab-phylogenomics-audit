"""File-only closed protein-scope ledger; no science dispatch or retry authority."""
from pathlib import Path
import copy,collections,uuid
import local_tree2_dispatcher as b

def selected_next(ledger,rows,limit=20):
 groups={}
 for row in sorted(rows,key=lambda value:value['position']):
  if ledger['entries'][row['accession']]['state']=='NOT_RUN_UNKNOWN':groups.setdefault(row['family'],[]).append(row['accession'])
 selected=[]
 while len(selected)<limit and any(groups.values()):
  for family in sorted(groups):
   if groups[family]:selected.append(groups[family].pop(0))
   if len(selected)==limit:break
 return selected

def closed_acceptance(root,row):
 accepted=b.read(b.bind(root,row))
 assert accepted['schema']=='TREE2_CLOSED_DEFENCE_COHORT_ACCEPTANCE_V001' and accepted['status']=='ROOT_ACCEPTED_CLOSED_PROTEIN_SUPPORTED_COHORT_SCOPE_ONLY'
 assert accepted['all_native_WSL_stock_search_descendant_group_namespace_IPC_RAM_Rbinding_FD_and_fourlease_closure_verified'] and accepted['RNA51_UNKNOWN_ADF156_genericCAS_inferred154_relaxed19_crosscontig_repeated_roles_preserved']
 exit=b.read(b.bind(root,accepted['QA_native_actual_exit']));assert exit['actual_exit_code']==0 and exit['exact_birth_handle_retained']
 result=b.read(b.bind(root,accepted['QA_commit']));assert result['every_saved_file_independently_posthashed_again'] and result['actual0_stock_phases']==2*accepted['genomes']
 assert result['native_owner']['pid']==exit['worker_identity']['pid'] and result['native_owner']['windows_creation_filetime_100ns']==exit['worker_identity']['windows_creation_filetime_100ns'] and result['native_owner']['creation_time_utc']==exit['worker_identity']['creation_time_utc']
 b.bind(root,accepted['science_whole_closure']);b.bind(root,accepted['fresh_all_captured_births_closure']);assert b.read(b.bind(root,accepted['fresh_closure_actual_exit']))['actual_exit_code']==0
 science=b.read(b.bind(root,accepted['source_plan']));rows=b.read(b.bind(root,accepted['validated_rows']))['rows'];ids={value['accession'] for value in rows}
 assert len(ids)==len(rows)==accepted['genomes'] and ids==set(accepted['selected_accessions'])==set(science['selected_accessions'])
 assert accepted['source_queue']==science['queue'] and accepted['reservation']==science['reservation']
 assert abs(sum(engine['stock0_seconds'] for value in rows for engine in value['engines'].values())-accepted['scientific_seconds'])<1e-6
 return accepted,rows

def close(root,acceptance_row):
 directory=root/'state/defence_campaign_v001';path=directory/'ledger.json'
 with b.ByteLock(directory/'ledger_transaction.lock'):
  before=b.row(root,path);ledger=b.read(path);accepted,validated=closed_acceptance(root,acceptance_row);cohort=accepted['cohort_id']
  assert ledger['status']=='ACTIVE_RESERVED_COHORT' and ledger['cohort_id']==cohort and ledger['reservation']==accepted['reservation'] and cohort not in ledger.get('cohort_costs',{})
  reservation=b.read(b.bind(root,ledger['reservation']));assert set(reservation['selected_accessions'])==set(accepted['selected_accessions']) and ledger['source_queue']==accepted['source_queue']
  queue=b.read(b.bind(root,ledger['source_queue']));ids={value['accession'] for value in queue['rows']};assert set(ledger['entries'])==ids and len(ids)==919
  for value in validated:
   entry=ledger['entries'][value['accession']];assert entry['state']=='RESERVED' and entry['cohort_id']==cohort
   ledger['entries'][value['accession']]={'state':'CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED','cohort_id':cohort,'acceptance':acceptance_row,'original_source_masks_unchanged':True,'RNA_unavailable_models':'UNKNOWN_NOT_NEGATIVE','final_QC_taxonomy_panel_or_ring_acceptance':False}
  ledger.setdefault('cohort_costs',{})[cohort]={'scientific_seconds':accepted['scientific_seconds'],'cold_seconds':accepted['cold_seconds'],'file_QA_wall_seconds_separate':accepted['file_QA_wall_seconds_separate'],'acceptance':acceptance_row}
  ledger['known_cumulative_defence_scientific_seconds']=ledger['known_prior_defence_scientific_seconds']+sum(value['scientific_seconds'] for value in ledger['cohort_costs'].values())
  ledger['known_cumulative_defence_cold_seconds']=ledger['known_prior_defence_cold_seconds']+sum(value['cold_seconds'] for value in ledger['cohort_costs'].values())
  ledger['known_closed_cohort_file_QA_wall_seconds_separate']=sum(value['file_QA_wall_seconds_separate'] for value in ledger['cohort_costs'].values())
  nextids=selected_next(ledger,queue['rows']);nextcohort='C'+str(int(cohort[1:])+1).zfill(3)
  if nextids:
   byacc={value['accession']:value for value in queue['rows']}
   new={'schema':'TREE2_DEFENCE_IMMUTABLE_COHORT_RESERVATION_V001','status':'RESERVED_NOVEL_INPUTS_NOT_YET_SCIENTIFICALLY_ADMITTED','cohort_id':nextcohort,'source_queue':ledger['source_queue'],'source_population':919,'selected_accessions':nextids,'selection':'Round-robin source-family queues in frozen position order; onlyNOT_RUN_UNKNOWN, no accepted/failed/consumed/reserved replay','selected_family_counts':dict(collections.Counter(byacc[value]['family'] for value in nextids)),'prior_closed_acceptance':acceptance_row,'all_holds_preserved':True,'scientific_admission_still_required':True,'at_utc':b.utc()}
   reservation_path=directory/'reservations'/(nextcohort+'.json');b.exclusive(reservation_path,new);nextrow=b.row(root,reservation_path)
   for accession in nextids:assert ledger['entries'][accession]['state']=='NOT_RUN_UNKNOWN';ledger['entries'][accession]={'state':'RESERVED','cohort_id':nextcohort,'reservation':nextrow}
   ledger.update(status='ACTIVE_RESERVED_COHORT',cohort_id=nextcohort,reservation=nextrow)
  else:ledger.update(status='PENDING_FINALIZE_NOT_EXHAUSTED',cohort_id=None,reservation=None)
  archive=directory/'snapshots'/(before['sha256']+'.json')
  if not archive.exists():archive.parent.mkdir(exist_ok=True);archive.write_bytes(path.read_bytes())
  assert b.digest(archive)==before['sha256']
  ledger.update(revision='CLOSE_'+cohort+'_'+uuid.uuid4().hex,closed_paired_protein_scope_genomes=sum(value['state']=='CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED' for value in ledger['entries'].values()),not_exhausted=True,at_utc=b.utc())
  b.atomic(path,ledger)
  receipt={'schema':'TREE2_DEFENCE_LEDGER_CLOSED_COHORT_TRANSACTION_V001','closed_cohort':cohort,'acceptance':acceptance_row,'previous_ledger':b.row(root,archive),'updated_ledger_observation':b.row(root,path),'closed_paired_protein_scope_genomes':ledger['closed_paired_protein_scope_genomes'],'automatic_next_reservation':ledger['reservation'],'known_cumulative_scientific_seconds':ledger['known_cumulative_defence_scientific_seconds'],'complete_system_rings_or_final_tree_acceptance':False,'not_exhausted_until_finalize':True,'at_utc':b.utc()}
  b.exclusive(directory/'closed_transactions'/(cohort+'.json'),receipt);return receipt

def finalize(root):
 directory=root/'state/defence_campaign_v001';path=directory/'ledger.json'
 with b.ByteLock(directory/'ledger_transaction.lock'):
  ledger=b.read(path);queue=b.read(b.bind(root,ledger['source_queue']));ids={value['accession'] for value in queue['rows']}
  assert len(ids)==919 and set(ledger['entries'])==ids and all(value['state']=='CLOSED_PAIRED_PROTEIN_SCOPE_ACCEPTED' for value in ledger['entries'].values()),'Every eligible queue member must have a closed disposition; queue is not exhausted'
  checked={};baseline=None
  for accession,entry in ledger['entries'].items():
   row=entry['acceptance'];key=row['sha256']
   if key not in checked:
    a=b.read(b.bind(root,row))
    if a.get('cohort_id'):
     a,values=closed_acceptance(root,row);members={value['accession'] for value in values}
    else:
     assert a['status']=='ROOT_ACCEPTED_CLOSED_FIVE_GENOME_PROTEIN_DEFENCE_PILOT_ONLY' and a['all_captured_children_groups_private_mount_IPC_RAM_Rbinding_FDs_closed'];a_result=b.read(b.bind(root,a['source_result']));members=set(a_result['selected_accessions'])
    science=b.read(b.bind(root,a['source_plan']));signature=(science['queue']['sha256'],science['scope_sha256'],science['PADLOC_HMM_sha256'],science['DF_model_manifest']['sha256'])
    if baseline is None:baseline=signature
    assert signature==baseline,'Mixed source/model scopes need explicit reviewed reconciliation before finalize';checked[key]=members
   assert accession in checked[key]
  receipt={'schema':'TREE2_DEFENCE_CAMPAIGN_PROTEIN_SCOPE_FINALIZE_V001','status':'ALL919_CLOSED_PAIRED_PROTEIN_SCOPE_DISPOSITIONS_VERIFIED_RNA_UNAVAILABLE_UNKNOWN_REMAINS','ledger_observation':b.row(root,path),'queue':ledger['source_queue'],'genomes':919,'source_scope_signature':baseline,'closed_acceptance_receipts':len(checked),'not_final_biological_panel_tree_or_rings_acceptance':True,'at_utc':b.utc()}
  b.exclusive(directory/'PROTEIN_SCOPE_FINALIZED.json',receipt);return receipt
