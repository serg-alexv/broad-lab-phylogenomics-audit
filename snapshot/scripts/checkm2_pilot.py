#!/usr/bin/env python3
"""One-genome CheckM2 resource pilot. Default only prepares; no acceptance implied."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse,csv,datetime,fcntl,hashlib,json,math,os,re,resource,shutil,signal,socket,struct,subprocess,sys,time,uuid
R=Path(__file__).resolve().parents[1];ROOT=R.resolve();OUT=R/'analysis/checkm2_pilot';STATE=R/'state/checkm2_pilot_progress.json'
MAX_RSS=2*1024**3;HEADROOM=1024**3;TIMEOUT=600
START=datetime.datetime.now(datetime.timezone.utc).isoformat()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+uuid.uuid4().hex[:8]+'.tmp')
 with q.open('w',encoding='utf-8') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 for attempt in range(20):
  try:os.replace(q,p);return
  except PermissionError:
   if attempt==19:raise
   time.sleep(.05)
def inside(v):
 s=str(v)
 if re.match(r'^[A-Za-z]:[\\/]',s):s='/mnt/'+s[0].lower()+'/'+s[3:].replace('\\','/')
 p=Path(s);p=p if p.is_absolute() else R/p;p=p.resolve()
 if not p.is_relative_to(ROOT):raise RuntimeError('Path escapes isolated project root')
 return p

def stat(pid):
 x=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'parent_pid':int(x[1]),'process_group':int(x[2]),'creation_ticks':int(x[19]),'rss_bytes':int(x[21])*os.sysconf('SC_PAGE_SIZE'),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def group(pgid):
 result=[]
 for p in Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    s=stat(p.name)
    if s['process_group']==pgid:result.append(s)
   except(OSError,ValueError,IndexError):pass
 return result

def mem_available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024

def stop_gate(allow_preflight=False):
 if socket.gethostname().upper()!='WD':raise RuntimeError('WD-only guard')
 if (R/'state/STOP').exists() or ((R/'state/STOP_CHECKM2_PILOT').exists() and not allow_preflight):raise InterruptedError('STOP requested')
 available=mem_available()
 if available<HEADROOM:raise RuntimeError(f'RESOURCE_GATE: Linux available memory {available} bytes below1GiB')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('RESOURCE_GATE: backing volume below40GiB free')

def progress(status,detail,done=0,**extra):
 obj={'status':status,'done':done,'total':1,'unit':'pilot genomes','detail':detail,'started_utc':LAUNCH.get('started_utc',START) if LAUNCH else START,'controller_started_utc':START,'model_compatibility_status':'MATCHED_CONTROLS_RESOURCE_ONLY' if os.environ.get('TREE2_EFFECTIVE_RUNTIME_MANIFEST') else 'EFFECTIVE_RUNTIME_PREFLIGHT_PENDING','production_acceptance':'NOT_GRANTED','updated_utc':utc(),'native_linux_identity':stat(os.getpid()),'genome_quality_status':'NOT_ACCEPTED','defence_status':'NOT_RUN','completeness':None,'contamination':None,**extra}
 if LAUNCH:obj.update(pid=LAUNCH['pid'],creation_time_utc=LAUNCH['creation_time_utc'],windows_launch_token=LAUNCH.get('token'))
 save(STATE,obj)

def choose_input():
 panel=read(R/'metadata/provisional_panel.json');audit=read(R/'qc/source_provenance_audit.json')
 supported={r['accession'] for r in audit['records'] if r['production_disposition']=='SOURCE_SUPPORTED_BIOLOGICAL_QC_NOT_RUN'}
 candidates=[r for r in panel if r['accession'] in supported and r['metadata_qc']=='QC_METADATA_PASS' and r.get('ncbi_checkm_completeness') is not None and r.get('ncbi_checkm_contamination') is not None and (R/'raw'/r['accession']/'acquisition_receipt.json').exists()]
 if not candidates:raise RuntimeError('No source-supported candidate with known source CheckM comparison')
 row=candidates[0]
 if not re.fullmatch(r'GC[AF]_\d{9}\.\d+',row['accession']):raise RuntimeError('Expected a versioned public assembly accession')
 folder=R/'raw'/row['accession'];receipt=read(folder/'acquisition_receipt.json');dna=[f for f in receipt['files'] if f['path'].endswith('.fna')]
 if len(dna)!=1:raise RuntimeError('Expected exactly one genomic FNA')
 f=inside(folder/dna[0]['path'])
 if f.stat().st_size!=dna[0]['bytes'] or sha(f)!=dna[0]['sha256']:raise RuntimeError('Input FASTA fails acquisition hash binding')
 return {'accession':row['accession'],'species':row['species'],'species_taxid':row['species_taxid'],'fasta_path':str(f),'fasta_sha256':dna[0]['sha256'],'fasta_bytes':dna[0]['bytes'],'acquisition_receipt_sha256':sha(folder/'acquisition_receipt.json'),'source_provenance_audit_sha256':sha(R/'qc/source_provenance_audit.json'),'provisional_panel_sha256':sha(R/'metadata/provisional_panel.json'),'source_metadata_checkm':{'completeness':row['ncbi_checkm_completeness'],'contamination':row['ncbi_checkm_contamination'],'version':row.get('ncbi_checkm_version'),'comparison_role':'CONTEXT_ONLY_NOT_TRUTH_OR_CALIBRATION'}}

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);item=choose_input()
 plan={'status':'PREPARED_NOT_RUN','prepared_utc':utc(),'input':item,'required_runtime_ready':'state/checkm2_runtime_ready.json:READY_FOR_RESOURCE_PILOT','required_private_image_mount':True,'runtime_image_authority':'FINAL_READY_PLUS_CLEAN_UNMOUNT_SEAL_ONLY','namespace_launcher':'scripts/launch_checkm2_pilot.ps1','expected_versions':{'checkm2':'1.1.0','diamond':'2.1.11','database':'3'},'constraints':{'threads':2,'lowmem':True,'author_diamond_blocksize':0.5,'max_group_rss_bytes':MAX_RSS,'minimum_linux_available_bytes':HEADROOM,'max_prediction_seconds':TIMEOUT,'remove_intermediates':False,'author_internals_modified':False,'global_limits_changed':False},'acceptance_scope':'RESOURCE_AND_SCHEMA_PILOT_ONLY_NOT_FINAL_PANEL_ACCEPTANCE','script_sha256':sha(__file__)}
 save(OUT/'pilot_plan.json',plan);return plan

def mountinfo(path,mount_id=None):
 """Read this process's effective VFS mount; never create or modify a mount."""
 def unescape(value):return re.sub(r'\\([0-7]{3})',lambda m:chr(int(m.group(1),8)),value)
 matches=[]
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  parts=line.split();separator=parts.index('-')
  if unescape(parts[4])==str(path) and (mount_id is None or int(parts[0])==mount_id):
   matches.append({'mount_id':int(parts[0]),'root':unescape(parts[3]),'mountpoint':unescape(parts[4]),'vfs_options':parts[5].split(','),'fstype':parts[separator+1],'source':unescape(parts[separator+2]),'fs_options':parts[separator+3].split(',')})
 if len(matches)!=1:raise RuntimeError('WAITING_RUNTIME_NAMESPACE: expected one canonical mount entry')
 return matches[0]

