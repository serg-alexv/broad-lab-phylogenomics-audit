"""Future P20 original annotation entry. No annotation/import runs on module import."""
import argparse,os,shutil,sys
from pathlib import Path
import checkm2_P20_continue19_common_v001 as c
import checkm2_protein_helpers_v001 as h

def main(args):
 request=c.read(c.path(args.request))
 if c.sha(c.path(args.request))!=args.request_sha256 or request.get('request_schema')!='TREE2_PHASE_SEPARATED_P20_ANNOTATION_REQUEST_V001':raise RuntimeError('P20 annotation request hash/schema differs')
 plan,recipe,admission=c.request_gate(request);h.runtime_required()
 if Path(sys.executable).resolve()!=(c.path(request['runtime_prefix'])/'bin/python').resolve():raise RuntimeError('Annotation outside accepted prefix')
 prefix=c.path(request['runtime_prefix']);program=prefix/'bin/prodigal'
 if Path(shutil.which('prodigal') or '').resolve()!=program.resolve() or os.environ.get('PATH','').split(os.pathsep)[0]!=str(prefix/'bin'):raise RuntimeError('Original caller PATH resolution differs')
 staged=c.bind(request['staged_fna']);item=recipe['input']
 if staged.name!=item['accession']+'.fna' or c.sha(staged)!=item['fasta_sha256']:raise RuntimeError('P20 exact fresh staged input differs')
 runtime_plan={'input':{**item,'staged_fna':str(staged)},'runtime_prefix':request['runtime_prefix'],'original_prodigal_source_sha256':recipe['caller_source_sha256'],'prodigal_program_sha256':recipe['prodigal_program_sha256']}
 target=c.path(args.output);body=target.parent/'annotation_original_plan.json';c.save(body,runtime_plan)
 h.annotate(body,target)
 c.save(target/'entry_routing.json',{'runtime_prefix':str(prefix),'actual_Python':str(Path(sys.executable).resolve()),'actual_PATH':os.environ['PATH'],'actual_prodigal_resolution':str(program.resolve()),'prodigal_program_sha256':c.sha(program),'request_sha256':args.request_sha256,'no_author_patch':True})
 if c.sha(c.path(args.request))!=args.request_sha256:raise RuntimeError('Annotation request changed')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',required=True);main(p.parse_args())
