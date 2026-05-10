# Préparer le rapport et la soutenance PFA (pfaEXTRACT)

Ce document t’aide à **rédiger ton rapport** et à **préparer l’oral** en t’appuyant sur **ce qui existe réellement** dans le dépôt, sans inventer de fonctionnalités absentes du code. À utiliser avec `docs/GUIDE_COMPLET.md` (détail technique) et `docs/ARCHITECTURE.md` (vision plus large / recherche, à citer avec prudence : beaucoup de points y sont **cibles** et non encore implémentés).

---

## 1. Message clé du projet (à mettre en introduction)

**Problème** : des documents papier ou PDF (factures STEG, comptes rendus d’analyses, tickets de caisse) contiennent des informations utiles mais **non structurées**.

**Solution réalisée** : une application **Python** qui permet d’**uploader** un document, d’**extraire automatiquement** des champs cibles (selon le type), d’**afficher** les résultats sous forme de tableaux, d’**exporter** du JSON et de **consulter un historique** des extractions réussies.

**Positionnement honnête pour un PFA** : prototype de **plateforme d’extraction intelligente** combinant **OCR local** (Tesseract, OpenCV pour prétraitement), **compréhension par modèle de langage multimodal** (Google Gemini), et **interface web** (Streamlit). Pas de base de données relationnelle ni d’API REST documentée dans le code actuel : la persistance est **fichiers JSON**.

---

## 2. Plan type de rapport (aligné sur le projet)

Tu peux adapter les titres aux exigences de ton établissement ; l’ordre ci-dessous est classique pour un rapport PFA informatique / data.

### Chapitre 1 — Contexte et problématique

- Contexte : gestion de documents administratifs / santé / énergie en Tunisie (STEG), besoin de numérisation et d’exploitation des données.
- Problématique : coût du saisie manuelle, erreurs, besoin d’automatisation partielle avec **contrôle humain** possible.
- Périmètre **réel** du projet : trois familles de documents traitées dans l’application (voir chapitre 3).

### Chapitre 2 — Objectifs

**Objectifs fonctionnels** (vérifiables dans l’app) :

- Charger une image ou un PDF (selon les modes).
- Choisir le type de document ou laisser la **détection automatique** (`document_router.py`).
- Obtenir une **structure de données** (tableaux + JSON).
- **Télécharger** le JSON ; consulter l’**historique** avec filtres (`1_Historiques.py`).

**Objectifs techniques** :

- Intégrer **Gemini** avec clé API et paramètres (modèle, retries).
- Chaîner **OCR + règles** pour le médical et le STEG en mode OCR ; fusion possible avec Gemini pour le médical (`medical_pipeline.py`).

### Chapitre 3 — Analyse des besoins et cas d’usage

Présente **un cas d’usage par type** :

| Type | Besoin métier (exemples de champs) | Réalisation dans le code |
|------|-----------------------------------|---------------------------|
| Analyse médicale | Patient, médecin, date, liste d’analyses | `extract_medical_report_gemini.py` (JSON simple) ; pipeline OCR + schéma Pydantic dans `medical_pipeline.py` / `schemas.py` |
| Facture STEG | Référence, montant à payer, dates, période | `extract_steg_invoice_gemini.py` ; OCR riche dans `steg_invoice_extractor.py` |
| Ticket de caisse | Magasin, lignes articles, total | `extract_receipt_gemini.py` |

Ajoute un **diagramme de cas d’utilisation** (UML simplifié) : acteur « Utilisateur », cas « Extraire document », « Consulter historique », « Exporter JSON ».

### Chapitre 4 — Conception et architecture

- **Schéma global** (à reproduire dans le rapport) : navigateur → Streamlit → services / pipelines → fichiers + API Gemini (inspiré du schéma dans `GUIDE_COMPLET.md`).
- **Modules principaux** : `src/web/` (UI), `src/services/` (routage, historique, LLM), `src/extraction/` (OCR + prétraitement), `pipelines/` (prompts Gemini vision JSON), `src/gemini_vision.py` (appels API, retries, fallback modèle).
- **Données** : schéma JSON d’historique (`_meta` : `saved_at`, `source_filename`, `kind`) — voir `extraction_history.py`.
- **Distinction importante** : `docs/ARCHITECTURE.md` décrit une **architecture cible** (ingestion, preprocessing dédié, API, SQL, dashboard analytique). Pour le PFA, précise ce qui est **fait** vs **prévu / perspective de recherche** pour ne pas sur vendre.

### Chapitre 5 — Réalisation technique

Sous-parties possibles :

1. **Interface (Streamlit)**  
   Fichiers : `app.py`, `pages/1_Historiques.py`, `history_views.py`.  
   Parle de formulaires, upload, `session_state` pour les filtres, multi-pages.

2. **Routage et détection**  
   `document_router.py` : heuristiques nom de fichier + OCR léger pour classer STEG / ticket / médical.

3. **Prétraitement d’image**  
   Pas un dossier `src/preprocessing/` séparé, mais **fonctions intégrées** : `deskew_image`, `preprocess_roi`, variantes de binarisation dans `steg_invoice_extractor.py` et `medical_analysis_extractor.py` (OpenCV).

