# Contrôle interne IMF

Plateforme Streamlit de contrôle interne pour institution de microfinance, orientée import Excel/CSV, standardisation métier et restitution d’analyses dans une interface unique.

## Présentation

L’application permet de :

- téléverser un fichier Excel ou CSV
- téléverser plusieurs fichiers Excel pour les compiler dans une même session
- relire un fichier déjà présent dans `line_list/`
- compiler plusieurs fichiers inclus pour les tests
- renommer automatiquement des colonnes hétérogènes à partir du référentiel interne
- nettoyer certaines valeurs métier à partir des fichiers de référence Excel
- piloter plusieurs cycles d’activité dans une seule plateforme
- conserver une synthèse standard visible pendant toute la navigation
- produire des analyses par onglet : vue d’ensemble, audit et contrôle, surveillance, portefeuille, risque, qualité, export et méthode
- générer des watchlists, des lectures métier et des actions prioritaires selon le cycle actif

L’objectif est de fournir à la direction, au contrôle interne, à la conformité et aux responsables opérationnels une lecture exploitable des risques, anomalies, volumes, écarts de procédure et points de contrôle.

## Cycles couverts

La plateforme gère actuellement les cycles suivants :

- `Cycle crédit`
- `Cycle épargne`
- `Suivi clients CRM`
- `Cycle caisse et guichet`
- `Cycle trésorerie et banque`
- `Cycle comptable et financier`
- `Cycle ressources humaines et administration`
- `Sécurité du système d’information`
- `Sauvegarde et continuité d’activité`
- `Likelemba solidaire`
- `Money Provider`

Chaque cycle dispose :

- d’un référentiel de champs attendus
- de filtres latéraux adaptés
- d’une vue d’ensemble contextualisée
- de règles de surveillance et de watchlist propres au métier
- d’un onglet d’audit et de méthode pour relier les résultats aux procédures

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

- le téléversement local de fichiers `.xlsx`, `.xls` et `.csv`
- le téléversement de plusieurs fichiers Excel détaillés pour compilation
- la relecture de fichiers déjà déposés dans `line_list/`
- la compilation de plusieurs fichiers inclus présents dans `line_list/`

Références de standardisation :

- `data/Rename_columns.xlsx` pour le renommage des colonnes
- `data/Replace_values.xlsx` pour l’harmonisation de certaines valeurs métier

Documents métier et procédures :

- `SOP/`

Important :

- `line_list/` sert surtout de zone de test locale
- en production, l’utilisateur peut travailler uniquement par téléversement sans déposer les fichiers sensibles dans le projet

## Interface actuelle

### Zone haute

La zone haute conserve une synthèse standard visible pendant toute la navigation. Selon le cycle et les colonnes disponibles, elle peut afficher :

- des KPI métier
- une distribution principale
- une évolution mensuelle ou temporelle
- des regroupements opérationnels
- la répartition par sexe
- la distribution par tranche d’âge
- la pyramide âge-sexe

### Barre latérale

Le panneau latéral permet de :

- choisir le cycle actif
- choisir la source de données
- téléverser un fichier unique ou plusieurs fichiers
- sélectionner une feuille Excel quand nécessaire
- appliquer des filtres métier adaptés au cycle
- filtrer sur la période principale du cycle
- consulter le résumé des filtres actifs
- visualiser la couverture du référentiel du cycle
- activer l’option `Afficher annotations (valeurs)`
- définir le taux `CDF/USD` pour le cycle épargne

Pour le cycle épargne, le taux `2300` signifie :

```text
1 USD = 2300,00 CDF
```

## Onglets disponibles

- `Vue d’ensemble active`
- `Audit et contrôle`
- `Surveillance`
- `Portefeuille`
- `Risque`
- `Qualité`
- `Export`
- `Méthode`

Onglet conditionnel :

- `Actions CRM`
  Cet onglet apparaît uniquement quand le cycle `Suivi clients CRM` est sélectionné.

## Logique des onglets

- `Vue d’ensemble active` : présente les KPI standard, graphiques principaux et repères synthétiques du cycle.
- `Audit et contrôle` : relie les analyses aux procédures, aux points de contrôle, aux référentiels métier et aux pièces attendues.
- `Actions CRM` : rassemble les corrections et relances prioritaires pour les fiches clients CRM.
- `Surveillance` : regroupe les actions prioritaires, les classements actifs, la watchlist et l’aperçu filtré.
- `Portefeuille` : montre les volumes, regroupements, répartitions et tableaux métier du cycle.
- `Risque` : consolide les signaux d’exposition, motifs d’alerte et distributions de risque.
- `Qualité` : expose les anomalies, les valeurs manquantes et le mapping source vers standard.
- `Export` : permet de télécharger les données standardisées et un pack Excel.
- `Méthode` : documente les conventions, les règles de lecture, la couverture et les limites d’interprétation.

