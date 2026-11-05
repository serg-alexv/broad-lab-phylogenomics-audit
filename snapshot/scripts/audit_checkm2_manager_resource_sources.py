"""Static original-source/resource-receipt review; executes no scientific code."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'tools/checkm2_runtime_pkgs'
TARGETS={
 'checkm2-1.1.0-pyhdfd78af_2':['site-packages/checkm2/predictQuality.py','site-packages/checkm2/modelProcessing.py','site-packages/checkm2/main.py','site-packages/checkm2/diamond.py','site-packages/checkm2/prodigal.py'],
 'python-3.12.16-h5f976f7_0_cpython':['lib/python3.12/multiprocessing/context.py','lib/python3.12/multiprocessing/managers.py','lib/python3.12/multiprocessing/popen_fork.py']}


def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
 rows=[]
 for package,files in TARGETS.items():
  folder=CACHE/package;metadata=folder/'info/paths.json'
  paths={row['_path']:row for row in json.loads(metadata.read_text())['paths']}
  for relative in files:
   path=folder/relative;digest=sha(path);bound=paths[relative]
   if digest!=bound['sha256'] or path.stat().st_size!=bound['size_in_bytes']:
    raise RuntimeError('Cached original source differs from package payload metadata')
   rows.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=digest,bytes=path.stat().st_size,package=package,
       cached_paths_metadata_sha256=sha(metadata),payload_source_hash_and_size_match=True))
 source=CACHE/'checkm2-1.1.0-pyhdfd78af_2/site-packages/checkm2/predictQuality.py'
 tree=ast.parse(source.read_text())
 functions={node.name:node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef)}
 def managers(name):
  return sorted(node.lineno for node in ast.walk(functions[name]) if isinstance(node,ast.Call)
      and isinstance(node.func,ast.Attribute) and node.func.attr=='Manager'
      and isinstance(node.func.value,ast.Name) and node.func.value.id=='mp')
 gene=managers('__run_prodigal');metadata_calls=managers('__calculate_metadata')
 assert gene==list(range(388,397)) and metadata_calls==[443]
 workflow=functions['prediction_wf']
 constructor=[node.lineno for node in ast.walk(workflow) if isinstance(node,ast.Call)
     and isinstance(node.func,ast.Attribute) and node.func.attr=='modelProcessor'
     and isinstance(node.func.value,ast.Name) and node.func.value.id=='modelProcessing']
 assert constructor==[87]
 run=ROOT/'analysis/checkm2_pilot/runs/20261026T223655Z-affb024a8930'
 receipt=run/'execution_receipt.json';observed=json.loads(receipt.read_text())
 assert observed['sampled_peak_group_rss_bytes']==3114455040
 assert observed['group_rss_limit_bytes']==2147483648
 assert observed['owned_group_empty'] is True and observed['exit_code']==-15
 report=dict(status='STATIC_SOURCE_DIAGNOSIS_NO_NEW_EXECUTION',
     created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_source_files=rows,
     static_gene_Manager_constructor_lines=gene,static_metadata_Manager_constructor_lines=metadata_calls,
     model_constructor_precedes_gene_call_at_line=87,
     gene_phase_static_expected_python_processes_including_parent={'threads1':12,'threads2':13},
     static_counts_are_not_observed_failed_run_process_counts=True,
     pinned_Linux_default_start_method='fork',actual_failed_run_start_method='NOT_RECORDED',
     observed_execution_receipt_path=receipt.relative_to(ROOT).as_posix(),observed_execution_receipt_sha256=sha(receipt),
     observed_resource_stop=observed,
     observed_per_PID_RSS_PSS_USS='NOT_COLLECTED',
     shared_page_contribution='PLAUSIBLE_SOURCE_SUPPORTED_HYPOTHESIS_NOT_MEASURED',
     supported_threads1_reduces_fixed_managers=False,
     supported_no_process_gene_mode_found=False,
     lowmem_scope='DIAMOND_BLOCKSIZE_ONLY',
     one_proposed_next_step='Parent-reviewed engineering model/Manager-only memory reproduction; no genomes; unchanged summedRSS2GiB stop; perPID RSS/PSS/private metrics and exact closure.',
     proposed_diagnostic_executed=False,scientific_import_model_mount_prediction_executed=False,
     no_budget_policy_version_or_method_change=True,
     no_retroactive_physical_memory_or_OOM_claim=True,
     source_controller_sha256=sha(Path(__file__)),
     human_review_sha256=sha(ROOT/'docs/CHECKM2_MANAGER_RESOURCE_SOURCE_REVIEW.md'))
 path=ROOT/'evidence/checkm2_runtime/manager_resource_source_review.json';temp=path.with_suffix('.tmp')
 with temp.open('w') as handle:
  json.dump(report,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
 os.replace(temp,path)
 print(json.dumps(dict(status=report['status'],original_sources_verified=len(rows),gene_Managers=len(gene),receipt_sha256=sha(path))))


if __name__=='__main__':main()
