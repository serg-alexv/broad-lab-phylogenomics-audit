[CmdletBinding()]
param([string]$ProjectRoot='', [switch]$KeepOldConsole)
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)}
$ProjectRoot=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
if($env:COMPUTERNAME -ne 'WD'){throw 'This monitor upgrade is WD-only'}
$Out=Join-Path $ProjectRoot 'state\monitor_v3'
[IO.Directory]::CreateDirectory($Out)|Out-Null
$Stamp=[datetime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$Evidence=Join-Path $ProjectRoot ('evidence\monitor\v3_upgrade_'+$Stamp)
[IO.Directory]::CreateDirectory($Evidence)|Out-Null
function Save($Path,$Value){[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))}
function Utc($Value){if($Value -is [datetime]){return $Value.ToUniversalTime()};return [DateTimeOffset]::Parse([string]$Value).UtcDateTime}
function Identity($Number,$Birth,$Script){
 $Job=Get-Process -Id $Number -ErrorAction Stop
 $null=$Job.Handle
 if($Job.StartTime.ToUniversalTime().Ticks -ne (Utc $Birth).Ticks){throw ('Process birth mismatch: '+$Number)}
 $Command=[string](Get-CimInstance Win32_Process -Filter ('ProcessId='+$Number)).CommandLine
 if($Command.IndexOf($ProjectRoot,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $Command.IndexOf($Script,[StringComparison]::OrdinalIgnoreCase) -lt 0){throw ('Process command mismatch: '+$Number)}
 return $Job
}
function Capture($Job,$Script){return @{pid=$Job.Id;creation_time_utc=$Job.StartTime.ToUniversalTime().ToString('o');windows_creation_filetime_100ns=$Job.StartTime.ToUniversalTime().ToFileTimeUtc();script=$Script;script_sha256=(Get-FileHash -LiteralPath (Join-Path $ProjectRoot $Script) -Algorithm SHA256).Hash.ToLowerInvariant();command=[string](Get-CimInstance Win32_Process -Filter ('ProcessId='+$Job.Id)).CommandLine}}
$Old=Identity 20544 '2026-10-27T08:47:55.9789108Z' 'live_progress_v2.ps1'
$OldIdentity=Capture $Old 'scripts\live_progress_v2.ps1'
$OldIdentity.title=$Old.MainWindowTitle
$Publisher=Identity 5812 '2026-10-27T00:50:40.4735797Z' 'live_stage_publisher.py'
$PublisherIdentity=Capture $Publisher 'scripts\live_stage_publisher.py'
$Protected=@('scripts\live_stage_publisher.py','scripts\live_progress_v2.ps1','scripts\prep_activity_collector_v2.py','metadata\checkm2_phase_separated_implementation_N1_v002.json','metadata\checkm2_phase_separated_execution_plan_N1_v002.json')
$Before=@($Protected|ForEach-Object{@{path=$_;sha256=(Get-FileHash -LiteralPath (Join-Path $ProjectRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant()}})
Save (Join-Path $Evidence 'before.json') @{old_gui=$OldIdentity;publisher=$PublisherIdentity;protected_sources=$Before}
$OldCollectorLaunch=Get-Content -LiteralPath (Join-Path $ProjectRoot 'state\monitor_v2\launch_collector.json') -Raw|ConvertFrom-Json
$OldCollectorExit=Get-Content -LiteralPath (Join-Path $ProjectRoot 'state\monitor_v2\collector_exit.json') -Raw|ConvertFrom-Json
$OldCollectorError=[IO.File]::ReadAllText((Join-Path $ProjectRoot 'evidence\monitor\v2_upgrade_20261027T084754Z\collector.stderr.txt'))
Save (Join-Path $Evidence 'old_collector_diagnosis.json') @{status='UNHANDLED_OPTIONAL_SIDECAR_REPLACE_ACCESS_DENIED';old_launch=$OldCollectorLaunch;finally_receipt=$OldCollectorExit;native_exit_code='UNKNOWN_NO_RETAINED_HANDLE_OBSERVATION';stderr=$OldCollectorError;access_denial_underlying_cause='UNRESOLVED';no_exit0_inferred=$true}
$ExistingPath=Join-Path $Out 'launch_collector.json'
if(Test-Path -LiteralPath $ExistingPath){
 $Existing=Get-Content -LiteralPath $ExistingPath -Raw|ConvertFrom-Json
 try{$ExistingJob=Identity $Existing.pid $Existing.creation_time_utc 'prep_activity_collector_v3.py'}catch{$ExistingJob=$null}
 if($ExistingJob){throw 'A matching V3 collector already exists; do not create a duplicate'}
}
$Runtime=Get-Content -LiteralPath (Join-Path $ProjectRoot 'config\runtime.json') -Raw|ConvertFrom-Json
$CollectorScript=Join-Path $ProjectRoot 'scripts\prep_activity_collector_v3.py'
$Collector=Start-Process -FilePath $Runtime.python -ArgumentList ('-B -u "'+$CollectorScript+'" --project-root "'+$ProjectRoot+'" --interval 4') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Evidence 'collector.stdout.txt') -RedirectStandardError (Join-Path $Evidence 'collector.stderr.txt') -PassThru
$CollectorIdentity=Capture $Collector 'scripts\prep_activity_collector_v3.py'
Save (Join-Path $Out 'launch_collector.json') $CollectorIdentity
$ConsoleScript=Join-Path $ProjectRoot 'scripts\live_progress_v3.ps1'
$Console=Start-Process -FilePath powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$ConsoleScript+'" -ProjectRoot "'+$ProjectRoot+'" -RefreshSeconds 4') -WorkingDirectory $ProjectRoot -WindowStyle Maximized -PassThru
$ConsoleIdentity=Capture $Console 'scripts\live_progress_v3.ps1'
Save (Join-Path $Out 'launch_console.json') $ConsoleIdentity
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Tree2MonitorV3Window {
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr handle);
}
'@
$Deadline=[datetime]::UtcNow.AddSeconds(20)
$Healthy=$false
do{
 Start-Sleep -Milliseconds 250
 $Console=Identity $ConsoleIdentity.pid $ConsoleIdentity.creation_time_utc 'live_progress_v3.ps1'
 $Collector=Identity $CollectorIdentity.pid $CollectorIdentity.creation_time_utc 'prep_activity_collector_v3.py'
 $Console.Refresh()
 $HealthPath=Join-Path $Out 'display_health.json'
 if(Test-Path -LiteralPath $HealthPath){
  try{
   $Health=Get-Content -LiteralPath $HealthPath -Raw|ConvertFrom-Json
   $Snapshot=Get-Content -LiteralPath (Join-Path $Out 'preparation_activity.json') -Raw|ConvertFrom-Json
   $Healthy=$Health.pid -eq $ConsoleIdentity.pid -and (Utc $Health.creation_time_utc).Ticks -eq (Utc $ConsoleIdentity.creation_time_utc).Ticks -and [int]$Health.frame -ge 2 -and $Snapshot.collector_pid -eq $CollectorIdentity.pid -and ([datetime]::UtcNow-(Utc $Health.updated_utc)).TotalSeconds -lt 8 -and $Console.MainWindowHandle -ne 0 -and [Tree2MonitorV3Window]::IsWindowVisible($Console.MainWindowHandle) -and $Console.MainWindowTitle -eq 'TREE 2 - WD - LIVE PROGRESS V3'
  }catch{$Healthy=$false}
 }
 if($Healthy){break}
}while([datetime]::UtcNow -lt $Deadline)
if(-not $Healthy){throw 'New console did not prove two fresh frames and visible matching title; old GUI preserved. Inspect V3 receipts.'}
$ConsoleIdentity.window_title=$Console.MainWindowTitle
$ConsoleIdentity.window_handle=$Console.MainWindowHandle.ToInt64()
$ConsoleIdentity.visible=$true
Save (Join-Path $Out 'launch_console.json') $ConsoleIdentity
$BeforeFrame=[IO.File]::ReadAllText((Join-Path $Out 'display_last_frame.txt'))
[IO.File]::WriteAllText((Join-Path $Evidence 'observed_fresh_frame.txt'),$BeforeFrame,[Text.UTF8Encoding]::new($false))
Save (Join-Path $Evidence 'new_console_health_before_old_close.json') $Health
if($KeepOldConsole){
 $Receipt=@{status='V3_VISIBLE_FRESH_OLD_DISPLAY_PRESERVED';completed_utc=[datetime]::UtcNow.ToString('o');old_console=$OldIdentity;new_console=$ConsoleIdentity;new_collector=$CollectorIdentity;publisher_preserved=$PublisherIdentity;scientific_workers_touched=$false;evidence_directory=$Evidence;verified_fresh_frame=$Health}
 Save (Join-Path $Evidence 'upgrade_receipt.json') $Receipt
 Save (Join-Path $Out 'upgrade_receipt.json') $Receipt
 $Receipt|ConvertTo-Json -Depth 15
 exit 0
}
# Only the superseded display is closed, after exact birth revalidation and V3 visibility.
$Old=Identity $OldIdentity.pid $OldIdentity.creation_time_utc 'live_progress_v2.ps1'
$Old.Kill()
if(-not $Old.WaitForExit(5000)){throw 'Old owned display did not exit; no further stop action issued'}
$OldExit=$Old.ExitCode
$Publisher=Identity $PublisherIdentity.pid $PublisherIdentity.creation_time_utc 'live_stage_publisher.py'
$After=@($Protected|ForEach-Object{@{path=$_;sha256=(Get-FileHash -LiteralPath (Join-Path $ProjectRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant()}})
for($I=0;$I -lt $Before.Count;$I++){if($Before[$I].sha256 -ne $After[$I].sha256){throw ('Protected source bytes changed: '+$Before[$I].path)}}
$ScientificManifest=Get-Content -LiteralPath (Join-Path $ProjectRoot 'metadata\checkm2_phase_separated_implementation_N1_v002.json') -Raw|ConvertFrom-Json
foreach($Row in $ScientificManifest.sources){if((Get-FileHash -LiteralPath (Join-Path $ProjectRoot $Row.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Row.sha256){throw ('Scientific source pin mismatch: '+$Row.path)}}
$Receipt=@{status='V3_VISIBLE_FRESH_AND_OLD_DISPLAY_CLOSED';completed_utc=[datetime]::UtcNow.ToString('o');old_console=$OldIdentity;old_console_observed_exit=$OldExit;new_console=$ConsoleIdentity;new_collector=$CollectorIdentity;publisher_preserved=$PublisherIdentity;protected_source_bytes_unchanged=$true;scientific_workers_touched=$false;runtime_or_WSL_probes=$false;evidence_directory=$Evidence;verified_fresh_frame=$Health;protected_sources=$After}
Save (Join-Path $Evidence 'upgrade_receipt.json') $Receipt
Save (Join-Path $Out 'upgrade_receipt.json') $Receipt
$Receipt|ConvertTo-Json -Depth 15
