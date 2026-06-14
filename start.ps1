#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the LowCap Short operator console.

.DESCRIPTION
    Single entry point for the system's UI. Verifies Node.js is available,
    installs the UI dependencies on first run, then launches the Vite dev
    server. Re-run any time; dependencies are only installed when missing
    (or when -Install is passed).

.PARAMETER Port
    Port for the dev server. Defaults to 5173 (Vite's default).

.PARAMETER Open
    Open the console in your default browser once the server is ready.

.PARAMETER Install
    Force a fresh `npm install` even if node_modules already exists.

.EXAMPLE
    ./start.ps1
.EXAMPLE
    ./start.ps1 -Port 3000 -Open
.EXAMPLE
    ./start.ps1 -Install
#>
[CmdletBinding()]
param(
    [int]$Port = 5173,
    [switch]$Open,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

# Resolve paths relative to this script so it runs from anywhere.
$root = $PSScriptRoot
$ui   = Join-Path $root "ui"

if (-not (Test-Path $ui)) {
    Write-Error "UI directory not found at '$ui'. Run this script from the repo root."
    exit 1
}

# 1. Verify Node.js / npm are on PATH.
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found on PATH. Install Node 18+ from https://nodejs.org and retry."
    exit 1
}
Write-Host ("Using node {0}, npm {1}" -f (node --version), (npm --version)) -ForegroundColor DarkGray

Set-Location $ui

# 2. Install dependencies on first run (or when forced).
if ($Install -or -not (Test-Path (Join-Path $ui "node_modules"))) {
    Write-Host "Installing UI dependencies..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Error "npm install failed (exit $LASTEXITCODE)."
        exit $LASTEXITCODE
    }
} else {
    Write-Host "Dependencies present (pass -Install to reinstall)." -ForegroundColor DarkGray
}

# 3. Launch the dev server.
Write-Host ("Starting LowCap Short console on http://localhost:{0} ..." -f $Port) -ForegroundColor Green
$devArgs = @("run", "dev", "--", "--port", "$Port", "--strictPort")
if ($Open) { $devArgs += "--open" }
npm @devArgs
exit $LASTEXITCODE
