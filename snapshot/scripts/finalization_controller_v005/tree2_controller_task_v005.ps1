[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$AuthoritySha256)
$ErrorActionPreference='Stop'
$Root='C:\Users\wheel\Documents\Codex\2026-10-26\referenced-chatgpt-conversation-this-is-an\outputs\TREE2_WD_20261026'
$Directory=Join-Path $Root 'metadata\finalization_recovery_20261103\controller'
$Runtime='C:\Users\wheel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$RuntimeSha='f8b45d63047da9d9adf09892e4cc4317b859e86a93a478cc9616bc69d3b176e5'
$Entry=Join-Path $Root 'scripts\finalization_controller_v005\tree2_controller_task_entry_v005.py'
$Wrapper=Join-Path $Root 'scripts\finalization_controller_v005\tree2_controller_task_v005.ps1'
$Launcher=Join-Path $Root 'scripts\finalization_controller_v005\tree2_controller_launcher_v005.py'
$SpecPath=Join-Path $Directory 'task_spec.json'
$AuthorityPath=Join-Path $Directory 'Root_authority.json'
$ReceiptPath=Join-Path $Directory 'task_registration_receipt.json'
$RegisteredXml=Join-Path $Directory 'task.registered.xml'
$Utf8=[Text.UTF8Encoding]::new($false,$true)

