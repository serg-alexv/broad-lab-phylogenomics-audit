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
if ([string]::IsNullOrWhiteSpace($DataPath)) { $DataPath = Join-Path $ProjectRoot 'state\monitor_v5_3\current.json' }
$DataPath = [IO.Path]::GetFullPath($DataPath)
if (-not $DataPath.StartsWith($RootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Monitor data must remain inside this Tree2 project' }
[IO.Directory]::CreateDirectory((Split-Path -Parent $DataPath)) | Out-Null
if ($SnapshotPath) {
    $SnapshotPath = [IO.Path]::GetFullPath($SnapshotPath)
    if (-not $SnapshotPath.StartsWith($RootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Monitor snapshot must remain inside this Tree2 project' }
}
$State = Join-Path $ProjectRoot 'state\monitor_display_v5_3'
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
$MetricsSource = Join-Path $ProjectRoot 'scripts\monitor_metrics_v5_3.ps1'
. $MetricsSource

function Save-Json([string]$Path,$Value) {
    $Temp = $Path + '.' + $PID + '.tmp'
    [IO.File]::WriteAllText($Temp,($Value | ConvertTo-Json -Depth 12),$Utf8)
    if ($script:NativeReady) {
        if (-not [Tree2V53Console]::MoveFileEx($Temp,$Path,9)) { throw 'Display receipt replacement failed' }
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
    if(Clean $Text){$Lines.Add((Fit $Text $Width).TrimEnd())}
}
function Add-Table($Lines,$Rows,[string[]]$Columns,[int[]]$Widths) {
    $Border='+'+(($Widths|ForEach-Object{'-'*($_+2)}) -join '+')+'+'
    $Lines.Add($Border)
    $Cells=@();for($i=0;$i -lt $Columns.Count;$i++){$Cells+=' '+(Fit $Columns[$i] $Widths[$i])+' '}
    $Lines.Add('|'+($Cells -join '|')+'|');$Lines.Add($Border)
    foreach($Row in @($Rows)){
        $Cells=@();for($i=0;$i -lt $Columns.Count;$i++){$Cells+=' '+(Fit $Row[$i] $Widths[$i])+' '}
        $Lines.Add('|'+($Cells -join '|')+'|')
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
    if(-not $Once){$geo=[Tree2V53Console]::Geometry($script:ConsoleOut);$Width=[Math]::Min($TableWidth,$geo[0]-2);if($Width -lt 80){throw 'Own console is too narrow for the bounded tables'}}
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
    $Lines.Add('Refresh '+$RefreshSeconds+'s | Close window to dismiss; scientific work continues.')
    return [string]::Join([Environment]::NewLine,$Lines)
}
function Enable-StableConsole {
    $oldTemp=$env:TEMP;$oldTmp=$env:TMP
    try {
        $env:TEMP=Join-Path $State 'compile_temp';$env:TMP=$env:TEMP
        [void][IO.Directory]::CreateDirectory($env:TEMP)
        Add-Type -TypeDefinition @'
using System; using System.ComponentModel; using System.Runtime.InteropServices;
public static class Tree2V53Console {
 [StructLayout(LayoutKind.Sequential)] public struct COORD {public short X,Y; public COORD(short x,short y){X=x;Y=y;}}
 [StructLayout(LayoutKind.Sequential)] public struct RECT {public short Left,Top,Right,Bottom;}
 [StructLayout(LayoutKind.Sequential)] public struct BUFFER {public COORD Size,Cursor;public ushort Attributes;public RECT Window;public COORD MaximumWindow;}
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetConsoleScreenBufferInfo(IntPtr h,out BUFFER info);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleCursorPosition(IntPtr h,COORD p);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleWindowInfo(IntPtr h,bool absolute,ref RECT rect);
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool WriteConsoleOutputCharacter(IntPtr h,string text,uint count,COORD start,out uint written);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetConsoleMode(IntPtr h,out uint mode);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleMode(IntPtr h,uint mode);
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern bool MoveFileEx(string source,string target,uint flags);
 [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool AllocConsole();
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] public static extern IntPtr CreateFile(string path,uint access,uint share,IntPtr security,uint creation,uint flags,IntPtr template);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] public static extern bool SetConsoleTitle(string title);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int command);
 static void Check(bool ok,string operation){if(!ok)throw new Win32Exception(Marshal.GetLastWin32Error(),operation);}
 public static int[] Geometry(IntPtr h){BUFFER b;Check(GetConsoleScreenBufferInfo(h,out b),"Own console geometry");return new int[]{b.Window.Right-b.Window.Left+1,b.Window.Bottom-b.Window.Top+1,b.Size.X,b.Size.Y,b.Window.Left,b.Window.Top};}
 public static int[] Draw(IntPtr h,string[] lines){
  BUFFER b;Check(GetConsoleScreenBufferInfo(h,out b),"Own console geometry before frame");
  int width=b.Window.Right-b.Window.Left+1,height=b.Window.Bottom-b.Window.Top+1;
  if(lines.Length>height-2)throw new InvalidOperationException("Frame exceeds the visible viewport safe margin");
  foreach(string line in lines)if(line.Length>width-2)throw new InvalidOperationException("Frame exceeds the visible viewport width");
  RECT rect=new RECT{Left=0,Top=0,Right=(short)(width-1),Bottom=(short)(height-1)};
  Check(SetConsoleWindowInfo(h,true,ref rect),"Reset own viewport before frame");
  for(int y=0;y<height;y++){
   string line=(y<lines.Length?lines[y]:"").PadRight(width);
   uint written;Check(WriteConsoleOutputCharacter(h,line,(uint)line.Length,new COORD(0,(short)y),out written),"Write own fixed console row");
   if(written!=line.Length)throw new InvalidOperationException("Incomplete own console row write");
  }
  Check(SetConsoleCursorPosition(h,new COORD(0,0)),"Reset own console cursor");
  Check(SetConsoleWindowInfo(h,true,ref rect),"Reset own viewport after frame");
  Check(GetConsoleScreenBufferInfo(h,out b),"Verify own viewport after frame");
  if(b.Window.Left!=0||b.Window.Top!=0||b.Cursor.X!=0||b.Cursor.Y!=0)throw new InvalidOperationException("Own viewport/cursor reset not retained");
  return new int[]{width,height,lines.Length,b.Window.Top,b.Cursor.Y};
 }
}
'@
        if([Tree2V53Console]::GetConsoleWindow() -eq [IntPtr]::Zero -and -not [Tree2V53Console]::AllocConsole()){throw 'Own visible console allocation failed'}
        $script:ConsoleOut=[Tree2V53Console]::CreateFile('CONOUT$',[uint32]::Parse('3221225472'),3,[IntPtr]::Zero,3,0,[IntPtr]::Zero)
        $script:ConsoleIn=[Tree2V53Console]::CreateFile('CONIN$',[uint32]::Parse('3221225472'),3,[IntPtr]::Zero,3,0,[IntPtr]::Zero)
        if($script:ConsoleOut.ToInt64() -eq -1 -or $script:ConsoleIn.ToInt64() -eq -1){throw 'Own explicit console handles unavailable'}
        [uint32]$mode=0
        if(-not [Tree2V53Console]::GetConsoleMode($script:ConsoleIn,[ref]$mode)){throw 'Own input mode unavailable'}
        $mode=($mode -bor 0x80) -band ([uint32]::MaxValue -bxor [uint32]0x40)
        if(-not [Tree2V53Console]::SetConsoleMode($script:ConsoleIn,$mode)){throw 'Own QuickEdit disable failed'}
        [uint32]$verifiedMode=0
        if(-not [Tree2V53Console]::GetConsoleMode($script:ConsoleIn,[ref]$verifiedMode) -or ($verifiedMode -band 0x40)){throw 'Own QuickEdit disable not verified'}
        if(-not [Tree2V53Console]::SetConsoleTitle('TREE 2 - LIVE PROGRESS V5.3')){throw 'Own title update failed'}
        [void][Tree2V53Console]::ShowWindow([Tree2V53Console]::GetConsoleWindow(),3)
        $script:NativeReady=$true
        Save-Json (Join-Path $State 'stable_console_mode.json') @{pid=$PID;creation_time_utc=$Born;quick_edit_enabled=$false;own_explicit_CONOUT_handle=$true;scope='OWN_CONSOLE_ONLY';at_utc=[DateTime]::UtcNow.ToString('o')}
    } finally {$env:TEMP=$oldTemp;$env:TMP=$oldTmp}
}

if ($Once) {
    $Frame=Get-Frame
    if ($SnapshotPath) { [IO.Directory]::CreateDirectory((Split-Path -Parent $SnapshotPath)) | Out-Null;[IO.File]::WriteAllText($SnapshotPath,$Frame,$Utf8) }
    [Console]::WriteLine($Frame)
    exit 0
}
try { Enable-StableConsole } catch { Record-Error 'CONSOLE_MODE' $_.Exception;throw }
# Presentation lifetime is bounded by the unchanged production deadline; Q remains display-only.
$DisplayDeadline=[DateTimeOffset]::FromUnixTimeSeconds(1793887122).UtcDateTime
while ([DateTime]::UtcNow -lt $DisplayDeadline) {
    $ReadError=$null
    try { $Frame=Get-Frame;$script:LastGoodFrame=$Frame }
    catch {
        $ReadError=$_.Exception.Message;Record-Error 'READ_FRAME' $_.Exception
        $Banner='DISPLAY DATA UNAVAILABLE: retaining last readable frame. Retrying in '+$RefreshSeconds+'s.'
        $Frame=$Banner+[Environment]::NewLine+$(if($script:LastGoodFrame){$script:LastGoodFrame}else{'No readable data yet. No worker status or completion is inferred.'})
    }
    $Rendered=$false
    try {
        $Rows=$Frame -split '\r?\n'
        $native=[Tree2V53Console]::Draw($script:ConsoleOut,[string[]]$Rows)
        $script:LastRenderedRows=$Rows.Count;$script:LastRenderedWidth=$script:RenderWidth
        $Rendered=$true;$script:FrameNumber++
        $script:LastNativeProof=@{visible_width=$native[0];visible_height=$native[1];frame_rows=$native[2];viewport_top=$native[3];cursor_y=$native[4];checked_native_write=$true}
    } catch {Record-Error 'RENDER_FRAME' $_.Exception;throw}
    try {
        [IO.File]::WriteAllText((Join-Path $State 'display_last_frame.txt'),$Frame,$Utf8)
        if($script:LastGoodFrame){[IO.File]::WriteAllText((Join-Path $State 'last_known_good_frame.txt'),$script:LastGoodFrame,$Utf8)}
        Save-Json (Join-Path $State 'display_health.json') @{pid=$PID;creation_time_utc=$Born;frame=$script:FrameNumber;updated_utc=[datetime]::UtcNow.ToString('o');rendered=$Rendered;read_error=$ReadError;refresh_seconds=$RefreshSeconds;table_width=$script:RenderWidth;rows=$script:LastRenderedRows;native_viewport=$script:LastNativeProof;title='TREE 2 - LIVE PROGRESS V5.3';data_schema=$script:LastData.schema;data_observed_at_utc=$script:LastData.observed_at_utc;status_label=$script:LastData.status_label;headline=$script:LastData.headline;worker_verified=$script:LastData.worker_verified;role='VISIBLE_PRESENTATION_ONLY_NOT_SCIENTIFIC_WORKER'}
    } catch { Record-Error 'SAVE_FRAME' $_.Exception }
    $Until=[datetime]::UtcNow.AddSeconds($RefreshSeconds)
    while([datetime]::UtcNow -lt $Until){
        Start-Sleep -Milliseconds 200
    }
}
