# Diagramme de cas d'utilisation — pfaEXTRACT

Le diagramme ci-dessous résume les acteurs et les cas d'utilisation principaux de l'application.

```mermaid
flowchart LR
    %% Acteurs
    U[Utilisateur]
    A[Administrateur / Opérateur]
    G[Service Gemini API]
    O[OCR Local<br/>(Tesseract / EasyOCR)]
    H[Stockage Historique<br/>(SQLite + JSON)]
    P[Service PDF ReportLab]

    %% Frontière système
    subgraph S["Système pfaEXTRACT (Streamlit)"]
        UC1((Importer un document<br/>(image/PDF)))
        UC2((Choisir type de document<br/>Auto / Médical / STEG / Ticket))
        UC3((Choisir méthode<br/>Gemini ou OCR local))
        UC4((Lancer extraction))
        UC5((Afficher résultats structurés))
        UC6((Générer rapport PDF))
        UC7((Consulter historique))
        UC8((Filtrer/Rechercher historique))
        UC9((Télécharger PDF / original / JSON))
        UC10((Supprimer une extraction))
        UC11((Aperçu document/PDF))
    end

    %% Interactions acteur principal
    U --> UC1
    U --> UC2
    U --> UC3
    U --> UC4
    U --> UC5
    U --> UC6
    U --> UC7
    U --> UC8
    U --> UC9
    U --> UC10
    U --> UC11

    %% Interactions opérateur/admin
    A --> UC7
    A --> UC8
    A --> UC10

    %% Dépendances techniques
    UC4 --> G
    UC4 --> O
    UC4 --> H
    UC6 --> P
    UC6 --> H
    UC7 --> H
    UC8 --> H
    UC9 --> H
    UC10 --> H
    UC11 --> H
```

## Acteurs

- `Utilisateur` : lance les extractions, consulte et exporte les résultats.
- `Administrateur / Opérateur` : supervise l'historique et supprime des entrées si nécessaire.

## Cas d'utilisation clés

- Import de documents médicaux, factures STEG, tickets.
- Extraction en mode cloud (`Gemini`) ou local (`OCR`).
- Visualisation des résultats structurés.
- Génération de rapport PDF.
- Gestion de l'historique : recherche, filtres, téléchargement, suppression.
