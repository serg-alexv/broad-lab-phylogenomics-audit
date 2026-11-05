"""Future N5 original model-free DiamondRunner; no tool/science import on module load."""
from pathlib import Path
import argparse,os,shutil,sys,tempfile
import checkm2_phase_separated_common_N5 as c
import checkm2_protein_helpers_v001 as h
import checkm2_phase_separated_artifacts_N1 as artifacts
FORBIDDEN=('tensorflow','keras','lightgbm','sklearn','checkm2.main','checkm2.predictQuality','checkm2.modelProcessing')
def no_models():
 bad=[x for x in sys.modules if any(x==name or x.startswith(name+'.') for name in FORBIDDEN)]
 if bad:raise RuntimeError('Model-free search imported forbidden modules: '+repr(bad))
 return []
def main(args):
 request=c.read(c.path(args.request))
 if c.sha(c.path(args.request))!=args.request_sha256 or request.get('request_schema')!='TREE2_PHASE_SEPARATED_N5_DIAMOND_REQUEST_V001':raise RuntimeError('N5 DIAMOND request differs')
 plan,recipe,admitted=c.request_gate(request);h.runtime_required();prefix=c.path(request['runtime_prefix']);no_models()
 if Path(sys.executable).resolve()!=(prefix/'bin/python').resolve():raise RuntimeError('Model-free search outside accepted prefix')
 faa=c.bind(request['selected_faa']);acc=recipe['input']['accession']
 if faa.name!=acc+'.faa':raise RuntimeError('Exact versioned FAA basename required')
 annotation=c.read(c.bind(request['annotation_receipt']))
 if annotation['accession']!=acc or annotation['faa_sha256']!=c.sha(faa) or not c.unit_closed(c.read(c.bind(request['annotation_unit_execution']))):raise RuntimeError('Fresh closed own annotation required')
 proteins=h.parse_fasta(faa.read_text(),h.AA)
 if h.sequence_receipt(proteins)!=annotation['protein_sequences']:raise RuntimeError('Exact FAA sequence/header/ID inventory changed')
 database=c.bind(request['database']);binary=c.bind(request['diamond_binary'])
 if binary!=prefix/'bin/diamond' or c.sha(binary)!=recipe['runtime_binding']['tools']['diamond']['sha256'] or Path(shutil.which('diamond') or '').resolve()!=binary.resolve() or os.environ.get('PATH','').split(os.pathsep)[0]!=str(prefix/'bin'):raise RuntimeError('Pinned original DIAMOND binary required')
 for source in recipe['author_sources']:
  name=Path(source['path']).name;module=prefix/'lib/python3.12/site-packages/checkm2'/name
  if c.sha(module)!=source['sha256']:raise RuntimeError('Original author source differs before direct import: '+name)
 scratch=c.path(request['durable_scratch']);scratch.mkdir(parents=True,exist_ok=False);tempfile.tempdir=str(scratch)
 if Path(tempfile.gettempdir()).resolve()!=scratch:raise RuntimeError('Model-free ordinary tempfile path differs')
 import checkm2.diamond as original
 expected=next(x for x in recipe['author_sources'] if Path(x['path']).name=='diamond.py')
 if Path(original.__file__).resolve()!=prefix/'lib/python3.12/site-packages/checkm2/diamond.py' or c.sha(Path(original.__file__))!=expected['sha256']:raise RuntimeError('Original DiamondRunner import origin differs')
 no_models();output=c.path(request['resume_output']);output.mkdir(parents=True,exist_ok=False)
 runner=original.DiamondRunner(1,str(output),True,str(database))
 if runner.blocksize!=0.5 or runner.threads!=1 or runner.diamond_location!=str(database):raise RuntimeError('Original lowmem/search/DB controls differ')
 names=runner.run([str(faa)]);no_models()
 if names!=['DIAMOND_RESULTS.tsv']:raise RuntimeError('Unexpected direct-runner output inventory')
 result=artifacts.validate_diamond(output/'diamond_output/DIAMOND_RESULTS.tsv',acc,{x['id'] for x in proteins})
 if result['rows']==0:raise RuntimeError('NO_ANNOTATIONS_STOCK_PREDICTION_UNAVAILABLE_NOT_NEGATIVE')
 artifacts.exact_diamond_inventory(output/'diamond_output',result)
 no_models();origins={name:str(Path(module.__file__).resolve()) for name,module in list(sys.modules.items()) if name.startswith('checkm2.') and getattr(module,'__file__',None)}
 if any(not Path(value).is_relative_to(prefix) for value in origins.values()):raise RuntimeError('Direct author import escaped accepted prefix')
 c.save(c.path(args.output),{'status':'N5_ORIGINAL_DIAMOND_ARTIFACTS_VALIDATED_PENDING_UNIT_CLOSURE','accession':acc,'request_sha256':args.request_sha256,'selected_faa':request['selected_faa'],'annotation_receipt':request['annotation_receipt'],'database':request['database'],'diamond_binary':request['diamond_binary'],'raw_diamond':result,'actual_author_origins':origins,'forbidden_model_modules_loaded':no_models(),'actual_PATH':os.environ['PATH'],'actual_diamond_resolution':str(Path(shutil.which('diamond')).resolve()),'block_size':0.5,'threads':1,'original_author_source_unchanged':True,'ML_prediction_invoked':False})
 if c.sha(c.path(args.request))!=args.request_sha256:raise RuntimeError('DIAMOND request changed')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);main(p.parse_args())
