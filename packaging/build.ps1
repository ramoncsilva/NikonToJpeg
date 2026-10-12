# Builds dist\nikon2jpeg\nikon2jpeg.exe (one-folder build; no Python needed to run it).
# Uses the project's .venv when present, otherwise the python on PATH.
#
# The app is built into build\stage and then mirrored into dist, so a failed build never wipes
# an existing dist folder, and an open terminal sitting in dist does not block the update.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

& $python -m PyInstaller --noconfirm --clean --onedir --console --name nikon2jpeg `
    --distpath build\stage --paths src --collect-all rawpy --exclude-module tkinter `
    packaging\entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit code $LASTEXITCODE)" }

robocopy build\stage\nikon2jpeg dist\nikon2jpeg /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Copying to dist failed (robocopy exit code $LASTEXITCODE)" }

Write-Host "Built: $(Resolve-Path dist\nikon2jpeg\nikon2jpeg.exe)"
