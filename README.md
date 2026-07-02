# Contrôle interne IMF

Plateforme Streamlit de contrôle interne pour IMF, orientée import Excel/CSV, standardisation métier et restitution sur une interface unique.

## Présentation

L’application permet de :

- charger une base `.xlsx`, `.xls` ou `.csv`
- standardiser automatiquement des colonnes métier hétérogènes
- piloter plusieurs cycles d’activité dans une même plateforme
- conserver une synthèse standard visible pendant la navigation
- produire des analyses par onglet : surveillance, portefeuille, risque, qualité, export et méthodologie
- générer des watchlists et des actions prioritaires selon le cycle actif

L’objectif est de fournir à la direction, au contrôle interne, à la conformité et aux responsables opérationnels une lecture fiable des risques, anomalies, volumes et points de contrôle.

## Cycles couverts

La plateforme gère actuellement les cycles suivants :

- `Crédit`
- `Likelemba solidaire`
- `Épargne`
- `Caisse et guichet`
- `Trésorerie et banque`
- `Comptable et financier`
- `Ressources humaines et administration`
- `Sécurité du système d’information`
- `Sauvegarde et continuité d’activité`
- `Money Provider`

Chaque cycle dispose :

- d’un référentiel de champs attendus
- de filtres latéraux adaptés
- d’une vue d’ensemble contextualisée
- de règles de watchlist et de surveillance métier

## Démarrage rapide

### Environnement Python utilisé

```text
C:\ProgramData\anaconda3
```

### Installer les dépendances

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r requirements.txt
```

### Lancer l’application

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m streamlit run .\controle_interne.py
```

