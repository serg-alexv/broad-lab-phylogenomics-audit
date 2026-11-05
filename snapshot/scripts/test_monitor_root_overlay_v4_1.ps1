param([string]$ProjectRoot='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)}
. (Join-Path $ProjectRoot 'scripts\monitor_root_preparation_overlay_v4_1.ps1')
$Old=@{Category='FAIL';Reason='last worker failed';ProcessingReported=$false;NativeVerified=$false;DeclaredUnit='unit_diamond'}
$Stage=@{status='FAILED';detail='preserve actual timeout and debits'}
$Root=@{Verified=$true;Category='PREPARATION';Reason='actual controller preparing';DispatcherOwner=@{pid=10};CliOwner=@{pid=11}}
$Value=Merge-RootPresentationV41 $Old $Root $Stage $false
if($Value.Category -ne 'PREPARATION' -or $Value.LastAttemptStatus -ne 'FAILED' -or $Value.ProcessingReported -or $Value.NativeVerified -or -not $Value.ControllerVerified){throw 'Preparation overlay loses failure or fabricates processing'}
if($Old.Category -ne 'FAIL' -or $Stage.status -ne 'FAILED'){throw 'Original stage state mutated'}
if((Merge-RootPresentationV41 $Old @{Verified=$false} $Stage $false).Category -ne 'FAIL'){throw 'Unverified controller overrode prior outcome'}
if((Merge-RootPresentationV41 @{Category='GENOME_PROCESSING';NativeVerified=$true;ProcessingReported=$true} $Root $Stage $true).Category -ne 'GENOME_PROCESSING'){throw 'Controller overlay hid real scientific owner'}
$Root.Category='CLEANUP'
if((Merge-RootPresentationV41 $Old $Root $Stage $false).Category -ne 'CLEANUP'){throw 'Completed CLI teardown misclassified'}
@{status='FIVE_PURE_ROOT_OVERLAY_GROUPS_PASS';count=5;actual_process_or_science_calls=$false}|ConvertTo-Json
