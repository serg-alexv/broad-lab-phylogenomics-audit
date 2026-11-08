#!/usr/bin/env python3
"""Independent 44-peptide HMMER profile check against pinned public model source commits.

IMPORTANT: New targeted model search, not recovery of historical 734-genome HMMER receipts.
Targeted database E-values are not directly comparable to original genome-wide E-values.
No claims of final biological subtype, fitness, immunity or full-system count.
"""
import csv,hashlib,json,re,subprocess,sys,tarfile
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import quote

SOURCES={
 "PADLOC-DB":("padlocbio/padloc-db","7f99b47b75e232b111c18626badb9ac32e8e0b5a",
  "de1c9697ee735c7c8a856295ace5614c9c1959b6010cbc074a29125aa9c04fc9"),
 "defense-finder-models":("mdmparis/defense-finder-models","afb0e5a8b466be53586b13266f5d38d98c3ac268",None),
 "CasFinder":("macsy-models/CasFinder","ad7096548a814788ca04538602d71f85115b4c71",None)
}
def require(x,s):
 if not x:raise RuntimeError(s)
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def fetch(url,dest):
 cmd=["curl","--location","--fail","--show-error","--silent","--retry","4",
      "--retry-delay","3","--connect-timeout","30","--max-time","1000","--output",str(dest),url]
 require(subprocess.run(cmd,check=False).returncode==0,"Download failed: "+url)
def readfasta(path):
 result={}
 title=None; buf=[]
 for line in path.read_text().splitlines():
  if line.startswith(">"):
   if title:result[title]="".join(buf)
   title=line[1:].split()[0];buf=[]
  elif line:buf.append(line.strip())
 if title:result[title]="".join(buf)
 return result
