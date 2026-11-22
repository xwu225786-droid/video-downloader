param([ValidateSet('start', 'stop', 'status', 'restart')][string]$Action = 'start')
. "$PSScriptRoot\windows-common.ps1"
Assert-Windows
Set-AppEnvironment
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run the Windows installer first.' }
Push-Location $AppRoot
try {
    Invoke-Checked $Python @('-m', 'voxpull.cli', $Action)
    if ($Action -in @('start', 'restart')) {
        $port = & $Python -m voxpull.cli port
        if ($LASTEXITCODE -ne 0) { throw 'Cannot determine server port.' }
        Start-Process "http://127.0.0.1:$($port.Trim())/"
    }
} finally { Pop-Location }
