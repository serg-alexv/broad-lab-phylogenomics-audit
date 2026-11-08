#!/usr/bin/env python3
"""Extract exactly 44 preserved, identified original proteins across nine LAB genomes.

Read-only and pinned: downloads frozen 5 Nov GitHub release data, independently hashes
every compressed split archive part and exact selected source member against original
per-file manifest, then emits only selected peptides, native coordinate TSV, provenance.
No HMMER/model search and no original cohort ledger edits.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

REPO="serg-alexv/broad-lab-phylogenomics-audit"
TAG="tree2-audit-20261105"
COHORT={
 "GCF_001885945.1": "gene001500 gene001501 gene001502 gene001503",
 "GCF_002706745.1": "gene001916 gene001920 gene001921 gene001922",
 "GCF_003946485.1": "gene001001 gene001002 gene001004",
 "GCF_016861785.1": "gene000293 gene000294 gene000297 gene000298 gene000299 gene000300 gene000301 gene000302",
 "GCF_024397795.1": "gene001579 gene001580 gene001581 gene001582 gene001583 gene001584 gene001585 gene001586 gene001587",
 "GCF_053758405.1": "gene000563 gene000564 gene000565 gene000566 gene000567",
 "GCF_053761245.1": "gene000954 gene000955 gene000956 gene000957",
 "GCF_054784775.1": "gene000252 gene000253 gene000255",
 "GCF_057364865.1": "gene001150 gene001151 gene001152 gene001153"
}
COHORT={acc:{acc+"|"+g for g in genes.split()} for acc,genes in COHORT.items()}
def require(x,msg):
 if not x: raise RuntimeError(msg)
def checksum(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url,path):
 for attempt in range(3):
  p=subprocess.run(["curl","--location","--fail","--silent","--show-error",
                    "--retry","3","--retry-delay","2","--connect-timeout","30",
                    "--max-time","1000","--output",str(path),url])
  if p.returncode==0:return
  time.sleep(2)
 require(False,"Unable to download pinned original release asset "+path.name)
def read_records(data):
 title=None; seq=[]
 for ln in data.decode("ascii").splitlines():
  if ln.startswith(">"):
   if title is not None:yield title,"".join(seq)
   title=ln[1:].split()[0];seq=[]
  elif ln.strip():seq.append(ln.strip())
 if title is not None:yield title,"".join(seq)
def main():
 require(len(sys.argv)==3,"Expected WORK_DIRECTORY OUTPUT_DIRECTORY")
 wd,out=Path(sys.argv[1]),Path(sys.argv[2])
 require(not out.exists(),"Output already exists; refuse overwrite")
 out.mkdir(parents=True);wd.mkdir(parents=True,exist_ok=True)
 index=json.loads(Path("handoff/package_index.json").read_text())
 pack=next(a for a in index["archives"] if a["group"]=="results--uniform_annotation_v001")
 parts=[]
 for i,r in enumerate(pack["parts"]):
  name=Path(r["path"]).name
  dest=wd/name
  if not dest.exists():
   fetch("https://github.com/"+REPO+"/releases/download/"+TAG+"/"+name,dest)
  require(dest.stat().st_size==r["bytes"] and checksum(dest)==r["sha256"],
          "Pinned original compressed part mismatches "+name)
  parts.append(dest)
  print("PINNED_ANNOTATION_PART",i+1,len(pack["parts"]),name,flush=True)
 manifest=pack["manifest"]
 mf=wd/"manifest--results--uniform_annotation_v001.ndjson"
 if not mf.exists():
  fetch("https://github.com/"+REPO+"/releases/download/"+TAG+"/"+mf.name,mf)
 require(mf.stat().st_size==manifest["bytes"] and checksum(mf)==manifest["sha256"],
         "Pinned original file manifest differs")
 exact={}
 for line in mf.open():
  v=json.loads(line);p=v["path"]
  for acc in COHORT:
   if "/"+acc+"/" in p and p.endswith(("/proteins.faa","/protein_coordinate_map.tsv")):
    exact[p]=v
 require(len(exact)==len(COHORT)*2,"Missing one of nine original FASTA/coordinate sources")
 source_hashes={}
 seqs={}
 maps={}
 with subprocess.Popen(["cat",*[str(x) for x in parts]],stdout=subprocess.PIPE) as process:
  with tarfile.open(fileobj=process.stdout,mode="r|gz") as tar:
   for member in tar:
    name=member.name.lstrip("./")
    if name not in exact:continue
    require(member.isfile(),"Source member must be file "+name)
    blob=tar.extractfile(member).read()
    v=exact[name]
    require(len(blob)==v["bytes"] and sha(blob)==v["sha256"],
            "Original file manifest mismatch "+name)
    require(name not in source_hashes,"Duplicate member "+name)
    source_hashes[name]={"sha256":sha(blob),"bytes":len(blob)}
    acc=next(a for a in COHORT if "/"+a+"/" in name)
    if name.endswith("/proteins.faa"):
     chosen={}
     for pid,protein in read_records(blob):
      if pid in COHORT[acc]:
       require(pid not in chosen,"Duplicate FASTA ID "+pid)
       chosen[pid]=protein
     require(set(chosen)==COHORT[acc],
             "Original FASTA not bound to every expected target: "+acc+
             " found="+str(sorted(chosen)))
     seqs[acc]=chosen
    else:
     maps[acc]=blob
  require(process.wait()==0,"Source tar stream process failed")
 require(len(source_hashes)==len(exact) and len(seqs)==len(COHORT)
         and len(maps)==len(COHORT),"Incomplete selected source records")
 results={}
 with (out/"44_verified_original_source_peptides.faa").open("w") as fasta:
  for acc in sorted(seqs):
   results[acc]={}
   for pid,seq in sorted(seqs[acc].items()):
    fasta.write(">"+pid+"\n"+seq+"\n")
    results[acc][pid]={"aa_length":len(seq),"aa_sha256":sha(seq.encode("ascii"))}
    # Coordinate evidence is preserved in original source map separately.
   p=out/(acc+"_original_coordinate_map.tsv")
   p.write_bytes(maps[acc])
 (out/"SOURCE_MEMBERS_ORIGINAL_HASHES.json").write_text(
    json.dumps(source_hashes,sort_keys=True,indent=2)+"\n")
 (out/"44_original_peptide_SHA256.json").write_text(
    json.dumps({"target_gene_count":sum(map(len,COHORT.values())),
                "source_release":TAG,"source_commit":"7d0622402fc00c493b18b7d630f52bae2a733d47",
                "accessions":results},sort_keys=True,indent=2)+"\n")
 print("PASS_STAGE10C_PINNED_SOURCE_PEPTIDE_EXTRACT",len(seqs),
       "GENOMES",sum(map(len,seqs.values())),"PEPTIDES",flush=True)
 print("HMMER_NOT_RUN_NO_ORIGINAL_STOCK_OUTPUT_CLAIM",flush=True)

if __name__=="__main__":
 try:main()
 except Exception as e:
  print("FAIL_STAGE10C_PINNED_SOURCE_PEPTIDE_EXTRACT",type(e).__name__,e,file=sys.stderr)
  sys.exit(2)
