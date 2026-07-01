# Analyste Credit

Application Streamlit de standardisation et d'analyse credit, orientee import Excel/CSV et restitution sur une meme plateforme.

Le projet permet de :

- charger une base credit depuis un fichier televerse ou un fichier deja present dans `line_list/`
- standardiser automatiquement une partie des colonnes et de certaines valeurs metier
- produire une synthese standard avec KPI, graphiques, repartition par sexe, distribution par tranche d'age et pyramide age-sexe
- regrouper les blocs operationnels dans un onglet `Surveillance`
- exposer un onglet pedagogique sur les notions importantes du metier d'analyste credit
- analyser le portefeuille, le risque, la qualite des donnees et exporter un pack de restitution

## Presentation du projet

Ce projet vise a mettre en place un systeme structure d'analyse, de suivi et de reporting des demandes de credit au sein de l'organisation.

Il appuie la prise de decision sur l'octroi ou le refus de credit, tout en renforcant :

- le suivi des clients
- la gestion des risques
- la qualite des donnees utilisees dans le processus credit
- la production de tableaux de bord exploitables par les equipes

L'objectif principal est de fournir aux equipes credit, commerciales, recouvrement et direction des informations fiables, exploitables et actualisees pour reduire les risques financiers et ameliorer la performance du portefeuille de credit.

## Contexte metier

Dans une institution financiere ou une microfinance, l'analyse du credit joue un role central dans la maitrise des risques.

Chaque demande de credit doit etre evaluee a partir :

- des informations personnelles du client
- des informations financieres
- de l'historique de paiement
- des garanties disponibles
- du comportement de remboursement observe

L'analyste credit intervient pour :

- evaluer la solvabilite des clients
- analyser les risques lies a chaque demande
- formuler des recommandations d'octroi ou de refus
- suivre les credits approuves
- produire des rapports pour faciliter la prise de decision
- contribuer a la qualite et a la tracabilite des dossiers clients

## Objectifs du projet

Les objectifs couverts par l'application sont les suivants :

- centraliser les informations liees aux demandes de credit
- ameliorer l'analyse des dossiers clients
- suivre les credits accordes et les remboursements
- detecter rapidement les retards ou risques de defaut
- produire des tableaux de bord de suivi du portefeuille credit
- securiser et documenter les donnees liees aux clients
- faciliter la collaboration entre les equipes credit, recouvrement, relation client et direction

## Demarrage rapide

### Environnement utilise

Le projet est actuellement exploite avec Python depuis :

```text
C:\ProgramData\anaconda3
```

### Installation des dependances

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

## Source de donnees

L'application supporte aujourd'hui :

- un televersement local `.xlsx`, `.xls` ou `.csv`
- un fichier inclus dans `line_list/`

Exemple deja present dans le projet :

- `line_list/base_donnees_brute_credit.xlsx`

References de standardisation presentes :

- `data/Rename_columns.xlsx`
- `data/Replace_values.xlsx`

## Ce que fait l'application

L'interface combine plusieurs briques sur une meme page :

- chargement de la source et choix de feuille Excel
- standardisation des colonnes credit
- filtres par statut, agence, produit et periode
- synthese standard toujours visible en haut de page
- onglets detailles en bas
- export CSV et pack Excel

Variables derivees actuellement calculees :

- `capacite_remboursement`
- `taux_endettement`
- `mensualite_estimee`
- `niveau_risque_calcule`
- `mois_demande`

Variables metier integrees a la standardisation :

- `sexe`
- `age`

## Organisation actuelle de l'interface

### Synthese standard

La zone haute de la page conserve les indicateurs et graphiques standard. Elle inclut notamment :

- KPI de production, risque et remboursement
- `Distribution des statuts de dossier`
- `Evolution mensuelle des demandes`
- `Distribution des niveaux de risque`
- `Distribution par tranche d'age`
- `Repartition par sexe`
- `Pyramide age-sexe`

Une option laterale permet aussi :

- `Afficher annotations (valeurs)`
- definir un seuil minimal d'affichage des annotations

### Onglets detailles

L'application expose aujourd'hui :

- `Vue d'ensemble active`
- `Notions importantes`
- `Surveillance`
- `Portefeuille`
- `Risque`
- `Qualite`
- `Export`
- `Methodologie`

