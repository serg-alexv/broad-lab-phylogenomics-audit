"""File-only external closure/finalization; cannot dispatch science or resume."""
import datetime,time
import checkm2_benchmark10_common_T1 as c
def finalize(plan_path,plan_sha,external_closure):
 start=time.monotonic();plan,strategy,admission=c.plan_gate(plan_path,plan_sha);proof=c.read(c.bind(external_closure));launch=c.read(c.LAUNCH)
 execution_path=c.E/'execution_pending_owner_exit.json';execution=c.read(execution_path)
 if proof.get('status')!='BENCHMARK_PHASE_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED' or proof.get('native_owner')!=launch['native_owner']:raise RuntimeError('Actual benchmark native identity/closure absent')
 for key in ('native_exit_code_observed','wsl_exit_code_observed'):
  if type(proof.get(key)) is not int or proof[key]!=0:raise RuntimeError('Externally observed integer zero exits required')
 for key in ('owned_unit_groups_empty','ordinary_runtime_closed','image_unchanged','common_leases_reacquired_released','original_artifacts_unchanged'):
  if proof.get(key) is not True:raise RuntimeError('Actual benchmark group/image/lease closure unproved')
 if proof.get('execution_sha256')!=c.sha(execution_path) or proof.get('input_plan_sha256')!=plan_sha or proof.get('protocol_admission_sha256')!=c.sha(c.ADMISSION) or proof.get('session_identity_sha256')!=plan['session_identity_sha256']:raise RuntimeError('Current benchmark closure binding differs')
 snapshot=c.bind(proof['closed_snapshot_manifest']);c.verify_manifest(snapshot.parent,c.read(snapshot))
 if execution.get('status')!='BENCHMARK_PHASE_OUTPUTS_CLOSED_PENDING_OBSERVED_OWNER_EXIT_REVIEW' or execution.get('all_started_unit_groups_closed') is not True or execution.get('wsl_child_exit_code')!=0:raise RuntimeError('Successful current phase outputs/guest closure absent')
 pending=c.read(c.OUT/'latest_pending_native.json');run=c.path(pending['run_directory']);manifest=c.path(pending['manifest_path'])
 if not c.pending_is_current(pending,launch['token'],plan_sha,c.sha(c.ADMISSION),c.E/'namespace_runs'/(launch['token']+'.json')):raise RuntimeError('Current benchmark phase pending pointer is stale')
 if c.sha(manifest)!=pending['manifest_sha256'] or pending['input_plan_sha256']!=plan_sha:raise RuntimeError('Current run manifest/plan differs')
 c.verify_manifest(run,c.read(manifest))
 if not c.group_receipts_closed(run):raise RuntimeError('Current invocation terminal receipts incomplete')
 result=c.read(run/'result.json');phase=admission['phase']
 if result['protocol_admission_sha256']!=c.sha(c.ADMISSION):raise RuntimeError('Different admitted benchmark phase')
 if phase=='BOUNDARY_AFTER_FIRST_ANNOTATION':
  members=result['annotation_members']
  if len(members)!=1 or result.get('batch_prediction_invoked') is not False or any(x['reused'] for x in result['reused']):raise RuntimeError('First validated boundary demonstration not established')
  status='BENCHMARK_FIRST_COMMIT_BOUNDARY_CLOSED_RESUME_HELD';stage='PENDING_BENCHMARK_RESUME'
 else:
  batch=result['batch'];members=batch['annotation_members'];features=c.read(c.bind(batch['feature_validation']))
  if features.get('status')!='BENCHMARK10_FEATURES_V002_PASS_PENDING_NATIVE_CLOSURE' or features.get('row_count')!=10 or features.get('dataframe_shape')!=[10,21242] or sorted(features.get('validated_accessions',[]))!=sorted(x['accession'] for x in strategy['inputs']):raise RuntimeError('Complete exact-ten cohort validation absent')
  if sorted(features.get('source_hold_accessions_preserved',[]))!=sorted(strategy['cohort_summary']['ancillary_metadata_hold_accessions']):raise RuntimeError('Ancillary holds lost')
  status='BENCHMARK10_METHOD_RESOURCE_DIAGNOSTIC_PASS_CLOSED';stage='PENDING_COHORT_REVIEW'
 commit_hashes={x['accession']:c.sha(c.bind(x['annotation_commit'])) for x in members}
 tokens={launch['token']}
 if phase!='BOUNDARY_AFTER_FIRST_ANNOTATION':tokens.update(c.resume_proof(admission,plan['session_identity_sha256'])['closed_native_launch_tokens'])
 authority={**proof,'closed_native_launch_tokens':sorted(tokens),'annotation_commit_sha256s':commit_hashes,'phase':phase,'external_closure':external_closure,'status':'BENCHMARK_PHASE_NATIVE_GROUP_NAMESPACE_IMAGE_LEASE_CLOSED','continuation_or_validation_execution_authorized':False,'production_panel_acceptance':False,'validation_budget_bindings':[]}
 if phase!='BOUNDARY_AFTER_FIRST_ANNOTATION':
  authority['prediction_commit_sha256']=batch['prediction_commit']['sha256'];authority['committed_prediction_exit0_group_closed']=True
  batch_folder=c.bind(batch['prediction_commit']).parent
  ledger=set(batch_folder.glob('validation_*_budget.json'))|set(batch_folder.glob('validation_*/execution.json'));authority['validation_budget_bindings']=[c.row(p) for p in sorted(ledger)]
 destination=c.E/'closed_phases'/c.sha(c.ADMISSION);destination.mkdir(parents=True,exist_ok=False)
 c.save(destination/'resume_authority.json',authority)
 output={'status':status,'phase':phase,'input_plan_sha256':plan_sha,'result':c.row(run/'result.json'),'external_closure':external_closure,'resume_authority':c.row(destination/'resume_authority.json'),'annotation_commit_sha256s':commit_hashes,'all3_ancillary_holds_preserved':True,'source_scores_are_context_only':True,'production_or_full_panel_acceptance':False,'operational_recovery_policy':plan['operational_recovery_policy'],'historical_unknown_annotation_debit_seconds':600,'new_session_annotation_ceiling_seconds':5400,'actual_boundary_stop_resume_demonstrated':False,'boundary_note':'First boundary closure alone is not a demonstrated continuation. Root must admit a separate CONTINUE phase and verify first accession reused without another gene call.'}
 if phase=='CONTINUE':
  prior=c.resume_proof(admission,plan['session_identity_sha256']);first=strategy['inputs'][0]['accession'];invocations=c.read(run/'invocations.json')
  output['actual_boundary_stop_resume_demonstrated']=(prior.get('phase')=='BOUNDARY_AFTER_FIRST_ANNOTATION' and result['reused'][0]=={'accession':first,'reused':True} and not any('/annotations/'+first+'/' in str(p).replace('\\','/') for p in invocations))
 if time.monotonic()-start>600:raise TimeoutError('External file-only benchmark close exceeded600s')
 c.save(destination/'diagnostic.json',output);c.save(c.OUT/'latest_closed_phase.json',c.row(destination/'diagnostic.json'))
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();progress={'status':stage,'detail':status+'; further work requires separate root review/admission','done':len(members),'total':10,'unit':'benchmark annotation commits','updated_utc':now,'operation':'BENCHMARK10_CLOSED_DIAGNOSTIC','diagnostic':c.row(destination/'diagnostic.json'),'source_holds_preserved':True,'production_panel_acceptance':False,'pid':None,'creation_time_utc':None}
 c.save(c.STATE,progress);c.save(c.R/'state/stages/04.json',{'id':'04','name':'Independent biological QC',**progress})
 return output