def live_loop_identity(node):
 if not re.fullmatch(r'/dev/loop[0-7]',str(node)):raise RuntimeError('Unrecognized existing runtime loop node')
 fd=os.open(node,os.O_RDONLY|os.O_CLOEXEC)
 try:
  buffer=bytearray(232);fcntl.ioctl(fd,0x4C05,buffer,True)
  values=struct.unpack('=5Q4I64s64s32s2Q',buffer)
  return {'dev':values[0],'ino':values[1],'offset':values[3],'sizelimit':values[4],'flags':values[8],'backing_path':Path('/sys/block/'+Path(node).name+'/loop/backing_file').read_text().strip()}
 finally:os.close(fd)

def binding_digest(binding):
 stable=json.loads(json.dumps(binding));runtime=stable.get('runtime',{});runtime.pop('private_readonly_runtime',None);runtime.pop('private_ipc_namespace',None)
 if 'ready' in runtime:
  ready=runtime['ready'];image=ready.get('runtime_image',{});effective=runtime.get('effective_runtime') or {}
  stable['runtime']={'prefix':runtime.get('prefix'),'database_path':runtime.get('database_path'),'database_sha256':runtime.get('database_sha256'),'database_bytes':runtime.get('database_bytes'),'tools':runtime.get('tools'),'models':runtime.get('models'),'checkm2_version':ready.get('checkm2_version'),'diamond_version':ready.get('diamond_version'),'image':{key:image.get(key) for key in ('sha256','bytes','filesystem_uuid')},'effective':{key:effective.get(key) for key in ('required_environment','overlay_manifest_sha256','bootstrap_sha256','wheel_sha256')},'ipc_routing':runtime.get('ipc_routing')}
 return hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest()

def readonly_runtime_gate(ready):
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('WAITING_RUNTIME_NAMESPACE: private read-only runtime marker missing')
 if ready.get('requires_private_image_mount') is not True:raise RuntimeError('WAITING_RUNTIME_NAMESPACE: READY is not bound to a private image runtime')
 value=os.environ.get('TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT')
 if not value:raise RuntimeError('WAITING_RUNTIME_NAMESPACE: mount receipt path missing')
 receipt_path=inside(value);proof=read(receipt_path)
 if proof.get('status')!='READONLY_RUNTIME_MOUNT_VERIFIED' or proof.get('mount_namespace')!=os.readlink('/proc/self/ns/mnt'):raise RuntimeError('WAITING_RUNTIME_NAMESPACE: stale or unaccepted mount proof')
 image_binding=ready['runtime_image'];image=inside(image_binding['path'])
 if image!=R/'tools/checkm2_runtime_ext4.img':raise RuntimeError('Unexpected runtime image source')
 seal_path=inside(image_binding['seal_receipt_path'])
 if sha(seal_path)!=image_binding['seal_receipt_sha256']:raise RuntimeError('Image seal receipt differs from READY')
 seal=read(seal_path)
 if seal.get('status')!='SEALED_AFTER_CLEAN_UNMOUNT' or seal.get('sha256')!=image_binding['sha256']:raise RuntimeError('Image was not accepted after clean unmount')
 if proof.get('image_sha256')!=image_binding['sha256'] or proof.get('filesystem_uuid')!=image_binding['filesystem_uuid']:raise RuntimeError('Mounted image source hash/UUID differs from READY')
 prefix=inside(ready['prefix_linux']);database=inside(ready['database_path']);base=inside(proof['mountpoint'])
 if inside(proof['image_path'])!=image or inside(proof['prefix_linux'])!=prefix or inside(proof['database_path'])!=database:raise RuntimeError('Canonical mounted paths differ from READY')
 identity=image.stat()
 if identity.st_nlink!=1 or identity.st_size!=int(image_binding['bytes']):raise RuntimeError('Image identity/link count/size differs')
 actual={'dev':identity.st_dev,'ino':identity.st_ino,'size':identity.st_size,'nlink':identity.st_nlink}
 if actual!=proof.get('image_identity'):raise RuntimeError('Mounted backing-file identity differs')
 for key,path in [('raw_image_readonly',image),('canonical_prefix_readonly',prefix),('canonical_database_readonly',database)]:
  if proof.get(key) is not True or not os.statvfs(path).f_flag&os.ST_RDONLY:raise RuntimeError('WAITING_RUNTIME_NAMESPACE: actual runtime path is not read-only: '+str(path))
 if os.statvfs(prefix).f_flag&getattr(os,'ST_NOEXEC',8):raise RuntimeError('Runtime prefix unexpectedly mounted noexec')
 if not os.statvfs('/').f_flag&os.ST_RDONLY or os.statvfs(R).f_flag&os.ST_RDONLY:raise RuntimeError('Private namespace root/project write protections differ')
 loop=live_loop_identity(proof['loop_node'])
 if loop['dev']!=identity.st_dev or loop['ino']!=identity.st_ino or loop['offset'] or loop['sizelimit'] or loop['flags']&5!=5 or loop['backing_path']!=str(image):raise RuntimeError('Actual read-only/autoclear loop backing identity differs')
 if proof.get('loop_readonly') is not True or proof.get('loop_autoclear') is not True or proof.get('loop_flags')!=loop['flags']:raise RuntimeError('Mount proof loop flags differ from actual kernel state')
 observed=subprocess.run(['/usr/sbin/blkid','-p','-o','export',proof['loop_node']],capture_output=True,text=True,check=True,timeout=10)
 fs=dict(line.split('=',1) for line in observed.stdout.splitlines() if '=' in line)
 if fs.get('TYPE')!='ext4' or fs.get('UUID')!=image_binding['filesystem_uuid']:raise RuntimeError('Actual loop filesystem UUID/type differs')
 image_mount=mountinfo(base);prefix_mount=mountinfo(prefix);db_mount=mountinfo(database)
 for entry in (image_mount,prefix_mount,db_mount):
  if entry['fstype']!='ext4' or entry['source']!=proof['loop_node'] or not {'ro','nodev','nosuid'}.issubset(entry['vfs_options']) or 'noexec' in entry['vfs_options']:raise RuntimeError('Actual ext4 mount source/protections differ')
 if not {'noload','norecovery'}.intersection(image_mount['fs_options']):raise RuntimeError('Read-only ext4 journal replay is not disabled')
 if prefix_mount['root']!='/env' or db_mount['root']!='/db/uniref100.KO.1.dmnd':raise RuntimeError('Canonical runtime binds do not point to image env/db')
 return {'mount_receipt_path':str(receipt_path),'mount_receipt_sha256':sha(receipt_path),'image_binding':image_binding,'actual_image_identity':actual,'actual_loop':loop,'actual_mounts':[image_mount,prefix_mount,db_mount],'mount_namespace':proof['mount_namespace'],'read_only_paths_independently_checked':True,'no_mount_operations_by_controller':True}

