"""Meaningful synthetic fixtures only; no genome/FAA/model/author-tool execution."""
from pathlib import Path
import ast,copy,datetime,importlib.util,json,os,sys,types,uuid
import checkm2_protein_helpers_v001 as h
import checkm2_protein_pilot_v001 as p
R=h.R;folder=R/'work/checkm2_protein_v001_fixtures'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False);checks=[]
def check(name,fn):fn();checks.append({'check':name,'status':'PASS'})
def reject(name,fn):
 try:fn()
 except (ValueError,RuntimeError):checks.append({'check':name,'status':'PASS_REJECTED'})
 else:raise AssertionError(name)
stop_sha=h.sha(R/'state/STOP_CHECKM2_PILOT');old_progress_sha=h.sha(R/'state/checkm2_pilot_progress.json')
records=h.parse_fasta('>a\ngc\n>b\nAT\n>c\nNNNN\n',h.DNA);stats=h.dna_statistics(records)
assert stats['total_bases']==8 and stats['standard_contig_N50']==4 and stats['GC_fraction_among_ACGT']==.5 and stats['ambiguous_bases']==4
checks.append({'check':'IndependentDNA_N50,GCdenominator,ambiguous counts and rawcase retention','status':'PASS'})
reject('Duplicate identifiers rejected',lambda:h.parse_fasta('>a\nAC\n>a\nGT',h.DNA))
reject('Sequence without header rejected',lambda:h.parse_fasta('ACGT',h.DNA))
protein=h.parse_fasta('>p description\nMKX*\n',h.AA);assert protein[0]['sequence']=='MKX*'
checks.append({'check':'Protein stops/ambiguous characters preserved for AA-length semantics','status':'PASS'})
reject('Protein case is not silently normalized',lambda:h.parse_fasta('>p\nmk',h.AA))
raw=['fixture',11,.8,3.5,4.25,8,2,.499,3,4];metrics=h.validate_author_return(raw,'fixture');assert metrics['author_N50']==3.5
raw[5]=2**54+1;assert h.validate_author_return(raw,'fixture')['total_nucleotide_bases']==2**54+1
checks.append({'check':'All10original values retain fractionalN50 and exact large integer counts','status':'PASS'})
bad=raw.copy();bad[4]=float('nan');reject('Nonfinite original measurement held',lambda:h.validate_author_return(bad,'fixture'))
report=folder/'synthetic_report.tsv';report.write_text('\t'.join(h.PROTEIN_COLUMNS)+'\nfixture\t99.25\t0.5\tFixtureModel\tNone\n');assert h.parse_protein_report(report,'fixture')[1:]==(99.25,.5)
checks.append({'check':'Declared five-column protein report accepted as synthetic only','status':'PASS'})
reject('Accession/version mismatch rejected',lambda:h.parse_protein_report(report,'fixture.1'))
report.write_text('\t'.join(h.PROTEIN_COLUMNS+h.DNA_COLUMNS)+'\n');reject('Invented nucleotide columns rejected',lambda:h.parse_protein_report(report,'fixture'))
report.write_text('\t'.join(h.PROTEIN_COLUMNS)+'\nfixture\tnan\t0\tFixture\tNone\n');reject('Missing/nonfinite estimate never negative',lambda:h.parse_protein_report(report,'fixture'))
report.write_text('\t'.join(h.PROTEIN_COLUMNS)+'\nfixture\t99\t0\tFixture\tNone\textra\n');reject('Extra data cell rejected despite correct five-column header',lambda:h.parse_protein_report(report,'fixture'))
partial=folder/'closure_aggregate';(partial/'unit01').mkdir(parents=True);(partial/'unit02').mkdir()
for unit in ('unit01','unit02'):(partial/unit/'command.json').write_text('{}')
(partial/'unit01/execution.json').write_text(json.dumps({'owned_group_empty':True}))
assert p.all_unit_groups_closed(partial) is False
(partial/'unit02/execution.json').write_text(json.dumps({'owned_group_empty':True}));assert p.all_unit_groups_closed(partial) is True
checks.append({'check':'Later started unit without terminal receipt cannot inherit earlier closure','status':'PASS'})
schema=h.read(R/'metadata/checkm2_feature_schema_v001.json');columns=schema['ordered_dataframe_columns'];values=[0]*21241;kinds=['i']*21241
h.validate_feature_contract(schema,columns,['fixture'],values,kinds);checks.append({'check':'Complete reviewed21242-column schema accepted without scientificimports','status':'PASS'})
wrong=columns.copy();wrong[1],wrong[2]=wrong[2],wrong[1];reject('Reordered feature columns rejected without correction',lambda:h.validate_feature_contract(schema,wrong,['fixture'],values,kinds))
bad=values.copy();bad[0]=.5;reject('Nonintegral AA/KO count rejected',lambda:h.validate_feature_contract(schema,columns,['fixture'],bad,kinds))
bad=values.copy();bad[20437]=1.1;reject('Invalid membershipfraction rejected',lambda:h.validate_feature_contract(schema,columns,['fixture'],bad,kinds))
bad=values.copy();bad[-1]=float('nan');reject('Nonfinite raw vector rejected',lambda:h.validate_feature_contract(schema,columns,['fixture'],bad,kinds))
badkind=kinds.copy();badkind[0]='O';reject('Convertible object/string storage is not accepted',lambda:h.validate_feature_contract(schema,columns,['fixture'],values,badkind))
saved=(p.STATE,p.legacy.stop_gate,p.LAUNCH)
try:
 p.STATE=folder/'synthetic_progress.json';p.legacy.stop_gate=lambda *args:None;p.LAUNCH=None
 p.legacy.progress('PREPARED','fixture adapter only');assert p.STATE.exists()
 checks.append({'check':'Isolated byte-pinned readiness progress targets only new fixture state','status':'PASS'})
 os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]))
 try:p.run_unit('fixture_exit7',[sys.executable,'-c','import sys;sys.exit(7)'],os.environ.copy(),folder)
 except p.UnitFailure as ex:assert ex.receipt['exit_code']==7 and ex.receipt['owned_group_empty'] is True
 else:raise AssertionError('Nonzero subprocess treated as success')
 checks.append({'check':'Real tiny stdlib child exit7 retained with complete groupclosure','status':'PASS'})
 try:p.run_unit('fixture_timeout',[sys.executable,'-c','import time;time.sleep(2)'],os.environ.copy(),folder,timeout=.01)
 except p.UnitFailure as ex:assert ex.receipt['failure_kind']=='TIMEOUT' and ex.receipt['owned_group_empty'] is True
 else:raise AssertionError('Deadline did not fail closed')
 checks.append({'check':'Declared-unit deadline retains classification and closes own tiny child','status':'PASS'})
finally:p.STATE,p.legacy.stop_gate,p.LAUNCH=saved
assert h.sha(R/'state/STOP_CHECKM2_PILOT')==stop_sha and h.sha(R/'state/checkm2_pilot_progress.json')==old_progress_sha
checks.append({'check':'Owned biologicalSTOP and acceptedFNA progress unchanged','status':'PASS'})
for path in (R/'scripts').glob('checkm2_protein*_v001.py'):ast.parse(path.read_text())
report={'status':'PASS','fixture_only':True,'real_genome_FAA_model_or_author_tool_executed':False,'tiny_stdlib_exit_deadline_children_only':True,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'controller_sha256':h.sha(Path(p.__file__)),'helpers_sha256':h.sha(Path(h.__file__)),'feature_schema_sha256':h.sha(R/'metadata/checkm2_feature_schema_v001.json')};h.save(R/'evidence/checkm2_protein_pilot_v001/fixture_report.json',report);print(json.dumps({'status':'PASS','checks':len(checks)}))
