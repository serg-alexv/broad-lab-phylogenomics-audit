#!/usr/bin/env python3
"""Nondestructive source-only review of existing ANI flags. No ANI computation."""
from pathlib import Path
import collections,csv,datetime,hashlib,json,os,re,shutil,uuid
R=Path(__file__).resolve().parents[1];D=R/'analysis/sequence_qc/d64e016face251f1';P=R/'state/sequence_qc_curation_progress.json'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+uuid.uuid4().hex[:8]+'.tmp')
 with q.open('w',encoding='utf-8') as f:json.dump(o,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(q,p)
def get(o,k,default=None):
 if not isinstance(o,dict):return default
 if k in o:return o[k]
 parts=k.split('_');return o.get(parts[0]+''.join(x.title() for x in parts[1:]),default)
def clean(x):
 x=re.sub(r'\s+',' ',str(x).strip()).upper()
 return '' if x in {'','NONE','NA','N/A','MISSING','NOT APPLICABLE','NOT COLLECTED','NOT PROVIDED','UNKNOWN','NOT AVAILABLE'} else x
def key(x):return re.sub(r'[^a-z0-9]','',str(x).lower())
def culture_tokens(values):
 out=set()
 for value in values:
  text=clean(value)
  for prefix,num in re.findall(r'\b([A-Z][A-Z-]{1,12})\s*[:_ -]?\s*(\d+[A-Z0-9-]*)\b',text):out.add(prefix+':'+num)
 return sorted(out)
def material_class(label,text):
 if label=='TYPE_MATERIAL':return 'SOURCE_ASSERTED_TYPE_MATERIAL_SCOPE_UNVERIFIED'
 if label=='TYPE_MATERIAL_NEOTYPE':return 'SOURCE_ASSERTED_NEOTYPE_REQUIRES_NOMENCLATURE_CURATION'
 if label=='TYPE_MATERIAL_SYN':return 'SOURCE_ASSERTED_SYNONYM_TYPE_REQUIRES_NAME_CURATION'
 if label=='TYPE_MATERIAL_CLADE':return 'CLADE_EXEMPLAR_NOT_A_NOMENCLATURAL_TYPE_ANCHOR'
 if label=='TYPE_MATERIAL_REFTYPE' or 'co-identical' in text.lower() or 'coidentical' in text.lower():return 'REFERENCE_OR_COIDENTICAL_PROXY_NOT_VERIFIED_TYPE'
 if label=='PATHOVAR_TYPE':return 'PATHOVAR_TYPE_NOT_A_SPECIES_TYPE_ANCHOR'
 if not label:return 'NO_EXPLICIT_NOMENCLATURAL_TYPE_CLAIM'
 return 'OTHER_TYPE_CATEGORY_REQUIRES_CURATION'
def progress(done,total,detail,status='RUNNING'):
 save(P,{'status':status,'done':done,'total':total,'unit':'source genomes','detail':detail,'updated_utc':utc(),'pid':os.getpid(),'scope':'Existing ANI flags/source metadata only; no taxonomy acceptance'})
def table(p,rows):
 if not rows:return
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def main():
 cohort=read(D/'input_manifest.json')['rows'];by={r['accession']:r for r in cohort};flags=read(D/'full_cohort/pair_review_flags.json')
 audit_path=R/'qc/source_provenance_audit.json';audit=read(audit_path);holds={r['accession']:r for r in audit['records']}
 ids=sorted({r[k] for r in flags for k in ('reference','query')});taxpath=R/'metadata/taxonomy_map.json';tax=read(taxpath)
 base={'ani_commit_sha256':sha(D/'commit.json'),'ani_tsv_sha256':sha(D/'full_cohort/ani.tsv'),'input_manifest_sha256':sha(D/'input_manifest.json'),'source_audit_sha256':sha(audit_path),'taxonomy_map_sha256':sha(taxpath),'script_sha256':sha(__file__)}
 out=D/'curation_source_review'/hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest()[:16]
 if (out/'commit.json').exists():
  for f in read(out/'manifest.json')['files']:
   q=out/f['path'];assert q.stat().st_size==f['bytes'] and sha(q)==f['sha256']
  progress(len(ids),len(ids),'Verified existing immutable source curation; no recomputation','COMPLETED');print(json.dumps({'status':'VERIFIED_REUSE','path':str(out)}));return
 out.mkdir(parents=True,exist_ok=False);save(out/'inputs.json',base);sources={}
 for n,a in enumerate(ids,1):
  folder=R/'raw'/a;receipt=read(folder/'acquisition_receipt.json');parts=[f for f in receipt['files'] if f['path'].endswith('/assembly_data_report.jsonl') or f['path']=='assembly_data_report.jsonl']
  if len(parts)!=1:raise RuntimeError('Missing/duplicate source report '+a)
  entry=parts[0];rp=folder/entry['path'];assert rp.stat().st_size==entry['bytes'] and sha(rp)==entry['sha256'],a
  report=json.loads(rp.read_text(encoding='utf-8').splitlines()[0]);info=get(report,'assembly_info',{});bs=get(info,'biosample',{});org=get(report,'organism',{});inf=get(org,'infraspecific_names',{})
  attrs=collections.defaultdict(list)
  for item in bs.get('attributes',[]):
   name=key(item.get('name',''));value=item.get('value','')
   if clean(value):attrs[name].append(value)
  strains=[get(inf,'strain',''),get(bs,'strain','')]+attrs.get('strain',[])+attrs.get('isolate',[])+attrs.get('isolatenamealias',[])
  cultures=attrs.get('culturecollection',[])+attrs.get('straincollection',[])
  types=get(report,'type_material',{});label=get(types,'type_label','');display=get(types,'type_display_text','')
  taxonomy=tax.get(str(by[a]['organism_taxid']),{})
  source=holds.get(a,{})
  sources[a]={'accession':a,'species':by[a]['species'],'species_taxid':by[a]['species_taxid'],'organism_taxid':by[a]['organism_taxid'],'organism_name':get(org,'organism_name',''),'biosample':get(bs,'accession',''),'bioproject':get(info,'bioproject_accession',''),'raw_strain_values':sorted(set(x for x in strains if clean(x))),'normalized_strain_values':sorted({clean(x) for x in strains if clean(x)}),'raw_culture_collection_values':sorted(set(cultures)),'normalized_culture_tokens':culture_tokens(cultures),'other_biomaterial_identifiers':attrs.get('refbiomaterial',[])+attrs.get('biomaterialprovider',[]),'raw_type_object':types,'type_label':label,'type_display_text':display,'type_evidence_class':material_class(label,display),'true_nomenclatural_type_validation':'NOT_VERIFIED','type_taxon_scope':'UNSPECIFIED_BY_ASSEMBLY_TYPE_OBJECT','biosample_type_material_statements':attrs.get('typematerial',[]),'current_taxonomy_metadata':taxonomy,'source_disposition':source.get('production_disposition','UNKNOWN'),'source_holds_or_exclusions':source.get('holds_or_exclusions',[]),'ncbi_ani_metadata':get(report,'average_nucleotide_identity',{}),'report_path':str(rp.relative_to(R)),'report_sha256':entry['sha256'],'acquisition_receipt_sha256':sha(folder/'acquisition_receipt.json'),'metadata_qc':by[a].get('metadata_qc'),'input_type_anchor_flag_was_exact_TYPE_MATERIAL':by[a].get('type_anchor_from_metadata',False)}
  if n%20==0:progress(n,len(ids),'Extracting source identity/type/provenance metadata; no ANI recalculation')
 save(out/'source_evidence.json',list(sources.values()))
 allrows={}
 fasta_to_acc={r['fasta']:r['accession'] for r in cohort}
 with (D/'full_cohort/ani.tsv').open() as f:
  for row in csv.DictReader(f,delimiter='\t'):
   a=fasta_to_acc[row['Ref_file']];b=fasta_to_acc[row['Query_file']]
   allrows[frozenset((a,b))]=row
 def ani_matches(source,other):
  out=[];ani=source['ncbi_ani_metadata'];target={other['accession'],get(read(R/'raw'/other['accession']/'acquisition_receipt.json')['metadata_record'],'paired_accession','')}
  for field in ('submitted_ani_match','best_ani_match'):
   value=get(ani,field,{})
   if value.get('assembly') in target:out.append({'field':field,'matched_assembly':value.get('assembly'),'category':value.get('category'),'ANI':value.get('ani'),'assembly_coverage':get(value,'assembly_coverage'),'type_assembly_coverage':get(value,'type_assembly_coverage'),'taxonomy_check_status':get(ani,'taxonomy_check_status')})
  return out
 pairreviews=[]
 for flag in flags:
  a,b=flag['reference'],flag['query'];sa,sb=sources[a],sources[b];same=sa['species_taxid']==sb['species_taxid'];shared_bs=[sa['biosample']] if sa['biosample'] and sa['biosample']==sb['biosample'] else []
  shared_strain=sorted(set(sa['normalized_strain_values'])&set(sb['normalized_strain_values']));shared_culture=sorted(set(sa['normalized_culture_tokens'])&set(sb['normalized_culture_tokens']));raw=allrows[frozenset((a,b))]
  low=float(raw.get('ANI_5_percentile','nan'));high=float(raw.get('ANI_95_percentile','nan'));borderline=low<=95<=high
  strict=flag['ANI']>=99.99 and min(flag['AF_reference'],flag['AF_query'])>=95
  reasons=[];priority=3
  if 'CROSS_LABEL_HIGH_ANI_REVIEW' in flag['review_flags']:
   priority=1;reasons.append('CROSS_SPECIES_LABEL_HIGH_ANI_REQUIRES_NOMENCLATURE_AND_REFERENCE_REVIEW')
   if shared_bs or shared_culture or shared_strain:reasons.append('SHARED_SOURCE_IDENTIFIER_ACROSS_SPECIES_LABELS')
   if sa['type_label']=='TYPE_MATERIAL' and sb['type_label']=='TYPE_MATERIAL':reasons.append('BOTH_HAVE_SOURCE_TYPE_MATERIAL_ASSERTIONS_NOT_INDEPENDENTLY_CURATED')
  if 'WITHIN_LABEL_LOW_ANI_REVIEW' in flag['review_flags']:
   priority=min(priority,2);reasons.append('WITHIN_LABEL_LOW_ANI_IS_A_REVIEW_FLAG_NOT_A_MISLABEL_CALL')
   if borderline:reasons.append('SKANI_5_TO95_PERCENTILE_INTERVAL_STRADDLES95_THRESHOLD')
  if strict:
   priority=min(priority,2 if shared_bs or shared_culture or shared_strain else 3);reasons.append('STRICT_NEAR_DUPLICATE_REVIEW_NO_AUTOMATIC_PRUNING')
   if shared_bs:reasons.append('SHARED_BIOSAMPLE')
   if shared_strain:reasons.append('SHARED_NORMALIZED_STRAIN')
   if shared_culture:reasons.append('SHARED_NORMALIZED_CULTURE_COLLECTION_TOKEN')
  if sa['source_holds_or_exclusions'] or sb['source_holds_or_exclusions']:reasons.append('SOURCE_HOLD_OR_EXCLUSION_PRESENT');priority=1
  pairreviews.append({**flag,'priority':priority,'same_species_taxid':same,'shared_biosamples':shared_bs,'shared_normalized_strains':shared_strain,'shared_normalized_culture_tokens':shared_culture,'strict_near_duplicate_AFboth_ge95':strict,'skani_ANI_5_percentile':low,'skani_ANI_95_percentile':high,'interval_straddles95':borderline,'reference_type_class':sa['type_evidence_class'],'query_type_class':sb['type_evidence_class'],'reference_source_holds':sa['source_holds_or_exclusions'],'query_source_holds':sb['source_holds_or_exclusions'],'reference_ncbi_match_to_other':ani_matches(sa,sb),'query_ncbi_match_to_other':ani_matches(sb,sa),'review_reasons':reasons,'decision':'REVIEW_ONLY_NO_REMOVAL_RENAMING_OR_TAXONOMY_ACCEPTANCE'})
 save(out/'pair_reviews.json',pairreviews);table(out/'pair_reviews.tsv',pairreviews)
 # Components are defined by any flagged edge, with strict-near-duplicate subcomponents preserved separately.
 def components(edges):
  parent={}
  def find(a):
   parent.setdefault(a,a)
   if parent[a]!=a:parent[a]=find(parent[a])
   return parent[a]
  for a,b in edges:
   x,y=find(a),find(b)
   if x!=y:parent[max(x,y)]=min(x,y)
  groups=collections.defaultdict(list)
  for a in parent:groups[find(a)].append(a)
  return [sorted(x) for x in sorted(groups.values(),key=lambda x:min(x))]
 comps=[]
 for n,members in enumerate(components([(r['reference'],r['query']) for r in pairreviews]),1):
  pairs=[r for r in pairreviews if r['reference'] in members and r['query'] in members];ss=[sources[a] for a in members]
  comps.append({'component_id':f'ANI_REVIEW_{n:03d}','members':members,'species_labels':sorted({s['species'] for s in ss}),'species_taxids':sorted({s['species_taxid'] for s in ss}),'priority':min(r['priority'] for r in pairs),'flagged_edges':len(pairs),'strict_near_duplicate_edges':sum(r['strict_near_duplicate_AFboth_ge95'] for r in pairs),'shared_BioSample_edges':sum(bool(r['shared_biosamples']) for r in pairs),'shared_strain_edges':sum(bool(r['shared_normalized_strains']) for r in pairs),'shared_culture_edges':sum(bool(r['shared_normalized_culture_tokens']) for r in pairs),'source_type_classes':dict(collections.Counter(s['type_evidence_class'] for s in ss)),'source_holds':{s['accession']:s['source_holds_or_exclusions'] for s in ss if s['source_holds_or_exclusions']},'review_reasons':sorted({x for r in pairs for x in r['review_reasons']}),'decision':'REVIEW_ONLY_NO_PANEL_CHANGE'})
 save(out/'component_reviews.json',comps);table(out/'component_reviews.tsv',comps)
 strictcomponents=components([(r['reference'],r['query']) for r in pairreviews if r['strict_near_duplicate_AFboth_ge95']]);save(out/'strict_near_duplicate_components.json',strictcomponents)
 summary={'created_utc':utc(),'source_genomes_checked':len(sources),'source_report_hashes':'ALL_MATCH_ACQUISITION_RECEIPTS','flagged_pairs':len(pairreviews),'review_components':len(comps),'priority_pair_counts':dict(collections.Counter(str(r['priority']) for r in pairreviews)),'priority_component_counts':dict(collections.Counter(str(r['priority']) for r in comps)),'shared_BioSample_pairs':sum(bool(r['shared_biosamples']) for r in pairreviews),'shared_strain_pairs':sum(bool(r['shared_normalized_strains']) for r in pairreviews),'shared_culture_collection_pairs':sum(bool(r['shared_normalized_culture_tokens']) for r in pairreviews),'strict_near_duplicate_pairs':sum(r['strict_near_duplicate_AFboth_ge95'] for r in pairreviews),'strict_near_duplicate_components':len(strictcomponents),'flagged_genome_type_label_counts':dict(collections.Counter(s['type_label'] or 'NONE' for s in sources.values())),'whole_screen_type_label_counts':dict(collections.Counter(r.get('type_material_label') or 'NONE' for r in cohort)),'current_source_holds_in_flagged_genomes':sum(bool(s['source_holds_or_exclusions']) for s in sources.values()),'true_nomenclatural_type_anchors_independently_verified':0,'classification_note':'TYPE_MATERIAL is a source assertion; neotypes,synonym types,clade exemplars and reference/co-identical proxies remain distinct. No nonempty type object alone grants a type anchor.','within_label_case':[r for r in pairreviews if 'WITHIN_LABEL_LOW_ANI_REVIEW' in r['review_flags']],'no_pruning':True,'no_renaming':True,'no_taxonomy_acceptance':True,'no_ANI_recompute':True,'missing_metadata':'UNKNOWN_RECORDED_NOT_NEGATIVE','limitations':['Culture identifier normalization is review evidence,not proof of shared physical stock.','Same reported strain/type metadata does not establish byte-identical genomes or identical accessory/defence content.','Connected components do not imply every member pair meets the ANI/AF threshold.','Existing NCBI ANI metadata and new skani estimates use different methods; differences are not automatically source errors.']}
 save(out/'summary.json',summary)
 files=[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file()]
 save(out/'manifest.json',{'created_utc':utc(),'files':files});save(out/'commit.json',{'status':'COMMITTED_SOURCE_REVIEW_ONLY','created_utc':utc(),'inputs':base,'manifest_sha256':sha(out/'manifest.json'),'summary':summary});save(D/'curation_source_review/latest.json',{'directory':str(out),'commit_sha256':sha(out/'commit.json'),'summary':summary});progress(len(ids),len(ids),'Source-only ANI curation complete; no panel changes or taxonomy acceptance','COMPLETED');print(json.dumps({'directory':str(out),'summary':summary}))
if __name__=='__main__':
 try:main()
 except BaseException as e:progress(0,0,repr(e),'FAILED');raise
