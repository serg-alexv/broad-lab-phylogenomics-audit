param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop'
foreach($Name in @('live_progress_v4_6.ps1','monitor_qc_checkm1_overlay_v3.ps1','monitor_checkm1_ram_eta_v1.ps1')){
    $Tokens=$null;$Errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $ProjectRoot ('scripts\'+$Name)),[ref]$Tokens,[ref]$Errors)
    if($Errors.Count){throw ($Name+': '+[string]::Join('; ',@($Errors|ForEach-Object {$_.Message})))}
}
function Read-MonitorSharedJson([string]$Path){$S=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));try{$R=[IO.StreamReader]::new($S,[Text.Encoding]::UTF8,$true);try{return ($R.ReadToEnd()|ConvertFrom-Json)}finally{$R.Dispose()}}finally{$S.Dispose()}}
. (Join-Path $ProjectRoot 'scripts\monitor_hash_v4_4.ps1')
. (Join-Path $ProjectRoot 'scripts\monitor_computed_rows_overlay_v4_4.ps1')
. (Join-Path $ProjectRoot 'scripts\monitor_checkm1_ram_eta_v1.ps1')
$Relative='work\monitor_RAM_ETA_fixture_'+[guid]::NewGuid().ToString('N');$Base=Join-Path $ProjectRoot $Relative
[IO.Directory]::CreateDirectory($Base)|Out-Null
function Put([string]$Path,$Value){[IO.Directory]::CreateDirectory((Split-Path -Parent $Path))|Out-Null;[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false));return @{path=$Path.Substring($ProjectRoot.Length+1);sha256=(Get-DisplayFileHashV44 $Path).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $Path).Length}}
$Plan=@{output=$Relative;execution_backend='PRIVATE_RAM_SCRATCH_DURABLE_PER_BIN_AND_BATCH';linux_total_RSS_bytes=2GB};$Ref=@{sha256=('a'*64)}
$Progress=@{done=18;total=919;status='RUNNING';group_rss_bytes=512MB;private_RAM_used_bytes=256MB;combined_memory_bytes=768MB}
$Label=Get-CheckM1MemoryLabelV46 $Progress $Plan
if($Label -notmatch '0.50 GiB.*0.25 GiB.*0.75 GiB'){throw 'RSS/scratch/combined labels differ'}
$Before=Get-CheckM1WarmETA_V46 $ProjectRoot $Plan $Ref $Progress $true
if($null -ne $Before.remaining_seconds){throw 'ETA before a complete new RAM batch'}
$Cold=Join-Path $Base 'batch_000'
$null=Put (Join-Path $Cold 'COMMITTED.json') @{status='CHECKM1_BATCH_MEASURED_VALIDATED';original_method_plan_sha256=('b'*64);accessions=@('OLD');rows=@(@{accession='OLD'})}
if($null -ne (Get-CheckM1WarmETA_V46 $ProjectRoot $Plan $Ref $Progress $true).remaining_seconds){throw 'Reused cold pilot incorrectly calibrated'}
$Warm=Join-Path $Base 'batch_001';$Names=@('GCF_000000001.1','GCF_000000002.1')
$null=Put (Join-Path $Warm 'once_claim.json') @{method_plan_sha256=$Ref.sha256;accessions=$Names;started_utc='2026-01-01T00:00:00Z'}
$Bindings=@();foreach($Unit in @('unit_analyze','unit_qa')){$Bindings+=Put (Join-Path $Warm ($Unit+'\execution.json')) @{actual_exit_code=0;actual_child_waited_and_reaped=$true;group_closed=$true}}
$Commit=@{status='CHECKM1_BATCH_MEASURED_VALIDATED';original_method_plan_sha256=$Ref.sha256;accessions=$Names;rows=@($Names|ForEach-Object {@{accession=$_}});artifacts=$Bindings;ended_utc='2026-01-01T00:02:00Z'}
$null=Put (Join-Path $Warm 'COMMITTED.json') $Commit
$Progress.done=20;$Progress.total=30
$After=Get-CheckM1WarmETA_V46 $ProjectRoot $Plan $Ref $Progress $true
if($After.samples -ne 1 -or $After.remaining_seconds -ne 600 -or -not $After.finish_msk){throw ('Full new-batch calibration failed: '+($After|ConvertTo-Json -Depth 4))}
$Stopped=Get-CheckM1WarmETA_V46 $ProjectRoot $Plan $Ref $Progress $false
if($Stopped.finish_msk){throw 'Stopped owner received a running finish clock'}
$null=Put (Join-Path $Warm 'unit_qa\execution.json') @{actual_exit_code=1;actual_child_waited_and_reaped=$true;group_closed=$true}
if($null -ne (Get-CheckM1WarmETA_V46 $ProjectRoot $Plan $Ref $Progress $true).remaining_seconds){throw 'Changed/nonzero QA evidence incorrectly calibrated'}
$Report=@{status='PASS_SYNTHETIC_RAM_ETA';RSS_scratch_and_combined_distinct=$true;no_ETA_before_new_completed_RAM_batch=$true;reused_cold_pilot_excluded=$true;bound_analyze_and_QA_actual0_required=$true;sample_limited_remaining_measurement_ETA=$true;inactive_finish_clock_suspended=$true;changed_QA_rejected=$true;scientific_execution=$false;fixture=$Base}
[IO.File]::WriteAllText((Join-Path $Base 'receipt.json'),($Report|ConvertTo-Json),[Text.UTF8Encoding]::new($false));$Report|ConvertTo-Json -Compress
