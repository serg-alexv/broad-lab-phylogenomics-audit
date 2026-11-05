"""Static source audit only: parse text/AST, never import CheckM2 or models."""
from pathlib import Path
import ast,datetime,hashlib,json,os,uuid

R=Path(__file__).resolve().parents[1]
OUT=R/'evidence/checkm2_runtime/bound_self_source_review.json'

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def payload(package,relative):
 cache=R/'tools/checkm2_runtime_pkgs'/package
 metadata=cache/'info/paths.json';rows=read(metadata)['paths']
 matches=[x for x in rows if x['_path']==relative]
 if len(matches)!=1:raise RuntimeError('Official payload metadata entry is ambiguous')
 row=matches[0];p=cache/relative
 if p.stat().st_size!=row['size_in_bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Official source payload differs')
 return p,{'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'official_paths_metadata_sha256':sha(metadata)}

def main():
 checkm='checkm2-1.1.0-pyhdfd78af_2';python='python-3.12.16-h5f976f7_0_cpython'
 paths={};sources=[]
 for key,package,path in [('predictor',checkm,'site-packages/checkm2/predictQuality.py'),('models',checkm,'site-packages/checkm2/modelProcessing.py'),('packaged_entry',checkm,'site-packages/bin/checkm2'),('spawn',python,'lib/python3.12/multiprocessing/spawn.py'),('forkserver',python,'lib/python3.12/multiprocessing/forkserver.py'),('reduction',python,'lib/python3.12/multiprocessing/reduction.py')]:
  paths[key],receipt=payload(package,path);sources.append(receipt)
 source=paths['predictor'].read_text();tree=ast.parse(source)
 predictor=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Predictor')
 methods={n.name:n for n in predictor.body if isinstance(n,ast.FunctionDef)}
 fields=[];targets=[];model_local=[]
 for name,method in methods.items():
  for node in ast.walk(method):
   if isinstance(node,ast.Assign):
    for target in node.targets:
     if isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=='self':fields.append({'method':name,'field':target.attr,'line':node.lineno,'expression':ast.unparse(node.value)})
     if isinstance(target,ast.Name) and target.id=='modelProc':model_local.append({'method':name,'line':node.lineno,'expression':ast.unparse(node.value),'assignment_target':'LOCAL_NAME_modelProc'})
   if isinstance(node,ast.Call) and ast.unparse(node.func)=='mp.Process':
    target=next((k.value for k in node.keywords if k.arg=='target'),None)
    targets.append({'method':name,'line':node.lineno,'target':ast.unparse(target),'argument_expression':next((ast.unparse(k.value) for k in node.keywords if k.arg=='args'),None)})
 assert len(model_local)==1 and model_local[0]['line']==87
 assert not any('modelProc' in x['field'] or 'modelProcessor(' in x['expression'] for x in fields)
 assert len(targets)==4 and all(x['target'].startswith('self.') for x in targets)
 special=[name for name in methods if name in ('__getstate__','__setstate__','__reduce__','__reduce_ex__')]
 assert not special and not predictor.bases
 bootstrap=R/'scripts/checkm2_effective_bootstrap.py'
 accepted=read(R/'evidence/checkm2_runtime/sklearn161_effective_runtime_validated.json')
 if sha(bootstrap)!=accepted['launch_protocol']['bootstrap_sha256']:raise RuntimeError('Accepted bootstrap source differs')
 result={'status':'STATIC_BOUND_SELF_AND_CHILD_IMPORT_REVIEW_ONLY','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_payloads':sources,'predictor_self_assignments':fields,'model_processor_assignment':model_local,'bound_process_targets':targets,'predictor_custom_pickle_hooks':special,'predictor_base_classes':[],'model_weights_explicitly_in_predictor_self':False,'interpretation':'The modelProc object is a local workflow variable, not a Predictor field. Fork copies the process address space regardless; forkserver/spawn serializes the bound Predictor state and arguments instead. Static state is not a runtime pickle/worker test.','module_import_chain':{'predictQuality.py:1':'from checkm2 import modelProcessing','modelProcessing.py:11,18-22':'module-scope LightGBM, Keras, load_model and MinMaxScaler imports; model file loading is in constructor38-43','multiprocessing/reduction.py:206-210':'bound method reduction retrieves method from its self object','multiprocessing/spawn.py:126-135,192-202,243-246,275-300':'preparation and __main__ replay precede process-object unpickling','accepted_bootstrap.py':'runpy.run_path(entry,run_name=__main__) changes current main module during unchanged CheckM2 execution'},'accepted_bootstrap_sha256':sha(bootstrap),'forkserver_assessment':{'python_library_supported':True,'checkm2_cli_option_exposed':False,'predictor_model_payload_pickle_blocker_found':False,'actual_writer_worker_serialization_tested':False,'actual_cli_child_import_origins_tested':False,'full_checkm2_forkserver_compatibility':'UNVALIDATED','manager_only_diagnostic_cannot_validate':['Predictor bound writer/worker serialization','fresh child module imports and effective sklearn origins','writer/worker RSS including ML module imports','gene/metadata/numerical equivalence or biological quality'],'main_replay_caveat':'A stdlib-only engineering entrypoint differs from CheckM2 execution under nested runpy. Fresh children can replay the current entrypoint before unpickling; the official packaged entry imports checkm2.main outside its main guard. The installed prefix entry bytes were not read outside the accepted runtime.','no_hidden_policy_substitution':'No PSS-based guard, author patch, process-start change in biology or biological retry is admitted.'},'scientific_imports_or_models_or_prediction_executed':False,'author_source_modified':False,'source_audit_sha256':sha(__file__)}
 temp=OUT.with_name(OUT.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');os.replace(temp,OUT)
 print(json.dumps({'status':result['status'],'self_assignment_count':len(fields),'bound_target_count':len(targets),'receipt_sha256':sha(OUT)}))

if __name__=='__main__':main()
