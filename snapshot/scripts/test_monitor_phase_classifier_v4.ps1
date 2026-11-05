[CmdletBinding()]
param([string]$ProjectRoot='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)}
. (Join-Path $ProjectRoot 'scripts\monitor_phase_classifier_v4.ps1')
$Now=[datetime]::UtcNow
function Make-Stage([string]$Detail,[string]$Unit='', [string]$Status='RUNNING'){
    return [pscustomobject]@{status='RUNNING';detail=$Detail;operation='PREDICTION';windows_launch_token='same';updated_utc=$Now.ToString('o');
        current_substep=[pscustomobject]@{status=$Status;detail=$Detail;declared_unit=$Unit;windows_launch_token='same';updated_utc=$Now.ToString('o');worker_pid=123;worker_creation_identity=@{pid=123;creation_ticks=456;boot_id='test-boot'}}}
}
function Expect($Stage,[bool]$Native,[string]$Category){
    $Result=Get-WorkPresentationV4 $Stage $Native $Now
    if($Result.Category -ne $Category){throw ('Expected '+$Category+' got '+$Result.Category+' for '+$Stage.detail)}
}
$Checks=New-Object 'Collections.Generic.List[string]'
Expect (Make-Stage 'Verifying sealed image and mounting runtime read-only; preflight pending' '' 'PREPARING') $true 'PREPARATION'
$Checks.Add('PREDICTION flag and live native do not turn runtime hash/mount into genome processing')
foreach($Unit in @('unit_annotation','unit_diamond','unit_resume','unit_quality')){Expect (Make-Stage $Unit $Unit) $true 'GENOME_PROCESSING'}
$Checks.Add('four declared scientific unit kinds use fresh own-child report plus verified native')
Expect (Make-Stage 'unit_feature_validation' 'unit_feature_validation') $true 'RESULT_VALIDATION'
$Checks.Add('saved-feature validation is distinct from genome processing')
Expect (Make-Stage 'Runtime unmounted; verifying sealed image') $true 'CLEANUP'
$Checks.Add('post-unmount image hash is cleanup')
$Stage=Make-Stage 'unit_diamond' 'unit_diamond';$Stage.current_substep.worker_creation_identity=$null
Expect $Stage $true 'WAIT'
Expect (Make-Stage 'unit_diamond' 'unit_diamond') $false 'WAIT'
$Checks.Add('PID-only and missing scientific child identity do not qualify')
$Stage=Make-Stage 'unit_diamond' 'unit_diamond';$Stage.current_substep.updated_utc=$Now.AddMinutes(-3).ToString('o')
Expect $Stage $true 'WAIT'
$Stage=Make-Stage 'unit_diamond' 'unit_diamond';$Stage.current_substep.windows_launch_token='other'
Expect $Stage $true 'WAIT'
$Checks.Add('stale and mismatched-token reports remain unverified')
$Stage=Make-Stage 'failed unit';$Stage.status='FAILED';Expect $Stage $false 'FAIL'
$Stage=Make-Stage 'waiting at gate';$Stage.status='BLOCKED_RESOURCE';Expect $Stage $false 'BLOCK'
$Checks.Add('fail and block stay visible')
@{status='SEVEN_PURE_PHASE_CLASSIFICATION_GROUPS_PASS';count=$Checks.Count;checks=@($Checks);OS_process_or_science_operations=$false}|ConvertTo-Json -Depth 8
