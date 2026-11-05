# Display-only SHA256; independent of PowerShell module auto-loading.
function Get-DisplayFileHashV44([string]$LiteralPath,[string]$Algorithm='SHA256'){
    if($Algorithm -ne 'SHA256'){throw 'Only SHA256 display bindings are supported'}
    $Path=[IO.Path]::GetFullPath($LiteralPath)
    if(-not $Path.StartsWith($ProjectRoot.TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Display hash outside project'}
    $Stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $Digest=[Security.Cryptography.SHA256]::Create()
    try{return @{Hash=([BitConverter]::ToString($Digest.ComputeHash($Stream))).Replace('-','')}}
    finally{$Digest.Dispose();$Stream.Dispose()}
}
