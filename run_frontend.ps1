$ErrorActionPreference = "Stop"

Write-Host "Lancement frontend Next.js..." -ForegroundColor Green
Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path ".\node_modules")) {
    Write-Host "Installation des dependances frontend..." -ForegroundColor Yellow
    corepack pnpm install
}

if (Test-Path ".\.next") {
    Write-Host "Nettoyage du cache Next.js..." -ForegroundColor Yellow
    Remove-Item -LiteralPath ".\.next" -Recurse -Force
}

corepack pnpm dev --hostname 127.0.0.1 --port 3000
