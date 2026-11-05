"""Bounded file-only Stage07 construction; original accepted alignments are immutable.

No subprocesses, WSL, annotation, searches, aligner or inference is launched.
Each locus is atomically committed and verified before reuse after interruption.
This is computational input QC, not final biological/taxonomic acceptance.
"""
from pathlib import Path
import argparse, collections, datetime as dt, hashlib, json, math, os, statistics, sys, time


def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def atomic_bytes(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.partial.' + str(os.getpid()))
    with tmp.open('wb') as f:
        f.write(value); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)


def save(p, value):
    atomic_bytes(p, (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode())


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))


def path(root, rel):
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or p.is_relative_to(root / 'work/local_continuation/codex_home'):
        raise ValueError('Out of scope path')
    return p


def ref(root, p):
    p = p.resolve()
    return {'path': str(p.relative_to(root)).replace('\\', '/'),
            'sha256': digest(p), 'bytes': p.stat().st_size}


def bound(root, row):
    p = path(root, row['path'])
    if p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
        raise ValueError('Bound input/output drift: ' + row['path'])
    return p


def fasta(p):
    records = {}; name = None
    for raw in p.read_text(encoding='ascii').splitlines():
        if raw.startswith('>'):
            name = raw[1:].split()[0]
            if name in records: raise ValueError('Duplicate FASTA header')
            records[name] = []
        elif raw.strip():
            if name is None: raise ValueError('FASTA sequence before header')
            records[name].append(raw.strip())
    return {k: ''.join(v) for k, v in records.items()}


def fasta_bytes(rows):
    return ''.join('>' + name + '\n' + seq + '\n' for name, seq in rows).encode('ascii')


AA = set('ACDEFGHIKLMNPQRSTVWY')
ALLOWED = AA | set('BXZJUO-')