def ready_gate(path,require_effective=False):
 p=inside(path)
 if not p.exists():raise RuntimeError('WAITING_RUNTIME: readiness receipt absent')
 ready=read(p)
 if ready.get('status')!='READY_FOR_RESOURCE_PILOT':raise RuntimeError('WAITING_RUNTIME: installed runtime/model smoke is not accepted')
 if ready.get('import_smoke_passed') is not True or ready.get('model_load_smoke_passed') is not True:raise RuntimeError('WAITING_RUNTIME: import/model smoke booleans not accepted')
 if str(ready.get('checkm2_version'))!='1.1.0' or str(ready.get('diamond_version'))!='2.1.11':raise RuntimeError('Pinned executable versions differ')
 controls=ready.get('runtime_environment_overrides',{})
 if not isinstance(controls,dict) or set(controls)-{'GLIBC_TUNABLES'}:raise RuntimeError('Unreviewed runtime environment control')
 if any(os.environ.get(key)!=value for key,value in controls.items()):raise RuntimeError('WAITING_RUNTIME: actual process environment differs from accepted model smoke')
 mounted=readonly_runtime_gate(ready)
 prefix=inside(ready.get('prefix_linux') or ready.get('prefix'));database=inside(ready['database_path']);dbreceipt_path=inside(ready['database_receipt_path']);dbreceipt=read(dbreceipt_path)
 environment_receipt=inside(ready['environment_receipt_path'])
 if sha(environment_receipt)!=ready.get('environment_receipt_sha256'):raise RuntimeError('Environment receipt hash differs from READY binding')
 environment=read(environment_receipt)
 if environment.get('runtime_environment_overrides',{})!=controls:raise RuntimeError('WAITING_RUNTIME: accepted environment controls differ from READY')
 if environment.get('status')!='COMPLETE' or environment.get('host_registry_unchanged') is not True or ready.get('heavy_linux_children_closed') is not True:raise RuntimeError('WAITING_RUNTIME: installation/audit/child-closure acceptance missing')
 ro=environment.get('read_only_validation');ro_path=None
 if not isinstance(ro,dict):
  ro_path=inside(environment['read_only_validation_path']);ro=read(ro_path)
 if ro.get('status')!='PASS_READONLY_RUNTIME_PERSISTENCE' or ro.get('all_smoke_children_closed') is not True:raise RuntimeError('WAITING_RUNTIME: read-only persistence/child-closure validation missing')
 if ro.get('runtime_environment_overrides',{})!=controls or ro.get('image_seal',{}).get('sha256')!=ready['runtime_image']['sha256'] or ro.get('image_seal',{}).get('filesystem_uuid')!=ready['runtime_image']['filesystem_uuid']:raise RuntimeError('Read-only validation source image/environment differs from READY')
 if ro.get('installed_manifest_sha256')!=ready['installed_manifest_sha256'] or ro.get('models_manifest_sha256')!=ready['models_manifest_sha256']:raise RuntimeError('Read-only validation manifests differ from READY')
 if not database.is_file():raise RuntimeError('WAITING_RUNTIME: verified extracted database missing')
 # The extracted receipt must explicitly bind this binary. Do not infer an extracted hash from archive hash.
 expected=dbreceipt.get('dmnd_sha256') or dbreceipt.get('sha256')
 expected_bytes=dbreceipt.get('dmnd_bytes') or dbreceipt.get('bytes')
 if isinstance(dbreceipt.get('database'),dict):expected=dbreceipt['database'].get('sha256',expected);expected_bytes=dbreceipt['database'].get('bytes',expected_bytes)
 if not expected or not expected_bytes:raise RuntimeError('Extracted DB receipt has no explicit binary size/SHA256')
 progress('PREPARING','Binding input,program,models and extracted database hashes; no prediction process')
 if database.stat().st_size!=int(expected_bytes) or sha(database)!=expected:raise RuntimeError('Extracted database size/SHA256 mismatch')
 models_manifest_path=inside(ready['models_manifest_path']);models_manifest=read(models_manifest_path)
 if sha(models_manifest_path)!=ready.get('models_manifest_sha256'):raise RuntimeError('Models manifest differs from READY hash')
 rows=models_manifest if isinstance(models_manifest,list) else models_manifest.get('artifacts',models_manifest.get('files',models_manifest.get('models',[])))
 if not rows:raise RuntimeError('Model hash manifest is empty')
 # The setup models/ manifest and all nine author external assets are distinct.
 for row in rows:
  path=inside(row['path'])
  if row.get('kind')=='symlink':
   if not path.is_symlink():raise RuntimeError('Expected model-manifest symlink')
  elif not path.is_file() or sha(path)!=row['sha256']:raise RuntimeError('Model manifest hash mismatch')
 smoke=inside(ready['smoke_receipt_path']);installed=inside(ready['installed_manifest_path'])
 if not smoke.exists() or not installed.exists():raise RuntimeError('Readiness dependency evidence missing')
 if sha(installed)!=ready.get('installed_manifest_sha256'):raise RuntimeError('Installed manifest differs from READY hash')
 smoke_data=read(smoke)
 if smoke_data.get('runtime_environment_overrides',{})!=controls:raise RuntimeError('WAITING_RUNTIME: model smoke process environment differs from READY')
 if smoke_data.get('status')!='PASS_IMPORT_AND_MODEL_LOADING_SMOKE' or smoke_data.get('author_database_compatibility')!='PASS' or smoke_data.get('bundled_test_genome_checksum')!='PASS':raise RuntimeError('WAITING_RUNTIME: all-model/import/author-data smoke not accepted')
 if smoke_data.get('database_sha256')!=expected:raise RuntimeError('Smoked database differs from extracted binding')
 model_rows=[]
 for row in smoke_data.get('model_files',[]):
  path=inside(row['path'])
  if not path.is_file() or sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise RuntimeError('Author model/scaler/reference hash mismatch')
  model_rows.append({'path':str(path),'sha256':row['sha256'],'bytes':row['bytes']})
 package_dirs={Path(row['path']).parent.parent for row in model_rows}
 if len(package_dirs)!=1:raise RuntimeError('Bound author assets do not share one CheckM2 package root')
 package=next(iter(package_dirs))
 if package.name!='checkm2' or package.parent.name!='site-packages' or not package.is_relative_to(prefix/'lib'):raise RuntimeError('Bound CheckM2 package root escapes the pinned prefix')
 required={'data/feature_ordering.json','data/kegg_path_category_mapping.json','data/module_definitions.json','models/general_model_COMP.gbm','models/specific_model_COMP.keras','models/model_CONT.gbm','models/scaler.sav','models/cosine_table.pkl','data/min_ref_rsdata_v1.npz'}
 covered={str(Path(r['path']).resolve()) for r in model_rows}
 if not {str((package/x).resolve()) for x in required}.issubset(covered):raise RuntimeError('All nine author model/scaler/reference assets must be hash-bound')
 tools={}
 for name in ('python','checkm2','diamond','prodigal'):
  q=prefix/'bin'/name
  if not q.is_file():raise RuntimeError('Runtime executable missing '+name)
  tools[name]={'path':str(q),'sha256':sha(q),'bytes':q.stat().st_size}
 effective=None
 if require_effective:
  from checkm2_effective_gate import effective_gate
  effective=effective_gate(p,mounted=True,mount_proof=read(inside(os.environ['TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT'])))
 return {'effective_runtime':effective,'ready':ready,'ready_receipt_path':str(p),'ready_receipt_sha256':sha(p),'private_readonly_runtime':mounted,'prefix':str(prefix),'database_path':str(database),'database_sha256':expected,'database_bytes':int(expected_bytes),'database_receipt_sha256':sha(dbreceipt_path),'models_manifest_sha256':sha(models_manifest_path),'models':model_rows,'smoke_receipt_sha256':sha(smoke),'installed_manifest_sha256':sha(installed),'environment_receipt_sha256':sha(environment_receipt),'read_only_validation_sha256':sha(ro_path) if ro_path else hashlib.sha256(json.dumps(ro,sort_keys=True).encode()).hexdigest(),'tools':tools}

