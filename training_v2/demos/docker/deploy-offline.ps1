[CmdletBinding()]
param(
    [string]$PythonExe,
    [string]$Adb,
    [string]$Serial,
    [string]$TransportId,
    [string]$UnitLabel = 'classroom-box',
    [switch]$ValidateOnly,
    [switch]$StopAfterTest
)
$ErrorActionPreference = 'Stop'
$trainingDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$preparedPython = Join-Path $trainingDirectory 'provision_target/.venv/Scripts/python.exe'
if ($PythonExe) {
    $pythonExecutable = (Resolve-Path -LiteralPath $PythonExe).Path
} elseif (Test-Path -LiteralPath $preparedPython) {
    $pythonExecutable = $preparedPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand -or $pythonCommand.Source -match '\\Microsoft\\WindowsApps\\') {
        throw 'Run provision_target/setup_host.ps1 from training_v2 first, or supply -PythonExe FULL_PATH.'
    }
    $pythonExecutable = $pythonCommand.Source
}
$pythonPrefix = @()
$deployScript = Join-Path $PSScriptRoot 'host/deploy_offline.py'
$deployArguments = $pythonPrefix + @($deployScript, '--unit-label', $UnitLabel)
if ($Adb) { $deployArguments += @('--adb', $Adb) }
if ($Serial) { $deployArguments += @('--serial', $Serial) }
if ($TransportId) { $deployArguments += @('--transport-id', $TransportId) }
if ($ValidateOnly) { $deployArguments += '--validate-only' }
if ($StopAfterTest) { $deployArguments += '--stop-after-test' }
& $pythonExecutable @deployArguments
if ($LASTEXITCODE -ne 0) { throw "Offline deployment failed (exit $LASTEXITCODE). See evidence in the extracted package." }
