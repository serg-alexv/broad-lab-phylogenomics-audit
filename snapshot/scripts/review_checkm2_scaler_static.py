"""Inspect pickle opcodes and author source as data; never unpickle/import models."""
from pathlib import Path
from compression import zstd
import datetime,hashlib,json,os,pickletools,tarfile,zipfile
R=Path(__file__).resolve().parents[1];E=R/'evidence/checkm2_runtime'
ARCHIVE=R/'work/checkm2_resolution/channels/bioconda/noarch/checkm2-1.1.0-pyhdfd78af_2.conda'
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 if digest(ARCHIVE)!='1af64d8c354104818d0b7d4fbc23c7c875e8a8b73f2541ecf1d39b90385f27d2':raise RuntimeError('Accepted package source changed')
 sources={};controls=[];fields={};scaler_sha=None;op_fields=[]
 with zipfile.ZipFile(ARCHIVE) as archive:
  for part in archive.namelist():
   if not part.startswith('pkg-'):continue
   with archive.open(part) as compressed,zstd.open(compressed,'rb') as stream,tarfile.open(fileobj=stream,mode='r|') as tar:
    for member in tar:
     if member.name.endswith('checkm2/models/scaler.sav'):
      raw=tar.extractfile(member).read();scaler_sha=hashlib.sha256(raw).hexdigest();ops=list(pickletools.genops(raw))
      for i,(op,value,offset) in enumerate(ops):
       if not isinstance(value,str):continue
       if value in ('_sklearn_version','n_features_in_','feature_range','copy','clip','scale_','min_','data_min_','data_max_','data_range_','feature_names_in_'):
        following=[(a,b) for a,b,_ in ops[i+1:i+8] if a.name!='MEMOIZE'];op_fields.append({'name':value,'byte_offset':offset,'next_primitive_opcodes':[{'op':a.name,'value':b if isinstance(b,(str,int,float,bool,type(None))) else 'NONPRIMITIVE_NOT_EXECUTED'} for a,b in following[:5]]})
        if value in ('_sklearn_version','n_features_in_'):fields[value]=following[0][1]
        elif value in ('clip','copy'):fields[value]=following[0][0].name=='NEWTRUE'
        elif value=='feature_range':fields[value]=[following[0][1],following[1][1]]
     elif member.name.endswith(('checkm2/main.py','checkm2/modelProcessing.py','checkm2/predictQuality.py')):
      raw=tar.extractfile(member).read();text=raw.decode();sources[member.name]={'sha256':hashlib.sha256(raw).hexdigest(),'lines':text.splitlines()}
     elif '/checkm2/testrun/TEST' in member.name and member.isfile():
      source=tar.extractfile(member);controls.append({'path':member.name,'bytes':member.size,'sha256':hashlib.file_digest(source,'sha256').hexdigest()})
 assert fields=={'feature_range':[0,1],'copy':True,'clip':False,'n_features_in_':21241,'_sklearn_version':'1.6.1'}
 snippets={}
 for path,source in sources.items():
  ranges=(1,23) if path.endswith('/main.py') else ((65,87) if path.endswith('/modelProcessing.py') else (201,234))
  snippets[path]={'source_sha256':source['sha256'],'selected_lines':[{'line':i+1,'text':line} for i,line in enumerate(source['lines']) if ranges[0]<=i+1<=ranges[1]]}
  if path.endswith('/main.py'):snippets[path]['testrun_lines']=[{'line':i+1,'text':line} for i,line in enumerate(source['lines']) if 240<=i+1<=266]
 result={'status':'STATIC_SCALER_VERSION_AND_INTERFACE_REVIEW','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'official_package_archive_sha256':digest(ARCHIVE),'scaler_sha256':scaler_sha,'pickle_fields_observed_without_deserialization':fields,'observed_state_opcodes':op_fields,'saved_sklearn_version_is_not_proof_of_original_training_environment':True,'controls':controls,'source_snippets':snippets,'source_findings':{'checkm2_main_prepends_base_site_packages':True,'testrun_only_checks_more_than_one_result_row_not_expected_numeric_values':True,'full_scaled_features_feed_model_selection_as_well_as_specific_nn':True,'current_pickle_version_mismatch_is_unsupported_by_sklearn':True},'production_gate':'BLOCKED_UNTIL_MATCHING_EFFECTIVE_SCALER_VERSION_AND_INDEPENDENT_VALIDATION','unpickle_import_mount_prediction_or_version_change_performed':False,'primary_docs':['https://scikit-learn.org/1.6/model_persistence.html','https://scikit-learn.org/1.6/modules/generated/sklearn.preprocessing.MinMaxScaler.html']}
 p=E/'scaler_static_compatibility_review.json';tmp=p.with_suffix('.tmp')
 with tmp.open('w') as out:json.dump(result,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
 os.replace(tmp,p);print(json.dumps({'status':result['status'],'fields':fields,'controls':len(controls),'production_gate':result['production_gate']}))
if __name__=='__main__':main()
