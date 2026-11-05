# Display-only classification. No launch, signal, scientific inference or state mutation.
function Get-WorkPresentationV4($Stage,[bool]$NativeVerified,[datetime]$NowUtc=[datetime]::UtcNow) {
    $Sub=$Stage.current_substep
    $OwnerMatches=$true
    if($Sub -and $Stage.windows_launch_token){$OwnerMatches=([string]$Sub.windows_launch_token -eq [string]$Stage.windows_launch_token)}
    $Source=if($Sub -and $OwnerMatches){$Sub}else{$Stage}
    $Detail=[string]$Source.detail
    if(-not $Detail){$Detail=[string]$Stage.detail}
    $Status=([string]$Source.status).ToUpperInvariant()
    $StageStatus=([string]$Stage.status).ToUpperInvariant()
    $Unit=[string]$Source.declared_unit
    $Fresh=$false;$Age=$null
    try{
        $When=[datetimeoffset]::Parse([string]$Source.updated_utc).UtcDateTime
        $Age=[math]::Max(0,($NowUtc-$When).TotalSeconds)
        $Fresh=$Age -le 95
    }catch{}
    $Stale=($Stage.optional_telemetry_stale_or_unavailable -eq $true -or $Source.optional_telemetry_stale_or_unavailable -eq $true)
    $ChildNumber=0;$CreationTicks=[long]0
    $Child=$Source.worker_creation_identity
    $HasOwnChild=([int]::TryParse([string]$Source.worker_pid,[ref]$ChildNumber) -and $ChildNumber -gt 0 -and
        $Child -and [string]$Child.pid -eq [string]$ChildNumber -and
        [long]::TryParse([string]$Child.creation_ticks,[ref]$CreationTicks) -and $CreationTicks -gt 0 -and
        -not [string]::IsNullOrWhiteSpace([string]$Child.boot_id))
    $Category='WAIT';$Reason='No fresh classified scientific unit is reported.'
    $ActiveUnit=$NativeVerified -and $OwnerMatches -and $Fresh -and -not $Stale -and $HasOwnChild -and $Status -eq 'RUNNING'
    # Cleanup evidence wins over a previous unit's failure while the native owner closes it.
    if($NativeVerified -and ($Source.finalizing_namespace -eq $true -or $Detail -match '(?i)unmount|post.?hash|closed.image.verif|final.image.hash|namespace.*clos|cleanup|after.clean.unmount')){
        $Category='CLEANUP';$Reason='Closing resources or verifying the image after work; no genome processing is inferred.'
    }elseif($StageStatus -match 'FAIL|ERROR|STOPPED' -or $Status -match '^FAIL|ERROR|STOPPED'){
        $Category='FAIL';$Reason='A failure or stop is recorded; completed artifacts and unknown states remain preserved.'
    }elseif($StageStatus -match 'BLOCK|HOLD|WAITING_AT_GATE'){
        $Category='BLOCK';$Reason='Waiting at a recorded gate; no genome processing is inferred.'
    }elseif($StageStatus -match 'COMPLETE|CLOSED|PENDING.*(EXIT|CLOSURE|REVIEW|BENCHMARK)'){
        $Category='RESULT_VALIDATION';$Reason='Saved results or closure await review; this does not grant panel acceptance.'
    }elseif($Detail -match '(?i)preflight|mounting|verifying.sealed.image|setup|dependency|tool.setup|source.*review|source.*prepar|code.*prepar|hashing.*image' -or $Status -match '^PREPAR'){
        $Category='PREPARATION';$Reason='Preparing or checking the runtime, sources or inputs.'
    }elseif($NativeVerified -and $Fresh -and -not $Stale -and [string]$Stage.method -match '^CHECKM1' -and $Status -eq 'RUNNING' -and $Source.genome_processing -eq $true -and $Detail -eq 'analyze'){
        $Category='GENOME_PROCESSING';$Reason='Fresh CheckM1 analyze operation reported by its exact-birth registered owner. Other phases are not inferred to be genome analysis.'
    }elseif($NativeVerified -and $Fresh -and [string]$Stage.method -match '^CHECKM1' -and $Detail -match '^qa$|pilot.*review|root.*go'){
        $Category='RESULT_VALIDATION';$Reason='CheckM1 scoring or pilot review; this is separate from the analyze search and final panel acceptance.'
    }elseif($ActiveUnit -and ($Unit -match '(?i)feature.*valid|valid.*feature|saved.*valid|posthoc|file.only' -or $Detail -match '(?i)saved.*feature.*valid|independent.*membership.*valid')){
        $Category='RESULT_VALIDATION';$Reason='Fresh own-unit report: validating saved results and features; Windows owner verified.'
    }elseif($ActiveUnit -and ($Unit -match '(?i)annotation|prodigal|diamond|resume|quality|prediction|alignment|iqtree|phylog|padloc|defen|ortholog|marker' -or $Detail -match '(?i)^unit_(annotation|diamond|resume|quality|prediction)')){
        $Category='GENOME_PROCESSING';$Reason='Fresh own-unit report and Windows owner identity verified. A live PID alone is insufficient.'
    }elseif($Stale -or -not $OwnerMatches -or ($NativeVerified -and -not $Fresh)){
        $Category='WAIT';$Reason='Operation telemetry is stale, unavailable or belongs to another launch; processing is unverified.'
    }elseif($NativeVerified){
        $Category='WAIT';$Reason='The workflow owner is alive, but its current operation is unverified; no processing is inferred.'
    }
    return @{Category=$Category;Reason=$Reason;Detail=$Detail;DeclaredUnit=$Unit;FreshTelemetry=$Fresh;
        TelemetryAgeSeconds=$Age;NativeVerified=$NativeVerified;OwnScientificChildReported=[bool]$HasOwnChild;
        SourceStatus=$Status;LaunchTokenMatches=$OwnerMatches;ProcessingReported=($Category -eq 'GENOME_PROCESSING')}
}

