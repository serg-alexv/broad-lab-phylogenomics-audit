# Read-only presentation metrics. No scientific process, configuration or checkpoint is changed.
if (-not ('Tree2MonitorMetricsV5.Native' -as [type])) {
    $tree2CompileTemp=Join-Path (Split-Path -Parent $PSScriptRoot) 'work/monitor_v5_temp'
    [void](New-Item -ItemType Directory -Path $tree2CompileTemp -Force)
    $tree2PreviousTemp=$env:TEMP;$tree2PreviousTmp=$env:TMP
    try {
    $env:TEMP=$tree2CompileTemp;$env:TMP=$tree2CompileTemp
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Tree2MonitorMetricsV5 {
 public static class Native {
  [DllImport("kernel32.dll")] static extern IntPtr OpenProcess(uint a,bool b,int p);
  [DllImport("kernel32.dll")] static extern bool GetProcessTimes(IntPtr h,out long c,out long e,out long k,out long u);
  [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr h,uint t);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  public static long LiveBirth(int processNumber) {
   IntPtr h=OpenProcess(0x101000,false,processNumber);if(h==IntPtr.Zero)return -1;
   try { if(WaitForSingleObject(h,0)!=258)return -2;long c,e,k,u;
    return GetProcessTimes(h,out c,out e,out k,out u)?c:-3;
   } finally {CloseHandle(h);}
  }
 }
}
'@
    } finally {$env:TEMP=$tree2PreviousTemp;$env:TMP=$tree2PreviousTmp}
}

