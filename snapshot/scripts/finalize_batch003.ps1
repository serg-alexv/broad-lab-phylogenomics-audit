$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime=Get-Content (Join-Path $projectRoot 'config\runtime.json') -Raw | ConvertFrom-Json
$launch=Get-Content (Join-Path $projectRoot 'state\launch_batch003.json') -Raw | ConvertFrom-Json
$owner=Get-Content (Join-Path $projectRoot 'state\acquire_owner.json') -Raw | ConvertFrom-Json
$watch=Get-Process -Id $launch.pid -ErrorAction SilentlyContinue
if($watch){
 if($watch.StartTime.ToUniversalTime().Ticks -ne ([datetime]$launch.creation_time_utc).ToUniversalTime().Ticks){throw 'Batch003 process identity mismatch'}
 $watch.WaitForExit()
}
$exitPath=Join-Path $projectRoot ('logs\acquisition_exit_'+$owner.run_id+'.json')
$terminal=Get-Content $exitPath -Raw | ConvertFrom-Json
if($terminal.pid -ne $launch.pid -or $terminal.status -notin @('COMPLETE','PARTIAL_FAILURE')){throw 'Batch003 closure unresolved or stopped'}
$baseline=Join-Path $projectRoot 'qc\history\20261026T165845Z_accepted1046_before_new_cohort\acquisition_validation.json'
& $runtime.python (Join-Path $projectRoot 'scripts\verify_acquisition.py') --verify-new-from $baseline
if($LASTEXITCODE -ne 0){throw 'New-cohort independent integrity verification failed'}
& $runtime.python (Join-Path $projectRoot 'scripts\audit_source_provenance.py')
if($LASTEXITCODE -ne 0){throw 'Source provenance audit failed'}
& $runtime.python (Join-Path $projectRoot 'scripts\select_panel.py')
if($LASTEXITCODE -ne 0){throw 'Provisional source/sequence-QC refresh failed'}
& $runtime.python (Join-Path $projectRoot 'scripts\checkpoint.py')
if($LASTEXITCODE -ne 0){throw 'Final checkpoint failed'}
@{at_utc=(Get-Date).ToUniversalTime().ToString('o');status='STARTUP_ACQUISITION_VERIFIED';acquisition_terminal=$terminal.status;prior1046integrityresults='PRESERVED_WITHOUT_RECHECK';sourceaudit='COMPLETED';production_biological_qc='NOT_RUN';trees='NOT_RUN';defence='NOT_RUN'} | ConvertTo-Json | Set-Content (Join-Path $projectRoot 'state\batch003_finalization.json') -Encoding utf8
