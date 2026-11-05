"""Pure N1 artifact validation; no CheckM2/scientific imports or executable actions."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,os,re,stat
R=Path(__file__).resolve().parents[1]
COLUMNS=('qseqid','sseqid','pident','length','mismatch','gapopen','qstart','qend','sstart','send','evalue','bitscore')

def _project_path(value):
    path=Path(value)
    path=path if path.is_absolute() else R/path
    if not path.absolute().is_relative_to(R):raise ValueError('Artifact path escapes project')
    current=R
    for part in path.absolute().relative_to(R).parts:
        current=current/part
        mode=current.lstat()
        if stat.S_ISLNK(mode.st_mode) or getattr(mode,'st_file_attributes',0)&0x400:
            raise ValueError('Artifact path contains a symlink/reparse point')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(R):raise ValueError('Resolved artifact escapes project')
    return resolved

def _regular(value):
    path=_project_path(value)
    if not stat.S_ISREG(path.lstat().st_mode):raise ValueError('Artifact is not a regular file')
    return path

def _identity(info):
    # This Windows runtime returned different lstat/fstat ctime for unchanged toy bytes.
    # File identity, size, mtime and the complete raw SHA remain independently bound.
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)

def _finish(path,before,after,bytes_read):
    final=path.lstat()
    if not stat.S_ISREG(final.st_mode) or _identity(before)!=_identity(after) or _identity(after)!=_identity(final) or bytes_read!=final.st_size:
        raise ValueError('Artifact changed or became nonregular while read')
    return {'path':path.relative_to(R).as_posix(),'bytes':bytes_read}

def _artifact(value):
    path=_regular(value);initial=path.lstat();digest=hashlib.sha256();size=0
    with path.open('rb') as handle:
        before=os.fstat(handle.fileno())
        if _identity(initial)!=_identity(before):raise ValueError('Artifact changed before opening')
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk);size+=len(chunk)
        after=os.fstat(handle.fileno())
    return {**_finish(path,before,after,size),'sha256':digest.hexdigest()}

def _accession(value):
    if not isinstance(value,str) or not re.fullmatch(r'GC[AF]_[0-9]+\.[0-9]+',value):
        raise ValueError('Exact versioned NCBI accession required')
    return value

def _sha(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('Pinned lowercase SHA256 required')
    return value

def _one(folder,name):
    folder=_project_path(folder)
    if not stat.S_ISDIR(folder.lstat().st_mode):raise ValueError('Inventory root is not a directory')
    entries=list(folder.iterdir())
    if len(entries)!=1 or entries[0].name!=name:raise ValueError('Inventory must contain only the exact named file')
    return _regular(entries[0])

def exact_faa_inventory(folder,accession,expected_sha):
    accession=_accession(accession);expected_sha=_sha(expected_sha)
    path=_one(folder,accession+'.faa');result=_artifact(path)
    if result['sha256']!=expected_sha:raise ValueError('FAA inventory SHA256 differs')
    if _one(folder,accession+'.faa')!=path:raise ValueError('FAA inventory changed')
    return result

def exact_diamond_inventory(folder,expected_file):
    if not isinstance(expected_file,dict) or type(expected_file.get('bytes')) is not int or expected_file['bytes']<=0:
        raise ValueError('Pinned nonempty DIAMOND artifact row required')
    digest=_sha(expected_file.get('sha256'));path=_one(folder,'DIAMOND_RESULTS.tsv')
    if _regular(expected_file['path'])!=path:raise ValueError('Expected DIAMOND artifact is not the exact inventory member')
    result=_artifact(path)
    if result['sha256']!=digest or result['bytes']!=expected_file['bytes']:raise ValueError('DIAMOND inventory bytes/SHA256 differ')
    if _one(folder,'DIAMOND_RESULTS.tsv')!=path:raise ValueError('DIAMOND inventory changed')
    return result

def _integer(text,minimum,label):
    if not re.fullmatch('[0-9]+',text):raise ValueError(label+' is not a plain nonnegative integer')
    value=int(text)
    if value<minimum:raise ValueError(label+' is outside its valid range')
    return value

def _finite(text,minimum,maximum,label):
    if not text or text.strip()!=text:raise ValueError(label+' has an empty/whitespace numeric field')
    try:value=float(text)
    except ValueError as error:raise ValueError(label+' is not numeric') from error
    if not math.isfinite(value) or value<minimum or (maximum is not None and value>maximum):raise ValueError(label+' is nonfinite or outside its valid range')
    return value

def validate_diamond(tsv_path,accession,allowed_primary_ids):
    accession=_accession(accession)
    if isinstance(allowed_primary_ids,(str,bytes)):raise ValueError('FAA primary-ID collection required')
    allowed=set(allowed_primary_ids)
    if not allowed or any(not isinstance(x,str) or not x or 'Ω' in x or any(c.isspace() for c in x) for x in allowed):
        raise ValueError('Exact nonempty unambiguous FAA primary IDs required')
    path=_regular(tsv_path);initial=path.lstat();raw_sha=hashlib.sha256();size=0;rows=0;counts=Counter()
    with path.open('rb') as handle:
        before=os.fstat(handle.fileno())
        if _identity(initial)!=_identity(before):raise ValueError('TSV changed before opening: '+repr((_identity(initial),_identity(before))))
        for raw in handle:
            raw_sha.update(raw);size+=len(raw)
            try:
                line=raw.decode('utf-8')
                if line.endswith('\n'):line=line[:-1]
                if line.endswith('\r'):line=line[:-1]
            except UnicodeDecodeError as error:raise ValueError('DIAMOND TSV is not UTF-8') from error
            fields=line.split('\t')
            if len(fields)!=12:raise ValueError('DIAMOND row must contain all12 fields')
            genome,separator,primary=fields[0].partition('Ω')
            if separator!='Ω' or genome!=accession or primary not in allowed or 'Ω' in primary:
                raise ValueError('DIAMOND query is not the exact own accession/FAA primary ID')
            reference,separator,annotation=fields[1].partition('~')
            if separator!='~' or not reference.strip() or not annotation.strip() or any(c.isspace() for c in fields[1]):
                raise ValueError('DIAMOND target requires nonempty reference~annotation')
            _finite(fields[2],0,100,'pident');length=_integer(fields[3],1,'length')
            mismatch=_integer(fields[4],0,'mismatch');gapopen=_integer(fields[5],0,'gapopen')
            if mismatch>length or gapopen>length:raise ValueError('Mismatch/gap count exceeds alignment length')
            qs,qe,ss,se=(_integer(fields[i],1,COLUMNS[i]) for i in (6,7,8,9))
            if qs>qe or ss>se:raise ValueError('Protein alignment coordinates are reversed')
            _finite(fields[10],0,None,'evalue');_finite(fields[11],0,None,'bitscore')
            counts[tuple(fields)]+=1;rows+=1
        after=os.fstat(handle.fileno())
    if rows==0:raise ValueError('Complete nonempty DIAMOND output required; no unknown-as-negative conversion')
    artifact={**_finish(path,before,after,size),'sha256':raw_sha.hexdigest()}
    digest=hashlib.sha256(b'TREE2_DIAMOND12_FIELD_MULTISET_V1\0')
    for fields,multiplicity in sorted(counts.items()):
        payload=json.dumps(fields,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        digest.update(len(payload).to_bytes(8,'big'));digest.update(payload);digest.update(multiplicity.to_bytes(8,'big'))
    return {**artifact,'rows':rows,'unique_rows':len(counts),'duplicate_rows':rows-len(counts),'multiset_sha256':digest.hexdigest(),'query_genomes':[accession],'columns':list(COLUMNS),'canonicalization':'Row order and newline convention ignored; all12 original field strings and multiplicity preserved; no KO filtering'}
