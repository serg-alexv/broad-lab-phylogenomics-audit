"""ONE held format control; original wrappers imported in an isolated adapter."""
from pathlib import Path
import argparse,datetime,fcntl,json,os,shutil,time
import checkm2_format_common_v002 as c
import checkm2_protein_pilot_v001 as pilot
h=pilot.h;R=c.R;STEP=R/'state/checkm2_protein_format_invariance_v002_step.json'
LAUNCH=None
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def progress(status,detail,done=0,**extra):
 owner={'windows_launch_token':LAUNCH['token'],'pid':LAUNCH['pid'],'creation_time_utc':LAUNCH['creation_time_utc']} if LAUNCH else {}
 c.v.save(STEP,{'status':status,'detail':detail,'done':done,'total':1,'unit':'DNA-wrap61 format controls','updated_utc':utc(),'operation':'FORMAT_CONTROL','production_acceptance':'NOT_GRANTED','native_linux_identity':pilot.legacy.stat(os.getpid()),**owner,**extra})
pilot.OUT=c.OUT;pilot.STATE=STEP;pilot.progress=progress
pilot.legacy.STATE=STEP;pilot.legacy.OUT=c.OUT
original_stop=pilot.legacy.stop_gate
def stop(*args,**kwargs):c.stop();return original_stop(*args,**kwargs)
pilot.legacy.stop_gate=stop
def row(path):
 path=c.path(path);return {'path':path.relative_to(R).as_posix(),'sha256':h.sha(path),'bytes':path.stat().st_size}
