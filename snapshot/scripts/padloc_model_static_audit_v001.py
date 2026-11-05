"""File-only independent audit of a pinned PADLOC-DB release; no tool/genome prediction."""
from pathlib import Path
import sys,json,csv,hashlib,math,collections,ctypes,time,re,datetime
R=Path(__file__).resolve().parents[1];E=R/'evidence/model_routes/PADLOC_20261029/authorized_official_v2';O=E/'static_validation_20261029';O.mkdir(exist_ok=True)
B=R/'tools/databases/padloc_staged_20261029/v2_0_0_7f99b47';W=R/'tools/defence_runtime_sources_20261029/PyYAML-6.0.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl';sys.path.insert(0,str(W));import yaml
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];handle=k.GetCurrentProcess();a=ctypes.c_size_t();s=ctypes.c_size_t();assert k.GetProcessAffinityMask(handle,ctypes.byref(a),ctypes.byref(s));bit=a.value&-a.value;assert k.SetProcessAffinityMask(handle,bit)
started=time.monotonic()
def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def ref(p):data=p.read_bytes();return {'path':p.relative_to(R).as_posix(),'bytes':len(data),'sha256':sha_bytes(data)}
def save(name,v):p=O/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');t.replace(p)
def rows(p):
 with p.open(newline='')as f:return list(csv.DictReader(f,delimiter='\t'))
def tok(v):return [q.replace(' ','')for q in v.split('|')if q not in ('','NA')]
manifest=json.loads((E/'extracted_full_release_manifest.json').read_text());assert manifest['commit']=='7f99b47b75e232b111c18626badb9ac32e8e0b5a'
expected={x['path']:x for x in manifest['files']};actual={p.relative_to(R).as_posix()for p in B.rglob('*')if p.is_file()};assert len(expected)==5480 and actual==set(expected),'Final file set differs'
model_headers={};cm_headers={};byte_total=0;verified=[]
for i,(name,item)in enumerate(expected.items(),1):
 if time.monotonic()-started>600:raise TimeoutError('Finite file audit600s')
 p=R/name;data=p.read_bytes();assert len(data)==item['bytes']and sha_bytes(data)==item['sha256'],'Final filesystem differs '+name
 blob=hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest();assert blob==item['official_Git_blob_sha1'],'Official Git blob differs '+name
 byte_total+=len(data);verified.append({'path':name,'sha256':item['sha256'],'bytes':len(data),'official_Git_blob_sha1':blob})
 if p.suffix in('.hmm','.cm'):
  text=data.decode('ascii');lines=text.splitlines();assert text.rstrip().endswith('//'),'Missing model terminator '+name;assert sum(x.strip()=='//'for x in lines)==1,'Multiple model records '+name
  header={}
  for line in lines:
   if line.startswith('HMM ')or line.startswith('CM '):break
   fields=line.split(maxsplit=1)
   if len(fields)==2 and fields[0]in['NAME','ACC','LENG','CLEN','ALPH']:header[fields[0]]=fields[1].strip()
  if p.suffix=='.hmm':
   assert lines[0].startswith('HMMER3/'),'Non-HMMER3 model '+name;assert header.get('ALPH')=='amino'and int(header['LENG'])>0,'Invalid amino HMM '+name;assert header.get('NAME'),'Missing HMM NAME '+name
   if p.parent==B/'hmm':model_headers[p.stem]=header
  else:
   assert lines[0].startswith('INFERNAL'),'Non-Infernal CM '+name;assert header.get('ALPH')=='RNA'and int(header['CLEN'])>0,'Invalid RNA CM '+name;cm_headers[p.stem]=header
 if i%500==0:save('progress.json',{'verified_files':i,'total':len(expected),'bytes':byte_total,'elapsed_seconds':time.monotonic()-started})
hmm=rows(B/'hmm_meta.txt');sysmeta=rows(B/'sys_meta.txt');cmmeta=rows(B/'cm_meta.txt');web=json.loads((R/'evidence/model_routes/PADLOC_20261029/official_system_reference_catalogue.json').read_text());webrows={q['model_id']:q for q in web['rows']}
assert len(hmm)==len(model_headers)==5027 and len({q['hmm.accession']for q in hmm})==5027,'HMM inventory mismatch';assert set(model_headers)=={q['hmm.accession']for q in hmm}
primary=set();shortcuts=collections.defaultdict(set)
for q in hmm:
 acc=q['hmm.accession'];header=model_headers[acc];assert header.get('ACC')==acc and header['NAME']==q['hmm.name'],'HMM metadata name/accession differs '+acc
 names=tok(q['protein.name']);assert names,'No protein assignment';primary.update(names)
 for short in tok(q['secondary.name']):shortcuts[short].update(names)
 for field,default,upper in [('e.val.threshold',1e-5,None),('hmm.coverage.threshold',.3,1),('target.coverage.threshold',.3,1)]:
  value=default if q[field]in('','NA')else float(q[field]);assert math.isfinite(value)and value>=0 and(upper is None or value<=upper),'Bad cutoff '+acc
