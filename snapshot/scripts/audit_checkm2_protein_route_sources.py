"""Source/AST-only design audit: no CheckM2 import or runtime execution."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'tools/checkm2_runtime_pkgs'
PACK='checkm2-1.1.0-pyhdfd78af_2'
PY='python-3.12.16-h5f976f7_0_cpython'
TARGETS={PACK:[
 'site-packages/checkm2/predictQuality.py','site-packages/checkm2/modelProcessing.py',
 'site-packages/checkm2/metadata.py','site-packages/checkm2/prodigal.py',
 'site-packages/checkm2/sequenceClasses.py','site-packages/checkm2/keggData.py',
 'site-packages/checkm2/diamond.py','site-packages/checkm2/modelPostprocessing.py',
 'site-packages/checkm2/main.py','site-packages/checkm2/data/feature_ordering.json',
 'site-packages/bin/checkm2'],PY:[
 'lib/python3.12/multiprocessing/reduction.py','lib/python3.12/multiprocessing/spawn.py',
 'lib/python3.12/multiprocessing/popen_forkserver.py']}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
 files=[]
 for package,paths in TARGETS.items():
  folder=CACHE/package;metadata=folder/'info/paths.json'
  bound={r['_path']:r for r in json.loads(metadata.read_text())['paths']}
  for relative in paths:
   path=folder/relative;digest=sha(path)
   if digest!=bound[relative]['sha256'] or path.stat().st_size!=bound[relative]['size_in_bytes']:
    raise RuntimeError('Cached source/asset differs from original package payload metadata')
   files.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=digest,bytes=path.stat().st_size,
       cached_payload_metadata_sha256=sha(metadata),payload_match=True))
 package=CACHE/PACK/'site-packages/checkm2'
 features=json.loads((package/'data/feature_ordering.json').read_text())
 expected=list('ACDEFGHIKLMNPQRSTVWY')+['AALength','CDS']
 assert features['Metadata']==expected
 sizes={key:len(value) for key,value in features.items()}
 assert sizes==dict(Metadata=22,KO_Genes=19999,KO_Pathways=416,KO_Modules=757,KO_Categories=47)
 assert sum(sizes.values())==21241 and sizes['Metadata']+sizes['KO_Genes']==20021
 tree=ast.parse((package/'predictQuality.py').read_text())
 predictor=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Predictor')
 methods={node.name:node for node in predictor.body if isinstance(node,ast.FunctionDef)}
 targets=[]
 for node in ast.walk(predictor):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='Process':
   for keyword in node.keywords:
    if keyword.arg=='target' and isinstance(keyword.value,ast.Attribute):
     name=keyword.value.attr
     targets.append(dict(line=node.lineno,function_name=name,expected_class_attribute='_Predictor'+name,
         standard_method_reducer_uses_unmangled_name=True))
 assert len(targets)==4 and all(item['function_name'].startswith('__') for item in targets)
 hooks={'__getattr__','__getattribute__','__reduce__','__reduce_ex__','__getstate__'}&methods.keys()
 assert not hooks
 fields=sorted({node.targets[0].attr for node in ast.walk(predictor) if isinstance(node,ast.Assign)
     and len(node.targets)==1 and isinstance(node.targets[0],ast.Attribute)
     and isinstance(node.targets[0].value,ast.Name) and node.targets[0].value.id=='self'})
 assert not any('model' in name.lower() or 'scaler' in name.lower() for name in fields)
 omitted=['Translation_Table_Used','Coding_Density','Contig_N50','Average_Gene_Length','Genome_Size',
          'GC_Content','Total_Coding_Sequences','Total_Contigs','Max_Contig_Length']
 result=dict(status='CONDITIONAL_DESIGN_ADMISSION_SUPPORTED_PROTEIN_ROUTE_NO_BIOLOGY',
     created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verified_original_sources_and_asset=files,
     feature_counts=sizes,total_model_features=21241,neural_and_cosine_prefix_features=20021,
     metadata_order=expected,selector_zero_based_index20='AALength',
     selector_ratio='AALength / mean(general_completeness,specific_completeness)',
     same_FAA_and_DIAMOND_and_assets_imply_same_source_recipe=True,observed_numerical_equivalence=False,
     requires_exact_FAA_headers_IDs_order_case_stops_basename_and_sequences=True,
     candidate_original_CLI=['--genes','--threads','1','--extension','.faa','--lowmem'],
     gene_mode_metadata_phase_static_python_count_including_parent=4,
     gene_mode_missing_nucleotide_report_columns=omitted,
     original_runner_retained_output='Selected FAA and ten returned fields; chosen/candidate GFF and FNA deleted by unchanged author code.',
     original_runner_table_order=[4,11],default_table=11,
     table4_rule='density4-density11>0.05 AND density4>0.7',
     prodigal_mode_rule='single if totalBases>=100000 else meta; original missing/empty single-FAA fallback to meta',
     genes_output_protein_copy='output/protein_files/<basename> with no .faa extension; metadata/DIAMOND use supplied FAA path',
     Predictor_self_fields=fields,model_state_is_local_not_self=True,
     private_bound_Process_targets=targets,custom_private_lookup_or_pickle_hooks_present=False,
     forkserver_biological_transfer='NO_GO_STANDARD_PRIVATE_BOUND_METHOD_LOOKUP_AND_MAIN_REPLAY_UNRESOLVED',
     declared_engineering_arms=['DEFAULT_FORK_EXACT_MODEL_PRELOAD_UP_TO9_MANAGERS','DEFAULT_FORK_EXACT_MODEL_PRELOAD_1_MANAGER_2_HELD_CHILDREN'],
     engineering_limits=dict(sum_group_RSS_bytes=2147483648,min_Linux_available_bytes=1073741824,cpus=2,seconds_per_arm=600,PSS_replaces_RSS=False),
     requires_full_group_IPC_image_namespace_native_lock_closure=True,
     no_genome_reads_or_scientific_imports_or_mounts_by_reviewer=True,
     no_biological_retry_or_acceptance=True,no_author_algorithm_binary_model_patch=True,
     primary_documentation=['https://docs.python.org/3.12/library/multiprocessing.html#contexts-and-start-methods',
         'https://docs.python.org/3.12/library/functions.html#getattr'],
     source_controller_sha256=sha(Path(__file__)),human_review_sha256=sha(ROOT/'docs/CHECKM2_SUPPORTED_PROTEIN_ROUTE_SOURCE_REVIEW.md'))
 path=ROOT/'evidence/checkm2_runtime/supported_protein_route_source_review.json';tmp=path.with_suffix('.tmp')
 with tmp.open('w') as handle:
  json.dump(result,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
 os.replace(tmp,path)
 print(json.dumps(dict(status=result['status'],verified_files=len(files),receipt_sha256=sha(path))))


if __name__=='__main__':main()
