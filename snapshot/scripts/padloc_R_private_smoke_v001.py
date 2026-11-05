"""Finite PADLOC R/core compatibility smoke in a private mount view; no genome search."""
from pathlib import Path
import sys,os,json,subprocess,time,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import checkm2_owned_cleanup_T1 as own
E=R/'work/padloc_R_smoke_20261029';E.mkdir(exist_ok=False);start=time.monotonic();os.sched_setaffinity(0,{3});known={}

def save(name,data):
 p=E/name;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(data,indent=2));os.replace(t,p)

runtime=R/'tools/padloc_oci_case_runtime_20261029/usr/local';before=os.readlink('/proc/self/ns/mnt');subprocess.run(['mount','--bind',str(runtime),'/usr/local'],check=True);subprocess.run(['mount','-o','remount,bind,ro','/usr/local'],check=True)
save('private_namespace.json',{'mount_namespace':before,'bound_project_runtime':str(runtime.relative_to(R)),'visible_prefix':'/usr/local','read_only_private_binding':True,'no_host_path_bytes_or_global_WSL_configuration_changed':True})
for sub in ['home','cache','tmp','emptylibs']:(E/sub).mkdir()
env=os.environ.copy();env.update(HOME=str(E/'home'),XDG_CACHE_HOME=str(E/'cache'),XDG_DATA_HOME=str(E/'home'),TMPDIR=str(E/'tmp'),R_TMPDIR=str(E/'tmp'),R_LIBS_USER=str(E/'emptylibs'),R_PROFILE_USER='/dev/null',R_ENVIRON_USER='/dev/null',R_HISTFILE=str(E/'history'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PATH=str(R/'tools/bioenv/bin')+':/usr/local/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/usr/local/lib:/usr/local/lib/R/lib')

def guard():
 if time.monotonic()-start>180:raise TimeoutError('Bounded180s R core smoke')
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
 code="suppressPackageStartupMessages(library(tidyverse));library(getopt);library(yaml);p=c('tidyverse','getopt','yaml');v=vapply(p,function(x)as.character(packageVersion(x)),character(1));stopifnot(as.character(getRversion())=='4.3.1',identical(unname(v),c('2.0.0','1.20.3','2.3.7')));print(R.version.string);print(v);print(.libPaths())"
 run('R_libraries',['/usr/local/bin/Rscript','--vanilla','-e',code]);run('PADLOC_help',['/usr/local/bin/padloc','--help'])
 save('CORE_READY.json',{'status':'PRIVATE_READONLY_EXACT_PADLOC2_R_RUNTIME_CORE_READY','R':'4.3.1','tidyverse':'2.0.0','getopt':'1.20.3','yaml':'2.3.7','original_OCI_prefix_bound_only_in_private_namespace':True,'all_unit_actual0_and_closed':True,'no_model_or_genome_search':True,'elapsed_seconds':time.monotonic()-start})
 print('PADLOC_R_CORE_SMOKE_PASS',flush=True)
except BaseException as exc:save('FAILED.json',{'error':repr(exc),'no_biological_absence_inferred':True});raise
