"""Hash Linux analysis files and symlink targets without following links."""
from pathlib import Path
import datetime,hashlib,json,os
R=Path(__file__).resolve().parents[1]
rows=[]
for parent,dirs,files in os.walk(R/'analysis',followlinks=False):
 for name in list(dirs)+files:
  p=Path(parent)/name;rel=p.relative_to(R).as_posix()
  if p.is_symlink():
   target=os.readlink(p);payload=target.encode('utf-8')
   rows.append({'path':rel,'kind':'symlink','target':target,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'checksum_scope':'UTF8 link target; target is not followed'})
  elif p.is_file():
   with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
   rows.append({'path':rel,'kind':'file','bytes':p.stat().st_size,'sha256':digest})
obj={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'analysis only; no symlink traversal','artifacts':sorted(rows,key=lambda r:r['path'])}
p=R/'manifests/linux_analysis_files.json';tmp=p.with_suffix('.json.tmp')
with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.replace(tmp,p)
print(json.dumps({'linux_analysis_manifest':str(p),'artifacts':len(rows),'symlinks':sum(r['kind']=='symlink' for r in rows)}))
