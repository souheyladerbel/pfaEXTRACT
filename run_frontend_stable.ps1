$ErrorActionPreference = "Stop"

Write-Host "Lancement frontend Next.js en mode stable..." -ForegroundColor Green
Set-Location "$PSScriptRoot\frontend"

if (-not (Test-Path ".\node_modules")) {
    Write-Host "Installation des dependances frontend..." -ForegroundColor Yellow
    corepack pnpm install
}

if (Test-Path ".\.next") {
    Write-Host "Nettoyage du build Next.js..." -ForegroundColor Yellow
    Remove-Item -LiteralPath ".\.next" -Recurse -Force
}

Write-Host "Compilation de l'application..." -ForegroundColor Yellow
corepack pnpm build

Write-Host "Demarrage en mode production..." -ForegroundColor Green
corepack pnpm start --hostname 127.0.0.1 --port 3000
