"""Pinned runtime/model loading smoke only; no genome-quality prediction."""
from pathlib import Path
import argparse,datetime as dt,hashlib,importlib,json,os,subprocess,sys
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,obj):
 temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(obj,indent=2)+'\n');os.replace(temp,p)

def verified_payload_paths(pins):
 # Read the unchanged info/paths.json saved from the SHA-verified official archive.
 handoff=json.loads((E/'cache_handoff.json').read_text())
 notices=R/handoff['notice_manifest']
 if sha(notices)!=handoff['notice_manifest_sha256']:raise RuntimeError('Original package inventory hash mismatch')
 inventory=json.loads(notices.read_text())
 package=next(x for x in inventory['packages'] if x['name']=='checkm2')
 if package['archive_sha256']!=pins['checkm2']['sha256']:raise RuntimeError('CheckM2 package archive identity mismatch')
 row=next(x for x in package['preserved_files'] if x['original_path']=='info/paths.json')
 original=R/row['preserved_object']
 if sha(original)!=row['sha256']:raise RuntimeError('Original package paths metadata hash mismatch')
 paths={x['_path']:x for x in json.loads(original.read_text())['paths']}
 return paths,{'package_archive_sha256':package['archive_sha256'],'original_paths_sha256':row['sha256'],
               'original_paths_object':row['preserved_object']}
def main():
 a=argparse.ArgumentParser();a.add_argument('--cli',action='store_true');a.add_argument('--models',action='store_true');a.add_argument('--database');args=a.parse_args()
 if os.environ.get('TREE2_PRIVATE_NAMESPACE_VERIFIED')!='1':raise RuntimeError('Private namespace required')
 prefix=Path(sys.prefix);assert prefix.resolve()==(R/'tools/checkm2_env').resolve()
 pins={x['name']:x for x in json.loads((E/'resolved_packages.json').read_text())}
 report={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.version,'prefix':str(prefix),'scientific_prediction':'NOT_RUN',
         'smoke_script_sha256':sha(__file__),'upstream_warning_behavior':'Unmodified scientific source; compatibility warnings retained in stderr'}
 report['runtime_environment_overrides']={'GLIBC_TUNABLES':os.environ['GLIBC_TUNABLES']} if os.environ.get('GLIBC_TUNABLES') else {}
 report['process_stack_mapping']=[line for line in Path('/proc/self/maps').read_text().splitlines() if '[stack]' in line]
 if args.cli:
  commands=[[str(prefix/'bin/checkm2'),'--version'],[str(prefix/'bin/checkm2'),'--help'],[str(prefix/'bin/diamond'),'version'],[str(prefix/'bin/prodigal'),'-v']]
  rows=[]
  for cmd in commands:
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
   print(r.stdout,flush=True);print(r.stderr,file=sys.stderr,flush=True)
   if r.returncode:raise RuntimeError(f'CLI smoke failed:{cmd[0]} exit{r.returncode}')
   rows.append({'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  from checkm2.version import __version__
  assert __version__=='1.1.0';assert '2.1.11' in rows[2]['stdout']+rows[2]['stderr']
  report.update(status='PASS_CLI_SMOKE',checkm2_version=__version__,commands=rows)
  save(E/'cli_smoke_receipt.json',report)
 elif args.models:
  libs={}
  for mod,package in [('numpy','numpy'),('pandas','pandas'),('scipy','scipy'),('sklearn','scikit-learn'),('lightgbm','lightgbm'),('tensorflow','tensorflow-base'),('keras','keras')]:
   value=importlib.import_module(mod);version=value.__version__;expected=pins[package]['version']
   if version!=expected:raise RuntimeError(f'{mod} actual{version} !=pin{expected}')
   libs[mod]={'version':version,'source':str(Path(value.__file__))}
   print(json.dumps({'imported':mod,'version':version}),flush=True)
  import tensorflow as tf
  if os.environ.get('TF_NUM_INTRAOP_THREADS')!='2' or os.environ.get('TF_NUM_INTEROP_THREADS')!='1':raise RuntimeError('TensorFlow thread environment not pinned')
  if tf.config.list_physical_devices('GPU'):raise RuntimeError('Unexpected GPU device in CPU-only smoke')
  from checkm2.defaultValues import DefaultValues
  from checkm2.version import __version__
  import pandas as pd
  version_path=Path(DefaultValues.VERSION_PATH)/f'version_hashes_{__version__}.json'
  table=pd.read_json(version_path);allowed=set(table['sha256'].astype(str));model_files=[]
  payload,provenance=verified_payload_paths(pins)
  package_root=Path(importlib.import_module('checkm2').__file__).parent.resolve()
  for path in DefaultValues.EXTERNAL_FILES_TO_VERIFY:
   p=Path(path);digest=sha(p)
   original_path='site-packages/checkm2/'+p.resolve().relative_to(package_root).as_posix()
   expected=payload[original_path]
   if digest!=expected['sha256'] or p.stat().st_size!=expected['size_in_bytes']:
    raise RuntimeError('Program-bundled data/model differs from official archive:'+str(p))
   model_files.append({'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':digest,
                       'official_package_path':original_path,'official_package_integrity':'PASS_SHA256_AND_SIZE',
                       'author_hash_table':'MATCH' if digest in allowed else 'HASH_ABSENT_FROM_AUTHOR_TABLE'})
  from checkm2.modelProcessing import modelProcessor
  loaded=modelProcessor(threads=2)
  if loaded.general_model_comp is None or loaded.model_cont is None or loaded.specific_model_comp_nn is None or loaded.minmax_scaler is None:raise RuntimeError('Incomplete model/scaler load')
  from checkm2.versionControl import VersionControl
  if not VersionControl().checksum_test_genomes():raise RuntimeError('Author test-genome package checksums failed')
  db=Path(args.database).resolve()
  if not db.is_relative_to(R):raise RuntimeError('Database outside project')
  if not VersionControl().checksum_version_validate_DIAMOND(str(db)):raise RuntimeError('Author database compatibility/hash gate failed')
  report.update(status='PASS_IMPORT_AND_MODEL_LOADING_SMOKE',imports=libs,model_files=model_files,
                original_package_provenance=provenance,
                model_payload_integrity='PASS_OFFICIAL_ARCHIVE_PATH_SHA256',
                author_model_table_status='PARTIAL_STALE_AUTHOR_METADATA' if any(x['author_hash_table']!='MATCH' for x in model_files) else 'ALL_MODEL_HASHES_MATCH',
                author_version_table_sha256=sha(version_path),bundled_test_genome_checksum='PASS',
                author_database_compatibility='PASS',database_path=db.relative_to(R).as_posix(),database_sha256=sha(db),
                lightgbm_general_features=loaded.general_model_comp.num_feature(),lightgbm_contamination_features=loaded.model_cont.num_feature(),
                keras_input_shape=str(loaded.specific_model_comp_nn.input_shape),keras_output_shape=str(loaded.specific_model_comp_nn.output_shape),
                scaler_type=type(loaded.minmax_scaler).__name__,GPU_devices=[])
  save(E/'runtime_smoke_receipt.json',report)
 else:raise ValueError('Specify exactlyone smoke mode')
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
