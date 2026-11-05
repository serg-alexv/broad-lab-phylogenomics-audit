param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop'
foreach($Name in @('live_progress_v4_4.ps1','monitor_hash_v4_4.ps1','monitor_phase_classifier_v4_4.ps1','monitor_computed_rows_overlay_v4_4.ps1','monitor_qc_checkm1_overlay_v1.ps1')){
    $Tokens=$null;$Errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $ProjectRoot ('scripts\'+$Name)),[ref]$Tokens,[ref]$Errors)
    if($Errors.Count){throw ($Name+': '+[string]::Join('; ',@($Errors|ForEach-Object {$_.Message})))}
}
. (Join-Path $ProjectRoot 'scripts\monitor_hash_v4_4.ps1')
. (Join-Path $ProjectRoot 'scripts\monitor_phase_classifier_v4_4.ps1')
$Fixture=Join-Path $ProjectRoot ('work\monitor_checkm1_fixture_'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($Fixture)|Out-Null
$File=Join-Path $Fixture 'sha_fixture.txt';[IO.File]::WriteAllText($File,'abc',[Text.UTF8Encoding]::new($false))
if((Get-DisplayFileHashV44 $File).Hash.ToLowerInvariant() -ne 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'){throw 'Direct .NET SHA256 fixture differs'}
$Stage=@{status='RUNNING';method='CHECKM1_1_2_5_LACTOBACILLALES';detail='preflight';updated_utc=[datetime]::UtcNow.ToString('o');genome_processing=$false}
if((Get-WorkPresentationV4 $Stage $true).Category -eq 'GENOME_PROCESSING'){throw 'Preflight falsely called analysis'}
$Stage.detail='analyze'
if((Get-WorkPresentationV4 $Stage $true).Category -eq 'GENOME_PROCESSING'){throw 'Missing analyze report falsely accepted'}
$Stage.genome_processing=$true
if((Get-WorkPresentationV4 $Stage $true).Category -ne 'GENOME_PROCESSING'){throw 'Fresh current analyze report not shown'}
if((Get-WorkPresentationV4 $Stage $false).Category -eq 'GENOME_PROCESSING'){throw 'Unverified owner falsely accepted'}
$Stage.updated_utc=[datetime]::UtcNow.AddMinutes(-3).ToString('o')
if((Get-WorkPresentationV4 $Stage $true).Category -eq 'GENOME_PROCESSING'){throw 'Stale report falsely accepted'}
$Stage.updated_utc=[datetime]::UtcNow.ToString('o');$Stage.detail='qa';$Stage.genome_processing=$false
if((Get-WorkPresentationV4 $Stage $true).Category -ne 'RESULT_VALIDATION'){throw 'QA phase not distinguished'}
$Stage.status='FAILED'
if((Get-WorkPresentationV4 $Stage $true).Category -ne 'FAIL'){throw 'Failure not retained'}
$Receipt=@{status='PASS_DISPLAY_ONLY_CHECKM1_SEMANTICS';direct_dotnet_SHA256=$true;preflight_not_analysis=$true;fresh_analyze_report_and_owner_required=$true;stale_or_unverified_not_analysis=$true;QA_distinct_from_search=$true;failure_retained=$true;fixture=$Fixture;scientific_execution=$false}
[IO.File]::WriteAllText((Join-Path $Fixture 'receipt.json'),($Receipt|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$Receipt|ConvertTo-Json -Compress
