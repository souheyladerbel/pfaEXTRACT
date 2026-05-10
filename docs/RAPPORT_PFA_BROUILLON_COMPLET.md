# Rapport PFA (Brouillon complet)

## Titre propose
Conception et implementation d'une plateforme intelligente d'extraction documentaire multi-domaines

## Resume
Ce projet de fin d'annee porte sur la conception et le developpement d'une plateforme intelligente d'extraction d'informations structurees a partir de documents heterogenes (images et PDF). La solution proposee, pfaEXTRACT, combine des techniques d'OCR local et des modeles Gemini afin de traiter trois cas d'usage principaux: analyses medicales, factures STEG et tickets de caisse. Le systeme offre une interface web Streamlit pour l'import de documents, l'extraction automatique, l'affichage des resultats, l'historisation des traitements (JSON + SQLite) et la generation de rapports PDF. La demarche methodologique adoptee articule une gestion agile du developpement (SCRUM/XP) et un cadre Data Science de type CRISP-DM. Les resultats obtenus montrent la faisabilite de l'approche hybride, tout en mettant en evidence des limites liees a la qualite des documents et aux contraintes de quota des services cloud. Le projet ouvre des perspectives d'industrialisation vers une architecture API, une base relationnelle evolutive et un tableau de bord analytique.

Mots-cles: OCR, extraction d'information, Gemini, Streamlit, CRISP-DM, documents non structures.

---

## Table des matieres
1. Introduction  
2. Contexte et problematique  
3. Etat de l'art  
4. Methodologie  
   4.1 Methodologie de travail (SCRUM / XP)  
   4.2 Methodologie Data Science (CRISP-DM)  
5. Analyse des besoins  
6. Conception (architecture et UML)  
7. Implementation  
8. Resultats et tests  
9. Discussion  
10. Conclusion et perspectives  
11. Conseils de mise en forme et conformite  
12. Annexes utiles (phrases, erreurs a eviter)

---

## 1. Introduction
Dans un contexte de transformation numerique, les organisations manipulent un volume croissant de documents non structures (factures, comptes rendus medicaux, tickets, formulaires), dont l'exploitation manuelle demeure couteuse, lente et sujette a des erreurs. Cette problematique est particulierement marquee lorsque les documents presentent une forte variabilite de mise en page, de qualite visuelle ou de terminologie.

Le present Projet de Fin d'Annee s'inscrit dans cette perspective et vise a concevoir et implementer une plateforme intelligente d'extraction d'informations structurees a partir de documents heterogenes. La solution proposee, nommee pfaEXTRACT, combine des techniques d'OCR local et des modeles de comprehension documentaire bases sur Gemini, afin d'augmenter la robustesse de l'extraction selon le type de document traite.

Le systeme couvre trois cas d'usage principaux: les analyses medicales, les factures STEG et les tickets de caisse. Il integre egalement des fonctionnalites de visualisation des resultats, d'historisation des extractions (JSON + SQLite) et de generation de rapports PDF, de maniere a assurer la tracabilite et l'exploitabilite des donnees produites.

Sur le plan methodologique, ce travail adopte une demarche hybride associant les principes des methodes agiles (pour l'organisation et l'iteration de developpement) et le cadre CRISP-DM (pour la structuration des etapes Data Science). Cette double approche permet d'aligner les besoins metier, les choix techniques et l'evaluation des performances du systeme.

---

## 2. Contexte et problematique

### 2.1 Contexte
Les structures medicales et administratives traitent quotidiennement des documents scannes, photographies ou exportes en PDF. Ces donnees sont souvent difficiles a exploiter directement pour la recherche d'information, la prise de decision ou l'alimentation d'applications metier.

### 2.2 Problematique
Le traitement manuel entraine:
- un cout operationnel eleve,
- des delais de traitement importants,
- des erreurs de saisie,
- une faible standardisation des sorties.

La question centrale du projet est donc la suivante: **comment automatiser l'extraction de donnees pertinentes depuis des documents heterogenes, avec une precision suffisante et une restitution exploitable?**

### 2.3 Objectifs
- Construire une chaine d'extraction de bout en bout pour plusieurs types de documents.
- Proposer une interface simple d'utilisation pour import, extraction et visualisation.
- Sauvegarder les resultats de facon traçable et consultable.
- Produire des sorties exportables (JSON, PDF) reutilisables dans des flux metier.

---

## 3. Etat de l'art

### 3.1 OCR classique
Les moteurs OCR (ex. Tesseract) convertissent l'image en texte. Ils sont efficaces sur des documents lisibles mais restent sensibles au bruit, aux rotations, aux faibles resolutions et aux variations de mise en page.

### 3.2 Extraction basee sur regles
Les approches par regex et heuristiques sont performantes sur des formats stables (ex. factures normalisees), mais perdent en robustesse quand la structure change.

