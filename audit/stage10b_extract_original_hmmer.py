#!/usr/bin/env python3
"""Frozen-source, read-only original HMMER extraction for six Stage 10A priority loci.
No prediction runs, no biological system merges, no ledger changes.
"""
import csv
import hashlib
import io
import json
import re
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

TARGET = {
 "GCF_001870205.1": ["gene000640","gene000641","gene000642","gene000643","gene000644"],
 "GCF_002847845.2": ["gene000430","gene000431","gene000432","gene000433"],
 "GCF_024701915.1": ["gene001756","gene001758","gene001759","gene001760","gene001761"],
 "GCF_026131645.1": ["gene001552","gene001553","gene001554","gene001555","gene001556","gene001557"],
 "GCF_030222485.2": ["gene000430","gene000431","gene000432","gene000433"],
 "GCF_900129415.1": ["gene002103","gene002107","gene002108","gene002110","gene002111"],
}
COHORT = {"GCF_001870205.1":"C003","GCF_002847845.2":"C005",
          "GCF_024701915.1":"C006","GCF_026131645.1":"C007",
          "GCF_030222485.2":"C008","GCF_900129415.1":"C006"}
ARCHIVES = {
 "data_provenance.tar.gz.part0001":("520427112-dont-use",""),
 "results--defence_bulk_C003_v001.tar.gz.part0001":("6bf718a559fd24c92e1a99e4edcda5e5e916ddfebb0c38862cab7888ea04e968",87002107),
 "results--defence_bulk_C005_v002.tar.gz.part0001":("9ac6f3b0f5c4f96c100aa8da940f5cf7f39cc0e1cb67aaffe6e3fd461dbd8715",89296421),
 "results--defence_bulk_C006_v002.tar.gz.part0001":("7d970d9235bacb51f6803ea7125001b54d9f52dbdf9c8fd118fd1c500a93c768",92683011),
 "results--defence_bulk_C007_v002.tar.gz.part0001":("18a8197eb45aa281afe6fd01119dffa84e3189b253d5b2657009fae1603237d1",91293604),
 "results--defence_bulk_C008_recovery_v003.tar.gz.part0001":("112787c745597729fa0c7f9e52cf13f8d4db7b783bec01f757b09a9a3caa9091",57610544),
 "results--defence_bulk_C008_v002.tar.gz.part0001":("cef4e2d20ef33b39ec971b996d9ef2a04b98928418183de1c07db92ff8bfb7f4",34128274),
}
ARCHIVES["data_provenance.tar.gz.part0001"]=("1cf059b359c7e9b53282ff20b91d8e4c63dae9a042fc033c4604bfecdadd77de",41673772)
ROW = re.compile(r"(?:^|/)rows/(GC[AF]_\d{9}\.\d+)/(PADLOC|DefenseFinder)/(.+)$")

def die(msg):
 raise ValueError(msg)
def sha(x):
 h=hashlib.sha256();h.update(x);return h.hexdigest()
def streamhash(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(2*1024*1024),b''):h.update(b)
 return h.hexdigest()
def parse_raw(path,source,rawhits):
 # The raw file contains unmodified HMMER --domtblout, --tblout, or -o.
 lines=source.decode('utf-8',errors='replace').splitlines()
 for line in lines:
  if not line.strip() or line.startswith("#"): continue
  fields=line.split(maxsplit=22)
  if len(fields)<7: continue
  rawhits.append({"source_path":path,"raw_target":fields[0],
      "raw_query_profile":fields[3] if len(fields)>3 else "",
      "full_evalue":fields[6] if len(fields)>6 else "",
      "domain_i_evalue":fields[12] if len(fields)>12 else "",
      "raw_line":line[:3000]})
 return (lines[-1].strip() if lines else "")

