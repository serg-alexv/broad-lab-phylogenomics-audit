"""Bounded optional collector; the parent continues the original fast RSS gate."""
from pathlib import Path
import argparse,json,os,time
def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);a=p.parse_args();source=json.loads(Path(a.snapshot).read_text());rows=[];started=time.monotonic()
 for prior in source['processes']:
  row={k:prior[k] for k in ('pid','creation_ticks','boot_id')};path=Path('/proc')/str(prior['pid'])
  try:
   before=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(before[19])!=prior['creation_ticks']:raise RuntimeError('PID creation changed')
   values={line.split(':',1)[0]:int(line.split()[1])*1024 for line in (path/'smaps_rollup').read_text().splitlines() if ':' in line and len(line.split())>=3 and line.split()[-1]=='kB'}
   row.update(smaps_rollup=values,pss_bytes=values.get('Pss'),private_resident_bytes=values['Private_Clean']+values['Private_Dirty'] if all(k in values for k in ('Private_Clean','Private_Dirty')) else None,private_hugetlb_bytes=values.get('Private_Hugetlb'))
   row['heavy_native_mapping_paths']=sorted(set(line.split()[-1] for line in (path/'maps').read_text().splitlines() if any(x in line.lower() for x in ('tensorflow','lightgbm','sklearn','libgomp')) and '/' in line))
   row['cmdline']=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   after=(path/'stat').read_text().rsplit(')',1)[1].split()
   if int(after[19])!=prior['creation_ticks']:raise RuntimeError('PID creation changed during metrics')
  except (OSError,RuntimeError) as ex:row.update(metrics_unavailable=repr(ex),pss_bytes=None,private_resident_bytes=None)
  rows.append(row)
 pss_ok=bool(rows) and all(x.get('pss_bytes') is not None for x in rows);private_ok=bool(rows) and all(x.get('private_resident_bytes') is not None for x in rows)
 print(json.dumps({'status':'OPTIONAL_DESCRIPTIVE_METRICS_ONLY','collection_seconds':time.monotonic()-started,'processes':rows,'sum_pss_bytes':sum(x['pss_bytes'] for x in rows) if pss_ok else None,'sum_private_resident_bytes':sum(x['private_resident_bytes'] for x in rows) if private_ok else None,'pss_complete':pss_ok,'private_complete':private_ok,'used_for_resource_gate':False}),flush=True)
if __name__=='__main__':main()