### 3.3 Modeles IA et Vision-Language
Les modeles de type Gemini permettent de mieux interpreter le contexte semantique et la structure implicite du document. Ils ameliorent souvent la qualite d'extraction sur des documents complexes, mais introduisent des contraintes de cout, quota et dependance cloud.

### 3.4 Positionnement du projet
Le projet adopte une approche **hybride**:
- OCR local lorsque possible (autonomie, cout reduit),
- Gemini sur les cas complexes (meilleure comprehension),
- schema JSON cible pour standardiser les resultats.

---

## 4. Methodologie

### 4.1 Methodologie de travail (SCRUM / XP)
La conduite du projet a repose sur une organisation agile inspiree de SCRUM, permettant de structurer le developpement en iterations courtes et orientees valeur. Le travail a ete decoupe en sprints successifs, chacun associe a des objectifs precis: mise en place de l'interface d'extraction, integration des pipelines documentaires, gestion de l'historique, puis export PDF et amelioration de l'ergonomie.

Le backlog a ete formalise sous forme de fonctionnalites prioritaires (user stories), par exemple: "en tant qu'utilisateur, je souhaite importer un document et obtenir automatiquement les champs extraits", ou "en tant qu'operateur, je souhaite consulter l'historique pour auditer les traitements." A la fin de chaque sprint, une revue fonctionnelle a permis de valider les livrables, d'identifier les anomalies et de reajuster les priorites.

En complement, plusieurs pratiques issues d'XP ont ete mobilisees: refactoring continu pour ameliorer la lisibilite du code, tests progressifs des fonctionnalites critiques, et livraison incrementale de versions exploitables. Cette approche a favorise la reduction du risque technique, la correction rapide des defauts et l'amelioration continue de la qualite logicielle.

Ainsi, la methodologie agile adoptee a permis d'assurer un pilotage souple, une meilleure maitrise des delais et une adaptation constante aux contraintes techniques (notamment la variabilite des documents et la dependance aux services cloud).

### 4.2 Methodologie Data Science (CRISP-DM)
Le cycle CRISP-DM a servi de cadre pour structurer la partie extraction intelligente et garantir la coherence entre objectifs metier et performances techniques.

**Business Understanding**  
Le besoin principal consiste a automatiser l'extraction de champs utiles a partir de documents non structures, tout en conservant une tracabilite des resultats et une restitution lisible pour l'utilisateur final.

**Data Understanding**  
Les donnees traitees regroupent des documents heterogenes (images/PDF) de natures differentes (medical, facturation STEG, ticket), avec une variabilite importante en termes de qualite, de mise en page et de densite textuelle.

**Data Preparation**  
Cette etape inclut le chargement des fichiers, les transformations necessaires selon le type (lecture image/PDF), et la preparation des contenus pour les moteurs d'extraction (OCR local, pipeline Gemini vision). Les sorties sont normalisees vers des schemas JSON adaptes au type documentaire.

**Modeling**  
Une strategie hybride est adoptee: extraction OCR/regles pour certains scenarios, et extraction assistee par modele Gemini pour ameliorer la couverture sur documents complexes. Le routage du document vers le pipeline pertinent constitue un element central de la modelisation.

**Evaluation**  
L'evaluation s'appuie sur la qualite des champs extraits (completude, coherence, lisibilite metier), l'analyse des cas d'echec (documents bruites, ambiguïtes de texte, limites de quota API), et la validation fonctionnelle via l'interface et l'historique.

**Deployment**  
Le deploiement operationnel est assure via une application Streamlit permettant l'extraction, la consultation des resultats, leur archivage et l'export PDF. Cette phase confirme l'utilisabilite de la solution dans un contexte reel de traitement documentaire.

---

## 5. Analyse des besoins

### 5.1 Besoins fonctionnels
- Importer un document image/PDF.
- Selectionner un mode de traitement (auto, medical, STEG, ticket).
- Choisir la methode (OCR local, Gemini selon disponibilite).
- Afficher les resultats structures sous forme lisible.
- Enregistrer les extractions en historique.
- Exporter les resultats en JSON et PDF.
- Consulter, filtrer et supprimer des extractions historiques.

### 5.2 Besoins non fonctionnels
- Performance acceptable pour un usage interactif.
- Robustesse face a des documents imparfaits.
- Traçabilite des traitements et auditabilite.
- Maintenabilite et modularite du code.
- Simplicite d'utilisation de l'interface.

### 5.3 Contraintes
- Dependance a la qualite d'image et au OCR.
- Quotas et couts potentiels de l'API Gemini.
- Heterogeneite forte des formats documentaires.

---

## 6. Conception (architecture et UML)

### 6.1 Vue d'architecture
L'architecture implementee repose sur Streamlit (front + orchestration), des services Python modulaires (routage, extraction, historique) et une persistance locale (SQLite + JSON).

