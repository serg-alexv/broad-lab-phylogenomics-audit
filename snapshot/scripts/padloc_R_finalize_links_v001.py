from pathlib import Path,PurePosixPath
import json,os,time,hashlib
R=Path(__file__).resolve().parents[1];E=R/'work/padloc_R_case_extract_20261029';D=R/'tools/padloc_oci_case_runtime_20261029';j=json.loads((E/'payload_manifest.json').read_text());start=time.monotonic();done=[]
os.sched_setaffinity(0,{3})
for q in j['links']:
 if time.monotonic()-start>240:raise TimeoutError('Finite240s contained link finalization')
 rel=PurePosixPath(q['path'])
 if rel.is_absolute()or'..'in rel.parts or rel.parts[:2]!=('usr','local'):raise RuntimeError('Link destination leaves runtime')
 dest=D.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
 if os.path.lexists(dest):raise RuntimeError('Deferred link already exists; inspect before retry '+q['path'])
 if q['kind']=='symlink':os.symlink(q['target'],dest)
 else:
  src=PurePosixPath(q['target'].lstrip('/'))
  if src.parts[:2]!=('usr','local')or'..'in src.parts:raise RuntimeError('Hardlink source escapes runtime')
  source=D.joinpath(*src.parts)
  if not source.is_file()or not source.resolve().is_relative_to(D):raise RuntimeError('Missing/escaping hardlink source')
  os.link(source,dest)
 done.append(q)
report={'status':'EXACT_OCI_USR_LOCAL_RUNTIME_LINKS_COMPLETE_NO_R_EXECUTION','runtime':str(D.relative_to(R)),'source_manifest_sha256':hashlib.sha256((E/'payload_manifest.json').read_bytes()).hexdigest(),'regular_files':len(j['files']),'links_created':len(done),'absolute_symlinks':[q for q in done if q['kind']=='symlink'and q['target'].startswith('/')],'requires_private_usr_local_binding':True,'elapsed_seconds':time.monotonic()-start}
(E/'links_complete.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='absolute_symlinks'}),flush=True)
