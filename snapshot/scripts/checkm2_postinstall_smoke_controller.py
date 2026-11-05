"""One read-only, process-local loader-compatibility smoke of the completed image."""
from pathlib import Path
import json,msvcrt,os,shutil,subprocess,time
import checkm2_ext4_recovery_controller as imagectl
import checkm2_private_install_controller as base
R=base.R;E=base.E;L=base.L;OWNER=base.OWNER;START=base.START
OVERRIDES={'GLIBC_TUNABLES':'glibc.rtld.execstack=2'}

def main():
 base.gate()
 if (R/'state/checkm2_runtime_ready.json').exists():raise RuntimeError('Runtime is already ready')
 if base.read(E/'install_exit.json')['exit_code']!=0 or not base.read(E/'ext4_driver_exit.json')['all_owned_children_closed']:raise RuntimeError('Completed installation/closure required')
 if base.read(E/'ext4_install_mount_closure.json')['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH':raise RuntimeError('Image closure required')
 lock=(R/'state/checkm2_install.lock').open('r+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 before=base.private.registry();status='FAILED';error=None;sealed=None;candidate=None
 base.save(R/'state/launch_tool_setup.json',{**OWNER,'script':'scripts/checkm2_postinstall_smoke_controller.py','phase':'READONLY_POSTINSTALL_LOADER_SMOKE'})
 imagectl.progress('Testing documented process-local loader compatibility in the completed read-only image; no user input required',0)
 try:
  d=E/'history/ext4_cli_loader_failure_20261026T203941Z';d.mkdir(exist_ok=False);preserved=[]
  for rel in ['evidence/checkm2_runtime/'+n for n in ('install_exit.json','cli_smoke_exit.json','private_install_linux_failure.json','ext4_install_execution.json','ext4_driver_exit.json','ext4_install_mount_closure.json')]+['logs/'+n for n in ('checkm2_cli_smoke.stderr.txt','checkm2_cli_smoke.stdout.txt','checkm2_ext4_install.stderr.txt')]:
   p=R/rel
   if p.exists():
    out=d/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out);preserved.append({'original':rel,'preserved':out.relative_to(R).as_posix(),'sha256':base.sha(out)})
  base.save(d/'manifest.json',{'at_utc':base.utc(),'artifacts':preserved})
  with (E/'postinstall_single_smoke_claim.json').open('x') as f:json.dump({'at_utc':base.utc(),'owner':OWNER,'runtime_environment_overrides':OVERRIDES,'no_installation_command':True,'per_smoke_deadline_seconds':600},f);f.flush();os.fsync(f.fileno())
  sealed=imagectl.seal('install')
  with (R/'logs/checkm2_postinstall_smoke.stdout.txt').open('w') as out,(R/'logs/checkm2_postinstall_smoke.stderr.txt').open('w') as err:
   p=subprocess.Popen(['wsl','-d','Ubuntu','--','/bin/bash',L+'/scripts/checkm2_private_setup_ns.sh','outer','run',L+'/scripts/checkm2_postinstall_smoke.sh'],stdout=out,stderr=err)
   while p.poll() is None:time.sleep(1)
   if p.returncode:raise RuntimeError(f'Read-only compatibility smoke failed exit{p.returncode}')
  closure=base.read(E/'postinstall_compat_mount_closure.json');candidate=base.read(E/'environment_candidate_receipt.json');model=base.read(E/'runtime_smoke_receipt.json');ro=base.read(E/'ext4_readonly_validation.json')
  if closure['status']!='CLEAN_UNMOUNT_AND_LOOP_DETACH' or candidate['status']!='CANDIDATE_ENVIRONMENT_SMOKE_PASS' or ro['status']!='PASS_READONLY_RUNTIME_PERSISTENCE' or model['runtime_environment_overrides']!=OVERRIDES:raise RuntimeError('Final RO/CLI/model/closure receipt not accepted')
  for key in ('installed_manifest','models_manifest'):
   if base.sha(R/candidate[key]['path'])!=candidate[key]['sha256']:raise RuntimeError('Final artifact manifest changed')
  status='COMPLETE'
 except BaseException as ex:error=repr(ex)
 finally:
  after=base.private.registry();same=before==after
  if not same:status='FAILED';error='Outside shared registry changed'
  receipt={'status':status,'started_utc':START,'ended_utc':base.utc(),'native_owner':OWNER,'error':error,'host_registry_before':before,'host_registry_after':after,'host_registry_unchanged':same,'image_seal':sealed,'candidate':candidate,'runtime_environment_overrides':OVERRIDES,'no_installation_command':True,'scientific_prediction':'NOT_RUN','controller_sha256':base.sha(__file__)}
  base.save(E/'postinstall_smoke_execution.json',receipt)
  if status=='COMPLETE':
   env={**receipt,'native_process_identity':OWNER,'storage':'PROJECT_OWNED_EXT4_IMAGE','loader_compatibility_source_audit_path':'evidence/checkm2_runtime/loader_compatibility_source_audit.json','read_only_validation_path':'evidence/checkm2_runtime/ext4_readonly_validation.json'};base.save(E/'tool_environment_receipt.json',env)
   ready={'status':'READY_FOR_RESOURCE_PILOT','created_utc':base.utc(),'storage':'PROJECT_OWNED_EXT4_IMAGE','requires_private_image_mount':True,'prefix_linux':candidate['prefix_linux'],'prefix_windows':str(R/'tools/checkm2_env'),'outside_prefix_is_preserved_unaccepted_ntfs_partial':True,'checkm2_version':'1.1.0','diamond_version':'2.1.11','import_smoke_passed':True,'model_load_smoke_passed':True,'smoke_receipt_path':candidate['smoke_receipt_path'],'installed_manifest_path':candidate['installed_manifest']['path'],'installed_manifest_sha256':candidate['installed_manifest']['sha256'],'models_manifest_path':candidate['models_manifest']['path'],'models_manifest_sha256':candidate['models_manifest']['sha256'],'database_path':L+'/'+candidate['database']['database_path'],'database_receipt_path':'tools/databases/checkm2_v3/extracted_receipt.json','environment_receipt_path':'evidence/checkm2_runtime/tool_environment_receipt.json','environment_receipt_sha256':base.sha(E/'tool_environment_receipt.json'),'runtime_environment_overrides':OVERRIDES,'heavy_linux_children_closed':True,'scientific_prediction':'NOT_RUN','image_relative_path':imagectl.IMAGE.relative_to(R).as_posix(),'image_sha256':sealed['sha256'],'filesystem_uuid':sealed['filesystem_uuid'],'image_seal_receipt_path':'evidence/checkm2_runtime/ext4_image_seal.json','readonly_mount_helper_path':'scripts/checkm2_runtime_image.py','runtime_image':{'path':L+'/tools/checkm2_runtime_ext4.img','windows_path':str(imagectl.IMAGE),'relative_path':imagectl.IMAGE.relative_to(R).as_posix(),'sha256':sealed['sha256'],'bytes':sealed['bytes'],'filesystem_uuid':sealed['filesystem_uuid'],'seal_receipt_path':'evidence/checkm2_runtime/ext4_image_seal.json','seal_receipt_sha256':base.sha(E/'ext4_image_seal.json')}}
   base.save(R/'state/checkm2_runtime_ready.json',ready)
  imagectl.progress('Read-only CLI/models passed with documented process-local loader environment; pilot next' if status=='COMPLETE' else error,6 if status=='COMPLETE' else 0,'COMPLETE' if status=='COMPLETE' else 'FAILED')
  lock.close();print(json.dumps(receipt),flush=True)
 return 0 if status=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
