from pathlib import Path
import collections,hashlib,json,os,re,datetime
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
state=read(R/'state/discovery_universe_accessions.json')
assert state['complete']
rows=[]; hashes=[]
for n in range(state['page']+1):
 p=R/f'metadata/catalogs/universe_accessions/page_{n:04d}.json'; receipt=read(p.with_suffix('.json.receipt.json'))
 assert sha(p)==receipt['sha256'],p
 data=read(p); current=[r['accession'] for r in data.get('reports',[])]
 assert all(re.fullmatch(r'GC[AF]_\d{9}\.\d+',x) for x in current),p
 rows.extend(current); hashes.append({'page':n,'sha256':receipt['sha256'],'records':len(current)})
assert len(rows)==len(set(rows))==state['records']==state['reported_total']
p=R/'metadata/census_accessions.txt'; tmp=p.with_suffix('.txt.part')
with tmp.open('w',encoding='ascii',newline='\n') as f:
 for acc in sorted(rows):f.write(acc+'\n')
 f.flush();os.fsync(f.fileno())
os.replace(tmp,p)
obj={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_ACCESSION_CENSUS_COUNTS_SCHEMA_HASHES','unique_current_paired_deduplicated_accessions':len(rows),'pages':len(hashes),'sources':dict(collections.Counter(x[:3] for x in rows)),'index_sha256':sha(p),'index_path':'metadata/census_accessions.txt','page_hashes':hashes,'scope':'NCBI Lactobacillales186826 current assemblies; not biological-QC-passed genomes','source_taxonomy_assembly_count':read(R/'metadata/order_taxonomy.json')['reports'][0]['taxonomy']['counts'][0]['count'],'note':'Taxonomy service assembly count is a separately retrieved denominator; it differs from the verified Datasets assembly census. No biological inference from that difference.'}
p=R/'qc/census_validation.json';tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8');os.replace(tmp,p)
print(json.dumps({k:v for k,v in obj.items() if k!='page_hashes'}))
