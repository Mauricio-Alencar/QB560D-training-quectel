[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('3.8','3.12')][string]$Version,
    [string]$TrainingRoot,
    [switch]$CheckOnly
)
# Extract a locked official CPython NuGet package; never run a Windows installer.
$ErrorActionPreference = 'Stop'
if (-not $TrainingRoot) { $TrainingRoot = Split-Path -Parent $PSScriptRoot }
$trainingDirectory = (Resolve-Path -LiteralPath $TrainingRoot).Path
$key = $Version.Replace('.','')
$sourceDirectory = Join-Path $trainingDirectory ('tools/python' + $key)
$lock = Get-Content -LiteralPath (Join-Path $sourceDirectory ('python' + $key + '.lock.json')) -Raw | ConvertFrom-Json
$package = Join-Path $sourceDirectory $lock.archive
$spec = $lock.files.($lock.archive)
if (-not (Test-Path -LiteralPath $package -PathType Leaf)) { throw 'Portable Python package missing from training archive.' }
if ((Get-Item -LiteralPath $package).Length -ne $spec.bytes -or (Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $spec.sha256) { throw 'Portable Python package hash/size mismatch.' }
if ($CheckOnly) { Write-Output ('CHECK_ONLY_OK: CPython ' + $lock.version + ' portable package verified.'); return }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$build = [IO.Path]::GetFullPath((Join-Path $trainingDirectory '.build'))
$destination = [IO.Path]::GetFullPath((Join-Path $build ('portable-python' + $key)))
$prefix = $build.TrimEnd('\') + '\'
if (-not $destination.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime destination outside training build directory.' }
$archive = [IO.Compression.ZipFile]::OpenRead($package)
$staging = $null
try {
    if (Test-Path -LiteralPath $destination) {
        $owner = Join-Path $destination '.portable-python.json'
        if (-not (Test-Path -LiteralPath $owner -PathType Leaf)) { throw 'Existing portable runtime has no ownership marker; review it before retrying.' }
        $old = Get-Content -LiteralPath $owner -Raw | ConvertFrom-Json
        if ($old.package_sha256 -ne $spec.sha256) { throw 'Existing portable runtime belongs to another package; preserve it and use a new training copy.' }
        $active = $destination
    } else {
        New-Item -ItemType Directory -Force -Path $build | Out-Null
        $staging = Join-Path $build ('portable-python' + $key + '-' + [guid]::NewGuid().ToString('N') + '.staging')
        New-Item -ItemType Directory -Path $staging | Out-Null
        $active = $staging
    }
    foreach ($entry in $archive.Entries) {
        if (-not $entry.FullName.StartsWith('tools/') -or $entry.FullName.EndsWith('/')) { continue }
        $relative = $entry.FullName.Substring(6).Replace('/',[IO.Path]::DirectorySeparatorChar)
        $target = [IO.Path]::GetFullPath((Join-Path $active $relative))
        if (-not $target.StartsWith($active.TrimEnd('\') + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe member in portable Python package.' }
        if ($staging) {
            [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)
        } elseif (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw ('Portable runtime member missing: ' + $relative) }
        $stream = $entry.Open(); $hasher = [Security.Cryptography.SHA256]::Create()
        try { $expected = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant() } finally { $stream.Dispose(); $hasher.Dispose() }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw ('Portable runtime member changed: ' + $relative) }
    }
    if ($staging) {
        @{package_sha256=$spec.sha256; version=$lock.version} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $staging '.portable-python.json') -Encoding UTF8
        # Both absolute paths were checked against this training copy's .build.
        if (-not ([IO.Path]::GetFullPath($staging)).StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Staging directory outside training build directory.' }
        Move-Item -LiteralPath $staging -Destination $destination
    }
} finally { $archive.Dispose() }
$python = Join-Path $destination 'python.exe'
$probe = & $python -I -B -c "import sys,struct,venv,ensurepip; assert '.'.join(map(str,sys.version_info[:2]))=='$Version' and struct.calcsize('P')==8; print(sys.version.split()[0])"
if ($LASTEXITCODE -ne 0 -or ($probe -join '').Trim() -ne $lock.version) { throw 'Portable Python version/capability verification failed.' }
Write-Output $python
