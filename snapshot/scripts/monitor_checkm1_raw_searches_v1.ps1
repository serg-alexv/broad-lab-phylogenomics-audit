# Presentation only: existing command/actual-exit receipts, never HMM/FAA output.
function Get-CheckM1QueryAccessionV45([string]$Value){
    $Text=$Value.Replace('\','/')
    if($Text -match '(?:^|/)(GC[AF]_\d+\.\d+)/(?:genes|prodigal)\.faa$'){return $Matches[1]}
    if($Text -match '(?:^|/)(GC[AF]_\d+\.\d+)\.(?:faa|fasta|fa)$'){return $Matches[1]}
    return $null
}
function Get-CheckM1RawSearchesV45([string]$Root,$Plan,$Progress){
    try{
        $Output=Resolve-DisplayPathV42 $Root ([string]$Plan.output)
        $Batch=[int]$Progress.batch-1
        if($Batch -lt 0 -or $Batch -gt 1023){throw 'Current batch index unavailable'}
        $Folder=Join-Path $Output ('batch_{0:d3}' -f $Batch)
        if($Progress.log_path){
            $Log=Resolve-DisplayPathV42 $Root ([string]$Progress.log_path)
            if(-not $Log.StartsWith($Folder+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Current log does not belong to this batch'}
        }
        $Manifest=@(Read-SmallDisplayJsonV42 (Join-Path $Folder 'staged_input_manifest.json'))
        $Names=@{}
        foreach($Row in $Manifest){
            $Name=[string]$Row.accession
            if($Name -notmatch '^GC[AF]_\d+\.\d+$' -or $Names.ContainsKey($Name)){throw 'Staged batch accession list is invalid'}
            $Names[$Name]=$true
        }
        if($Names.Count -ne [int]$Progress.batch_genomes -or $Names.Count -eq 0){throw 'Staged batch denominator differs from current report'}
        $Directory=Join-Path $Folder 'HMMER_receipts'
        if(-not [IO.Directory]::Exists($Directory)){throw 'No command receipt directory yet'}
        $Files=@(Get-ChildItem -LiteralPath $Directory -Filter '*.json' -File -ErrorAction Stop | Select-Object -First 4097)
        if($Files.Count -gt 4096){throw 'Receipt count exceeds bounded display scan'}
        $Completed=@{};$Unreadable=0;$OutOfScope=0
        foreach($File in $Files){
            try{
                # Read-SmallDisplayJsonV42 uses Read-MonitorSharedJson, whose
                # FileShare includes WRITE and DELETE for atomic live writers.
                $Receipt=Read-SmallDisplayJsonV42 $File.FullName
                $Arguments=@($Receipt.argv)
                if($Arguments.Count -lt 4 -or ([string]$Arguments[0]).Replace('\','/') -notmatch '(?:^|/)hmmsearch(?:\.exe)?$'){continue}
                if(-not ($Receipt.actual_exit_code -is [int] -or $Receipt.actual_exit_code -is [long]) -or $Receipt.actual_exit_code -ne 0 -or $Receipt.probe_only -eq $true){continue}
                $Indices=@(for($i=0;$i -lt $Arguments.Count;$i++){if([string]$Arguments[$i] -eq '--domtblout'){$i}})
                if($Indices.Count -ne 1 -or $Indices[0]+1 -ge $Arguments.Count){continue}
                $Accession=Get-CheckM1QueryAccessionV45 ([string]$Arguments[-1])
                $DomainPath=([string]$Arguments[$Indices[0]+1]).Replace('\','/')
                $DomainAccession=$null
                if($DomainPath -match '(?:^|/)(GC[AF]_\d+\.\d+)/[^/]+$'){$DomainAccession=$Matches[1]}
                if(-not $Accession -or -not $Names.ContainsKey($Accession) -or $DomainAccession -ne $Accession){$OutOfScope++;continue}
                $Completed[$Accession]=$true
            }catch{$Unreadable++}
        }
        return @{status='KNOWN_SUCCESSFUL_RAW_SEARCH_RECEIPTS';completed=$Completed.Count;total=$Names.Count;accessions=@($Completed.Keys|Sort-Object);receipt_directory=$Directory.Substring($Root.Length+1).Replace('\','/');receipts_seen=$Files.Count;unreadable_receipts=$Unreadable;out_of_scope_receipts=$OutOfScope;definition='unique staged query accession; hmmsearch with --domtblout; numeric actual_exit_code0';QC_estimate_completion_inferred=$false}
    }catch{return @{status='OBSERVATION_UNAVAILABLE';completed=$null;total=$null;reason=$_.Exception.Message;QC_estimate_completion_inferred=$false}}
}
