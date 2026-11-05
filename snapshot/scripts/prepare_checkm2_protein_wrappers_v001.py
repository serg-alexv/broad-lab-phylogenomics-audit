"""Generate a held separate lifecycle wrapper set from byte-pinned accepted sources."""
from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 sources={'scripts/launch_checkm2_pilot.ps1':'3f945771e0d18199f8aa0ffc382704bc11e8b05185b785f8cd56de0bbe7ac29f','scripts/checkm2_pilot_image_entry.py':'e91d874563792e7b019d9c95eddad0df2a5cd140623e03dcf817da3667cdcb29','scripts/checkm2_pilot_image.sh':'57594defc03bb91ae9821356e4a8b5472c0caaad88aa19aa8f83766af6646147'}
 texts={}
 for name,expected in sources.items():
  p=R/name
  if sha(p)!=expected:raise RuntimeError('Accepted nucleotide lifecycle source differs:'+name)
  texts[name]=p.read_text()
 native=texts['scripts/launch_checkm2_pilot.ps1'].replace('checkm2_pilot','checkm2_protein_pilot_v001')
 native=native.replace('state\\checkm2_protein_pilot_v001_launcher.lock','state\\checkm2_pilot_launcher.lock')
 native=native.replace('scripts/checkm2_protein_pilot_v001_image.sh','scripts/checkm2_protein_image_v001.sh')
 # A second explicit admission is required; this file never removes a STOP.
 marker=" $operation=if($MountSmoke){'MOUNT_SMOKE_ONLY'}else{'PREDICTION'}"
 gate=""" $strategyPath=Join-Path $projectRoot 'state/checkm2_protein_strategy_ready_v001.json'
 if(-not (Test-Path -LiteralPath $strategyPath)){throw 'HELD: supported-protein strategy admission absent; no worker launched'}
 $strategy=Get-Content -LiteralPath $strategyPath -Raw | ConvertFrom-Json
 if($strategy.schema -ne 'TREE2_SUPPORTED_PROTEIN_STRATEGY_V1' -or $strategy.status -ne 'ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT' -or $strategy.biological_dispatch_authorized -ne $true){throw 'HELD: protein strategy not admitted'}
 foreach($pin in $strategy.sources){$null=Read-BoundProjectJsonSource $pin.path $pin.sha256}
"""
 # Source files are not JSON; use the same path containment/hash policy.
 function="""function Read-BoundProjectJsonSource([string]$relative,[string]$expected){
 $target=[IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
 if(-not $target.StartsWith($projectRoot+'\\',[StringComparison]::OrdinalIgnoreCase)){throw 'Strategy source path escapes project'}
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $expected){throw 'Strategy source SHA differs'}
 return $true
}
"""
 native=native.replace('try{\n $priorPath=',function+'try{\n $priorPath=',1).replace(marker,gate+marker,1)
 native=native.replace('resume_from=$null;created_utc=',"resume_from=$null;strategy_receipt_path=($linuxRoot+'/state/checkm2_protein_strategy_ready_v001.json');strategy_receipt_sha256=(Get-FileHash -LiteralPath $strategyPath -Algorithm SHA256).Hash.ToLowerInvariant();created_utc=",1)
 native=native.replace(" if($ResumeFrom){\n  $resolved=", " if($ResumeFrom){throw 'Stock or legacy resume is forbidden for supported-protein v001'}\n if($ResumeFrom){\n  $resolved=",1)
 (R/'scripts/launch_checkm2_protein_pilot_v001.ps1').write_text(native)
 entry=texts['scripts/checkm2_pilot_image_entry.py'].replace('checkm2_pilot','checkm2_protein_pilot_v001')
 entry=entry.replace("ready = read(ready_path)","strategy_path = inside(request['strategy_receipt_path'])\n    if sha(strategy_path) != request['strategy_receipt_sha256']:\n        raise RuntimeError('Protein strategy changed after native admission')\n    ready = read(ready_path)",1)
 entry=entry.replace("    if request.get('resume_from'):\n        inner_command += ['--resume-from', str(inside(request['resume_from']))]","    if request.get('resume_from'):\n        raise RuntimeError('Resume forbidden in supported protein route')",1)
 entry=entry.replace("detail='One-genome numeric result and runtime closure verified; production QC review remains'","detail='Supported protein resource result and namespace closed; production QC remains unaccepted'")
 (R/'scripts/checkm2_protein_image_entry_v001.py').write_text(entry)
 shell=texts['scripts/checkm2_pilot_image.sh'].replace('checkm2_pilot_image_entry.py','checkm2_protein_image_entry_v001.py')
 (R/'scripts/checkm2_protein_image_v001.sh').write_text(shell)
 print('HELD_WRAPPERS_GENERATED_NO_LAUNCH')
if __name__=='__main__':main()
