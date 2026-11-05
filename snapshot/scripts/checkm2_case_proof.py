from pathlib import Path
import json,os,datetime
r=Path(__file__).resolve().parents[1];e=r/'evidence/checkm2_runtime';records=[]
for name,tag in [('checkm2_env','prefix'),('checkm2_runtime_pkgs','package_cache')]:
 p=r/'tools'/name;probe=p/'.case_probe';assert (probe/'CaseProbe').read_text()=='upper' and (probe/'caseprobe').read_text()=='lower'
 dest=e/('case_probe_'+tag)
 if dest.exists():raise RuntimeError('Prior case proof unexpectedly exists')
 os.replace(probe,dest)
 records.append({'path':str(p),'case_sensitive':True,'nested_case_pair_preserved':True,'probe_evidence':str(dest.relative_to(r))})
obj={'status':'PASS_PROJECT_DIRECTORY_CASE_SENSITIVITY','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directories':records,'scope':'Only new empty project prefix/cache; no global case setting changed'}
(e/'case_sensitive_directory_proof.json').write_text(json.dumps(obj,indent=2)+'\n');print(json.dumps(obj))
