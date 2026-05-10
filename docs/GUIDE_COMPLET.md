# Guide complet du projet pfaEXTRACT

Pour une **cartographie complète du code et de l’architecture réelle**, voir aussi **[`DOCUMENTATION_PROJET.md`](./DOCUMENTATION_PROJET.md)**.

Ce document explique l’ensemble du dépôt pour des profils variés (débutant, data scientist, développeur « front », développeur « back », encadrant de PFA). Les termes **interface** et **logique métier** remplacent souvent « front » et « back » ici, car il n’y a pas de site React/Vue séparé : tout tourne en **Python** avec **Streamlit** comme couche visuelle.

---

## 1. Qu’est-ce que ce projet ?

**Objectif** : extraire automatiquement des informations structurées à partir de documents hétérogènes (images, PDF) : analyses de laboratoire, factures STEG (Tunisie), tickets de caisse.

**Technologies principales** :

| Rôle | Technologie |
|------|-------------|
| Interface utilisateur | [Streamlit](https://streamlit.io/) — pages Python qui s’affichent dans le navigateur |
| Données typées | [Pydantic](https://docs.pydantic.dev/) (`src/models/schemas.py`) |
| OCR local | Tesseract (`pytesseract`), parfois EasyOCR en secours |
| PDF | `pdf2image`, `pypdf` |
| Vision / LLM | Google **Gemini** : SDK `google-genai` (vision JSON) et `google-generativeai` (pipeline médical hybride) |
| Persistance locale | Fichiers **JSON** + index **SQLite** (`extractions.db`, table `extraction_history`) ; voir `docs/DOCUMENTATION_PROJET.md` |

---

## 2. Architecture réelle (ce qui est implémenté)

Le fichier `docs/ARCHITECTURE.md` décrit une **cible** doctorale (ingestion, preprocessing, API REST, PostgreSQL, etc.). **Dans le code actuel**, l’architecture effective est plus simple :

```text
Utilisateur (navigateur)
        │
        ▼
┌───────────────────────────────────────┐
│  Streamlit (src/web/app.py, pages/) │  ← « Front » : formulaires, tableaux, téléchargements
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Services (src/services/)            │  ← « Back » : routage, pipelines, historique
│  Pipelines (pipelines/)              │
│  Extraction (src/extraction/)        │
│  Gemini (src/gemini_vision.py, …)   │
└───────────────────────────────────────┘
        │
        ├──► Fichiers disque (upload temporaire, JSON historique)
        └──► API Google Gemini (réseau)
```

Il n’y a **pas** d’API HTTP maison (FastAPI/Flask) exposée au navigateur : Streamlit exécute le Python **côté serveur** à chaque interaction et rafraîchit la page.

---

## 3. Arborescence utile

L’arborescence **exacte et à jour** du dépôt est dans **[`DOCUMENTATION_PROJET.md`](./DOCUMENTATION_PROJET.md)** (section 3). Ci-dessous, un résumé :

```text
pfaEXTRACT/
├── Data/                          # Données exemples / brut (selon usage)
├── docs/
│   ├── ARCHITECTURE.md            # Vision long terme (doctorat)
│   └── GUIDE_COMPLET.md           # Ce fichier
├── pipelines/                     # Scripts CLI + logique Gemini réutilisable
│   ├── extract_medical_report_gemini.py
│   ├── extract_receipt_gemini.py
│   ├── extract_steg_invoice_gemini.py
│   └── run_*.py                   # Orchestrations optionnelles
├── src/
│   ├── config.py                  # Chargement .env, chemins, modèle Gemini
│   ├── main.py                    # CLI extraction médicale (OCR ± Gemini)
│   ├── gemini_vision.py           # Appels google-genai + parsing JSON
│   ├── gemini_models.py           # Noms de modèles, fallback 404
│   ├── models/schemas.py          # Modèles Pydantic (résultat médical structuré)
│   ├── extraction/                # OCR + règles (médical, STEG)
│   ├── services/
│   │   ├── document_router.py     # Détection type + orchestration
│   │   ├── medical_pipeline.py    # Image/PDF → OCR → optional Gemini merge
│   │   ├── gemini_llm.py          # Gemini « classique » pour schéma MedicalDocumentResult
│   │   └── extraction_history.py # Sauvegarde JSON historique
│   ├── utils/logger.py
│   └── web/
│       ├── app.py                 # Page principale Streamlit
│       ├── history_views.py       # Affichage détail / helpers tableaux
│       └── pages/1_Historiques.py # Multi-page Streamlit : historique
├── requirements.txt
├── .env.example                   # Modèle de variables d’environnement
└── run_web.ps1                    # Exemple de lancement sous Windows
```

**Remarque chemins** : `src/config.py` utilise par défaut un dossier `data/` à la racine pour certains répertoires ; l’historique peut être surchargé par `EXTRACTION_HISTORY_DIR`. Sur Windows, `Data` et `data` peuvent coexister ou se confondre selon la casse du système de fichiers.

---

## 4. Installation et exécution

### 4.1 Prérequis système

- **Python 3.10+** (recommandé ; vérifier avec `python --version`).
- **Tesseract OCR** installé ; sous Windows, chemin par défaut attendu dans `config.py` :  
  `C:\Program Files\Tesseract-OCR\tesseract.exe` (modifiable via `TESSERACT_CMD`).
- Pour PDF → image : **Poppler** doit être accessible à `pdf2image` (variable d’environnement ou PATH selon l’installation).

### 4.2 Dépendances Python

```bash
python -m pip install -r requirements.txt
```

Paquets notables : `streamlit`, `pydantic`, `opencv-python`, `pytesseract`, `pdf2image`, `Pillow`, `google-genai`, `google-generativeai`, `python-dotenv`, etc.

### 4.3 Variables d’environnement

Copier `.env.example` vers `.env` à la racine du projet et renseigner au minimum :

| Variable | Rôle |
|----------|------|
| `GEMINI_API_KEY` | Clé [Google AI Studio](https://aistudio.google.com/apikey) (ou `GOOGLE_API_KEY` acceptée à la lecture) |
| `GEMINI_MODEL` | Ex. `gemini-2.5-flash` (éviter les anciens `gemini-1.5-*` : souvent 404) |
| `EXTRACTION_HISTORY_DIR` | Dossier des JSON d’historique (optionnel) |
| `TESSERACT_CMD` | Chemin exécutable Tesseract si non défaut |

### 4.4 Lancer l’interface web

```bash
streamlit run src/web/app.py
```

Streamlit ouvre une URL locale (ex. `http://localhost:8501`). Le menu latéral permet d’accéder à la page **Historiques** (`pages/1_Historiques.py`).

### 4.5 Lancer en ligne de commande (médical)

```bash
python -m src.main --input "chemin/vers/document.jpg"
python -m src.main --input "chemin/vers/document.pdf" --gemini --output "sortie.json"
```

Les pipelines Gemini isolés peuvent aussi être lancés en `python -m pipelines.extract_medical_report_gemini` (voir `--help` dans chaque fichier).

---

## 5. « Front » : interface Streamlit

### 5.1 Rôle

- **Dashboard** (`src/web/app.py`) : vue synthétique de l’historique, sélection d’une ligne, détail, téléchargement rapport PDF.
- **Extraction** (`src/web/pages/1_Extraction.py`) : upload, **mode** (auto / médical / STEG / ticket), clé API / modèle, résultats, sauvegarde historique, rapport PDF.
- **Historiques** (`src/web/pages/1_Historiques.py`) : filtres, liste, **Voir** pour le détail, téléchargements (rapport PDF, fichier source).

### 5.2 Concepts Streamlit importants pour un dev « front » habitué au web

- **Pas de HTML/CSS/JS à écrire** pour la logique : on compose avec `st.title`, `st.sidebar`, `st.file_uploader`, `st.dataframe`, etc.
- **Script réexécuté du haut en bas** à chaque action utilisateur : il faut utiliser `st.session_state` pour conserver des filtres (ex. page Historiques).
- **Secrets** : la clé API peut être saisie dans la sidebar ; le code peut aussi la passer temporairement dans `os.environ` (`_gemini_env` dans `app.py`) pour les appels qui lisent `GEMINI_API_KEY`.

### 5.3 Flux utilisateur sur la page principale

1. Choisir le **type de document** (sidebar).
2. Optionnel : renseigner clé Gemini, modèle, retries.
3. Uploader une **image** ou un **PDF** (selon le mode, le PDF peut être refusé pour STEG ou ticket — Gemini vision sur image seulement pour ces flux).
4. L’application affiche succès / erreur, tableaux, JSON dans un expander, bouton téléchargement.
5. Si extraction réussie, un JSON est écrit sous `extraction_history_dir/<kind>/`.

### 5.4 Fichiers à lire pour modifier l’UI

- `src/web/app.py` — dashboard.
- `src/web/pages/1_Extraction.py` — flux d’upload et d’extraction.
- `src/web/pages/1_Historiques.py` — historique filtré et détail.
- `src/web/history_views.py` — `render_extraction_detail`, tableaux médicaux (`medical_results_df`, etc.).
- `src/web/ui_theme.py` — styles CSS partagés (`inject_app_styles`).

---

## 6. « Back » : logique métier et données

### 6.1 Configuration (`src/config.py`)

- Détermine `project_root`, chemins données, `tesseract_cmd`, `log_level`, clé/modèle Gemini lues depuis l’environnement (après `load_dotenv`), et **`extraction_history_dir`** pour l’historique.

### 6.2 Routage des documents (`src/services/document_router.py`)

**`detect_document_type(path)`** — heuristiques :

- Nom de fichier (ex. `steg`, `analyse`, `ticket`, …).
- Sinon, pour une **image** : OCR léger Tesseract (`eng+ara`, PSM 6 et 11), comptage de mots-clés pour **STEG**, **ticket**, **médical**.

Retourne une chaîne parmi : `steg_invoice`, `receipt`, `medical_lab_report`.

**`process_any_document(...)`** — selon `mode` :

- `auto` : applique la détection puis branche vers STEG / ticket / médical.
- `steg` avec `use_gemini=True` : `extract_steg_invoice` (pipeline Gemini).
- `steg` sans Gemini : extracteur OCR `extract_fields_from_invoice`.
- `receipt` : `extract_receipt` (Gemini), image uniquement.
- `medical` : `process_medical_file` (OCR + optional fusion Gemini selon flags).

### 6.3 Pipeline médical (`src/services/medical_pipeline.py`)

- **Image** : OCR combiné + extraction structurée locale (`medical_analysis_extractor`) → **baseline** `MedicalDocumentResult` avec `extraction_source="ocr"`.
- Si `--gemini` / `use_gemini` et clé présente : `analyze_medical_document_gemini` envoie **texte OCR + image** au modèle (`google.generativeai`) et attend un JSON aligné sur le schéma décrit dans `gemini_llm.py`.
- **Fusion** : si Gemini renvoie des tests, on merge avec la baseline (champs manquants complétés).
- **PDF** : extraction texte `pypdf` + conversion **première page** en PNG pour OCR / image Gemini.

### 6.4 Pipelines Gemini « vision JSON » (`pipelines/*.py` + `src/gemini_vision.py`)

Utilisés par l’UI pour :

- **Analyse médicale « simple »** (`extract_medical_report`) : une image → prompt fixe → JSON `{ patient_name, doctor_name, date, analyses[] }`.
- **Ticket** (`extract_receipt`) : JSON magasin, date, lignes articles, total, etc.
- **STEG** (`extract_steg_invoice`) : JSON champs facture (référence, montant, périodes, coupon, etc.).

**`generate_vision_json`** (`gemini_vision.py`) :

- Client `google.genai` avec `response_mime_type="application/json"`, température 0.
- Chaîne de **fallback modèles** (`gemini_models.py`) si 404 ou indisponible ; gestion basique des erreurs **429 / 503** avec retries et backoff.

**Important** : ces pipelines lisent **`GEMINI_API_KEY`** dans l’environnement au moment de l’appel — d’où le context manager dans `app.py` qui injecte la clé saisie dans l’UI.

### 6.5 Schémas de données (`src/models/schemas.py`)

Modèle principal **`MedicalDocumentResult`** : laboratoire, patient, métadonnées document, liste de **`LabTest`** (nom brut, valeur numérique ou texte, unité, plage de référence, statut low/normal/high/unknown, confiance), avertissements, `extraction_source`.

Les sorties **Gemini « simple »** (page web médicale) sont des **dict** JSON sans ce modèle Pydantic complet — l’historique les enregistre sous le kind `medical_gemini`.

### 6.6 Historique (`src/services/extraction_history.py`)

- **`save_extraction(..., source_bytes=...)`** : écrit  
  `{extraction_history_dir}/{kind}/{timestampUTC}_{stem}.json` ; enregistre une ligne dans **SQLite** (`extraction_history_db_path`) avec le JSON dans `payload_json` ; peut archiver le **fichier source** à côté du JSON (`source_file_relative` dans `_meta`).
- **`list_history_entries(cfg)`** : si la base `.db` existe, lit la table `extraction_history` (tri par `saved_at`) ; sinon **fallback** : parcours récursif des `*.json`, tri par mtime.

Kinds typiques : `receipt`, `medical_gemini`, `steg_gemini`, `steg_ocr`, `medical_ocr`.

Détail : [`DOCUMENTATION_PROJET.md`](./DOCUMENTATION_PROJET.md) §4.7.

---

## 7. Formats JSON (référence rapide)

### 7.1 Médical — Gemini « page principale » (`extract_medical_report`)

```json
{
  "patient_name": "…",
  "doctor_name": "…",
  "date": "…",
  "analyses": [
    { "test_name": "…", "value": "…", "unit": "…" }
  ]
}
```

### 7.2 Ticket (`extract_receipt`)

Champs : `store_name`, `date`, `time`, `ticket_number`, `currency`, `items[]` (`description`, `quantity`, `unit_price`, `line_total`), `total`, `payment_method`.

### 7.3 STEG Gemini (`extract_steg_invoice`)

Champs : `reference`, `montant_a_payer`, `date_limite_paiement`, `periode_du`, `periode_au`, `coupon_reference_raw`, `coupon_montant`, `confidence_note`, `extraction_source: "gemini"`.

### 7.4 Médical OCR / hybride (`MedicalDocumentResult.model_dump()`)

Objet riche : voir `schemas.py` — utilisé quand le flux passe par `process_medical_file` sans la branche « dict médical Gemini only » de la page d’accueil.

Chaque fichier d’historique inclut en plus :

```json
"_meta": {
  "saved_at": "ISO-8601 UTC",
  "source_filename": "nom original upload",
  "kind": "medical_gemini"
}
```

---

## 8. Limitations et pièges connus

- **STEG et tickets** : l’extraction Gemini attend une **image**, pas un PDF (message d’erreur explicite dans l’UI).
- **Deux SDK Google** : `google-genai` (vision JSON pipelines) vs `google-generativeai` (pipeline médical `gemini_llm.py`) — maintenance future pourrait unifier.
- **Quota / facturation** Gemini : les erreurs 429 remontent à l’utilisateur ; les retries sont limités.
- **Qualité** : les LLM peuvent halluciner ; les prompts demandent de ne pas inventer, mais une **vérification humaine** reste nécessaire pour un usage métier.
- **Sécurité** : ne pas commiter `.env` ; en production, ne pas exposer Streamlit sur Internet sans authentification et HTTPS.

---

## 9. Tests et qualité

- `pytest` est dans `requirements.txt` ; lancer `pytest` à la racine si des tests sont ajoutés sous `tests/`.
- Logs : `src/utils/logger.py` utilisé par la CLI `main.py`.

---

## 10. Glossaire pour non-spécialistes

| Terme | Explication courte |
|-------|---------------------|
| OCR | Reconnaissance optique de caractères : image → texte. |
| Pipeline | Enchaînement d’étapes (lecture fichier → OCR → extraction → sauvegarde). |
| Schéma | Structure attendue des données (champs, types). |
| Streamlit | Framework Python pour créer des pages web interactives sans écrire de serveur REST séparé. |
| Gemini | Modèle multimodal Google (texte + image) utilisé ici pour lire les documents et produire du JSON. |

---

## 11. Pistes d’évolution (hors scope immédiat)

Alignées avec `docs/ARCHITECTURE.md` : API REST, base de données, prétraitement image avancé, évaluation quantitative sur annotations, dashboard analytique séparé.

---

*Document généré pour le dépôt pfaEXTRACT — à tenir à jour lors des changements majeurs de flux ou de dépendances.*