function Get-Sha([byte[]]$Bytes) {
 $Hash=[Security.Cryptography.SHA256]::Create()
 try{return [BitConverter]::ToString($Hash.ComputeHash($Bytes)).Replace('-','').ToLowerInvariant()}finally{$Hash.Dispose()}
}
function Get-Row([string]$Path) {
 $Path=[IO.Path]::GetFullPath($Path);$Bytes=[IO.File]::ReadAllBytes($Path)
 return [pscustomobject][ordered]@{path=$Path;bytes=[long]$Bytes.Length;sha256=(Get-Sha $Bytes)}
}
function Assert-Row($Row,[string]$Path) {
 $Actual=Get-Row $Path
 if($null -eq $Row -or @($Row.PSObject.Properties).Count -ne 3 -or $Row.path -cne $Actual.path -or $Row.bytes -ne $Actual.bytes -or $Row.sha256 -cne $Actual.sha256){throw ('Exact fixed Task file pin differs: '+$Path)}
}
function Assert-PowerShellRow($Row,[string]$Path) {
 # SystemRoot is C:\WINDOWS here while canonical file rows use C:\Windows.
 # This native executable comparison alone is case-insensitive; bytes/hash stay exact.
 $Actual=Get-Row $Path
 if($null -eq $Row -or @($Row.PSObject.Properties).Count -ne 3 -or $Row.path -ine $Actual.path -or $Row.bytes -ne $Actual.bytes -or $Row.sha256 -cne $Actual.sha256){throw 'Exact native PowerShell binary pin differs'}
}
function Read-Json([string]$Path) {return $Utf8.GetString([IO.File]::ReadAllBytes($Path)).TrimStart([char]0xfeff) | ConvertFrom-Json}
function Write-ExclusiveJson([string]$Path,$Value) {
 $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Path))
 $Bytes=$Utf8.GetBytes(($Value | ConvertTo-Json -Depth 16)+"`n")
 $File=[IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$File.Write($Bytes,0,$Bytes.Length);$File.Flush($true)}finally{$File.Dispose()}
}
function Get-ArgumentsTemplate {return '-NoProfile -NonInteractive -WindowStyle Hidden -File "'+$Wrapper+'" -AuthoritySha256 {{AUTHORITY_SHA256}}'}
function Initialize-Native {
 if('CodexTree2TaskV005.Native' -as [type]){return}
 $CompilerTemp=Join-Path $Root 'work\finalization_controller_v005\compiler_temp'
 $null=[IO.Directory]::CreateDirectory($CompilerTemp)
 $PriorTemp=[Environment]::GetEnvironmentVariable('TEMP','Process')
 $PriorTmp=[Environment]::GetEnvironmentVariable('TMP','Process')
 try {
 [Environment]::SetEnvironmentVariable('TEMP',$CompilerTemp,'Process')
 [Environment]::SetEnvironmentVariable('TMP',$CompilerTemp,'Process')
 Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
namespace CodexTree2TaskV005 {
 public static class Native {
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetProcessTimes(IntPtr h,out long born,out long ended,out long kernel,out long user);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr h,out uint code);
  [DllImport("kernel32.dll", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr h,uint ms);
  [DllImport("kernel32.dll", SetLastError=true,CharSet=CharSet.Unicode)] static extern bool QueryFullProcessImageName(IntPtr h,uint flags,StringBuilder text,ref uint length);
  public static Dictionary<string,object> Identity(IntPtr h,int pid) {
   long born,ended,kernel,user;if(!GetProcessTimes(h,out born,out ended,out kernel,out user))throw new Win32Exception();
   return new Dictionary<string,object>{{"pid",pid},{"windows_creation_filetime_100ns",born},{"creation_time_utc",DateTime.FromFileTimeUtc(born).ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")}};
  }
  public static uint Wait(IntPtr h,uint ms) {uint result=WaitForSingleObject(h,ms);if(result!=0 && result!=258)throw new Win32Exception();return result;}
  public static uint ExitCode(IntPtr h) {if(Wait(h,0)!=0)throw new InvalidOperationException("Actual exit required");uint code;if(!GetExitCodeProcess(h,out code))throw new Win32Exception();return code;}
  public static string Image(IntPtr h) {var text=new StringBuilder(32768);uint size=32768;if(!QueryFullProcessImageName(h,0,text,ref size))throw new Win32Exception();return text.ToString();}
 }
}
'@
 } finally {
  [Environment]::SetEnvironmentVariable('TEMP',$PriorTemp,'Process')
  [Environment]::SetEnvironmentVariable('TMP',$PriorTmp,'Process')
 }
}
function Test-Identity($Left,$Right) {
 return ($null -ne $Left -and $null -ne $Right -and $Left.pid -gt 0 -and $Left.windows_creation_filetime_100ns -gt 0 -and $Left.creation_time_utc -match '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z$' -and $Left.pid -eq $Right.pid -and $Left.windows_creation_filetime_100ns -eq $Right.windows_creation_filetime_100ns -and $Left.creation_time_utc -ceq $Right.creation_time_utc)
}
function Get-TaskBinding($Authority,[string]$Sha) {
 Assert-Row $Authority.task_spec $SpecPath
 $Spec=Read-Json $SpecPath
 $Sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 $PowerShell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 if($Spec.schema -cne 'TREE2_V005_FIXED_TASK_SPEC_V1' -or $Spec.task_name -cne 'CodexTree2CustodianV005-wheel' -or $Spec.task_path -cne '\Codex\' -or $Spec.user_sid -cne $Sid -or $Spec.working_directory -cne $Root -or $Spec.arguments_template -cne (Get-ArgumentsTemplate) -or $Spec.logon_type -cne 'InteractiveToken' -or $Spec.run_level -cne 'Limited' -or $Spec.trigger_count -ne 0 -or $Spec.restart_count -ne 0 -or $Spec.multiple_instances -cne 'IgnoreNew' -or $Spec.execution_time_limit -cne 'PT0S' -or $Spec.allow_hard_terminate -ne $false -or $Spec.expected_job_limit_flags -ne 0){throw 'Fixed stable Task descriptor differs'}
 Assert-PowerShellRow $Spec.powershell $PowerShell
 $Task=Get-ScheduledTask -TaskName 'CodexTree2CustodianV005-wheel' -TaskPath '\Codex\'
 $PrincipalId=[string]$Task.Principal.UserId
 $ActualSid=if($PrincipalId.StartsWith('S-1-')){$PrincipalId}else{([Security.Principal.NTAccount]::new($PrincipalId)).Translate([Security.Principal.SecurityIdentifier]).Value}
 $Arguments=(Get-ArgumentsTemplate).Replace('{{AUTHORITY_SHA256}}',$Sha)
 if([string]$Task.State -ne 'Running' -or $ActualSid -cne $Sid -or [string]$Task.Principal.RunLevel -ne 'Limited' -or [string]$Task.Principal.LogonType -notin @('Interactive','InteractiveToken') -or @($Task.Actions).Count -ne 1 -or @($Task.Triggers | Where-Object {$null -ne $_}).Count -ne 0 -or $Task.Actions[0].Execute -ine $PowerShell -or $Task.Actions[0].Arguments -cne $Arguments -or $Task.Actions[0].WorkingDirectory -cne $Root -or $Task.Settings.RestartCount -ne 0 -or [string]$Task.Settings.MultipleInstances -ne 'IgnoreNew' -or [string]$Task.Settings.ExecutionTimeLimit -ne 'PT0S' -or $Task.Settings.AllowHardTerminate -ne $false){throw 'Actual exact current-user Task/action/settings differ'}
 $Receipt=Read-Json $ReceiptPath
 $XmlRow=Get-Row $RegisteredXml
 if($Receipt.schema -cne 'TREE2_FIXED_TASK_PHASE_UPDATE_V1' -or $Receipt.phase -cne 'Controller' -or $Receipt.registered -ne $true -or $Receipt.task_name -cne $Spec.task_name -or $Receipt.task_path -cne $Spec.task_path -or $Receipt.user_sid -cne $Sid -or $Receipt.root -cne $Root -or $Receipt.phase_source -cne $Wrapper -or $Receipt.phase_source_sha256 -cne $Authority.task_wrapper.sha256 -or $Receipt.registered_xml_sha256 -cne $XmlRow.sha256){throw 'Fixed final Controller registration receipt differs'}
 $Export=Export-ScheduledTask -TaskName 'CodexTree2CustodianV005-wheel' -TaskPath '\Codex\'
 $Bytes=[Text.Encoding]::Unicode.GetPreamble()+[Text.Encoding]::Unicode.GetBytes($Export)
 if((Get-Sha $Bytes) -cne $XmlRow.sha256){throw 'Actual Task XML differs from final registered receipt'}
 return [pscustomobject]@{spec=$Spec;receipt=(Get-Row $ReceiptPath);xml=$XmlRow}
}
function Test-OperatorAck($Owner,[string]$Sha) {
 $Acceptance=Join-Path $Directory 'actual\operator_acceptance.json'
 if(-not [IO.File]::Exists($Acceptance)){return $false}
 $Claim=Read-Json (Join-Path $Directory 'operator_launch_claim.json')
 $Ack=Read-Json $Acceptance
 if($Claim.schema -cne 'TREE2_V005_OPERATOR_CREATION_CLAIM_V1' -or -not (Test-Identity $Claim.operator_owner $Owner) -or $Claim.authority_sha256 -cne $Sha -or $Ack.schema -cne 'TREE2_V005_OPERATOR_ACCEPTANCE_V1' -or $Ack.authority_sha256 -cne $Sha){throw 'Operator ACK belongs to different source/native creation'}
 Assert-Row $Claim.launcher_source $Launcher
 Assert-Row $Claim.runtime $Runtime
 Assert-Row $Ack.custody_ready (Join-Path $Directory 'actual\custody_ready.json')
 $Ready=Read-Json (Join-Path $Directory 'actual\custody_ready.json')
 if($Ready.schema -cne 'TREE2_V005_CUSTODY_READY_V1' -or $Ready.authority_sha256 -cne $Sha -or -not (Test-Identity $Ready.custodian_owner $Ack.custodian_owner)){throw 'Exact ready/acceptance join differs'}
 return $true
}
function Get-AckObservation($Owner,[string]$Sha,[double]$Elapsed) {
 if($Elapsed -ge 45){return 'TIMEOUT'}
 if(Test-OperatorAck $Owner $Sha){return 'ACK'}
 return 'WAIT'
}
function Write-AckTimeout($Owner,[string]$Sha) {
 Write-ExclusiveJson (Join-Path $Directory 'actual\task_operator_ack_timeout.json') ([ordered]@{schema='TREE2_V005_TASK_OPERATOR_ACK_TIMEOUT_V1';operator_owner=$Owner;authority_sha256=$Sha;ack_bound_seconds=45;actual_exit='UNKNOWN_LIVE_OR_EXIT_OBSERVATION_PENDING';no_signal=$true;no_retry=$true})
}
function Invoke-FixedTaskOperator([string]$Sha) {
 if([IO.Path]::GetFullPath($PSCommandPath) -cne $Wrapper -or [IO.Path]::GetFullPath($PSScriptRoot) -cne (Join-Path $Root 'scripts\finalization_controller_v005')){throw 'Only the fixed stable Task wrapper is admitted'}
 $AuthorityBytes=[IO.File]::ReadAllBytes($AuthorityPath)
 if((Get-Sha $AuthorityBytes) -cne $Sha){throw 'Mandatory exact Root authority bytes/hash differ'}
 $Authority=$Utf8.GetString($AuthorityBytes).TrimStart([char]0xfeff) | ConvertFrom-Json
 if($Authority.schema -cne 'TREE2_CONTROLLER_FRESH_FINALIZATION_ACTIVATION_V005' -or $Authority.status -cne 'ROOT_ADMITTED_ATTACH_SEPARATELY_ADMITTED_FINALIZATION_WORKER_ONLY' -or $Authority.initial_AI_calls -ne 0 -or $Authority.initial_science_launches -ne 0 -or $Authority.process_repairs_remaining -ne 0){throw 'Attach-only Root authority differs'}
 foreach($Pair in @(@('task_entry',$Entry),@('task_wrapper',$Wrapper),@('operator_launcher',$Launcher),@('runtime',$Runtime),@('python_runtime',$Runtime))){Assert-Row $Authority.($Pair[0]) $Pair[1]}
 $RuntimeRow=Get-Row $Runtime
 if($RuntimeRow.bytes -ne 107312 -or $RuntimeRow.sha256 -cne $RuntimeSha){throw 'Exact pinned core Python runtime differs'}
 $Binding=Get-TaskBinding $Authority $Sha
 Initialize-Native
 $Self=[Diagnostics.Process]::GetCurrentProcess()
 $WrapperOwner=[CodexTree2TaskV005.Native]::Identity($Self.Handle,$PID)
 Write-ExclusiveJson (Join-Path $Directory 'task_wrapper_launch_claim.json') ([ordered]@{schema='TREE2_V005_TASK_WRAPPER_LAUNCH_CLAIM_V1';authority_sha256=$Sha;wrapper_owner=$WrapperOwner;task_entry=$Authority.task_entry;task_wrapper=$Authority.task_wrapper;operator_launcher=$Authority.operator_launcher;task_spec=$Authority.task_spec;python_runtime=$Authority.runtime;task_registration_receipt=$Binding.receipt;task_registered_xml=$Binding.xml;task_name=$Binding.spec.task_name;task_path=$Binding.spec.task_path;user_sid=$Binding.spec.user_sid;max_operator_starts=1;no_retry=$true;operator_expected_ack_seconds=45;claimed_utc=[DateTime]::UtcNow.ToString('o')})
 $Folder=Join-Path $Root 'work\finalization_controller_v005\task_operator_native'
 if([IO.Directory]::Exists($Folder)){throw 'Permanent one-shot operator log directory already exists; no retry'}
 $null=[IO.Directory]::CreateDirectory($Folder)
 $OutPath=Join-Path $Folder 'stdout.log';$ErrPath=Join-Path $Folder 'stderr.log'
 $Out=[IO.FileStream]::new($OutPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 $Err=[IO.FileStream]::new($ErrPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 $PythonRoot="'"+$Root.Replace('\','\\').Replace("'","\'")+"'"
 $PythonEntry="'"+$Entry.Replace('\','\\').Replace("'","\'")+"'"
 $Code='import sys,runpy;sys.path.insert(0,'+$PythonRoot+');sys.argv=['+$PythonEntry+']+sys.argv[1:];runpy.run_path('+$PythonEntry+",run_name='__main__')"
 $Info=[Diagnostics.ProcessStartInfo]::new();$Info.FileName=$Runtime;$Info.WorkingDirectory=$Root
 $Info.Arguments='-I -S -B -c "'+$Code+'" --authority-sha256 '+$Sha
 $Info.UseShellExecute=$false;$Info.CreateNoWindow=$true;$Info.RedirectStandardInput=$true;$Info.RedirectStandardOutput=$true;$Info.RedirectStandardError=$true
 $Process=[Diagnostics.Process]::new();$Process.StartInfo=$Info
 $Started=$false;$RefHeld=$false;$Handle=[IntPtr]::Zero;$Owner=$null;$OutDrain=$null;$ErrDrain=$null
 $Ack=$false;$Timeout=$false;$NativeCode=$null;$ProcessCode=$null;$Drained=$false
 $Errors=[Collections.Generic.List[string]]::new()
 try {
  if(-not $Process.Start()){throw 'Fixed operator creation returned false'};$Started=$true
  $Clock=[Diagnostics.Stopwatch]::StartNew()
  $Safe=$Process.SafeHandle;$Safe.DangerousAddRef([ref]$RefHeld);$Handle=$Safe.DangerousGetHandle()
  $Process.StandardInput.Close()
  $OutDrain=$Process.StandardOutput.BaseStream.CopyToAsync($Out);$ErrDrain=$Process.StandardError.BaseStream.CopyToAsync($Err)
  $Owner=[CodexTree2TaskV005.Native]::Identity($Handle,$Process.Id)
  if([IO.Path]::GetFullPath([CodexTree2TaskV005.Native]::Image($Handle)) -cne $Runtime){throw 'Creation-handle executable differs from pinned runtime'}
  Write-ExclusiveJson (Join-Path $Directory 'actual\task_operator_created.json') ([ordered]@{schema='TREE2_V005_TASK_OPERATOR_CREATED_V1';at=[DateTime]::UtcNow.ToString('o');authority_sha256=$Sha;wrapper_owner=$WrapperOwner;operator_owner=$Owner;runtime=$RuntimeRow;entry=$Authority.task_entry;wrapper=$Authority.task_wrapper;creation_handle_retained=$true;argv=$Info.Arguments})
  while([CodexTree2TaskV005.Native]::Wait($Handle,250) -ne 0){
   if(-not $Ack -and -not $Timeout){$Observation=Get-AckObservation $Owner $Sha $Clock.Elapsed.TotalSeconds;if($Observation -eq 'ACK'){$Ack=$true}elseif($Observation -eq 'TIMEOUT'){$Timeout=$true;Write-AckTimeout $Owner $Sha}}
  }
  if(-not $Ack -and -not $Timeout){$Observation=Get-AckObservation $Owner $Sha $Clock.Elapsed.TotalSeconds;if($Observation -eq 'ACK'){$Ack=$true}elseif($Observation -eq 'TIMEOUT'){$Timeout=$true;Write-AckTimeout $Owner $Sha}}
 } catch {$Errors.Add($_.Exception.ToString())}
 finally {
  if($Started){
   try {
    # Any timeout/publication/drain error keeps custody; never kill, detach or retry.
    if($Handle -ne [IntPtr]::Zero){try{while([CodexTree2TaskV005.Native]::Wait($Handle,1000) -ne 0){}}catch{$Errors.Add($_.Exception.ToString())}}
    $DotNetExitConfirmed=$false
    while(-not $DotNetExitConfirmed){try{$Process.WaitForExit();$ProcessCode=$Process.ExitCode;$DotNetExitConfirmed=$true}catch{if($Errors.Count -lt 16){$Errors.Add($_.Exception.ToString())};[Threading.Thread]::Sleep(1000)}}
    if($Handle -ne [IntPtr]::Zero){$NativeCode=[CodexTree2TaskV005.Native]::ExitCode($Handle)}
    if($null -ne $NativeCode -and $NativeCode -ne [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$ProcessCode),0)){throw 'Retained native/.NET actual exit codes differ'}
    if($null -ne $OutDrain){$OutDrain.GetAwaiter().GetResult()};if($null -ne $ErrDrain){$ErrDrain.GetAwaiter().GetResult()}
    $Out.Flush($true);$Err.Flush($true);$Drained=($null -ne $OutDrain -and $null -ne $ErrDrain)
   } catch {$Errors.Add($_.Exception.ToString())}
  }
  $Out.Dispose();$Err.Dispose()
  if($Started){try{Write-ExclusiveJson (Join-Path $Directory 'actual\task_operator_actual_exit.json') ([ordered]@{schema='TREE2_V005_TASK_OPERATOR_ACTUAL_EXIT_V1';at=[DateTime]::UtcNow.ToString('o');authority_sha256=$Sha;wrapper_owner=$WrapperOwner;operator_owner=$Owner;actual_exit_code=$NativeCode;dotnet_exit_code=$ProcessCode;native_handle_retained=($Handle -ne [IntPtr]::Zero);output_drained=$Drained;stdout=(Get-Row $OutPath);stderr=(Get-Row $ErrPath);ack_within_bound=$Ack;ack_timeout=$Timeout;errors=@($Errors.ToArray());science_signalled=$false;automatic_retry=$false})}catch{$Errors.Add($_.Exception.ToString())}}
  if($RefHeld){$Safe.DangerousRelease()};$Process.Dispose();$Self.Dispose()
 }
 if($Errors.Count -gt 0 -or -not $Ack -or $Timeout -or $NativeCode -ne 0 -or -not $Drained){throw ('One-shot Task operator held/failed; no retry: '+($Errors -join ' | '))}
 return 0
}
exit (Invoke-FixedTaskOperator $AuthoritySha256)
