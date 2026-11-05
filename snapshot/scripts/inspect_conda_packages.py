"""Measure package unpacked size; retain every original info file/notice."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import zipfile
import zstandard

ROOT=Path(__file__).resolve().parents[1]
resolved=json.loads((ROOT/'evidence'/'tooling'/'resolved_packages.json').read_text())
results=[]


def consume(tar, row, out):
    total=0
    notices=[]
    for member in tar:
        if not member.isfile():
            continue
        total+=member.size
        if not member.name.startswith('info/'):
            continue
        rel=PurePosixPath(member.name)
        assert not rel.is_absolute() and '..' not in rel.parts
        assert member.size<20*1024**2
        path=out.joinpath(*rel.parts)
        path.parent.mkdir(parents=True,exist_ok=True)
        data=tar.extractfile(member).read()
        path.write_bytes(data)
        if ('license' in member.name.lower() or 'copyright' in member.name.lower() or 'notice' in member.name.lower()):
            notices.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    return total,notices


for row in resolved:
    suffix=row['url'].split('/conda_channels/',1)[1]
    path=ROOT/'work'/'conda_channels'/suffix
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    dist=row['fn'].removesuffix('.tar.bz2').removesuffix('.conda')
    out=ROOT/'tools'/'package_notices'/dist
    total=0
    notices=[]
    if path.name.endswith('.tar.bz2'):
        with tarfile.open(path,'r:bz2') as tar:
            size,files=consume(tar,row,out);total+=size;notices.extend(files)
    else:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith('.tar.zst'):
                    continue
                with z.open(name) as compressed, zstandard.ZstdDecompressor().stream_reader(compressed) as stream, tarfile.open(fileobj=stream,mode='r|') as tar:
                    size,files=consume(tar,row,out);total+=size;notices.extend(files)
    results.append({'name':row['name'],'version':row['version'],'build':row['build'],
                    'compressed_bytes':row['size'],'unpacked_bytes':total,'license_identifier':row.get('license'),
                    'source_url':'https://conda.anaconda.org/'+suffix,'sha256':row['sha256'],
                    'notice_files':notices,'original_package_info_preserved':str(out.relative_to(ROOT))})
    print(json.dumps(results[-1]),flush=True)
compressed=sum(x['compressed_bytes'] for x in results)
unpacked=sum(x['unpacked_bytes'] for x in results)
summary={'packages':results,'total_compressed_bytes':compressed,'total_unpacked_bytes':unpacked,
         'conservative_total_footprint_bytes':2*compressed+2*unpacked,
         'admitted_under_2GiB':2*compressed+2*unpacked<2*1024**3,
         'source_restriction':'Only official conda-forge/bioconda channel package downloads; redirects disabled.'}
(ROOT/'evidence'/'tooling'/'package_size_and_notices.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='packages'}),flush=True)
assert summary['admitted_under_2GiB'], 'Package footprint exceeds <2GiB gate'