### Lancer les tests

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m unittest discover -s tests -v
```

## Sources de données

L’application supporte :

- le téléversement local de fichiers Excel ou CSV
- la relecture de fichiers déjà déposés dans `line_list/`

Exemple inclus :

- `line_list/base_donnees_brute_credit.xlsx`

Références de standardisation :

- `data/Rename_columns.xlsx`

Documents de référence métier disponibles dans le projet :

- `SOP/`

## Interface actuelle

### Zone haute

La zone haute conserve une synthèse standard visible pendant toute la navigation. Selon le cycle et les colonnes disponibles, elle affiche notamment :

- des KPI métier
- une distribution principale
- une évolution mensuelle
- des regroupements opérationnels
- la répartition par sexe
- la distribution par tranche d’âge
- la pyramide âge-sexe

### Sidebar

Le panneau latéral permet de :

- choisir le cycle actif
- choisir la source des données
- appliquer des filtres dynamiques adaptés au cycle
- filtrer sur la période pilote du cycle
- consulter le résumé des filtres actifs
- visualiser la couverture du référentiel de cycle
- activer l’option `Afficher annotations (valeurs)`

### Onglets disponibles

- `Vue d’ensemble active`
- `Notions importantes`
- `Surveillance`
- `Portefeuille`
- `Risque`
- `Qualité`
- `Export`
- `Méthodologie`

## Logique des onglets

- `Vue d’ensemble active` : confirme que la synthèse haute reste visible pendant la navigation.
- `Notions importantes` : rappelle les notions métier, les définitions, les indicateurs et les bonnes pratiques de lecture.
- `Surveillance` : regroupe les actions prioritaires, les classements actifs, la watchlist et l’aperçu filtré.
- `Portefeuille` : montre les volumes, regroupements, croisements et répartitions métier du cycle.
- `Risque` : consolide les alertes, distributions, motifs d’anomalie et watchlists.
- `Qualité` : expose anomalies, valeurs manquantes et mapping source → standard.
- `Export` : permet de télécharger les données standardisées et un pack Excel.
- `Méthodologie` : documente conventions, champs attendus, couverture et logique de calcul.

## Données attendues

La plateforme reste souple, mais les analyses sont meilleures si les bases contiennent des champs proches du référentiel du cycle actif.

Exemples de colonnes utiles selon les cas :

- `client_id`
- `dossier_id`
- `date_demande`
- `date_operation`
- `montant_demande`
- `montant_accorde`
- `montant_operation`
- `statut_dossier`
- `statut_remboursement`
- `agence`
- `type_produit`
- `agent_credit`
- `operateur`
- `tresorier`
- `journal`
- `compte_bancaire`
- `statut_compte`
- `sexe`
- `age`

## Standardisation métier

Le moteur métier :

- renomme automatiquement une partie des colonnes reconnues
- convertit les colonnes numériques et dates utiles
- normalise certains statuts et valeurs métier
- dérive des variables calculées lorsqu’elles sont possibles

Variables dérivées actuellement :

- `capacite_remboursement`
- `taux_endettement`
- `mensualite_estimee`
- `niveau_risque_calcule`
- `mois_demande`

## Contrôles qualité intégrés

Le projet vérifie notamment :

- clients sans identifiant
- dossiers dupliqués
- dossiers sans statut
- montants négatifs
- montants accordés supérieurs au montant demandé
- données financières manquantes
- capacité de remboursement négative
- retards négatifs

Selon le cycle actif, des watchlists spécifiques peuvent aussi être construites, par exemple :

- référence manquante
- opérateur non renseigné
- écart de caisse
- écart de rapprochement
- écriture non équilibrée
- test de reprise non documenté

## Exports disponibles

L’onglet `Export` permet de télécharger :

- les données standardisées en CSV
- un pack Excel contenant :
  - les données standardisées
  - les contrôles qualité
  - le mapping des colonnes

## Structure du projet

```text
controle_interne/
|-- controle_interne.py
|-- README.md
|-- requirements.txt
|-- credit_app/
|   |-- app_loader.py
|   |-- core.py
|   |-- cycles.py
|   |-- control_references.py
|   |-- domain.py
|   |-- ui.py
|   |-- tabs/
|   |   |-- overview.py
|   |   |-- analyste_credit.py
|   |   |-- surveillance.py
|   |   |-- portfolio.py
|   |   |-- risk.py
|   |   |-- quality.py
|   |   |-- export.py
|   |   |-- methodology.py
|-- data/
|   |-- Rename_columns.xlsx
|-- line_list/
|   |-- base_donnees_brute_credit.xlsx
|-- SOP/
|-- tests/
|   |-- test_credit_domain.py
```

## Fichiers principaux

- application principale : [controle_interne.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/controle_interne.py)
- logique métier : [credit_app/domain.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/domain.py)
- cycles et presets : [credit_app/cycles.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/cycles.py)
- composants UI : [credit_app/ui.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/ui.py)
- synthèse standard : [credit_app/tabs/overview.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/overview.py)
- notions importantes : [credit_app/tabs/analyste_credit.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/analyste_credit.py)
- surveillance : [credit_app/tabs/surveillance.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/surveillance.py)
- portefeuille : [credit_app/tabs/portfolio.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/portfolio.py)
- risque : [credit_app/tabs/risk.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/risk.py)
- qualité : [credit_app/tabs/quality.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/quality.py)
- méthodologie : [credit_app/tabs/methodology.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/methodology.py)

## Vérification

Les tests couvrent notamment :

- la standardisation des colonnes
- les variables dérivées
- les contrôles qualité
- la synthèse métier
- les watchlists
- les distributions sexe / âge
- la pyramide âge-sexe
- le chargement du fichier Excel inclus
- la logique des séries par cycle
- les watchlists et filtres génériques hors crédit

## Confidentialité

Les données manipulées dans ce projet sont sensibles et doivent être traitées avec confidentialité.

Bonnes pratiques :

- limiter l’accès aux données aux personnes autorisées
- éviter le partage non sécurisé des fichiers
- protéger les informations personnelles et financières
- documenter les modifications importantes
- conserver une traçabilité des décisions et des corrections

## Limites actuelles

- la qualité des analyses dépend fortement des colonnes disponibles dans la source
- certaines règles de risque et d’alerte restent heuristiques
- certains cycles seront encore meilleurs avec des bases plus riches et plus normalisées
- selon l’installation locale Streamlit/Anaconda, un warning de cache ou de composants peut apparaître sans bloquer l’application

## Évolutions possibles

- mapping interactif des colonnes non reconnues
- chargement multi-fichiers et consolidation
- exports PDF ou rapports de synthèse
- règles de contrôle encore plus fines par cycle
- tableaux de bord historiques par période ou par campagne de contrôle
