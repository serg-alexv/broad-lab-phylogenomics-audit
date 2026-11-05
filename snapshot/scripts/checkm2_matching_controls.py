"""Matching-version numerical/control diagnostics; no genome or biology acceptance."""
from pathlib import Path
import argparse,hashlib,json,os,warnings
import checkm2_runtime_image as image
import checkm2_effective_bootstrap as bootstrap
import checkm2_private_install_linux as old
R=image.R;E=image.E

def evaluate():
 proof=bootstrap.preload_and_verify()
 import numpy as np,pandas as pd,sklearn,tensorflow as tf
 from sklearn.exceptions import InconsistentVersionWarning
 from checkm2.modelProcessing import modelProcessor
 from checkm2 import modelPostprocessing
 from scipy.sparse import csr_matrix
 from threadpoolctl import threadpool_info
 from decimal import Decimal,localcontext
 spec=bootstrap.specification()
 for row in spec['base_model_assets']:
  if image.sha(R/row['path'])!=row['sha256']:raise RuntimeError('Original model/data asset changed')
 with warnings.catch_warnings(record=True) as caught:
  warnings.simplefilter('always',InconsistentVersionWarning);loaded=modelProcessor(threads=2)
 version_warnings=[str(w.message) for w in caught if isinstance(w.message,InconsistentVersionWarning)]
 if version_warnings:raise RuntimeError('Matching-version scaler still emitted version warning')
 scaler=loaded.minmax_scaler;n=int(scaler.n_features_in_)
 if n!=21241:raise RuntimeError('Unexpected full scaler feature count')
 x=np.vstack([np.zeros(n),np.ones(n),-np.ones(n),np.linspace(-.5,.5,n),scaler.data_min_,scaler.data_max_]).astype(np.float64);rows=x.shape[0]
 oracle=x*np.asarray(scaler.scale_)+np.asarray(scaler.min_)
 if getattr(scaler,'clip',False):oracle=np.clip(oracle,*scaler.feature_range)
 actual=scaler.transform(x.copy());per_column=np.max(np.abs(actual-oracle),axis=0)
 if not np.all(np.isfinite(actual)) or not np.allclose(actual,oracle,rtol=1e-12,atol=1e-12):raise RuntimeError('All-column affine scaler control differs')
 decimal_error=0.;decimal_checks=0
 with localcontext() as context:
  context.prec=60
  for row in (0,1,4,5):
   for column in range(n):
    exact=Decimal.from_float(float(x[row,column]))*Decimal.from_float(float(scaler.scale_[column]))+Decimal.from_float(float(scaler.min_[column]))
    expected=float(exact)
    if getattr(scaler,'clip',False):expected=min(max(expected,scaler.feature_range[0]),scaler.feature_range[1])
    error=abs(float(actual[row,column])-expected);decimal_error=max(decimal_error,error);decimal_checks+=1
    if error>1e-12+1e-12*abs(expected):raise RuntimeError('Independent Decimal affine fixture differs')
 outputs={};dims={}
 for name,model in [('general',loaded.general_model_comp),('contamination',loaded.model_cont)]:
  if model.num_feature()!=n:raise RuntimeError('General/scaler feature dimensions differ')
  y=np.asarray(model.predict(x,num_threads=2))
  if y.shape!=(rows,) or not np.all(np.isfinite(y)):raise RuntimeError('Synthetic booster finite/shape failure')
  outputs[name]=y.tolist();dims[name]=model.num_feature()
 shape=loaded.specific_model_comp_nn.input_shape;seq=int(shape[1])
 if seq!=20021 or int(shape[2])!=1:raise RuntimeError('Specific sequence/channel dimensions differ')
 nn=np.asarray(loaded.specific_model_comp_nn(np.asarray(actual[:,:seq],dtype=np.float32).reshape(rows,seq,1),training=False).numpy())
 if nn.shape!=(rows,1) or not np.all(np.isfinite(nn)):raise RuntimeError('Synthetic NN finite/shape failure')
 upstream,scaled=loaded.run_prediction_specific(x.copy(),seq)
 if not np.allclose(scaled,oracle,rtol=1e-12,atol=1e-12) or not np.allclose(upstream,nn.reshape(-1)*100,rtol=1e-5,atol=1e-4):raise RuntimeError('Upstream scale/slice/reshape/100-scale composition differs')
 outputs['specific_unscaled']=nn.tolist();dims['specific_sequence']=seq;dims['specific_channels']=1
 selector=modelPostprocessing.modelProcessor.__new__(modelPostprocessing.modelProcessor);selector.reduced_cutoff=1500
 fixtures=[(50,50,1,1499,'Gradient Boost (General Model)'),(50,50,1,1500,'Neural Network (Specific Model)'),(95,95,1,2000,'Neural Network (Specific Model)'),(95,95,.5,2000,'Gradient Boost (General Model)'),(20,30,1,2000,'Neural Network (Specific Model)')]
 selected=[]
 for general,specific,cosine,aa,expected in fixtures:
  value,chosen=selector.cosine_decider(pd.Series({'General':general,'Specific':specific,'Cosine_Similarity':cosine,'AA_Ratio':aa}))
  if chosen!=expected:raise RuntimeError('Selected model boundary fixture differs')
  selected.append({'general':general,'specific':specific,'cosine':cosine,'aa_ratio':aa,'expected':expected,'actual':chosen,'synthetic_value':float(value)})
 a=csr_matrix([[1.,0.],[0.,1.],[0.,0.]]);b=csr_matrix([[1.,1.],[0.,0.]])
 cosine=selector._modelProcessor__calculate_sparse_CSM(a,b);expected=np.array([[1/np.sqrt(2),0],[1/np.sqrt(2),0],[0,0]])
 if not np.allclose(cosine,expected,rtol=1e-12,atol=1e-12):raise RuntimeError('Sparse cosine/zero norm control differs')
 after=bootstrap.provenance('AFTER_MATCHING_MODEL_AND_SELECTION_CONTROLS')
 report={'status':'MATCHING_VERSION_FORWARD_CONTROLS_PASS_RESOURCE_ONLY','at_utc':image.utc(),'scope':'SYNTHETIC_CONTROLS_NO_BIOLOGICAL_TRUTH','genome_inputs_used':0,'production_acceptance':False,'scaler_saved_version':'1.6.1','effective_sklearn_version':sklearn.__version__,'inconsistent_version_warnings':version_warnings,'recorded_load_warnings':[{'category':w.category.__name__,'message':str(w.message)} for w in caught],'import_proof':proof,'post_control_provenance':after,'feature_dimensions':dims,'scaler_oracle':{'columns_tested':n,'rows':4,'maximum_absolute_difference':float(per_column.max()),'all_columns_within_tolerance':True,'rtol':1e-12,'atol':1e-12,'formula':'X * saved_scale_ + saved_min_; optional saved clipping'},'synthetic_outputs':outputs,'upstream_specific_composition':'MATCH_FOR_SYNTHETIC_FIXTURES_ONLY','selection_fixtures':selected,'sparse_cosine_zero_norm_fixture':'PASS','native_threadpools':threadpool_info(),'loaded_native_maps':[line for line in Path('/proc/self/maps').read_text().splitlines() if '.so' in line and ('sklearn' in line or 'libgomp' in line or 'libomp' in line)],'runtime_environment_overrides':spec['required_runtime_environment'],'all_original_model_assets_verified':True,'script_sha256':image.sha(__file__),'bootstrap_sha256':image.sha(R/'scripts/checkm2_effective_bootstrap.py')}
 report['scaler_oracle'].update(rows=rows,fixture_patterns=['zeros','ones','minus_ones','linear_-0.5_to0.5','saved_data_min','saved_data_max'],decimal_precision=60,decimal_scalar_checks=decimal_checks,decimal_maximum_absolute_difference=decimal_error)
 image.save(E/'matching_runtime_controls.json',report);print(json.dumps(report),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--evaluate',action='store_true');a=ap.parse_args();image.private();os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]));old.gate()
 if a.evaluate:evaluate();return
 with image.RuntimeImage(True,True,E/'matching_runtime_mount.json') as ctx:
  spec=bootstrap.bind_overlay(ctx);os.environ.update(spec['required_runtime_environment']);os.environ['TREE2_CHECKM2_READONLY_RUNTIME_VERIFIED']='1';os.environ['TREE2_CHECKM2_RUNTIME_MOUNT_RECEIPT']=str(ctx.receipt)
  for name,arg in [('version','--version'),('help','--help')]:
   os.environ['TREE2_EFFECTIVE_ORIGIN_RECEIPT']=str(E/f'matching_cli_{name}_origins.json')
   old.run('matching_cli_'+name,[str(image.PREFIX/'bin/python'),str(R/'scripts/checkm2_effective_bootstrap.py'),'checkm2',arg],600)
  os.environ.pop('TREE2_EFFECTIVE_ORIGIN_RECEIPT',None)
  old.run('matching_forward_controls',[str(image.PREFIX/'bin/python'),str(R/'scripts/checkm2_matching_controls.py'),'--evaluate'],600)
  image.save(E/'matching_runtime_inside_receipt.json',{'status':'MATCHING_RUNTIME_TESTS_PASS_RESOURCE_ONLY','at_utc':image.utc(),'static_effective_manifest_path':bootstrap.SPEC.relative_to(R).as_posix(),'static_effective_manifest_sha256':image.sha(bootstrap.SPEC),'control_receipt_path':'evidence/checkm2_runtime/matching_runtime_controls.json','control_receipt_sha256':image.sha(E/'matching_runtime_controls.json'),'phases':old.PHASES,'all_owned_smoke_groups_closed':all(x['process_group_empty'] for x in old.PHASES),'runtime_environment_overrides':spec['required_runtime_environment'],'production_acceptance':False,'genome_inputs_used':0})
if __name__=='__main__':main()
