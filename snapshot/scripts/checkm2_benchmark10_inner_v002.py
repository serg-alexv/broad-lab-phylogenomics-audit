"""HELD ten-genome workflow. Only an exact separately admitted phase can run."""
from pathlib import Path
import argparse,datetime,fcntl,json,math,os,shutil,time
import checkm2_benchmark10_common_v002 as c
import checkm2_protein_pilot_v001 as pilot
h=pilot.h;R=c.R;STEP=R/'state/checkm2_benchmark10_protein_v002_step.json';LAUNCH=None;CLOSED_TOKENS=set();COMMITTED_COUNT=0;RESUME_PROOF={}
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def progress(status,detail,done=None,**extra):
 global COMMITTED_COUNT
 if done is not None:COMMITTED_COUNT=done
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc']} if LAUNCH else {}
 c.save(STEP,{'status':status,'detail':detail,'done':COMMITTED_COUNT,'total':10,'unit':'benchmark annotation commits','updated_utc':utc(),'operation':'BENCHMARK10','native_linux_identity':pilot.legacy.stat(os.getpid()),'production_panel_acceptance':False,**owner,**extra})
pilot.OUT=c.OUT;pilot.STATE=STEP;pilot.progress=progress;pilot.legacy.STATE=STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate
def stop(*args,**kwargs):
 c.stop()
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('Benchmark phase admission changed during owned execution')
 return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop
def invoke(name,command,env,folder,run,seconds):
 index=c.read(run/'invocations.json');index.append(str(folder/name));c.save(run/'invocations.json',index)
 return pilot.run_unit(name,command,env,folder,seconds)
def annotation_binding(item,runtime,plan):
 return {'input':item,'source_manifest_sha256':plan['source_manifest']['sha256'],'session_identity_sha256':plan['session_identity_sha256'],'image_sha256':runtime['ready']['runtime_image']['sha256'],'effective_runtime_manifest_sha256':runtime['effective_runtime']['manifest_sha256'],'caller_source_sha256':plan['original_prodigal_source_sha256'],'prodigal_program_sha256':runtime['tools']['prodigal']['sha256'],'automatic_original_table_selection':True}
def committed_annotation(folder,binding):
 if not (folder/'commit.json').exists():raise RuntimeError('Partial/uncommitted annotation preserved; no automatic retry:'+str(folder))
 if c.sha(folder/'commit.json')!=RESUME_PROOF.get('annotation_commit_sha256s',{}).get(binding['input']['accession']):raise RuntimeError('Committed annotation is not hash-bound by actual prior closed-phase authority')
 commit=c.read(folder/'commit.json')
 if commit.get('status')!='ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT' or commit.get('binding')!=binding:raise RuntimeError('Annotation checkpoint binding differs; do not recompute')
 if commit.get('native_launch_token') not in CLOSED_TOKENS|{LAUNCH['token']}:raise RuntimeError('Annotation native launch closure not covered by current resume authority')
 c.verify_manifest(folder,c.read(c.bind(commit['manifest'])))
 if not c.unit_closed(c.read(folder/'unit_annotation/execution.json')):raise RuntimeError('Annotation terminal exit/group closure absent')
 receipt=c.read(c.bind(commit['annotation_receipt']));c.bind(commit['selected_faa'])
 if receipt['faa_sha256']!=commit['selected_faa']['sha256']:raise RuntimeError('Annotation FAA binding differs')
 return commit
def annotate(item,runtime,plan,session,run):
 folder=session/'annotations'/item['accession'];binding=annotation_binding(item,runtime,plan)
 if folder.exists():return committed_annotation(folder,binding),True
 source=pilot.verify_input(item);folder.mkdir(parents=True,exist_ok=False);staged=folder/(item['accession']+'.fna');shutil.copyfile(source,staged)
 if c.sha(staged)!=item['fasta_sha256']:raise RuntimeError('Staged benchmark DNA differs')
 annotation_plan={'input':{**item,'staged_fna':str(staged)},'runtime_prefix':runtime['prefix'],'original_prodigal_source_sha256':plan['original_prodigal_source_sha256'],'prodigal_program_sha256':runtime['tools']['prodigal']['sha256']}
 c.save(folder/'annotation_plan.json',annotation_plan);output=folder/'annotation'
 invoke('unit_annotation',[str(Path(runtime['prefix'])/'bin/python'),'-B',str(R/'scripts/checkm2_protein_helpers_v001.py'),'annotate','--plan',str(folder/'annotation_plan.json'),'--output',str(output)],pilot.environment(Path(runtime['prefix'])),folder,run,600)
 receipt=c.read(output/'annotation_receipt.json');faa=c.path(receipt['faa_path'])
 if receipt['status']!='ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or receipt['accession']!=item['accession'] or c.sha(faa)!=receipt['faa_sha256'] or receipt['ML_modules_loaded']!=[]:raise RuntimeError('Original annotation/FAA checkpoint invalid')
 if h.validate_author_return(receipt['all10_original_return_values'],item['accession'])!=receipt['original_measurements']:raise RuntimeError('Original ten values/sidecar differ')
 parsed=h.parse_fasta(faa.read_text(),h.AA)
 if h.sequence_receipt(parsed)!=receipt['protein_sequences']:raise RuntimeError('FAA ordered sequence receipt differs')
 commit={'status':'ANNOTATION_EXIT0_VALIDATED_ATOMIC_COMMIT','binding':binding,'annotation_receipt':c.row(output/'annotation_receipt.json'),'selected_faa':c.row(faa),'unit_execution':c.row(folder/'unit_annotation/execution.json'),'native_launch_token':LAUNCH['token'],'protocol_admission_sha256':c.sha(c.ADMISSION),'manifest':c.manifest(folder),'production_acceptance':'NOT_GRANTED'}
 c.save(folder/'commit.json',commit);return commit,False
