"""Read source archives without installing; inventory bytes and preserve original info/notices."""
from pathlib import Path,PurePosixPath
from compression import zstd
import datetime as dt,hashlib,json,os,posixpath,shutil,tarfile,time,zipfile
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
EXPECTED='a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52'
NOTICES=R/'tools/checkm2_package_notices';CACHE=R/'work/checkm2_resolution/channels'
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(p,algorithm='sha256'):
 with p.open('rb') as f:return hashlib.file_digest(f,algorithm).hexdigest()
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def load(p):return json.loads(p.read_text())
def gate():
 if (R/'state/STOP').exists():raise KeyboardInterrupt('STOP requested')
 if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Less than40GiB reserve')
def path_ok(name):
 p=PurePosixPath(name)
 if name.startswith('/') or '\\' in name or '..' in p.parts:raise ValueError('Unsafe archive member: '+name)
 return str(p)
def preserve(stream,path,folder,size,kind):
 if size>64*1024**2:raise ValueError('Unexpected metadata/notice larger than64MiB: '+path)
 temp=folder/'objects'/(str(time.time_ns())+'.part');temp.parent.mkdir(parents=True,exist_ok=True)
 h=hashlib.sha256();written=0
 with temp.open('wb') as output:
  while chunk:=stream.read(1024**2):
   gate();written+=len(chunk);h.update(chunk);output.write(chunk)
  output.flush();os.fsync(output.fileno())
 if written!=size:raise ValueError('Truncated preserved source member')
 sha=h.hexdigest();dest=temp.with_name(sha)
 if dest.exists():
  if digest(dest)!=sha:raise ValueError('Notice object corrupt')
  temp.unlink()
 else:os.replace(temp,dest)
 return {'original_path':path,'kind':kind,'size':size,'sha256':sha,'preserved_object':str(dest.relative_to(R))}
def inspect(row):
 archive=CACHE/row['channel_name']/row['subdir']/row['fn'];gate()
 if archive.stat().st_size!=row['size'] or digest(archive)!=row['sha256'] or digest(archive,'md5')!=row['md5']:raise ValueError('Pinned archive mismatch: '+row['fn'])
 folder=NOTICES/row['fn'];receipt=folder/'inspection.json'
 if receipt.exists():
  previous=load(receipt)
  if previous['archive_sha256']==row['sha256']:
   for notice in previous['preserved_files']:
    p=R/notice['preserved_object']
    if not p.exists() or p.stat().st_size!=notice['size'] or digest(p)!=notice['sha256']:raise ValueError('Preserved notice mismatch')
   return previous
 result={'name':row['name'],'version':row['version'],'build':row['build'],'archive':str(archive.relative_to(R)),'archive_sha256':row['sha256'],'archive_md5':row['md5'],'compressed_bytes':row['size'],'regular_unpacked_bytes':0,'regular_files':0,'directories':0,'links':[],'other_members':[],'preserved_files':[],'case_collisions':[],'declared_license':row.get('license'),'license_family':row.get('license_family')}
 seen={};inventory=folder/'members.jsonl.part';folder.mkdir(parents=True,exist_ok=True)
 def consume(tar,part,output):
  for member in tar:
   gate();name=path_ok(member.name)
   if name=='.':continue
   key=name.casefold()
   if key in seen and seen[key]!=name:result['case_collisions'].append([seen[key],name])
   seen[key]=name
   detail={'path':name,'part':part,'size':member.size,'type':member.type.decode('ascii','replace'),'mode':member.mode,'linkname':member.linkname}
   output.write(json.dumps(detail)+'\n')
   if member.isfile():
    result['regular_files']+=1;result['regular_unpacked_bytes']+=member.size
    if result['regular_unpacked_bytes']>12*1024**3:raise ValueError('Archive exceeds12GiB bounded inspection')
    is_info=name.startswith('info/');base=PurePosixPath(name).name.lower()
    if is_info or any(x in base for x in ('license','licence','copyright','copying','notice')):
     with tar.extractfile(member) as source:result['preserved_files'].append(preserve(source,name,folder,member.size,'original_info' if is_info else 'payload_notice'))
   elif member.isdir():result['directories']+=1
   elif member.issym() or member.islnk():
    target=member.linkname;normal=posixpath.normpath(posixpath.join(posixpath.dirname(name),target)) if member.issym() else posixpath.normpath(target)
    result['links'].append({'path':name,'target':target,'type':'symlink' if member.issym() else 'hardlink','outside_prefix':target.startswith('/') or normal=='..' or normal.startswith('../')})
   else:result['other_members'].append(detail)
 with inventory.open('w') as out:
  if archive.name.endswith('.tar.bz2'):
   with tarfile.open(archive,'r:bz2') as tar:consume(tar,'archive',out)
  elif archive.name.endswith('.conda'):
   with zipfile.ZipFile(archive) as package:
    names=package.namelist();parts=[n for n in names if n.endswith('.tar.zst')]
    if len(parts)!=2 or not any(n.startswith('info-') for n in parts) or not any(n.startswith('pkg-') for n in parts):raise ValueError('Unexpected Conda archive layout')
    for name in names:
     path_ok(name)
     if name.endswith('.tar.zst'):
      with package.open(name) as compressed,zstd.open(compressed,'rb') as stream:
       with tarfile.open(fileobj=stream,mode='r|') as tar:consume(tar,name,out)
       while stream.read(1024**2):gate()
     else:
      with package.open(name) as source:result['preserved_files'].append(preserve(source,name,folder,package.getinfo(name).file_size,'archive_metadata'))
  else:raise ValueError('Unsupported archive type')
  out.flush();os.fsync(out.fileno())
 os.replace(inventory,folder/'members.jsonl');result['member_inventory']=str((folder/'members.jsonl').relative_to(R));result['member_inventory_sha256']=digest(folder/'members.jsonl')
 result['info_files_preserved']=sum(p['kind']=='original_info' for p in result['preserved_files']);result['inspected_utc']=utc();result['no_payload_extraction_or_installation']=True
 if not result['info_files_preserved']:raise ValueError('No original package info found')
 atomic(receipt,result);return result
