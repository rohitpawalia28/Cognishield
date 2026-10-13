$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment was not found. Run .\scripts\setup.ps1 first."
    exit 1
}

.\.venv\Scripts\python.exe run_batch.py --input-dir data\input

