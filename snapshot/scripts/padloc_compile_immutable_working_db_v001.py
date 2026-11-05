"""Create stock PADLOC compiled database as a derived copy, preserving every original."""
from pathlib import Path
import hashlib,json,time,shutil,os
R=Path(__file__).resolve().parents[1];S=R/'tools/databases/padloc_staged_20261029/v2_0_0_7f99b47';D=R/'tools/databases/padloc_compiled_v2_20261029';D.mkdir(exist_ok=False);started=time.monotonic();outputs=[]
def ref(p):return{'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for folder,ext in [('hmm','.hmm'),('cm','.cm')]:
 (D/folder).mkdir();files=sorted((S/folder).glob('*'+ext));assert len(files)==(5027 if folder=='hmm'else 21);dest=D/folder/('padlocdb'+ext);h=hashlib.sha256();origins=[]
 with dest.open('xb')as out:
  for p in files:
   if time.monotonic()-started>300:raise TimeoutError('Bounded300s model concatenation')
   if shutil.disk_usage(R).free<40*1024**3:raise RuntimeError('Backingreserve40GiB')
   part=hashlib.sha256();n=0
   with p.open('rb')as f:
    for b in iter(lambda:f.read(1024**2),b''):out.write(b);h.update(b);part.update(b);n+=len(b)
   origins.append({'path':p.relative_to(R).as_posix(),'sha256':part.hexdigest(),'bytes':n})
  out.flush();os.fsync(out.fileno())
 outputs.append({'path':dest.relative_to(R).as_posix(),'sha256':h.hexdigest(),'bytes':dest.stat().st_size,'ordered_source_files':origins})
shutil.copytree(S/'sys',D/'sys')
for n in ['hmm_meta.txt','cm_meta.txt','sys_meta.txt','LICENSE','README.md','RELEASE.md','system_info.md']:shutil.copyfile(S/n,D/n)
report={'status':'STOCK_FORMAT_DERIVED_DATABASE_COMPILED_ORIGINAL_RELEASE_UNCHANGED','source_tag':'v2.0.0','source_commit':'7f99b47b75e232b111c18626badb9ac32e8e0b5a','compilation_order':'lexicographic release filenames, allactiveHMM5027 andCM21; nooriginaldeletion','outputs':outputs,'other_files':[ref(p)for p in D.rglob('*')if p.is_file()and p.name not in ['padlocdb.hmm','padlocdb.cm']],'elapsed_seconds':time.monotonic()-started,'runtime_model_or_genome_search_executed':False};(R/'metadata/defence_parallel_preparation_20261029/PADLOC_compiled_database.json').write_text(json.dumps(report,indent=2)+'\n');print('PADLOC_DERIVED_DB_COMPILED',round(report['elapsed_seconds'],3),flush=True)
