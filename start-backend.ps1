<#
.SYNOPSIS
  Start the KisanSathi backend locally.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $backendRoot
try {
    $pythonExe = Join-Path $backendRoot 'venv\Scripts\python.exe'
    if (-not (Test-Path $pythonExe)) {
        Write-Error 'Python virtual environment not found. Run `python -m venv venv` first.'
        exit 1
    }

    Write-Host 'Starting FastAPI backend on http://127.0.0.1:8000...'
    & $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
}
finally {
    Pop-Location
}
