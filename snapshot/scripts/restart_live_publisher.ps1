$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if($env:COMPUTERNAME -ne 'WD'){throw 'WD-only publisher restart'}
$state=Join-Path $projectRoot 'state'
function Utc-Date($value){if($value -is [datetime]){return $value.ToUniversalTime()};return [DateTimeOffset]::Parse([string]$value).UtcDateTime}
function Save-Atomic($path,$value){
 $tmp=$path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
 [IO.File]::WriteAllText($tmp,($value|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
 if([IO.File]::Exists($path)){[IO.File]::Replace($tmp,$path,[NullString]::Value)}else{[IO.File]::Move($tmp,$path)}
}
function Matches-Identity($identity){
 $process=Get-Process -Id $identity.pid -ErrorAction SilentlyContinue
 return ($process -and $process.StartTime.ToUniversalTime().Ticks -eq (Utc-Date $identity.creation_time_utc).Ticks)
}
$old=Get-Content (Join-Path $state 'launch_live_publisher.json') -Raw | ConvertFrom-Json
if(-not (Matches-Identity $old)){throw 'Old publisher creation identity is not live; no stop issued'}
$command=(Get-CimInstance Win32_Process -Filter ('ProcessId='+$old.pid)).CommandLine
if($command -notlike '*live_stage_publisher.py*' -or $command.IndexOf($projectRoot,[StringComparison]::OrdinalIgnoreCase) -lt 0){throw 'Old publisher command not verified'}
$console=Get-Content (Join-Path $state 'launch_live_console.json') -Raw | ConvertFrom-Json
if(-not (Matches-Identity $console)){throw 'Expected visible monitor identity is not live'}
$stopPath=Join-Path $state 'LIVE_PROGRESS_STOP'
if(Test-Path -LiteralPath $stopPath){throw 'Existing publisher stop flag is not owned by this restart'}
$token=[guid]::NewGuid().ToString('N')
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$evidence=Join-Path $projectRoot ('evidence\monitor\publisher_restart_'+$stamp+'_'+$token.Substring(0,8))
[IO.Directory]::CreateDirectory($evidence)|Out-Null
foreach($name in @('launch_live_publisher.json','live_publisher_owner.json','live_publisher_exit.json')){
 $path=Join-Path $state $name
 if(Test-Path -LiteralPath $path){Copy-Item -LiteralPath $path -Destination (Join-Path $evidence ('before_'+$name))}
}
$requested=(Get-Date).ToUniversalTime()
$ownedStop=@{token=$token;requested_utc=$requested.ToString('o');purpose='Restart only evidence publisher';old_publisher=$old}
$file=[IO.File]::Open($stopPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$bytes=[Text.Encoding]::UTF8.GetBytes(($ownedStop|ConvertTo-Json -Depth 6));$file.Write($bytes,0,$bytes.Length);$file.Flush($true)}finally{$file.Close()}
$deadline=(Get-Date).AddSeconds(20)
while(Matches-Identity $old){if((Get-Date)-gt $deadline){throw 'Publisher did not gracefully close; stop flag preserved and no relaunch'};Start-Sleep -Milliseconds 250}
$exitPath=Join-Path $state 'live_publisher_exit.json'
$exitReceipt=Get-Content $exitPath -Raw | ConvertFrom-Json
if($exitReceipt.pid -ne $old.pid -or $exitReceipt.status -ne 'STOPPED' -or (Utc-Date $exitReceipt.ended_utc) -lt $requested){throw 'Matching graceful exit receipt missing; no relaunch'}
$probe=[IO.File]::Open((Join-Path $state 'live_publisher.lock'),[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::ReadWrite)
try{$probe.Lock(0,1);$probe.Unlock(0,1)}finally{$probe.Close()}
Copy-Item -LiteralPath $exitPath -Destination (Join-Path $evidence 'graceful_exit.json')
$closure=@{status='OLD_PUBLISHER_CLOSED_AND_LOCK_RELEASED';old_identity=$old;matching_native_identity_absent=$true;os_byte_lock_reacquired_and_released=$true;exit_receipt_sha256=(Get-FileHash $exitPath -Algorithm SHA256).Hash.ToLowerInvariant();verified_utc=(Get-Date).ToUniversalTime().ToString('o')}
Save-Atomic (Join-Path $evidence 'old_publisher_closure.json') $closure
$currentStop=Get-Content $stopPath -Raw | ConvertFrom-Json
if($currentStop.token -ne $token){throw 'Publisher stop ownership changed; flag preserved'}
Remove-Item -LiteralPath $stopPath
$python='C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$script=Join-Path $projectRoot 'scripts\live_stage_publisher.py'
$job=Start-Process -FilePath $python -ArgumentList @('-B','-u',$script) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $evidence 'publisher.stdout.txt') -RedirectStandardError (Join-Path $evidence 'publisher.stderr.txt') -PassThru
$launch=@{pid=$job.Id;creation_time_utc=$job.StartTime.ToUniversalTime().ToString('o');script='scripts/live_stage_publisher.py';script_sha256=(Get-FileHash $script -Algorithm SHA256).Hash.ToLowerInvariant();role='progress_publisher_not_scientific_worker';restart_token=$token}
Save-Atomic (Join-Path $state 'launch_live_publisher.json') $launch
$deadline=(Get-Date).AddSeconds(15)
do{
 if(-not (Matches-Identity $launch)){throw 'New publisher closed before publication; inspect restart stderr'}
 $owner=Get-Content (Join-Path $state 'live_publisher_owner.json') -Raw | ConvertFrom-Json
 $journal=Get-Content (Join-Path $state 'live_stages.json') -Raw | ConvertFrom-Json
 if($owner.pid -eq $job.Id -and $owner.script_sha256 -eq $launch.script_sha256 -and $journal.publisher_pid -eq $job.Id){break}
 if((Get-Date)-gt $deadline){throw 'New publisher did not commit matching owner/journal'}
 Start-Sleep -Milliseconds 250
}while($true)
if(-not (Matches-Identity $console)){throw 'Visible monitor identity changed during publisher-only restart'}
$receipt=@{status='PUBLISHER_RESTARTED_AND_JOURNAL_VERIFIED';old_closure=$closure;new_publisher=$launch;visible_monitor=$console;visible_monitor_preserved=$true;workflow_stop_touched=$false;scientific_workers_touched=$false;publisher_stop_flag_removed_by_own_token=$true;stage04_status=(@($journal.stages)|Where-Object id -eq '04').status;completed_utc=(Get-Date).ToUniversalTime().ToString('o');evidence_directory=$evidence}
Save-Atomic (Join-Path $evidence 'restart_receipt.json') $receipt
Save-Atomic (Join-Path $state 'live_publisher_restart_receipt.json') $receipt
$receipt|ConvertTo-Json -Depth 10
