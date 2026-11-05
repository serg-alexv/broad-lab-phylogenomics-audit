[CmdletBinding()]
param([string]$ProjectRoot='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)}
$ProjectRoot=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
if($env:COMPUTERNAME -ne 'WD'){throw 'WD-only observer replacement'}
$Out=Join-Path $ProjectRoot 'state\monitor_v4'
[IO.Directory]::CreateDirectory($Out)|Out-Null
$Evidence=Join-Path $ProjectRoot ('evidence\monitor\v4_collector_'+[datetime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
[IO.Directory]::CreateDirectory($Evidence)|Out-Null
function Utc($Value){if($Value -is [datetime]){return $Value.ToUniversalTime()};return [datetimeoffset]::Parse([string]$Value).UtcDateTime}
function Save($Path,$Value){[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 25),[Text.UTF8Encoding]::new($false))}
function Identity($Number,$Birth,$Name){
 $Job=Get-Process -Id $Number -ErrorAction Stop
 $null=$Job.Handle
 if($Job.StartTime.ToUniversalTime().Ticks -ne (Utc $Birth).Ticks){throw ('Birth mismatch '+$Number)}
 $Command=[string](Get-CimInstance Win32_Process -Filter ('ProcessId='+$Number)).CommandLine
 if($Command.IndexOf($ProjectRoot,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $Command.IndexOf($Name,[StringComparison]::OrdinalIgnoreCase) -lt 0){throw ('Command mismatch '+$Number)}
 return $Job
}
function Capture($Job,$Name){return @{pid=$Job.Id;creation_time_utc=$Job.StartTime.ToUniversalTime().ToString('o');windows_creation_filetime_100ns=$Job.StartTime.ToUniversalTime().ToFileTimeUtc();script=$Name;script_sha256=(Get-FileHash -LiteralPath (Join-Path $ProjectRoot $Name) -Algorithm SHA256).Hash.ToLowerInvariant();command=[string](Get-CimInstance Win32_Process -Filter ('ProcessId='+$Job.Id)).CommandLine}}
$Gui=Identity 24544 '2026-10-27T09:34:27.9680670Z' 'live_progress_v3.ps1'
$Publisher=Identity 5812 '2026-10-27T00:50:40.4735797Z' 'live_stage_publisher.py'
$Old=Identity 14412 '2026-10-27T09:34:27.7305181Z' 'prep_activity_collector_v3.py'
$GuiIdentity=Capture $Gui 'scripts\live_progress_v3.ps1'
$PublisherIdentity=Capture $Publisher 'scripts\live_stage_publisher.py'
$OldIdentity=Capture $Old 'scripts\prep_activity_collector_v3.py'
$Protected=@('scripts\live_progress_v3.ps1','scripts\prep_activity_collector_v3.py','scripts\live_stage_publisher.py','state\monitor_v3\launch_console.json','state\monitor_v3\launch_collector.json','state\monitor_v3\collector_owner.json')
$Before=@($Protected|ForEach-Object{@{path=$_;sha256=(Get-FileHash -LiteralPath (Join-Path $ProjectRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant()}})
foreach($Name in @('launch_collector.json','collector_owner.json','collector_exit.json')){
 $Path=Join-Path $ProjectRoot ('state\monitor_v3\'+$Name)
 if(Test-Path -LiteralPath $Path){Copy-Item -LiteralPath $Path -Destination (Join-Path $Evidence ('before_'+$Name))}
}
Save (Join-Path $Evidence 'before.json') @{gui=$GuiIdentity;publisher=$PublisherIdentity;old_collector=$OldIdentity;protected=$Before}
# The only terminated process is this exact observer. Its retained native handle
# establishes the observed intentional exit; no scientific worker is inspected.
$Old=Identity $OldIdentity.pid $OldIdentity.creation_time_utc 'prep_activity_collector_v3.py'
$null=$Old.Handle
$Old.Kill()
if(-not $Old.WaitForExit(5000)){throw 'Owned old observer exit not observed; no replacement launch'}
$Closure=@{status='INTENTIONALLY_CLOSED_FOR_OBSERVER_UPGRADE';old_collector=$OldIdentity;native_exit_code=$Old.ExitCode;observed_utc=[datetime]::UtcNow.ToString('o');termination_scope='Exact birth-matched optional preparation collector only';scientific_worker_touched=$false}
Save (Join-Path $Evidence 'old_collector_actual_exit.json') $Closure
$Runtime=Get-Content -LiteralPath (Join-Path $ProjectRoot 'config\runtime.json') -Raw|ConvertFrom-Json
$Script=Join-Path $ProjectRoot 'scripts\prep_activity_collector_v4.py'
$New=Start-Process -FilePath $Runtime.python -ArgumentList ('-B -u "'+$Script+'" --project-root "'+$ProjectRoot+'" --interval 4') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Evidence 'collector.stdout.txt') -RedirectStandardError (Join-Path $Evidence 'collector.stderr.txt') -PassThru
$NewIdentity=Capture $New 'scripts\prep_activity_collector_v4.py'
Save (Join-Path $Out 'launch_collector.json') $NewIdentity
$Deadline=[datetime]::UtcNow.AddSeconds(30)
$Healthy=$false
do{
 Start-Sleep -Milliseconds 300
 $New=Identity $NewIdentity.pid $NewIdentity.creation_time_utc 'prep_activity_collector_v4.py'
 try{
  $Snapshot=Get-Content -LiteralPath (Join-Path $ProjectRoot 'state\monitor_v3\preparation_activity.json') -Raw|ConvertFrom-Json
  $Health=Get-Content -LiteralPath (Join-Path $ProjectRoot 'state\monitor_v3\display_health.json') -Raw|ConvertFrom-Json
  $Frame=[IO.File]::ReadAllText((Join-Path $ProjectRoot 'state\monitor_v3\display_last_frame.txt'))
  $Paths=@($Snapshot.artifacts|ForEach-Object{$_.path})
  $Healthy=$Snapshot.collector_version -eq 4 -and $Snapshot.collector_pid -eq $New.Id -and $Health.pid -eq $Gui.Id -and (Utc $Health.updated_utc) -gt (Utc $Snapshot.updated_utc) -and $Frame.Contains('N5') -and $Paths.Contains('metadata/checkm2_N5_independent_history_selection_review_v002.json') -and $Paths.Contains('metadata/checkm2_phase_separated_OPS_component_HELD_N5_v001.json')
 }catch{$Healthy=$false}
 if($Healthy){break}
}while([datetime]::UtcNow -lt $Deadline)
if(-not $Healthy){throw 'V4 did not prove a fresh compatible V3 frame with N5 receipts; inspect collector logs'}
$Gui=Identity $GuiIdentity.pid $GuiIdentity.creation_time_utc 'live_progress_v3.ps1'
$Publisher=Identity $PublisherIdentity.pid $PublisherIdentity.creation_time_utc 'live_stage_publisher.py'
foreach($Row in $Before){if((Get-FileHash -LiteralPath (Join-Path $ProjectRoot $Row.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Row.sha256){throw ('Preserved source/receipt changed: '+$Row.path)}}
[IO.File]::WriteAllText((Join-Path $Evidence 'fresh_unchanged_GUI_frame.txt'),$Frame,[Text.UTF8Encoding]::new($false))
$Observed=@($Snapshot.artifacts|Where-Object{$_.path -in @('metadata/checkm2_N5_independent_history_selection_review_v002.json','metadata/checkm2_phase_separated_OPS_component_HELD_N5_v001.json')})
$Receipt=@{status='V4_COLLECTOR_ACTIVE_UNCHANGED_GUI_AND_PUBLISHER_FRESH';completed_utc=[datetime]::UtcNow.ToString('o');old_collector_actual_exit=$Closure;new_collector=$NewIdentity;gui_preserved=$GuiIdentity;publisher_preserved=$PublisherIdentity;newest_source_commit=$Snapshot.latest_source_commit;resolved_git_HEAD=$Snapshot.resolved_git_HEAD;N5_receipts=$Observed;code_frozen_current=$Snapshot.code_frozen;accepted_N1_baseline_source_bound=$Snapshot.code_frozen_manifest_matches;fresh_display=$Health;protected_sources_and_receipts_preserved=$true;scientific_runtime_or_lease_probes=$false;evidence_directory=$Evidence}
Save (Join-Path $Evidence 'replacement_receipt.json') $Receipt
Save (Join-Path $Out 'replacement_receipt.json') $Receipt
$Receipt|ConvertTo-Json -Depth 25
