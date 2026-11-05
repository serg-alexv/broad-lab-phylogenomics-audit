"""Read exact accepted ELF program headers; never import/load a scientific library."""
from pathlib import Path
from compression import zstd
import datetime,hashlib,json,os,struct,subprocess,tarfile,zipfile
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inspect(row,target):
 archive=R/'work/checkm2_resolution/channels'/row['channel_name']/row['subdir']/row['fn']
 if sha(archive)!=row['sha256']:raise ValueError('Accepted source archive changed')
 with zipfile.ZipFile(archive) as package:
  for name in package.namelist():
   if not name.startswith('pkg-'):continue
   with package.open(name) as compressed,zstd.open(compressed,'rb') as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
    for member in tar:
     if not member.isfile() or not target(member.name):continue
     source=tar.extractfile(member);head=source.read(64)
     if head[:6]!=b'\x7fELF\x02\x01':raise ValueError('Expected ELF64 little-endian binary')
     elf=struct.unpack('<16sHHIQQQIHHHHHH',head);offset,size,count=elf[5],elf[9],elf[10]
     if offset<64 or offset+size*count>1024**2 or size!=56:raise ValueError('Unexpected program-header bounds')
     raw=head+source.read(offset+size*count-64);headers=[]
     for n in range(count):
      values=struct.unpack_from('<IIQQQQQQ',raw,offset+n*size)
      if values[0] in (0x6474e551,3):headers.append({'type':'PT_GNU_STACK' if values[0]==0x6474e551 else 'PT_INTERP','flags':values[1],'read':bool(values[1]&4),'write':bool(values[1]&2),'execute':bool(values[1]&1),'offset':values[2],'file_bytes':values[5],'memory_bytes':values[6]})
     return {'package':row['name'],'version':row['version'],'build':row['build'],'archive_path':str(archive.relative_to(R)),'archive_sha256':row['sha256'],'archive_member':member.name,'member_bytes':member.size,'elf_machine':elf[2],'program_header_bytes_sha256':hashlib.sha256(raw).hexdigest(),'relevant_program_headers':headers,'source_member_loaded_or_executed':False}
 raise ValueError('Requested regular ELF member not found in accepted package')
def main():
 rows=json.loads((E/'resolved_packages.json').read_text());records={r['name']:r for r in rows}
 binaries=[inspect(records['libtensorflow_cc'],lambda name:'/libtensorflow_cc.so.' in name),inspect(records['python'],lambda name:name=='bin/python3.12')]
 loader='/lib64/ld-linux-x86-64.so.2';baseline=subprocess.check_output([loader,'--list-tunables'],text=True)
 candidate=subprocess.check_output(['/usr/bin/env','GLIBC_TUNABLES=glibc.rtld.execstack=2',loader,'--list-tunables'],text=True)
 result={'status':'STATIC_ELF_AND_LOADER_COMPATIBILITY_EVIDENCE','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_binaries':binaries,'host_loader_version':subprocess.check_output([loader,'--version'],text=True).splitlines()[0],'host_loader_sha256':sha(loader),'host_libc_sha256':sha('/lib/x86_64-linux-gnu/libc.so.6'),'default_execstack_query':[x for x in baseline.splitlines() if x.startswith('glibc.rtld.execstack:')],'process_local_execstack2_query':[x for x in candidate.splitlines() if x.startswith('glibc.rtld.execstack:')],'candidate_environment':{'GLIBC_TUNABLES':'glibc.rtld.execstack=2'},'official_sources':['https://sourceware.org/glibc/manual/2.42/html_node/Dynamic-Linking-Tunables.html','https://sourceware.org/pipermail/glibc-cvs/2025q2/087912.html'],'scope':'Per-process glibc compatibility mode explicitly permits executable process stacks. It changes no installed bytes or global setting. Scientific runtime imports/model loading remain untested by this audit.','tensorflow_import_performed':False,'image_mount_performed':False,'installation_performed':False}
 path=E/'loader_compatibility_source_audit.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');os.replace(temp,path)
 print(json.dumps(result))
if __name__=='__main__':main()
