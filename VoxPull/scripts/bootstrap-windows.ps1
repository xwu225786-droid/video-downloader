param([switch]$Dev)
. "$PSScriptRoot\windows-common.ps1"
Assert-Windows
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null
$manifest = Get-Content -LiteralPath "$PSScriptRoot\windows-runtime.json" -Raw -Encoding UTF8 | ConvertFrom-Json

function Save-Verified {
    param([string[]]$Urls, [string]$Destination, [string]$Hash)
    if ((Test-Path -LiteralPath $Destination) -and
        (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -eq $Hash) { return }
    $part = "$Destination.part"
    foreach ($url in $Urls) {
        try {
            Write-Host "Downloading $url"
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $part -TimeoutSec 1200
            if ((Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash -ne $Hash) {
                throw "SHA-256 mismatch for $url"
            }
            Move-Item -LiteralPath $part -Destination $Destination -Force
            return
        } catch {
            Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
            Write-Warning $_
        }
    }
    throw "Download failed: $Destination. Check network access and rerun the installer."
}

$runtime = @{}
foreach ($name in @('uv', 'ffmpeg')) {
    $asset = $manifest.$name
    $archive = Join-Path $ToolsRoot "$name-$($asset.sha256).zip"
    Save-Verified @($asset.url) $archive $asset.sha256
    $destination = Join-Path $ToolsRoot "$name-$($asset.sha256.Substring(0, 12))"
    if (-not (Test-Path -LiteralPath $destination)) {
        $temporary = "$destination.extracting"
        Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -LiteralPath $archive -DestinationPath $temporary -Force
        Move-Item -LiteralPath $temporary -Destination $destination
    }
    $executables = @(Get-ChildItem -LiteralPath $destination -Recurse -File -Filter $asset.executable)
    if ($executables.Count -ne 1) { throw "Expected exactly one $($asset.executable) in $name." }
    $runtime[$name] = $executables[0].FullName
}
$runtime | ConvertTo-Json | Set-Content -LiteralPath $RuntimeFile -Encoding UTF8
Set-AppEnvironment
$uv = $runtime['uv']
Push-Location $AppRoot
try {
    Invoke-Checked $uv @('python', 'install', '3.14')
    $sync = @('sync', '--locked', '--python', '3.14')
    if ($Dev) { $sync += @('--extra', 'dev') }
    Invoke-Checked $uv $sync
    Invoke-Checked $Python @('-m', 'playwright', 'install', 'chromium')
    Invoke-Checked $runtime['ffmpeg'] @('-version')
} finally { Pop-Location }
Write-Host 'Installation complete. Use the Windows start launcher in the repository root.'
