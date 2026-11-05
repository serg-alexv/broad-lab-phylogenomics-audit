[CmdletBinding()]
param([string]$ProjectRoot='', [ValidateRange(30,30)][int]$RefreshSeconds=30)
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)}
$ProjectRoot=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
if($env:COMPUTERNAME -ne 'WD'){throw 'WD-only display replacement'}
$Own=Join-Path $ProjectRoot 'state\monitor_display_v4'
[IO.Directory]::CreateDirectory($Own)|Out-Null
$Evidence=Join-Path $ProjectRoot ('evidence\monitor\display_v4_'+[datetime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
[IO.Directory]::CreateDirectory($Evidence)|Out-Null
function Read-Shared([string]$Path){
    $Stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try{$Reader=[IO.StreamReader]::new($Stream,[Text.Encoding]::UTF8,$true);try{return ($Reader.ReadToEnd()|ConvertFrom-Json)}finally{$Reader.Dispose()}}finally{$Stream.Dispose()}
}
function Save-New([string]$Path,$Value){
    $Data=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 30))
    $Stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try{$Stream.Write($Data,0,$Data.Length);$Stream.Flush($true)}finally{$Stream.Dispose()}
}
function Hash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Birth($Value){return [datetimeoffset]::Parse([string]$Value).UtcDateTime}
$SourceManifestPath=Join-Path $ProjectRoot 'metadata\monitor_display_v4\source_manifest.json'
$Sources=Read-Shared $SourceManifestPath
foreach($Item in $Sources.sources){if((Hash (Join-Path $ProjectRoot $Item.path)) -ne $Item.sha256){throw ('V4 source changed: '+$Item.path)}}
$RolePath=Join-Path $ProjectRoot 'state\monitor_current_roles.json'
$RoleHash=Hash $RolePath;$Roles=Read-Shared $RolePath
$Old=Get-Process -Id ([int]$Roles.gui.pid) -ErrorAction Stop
if($Old.StartTime.ToUniversalTime().Ticks -ne (Birth $Roles.gui.creation_time_utc).Ticks){throw 'Original display birth mismatch; no replacement'}
$OldCommand=[string](Get-CimInstance Win32_Process -Filter ('ProcessId='+$Old.Id)).CommandLine
if($OldCommand.IndexOf($ProjectRoot,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or $OldCommand.IndexOf([IO.Path]::GetFileName([string]$Roles.gui.script),[StringComparison]::OrdinalIgnoreCase) -lt 0){throw 'Original display command mismatch'}
[IO.File]::Copy($RolePath,(Join-Path $Evidence 'previous_monitor_current_roles.json'),$false)
$PlanPath=Join-Path $ProjectRoot 'evidence\checkm2_phase_separated_P20\resource_repair_v002\runtime_plan.json'
$PlanHash=Hash $PlanPath;$Plan=Read-Shared $PlanPath
$Pinned=Read-Shared (Join-Path $ProjectRoot $Plan.source_manifest.path)
if((Hash (Join-Path $ProjectRoot $Plan.source_manifest.path)) -ne $Plan.source_manifest.sha256){throw 'Active science source manifest differs'}
foreach($Item in $Pinned.sources){if((Hash (Join-Path $ProjectRoot $Item.path)) -ne $Item.sha256){throw ('Active scientific source differs: '+$Item.path)}}
Save-New (Join-Path $Evidence 'before.json') @{old_gui=$Roles.gui;monitor_roles_sha256=$RoleHash;active_plan_sha256=$PlanHash;active_sources=$Pinned.sources;new_sources=$Sources.sources;old_gui_will_be_preserved=$true;role_pointer_will_not_be_changed=$true}
Save-New (Join-Path $Own 'launch_once.json') @{scope='DISPLAY_ONLY';at_utc=[datetime]::UtcNow.ToString('o');source_manifest_sha256=(Hash $SourceManifestPath);evidence=$Evidence;no_scientific_process_change=$true}
$Console=$null
try{
    $Script=Join-Path $ProjectRoot 'scripts\live_progress_v4.ps1'
    $Console=Start-Process -FilePath powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$Script+'" -ProjectRoot "'+$ProjectRoot+'" -RefreshSeconds 30') -WorkingDirectory $ProjectRoot -WindowStyle Maximized -PassThru
    $null=$Console.Handle
    $Owner=@{pid=$Console.Id;creation_time_utc=$Console.StartTime.ToUniversalTime().ToString('o');windows_creation_filetime_100ns=$Console.StartTime.ToUniversalTime().ToFileTimeUtc();script='scripts\live_progress_v4.ps1';script_sha256=(Hash $Script);classifier='scripts\monitor_phase_classifier_v4.ps1';classifier_sha256=(Hash (Join-Path $ProjectRoot 'scripts\monitor_phase_classifier_v4.ps1'));refresh_seconds=30}
    Save-New (Join-Path $Own 'launch.json') @{schema='TREE2_DISPLAY_V4_NATIVE_LAUNCH_V001';native_owner=$Owner;actual_exit='UNKNOWN_LIVE_DISPLAY';previous_gui=$Roles.gui;old_gui_preserved=$true;monitor_roles_unchanged=$true;launched_utc=[datetime]::UtcNow.ToString('o')}
    $Deadline=[datetime]::UtcNow.AddSeconds(25);$Healthy=$false
    do{
        Start-Sleep -Milliseconds 250
        $Console.Refresh()
        if($Console.HasExited){throw ('New display exited: '+$Console.ExitCode)}
        try{
            $Health=Read-Shared (Join-Path $Own 'display_health.json')
            $Mode=Read-Shared (Join-Path $Own 'stable_console_mode.json')
            $Healthy=([int]$Health.pid -eq $Console.Id -and (Birth $Health.creation_time_utc).Ticks -eq $Console.StartTime.ToUniversalTime().Ticks -and [int]$Health.frame -ge 1 -and $Health.rendered -eq $true -and $Mode.pid -eq $Console.Id -and $Mode.quick_edit_enabled -eq $false -and [int]$Health.refresh_seconds -eq 30 -and $Console.MainWindowHandle -ne 0 -and $Console.MainWindowTitle -eq 'TREE 2 - WD - LIVE PROGRESS V4')
        }catch{$Healthy=$false}
        if($Healthy){break}
    }while([datetime]::UtcNow -lt $Deadline)
    if(-not $Healthy){throw 'New console did not prove visible first frame and own QuickEdit-off; original display preserved'}
    if((Hash $RolePath) -ne $RoleHash -or (Hash $PlanPath) -ne $PlanHash){throw 'Protected role/plan changed during display handoff; inspect without stopping workers'}
    foreach($Item in $Pinned.sources){if((Hash (Join-Path $ProjectRoot $Item.path)) -ne $Item.sha256){throw ('Protected source changed: '+$Item.path)}}
    [IO.File]::Copy((Join-Path $Own 'display_last_frame.txt'),(Join-Path $Evidence 'first_visible_frame.txt'),$false)
    $Owner.window_handle=$Console.MainWindowHandle.ToInt64();$Owner.window_title=$Console.MainWindowTitle
    $Receipt=@{schema='TREE2_DISPLAY_V4_VISIBLE_HANDOFF_V001';status='V4_VISIBLE_FIRST_FRAME_OLD_GUI_PRESERVED_ROLE_POINTER_UNCHANGED';native_owner=$Owner;display_health=$Health;console_mode=$Mode;old_gui=$Roles.gui;monitor_roles_sha256=$RoleHash;active_plan_sha256=$PlanHash;scientific_sources_unchanged=$true;scientific_workers_touched=$false;publisher_and_collector_unchanged=$true;old_gui_closed=$false;updated_utc=[datetime]::UtcNow.ToString('o')}
    Save-New (Join-Path $Evidence 'receipt.json') $Receipt
    Save-New (Join-Path $Own 'visible_handoff.json') $Receipt
    $Receipt|ConvertTo-Json -Depth 20
}catch{
    Save-New (Join-Path $Evidence 'failure.json') @{status='DISPLAY_HANDOFF_HELD_NO_WORKER_STOP';error=$_.Exception.ToString();known_new_pid=$(if($Console){$Console.Id}else{$null});old_gui_preserved=$true;role_pointer_unchanged=((Hash $RolePath) -eq $RoleHash);at_utc=[datetime]::UtcNow.ToString('o')}
    throw
}finally{if($Console){$Console.Dispose()};$Old.Dispose()}
