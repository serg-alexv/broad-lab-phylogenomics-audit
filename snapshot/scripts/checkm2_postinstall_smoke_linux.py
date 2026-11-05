"""Read-only continuation of completed installation; never invokes Conda/prediction."""
from pathlib import Path
import json,os
import checkm2_runtime_image as image
import checkm2_private_install_linux as old
R=image.R;E=image.E;P=image.PREFIX
OVERRIDES={'GLIBC_TUNABLES':'glibc.rtld.execstack=2'}

def main():
 image.private();os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));old.gate()
 if image.read(E/'install_exit.json')['exit_code']!=0:raise RuntimeError('Installation itself was not completed')
 with image.RuntimeImage(True,True,E/'postinstall_compat_mount.json'):
  records=image.read(E/'resolved_packages.json')
  if not old.package_matches(records):raise RuntimeError('Completed installed package metadata differs from pinned133 closure')
  cached=[]
  for row in records:
   old.gate();p=image.MOUNT/'pkgs'/row['fn']
   if p.stat().st_size!=row['size'] or image.sha(p)!=row['sha256']:raise RuntimeError('Image cached archive differs:'+row['fn'])
   cached.append({'name':row['name'],'sha256':row['sha256'],'bytes':row['size']})
  image.save(E/'ext4_cached_archives_verified.json',{'status':'PASS_ALL133_IMAGE_CACHE_ARCHIVES','at_utc':image.utc(),'packages':cached})
  # These variables affect new child processes at loader startup, not this helper.
  os.environ.update(OVERRIDES)
  old.run('compat_cli_smoke',[str(P/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--cli'],600)
  old.run('compat_model_smoke',[str(P/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--models','--database',str(image.DB)],600)
  smoke=image.read(E/'runtime_smoke_receipt.json')
  if smoke.get('runtime_environment_overrides')!=OVERRIDES:raise RuntimeError('Actual model smoke environment was not recorded')
  installed=old.manifest(P,R/'manifests/checkm2_environment_files.json')
  modelroot=next((P/'lib').glob('python*/site-packages/checkm2'))/'models'
  models=old.manifest(modelroot,R/'manifests/checkm2_model_files.json')
  db=image.read(R/'tools/databases/checkm2_v3/extracted_receipt.json')
  candidate={'status':'CANDIDATE_ENVIRONMENT_SMOKE_PASS','created_utc':image.utc(),'prefix_linux':str(P),'checkm2_version':'1.1.0','diamond_version':'2.1.11','package_count':133,'resolved_packages_sha256':old.EXPECTED,'installed_manifest':installed,'models_manifest':models,'database':db,'phases':old.PHASES,'import_smoke_passed':True,'model_load_smoke_passed':True,'smoke_receipt_path':'evidence/checkm2_runtime/runtime_smoke_receipt.json','runtime_environment_overrides':OVERRIDES,'scientific_prediction':'NOT_RUN'}
  image.save(E/'environment_candidate_receipt.json',candidate)
  result={'status':'PASS_READONLY_RUNTIME_PERSISTENCE','at_utc':image.utc(),'installed_manifest_sha256':installed['sha256'],'models_manifest_sha256':models['sha256'],'image_seal':image.read(E/'ext4_image_seal.json'),'canonical_prefix':str(P),'canonical_database':str(image.DB),'all_smoke_children_closed':True,'runtime_environment_overrides':OVERRIDES,'scientific_prediction':'NOT_RUN','no_installation_command':True}
  image.save(E/'ext4_readonly_validation.json',result)
if __name__=='__main__':main()