assert len(cmmeta)==len(cm_headers)==21 and {q['cm.name']for q in cmmeta}==set(cm_headers),'RNA covariance inventory mismatch'
for q in cmmeta:assert cm_headers[q['cm.name']]['NAME']==q['cm.name']
metadata={q['yaml.name']:q for q in sysmeta};assert len(metadata)==len(sysmeta)==385,'Duplicate system metadata';assert set(webrows)==set(metadata)-{'adjacent','cas_type_arrays'},'Website/release metadata mismatch'
models={p.stem:(p,yaml.safe_load(p.read_text()))for p in(B/'sys').glob('*.yaml')};assert len(models)==385
assert set(models)-set(metadata)=={'lamassu_other'}and set(metadata)-set(models)=={'adjacent'},'Unexpected metadata/definition coverage'
assert metadata['adjacent']['search']=='FALSE','Display-only adjacent must not search'
known=primary|set(shortcuts)|{'CRISPR_array','ncRNA'};inventory=[];missing=[]
keys={'force_strand','maximum_separation','minimum_core','minimum_total','core_genes','secondary_genes','neutral_genes','prohibited_genes'}
for name,(path,v)in models.items():
 assert isinstance(v,dict)and set(v)==keys,'System schema differs '+name
 assert type(v['force_strand'])is bool and all(type(v[q])is int and v[q]>=0 for q in ['maximum_separation','minimum_core','minimum_total']),'Invalid rule type/range '+name
 expanded={};rna={}
 for role in ['core_genes','secondary_genes','neutral_genes','prohibited_genes']:
  assert isinstance(v[role],list)and all(isinstance(x,str)for x in v[role]),'Bad gene list '+name
  values=[x for x in v[role]if x!='NA'];unknown=sorted(set(values)-known)
  if unknown:missing.append({'model':name,'role':role,'unknown':unknown})
  ex=set(values)
  for x in values:ex.update(shortcuts.get(x,set()))
  expanded[role]=sorted(ex);rna[role]=sorted(set(values)&{'CRISPR_array','ncRNA'})
 core=set(expanded['core_genes']);prohibited=set(expanded['prohibited_genes'])-core;secondary=set(expanded['secondary_genes'])-(core|prohibited);neutral=set(expanded['neutral_genes'])-(core|secondary|prohibited)
 realcore=core&(primary|{'CRISPR_array','ncRNA'});realsecondary=secondary&(primary|{'CRISPR_array','ncRNA'})
 assert v['minimum_core']<=len(realcore)and v['minimum_total']<=len(realcore|realsecondary),'Unattainable expanded rule quorum '+name
 meta=metadata.get(name);reference=webrows.get(name);candidate=bool(reference and reference['explicit_candidate_or_inferred']);relaxed=bool(reference and reference['relaxed_other_model']);registered=bool(meta and meta['search']=='TRUE')
 comments=''if not meta else meta['comment'];module=bool(re.search(r'(?i)transposon|adaptation|array|anti[- ]plasmid',name+' '+comments))
 inventory.append({'model_id':name,'definition':ref(path),'registered_search_enabled':registered,'metadata':meta,'website_reference_metadata':reference,'rules_original':v,'expanded_annotations_after_stock_shortcuts':{'core':sorted(core),'secondary':sorted(secondary),'neutral':sorted(neutral),'prohibited':sorted(prohibited)},'profile_join_resolved':not any(q['model']==name for q in missing),'evidence_class':'EXPLICIT_INFERRED_HEC_PDC_CANDIDATE'if candidate else'RELAXED_OTHER_DIAGNOSTIC'if relaxed else'CURATED_MODEL_REFERENCE_NOT_EXPERIMENTAL_VALIDATION_AUDIT','explicit_HEC_PDC_candidate':candidate,'relaxed_other_model':relaxed,'module_or_non_antiphage_function_review_flag':module,'RNA_feature_roles':rna,'protein_only_negative_allowed_without_missing_feature_review':not any(rna.values()),'prohibited_RNA_feature_requires_successful_RNA_search_before_positive':bool(rna['prohibited_genes']),'complete_model_relative_rule':'stock unique annotation-name quorum in same-contig/spacing/strand cluster, no prohibited annotations','biological_absence_or_native_compatibility_validated':False})