### 6.2 Flux principal
1. Upload du document.
2. Detection/routage du type.
3. Extraction via pipeline adapte (OCR/Gemini).
4. Affichage des resultats.
5. Sauvegarde historique.
6. Export PDF/JSON.

### 6.3 Diagrammes UML a inclure
- Diagramme de cas d'utilisation (utilisateur, operateur, API Gemini, stockage).
- Diagramme de sequence (upload -> extraction -> sauvegarde -> restitution).
- Diagramme de composants (UI Streamlit, services, pipelines, stockage).

---

## 7. Implementation

### 7.1 Technologies
- Python, Streamlit
- Tesseract / EasyOCR
- Gemini (`google-genai`, `google-generativeai`)
- SQLite, JSON
- ReportLab, pandas, Pydantic

### 7.2 Modules cles
- `src/web/pages/1_Extraction.py`: upload, execution extraction, affichage resultat.
- `src/services/document_router.py`: detection de type et orchestration.
- `src/gemini_vision.py`: appels Gemini vision JSON + gestion retry.
- `src/services/extraction_history.py`: sauvegarde/lecture historique.
- `src/services/extraction_report_pdf.py`: generation des rapports PDF.

### 7.3 Choix techniques
- Modularite pour faciliter l'evolution des pipelines.
- Approche hybride OCR + Gemini pour couvrir plus de cas.
- Historique local pour audit et reproductibilite.

---

## 8. Resultats et tests

### 8.1 Resultats attendus
- Extraction correcte des champs principaux selon le type de document.
- Affichage clair des resultats (tableaux, details, export).
- Historique consultable et filtrable.

### 8.2 Strategie de test
- Tests fonctionnels par scenario (medical, STEG, ticket).
- Tests d'erreur (absence cle API, quota depasse, fichier invalide).
- Verification de la persistance (JSON + SQLite).
- Verification export PDF.

### 8.3 Indicateurs a renseigner par l'etudiante
- Nombre de documents testes par type.
- Taux de champs correctement extraits.
- Temps moyen de traitement.
- Principales causes d'echec.

---

## 9. Discussion
Les premiers resultats confirment l'interet de l'approche hybride: les methodes locales offrent une base autonome, tandis que Gemini ameliore la qualite de comprehension sur des documents complexes. Cependant, la performance globale depend de la qualite des entrees et des contraintes externes (quota cloud, lisibilite des scans). Le systeme presente un bon compromis pour un prototype academique orienté vers une future industrialisation.

---

## 10. Conclusion et perspectives
Ce PFA a permis de concevoir et de realiser une plateforme operationnelle d'extraction documentaire multi-domaines. Le projet a adresse les enjeux de structuration des donnees, de visualisation et de tracabilite dans un cadre pratique et reproductible.

Les perspectives prioritaires sont:
- mise en place d'une evaluation quantitative plus fine (precision/rappel/F1 par champ),
- integration d'une API dediee,
- migration vers une base relationnelle plus evolutive,
- construction d'un dashboard analytique avance,
- extension a de nouveaux types documentaires.

---

## 11. Conformite de forme (checklist)
Appliquer dans Word:
- Police: Times New Roman, taille 12.
- Interligne: 1,5.
- Marges: 2,5 cm sur les 4 cotes.
- Numerotation des sections: 1, 1.1, 1.1.1.
- Table des matieres automatique.
- Legendes numerotees pour figures et tableaux.

---

## 12. Annexes utiles

### 12.1 Titres professionnels proposes
- Extraction automatique d'informations structurees depuis des documents heterogenes: conception et implementation d'une plateforme intelligente
- Approche hybride OCR-Gemini pour l'analyse documentaire multi-domaines
- Plateforme de traitement documentaire intelligent pour analyses medicales, factures et tickets

### 12.2 Phrases reutilisables
- "L'architecture retenue privilegie une approche modulaire afin d'assurer la maintenabilite et l'evolutivite du systeme."
- "Le choix d'une strategie hybride OCR/LLM repond a la variabilite structurelle des documents traites."
- "La traçabilite des extractions est assuree par un mecanisme d'historisation combinant persistance JSON et indexation SQLite."

### 12.3 Erreurs frequentes a eviter
- Decrire les outils sans expliciter clairement le probleme metier.
- Melanger etat de l'art et implementation pratique.
- Donner des resultats sans protocole de test ni indicateurs.
- Oublier les limites et les perspectives.
- Inserer des captures sans interpretation analytique.

---

## Partie a completer apres reception du guide officiel
- Page de garde exacte selon ton etablissement.
- Style de citations et bibliographie exige (IEEE/APA/ISO 690...).
- Regles precises de pagination, en-tetes/pieds et numerotation des annexes.
- Formulation finale selon les consignes officielles du PDF de redaction.