function Read-T5Bytes([string]$Path,[long]$Offset=0,[int]$Maximum=2097152) {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try {
        if($Offset -gt 0){[void]$stream.Seek($Offset,[IO.SeekOrigin]::Begin)}
        $memory=New-Object IO.MemoryStream
        try {
            $buffer=New-Object byte[] 32768;$remaining=$Maximum
            while($remaining -gt 0){$n=$stream.Read($buffer,0,[Math]::Min($buffer.Length,$remaining));if($n -eq 0){break};$memory.Write($buffer,0,$n);$remaining-=$n}
            return ,$memory.ToArray()
        } finally {$memory.Dispose()}
    } finally {$stream.Dispose()}
}
function Read-T5Text([string]$Path,[long]$Offset=0,[int]$Maximum=2097152) {
    return [Text.Encoding]::UTF8.GetString((Read-T5Bytes $Path $Offset $Maximum))
}
function Read-T5Json([string]$Path) { return (Read-T5Text $Path 0 12582912 | ConvertFrom-Json) }
function Format-T5Duration([double]$Seconds) {
    if($Seconds -lt 0){return 'unknown'}
    $span=[TimeSpan]::FromSeconds($Seconds)
    if($span.TotalDays -ge 1){return ('{0}d {1:00}h {2:00}m' -f [int][Math]::Floor($span.TotalDays),$span.Hours,$span.Minutes)}
    if($span.TotalHours -ge 1){return ('{0}h {1:00}m' -f [int][Math]::Floor($span.TotalHours),$span.Minutes)}
    if($span.TotalMinutes -ge 1){return ('{0}m {1:00}s' -f [int][Math]::Floor($span.TotalMinutes),$span.Seconds)}
    return ('{0:0}s' -f $Seconds)
}
function Convert-T5Number([string]$Value) { return [double]::Parse($Value,[Globalization.CultureInfo]::InvariantCulture) }
function Format-T5Number([double]$Value,[string]$Format='N3') { return $Value.ToString($Format,[Globalization.CultureInfo]::InvariantCulture) }
function Get-T5ProcStat([string]$Path) {
    $text=Read-T5Text $Path 0 16384;$end=$text.LastIndexOf(')');if($end -lt 0){throw 'Unreadable Linux process stat'}
    $fields=$text.Substring($end+1).Trim() -split '\s+'
    return @{state=$fields[0];parent=[long]$fields[1];start=[long]$fields[19];ticks=([long]$fields[11]+[long]$fields[12]);rss_pages=[long]$fields[21]}
}
function Get-T5LinuxCpu([string]$ProjectRoot,$Plan,$Previous) {
    $procBase='\\wsl.localhost\Ubuntu\proc'
    $owner=Read-T5Json (Join-Path $ProjectRoot ($Plan.work+'/linux_owner.json'))
    $boot=(Read-T5Text ($procBase+'\sys\kernel\random\boot_id') 0 4096).Trim()
    if($boot -ne $owner.boot_id){throw 'Linux boot identity differs'}
    $driver=Get-T5ProcStat ($procBase+'\'+$owner.pid+'\stat')
    if($driver.start -ne [long]$owner.creation_ticks){throw 'Linux driver creation identity differs'}
    $command=Read-T5Json (Join-Path $ProjectRoot ($Plan.output+'/attempts/'+$Plan.attempt_id+'/unit/command.json'))
    $children=(Read-T5Text ($procBase+'\'+$owner.pid+'\task\'+$owner.pid+'\children') 0 16384).Trim() -split '\s+'
    $verifiedChildren=@()
    foreach($childNumber in $children){
        if($childNumber -notmatch '^\d+$'){continue}
        try {
            $childBase=$procBase+'\'+$childNumber
            $raw=Read-T5Text ($childBase+'\cmdline') 0 65536
            $tokens=@($raw.Split([char]0) | Where-Object {$_ -ne ''})
            if($tokens.Count -ne @($command.argv).Count){continue}
            $same=$true;for($i=0;$i -lt $tokens.Count;$i++){if($tokens[$i] -cne [string]$command.argv[$i]){$same=$false;break}}
            if(-not $same){continue}
            $stat=Get-T5ProcStat ($childBase+'\stat');if($stat.parent -ne [long]$owner.pid){continue}
            $aux=Read-T5Bytes ($childBase+'\auxv') 0 16384;$hz=0L;$pageSize=0L
            for($j=0;$j+15 -lt $aux.Length;$j+=16){$kind=[BitConverter]::ToUInt64($aux,$j);$value=[BitConverter]::ToUInt64($aux,$j+8);if($kind -eq 17){$hz=[long]$value};if($kind -eq 6){$pageSize=[long]$value}}
            if($hz -le 0 -or $pageSize -le 0){throw 'Linux clock/page-size ABI unavailable'}
            $uptime=Convert-T5Number (((Read-T5Text ($procBase+'\uptime') 0 4096).Trim() -split '\s+')[0])
            $key=$boot+':'+$childNumber+':'+$stat.start
            $monotonic=[Diagnostics.Stopwatch]::GetTimestamp()/[double][Diagnostics.Stopwatch]::Frequency
            $cpuSeconds=$stat.ticks/[double]$hz;$percent=$null
            if($Previous -and $Previous.key -eq $key -and $monotonic -gt [double]$Previous.monotonic -and $cpuSeconds -ge [double]$Previous.cpu_seconds){
                $percent=100*($cpuSeconds-[double]$Previous.cpu_seconds)/($monotonic-[double]$Previous.monotonic)
            }
            $verifiedChildren+=@{key=$key;monotonic=$monotonic;cpu_seconds=$cpuSeconds;percent_one_core=$percent;
                state=$stat.state;wall_seconds=($uptime-$stat.start/[double]$hz);rss_bytes=($stat.rss_pages*$pageSize);
                process_number=[long]$childNumber;start_ticks=$stat.start;exact_argv_verified=$true}
        } catch {continue}
    }
    if($verifiedChildren.Count -ne 1){throw 'Exact current IQ-TREE child could not be verified'}
    return $verifiedChildren[0]
}
function Get-T5LogContext([string]$Path,$Previous) {
    $info=Get-Item -LiteralPath $Path -ErrorAction Stop
    if($Previous -and $Previous.path -eq $Path -and [long]$info.Length -ge [long]$Previous.offset){$context=$Previous;$offset=[long]$context.offset}
    else {$context=@{path=$Path;offset=0L;phase='Reading data / initial setup';initial_ll=$null;best_ll=$null;last_iteration=$null;initial_candidates=$null;samples_prepared=$false;ufboot_started=$false;ufboot_written=$false;sh_started=$false;search_finished=$false;events=@();pending=''};$offset=0L}
    $bytes=Read-T5Bytes $Path $offset 2097152;$text=[string]$context.pending+[Text.Encoding]::UTF8.GetString($bytes)
    $context.offset=$offset+$bytes.Length;$lines=$text -split "`n"
    if($text.EndsWith("`n")){$context.pending=''}else{$context.pending=$lines[-1];if($lines.Count -gt 1){$lines=$lines[0..($lines.Count-2)]}else{$lines=@()}}
    foreach($rawLine in $lines){
        $line=$rawLine.Trim();if(-not $line){continue};$event=$false
        if($line -match 'Create initial parsimony tree'){$context.phase='Constructing initial tree';$event=$true}
        if($line -match '^Generating\s+(\d+) samples for ultrafast bootstrap'){$context.samples_prepared=$true;$event=$true}
        if($line -match '^Estimate model parameters' -and $context.phase -in @('Reading data / initial setup','Constructing initial tree')){$context.phase='Fitting initial model parameters';$event=$true}
        if($line -match '^Computing ML distances'){$context.phase='Computing distances / starting trees';$event=$true}
        if($line -match '^Generating (\d+) parsimony trees'){$context.phase='Building initial tree candidates';$event=$true}
        if($line -match '^Computing log-likelihood of (\d+) initial trees'){$context.phase='Scoring initial tree candidates';$event=$true}
        if($line -match '^Do NNI search on (\d+) best initial trees'){$context.phase='Initial-tree refinement';$context.initial_candidates=[int]$Matches[1];$context.last_iteration=$null;$event=$true}
        if($line -match '^CHECKPOINT: Resuming analysis'){$context.phase='Restoring saved checkpoint';$context.checkpoint_resume=$true;$event=$true}
        if($line -match '^CHECKPOINT: .*restored.*LogL: ([-0-9.]+)'){$context.best_ll=Convert-T5Number $Matches[1];$context.phase='Saved checkpoint restored';$event=$true}
        if($line -match '^Number of iterations: (\d+)'){$context.restored_iteration=[int]$Matches[1];$event=$true}
        if($line -match 'Finish initializing candidate tree set'){$context.phase='Initial candidates ready';$event=$true}
        if($line -match 'OPTIMIZING CANDIDATE TREE SET' -and $context.checkpoint_resume){$context.phase='Optimizing restored candidates';$event=$true}
        if($line -match 'ML-TREE SEARCH START'){$context.phase='Main maximum-likelihood tree search';$event=$true}
        if($line -match '^TREE SEARCH COMPLETED AFTER'){$context.search_finished=$true;$context.phase='Tree search complete / branch supports';$event=$true}
        if($line -match 'Refining ufboot trees with NNI'){$context.ufboot_started=$true;$context.phase='Refining bootstrap trees';$event=$true}
        if($line -match '^ASSESSING SH-aLRT BRANCH SUPPORTS'){$context.sh_started=$true;$context.phase='Computing SH-aLRT branch supports';$event=$true}
        if($line -match '^UFBoot trees printed to'){$context.ufboot_written=$true;$event=$true}
        if($line -match '^BETTER TREE FOUND at iteration (\d+):\s*([-+0-9.eE]+)'){
            $context.last_iteration=[int]$Matches[1];$value=Convert-T5Number $Matches[2]
            if($null -eq $context.best_ll -or $value -gt [double]$context.best_ll){$context.best_ll=$value};$event=$true
        } elseif($line -match '^\d+\. Initial log-likelihood:\s*([-+0-9.eE]+)'){
            $value=Convert-T5Number $Matches[1];if($null -eq $context.initial_ll){$context.initial_ll=$value};if($null -eq $context.best_ll -or $value -gt [double]$context.best_ll){$context.best_ll=$value};$event=$true
        } elseif($line -match '^(?:\d+\. Current log-likelihood:|Optimal log-likelihood:|Current best score:)\s*([-+0-9.eE]+)'){
            $value=Convert-T5Number $Matches[1];if($null -eq $context.best_ll -or $value -gt [double]$context.best_ll){$context.best_ll=$value};$event=$true
        }
        if($event){$context.events=@($context.events | Select-Object -Last 3)+@($line)}
    }
    $context.age_seconds=[Math]::Max(0,([DateTime]::UtcNow-$info.LastWriteTimeUtc).TotalSeconds)
    return $context
}
function Get-Tree2MonitorDataV5([string]$ProjectRoot,$Previous) {
    $now=[DateTime]::UtcNow;$run=Read-T5Json (Join-Path $ProjectRoot 'state/full900_production_current.json')
    $plan=Read-T5Json (Join-Path $ProjectRoot $run.plan.path)
    $producer=Read-T5Json (Join-Path $ProjectRoot ($plan.work+'/progress.json'))
    $birth=[Tree2MonitorMetricsV5.Native]::LiveBirth([int]$run.worker.pid)
    $verified=($birth -eq [long]$run.worker.windows_creation_filetime_100ns)
    $sameProducer=($producer.pid -eq $run.worker.pid -and [string]$producer.creation_time_utc -eq [string]$run.worker.creation_time_utc)
    $producerAge=[Math]::Max(0,($now-[DateTime]::Parse($producer.updated_utc).ToUniversalTime()).TotalSeconds)
    $cpu=$null;$cpuError=$null
    if($verified -and $sameProducer){try {$priorCpu=$null;if($Previous){$priorCpu=$Previous.cpu};$cpu=Get-T5LinuxCpu $ProjectRoot $plan $priorCpu}catch{$cpuError=$_.Exception.Message}}
    $logPath=Join-Path $ProjectRoot ($plan.prefix+'.log');$priorLog=$null;if($Previous){$priorLog=$Previous.log}
    try {$context=Get-T5LogContext $logPath $priorLog}catch{if($priorLog){$context=$priorLog}else{$context=@{phase='Waiting for IQ-TREE log';best_ll=$null;initial_ll=$null;last_iteration=$null;initial_candidates=$null;events=@();samples_prepared=$false;ufboot_started=$false;ufboot_written=$false;sh_started=$false;search_finished=$false;age_seconds=-1}}}
    $status='CHECKING';$headline='Checking the production process'
    if($verified -and $sameProducer){$status='RUNNING';$headline='Full-panel phylogeny is computing'}
    elseif(-not $verified){$status='NOT VERIFIED';$headline='Production owner is not live; check the recorded exit and next stage'}
    if($producer.status -match '^COMPUTED'){$status='COMPUTED';$headline='Tree computation finished; independent validation is next'}
    $rows=New-Object Collections.Generic.List[object]
    $phaseNote='';if($context.initial_candidates -and $context.phase -eq 'Initial-tree refinement'){$phaseNote=([string]$context.initial_candidates+' candidates; no completion count reported')}
    $rows.Add(@{metric='Current phase';value=[string]$context.phase;note=$phaseNote})
    $activity='CPU measurement unavailable';$activityNote=''
    if($cpu){
        if($null -ne $cpu.percent_one_core){$activity=(Format-T5Number $cpu.percent_one_core 'N1')+'% of one CPU core';if($cpu.percent_one_core -ge 2){$activityNote='CPU active; quiet log does not imply a stall'}else{$activityNote='Low CPU over this interval; no failure inferred'}}
        else {$activity='Process verified; measuring CPU';$activityNote='CPU percentage appears on the next refresh'}
    }elseif($cpuError){$activityNote='CPU observation unavailable; no idle/running inference from its absence'}
    $rows.Add(@{metric='Actual CPU activity';value=$activity;note=$activityNote})
    $priorProduction=[double]$plan.previous_production_scientific_seconds
    $attemptElapsed=[double]$producer.elapsed_scientific_seconds;if($cpu){$attemptElapsed=[double]$cpu.wall_seconds}
    $elapsed=$priorProduction+$attemptElapsed
    $requestedThreads=1;if($plan.compute_threads){$requestedThreads=[int]$plan.compute_threads}
    $rows[$rows.Count-1].note='Requested '+$requestedThreads+' threads; affinity '+(@($plan.cpu_affinity) -join ',')
    if($context.restored_iteration){$rows[0].note='Checkpoint restored; saved iteration '+$context.restored_iteration+' retained'}
    $cpuText='';if($cpu){$cpuText='IQ-TREE CPU time '+(Format-T5Duration $cpu.cpu_seconds)}
    $rows.Add(@{metric='Total production time';value=(Format-T5Duration $elapsed);note=('Prior '+(Format-T5Duration $priorProduction)+'; current '+(Format-T5Duration $attemptElapsed))})
    $iteration='Not reported yet';if($null -ne $context.last_iteration){$iteration='Last improvement: iteration '+$context.last_iteration}
    $rows.Add(@{metric='Search progress';value=$iteration;note='Adaptive search; no reliable overall ETA'})
    $likelihood='Not reported yet';$gain=''
    if($null -ne $context.best_ll){$likelihood=Format-T5Number $context.best_ll;if($null -ne $context.initial_ll){$gain='+'+(Format-T5Number ([double]$context.best_ll-[double]$context.initial_ll))+' since initial fit'}}
    $rows.Add(@{metric='Best likelihood';value=$likelihood;note=$gain})
    $boot='Not yet reached';$bootNote='1,000 support replicates requested'
    if($context.samples_prepared){$bootNote='1,000 samples ready; support still pending'}
    if($context.ufboot_started){$boot='Bootstrap tree refinement active'}
    if($context.ufboot_written){$boot='Bootstrap trees written';$bootNote='Output count and support quality require final verification'}
    $rows.Add(@{metric='Ultrafast bootstrap';value=$boot;note=$bootNote})
    $sh='Not yet reached';if($context.sh_started){$sh='SH-aLRT phase reached / processing'}
    if($status -eq 'COMPUTED'){$sh='Computation finished; validation pending'}
    $rows.Add(@{metric='SH-aLRT supports';value=$sh;note='1,000 requested; completion not yet validated'})
    $used=[double]$producer.owned_Linux_RSS_bytes+[double]$producer.private_RAM_used_bytes
    $rows.Add(@{metric='RAM / guard';value=((Format-T5Number ($used/1GB) 'N2')+' / '+(Format-T5Number ([double]$plan.linux_RSS_plus_RAM_bytes/1GB) 'N2')+' GiB');note=('Linux available '+(Format-T5Number ([double]$producer.Linux_available_bytes/1GB) 'N2')+' GiB; sample '+(Format-T5Duration $producerAge)+' old')})
    $checkpointText='No checkpoint observed yet';$checkpointNote='Active files are only inspected, never changed or hash-accepted'
    try {$st=Get-Item -LiteralPath (Join-Path $ProjectRoot ($plan.prefix+'.ckp.gz')) -ErrorAction Stop;$age=[Math]::Max(0,($now-$st.LastWriteTimeUtc).TotalSeconds);$checkpointText='Last write '+(Format-T5Duration $age)+' ago';$checkpointNote='Active optimization can run between stock writes'}catch{}
    $rows.Add(@{metric='Checkpoint';value=$checkpointText;note=$checkpointNote})
    $rows.Add(@{metric='Log activity';value=('Last write '+(Format-T5Duration $context.age_seconds)+' ago');note=('Process observer refreshed '+(Format-T5Duration $producerAge)+' ago')})
    $pipeline=@(
        @{stage='Genome QC';status='METHOD DONE';progress='919 estimates; 900 in current analysis; 19 held'},
        @{stage='Markers / alignments';status='CORE READY';progress='54-marker core; 196 candidate alignments completed'},
        @{stage='Combined alignment';status='QC PASSED';progress='900 genomes x 54 markers; 13,071 amino-acid columns'},
        @{stage='Full-panel phylogeny';status=$status;progress=[string]$context.phase},
        @{stage='Independent tree QC';status='QUEUED';progress='After the full tree and branch-support output'},
        @{stage='Defences / rings';status='QUEUED';progress='5 genomes run by both tools; remaining queue follows'},
        @{stage='Representative tree';status='QUEUED';progress='Separate deliverable after the full-panel stage'}
    )
    $recent=@();foreach($line in @($context.events | Select-Object -Last 2)){$recent+=@{label='Reported';text=[string]$line}}
    $notes=@('Review: 19 genomes held; 3 markers withheld; 9 composition flags retained. Final validation is queued.')
    if(-not $verified){$notes=@('Owner identity not verified: the monitor cannot declare success or closure from a missing PID.')}
    $result=@{schema='TREE2_READ_ONLY_LIVE_MONITOR_V5';observed_at_utc=$now.ToString('o');observed_at_local=[DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss');
        headline=$headline;dataset='900 genomes | 54 markers | 13,071 AA columns | LG+F+G4 | full production';worker_verified=$verified;status_label=$status;
        current_rows=@($rows.ToArray());pipeline_rows=$pipeline;recent_events=$recent;notes=$notes;
        production_cumulative_seconds=$elapsed;prior_closed_production_seconds=$priorProduction;current_attempt_seconds=$attemptElapsed;requested_threads=$requestedThreads;observation=@{cpu=$cpu;log=$context};source_age_seconds=$producerAge;no_science_or_configuration_or_checkpoint_modified=$true}
    # Follow subsequent stages through existing published evidence, without changing the pipeline.
    try {
        $journal=Read-T5Json (Join-Path $ProjectRoot 'state/live_stages.json')
        $map=@{};foreach($entry in $journal.stages){$map[[string]$entry.id]=$entry}
        $pairs=@(@{id='04';index=0},@{id='06';index=1},@{id='07';index=2},@{id='08';index=3},@{id='09';index=4},@{id='10';index=5},@{id='12';index=6})
        foreach($pair in $pairs){
            $entry=$map[$pair.id];if(-not $entry){continue};$s=[string]$entry.status
            if($s -match '^(RUNNING|VERIFYING|PREPARING|STARTING|DOWNLOADING)'){$result.pipeline_rows[$pair.index].status='ACTIVE';if($pair.id -eq '08' -and $verified){$result.pipeline_rows[$pair.index].progress=[string]$context.phase}else{$result.pipeline_rows[$pair.index].progress=[string]$entry.detail}}
            elseif($s -eq 'NOT_STARTED'){$result.pipeline_rows[$pair.index].status='QUEUED'}
            elseif($s -match '^(FAILED|ERROR|BLOCKED|RESOURCE_LIMIT|TIMEOUT)'){$result.pipeline_rows[$pair.index].status='ATTENTION';$result.pipeline_rows[$pair.index].progress=[string]$entry.detail}
            elseif($s -match '^COMPUTED'){$result.pipeline_rows[$pair.index].status='COMPUTED';$result.pipeline_rows[$pair.index].progress='Computation finished; external verification pending'}
            elseif($s -match '^(VALIDATED|COMPLETED|ACCEPTED|ROOT_ACCEPTED)'){$result.pipeline_rows[$pair.index].status='COMPLETE';$result.pipeline_rows[$pair.index].progress=[string]$entry.detail}
        }
        $other=@($journal.stages | Where-Object {([string]$_.id -ne '08' -and [string]$_.status -match '^(RUNNING|VERIFYING|PREPARING|STARTING|DOWNLOADING)') -or ([string]$_.id -eq '08' -and $_.pid -and $_.pid -ne $run.worker.pid -and [string]$_.status -eq 'RUNNING')} | Sort-Object updated_utc -Descending)
        if(-not $verified -and $other.Count -gt 0){
            $focus=$other[0];$ptr=Read-T5Json (Join-Path $ProjectRoot 'state/local_continuation_current_runtime.json')
            $handoff=Read-T5Json (Join-Path $ProjectRoot ($ptr.state_directory+'/handoff.json'));$newLive=$false
            if($handoff.status -eq 'WAITING_WORKER' -and $focus.pid -eq $handoff.worker.pid){$newLive=([Tree2MonitorMetricsV5.Native]::LiveBirth([int]$handoff.worker.pid) -eq [long]$handoff.worker.windows_creation_filetime_100ns)}
            $genericRows=New-Object Collections.Generic.List[object]
            $genericRows.Add(@{metric='Current stage';value=[string]$focus.name;note='Automatically follows the published stage journal'})
            $genericRows.Add(@{metric='Actual task';value=(([string]$focus.operation) -replace '_',' ');note=[string]$focus.detail})
            $genericRows.Add(@{metric='State';value=[string]$focus.status;note=$(if($newLive){'Exact current native process identity verified'}else{'Published stage status; native owner not verified here'})})
            if($null -ne $focus.done -and $null -ne $focus.total -and [double]$focus.total -gt 1){$genericRows.Add(@{metric='Measured work';value=([string]$focus.done+' / '+[string]$focus.total);note=[string]$focus.unit})}
            if($focus.updated_utc){$genericRows.Add(@{metric='Last status update';value=((Format-T5Duration ([Math]::Max(0,($now-[DateTime]::Parse($focus.updated_utc).ToUniversalTime()).TotalSeconds)))+' ago');note='A status heartbeat is distinct from compute progress'})}
            $result.headline=[string]$focus.name;$result.status_label=[string]$focus.status;$result.worker_verified=$newLive
            $result.current_rows=@($genericRows.ToArray());$result.recent_events=@();$result.notes=@('Current stage and measured units are shown; no overall percentage is invented.');$result.dataset='Tree 2 | automatic stage continuation'
            if($focus.updated_utc){$result.source_age_seconds=[Math]::Max(0,($now-[DateTime]::Parse($focus.updated_utc).ToUniversalTime()).TotalSeconds)}
        }
    } catch { $result.notes+=@('Pipeline summary is temporarily unavailable; current production observations are retained.') }
    return $result
}
