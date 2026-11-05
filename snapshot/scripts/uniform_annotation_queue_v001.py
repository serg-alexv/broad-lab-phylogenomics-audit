"""Provisional uniform Prodigal queue; paired coordinates are not biological QC."""
from pathlib import Path
import argparse,collections,csv,datetime,hashlib,io,json,os,re,signal,sys,time,uuid
import marker_pilot_compute_v001 as guard

R=Path(__file__).resolve().parents[1]
QUEUE_SHA='44d456e79af0f84a2c35a2dd3e1b6f8cd748df31d17ee8273becca7a765b75f1'
SCOPE='PROVISIONAL_UNIFORM_ANNOTATION_PENDING_INDEPENDENT_QC_TAXONOMY_FINAL_PANEL_FREEZE'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def inside(p):return guard.inside(p)
def sha(p):return guard.sha(p)
def read(p):return guard.read(p)
def ref(p):return guard.ref(p)
def bound(v):
 p=guard.bound(v)
 if 'bytes'in v and p.stat().st_size!=v['bytes']:raise RuntimeError('Bound artifact size changed')
 return p
def create(p,data):
 p=inside(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if p.read_bytes()==data:return ref(p)
  raise FileExistsError('Immutable output differs '+str(p))
 t=p.with_name(p.name+'.'+uuid.uuid4().hex+'.partial')
 try:
  with t.open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.link(t,p)
 finally:
  if t.exists():t.unlink()
 return ref(p)
def jcreate(p,v):return create(p,(json.dumps(v,indent=2)+'\n').encode())
def metadata_row(x):
 return {k:x.get(k)for k in('accession','species','species_taxid','genus','family','assembly_level','main_panel_member','source_supported_scope','source_eligibility','source_holds_preserved','source_pending_reasons','source_masks','source_provenance_record','frozen_order','species_round')}
def legacy_candidate(acc):
 p=R/'analysis/pilot10/annotations'/acc/'annotation_commit.json'
 if not p.exists():return None
 receipts=[]
 for e in sorted((R/'analysis/pilot10/runs').glob('*/prodigal_'+acc+'.exit.json')):
  x=read(e)
  if x.get('exit_code')==0 and x.get('owned_group_empty')is True and not x.get('error'):receipts.append(ref(e))
 if len(receipts)!=1:raise RuntimeError('Legacy reuse requires one actual0/closed Prodigal receipt '+acc)
 return {'commit':ref(p),'execution':receipts[0]}
def prepare(a):
 qpath=inside(a.queue)
 if sha(qpath)!=QUEUE_SHA:raise RuntimeError('Canonical queue changed; Root must reconcile scope')
 q=read(qpath);chosen=[];excluded=[]
 for x in q['rows']:
  m=metadata_row(x)
  if not(x.get('source_supported_scope')is True and x.get('acquired')is True):
   excluded.append({**m,'acquired':x.get('acquired'),'status':'NOT_QUEUED_SOURCE_HELD_EXCLUDED_OR_OPTIONAL_UNACQUIRED','no_negative_call':True});continue
  if x.get('source_holds_preserved'):raise RuntimeError('Supported queue row unexpectedly source-held')
  f=x['FNA_from_receipt'];p=inside(f['path']);receipt=read(bound(x['acquisition_receipt']))
  if receipt.get('accession')!=x['accession']or receipt.get('acquisition_status')!='PASS'or p.stat().st_size!=f['bytes']:raise RuntimeError('Acquisition metadata mismatch '+x['accession'])
  matches=[z for z in receipt['files']if z['sha256']==f['sha256']and z['bytes']==f['bytes']and(inside(x['acquisition_receipt']['path']).parent/z['path']).resolve()==p]
  if len(matches)!=1:raise RuntimeError('FNA not bound by acquisition receipt '+x['accession'])
  chosen.append({**m,'FNA':f,'acquisition_receipt':x['acquisition_receipt'],'legacy_uniform_annotation':legacy_candidate(x['accession']),'independent_biological_QC':'UNRESOLVED_SEPARATE_WORKFLOW','final_panel_acceptance':False,'defence_status':'UNKNOWN_UNSEARCHED'})
 if len(chosen)!=919 or len({x['accession']for x in chosen})!=919 or len(excluded)!=260:raise RuntimeError('Unexpected919/260 scope partition')
 out=inside(a.prepare_output);out.mkdir(parents=True,exist_ok=True)
 exclusions=jcreate(out/'excluded_and_held.json',{'rows':excluded,'counts':dict(collections.Counter(x['source_eligibility']for x in excluded)),'not_interpreted_as_biological_absence':True})
 tool=R/'tools/bioenv/bin/prodigal';pkg=R/'tools/bioenv/conda-meta/prodigal-2.6.3-h577a1d6_11.json'
 m={'schema':'TREE2_PROVISIONAL_UNIFORM_ANNOTATION_QUEUE_V001','created_utc':utc(),'status':'READY_FOR_ROOT_ADMISSION_NOT_LAUNCHED','scope':SCOPE,'canonical_queue':ref(qpath),'script':ref(Path(__file__).resolve()),'guard':ref(Path(guard.__file__).resolve()),'canonicalizer':ref(R/'scripts/pilot10.py'),'prodigal':ref(tool),'prodigal_package_record':ref(pkg),'method':{'program':'Prodigal2.6.3','procedure':'single','translation_table':11,'argv_options':['-p','single','-g','11','-q'],'canonicalizer':'Unmodified scripts/pilot10.py canonicalize()','protein_identifiers':'versioned_accession|geneNNNNNN','terminal_stop_handling':'Remove one terminal* only, explicitly recorded in original map','partial_flags':'Preserve original GFF attributes plus joined integrity TSV','genetic_code_policy':'Fixed11 uniform method; non11/unresolved biological requirements remain final-panel holds'},'count':len(chosen),'species_labels':len({x['species']for x in chosen}),'families':dict(collections.Counter(x['family']for x in chosen)),'eligible_legacy_reuse_candidates':sum(x['legacy_uniform_annotation']is not None for x in chosen),'excluded':exclusions,'rows':chosen,'quality_PASS_claimed':False,'source_screening_is_independent_biological_QC':False,'final_panel_acceptance':False,'QC_only_FAAs_without_paired_GFF_not_substituted':True,'new_scientific_process_started':False,'original_notices_preserved':True}
 r=jcreate(out/'input_manifest.json',m);print(json.dumps({'manifest':r,'genomes':len(chosen),'excluded':len(excluded),'legacy_candidates':m['eligible_legacy_reuse_candidates']},indent=2))
def records(path):
 result=[];h=None;parts=[]
 for line in Path(path).read_text().splitlines():
  if line.startswith('>'):
   if h is not None:result.append((h,''.join(parts)))
   h=line[1:];parts=[]
  elif line.strip():
   if h is None:raise ValueError('Sequence before FASTA header')
   parts.append(line.strip())
 if h is not None:result.append((h,''.join(parts)))
 return result
def contig_lengths(path):
 lengths={};name=None
 with Path(path).open()as f:
  for line in f:
   if line.startswith('>'):
    name=line[1:].split()[0]
    if not name or name in lengths:raise ValueError('Duplicate/empty contig identifier')
    lengths[name]=0
   elif line.strip():
    if name is None:raise ValueError('Sequence before FNA header')
    lengths[name]+=len(line.strip())
 if not lengths or min(lengths.values())<=0:raise ValueError('Empty contig/genome')
 return lengths
def coordinates(folder,acc,fna,expected,write_folder):
 """Independent bounds/strand/ID joins over original paired FAA,GFF,FFN/map."""
 lengths=contig_lengths(fna);mapping=read(folder/'protein_coordinate_map.json');normal=records(folder/'proteins.faa');raw=records(folder/'prodigal.faa');nucleotides=records(folder/'prodigal.ffn')
 if not(expected==len(mapping)==len(normal)==len(raw)==len(nucleotides)>0):raise ValueError('CDS/protein/map cardinality mismatch')
 norm=dict(normal)
 if len(norm)!=expected:raise ValueError('Duplicate canonical protein identifier')
 gff={}
 for line in (folder/'prodigal.gff').read_text().splitlines():
  if not line or line.startswith('#'):continue
  v=line.split('\t')
  if len(v)!=9 or v[2]!='CDS'or v[6]not in('+','-')or v[7]!='0':raise ValueError('Invalid CDS GFF record')
  attrs=dict(x.split('=',1)for x in v[8].split(';')if'='in x);ident=attrs['ID']
  if ident in gff:raise ValueError('Duplicate GFF CDS identifier')
  start,end=int(v[3]),int(v[4])
  if v[0]not in lengths or not 1<=start<=end<=lengths[v[0]]:raise ValueError('CDS outside source contig')
  if attrs.get('partial')not in('00','01','10','11'):raise ValueError('Missing/unresolved original partial flag')
  gff[ident]=(v[0],start,end,v[6],attrs)
 if len(gff)!=expected:raise ValueError('GFF cardinality mismatch')
 joined=[];partials=collections.Counter();seen=set();terminal=0
 for number,(row,(header,aa),(nh,nt))in enumerate(zip(mapping,raw,nucleotides),1):
  fid=acc+'|gene'+str(number).zfill(6)
  if row['protein_id']!=fid or row['accession']!=acc:raise ValueError('Canonical identifier/order mismatch')
  fields=header.split(' # ');nf=nh.split(' # ')
  if len(fields)!=5 or len(nf)!=5:raise ValueError('Malformed original Prodigal header')
  attrs=dict(x.split('=',1)for x in fields[4].split(';')if'='in x);na=dict(x.split('=',1)for x in nf[4].split(';')if'='in x);ident=attrs['ID'];contig,start,end,strand,ga=gff[ident]
  if ident in seen or na['ID']!=ident:raise ValueError('Non-bijective FAA/GFF/FFN join')
  seen.add(ident)
  if fields[1:4]!=nf[1:4]or(int(fields[1]),int(fields[2]),'+'if int(fields[3])==1 else'-')!=(start,end,strand):raise ValueError('Original FAA/FFN/GFF coordinates disagree')
  if(row['contig'],row['start'],row['end'],row['strand'],row['prodigal_gene_id'])!=(contig,start,end,strand,ident)or row['gff_attributes']!=ga:raise ValueError('Canonical coordinate map differs')
  if attrs.get('partial')!=ga['partial']or na.get('partial')!=ga['partial']or len(nt)!=end-start+1:raise ValueError('Partial flags or nucleotide span disagree')
  removed=aa.endswith('*');seq=aa[:-1]if removed else aa
  if not seq or'*'in seq or norm.get(fid)!=seq or row['aa_length']!=len(seq)or row['terminal_stop_removed']!=removed:raise ValueError('Original/canonical protein sequence differs')
  partials[ga['partial']]+=1;terminal+=removed
  joined.append({'protein_id':fid,'accession':acc,'contig':contig,'start_1based':start,'end_1based':end,'strand':strand,'original_prodigal_gene_id':ident,'partial':ga['partial'],'nucleotide_CDS_length':len(nt),'amino_acid_length':len(seq),'terminal_stop_removed':int(removed)})
 if set(gff)!=seen:raise ValueError('Unjoined GFF CDS')
 text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(joined[0]),delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(joined)
 integrity=jcreate(write_folder/'coordinate_validation.json',{'status':'PASS_PAIRED_CDS_COORDINATE_INTEGRITY_NOT_BIOLOGICAL_QC','source_FNA':ref(fna),'source_contigs':len(lengths),'source_nucleotide_bases':sum(lengths.values()),'protein_count':expected,'CDS_count':len(gff),'FFN_count':len(nucleotides),'partial_flag_counts':dict(partials),'terminal_stops_removed':terminal,'bounds_strand_header_ID_map_bijections_verified':True,'AA_DNA_translation_recomputed':False,'biological_quality_PASS':False})
 table=create(write_folder/'cds_join_integrity.tsv',text.getvalue().encode());return {'validation':integrity,'joined_coordinates':table}
def legacy(row,m):
 candidate=row['legacy_uniform_annotation']
 if candidate is None:return None
 cp=bound(candidate['commit']);old=read(cp);fp=old['fingerprint'];e=read(bound(candidate['execution']));cmd=e['command']
 if old.get('status')!='PASS_PILOT_GENE_CALLING'or old['accession']!=row['accession']or fp['source_receipt_sha256']!=row['acquisition_receipt']['sha256']or fp['script_sha256']!=m['canonicalizer']['sha256']or fp['prodigal_sha256']!=m['prodigal']['sha256']or fp['gene_calling_mode']!='single'or fp['translation_table']!=11:raise RuntimeError('Legacy method/source fingerprint mismatch')
 if e.get('exit_code')!=0 or e.get('owned_group_empty')is not True or e.get('error')or cmd[cmd.index('-p')+1]!='single'or cmd[cmd.index('-g')+1]!='11'or'-q'not in cmd:raise RuntimeError('Legacy execution not valid')
 for f in old['files']:bound({'path':(cp.parent/f['path']).relative_to(R).as_posix(),**{k:v for k,v in f.items()if k!='path'}})
 input_fna=next(z for z in old['files']if z['path']=='input.fna');h=hashlib.sha256()
 with bound(row['FNA']).open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 h.update(b'\n')
 if input_fna['sha256']not in(row['FNA']['sha256'],h.hexdigest()):raise RuntimeError('Legacy input is not exact bound FNA or explicitly appended one newline')
 return cp.parent,old['protein_count'],{'legacy_annotation_commit':candidate['commit'],'execution':candidate['execution'],'source_FNA_relation':'Exact bound source bytes, with legacy caller adding exactly one newline if differing','legacy_input_fna':input_fna}
def exec_prodigal(a):
 tool=bound({'path':a.prodigal,'sha256':a.prodigal_sha});source=bound({'path':a.fna,'sha256':a.fna_sha});out=inside(a.target);out.parent.relative_to(R)
 os.execv(str(tool),[str(tool),'-i',str(source),'-a',str(out),'-d',str(out.with_suffix('.ffn')),'-f','gff','-o',str(out.with_suffix('.gff')),'-p','single','-g','11','-q'])
def run(a):
 if os.name!='posix':raise RuntimeError('Actual Prodigal queue requires Linux')
 import fcntl,pilot10
 def interrupted(signum,frame):raise InterruptedError('Annotation queue received signal '+str(signum))
 signal.signal(signal.SIGTERM,interrupted)
 mp=inside(a.manifest);m=read(mp);admission=read(inside(a.admission));out=inside(a.output);out.mkdir(parents=True,exist_ok=True)
 for key,p in(('script',Path(__file__).resolve()),('guard',Path(guard.__file__).resolve()),('canonicalizer',Path(pilot10.__file__).resolve())):
  if sha(p)!=m[key]['sha256']:raise RuntimeError('Pinned queue source changed '+key)
 tool=bound(m['prodigal']);bound(m['canonical_queue'])
 if m['count']!=919 or len(m['rows'])!=919 or any(x['source_supported_scope']is not True or x['source_holds_preserved']for x in m['rows']):raise RuntimeError('Unsupported annotation scope')
 if admission.get('status')!='ROOT_ADMITTED_PROVISIONAL_UNIFORM_ANNOTATION'or admission.get('input_manifest_sha256')!=sha(mp)or admission.get('script_sha256')!=sha(__file__)or admission.get('prior_marker_pipeline_closed_verified')is not True:raise RuntimeError('Fresh exact Root admission and marker closure required')
 if not 0<admission.get('max_rss_bytes',0)<=256*1024**2 or admission.get('linux_available_stop_bytes',0)<int(1.25*1024**3)or not 0<admission.get('unit_timeout_seconds',0)<=180:raise RuntimeError('Annotation resource bounds invalid')
 cpu=admission.get('cpu')
 if cpu!=2 or cpu not in os.sched_getaffinity(0):raise RuntimeError('One dedicated CPU2 required')
 os.sched_setaffinity(0,{cpu});lock=(out/'queue.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 guard.save(out/'owner.json',{'identity':guard.proc(os.getpid()),'manifest':ref(mp),'admission':ref(inside(a.admission)),'started_utc':utc()})
 guard.TOOLCHAIN_SHA=hashlib.sha256(json.dumps({'tool':m['prodigal'],'canonicalizer':m['canonicalizer'],'method':m['method']},sort_keys=True).encode()).hexdigest()
 prior_stop=guard.stop_requested;guard.stop_requested=lambda:prior_stop()or(R/'state/STOP_UNIFORM_ANNOTATION').exists()
 started=utc();clock=time.monotonic();last=0;done=0;new=0;reused=0;current=None;rows=[];owner=guard.proc(os.getpid())
 def publish(operation,peak=None,mem=None,terminal=None):
  nonlocal last
  if terminal is None and time.monotonic()-last<30:return
  state={'id':'05','name':'Uniform gene/protein annotation','status':terminal or'RUNNING','operation':'ACTUAL_UNIFORM_PRODIGAL_PROCESSING','detail':str(current)+' / '+operation,'done':done,'total':919,'unit':'source-supported genomes with paired coordinate annotations','started_utc':started,'updated_utc':utc(),'pid':a.native_pid,'creation_time_utc':a.native_creation_utc,'linux_owner_identity':owner,'cpu_affinity':[cpu],'summed_owned_rss_bytes':peak,'linux_available_bytes':mem,'newly_annotated':new,'reused_verified':reused,'scope':SCOPE,'quality_PASS_claimed':False,'final_panel_acceptance':False,'log_path':str(out/'progress.json')}
  guard.save(out/'progress.json',state);guard.save(R/'state/stages/05.json',state);last=time.monotonic()
 publish('start919-genome automatic queue',terminal='RUNNING')
 try:
  for row in m['rows']:
   current=row['accession'];dest=out/'rows'/current;dest.mkdir(parents=True,exist_ok=True);commit=dest/'commit.json';source=bound(row['FNA']);bound(row['acquisition_receipt'])
   fingerprint={'source_FNA':row['FNA'],'acquisition_receipt':row['acquisition_receipt'],'prodigal_sha256':m['prodigal']['sha256'],'canonicalizer_sha256':m['canonicalizer']['sha256'],'script_sha256':sha(__file__),'gene_calling_mode':'single','translation_table':11}
   if commit.exists():
    c=read(commit)
    if c['fingerprint']!=fingerprint or c['status']!='COMMITTED_PROVISIONAL_PAIRED_COORDINATE_ANNOTATION':raise RuntimeError('Existing row fingerprint/status changed '+current)
    if set(c['artifacts'])!=set(('prodigal.faa','prodigal.ffn','prodigal.gff','proteins.faa','protein_coordinate_map.json','protein_coordinate_map.tsv'))or set(c['coordinate_integrity'])!=set(('validation','joined_coordinates'))or not c['protein_count']==c['CDS_count']>0:raise RuntimeError('Incomplete committed artifact/count set')
    for v in c['artifacts'].values():bound(v)
    for v in c['coordinate_integrity'].values():bound(v)
    e=read(bound(c['scientific_execution']))
    if e.get('actual_exit_code',e.get('exit_code'))!=0 or e.get('owned_group_empty')is not True:raise RuntimeError('Committed row lacks actual0/closed execution')
    reused+=1
   else:
    if guard.stop_requested():raise InterruptedError('Stop requested before next genome')
    if guard.available()<admission['linux_available_stop_bytes']:raise MemoryError('Insufficient shared Linux headroom')
    old=legacy(row,m)
    if old:
     folder,count,provenance=old;execution=row['legacy_uniform_annotation']['execution'];action='VERIFIED_EXISTING_PILOT10_UNIFORM_PAIR';reused+=1
    else:
     args=[sys.executable,'-B',str(Path(__file__).resolve()),'--exec-prodigal','--prodigal',str(tool),'--prodigal-sha',m['prodigal']['sha256'],'--fna',str(source),'--fna-sha',row['FNA']['sha256'],'--target','{OUTPUT}']
     unit=guard.run_unit(out/'units'/current,'prodigal',args,[row['FNA'],row['acquisition_receipt'],m['script'],m['canonicalizer'],m['prodigal']],'prodigal.faa',admission,publish)
     folder=bound(unit['output']).parent;count=pilot10.canonicalize(folder,current);execution=unit['execution'];provenance={'unit_commit':ref(out/'units'/current/'prodigal_committed.json'),'uniform_method':m['method']};action='NEW_UNIFORM_ANNOTATION';new+=1
    integrity=coordinates(folder,current,source,count,dest)
    artifacts={name:ref(folder/name)for name in('prodigal.faa','prodigal.ffn','prodigal.gff','proteins.faa','protein_coordinate_map.json','protein_coordinate_map.tsv')}
    c={'schema':'TREE2_PROVISIONAL_UNIFORM_ANNOTATION_ROW_V001','status':'COMMITTED_PROVISIONAL_PAIRED_COORDINATE_ANNOTATION','accession':current,'completed_utc':utc(),'fingerprint':fingerprint,'action':action,'protein_count':count,'CDS_count':count,'artifacts':artifacts,'coordinate_integrity':integrity,'scientific_execution':execution,'provenance':provenance,'source_metadata':metadata_row(row),'scope':SCOPE,'biological_QC_PASS':False,'independent_taxonomy':'UNRESOLVED_NOT_ACCEPTED','final_panel_acceptance':False,'defence_status':'UNKNOWN_UNSEARCHED'}
    jcreate(commit,c)
   rows.append({'accession':current,'commit':ref(commit),'protein_count':c['protein_count'],'action':c['action']});done+=1
   guard.save(out/'checkpoint.json',{'completed':done,'total':919,'newly_annotated':new,'reused_verified':reused,'current_committed':ref(commit),'updated_utc':utc(),'scope':SCOPE});publish('genome coordinate commit')
  guard.save(out/'result.json',{'status':'PROVISIONAL_UNIFORM_ANNOTATION_QUEUE_COMPLETE_PENDING_EXTERNAL_CLOSURE','scope':SCOPE,'input_manifest':ref(mp),'admission':ref(inside(a.admission)),'rows':rows,'completed':done,'total':919,'newly_annotated':new,'reused_verified':reused,'protein_count':sum(x['protein_count']for x in rows),'elapsed_seconds':time.monotonic()-clock,'final_panel_acceptance':False,'biological_QC_PASS':False});publish('all919paired annotations committed',terminal='COMPUTED_PENDING_EXTERNAL_CLOSURE')
 except BaseException as ex:
  guard.save(out/'failure.json',{'status':'ANNOTATION_QUEUE_STOPPED_PRESERVE_COMMITTED_ROWS','error':repr(ex),'current':current,'completed':done,'unfinished':'UNKNOWN_NOT_ACCEPTED','updated_utc':utc()});publish(repr(ex),terminal='STOPPED');raise
def cli():
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--queue',default='metadata/tree2_qc_campaign_queue_v001.json');p.add_argument('--prepare-output',default='metadata/uniform_annotation_queue_v001');p.add_argument('--manifest',default='metadata/uniform_annotation_queue_v001/input_manifest.json');p.add_argument('--admission');p.add_argument('--output',default='analysis/uniform_annotation_v001');p.add_argument('--native-pid',type=int);p.add_argument('--native-creation-utc');p.add_argument('--exec-prodigal',action='store_true');p.add_argument('--prodigal');p.add_argument('--prodigal-sha');p.add_argument('--fna');p.add_argument('--fna-sha');p.add_argument('--target');a=p.parse_args()
 if a.exec_prodigal:exec_prodigal(a)
 elif a.prepare:prepare(a)
 else:
  if not a.admission or not a.native_pid or not a.native_creation_utc:p.error('Root admission and native launcher creation identity required')
  run(a)
if __name__=='__main__':cli()
