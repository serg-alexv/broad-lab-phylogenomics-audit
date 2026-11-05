"""Static v002 module-domain correction; source/data only, no runtime imports."""
from pathlib import Path
import ast,copy,hashlib,json,os
R=Path(__file__).resolve().parents[1]
OLD=R/"metadata/checkm2_feature_schema_v001.json"
OUT=R/"metadata/checkm2_feature_schema_v002.json"
OLD_SHA="2be7bda6589a445a8b70023d9cf84ffadc76a380db112b34a70ce0094fc53adb"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze(path,data):
 if path.exists():
  if path.read_bytes()!=data:raise RuntimeError("Immutable proposed v002 differs")
 else:
  temp=path.with_suffix(path.suffix+".pending")
  with temp.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
def main():
 if sha(OLD)!=OLD_SHA:raise RuntimeError("Original v001 changed")
 old=json.loads(OLD.read_text());rows=old["source_files_and_assets"]
 for row in rows:
  p=R/row["cached_path"]
  if sha(p)!=row["sha256"] or p.stat().st_size!=row["bytes"]:raise RuntimeError("Original package source/data changed")
 byname={Path(row["cached_path"]).name:R/row["cached_path"] for row in rows}
 kegg_path=byname["keggData.py"];text=kegg_path.read_text();tree=ast.parse(text)
 klass=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="KeggCalculator")
 methods={x.name:x for x in klass.body if isinstance(x,ast.FunctionDef)}
 def output_assignment(method):
  loop=next(x for x in methods[method].body if isinstance(x,ast.For))
  return next(x for x in loop.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=="KO_gene_data" for t in x.targets))
 group=output_assignment("calculate_KO_group");module=output_assignment("calculate_module_completeness")
 group_names={n.id for n in ast.walk(group.value) if isinstance(n,ast.Name)};module_names={n.id for n in ast.walk(module.value) if isinstance(n,ast.Name)}
 assert "presence_absence_subset" in group_names and "presence_absence_subset" not in module_names and "KO_gene_data" in module_names
 modules=json.loads(byname["module_definitions.json"].read_text());order=json.loads(byname["feature_ordering.json"].read_text());kos=set(order["KO_Genes"])
 assert list(modules)==order["KO_Modules"]
 missing=[(name,value) for name,values in modules.items() for value in values if value not in kos]
 assert len(missing)==14 and not any(value in set(modules)|{"Name"} for name,value in missing)
 def raw_mean(name,counts):
  members=modules[name];return sum(counts.get(x,0) for x in members if x in kos)/len(members)
 first=next(iter(modules));all_two={k:2 for k in kos};two=raw_mean(first,all_two)
 assert two==2.0
 clipped=sum(1 for x in modules[first] if x in kos)/len(modules[first]);assert clipped==1.0
 duplicate=next(x for x in modules[first] if modules[first].count(x)>1);dup_count=modules[first].count(duplicate);denom=len(modules[first]);dup_value=raw_mean(first,{duplicate:denom})
 assert dup_value==dup_count and dup_value>1
 missing_module=missing[0][0];retained=sum(x in kos for x in modules[missing_module]);missing_value=raw_mean(missing_module,{k:1 for k in kos})
 assert missing_value==retained/len(modules[missing_module]) and missing_value<1
 new=copy.deepcopy(old);new["schema"]="TREE2_CHECKM2_ORDERED_FEATURE_SCHEMA_V2";new["status"]="PROPOSED_STATIC_MODULE_DOMAIN_CORRECTION_NO_PRESERVED_RUN_READ"
 for group_spec in new["groups"]:
  if group_spec["name"]=="KO_Modules":
   group_spec["logical_type"]="NONNEGATIVE_REAL_COPY_COUNT_MEAN"
   group_spec["allowed_numeric_domain"]="finite real >=0; may exceed1; no universal upper bound1"
   group_spec["nominal_raw_dtype"]="real numeric mean of raw integer KO copy counts"
 new["module_semantics"]="sum original raw KO counts with membership multiplicity, after excluding missing KO identifiers, divided by original prefilter membership-list length; temporary clipped copy is unused in result"
 new["module_algorithm"]={"raw_KO_counts_used":True,"clipped_temporary_used_in_result":False,"original_membership_multiplicity_preserved":True,"original_prefilter_denominator_preserved":True,"universal_upper_bound_one":False,"missing_KO_references_to_Name_or_previous_module_columns":False,"optional_independent_validation":"recompute from bound raw KO count features and original module lists/denominators without clipping or rewriting values"}
 new["source_domain_proof"]={"kegg_source_sha256":sha(kegg_path),"pathway_category_result_line":group.lineno,"pathway_category_result":ast.get_source_segment(text,group),"module_result_line":module.lineno,"module_result":ast.get_source_segment(text,module),"synthetic_semantic_fixtures":{"all_raw_counts_two":{"module":first,"original_result":two,"clipped_result_not_used_by_source":clipped},"duplicate_memberships":{"module":first,"KO":duplicate,"occurrences":dup_count,"original_denominator":denom,"single_KO_count":denom,"result":dup_value},"missing_KO_prefilter_denominator":{"module":missing_module,"original_denominator":len(modules[missing_module]),"retained_occurrences":retained,"all_retained_counts_one_result":missing_value}},"fixture_inputs":"synthetic dictionaries from official source/data; no genome/FAA/pickle/model imports or reads"}
 new["parser_requirements"]=["bound controlled artifact SHA before reading pickle","one exact expected Name row","exact full ordered columns; no duplicate/missing/extra/reordered columns","Metadata/KO_Genes finite nonnegative integral counts; KO_Pathways/KO_Categories finite within[0,1]; KO_Modules finite nonnegative raw-copy-count means and may exceed1","reject nulls and nonnumeric/bool/complex values; do not fill missing columns with zero","preserve actual numeric vectors; no clipping or normalization to satisfy validator","canonical ordered float64 values are distinct from raw pickle bytes","no model-accuracy or biological acceptance from schema or vectors alone"]
 new["supersedes_module_domain_only"]={"schema_path":OLD.relative_to(R).as_posix(),"sha256":OLD_SHA,"reason":"v001 wrongly used presence-absence semantics for raw-count module calculation","v001_and_failed_validator_preserved":True,"actual_preserved_run_artifacts_opened":False,"posthoc_runtime_validation_authorized_or_executed":False}
 new["builder_sha256"]=sha(__file__);new["human_summary_sha256"]=sha(R/"docs/CHECKM2_ORDERED_FEATURE_SCHEMA_V002.md")
 assert new["ordered_dataframe_columns"]==old["ordered_dataframe_columns"] and new["ordered_model_features"]==old["ordered_model_features"]
 raw=(json.dumps(new,ensure_ascii=False,indent=2)+"\n").encode("utf-8");freeze(OUT,raw);digest=sha(OUT)
 freeze(OUT.with_suffix(".sha256"),(digest+"  "+OUT.name+"\n").encode("ascii"))
 if sha(OLD)!=OLD_SHA:raise RuntimeError("Original v001 changed during source-only proposal")
 print(json.dumps({"status":new["status"],"schema_path":OUT.relative_to(R).as_posix(),"sha256":digest,"bytes":len(raw),"module_domain":"NONNEGATIVE_REAL_COPY_COUNT_MEAN","ordered_columns_unchanged":True,"actual_run_artifacts_read":False}))
if __name__=="__main__":main()
