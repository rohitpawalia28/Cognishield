$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if ($args.Count -lt 1) {
    Write-Host "Usage: .\scripts\run_cli_example.ps1 path\to\image.jpg"
    exit 1
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment was not found. Run .\scripts\setup.ps1 first."
    exit 1
}

.\.venv\Scripts\python.exe run_pipeline.py $args[0]

