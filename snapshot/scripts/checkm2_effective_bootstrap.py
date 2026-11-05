"""Verified matching-sklearn preload before the unchanged CheckM2 entrypoint."""
from pathlib import Path
import importlib.metadata,json,os,runpy,sys
import checkm2_runtime_image as image
R=image.R;E=image.E;SPEC=E/'sklearn161_effective_runtime.json'

def specification():
 prep=image.read(E/'sklearn161_overlay_preparation.json')
 if image.sha(SPEC)!=prep['effective_runtime_manifest_sha256']:raise RuntimeError('Static effective-runtime manifest changed')
 spec=image.read(SPEC)
 if image.sha(R/spec['base_ready_receipt']['path'])!=spec['base_ready_receipt']['sha256']:raise RuntimeError('Base candidate changed')
 return spec
def bind_overlay(ctx):
 spec=specification();root=Path(spec['overlay']['root_linux']);manifest=R/spec['overlay']['manifest_path']
 if root.resolve()!=root or not root.is_relative_to(R) or not root.is_dir():raise RuntimeError('Overlay root path/type differs')
 if image.sha(manifest)!=spec['overlay']['manifest_sha256']:raise RuntimeError('Overlay payload manifest changed')
 image.command(['mount','--bind',root,root]);ctx.mounts.append(root);image.command(['mount','-o','remount,bind,ro',root])
 if not os.statvfs(root).f_flag&os.ST_RDONLY:raise RuntimeError('Overlay binding is not read-only')
 data=image.read(manifest)
 for row in data['files']:
  p=root/row['path']
  if p.resolve()!=p or not p.is_relative_to(root) or p.stat().st_size!=row['bytes'] or image.sha(p)!=row['sha256']:raise RuntimeError('Overlay file differs:'+row['path'])
 ctx.result['effective_overlay']={'root':str(root),'readonly':True,'manifest_path':spec['overlay']['manifest_path'],'manifest_sha256':spec['overlay']['manifest_sha256'],'files_verified':len(data['files']),'effective_static_manifest_path':SPEC.relative_to(R).as_posix(),'effective_static_manifest_sha256':image.sha(SPEC)}
 ctx.result['mounts'][str(root)]=image.command(['findmnt','-T',root,'-n','-o','TARGET,SOURCE,FSTYPE,VFS-OPTIONS,FS-OPTIONS'])
 image.save(ctx.receipt,ctx.result);return spec
def provenance(stage):
 import sklearn
 spec=specification();site=Path(spec['overlay']['site_packages_linux']);origin=Path(sklearn.__file__).resolve()
 if sklearn.__version__!='1.6.1' or not origin.is_relative_to(site):raise RuntimeError('Effective sklearn version/origin differs')
 for path in sklearn.__path__:
  if not Path(path).resolve().is_relative_to(site):raise RuntimeError('Effective sklearn package search path escapes overlay')
 mods={}
 for name,module in list(sys.modules.items()):
  if name=='sklearn' or name.startswith('sklearn.'):
   f=getattr(module,'__file__',None)
   if f:
    p=Path(f).resolve()
    if not p.is_relative_to(site):raise RuntimeError('Mixed sklearn module origins:'+name)
    mods[name]=str(p)
 dist=importlib.metadata.PathDistribution(site/'scikit_learn-1.6.1.dist-info')
 if dist.version!='1.6.1':raise RuntimeError('Pinned overlay dist-info differs')
 return {'stage':stage,'version':sklearn.__version__,'module_origin':str(origin),'package_path':list(sklearn.__path__),'overlay_distribution_version':dist.version,'generic_metadata_discovery_version':importlib.metadata.version('scikit-learn'),'imported_sklearn_origins':mods}
def preload_and_verify():
 image.private();spec=specification()
 if os.environ.get('TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED')!='1':raise RuntimeError('Read-only runtime guard missing')
 for key,value in spec['required_runtime_environment'].items():
  if os.environ.get(key)!=value:raise RuntimeError('Effective launch environment differs:'+key)
 if not os.statvfs(spec['overlay']['root_linux']).f_flag&os.ST_RDONLY:raise RuntimeError('Overlay is writable')
 import sklearn
 from sklearn.preprocessing import MinMaxScaler
 before=provenance('PRELOADED_BEFORE_UNCHANGED_CHECKM2_MAIN')
 import checkm2.main
 after=provenance('AFTER_UPSTREAM_BASE_SITE_PACKAGES_PREPEND')
 return {'before':before,'after':after,'environment':spec['required_runtime_environment'],'bootstrap_sha256':image.sha(__file__),'base_image_sha256':spec['base_image']['sha256'],'static_effective_manifest_sha256':image.sha(SPEC)}
def main():
 proof=preload_and_verify()
 receipt=os.environ.get('TREE2_EFFECTIVE_ORIGIN_RECEIPT')
 if receipt:
  p=Path(receipt)
  if not p.resolve().is_relative_to(R):raise RuntimeError('Origin receipt outside project')
  image.save(p,proof)
 if len(sys.argv)<2 or sys.argv[1]!='checkm2':raise ValueError('Expected checkm2 then unchanged CLI arguments')
 entry=image.PREFIX/'bin/checkm2';sys.argv=[str(entry),*sys.argv[2:]]
 runpy.run_path(str(entry),run_name='__main__')
if __name__=='__main__':main()
