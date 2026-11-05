"""Bounded source-only review; never changes genomes, labels, selections or QC."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,urljoin
import concurrent.futures,datetime,hashlib,json,os,re,sys,time
R=Path(__file__).resolve().parents[1];D=R/'analysis/sequence_qc/d64e016face251f1/curation_source_review/3fa9c62b41bb4a54'
OUT=R/'analysis/sequence_qc/d64e016face251f1/nomenclature_source_review/priority1_first3_20261026'
STATE=R/'state/ani_nomenclature_review_progress.json'
sys.path.insert(0,str(R/'tools/python_lib'))
import requests
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def progress(detail,done=0,status='SOURCE_REVIEW_IN_PROGRESS'):
 save(STATE,{'status':status,'updated_utc':utc(),'detail':detail,'done':done,'total':3,'reviewer':'checkm2_resolve','scope':'SOURCE_ONLY_NO_RECOMPUTATION','scientific_worker_running':False,'no_label_selection_pruning_or_biological_qc_change':True,'artifact_directory':OUT.relative_to(R).as_posix()})
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.words=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.skip:self.skip-=1
 def handle_data(self,data):
  if not self.skip:self.words.append(data)
def fetch(item):
 name,url,needle=item;started=utc();p=Text();receipt={'source_id':name,'requested_url':url,'retrieved_utc':started,'scope':'SOURCE_PAGE_NOT_GENOME'}
 try:
  with requests.Session() as session:
   session.headers['User-Agent']='Tree2-WD-bounded-taxonomy-source-review/1.0'
   target=url
   for _ in range(4):
    response=session.get(target,timeout=(15,40),allow_redirects=False)
    if response.status_code in (301,302,303,307,308):
     target=urljoin(target,response.headers['Location']);host=urlparse(target).hostname or ''
     if not any(host==x or host.endswith('.'+x) for x in ('dsmz.de','ncbi.nlm.nih.gov','jcm.riken.jp','brc.riken.jp')):raise RuntimeError('Unapproved redirect host')
     continue
    break
   raw=response.content;p.feed(response.text);text=' '.join(' '.join(p.words).split());match=re.search(needle,text,re.I)
   excerpt=' '.join(text[match.start():].split()[:24]) if match else ''
   receipt.update(final_url=response.url,http_status=response.status_code,response_bytes=len(raw),response_sha256=hashlib.sha256(raw).hexdigest(),content_type=response.headers.get('Content-Type'),last_modified=response.headers.get('Last-Modified'),raw_bounded_excerpt=excerpt,excerpt_word_limit=24,needle_found=bool(match),source_readable=response.status_code==200 and bool(match),response_body_retained=False)
 except Exception as exc:receipt.update(source_readable=False,error=repr(exc))
 save(OUT/'sources'/(name+'.json'),receipt);return receipt
def main():
 if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only source review')
 # A committed source review is immutable. Resume validates it rather than refetching into it.
 if (OUT/'commit.json').exists():
  committed=read(OUT/'commit.json')
  if sha(OUT/'manifest.json')!=committed['manifest_sha256']:raise RuntimeError('Committed review manifest differs')
  for row in read(OUT/'manifest.json')['files']:
   p=OUT/row['path']
   if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Committed source artifact differs:'+row['path'])
  print(json.dumps({'status':'VERIFIED_SOURCE_ONLY_REVIEW_REUSE_NO_FETCH','manifest_sha256':committed['manifest_sha256'],'artifacts':committed['artifacts']}));return
 OUT.mkdir(parents=True,exist_ok=True);progress('Checking accepted source hashes and deterministic priority1 component selection')
 rows=read(D/'manifest.json')['files'];verified=[]
 for row in rows:
  p=D/row['path']
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Accepted source artifact changed:'+row['path'])
  verified.append(row)
 components=sorted((x for x in read(D/'component_reviews.json') if x['priority']==1),key=lambda x:x['component_id'])[:3];ids={a for c in components for a in c['members']};sources=[x for x in read(D/'source_evidence.json') if x['accession'] in ids]
 for item in sources:
  report=R/Path(item['report_path']);receipt=R/'raw'/item['accession']/'acquisition_receipt.json'
  if sha(report)!=item['report_sha256'] or sha(receipt)!=item['acquisition_receipt_sha256']:raise RuntimeError('Cached genome source changed:'+item['accession'])
  acquired=read(receipt);dna=[f for f in acquired['files'] if f['path'].endswith('.fna')]
  if len(dna)==1:
   p=R/'raw'/item['accession']/dna[0]['path']
   with p.open('rb') as f:item['cached_first_fasta_header_read_only']=f.readline().decode('ascii').strip()
   item['whole_fasta_rehashed_by_this_review']=False
 save(OUT/'accepted_inputs.json',{'created_utc':utc(),'input_manifest_sha256':sha(D/'manifest.json'),'accepted_artifacts_verified':verified,'selection':'FIRST3_PRIORITY1_COMPONENTS_SORTED_BY_COMPONENT_ID','component_ids':[c['component_id'] for c in components],'components':components,'genome_source_records':sources,'type_anchor_baseline':'ALL_SOURCE_ASSERTIONS_UNVERIFIED_SCOPE','source_only':True})
 taxa=[('streptococcus_infantarius','streptococcus-infantarius',102684),('streptococcus_ruminicola','streptococcus-ruminicola',2686210),('dellaglioa_algida','dellaglioa-algida',105612),('dellaglioa_carnosa','dellaglioa-carnosa',2995136),('vagococcus_teuberi','vagococcus-teuberi',519472),('vagococcus_martis','vagococcus-martis',1768210)]
 urls=[]
 for key,slug,taxid in taxa:
  urls.extend([(key+'_lpsn','https://lpsn.dsmz.de/species/'+slug,r'Type strain:'),(key+'_ncbi','https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id='+str(taxid)+'&mode=Info',r'type strain of')])
 urls.extend([('infantarius_dsm22960','https://www.dsmz.de/collection/catalogue/details/culture/DSM-22960',r'DSM No.'),('algida_dsm15638','https://www.dsmz.de/collection/catalogue/details/culture/DSM-15638',r'DSM No.'),('carnosa_dsm114968','https://www.dsmz.de/collection/catalogue/details/culture/DSM-114968',r'DSM No.'),('teuberi_dsm21459','https://www.dsmz.de/collection/catalogue/details/culture/DSM-21459',r'DSM No.'),('ruminicola_protologue','https://pubmed.ncbi.nlm.nih.gov/36127476/',r'94\.0'),('carnosa_protologue','https://pubmed.ncbi.nlm.nih.gov/37148784/',r'63\.2'),('teuberi_protologue','https://pubmed.ncbi.nlm.nih.gov/29306597/',r'The type strain is named'),('martis_protologue','https://pubmed.ncbi.nlm.nih.gov/28857031/',r'The type strain is'),('infantarius_protologue','https://pubmed.ncbi.nlm.nih.gov/10939646/',r'HDP 90056'),('teuberi_genome_paper','https://pmc.ncbi.nlm.nih.gov/articles/PMC5270701/',r'CP017267')])
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for result in pool.map(fetch,urls):
   results.append(result);progress(f'Retained dated source receipts {len(results)}/{len(urls)}; names/type assertions only')
 save(OUT/'source_retrieval_summary.json',{'created_utc':utc(),'sources':results,'source_count':len(results),'readable_count':sum(x['source_readable'] for x in results),'no_new_genomes_downloaded':True,'no_recomputation':True})
 progress('Primary source retrieval complete; bounded relation/type mapping review remains',status='SOURCE_PAGES_RETRIEVED_REVIEW_PENDING');print(json.dumps({'output':str(OUT),'sources':len(results),'readable':sum(x['source_readable'] for x in results),'component_ids':[c['component_id'] for c in components]}))
if __name__=='__main__':main()