def main():
 if digest(E/'resolved_packages.json')!=EXPECTED:raise ValueError('Resolved closure manifest changed')
 rows=load(E/'resolved_packages.json');assert len(rows)==133
 results=[]
 for row in rows:
  atomic(R/'state/checkm2_inspection_progress.json',{'done':len(results),'total':len(rows),'detail':'Inspecting '+row['name']+'; preserving original package information and notices','updated_utc':utc()})
  results.append(inspect(row));print(json.dumps({'at_utc':utc(),'done':len(results),'package':row['name'],'unpacked_bytes':results[-1]['regular_unpacked_bytes']}),flush=True)
 total=sum(x['regular_unpacked_bytes'] for x in results);compressed=sum(x['compressed_bytes'] for x in results)
 summary={'status':'ALL_ARCHIVES_INSPECTED','resolved_manifest_sha256':EXPECTED,'packages':results,'package_count':len(results),'compressed_bytes':compressed,'regular_unpacked_bytes':total,'conservative_cache_extraction_prefix_bytes':2*compressed+2*total,'disk_free_bytes':shutil.disk_usage(R).free,'outside_prefix_links':[{'package':x['name'],**link} for x in results for link in x['links'] if link['outside_prefix']],'case_collision_count':sum(len(x['case_collisions']) for x in results),'all_original_info_and_detected_notices_preserved_as_objects_with_original_path_mapping':True,'inspection_completed_utc':utc()}
 if shutil.disk_usage(R).free-summary['conservative_cache_extraction_prefix_bytes']<40*1024**3:raise RuntimeError('Conservative install footprint violates40GiB reserve')
 notice=E/'package_size_and_notices.json';atomic(notice,summary)
 explicit=E/'checkm2_cpu_explicit_offline.txt';tmp=explicit.with_suffix('.tmp');tmp.write_text('@EXPLICIT\n'+'\n'.join((CACHE/r['channel_name']/r['subdir']/r['fn']).as_uri()+'#'+r['md5'] for r in rows)+'\n');os.replace(tmp,explicit)
 handoff={'status':'CACHE_AND_ARCHIVE_INSPECTION_COMPLETE','resolved_manifest_sha256':EXPECTED,'package_count':len(results),'compressed_bytes':compressed,'regular_unpacked_bytes':total,'conservative_cache_extraction_prefix_bytes':summary['conservative_cache_extraction_prefix_bytes'],'notice_manifest':str(notice.relative_to(R)),'notice_manifest_sha256':digest(notice),'explicit_offline_file':str(explicit.relative_to(R)),'explicit_offline_file_sha256':digest(explicit),'cache_receipt':'evidence/checkm2_runtime/package_cache_receipt.json','cache_receipt_sha256':digest(E/'package_cache_receipt.json'),'outside_prefix_links_count':len(summary['outside_prefix_links']),'case_collision_count':summary['case_collision_count'],'environment_installed':False,'biological_qc_run':False,'completed_utc':utc()}
 atomic(E/'cache_handoff.json',handoff);atomic(R/'state/checkm2_inspection_progress.json',{'done':len(results),'total':len(rows),'detail':'All133archives inspected; cache handoff available','updated_utc':utc()});print(json.dumps(handoff),flush=True)
if __name__=='__main__':
 try:main()
 except KeyboardInterrupt:raise SystemExit(130)
