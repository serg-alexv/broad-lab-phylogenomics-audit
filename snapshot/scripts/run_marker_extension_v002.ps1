$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$linuxRoot='/mnt/c/Users/wheel/Documents/Codex/2026-10-26/referenced-chatgpt-conversation-this-is-an/outputs/TREE2_WD_20261026'
$birth=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
Set-Location -LiteralPath $projectRoot
function Hash([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $projectRoot $p)).Hash.ToLowerInvariant()}
function Put([string]$p,$v){$target=Join-Path $projectRoot $p;$null=[IO.Directory]::CreateDirectory((Split-Path -Parent $target));$temp=$target+'.'+[Guid]::NewGuid().ToString('N')+'.partial';[IO.File]::WriteAllText($temp,($v|ConvertTo-Json -Depth 40),[Text.UTF8Encoding]::new($false));if(Test-Path -LiteralPath $target){[IO.File]::Replace($temp,$target,$null)}else{[IO.File]::Move($temp,$target)}}
function Base([string]$status,[string]$script,[int]$seconds){@{status=$status;script_sha256=(Hash $script);guard_script_sha256=(Hash 'scripts/marker_pilot_compute_v001.py');cpu=2;max_rss_bytes=268435456;linux_available_stop_bytes=1342177280;unit_timeout_seconds=$seconds;scope='EXPLORATORY_MARKERS_ONLY_NOT_PRODUCTION_ACCEPTANCE';native_pid=$PID;native_creation_utc=$birth}}
function RunLinux([string]$script,[string[]]$arguments){& wsl.exe -d Ubuntu --cd $linuxRoot --exec /usr/bin/python3 -B $script @arguments --native-pid $PID --native-creation-utc $birth;if($LASTEXITCODE -ne 0){throw "Scientific phase $script actual WSL exit $LASTEXITCODE"}}
$phase='upstream closure verification'
try{
 $up=Get-Content -LiteralPath 'analysis/marker_discovery/pilot10_recovered_v001/compute/Root_external_closure.json' -Raw|ConvertFrom-Json
 if($up.actual_native_exit_code -ne 0 -or $up.owned_scientific_units_closed -ne $true){throw 'Upstream marker owner has not successfully closed'}
 if((Hash 'scripts/marker_pilot_compute_v001.py') -ne 'b04aeeeb9e8d972b2d38ce1e5b6466913a4adaa1fb49507275ad0aab58a91cad'){throw 'Frozen compute guard changed'}
 if((Hash 'scripts/marker_pilot_hmmsearch_v001.py') -ne '9dfb40f528a948ed342fefcba9c222649876be467abc8b391372aecba7cdbbcf'){throw 'Frozen HMM search driver changed'}
 if((Hash 'scripts/marker_pilot_alignment_sensitivity_v001.py') -ne '28dae05faf39682d0a37969bb6064a52bdd0e62e41f9d467dfd8ab2d108f95f8'){throw 'Frozen sensitivity driver changed'}
 Put 'work/marker_extension_v002/native_registration.json' @{pid=$PID;creation_time_utc=$birth;windows_creation_filetime_100ns=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToFileTimeUtc();role='REAL_MARKER_RECOVERY_ALIGNMENT_SENSITIVITY_AND_PILOT_TREE';script_sha256=(Hash 'scripts/run_marker_extension_v002.ps1');upstream_exit_receipt_sha256=(Hash 'analysis/marker_discovery/pilot10_recovered_v001/compute/Root_external_closure.json')}
 $profiles='analysis/marker_discovery/pilot10_recovered_v001/compute/result.json'
 $phase='reuse genuine closed HMM search; original extension native exit1 preserved'
 $saved=Get-Content -LiteralPath 'analysis/marker_discovery/pilot14_validation_v001/search/result.json' -Raw|ConvertFrom-Json
 if($saved.status -ne 'EXPLORATORY_PILOT14_HMM_SEARCH_COMPLETE'){throw 'No completed HMM search'}
 $execution=$saved.search.execution
 if((Hash $execution.path) -ne $execution.sha256){throw 'HMM execution receipt changed'}
 $e=Get-Content -LiteralPath $execution.path -Raw|ConvertFrom-Json
 if($e.actual_exit_code -ne 0 -or $e.owned_group_empty -ne $true){throw 'HMM search not genuinely successful/closed'}
 foreach($ref in @($saved.search.output,$saved.query_manifest)+@($saved.outputs)){if((Hash $ref.path) -ne $ref.sha256){throw 'Saved HMM result artifact changed'}}
 $w=Get-Content -LiteralPath 'work/marker_extension_v001/hmm_external_wsl_exit.json' -Raw|ConvertFrom-Json
 if($w.actual_wsl_exit -ne 0 -or $w.result_sha256 -ne (Hash 'analysis/marker_discovery/pilot14_validation_v001/search/result.json')){throw 'Prior actual HMM WSL closure changed'}
 Put 'work/marker_extension_v002/hmm_reuse.json' @{status='REUSED_ACTUAL0_CLOSED_HMM_SEARCH';original_phase_wsl_exit=0;original_native_chain_exit=1;source_result_sha256=(Hash 'analysis/marker_discovery/pilot14_validation_v001/search/result.json');no_hmm_search_rerun=$true}
 $phase='careful alignment sensitivity on20 length-stratified loci'
 $a=Base 'ROOT_ADMITTED_EXPLORATORY_ALIGNMENT_SENSITIVITY' 'scripts/marker_pilot_alignment_sensitivity_v001.py' 180
 $a.input_manifest_sha256=Hash 'analysis/marker_discovery/pilot10_recovered_v001/candidate_manifest.json';$a.fast_manifest_sha256=Hash $profiles;$a.table_helper_script_sha256=Hash 'scripts/marker_pilot_hmmsearch_v001.py'
 $a.tools=@{mafft=@{path='/root/miniconda3/envs/phylogeny/bin/mafft';sha256='9e4b9f4cdcf309980bf15a7140099eaa4efb3201585c59d11fc5814ac8820966'}}
 Put 'work/marker_extension_v002/sensitivity_admission.json' $a
 RunLinux 'scripts/marker_pilot_alignment_sensitivity_v001.py' @('--input-manifest','analysis/marker_discovery/pilot10_recovered_v001/candidate_manifest.json','--fast-manifest',$profiles,'--admission','work/marker_extension_v002/sensitivity_admission.json','--output','analysis/marker_discovery/pilot10_recovered_v001/sensitivity')
 $phase='construct checked exploratory concatenation'
 & 'C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/build_marker_pilot_concat_v001.py
 if($LASTEXITCODE -ne 0){throw "Concatenation actual exit $LASTEXITCODE"}
 $phase='exploratory ten-taxon tree'
 $a=Base 'ROOT_ADMITTED_EXPLORATORY_TEN_TAXON_TREE' 'scripts/marker_pilot_tree_v001.py' 600
 $a.alignment_sha256=Hash 'analysis/marker_discovery/pilot10_recovered_v001/concat_v001/concatenated.faa';$a.tools=@{iqtree=@{path='/root/miniconda3/envs/phylogeny/bin/iqtree3';sha256='7d2cf1ccc5a02197e8910702314d4fcd6ea5ea8d9c8062e5fa0bdfbe38c26c8f'}}
 Put 'work/marker_extension_v002/tree_admission.json' $a
 RunLinux 'scripts/marker_pilot_tree_v001.py' @('--input-directory','analysis/marker_discovery/pilot10_recovered_v001/concat_v001','--admission','work/marker_extension_v002/tree_admission.json','--output','analysis/marker_discovery/pilot10_recovered_v001/tree_v001')
 Put 'work/marker_extension_v002/result.json' @{status='EXPLORATORY_MARKER_EXTENSION_COMPUTED_PENDING_NATIVE_PARENT_CLOSURE';actual_phase_exits=0;production_acceptance=$false;native_pid=$PID;native_creation_utc=$birth;completed_utc=[DateTime]::UtcNow.ToString('o')}
 exit 0
}catch{Put 'work/marker_extension_v002/failure.json' @{phase=$phase;error=$_.Exception.Message;all_unfinished_states='UNKNOWN';native_pid=$PID;native_creation_utc=$birth;failed_utc=[DateTime]::UtcNow.ToString('o')};Write-Error $_ -ErrorAction Continue;exit 2}