function Resolve-MonitorArtifactV4([string]$Root,$Row){
    if(-not $Row.path -or [string]$Row.sha256 -notmatch '^[0-9a-fA-F]{64}$'){throw 'Missing artifact binding'}
    $Prefix=$Root.TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
    $Path=[IO.Path]::GetFullPath((Join-Path $Root ([string]$Row.path)))
    if(-not $Path.StartsWith($Prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Display artifact outside project'}
    if((Get-DisplayFileHashV44 -LiteralPath $Path -Algorithm SHA256).Hash -ne [string]$Row.sha256){throw ('Display artifact hash differs: '+$Row.path)}
    return $Path
}

function Get-CampaignPresentationV4([string]$Root){
    $Intent=Read-MonitorSharedJson (Join-Path $Root 'state\qc_campaign_queue_v1\intent.json')
    $Queue=Read-MonitorSharedJson (Resolve-MonitorArtifactV4 $Root $Intent.queue)
    if($Queue.schema -ne 'TREE2_CANONICAL_QC_QUEUE_V001'){throw 'Unknown campaign queue schema'}
    $Supported=@{}
    foreach($Entry in @($Queue.rows)){if($Entry.source_supported_scope -eq $true){$Supported[[string]$Entry.accession]=$true}}
    if($Supported.Count -ne [int]$Intent.source_supported_genomes){throw 'Campaign scope count differs'}
    $Candidates=@(Get-ChildItem -LiteralPath (Join-Path $Root 'metadata') -Filter 'checkm2_accepted_method_result_registry_v*.json' -File | Sort-Object @{Expression={[int]([regex]::Match($_.Name,'v(\d+)\.json$').Groups[1].Value)};Descending=$true})
    $Errors=New-Object 'Collections.Generic.List[string]'
    foreach($File in $Candidates){
        try{
            $Registry=Read-MonitorSharedJson $File.FullName
            if([string]$Registry.schema -notmatch '^TREE2_ACCEPTED_METHOD_RESULT_REGISTRY_V\d+$'){throw 'Unknown registry schema'}
            $Accepted=@{};$Authorities=@{}
            foreach($Row in @($Registry.rows)){
                if(-not $Row.accession -or $Accepted.ContainsKey([string]$Row.accession)){throw 'Duplicate or missing accepted row'}
                $Authority=if($Row.authority){$Row.authority}else{$Registry.cohort_authority}
                if(-not $Authority){throw 'Method row lacks acceptance authority'}
                $Authorities[[string]$Authority.sha256]=$Authority
                $Accepted[[string]$Row.accession]=$true
            }
            if($Registry.additional_baseline){
                $Baseline=$Registry.additional_baseline
                $Authorities[[string]$Baseline.authority.sha256]=$Baseline.authority
                $Accepted[[string]$Baseline.accession]=$true
            }
            $Declared=@($Registry.accepted_unique_method_accessions)
            if(-not $Declared.Count -or $Declared[0] -isnot [string] -or $Declared.Count -ne $Accepted.Count){throw 'Accepted accession list is incomplete/malformed'}
            foreach($Accession in $Declared){if(-not $Accepted.ContainsKey([string]$Accession)){throw 'Accepted list differs from rows'}}
            if($Registry.accepted_method_count -and [int]$Registry.accepted_method_count -ne $Accepted.Count){throw 'Accepted method count differs'}
            foreach($Authority in $Authorities.Values){
                $Value=Read-MonitorSharedJson (Resolve-MonitorArtifactV4 $Root $Authority)
                if([string]$Value.status -notmatch 'ACCEPT' -or [string]$Value.status -match 'HELD|PREPARED'){throw 'Authority is not accepted'}
            }
            $InScope=0
            foreach($Accession in $Accepted.Keys){if($Supported.ContainsKey($Accession)){$InScope++}}
            return @{AcceptedSupported=$InScope;SupportedTotal=$Supported.Count;Remaining=($Supported.Count-$InScope);
                AcceptedAll=$Accepted.Count;Registry=$File.Name;RegistrySha256=(Get-DisplayFileHashV44 -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant();
                SeedAccepted=[int]$Intent.accepted_source_supported_method_rows;SeedRemaining=[int]$Intent.source_supported_remaining;
                Status='REGISTRY_AND_ACCEPTANCE_AUTHORITIES_HASH_VERIFIED';Warnings=@($Errors);PanelAcceptance='NOT_GRANTED'}
        }catch{$Errors.Add($File.Name+': '+$_.Exception.Message)}
    }
    throw ('No verified accepted registry available: '+[string]::Join('; ',$Errors))
}