def ipc_runtime_gate(runtime):
 """Verify the separate short IPC alias; scientific scratch remains durable."""
 if os.environ.get('TREE2_CHECKM2_PRIVATE_IPC_VERIFIED')!='1':raise RuntimeError('WAITING_PRIVATE_IPC: verified private alias is required')
 receipt_path=inside(os.environ['TREE2_CHECKM2_PRIVATE_IPC_RECEIPT']);active=read(receipt_path)
 if active.get('status')!='PRIVATE_SHORT_IPC_ACTIVE' or active.get('mount_namespace')!=os.readlink('/proc/self/ns/mnt') or active.get('alias')!='/tmp':raise RuntimeError('IPC alias receipt is stale or differs from current namespace')
 proofpath=inside(active['proof_path']);proofsha=active['proof_sha256'];proof=read(proofpath)
 if sha(proofpath)!=proofsha or os.environ.get('TREE2_CHECKM2_PRIVATE_IPC_PROOF_SHA256')!=proofsha or proof.get('status')!='PRIVATE_SHORT_IPC_PROVEN':raise RuntimeError('IPC capability proof differs')
 helper=R/'scripts/checkm2_ipc_alias.py';bootstrap=R/'scripts/checkm2_ipc_bootstrap.py';effective=runtime['effective_runtime']
 if proof.get('helper_sha256')!=sha(helper) or active.get('helper_sha256')!=sha(helper) or proof.get('target_bootstrap_sha256')!=sha(bootstrap):raise RuntimeError('IPC helper/bootstrap source differs from proven bytes')
 if proof.get('image_sha256')!=runtime['ready']['runtime_image']['sha256'] or proof.get('effective_runtime_manifest_sha256')!=effective['manifest_sha256'] or proof.get('unchanged_effective_bootstrap_sha256')!=effective['bootstrap_sha256']:raise RuntimeError('IPC proof is bound to another runtime')
 mode=proof.get('selected_mode')
 if mode not in ('PROJECT_BIND','TMPFS_32M') or active.get('mode')!=mode:raise RuntimeError('IPC backend differs from proven mode')
 backing=inside(active['backing_path'])
 if not backing.is_relative_to(R/'work/checkm2_ipc'):raise RuntimeError('IPC backing leaves dedicated project workspace')
 def ident(p):
  s=os.stat(p);return {'dev':s.st_dev,'ino':s.st_ino,'uid':s.st_uid,'gid':s.st_gid}
 if ident('/tmp')!=active['backing_identity'] or ident(backing)!=active['backing_identity']:raise RuntimeError('Actual short IPC alias does not map exact backing inode')
 # /tmp has an earlier RO bind under this private alias. Ask the kernel which
 # mount a real directory FD resolves to; mountinfo order is not authority.
 fd=os.open('/tmp',os.O_PATH|os.O_DIRECTORY|os.O_CLOEXEC)
 try:
  info=Path(f'/proc/self/fdinfo/{fd}').read_text()
  mount_id=int(next(line.split()[1] for line in info.splitlines() if line.startswith('mnt_id:')))
  actual=mountinfo('/tmp',mount_id=mount_id)
 finally:os.close(fd)
 flags=set(actual['vfs_options'])
 if not {'rw','nodev','nosuid','noexec'}.issubset(flags) or 'ro' in flags:raise RuntimeError('Actual IPC alias mount protections differ')
 capacity=None
 if mode=='TMPFS_32M':
  s=os.statvfs('/tmp');capacity=s.f_blocks*s.f_frsize
  if actual['fstype']!='tmpfs' or capacity!=32*1024**2 or active.get('capacity_bytes')!=capacity:raise RuntimeError('IPC tmpfs is not the proven32MiB backend')
 if active.get('scientific_outputs_stored_here') is not False:raise RuntimeError('IPC namespace is not restricted to ephemeral IPC')
 routing={'proof_path':str(proofpath),'proof_sha256':proofsha,'helper_path':str(helper),'helper_sha256':sha(helper),'bootstrap_path':str(bootstrap),'bootstrap_sha256':sha(bootstrap),'selected_mode':mode,'alias':'/tmp','capacity_bytes':capacity,'prewarm':'multiprocessing.util.get_temp_dir before unchanged author CLI','scientific_tmp_rule':'durable unique run/tmp; unchanged author --tmpdir'}
 return routing,{'receipt_path':str(receipt_path),'receipt_sha256':sha(receipt_path),'mount_namespace':active['mount_namespace'],'actual_alias_mount':actual,'actual_backing_identity':ident(backing)}

