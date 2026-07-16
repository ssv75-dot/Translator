# Rebuild portable EXE and Windows installer (Inno Setup).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$venvPyi = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $venvPyi)) {
    throw "PyInstaller not found: $venvPyi"
}

Write-Host "==> PyInstaller (ScreenTranslatorPortable)"
& $venvPyi --noconfirm "ScreenTranslator.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$portableDir = Join-Path $Root "dist\ScreenTranslatorPortable"
$portableExe = Join-Path $portableDir "ScreenTranslatorPortable.exe"
if (-not (Test-Path $portableExe)) {
    throw "Portable exe missing: $portableExe"
}

# Deploy portable copy next to sources (folder mode)
$rootPortable = Join-Path $Root "ScreenTranslatorPortable"
if (Test-Path $rootPortable) {
    Remove-Item $rootPortable -Recurse -Force
}
Copy-Item $portableDir $rootPortable -Recurse
Copy-Item $portableExe (Join-Path $Root "ScreenTranslatorPortable.exe") -Force

# Remove legacy name if present
$legacy = Join-Path $Root "ScreenTranslator.exe"
if (Test-Path $legacy) { Remove-Item $legacy -Force }

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "==> Inno Setup not found; trying winget install..."
    winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 and re-run."
}

Write-Host "==> Inno Setup: $iscc"
$iss = Join-Path $Root "installer\ScreenTranslator.iss"
& $iscc $iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }

$setup = Join-Path $Root "dist\installer\ScreenTranslatorSetup.exe"
Write-Host "Portable: $portableExe"
Write-Host "Installer: $setup"
Write-Host "Done."