def execute(run,plan,runtime):
 original=pilot.verify_input(plan['input']);inputdir=run/'derived_input';inputdir.mkdir()
 derived=inputdir/(plan['input']['accession']+'.fna')
 # The root protocol is checked before reaching the only variant constructor.
 semantic=c.fasta.rewrap_new(original,derived,61);h.save(run/'semantic_identity.json',semantic)
 if semantic['original_sha256']!=plan['input']['fasta_sha256'] or semantic['original_sha256']==semantic['derived_sha256'] or semantic['original_semantics']!=semantic['derived_semantics']:raise RuntimeError('Declared format-only input identity failed')
 item={**plan['input'],'fasta_sha256':semantic['derived_sha256'],'fasta_bytes':semantic['derived_bytes'],'staged_fna':str(derived)}
 prefix=Path(runtime['prefix']);env=pilot.environment(prefix);annotation=run/'annotation'
 annotation_plan={'input':item,'runtime_prefix':str(prefix),'original_prodigal_source_sha256':plan['original_prodigal_source_sha256'],'prodigal_program_sha256':runtime['tools']['prodigal']['sha256']}
 h.save(run/'annotation_plan.json',annotation_plan)
 pilot.run_unit('unit01_original_annotation',[str(prefix/'bin/python'),'-B',str(R/'scripts/checkm2_protein_helpers_v001.py'),'annotate','--plan',str(run/'annotation_plan.json'),'--output',str(annotation)],env,run)
 annotated=h.read(annotation/'annotation_receipt.json');faa=c.path(annotated['faa_path'])
 if annotated['status']!='ORIGINAL_SEQUENTIAL_PRODIGAL_COMPLETED_NOT_GENOME_ACCEPTANCE' or h.sha(faa)!=annotated['faa_sha256']:raise RuntimeError('Control annotation source/FAA binding failed')
 baseline_annotation=h.read(c.bind(plan['baseline_annotation']))
 import checkm2_protein_invariance_v002 as compare
 annotation_comparison=compare.compare_annotation_receipts(baseline_annotation,annotated)
 h.save(run/'annotation_comparison.json',annotation_comparison)
 if annotation_comparison['equal'] is not True:raise RuntimeError('DNA-wrap61 changed original annotation; no quality substitution/retry')
 quality_input=run/'protein_input';quality_input.mkdir();copied=quality_input/(item['accession']+'.faa');shutil.copyfile(faa,copied)
 if h.sha(copied)!=annotated['faa_sha256']:raise RuntimeError('Control selected FAA changed during staging')
 core={'image_sha256':runtime['ready']['runtime_image']['sha256'],'models_manifest_sha256':runtime['models_manifest_sha256'],'database_sha256':runtime['database_sha256'],'effective_runtime_manifest_sha256':runtime['effective_runtime']['manifest_sha256']}
 flags={'genes':True,'extension':'faa','threads':1,'lowmem':True,'dbg_vectors':True,'mode':'auto'}
 original_quality=h.read(c.bind(plan['baseline_quality_binding']))
 if original_quality['core_model_database_binding']!=core or original_quality['flags']!=flags or original_quality['original_caller_sha256']!=plan['original_prodigal_source_sha256']:raise RuntimeError('Control runtime/model/DB/author/options differ from baseline')
 quality_binding={'role':c.ROLE,'original_FNA_sha256':plan['input']['fasta_sha256'],'derived_FNA_sha256':semantic['derived_sha256'],'semantic_identity_sha256':h.sha(run/'semantic_identity.json'),'annotation_receipt_sha256':h.sha(annotation/'annotation_receipt.json'),'selected_FAA_sha256':annotated['faa_sha256'],'exact_basename':copied.name,'core_model_database_binding':core,'flags':flags,'feature_schema_sha256':plan['feature_schema']['sha256'],'original_caller_sha256':plan['original_prodigal_source_sha256']};h.save(run/'protein_quality_binding.json',quality_binding)
 tmp=run/'durable_quality_tmp';tmp.mkdir();quality=run/'quality_output';route=runtime['ipc_routing'];env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(run/'effective_import_origins.json')
 cmd=[str(prefix/'bin/python'),'-B',route['bootstrap_path'],'--proof',route['proof_path'],'--proof-sha256',route['proof_sha256'],'--receipt',str(run/'target_ipc.json'),'checkm2','predict','--genes','--extension','faa','--threads','1','--lowmem','--input',str(quality_input),'--output-directory',str(quality),'--tmpdir',str(tmp),'--database_path',runtime['database_path'],'--dbg_vectors','--debug']
 started=time.monotonic();pilot.run_unit('unit02_protein_quality',cmd,env,run)
 request={'request_schema':'TREE2_CONTROL_FEATURE_REQUEST_V002','accession':item['accession'],'runtime_prefix':str(prefix),'source_manifest':plan['source_manifest'],'protocol_admission':row(c.ADMISSION),'schema':plan['feature_schema'],'input_plan_sha256':plan['_plan_sha256'],'artifacts':{'raw_pickle':row(quality/'feature_vectors_1.pkl'),'selected_faa':row(copied),'annotation_receipt':row(annotation/'annotation_receipt.json'),'quality_report':row(quality/'quality_report.tsv'),'quality_unit_execution':row(run/'unit02_protein_quality/execution.json')}}
 # Keep the request kind separate from its schema-file binding.
 h.save(run/'feature_request.json',request)
 remaining=600-(time.monotonic()-started)
 if remaining<=0:raise TimeoutError('Protein prediction plus corrected validation exceeded600s')
 validator=R/'scripts/checkm2_control_feature_validator_v002.py'
 pilot.run_unit('unit02_feature_validation',[str(prefix/'bin/python'),'-B',str(validator),'--request',str(run/'feature_request.json'),'--request-sha256',h.sha(run/'feature_request.json'),'--output',str(run/'feature_validation.json')],env,run,remaining)
 features=h.read(run/'feature_validation.json')
 if features['status']!='PROTEIN_CONTROL_FEATURES_V002_PASS_PENDING_CLOSURE':raise RuntimeError('Corrected fresh-control feature validation absent')
 report,comp,cont=h.parse_protein_report(quality/'quality_report.tsv',item['accession'])
 result={'status':'FORMAT_CONTROL_CORE_PENDING_NAMESPACE_NATIVE_AND_COMPARISON','role':c.ROLE,'accession':item['accession'],'Completeness':comp,'Contamination':cont,'raw_author_protein_report_row':report,'annotation_receipt':row(annotation/'annotation_receipt.json'),'feature_validation':row(run/'feature_validation.json'),'protein_quality_binding':row(run/'protein_quality_binding.json'),'semantic_identity':row(run/'semantic_identity.json'),'selected_faa':row(copied),'quality_report':row(quality/'quality_report.tsv'),'quality_output':str(quality),'input_plan_sha256':plan['_plan_sha256'],'protocol_admission_sha256':h.sha(c.ADMISSION),'production_acceptance':'NOT_GRANTED','format_invariance_acceptance':'NOT_GRANTED','stock_resume_used':False,'nucleotide_route_numeric_equivalence_measured':False}
 h.save(run/'result.json',result);return result
