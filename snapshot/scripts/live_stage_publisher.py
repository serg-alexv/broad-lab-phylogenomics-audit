"""Continuously publish evidence-backed Tree2 stages for the native console."""
from pathlib import Path
import datetime as dt, hashlib, json, os, time
R=Path(__file__).resolve().parents[1]
CACHE={}
ACTIVE={'RUNNING','DOWNLOADING','STARTING','PREPARING','VERIFYING','EXTRACTING','RETRYING'}
ATTENTION={'FAILED','ERROR','RESOURCE_LIMIT','TIMEOUT','BLOCKED_RESOURCE',
           'INTERRUPTED_BUDGET','HELD_PREVIOUS_ATTEMPT'}

def needs_attention(status):
    return status in ATTENTION or status.startswith(('FAILED_','ERROR_'))

def qc_status_for(statuses):
    if any(needs_attention(value) for value in statuses):return 'ATTENTION'
    if any(value in ACTIVE for value in statuses):return 'RUNNING'
    if any(value in {'STOPPED','CANCELLED','CANCELED'} for value in statuses):return 'STOPPED'
    return 'AUTO_SETUP_PENDING'
def read(rel, default=None):
    p=R/rel
    try:
        stamp=p.stat().st_mtime_ns
        if rel not in CACHE or CACHE[rel][0]!=stamp:
            CACHE[rel]=(stamp,json.loads(p.read_text(encoding='utf-8-sig')))
        return CACHE[rel][1]
    except (OSError,ValueError): return default
def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def atomic(p,obj):
    tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2);f.flush();os.fsync(f.fileno())
    for attempt in range(12):
        try: os.replace(tmp,p);return
        except PermissionError:time.sleep(.1)
    raise RuntimeError('Progress journal replacement busy')
NAMES=['Isolation / workstation','Taxonomy and source census','Provisional species-balanced sampling',
       'Genome acquisition / integrity','Independent genome QC / final panel','Uniform gene calls',
       'De novo marker discovery','Alignment and supermatrix QC','Full-panel phylogeny',
       'Independent phylogeny QC','PADLOC + DefenseFinder','Complete-system rings',
       'Representative tree','Conventional figures / local package']
def stage(n,status,detail,done=None,total=None,unit=None,**kw):
    return {'id':f'{n:02d}','name':NAMES[n],'status':status,'detail':detail,
            'done':done,'total':total,'unit':unit,**kw}
def winlog(value):
    value=str(value or '')
    if value.lower().startswith('/mnt/c/'):return 'C:\\'+value[7:].replace('/','\\')
    return value or None