### Logique des onglets

- `Vue d'ensemble active` : confirme que la synthese haute reste visible pendant la navigation
- `Notions importantes` : explique le role de l'analyste credit, les notions essentielles, le processus credit, les KPI et les bonnes pratiques
- `Surveillance` : actions prioritaires, top agences, top produits, dossiers a suivre en priorite, apercu des dossiers
- `Portefeuille` : production par produit, agent, agence, lecture agence x statut
- `Risque` : distributions de risque, remboursement, classes de retard, watchlist
- `Qualite` : anomalies, valeurs manquantes et mapping source -> standard
- `Export` : export CSV et pack Excel
- `Methodologie` : conventions et logique de calcul

## Donnees attendues

Les analyses sont plus solides si la base contient au minimum :

- un identifiant client
- un identifiant dossier
- une date de demande
- un montant demande
- un statut de dossier

Colonnes tres utiles selon les modules :

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

Donnees souvent utiles au niveau metier :

- identite du client
- activite professionnelle ou commerciale
- garanties proposees
- commentaires des analystes
- historique des credits
- historique des paiements

## Conventions de mapping

Exemples de colonnes reconnues automatiquement :

- `ID Client`, `id_client`, `code_client` -> `client_id`
- `Numero Dossier`, `reference_dossier` -> `dossier_id`
- `Montant demande` -> `montant_demande`
- `Montant accorde` -> `montant_accorde`
- `Revenu mensuel` -> `revenu_mensuel`
- `Charges mensuelles` -> `charge_mensuelle`
- `Statut dossier` -> `statut_dossier`
- `Statut remboursement` -> `statut_remboursement`
- `Sexe` -> `sexe`
- `Age` -> `age`

Normalisations utiles deja appliquees :

- statuts dossier
- statuts remboursement
- valeurs de sexe comme `M`, `F`, `Masculin`, `Feminin`

## Regles metier principales

### Capacite de remboursement

```text
Capacite de remboursement = Revenu mensuel - Charges mensuelles
```

### Taux d'endettement

```text
Taux d'endettement = Charges mensuelles / Revenu mensuel
```

Interpretation usuelle :

```text
0 % a 30 %   -> risque faible
31 % a 50 %  -> risque moyen
plus de 50 % -> risque eleve
```

### Mensualite estimee

```text
Mensualite estimee = Montant accorde / Duree du credit en mois
```

### Niveau de risque calcule

Priorite actuelle :

1. niveau de risque deja present
2. score credit
3. taux d'endettement
4. retard en jours

Interpretation usuelle du score credit :

```text
80 a 100 -> risque faible
50 a 79  -> risque moyen
0 a 49   -> risque eleve
```

### Statuts du dossier a suivre

Les statuts metier les plus importants dans le projet sont :

- `Recu`
- `A completer`
- `En analyse`
- `Approuve`
- `Rejete`
- `Decaisse`
- `En remboursement`
- `En retard`
- `Cloture`

## Role et responsabilites principales

### Evaluation des demandes de credit

- analyser les informations personnelles et financieres du client
- verifier les revenus, charges, activites et garanties
- examiner l'historique de paiement
- controler la coherence des documents fournis
- identifier les informations manquantes ou incoherentes
- evaluer la capacite de remboursement

### Analyse des risques

- identifier les risques de non-remboursement
- analyser le niveau d'endettement
- utiliser les scores ou notations disponibles
- appliquer les politiques internes de credit
- proposer des mesures d'attenuation du risque

### Recommandation de decision

Les recommandations possibles peuvent etre :

- credit recommande
- credit recommande avec conditions
- credit a revoir
- credit non recommande

### Suivi du portefeuille credit

- suivre les echeances de remboursement
- identifier les retards de paiement
- surveiller les comptes a risque
- collaborer avec l'equipe de recouvrement
- produire des alertes sur les dossiers sensibles

### Reporting et documentation

- rapports d'analyse de credit
- tableaux de bord de suivi
- rapports sur les retards de paiement
- syntheses sur le portefeuille credit
- statistiques sur les demandes approuvees et rejetees
- rapports de performance par agence, produit ou periode
- documentation des decisions de credit

## Processus general d'analyse credit

