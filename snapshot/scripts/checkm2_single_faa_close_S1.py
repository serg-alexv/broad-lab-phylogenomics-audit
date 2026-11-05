"""File-only external S1 aggregation. Never dispatches inference or annotations."""
import datetime,time
import checkm2_single_faa_common_S1 as c

def finalize(plan_path,plan_sha,external_closure):
 start=time.monotonic();plan,cohort,admission=c.plan_gate(plan_path,plan_sha,closed_finalization=True);proof=c.read(c.bind(external_closure));launch=c.read(c.LAUNCH);execution_path=c.E/'execution_pending_owner_exit.json';execution=c.read(execution_path)
 if proof.get('status')!='S1_ROW_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('native_owner')!=launch['native_owner']:raise RuntimeError('Actual S1 native identity/closure absent')
 if any(type(proof.get(k)) is not int or proof[k]!=0 for k in ('native_exit_code_observed','wsl_exit_code_observed')):raise RuntimeError('Externally observed genuine S1 native/WSL zero exits required')
 if any(proof.get(k) is not True for k in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged')):raise RuntimeError('Actual S1 child/context/image/lease closure incomplete')
 if proof.get('execution_sha256')!=c.sha(execution_path) or proof.get('input_plan_sha256')!=plan_sha or proof.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or proof.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('S1 current closure/source binding differs')
 snapshot=c.bind(proof['closed_snapshot_manifest']);c.verify_manifest(snapshot.parent,c.read(snapshot))
 if execution.get('status')!='S1_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW' or execution.get('all_started_unit_groups_closed') is not True or execution.get('wsl_child_exit_code')!=0:raise RuntimeError('S1 current outputs/guest closure unproved')
 pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);manifest=c.path(pending['manifest_path'])
 if not c.pending_is_current(pending,launch['token'],plan_sha,c.sha(c.ADMISSION),c.E/'namespace_runs'/(launch['token']+'.json')) or c.sha(manifest)!=pending['manifest_sha256']:raise RuntimeError('S1 current pointer/manifest is stale')
 c.verify_manifest(run,c.read(manifest));result=c.read(run/'result.json')
 if result.get('status')!='S1_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE' or result.get('annotation_functions_invoked') is not False or result.get('maximum_query_genomes_per_prediction')!=1 or result.get('protocol_admission_sha256')!=c.sha(c.ADMISSION):raise RuntimeError('S1 inference-only current result differs')
 rows=result.get('rows',[]);expected={x['accession']:x for x in cohort['inputs']}
 if len(rows)!=10 or {x['accession'] for x in rows}!=set(expected):raise RuntimeError('Ten distinct S1 rows required; no synthetic batch result')
 quality_paths=set();validation_paths=set();feature_paths=set();summary=[];row_map={};holds=[]
 for member in rows:
  acc=member['accession'];p=c.bind(member['commit']);commit=c.read(p)
  if p!=c.OUT/'sessions'/plan['session_identity_sha256']/'rows'/acc/'commit.json' or commit.get('status')!='SINGLE_FAA_EXIT0_FEATURES_VALIDATED_PENDING_NATIVE_CLOSURE':raise RuntimeError('S1 exact per-genome commit absent')
  c.verify_manifest(p.parent,c.read(c.bind(commit['manifest'])))
  for k,seen in [('quality_unit_execution',quality_paths),('validation_unit_execution',validation_paths)]:
   q=c.bind(commit[k]);seen.add(q)
   if not c.unit_closed(c.read(q)):raise RuntimeError('S1 genuine unit exit0/group receipt required')
  f=c.bind(commit['feature_validation']);feature_paths.add(f);features=c.read(f)
  if features.get('status')!='SINGLE_FAA_FEATURES_S1_PASS_PENDING_NATIVE_CLOSURE' or features.get('row_count')!=1 or features.get('accession')!=acc or features.get('finite_domain_features')!=21241 or features.get('exact_FAA_metadata_features')!=22 or features.get('independently_recomputed_membership_features')!=1220 or features.get('membership_mismatches')!=0:raise RuntimeError('Own exact S1 row/feature math validation required')
  if features.get('source_holds_preserved')!=expected[acc]['source_holds_preserved'] or features.get('input_plan_sha256')!=plan_sha or features.get('source_manifest_sha256')!=plan['source_manifest']['sha256'] or features.get('cohort_contract_sha256')!=plan['cohort_contract']['sha256']:raise RuntimeError('S1 source/cohort/hold bindings changed')
  if features['source_holds_preserved']:holds.append(acc)
  row_map[acc]=features['canonical_float64_le_row_sha256'];summary.append({'accession':acc,'Completeness':features['Completeness'],'Contamination':features['Contamination'],'source_holds_preserved':features['source_holds_preserved'],'feature_validation':commit['feature_validation'],'quality_unit_execution':commit['quality_unit_execution'],'validation_unit_execution':commit['validation_unit_execution'],'commit':member['commit'],'production_acceptance':'NOT_GRANTED'})
 if len(quality_paths)!=10 or len(validation_paths)!=10 or len(feature_paths)!=10 or sorted(holds)!=sorted(cohort['expected_source_hold_accessions']):raise RuntimeError('Ten distinct prediction+validation receipts or source-hold coverage absent')
 session=c.OUT/'sessions'/plan['session_identity_sha256'];budget=c.budget(session)
 destination=c.E/'closed_phases'/c.sha(c.ADMISSION);destination.mkdir(parents=True,exist_ok=False)
 output={'status':'SINGLE_FAA_SERIES_METHOD_ESTIMATES_PASS_CLOSED','input_plan_sha256':plan_sha,'cohort_contract':plan['cohort_contract'],'annotation_reuse_authority':admission['annotation_reuse_authority'],'rows':summary,'canonical_accession_row_hashes':row_map,'finite_domain_features_total':212410,'exact_FAA_metadata_features_total':220,'independently_recomputed_membership_features_total':12200,'membership_mismatches':0,'budget':budget,'external_closure':external_closure,'prediction_genomes_per_call':1,'original_ten_genome_batch_resource_benchmark_passed':False,'annotation_functions_invoked':False,'source_taxonomy_or_production_panel_acceptance':False}
 if time.monotonic()-start>600:raise TimeoutError('S1 external file-only aggregation exceeded600s')
 c.save(destination/'cohort_measurements.json',output)
 authority={**proof,'status':'S1_ROW_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED','accepted_row_commit_sha256s':{x['accession']:x['commit']['sha256'] for x in rows},'closed_native_launch_tokens':sorted({c.read(c.bind(x['commit']))['native_launch_token'] for x in rows}), 'budget_bindings':[c.row(p) for p in sorted(c.budget_files(session))],'continuation_execution_authorized':False,'production_panel_acceptance':False}
 c.save(destination/'closed_row_authority.json',authority);c.save(c.OUT/'latest_closed_series.json',c.row(destination/'cohort_measurements.json'))
 progress={'status':'PENDING_SOURCE_TAXONOMY_AND_COHORT_QC','detail':'Ten single-FAA method estimates closed; original ten-query batch failed resources; whole-panel/source/taxonomy acceptance pending','done':10,'total':10,'unit':'validated single-FAA QC commits','updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operation':'SINGLE_FAA_S1_CLOSED','diagnostic':c.row(destination/'cohort_measurements.json'),'production_panel_acceptance':False,'pid':None,'creation_time_utc':None}
 c.save(c.STATE,progress);c.save(c.R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**progress});return output
