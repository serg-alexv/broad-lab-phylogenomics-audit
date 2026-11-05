$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime=Get-Content (Join-Path $projectRoot 'config\runtime.json') -Raw | ConvertFrom-Json
$launch=Get-Content (Join-Path $projectRoot 'state\launch_acquisition_batch_001.json') -Raw | ConvertFrom-Json
$owner=Get-Content (Join-Path $projectRoot 'state\acquire_owner.json') -Raw | ConvertFrom-Json
$watch=Get-Process -Id $launch.pid -ErrorAction SilentlyContinue
if($watch){
 if($watch.StartTime.ToUniversalTime().Ticks -ne ([datetime]$launch.creation_time_utc).ToUniversalTime().Ticks){throw 'PID creation mismatch'}
 $watch.WaitForExit()
}
$terminalPath=Join-Path $projectRoot ('logs\acquisition_exit_'+$owner.run_id+'.json')
if(-not(Test-Path $terminalPath)){throw 'Missing matching exit receipt'}
$terminal=Get-Content $terminalPath -Raw | ConvertFrom-Json
if($terminal.pid -ne $launch.pid -or $terminal.status -notin @('COMPLETE','PARTIAL_FAILURE')){throw 'Original acquisition stopped or closure unresolved'}
$phaseResults=@()
function Invoke-ControlledAcquisition([string]$panelPath){
 & $runtime.python (Join-Path $projectRoot 'scripts\acquire.py') --panel $panelPath --limit 0
 $code=$LASTEXITCODE
 $receipt=Get-Content (Join-Path $projectRoot 'state\acquisition_last_exit.json') -Raw | ConvertFrom-Json
 if($code -ne 0 -and $receipt.status -ne 'PARTIAL_FAILURE'){throw ('Acquisition stopped/failed: '+$panelPath)}
 return @{panel=$panelPath;exit_code=$code;status=$receipt.status;run_id=$receipt.run_id}
}
foreach($name in @('acquisition_batch_002.json','acquisition_qc_review_only.json')){
 $panelPath=Join-Path $projectRoot ('metadata\'+$name)
 if(Test-Path $panelPath){$phaseResults+=Invoke-ControlledAcquisition $panelPath}
}
$builderOutput=& $runtime.python (Join-Path $projectRoot 'scripts\build_replacement_queue.py') --terminal $terminalPath --original-panel (Join-Path $projectRoot 'metadata\acquisition_batch_001.json')
$builderCode=$LASTEXITCODE
$builderOutput | ForEach-Object {Write-Output $_}
if($builderCode -ne 0){throw 'Bounded replacement builder failed; no replacement execution'}
$replacement=$builderOutput[-1] | ConvertFrom-Json
if($replacement.replacement_count -gt 0){$phaseResults+=Invoke-ControlledAcquisition $replacement.queue_path}
& $runtime.python (Join-Path $projectRoot 'scripts\verify_acquisition.py')
if($LASTEXITCODE -ne 0){throw 'Independent validation failed'}
& $runtime.python (Join-Path $projectRoot 'scripts\checkpoint.py')
if($LASTEXITCODE -ne 0){throw 'Checkpoint failed'}
@{at_utc=(Get-Date).ToUniversalTime().ToString('o');status='COMPLETED_BOUNDED_ACQUISITION_SEQUENCE';phases=$phaseResults;replacement_audit=$replacement.audit_path;biological_qc='NOT_RUN';tree='NOT_RUN';defence='NOT_RUN'} | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $projectRoot 'state\queued_acquisition_exit.json') -Encoding utf8