def main(src,out):
 out.mkdir(exist_ok=False)
 metadata={"archive_sha256":{},"archive_members":{},"selected_genomes":sorted(TARGET)}
 receipts={}
 rawseen={}
 artsha={}
 rawhits=[]
 scoped={}
 phases={}
 full={}
 orig_maps={}
 stockfiles={}
 found_members={}
 for archive, (expected_hash,expected_size) in ARCHIVES.items():
  p=src/archive
  if not p.exists() or p.stat().st_size!=expected_size:die("Missing or wrong size: "+archive)
  got=streamhash(p)
  if got!=expected_hash:die("Original release SHA mismatch: "+archive)
  metadata["archive_sha256"][archive]=got
  count=0
  with tarfile.open(p,'r|gz') as tar:
   for mem in tar:
    count+=1
    if not mem.isfile():continue
    m=ROW.search(mem.name)
    if not m:
     if mem.name.endswith("/COHORT_COMPLETE.json") and archive.startswith("results--"):
      blob=tar.extractfile(mem).read()
      full[archive]=json.loads(blob)
     if any(acc in mem.name for acc in TARGET) and mem.name.endswith("protein_identity_map.json"):
      blob=tar.extractfile(mem).read()
      obj=json.loads(blob)
      acc=next((acc for acc in TARGET if acc in mem.name),None)
      if acc:
       mapping=obj.get("mapping",obj) if isinstance(obj,dict) else obj
       if isinstance(mapping,list):
        orig_maps[acc]={"source_path":mem.name,"source_sha256":sha(blob),
          "df_to_canonical":{r["DF_ID"]:r["canonical_id"] for r in mapping}}
     continue
    acc,engine,rel=m.groups()
    if acc not in TARGET:continue
    if archive.startswith("results--") and COHORT[acc] not in archive: continue
    found_members[archive]=found_members.get(archive,0)+1
    # Preserve original sha for every selected member and compare to COMMITTED references.
    buf=tar.extractfile(mem).read()
    s=sha(buf)
    artsha[mem.name]=(s,len(buf))
    if rel=="COMMITTED.json":
     phases[acc,engine]={"record":json.loads(buf),"original_sha256":s,"path":mem.name,
                         "original_bytes":len(buf),"archive":archive}
    elif rel=="scoped_predictions.json":
     scoped[acc,engine]=json.loads(buf)
    elif rel.startswith("HMMER_receipts/") and rel.endswith(".json"):
     receipts[mem.name]={"row":json.loads(buf),"original_sha256":s,"original_bytes":len(buf)}
    elif rel.startswith("HMMER_receipts/") and rel.endswith(".raw"):
     before=len(rawhits)
     footer=parse_raw(mem.name,buf,rawhits)
     rawseen[mem.name]={"sha256":s,"bytes":len(buf),"footer":footer,"hits":len(rawhits)-before}
    elif rel.startswith("stock_output/") and (rel.endswith(".csv") or rel.endswith(".tsv")):
     # Original stock output, not recomputed predictions.
     stockfiles[mem.name]={"sha256":s,"bytes":len(buf),"content":buf.decode('utf-8',errors='replace')[:400000]}
  metadata["archive_members"][archive]=count
  print("ARCHIVE_CHECKED",archive,"members",count,"selected_members",found_members.get(archive,0),flush=True)

 # Find reversible DF mapping anywhere in the archived stock results.
 for acc in TARGET:
  for path in list(artsha):
   if acc in path and path.endswith("protein_identity_map.json") and acc not in orig_maps:
    # Already read in previous pass only where no ROW match; if member was inside row scope
    # we still cannot recover it here, which remains an explicit absence.
    pass
 by_locus=[]
 for acc in sorted(TARGET):
  targets={acc+"|"+gid for gid in TARGET[acc]}
  reversible=orig_maps.get(acc,{}).get("df_to_canonical",{})
  hits=[]
  raw_belongs=Counter()
  for h in rawhits:
   p=h["source_path"]
   if "/rows/"+acc+"/" not in p and not p.startswith("rows/"+acc+"/"):continue
   canon=h["raw_target"] if h["raw_target"] in targets else reversible.get(h["raw_target"],"")
   if canon in targets:
    match=dict(h);match["canonical_protein_id"]=canon
    hits.append(match)
    raw_belongs[p.split("/"+acc+"/")[1].split("/")[0]]+=1
  by_locus.append({"accession":acc,"cohort":COHORT[acc],
   "target_gene_ids":sorted(targets),
   "mapping_available":bool(reversible),"mapped_DF_targets":len(reversible),
   "target_raw_hmmer_hit_count":len(hits),
   "target_raw_hmmer_hits":hits,
   "hits_by_engine":dict(raw_belongs)})
 # Verify phase artifact hashes using independent tar-member byte hashes, including original
 # raw evidence, but only if the phase was retained in the frozen cohort archive.
 gates=[]
 for (acc,engine),obj in sorted(phases.items()):
  rows=obj["record"]
  checked=0
  missing=[]
  mismatched=[]
  for ref in rows.get("artifacts",[]):
   v=artsha.get(ref["path"])
   if v is None:
    missing.append(ref["path"])
   elif v!=(ref["sha256"],ref["bytes"]):
    mismatched.append(ref["path"])
   else:checked+=1
  gates.append({"accession":acc,"engine":engine,"archive":obj["archive"],
   "phase_sha256":obj["original_sha256"],"artifacts_rehashed_ok":checked,
   "missing_artifacts":missing[:20],"missing_artifact_count":len(missing),
   "mismatched_artifacts":mismatched[:20],"mismatched_artifact_count":len(mismatched)})
 # Format a compact candidate/role table from the captured, original model profile results.
 with (out/"target_hmmer_model_roles.tsv").open("w",newline="") as f:
  w=csv.writer(f,delimiter="\t")
  w.writerow(["accession","canonical_protein_id","engine","HMMER_target","HMMER_query_profile",
              "full_evalue","domain_i_evalue","source_raw_path"])
  for x in by_locus:
   for h in x["target_raw_hmmer_hits"]:
    engine="PADLOC" if "/PADLOC/" in h["source_path"] else "DefenseFinder"
    w.writerow([x["accession"],h["canonical_protein_id"],engine,h["raw_target"],
       h["raw_query_profile"],h["full_evalue"],h["domain_i_evalue"],h["source_path"]])
 # Make evidence accessible for following analysis without exposing 6*1,000 full receipts or raw files.
 for x in by_locus:
  x.pop("target_raw_hmmer_hits")
 # Bind each original DefenseFinder gembase gene ID to its verified canonical ID and
 # retain exact stock gene-level role assignments (without rerunning MacSyFinder).
 target_map={}
 for acc in TARGET:
  canonical_targets={acc+"|"+gid for gid in TARGET[acc]}
  mapping=orig_maps.get(acc,{}).get("df_to_canonical",{})
  target_map[acc]={dfid:canon for dfid,canon in mapping.items() if canon in canonical_targets}
 df_role_rows=[]
 for path,record in stockfiles.items():
  if not (path.endswith("_defense_finder_genes.tsv") or path.endswith("_defense_finder_hmmer.tsv")):
   continue
  acc=next((a for a in TARGET if "/"+a+"/" in path),None)
  if acc is None:continue
  for row in csv.DictReader(io.StringIO(record["content"]),delimiter="\t"):
   gene=target_map[acc].get(row.get("hit_id",""))
   if gene:
    df_role_rows.append({"accession":acc,"canonical_protein_id":gene,
      "source_path":path,"source_sha256":record["sha256"],
      "DF_gene_id":row["hit_id"],"DF_hit_name":row.get("gene_name",""),
      "DF_model":row.get("model_fqn",""),"DF_hit_i_eval":row.get("hit_i_eval",row.get("i_eval","")),
      "DF_hit_score":row.get("hit_score",""),"DF_hit_status":row.get("hit_status",""),
      "DF_system_id":row.get("sys_id","")})
 with (out/"target_defensefinder_stock_gene_roles.tsv").open("w",newline="") as f:
  cols=["accession","canonical_protein_id","source_path","source_sha256","DF_gene_id",
        "DF_hit_name","DF_model","DF_hit_i_eval","DF_hit_score","DF_hit_status","DF_system_id"]
  writer=csv.DictWriter(f,fieldnames=cols,delimiter="\t");writer.writeheader();writer.writerows(df_role_rows)
 metadata.update({
  "target_df_id_mapping":target_map,
  "target_df_stock_role_rows":len(df_role_rows),
  "original_defensefinder_raw_samples":[h for h in rawhits if "/DefenseFinder/" in h["source_path"]][:5],
  "genomes":by_locus,
  "phase_source_gates":gates,
  "original_stock_file_inventory":[{"path":p,"sha256":v["sha256"],"bytes":v["bytes"]}
                                  for p,v in sorted(stockfiles.items())],
  "original_source_mapping_paths":{a:d["source_path"] for a,d in orig_maps.items()},
  "raw_file_count":len(rawseen),"receipt_file_count":len(receipts),
  "raw_hit_count_all_genes":len(rawhits),
  "selected_artifact_files_rehashed":len(artsha),
  "scientific_disposition":"SOURCE_HMMER_PROFILE_EVIDENCE_EXTRACTED_NO_BIOLOGICAL_ACCEPTANCE",
  "no_model_or_predictor_runs":True,"no_ledger_mutation":True})
 (out/"SOURCE_EVIDENCE_SUMMARY.json").write_text(json.dumps(metadata,indent=2)+"\n")
 (out/"ORIGINAL_STOCK_FILES.json").write_text(json.dumps(stockfiles,indent=2)+"\n")
 print("SELECTED_SOURCE_EVIDENCE",len(phases),"PHASES",len(rawseen),"RAW_FILES",len(rawhits),"RAW_HITS",flush=True)
 print("TARGET_ROLE_HITS",sum(x["target_raw_hmmer_hit_count"] for x in by_locus),flush=True)
 print("STATUS_HOLD_SUBTYPE_AND_BIOLOGICAL_ACCEPTANCE",flush=True)

if __name__=="__main__":
 try:
  if len(sys.argv)!=3:die("Usage: extract.py <download-directory> <new-output-directory>")
  main(Path(sys.argv[1]),Path(sys.argv[2]))
 except Exception as e:
  print("FAIL_STAGE10B_SOURCE_EXTRACT",type(e).__name__,str(e),file=sys.stderr)
  raise
