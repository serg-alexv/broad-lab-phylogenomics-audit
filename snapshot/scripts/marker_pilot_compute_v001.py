"""Bounded exploratory marker alignments/profiles; no final marker/panel acceptance."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,math,os,re,signal,subprocess,sys,time,uuid

R=Path(__file__).resolve().parents[1]
AA=set('ACDEFGHIKLMNPQRSTVWYBXZJUO')
TOOLCHAIN_SHA=None

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def inside(p):
 p=Path(p);p=(p if p.is_absolute() else R/p).resolve();p.relative_to(R);return p
def save(p,value):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 with t.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def ref(p):
 p=inside(p);return {'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def bound(value):
 p=inside(value['path'])
 if sha(p)!=value['sha256']:raise RuntimeError('Bound artifact changed: '+str(p))
 return p
def fasta(p,aligned=False):
 records={};name=None;parts=[]
 def add():
  if name is None:return
  sequence=''.join(parts).upper()
  if not sequence or name in records:raise ValueError('Empty sequence or duplicate FASTA identifier: '+str(name))
  allowed=AA|({'-','.'}if aligned else {'*'})
  if set(sequence)-allowed:raise ValueError('Invalid amino acid symbol in '+name)
  if not aligned and '*' in sequence[:-1]:raise ValueError('Internal stop in '+name)
  records[name]=sequence
 for line in Path(p).read_text(encoding='utf-8').splitlines():
  line=line.strip()
  if not line:continue
  if line.startswith('>'):
   add();name=line[1:].split()[0];parts=[]
   if not name:raise ValueError('Empty FASTA name')
  elif name is None:raise ValueError('Sequence before FASTA header')
  else:parts.append(line)
 add()
 if not records:raise ValueError('Empty FASTA')
 return records
def validate_alignment(records,taxa):
 observed=[n.split('|',1)[0]for n in records]
 if len(records)!=len(taxa) or len(set(observed))!=len(taxa)or set(observed)!=set(taxa):raise ValueError('Alignment must contain each declared taxon exactly once')
 lengths={len(s)for s in records.values()}
 if len(lengths)!=1:raise ValueError('Unequal alignment lengths')
 return next(iter(lengths))
def metrics(records,taxa,occupancy=.8):
 length=validate_alignment(records,taxa);n=len(records);mask=[];constant=informative=variable=0;observed_cells=0
 for i in range(length):
  counts=collections.Counter(s[i]for s in records.values()if s[i]not in '-.BXZJUO')
  observed=sum(counts.values());observed_cells+=observed;mask.append(observed/n>=occupancy)
  constant+=int(len(counts)==1);variable+=int(len(counts)>1);informative+=int(sum(v>=2 for v in counts.values())>=2)
 return {'taxa':n,'alignment_columns':length,'mean_unambiguous_occupancy':observed_cells/(length*n),'constant_columns':constant,'variable_columns':variable,'parsimony_informative_columns':informative,'retained_columns':sum(mask),'column_occupancy_threshold':occupancy,'ambiguity_excluded_from_metrics':'B X Z J U O and gaps','marker_set_acceptance':'NOT_GRANTED'},mask
def write_fasta(p,records):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 with t.open('x',encoding='utf-8',newline='\n')as f:
  for name,seq in records.items():f.write('>'+name+'\n'+seq+'\n')
  f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def proc(pid):
 raw=Path('/proc',str(pid),'stat').read_text();fields=raw.rsplit(')',1)[1].split()
 return {'pid':int(pid),'ppid':int(fields[1]),'pgrp':int(fields[2]),'start_ticks':int(fields[19]),'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'state':fields[0],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def group(pgid):
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:q=proc(int(p.name))
  except(FileNotFoundError,ProcessLookupError):continue
  if q['pgrp']==pgid:rows.append(q)
 return rows
def available():return int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))*1024
def stop_requested():return (R/'state/STOP').exists()or(R/'state/STOP_MARKER_PILOT').exists()
def exec_unit(plan_path,expected):
 plan=read(bound({'path':str(plan_path),'sha256':expected}));birth=proc(os.getpid())
 save(plan['birth_path'],{'token':plan['token'],'identity':birth,'command_sha256':plan['command_sha256']})
 os.chdir(inside(plan['cwd']));env={**os.environ,**plan['environment']}
 os.execvpe(plan['argv'][0],plan['argv'],env)

def run_unit(folder,name,argv,input_refs,output_name,admission,publish):
 folder=inside(folder);folder.mkdir(parents=True,exist_ok=True);commit=folder/(name+'_committed.json')
 tool=Path(argv[0]).resolve();signature={'argv':argv,'inputs':input_refs,'tool_path':str(tool),'tool_sha256':sha(tool),'toolchain_sha256':TOOLCHAIN_SHA,'script_sha256':sha(__file__),'cpu':admission['cpu'],'max_rss_bytes':admission['max_rss_bytes'],'linux_available_stop_bytes':admission['linux_available_stop_bytes'],'timeout_seconds':admission['unit_timeout_seconds']}
 signature_sha=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
 if commit.exists():
  c=read(commit)
  if c['signature_sha256']!=signature_sha:raise RuntimeError('Completed unit has different command/input/tool: '+name)
  receipt=read(bound(c['execution']))
  if receipt.get('actual_exit_code')!=0 or receipt.get('owned_group_empty')is not True:raise RuntimeError('Resume requires actual successful closed group')
  bound(c['output']);return c
 # Unknown old attempts are preserved and may not overlap a new owned group.
 for p in folder.glob(name+'_attempt_*/birth.json'):
  old=read(p)['identity']
  try:live=proc(old['pid'])
  except(FileNotFoundError,ProcessLookupError):live=None
  if live and live['start_ticks']==old['start_ticks']:raise RuntimeError('Prior unit owner still live; no duplicate')
  if group(old['pgrp']):raise RuntimeError('Prior process group not closed; no duplicate')
 attempt=folder/(name+'_attempt_'+uuid.uuid4().hex);attempt.mkdir();scratch=attempt/'tmp';scratch.mkdir();out=attempt/output_name
 # Output position is replaced only in the new immutable command copy.
 command=[str(out)if x=='{OUTPUT}'else x for x in argv]
 env={'TMPDIR':str(scratch),'TMP':str(scratch),'TEMP':str(scratch),'MAFFT_TMPDIR':str(scratch),'XDG_CACHE_HOME':str(scratch/'cache'),'XDG_CONFIG_HOME':str(scratch/'config'),'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','TF_NUM_INTRAOP_THREADS':'1','TF_NUM_INTEROP_THREADS':'1'}
 plan={'token':uuid.uuid4().hex,'argv':command,'command_sha256':hashlib.sha256(json.dumps(command).encode()).hexdigest(),'cwd':str(attempt),'environment':env,'birth_path':str(attempt/'birth.json')};save(attempt/'plan.json',plan)
 started=utc();clock=time.monotonic();peak=0;min_available=None;error=None;child=None;code=None;birth=None;captured={}
 try:
  if stop_requested():raise InterruptedError('Marker/global stop requested')
  if available()<admission['linux_available_stop_bytes']:raise MemoryError('Marker preferential stop: insufficient shared headroom')
  with (attempt/'stdout.txt').open('wb')as stdout,(attempt/'stderr.txt').open('wb')as stderr:
   child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--_exec-unit',str(attempt/'plan.json'),'--_exec-plan-sha',sha(attempt/'plan.json')],stdout=stdout,stderr=stderr,start_new_session=True)
   while child.poll()is None:
    if (attempt/'birth.json').exists():birth=read(attempt/'birth.json')
    rows=group(child.pid)
    for q in rows:captured[(q['pid'],q['start_ticks'],q['boot_id'])]=q
    rss=sum(q['rss_bytes']for q in rows)+proc(os.getpid())['rss_bytes'];mem=available();peak=max(peak,rss);min_available=mem if min_available is None else min(min_available,mem)
    if stop_requested():raise InterruptedError('Marker/global stop requested')
    if rss>admission['max_rss_bytes']:raise MemoryError('Marker summed RSS limit')
    if mem<admission['linux_available_stop_bytes']:raise MemoryError('Marker preferential shared-headroom stop')
    if time.monotonic()-clock>admission['unit_timeout_seconds']:raise TimeoutError('Marker unit deadline')
    publish(name,peak,mem);time.sleep(.15)
   code=child.wait()
  birth=read(attempt/'birth.json')
  if birth['token']!=plan['token']or birth['identity']['pid']!=child.pid or birth['command_sha256']!=plan['command_sha256']:raise RuntimeError('Birth/command identity mismatch')
  if group(child.pid):raise RuntimeError('Successful direct exit left owned group members')
  if code!=0:raise RuntimeError('Marker scientific unit exit '+str(code))
  if name=='mafft':out.write_bytes((attempt/'stdout.txt').read_bytes())
  if not out.exists()or not out.stat().st_size:raise RuntimeError('Missing or empty required output')
 except BaseException as ex:
  error={'type':type(ex).__name__,'message':str(ex)}
  if child is not None:
   for sig,seconds in ((signal.SIGTERM,3),(signal.SIGKILL,3)):
    current_members=group(child.pid)
    if current_members:
     if not any((q['pid'],q['start_ticks'],q['boot_id'])in captured for q in current_members):raise RuntimeError('Cannot signal group whose captured creation identity is absent')
     os.killpg(child.pid,sig);until=time.monotonic()+seconds
     while group(child.pid)and time.monotonic()<until:time.sleep(.05)
   try:code=child.wait(timeout=1)
   except subprocess.TimeoutExpired:pass
 finally:
  closed=child is not None and not group(child.pid)
  receipt={'status':'UNIT0_CLOSED'if error is None else'FAILED_UNKNOWN_OR_INTERRUPTED','unit':name,'started_utc':started,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-clock,'actual_exit_code':code,'owned_group_empty':closed,'birth':birth,'captured_owned_identities':list(captured.values()),'peak_summed_owned_rss_bytes':peak,'minimum_linux_available_bytes':min_available,'signature':signature,'signature_sha256':signature_sha,'executed_argv':command,'error':error}
  save(attempt/'execution.json',receipt)
 if error:raise RuntimeError(json.dumps({'unit':name,'attempt':str(attempt),'error':error}))
 c={'status':'ACTUAL0_CLOSED_OUTPUT_COMMITTED','signature_sha256':signature_sha,'execution':ref(attempt/'execution.json'),'output':ref(out)};save(commit,c);return c

def main(a):
 global TOOLCHAIN_SHA
 if os.name!='posix':raise RuntimeError('This computation requires Linux; import/format fixtures are portable')
 manifest_path=inside(a.input_manifest);manifest=read(manifest_path);admission=read(inside(a.admission));out=inside(a.output);out.mkdir(parents=True,exist_ok=True)
 if admission.get('status')!='ROOT_ADMITTED_EXPLORATORY_MARKER_PILOT'or admission.get('input_manifest_sha256')!=sha(manifest_path)or admission.get('script_sha256')!=sha(__file__):raise RuntimeError('Fresh exact Root shared-resource admission required')
 if admission.get('max_rss_bytes')is None or not 0<admission['max_rss_bytes']<=256*1024**2 or admission.get('linux_available_stop_bytes',0)<int(1.25*1024**3)or not 0<admission.get('unit_timeout_seconds',0)<=180:raise RuntimeError('Marker resource bounds differ')
 cpu=admission['cpu']
 if type(cpu)is not int or cpu not in os.sched_getaffinity(0)or cpu in(0,1):raise RuntimeError('One QC-unused CPU2/3 required')
 os.sched_setaffinity(0,{cpu})
 tools={}
 for tool in('mafft','hmmbuild'):
  spec=admission['tools'][tool];p=Path(spec['path']).resolve()
  if sha(p)!=spec['sha256']:raise RuntimeError('Pinned tool changed: '+tool)
  tools[tool]=str(p)
 tool_files=[{'path':p,'sha256':sha(p),'bytes':Path(p).stat().st_size}for p in tools.values()]
 helpers=Path(tools['mafft']).parent.parent/'libexec/mafft'
 if helpers.is_dir():
  for p in sorted(helpers.rglob('*')):
   if p.is_file():tool_files.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
 TOOLCHAIN_SHA=hashlib.sha256(json.dumps(tool_files,sort_keys=True).encode()).hexdigest();save(out/'toolchain_snapshot.json',{'files':tool_files,'canonical_sha256':TOOLCHAIN_SHA,'source':'Read-only existing executable/helper files; no old scientific results'})
 taxa=[t if isinstance(t,str)else t['accession']for t in manifest['taxa']]
 if len(taxa)!=10 or len(set(taxa))!=10:raise ValueError('Exploratory pilot requires ten unique declared taxa')
 candidates=manifest['candidates'];names=[str(c.get('id',c.get('marker_id','')))for c in candidates]
 if len(set(names))!=len(names)or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',n)for n in names):raise ValueError('Unsafe or duplicate candidate IDs')
 started=utc();owner=proc(os.getpid());done=0;rows=[];last=0;current=None
 def publish(unit,peak=None,mem=None,terminal=None):
  nonlocal last
  if terminal is None and time.monotonic()-last<30:return
  stage={'id':'06','name':'Marker discovery and orthology','status':terminal or'RUNNING','operation':'EXPLORATORY_MARKER_ALIGNMENT_AND_PROFILE_BUILD','detail':str(current)+' / '+unit,'done':done,'total':len(candidates),'unit':'processed pilot marker candidates','started_utc':started,'updated_utc':utc(),'pid':a.native_pid or os.getpid(),'creation_time_utc':a.native_creation_utc or None,'linux_owner_identity':owner,'cpu_affinity':[cpu],'summed_owned_rss_bytes':peak,'linux_available_bytes':mem,'source_taxonomy_and_final_panel_acceptance':'NOT_GRANTED','marker_set_acceptance':'NOT_GRANTED','log_path':str(out/'progress.json'),'input_manifest':ref(manifest_path),'admission':ref(inside(a.admission))}
  save(out/'progress.json',stage);save(R/'state/stages/06.json',stage);last=time.monotonic()
 publish('starting',terminal='RUNNING')
 try:
  for candidate,name in zip(candidates,names):
   current=name;folder=out/'candidates'/name;folder.mkdir(parents=True,exist_ok=True);final=folder/'candidate_commit.json'
   source=inside(candidate.get('fasta_path',candidate.get('path',candidate.get('fasta',''))))
   expected=candidate.get('sha256',candidate.get('fasta_sha256'))
   if not expected or sha(source)!=expected:raise RuntimeError('Candidate input hash mismatch: '+name)
   records=fasta(source);normalized={n:s[:-1]if s.endswith('*')else s for n,s in records.items()};validate_alignment({n:'A'for n in normalized},taxa)
   normalized_path=folder/'input_for_alignment.faa'
   if not normalized_path.exists():write_fasta(normalized_path,normalized)
   elif fasta(normalized_path)!=normalized:raise RuntimeError('Normalized input differs on resume')
   align=run_unit(folder,'mafft',[tools['mafft'],'--amino','--retree','1','--maxiterate','0','--thread','1','--inputorder','--quiet',str(normalized_path)],[ref(source),ref(normalized_path)],'alignment.faa',admission,publish)
   aligned=fasta(bound(align['output']),aligned=True);m,mask=metrics(aligned,taxa,a.occupancy)
   trimmed={n:''.join(x for x,keep in zip(s,mask)if keep)for n,s in aligned.items()};trim=folder/'trimmed.faa';write_fasta(trim,trimmed)if m['retained_columns']else None
   save(folder/'metrics.json',{'candidate':name,**m,'column_mask':mask,'source':ref(source),'alignment':align['output'],'terminal_stops_removed':[n for n,s in records.items()if s.endswith('*')]})
   result={'id':name,'source':ref(source),'mafft':align,'metrics':ref(folder/'metrics.json'),'scope':'PILOT_CANDIDATE_ONLY','marker_set_acceptance':'NOT_GRANTED'}
   if m['retained_columns']>=a.minimum_columns and all(any(c in AA for c in s)for s in trimmed.values()):
    profile=run_unit(folder,'hmmbuild',[tools['hmmbuild'],'--cpu','1','-n',name,'{OUTPUT}',str(trim)],[ref(trim)],'profile.hmm',admission,publish);result.update(status='ALIGNED_PROFILE_BUILT_EXPLORATORY',trimmed=ref(trim),profile=profile)
   else:result.update(status='CANDIDATE_REJECTED_ALIGNMENT_LENGTH_OR_EMPTY_TAXON',reason='Trimmed columns/remaining sequence do not satisfy explicit pilot criteria')
   save(final,result);rows.append(result);done+=1;save(out/'completed_candidates.json',{'rows':rows,'processed':done,'total':len(candidates),'marker_set_acceptance':'NOT_GRANTED'});publish('candidate checkpoint',terminal='RUNNING')
  save(out/'result.json',{'status':'EXPLORATORY_PILOT_COMPUTATION_COMPLETE','input_manifest':ref(manifest_path),'admission':ref(inside(a.admission)),'processed_candidates':done,'profiles':sum(r['status']=='ALIGNED_PROFILE_BUILT_EXPLORATORY'for r in rows),'rejected':sum(r['status']!='ALIGNED_PROFILE_BUILT_EXPLORATORY'for r in rows),'rows':rows,'marker_set_acceptance':'NOT_GRANTED','full_panel_testing':'NOT_RUN'});publish('exploratory candidate computation complete',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as ex:
  save(out/'failure.json',{'status':'MARKER_PILOT_STOPPED_PRESERVE_CHECKPOINTS','error':repr(ex),'processed_candidates':done,'current':current,'all_unfinished_states':'UNKNOWN_OR_NOT_RUN','previous_completed_outputs_preserved':True});publish(str(ex),terminal='STOPPED');raise

if __name__=='__main__':
 if '--_exec-unit'in sys.argv:
  i=sys.argv.index('--_exec-unit');j=sys.argv.index('--_exec-plan-sha');exec_unit(inside(sys.argv[i+1]),sys.argv[j+1])
 else:
  p=argparse.ArgumentParser();p.add_argument('--input-manifest',required=True);p.add_argument('--admission',required=True);p.add_argument('--output',required=True);p.add_argument('--occupancy',type=float,default=.8);p.add_argument('--minimum-columns',type=int,default=30);p.add_argument('--native-pid',type=int);p.add_argument('--native-creation-utc');a=p.parse_args()
  if not 0<a.occupancy<=1 or a.minimum_columns<1:p.error('Invalid explicit alignment criteria')
  main(a)