def no_heavy_science():
 names={'diamond','prodigal','checkm2','mmseqs','iqtree','iqtree2','iqtree3','mafft'}
 busy=[];ancestors={os.getpid()};parent=os.getpid()
 for _ in range(64):
  try:parent=stat(parent)['parent_pid']
  except (OSError,ValueError,IndexError):break
  if parent<=0 or parent in ancestors:break
  ancestors.add(parent)
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in ancestors:continue
  try:
   name=(p/'comm').read_text().strip();cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if name in names or (str(R) in cmd and (('/bin/checkm2' in cmd and 'predict' in cmd) or any(x in cmd for x in ('checkm2_pilot.py','checkm2_matching_controls','checkm2_forward_diagnostic','checkm2_effective_bootstrap.py','install_checkm2','checkm2_private_install','checkm2_private_setup','model_smoke','runtime_smoke','conda create','conda install')))):busy.append({'pid':int(p.name),'name':name})
  except(OSError,ValueError):pass
 if busy:raise RuntimeError('WAITING_HEAVY_PROCESS: '+json.dumps(busy))

def warning_inventory(paths):
 result=[]
 for p in paths:
  if not p.exists() or not p.is_file():continue
  for n,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
   if re.search(r'warning|inconsistentversion|not\s+compatible|version\s+mismatch|deprecat',line,re.I):result.append({'path':str(p.relative_to(R)),'line':n,'text':line[:2000]})
 return result

