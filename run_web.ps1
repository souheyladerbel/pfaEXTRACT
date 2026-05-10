# Lancer l'app Streamlit depuis la racine du projet (PowerShell)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Fichier .env cree a partir de .env.example — renseignez GEMINI_API_KEY pour Gemini / tickets."
    }
}

streamlit run src/web/app.py
