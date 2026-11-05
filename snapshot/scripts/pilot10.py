#!/usr/bin/env python3
"""Prepare/run a bounded exploratory ten-genome annotation/clustering benchmark.

No biological completeness/contamination validation or accepted marker set is
created here. Default is a plan; --run is required for scientific execution.
"""
import argparse
import collections
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
MAX_RSS=2*1024**3
HEADROOM=1024**3
STOPPING=False


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write_json(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp-'+uuid.uuid4().hex[:8])
    with tmp.open('w') as f:
        json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)


def available():
    return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024


def process_stat(pid):
    rest=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return {'pid':int(pid),'group':int(rest[2]),'creation_ticks':int(rest[19]),
            'rss_bytes':int(rest[21])*os.sysconf('SC_PAGE_SIZE')}


def group_snapshot(group):
    rows=[]
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                row=process_stat(p.name)
                if row['group']==group:rows.append(row)
            except (OSError,ValueError,IndexError):pass
    return rows


def stop_gate():
    if STOPPING or (ROOT/'state/STOP').exists() or (ROOT/'state/STOP_PILOT10').exists():
        raise RuntimeError('STOP requested')
    if available()<HEADROOM:raise RuntimeError('Linux available memory below 1GiB headroom')
    if shutil.disk_usage(ROOT).free<20*1024**3:raise RuntimeError('Project volume below 20GiB free')


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS,(MAX_RSS,MAX_RSS))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def execute(command,logbase,deadline,env):
    stop_gate()
    started=time.monotonic()
    peak=0
    receipt={'command':command,'started_utc':utc(),'limit_rss_bytes':MAX_RSS,
             'limit_virtual_address_bytes_per_process':MAX_RSS,'sample_interval_seconds':.1}
    proc=None
    problem=None
    with Path(str(logbase)+'.stdout').open('wb') as out,Path(str(logbase)+'.stderr').open('wb') as err:
        try:
            proc=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True,preexec_fn=child_limits)
            receipt['process_creation_identity']=process_stat(proc.pid)
            while proc.poll() is None:
                stop_gate()
                if time.monotonic()>deadline:raise RuntimeError('600-second pilot deadline exceeded')
                rows=group_snapshot(proc.pid)
                current=sum(x['rss_bytes'] for x in rows)
                peak=max(peak,current)
                if current>MAX_RSS:raise RuntimeError('Owned process group RSS exceeds 2GiB')
                time.sleep(.1)
            if proc.returncode:raise RuntimeError(f'Command exit {proc.returncode}')
        except BaseException as exc:
            problem=repr(exc)
            if proc and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        finally:
            remaining=group_snapshot(proc.pid) if proc else []
            if remaining and proc:
                os.killpg(proc.pid,signal.SIGKILL)
                time.sleep(.1)
                remaining=group_snapshot(proc.pid)
            receipt.update(ended_utc=utc(),elapsed_seconds=time.monotonic()-started,
                           sampled_peak_group_rss_bytes=peak,exit_code=proc.returncode if proc else None,
                           error=problem,owned_group_empty=not remaining)
            write_json(str(logbase)+'.exit.json',receipt)
    if problem:raise RuntimeError(problem)
    if remaining:raise RuntimeError('Owned process group closure unresolved')
    return receipt


def verify_files(folder,receipt):
    for row in receipt['files']:
        p=folder/row['path']
        assert '..' not in Path(row['path']).parts
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],f'Hash mismatch {p}'