1. Reception de la demande de credit.
2. Collecte des informations du client.
3. Verification des documents fournis.
4. Analyse financiere et comportementale.
5. Evaluation du risque.
6. Calcul de la capacite de remboursement.
7. Formulation d'une recommandation.
8. Validation par les responsables concernes.
9. Suivi du credit apres approbation.
10. Reporting et mise a jour du dossier client.

## Indicateurs de performance a suivre

### Indicateurs de demande

- nombre total de demandes
- nombre de demandes en attente
- nombre de demandes approuvees
- nombre de demandes rejetees
- montant total demande
- montant total accorde
- delai moyen de traitement

### Indicateurs de risque

- nombre de dossiers a risque faible
- nombre de dossiers a risque moyen
- nombre de dossiers a risque eleve
- taux de rejet
- taux d'endettement moyen
- score credit moyen
- nombre de dossiers avec donnees incompletes

### Indicateurs de remboursement

- montant total rembourse
- montant restant du
- nombre de clients a jour
- nombre de clients en retard
- nombre de jours moyens de retard
- portefeuille a risque

### Indicateurs par dimension

Les analyses doivent pouvoir etre relues par :

- agence
- agent de credit
- type de produit
- sexe du client
- tranche d'age
- activite economique
- periode
- niveau de risque
- statut du dossier

## Controles qualite integres

Le projet verifie notamment :

- clients sans identifiant
- dossiers sans identifiant
- dossiers dupliques
- dossiers sans statut
- montants negatifs
- montants accordes superieurs au montant demande
- donnees financieres manquantes
- capacite de remboursement negative
- retards negatifs
- dossiers approuves incoherents

## Exports disponibles

L'onglet `Export` permet de telecharger :

- les donnees standardisees en CSV
- un pack Excel contenant :
  - donnees standardisees
  - controles qualite
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

- application principale : [analyste_credit.py](./analyste_credit.py)
- chargement des fichiers : [credit_app/app_loader.py](./credit_app/app_loader.py)
- logique metier : [credit_app/domain.py](./credit_app/domain.py)
- styles et helpers UI : [credit_app/ui.py](./credit_app/ui.py)
- synthese standard : [credit_app/tabs/overview.py](./credit_app/tabs/overview.py)
- notions importantes : [credit_app/tabs/analyste_credit.py](./credit_app/tabs/analyste_credit.py)
- surveillance : [credit_app/tabs/surveillance.py](./credit_app/tabs/surveillance.py)
- portefeuille : [credit_app/tabs/portfolio.py](./credit_app/tabs/portfolio.py)
- risque : [credit_app/tabs/risk.py](./credit_app/tabs/risk.py)
- qualite : [credit_app/tabs/quality.py](./credit_app/tabs/quality.py)

## Tests et etat actuel

Les tests couvrent aujourd'hui les briques critiques :

- standardisation des colonnes
- variables derivees
- controles qualite
- synthese metier
- watchlist
- distributions sexe / age
- pyramide age-sexe
- chargement du fichier Excel inclus

Commande de verification utilisee :

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m unittest discover -s tests -v
```

Etat verifie pendant la mise a jour :

- application Streamlit demarre correctement
- tests `8/8` OK

## Confidentialite et securite

Les donnees manipulees dans ce projet sont sensibles et doivent etre traitees avec confidentialite.

Bonnes pratiques a respecter :

- limiter l'acces aux donnees aux personnes autorisees
- eviter le partage non securise des fichiers clients
- proteger les informations personnelles et financieres
- documenter les modifications importantes
- conserver une tracabilite des decisions
- respecter les procedures internes de securite

## Limites et point d'attention

- la qualite des analyses depend fortement des colonnes disponibles dans la source
- certaines regles de risque restent heuristiques et devront etre adaptees a votre institution
- le warning Streamlit suivant peut encore apparaitre selon l'installation locale Anaconda :

```text
Failed to scan component manifests: 'NoneType' object has no attribute 'lower'
```

Ce warning vient de la distribution Streamlit installee, pas de la logique metier du projet, et n'empeche pas le lancement de l'application.

## Prochaines evolutions possibles

- tranches d'age plus fines pour la pyramide age-sexe
- parametres de scoring credit plus metier
- chargement multi-fichiers et consolidation
- mapping interactif des colonnes non reconnues
- rapports PDF ou exports de synthese
- enrichissement du bloc de surveillance