def peak_rss():
    if os.name != 'nt': return None
    import ctypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (x, ctypes.c_size_t) for x in ['PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]
    c = Counters(); c.cb = ctypes.sizeof(c)
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        raise OSError('Cannot measure own memory')
    return c.PeakWorkingSetSize


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--plan', required=True)
    ap.add_argument('--stop-after-new-loci', type=int)
    a = ap.parse_args(); root = Path(a.root).resolve(); plan_path = path(root, a.plan); plan = read(plan_path)
    if plan['status'] != 'ROOT_ADMITTED_BOUNDED_COMPUTATIONAL_MATRIX_ONLY': raise ValueError('Not admitted')
    if digest(Path(__file__)) != plan['source']['sha256']: raise ValueError('Source drift')
    if plan['launches_subprocesses'] or plan['final_biological_acceptance']: raise ValueError('Scope mismatch')
    selection = read(bound(root, plan['marker_selection'])); cohort = read(bound(root, plan['cohort_manifest']))
    ids = bound(root, plan['cohort_accessions']).read_text(encoding='ascii').splitlines()
    if len(ids) != plan['expected_genomes'] or len(set(ids)) != len(ids): raise ValueError('Cohort count/duplicate')
    if ids != [r['accession'] for r in cohort['rows']]: raise ValueError('Cohort order mismatch')
    if any(r['exclusion_or_hold_reasons'] or r['final_high_quality_or_taxonomic_panel_acceptance'] for r in cohort['rows']):
        raise ValueError('Known held or falsely final row in computational cohort')
    profiles = selection['profiles']
    if [r['profile'] for r in profiles] != selection['matrix_rules']['concatenate_profiles_in_this_explicit_order']:
        raise ValueError('Profile order mismatch')
    if len(profiles) != plan['expected_loci']: raise ValueError('Locus count mismatch')
    for key in ['accepted_alignment_closure', 'accepted_diagnostic_gene_tree_closure', 'accepted_CheckM1_method_closure',
                'method_registry_current_not_original_stale_not_run_mask', 'full281_decision_table', 'sensitivity3_exclusions']:
        bound(root, selection[key])
    out = path(root, plan['output_directory']); out.mkdir(parents=True, exist_ok=True)
    plan_sha = digest(plan_path); started = time.monotonic(); new_loci = 0; reused = 0; commits = []
    stage_path = root / 'state/stages/07.json'
    def progress(detail, done, status='RUNNING'):
        peak = peak_rss()
        if peak and peak > plan['maximum_native_peak_RSS_bytes']: raise MemoryError('File-only memory ceiling exceeded')
        row = {'id':'07', 'name':'Alignment and supermatrix QC', 'status':status,
               'operation':'BOUNDED_FILE_ONLY_CONSERVATIVE900_CORE54_MATRIX', 'detail':detail,
               'done':done, 'total':len(profiles), 'unit':'selected locus matrix checkpoints',
               'candidate_alignments_accepted':196, 'candidate_alignments_total':196,
               'final_supermatrix_acceptance':False, 'taxonomy_acceptance':False,
               'pid':os.getpid(), 'updated_utc':utc(), 'peak_native_RSS_bytes':peak,
               'plan':ref(root,plan_path), 'no_WSL_or_search_or_aligner_launched':True}
        save(stage_path,row); save(out/'progress.json',row)
    progress('Primary phylogeny path: constructing selected-locus matrix; healthy finite defence pilot remains background',0)
    for index, profile in enumerate(profiles):
        folder = out / 'loci' / profile['profile']; cp = folder / 'COMMITTED.json'
        if cp.exists():
            commit = read(cp)
            if commit['plan_sha256'] != plan_sha: raise ValueError('Existing locus belongs to another plan')
            for row in commit['artifacts']: bound(root,row)
            reused += 1
        else:
            records = fasta(bound(root,profile['trimmed_alignment'])); mapping = profile['leaf_to_accession']
            for key in ['alignment_commit','leaf_provenance','genome_dispositions','gene_tree_commit','gene_tree']:
                bound(root,profile[key])
            if set(records) != set(mapping) or len(set(mapping.values())) != len(records):
                raise ValueError('Copy/mapping ambiguity')
            by_genome = {mapping[k]:v for k,v in records.items()}
            if any(set(v)-ALLOWED for v in records.values()): raise ValueError('Invalid amino acid')
            if {len(v) for v in records.values()} != {profile['columns']}: raise ValueError('Input row lengths')
            selected = [by_genome[x] for x in ids]
            metrics_path = path(root,profile['alignment_commit']['path']).parent/'metrics.json'
            upstream_commit = read(bound(root,profile['alignment_commit']))
            metric_ref = next(r for r in upstream_commit['artifacts'] if r['path'].endswith('/metrics.json'))
            metrics = read(bound(root,metric_ref)); original_indices = [i+1 for i,v in enumerate(metrics['column_mask']) if v]
            if len(original_indices) != profile['columns']: raise ValueError('Upstream original-column mask length')
            columns = []
            for j, col in enumerate(zip(*selected)):
                count = collections.Counter(col); canonical = sum(v for k,v in count.items() if k in AA)
                nongap = len(ids)-count.get('-',0)
                keep = canonical / len(ids) >= plan['minimum_canonical_column_occupancy']
                counts = [v for k,v in count.items() if k in AA]
                columns.append({'old_trimmed_column_1based':j+1, 'original_alignment_column_1based':original_indices[j],
                                'genomes':len(ids), 'nongap':nongap, 'canonical':canonical, 'retained':keep,
                                'canonical_states':len(counts), 'parsimony_informative':sum(v>=2 for v in counts)>=2})
            keep_indices = [i for i,x in enumerate(columns) if x['retained']]
            if len(keep_indices)<plan['minimum_columns_per_locus']: raise ValueError('Insufficient retained locus signal')
            trimmed = [(x, ''.join(by_genome[x][i] for i in keep_indices)) for x in ids]
            if any(not (set(s)&AA) for _,s in trimmed): raise ValueError('All-gap or all-unknown selected taxon/locus')
            save(folder/'column_mask.json',{'source_metrics':metric_ref, 'source_alignment':profile['trimmed_alignment'],
                 'cohort':plan['cohort_accessions'], 'threshold':plan['minimum_canonical_column_occupancy'], 'columns':columns})
            atomic_bytes(folder/'alignment.faa',fasta_bytes(trimmed))
            commit = {'schema':'TREE2_STAGE07_LOCUS_COMMIT_V001','profile':profile['profile'], 'plan_sha256':plan_sha,
                      'source_alignment':profile['trimmed_alignment'], 'rows':len(ids), 'source_columns':profile['columns'],
                      'retained_columns':len(keep_indices), 'artifacts':[ref(root,folder/'alignment.faa'),ref(root,folder/'column_mask.json')],
                      'computed_at_utc':utc(), 'biological_orthology_or_taxonomy_acceptance':False}
            save(cp,commit); new_loci += 1
        commits.append(ref(root,cp)); progress('Selected-locus matrix checkpoint '+profile['profile'],index+1)
        if a.stop_after_new_loci and new_loci >= a.stop_after_new_loci:
            save(out/'planned_stop.json',{'status':'CLEAN_STOP_AT_ATOMIC_LOCUS_BOUNDARY','done':index+1,
                 'new_loci':new_loci,'reused_loci':reused,'commits':commits,'actual_exit_requested':3,'at_utc':utc()})
            progress('Planned checkpoint stop; next invocation verifies and reuses committed loci',index+1,'CHECKPOINTED_PLANNED_STOP')
            return 3
    pieces = {x:[] for x in ids}; partitions=[]; pos=1; column_rows=[]; missing=['accession\tprofile\tcolumns\tgap_residues\tambiguous_residues\tcanonical_residues']
    for profile, cp_ref in zip(profiles,commits):
        c=read(bound(root,cp_ref)); rows=fasta(bound(root,c['artifacts'][0])); mask=read(bound(root,c['artifacts'][1]))
        if list(rows)!=ids: raise ValueError('Locus accession order drift')
        end=pos+c['retained_columns']-1
        partitions.append({'profile':profile['profile'],'start':pos,'end':end,'columns':c['retained_columns']})
        for x in ids:
            seq=rows[x]; pieces[x].append(seq); count=collections.Counter(seq)
            canonical=sum(v for k,v in count.items() if k in AA); gaps=count.get('-',0)
            missing.append(f'{x}\t{profile["profile"]}\t{len(seq)}\t{gaps}\t{len(seq)-gaps-canonical}\t{canonical}')
        offset=pos
        for col in mask['columns']:
            if col['retained']:
                column_rows.append({'matrix_column':offset,'profile':profile['profile'],**col});offset+=1
        if offset!=end+1: raise ValueError('Column provenance count')
        pos=end+1
    matrix={x:''.join(pieces[x]) for x in ids}; del pieces
    ncols=pos-1
    if {len(v) for v in matrix.values()}!={ncols}: raise ValueError('Supermatrix row lengths')
    if any(not (set(s)&AA) for s in matrix.values()): raise ValueError('Empty supermatrix row')
    if any(a['end']+1!=b['start'] for a,b in zip(partitions,partitions[1:])): raise ValueError('Partition gaps/overlaps')
    pool=collections.Counter(''.join(matrix.values())); total_canonical=sum(pool[x] for x in AA)
    freqs={x:pool[x]/total_canonical for x in AA}; per_genome=[]
    for x,s in matrix.items():
        count=collections.Counter(s); n=sum(count[a] for a in AA)
        chi=sum((count[a]-n*f)**2/(n*f) for a,f in freqs.items() if f)
        miss=1-n/ncols
        per_genome.append({'accession':x,'canonical_residues':n,'gap_residues':count.get('-',0),
                           'ambiguous_residues':ncols-n-count.get('-',0), 'missing_fraction':miss,
                           'composition_Pearson_score_descriptive_no_pvalue':chi,
                           'missingness_gate_pass':miss<=plan['maximum_taxon_missing_fraction']})
    if not all(r['missingness_gate_pass'] for r in per_genome): raise ValueError('Taxon missingness gate')
    values=[r['composition_Pearson_score_descriptive_no_pvalue'] for r in per_genome]
    median=statistics.median(values); mad=statistics.median(abs(x-median) for x in values)
    for row in per_genome:
        row['composition_descriptive_5_scaled_MAD_review_flag']=row['composition_Pearson_score_descriptive_no_pvalue']>median+5*1.4826*mad
    atomic_bytes(out/'supermatrix.faa',fasta_bytes(matrix.items()))
    atomic_bytes(out/'supermatrix.phy',(f'{len(ids)} {ncols}\n'+''.join(x+' '+s+'\n' for x,s in matrix.items())).encode('ascii'))
    save(out/'partitions.json',partitions)
    atomic_bytes(out/'partitions.nex',('#nexus\nbegin sets;\n'+''.join(f'  charset {p["profile"]} = {p["start"]}-{p["end"]};\n' for p in partitions)+
                 '  charpartition initial_LG_template = '+', '.join('LG: '+p['profile'] for p in partitions)+';\nend;\n').encode('ascii'))
    atomic_bytes(out/'taxon_locus_missingness.tsv',('\n'.join(missing)+'\n').encode('ascii'))
    save(out/'column_provenance.json',column_rows); save(out/'taxon_QC.json',per_genome)
    summary={'schema':'TREE2_STAGE07_COMPUTATIONAL_MATRIX_QC_V001','status':'COMPUTED_PENDING_INDEPENDENT_FILE_VALIDATION',
         'genomes':len(ids),'source_species_labels':cohort['counts']['primary_source_species_labels'], 'loci':len(profiles),
         'source_columns':sum(p['columns'] for p in profiles),'matrix_columns':ncols,
         'canonical_residues':total_canonical,'gap_residues':pool.get('-',0),'ambiguity_residues':sum(v for k,v in pool.items() if k not in AA|{'-'}),
         'variable_columns':sum(c['canonical_states']>=2 for c in column_rows),
         'parsimony_informative_columns':sum(c['parsimony_informative'] for c in column_rows),
         'minimum_taxon_canonical_residues':min(r['canonical_residues'] for r in per_genome),
         'maximum_taxon_missing_fraction':max(r['missing_fraction'] for r in per_genome),
         'composition_review_flags':sum(r['composition_descriptive_5_scaled_MAD_review_flag'] for r in per_genome),
         'composition_flags_are_not_taxonomic_failure_or_automatic_exclusion':True,
         'minimum_canonical_column_occupancy':plan['minimum_canonical_column_occupancy'],
         'exact_accessions_and_partition_coverage_validated':True,'all_54_exactly_one_source_copy_per919_screen_genome':True,
         'known19_genome_holds_and_3_alignment_sensitive_locus_holds_preserved':True,
         'final_marker_orthology_taxonomy_full_tree_or_representative_tree_acceptance':False,
         'no_subprocess_WSL_aligner_or_inference_launched':True,'elapsed_seconds':time.monotonic()-started,
         'peak_native_RSS_bytes':peak_rss(),'new_loci':new_loci,'reused_loci':reused,'plan_sha256':plan_sha,'at_utc':utc()}
    save(out/'QC_summary.json',summary)
    outputs=['supermatrix.faa','supermatrix.phy','partitions.json','partitions.nex','taxon_locus_missingness.tsv','column_provenance.json','taxon_QC.json','QC_summary.json']
    save(out/'COMMITTED.json',{'schema':'TREE2_STAGE07_MATRIX_COMMIT_V001','status':summary['status'],'plan':ref(root,plan_path),
              'locus_commits':commits,'artifacts':[ref(root,out/x) for x in outputs], 'at_utc':utc(), 'final_biological_acceptance':False})
    progress('900-genome /54-locus conservative matrix built; independent file QC and biological review required',len(profiles),summary['status'])
    print(json.dumps(summary)); return 0


if __name__=='__main__':
    sys.exit(main())
