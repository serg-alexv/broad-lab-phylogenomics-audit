"""Checkpointed NCBI metadata discovery for isolated WD Tree2."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python_lib'))
HELPER=ROOT/'tools/ncbi_skill_package/skills/ncbi-datasets-skill/scripts/ncbi_datasets.py'
spec=importlib.util.spec_from_file_location('ncbi_datasets_skill',HELPER)
ncbi=importlib.util.module_from_spec(spec); spec.loader.exec_module(ncbi)
def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def sha(p): return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def atomic(p,obj):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_name(p.name+'.tmp')
 with open(tmp,'w',encoding='utf-8',newline='\n') as f:
  json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,p)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def event(kind,**kw):
 obj={'at':now(),'kind':kind,**kw}
 with open(ROOT/'logs/discovery.jsonl','a',encoding='utf-8') as f:
  f.write(json.dumps(obj)+'\n'); f.flush(); os.fsync(f.fileno())
 print(json.dumps(obj),flush=True)
def admission():
 if os.environ.get('COMPUTERNAME')!='WD': raise RuntimeError('WD-only host guard')
 if (ROOT/'state/STOP').exists(): raise InterruptedError('STOP requested')
 if shutil.disk_usage(ROOT).free<20*2**30: raise RuntimeError('Less than 20GiB free')
def get(path,params,target):
 admission(); target=ROOT/target; receipt=target.with_suffix('.json.receipt.json')
 request={'path':path,'params':params}
 if target.exists() and receipt.exists():
  r=read(receipt)
  if r['request']==request and r['sha256']==sha(target): return read(target)
  raise RuntimeError('Metadata cache request or hash mismatch: '+str(target))
 target.parent.mkdir(parents=True,exist_ok=True); part=target.with_suffix('.json.part')
 for attempt in range(1,5):
  admission()
  result=ncbi.execute({'path':path,'params':params,'save_raw':True,'raw_output_path':str(part),'max_items':1,'timeout_sec':60})
  if result.get('ok'):
   data=read(part)
   if not isinstance(data,dict): raise ValueError('Expected JSON object')
   os.replace(part,target)
   atomic(receipt,{'request':request,'at':now(),'sha256':sha(target),'bytes':target.stat().st_size,'sources':result.get('sources',[])})
   time.sleep(.4); return data
  event('metadata_retry',request_path=path[:100],attempt=attempt,error=result.get('error'))
  time.sleep(min(2**attempt,16))
 raise RuntimeError('Metadata failed after four attempts: '+str(result.get('error')))
COMMON={'page_size':1000,'filters.exclude_paired_reports':'true','filters.assembly_version':'current'}
QUALITY={'filters.exclude_atypical':'true','filters.is_metagenome_derived':'metagenome_derived_exclude'}
CATALOGS={
 'references':{**COMMON,**QUALITY,'filters.reference_only':'true'},
 'type_material':{**COMMON,**QUALITY,'filters.is_type_material':'true'},
 'closed':{**COMMON,**QUALITY,'filters.assembly_level':['complete_genome','chromosome']},
 'universe_accessions':{**COMMON,'returned_content':'ASSM_ACC'}
}
def discover(name):
 records=[]; seen=set(); token=''; page=0; total=None
 while True:
  params={**CATALOGS[name],**({'page_token':token} if token else {})}
  data=get('genome/taxon/186826/dataset_report',params,f'metadata/catalogs/{name}/page_{page:04d}.json')
  for r in data.get('reports',[]):
   acc=r['accession']
   if acc in seen: raise RuntimeError('Duplicate accession in pagination: '+acc)
   seen.add(acc); records.append(r)
  if total is None: total=int(data.get('total_count',len(records)))
  token=data.get('next_page_token','')
  atomic(ROOT/f'state/discovery_{name}.json',{'catalog':name,'records':len(records),'reported_total':total,'page':page,'complete':not bool(token),'at':now()})
  event('page',catalog=name,page=page,records=len(records),total=total,complete=not bool(token))
  if not token: break
  page+=1
 if len(records)!=total: raise RuntimeError(f'Count mismatch {len(records)} != {total}')
 return records
def load():
 out={}
 for name in ('references','type_material','closed','species_gaps','species_rescue'):
  status=ROOT/f'state/discovery_{name}.json'
  if not status.exists() or not read(status).get('complete'): continue
  allowed_pages=None
  if name in ('species_gaps','species_rescue'):
   result_file=ROOT/('state/gap_discovery_results.json' if name=='species_gaps' else 'state/rescue_discovery_results.json')
   results=read(result_file) if result_file.exists() else {}
   allowed_pages={Path(page['path']).name for result in results.values() if result.get('status') in ('RETRIEVED','NO_CURRENT_REPORTS','NO_CURRENT_ASSEMBLIES_AFTER_FILTERS') for page in result.get('pages',[])}
  for p in sorted((ROOT/f'metadata/catalogs/{name}').glob('page_*.json')):
   if '.receipt.' in p.name: continue
   if allowed_pages is not None and p.name not in allowed_pages: continue
   if read(p.with_suffix('.json.receipt.json'))['sha256']!=sha(p): raise RuntimeError('Catalog hash mismatch')
   for r in read(p).get('reports',[]): out[r['accession']]=r
 return list(out.values())
def taxonomy():
 records=load(); ids=sorted({int(r['organism']['tax_id']) for r in records}); out={}; errors=[]
 for i in range(0,len(ids),100):
  batch=ids[i:i+100]; key=hashlib.sha256(','.join(map(str,batch)).encode()).hexdigest()[:16]
  data=get('taxonomy/taxon/'+','.join(map(str,batch))+'/dataset_report',{'page_size':1000},f'metadata/taxonomy/batch_{key}.json')
  for r in data.get('reports',[]):
   if 'taxonomy' not in r:
    errors.append(r); continue
   t=r['taxonomy']; out[str(t['tax_id'])]=t
   for alias in r.get('query',[]):
    if str(alias).isdigit(): out[str(alias)]=t
  unresolved=[x for x in batch if str(x) not in out]
  if unresolved and not any(r.get('errors') for r in data.get('reports',[])):
   raise RuntimeError('Unexplained missing taxonomy response')
  event('taxonomy',retrieved=len(out),requested=len(ids))
 atomic(ROOT/'metadata/taxonomy_map.json',out)
 atomic(ROOT/'metadata/taxonomy_errors.json',errors)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['catalog','taxonomy','scope']); ap.add_argument('--catalog',choices=list(CATALOGS)); args=ap.parse_args()
 admission()
 import msvcrt
 lock=open(ROOT/'state/discovery.lock','a+b'); lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
 try: msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 except OSError: raise RuntimeError('Another discovery controller holds the OS lock')
 identity={'pid':os.getpid(),'at':now(),'argv':sys.argv,'host':os.environ.get('COMPUTERNAME')}
 atomic(ROOT/'state/discovery_process.json',identity); event('start',**identity); status='FAILED'
 try:
  if args.action=='catalog': discover(args.catalog)
  elif args.action=='taxonomy': taxonomy()
  else:
   get('taxonomy/taxon/186826/dataset_report',{},'metadata/order_taxonomy.json')
   get('taxonomy/taxon/186826/filtered_subtree',{'rank_limits':'SPECIES','levels':5},'metadata/species_subtree.json')
  status='COMPLETED'
 except InterruptedError: status='STOPPED'
 except BaseException as e: event('failed',error=repr(e)); raise
 finally:
  atomic(ROOT/f'state/discovery_exit_{args.action}_{args.catalog or "none"}.json',{**identity,'ended_at':now(),'status':status})
  lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1); lock.close()
if __name__=='__main__': main()