def collect_intermediates(run,binding):
 output=run/'output';logs=[]
 for p in [run/'predict.stderr.txt',run/'predict.stdout.txt']+list(output.glob('*.log')):
  if p.exists():logs.append(p.read_text(encoding='utf-8',errors='replace'))
 text='\n'.join(logs);proteins=list((output/'protein_files').glob('*')) if (output/'protein_files').exists() else []
 proteins=[p for p in proteins if p.is_file()];diamond=list((output/'diamond_output').glob('DIAMOND_RESULTS*')) if (output/'diamond_output').exists() else []
 gene_ok=bool(proteins);protein_ids=set()
 for p in proteins:
  current=None;length=0
  try:
   with p.open(encoding='ascii') as f:
    for line in f:
     line=line.strip()
     if not line:continue
     if line.startswith('>'):
      if current is not None and not length:raise ValueError('Empty protein')
      current=line[1:].split()[0]
      if current in protein_ids:raise ValueError('Duplicate protein identifier')
      protein_ids.add(current);length=0
     else:
      if current is None or not re.fullmatch(r'[A-Z*]+',line):raise ValueError('Malformed protein sequence')
      length+=len(line)
   if current is None or not length:raise ValueError('Missing/empty protein record')
  except Exception:gene_ok=False
 diamond_ok=bool(diamond) and 'Finished Running DIAMOND' in text and 'Processing DIAMOND output' in text
 errors=[];hit_rows=0
 for p in diamond:
  try:
   with p.open(encoding='utf-8') as f:
    for line in f:
     parts=line.rstrip('\n').split('\t')
     if len(parts)!=12 or not parts[0].startswith(binding['input']['accession']+'Ω'):raise ValueError('Malformed or mismatched DIAMOND row')
     if parts[0].split('Ω',1)[1] not in protein_ids:raise ValueError('DIAMOND query not in preserved protein records')
     if not all(math.isfinite(float(parts[k])) for k in (2,3,4,5,6,7,8,9,10,11)):raise ValueError('Nonfinite DIAMOND value')
     hit_rows+=1
  except Exception as e:errors.append({'file':str(p),'error':repr(e)});diamond_ok=False
 if hit_rows==0:diamond_ok=False
 files=[{'path':str(p.relative_to(run)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in proteins+diamond if p.is_file()]
 obj={'recorded_utc':utc(),'binding_sha256':binding_digest(binding),'proteins_syntactically_present':gene_ok,'diamond_finished_sentinel_seen':'Finished Running DIAMOND' in text,'diamond_postprocessing_sentinel_seen':'Processing DIAMOND output' in text,'diamond_rows':hit_rows,'diamond_schema_errors':errors,'compatible_for_author_resume':gene_ok and diamond_ok,'files':files,'note':'Partial/unproven outputs are preserved but cannot be resumed. No flag is a biological negative.'}
 save(run/'intermediate_inventory.json',obj)
 if obj['compatible_for_author_resume']:save(run/'verified_intermediate_checkpoint.json',{**obj,'full_binding':binding})
 return obj

def parse_quality_report(report,expected):
 with Path(report).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
 if len(rows)!=1 or rows[0].get('Name')!=expected:raise RuntimeError('Prediction row/name does not match the one-genome input')
 row=rows[0]
 if not {'Completeness','Contamination'}.issubset(row):raise RuntimeError('Prediction schema lacks Completeness/Contamination')
 comp=float(row['Completeness']);cont=float(row['Contamination'])
 if not(math.isfinite(comp) and math.isfinite(cont) and 0<=comp<=100 and cont>=0):raise RuntimeError('Prediction values are missing/nonfinite/outside allowed numeric domain')
 return row,comp,cont

def prediction(run,binding,resume_from=None):
 if not binding['runtime'].get('effective_runtime'):raise RuntimeError('WAITING_EFFECTIVE_RUNTIME: matching-version overlay, bound forward gate and audited CheckM2 bootstrap are required; no prediction started')
 routing,namespace=ipc_runtime_gate(binding['runtime'])
 if routing!=binding['runtime'].get('ipc_routing'):raise RuntimeError('Private IPC routing changed after input/options binding')
 prefix=Path(binding['runtime']['prefix']);tmp=run/'tmp';tmp.mkdir();inputdir=run/'input';inputdir.mkdir();source=Path(binding['input']['fasta_path']);fasta=inputdir/(binding['input']['accession']+'.fna');shutil.copyfile(source,fasta)
 if sha(fasta)!=binding['input']['fasta_sha256']:raise RuntimeError('Staged input hash mismatch')
 output=run/'output';resume=False
 if resume_from:
  prior=inside(resume_from);checkpoint=read(prior/'verified_intermediate_checkpoint.json')
  if checkpoint['binding_sha256']!=binding_digest(binding):raise RuntimeError('Resume binding differs; do not reuse intermediates')
  if checkpoint.get('compatible_for_author_resume') is not True:raise RuntimeError('No verified compatible intermediate checkpoint')
  for f in checkpoint['files']:
   p=inside(prior/f['path'])
   if p.stat().st_size!=f['bytes'] or sha(p)!=f['sha256']:raise RuntimeError('Resume intermediate hash mismatch')
   target=output/p.relative_to(prior/'output');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  resume=True
 cache_paths={'TMPDIR':Path('/tmp'),'TMP':Path('/tmp'),'TEMP':Path('/tmp'),'XDG_CACHE_HOME':R/'work/checkm2_private_xdg','XDG_CONFIG_HOME':R/'work/checkm2_private_config','KERAS_HOME':R/'work/checkm2_keras','MPLCONFIGDIR':R/'work/checkm2_mpl','NUMBA_CACHE_DIR':R/'work/checkm2_numba'}
 for path in set(cache_paths.values()):path.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env.update({k:str(v) for k,v in cache_paths.items()});env.update(PATH=str(prefix/'bin')+os.pathsep+env.get('PATH',''),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONWARNINGS='default',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2',TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='1',CUDA_VISIBLE_DEVICES='-1')
 cmd=[str(prefix/'bin/python'),'-B',routing['bootstrap_path'],'--proof',routing['proof_path'],'--proof-sha256',routing['proof_sha256'],'--receipt',str(run/'target_ipc.json'),'checkm2','predict','--input',str(inputdir),'--output-directory',str(output),'--threads','2','--lowmem','--tmpdir',str(tmp),'--database_path',binding['runtime']['database_path'],'--debug']
 env['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(run/'effective_import_origins.json')
 if resume:cmd.append('--resume')
 save(run/'command.json',{'command':cmd,'environment_overrides':{k:env[k] for k in env if k in set(cache_paths)|{'PATH','PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','PYTHONWARNINGS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS','CUDA_VISIBLE_DEVICES','GLIBC_TUNABLES','PYTHONPATH','TREE2_EFFECTIVE_ORIGIN_RECEIPT'}},'HOME_unchanged':env.get('HOME')==os.environ.get('HOME'),'author_diamond_lowmem_blocksize':0.5,'no_author_internals_modified':True,'upstream_logging_note':'Stock CheckM2 main/predictQuality set TF_CPP_MIN_LOG_LEVEL=3. Wrapper adds no suppression and preserves all emitted warnings.'})
 start=time.monotonic();proc=None;err=None;peak=0;identity=None;exitcode=None;minimum_available=mem_available()
 with (run/'predict.stdout.txt').open('wb') as out,(run/'predict.stderr.txt').open('wb') as stderr:
  try:
   stop_gate()
   def limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
   proc=subprocess.Popen(cmd,stdout=out,stderr=stderr,env=env,cwd=run,start_new_session=True,preexec_fn=limits);identity=stat(proc.pid)
   while proc.poll() is None:
    stop_gate();rss=sum(x['rss_bytes'] for x in group(proc.pid));peak=max(peak,rss);available=mem_available();minimum_available=min(minimum_available,available)
    if rss>MAX_RSS:raise RuntimeError(f'RESOURCE_GATE: owned group RSS {rss} bytes exceeds2GiB')
    if time.monotonic()-start>TIMEOUT:raise TimeoutError('Prediction600s time budget reached')
    paths=[run/'predict.stderr.txt',run/'predict.stdout.txt']+list(output.glob('*.log'));tail='\n'.join(p.read_text(errors='replace')[-16000:] for p in paths if p.exists())
    phase='Loading pinned ML models and verifying explicit database'
    if 'Annotating input genomes with DIAMOND' in tail:phase='DIAMOND low-memory annotation (author blocksize0.5)'
    if 'Processing DIAMOND output' in tail:phase='DIAMOND completed; building feature vectors'
    if 'Predicting completeness and contamination' in tail:phase='Estimating completeness/contamination with pinned models'
    progress('RUNNING',phase,worker_pid=proc.pid,worker_creation_identity=identity,group_rss_bytes=rss,linux_available_bytes=available,elapsed_seconds=time.monotonic()-start,log_path=str(run/'predict.stderr.txt'),run_directory=str(run),accession=binding['input']['accession'])
    time.sleep(.25)
   exitcode=proc.returncode
   if exitcode:raise RuntimeError('CheckM2 process exit '+str(exitcode))
  except BaseException as e:
   err=repr(e)
   if proc and proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
  finally:
   remaining=group(proc.pid) if proc else []
   if remaining and proc:
    os.killpg(proc.pid,signal.SIGKILL);time.sleep(.1);remaining=group(proc.pid)
   receipt={'started_utc':START,'ended_utc':utc(),'elapsed_prediction_seconds':time.monotonic()-start,'native_linux_process_identity':identity,'native_windows_launch':LAUNCH,'exit_code':proc.returncode if proc else None,'error':err,'sampled_peak_group_rss_bytes':peak,'sampled_min_linux_available_bytes':minimum_available,'group_rss_limit_bytes':MAX_RSS,'headroom_minimum_bytes':HEADROOM,'timeout_seconds':TIMEOUT,'owned_group_empty':not remaining,'intermediates_preserved':True,'resume_used':resume}
   save(run/'execution_receipt.json',receipt)
 if remaining:raise RuntimeError('Owned process group closure unresolved')
 intermediate=collect_intermediates(run,binding)
 if err:raise RuntimeError(err)
 report=output/'quality_report.tsv'
 if not report.exists():raise RuntimeError('INCOMPLETE_PREDICTION: quality_report.tsv absent')
 row,comp,cont=parse_quality_report(report,binding['input']['accession'])
 warnings=warning_inventory([run/'predict.stdout.txt',run/'predict.stderr.txt']+list(output.glob('*.log')))
 source=binding['input']['source_metadata_checkm'];result={'status':'RESOURCE_PILOT_COMPLETED_NOT_PRODUCTION_ACCEPTANCE','accession':row['Name'],'species':binding['input']['species'],'Completeness':comp,'Contamination':cont,'raw_prediction_row':row,'metadata_checkm_comparison_only':source,'difference_from_source_metadata':{'completeness_percentage_points':comp-source['completeness'],'contamination_percentage_points':cont-source['contamination']},'estimate_screen_95_5':comp>=95 and cont<=5,'warnings':warnings,'effective_runtime_compatibility_status':binding['runtime']['effective_runtime']['compatibility_status'],'official_numeric_controls_tested':False,'compatibility_warning_review_required':bool(warnings),'source_version':'CheckM2 1.1.0 / database3 / DIAMOND2.1.11','production_genome_acceptance':'NOT_GRANTED','overall_panel_freeze':'NOT_GRANTED','biological_absence_inference':'NONE','execution':receipt,'intermediates':intermediate}
 save(run/'result.json',result)
 manifest=[{'path':p.relative_to(run).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(run.rglob('*')) if p.is_file()]
 save(run/'manifest.json',{'files':manifest});return result

def main(args):
 if (args.run or args.mount_smoke) and os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('WAITING_RUNTIME_NAMESPACE: private read-only image runtime must be verified before prediction preflight')
 plan=prepare()
 if not args.run and not args.mount_smoke:
  progress('PREPARED','One-genome plan ready; awaiting installed runtime/model/database smoke acceptance');print(json.dumps(plan));return
 global LAUNCH
 if not args.launch_token:raise RuntimeError('Native Windows launcher token is required')
 for _ in range(100):
  p=R/'state/launch_checkm2_pilot.json'
  if p.exists():
   v=read(p)
   if v.get('token')==args.launch_token:LAUNCH=v;break
  time.sleep(.1)
 else:raise RuntimeError('No matching native Windows WSL-launch receipt')
 lock=open(R/'state/checkm2_pilot.lock','a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  stop_gate(args.mount_smoke);runtime=ready_gate(args.ready_receipt,require_effective=True);runtime['ipc_routing'],runtime['private_ipc_namespace']=ipc_runtime_gate(runtime);no_heavy_science();stop_gate(args.mount_smoke)
  if args.mount_smoke:
   target=R/'evidence/checkm2_pilot/namespace_runs'/(LAUNCH['token']+'_preflight.json')
   save(target,{'status':'READONLY_TOOL_PREFLIGHT_PASS_PENDING_CLOSURE','runtime':runtime,'scientific_prediction':'NOT_RUN','native_windows_launch':LAUNCH,'controller_sha256':sha(__file__)})
   progress('PREFLIGHT_DONE_PENDING_NAMESPACE_CLOSURE','Read-only namespace/tool preflight passed; prediction not run',preflight_receipt=str(target),scientific_prediction='NOT_RUN');return
  if not runtime.get('effective_runtime'):raise RuntimeError('WAITING_RUNTIME_EFFECTIVE: matching-version overlay, bound forward diagnostic and audited bootstrap are not yet accepted; no prediction started')
  allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,set(allowed[:2]))
  opts={'threads':2,'lowmem':True,'author_diamond_blocksize':0.5,'mode':'auto','translation_table':'author_default_auto','query_cover':80,'subject_cover':80,'identity':30,'evalue':1e-5,'timeout_seconds':600,'group_rss_bytes':MAX_RSS,'headroom_bytes':HEADROOM}
  binding={'input':plan['input'],'runtime':runtime,'options':opts};key=binding_digest(binding)
  latest=OUT/'latest.json'
  if latest.exists():
   completed=read(latest)
   if completed.get('binding_sha256')==key:
    manifest=inside(completed['manifest_path']);base=manifest.parent
    for entry in read(manifest)['files']:
     f=inside(base/entry['path'])
     if f.stat().st_size!=entry['bytes'] or sha(f)!=entry['sha256']:raise RuntimeError('Completed pilot output hash mismatch')
    namespace_path=inside(completed['namespace_execution_receipt_path'])
    if not namespace_path.exists() or sha(namespace_path)!=completed.get('namespace_execution_receipt_sha256'):raise RuntimeError('WAITING_RUNTIME_NAMESPACE: prior numeric core awaits verified namespace closure; preserve without recomputation')
    envelope=read(namespace_path)
    if envelope.get('status')!='NAMESPACE_CLOSED_AND_VERIFIED' or envelope.get('helper_exit_code')!=0 or envelope.get('inner_progress',{}).get('binding_sha256')!=key:raise RuntimeError('Prior pilot namespace completion gate failed')
    result=read(inside(completed['result_path']))
    progress('CACHED_RESULT_PENDING_NAMESPACE_CLOSURE','Verified existing one-genome pilot; no prediction process relaunched',1,result_path=completed['result_path'],completeness=result['Completeness'],contamination=result['Contamination'],binding_sha256=key,cache_reused_without_prediction=True)
    print(json.dumps({'status':'VERIFIED_REUSE_NO_PREDICTION','result_path':completed['result_path']}));return
  previous=OUT/'last_exit.json'
  if previous.exists():
   failed=read(previous)
   if failed.get('binding_sha256')==key and failed.get('status')!='COMPLETE_PILOT_ONLY':
    if not args.resume_from or failed.get('status')=='BLOCKED_RESOURCE':raise RuntimeError('BLOCKED_RESOURCE_OR_PRIOR_FAILURE: same pilot is held; no automatic repeat or budget increase')
  run=OUT/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+key[:12]);run.mkdir(parents=True,exist_ok=False);save(run/'binding.json',binding);shutil.copyfile(__file__,run/'controller_source_at_execution.py')
  save(R/'state/checkm2_pilot_owner.json',{'pid':os.getpid(),'native_linux_identity':stat(os.getpid()),'native_windows_launch':LAUNCH,'started_utc':START,'binding_sha256':key,'run_directory':str(run)})
  try:result=prediction(run,binding,args.resume_from)
  except BaseException as e:
   status='STOPPED' if isinstance(e,InterruptedError) or 'STOP requested' in str(e) else 'BLOCKED_RESOURCE' if 'RESOURCE_GATE' in str(e) else 'INTERRUPTED_BUDGET' if '600s' in str(e) else 'FAILED_RUNTIME_OR_FIT'
   obj={'status':status,'ended_utc':utc(),'error':repr(e),'binding_sha256':key,'run_directory':str(run),'source_input_untouched':True,'completeness':None,'contamination':None,'biological_absence_inference':'NONE','production_acceptance':'NOT_GRANTED'}
   save(run/'failure_receipt.json',obj)
   execution=read(run/'execution_receipt.json') if (run/'execution_receipt.json').exists() else {}
   closed=execution.get('owned_group_empty') is True
   stable_names={'binding.json','controller_source_at_execution.py','command.json','execution_receipt.json','failure_receipt.json'}
   artifacts=[{'path':f.relative_to(run).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(run.rglob('*')) if f.is_file() and (closed or f.name in stable_names)]
   save(run/'failure_manifest.json',{'files':artifacts,'all_preserved_files_stable_and_hashed':closed,'owned_group_empty':execution.get('owned_group_empty'),'unstable_intermediates_excluded_if_closure_unproven':not closed})
   save(OUT/'last_exit.json',{**obj,'failure_manifest_path':str(run/'failure_manifest.json'),'failure_manifest_sha256':sha(run/'failure_manifest.json')});progress(status,str(e),log_path=str(run/'predict.stderr.txt'),run_directory=str(run));raise
  save(OUT/'latest.json',{'result_path':str(run/'result.json'),'manifest_path':str(run/'manifest.json'),'binding_sha256':key,'result':result,'namespace_execution_receipt_path':str(R/'evidence/checkm2_pilot/namespace_runs'/(LAUNCH['token']+'.json'))});save(OUT/'last_exit.json',{'status':'COMPLETE_PILOT_ONLY','ended_utc':utc(),'run_directory':str(run),'binding_sha256':key,'production_acceptance':'NOT_GRANTED'});progress('PREDICTION_DONE_PENDING_NAMESPACE_CLOSURE','One-genome numeric estimate obtained; compatibility/quality review and cohort gates remain',1,result_path=str(run/'result.json'),completeness=result['Completeness'],contamination=result['Contamination'],group_rss_peak_bytes=result['execution']['sampled_peak_group_rss_bytes'],binding_sha256=key,manifest_path=str(run/'manifest.json'));print(json.dumps(result))
 finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

if __name__=='__main__':
 LAUNCH=None
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--mount-smoke',action='store_true');p.add_argument('--ready-receipt',default=str(R/'state/checkm2_runtime_ready.json'));p.add_argument('--launch-token');p.add_argument('--resume-from');args=p.parse_args()
 try:main(args)
 except BaseException as e:
  if 'WAITING_RUNTIME' in str(e) or 'WAITING_HEAVY_PROCESS' in str(e):progress('WAITING_READY_OR_RESOURCE',str(e))
  elif 'BLOCKED_RESOURCE_OR_PRIOR_FAILURE' in str(e):progress('HELD_PREVIOUS_ATTEMPT',str(e))
  elif 'RESOURCE_GATE' in str(e):progress('BLOCKED_RESOURCE',str(e))
  elif not STATE.exists() or read(STATE).get('status') not in ('FAILED_RUNTIME_OR_FIT','BLOCKED_RESOURCE','INTERRUPTED_BUDGET','STOPPED'):progress('FAILED_PRECHECK',repr(e))
  raise
