# Plateforme intelligente d'extraction d'informations

Projet doctoral pour l'extraction automatique d'informations a partir de documents heterogenes (PDF, images scannees, factures, rapports, comptes rendus, etc.).

## Objectif

Construire une plateforme de bout en bout qui:
- collecte des documents non structures,
- applique un pretraitement adapte,
- execute l'OCR,
- extrait des entites/champs metier,
- stocke les resultats dans une base exploitable,
- fournit une visualisation analytique.

## Documentation et structure du code

- **Vue d’ensemble du dépôt (arborescence réelle, flux, SQLite, Streamlit)** : [`docs/DOCUMENTATION_PROJET.md`](docs/DOCUMENTATION_PROJET.md)
- **Architecture cible** (doctorat, non entièrement implémentée) : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Guide pédagogique** : [`docs/GUIDE_COMPLET.md`](docs/GUIDE_COMPLET.md)

En bref : `src/` (application), `pipelines/` (Gemini vision JSON), `data/history/` (JSON + `extractions.db` par défaut), `docs/`.

## Pipeline cible (v1)

1. Collecte des documents (dossier, upload, scanner, email).
2. Pretraitement (deskew, denoise, binarisation, detection de zones).
3. OCR (texte + position + confiance).
4. Extraction d'informations (champs facture, dates, montants, client, etc.).
5. Validation/qualite (scores, regles de coherence).
6. Stockage (base relationnelle + index recherche).
7. Visualisation (tableaux de bord, suivi qualite OCR/extraction).

## Prochaine etape recommandee

Commencer par un premier cas d'usage: **factures STEG** avec un schema simple:
- reference_facture
- date_facture
- nom_client
- adresse
- montant_ht
- montant_tva
- montant_ttc
- periode_consommation
- identifiant_compteur

Le fichier `docs/ARCHITECTURE.md` détaille l'architecture cible ; `docs/DOCUMENTATION_PROJET.md` décrit ce qui est réellement implémenté.

## Nouvelle interface web (Next.js + FastAPI)

Le projet contient maintenant une nouvelle interface admin moderne :
- `backend/` : API `FastAPI` qui reutilise les pipelines Python existants
- `frontend/` : interface `Next.js` multi-pages (dashboard, extractions, resultats, historiques, analyses, modeles, parametres)

### 1. Lancer le backend FastAPI

Depuis la racine du projet :

```bash
python -m pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

API disponible sur :
- `http://127.0.0.1:8000/api/health`
- ou via `.\run_api.ps1`

### 2. Lancer le frontend Next.js

Depuis `frontend/` :

```bash
npm install
npm run dev
```

Alternative si `npm` est endommage sur Windows :

```bash
corepack pnpm install
corepack pnpm dev
```

Interface disponible sur :
- `http://localhost:3000`
- ou via `.\run_frontend.ps1`

Si tu veux un lancement plus stable apres un `git pull` ou beaucoup de changements, utilise :

```bash
.\run_frontend_stable.ps1
```

Ce script nettoie `.next`, recompile puis lance le frontend en mode production.

### 3. Cle Gemini

Le meilleur emplacement reste le fichier `.env` a la racine du projet backend :

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

La cle peut aussi etre saisie dans l'interface pour une session navigateur.

## Ancienne interface Streamlit (legacy)

Depuis la racine du projet:

```bash
python -m pip install -r requirements.txt
streamlit run src/web/app.py
```

Interface web:
- upload image/PDF d'analyse medicale,
- affichage des metadonnees,
- tableau des tests extraits,
- export JSON telechargeable.

### Gemini (comprehension du document)

1. Creer une cle API : [Google AI Studio](https://aistudio.google.com/apikey)
2. Copier `.env.example` vers `.env` et renseigner `GEMINI_API_KEY=...`
3. Dans l'app web, cocher **Utiliser Gemini** (ou laisser la cle dans `.env` uniquement)

Sans cle : l'application utilise uniquement l'OCR local (Tesseract).

## Lancer en CLI (sans interface)

```bash
python -m src.main --input "Data/raw_Data/medical/analyse1.jpg"
python -m src.main --input "Data/raw_Data/medical/analyse1.jpg" --output "data/output/analyse1.json"
python -m src.main --input "Data/raw_Data/medical/analyse1.jpg" --gemini --output "data/output/analyse1.json"
```
