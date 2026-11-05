param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop'
foreach($Name in @('live_progress_v4_5.ps1','monitor_qc_checkm1_overlay_v2.ps1','monitor_checkm1_raw_searches_v1.ps1')){
    $Tokens=$null;$Errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $ProjectRoot ('scripts\'+$Name)),[ref]$Tokens,[ref]$Errors)
    if($Errors.Count){throw ($Name+': '+[string]::Join('; ',@($Errors|ForEach-Object {$_.Message})))}
}
function Read-MonitorSharedJson([string]$Path){
    $Stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try{$Reader=[IO.StreamReader]::new($Stream,[Text.Encoding]::UTF8,$true);try{return ($Reader.ReadToEnd()|ConvertFrom-Json)}finally{$Reader.Dispose()}}finally{$Stream.Dispose()}
}
. (Join-Path $ProjectRoot 'scripts\monitor_computed_rows_overlay_v4_4.ps1')
. (Join-Path $ProjectRoot 'scripts\monitor_checkm1_raw_searches_v1.ps1')
$Relative='work\monitor_raw_search_fixture_'+[guid]::NewGuid().ToString('N')
$Folder=Join-Path $ProjectRoot ($Relative+'\batch_000');$Receipts=Join-Path $Folder 'HMMER_receipts'
[IO.Directory]::CreateDirectory($Receipts)|Out-Null
function Put([string]$Name,$Value){[IO.File]::WriteAllText((Join-Path $Receipts $Name),($Value|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))}
function Search([string]$Accession,[int]$Code=0){return @{argv=@('/tools/hmmsearch','--domtblout',('/run/private/bins/'+$Accession+'/hmmer.analyze.txt'),'/tmp/marker.hmm',('/run/private/bins/'+$Accession+'/genes.faa'));actual_exit_code=$Code;binary_handle_waited_and_reaped=$true}}
$Names=@('GCF_000000001.1','GCA_000000002.1','GCF_000000003.1')
$Manifest=@($Names|ForEach-Object {@{accession=$_}})
[IO.File]::WriteAllText((Join-Path $Folder 'staged_input_manifest.json'),($Manifest|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Put 'success.json' (Search $Names[0]);Put 'duplicate.json' (Search $Names[0]);Put 'failure.json' (Search $Names[1] 1)
Put 'probe.json' @{argv=@('/tools/hmmsearch','-h');actual_exit_code=0}
Put 'index.json' @{argv=@('/tools/hmmfetch','--index','/tmp/index');actual_exit_code=0}
Put 'out_of_scope.json' (Search 'GCF_999999999.1')
Put 'started.json' @{argv=(Search $Names[2]).argv;status='STARTED_NOT_COMPLETED'}
[IO.File]::WriteAllText((Join-Path $Receipts 'partial.json'),'invalid-partial-json',[Text.UTF8Encoding]::new($false))
$Plan=@{output=$Relative};$Progress=@{batch=1;batch_genomes=3;done=0;total=919;log_path=(Join-Path $Folder 'unit_analyze\stderr.txt')}
$First=Get-CheckM1RawSearchesV45 $ProjectRoot $Plan $Progress
if($First.completed -ne 1 -or $First.total -ne 3 -or $First.unreadable_receipts -ne 1){throw ('Deduplication/failure/probe/partial handling failed: '+($First|ConvertTo-Json -Compress))}
Put 'second_success.json' (Search $Names[1])
# A simultaneous writer/delete-capable handle must not block the UI reader.
$Shared=[IO.FileStream]::new((Join-Path $Receipts 'second_success.json'),[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete),4096,[IO.FileOptions]::DeleteOnClose)
try{$Second=Get-CheckM1RawSearchesV45 $ProjectRoot $Plan $Progress}finally{$Shared.Dispose()}
if($Second.completed -ne 2 -or $Progress.done -ne 0){throw 'Shared reader or QC/raw-count separation failed'}
$Progress.log_path=Join-Path $ProjectRoot 'wrong_batch\stderr.txt'
$Unknown=Get-CheckM1RawSearchesV45 $ProjectRoot $Plan $Progress
if($Unknown.status -ne 'OBSERVATION_UNAVAILABLE' -or $null -ne $Unknown.completed){throw 'Mismatched batch must remain unknown'}
$Report=@{status='PASS_SYNTHETIC_RAW_MARKER_PROGRESS';unique_query_accessions=$true;actual_exit0_and_domtblout_required=$true;failed_probe_index_and_started_excluded=$true;partial_JSON_not_counted=$true;RAM_query_paths_supported_without_opening_RAM=$true;shared_WRITE_DELETE_reader=$true;raw_searches_do_not_increment_QC=$true;mismatched_batch_unknown_not_zero=$true;fixture=(Join-Path $ProjectRoot $Relative);scientific_execution=$false}
[IO.File]::WriteAllText((Join-Path $ProjectRoot ($Relative+'\receipt.json')),($Report|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$Report|ConvertTo-Json -Compress