def build():
    brief=read('state/current_brief.json',{}); sel=read('metadata/selection_summary.json',{})
    census=read('qc/census_validation.json',{});seq=read('state/sequence_qc_progress.json',{})
    db=read('state/completeness_db_progress.json',{})
    setup=read('state/tool_setup_progress.json',{})
    pilot=read('state/checkm2_pilot_progress.json',{})
    protein=read('state/checkm2_protein_pilot_v001_progress.json',{})
    strategy=read('state/checkm2_protein_strategy_ready_v001.json',{})
    benchmark=read('state/checkm2_benchmark_progress.json',{})
    seq_status=str(seq.get('status','NOT_STARTED')).upper()
    db_status=str(db.get('status','NOT_STARTED')).upper()
    setup_status=str(setup.get('status','NOT_STARTED')).upper()
    pilot_status=str(pilot.get('status','NOT_STARTED')).upper()
    protein_status=str(protein.get('status','NOT_STARTED')).upper()
    protein_is_posthoc=(protein.get('scope')=='FILE_ONLY_POSTHOC_V002_NO_PREDICTION_RERUN')
    protein_source='checkm2_posthoc_v002' if protein_is_posthoc else 'checkm2_protein_pilot_v001'
    protein_label='saved-output validation' if protein_is_posthoc else 'supported-protein pilot'
    benchmark_status=str(benchmark.get('status','NOT_STARTED')).upper()
    active=ACTIVE
    protein_admitted=(strategy.get('schema')=='TREE2_SUPPORTED_PROTEIN_STRATEGY_V1'
                      and strategy.get('status')=='ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT'
                      and strategy.get('biological_dispatch_authorized') is True)
    historical_pilot=protein_admitted and pilot_status=='BLOCKED_RESOURCE'
    sources=[(protein_source,protein,protein_status,'state/launch_checkm2_posthoc_v002.json' if protein_is_posthoc else 'state/launch_checkm2_protein_pilot_v001.json'),
             ('tool_setup',setup,setup_status,'state/launch_tool_setup.json'),
             ('checkm2_pilot',pilot,pilot_status,'state/launch_checkm2_pilot.json'),
             ('checkm2_benchmark',benchmark,benchmark_status,'state/launch_checkm2_benchmark.json'),
             ('sequence_consistency',seq,seq_status,'state/launch_sequence_qc.json'),
             ('completeness_database',db,db_status,'state/launch_completeness_db.json')]
    historical_sources=[{'source':'checkm2_pilot','status':pilot_status,'detail':pilot.get('detail'),
                         'log_path':winlog(pilot.get('log_path')),'historical':True,
                         'retired_from_current_by':'state/checkm2_protein_strategy_ready_v001.json'}] if historical_pilot else []
    if historical_pilot:sources=[row for row in sources if row[0]!='checkm2_pilot']
    if protein_is_posthoc:
        historical_sources.append({'source':'checkm2_protein_pilot_v001',
                                   'status':'FAILED_RUNTIME_OR_SCHEMA',
                                   'detail':'Original computation preserved; v001 feature checker rejected valid module copy-count means.',
                                   'historical':True,
                                   'retired_from_current_by':'evidence/checkm2_posthoc_v002/admission.json'})
    qc_status=qc_status_for(tuple(status for _,_,status,_ in sources))
    attention_sources=[{'source':name,'status':status,'detail':record.get('detail'),
                        'log_path':winlog(record.get('log_path'))}
                       for name,record,status,_ in sources if needs_attention(status)]
    pilot_label='historical FNA resource pilot' if historical_pilot else 'one-genome FNA pilot'
    details=[f'No user input required. Internal setup: {setup_status}; {protein_label}: {protein_status}; {pilot_label}: {pilot_status}; ten-genome benchmark: {benchmark_status}; DNA consistency: {seq_status}; completeness DB: {db_status}; biological QC not accepted']
    if seq.get('detail'):details.append(str(seq['detail']))
    if db.get('detail'):details.append(str(db['detail']))
    if setup.get('detail'):details.append(str(setup['detail']))
    if (protein_is_posthoc or protein_status in active or needs_attention(protein_status)) and protein.get('detail'):details.append(str(protein['detail']))
    if (pilot_status in active or needs_attention(pilot_status)) and pilot.get('detail'):details.append(('Historical: ' if historical_pilot else '')+str(pilot['detail']))
    if (benchmark_status in active or needs_attention(benchmark_status)) and benchmark.get('detail'):details.append(str(benchmark['detail']))
    owner={};current={}
    if protein_status in active:
        # The posthoc controller publishes its own native Windows identity.
        # Its WSL child and the old protein launch are different processes.
        owner=protein if protein_is_posthoc else read('state/launch_checkm2_protein_pilot_v001.json',{}) or protein;current=protein
    elif benchmark_status in active:
        owner=read('state/launch_checkm2_benchmark.json',{}) or benchmark;current=benchmark
    elif pilot_status in active:
        owner=read('state/launch_checkm2_pilot.json',{}) or pilot;current=pilot
    elif setup_status in active:
        owner=read('state/launch_tool_setup.json',{}) or setup;current=setup
    elif db_status in active:
        owner=read('state/launch_completeness_db.json',{}) or db;current=db
    elif seq_status in active:
        owner=read('state/launch_sequence_qc.json',{});current=seq
    if not current:
        for _,record,status,launch in sources:
            if needs_attention(status) or status in {'STOPPED','CANCELLED','CANCELED'}:
                current=record;owner=record if record.get('pid') else read(launch,{})
                break
    rows=[stage(0,'COMPLETED','WD confirmed;4CPU/3584MB WSL; local-only'),
          stage(1,'COMPLETED','Current paired-deduplicated NCBI accession census',census.get('unique_current_paired_deduplicated_accessions'),census.get('unique_current_paired_deduplicated_accessions'),'accessions'),
          stage(2,'PROVISIONAL',f"Every eligible species first; {sel.get('selected_species','?')} taxa; final QC pending",sel.get('panel_count'),1000,'target genomes'),
          stage(3,'COMPLETED','Acquired collection; integrity verified separately from biology',brief.get('committed_genomes'),brief.get('committed_genomes'),'genomes'),
          stage(4,qc_status,' | '.join(details),current.get('done'),current.get('total'),current.get('unit'),
                pid=owner.get('pid'),creation_time_utc=owner.get('creation_time_utc'),
                log_path=winlog(current.get('log_path') or owner.get('log_path')),
                started_utc=current.get('started_utc'),ended_utc=current.get('ended_utc'),
                attention_sources=attention_sources,
                historical_attention_sources=historical_sources,
                protein_strategy_admitted=protein_admitted,
                substeps={'sequence_consistency':seq,'completeness_database':db,'tool_setup':setup,'checkm2_pilot':pilot,protein_source:protein,'checkm2_benchmark':benchmark},requires_user_input=False),
          stage(5,'WAITING_QC','10-genome exploratory gene-call pilot completed; production gated'),
          stage(6,'WAITING_QC','Pilot:281 universal single-copy candidate clusters; production orthology not accepted'),
          stage(7,'NOT_STARTED','Requires accepted markers and final input panel'),
          stage(8,'NOT_STARTED','Requires validated supermatrix and resource admission'),
          stage(9,'NOT_STARTED','Requires completed full-panel inference'),
          stage(10,'BLOCKED','No verified permitted complete defence-model source under NO GITHUB'),
          stage(11,'NOT_STARTED','Requires validated complete predictions; unknown stays unknown'),
          stage(12,'NOT_STARTED','Separate inference after full-panel stage'),
          stage(13,'NOT_STARTED','Conventional full/representative figures first;3D deferred')]
    # Future controllers register per-stage evidence here; completed stages never
    # become running simply because a file or a stale process ID exists.
    for n in range(14):
        override=read(f'state/stages/{n:02d}.json')
        if override:rows[n]={**rows[n],**override,'id':f'{n:02d}','name':NAMES[n]}
    return {'project':'TREE2_WD_20261026','updated_utc':utc(),'publisher_pid':os.getpid(),
            'sampling_contract':'Every eligible species; balanced strains near1000',
            'continuation':'Automatic continuation check every30minutes; quiet when unchanged',
            'stages':rows,'notice':'Technical integrity and exploratory pilots are not biological acceptance.'}
def main():
    if os.environ.get('COMPUTERNAME','').upper()!='WD':raise RuntimeError('WD-only publisher')
    import msvcrt
    lock=(R/'state/live_publisher.lock').open('a+b');lock.seek(0)
    if lock.read(1)==b'':lock.write(b'0');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    atomic(R/'state/live_publisher_owner.json',{'pid':os.getpid(),'started_utc':utc(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    try:
        while not (R/'state/LIVE_PROGRESS_STOP').exists():
            atomic(R/'state/live_stages.json',build());time.sleep(2)
    finally:
        lock.close();atomic(R/'state/live_publisher_exit.json',{'pid':os.getpid(),'ended_utc':utc(),'status':'STOPPED'})
if __name__=='__main__':main()
