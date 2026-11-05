from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
R=Path(__file__).resolve().parents[1]
subprocess.run([__import__('sys').executable,str(R/'scripts/write_startup_report.py')],check=True)
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp')
 with t.open('w',encoding='utf-8') as f:json.dump(x,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); D=R/'checkpoints'/stamp;D.mkdir(parents=True)
receipts=[read(p) for p in sorted((R/'raw').glob('GC[AF]_*/acquisition_receipt.json'))]
sel=read(R/'metadata/selection_summary.json')
status={'at_utc':stamp,'host':os.environ.get('COMPUTERNAME'),'committed_genomes':len(receipts),'bases':sum(x['sequence_qc']['total_sequence_length'] for x in receipts),'panel_genomes':sel['panel_count'],'panel_species':sel['selected_species'],'biological_qc':'NOT_RUN','marker_discovery':'NOT_RUN','phylogeny':'NOT_RUN','padloc':'NOT_RUN','defensefinder':'NOT_RUN','snapshot_is_not_liveness_proof':True}
status['production_marker_discovery']=status.pop('marker_discovery')
if (R/'state/pilot10_last_exit.json').exists():
 pilot=read(R/'state/pilot10_last_exit.json')
 status['pilot_marker_discovery']={'status':pilot.get('status'),'run_id':pilot.get('run_id'),'note':'Exploratory10-genome candidate clusters, not accepted production markers','evidence':'analysis/pilot10/mmseqs_failure_and_correction.json'}
if (R/'state/discovery_universe_accessions.json').exists():status['source_census']=read(R/'state/discovery_universe_accessions.json')
for folder in ('state','metadata','qc'):
 (D/folder).mkdir()
 for p in (R/folder).glob('*'):
  if p.is_file() and p.suffix in ('.json','.tsv','.md'):shutil.copyfile(p,D/folder/p.name)
save(D/'status.json',status);save(R/'state/current_brief.json',status)
artifacts=[]
for folder in ('docs','scripts','config','metadata','raw','qc','evidence'):
 for p in sorted((R/folder).rglob('*')):
  rel=p.relative_to(R)
  if p.is_file() and not any(x.startswith('.') for x in rel.parts) and p.suffix not in ('.tmp','.part','.pyc'):
   artifacts.append({'path':rel.as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
if (R/'analysis').exists():
 linux_root='/mnt/'+R.drive[0].lower()+'/'+str(R)[3:].replace('\\','/')
 subprocess.run(['wsl','-d','Ubuntu','--','/usr/bin/python3',linux_root+'/scripts/manifest_linux_analysis.py'],check=True,timeout=120)
 lm=R/'manifests/linux_analysis_files.json'
 artifacts.extend(read(lm)['artifacts'])
 artifacts.append({'path':lm.relative_to(R).as_posix(),'bytes':lm.stat().st_size,'sha256':sha(lm)})
for name in ('README.md','AGENTS.md','STARTUP_REPORT.md'):
 p=R/name
 if p.exists():artifacts.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
save(R/'manifests'/f'{stamp}.json',{'snapshot_utc':stamp,'artifacts':artifacts,'note':'Committed artifacts at snapshot; per-genome immutable receipts also enumerate hashes. Changing metadata is archived under checkpoints and local Git history.'})
(R/'STATUS.md').write_text(f"# Tree 2 execution checkpoint\n\nAs of {stamp} UTC on WD.\n\nCommitted acquired genomes: **{len(receipts)}**. Provisional panel: **{sel['panel_count']} genomes / {sel['selected_species']} species**.\n\nProduction biological QC, accepted markers, trees, PADLOC and DefenseFinder: **NOT_RUN**. Source/sequence validation is distinct from biological QC. The completed ten-genome gene-prediction and candidate-cluster pilot is exploratory; see analysis/pilot10/mmseqs_failure_and_correction.json.\n\nDownloads may be running. Check matching process creation identity, OS locks and terminal exit receipts before resuming. This snapshot is not liveness evidence.\n\nPlan: docs/STAGE_PLAN.md. Sources: docs/SOURCES.md. Snapshot: checkpoints/{stamp}/status.json. SHA256 manifest: manifests/{stamp}.json. No GitHub operations.\n",encoding='utf-8')
print(json.dumps({**status,'manifest_artifacts':len(artifacts)}))

