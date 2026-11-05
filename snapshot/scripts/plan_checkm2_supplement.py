"""Supplement current channel index with pinned official historical CPU records."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,os,sys
R=Path(__file__).resolve().parents[1];W=R/'work/checkm2_resolution';E=R/'evidence/checkm2_runtime'
sys.path.insert(0,str(R/'tools/python_lib'))
import requests
RELEASES=[('libtensorflow_cc','2.19.1'),('libtensorflow_framework','2.19.1'),
          ('tensorboard','2.19.0'),('libml_dtypes-headers','0.5.4'),('_x86_64-microarch-level','3')]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fetch(pair):
 name,version=pair;url=f'https://api.anaconda.org/release/conda-forge/{name}/{version}'
 target=W/'anaconda_api'/f'{name}_{version}.json';target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():data=json.loads(target.read_text())
 else:
  response=requests.get(url,timeout=(15,90),allow_redirects=False);response.raise_for_status();data=response.json()
  target.write_bytes(response.content)
 return name,version,data,{'url':url,'path':str(target.relative_to(R)),'sha256':sha(target),'bytes':target.stat().st_size}
def main():
 results=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(fetch,RELEASES));indexes={};sources=[];added=[]
 for name,version,data,source in results:
  sources.append(source)
  for item in data['distributions']:
   subdir,fn=item['basename'].split('/',1)
   if subdir not in ('linux-64','noarch') or 'main' not in item.get('labels',[]):continue
   attrs=item['attrs'];build=attrs['build']
   if name=='libtensorflow_cc' and build!='cpu_ha812d39_5':continue
   if name=='libtensorflow_framework' and build!='cpu_h0a5eddc_5':continue
   if name=='_x86_64-microarch-level' and build!='5_skylake':continue
   if not item.get('sha256'):raise RuntimeError('Missing official SHA256 '+fn)
   if subdir not in indexes:
    path=W/'channels/conda-forge'/subdir/'repodata.json';indexes[subdir]=(path,json.loads(path.read_text()))
   rec={k:attrs[k] for k in ('arch','build','build_number','depends','license','platform','subdir','timestamp','constrains','track_features','noarch') if k in attrs}
   rec.update(name=name,version=version,sha256=item['sha256'],md5=item['md5'],size=item['size'],subdir=subdir)
   group='packages.conda' if fn.endswith('.conda') else 'packages'
   indexes[subdir][1][group][fn]=rec
   added.append({'subdir':subdir,'fn':fn,'sha256':item['sha256'],'size':item['size'],'source':source['url']})
 channels=[]
 for subdir,(path,data) in indexes.items():
  tmp=path.with_suffix('.json.tmp')
  with tmp.open('w',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'));f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
  base=R/'work/conda_channels/conda-forge'/subdir/'repodata.json'
  channels.append({'path':str(path.relative_to(R)),'base_sha256':sha(base),'derived_sha256':sha(path)})
 receipt={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'current_repodata omits required historical dependencies, not package incompatibility',
          'sources':sources,'added_records':added,'derived_channels':channels,'network':'Windows HTTPS only official api.anaconda.org; no redirects'}
 (E/'metadata_supplement.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'added_records':len(added),'derived_subdirs':list(indexes),'sources':len(sources)}))
if __name__=='__main__':main()
