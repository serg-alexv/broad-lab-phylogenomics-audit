# Display-only RAM labels and measured-batch calibration. No daemon or runtime probe.
function Get-CheckM1MemoryLabelV46($Progress,$Plan){
    if($null -ne $Progress.private_RAM_used_bytes -and $null -ne $Progress.combined_memory_bytes -and $null -ne $Progress.group_rss_bytes){
        return ('Reported memory: process RSS {0:N2} GiB + private RAM scratch {1:N2} GiB = combined {2:N2} GiB; combined budget {3:N2} GiB.' -f ([double]$Progress.group_rss_bytes/1GB),([double]$Progress.private_RAM_used_bytes/1GB),([double]$Progress.combined_memory_bytes/1GB),([double]$Plan.linux_total_RSS_bytes/1GB))
    }
    if($null -ne $Progress.group_rss_bytes){return ('Reported Linux process RSS {0:N2} GiB; private RAM scratch/combined memory not reported.' -f ([double]$Progress.group_rss_bytes/1GB))}
    return 'Reported memory: unavailable; no zero usage inferred.'
}
function Read-CheckM1TimingMetadataV46([string]$Path){
    $Item=Get-Item -LiteralPath $Path -ErrorAction Stop
    if($Item.Length -gt 2097152 -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Not bounded timing metadata'}
    return Read-MonitorSharedJson $Path
}
function Get-CheckM1WarmETA_V46([string]$Root,$Plan,$PlanReference,$Progress,[bool]$OwnerLive){
    $Unknown=@{status='UNCALIBRATED_NO_COMPLETED_NEW_RAM_BATCH';remaining_seconds=$null;finish_msk=$null;samples=0;text='Uncalibrated: wait for the first complete new RAM-backed batch; reused pilot18 and partial raw searches are not timing samples.'}
    try{
        if($Plan.execution_backend -ne 'PRIVATE_RAM_SCRATCH_DURABLE_PER_BIN_AND_BATCH'){return $Unknown}
        $Output=Resolve-DisplayPathV42 $Root ([string]$Plan.output)
        $Samples=@();$Seen=@{}
        foreach($Folder in @(Get-ChildItem -LiteralPath $Output -Directory -Filter 'batch_*' -ErrorAction Stop|Select-Object -First 128)){
            $CommitPath=Join-Path $Folder.FullName 'COMMITTED.json'
            if(-not [IO.File]::Exists($CommitPath)){continue}
            try{
                $Commit=Read-CheckM1TimingMetadataV46 $CommitPath
                if($Commit.status -ne 'CHECKM1_BATCH_MEASURED_VALIDATED' -or [string]$Commit.original_method_plan_sha256 -ne [string]$PlanReference.sha256){continue}
                $Names=@($Commit.accessions)
                if($Names.Count -eq 0 -or @($Commit.rows).Count -ne $Names.Count){continue}
                if(@($Names|Sort-Object -Unique).Count -ne $Names.Count -or [string]::Join('|',@($Commit.rows|ForEach-Object {$_.accession})) -ne [string]::Join('|',$Names)){continue}
                $Claim=Read-CheckM1TimingMetadataV46 (Join-Path $Folder.FullName 'once_claim.json')
                if([string]$Claim.method_plan_sha256 -ne [string]$PlanReference.sha256 -or [string]::Join('|',@($Claim.accessions)) -ne [string]::Join('|',$Names)){continue}
                $Valid=$true
                foreach($Unit in @('unit_analyze','unit_qa')){
                    $UnitPath=Join-Path $Folder.FullName ($Unit+'\execution.json')
                    $Binding=@($Commit.artifacts|Where-Object {(Resolve-DisplayPathV42 $Root ([string]$_.path)) -eq $UnitPath})
                    if($Binding.Count -ne 1){$Valid=$false;break}
                    if((Get-DisplayFileHashV44 $UnitPath).Hash -ne [string]$Binding[0].sha256 -or (Get-Item -LiteralPath $UnitPath).Length -ne $Binding[0].bytes){$Valid=$false;break}
                    $Execution=Read-CheckM1TimingMetadataV46 $UnitPath
                    if(-not ($Execution.actual_exit_code -is [int] -or $Execution.actual_exit_code -is [long]) -or $Execution.actual_exit_code -ne 0 -or $Execution.actual_child_waited_and_reaped -ne $true -or $Execution.group_closed -ne $true){$Valid=$false;break}
                }
                if(-not $Valid){continue}
                $Span=([datetimeoffset]::Parse([string]$Commit.ended_utc)-[datetimeoffset]::Parse([string]$Claim.started_utc)).TotalSeconds
                if($Span -le 0 -or [double]::IsNaN($Span) -or [double]::IsInfinity($Span)){continue}
                if(@($Names|Where-Object {$Seen.ContainsKey([string]$_)}).Count){continue}
                foreach($Name in $Names){$Seen[[string]$Name]=$true}
                $Samples+=@{batch=$Folder.Name;genomes=$Names.Count;wall_seconds=$Span;commit=$CommitPath.Substring($Root.Length+1).Replace('\','/');commit_sha256=(Get-DisplayFileHashV44 $CommitPath).Hash.ToLowerInvariant()}
            }catch{continue}
        }
        if(-not $Samples.Count){return $Unknown}
        $Seconds=0.0;$Genomes=0
        foreach($Sample in $Samples){$Seconds+=$Sample.wall_seconds;$Genomes+=$Sample.genomes}
        $Remaining=[math]::Max(0,[int]$Progress.total-[int]$Progress.done)
        $Estimate=$Seconds/$Genomes*$Remaining
        $Text=('About {0:N1} h for remaining CheckM1 measurements, from {1} completed RAM batch(es)/{2} genomes; sample-limited. Unfinished batches counted in full; source/taxonomy/panel review extra.' -f ($Estimate/3600),$Samples.Count,$Genomes)
        $Finish=$null
        if($OwnerLive -and [string]$Progress.status -eq 'RUNNING'){$Finish=[datetime]::UtcNow.AddSeconds($Estimate).AddHours(3).ToString('yyyy-MM-dd HH:mm')+' MSK'}
        else{$Text+=' Finish clock suspended while the owner is not actively running.'}
        return @{status='MEASURED_NEW_RAM_BATCH_SAMPLE_LIMITED';remaining_seconds=$Estimate;finish_msk=$Finish;samples=$Samples.Count;sample_genomes=$Genomes;wall_seconds_per_genome=$Seconds/$Genomes;sample_receipts=$Samples;text=$Text;unfinished_batches_counted_in_full=$true;final_acceptance_inferred=$false}
    }catch{return @{status='TIMING_OBSERVATION_UNAVAILABLE';remaining_seconds=$null;finish_msk=$null;samples=0;text=('Timing observation unavailable: '+$_.Exception.Message+'; no rate or ETA inferred.')}}
}