def build_banks(work):
 details={}
 for origin,(repo,commit,reference_hash) in SOURCES.items():
  name=origin.replace("-","_")
  tarpath=work/(name+".tar.gz")
  fetch("https://codeload.github.com/"+repo+"/tar.gz/"+commit,tarpath)
  got=digest(tarpath)
  if reference_hash:
   require(got==reference_hash,"Public model source archive SHA mismatch: "+origin)
  unpack=work/name
  unpack.mkdir(exist_ok=False)
  with tarfile.open(tarpath,"r:gz") as tar:
   tar.extractall(unpack,filter="data")
  paths=sorted(p for p in unpack.rglob("*") if p.is_file() and p.suffix.lower() in (".hmm",".hmm3"))
  if not paths:
   # Include HMM files lacking standard extensions, but cap scanning to sensible sizes.
   paths=sorted(p for p in unpack.rglob("*") if p.is_file() and p.stat().st_size<15_000_000
                and "hmm" in p.name.lower())
  bank=work/(name+".hmm")
  model_refs={}
  valid=0;invalid=0
  with bank.open("wb") as dst:
   for p in paths:
    data=p.read_bytes()
    # Only native HMMER 3 flat model files. No unverified conversion or model rebuilding.
    if not data.lstrip().startswith((b"HMMER3/",b"HMMER3")) or b"\n//" not in data:
     invalid+=1;continue
    if not data.endswith(b"\n"):data+=b"\n"
    for match in re.finditer(rb"(?m)^NAME\s+(\S+)\s*$",data):
     id=match.group(1).decode("utf8","replace")
     model_refs.setdefault(id,[]).append({"path":p.relative_to(unpack).as_posix(),
                                            "sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
    dst.write(data);valid+=1
  details[origin]={"git_repo":repo,"source_commit":commit,"source_archive_sha256":got,
                   "reference_archive_sha256_matched":bool(reference_hash),
                   "native_hmm_files":valid,"skipped_files":invalid,
                   "unique_profile_names":len(model_refs),"combined_sha256":digest(bank) if valid else None,
                   "model_ref":model_refs}
  print("MODEL_SOURCE",origin,"NATIVE_HMM_FILES",valid,"PROFILE_NAMES",len(model_refs),flush=True)
  require(valid>=1,"No verified native HMMER profile source found for "+origin)
 return details

def parse_domtbl(path,origin,known):
 rows=[]
 for line in path.read_text(errors="replace").splitlines():
  if not line or line.startswith("#"):continue
  bits=line.split(maxsplit=22)
  require(len(bits)>=23,"Malformed domtblout: "+origin)
  # hmmsearch: target sequence name, query HMM name, full E-value, domain i-E-value, score, coordinates.
  target,profile=bits[0],bits[3]
  require(profile in known,"Profile missing from original model source: "+profile)
  rows.append({"source_bank":origin,"target":target,"profile_name":profile,
              "full_evalue":bits[6],"full_bitscore":bits[7],
              "domain_i_evalue":bits[12],"domain_bitscore":bits[13],
              "hmm_from":bits[15],"hmm_to":bits[16],
              "target_from":bits[17],"target_to":bits[18],
              "source_model_file":known[profile][0]["path"],
              "source_model_file_sha256":known[profile][0]["sha256"]})
 return rows
def main():
 require(len(sys.argv)==4,"usage: script INPUT_PEPTIDE_DIRECTORY WORKDIR OUTDIR")
 inp,work,out=[Path(a) for a in sys.argv[1:]]
 require(not out.exists(),"Refusing to overwrite output")
 work.mkdir(exist_ok=True,parents=True);out.mkdir(parents=True)
 seq=readfasta(inp/"44_verified_original_source_peptides.faa")
 source=json.loads((inp/"44_original_peptide_SHA256.json").read_text())["accessions"]
 require(len(seq)==44 and len(source)==9 and sum(len(v) for v in source.values())==44,
         "Wrong target genome or protein count")
 for acc,m in source.items():
  for id,row in m.items():
   require(id in seq and hashlib.sha256(seq[id].encode()).hexdigest()==row["aa_sha256"],
           "Original target peptide SHA mismatch "+id)
 tool=subprocess.run(["hmmsearch","-h"],capture_output=True,text=True)
 require(tool.returncode==0,"hmmsearch missing")
 tool_version=tool.stdout.splitlines()[1:5]
 details=build_banks(work)
 results=[]
 for origin in SOURCES:
  bank=work/(origin.replace("-","_")+".hmm")
  dom=out/(origin.replace("-","_")+".domtblout")
  cmd=["hmmsearch","--cpu","2","--noali","--notextw","-E","10","--domE","10",
       "--domtblout",str(dom),str(bank),str(inp/"44_verified_original_source_peptides.faa")]
  print("BEGIN_TARGETED_HMMER",origin,flush=True)
  with (out/(origin.replace("-","_")+".log")).open("w") as logfile:
   p=subprocess.run(cmd,stdout=logfile,stderr=subprocess.PIPE,text=True)
  require(p.returncode==0,"HMMER run failed for "+origin+": "+p.stderr[-1500:])
  entries=parse_domtbl(dom,origin,details[origin]["model_ref"])
  for row in entries:require(row["target"] in seq,"Unexpected protein in model result")
  results.extend(entries)
  print("FINISHED_TARGETED_HMMER",origin,"DOMAIN_ROWS",len(entries),flush=True)
 cols=["source_bank","target","profile_name","full_evalue","full_bitscore","domain_i_evalue",
       "domain_bitscore","hmm_from","hmm_to","target_from","target_to","source_model_file","source_model_file_sha256"]
 with (out/"44_all_original_profile_domain_hits.tsv").open("w",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=cols,delimiter="\t");writer.writeheader();writer.writerows(results)
 best=defaultdict(list)
 for row in results:
  try:
   if float(row["domain_i_evalue"])<=1e-3:
    best[row["target"]].append(row)
  except ValueError:pass
 selection=[]
 for target,rows in sorted(best.items()):
  for x in sorted(rows,key=lambda v:(float(v["domain_i_evalue"]),-float(v["domain_bitscore"])))[:20]:
   selection.append(x)
 with (out/"44_top20_per_protein_significant_hits.tsv").open("w",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=cols,delimiter="\t");writer.writeheader();writer.writerows(selection)
 # Preserve original model-file paths/hashes for independent rerun; no raw tarball included.
 details_short={k:{f:v for f,v in d.items() if f!="model_ref"} for k,d in details.items()}
 (out/"MODEL_SOURCE_QA.json").write_text(json.dumps(details_short,indent=2)+"\n")
 summary={"schema":"TREE2_STAGE10C_TARGETED_MODEL_EVIDENCE_V1",
 "status":"PASS_STAGE10C_NEW_TARGETED_44_PEPTIDE_PROFILE_SEARCH_NOT_ORIGINAL_GENOME_WIDE_REPORTS",
 "new_search":True,"original_734_raw_HMMER_replayed":False,
 "target_peptides_sha_verified":len(seq),"target_genomes":len(source),
 "model_repos_exact_commit":{k:v[1] for k,v in SOURCES.items()},
 "hmmer_tool_version":tool_version,
 "total_domain_rows":len(results),"significant_i_e_le_1e_3":sum(len(r) for r in best.values()),
 "per_source_domains":dict(Counter(x["source_bank"] for x in results)),
 "no_biological_system_count_or_final_subtype_promoted":True,
 "E_values_not_comparable_to_original_full_genome_search":True,
 "model_interpretation_requires_gene_neighborhood_completeness_and_array_or_target_assessment":True}
 (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n")
 print("PASS_STAGE10C_INDEPENDENT_TARGETED_HMMER_MODEL_CHECK",len(seq),"PEPTIDES",len(results),"DOMAINS",flush=True)
 print("NO_HISTORICAL_STOCK_REPORT_OR_BIOLOGICAL_ACCEPTANCE_CLAIM",flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  print("FAIL_STAGE10C_HMMER_TARGETED_ROLE_CHECK",type(e).__name__,e,file=sys.stderr)
  raise SystemExit(2)
