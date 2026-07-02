# Contrôle interne IMF

Application Streamlit de contrôle interne, de suivi des cycles d'activité et d'analyse métier, orientée import Excel/CSV et restitution sur une même plateforme.

## Présentation

L'application permet de :

- charger une base crédit depuis un fichier téléversé ou un fichier déjà présent dans `line_list/`
- standardiser automatiquement une partie des colonnes et des valeurs métier
- produire une synthèse standard avec KPI, graphiques, répartition par sexe, distribution par tranche d'âge et pyramide âge-sexe
- regrouper les blocs opérationnels dans l'onglet `Surveillance`
- exposer un onglet pédagogique `Notions importantes`
- analyser le portefeuille, le risque, la qualité des données et exporter un pack de restitution

L'objectif est de fournir à la direction, au contrôle interne, à la conformité et aux responsables opérationnels des informations fiables pour mieux piloter les cycles, renforcer les contrôles et réduire les risques.

## Démarrage rapide

### Environnement Python utilisé

```text
C:\ProgramData\anaconda3
```

### Installer les dépendances

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r requirements.txt
```

### Lancer l'application

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m streamlit run .\analyste_credit.py
```

### Lancer les tests

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m unittest discover -s tests -v
```

## Sources de données

L'application supporte :

- un téléversement local `.xlsx`, `.xls` ou `.csv`
- un fichier inclus dans `line_list/`

Exemple inclus :

- `line_list/base_donnees_brute_credit.xlsx`

Références de standardisation :

- `data/Rename_columns.xlsx`
- `data/Replace_values.xlsx`

## Interface actuelle

### Zone haute

La zone haute conserve la synthèse standard visible pendant toute la navigation :

- KPI de production, risque et remboursement
- `Distribution des statuts de dossier`
- `Évolution mensuelle des demandes`
- `Distribution des niveaux de risque`
- `Distribution par tranche d'âge`
- `Répartition par sexe`
- `Pyramide âge-sexe`

Une option latérale permet aussi :

- `Afficher annotations (valeurs)`
- définir un seuil minimal d'affichage des annotations

### Onglets disponibles

- `Vue d'ensemble active`
- `Notions importantes`
- `Surveillance`
- `Portefeuille`
- `Risque`
- `Qualité`
- `Export`
- `Méthodologie`

### Logique des onglets

- `Vue d'ensemble active` : confirme que la synthèse haute reste visible pendant la navigation
- `Notions importantes` : rappelle les notions métier, les KPI et les bonnes pratiques d'analyse crédit
- `Surveillance` : actions prioritaires, top agences, top produits, dossiers à suivre en priorité, aperçu des dossiers
- `Portefeuille` : production par produit, agent, agence et lecture croisée agence x statut
- `Risque` : distributions de risque, remboursement, classes de retard et watchlist
- `Qualité` : anomalies, valeurs manquantes et mapping source -> standard
- `Export` : export CSV et pack Excel
- `Méthodologie` : conventions, formules et logique de calcul

## Données attendues

Les analyses sont plus solides si la base contient au minimum :

- un identifiant client
- un identifiant dossier
- une date de demande
- un montant demandé
- un statut de dossier

Colonnes particulièrement utiles :

- `montant_accorde`
- `revenu_mensuel`
- `charge_mensuelle`
- `score_credit`
- `retard_jours`
- `statut_remboursement`
- `agence`
- `agent_credit`
- `type_produit`
- `date_decision`
- `duree_credit_mois`
- `sexe`
- `age`

## Variables dérivées

Variables calculées actuellement :

- `capacite_remboursement`
- `taux_endettement`
- `mensualite_estimee`
- `niveau_risque_calcule`
- `mois_demande`

Variables métier standardisées :

- `statut_dossier`
- `statut_remboursement`
- `sexe`
- `age`

## Conventions métier principales

### Capacité de remboursement

```text
Capacité de remboursement = Revenu mensuel - Charges mensuelles
```

### Taux d'endettement

```text
Taux d'endettement = Charges mensuelles / Revenu mensuel
```

Lecture usuelle :

```text
0 % à 30 %   -> risque faible
31 % à 50 %  -> risque moyen
plus de 50 % -> risque élevé
```

### Mensualité estimée

```text
Mensualité estimée = Montant accordé / Durée du crédit en mois
```

### Priorité de calcul du risque

1. niveau de risque déjà présent
2. score crédit
3. taux d'endettement
4. retard en jours

### Statuts métier suivis

- `Reçu`
- `À compléter`
- `En analyse`
- `Approuvé`
- `Rejeté`
- `Décaissé`
- `En remboursement`
- `En retard`
- `Clôturé`

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

## Exports disponibles

L'onglet `Export` permet de télécharger :

- les données standardisées en CSV
- un pack Excel contenant :
  - données standardisées
  - contrôles qualité
  - mapping des colonnes

## Structure du projet

```text
analyste_credit/
|-- analyste_credit.py
|-- README.md
|-- requirements.txt
|-- credit_app/
|   |-- app_loader.py
|   |-- core.py
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
|   |-- Replace_values.xlsx
|-- line_list/
|   |-- base_donnees_brute_credit.xlsx
|-- tests/
|   |-- test_credit_domain.py
```

## Fichiers principaux

- application principale : [analyste_credit.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/analyste_credit.py)
- logique métier : [credit_app/domain.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/domain.py)
- styles et composants UI : [credit_app/ui.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/ui.py)
- synthèse standard : [credit_app/tabs/overview.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/overview.py)
- notions importantes : [credit_app/tabs/analyste_credit.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/analyste_credit.py)
- surveillance : [credit_app/tabs/surveillance.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/surveillance.py)
- portefeuille : [credit_app/tabs/portfolio.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/portfolio.py)
- risque : [credit_app/tabs/risk.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/risk.py)
- qualité : [credit_app/tabs/quality.py](/C:/Users/Benjamin%20MUPANZI/Documents/analyste_credit/credit_app/tabs/quality.py)

## Vérification

Les tests couvrent notamment :

- la standardisation des colonnes
- les variables dérivées
- les contrôles qualité
- la synthèse métier
- la watchlist
- les distributions sexe / âge
- la pyramide âge-sexe
- le chargement du fichier Excel inclus

## Confidentialité

Les données manipulées dans ce projet sont sensibles et doivent être traitées avec confidentialité.

Bonnes pratiques :

- limiter l'accès aux données aux personnes autorisées
- éviter le partage non sécurisé des fichiers clients
- protéger les informations personnelles et financières
- documenter les modifications importantes
- conserver une traçabilité des décisions

## Limites actuelles

- la qualité des analyses dépend fortement des colonnes disponibles dans la source
- certaines règles de risque restent heuristiques et doivent être adaptées à votre institution
- selon l'installation locale Streamlit/Anaconda, un warning de scan de composants peut encore apparaître sans bloquer l'application

## Évolutions possibles

- tranches d'âge plus fines pour la pyramide âge-sexe
- paramètres de scoring crédit plus métier
- chargement multi-fichiers et consolidation
- mapping interactif des colonnes non reconnues
- rapports PDF ou exports de synthèse
