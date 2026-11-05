$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime=Get-Content -LiteralPath (Join-Path $projectRoot 'config\runtime.json') -Raw | ConvertFrom-Json
$launch=Get-Content -LiteralPath (Join-Path $projectRoot 'state\launch_acquisition_batch_001.json') -Raw | ConvertFrom-Json
$owner=Get-Content -LiteralPath (Join-Path $projectRoot 'state\acquire_owner.json') -Raw | ConvertFrom-Json
$watch=Get-Process -Id $launch.pid -ErrorAction SilentlyContinue
if ($watch) {
  if ($watch.StartTime.ToUniversalTime().ToString('o') -ne $launch.creation_time_utc) {throw 'PID identity mismatch; refusing to wait on unrelated process'}
  $watch.WaitForExit()
  $actualExitCode=$watch.ExitCode
}
$terminalPath=Join-Path $projectRoot ('logs\acquisition_exit_'+$owner.run_id+'.json')
if (-not (Test-Path -LiteralPath $terminalPath)) {throw 'No matching terminal receipt; closure unresolved'}
$terminal=Get-Content -LiteralPath $terminalPath -Raw | ConvertFrom-Json
if ($terminal.pid -ne $launch.pid) {throw 'Terminal receipt PID mismatch'}
if ($terminal.status -notin @('COMPLETE','PARTIAL_FAILURE')) {throw ('Acquisition stopped or failed: '+$terminal.status)}
& $runtime.python (Join-Path $projectRoot 'scripts\verify_acquisition.py')
if ($LASTEXITCODE -ne 0) {throw 'Independent source/sequence validation failed'}
& $runtime.python (Join-Path $projectRoot 'scripts\checkpoint.py')
if ($LASTEXITCODE -ne 0) {throw 'Checkpoint failed'}
@{at_utc=(Get-Date).ToUniversalTime().ToString('o');acquisition_run_id=$owner.run_id;acquisition_pid=$terminal.pid;acquisition_terminal=$terminal.status;actual_exit_code=$actualExitCode;independent_acquisition_verification='COMPLETED';biological_qc='NOT_RUN';markers='NOT_RUN';trees='NOT_RUN';defence='NOT_RUN'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'state\batch001_finalization.json') -Encoding utf8
