"""Actual exploratory single-copy marker extraction from the saved Tree2 pilot."""
import collections, csv, datetime, hashlib, json, os, pathlib, re, sys

R = pathlib.Path(__file__).resolve().parents[1]
SOURCE = R / 'analysis/pilot10/runs/20261026T161747Z-cluster-resume-f688a380'
OUT = R / 'analysis/marker_discovery/pilot10_recovered_v001'
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def ref(p): return {'path': p.relative_to(R).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    q = p.with_name(p.name + '.tmp')
    with q.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(v, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(q, p)
def fasta(p):
    found = {}; name = None; seq = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('>'):
            if name is not None: found[name] = ''.join(seq).upper()
            name = line[1:].split()[0]
            if name in found: raise ValueError('Duplicate FASTA ID ' + name)
            seq = []
        elif line.strip():
            if name is None: raise ValueError('Sequence without header')
            seq.append(line.strip())
    if name is not None:
        if name in found: raise ValueError('Duplicate last FASTA ID')
        found[name] = ''.join(seq).upper()
    return found

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'result.json').exists():
        old = json.loads((OUT/'result.json').read_text())
        for item in old['artifacts']:
            if sha(R/item['path']) != item['sha256']: raise ValueError('Committed output changed')
        print(json.dumps({'status':'VERIFIED_REUSE', 'summary':old['summary']})); return
    stage = {'id':'06', 'name':'Marker discovery and orthology', 'status':'RUNNING',
             'operation':'EXPLORATORY_SAVED_CLUSTER_SINGLE_COPY_ANALYSIS', 'done':0, 'total':9015,
             'unit':'protein clusters analysed', 'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'detail':'Reusing completed project-local MMseqs clusters; extracting conserved single-copy candidates.',
             'pid':os.getpid(), 'production_marker_acceptance':False,
             'log_path':str(OUT/'result.json')}
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        creation, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        win = ctypes.WinDLL('kernel32', use_last_error=True)
        win.GetCurrentProcess.restype = wintypes.HANDLE
        win.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)]*4
        win.GetProcessTimes.restype = wintypes.BOOL
        if not win.GetProcessTimes(win.GetCurrentProcess(), ctypes.byref(creation), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
            raise ctypes.WinError(ctypes.get_last_error())
        ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        born = datetime.datetime(1601,1,1,tzinfo=datetime.timezone.utc) + datetime.timedelta(microseconds=ticks//10)
        stage['creation_time_utc'] = born.strftime('%Y-%m-%dT%H:%M:%S') + f'.{ticks%10000000:07d}Z'
        stage['windows_creation_filetime_100ns'] = ticks
    save(R/'state/stages/06.json', stage)
    unit = json.loads((SOURCE/'mmseqs_easy_cluster.exit.json').read_text())
    if unit['exit_code'] != 0 or unit['owned_group_empty'] is not True: raise ValueError('No successful historical clustering')
    seqs = fasta(SOURCE/'all_proteins.faa')
    taxa = sorted({k.split('|')[0] for k in seqs})
    if len(taxa) != 10 or any(not re.fullmatch(r'GC[AF]_\d+\.\d+', x) for x in taxa): raise ValueError('Unexpected pilot genome set')
    groups = collections.defaultdict(list); seen = set()
    for line in (SOURCE/'cluster_cluster.tsv').read_text().splitlines():
        representative, member = line.split('\t')
        if representative not in seqs or member not in seqs or member in seen: raise ValueError('Invalid cluster partition')
        groups[representative].append(member); seen.add(member)
    if seen != set(seqs): raise ValueError('Incomplete protein partition')
    overlay_path = R/'work/marker_discovery_start/saved_pilot10_inputs_with_qc_overlay.json'
    overlay = json.loads(overlay_path.read_text())
    if sorted(g['accession'] for g in overlay['input_genomes']) != taxa: raise ValueError('QC overlay belongs to another panel')
    counts_path = OUT/'copy_number_matrix.tsv'; metrics_path = OUT/'cluster_audit.tsv'
    candidates = []; strict_total = 0; accepted_near = 0; reasons = collections.Counter(); artifacts = []
    (OUT/'candidates').mkdir(exist_ok=True)
    with counts_path.open('w', encoding='utf-8', newline='') as count_file, metrics_path.open('w', encoding='utf-8', newline='') as metric_file:
        cw = csv.writer(count_file, delimiter='\t', lineterminator='\n'); mw = csv.writer(metric_file, delimiter='\t', lineterminator='\n')
        cw.writerow(['representative']+taxa)
        mw.writerow(['representative','proteins','genomes','single_copy_present','min_aa','max_aa','length_ratio','candidate_id','candidate_gate'])
        for i, (representative, members) in enumerate(sorted(groups.items()), 1):
            copies = collections.Counter(x.split('|')[0] for x in members)
            single = max(copies.values()) == 1
            cw.writerow([representative]+[copies.get(x,0) for x in taxa])
            clean = {m:seqs[m].rstrip('*') for m in members}
            lengths = [len(s) for s in clean.values()]; ratio = max(lengths)/min(lengths) if min(lengths) else float('inf')
            if single and len(copies) >= 9: accepted_near += 1
            reason = 'NOT_TEN_GENOME_SINGLE_COPY'; cid = ''
            if single and len(copies) == 10:
                strict_total += 1
                reason = 'EXPLORATORY_CANDIDATE'
                if min(lengths) < 40: reason = 'TOO_SHORT_FOR_THIS_ALIGNMENT_PILOT'
                elif ratio > 1.5: reason = 'LENGTH_OUTLIER_FRAGMENT_FUSION_REVIEW'
                elif any('*' in s or sum(c not in 'ACDEFGHIKLMNPQRSTVWY' for c in s)/len(s) > .05 for s in clean.values()): reason = 'AMBIGUOUS_OR_INTERNAL_STOP_REVIEW'
                if reason == 'EXPLORATORY_CANDIDATE':
                    cid = f'T2P10_{len(candidates)+1:05d}'
                    p = OUT/'candidates'/(cid+'.faa')
                    p.write_text(''.join('>'+m+'\n'+clean[m]+'\n' for m in sorted(members)), encoding='utf-8', newline='\n')
                    candidates.append({'id':cid, 'representative':representative, 'fasta_path':p.relative_to(R).as_posix(),
                                       'sha256':sha(p), 'members':sorted(members), 'occupancy':10, 'single_copy':True,
                                       'length_min':min(lengths), 'length_max':max(lengths),
                                       'terminal_stop_characters_removed':sum(len(seqs[m])-len(clean[m]) for m in members),
                                       'orthology_accepted':False})
                    artifacts.append(ref(p))
            reasons[reason] += 1
            mw.writerow([representative,len(members),len(copies),single,min(lengths),max(lengths),f'{ratio:.6f}',cid,reason])
    manifest_path = OUT/'candidate_manifest.json'
    manifest = {'schema':'TREE2_EXPLORATORY_MARKER_CANDIDATES_V001', 'scope':'TEN_GENOME_DISCOVERY_NOT_PRODUCTION_MARKER_SET',
                'taxa':taxa, 'candidates':candidates, 'input_genomes':overlay['input_genomes'],
                'source_inputs':[ref(SOURCE/'all_proteins.faa'),ref(SOURCE/'cluster_cluster.tsv'),ref(SOURCE/'mmseqs_easy_cluster.exit.json'),ref(overlay_path)],
                'source_held_genomes_included_only_exploratorily':True, 'qc_thresholds_unchanged':True,
                'full_panel_marker_acceptance':False, 'old_tree1_or_old105_used':False}
    save(manifest_path,manifest); artifacts.extend([ref(counts_path),ref(metrics_path),ref(manifest_path)])
    summary = {'pilot_genomes':10,'families':len({g['family'] for g in overlay['input_genomes']}),
               'proteins':len(seqs),'clusters':len(groups),'single_copy_in_all10':strict_total,
               'single_copy_in_at_least9':accepted_near,'alignment_candidates':len(candidates), 'gate_counts':dict(reasons)}
    result = {'status':'EXPLORATORY_CANDIDATES_EXTRACTED', 'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'summary':summary,'artifacts':artifacts,'source_inputs':manifest['source_inputs'],
              'production_marker_acceptance':False,'scope_limitations':['10genomes only','Four source-held genomes remain exploratory','Similarity clusters are not proven orthogroups','Full-panel occupancy/paralogy/gene-tree tests pending']}
    save(OUT/'result.json', result)
    stage.update(status='PREPARING', operation='MARKER_ALIGNMENT_PILOT', done=len(groups), total=len(groups),
                 detail=f"Extracted {len(candidates)} pilot marker candidates; next alignments/profile validation.",
                 updated_utc=result['at_utc'], computed_candidate_count=len(candidates), marker_set_status='PROVISIONAL_NOT_ACCEPTED',
                 terminal_receipt=ref(OUT/'result.json'))
    save(R/'state/stages/06.json',stage)
    print(json.dumps(summary))

if __name__ == '__main__': main()
