"""Finite PADLOC R/core compatibility smoke in a private mount view; no genome search."""
from pathlib import Path
import sys,os,json,subprocess,time,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import checkm2_owned_cleanup_T1 as own
E=R/'work/padloc_native_controls_20261029';E.mkdir(exist_ok=False);start=time.monotonic();os.sched_setaffinity(0,{3});known={}

def save(name,data):
 p=E/name;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(data,indent=2));os.replace(t,p)

runtime=R/'tools/padloc_oci_case_runtime_20261029/usr/local';before=os.readlink('/proc/self/ns/mnt');subprocess.run(['mount','--bind',str(runtime),'/usr/local'],check=True);subprocess.run(['mount','-o','remount,bind,ro','/usr/local'],check=True)
save('private_namespace.json',{'mount_namespace':before,'bound_project_runtime':str(runtime.relative_to(R)),'visible_prefix':'/usr/local','read_only_private_binding':True,'no_host_path_bytes_or_global_WSL_configuration_changed':True})
for sub in ['home','cache','tmp','emptylibs']:(E/sub).mkdir()
env=os.environ.copy();env.update(HOME=str(E/'home'),XDG_CACHE_HOME=str(E/'cache'),XDG_DATA_HOME=str(E/'home'),TMPDIR=str(E/'tmp'),R_TMPDIR=str(E/'tmp'),R_LIBS_USER=str(E/'emptylibs'),R_PROFILE_USER='/dev/null',R_ENVIRON_USER='/dev/null',R_HISTFILE=str(E/'history'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PATH=str(R/'tools/bioenv/bin')+':/usr/local/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/usr/local/lib:/usr/local/lib/R/lib')

def guard():
 if time.monotonic()-start>600:raise TimeoutError('Bounded600s PADLOC native controls')
 if(R/'state/STOP').exists():raise InterruptedError('ProjectSTOP')
 available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
 if available<1610612736:raise RuntimeError('PREPARATION stops below1.5GiB available to preserve marker')

def run(name,argv):
 guard();folder=E/name;folder.mkdir();p=None;identity=None;members={};error=None;peak=0;t=time.monotonic()
 save(name+'/command.json',{'argv':argv,'CPU_affinity':[3],'maximum_RSS':536870912,'minimum_available':1610612736,'no_genomes_or_model_search':True})
 try:
  with(folder/'stdout.txt').open('wb')as out,(folder/'stderr.txt').open('wb')as err:
   p=subprocess.Popen(argv,cwd=E,env=env,stdout=out,stderr=err,start_new_session=True);identity=own.identity(p.pid);members[p.pid]=identity
   while p.poll()is None:
    guard();own.track_descendants(identity,members);rss=0
    for q in members.values():
     if own.current_matching(q)is not None:
      try:rss+=int(Path('/proc/'+str(q['pid'])+'/stat').read_text().rsplit(')',1)[1].split()[21])*os.sysconf('SC_PAGE_SIZE')
      except FileNotFoundError:pass
    peak=max(peak,rss)
    if rss>536870912:raise RuntimeError('R smoke ownedRSS exceeds512MiB')
    time.sleep(.2)
   code=p.wait()
  if code!=0:raise RuntimeError(name+' actualexit '+str(code))
 except BaseException as exc:
  error=repr(exc)
  if p is not None:save(name+'/cleanup.json',own.cleanup_linux_helper(p,identity,members,E/'STOP','R_SMOKE_'+str(os.getpid())))
  raise
 finally:
  remaining=[q for q in members.values()if own.current_matching(q)is not None]
  save(name+'/execution.json',{'actual_exit_code':p.returncode if p is not None else None,'actual_child_waited_and_reaped':p is not None and p.poll()is not None,'child_identity':identity,'captured_owned_identities':list(members.values()),'remaining_owned_identities':remaining,'group_closed':not remaining,'peak_sampled_owned_RSS_bytes':peak,'elapsed_seconds':time.monotonic()-t,'error':error})
  if remaining and error is None:raise RuntimeError('R smoke descendants remain')

try:
 import csv,shutil
 fixture=R/'evidence/model_routes/PADLOC_20261029';faa=fixture/'protein-example.faa';gff=fixture/'protein-example.gff';data=R/'tools/databases/padloc_compiled_v2_20261029';positive=E/'positive_output';positive.mkdir()
 argv=['/usr/local/bin/padloc','--data',str(data),'--faa',str(faa),'--gff',str(gff),'--outdir',str(positive),'--cpu','1'];run('PADLOC_positive',argv)
 report=positive/'protein-example_padloc.csv'
 with report.open()as f:rows=list(csv.DictReader(f))
 brex=[q for q in rows if q['system']=='brex_type_I'];targets={q['target.name']for q in brex};proteins={q['protein.name']for q in brex}
 if len(targets)!=6 or proteins!={'BrxA','BrxB','BrxC','PglX','PglZ','BrxL'}or len({q['system.number']for q in brex})!=1:raise RuntimeError('Official BREXI positive did not contain exact complete six-gene system')
 raw=positive/'protein-example.domtblout'
 if '# [ok]'not in raw.read_text()[-4000:]:raise RuntimeError('Full public control rawHMM search incomplete')
 save('positive_validation.json',{'status':'OFFICIAL_PUBLIC_PROTEIN_CONTROL_COMPLETE_BREX_I_PASS','selected_rows':brex,'all_other_calls_retained':rows,'unavailable_RNA_input_states':'UNKNOWN_FOR_APPLICABLE_MODELS_NOT_NEGATIVE','official_precomputed_CSV_is_reference_only':True})
 # Identical searched proteins; only the explicit synthetic BrxA contig differs.
 moved=next(q['target.name']for q in brex if q['protein.name']=='BrxA');synthetic=E/'counterfactual_split_BrxA.gff';lines=[];changed=0
 for line in gff.read_text().splitlines():
  if line.startswith('#')or not line:lines.append(line);continue
  fields=line.split('\t');attrs={a.split('=',1)[0]:a.split('=',1)[1]for a in fields[8].split(';')if'='in a}
  if moved in attrs.values()or 'cds-'+moved in attrs.values():fields[0]='SYNTHETIC_SEPARATE_CONTIG_BrxA';changed+=1
  lines.append('\t'.join(fields))
 if changed<1:raise RuntimeError('Could not identify public BrxA GFF feature for explicit counterfactual')
 synthetic.write_text('\n'.join(lines)+'\n');negative=E/'counterfactual_output';negative.mkdir();shutil.copyfile(raw,negative/raw.name)
 run('PADLOC_counterfactual_locus',['/usr/local/bin/padloc','--data',str(data),'--faa',str(faa),'--gff',str(synthetic),'--outdir',str(negative),'--cpu','1'])
 if hashlib.sha256(raw.read_bytes()).hexdigest()!=hashlib.sha256((negative/raw.name).read_bytes()).hexdigest():raise RuntimeError('Reused exact search changed')
 with(negative/'protein-example_padloc.csv').open()as f:counter=list(csv.DictReader(f))
 if any(q['system']=='brex_type_I'for q in counter):raise RuntimeError('Incomplete same-contig BREX locus produced complete call across synthetic contig boundary')
 stdout=(E/'PADLOC_counterfactual_locus/stdout.txt').read_text()
 if 'domtblout already exists'not in stdout:raise RuntimeError('Supported savedsearch skip was not observed')
 save('COMPLETE.json',{'status':'PADLOC2_FULL_CURRENT_MODEL_NATIVE_POSITIVE_AND_INCOMPLETE_CONTIG_LOCUS_CONTROLS_PASS','full_positive_actual0':True,'complete_BREX_I_six_gene_positive':brex,'counterfactual_separate_BrxA_complete_BREX_absent':True,'counterfactual_explicitly_synthetic_not_biological_genome':True,'same_exact_original_FAA_and_search_reused':True,'original_public_GFF_unchanged':True,'all_original_model_files_preserved':True,'all_other_counterfactual_calls_retained':counter,'RNA_feature_dependent_unavailable_states':'UNKNOWN','no_project_genomes_searched':True,'elapsed_seconds':time.monotonic()-start});print('PADLOC_NATIVE_CONTROLS_PASS',flush=True)
except BaseException as exc:save('FAILED.json',{'error':repr(exc),'saved_successful_searches_preserved':True,'no_biological_absence_inferred':True});raise
