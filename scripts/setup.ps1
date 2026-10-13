$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found on PATH. Install Python 3.12 and tick 'Add python.exe to PATH'."
    exit 1
}

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements-core.txt
.\.venv\Scripts\pip.exe install -r requirements-torch-cu128.txt
.\.venv\Scripts\pip.exe install -r requirements-ai.txt

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run the app with: .\scripts\run_app.ps1"
