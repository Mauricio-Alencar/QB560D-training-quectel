[CmdletBinding()]
param(
    [string]$PythonExe,
    [switch]$InstallPython,
    [switch]$CheckOnly
)
# Prepares only the Windows host. Never opens an ADB session or installs on the target.
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$venvDirectory = Join-Path $PSScriptRoot '.venv'
$venvPython = Join-Path $venvDirectory 'Scripts/python.exe'

function Test-Python312([string]$Candidate) {
    if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { return $null }
    # WindowsApps aliases can redirect to the Store. They are not interpreter paths.
    if ($Candidate -match '\\Microsoft\\WindowsApps\\') { return $null }
    try {
        $probeCode = "import json,sys,struct; print(json.dumps({'executable':sys.executable,'version':sys.version.split()[0],'major':sys.version_info[0],'minor':sys.version_info[1],'bits':struct.calcsize('P')*8}))"
        $result = & $Candidate -c $probeCode 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $info = ($result -join "`n") | ConvertFrom-Json
        if ($info.major -eq 3 -and $info.minor -eq 12 -and $info.bits -eq 64) { return $info }
    } catch { return $null }
    return $null
}

# InstallPython is retained for old command lines; preparation is now portable.
if ($PythonExe) {
    $pythonInfo = Test-Python312 $PythonExe
    if (-not $pythonInfo) { throw 'PythonExe must point to a working Python 3.12 x64 executable.' }
} elseif (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $pythonInfo = Test-Python312 $venvPython
    if (-not $pythonInfo) { throw 'The existing .venv must use Python 3.12 x64. Review it before retrying.' }
} else {
    $preparePortable = Join-Path $repository 'host/prepare_portable_python.ps1'
    if ($CheckOnly) {
        & $preparePortable -Version 3.12 -TrainingRoot $repository -CheckOnly
        Write-Output 'CHECK_ONLY_OK: no environment created and no target connection.'
        exit 0
    }
    $portablePython = & $preparePortable -Version 3.12 -TrainingRoot $repository
    $pythonInfo = Test-Python312 $portablePython
    if (-not $pythonInfo) { throw 'Portable Python 3.12 x64 failed validation.' }
}
Write-Output ('Python: ' + $pythonInfo.version + ' x64, ' + $pythonInfo.executable)
if ($CheckOnly) { Write-Output 'CHECK_ONLY_OK: no software installed and no target connection.'; exit 0 }

if (-not (Test-Path -LiteralPath $venvPython)) {
    if (Test-Path -LiteralPath $venvDirectory) { throw 'An incomplete .venv directory exists. Review it before retrying.' }
    & $pythonInfo.executable -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
}
if (-not (Test-Python312 $venvPython)) { throw 'The existing .venv must use Python 3.12 x64.' }
$hostWheels = Join-Path $repository 'offline/host-wheels'
$wheelLock = Join-Path $hostWheels 'wheels.lock.json'
if (Test-Path -LiteralPath $wheelLock) {
    $lockedWheels = Get-Content -LiteralPath $wheelLock -Raw | ConvertFrom-Json
    foreach ($wheel in $lockedWheels.files) {
        $wheelPath = Join-Path $hostWheels $wheel.file
        if (-not (Test-Path -LiteralPath $wheelPath)) { throw ('Missing host wheel: ' + $wheel.file) }
        $wheelStream = [IO.File]::OpenRead($wheelPath)
        $wheelHasher = [Security.Cryptography.SHA256]::Create()
        try {
            $wheelDigest = [BitConverter]::ToString($wheelHasher.ComputeHash($wheelStream)).Replace('-','').ToLowerInvariant()
        } finally {
            $wheelStream.Dispose()
            $wheelHasher.Dispose()
        }
        if ($wheelDigest -ne $wheel.sha256) {
            throw ('Host wheel hash mismatch: ' + $wheel.file)
        }
    }
    & $venvPython -m pip install --no-index --find-links $hostWheels -r (Join-Path $repository 'runtimes/qairt_2_51/requirements-host.txt')
} else {
    & $venvPython -m pip install -r (Join-Path $repository 'runtimes/qairt_2_51/requirements-host.txt')
}
if ($LASTEXITCODE -ne 0) { throw 'Host dependency installation failed.' }
& $venvPython -c "import numpy,PIL; assert numpy.__version__ == '2.3.5'; assert PIL.__version__ == '12.3.0'; print('HOST_READY: NumPy ' + numpy.__version__ + ', Pillow ' + PIL.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Host dependency verification failed.' }
Write-Output ('Use this Python: ' + $venvPython)
