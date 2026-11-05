"""Tiny project-owned synthetic files only; no real FAA/TSV or scientific import."""
from pathlib import Path
import hashlib,json,shutil,tempfile
import checkm2_phase_separated_artifacts_N1 as a
R=Path(__file__).resolve().parents[1];ACC='GCF_000000001.1'
def denied(call):
    try:call()
    except (ValueError,FileNotFoundError,NotADirectoryError):return
    raise AssertionError('Invalid synthetic artifact was accepted')
def main():
    work=(R/'work').resolve();folder=Path(tempfile.mkdtemp(prefix='N1_artifacts_SYNTHETIC_',dir=work)).resolve()
    if not folder.is_relative_to(work):raise RuntimeError('Synthetic cleanup target escapes project work')
    checks=[]
    base=[ACC+'Ωp1','REF1~K00001','90.0','10','1','0','1','10','2','11','1e-10','50.0']
    other=[ACC+'Ωp2','REF2~NON_DEFAULT_KO','100','3','0','0','1','3','1','3','0','7']
    def emit(name,rows,newline='\n'):
        path=folder/name;path.write_bytes((newline.join('\t'.join(x) for x in rows)+newline).encode('utf-8'));return path
    try:
        p=emit('original.tsv',[base,base,other]);q=emit('reordered.tsv',[other,base,base],newline='\r\n')
        first=a.validate_diamond(p,ACC,{'p1','p2'});reordered=a.validate_diamond(q,ACC,{'p1','p2'})
        assert first['rows']==3 and first['unique_rows']==2 and first['duplicate_rows']==1 and first['query_genomes']==[ACC]
        assert first['sha256']!=reordered['sha256'] and first['multiset_sha256']==reordered['multiset_sha256']
        checks.append('full12_row_order_CRLF_invariance_and_duplicate_preservation')
        changed=base.copy();changed[11]='51.0'
        assert a.validate_diamond(emit('changed_unused_column.tsv',[changed,base,other]),ACC,{'p1','p2'})['multiset_sha256']!=first['multiset_sha256']
        assert a.validate_diamond(emit('removed_duplicate.tsv',[base,other]),ACC,{'p1','p2'})['multiset_sha256']!=first['multiset_sha256']
        checks.append('unused_numeric_field_and_duplicate_count_change_digest')
        assert a.validate_diamond(emit('outside_KO.tsv',[other]),ACC,{'p2'})['rows']==1
        checks.append('outside_default_KO_annotation_retained')
        bad=[]
        bad.append(base[:-1])
        for index,value in [(0,'GCF_000000002.1Ωp1'),(0,ACC+'Ωunknown'),(1,'REF~'),(2,'101'),(3,'0'),(4,'11'),(6,'0'),(6,'11'),(10,'NaN'),(11,'-1')]:
            record=base.copy();record[index]=value;bad.append(record)
        for i,record in enumerate(bad):denied(lambda record=record,i=i:a.validate_diamond(emit('bad'+str(i)+'.tsv',[record]),ACC,{'p1'}))
        empty=folder/'empty.tsv';empty.write_bytes(b'');denied(lambda:a.validate_diamond(empty,ACC,{'p1'}))
        checks.append('eleven_malformed_ABI_numeric_cases_and_empty_output_rejected')
        faa_dir=folder/'faa';faa_dir.mkdir();faa=faa_dir/(ACC+'.faa');faa.write_bytes(b'>p1 synthetic only\nMAA\n');digest=hashlib.sha256(faa.read_bytes()).hexdigest()
        assert a.exact_faa_inventory(faa_dir,ACC,digest)['sha256']==digest
        denied(lambda:a.exact_faa_inventory(faa_dir,ACC,'0'*64))
        extra=faa_dir/'extra.txt';extra.write_bytes(b'only fixture');denied(lambda:a.exact_faa_inventory(faa_dir,ACC,digest));extra.unlink()
        checks.append('exact_versioned_FAA_hash_and_no_extra_inventory')
        dia_dir=folder/'dia';dia_dir.mkdir();tsv=dia_dir/'DIAMOND_RESULTS.tsv';tsv.write_bytes(p.read_bytes());artifact=a.validate_diamond(tsv,ACC,{'p1','p2'})
        assert a.exact_diamond_inventory(dia_dir,artifact)['sha256']==artifact['sha256']
        sub=dia_dir/'extra_directory';sub.mkdir();denied(lambda:a.exact_diamond_inventory(dia_dir,artifact));sub.rmdir()
        denied(lambda:a.exact_diamond_inventory(dia_dir,{**artifact,'bytes':artifact['bytes']+1}))
        checks.append('exact_Diamond_inventory_hash_size_and_subdirectory_rejection')
        # Do not request privilege changes just to exercise a Windows symlink fixture.
        symlink_status='NOT_AVAILABLE_ON_HOST'
        linked=folder/'symlink.tsv'
        try:linked.symlink_to(p)
        except OSError:pass
        else:
            denied(lambda:a.validate_diamond(linked,ACC,{'p1','p2'}));symlink_status='REJECTED';linked.unlink()
        print(json.dumps({'status':'SYNTHETIC_ARTIFACT_FIXTURES_PASS','groups':len(checks),'checks':checks,'symlink_fixture':symlink_status,'real_genome_FAA_TSV_or_scientific_module_used':False,'tools_processes_runtime_or_models_started':False},indent=2))
    finally:
        # This is the exact fresh directory created above, verified inside project work.
        if not folder.resolve().is_relative_to(work) or folder==work:raise RuntimeError('Refused unsafe synthetic cleanup')
        shutil.rmtree(folder)
if __name__=='__main__':main()
