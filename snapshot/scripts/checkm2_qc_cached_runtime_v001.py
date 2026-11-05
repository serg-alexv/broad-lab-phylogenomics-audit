"""Narrow image verification cache around the unchanged reviewed RO runtime owner."""
from pathlib import Path
import argparse,os,json,hashlib,fcntl,sys
import checkm2_runtime_image as original
R=original.R

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4096),b''):h.update(b)
 return h.hexdigest()
def bind(ref):
 p=R/ref['path']if not Path(ref['path']).is_absolute()else Path(ref['path'])
 if not p.resolve().is_relative_to(R)or sha(p)!=ref['sha256']or p.stat().st_size!=ref['bytes']:raise RuntimeError('Image-cache authority dependency changed')
 return p
def stamp(p):
 s=Path(p).stat();return{'dev':s.st_dev,'ino':s.st_ino,'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}

def rebound_format(fmt,admission,current_identity,current_stat,seal):
 """Return a copy with only Root-admitted volatile DrvFS st_dev rebound."""
 if admission.get('status')!='ROOT_ADMITTED_DRVFS_VOLATILE_DEVICE_REBIND_V001' or admission.get('reason')!='WSL_VM_RESTART_DRVFS_ST_DEV_CHANGED':raise RuntimeError('Explicit Root volatile-device rebind required')
 old=admission.get('old_identity');new=admission.get('new_identity')
 if not isinstance(old,dict) or not isinstance(new,dict) or set(old)!=set(('dev','ino','size','nlink')) or set(new)!=set(old) or any(type(v)is not int for v in (*old.values(),*new.values())):raise RuntimeError('Exact typed old/new image identities required')
 if fmt.get('status')!='FORMATTED_NEW_PROJECT_REGULAR_IMAGE' or fmt.get('identity')!=old or old['dev']!=52 or new['dev']!=51 or {k:v for k,v in old.items()if k!='dev'}!={k:v for k,v in new.items()if k!='dev'} or new['ino']!=5348024557958676 or new['size']!=17179869184 or new['nlink']!=1 or current_identity!=new:raise RuntimeError('Only admitted dev52 to dev51 transition of the same image is allowed')
 if current_stat!=admission.get('image_stat') or current_stat['dev']!=new['dev'] or current_stat['ino']!=new['ino'] or current_stat['bytes']!=new['size']:raise RuntimeError('Exact current image stat required for volatile-device rebind')
 if seal.get('status')!='SEALED_AFTER_CLEAN_UNMOUNT' or seal.get('sha256')!=admission.get('image_sha256') or seal.get('sha256')!='c40e6918688eaf2e1a9e4161e77a4b473c3f611de575b39a89bdc03fba224ad4' or seal.get('bytes')!=new['size']:raise RuntimeError('Unchanged complete clean-unmount seal required')
 result=json.loads(json.dumps(fmt));result['identity']['dev']=new['dev'];return result

def main():
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--cache-authority');parser.add_argument('--cache-authority-sha256');a,rest=parser.parse_known_args()
 lock=(R/'state/checkm2_pilot.lock').open('r+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  real_sha=original.sha;real_read=original.read;cached=None
  if a.cache_authority:
   path=Path(a.cache_authority)
   if not path.resolve().is_relative_to(R)or sha(path)!=a.cache_authority_sha256:raise RuntimeError('Root image-cache admission changed')
   authority=json.loads(path.read_text());last=json.loads(bind(authority['last_full_posthash_receipt']).read_text());seal=original.read(original.E/'ext4_image_seal.json')
   if authority.get('status')!='ROOT_ADMITTED_EXCLUSIVE_READONLY_QC_IMAGE_VERIFICATION_CACHE_V001'or authority.get('no_writer_since_last_full_hash')is not True or authority.get('only_QC_exclusive_image_leases_authorized')is not True or authority.get('scientific_or_previous_whole0_acceptance_claimed')is not False:raise RuntimeError('Narrow Root operational cache authority required')
   if last.get('image_sha256_after_clean_unmount')!=seal['sha256']or last.get('image_bytes')!=17179869184 or last.get('image_unchanged')is not True:raise RuntimeError('Actual last complete posthash c40/size/closure binding absent')
   if stamp(original.IMAGE)!=authority['image_stat']:raise RuntimeError('Image stat drift; cache reuse forbidden')
   cached={'authority_path':str(path),'authority_sha256':a.cache_authority_sha256,'image_stat':authority['image_stat'],'last_full_posthash_receipt':authority['last_full_posthash_receipt'],'derived_sha256':seal['sha256']}
   if authority.get('volatile_device_rebind')is not None:
    rebind=authority['volatile_device_rebind']
    if rebind.get('image_stat')!=authority['image_stat']:raise RuntimeError('Root rebind and cache current stat differ')
    fmt_path=bind(rebind['format_receipt'])
    if fmt_path.resolve()!=(original.E/'ext4_format_receipt.json').resolve():raise RuntimeError('Only original format receipt may be viewed with rebound dev')
    rebound_format(real_read(fmt_path),rebind,original.image_identity(),stamp(original.IMAGE),seal)
    receipt=Path(authority['cache_use_receipt']).with_name('volatile_device_rebind.json')
    if not receipt.resolve().is_relative_to(R):raise RuntimeError('Volatile-device receipt escapes project')
    def admitted_read(p):
     if Path(p).resolve()!=fmt_path.resolve():return real_read(p)
     bind(rebind['format_receipt'])
     result=rebound_format(real_read(p),rebind,original.image_identity(),stamp(original.IMAGE),real_read(original.E/'ext4_image_seal.json'))
     original.save(receipt,{'status':'ROOT_ADMITTED_VOLATILE_DRVFS_DEVICE_REBOUND_IN_MEMORY_ONLY','at_utc':original.utc(),'authority_path':str(path),'authority_sha256':a.cache_authority_sha256,'format_receipt':rebind['format_receipt'],'old_identity':rebind['old_identity'],'new_identity':rebind['new_identity'],'exact_current_stat':rebind['image_stat'],'reason':rebind['reason'],'last_full_posthash_receipt':authority['last_full_posthash_receipt'],'image_sha256':seal['sha256'],'original_format_receipt_modified':False,'returned_format_field_changed_only':'identity.dev','Linux_QC_compute_flock_held':True,'all_other_original_identity_kernel_loop_UUID_RO_guards_required':True,'final_full_posthash_still_required':True})
     return result
    original.read=admitted_read
   def admitted_sha(p):
    if Path(p).resolve()!=original.IMAGE.resolve():return real_sha(p)
    if not os.statvfs(original.IMAGE).f_flag&os.ST_RDONLY or stamp(original.IMAGE)!=cached['image_stat']:raise RuntimeError('Cache requires same exact stat and kernel-readonly raw image bind')
    original.save(Path(authority['cache_use_receipt']),{'status':'PREHASH_REUSED_ONLY_FROM_BOUND_COMPLETE_POSTHASH_AND_IDENTICAL_STAT','cache':cached,'raw_image_readonly':True,'Linux_QC_compute_flock_held':True,'fresh_full_prehash_performed':False,'original_runtime_loop_UUID_RO_flags_bindings_still_required':True,'final_full_posthash_still_required':True})
    return cached['derived_sha256']
   original.sha=admitted_sha
  sys.argv=[str(Path(original.__file__)),*rest];original.main()
 finally:
  try:
   original.sha=real_sha;original.read=real_read
   fcntl.flock(lock,fcntl.LOCK_UN)
  finally:lock.close()
if __name__=='__main__':main()
