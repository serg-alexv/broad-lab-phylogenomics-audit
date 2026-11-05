"""Bounded matching-overlay controls; production and genome prediction stay blocked."""
from pathlib import Path
import json,msvcrt,os,subprocess,time
import checkm2_private_install_controller as base
import checkm2_ext4_recovery_controller as imagectl
R=base.R;E=base.E;L=base.L;OWNER=base.OWNER;START=base.START
SPEC=E/'sklearn161_effective_runtime.json'

def main():
 base.gate();lock=(R/'state/checkm2_install.lock').open('r+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 prep=base.read(E/'sklearn161_overlay_preparation.json');closed=base.read(E/'sklearn161_overlay_closure.json');spec=base.read(SPEC)
 if not closed['native_pid_absent'] or not closed['setup_os_lock_reacquired_and_released'] or base.sha(SPEC)!=prep['effective_runtime_manifest_sha256']:raise RuntimeError('Static overlay preparation/closure not accepted')
 candidate_sha=base.sha(R/'state/checkm2_runtime_ready.json')
 if candidate_sha!=spec['base_ready_receipt']['sha256']:raise RuntimeError('Base candidate differs')
 before=base.private.registry();status='FAILED';error=None;inside=None;control=None
 base.save(R/'state/launch_tool_setup.json',{**OWNER,'script':'scripts/checkm2_matching_runtime_controller.py','phase':'MATCHING_SKLEARN_LOAD_FORWARD_CONTROLS_RESOURCE_ONLY'})
 imagectl.progress('Validating matching-version overlay and original models under read-only bindings; no genome prediction',0)
 try:
  with (E/'matching_runtime_validation_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'owner':OWNER,'static_manifest_sha256':base.sha(SPEC),'candidate_ready_sha256':candidate_sha,'production_acceptance':False},f);f.flush();os.fsync(f.fileno())
  with (R/'logs/checkm2_matching_runtime.stdout.txt').open('w') as out,(R/'logs/checkm2_matching_runtime.stderr.txt').open('w') as err:
   p=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_matching_runtime.sh'],stdout=out,stderr=err)
   while p.poll() is None:time.sleep(1)
   if p.returncode:raise RuntimeError(f'Matching-version controls exit{p.returncode}')
  inside=base.read(E/'matching_runtime_inside_receipt.json');control=base.read(E/'matching_runtime_controls.json');closure=base.read(E/'matching_runtime_mount_closure.json')
  if inside['status']!='MATCHING_RUNTIME_TESTS_PASS_RESOURCE_ONLY' or not inside['all_owned_smoke_groups_closed'] or closure['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH' or control['effective_sklearn_version']!='1.6.1' or control['inconsistent_version_warnings']:raise RuntimeError('Matching runtime result/closure not accepted')
  if base.sha(R/'state/checkm2_runtime_ready.json')!=candidate_sha or base.sha(SPEC)!=prep['effective_runtime_manifest_sha256']:raise RuntimeError('Candidate/static effective manifest changed')
  status='MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY'
 except BaseException as ex:error=repr(ex)
 finally:
  after=base.private.registry();same=before==after
  if not same:status='FAILED';error='Outside shared registry changed'
  receipt={'status':status,'started_utc':START,'ended_utc':base.utc(),'native_owner':OWNER,'error':error,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':same,'candidate_ready_sha256':candidate_sha,'static_effective_manifest_sha256':base.sha(SPEC),'inside_result':inside,'control_receipt_path':'evidence/checkm2_runtime/matching_runtime_controls.json','runtime_environment_overrides':spec['required_runtime_environment'],'production_acceptance':False,'genome_inputs_used':0,'script_sha256':base.sha(__file__)}
  base.save(E/'matching_runtime_validation_execution.json',receipt)
  if status=='MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY':
   effective={**spec,'schema':'TREE2_EFFECTIVE_RUNTIME_VALIDATED_V1','status':status,'static_candidate_manifest_path':SPEC.relative_to(R).as_posix(),'static_candidate_manifest_sha256':base.sha(SPEC),'effective_import_provenance_and_native_runtime_tested':True,'scaler_equivalence_tested':'SYNTHETIC_AFFINE_FIXTURES_ALL21241_COLUMNS','official_numeric_controls_tested':False,'production_acceptance':'NOT_GRANTED','runtime_validation_receipt_path':'evidence/checkm2_runtime/matching_runtime_validation_execution.json','runtime_validation_receipt_sha256':base.sha(E/'matching_runtime_validation_execution.json'),'control_receipt_path':'evidence/checkm2_runtime/matching_runtime_controls.json','control_receipt_sha256':base.sha(E/'matching_runtime_controls.json'),'launch_protocol':{**spec['launch_protocol'],'bootstrap_status':'PRELOAD_POST_MAIN_ORIGINS_CLI_AND_CONTROLS_VERIFIED','bootstrap_path':'scripts/checkm2_effective_bootstrap.py','bootstrap_sha256':base.sha(R/'scripts/checkm2_effective_bootstrap.py'),'invocation':['<image-prefix>/bin/python','-B','<project>/scripts/checkm2_effective_bootstrap.py','checkm2','<original CLI arguments>']}}
   target=E/'sklearn161_effective_runtime_validated.json';base.save(target,effective)
   gate={'status':'FORWARD_DIAGNOSTIC_PASS_RESOURCE_ONLY','created_utc':base.utc(),'candidate_ready_sha256':candidate_sha,'receipt_path':'evidence/checkm2_runtime/matching_runtime_validation_execution.json','receipt_sha256':base.sha(E/'matching_runtime_validation_execution.json'),'image_sha256':spec['base_image']['sha256'],'models_manifest_sha256':spec['base_models_manifest']['sha256'],'runtime_environment_overrides':spec['required_runtime_environment'],'effective_runtime_manifest_path':target.relative_to(R).as_posix(),'effective_runtime_manifest_sha256':base.sha(target),'overlay_manifest_path':spec['overlay']['manifest_path'],'overlay_manifest_sha256':spec['overlay']['manifest_sha256'],'bootstrap_path':'scripts/checkm2_effective_bootstrap.py','bootstrap_sha256':base.sha(R/'scripts/checkm2_effective_bootstrap.py'),'native_owner':OWNER,'closure_proof_path':'evidence/checkm2_runtime/matching_runtime_mount_closure.json','closure_proof_sha256':base.sha(E/'matching_runtime_mount_closure.json'),'compatibility_status':'MATCHED_SCALER_VERSION_SYNTHETIC_CONTROLS_PASS_RESOURCE_ONLY','production_acceptance':False}
   base.save(R/'state/checkm2_forward_ready.json',gate)
  imagectl.progress('Matching scaler version/imports/forward controls passed; diagnostic resource pilot only' if status!='FAILED' else error,6 if status!='FAILED' else 0,'COMPLETE' if status!='FAILED' else 'FAILED')
  lock.close();print(json.dumps(receipt),flush=True)
 return 0 if status!='FAILED' else 2
if __name__=='__main__':raise SystemExit(main())
