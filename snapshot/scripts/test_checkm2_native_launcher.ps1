$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source=Join-Path $PSScriptRoot 'launch_checkm2_pilot.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors){throw ($errors | Out-String)}
$function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Save-Receipt'},$true)
if(-not $function){throw 'Atomic receipt writer was not found'}
Invoke-Expression $function.Extent.Text
$token=[guid]::NewGuid().ToString('N')
$fixture=Join-Path $projectRoot 'work/checkm2_native_launcher_selftest'
[IO.Directory]::CreateDirectory($fixture) | Out-Null
$path=Join-Path $fixture 'receipt.json'
Save-Receipt $path @{value=1;fixture_only=$true}
Save-Receipt $path @{value=2;fixture_only=$true}
if((Get-Content -LiteralPath $path -Raw | ConvertFrom-Json).value -ne 2){throw 'Existing receipt replacement failed'}
$runtimeFunction=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Runtime-Closed'},$true)
Invoke-Expression $runtimeFunction.Extent.Text
$MountSmoke=$true
$actualProjectRoot=$projectRoot
try{
 $projectRoot=Join-Path $fixture 'path_only_ro'
 [IO.Directory]::CreateDirectory((Join-Path $projectRoot 'state')) | Out-Null
 [IO.File]::WriteAllText((Join-Path $projectRoot 'state/checkm2_install.lock'),'0')
 $controls=@{GLIBC_TUNABLES='fixture-only-never-applied'}
 $ro=@{status='PASS_READONLY_RUNTIME_PERSISTENCE';all_smoke_children_closed=$true;image_seal=@{sha256='image-fixture';filesystem_uuid='uuid-fixture'};installed_manifest_sha256='installed-fixture';models_manifest_sha256='models-fixture';runtime_environment_overrides=$controls}
 Save-Receipt (Join-Path $projectRoot 'ro.json') $ro
 $ownerTime=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToFileTimeUtc()
 $environment=@{status='COMPLETE';host_registry_unchanged=$true;storage='PROJECT_OWNED_EXT4_IMAGE';read_only_validation_path='ro.json';runtime_environment_overrides=$controls;native_process_identity=@{pid=$PID;windows_creation_filetime_100ns=$ownerTime}}
 Save-Receipt (Join-Path $projectRoot 'environment.json') $environment
 $ready=@{status='READY_FOR_RESOURCE_PILOT';import_smoke_passed=$true;model_load_smoke_passed=$true;heavy_linux_children_closed=$true;requires_private_image_mount=$true;environment_receipt_path='environment.json';environment_receipt_sha256=(Get-FileHash -LiteralPath (Join-Path $projectRoot 'environment.json') -Algorithm SHA256).Hash;runtime_image=@{sha256='image-fixture';filesystem_uuid='uuid-fixture'};installed_manifest_sha256='installed-fixture';models_manifest_sha256='models-fixture';runtime_environment_overrides=$controls}
 if(Runtime-Closed $ready){throw 'Live exact installer identity must block dispatch'}
 $environment.native_process_identity.windows_creation_filetime_100ns=$ownerTime-1
 Save-Receipt (Join-Path $projectRoot 'environment.json') $environment
 $ready.environment_receipt_sha256=(Get-FileHash -LiteralPath (Join-Path $projectRoot 'environment.json') -Algorithm SHA256).Hash
 if(-not (Runtime-Closed $ready)){throw 'Path-only RO producer schema failed valid metadata fixture'}
 $ro.image_seal.sha256='wrong-image-fixture'
 Save-Receipt (Join-Path $projectRoot 'ro.json') $ro
 if(Runtime-Closed $ready){throw 'RO image fingerprint mismatch was accepted'}
}finally{$projectRoot=$actualProjectRoot}
$digest=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
if($digest -notmatch '^[0-9a-f]{64}$'){throw 'Native SHA256 normalization failed'}
$exitScript=Join-Path $fixture 'exit7.ps1'
[IO.File]::WriteAllText($exitScript,'exit 7')
$child=Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$exitScript+'"')) -WindowStyle Hidden -PassThru
$ownedHandle=$child.Handle
if(-not $child.WaitForExit(10000)){throw 'Owned exit-code fixture did not close'}
$child.Refresh()
if($child.ExitCode -ne 7){throw 'Native exit-code handle fixture failed'}
$receipt=@{status='PASS';fixture_only=$true;no_scientific_worker_started=$true;owned_exit7_fixture_closed=$true;created_utc=(Get-Date).ToUniversalTime().ToString('o');powershell_version=$PSVersionTable.PSVersion.ToString();source_sha256=$digest;checks=@('Native parser accepts launcher','Actual Save-Receipt creates and replaces an existing fixture atomically','Native request hash is lowercase SHA256','Live exact installer creation identity blocks dispatch','Path-only RO validation producer schema is accepted with closed identity and unlocked fixture','RO image fingerprint mismatch blocks dispatch','Held native process handle retains actual nonzero exit code after timed wait')}
Save-Receipt (Join-Path $projectRoot 'evidence/checkm2_pilot/native_launcher_selftest.json') $receipt
$receipt | ConvertTo-Json -Compress
