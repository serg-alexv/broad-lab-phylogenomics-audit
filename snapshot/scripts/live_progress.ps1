[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [ValidateRange(1,60)][int]$RefreshSeconds = 3,
    [switch]$Once
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
$JournalPath = Join-Path $ProjectRoot 'state\live_stages.json'
$RootPrefix = $ProjectRoot + [IO.Path]::DirectorySeparatorChar
$LinuxRoot = if ($ProjectRoot -match '^([A-Za-z]):\\(.*)$') { '/mnt/' + $Matches[1].ToLowerInvariant() + '/' + $Matches[2].Replace('\','/') } else { $ProjectRoot }
try { $MoscowZone = [TimeZoneInfo]::FindSystemTimeZoneById('Russian Standard Time') }
catch { try { $MoscowZone = [TimeZoneInfo]::FindSystemTimeZoneById('Europe/Moscow') } catch { $MoscowZone = $null } }
try { [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false) } catch {}
try { $Host.UI.RawUI.WindowTitle = 'TREE 2 - WD - LIVE PROGRESS' } catch {}
$script:LastValid = $null
$script:LastReadUtc = $null
$script:ResourceText = 'Resources: obtaining current data'
$script:ResourceAt = [datetime]::MinValue

function Get-UtcDate($Value) {
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    try {
        if ($Value -is [datetime]) { return $Value.ToUniversalTime() }
        if ($Value -is [datetimeoffset]) { return $Value.UtcDateTime }
        return [datetimeoffset]::Parse([string]$Value, [Globalization.CultureInfo]::InvariantCulture).UtcDateTime
    } catch { return $null }
}
function Fit([string]$Text, [int]$Length) {
    $Text = ($Text -replace '[\r\n\t]+',' ').Trim()
    if ($Text.Length -le $Length) { return $Text.PadRight($Length) }
    if ($Length -lt 4) { return $Text.Substring(0,$Length) }
    return $Text.Substring(0,$Length-3) + '...'
}
function Get-Elapsed($Stage) {
    $Start = Get-UtcDate $Stage.started_utc
    if ($null -eq $Start) { return '-' }
    $End = Get-UtcDate $Stage.ended_utc
    if ($null -eq $End) { $End = [datetime]::UtcNow }
    $Seconds = [math]::Max(0, [math]::Floor(($End-$Start).TotalSeconds))
    return '{0:00}:{1:00}:{2:00}' -f [math]::Floor($Seconds/3600),[math]::Floor(($Seconds%3600)/60),($Seconds%60)
}
function Check-Worker($Stage) {
    $Result = @{ Verified=$false; Text='not registered'; Worker=$null }
    $WorkerId = 0
    if (-not [int]::TryParse([string]$Stage.pid,[ref]$WorkerId) -or $WorkerId -le 0) { return $Result }
    $Expected = Get-UtcDate $Stage.creation_time_utc
    if ($null -eq $Expected) { $Result.Text='creation identity missing'; return $Result }
    try {
        $Worker = Get-Process -Id $WorkerId -ErrorAction Stop
        if ($Worker.StartTime.ToUniversalTime().Ticks -ne $Expected.Ticks) { $Result.Text='PID reused / identity differs'; return $Result }
        $Record = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $WorkerId) -ErrorAction Stop
        $Command = [string]$Record.CommandLine
        $MatchesRoot = ($Command.Replace('/','\').IndexOf($ProjectRoot,[StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($Command.IndexOf($LinuxRoot,[StringComparison]::OrdinalIgnoreCase) -ge 0)
        if (-not $MatchesRoot) { $Result.Text='command path is unverified'; return $Result }
        $Result.Verified=$true; $Result.Worker=$Worker
        $Result.Text=('PID {0}; host CPU {1:N1}s; host RSS {2:N0} MiB' -f $WorkerId,$Worker.CPU,($Worker.WorkingSet64/1MB))
    } catch { $Result.Text='no matching live worker' }
    return $Result
}
function Read-Journal {
    $Warning = $null
    try {
        $Text = Get-Content -LiteralPath $JournalPath -Raw -Encoding UTF8 -ErrorAction Stop
        $Data = $Text | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $Data.stages) { throw 'The journal has no stages array.' }
        $script:LastValid=$Data; $script:LastReadUtc=[datetime]::UtcNow
    } catch {
        $Warning='Journal not currently readable: ' + $_.Exception.Message
    }
    if ($null -eq $script:LastValid) {
        $StageNames=@('WD resources and workspace','Taxonomy and source discovery','Sampling and source curation','Acquisition and integrity QC','Independent biological QC','Uniform gene prediction','Marker discovery and orthology','Alignments and concatenation','Full phylogenetic tree','Independent phylogenetic QC','PADLOC and DefenseFinder','Complete-system ring matrices','Representative tree','Conventional figures and release')
        $Fallback=@()
        for ($Number=0;$Number -lt $StageNames.Count;$Number++) {
            $Fallback += [pscustomobject]@{ id=('{0:00}' -f $Number); name=$StageNames[$Number]; status='NOT_REGISTERED'; detail='Waiting for the workflow stage journal; no running work inferred.' }
        }
        $script:LastValid=[pscustomobject]@{ project='TREE2_WD_20261026'; stages=$Fallback; updated_utc=$null }
    }
    return @{Data=$script:LastValid; Warning=$Warning}
}
function Get-Resources {
    if (([datetime]::UtcNow-$script:ResourceAt).TotalSeconds -lt 10) { return $script:ResourceText }
    try {
        $OS = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $Volume = Get-Item -LiteralPath $ProjectRoot -ErrorAction Stop
        $DriveName = $Volume.PSDrive.Name
        $Drive = Get-PSDrive -Name $DriveName -ErrorAction Stop
        $script:ResourceText = 'WD free RAM {0:N2} / {1:N2} GiB; {2}: free disk {3:N1} GiB' -f ($OS.FreePhysicalMemory/1MB),($OS.TotalVisibleMemorySize/1MB),$DriveName,($Drive.Free/1GB)
    } catch { $script:ResourceText='Resources: live resource query unavailable' }
    $script:ResourceAt=[datetime]::UtcNow
    return $script:ResourceText
}
function Get-Frame {
    $Read=Read-Journal; $Data=$Read.Data
    $Width=120
    try { if ([Console]::WindowWidth -ge 80) { $Width=[math]::Min(180,[Console]::WindowWidth) } } catch {}
    $Lines=New-Object 'Collections.Generic.List[string]'
    $NowUtc=[datetime]::UtcNow
    $Moscow = if ($null -ne $MoscowZone) { [TimeZoneInfo]::ConvertTimeFromUtc($NowUtc,$MoscowZone) } else { $NowUtc.AddHours(3) }
    $Lines.Add('TREE 2 - WD - LIVE PROGRESS    ' + $Moscow.ToString('yyyy-MM-dd HH:mm:ss') + ' MSK')
    $Lines.Add((Get-Resources))
    $Lines.Add('')
    $Updated=Get-UtcDate $Data.updated_utc
    if ($null -ne $Updated) {
        $Age=[math]::Max(0,[math]::Floor(($NowUtc-$Updated).TotalSeconds))
        $Lines.Add('Stage journal age: '+$Age+' s. Process identity is checked afresh; this is not an overall completion estimate.')
        if ($Age -gt 60) { $Lines.Add('NOTICE: progress journal is stale. A live worker below may still be working; inspect its log.') }
    } else { $Lines.Add('No usable stage timestamp yet. No scientific worker is assumed to be running.') }
    if ($Read.Warning) { $Lines.Add((Fit $Read.Warning $Width).TrimEnd()) }
    $Lines.Add('')
    $Lines.Add((Fit 'ID' 4)+(Fit 'Stage' 33)+(Fit 'Status' 25)+(Fit 'Recorded progress' 24)+'Elapsed')
    $Lines.Add(('-' * [math]::Min($Width,110)))
    $VerifiedActive=@(); $UnverifiedActive=@(); $Blocked=0; $Pending=0
    foreach ($Stage in @($Data.stages)) {
        $Code=([string]$Stage.status).ToUpperInvariant()
        $Display=if ([string]::IsNullOrWhiteSpace($Code)) {'UNKNOWN'} else {$Code}
        $Live=$null
        if ($Code -in @('RUNNING','STARTING','ACTIVE','VERIFYING')) {
            $Live=Check-Worker $Stage
            if ($Live.Verified) { $VerifiedActive+=@{Stage=$Stage;Live=$Live} }
            else { $Display='UNVERIFIED ACTIVITY'; $UnverifiedActive+=@{Stage=$Stage;Live=$Live} }
        }
        if ($Code -match 'BLOCK|HOLD|WAITING_AT_GATE') { $Blocked++ }
        if ($Code -in @('NOT_RUN','WAITING','PENDING','NOT_REGISTERED','QUEUED')) { $Pending++ }
        $Progress='-'
        if ($null -ne $Stage.done -and $null -ne $Stage.total -and [string]$Stage.done -ne '' -and [string]$Stage.total -ne '') { $Progress=('{0} / {1} {2}' -f $Stage.done,$Stage.total,$Stage.unit).Trim() }
        elseif ($null -ne $Stage.done -and [string]$Stage.done -ne '') { $Progress=('{0} {1}' -f $Stage.done,$Stage.unit).Trim() }
        $Lines.Add((Fit ([string]$Stage.id) 4)+(Fit ([string]$Stage.name) 33)+(Fit $Display 25)+(Fit $Progress 24)+(Get-Elapsed $Stage))
    }
    $Lines.Add('')
    if ($VerifiedActive.Count -gt 0) { $Lines.Add('UNDERWAY: '+$VerifiedActive.Count+' registered worker(s) have matching live process identity and project command path.') }
    elseif ($UnverifiedActive.Count -gt 0) { $Lines.Add('ATTENTION: reported activity has no verified live worker. Do not infer progress from an old PID or status file.') }
    elseif ($Blocked -gt 0) { $Lines.Add('WAITING AT A GATE: no registered scientific worker is currently verified active. See stage details above.') }
    elseif ($Pending -gt 0) { $Lines.Add('READY / WAITING: no registered scientific worker is currently verified active. Later stages have not started.') }
    else { $Lines.Add('No registered scientific worker is currently verified active. Read terminal receipts for completed stages.') }
    foreach ($Item in @($VerifiedActive)+@($UnverifiedActive)) {
        $Lines.Add(('Current '+[string]$Item.Stage.id+': '+[string]$Item.Stage.detail))
        $Lines.Add('    '+$Item.Live.Text)
    }
    $Gate = @($Data.stages | Where-Object { ([string]$_.status).ToUpperInvariant() -match 'BLOCK|HOLD|WAITING_AT_GATE' } | Select-Object -First 1)
    if ($Gate.Count -gt 0) { $Lines.Add(('Gate '+[string]$Gate[0].id+': '+(Fit ([string]$Gate[0].detail) ([math]::Max(50,$Width-12))).TrimEnd())) }
    $ActiveLog=$null
    if ($VerifiedActive.Count -gt 0) { $ActiveLog=$VerifiedActive[0].Stage.log_path }
    if (-not [string]::IsNullOrWhiteSpace([string]$ActiveLog)) {
        try {
            $LogPath = if ([IO.Path]::IsPathRooted([string]$ActiveLog)) { [IO.Path]::GetFullPath([string]$ActiveLog) } else { [IO.Path]::GetFullPath((Join-Path $ProjectRoot ([string]$ActiveLog))) }
            if (-not $LogPath.StartsWith($RootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Log is outside the project; not read.' }
            $Lines.Add(''); $Lines.Add('Latest active log: '+$LogPath)
            foreach($LogLine in @(Get-Content -LiteralPath $LogPath -Tail 3 -Encoding UTF8 -ErrorAction Stop)) { $Lines.Add((Fit ([string]$LogLine) $Width).TrimEnd()) }
        } catch { $Lines.Add('Active log not available yet: '+$_.Exception.Message) }
    }
    $Lines.Add(''); $Lines.Add('Refresh '+$RefreshSeconds+' s. Close this window or press Q to close only the monitor; workers continue.')
    $Lines.Add('Graceful workflow stop request: '+(Join-Path $ProjectRoot 'state\STOP'))
    $Lines.Add('Unknown / failed / unsearched defence calls remain unknown. Every later stage uses this same journal.')
    return [string]::Join([Environment]::NewLine,$Lines)
}
if ($Once) { Get-Frame; exit 0 }
while ($true) {
    try { $Frame=Get-Frame } catch { $Frame='Live monitor error: '+$_.Exception.Message+[Environment]::NewLine+'No worker status is inferred. Retrying shortly.' }
    try { Clear-Host } catch {}
    Write-Host $Frame
    $End=[datetime]::UtcNow.AddSeconds($RefreshSeconds)
    while ([datetime]::UtcNow -lt $End) {
        try { if ([Console]::KeyAvailable -and [Console]::ReadKey($true).Key -eq [ConsoleKey]::Q) { exit 0 } } catch {}
        Start-Sleep -Milliseconds 200
    }
}