4. **OCR**  
   Tesseract, langues, zones d’intérêt (ROI) pour STEG et médical.

5. **Gemini**  
   Deux usages : vision JSON (`google-genai`, `generate_vision_json`) pour tickets / STEG Gemini / rapport médical « simple » ; `google-generativeai` dans `gemini_llm.py` pour le schéma médical détaillé. Tu peux expliquer **pourquoi** deux SDK (historique d’intégration / contraintes API).

6. **Configuration et sécurité**  
   `.env`, clé API, ne pas commiter les secrets ; limitation : Streamlit local vs déploiement public.

### Chapitre 6 — Expérimentation / résultats / démonstration

- **Jeu de tests** : quelques images/PDF réels ou anonymisés (respect RGPD / consentement).
- **Captures d’écran** : page principale après extraction ; page historique avec filtres ; exemple de JSON.
- **Critères qualitatifs** : champs corrects / manquants / hallucinations possibles du LLM ; intérêt de l’OCR + Gemini combinés pour le médical.
- Si tu n’as pas de métriques quantitatives (précision par champ), dis-le clairement et propose une **piste d’évaluation** (jeu annoté, comparaison champ à champ).

### Chapitre 7 — Difficultés, limites, perspectives

**Limites réalistes** (bonnes pour un jury) :

- Pas de base SQL ; historique en fichiers.
- STEG et tickets Gemini : **image seule**, pas PDF dans ces flux.
- Dépendance réseau et **quota** Gemini ; coût éventuel.
- Qualité variable selon scan, bruit, écriture manuscrite.
- Fuseau horaire UTC pour les dates d’historique (nuance expliquée dans le guide).

**Perspectives** : API REST, base de données, prétraitement unifié, évaluation sur corpus annoté, authentification, déploiement sécurisé (cf. `ARCHITECTURE.md`).

### Chapitre 8 — Conclusion

- Rappel des objectifs et de ce qui a été **livré**.
- Apports personnels (techniques et méthodologiques).
- Ouverture.

**Bibliographie / Webographie** : Streamlit, Tesseract, OpenCV, Google AI / Gemini, Pydantic, éventuellement articles sur extraction de factures ou documents médicaux.

---

## 3. Liste de figures et annexes recommandées

| # | Contenu |
|---|--------|
| 1 | Schéma d’architecture (boîtes : UI, services, OCR, Gemini, stockage) |
| 2 | Capture : interface principale (sidebar + résultat) |
| 3 | Capture : historique + détail d’une ligne |
| 4 | Exemple de JSON exporté (anonymisé) |
| 5 | Pseudo-code ou flux : « upload → routage → extraction → sauvegarde » |
| Annexe A | Extraits de code commentés (courts) ou lien vers le dépôt |
| Annexe B | Variables d’environnement (tableau depuis `.env.example`) |

---

## 4. Oral de soutenance (structure 10–20 min)

1. **Accroche** (30 s) : problème des documents non structurés.  
2. **Objectifs et périmètre** (1–2 min) : trois types de documents, une application démo.  
3. **Démo live ou vidéo** (3–5 min) : un upload par type ou au moins un cas représentatif + historique.  
4. **Architecture** (2–3 min) : un schéma, Stack Python + Streamlit + Gemini + OCR.  
5. **Choix techniques** (1–2 min) : pourquoi Streamlit pour un PFA itératif ; pourquoi Gemini pour la variété des mises en page.  
6. **Difficultés et limites** (1 min) : honnêteté = crédibilité.  
7. **Conclusion et perspectives** (30 s–1 min).

**Questions possibles du jury** (prépare des réponses courtes) :

- Comment garantissez-vous la **fiabilité** des montants / données médicales ?  
  → Réponse : extraction assistée, **vérification humaine** obligatoire en production ; prompts qui demandent de ne pas inventer ; limites connues des LLM.

- Où sont stockées les données ?  
  → JSON sur disque, pas de BDD dans cette version.

- Différence entre OCR seul et Gemini ?  
  → OCR : rapide, local, sensible au bruit ; Gemini : meilleure compréhension de la mise en page, mais API externe et coût/latence.

---

## 5. Ce qu’il ne faut pas écrire si ce n’est pas fait

Pour rester **aligné avec le code** :

- Ne pas affirmer qu’il existe une **API REST** documentée pour des clients tiers (l’app est Streamlit monolithique).
- Ne pas affirmer une **base PostgreSQL** ou un **dashboard analytique KPI** complet si tu ne les as pas implémentés.
- Ne pas présenter tout le chapitre 2 de `ARCHITECTURE.md` comme « livré » : le présenter comme **vision** ou **travaux futurs** si ce n’est pas dans le dépôt.

Tu peux au contraire valoriser : **détection multi-documents**, **hybride OCR + LLM**, **historique consultable**, **export structuré**, **prétraitement image** dans les extracteurs STEG/médical.

---

## 6. Liens internes utiles lors de la rédaction

| Sujet | Fichier |
|-------|---------|
| Détail technique global | `docs/GUIDE_COMPLET.md` |
| Vision long terme / recherche | `docs/ARCHITECTURE.md` |
| Lancement et dépendances | `README.md` |

---

*Bonne rédaction et bonne soutenance.*
