# Architecture technique proposee

> **Lecture conjointe** : l’implémentation **actuelle** du dépôt (Streamlit, SQLite + JSON, services Python) est décrite dans [`DOCUMENTATION_PROJET.md`](./DOCUMENTATION_PROJET.md). Ce fichier `ARCHITECTURE.md` reste une **vision cible** pour le doctorat (pipeline complet, PostgreSQL, API, dashboard analytique, etc.) — tout n’est pas encore présent dans le code.

## 1) Vue d'ensemble

Architecture modulaire orientee pipeline:

`Collecte -> Pretraitement -> OCR -> Extraction -> Validation -> Stockage -> Visualisation`

Chaque etape produit des artefacts versionnes pour la tracabilite experimentale (important pour un travail doctoral).

## 2) Modules

### 2.1 Ingestion (`src/ingestion`)
- Lecture de documents depuis `Data/raw_Data`.
- Detection du type (`pdf`, `image`, `scan`).
- Attribution d'un `document_id` unique .
- Journalisation metadata (source, date, format, hash).

### 2.2 Pretraitement (`src/preprocessing`)
- Conversion PDF en images.
- Correction d'inclinaison (deskew).
- Reduction du bruit.
- Amelioration contraste / binarisation.
- Segmentation par zones (en-tete, tableau, pied de page) si necessaire.

### 2.3 OCR (`src/ocr`)
- Moteur OCR principal (Tesseract, PaddleOCR, EasyOCR ou cloud OCR).
- Sortie standard:
  - texte extrait,
  - bounding boxes,
  - score de confiance.
- Post-traitement:
  - correction erreurs frequentes,
  - normalisation caracteres (ex: virgule/point, espaces).

### 2.4 Extraction (`src/extraction`)
- Approche hybride:
  - Regles/Regex pour champs stables (montants, dates),
  - NER/ML pour champs variables,
  - eventuellement LLM pour extraction semi-structuree.
- Mapping vers schema metier facture.
- Gestion des champs manquants avec score de confiance.

### 2.5 Validation qualite
- Regles de coherence:
  - `montant_ht + montant_tva ~= montant_ttc`
  - format de date valide,
  - identifiant present.
- Marquage `accepted / review_required`.

### 2.6 Stockage (`src/storage`)
- Base relationnelle (PostgreSQL recommande) pour structure principale.
- Option index de recherche plein texte (Elasticsearch/OpenSearch) pour recherche documentaire.
- Tables minimales:
  - `documents`
  - `ocr_blocks`
  - `extracted_fields`
  - `validation_reports`

### 2.7 API et dashboard (`src/api`, `src/dashboard`)
- API pour consulter documents/champs.
- Tableau de bord KPI:
  - taux de reussite OCR,
  - precision extraction par champ,
  - documents en revue manuelle,
  - delai moyen de traitement.

## 3) Flux de donnees

1. Depot document dans `Data/raw_Data`.
2. Normalisation + pretraitement vers `Data/intermediate`.
3. OCR vers `outputs/ocr`.
4. Extraction vers `outputs/extraction`.
5. Insertion en base + export vers `Data/processed`.
6. Visualisation dans `outputs/visualization` / dashboard.

## 4) Strategie experimentale (doctorat)

- Definir un jeu de verite terrain dans `Data/annotations`.
- Mesurer:
  - OCR: CER/WER,
  - extraction: Precision/Recall/F1 par champ.
- Comparer plusieurs configurations:
  - pretraitement A/B,
  - OCR engine 1 vs 2,
  - extraction regles vs hybride.
- Versionner les experiences (`configs/` + `logs/` + `outputs/`).

## 5) Cas d'usage initial recommande: Factures STEG

Champs cibles v1:
- numero_facture
- date_facture
- client
- adresse
- periode_consommation
- montant_ht
- montant_tva
- montant_ttc
- compteur_id

## 6) Roadmap courte

1. Construire un pipeline minimal executable sur 20-50 factures STEG.
2. Ajouter evaluation automatique sur annotations.
3. Industrialiser stockage + API.
4. Ajouter dashboard de suivi qualite.
5. Etendre a d'autres types de documents.
