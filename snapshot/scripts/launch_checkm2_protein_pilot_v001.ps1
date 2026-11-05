param([switch]$WaitForReady,[string]$ResumeFrom,[switch]$MountSmoke,[ValidateRange(1,7200)][int]$ReadinessWaitSeconds=5400)
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if($env:COMPUTERNAME -ne 'WD'){throw 'WD-only launcher'}
$lockPath=Join-Path $projectRoot 'state\checkm2_pilot_launcher.lock'
try{$lock=[System.IO.File]::Open($lockPath,[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)}catch{throw 'Another pilot launcher owns the OS lock'}
$token=[guid]::NewGuid().ToString('N')
$started=(Get-Date).ToUniversalTime().ToString('o')
$nativeIdentity=@{pid=$PID;creation_time_utc=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o');token=$token;started_utc=$started}
function Save-Receipt([string]$path,$value){
 $tmp=$path+'.'+$token+'.tmp'
 [System.IO.File]::WriteAllText($tmp,($value | ConvertTo-Json -Depth 12),[System.Text.UTF8Encoding]::new($false))
 if([System.IO.File]::Exists($path)){[System.IO.File]::Replace($tmp,$path,[NullString]::Value)}else{[System.IO.File]::Move($tmp,$path)}
}
Save-Receipt (Join-Path $projectRoot 'state\checkm2_protein_pilot_v001_waiter.json') $nativeIdentity
function Runtime-Closed($ready){
 if(-not $ready -or $ready.status -ne 'READY_FOR_RESOURCE_PILOT' -or $ready.import_smoke_passed -ne $true -or $ready.model_load_smoke_passed -ne $true -or $ready.heavy_linux_children_closed -ne $true -or $ready.requires_private_image_mount -ne $true){return $false}
 if(-not $MountSmoke){
  $forwardPath=Join-Path $projectRoot 'state/checkm2_forward_ready.json'
  if(-not (Test-Path -LiteralPath $forwardPath)){return $false}
  $forward=Get-Content -LiteralPath $forwardPath -Raw | ConvertFrom-Json
  if($forward.status -ne 'FORWARD_DIAGNOSTIC_PASS_RESOURCE_ONLY' -or -not $forward.effective_runtime_manifest_path -or -not $forward.effective_runtime_manifest_sha256){return $false}
 }
 if(-not $ready.environment_receipt_path){return $false}
 $receiptPath=[System.IO.Path]::GetFullPath((Join-Path $projectRoot $ready.environment_receipt_path))
 if(-not $receiptPath.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Environment receipt escapes project'}
 if(-not (Test-Path -LiteralPath $receiptPath)){return $false}
 if((Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash -ne $ready.environment_receipt_sha256){throw 'Environment receipt hash differs from READY'}
 $receipt=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
 if($receipt.status -ne 'COMPLETE' -or $receipt.host_registry_unchanged -ne $true -or $receipt.storage -ne 'PROJECT_OWNED_EXT4_IMAGE'){return $false}
 $ro=$receipt.read_only_validation
 if(-not $ro -and $receipt.read_only_validation_path){
  $roPath=[IO.Path]::GetFullPath((Join-Path $projectRoot $receipt.read_only_validation_path))
  if(-not $roPath.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Read-only validation path escapes project'}
  if(-not (Test-Path -LiteralPath $roPath)){return $false}
  $ro=Get-Content -LiteralPath $roPath -Raw | ConvertFrom-Json
 }
 if(-not $ro -or $ro.status -ne 'PASS_READONLY_RUNTIME_PERSISTENCE' -or $ro.all_smoke_children_closed -ne $true){return $false}
 if($ro.image_seal.sha256 -ne $ready.runtime_image.sha256 -or $ro.image_seal.filesystem_uuid -ne $ready.runtime_image.filesystem_uuid -or $ro.installed_manifest_sha256 -ne $ready.installed_manifest_sha256 -or $ro.models_manifest_sha256 -ne $ready.models_manifest_sha256){return $false}
 if(($ro.runtime_environment_overrides | ConvertTo-Json -Compress) -cne ($ready.runtime_environment_overrides | ConvertTo-Json -Compress)){return $false}
 if(($receipt.runtime_environment_overrides | ConvertTo-Json -Compress) -cne ($ready.runtime_environment_overrides | ConvertTo-Json -Compress)){return $false}
 $owner=$receipt.native_process_identity
 if(-not $owner.pid -or -not $owner.windows_creation_filetime_100ns){return $false}
 $oldProcess=Get-Process -Id $owner.pid -ErrorAction SilentlyContinue
 if($oldProcess -and $oldProcess.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [int64]$owner.windows_creation_filetime_100ns){return $false}
 # Test the installer's actual byte lock; readable/stale lock-file bytes are insufficient.
 $probe=$null
 try{
  $probe=[System.IO.File]::Open((Join-Path $projectRoot 'state\checkm2_install.lock'),[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::ReadWrite)
  $probe.Lock(0,1);$probe.Unlock(0,1)
 }catch{return $false}finally{if($probe){$probe.Close()}}
 return $true
}
function Read-BoundProjectJson([string]$relative,[string]$expected){
 $target=[IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
 if(-not $target.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Bound diagnostic path escapes project'}
 if(-not (Test-Path -LiteralPath $target)){throw 'Bound diagnostic file missing'}
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $expected){throw 'Bound diagnostic SHA256 differs'}
 return (Get-Content -LiteralPath $target -Raw | ConvertFrom-Json)
}
function Forward-Closed($ready,[string]$readyPath){
 $path=Join-Path $projectRoot 'state/checkm2_forward_ready.json'
 if(-not (Test-Path -LiteralPath $path)){return $false}
 $forward=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
 if($forward.status -ne 'FORWARD_DIAGNOSTIC_PASS_RESOURCE_ONLY' -or $forward.production_acceptance -ne $false -or $forward.candidate_ready_sha256 -ne (Get-FileHash -LiteralPath $readyPath -Algorithm SHA256).Hash -or $forward.image_sha256 -ne $ready.runtime_image.sha256 -or $forward.models_manifest_sha256 -ne $ready.models_manifest_sha256){return $false}
 $effective=Read-BoundProjectJson $forward.effective_runtime_manifest_path $forward.effective_runtime_manifest_sha256
 if($effective.status -ne 'MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY' -or $effective.schema -ne 'TREE2_EFFECTIVE_RUNTIME_VALIDATED_V1' -or $effective.effective_import_provenance_and_native_runtime_tested -ne $true -or $effective.overlay.effective_version -ne '1.6.1' -or $effective.production_acceptance -ne 'NOT_GRANTED'){return $false}
 if(($effective.required_runtime_environment | ConvertTo-Json -Compress) -cne ($forward.runtime_environment_overrides | ConvertTo-Json -Compress)){return $false}
 $execution=Read-BoundProjectJson $forward.receipt_path $forward.receipt_sha256
 if($execution.status -ne 'MATCHING_RUNTIME_CONTROLS_PASS_RESOURCE_ONLY' -or $execution.host_registry_unchanged -ne $true -or $execution.inside_result.all_owned_smoke_groups_closed -ne $true -or $execution.production_acceptance -ne $false){return $false}
 $closure=Read-BoundProjectJson $forward.closure_proof_path $forward.closure_proof_sha256
 if($closure.status -ne 'CLEAN_UNMOUNT_AND_LOOP_DETACH' -or $closure.readonly -ne $true -or @($closure.errors).Count){return $false}
 $owner=$forward.native_owner
 if(-not $owner.pid -or -not $owner.windows_creation_filetime_100ns){return $false}
 $process=Get-Process -Id $owner.pid -ErrorAction SilentlyContinue
 if($process -and $process.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [int64]$owner.windows_creation_filetime_100ns){return $false}
 return $true
}
function Read-BoundProjectJsonSource([string]$relative,[string]$expected){
 $target=[IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
 if(-not $target.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Strategy source path escapes project'}
 if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $expected){throw 'Strategy source SHA differs'}
 return $true
}
try{
 $priorPath=Join-Path $projectRoot 'state\launch_checkm2_protein_pilot_v001.json'
 if(Test-Path -LiteralPath $priorPath){
  $prior=Get-Content -LiteralPath $priorPath -Raw | ConvertFrom-Json
  $priorProcess=Get-Process -Id $prior.pid -ErrorAction SilentlyContinue
  if($priorProcess -and $priorProcess.StartTime.ToUniversalTime().Ticks -eq ([datetime]$prior.creation_time_utc).ToUniversalTime().Ticks){throw 'Previous native WSL pilot/namespace worker is still active; no new launch'}
  if($prior.token -notmatch '^[0-9a-f]{32}$'){throw 'Prior launch identity requires review'}
  $priorEnvelope=Join-Path $projectRoot ('evidence\checkm2_protein_pilot_v001\namespace_runs\'+$prior.token+'.json')
  if(-not (Test-Path -LiteralPath $priorEnvelope)){throw 'Prior namespace closure is unproven; no relaunch'}
  $priorResult=Get-Content -LiteralPath $priorEnvelope -Raw | ConvertFrom-Json
  if($priorResult.status -ne 'NAMESPACE_CLOSED_AND_VERIFIED' -and $priorResult.helper_started -ne $false){throw 'Prior helper/mount closure is unproven; no relaunch'}
 }
 $readyPath=Join-Path $projectRoot 'state\checkm2_runtime_ready.json'
 $readinessDeadline=[datetime]::UtcNow.AddSeconds($ReadinessWaitSeconds)
 while($true){
  if((Test-Path (Join-Path $projectRoot 'state\STOP')) -or ((Test-Path (Join-Path $projectRoot 'state\STOP_CHECKM2_PILOT')) -and -not $MountSmoke)){throw 'STOP requested before pilot launch'}
  $ready=$null
  if(Test-Path $readyPath){try{$ready=Get-Content -LiteralPath $readyPath -Raw | ConvertFrom-Json}catch{}}
  if((Runtime-Closed $ready) -and (Forward-Closed $ready $readyPath)){break}
  if(-not $WaitForReady){throw 'Runtime/models/database are not READY; no pilot launched'}
  if([datetime]::UtcNow -ge $readinessDeadline){throw 'Bounded runtime readiness wait expired; no pilot launched'}
  Start-Sleep -Seconds 5
 }
 $linuxRoot='/mnt/'+$projectRoot.Substring(0,1).ToLower()+'/'+$projectRoot.Substring(3).Replace('\','/')
 $ipcRelative='evidence/checkm2_runtime/ipc_capability_proof.json'
 $ipcPath=Join-Path $projectRoot $ipcRelative
 if(-not (Test-Path -LiteralPath $ipcPath)){throw 'Private IPC capability proof is not ready; no prediction launched'}
 $ipc=Get-Content -LiteralPath $ipcPath -Raw | ConvertFrom-Json
 $forward=Get-Content -LiteralPath (Join-Path $projectRoot 'state/checkm2_forward_ready.json') -Raw | ConvertFrom-Json
 if($ipc.status -ne 'PRIVATE_SHORT_IPC_PROVEN' -or $ipc.image_sha256 -ne $ready.runtime_image.sha256 -or $ipc.effective_runtime_manifest_sha256 -ne $forward.effective_runtime_manifest_sha256 -or $ipc.unchanged_effective_bootstrap_sha256 -ne $forward.bootstrap_sha256 -or $ipc.helper_sha256 -ne (Get-FileHash -LiteralPath (Join-Path $projectRoot 'scripts/checkm2_ipc_alias.py') -Algorithm SHA256).Hash -or $ipc.target_bootstrap_sha256 -ne (Get-FileHash -LiteralPath (Join-Path $projectRoot 'scripts/checkm2_ipc_bootstrap.py') -Algorithm SHA256).Hash){throw 'Private IPC proof/source/runtime binding failed; no prediction launched'}
 $strategyPath=Join-Path $projectRoot 'state/checkm2_protein_strategy_ready_v001.json'
 if(-not (Test-Path -LiteralPath $strategyPath)){throw 'HELD: supported-protein strategy admission absent; no worker launched'}
 $strategy=Get-Content -LiteralPath $strategyPath -Raw | ConvertFrom-Json
 if($strategy.schema -ne 'TREE2_SUPPORTED_PROTEIN_STRATEGY_V1' -or $strategy.status -ne 'ROOT_ACCEPTED_FOR_ONE_RESOURCE_PILOT' -or $strategy.biological_dispatch_authorized -ne $true){throw 'HELD: protein strategy not admitted'}
 foreach($pin in $strategy.sources){$null=Read-BoundProjectJsonSource $pin.path $pin.sha256}
 $operation=if($MountSmoke){'MOUNT_SMOKE_ONLY'}else{'PREDICTION'}
 if($MountSmoke -and $ResumeFrom){throw 'Mount smoke does not resume a prediction'}
 $request=@{token=$token;operation=$operation;ready_receipt_path=($linuxRoot+'/state/checkm2_runtime_ready.json');ready_receipt_sha256=(Get-FileHash -LiteralPath $readyPath -Algorithm SHA256).Hash.ToLowerInvariant();ipc_proof_path=($linuxRoot+'/'+$ipcRelative);ipc_proof_sha256=(Get-FileHash -LiteralPath $ipcPath -Algorithm SHA256).Hash.ToLowerInvariant();resume_from=$null;strategy_receipt_path=($linuxRoot+'/state/checkm2_protein_strategy_ready_v001.json');strategy_receipt_sha256=(Get-FileHash -LiteralPath $strategyPath -Algorithm SHA256).Hash.ToLowerInvariant();created_utc=(Get-Date).ToUniversalTime().ToString('o')}
 if($ResumeFrom){throw 'Stock or legacy resume is forbidden for supported-protein v001'}
 if($ResumeFrom){
  $resolved=(Resolve-Path -LiteralPath $ResumeFrom).Path
  if(-not $resolved.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Resume path outside project'}
  $request.resume_from='/mnt/'+$resolved.Substring(0,1).ToLower()+'/'+$resolved.Substring(3).Replace('\','/')
 }
 $requestFolder=Join-Path $projectRoot 'state\checkm2_protein_pilot_v001_launch_requests'
 [IO.Directory]::CreateDirectory($requestFolder) | Out-Null
 Save-Receipt (Join-Path $requestFolder ($token+'.json')) $request
 $pilotArgs=@('-d','Ubuntu','--','/usr/bin/env',('TREE2_CHECKM2_PILOT_LAUNCH_TOKEN='+$token),'/bin/bash',($linuxRoot+'/scripts/checkm2_private_setup_ns.sh'),'outer','run',($linuxRoot+'/scripts/checkm2_protein_image_v001.sh'))
 $stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
 $stdout=Join-Path $projectRoot ('logs\checkm2_protein_pilot_v001_'+$stamp+'.stdout.jsonl')
 $stderr=Join-Path $projectRoot ('logs\checkm2_protein_pilot_v001_'+$stamp+'.stderr.txt')
 $job=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList $pilotArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
 $nativeProcessHandle=$job.Handle
 $launch=@{pid=$job.Id;creation_time_utc=$job.StartTime.ToUniversalTime().ToString('o');token=$token;launcher=$nativeIdentity;script='scripts/checkm2_protein_image_v001.sh';operation=$operation;scientific_prediction_requested=(-not $MountSmoke);ready_receipt_sha256=$request.ready_receipt_sha256;stdout=$stdout;stderr=$stderr;started_utc=(Get-Date).ToUniversalTime().ToString('o')}
 Save-Receipt (Join-Path $projectRoot 'state\launch_checkm2_protein_pilot_v001.json') $launch
 $exited=$job.WaitForExit(3600000)
 if($exited){$job.Refresh()}
 $nativeExitCode=if($exited){$job.ExitCode}else{$null}
 $receipt=@{status=if(-not $exited){'OUTER_WAIT_BOUND_REACHED_CHILD_NOT_CLOSED'}elseif($null -eq $nativeExitCode){'NATIVE_EXIT_CODE_UNAVAILABLE'}elseif($nativeExitCode -eq 0){'CONTROLLER_EXIT0_CHECK_SCIENTIFIC_RECEIPT'}else{'CONTROLLER_STOPPED_OR_FAILED_CHECK_SCIENTIFIC_RECEIPT'};ended_utc=(Get-Date).ToUniversalTime().ToString('o');native_windows_launch=$launch;exit_code=$nativeExitCode;native_child_closed=$exited;outer_wait_limit_seconds=3600;next_action='No automatic resource increase or repeat prediction';production_panel_acceptance='NOT_GRANTED'}
 Save-Receipt (Join-Path $projectRoot 'state\checkm2_protein_pilot_v001_launcher_exit.json') $receipt
 if(-not $exited){
  $progressPath=Join-Path $projectRoot 'state\checkm2_protein_pilot_v001_progress.json'
  $progress=Get-Content -LiteralPath $progressPath -Raw | ConvertFrom-Json
  $progress.status='INTERRUPTED_BUDGET';$progress.detail='Outer namespace wrapper exceeded3600s; native WSL worker remains active and closure is unproven. No relaunch.';$progress.updated_utc=(Get-Date).ToUniversalTime().ToString('o')
  Save-Receipt $progressPath $progress
  exit 4
 }
 if($null -eq $nativeExitCode){exit 4}
 if($nativeExitCode -ne 0){exit $nativeExitCode}
}finally{$lock.Close()}