## Fonctions métier déjà intégrées

### Standardisation

Le moteur métier :

- renomme automatiquement une partie des colonnes reconnues
- s’appuie sur `Rename_columns.xlsx` pour enrichir les alias internes
- convertit les colonnes numériques et les dates utiles
- nettoie certaines valeurs métier via `Replace_values.xlsx`
- normalise plusieurs statuts et libellés récurrents
- dérive des variables calculées quand cela est possible

Variables dérivées actuelles :

- `capacite_remboursement`
- `taux_endettement`
- `mensualite_estimee`
- `niveau_risque_calcule`
- `mois_demande`

### Contrôles qualité intégrés

Le projet vérifie notamment :

- clients sans identifiant
- dossiers dupliqués
- dossiers sans statut
- montants négatifs
- montants accordés supérieurs au montant demandé
- données financières manquantes
- capacité de remboursement négative
- retards négatifs

### Watchlists par cycle

Selon le cycle actif, la plateforme peut déjà remonter des alertes comme :

- référence manquante
- opérateur non renseigné
- écart de caisse
- écart de rapprochement
- écriture non équilibrée
- test de reprise non documenté
- téléphone non fiable
- compte inactif
- KYC incomplet
- client multi-comptes

## Règles métier renforcées

L’application intègre maintenant un référentiel métier plus proche des procédures, surtout pour l’épargne et le crédit.

### Référentiel épargne

Des références documentaires sont intégrées pour :

- `Compte Épargne Standard`
- `Dépôt à Terme (DAT)`
- `Compte Courant Commercial`
- `Elubu ya ba Maman`
- `Elenge ya Motuya`
- `Likelemba structurée`

Exemples de contrôles déjà exploités ou préparés :

- `DAT sous minimum attendu`
- `Taux DAT hors référentiel`
- `Produit femme à confirmer`
- lectures KYC, dormance, multi-comptes et comptes sensibles

### Référentiel crédit

Une matrice d’octroi et de tarification est intégrée pour des produits comme :

- `Lisungi`
- `Crédit salaires`
- `Crédit aux personnels`
- `Avance sur salaire`
- `Crédit Dare Dare`
- `Crédit PEPSI`
- `Crédit auto`
- `Crédit compte collectif`
- `Crédit LIKELEMBA`

Exemples de contrôles déjà exploités :

- `Garantie non renseignée`
- `Montant hors référentiel produit`
- `Durée hors référentiel produit`
- `Taux hors référentiel produit`
- `Avance sur salaire > 1/3 du salaire`

### KYC et conformité

Des référentiels documentaires sont également intégrés pour :

- les exigences KYC générales
- les pièces attendues à l’ouverture
- la checklist de dossier de crédit
- certains services et tarifs de référence

Ces éléments sont visibles dans les onglets `Audit et contrôle` et `Méthode`.

## Cycle épargne

Le cycle épargne contient des analyses standards et des analyses métier plus poussées.

Analyses standards affichées après la vue d’ensemble :

- `Distribution des produits d’épargne`
- `Dernière activité par mois`
- `Soldes cumulés par produit`
- `Portefeuille par gestionnaire`
- `Répartition par sexe`
- `Pyramide âge-sexe`

Analyses métier complémentaires :

- dormance des comptes
- clients multi-comptes
- comparaison des extractions
- complétude KYC
- qualité des téléphones
- rapport d’épargne reconstitué

### Rapport d’épargne reconstitué

L’onglet `Portefeuille` peut reconstituer un rapport d’épargne à partir des bases détaillées chargées dans la session.

Ce rapport permet notamment :

- de regrouper les soldes par famille de produit
- de convertir les montants CDF en équivalent USD selon le taux choisi
- de calculer un montant mobilisable selon des normes de lecture
- de comparer deux bundles ou deux dates si plusieurs extractions sont chargées

Si une seule extraction est présente, l’application le signale simplement avec un message en français courant.

## Cycle Suivi clients CRM

Le cycle `Suivi clients CRM` est conçu pour les exports CRMPlus Zoho.

Il permet notamment :

- de contrôler la qualité des fiches clients
- de repérer les téléphones ou e-mails non fiables
- d’identifier les pièces d’identité manquantes ou partagées
- de suivre l’inactivité client
- de produire une liste d’actions CRM rapide

