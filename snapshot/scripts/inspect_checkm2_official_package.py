from pathlib import Path,PurePosixPath
import compression.zstd as zstd,io,json,tarfile,zipfile
R=Path(__file__).resolve().parents[1];E=R/'evidence/completeness_qc';out=E/'checkm2_package_inspection';out.mkdir(exist_ok=True)
rows=[]
with zipfile.ZipFile(E/'checkm2-1.1.0-pyhdfd78af_2.conda') as z:
 for name in z.namelist():
  if not name.endswith('.tar.zst'):continue
  payload=zstd.decompress(z.read(name))
  with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
   for member in tar:
    rows.append({'name':member.name,'size':member.size,'type':str(member.type)})
    if member.isfile() and (member.name.startswith('info/') or member.name.endswith(('.py','.yml','.yaml'))):
     rel=PurePosixPath(member.name)
     assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in member.name
     assert member.size<2*1024**2
     dest=out.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
(E/'checkm2_package_file_inventory.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'files':len(rows),'unpacked_bytes':sum(r['size'] for r in rows),'model_files':[r for r in rows if any(s in r['name'].lower() for s in ('model','scaler'))]}))
