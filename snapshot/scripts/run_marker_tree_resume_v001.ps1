$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$linuxRoot='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
$birth=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
Set-Location -LiteralPath $projectRoot
function Hash([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $projectRoot $p)).Hash.ToLowerInvariant()}
function Put([string]$p,$v){$target=Join-Path $projectRoot $p;$null=[IO.Directory]::CreateDirectory((Split-Path -Parent $target));$temp=$target+'.'+[Guid]::NewGuid().ToString('N')+'.partial';[IO.File]::WriteAllText($temp,($v|ConvertTo-Json -Depth 40),[Text.UTF8Encoding]::new($false));if(Test-Path -LiteralPath $target){[IO.File]::Replace($temp,$target,$null)}else{[IO.File]::Move($temp,$target)}}
function Base([string]$status,[string]$script,[int]$seconds){@{status=$status;script_sha256=(Hash $script);guard_script_sha256=(Hash 'scripts/marker_pilot_compute_v001.py');cpu=2;max_rss_bytes=268435456;linux_available_stop_bytes=1342177280;unit_timeout_seconds=$seconds;scope='EXPLORATORY_MARKERS_ONLY_NOT_PRODUCTION_ACCEPTANCE';native_pid=$PID;native_creation_utc=$birth}}
function RunLinux([string]$script,[string[]]$arguments){& wsl.exe -d Ubuntu --cd $linuxRoot --exec /usr/bin/python3 -B $script @arguments --native-pid $PID --native-creation-utc $birth;if($LASTEXITCODE -ne 0){throw "Scientific phase $script actual WSL exit $LASTEXITCODE"}}
$phase='resource-bounded native IQ-TREE checkpoint recovery'
try{
 Put 'work/marker_tree_resume_v001/native_registration.json' @{pid=$PID;creation_time_utc=$birth;windows_creation_filetime_100ns=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToFileTimeUtc();role='REAL_EXPLORATORY_TREE_CHECKPOINT_RESUME';script_sha256=(Hash 'scripts/run_marker_tree_resume_v001.ps1')}
 $a=Base 'ROOT_ADMITTED_EXPLORATORY_TEN_TAXON_TREE' 'scripts/marker_pilot_tree_v001.py' 600
 $a.max_rss_bytes=402653184
 $a.resource_decision='IQ-TREE reported minimum198.03MB;256MiB summed wrappers+binary stop with3.02GB available was a local guard stop, not physicalOOM. Raise ONLY this pilot tree to384MiB; retain1CPU and1.25GiB minimumavailable. No global settings changed.'
 $a.alignment_sha256=Hash 'analysis/marker_discovery/pilot10_recovered_v001/concat_v001/concatenated.faa';$a.tools=@{iqtree=@{path='/root/miniconda3/envs/phylogeny/bin/iqtree3';sha256='7d2cf1ccc5a02197e8910702314d4fcd6ea5ea8d9c8062e5fa0bdfbe38c26c8f'}}
 Put 'work/marker_tree_resume_v001/tree_admission.json' $a
 RunLinux 'scripts/marker_pilot_tree_v001.py' @('--input-directory','analysis/marker_discovery/pilot10_recovered_v001/concat_v001','--admission','work/marker_tree_resume_v001/tree_admission.json','--output','analysis/marker_discovery/pilot10_recovered_v001/tree_v001')
 Put 'work/marker_tree_resume_v001/result.json' @{status='EXPLORATORY_TREE_COMPUTED_PENDING_NATIVE_PARENT_CLOSURE';actual_wsl_exit=0;native_pid=$PID;native_creation_utc=$birth;production_acceptance=$false;completed_utc=[DateTime]::UtcNow.ToString('o')}
 exit 0
}catch{Put 'work/marker_tree_resume_v001/failure.json' @{phase=$phase;error=$_.Exception.Message;all_unfinished_states='UNKNOWN';native_pid=$PID;native_creation_utc=$birth;failed_utc=[DateTime]::UtcNow.ToString('o')};Write-Error $_ -ErrorAction Continue;exit 2}
