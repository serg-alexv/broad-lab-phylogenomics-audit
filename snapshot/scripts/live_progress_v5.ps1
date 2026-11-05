[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [ValidateRange(10,300)][int]$RefreshSeconds = 30,
    [string]$DataPath = '',
    [ValidateRange(90,160)][int]$TableWidth = 128,
    [string]$SnapshotPath = '',
    [switch]$Once
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
$RootPrefix = $ProjectRoot + [IO.Path]::DirectorySeparatorChar
if ([string]::IsNullOrWhiteSpace($DataPath)) { $DataPath = Join-Path $ProjectRoot 'state\monitor_v5\current.json' }
$DataPath = [IO.Path]::GetFullPath($DataPath)
if (-not $DataPath.StartsWith($RootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Monitor data must remain inside this Tree2 project' }
[IO.Directory]::CreateDirectory((Split-Path -Parent $DataPath)) | Out-Null
if ($SnapshotPath) {
    $SnapshotPath = [IO.Path]::GetFullPath($SnapshotPath)
    if (-not $SnapshotPath.StartsWith($RootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Monitor snapshot must remain inside this Tree2 project' }
}
$State = Join-Path $ProjectRoot 'state\monitor_display_v5'
[IO.Directory]::CreateDirectory($State) | Out-Null
$Born = (Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o')
$Utf8 = [Text.UTF8Encoding]::new($false)
$script:LastGoodFrame = $null
$script:LastData = $null
$script:FrameNumber = 0
$script:LastRenderedRows = 0
$script:LastRenderedWidth = 0
$script:RenderWidth = $TableWidth
$script:NativeReady = $false
$script:PreviousObservation = $null
$MetricsSource = Join-Path $ProjectRoot 'scripts\monitor_metrics_v5.ps1'
. $MetricsSource

function Save-Json([string]$Path,$Value) {
    $Temp = $Path + '.' + $PID + '.tmp'
    [IO.File]::WriteAllText($Temp,($Value | ConvertTo-Json -Depth 12),$Utf8)
    if ($script:NativeReady) {
        if (-not [Tree2V5Console]::MoveFileEx($Temp,$Path,9)) { throw 'Display receipt replacement failed' }
    } else { Move-Item -LiteralPath $Temp -Destination $Path -Force }
}
function Record-Error([string]$Phase,$Failure) {
    try {
        $Row = @{pid=$PID;creation_time_utc=$Born;at_utc=[datetime]::UtcNow.ToString('o');phase=$Phase;error=[string]$Failure}
        [IO.File]::AppendAllText((Join-Path $State 'render_errors.jsonl'),(($Row | ConvertTo-Json -Compress)+[Environment]::NewLine),$Utf8)
    } catch {}
}
function Clean([object]$Value) {
    if ($null -eq $Value) { return '' }
    return ([string]$Value -replace '[\r\n\t]+',' ' -replace '\s+',' ').Trim()
}
function Fit([object]$Value,[int]$Width) {
    $Text = Clean $Value
    if ($Text.Length -gt $Width) { return $Text.Substring(0,[Math]::Max(0,$Width-3))+'...' }
    return $Text.PadRight($Width)
}
function Add-Wrapped($Lines,[string]$Text,[int]$Width) {
    $Text = Clean $Text
    if (-not $Text) { return }
    while ($Text.Length -gt $Width) {
        $Cut = $Text.LastIndexOf(' ',$Width)
        if ($Cut -lt [Math]::Floor($Width/2)) { $Cut = $Width }
        $Lines.Add($Text.Substring(0,$Cut).TrimEnd())
        $Text = $Text.Substring($Cut).TrimStart()
    }
    $Lines.Add($Text)
}
function Split-Cell([object]$Value,[int]$Width) {
    $Text=Clean $Value
    if($Text.Length -le $Width){return $Text}
    $Cut=$Text.LastIndexOf(' ',$Width)
    if($Cut -lt [Math]::Floor($Width/2)){$Cut=$Width}
    $Text.Substring(0,$Cut).TrimEnd()
    Fit $Text.Substring($Cut).TrimStart() $Width
}
function Add-Table($Lines,$Rows,[string[]]$Columns,[int[]]$Widths) {
    $Border = '+' + (($Widths | ForEach-Object { '-' * ($_+2) }) -join '+') + '+'
    $Lines.Add($Border)
    $Cells = @(); for($i=0;$i -lt $Columns.Count;$i++){ $Cells += ' '+(Fit $Columns[$i] $Widths[$i])+' ' }
    $Lines.Add('|'+($Cells -join '|')+'|');$Lines.Add($Border)
    foreach($Row in @($Rows)) {
        $Wrapped=@();$Height=1
        for($i=0;$i -lt $Columns.Count;$i++){$Part=@(Split-Cell $Row[$i] $Widths[$i]);$Wrapped+=,$Part;$Height=[Math]::Max($Height,$Part.Count)}
        for($line=0;$line -lt $Height;$line++){
            $Cells=@()
            for($i=0;$i -lt $Columns.Count;$i++){$Value='';if($line -lt $Wrapped[$i].Count){$Value=$Wrapped[$i][$line]};$Cells+=' '+(Fit $Value $Widths[$i])+' '}
            $Lines.Add('|'+($Cells -join '|')+'|')
        }
    }
    $Lines.Add($Border)
}
function Get-DataAge($Data) {
    try { return [Math]::Max(0,([datetime]::UtcNow-([datetimeoffset]::Parse([string]$Data.observed_at_utc)).UtcDateTime).TotalSeconds) }
    catch { return $null }
}
function Get-Frame {
    $Data = Get-Tree2MonitorDataV5 -ProjectRoot $ProjectRoot -Previous $script:PreviousObservation
    if ($Data.schema -ne 'TREE2_READ_ONLY_LIVE_MONITOR_V5') { throw 'Unknown presentation data schema' }
    if (-not $Data.current_rows -or -not $Data.pipeline_rows) { throw 'Current-work and pipeline rows are required' }
    $script:LastData = $Data
    $script:PreviousObservation = $Data.observation
    Save-Json $DataPath $Data
    $Lines = [Collections.Generic.List[string]]::new()
    $Width = $TableWidth
    if(-not $Once){try{$Width=[Math]::Max(90,[Math]::Min($TableWidth,$Host.UI.RawUI.WindowSize.Width-2))}catch{}}
    $script:RenderWidth=$Width
    $Header = 'TREE 2  |  '+(Clean $Data.status_label)+'  |  '+(Clean $Data.headline)
    Add-Wrapped $Lines $Header $Width
    Add-Wrapped $Lines (Clean $Data.dataset) $Width
    $Age = Get-DataAge $Data
    if ($null -eq $Age) { $Lines.Add('DATA TIME UNKNOWN - retained values require a fresh observation.') }
    elseif ($Age -gt [Math]::Max(90,$RefreshSeconds*3)) { $Lines.Add(('DATA STALE: {0:N0}s old; displayed values are the last readable observation.' -f $Age)) }
    else { $Lines.Add('Updated '+(Clean $Data.observed_at_local)+'  |  Refresh '+$RefreshSeconds+'s') }
    $Lines.Add('')
    $Current = @(); foreach($Row in @($Data.current_rows | Select-Object -First 10)) { $Current += ,@((Clean $Row.metric),(Clean $Row.value),(Clean $Row.note)) }
    Add-Table $Lines $Current @('CURRENT WORK','OBSERVED VALUE','WHAT IT MEANS') @(24,36,($Width-70))
    $Lines.Add('')
    $Pipeline = @(); foreach($Row in @($Data.pipeline_rows | Select-Object -First 8)) { $Pipeline += ,@((Clean $Row.stage),(Clean $Row.status),(Clean $Row.progress)) }
    Add-Table $Lines $Pipeline @('PROJECT STAGE','STATE','RESULT / NEXT DEPENDENCY') @(26,17,($Width-53))
    if ($Data.recent_events) {
        $Lines.Add('')
        foreach($Event in @($Data.recent_events | Select-Object -Last 2)) { Add-Wrapped $Lines ((Clean $Event.label)+': '+(Clean $Event.text)) $Width }
    }
    foreach($Note in @($Data.notes | Select-Object -First 2)) { Add-Wrapped $Lines (Clean $Note) $Width }
    $Lines.Add('')
    $Lines.Add('Q closes this display only. Analysis and automatic supervision continue.')
    return [string]::Join([Environment]::NewLine,$Lines)
}
function Enable-StableConsole {
    $OldTemp=$env:TEMP;$OldTmp=$env:TMP
    try {
        $env:TEMP=Join-Path $State 'compile_temp';$env:TMP=$env:TEMP
        [IO.Directory]::CreateDirectory($env:TEMP) | Out-Null
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Tree2V5Console {
 [DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr GetStdHandle(int which);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetConsoleMode(IntPtr handle,out uint mode);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleMode(IntPtr handle,uint mode);
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool MoveFileEx(string source,string target,uint flags);
 [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
}
'@
        $script:NativeReady=$true
        $InputHandle=[Tree2V5Console]::GetStdHandle(-10);[uint32]$Before=0;[uint32]$After=0
        if (-not [Tree2V5Console]::GetConsoleMode($InputHandle,[ref]$Before)) { throw 'Own console input mode unavailable' }
        [uint32]$Mode=($Before -bor 0x80) -band ([uint32]::MaxValue -bxor [uint32]0x40)
        if (-not [Tree2V5Console]::SetConsoleMode($InputHandle,$Mode)) { throw 'Own QuickEdit change failed' }
        if (-not [Tree2V5Console]::GetConsoleMode($InputHandle,[ref]$After) -or ($After -band 0x40)) { throw 'Own QuickEdit disable unverified' }
        Save-Json (Join-Path $State 'stable_console_mode.json') @{pid=$PID;creation_time_utc=$Born;before_mode=$Before;after_mode=$After;quick_edit_enabled=$false;console_window=[Tree2V5Console]::GetConsoleWindow().ToInt64();scope='OWN_CONSOLE_ONLY';at_utc=[datetime]::UtcNow.ToString('o')}
    } finally { $env:TEMP=$OldTemp;$env:TMP=$OldTmp }
    try {$Host.UI.RawUI.WindowTitle='TREE 2 - LIVE PROGRESS V5';[Console]::OutputEncoding=$Utf8;[Console]::CursorVisible=$false}catch{}
}

if ($Once) {
    $Frame=Get-Frame
    if ($SnapshotPath) { [IO.Directory]::CreateDirectory((Split-Path -Parent $SnapshotPath)) | Out-Null;[IO.File]::WriteAllText($SnapshotPath,$Frame,$Utf8) }
    [Console]::WriteLine($Frame)
    exit 0
}
try { Enable-StableConsole } catch { Record-Error 'CONSOLE_MODE' $_.Exception;throw }
while ($true) {
    $ReadError=$null
    try { $Frame=Get-Frame;$script:LastGoodFrame=$Frame }
    catch {
        $ReadError=$_.Exception.Message;Record-Error 'READ_FRAME' $_.Exception
        $Banner='DISPLAY DATA UNAVAILABLE: retaining last readable frame. Retrying in '+$RefreshSeconds+'s.'
        $Frame=$Banner+[Environment]::NewLine+$(if($script:LastGoodFrame){$script:LastGoodFrame}else{'No readable data yet. No worker status or completion is inferred.'})
    }
    $Rendered=$false
    try {
        try {[Console]::SetCursorPosition(0,0)}catch{}
        $Rows=$Frame -split '\r?\n'
        $EraseWidth=[Math]::Max($script:RenderWidth,$script:LastRenderedWidth)
        try{$EraseWidth=[Math]::Min($EraseWidth,[Console]::BufferWidth-1)}catch{}
        foreach($Line in $Rows) { [Console]::WriteLine($Line.PadRight($EraseWidth)) }
        if($script:LastRenderedRows -gt $Rows.Count) { for($i=$Rows.Count;$i -lt $script:LastRenderedRows;$i++){[Console]::WriteLine(' ' * $EraseWidth)} }
        $script:LastRenderedRows=$Rows.Count;$script:LastRenderedWidth=$script:RenderWidth;$Rendered=$true;$script:FrameNumber++
        try {[Console]::SetWindowPosition(0,0)}catch{}
    } catch { Record-Error 'RENDER_FRAME' $_.Exception }
    try {
        [IO.File]::WriteAllText((Join-Path $State 'display_last_frame.txt'),$Frame,$Utf8)
        if($script:LastGoodFrame){[IO.File]::WriteAllText((Join-Path $State 'last_known_good_frame.txt'),$script:LastGoodFrame,$Utf8)}
        Save-Json (Join-Path $State 'display_health.json') @{pid=$PID;creation_time_utc=$Born;frame=$script:FrameNumber;updated_utc=[datetime]::UtcNow.ToString('o');rendered=$Rendered;read_error=$ReadError;refresh_seconds=$RefreshSeconds;table_width=$script:RenderWidth;rows=$script:LastRenderedRows;title='TREE 2 - LIVE PROGRESS V5';data_schema=$script:LastData.schema;data_observed_at_utc=$script:LastData.observed_at_utc;status_label=$script:LastData.status_label;headline=$script:LastData.headline;worker_verified=$script:LastData.worker_verified;role='VISIBLE_PRESENTATION_ONLY_NOT_SCIENTIFIC_WORKER'}
    } catch { Record-Error 'SAVE_FRAME' $_.Exception }
    $Until=[datetime]::UtcNow.AddSeconds($RefreshSeconds)
    while([datetime]::UtcNow -lt $Until){
        try {if([Console]::KeyAvailable -and [Console]::ReadKey($true).Key -eq [ConsoleKey]::Q){try{[Console]::CursorVisible=$true}catch{};exit 0}}catch{}
        Start-Sleep -Milliseconds 200
    }
}