Quand ce cycle est sélectionné, l’onglet `Actions CRM` apparaît et regroupe :

- les corrections prioritaires
- les relances d’inactivité
- les fiches verrouillées
- les cas de désabonnement ou de rejet d’e-mail

## Données attendues

La plateforme reste souple, mais les analyses sont meilleures si les bases contiennent des champs proches du référentiel du cycle actif.

Exemples de colonnes utiles :

- `client_id`
- `nom_client`
- `dossier_id`
- `compte_id`
- `date_demande`
- `date_decision`
- `date_operation`
- `montant_demande`
- `montant_accorde`
- `montant_operation`
- `solde_compte`
- `statut_dossier`
- `statut_remboursement`
- `statut_compte`
- `agence`
- `type_produit`
- `type_client`
- `agent_credit`
- `operateur`
- `tresorier`
- `journal`
- `compte_bancaire`
- `telephone`
- `sexe`
- `age`
- `garantie`
- `taux_interet`

## Exports disponibles

L’onglet `Export` permet de télécharger :

- les données standardisées en CSV
- un pack Excel contenant :
  les données standardisées
  les contrôles qualité
  le mapping des colonnes

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
|   |-- colonne_valeur/
|   |   |-- colonne_nettoyage.py
|   |   |-- valeurs_nettoyage.py
|   |   |-- valeurs_suppression.py
|   |   |-- valeurs_completude.py
|   |-- compilation/
|   |   |-- fichiers_compilation.py
|   |   |-- fichiers_nommage.py
|   |-- tabs/
|   |   |-- overview.py
|   |   |-- audit_control.py
|   |   |-- crm_clients.py
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
|-- SOP/
|-- tests/
|   |-- test_credit_domain.py
```

## Fichiers principaux

- application principale : [controle_interne.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/controle_interne.py)
- logique métier : [credit_app/domain.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/domain.py)
- référentiels métiers : [credit_app/control_references.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/control_references.py)
- cycles et presets : [credit_app/cycles.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/cycles.py)
- composants UI : [credit_app/ui.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/ui.py)
- synthèse standard : [credit_app/tabs/overview.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/overview.py)
- audit et contrôle : [credit_app/tabs/audit_control.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/audit_control.py)
- actions CRM : [credit_app/tabs/crm_clients.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/crm_clients.py)
- surveillance : [credit_app/tabs/surveillance.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/surveillance.py)
- portefeuille : [credit_app/tabs/portfolio.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/portfolio.py)
- risque : [credit_app/tabs/risk.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/risk.py)
- qualité : [credit_app/tabs/quality.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/quality.py)
- méthode : [credit_app/tabs/methodology.py](/C:/Users/Benjamin%20MUPANZI/Documents/controle_interne/credit_app/tabs/methodology.py)

## Vérification

Les tests couvrent notamment :

- la standardisation des colonnes
- le nettoyage de certaines valeurs métier
- les variables dérivées
- les contrôles qualité
- les watchlists par cycle
- les distributions sexe / âge
- la pyramide âge-sexe
- le cycle épargne
- le cycle CRM
- les règles de contrôle renforcées pour l’épargne et le crédit

Commande de vérification :

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m unittest discover -s tests -v
```

## Confidentialité

Les données manipulées dans ce projet sont sensibles et doivent être traitées avec confidentialité.

Bonnes pratiques :

- limiter l’accès aux données aux personnes autorisées
- éviter le partage non sécurisé des fichiers
- privilégier le téléversement ponctuel pour les données d’entreprise
- protéger les informations personnelles et financières
- documenter les modifications importantes
- conserver une traçabilité des décisions et des corrections

## Limites actuelles

- la qualité des analyses dépend fortement des colonnes disponibles dans la source
- certaines règles restent des signaux de contrôle et non une preuve définitive
- plusieurs contrôles avancés exigent encore des colonnes supplémentaires
  comme les frais réellement facturés, le nombre de retraits mensuels, le préavis ou les pièces détaillées du dossier
- selon l’installation locale Streamlit/Anaconda, certains warnings techniques peuvent apparaître sans bloquer l’application

## Évolutions possibles

- mapping interactif des colonnes non reconnues
- enrichissement des contrôles automatiques par cycle
- consolidation multi-périodes plus poussée
- exports de rapports de synthèse plus formalisés
- tableaux de bord historiques par campagne de contrôle
- contrôle documentaire encore plus fin pour le crédit, l’épargne et les cycles support
