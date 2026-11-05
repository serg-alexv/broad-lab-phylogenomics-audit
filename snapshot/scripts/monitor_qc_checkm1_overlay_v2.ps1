. (Join-Path $ProjectRoot 'scripts\monitor_checkm1_raw_searches_v1.ps1')
# Prefer actual current CheckM1 progress; retain CheckM2 only as historical data.
. (Join-Path $ProjectRoot 'scripts\monitor_qc_eta_overlay_v1.ps1')
$script:LegacyQcOverlayV44=(Get-Item Function:\Add-QcEtaPresentationV1).ScriptBlock
function Add-QcEtaPresentationV1($Lines,[string]$Root,[int]$Width){
    $Value=$null
    try{$Value=Read-SmallDisplayJsonV42 (Join-Path $Root 'state\monitor_alternative_qc_v1\current.json')}catch{}
    if(-not $Value -or [string]$Value.method -notmatch '^CHECKM1'){
        & $script:LegacyQcOverlayV44 $Lines $Root $Width
        return
    }
    try{
        $Config=Read-SmallDisplayJsonV42 (Join-Path $Root 'state\monitor_checkm1_v1\config.json')
        $Plan=Read-SmallDisplayJsonV42 (Resolve-MonitorArtifactV4 $Root $Config.plan)
        $Launch=Read-SmallDisplayJsonV42 (Resolve-MonitorArtifactV4 $Root $Config.launch)
        $Identity=$Launch.native_owner
        if([int]$Value.pid -ne [int]$Identity.pid -or (Get-UtcDate $Value.creation_time_utc).ToFileTimeUtc() -ne [long]$Identity.windows_creation_filetime_100ns){throw 'Current CheckM1 report does not match the registered owner'}
        $Live=Confirm-PresentationOwnerV41 $Identity (Resolve-MonitorArtifactV4 $Root $Launch.entry_source)
        $Age=([datetime]::UtcNow-(Get-UtcDate $Value.updated_utc)).TotalSeconds
        $Fresh=$Age -ge -5 -and $Age -le 95
        $Done=[int]$Value.done;$Total=[int]$Value.total
        if($Total -ne [int]$Config.expected_genomes -or $Done -lt 0 -or $Done -gt $Total){throw 'CheckM1 progress denominator is unverified'}
        $Phase=[string]$Value.detail
        $ActuallyReportedAnalyze=$Live -and $Fresh -and $Value.status -eq 'RUNNING' -and $Value.genome_processing -eq $true -and $Phase -eq 'analyze'
        $Lines.Add('CURRENT QC METHOD: CheckM1 1.2.5 / Lactobacillales targeted markers')
        Add-Wrapped $Lines ('CheckM1 measured '+$Done+' / '+$Total+' genomes; method results remain separate from final source, taxonomy and panel acceptance.') ($Width-2)
        $Elapsed=if($null -ne $Value.batch_elapsed_seconds){'{0:N1} min' -f ([double]$Value.batch_elapsed_seconds/60)}else{'unknown'}
        Add-Wrapped $Lines ('Batch '+$Value.batch+' / '+$Value.batch_total+': '+$Value.batch_genomes+' genomes; phase '+$Phase+'; batch phase elapsed '+$Elapsed+'.') ($Width-2)
        $RawSearches=Get-CheckM1RawSearchesV45 $Root $Plan $Value
        if($RawSearches.status -eq 'KNOWN_SUCCESSFUL_RAW_SEARCH_RECEIPTS'){
            Add-Wrapped $Lines ('Raw marker searches completed '+$RawSearches.completed+' / '+$RawSearches.total+' in this batch (unique input genomes, actual search exit0). These are separate from fully measured QC '+$Done+' / '+$Total+'.') ($Width-2)
            if($RawSearches.unreadable_receipts -gt 0){Add-Wrapped $Lines ('Raw-search observation warning: '+$RawSearches.unreadable_receipts+' receipt(s) unreadable; only verified successful receipts counted.') ($Width-2)}
        }else{Add-Wrapped $Lines ('Raw marker search progress UNKNOWN: '+$RawSearches.reason+'; no search success inferred.') ($Width-2)}
        Add-Wrapped $Lines ('Current owner '+$Identity.pid+': '+$(if($Live){'LIVE, exact creation identity verified'}else{'not live; closure is not inferred'})+'; report '+$(if($Fresh){'fresh'}else{'STALE'})+'. Genome analysis '+$(if($ActuallyReportedAnalyze){'reported in the analyze unit'}else{'not inferred for this phase'})+'.') ($Width-2)
        if($null -ne $Value.group_rss_bytes){$Lines.Add(('Reported Linux group RAM {0:N2} GiB; configured CPUs {1}.' -f ([double]$Value.group_rss_bytes/1GB),$Plan.threads))}
        if([int]$Value.batch -le 1 -and $Done -lt 18){
            Add-Wrapped $Lines 'Queue: first18 pilot genomes; remaining901 require Root scientific review and a bound GO. This is an internal review, not a user approval wait.' ($Width-2)
        }else{
            Add-Wrapped $Lines 'Queue: follow actual worker phases and Root review/GO receipts. A completed count does not itself authorize later batches or grant final acceptance.' ($Width-2)
        }
        Add-Wrapped $Lines ('ETA: '+$(if($Done -eq 0){'uncalibrated; no completed CheckM1 batch benchmark yet.'}else{'not yet published from a reviewed CheckM1 benchmark; no finish time inferred.'})) ($Width-2)
        $Lines.Add('Historical CheckM2 accepted estimates are separate; they do not increment this CheckM1 count.')
        $script:EtaLast=@{schema='TREE2_CHECKM1_CURRENT_PRESENTATION_V1';producer=$Value;owner_verified_live=$Live;report_fresh=$Fresh;analyze_reported=$ActuallyReportedAnalyze;plan=$Config.plan;launch=$Config.launch;eta_seconds=$null;raw_marker_searches=$RawSearches}
    }catch{Add-Wrapped $Lines ('CURRENT CHECKM1 OBSERVATION UNAVAILABLE: '+$_.Exception.Message+'; no processing, count or ETA inferred.') ($Width-2)}
}
