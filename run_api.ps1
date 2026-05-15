$ErrorActionPreference = "Stop"

Write-Host "Lancement backend FastAPI..." -ForegroundColor Green
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
}
else {
    throw "Python introuvable. Installe Python ou ajoute-le au PATH."
}
