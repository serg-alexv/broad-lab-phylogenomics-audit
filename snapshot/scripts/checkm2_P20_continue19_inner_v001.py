"""HELD P20 single novel genome: sequential original annotation, model-free search, stock resume."""
from pathlib import Path
import argparse,datetime,fcntl,json,math,os,shutil,sys,time,traceback
import checkm2_P20_continue19_common_v001 as c
import checkm2_phase_separated_artifacts_N1 as artifacts
import checkm2_unit_observer_S1R2 as observer
import checkm2_protein_pilot_v001 as pilot
from checkm2_optional_progress_S1R2 import safe_call
R=c.R;LAUNCH=None;CURRENT_RUN=None;INNER_IDENTITY=None;DONE=0;HELPER_DEADLINE=None;PROGRESS_ERRORS=[];PROGRESS_ERROR_COUNT=0

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def note_optional(value):
 global PROGRESS_ERROR_COUNT
 PROGRESS_ERROR_COUNT+=1
 if len(PROGRESS_ERRORS)<32:PROGRESS_ERRORS.append(value)
 try:print(json.dumps({'optional_progress_io_error':value}),file=sys.stderr,flush=True)
 except OSError:pass

def raw_progress(status,detail,done=None,**extra):
 global DONE
 if type(done)is int and 0<=done<=19:DONE=max(DONE,done)
 if 'run_directory'in extra:extra['active_unit_directory']=extra.pop('run_directory')
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc'],'input_plan_sha256':LAUNCH['input_plan_sha256'],'protocol_admission_sha256':LAUNCH['protocol_admission_sha256']} if LAUNCH else {}
 current={'run_directory':str(CURRENT_RUN)} if CURRENT_RUN else {}
 c.save(c.STEP,{'status':status,'detail':detail,'done':DONE,'total':19,'unit':'validated serial novel P20 method estimates','operation':'PHASE_SEPARATED_P20','updated_utc':utc(),'native_linux_identity':INNER_IDENTITY,'production_panel_acceptance':False,**owner,**current,**extra})
def progress(*args,**kwargs):return safe_call(raw_progress,*args,error_sink=note_optional,**kwargs)
pilot.OUT=c.OUT;pilot.STATE=c.STEP;pilot.progress=progress;pilot.legacy.STATE=c.STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate

def stop(*args,**kwargs):
 c.stop()
 if LAUNCH and c.sha(c.ADMISSION)!=LAUNCH['protocol_admission_sha256']:raise InterruptedError('P20 admission changed')
 if HELPER_DEADLINE is not None and time.monotonic()>=HELPER_DEADLINE:raise TimeoutError('P20 helper finite deadline reached')
 return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop

def invoke(name,command,env,run):
 stop();spent=c.budget(CURRENT_RUN);acc=run.name;used=spent['input_scientific_seconds'].get(acc,0);phase_used=spent['units_seconds_by_accession'].get(acc,{})
 seconds=min(c.UNITS[name],1410-used,spent['remaining_cohort_scientific_seconds'],HELPER_DEADLINE-time.monotonic())
 if name in phase_used or not 0<seconds<=600 or(run/name).exists():raise RuntimeError('P20 phase once/debit/time boundary; no replay')
 c.save(run/(name+'_budget.json'),{'unit':name,'accession':acc,'allowed_seconds':seconds,'phase_ceiling_seconds':c.UNITS[name],'per_input_scientific_seconds':1410,'cohort_scientific_seconds':26790,'debit_before_start':spent,'input_debit_before_start_seconds':used,'helper_remaining_at_start_seconds':HELPER_DEADLINE-time.monotonic(),'protocol_admission_sha256':c.sha(c.ADMISSION)})
 index=c.read(CURRENT_RUN/'invocations.json');index.append(str(run/name));c.save(CURRENT_RUN/'invocations.json',index)
 observer.run_unit(name,command,env,run,seconds,hooks={'save':c.save,'stop_gate':stop,'stat':pilot.legacy.stat,'group':lambda pgid:observer.strict_group(pgid,pilot.legacy.stat),'mem_available':pilot.legacy.mem_available,'progress':raw_progress,'optional_error_sink':note_optional})
 if not c.unit_closed(c.read(run/name/'execution.json')):raise RuntimeError('P20 typed actual own phase0/group closure required')
 c.budget(CURRENT_RUN)

