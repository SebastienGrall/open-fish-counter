$ErrorActionPreference = "Stop"

$projectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot "..\.."
    )
).Path

Set-Location $projectRoot

Write-Host "[1/3] Construction PyInstaller"

Remove-Item build `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item dist `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

python -m PyInstaller `
    --noconfirm `
    --clean `
    packaging\windows\OpenFishCounter.spec

if ($LASTEXITCODE -ne 0) {
    throw "La construction PyInstaller a echoue. Code : $LASTEXITCODE"
}

$compilerCandidates = @(
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe"
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$iscc = $compilerCandidates |
    Where-Object {
        Test-Path $_
    } |
    Select-Object -First 1

if (-not $iscc) {
    throw "ISCC.exe introuvable. Installez Inno Setup puis relancez le script."
}

Write-Host "[2/3] Construction de l'installateur"
Write-Host "Compilateur Inno Setup : $iscc"

& $iscc `
    "packaging\windows\OpenFishCounter.iss"

if ($LASTEXITCODE -ne 0) {
    throw "La compilation Inno Setup a echoue. Code : $LASTEXITCODE"
}

$installerDirectory = (
    "packaging\windows\output"
)

if (-not (Test-Path $installerDirectory)) {
    throw "Le dossier de sortie de l'installateur est introuvable."
}

$installer = Get-ChildItem `
    "$installerDirectory\OpenFishCounter-Setup-*.exe" `
    -ErrorAction Stop |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $installer) {
    throw "Aucun installateur Open Fish Counter n'a ete genere."
}

Write-Host "[3/3] Installateur cree avec succes"
Write-Host ""

$installer |
    Select-Object FullName, Length, LastWriteTime