def batch(plan,strategy,runtime,session,run,members,phase):
 folder=session/'batch';prefix=Path(runtime['prefix']);env=pilot.environment(prefix);validation_phase_start=time.monotonic();started=None
 if phase=='VALIDATE_COMMITTED_BATCH':
  if c.sha(folder/'prediction_commit.json')!=RESUME_PROOF.get('prediction_commit_sha256'):raise RuntimeError('Prediction checkpoint is not bound to prior actual native closure')
  committed=c.read(folder/'prediction_commit.json');c.verify_manifest(folder,c.read(c.bind(committed['manifest'])))
  if not c.unit_closed(c.read(c.bind(committed['quality_unit_execution']))):raise RuntimeError('Preserved prediction terminal/group proof absent')
  if committed.get('native_launch_token') not in CLOSED_TOKENS:raise RuntimeError('Preserved prediction native closure absent from resume authority')
  elapsed=committed['elapsed_quality_seconds'];quality=c.path(committed['quality_output'])
  c.verify_budget_set(folder,RESUME_PROOF['validation_budget_bindings'])
 else:
  folder.mkdir(exist_ok=False)
  with (session/'batch_once_claim.json').open('x') as f:json.dump({'input_plan_sha256':plan['_sha'],'protocol_admission_sha256':c.sha(c.ADMISSION),'native_launch_token':LAUNCH['token']},f);f.flush();os.fsync(f.fileno())
  inputs=folder/'protein_input';inputs.mkdir()
  for member in members:
   source=c.bind(member['selected_faa']);destination=inputs/(member['accession']+'.faa');shutil.copyfile(source,destination)
   if c.sha(destination)!=member['selected_faa']['sha256']:raise RuntimeError('Benchmark staged FAA changed')
  quality=folder/'quality_output';tmp=folder/'durable_tmp';tmp.mkdir();route=runtime['ipc_routing'];env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(folder/'effective_import_origins.json')
  command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(folder/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--input',str(inputs),'--output-directory',str(quality),'--tmpdir',str(tmp),'--database_path',runtime['database_path'],'--dbg_vectors','--debug']
  started=time.monotonic();execute=invoke('unit_batch_quality',command,env,folder,run,3600);elapsed=time.monotonic()-started
  committed={'status':'BATCH_EXIT0_RAW_OUTPUTS_COMMITTED_VALIDATION_PENDING','input_plan_sha256':plan['_sha'],'quality_output':str(quality),'quality_unit_execution':c.row(folder/'unit_batch_quality/execution.json'),'elapsed_quality_seconds':elapsed,'raw_pickle':c.row(quality/'feature_vectors_1.pkl'),'quality_report':c.row(quality/'quality_report.tsv'),'manifest':c.manifest(folder),'native_launch_token':LAUNCH['token']};committed['elapsed_quality_seconds']=time.monotonic()-started;c.save(folder/'prediction_commit.json',committed);elapsed=committed['elapsed_quality_seconds']
 for previous in sorted(folder.glob('validation_*_budget.json')):
  budget=c.read(previous);terminal=folder/budget['unit']/'execution.json'
  if not terminal.exists():raise RuntimeError('Prior validation elapsed/closure UNKNOWN; no budget reset or automatic continuation')
  execution=c.read(terminal)
  if execution.get('owned_group_empty') is not True:raise RuntimeError('Prior validation group closure unproved')
  debit=float(budget['debit_before_start_seconds']);spent=float(execution['elapsed_seconds'])
  if not math.isfinite(debit) or not math.isfinite(spent) or min(debit,spent)<0:raise RuntimeError('Validation budget debit UNKNOWN/nonfinite')
  elapsed=max(elapsed,debit+spent)
 request={'request_schema':'TREE2_BENCHMARK10_FEATURE_REQUEST_V002','recipe':plan['recipe'],'runtime_prefix':str(prefix),'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'input_plan_sha256':plan['_sha'],'schema':plan['feature_schema'],'artifacts':{'raw_pickle':committed['raw_pickle'],'quality_report':committed['quality_report'],'quality_unit_execution':committed['quality_unit_execution']},'members':members}
 attempt='validation_'+c.sha(c.ADMISSION)[:16];request_path=folder/(attempt+'_request.json');c.save(request_path,request);output=folder/(attempt+'_features.json')
 debit=time.monotonic()-started if started is not None else elapsed+(time.monotonic()-validation_phase_start)
 remaining=3600-debit
 if remaining<=0:raise TimeoutError('No remaining shared3600s validation budget')
 c.save(folder/(attempt+'_budget.json'),{'unit':attempt,'debit_before_start_seconds':debit,'remaining_seconds':remaining,'shared_seconds':3600,'protocol_admission_sha256':c.sha(c.ADMISSION)})
 invoke(attempt,[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_benchmark10_feature_validator_v002.py'),'--request',str(request_path),'--request-sha256',c.sha(request_path),'--output',str(output)],env,folder,run,remaining)
 return {'feature_validation':c.row(output),'prediction_commit':c.row(folder/'prediction_commit.json'),'quality_output':str(quality),'annotation_members':members,'production_acceptance':'NOT_GRANTED','source_holds_preserved':True}
def main(a):
 global LAUNCH,CLOSED_TOKENS,RESUME_PROOF
 plan,strategy,admission=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_sha']=a.input_plan_sha256;LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Benchmark native/plan identity differs')
 if LAUNCH.get('protocol_admission_sha256')!=c.sha(c.ADMISSION):raise RuntimeError('Benchmark phase admission changed after native launch')
 pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH
 if admission['phase']!='BOUNDARY_AFTER_FIRST_ANNOTATION':RESUME_PROOF=c.resume_proof(admission,plan['session_identity_sha256']);CLOSED_TOKENS=set(RESUME_PROOF['closed_native_launch_tokens'])
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Accepted private read-only runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/plan['session_identity_sha256'];session.mkdir(parents=True,exist_ok=True);claims=session/'phase_claims';claims.mkdir(exist_ok=True)
  with (claims/(c.sha(c.ADMISSION)+'.json')).open('x') as f:json.dump({'launch':LAUNCH,'phase':admission['phase'],'protocol_sha256':c.sha(c.ADMISSION)},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False);c.save(run/'invocations.json',[]);c.save(run/'binding.json',{'plan':plan,'runtime':runtime,'admission':c.row(c.ADMISSION),'launch':LAUNCH})
  members=[];reused=[]
  try:
   for index,raw in enumerate(strategy['inputs']):
    if admission['phase']=='VALIDATE_COMMITTED_BATCH' and not (session/'annotations'/raw['accession']/'commit.json').exists():raise RuntimeError('Validation-only cannot generate missing annotation')
    item={**raw,'source_provenance_audit_sha256':strategy['original_source_metadata_hashes']['qc/source_provenance_audit.json'],'provisional_panel_sha256':strategy['original_source_metadata_hashes']['metadata/provisional_panel.json']}
    commit,was_reused=annotate(item,runtime,plan,session,run);members.append({'accession':raw['accession'],'selected_faa':commit['selected_faa'],'annotation_receipt':commit['annotation_receipt'],'annotation_unit_execution':commit['unit_execution'],'annotation_commit':c.row(session/'annotations'/raw['accession']/'commit.json')});reused.append({'accession':raw['accession'],'reused':was_reused});progress('RUNNING','Validated benchmark annotation commit '+raw['accession'],index+1)
    if admission['phase']=='BOUNDARY_AFTER_FIRST_ANNOTATION':
     if was_reused:raise RuntimeError('Boundary demonstration already committed; continuation admission required')
     result={'status':'BENCHMARK_BOUNDARY_FIRST_ANNOTATION_COMMITTED_PENDING_EXTERNAL_CLOSURE','annotation_members':members,'reused':reused,'batch_prediction_invoked':False};break
   else:
    result={'status':'BENCHMARK10_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','batch':batch(plan,strategy,runtime,session,run,members,admission['phase']),'reused':reused}
   result.update(input_plan_sha256=a.input_plan_sha256,session_identity_sha256=plan['session_identity_sha256'],protocol_admission_sha256=c.sha(c.ADMISSION),production_panel_acceptance=False,source_holds_preserved=True)
   c.save(run/'result.json',result);manifest=c.manifest(run);c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(run),'result_path':str(run/'result.json'),'manifest_path':str(c.bind(manifest)),'manifest_sha256':manifest['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE',result['status'],len(members))
  except BaseException as ex:
   c.save(run/'failure.json',{'status':'BENCHMARK_FAILED_OR_UNKNOWN_NO_RETRY','error':repr(ex),'current_invocation_groups_closed':c.group_receipts_closed(run),'production_acceptance':'NOT_GRANTED'});progress('FAILED','Benchmark phase held; preserve partial/uncommitted work and do not retry',len(members));raise
 finally:lock.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);main(p.parse_args())
