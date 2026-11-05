"""Private image proof/install/RO persistence; scientific prediction is never run."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,signal,subprocess,time
import checkm2_runtime_image as image
import checkm2_private_install_linux as old
R=image.R;E=image.E;M=image.MOUNT

def gate():
 old.gate()
 if (M/'lost+found').exists() and shutil.disk_usage(M).free<2*1024**3:raise RuntimeError('Image internal reserve below2GiB')
def progress(s,n=0):old.progress(s,n,6,unit='recovery phases')
def dbcopy():
 receipt=image.read(R/'tools/databases/checkm2_v3/extracted_receipt.json');dest=M/'db/uniref100.KO.1.dmnd'
 if dest.exists():raise RuntimeError('New-image database target already exists')
 h=hashlib.sha256();count=0;started=time.monotonic();last=0
 with image.DB.open('rb') as src,dest.with_suffix('.pending').open('xb') as out:
  while chunk:=src.read(8*1024**2):
   gate();out.write(chunk);h.update(chunk);count+=len(chunk)
   if time.monotonic()-started>600:raise RuntimeError('Database copy deadline600s exceeded')
   if time.monotonic()-last>3:progress(f'Copying verified database into private image {count}/{receipt["bytes"]}; no user input required',1);last=time.monotonic()
  out.flush();os.fsync(out.fileno())
 if count!=receipt['bytes'] or h.hexdigest()!=receipt['sha256']:raise RuntimeError('Image database copy differs from accepted source')
 os.replace(dest.with_suffix('.pending'),dest)
 image.save(E/'ext4_database_copy.json',{'status':'MATCH_VERIFIED_DATABASE_SOURCE','at_utc':image.utc(),'bytes':count,'sha256':h.hexdigest(),'original_database_unchanged':True,'image_path':'db/uniref100.KO.1.dmnd'})
def probe():
 p=M/'proof';a=p/'CaseProbe';b=p/'caseprobe';a.write_bytes(b'UPPER\n');b.write_bytes(b'lower\n')
 if a.read_bytes()==b.read_bytes() or os.path.samefile(a,b):raise RuntimeError('Image does not preserve case-distinct paths')
 rows=[];start=time.monotonic()
 for i in range(1000):
  gate();f=p/f'file_{i:04d}';payload=(str(i)+' Tree2 ext4 capability\n').encode();f.write_bytes(payload);rows.append({'path':f.name,'sha256':hashlib.sha256(payload).hexdigest()})
 command=['sync','-f',str(M)];image.command(command,60)
 image.save(E/'ext4_small_file_probe.json',{'status':'PASS_1000_NEW_IMAGE_FILES','at_utc':image.utc(),'seconds':time.monotonic()-start,'files':rows,'case_distinct_paths':True})
def snapshot():
 result={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split();rss=int(next((v.split()[1] for v in (p/'status').read_text().splitlines() if v.startswith('VmRSS:')),'0'))*1024
   result[int(p.name)]={'pid':int(p.name),'ppid':int(s[1]),'start_ticks':int(s[19]),'rss':rss,'state':s[0]}
  except (OSError,ValueError,IndexError):pass
 return result
def controlled_driver():
 args=['/usr/bin/python3','-B',str(R/'scripts/checkm2_private_install_linux.py')];start=image.utc();p=subprocess.Popen(args,start_new_session=True);known={};peak=0;error=None;deadline=time.monotonic()+5400
 try:
  while p.poll() is None:
   table=snapshot();selected={p.pid};changed=True
   while changed:
    more={pid for pid,v in table.items() if v['ppid'] in selected};changed=not more.issubset(selected);selected|=more
   for pid in selected:
    if pid in table:known[pid]=table[pid]['start_ticks']
   active=[v for pid,v in table.items() if known.get(pid)==v['start_ticks']]
   rss=sum(v['rss'] for v in active)+table.get(os.getpid(),{}).get('rss',0);peak=max(peak,rss);gate()
   if rss>2*1024**3:raise RuntimeError('Recovery process tree exceeds2GiB RSS')
   if time.monotonic()>deadline:raise RuntimeError('Recovery outer Linux deadline5400s exceeded')
   time.sleep(.5)
  if p.returncode:raise RuntimeError(f'Pinned runtime driver exit{p.returncode}')
 except BaseException as ex:
  error=repr(ex)
  for sig in (signal.SIGTERM,signal.SIGKILL):
   table=snapshot()
   for pid,tick in known.items():
    if pid in table and table[pid]['start_ticks']==tick:
     try:os.kill(pid,sig)
     except ProcessLookupError:pass
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:pass
 finally:
  table=snapshot();remaining=[v for pid,v in table.items() if known.get(pid)==v['start_ticks'] and v['state']!='Z']
  image.save(E/'ext4_driver_exit.json',{'started_utc':start,'ended_utc':image.utc(),'exit_code':p.poll(),'error':error,'peak_tree_rss_bytes':peak,'known_process_identities':known,'remaining':remaining,'all_owned_children_closed':not remaining,'command':args})
 if error or remaining:raise RuntimeError(error or 'Recovery descendants remain')
def prepare():
 progress('Creating filesystem only in the exclusively created regular project image; no user input required')
 image.format_new_image()
 with image.RuntimeImage(False,False,E/'ext4_prepare_mount.json'):
  hand=image.read(E/'cache_handoff.json');bound=hand['conservative_cache_extraction_prefix_bytes']+image.read(R/'tools/databases/checkm2_v3/extracted_receipt.json')['bytes']+2012243675+2*1024**3
  free=shutil.disk_usage(M).free
  if free<bound:raise RuntimeError(f'New image capacity{free} below conservative bound{bound}')
  image.save(E/'ext4_capacity_admission.json',{'at_utc':image.utc(),'available_bytes':free,'required_bound_bytes':bound,'host_free_bytes':shutil.disk_usage(R).free,'internal_reserve_bytes':2*1024**3})
  for d in ('env','pkgs','tmp','db','proof'):(M/d).mkdir()
  probe();dbcopy();progress('Private image proof and verified database copy complete; clean closure next',2)
def proof_ro():
 with image.RuntimeImage(True,False,E/'ext4_prepare_ro_mount.json'):
  if (M/'proof/CaseProbe').read_bytes()!=b'UPPER\n' or (M/'proof/caseprobe').read_bytes()!=b'lower\n':raise RuntimeError('Case/persistence probe differs after remount')
  manifest=image.read(E/'ext4_small_file_probe.json')
  for row in manifest['files']:
   if image.sha(M/'proof'/row['path'])!=row['sha256']:raise RuntimeError('Small-file persistence differs')
  db=image.read(E/'ext4_database_copy.json')
  if (M/'db/uniref100.KO.1.dmnd').stat().st_size!=db['bytes'] or image.sha(M/'db/uniref100.KO.1.dmnd')!=db['sha256']:raise RuntimeError('Database persistence differs')
  image.save(E/'ext4_prepare_persistence.json',{'status':'PASS_RW_CLOSE_RO_REMOUNT_PERSISTENCE','at_utc':image.utc(),'case_paths':True,'small_files':1000,'database_sha256':db['sha256']})
def install():
 with image.RuntimeImage(False,True,E/'ext4_install_mount.json'):
  os.environ.update(CONDA_PKGS_DIRS=str(M/'pkgs'),TMPDIR=str(M/'tmp'),TMP=str(M/'tmp'),TEMP=str(M/'tmp'))
  progress('Installing identical133-package closure inside the private image; no user input required',2);controlled_driver()
  records=image.read(E/'resolved_packages.json');rows=[]
  for row in records:
   gate();p=M/'pkgs'/row['fn']
   if p.stat().st_size!=row['size'] or image.sha(p)!=row['sha256']:raise RuntimeError('Image cached archive differs:'+row['fn'])
   rows.append({'name':row['name'],'sha256':row['sha256'],'bytes':row['size']})
  image.save(E/'ext4_cached_archives_verified.json',{'status':'PASS_ALL133_IMAGE_CACHE_ARCHIVES','at_utc':image.utc(),'packages':rows})
def verify_ro():
 with image.RuntimeImage(True,True,E/'ext4_validation_ro_mount.json'):
  for name in ('checkm2_environment_files.json','checkm2_model_files.json'):
   data=image.read(R/'manifests'/name)
   for row in data['artifacts']:
    old.gate();p=R/row['path'];actual=hashlib.sha256(os.readlink(p).encode()).hexdigest() if row['kind']=='symlink' else image.sha(p)
    if actual!=row['sha256']:raise RuntimeError('Read-only installed artifact differs:'+row['path'])
  old.run('readonly_cli_smoke',[str(image.PREFIX/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--cli'],600)
  old.run('readonly_model_smoke',[str(image.PREFIX/'bin/python'),str(R/'scripts/checkm2_runtime_smoke.py'),'--models','--database',str(image.DB)],600)
  image.save(E/'ext4_readonly_validation.json',{'status':'PASS_READONLY_RUNTIME_PERSISTENCE','at_utc':image.utc(),'installed_manifest_sha256':image.sha(R/'manifests/checkm2_environment_files.json'),'models_manifest_sha256':image.sha(R/'manifests/checkm2_model_files.json'),'image_seal':image.read(E/'ext4_image_seal.json'),'canonical_prefix':str(image.PREFIX),'canonical_database':str(image.DB),'all_smoke_children_closed':True,'scientific_prediction':'NOT_RUN'})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','proof_ro','install','verify_ro']);a=ap.parse_args();image.private();os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));globals()[a.stage]()
if __name__=='__main__':main()
