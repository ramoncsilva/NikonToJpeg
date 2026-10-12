# Builds dist\nikon2jpeg\nikon2jpeg.exe (one-folder build; no Python needed to run it).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m PyInstaller --noconfirm --clean --onedir --console --name nikon2jpeg `
    --paths src --collect-all rawpy --exclude-module tkinter `
    packaging\entry.py
Write-Host "Built: $(Resolve-Path dist\nikon2jpeg\nikon2jpeg.exe)"
