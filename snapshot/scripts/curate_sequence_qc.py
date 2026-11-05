from pathlib import Path
import collections,datetime,hashlib,json,os,shutil
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,o):
 p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
x=read(R/'analysis/sequence_qc/latest.json');D=Path(x['commit_path']);D=D.parent
if os.name=='nt':D=Path(str(D).replace('\\mnt\\c\\','C:\\').replace('/mnt/c/','C:/'))
c=read(D/'commit.json');original=R/'scripts/sequence_taxonomy_qc.py';snapshot=D/'controller_source_at_execution.py'
if not snapshot.exists():
 if sha(original)!=c['script_sha256']:raise RuntimeError('Cannot recover exact controller source')
 shutil.copyfile(original,snapshot)
if sha(snapshot)!=c['script_sha256']:raise RuntimeError('Controller source snapshot mismatch')
f=read(D/'full_cohort/pair_review_flags.json')
strict=[r for r in f if r['ANI']>=99.99 and min(r['AF_reference'],r['AF_query'])>=95]
parents={}
def find(a):
 parents.setdefault(a,a)
 if parents[a]!=a:parents[a]=find(parents[a])
 return parents[a]
def join(a,b):
 a=find(a);b=find(b)
 if a!=b:parents[max(a,b)]=min(a,b)
for r in strict:join(r['reference'],r['query'])
groups=collections.defaultdict(list)
for a in parents:groups[find(a)].append(a)
cur={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'REVIEW_ONLY_NO_PRUNING_OR_LABEL_OVERRIDE','strict_near_duplicate_pairs':len(strict),'strict_thresholds':{'ANI_min':99.99,'both_AF_min':95},'connected_components':[sorted(v) for v in groups.values()],'strict_pairs':strict,'all_shared_DNA_review_pairs':len(f),'within_label_low_ANI_review':[r for r in f if 'WITHIN_LABEL_LOW_ANI_REVIEW' in r['review_flags']],'limitations':['Connected components do not imply each pair is directly linked.','High ANI does not establish identical accessory or defence content.','No genome is removed and no taxonomic label is changed.','Completeness/contamination and final panel acceptance remain NOT_RUN.']}
save(D/'full_cohort/strict_duplicate_curation.json',cur)
rows=[{'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json']
save(D/'artifact_manifest.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Sequence-QC outputs and exact controller source; no raw genome rewrite','files':rows})
print(json.dumps({'strict_pairs':len(strict),'components':len(groups),'files_hashed':len(rows),'directory':str(D)}))