assert not missing,'Unresolved YAML profile/category references '+repr(missing)
assert sum(q['explicit_HEC_PDC_candidate']for q in inventory)==154,'Candidate evidence count differs'
assert sum(q['relaxed_other_model']for q in inventory)==19,'Relaxed model count differs'
save('per_model_rule_and_evidence_inventory.json',{'status':'STATIC_SCHEMA_PROFILE_AND_STOCK_SHORTCUT_RULES_VERIFIED_NATIVE_CONTROLS_PENDING','models':inventory,'display_metadata_no_definition':['adjacent'],'unregistered_definition_not_searched':['lamassu_other'],'RNA_feature_support':{'supplied_genes_accept_FNA_also':False,'supported_external_feature_flags':['--crispr','--ncrna'],'CRISPR_format':'CRISPRDetect GFF repeat_region records','ncRNA_format':'PADLOC-parsed tab-delimited Infernal results','RNA_tools_present_in_OCI':False,'RNA_tools_not_present':['CRISPRDetect','cmsearch/Infernal'],'no_reannotation_for_uniform_inputs':True,'unsupported_feature_states':'UNKNOWN; never infer negative or waive prohibited feature'},'stock_rule_source':{'R_source':ref(R/'tools/padloc_oci_case_runtime_20261029/usr/local/bin/padloc.R'),'shell_source':ref(R/'tools/padloc_oci_case_runtime_20261029/usr/local/bin/padloc'),'notes':['secondary.name is read positionally as system.definition.shortcut and expanded to primary protein names','Unique protein annotation names, not raw component-list length, determine quorum','CLI refuses --fna with supplied FAA/GFF; externalRNA feature outputs are supported','Only sys_meta searchTRUE rows are evaluated; adjacent is a disabled website display row']}})
save('independent_final_files_manifest.json',{'files':verified,'total_bytes':byte_total,'no_payload_mutated':True})
save('STATIC_READY_FOR_CONTROLS.json',{'schema':'TREE2_PADLOC_DB2_INDEPENDENT_STATIC_ADMISSION_V001','status':'STATIC_MODEL_INTEGRITY_PASS_PENDING_NATIVE_COMPATIBILITY_AND_FUNCTIONAL_CONTROLS','tag':'v2.0.0','commit':manifest['commit'],'archive':ref(E/'padloc-db-7f99b47b75e232b111c18626badb9ac32e8e0b5a.tar.gz'),'original_archive_sha256':'de1c9697ee735c7c8a856295ace5614c9c1959b6010cbc074a29125aa9c04fc9','final_files':ref(O/'independent_final_files_manifest.json'),'model_rule_and_evidence_inventory':ref(O/'per_model_rule_and_evidence_inventory.json'),'original_notices':[ref(B/x)for x in ['LICENSE','README.md','RELEASE.md']],'counts':{'final_release_files':len(verified),'bytes':byte_total,'active_amino_HMMs':len(model_headers),'deprecated_amino_HMMs':len([q for q in verified if'/hmm/deprecated/'in q['path']and q['path'].endswith('.hmm')]),'RNA_covariance_models':len(cm_headers),'all_YAML':len(models),'sys_meta_rows':len(sysmeta),'search_enabled_registered_models':sum(q['registered_search_enabled']for q in inventory),'website_protein_model_references':len(webrows),'explicit_HEC_PDC_candidates':154,'relaxed_other_models':19,'RNA_referencing_models':sum(any(q['RNA_feature_roles'].values())for q in inventory)},'known_upstream_inventory_exceptions':{'disabled_display_only_metadata_without_yaml':'adjacent','unregistered_unused_yaml':'lamassu_other','CRISPR_array_model_not_in_website_protein_table':'cas_type_arrays'},'all_final_file_SHA256_and_official_Git_blob_SHA1_verified':True,'all_active_HMM_metadata_and_gene_rule_shortcuts_resolved':True,'all_cm_metadata_and_model_headers_resolved':True,'native_prediction_or_biological_absence_acceptance':False,'old_extractor_native_exit':'UNKNOWN_NOT_INFERRED_FROM_FILE_EXISTENCE','new_independent_file_audit_actual_exit':'REQUIRES_OUTER_RETAINED_HANDLE_RECEIPT','CPU_affinity_one_bit':bit,'elapsed_seconds':time.monotonic()-started,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(json.dumps({'status':'PADLOC_STATIC_AUDIT_PASS_NATIVE_CONTROLS_PENDING','files':len(verified),'HMMs':len(model_headers),'models':len(models),'elapsed_seconds':time.monotonic()-started}),flush=True)
