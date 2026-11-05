"""Independently compare original archive identity/dependencies to solved records."""
from pathlib import Path
import datetime as dt,hashlib,json,os
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
def load(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 handoff=load(E/'cache_handoff.json');manifest=E/'resolved_packages.json';assert sha(manifest)==handoff['resolved_manifest_sha256']=='a8cd65d5fc4d7294aa38d05412a41fc527530fa564b08cf8a6d0088abce70a52'
 sources={r['fn']:r for r in load(manifest)};summary_path=R/handoff['notice_manifest'];assert sha(summary_path)==handoff['notice_manifest_sha256'];summary=load(summary_path)
 checks=[];errors=[]
 for package in summary['packages']:
  row=sources[Path(package['archive']).name]
  entries=[n for n in package['preserved_files'] if n['original_path']=='info/index.json'];assert len(entries)==1
  entry=entries[0];source=R/entry['preserved_object'];assert sha(source)==entry['sha256'];index=load(source)
  mismatch={k:{'record':row.get(k),'archive':index.get(k)} for k in ('name','version','build','build_number','subdir') if row.get(k)!=index.get(k)}
  dependencies_equal=sorted(row.get('depends',[]))==sorted(index.get('depends',[]))
  # Channel repodata may legitimately hotfix original archive dependency records.
  checks.append({'name':row['name'],'identity_matches':not mismatch,'identity_mismatch':mismatch,'dependencies_match_original_archive':dependencies_equal,'channel_dependency_record':row.get('depends',[]),'original_archive_dependencies':index.get('depends',[]),'archive_index_sha256':entry['sha256']})
  if mismatch:errors.append({'name':row['name'],'mismatch':mismatch})
 result={'status':'PASS_IDENTITIES_MATCH' if not errors else 'FAIL_IDENTITY_MISMATCH','resolved_manifest_sha256':sha(manifest),'package_count':len(checks),'identity_errors':errors,'dependency_hotfix_difference_count':sum(not x['dependencies_match_original_archive'] for x in checks),'checks':checks,'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'runtime_compatibility_tested':False}
 target=E/'cache_independent_audit.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');os.replace(tmp,target)
 print(json.dumps({k:v for k,v in result.items() if k!='checks'}));return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
