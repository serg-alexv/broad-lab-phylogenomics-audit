$ErrorActionPreference='Stop'
$Project=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $Project 'scripts\monitor_computed_rows_overlay_v4_2.ps1')
function Read-MonitorSharedJson($Path){Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json}
$Work=[IO.Path]::GetFullPath((Join-Path $Project 'work'))
$Toy=Join-Path $Work ('monitor_v42_toy_'+[guid]::NewGuid().ToString('N'))
$Run=Join-Path $Toy 'analysis\checkm2_campaign_index8_v002\toy\runs\test'
[IO.Directory]::CreateDirectory($Run)|Out-Null
function Put($Path,$Value){[IO.Directory]::CreateDirectory((Split-Path -Parent $Path))|Out-Null;[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))}
function Ref($Path){@{path=$Path.Substring($Toy.Length+1);sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $Path).Length}}
try{
 $Acc='GCF_000000001.1';$RefAcc='GCF_000000002.1';$Token='synthetic-token'
 $PlanPath=Join-Path $Toy 'metadata\plan.json';Put $PlanPath @{accessions=@($Acc);search_only_control=@{accession=$RefAcc}};$PlanRef=Ref $PlanPath
 Put (Join-Path $Run 'binding.json') @{immutable_request=@{token=$Token};plan=@{_sha=$PlanRef.sha256;_row=$PlanRef}}
 $Units=@{}
 foreach($Name in @('unit_annotation','unit_diamond','unit_saved_search_validation','unit_resume','unit_feature_validation')){
  $Path=Join-Path $Run ('rows\'+$Acc+'\'+$Name+'\execution.json');Put $Path @{status='UNIT_EXIT0_GROUP_CLOSED';exit_code=0;owned_group_empty=$true;remaining_owned_processes=@()};$Units[$Name]=Ref $Path
 }
 $FeaturePath=Join-Path $Run ('rows\'+$Acc+'\feature_validation.json')
 Put $FeaturePath @{status='P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE';accession=$Acc;row_count=1;finite_domain_features=21241;exact_FAA_metadata_features=22;independently_recomputed_membership_features=1220;membership_mismatches=0;Completeness=94.62;Contamination=0.06}
 $Other=Join-Path $Run 'metadata_only.json';Put $Other @{}
 $Commit=@{status='P20_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE';accession=$Acc;native_launch_token=$Token;input_plan_sha256=$PlanRef.sha256;unit_executions=$Units;feature_validation=(Ref $FeaturePath);annotation_commit=(Ref $Other);diamond_commit=(Ref $Other);prediction_commit=(Ref $Other);manifest=(Ref $Other)}
 $CommitPath=Join-Path $Run ('rows\'+$Acc+'\commit.json');Put $CommitPath $Commit
 $Control=Join-Path $Run 'controls\REFERENCE_CONTROL';$RequestPath=Join-Path $Control 'control_request.json'
 Put $RequestPath @{role='SEARCH_ONLY_CONTROL';accession=$RefAcc;input_plan=$PlanRef}
 Put (Join-Path $Control 'unit_diamond\command.json') @{command=@('synthetic-binary','--request',$RequestPath,'--request-sha256',(Ref $RequestPath).sha256)}
 $Stage=[pscustomobject]@{windows_launch_token=$Token;total=1;optional_telemetry_stale_or_unavailable=$false;current_substep=[pscustomobject]@{windows_launch_token=$Token;run_directory=$Run;input_plan_sha256=$PlanRef.sha256;active_unit_directory=$Control;declared_unit='unit_diamond'}}
 $Presentation=@{NativeVerified=$true;FreshTelemetry=$true;LaunchTokenMatches=$true;OwnScientificChildReported=$true;SourceStatus='RUNNING'}
 $View=Get-ComputedRowsPresentationV42 $Toy $Stage $Presentation
 if($View.Computed -ne 1 -or -not $View.ReferenceActive -or $View.GlobalAcceptedCountChanged){throw 'Computed/reference positive fixture failed'}
 $Presentation.NativeVerified=$false;$View=Get-ComputedRowsPresentationV42 $Toy $Stage $Presentation
 if($View.ReferenceActive -or $View.Computed -ne 1){throw 'PID-independent reference classification rejected incorrectly'}
 $Presentation.NativeVerified=$true
 $Closed=[pscustomobject]@{status='UNIT_EXIT0_GROUP_CLOSED';exit_code=$false;owned_group_empty=$true;remaining_owned_processes=@()}
 if(Test-ClosedDisplayUnitV42 $Closed){throw 'False became observed integer0'}
 Put (Join-Path $Run 'reference_control_commit.json') @{};$View=Get-ComputedRowsPresentationV42 $Toy $Stage $Presentation
 if($View.ReferenceActive -or $View.Computed -ne 1){throw 'Completed reference still active'}
 $Stage.current_substep.windows_launch_token='other-token'
 if($null -ne (Get-ComputedRowsPresentationV42 $Toy $Stage $Presentation)){throw 'Wrong epoch accepted'}
 $Stage.current_substep.windows_launch_token=$Token
 Put $FeaturePath @{wrong='changed'};$View=Get-ComputedRowsPresentationV42 $Toy $Stage $Presentation
 if($View.Computed -ne 0 -or $View.Warnings.Count -ne 1){throw 'Changed feature binding accepted'}
 'PASS: 6 display-only synthetic cases; no science/runtime/real data'
}finally{
 $Resolved=[IO.Path]::GetFullPath($Toy)
 if(-not $Resolved.StartsWith($Work+'\',[StringComparison]::OrdinalIgnoreCase) -or $Resolved -eq $Work){throw 'Unsafe toy cleanup target'}
 Remove-Item -LiteralPath $Resolved -Recurse -Force
}
