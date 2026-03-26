# Run CodeRev on this PC. Then expose HTTPS with cloudflared or ngrok (see README).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "app\main.py")) {
    Write-Host "Run this from the coderev repo (scripts\run-local.ps1)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "No .env — copy .env.example to .env and fill the 5 fields." -ForegroundColor Yellow
    exit 1
}

Write-Host "CodeRev → http://127.0.0.1:8080  (webhook POST /webhook)" -ForegroundColor Cyan
Write-Host "In another terminal: cloudflared tunnel --url http://127.0.0.1:8080" -ForegroundColor Gray

$env:PYTHONPATH = $Root
python -m pip install -q -r requirements-app.txt 2>$null
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
