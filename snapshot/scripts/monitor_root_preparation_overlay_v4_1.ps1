# Presentation-only read of public process metadata. Never reads CLI prompts or sessions.
function Confirm-PresentationOwnerV41($Identity,[string]$SourcePath=''){
    if(-not $Identity -or -not $Identity.pid -or -not $Identity.windows_creation_filetime_100ns){return $false}
    $Process=$null
    try{
        $Process=Get-Process -Id ([int]$Identity.pid) -ErrorAction Stop
        if($Process.StartTime.ToUniversalTime().ToFileTimeUtc() -ne [long]$Identity.windows_creation_filetime_100ns){return $false}
        if($SourcePath){
            $Record=Get-CimInstance Win32_Process -Filter ('ProcessId='+$Identity.pid) -ErrorAction Stop
            if(([string]$Record.CommandLine).IndexOf($SourcePath,[StringComparison]::OrdinalIgnoreCase) -lt 0){return $false}
        }
        return $true
    }catch{return $false}finally{if($Process){$Process.Dispose()}}
}

function Get-LocalRootPresentationV41([string]$Root){
    try{
        $Runtime=Read-MonitorSharedJson (Join-Path $Root 'state\local_continuation_current_runtime.json')
        $Roles=Read-MonitorSharedJson (Resolve-MonitorArtifactV4 $Root $Runtime.actual_runtime_roles)
        $Dispatcher=@($Roles.roles|Where-Object {$_.role -eq 'ROOT_LOCAL_RUNTIME_CONTROLLER'})
        if($Dispatcher.Count -ne 1){throw 'No exact local controller role'}
        $SourcePath=Resolve-MonitorArtifactV4 $Root $Dispatcher[0].source
        if(-not (Confirm-PresentationOwnerV41 $Dispatcher[0].identity $SourcePath)){throw 'Controller birth/source unverified'}
        $Directory=[IO.Path]::GetFullPath((Join-Path $Root ([string]$Runtime.state_directory)))
        if(-not $Directory.StartsWith($Root.TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Runtime directory escapes project'}
        $Status=Read-MonitorSharedJson (Join-Path $Directory 'dispatcher_status.json')
        if($Status.status -ne 'AI_TURN_ACTIVE' -or [int]$Status.dispatcher_pid -ne [int]$Dispatcher[0].identity.pid){throw 'Controller is not reporting an active preparation turn'}
        $Checkpoint=Read-MonitorSharedJson (Join-Path $Directory 'checkpoint.json')
        if([string]$Checkpoint.pending_event.sha256 -ne [string]$Status.event_sha256){throw 'Current event binding differs'}
        $EventPath=Resolve-MonitorArtifactV4 $Root $Checkpoint.pending_event
        $EventDirectory=Split-Path -Parent $EventPath
        $Started=Read-MonitorSharedJson (Join-Path $EventDirectory 'cli_started.json')
        if([string]$Started.event_sha256 -ne [string]$Status.event_sha256 -or -not (Confirm-PresentationOwnerV41 $Started.identity)){throw 'Current CLI birth/event unverified'}
        $Cli=Get-CimInstance -Query ('SELECT ProcessId,ParentProcessId,ExecutablePath FROM Win32_Process WHERE ProcessId='+$Started.identity.pid) -ErrorAction Stop
        if([int]$Cli.ParentProcessId -ne [int]$Dispatcher[0].identity.pid -or [IO.Path]::GetFileName([string]$Cli.ExecutablePath) -ne 'codex.exe'){throw 'Current CLI parent/executable unverified'}
        $Category='PREPARATION';$Reason='The local controller is reviewing or preparing the next queue work; actual controller and CLI births verified. Genome processing is not inferred.'
        $Semantic=Join-Path $EventDirectory 'semantic_turn_completed.json'
        if(Test-Path -LiteralPath $Semantic){
            $Finished=Read-MonitorSharedJson $Semantic
            if([string]$Finished.event_sha256 -eq [string]$Status.event_sha256){$Category='CLEANUP';$Reason='The local controller finished its model turn and is closing the CLI; this is not genome processing.'}
        }
        return @{Verified=$true;Category=$Category;Reason=$Reason;DispatcherOwner=$Dispatcher[0].identity;CliOwner=$Started.identity;Evidence='PUBLIC_CURRENT_EVENT_AND_EXACT_OS_BIRTHS';NoGenomeProcessingInference=$true}
    }catch{return @{Verified=$false;Reason=$_.Exception.Message;NoGenomeProcessingInference=$true}}
}

function Get-LastFailedAttemptV41([string]$Root,$Stage){
    try{
        $Reference=$Stage.terminal_receipt
        if(-not $Reference){
            $Policy=Read-MonitorSharedJson (Join-Path $Root 'metadata\monitor_display_v4_1\presentation_policy.json')
            $Reference=$Policy.initial_last_failed_attempt
        }
        $Value=Read-MonitorSharedJson (Resolve-MonitorArtifactV4 $Root $Reference)
        if($Value.failure_kind -or [string]$Value.status -match 'FAIL|TIMEOUT|STOPPED'){
            return @{status=$(if($Value.failure_kind){[string]$Value.failure_kind}else{[string]$Value.status});detail=('Recorded failed attempt; native exit '+[string]$Value.actual_native_exit_code+', WSL exit '+[string]$Value.actual_WSL_exit_code+'. Original attempts/debits and closure evidence remain retained.');receipt=$Reference}
        }
    }catch{}
    if([string]$Stage.status -match 'FAIL|ERROR|STOPPED'){return @{status=[string]$Stage.status;detail=[string]$Stage.detail}}
    return @{}
}

function Merge-RootPresentationV41($Primary,$Observation,$LastStage,[bool]$AnyLiveScientificOwner){
    $Result=@{};foreach($Key in $Primary.Keys){$Result[$Key]=$Primary[$Key]}
    if(-not $AnyLiveScientificOwner -and $Observation.Verified -eq $true -and $Observation.Category -in @('PREPARATION','CLEANUP')){
        $Result.Category=$Observation.Category;$Result.Reason=$Observation.Reason
        $Result.ProcessingReported=$false;$Result.NativeVerified=$false;$Result.ControllerVerified=$true
        $Result.RootController=$Observation.DispatcherOwner;$Result.RootCli=$Observation.CliOwner
        $Result.CurrentModeSource='LOCAL_CONTROLLER_PUBLIC_EVENT_AND_OS_IDENTITY'
        $Result.LastAttemptStatus=[string]$LastStage.status;$Result.LastAttemptDetail=[string]$LastStage.detail
        $Result.DeclaredUnit=''
    }
    return $Result
}