def files_manifest(folder):
    return [{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
            for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='annotation_commit.json']


def canonicalize(folder,accession):
    gff={}
    for line in (folder/'prodigal.gff').read_text().splitlines():
        if not line or line.startswith('#'):continue
        row=line.split('\t')
        assert len(row)==9 and row[2]=='CDS'
        attrs=dict(x.split('=',1) for x in row[8].split(';') if '=' in x)
        original=attrs['ID']
        assert original not in gff
        gff[original]={'contig':row[0],'start':int(row[3]),'end':int(row[4]),'strand':row[6],
                       'prodigal_gene_id':original,'gff_attributes':attrs}
    records=[]
    head=None;seq=[]
    for line in (folder/'prodigal.faa').read_text().splitlines():
        if line.startswith('>'):
            if head is not None:records.append((head,''.join(seq)))
            head=line[1:];seq=[]
        elif line.strip():seq.append(line.strip())
    if head is not None:records.append((head,''.join(seq)))
    mapping=[]
    seen=set()
    with (folder/'proteins.faa').open('w') as out:
        for number,(header,seq) in enumerate(records,1):
            fields=header.split(' # ')
            assert len(fields)==5
            attrs=dict(x.split('=',1) for x in fields[4].split(';') if '=' in x)
            original=attrs['ID'];coord=gff[original]
            assert original not in seen;seen.add(original)
            assert int(fields[1])==coord['start'] and int(fields[2])==coord['end']
            assert ('+' if int(fields[3])==1 else '-')==coord['strand']
            terminal=seq.endswith('*')
            if terminal:seq=seq[:-1]
            assert seq and '*' not in seq and set(seq)<=set('ABCDEFGHIKLMNPQRSTVWXYZ')
            ident=f'{accession}|gene{number:06d}'
            out.write('>'+ident+'\n'+seq+'\n')
            mapping.append({'protein_id':ident,'accession':accession,**coord,
                            'original_prodigal_header':header,'terminal_stop_removed':terminal,'aa_length':len(seq)})
    assert len(gff)==len(mapping)>0
    write_json(folder/'protein_coordinate_map.json',mapping)
    with (folder/'protein_coordinate_map.tsv').open('w') as f:
        f.write('protein_id\taccession\tcontig\tstart_1based\tend_1based\tstrand\tprodigal_gene_id\taa_length\n')
        for r in mapping:f.write('\t'.join(str(r[k]) for k in ('protein_id','accession','contig','start','end','strand','prodigal_gene_id','aa_length'))+'\n')
    return len(mapping)


def annotate(record,run_id,runfolder,deadline,env,tool):
    accession=record['accession']
    raw=ROOT/'raw'/accession
    source_receipt=raw/'acquisition_receipt.json'
    source=json.loads(source_receipt.read_text())
    assert source['accession']==accession and source['acquisition_status']=='PASS'
    verify_files(raw,source)
    fingerprint={'source_receipt_sha256':sha(source_receipt),'script_sha256':sha(__file__),
                 'prodigal_sha256':sha(tool),'gene_calling_mode':'single','translation_table':11}
    parent=ROOT/'analysis/pilot10/annotations';parent.mkdir(parents=True,exist_ok=True)
    final=parent/accession
    existing=final/'annotation_commit.json'
    if existing.exists():
        old=json.loads(existing.read_text())
        if old.get('fingerprint')==fingerprint:
            verify_files(final,old)
            return final,old['protein_count'],'VERIFIED_SKIP'
    stage=parent/('.staging-'+accession+'-'+run_id);stage.mkdir()
    fna=[raw/x['path'] for x in source['files'] if x['path'].endswith('.fna')]
    assert fna
    with (stage/'input.fna').open('wb') as out:
        for p in fna:
            with p.open('rb') as src:shutil.copyfileobj(src,out)
            out.write(b'\n')
    command=[str(tool),'-i',str(stage/'input.fna'),'-a',str(stage/'prodigal.faa'),
             '-d',str(stage/'prodigal.ffn'),'-f','gff','-o',str(stage/'prodigal.gff'),
             '-p','single','-g','11','-q']
    execute(command,runfolder/('prodigal_'+accession),deadline,env)
    count=canonicalize(stage,accession)
    commit={'status':'PASS_PILOT_GENE_CALLING','accession':accession,'completed_utc':utc(),
            'fingerprint':fingerprint,'protein_count':count,'files':files_manifest(stage),
            'biological_qc_status':'NOT_RUN','defence_status':'NOT_RUN'}
    write_json(stage/'annotation_commit.json',commit)
    verify_files(stage,commit)
    if final.exists():
        quarantine=ROOT/'work/pilot10_quarantine';quarantine.mkdir(parents=True,exist_ok=True)
        os.replace(final,quarantine/(accession+'-'+run_id))
    os.replace(stage,final)
    return final,count,'ANNOTATED'


def summarize_clusters(tsv,out,panel):
    clusters=collections.defaultdict(list)
    members=set()
    for line in tsv.read_text().splitlines():
        rep,member=line.split('\t')
        assert member not in members
        members.add(member);clusters[rep].append(member)
    rows=[]
    selected={x['accession'] for x in panel}
    for rep,values in clusters.items():
        counts=collections.Counter(v.split('|',1)[0] for v in values)
        assert set(counts)<=selected
        single_copy=all(n==1 for n in counts.values())
        rows.append({'representative':rep,'member_count':len(values),'genome_occupancy':len(counts),
                     'single_copy_among_present':single_copy,
                     'exploratory_candidate_only':single_copy and len(counts)>=9})
    write_json(out/'exploratory_cluster_summary.json',rows)
    summary={'clusters':len(rows),'proteins':len(members),
             'single_copy_occupancy_9of10_or_more':sum(x['exploratory_candidate_only'] for x in rows),
             'single_copy_occupancy_10of10':sum(x['single_copy_among_present'] and x['genome_occupancy']==10 for x in rows),
             'interpretation':'Exploratory ten-genome benchmark only; not an accepted broad-LAB marker set and not genome completeness/contamination QC.',
             'defence_status':'NOT_RUN'}
    write_json(out/'benchmark_summary.json',summary)
    return summary


def main():
    global STOPPING
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--panel',default=str(ROOT/'metadata/pilot_panel.json'))
    args=p.parse_args()
    assert socket.gethostname().casefold()=='wd','WD-only execution'
    panel=json.loads(Path(args.panel).read_text())[:10]
    assert len(panel)==10 and len({x['accession'] for x in panel})==10
    tools={x:ROOT/'tools/bioenv/bin'/x for x in ('prodigal','mmseqs')}
    assert all(x.exists() for x in tools.values())
    plan={'mode':'RUN' if args.run else 'PREPARED_ONLY','accessions':[x['accession'] for x in panel],
          'prodigal':'2.6.3 single mode / genetic code11','mmseqs':{'min_seq_id':.3,'coverage':.8,'cov_mode':0,'cluster_mode':2,'threads':2,'split_memory_limit':'1G'},
          'wall_timeout_seconds':600,'process_group_rss_limit_bytes':MAX_RSS,
          'minimum_linux_memory_headroom_bytes':HEADROOM,'new_panel_only':True,
          'accepted_marker_set_status':'NOT_RUN','biological_quality_qc_status':'NOT_RUN','defence_status':'NOT_RUN'}
    if not args.run:
        print(json.dumps(plan,indent=2));return 0
    assert available()>=MAX_RSS+HEADROOM,'Need >=3GiB Linux available memory for 2GiB budget plus1GiB headroom'
    stop_gate()
    run_id=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]
    runfolder=ROOT/'analysis/pilot10/runs'/run_id;runfolder.mkdir(parents=True)
    env=dict(os.environ)
    for name in ('TMPDIR','TMP','TEMP'):env[name]=str(ROOT/'work/pilot10_tmp'/run_id)
    env['XDG_CACHE_HOME']=str(ROOT/'work/pilot10_cache')
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='2'
    Path(env['TMPDIR']).mkdir(parents=True);Path(env['XDG_CACHE_HOME']).mkdir(parents=True,exist_ok=True)
    env['PATH']=str(ROOT/'tools/bioenv/bin')+':'+env.get('PATH','')
    lock=(ROOT/'state/pilot10.lock').open('a+')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    write_json(ROOT/'state/pilot10_owner.json',{'run_id':run_id,'started_utc':utc(),**process_stat(os.getpid())})
    for sig in (signal.SIGTERM,signal.SIGINT):
        signal.signal(sig,lambda *_:globals().__setitem__('STOPPING',True))
    started=time.monotonic();deadline=started+600
    status='FAILED';error=None;annotations=[];summary=None
    try:
        write_json(runfolder/'plan.json',plan)
        combined=runfolder/'all_proteins.faa'
        with combined.open('wb') as out:
            for record in panel:
                stop_gate()
                folder,count,action=annotate(record,run_id,runfolder,deadline,env,tools['prodigal'])
                with (folder/'proteins.faa').open('rb') as src:shutil.copyfileobj(src,out)
                annotations.append({'accession':record['accession'],'proteins':count,'action':action})
                write_json(runfolder/'annotation_progress.json',annotations)
        result=runfolder/'cluster'
        command=[str(tools['mmseqs']),'easy-cluster',str(combined),str(result),str(runfolder/'mmseqs_tmp'),
                 '--min-seq-id','0.3','-c','0.8','--cov-mode','0','--cluster-mode','2','--threads','2','--split-memory-limit','1G']
        execute(command,runfolder/'mmseqs_easy_cluster',deadline,env)
        summary=summarize_clusters(runfolder/'cluster_cluster.tsv',runfolder,panel)
        assert summary['proteins']==sum(x['proteins'] for x in annotations)
        status='PASS_EXPLORATORY_PILOT_ONLY'
    except BaseException as exc:error=repr(exc)
    finally:
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()
        receipt={'run_id':run_id,'status':status,'error':error,'ended_utc':utc(),
                 'elapsed_seconds':time.monotonic()-started,'annotations':annotations,'summary':summary,
                 'panel_sha256':sha(args.panel),'script_sha256':sha(__file__),
                 'process_creation_identity':process_stat(os.getpid()),'lock_released':True,
                 'outputs_preserved':str(runfolder),'genome_quality_status':'NOT_RUN','defence_status':'NOT_RUN'}
        write_json(runfolder/'pilot_exit_receipt.json',receipt)
        write_json(ROOT/'state/pilot10_last_exit.json',receipt)
        print(json.dumps(receipt,indent=2),flush=True)
    return 0 if status=='PASS_EXPLORATORY_PILOT_ONLY' else 2


if __name__=='__main__':raise SystemExit(main())
