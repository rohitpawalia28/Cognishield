$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "The virtual environment was not found. Run .\scripts\setup.ps1 first."
    exit 1
}

.\.venv\Scripts\python.exe app.py
