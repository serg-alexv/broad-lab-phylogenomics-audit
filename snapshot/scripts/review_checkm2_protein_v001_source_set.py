"""Independent hash-only source admission; no imports of reviewed modules or biology."""
from pathlib import Path
import ast,datetime,hashlib,json,os,uuid
R=Path(__file__).resolve().parents[1]
CONTRACT_SHA="87ce9cec98b7d109f2d34df3ac1671941ceec01e64bfe0b4a64fa2389707ed47"
SCHEMA_SHA="2be7bda6589a445a8b70023d9cf84ffadc76a380db112b34a70ce0094fc53adb"
STOP_SHA="352c2cacb99a5ba33cd8e35da845a5a32c6404eb137ae0558ac112477e69db16"
def sha(p):
 with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def main():
 contract_path=R/"metadata/checkm2_protein_implementation_v001.json"
 if sha(contract_path)!=CONTRACT_SHA:raise RuntimeError("Frozen implementation contract differs")
 contract=read(contract_path)
 if len(contract["sources"])!=12:raise RuntimeError("Expected all twelve execution/shared source pins")
 for row in contract["sources"]+[contract["fixture_report"],contract["strategy_template"]]:
  p=R/row["path"]
  if sha(p)!=row["sha256"] or p.stat().st_size!=row["bytes"]:raise RuntimeError("Reviewed source/receipt differs: "+str(p))
  if p.suffix==".py":ast.parse(p.read_text(encoding="utf-8-sig"))
 schema_path=R/"metadata/checkm2_feature_schema_v001.json"
 if sha(schema_path)!=SCHEMA_SHA:raise RuntimeError("Ordered feature schema differs")
 schema=read(schema_path)
 if len(schema["ordered_model_features"])!=21241 or schema["ordered_dataframe_columns"]!=["Name"]+schema["ordered_model_features"]:raise RuntimeError("Feature dimensions/order mismatch")
 fixture=read(R/contract["fixture_report"]["path"])
 if fixture["status"]!="PASS" or len(fixture["checks"])!=23 or fixture["real_genome_FAA_model_or_author_tool_executed"] is not False:raise RuntimeError("Owner fixture receipt is not the reviewed report")
 stop_path=R/"state/STOP_CHECKM2_PILOT"
 if sha(stop_path)!=STOP_SHA or (R/"state/checkm2_protein_strategy_ready_v001.json").exists():raise RuntimeError("Held state changed before source-only admission")
 prodigal=R/"tools/checkm2_runtime_pkgs/checkm2-1.1.0-pyhdfd78af_2/site-packages/checkm2/prodigal.py"
 if sha(prodigal)!="4d962b423281b81edf3e9eec7ce3219388a0df8ae52c13cde883419826592b6f":raise RuntimeError("Original caller source changed")
 receipt={"schema":"TREE2_PROTEIN_V001_INDEPENDENT_SOURCE_ADMISSION_REVIEW","status":"GO_SOURCE_ONLY_HELD_NO_DISPATCH","implementation_contract":{"path":contract_path.relative_to(R).as_posix(),"sha256":CONTRACT_SHA},"reviewed_source_set":contract["sources"],"owner_fixture_report":contract["fixture_report"],"owner_fixture_count":23,"fixtures_independently_executed_by_reviewer":False,"review_method":"Static original caller/feature/report semantics plus new helpers/controller and normalized native/entry/shell diff against accepted FNA wrappers; hashes checked without importing any reviewed module","feature_schema_sha256":SCHEMA_SHA,"original_prodigal_source_sha256":sha(prodigal),"resolved_findings":["Each started command unit must have a matching terminal execution receipt before group closure can be claimed","Exactly five stock report cells are required; extra/missing cells rejected"],"verified_design":["Fresh separate model-free interpreter calls unchanged original ProdigalRunner sequentially with no supplied translation table","Selected FAA and ten exact returned values retained; fractional N50 and scalar precision preserved","Original GFF/FNA deletion retained without interception; independent DNA metrics explicitly separate","--genes --extension faa --threads 1 --lowmem --dbg_vectors --debug with exact versioned basename and unchanged selected FAA bytes","Five stock protein report columns; no invented nine nucleotide columns","Complete ordered 21241 numeric features and exact 22 FAA metadata counts required, no fill/reindex/unknown-to-zero conversion","Two declared 600-second units; protein prediction plus feature validation share second unit; hard summed-RSS 2GiB and 1GiB headroom unchanged","Root strategy and exact owned hold transition required before any biological dispatch; common native/compute/install locks and accepted read-only image/overlay/IPC gates retained","One attempt per exact root strategy SHA; stock resume forbidden; failure is not absence"],"biological_stop_sha256":STOP_SHA,"strategy_admission_present":False,"reviewer_opened_genome_FAA_pickle_or_model":False,"reviewer_imported_reviewed_module":False,"reviewer_mounted_or_launched_runtime":False,"runtime_or_workflow_viability_measured":False,"production_acceptance":"NOT_GRANTED","future_owner_gates":["Root independently admits the actual closed engineering/runtime/source/input bindings","Live monitor adapter admitted before launch","Only the exact owned resource hold is transitioned; global/user STOP remains authoritative","Actual gene and protein units, complete artifact manifest, unchanged image/IPC/native/group/lock closures must pass","Numerical or biological acceptance requires later independent controls; this source review grants neither"]}
 out=R/"metadata/checkm2_protein_v001_source_admission_review.json"
 data=(json.dumps(receipt,indent=2,sort_keys=True)+"\n").encode()
 if out.exists():
  if out.read_bytes()!=data:raise RuntimeError("Independent admission receipt is immutable")
 else:
  temp=out.with_name(out.name+"."+uuid.uuid4().hex+".tmp")
  with temp.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(temp,out)
 print(json.dumps({"status":receipt["status"],"path":str(out),"sha256":sha(out),"source_pins":12,"biological_execution":False}))
if __name__=="__main__":main()
