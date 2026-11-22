$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path $PSScriptRoot -Parent
$RepoRoot = Split-Path $AppRoot -Parent
$ToolsRoot = Join-Path $RepoRoot '.local-tools\windows'
$RuntimeFile = Join-Path $ToolsRoot 'runtime.json'
$Python = Join-Path $AppRoot '.venv\Scripts\python.exe'

function Assert-Windows {
    if ($env:OS -ne 'Windows_NT' -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
        throw 'This installer supports native Windows 11 x64 (Intel/AMD) only.'
    }
}

function Invoke-Checked {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$File failed (exit $LASTEXITCODE)." }
}

function Set-DefaultEnvironment {
    param([string]$Name, [string]$Value)
    if (-not [Environment]::GetEnvironmentVariable($Name, 'Process')) {
        [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    }
}

function Set-AppEnvironment {
    if (-not (Test-Path -LiteralPath $RuntimeFile)) {
        throw 'Runtime not installed. Run the Windows installation launcher in the repository root first.'
    }
    $runtime = Get-Content -LiteralPath $RuntimeFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($name in @('uv', 'ffmpeg', 'whisper')) {
        if (-not (Test-Path -LiteralPath $runtime.$name)) {
            throw "Missing $name runtime. Run the Windows installer again."
        }
    }
    Set-DefaultEnvironment 'VOXPULL_FFMPEG_BIN' $runtime.ffmpeg
    Set-DefaultEnvironment 'VOXPULL_WHISPER_BIN' $runtime.whisper
    Set-DefaultEnvironment 'VOXPULL_STATE_DIR' (Join-Path $RepoRoot '.local-tools\state')
    Set-DefaultEnvironment 'PLAYWRIGHT_BROWSERS_PATH' (Join-Path $RepoRoot '.local-tools\browsers')
    Set-DefaultEnvironment 'UV_PYTHON_INSTALL_DIR' (Join-Path $ToolsRoot 'python')
    Set-DefaultEnvironment 'UV_PYTHON_BIN_DIR' (Join-Path $ToolsRoot 'python-bin')
    Set-DefaultEnvironment 'UV_CACHE_DIR' (Join-Path $ToolsRoot 'cache')
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PATH = (Split-Path $runtime.ffmpeg -Parent) + ';' + (Split-Path $runtime.whisper -Parent) + ';' + $env:PATH
}