def main(a):
 global LAUNCH
 plan,baseline,admission=c.plan_gate(a.input_plan,a.input_plan_sha256);plan['_plan_sha256']=a.input_plan_sha256
 LAUNCH=h.read(c.LAUNCH)
 if LAUNCH['token']!=a.launch_token or LAUNCH['input_plan_sha256']!=a.input_plan_sha256:raise RuntimeError('Native control launch/input-plan binding differs')
 pilot.LAUNCH=LAUNCH;pilot.legacy.LAUNCH=LAUNCH
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Private read-only runtime required')
 lock=(R/'state/checkm2_pilot.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));stop()
  runtime=pilot.legacy.ready_gate(R/'state/checkm2_runtime_ready.json',require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=pilot.legacy.ipc_runtime_gate(runtime);pilot.legacy.no_heavy_science()
  c.OUT.mkdir(parents=True,exist_ok=True)
  with (c.OUT/'one_control_claim.json').open('x') as f:json.dump({'admission_sha256':h.sha(c.ADMISSION),'input_plan_sha256':a.input_plan_sha256,'launch':LAUNCH},f);f.flush();os.fsync(f.fileno())
  run=c.OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.launch_token[:12]);run.mkdir(parents=True,exist_ok=False)
  h.save(run/'binding.json',{'plan':plan,'runtime':runtime,'root_protocol_admission_sha256':h.sha(c.ADMISSION),'launch':LAUNCH});shutil.copyfile(__file__,run/'controller_source_at_execution.py')
  try:
   result=execute(run,plan,runtime);digest=pilot.manifest(run,'manifest.json');h.save(c.OUT/'latest_pending_native.json',{'status':result['status'],'result_path':str(run/'result.json'),'manifest_path':str(run/'manifest.json'),'manifest_sha256':digest,'run_directory':str(run),'input_plan_sha256':a.input_plan_sha256,'namespace_execution_receipt_path':str(c.E/'namespace_runs'/(a.launch_token+'.json'))});progress('CONTROL_CORE_PENDING_CLOSURE','Control annotation, protein report and corrected raw features completed; native closure/comparison pending',1,result_path=str(run/'result.json'))
  except BaseException as ex:
   failure={'status':'CONTROL_FAILED_OR_UNPROVEN','error':repr(ex),'run_directory':str(run),'ended_utc':utc(),'all_started_unit_groups_closed':pilot.all_unit_groups_closed(run),'production_acceptance':'NOT_GRANTED'}
   h.save(run/'failure_receipt.json',failure)
   if failure['all_started_unit_groups_closed']:failure['manifest_sha256']=pilot.manifest(run,'failure_manifest.json')
   h.save(c.OUT/'last_exit.json',failure);progress('FAILED','DNA-wrap61 control failed or was not evaluable; see terminal receipt',0,log_path=str(run/'failure_receipt.json'));raise
 finally:lock.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-plan',required=True);p.add_argument('--input-plan-sha256',required=True);p.add_argument('--launch-token',required=True);a=p.parse_args()
 try:main(a)
 except BaseException as ex:
  progress('FAILED','Control failed or preflight/closure was unproven; no retry',0,error=repr(ex));raise
