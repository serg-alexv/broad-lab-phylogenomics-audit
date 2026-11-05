# Presentation only. Reads small current-run JSON; never reads genomes/models/DBs.
function Resolve-DisplayPathV42([string]$Root,[string]$Value){
    $Linux='/mnt/'+$Root.Substring(0,1).ToLowerInvariant()+'/'+$Root.Substring(3).Replace('\','/')
    if($Value.StartsWith($Linux+'/',[StringComparison]::OrdinalIgnoreCase)){$Value=Join-Path $Root $Value.Substring($Linux.Length+1)}
    elseif(-not [IO.Path]::IsPathRooted($Value)){$Value=Join-Path $Root $Value}
    $Resolved=[IO.Path]::GetFullPath($Value)
    if(-not $Resolved.StartsWith($Root.TrimEnd('\','/')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Display path outside project'}
    return $Resolved
}
function Read-SmallDisplayJsonV42([string]$Path){
    $Item=Get-Item -LiteralPath $Path -ErrorAction Stop
    if($Item.Length -gt 262144 -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Not a small regular display JSON'}
    return Read-MonitorSharedJson $Path
}
function Read-BoundDisplayJsonV42([string]$Root,$Row){
    $Path=Resolve-DisplayPathV42 $Root ([string]$Row.path)
    $Item=Get-Item -LiteralPath $Path -ErrorAction Stop
    if([string]$Row.sha256 -notmatch '^[0-9a-fA-F]{64}$' -or $Item.Length -ne $Row.bytes -or $Item.Length -gt 262144){throw 'Small metadata artifact binding differs'}
    if((Get-DisplayFileHashV44 -LiteralPath $Path -Algorithm SHA256).Hash -ne [string]$Row.sha256){throw 'Small metadata SHA256 differs'}
    return Read-SmallDisplayJsonV42 $Path
}
function Test-ClosedDisplayUnitV42($Unit){
    return ($Unit.status -eq 'UNIT_EXIT0_GROUP_CLOSED' -and ($Unit.exit_code -is [int] -or $Unit.exit_code -is [long]) -and
        $Unit.exit_code -eq 0 -and $Unit.owned_group_empty -eq $true -and $null -ne $Unit.remaining_owned_processes -and @($Unit.remaining_owned_processes).Count -eq 0)
}
function Get-ComputedRowsPresentationV42([string]$Root,$Stage,$Presentation){
    $Sub=$Stage.current_substep
    if(-not $Sub -or -not $Stage.windows_launch_token -or $Sub.windows_launch_token -ne $Stage.windows_launch_token -or -not $Sub.run_directory){return $null}
    $Run=Resolve-DisplayPathV42 $Root ([string]$Sub.run_directory)
    if($Run -notlike (Join-Path $Root 'analysis\checkm2_campaign_index8_v002\*\runs\*')){return $null}
    $Binding=Read-SmallDisplayJsonV42 (Join-Path $Run 'binding.json')
    if($Binding.immutable_request.token -ne $Stage.windows_launch_token -or $Binding.plan._sha -ne $Sub.input_plan_sha256){throw 'Current run/token/plan binding differs'}
    $Plan=Read-BoundDisplayJsonV42 $Root $Binding.plan._row
    $Accessions=@($Plan.accessions)
    if($Accessions.Count -ne [int]$Stage.total -or $Accessions.Count -gt 20){throw 'Current cohort count differs'}
    $Rows=@();$Warnings=@()
    foreach($Accession in $Accessions){
        if($Accession -notmatch '^GC[AF]_\d{9}\.\d+$'){throw 'Unexpected current cohort accession'}
        $CommitPath=Join-Path $Run ('rows\'+$Accession+'\commit.json')
        if(-not [IO.File]::Exists($CommitPath)){continue}
        try{
            $Commit=Read-SmallDisplayJsonV42 $CommitPath
            if($Commit.status -ne 'P20_FRESH_PHASE_SEPARATED_ROW_VALIDATED_PENDING_NATIVE_CLOSURE' -or $Commit.accession -ne $Accession -or
                $Commit.native_launch_token -ne $Stage.windows_launch_token -or $Commit.input_plan_sha256 -ne $Sub.input_plan_sha256){throw 'Own-row commit epoch differs'}
            foreach($Name in @('unit_annotation','unit_diamond','unit_saved_search_validation','unit_resume','unit_feature_validation')){
                if(-not (Test-ClosedDisplayUnitV42 (Read-BoundDisplayJsonV42 $Root $Commit.unit_executions.$Name))){throw ('Own unit not actual0/group closed: '+$Name)}
            }
            foreach($Name in @('annotation_commit','diamond_commit','prediction_commit','manifest')){Read-BoundDisplayJsonV42 $Root $Commit.$Name | Out-Null}
            $Feature=Read-BoundDisplayJsonV42 $Root $Commit.feature_validation
            if($Feature.status -ne 'P20_FEATURES_PASS_PENDING_NATIVE_CLOSURE' -or $Feature.accession -ne $Accession -or
                $Feature.row_count -ne 1 -or $Feature.finite_domain_features -ne 21241 -or $Feature.exact_FAA_metadata_features -ne 22 -or
                $Feature.independently_recomputed_membership_features -ne 1220 -or $Feature.membership_mismatches -ne 0){throw 'Own feature checks incomplete'}
            $Rows+=@{accession=[string]$Accession;commit_sha256=(Get-DisplayFileHashV44 -LiteralPath $CommitPath -Algorithm SHA256).Hash.ToLowerInvariant();
                completeness=$Feature.Completeness;contamination=$Feature.Contamination;status='COMPUTED_EXTERNAL_ACCEPTANCE_PENDING'}
        }catch{$Warnings+=([string]$Accession+': '+$_.Exception.Message)}
    }
    $ReferenceActive=$false;$ReferenceAccession=$null
    $Control=Join-Path $Run 'controls\REFERENCE_CONTROL'
    if($Rows.Count -gt 0 -and $Presentation.NativeVerified -and $Presentation.FreshTelemetry -and $Presentation.LaunchTokenMatches -and
        $Presentation.OwnScientificChildReported -and $Presentation.SourceStatus -eq 'RUNNING' -and -not $Stage.optional_telemetry_stale_or_unavailable -and
        -not [IO.File]::Exists((Join-Path $Run 'reference_control_commit.json')) -and
        (Resolve-DisplayPathV42 $Root ([string]$Sub.active_unit_directory)) -eq $Control -and $Sub.declared_unit -match '^unit_(diamond|saved_search_validation|reference_comparison)$'){
        $Command=Read-SmallDisplayJsonV42 (Join-Path $Control ($Sub.declared_unit+'\command.json'))
        $Arguments=@($Command.command);$Index=[array]::IndexOf($Arguments,'--request');$HashIndex=[array]::IndexOf($Arguments,'--request-sha256')
        if($Index -ge 0 -and $HashIndex -ge 0 -and $Index+1 -lt $Arguments.Count -and $HashIndex+1 -lt $Arguments.Count){
            $RequestPath=Resolve-DisplayPathV42 $Root ([string]$Arguments[$Index+1])
            if($RequestPath -eq (Join-Path $Control 'control_request.json') -and (Get-DisplayFileHashV44 -LiteralPath $RequestPath -Algorithm SHA256).Hash -eq $Arguments[$HashIndex+1]){
                $Request=Read-SmallDisplayJsonV42 $RequestPath
                if($Request.role -eq 'SEARCH_ONLY_CONTROL' -and $Request.input_plan.sha256 -eq $Sub.input_plan_sha256 -and $Request.accession -eq $Plan.search_only_control.accession){
                    $ReferenceActive=$true;$ReferenceAccession=[string]$Request.accession
                }
            }
        }
    }
    return @{Computed=$Rows.Count;Total=$Accessions.Count;Rows=$Rows;ReferenceActive=$ReferenceActive;ReferenceAccession=$ReferenceAccession;
        LaunchToken=[string]$Stage.windows_launch_token;InputPlanSha256=[string]$Sub.input_plan_sha256;Warnings=$Warnings;
        Status='COMPUTED_METHOD_ROWS_EXTERNAL_ACCEPTANCE_PENDING';GlobalAcceptedCountChanged=$false;PanelAcceptance='NOT_GRANTED'}
}