def request_base(plan,recipe,prefix):return {'input_plan':plan['_row'],'source_manifest':plan['source_manifest'],'protocol_admission':c.row(c.ADMISSION),'selected_inputs':recipe['selected_inputs'],'accession':recipe['input']['accession'],'runtime_prefix':str(prefix)}
def command_for(prefix,module,request,output):return [str(prefix/'bin/python'),'-B',str(R/'scripts'/module),'--request',str(request),'--request-sha256',c.sha(request),'--output',str(output)]
def phase_manifest(folder):return c.manifest(folder)

def one(plan,recipe,runtime,run):
 acc=recipe['input']['accession'];prefix=Path(runtime['prefix']);env=pilot.environment(prefix);requests=run/'requests';requests.mkdir();inputs=run/'input';inputs.mkdir()
 staged=inputs/(acc+'.fna');shutil.copyfile(c.path(recipe['input']['fasta_path']),staged)
 if c.sha(staged)!=recipe['input']['fasta_sha256']:raise RuntimeError('Fresh acquisition-bound staged FNA differs')
 base=request_base(plan,recipe,prefix);annotation=run/'annotation';request=requests/'annotation.json'
 c.save(request,{**base,'request_schema':'TREE2_PHASE_SEPARATED_P20_ANNOTATION_REQUEST_V001','staged_fna':c.row(staged)})
 progress('RUNNING','Original sequential model-free annotation; estimate remains unknown',0)
 invoke('unit_annotation',command_for(prefix,'checkm2_P20_continue19_annotation_v001.py',request,annotation),env,run)
 faa=annotation/(acc+'.faa');ann_receipt=c.row(annotation/'annotation_receipt.json');ann_unit=c.row(run/'unit_annotation/execution.json')
 ann_commit={'status':'P20_ANNOTATION_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'selected_faa':c.row(faa),'annotation_receipt':ann_receipt,'unit_execution':ann_unit,'native_launch_token':LAUNCH['token'],'manifest':phase_manifest(annotation),'all10_author_returns_preserved':True,'coordinate_GFF_FNA_deleted_by_unchanged_author':True,'source_masks':recipe['input']['source_masks']}
 c.save(run/'annotation_commit.json',ann_commit)
 protein_input=run/'protein_input';protein_input.mkdir();shutil.copyfile(faa,protein_input/faa.name)
 artifacts.exact_faa_inventory(protein_input,acc,c.sha(faa))
 resume=run/'resume_output';search_receipts=run/'search_receipts';search_receipts.mkdir();request=requests/'diamond.json'
 database=dict(recipe['runtime_binding']['database']);diamond_binary=dict(recipe['runtime_binding']['tools']['diamond'])
 if c.path(runtime['database_path'])!=c.path(database['path']) or runtime['database_sha256']!=database['sha256'] or runtime['database_bytes']!=database['bytes']:raise RuntimeError('Producer verified DB3 receipt differs')
 if database!=recipe['runtime_binding']['database'] or diamond_binary!=recipe['runtime_binding']['tools']['diamond'] or c.path(runtime['prefix'])!=c.path(recipe['runtime_binding']['canonical_prefix']) or runtime['ready']['runtime_image']['sha256']!=recipe['runtime_binding']['image_sha256'] or runtime['effective_runtime']['manifest_sha256']!=recipe['runtime_binding']['effective_manifest']['sha256']:raise RuntimeError('Producer actual accepted runtime/DB3/binary/image/effective ABI differs')
 if diamond_binary['sha256']!=recipe['diamond_program_sha256']:raise RuntimeError('Accepted DIAMOND executable differs')
 c.save(request,{**base,'request_schema':'TREE2_PHASE_SEPARATED_P20_DIAMOND_REQUEST_V001','selected_faa':c.row(faa),'annotation_receipt':ann_receipt,'annotation_unit_execution':ann_unit,'database':database,'diamond_binary':diamond_binary,'durable_scratch':str(run/'diamond_tmp'),'resume_output':str(resume)})
 progress('RUNNING','Fresh original DIAMOND without resident model state',0)
 invoke('unit_diamond',command_for(prefix,'checkm2_P20_continue19_diamond_v001.py',request,search_receipts/'diamond_receipt.json'),env,run)
 search=c.read(search_receipts/'diamond_receipt.json');raw=search['raw_diamond'];artifacts.exact_diamond_inventory(resume/'diamond_output',raw)
 search_commit={'status':'P20_DIAMOND_UNIT0_COMMITTED_PENDING_CONTEXT_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'selected_faa':c.row(faa),'diamond_receipt':c.row(search_receipts/'diamond_receipt.json'),'unit_execution':c.row(run/'unit_diamond/execution.json'),'raw_diamond':raw,'database':database,'native_launch_token':LAUNCH['token'],'manifest':phase_manifest(search_receipts)}
 c.save(run/'diamond_commit.json',search_commit)
 proteins=resume/'protein_files';proteins.mkdir();shutil.copyfile(faa,proteins/faa.name)
 before={'protein_files':artifacts.exact_faa_inventory(proteins,acc,c.sha(faa)),'diamond_files':artifacts.exact_diamond_inventory(resume/'diamond_output',raw),'fresh_search_commit':c.row(run/'diamond_commit.json'),'annotation_commit':c.row(run/'annotation_commit.json'),'source_plan_sha256':plan['_sha'],'stock_resume':True,'stock_genes':True,'search_or_annotation_replay_authorized':False}
 c.save(run/'stock_resume_inventory_before.json',before)
 tmp=run/'resume_tmp';tmp.mkdir();route=runtime['ipc_routing'];env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(run/'effective_import_origins.json')
 command=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(run/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--resume','--input',str(protein_input),'--output-directory',str(resume),'--tmpdir',str(tmp),'--database_path',str(c.path(runtime['database_path'])),'--dbg_vectors','--debug']
 progress('RUNNING','Unchanged stock genes/resume on complete fresh search/FAA inventory',0)
 invoke('unit_resume',command,env,run)
 after={'protein_files':artifacts.exact_faa_inventory(proteins,acc,c.sha(faa)),'diamond_files':artifacts.exact_diamond_inventory(resume/'diamond_output',raw)}
 if after!={key:before[key] for key in after}:raise RuntimeError('Stock resume changed its committed protein/search inputs')
 if {p.name for p in resume.glob('feature_vectors_*.pkl')}!={'feature_vectors_1.pkl'}:raise RuntimeError('One declared feature-vector chunk required')
 c.save(run/'stock_resume_inventory_after.json',after)
 prediction={'status':'P20_STOCK_RESUME_EXIT0_FEATURE_VALIDATION_PENDING','accession':acc,'unit_execution':c.row(run/'unit_resume/execution.json'),'raw_pickle':c.row(resume/'feature_vectors_1.pkl'),'quality_report':c.row(resume/'quality_report.tsv'),'fresh_search_commit':c.row(run/'diamond_commit.json'),'input_inventory_before':c.row(run/'stock_resume_inventory_before.json'),'input_inventory_after':c.row(run/'stock_resume_inventory_after.json'),'manifest':phase_manifest(resume)}
 c.save(run/'prediction_commit.json',prediction)
 request=requests/'features.json';output=run/'feature_validation.json'
 feature_artifacts={'raw_pickle':prediction['raw_pickle'],'selected_faa':c.row(faa),'annotation_receipt':ann_receipt,'annotation_unit_execution':ann_unit,'annotation_commit':c.row(run/'annotation_commit.json'),'diamond_receipt':search_commit['diamond_receipt'],'diamond_unit_execution':search_commit['unit_execution'],'diamond_commit':c.row(run/'diamond_commit.json'),'quality_report':prediction['quality_report'],'quality_unit_execution':prediction['unit_execution']}
 c.save(request,{**base,'request_schema':'TREE2_PHASE_SEPARATED_P20_FEATURE_REQUEST_V001','accession':acc,'scientific_recipe':plan['scientific_recipe'],'schema':plan['feature_schema'],'artifacts':feature_artifacts,'resume_output':str(resume)})
 progress('RUNNING','Saved own-row full feature and independent membership validation',0)
 invoke('unit_feature_validation',command_for(prefix,'checkm2_P20_continue19_feature_validator_v001.py',request,output),env,run)
 features=c.read(output)
 if features.get('status')!='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE' or features.get('accession')!=acc or features.get('row_count')!=1:raise RuntimeError('Own P20 feature result missing')
 commit={'status':'P20_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE','accession':acc,'input_plan_sha256':plan['_sha'],'source_manifest_sha256':plan['source_manifest']['sha256'],'native_launch_token':LAUNCH['token'],'annotation_commit':c.row(run/'annotation_commit.json'),'diamond_commit':c.row(run/'diamond_commit.json'),'prediction_commit':c.row(run/'prediction_commit.json'),'feature_validation':c.row(output),'unit_executions':{name:c.row(run/name/'execution.json') for name in c.UNITS},'manifest':c.manifest(run,'row_manifest.json'),'source_holds_preserved':recipe['input']['source_holds_preserved'],'source_pending_reasons':recipe['input']['source_pending_reasons'],'source_masks':recipe['input']['source_masks'],'source_taxonomy_acceptance':False,'production_panel_acceptance':False}
 c.save(run/'commit.json',commit);return {'accession':acc,'origin':'FRESH_NOVEL_PHASE_SEPARATED_P20','commit':c.row(run/'commit.json'),'feature_validation':c.row(output),'source_masks':recipe['input']['source_masks']}

def main(a):
 global LAUNCH,CURRENT_RUN,INNER_IDENTITY,HELPER_DEADLINE
 plan,recipe,admitted=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_sha']=a.input_plan_sha256;plan['_row']=c.row(c.path(a.input_plan));LAUNCH=c.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256 or LAUNCH['protocol_admission_sha256']!=c.sha(c.ADMISSION):raise RuntimeError('P20 launch/source/authority differs')
 request=c.read(c.E/'launch_requests'/(a.launch_token+'.json'))
 if request.get('token')!=a.launch_token or request.get('input_plan_sha256')!=a.input_plan_sha256 or request.get('protocol_admission_sha256')!=c.sha(c.ADMISSION)or request.get('cold_session_seconds')!=30000 or request.get('helper_max_seconds')!=28760:raise RuntimeError('P20 immutable cold request differs')
 deadline=a.helper_deadline_unix
 if not math.isfinite(deadline)or deadline>request['cold_wall_deadline_unix']-640+0.01 or deadline-time.time()>28760.01 or deadline<=time.time():raise TimeoutError('P20 helper deadline exceeds immutable fresh cold allocation')
 HELPER_DEADLINE=time.monotonic()+deadline-time.time();pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH;INNER_IDENTITY=pilot.legacy.stat(os.getpid())
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Private read-only accepted runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BaseException:lock.close();raise
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop();runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  session=c.OUT/'sessions'/plan['session_identity_sha256'];session.mkdir(parents=True,exist_ok=False)
  with(session/'once_claim.json').open('x')as f:json.dump({'native_launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'source_manifest_sha256':plan['source_manifest']['sha256'],'accessions':recipe['inference_order'],'phase':'CONTINUE_RESERVED19_ONCE'},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False);CURRENT_RUN=run;c.save(run/'invocations.json',[]);(run/'rows').mkdir()
  c.save(run/'binding.json',{'plan':plan,'runtime':runtime,'admission':c.row(c.ADMISSION),'launch':LAUNCH,'immutable_request':request,'helper_deadline_unix':deadline})
  c.save(c.OUT/'runs_by_token'/(a.launch_token+'.json'),{'run_directory':str(run),'launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'protocol_admission_sha256':c.sha(c.ADMISSION),'binding':c.row(run/'binding.json')})
  results=[]
  try:
   for item in recipe['inputs']:
    stop();acc=item['accession'];folder=run/'rows'/acc;folder.mkdir(exist_ok=False)
    with(folder/'once_claim.json').open('x')as f:json.dump({'accession':acc,'native_launch_token':a.launch_token,'input_plan_sha256':a.input_plan_sha256,'source_manifest_sha256':plan['source_manifest']['sha256'],'phase_order':list(c.UNITS)},f);f.flush();os.fsync(f.fileno())
    row=one(plan,{**recipe,'input':item},runtime,folder);results.append(row);c.save(run/'completed_rows_checkpoint.json',{'rows':results,'completed_qc_rows':len(results),'budget':c.budget(run),'native_group_namespace_closure_pending':True});progress('RUNNING','Completed four serial phases for '+acc,len(results))
   result={'status':'P20_CORE_PENDING_NAMESPACE_NATIVE_CLOSURE','input_plan_sha256':a.input_plan_sha256,'session_identity_sha256':plan['session_identity_sha256'],'protocol_admission_sha256':c.sha(c.ADMISSION),'completed_qc_rows':len(results),'rows':results,'budget':c.budget(run),'optional_progress_error_count':PROGRESS_ERROR_COUNT,'optional_progress_errors_first32':PROGRESS_ERRORS,'original_annotation_units':19,'original_fresh_DIAMOND_units':19,'stock_resume_prediction_units':19,'model_batch_genomes_per_invocation':1,'strict_serial_four_phases_per_input':True,'previously_accepted_rows_recalculated':False,'source_taxonomy_acceptance':False,'production_panel_acceptance':False}
   c.save(run/'result.json',result);manifest=c.manifest(run);c.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'run_directory':str(run),'result_path':str(run/'result.json'),'manifest_path':str(c.bind(manifest)),'manifest_sha256':manifest['sha256'],'input_plan_sha256':a.input_plan_sha256,'launch_token':a.launch_token,'protocol_admission_sha256':c.sha(c.ADMISSION),'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CORE_PENDING_CLOSURE',result['status'],19)
  except BaseException as ex:
   original_traceback=traceback.format_exc();closed=None;closure_error=None;spent=None;debit_error=None
   try:closed=c.group_receipts_closed(run)
   except BaseException as secondary:closure_error={'type':type(secondary).__name__,'error':repr(secondary)}
   try:spent=c.budget(run)
   except BaseException as secondary:debit_error={'type':type(secondary).__name__,'error':repr(secondary)}
   c.save(run/'failure.json',{'status':'P20_FAILED_NO_AUTOMATIC_RETRY_OR_FALLBACK','error':repr(ex),'error_type':type(ex).__name__,'traceback':original_traceback,'current_invocation_groups_closed':closed,'closure_observer_error':closure_error,'known_budget':spent,'unknown_debit_blocker':debit_error,'rows':results,'completed_qc_rows':len(results),'no_automatic_retry_or_fallback':True,'previously_accepted_rows_recalculated':False});progress('FAILED','P20 stopped at first failure; preserve every phase claim/commit/debit',len(results));raise
 finally:
  try:fcntl.flock(lock,fcntl.LOCK_UN)
  finally:lock.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);p.add_argument('--helper-deadline-unix',required=True,type=float);main(p.parse_args())
