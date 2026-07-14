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
- analyser la solution M-PESA / Bisou Bisou Digital par chargement de fichiers Excel
- rapprocher chaque `Receipt No` G2 avec `ref_no` du Portal/Turbo, puis contrôler téléphone, devise, montant et date
- produire un rapport G2/DAT des entrées et sorties par devise, avec transactions classées, anomalies et exports Excel, PDF et Word

L’objectif est de fournir à la direction, au contrôle interne, à la conformité et aux responsables opérationnels une lecture exploitable des risques, anomalies, volumes, écarts de procédure et points de contrôle.

## Interface et graphiques

- navigation compacte par cycle, avec onglets défilants sur les petits écrans
- en-tête et synthèse contextualisés selon le cycle sélectionné
- palette graphique commune, légendes automatiques et libellés longs protégés
- barre d’outils Plotly au survol, export PNG et zoom à la molette désactivé
- états vides explicites lorsqu’une analyse ne dispose pas de données exploitables

La convention détaillée des graphiques est documentée dans `reports/frontend_chart_map.md`.

## Sécurité des connexions SQL

Les identifiants SQL ne doivent jamais être écrits dans le code, le README ou un fichier versionné. Deux modèles sans secret réel sont fournis : `.env.example` et `.streamlit/secrets.toml.example`.

- privilégier l'authentification Windows avec un compte de lecture seule lorsque l'environnement le permet
- conserver `encrypt = true` et `trust_server_certificate = false`
- placer les secrets Streamlit réels dans `.streamlit/secrets.toml`, ignoré par Git
- ne jamais afficher la chaîne de connexion complète dans les journaux ou dans l'interface
- utiliser `credit_app.security.SqlServerSettings` pour valider la configuration avant la future connexion à Perfect Vision

Les fichiers Python, Markdown, YAML, TOML et JSON sont normalisés en UTF-8 par `.editorconfig` et `.gitattributes`. Le dump historique `data/vision/BB_VISION_PRO.sql` reste en UTF-16 et est lu explicitement comme tel par le skill Perfect Vision.

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
Ordinateur principal :
C:\Users\Benjamin-mupanzi\AppData\Local\anaconda3

Autre ordinateur :
C:\ProgramData\anaconda3
```

Pour éviter de modifier toutes les commandes, définir d’abord la variable `$PYTHON` selon l’ordinateur utilisé :

```powershell
$PYTHON = 'C:\Users\Benjamin-mupanzi\AppData\Local\anaconda3\python.exe'

# Sur un autre ordinateur :
# $PYTHON = 'C:\ProgramData\anaconda3\python.exe'
```

### Installer les dépendances

```powershell
& $PYTHON -m pip install -r requirements.txt
```

### Lancer l’application

```powershell
& $PYTHON -m streamlit run .\controle_interne.py
```

### Lancer les tests

```powershell
& $PYTHON -m unittest discover -s tests -v
```

## Sources de données

L’application supporte :

- le téléversement local de fichiers `.xlsx`, `.xls` et `.csv`
- le téléversement de plusieurs fichiers Excel détaillés pour compilation
- la relecture de fichiers déjà déposés dans `line_list/`
- la compilation de plusieurs fichiers inclus présents dans `line_list/`
- le chargement indépendant des fichiers M-PESA / G2 / Turbo dans l’onglet `Solution M-PESA`

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
- `Solution M-PESA`

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
- `Solution M-PESA` : analyse les transactions M-PESA_G2 et les fichiers Turbo par téléversement, sans connexion directe à Perfect Vision.

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

## Solution M-PESA / G2 / Turbo

L’onglet `Solution M-PESA` est un module indépendant qui fonctionne par téléversement de fichiers Excel. Il analyse les entrées et sorties M-PESA G2, les écritures Portal/Turbo, les comptes d’épargne, les DAT, les crédits et les correspondances clients avec G2 et Perfect.

### Fichiers acceptés

Les fichiers sont chargés directement dans l’onglet :

- `Transactions M-PESA Portal/Turbo`
  Fichier interne des écritures M-PESA, utile quand il contient notamment `customer_id`, `msisdn1`, `account_type`, `ref_no`, `description`, `dr`, `cr`, `bal_before`, `bal_after`, `currency_code` et `created_at`. Plusieurs lignes comptables peuvent appartenir à une seule opération G2.
- `Transactions G2`
  Fichier des transactions G2, avec au minimum `Receipt No`, `Currency` et `Opposite Party`. `Completion Time`, `Transaction Status`, `Details`, `Reason Type` et `Balance` enrichissent l’analyse. Le montant peut être fourni dans `Transaction Amount` ou éclaté dans `Paid In` et `Withdrawn`.
- `Comptes d’épargne courante`
  Fichier Turbo des comptes courants, avec `customer_id`, `msisdn`, `currency_code`, `created_at`, `updated_at`.
- `Comptes DAT / épargne bloquée`
  Fichier Turbo des comptes DAT, avec `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `date_approved`, `maturity_date`.
- `Clients`
  Fichier client Turbo, avec `msisdn1` et `created_at`. Il sert à retrouver la date de création du compte à partir du numéro de téléphone.
- `Crédits`
  Fichier facultatif pour enrichir l’extrait client et les diagnostics.
- `Clients Perfect (export 122)`
  Fichier facultatif de contrôle téléphonique avec `Phone_Prefixe`, les identifiants et le nom du client Perfect.

### Règles de rapprochement

L’application construit une seule ligne analytique par `Receipt No`. Un reçu dupliqué est signalé et n’est jamais compté deux fois.

Le rapprochement principal suit ces règles :

- `Receipt No = ref_no` est la clé prioritaire entre G2 et le Portal/Turbo.
- Les différentes écritures comptables d’un même `ref_no` sont regroupées sans être comptées comme plusieurs opérations clients.
- Pour les entrées rapprochées, `FIXED SAVINGS` ou `Depot Bloque` classe l’opération en `DAT`; `NORMAL SAVINGS` ou `Epargne depot` en `Depot normal`; les comptes ou descriptions de prêt en `Remboursement prets`.
- Sans référence Portal retrouvée, `Details`, `Reason Type`, le sens et les règles G2 servent de repli.
- `Paid In` non nul classe le flux en `Entree`; `Withdrawn` non nul le classe en `Sortie`. Le signe de `Transaction Amount` est utilisé comme repli dans l’ancien format.
- Les sorties `BisouBisouB2C` sont classées en `Paiement client B2C` et les demandes de prêt en `Demande de credit`.
- `Super Transaction` est classé en `Operation interne Bisou`; une sortie n’est jamais utilisée comme candidate DAT.

Chaque référence Portal retrouvée fait ensuite l’objet de quatre contrôles indépendants : téléphone, devise, montant et date. Le résultat devient `Rapproche exact`, `Rapproche avec ecart` ou `Non rapproche`. Les reçus dupliqués, statuts non terminés, références absentes, écarts et opérations non classées restent visibles dans les anomalies.

Pour les informations client :

- `Opposite Party` fournit le téléphone et le nom G2; le numéro est normalisé au format `243...`.
- `Nom_client` enrichit les rapports Turbo lorsque G2 est disponible.
- `Compte créer` provient d’abord de `Clients.created_at`, puis de l’épargne courante et enfin du DAT.
- `Phone_Prefixe` rapproche les clients M-PESA avec Perfect. Un numéro partagé par plusieurs fiches est agrégé avant la jointure afin de ne pas multiplier les opérations.

### Restitutions disponibles

Le sous-onglet `G2 / DAT` produit :

- un filtre combiné sur la date et l'heure de `Completion Time`, puis sur le sens : entrées, sorties ou tous les flux
- une synthèse des entrées, sorties, volumes et soldes nets par devise
- une ventilation par type d'opération incluant les paiements B2C et demandes de crédit
- une synthèse verticale par devise : `Devise`, `Synthese sur le Portail BB Digital`, `Montant`
- un tableau unique `Transactions classees`, trié par devise puis date décroissante, avec les colonnes :
  `date`, `receipt_no`, `currency_code`, `details_rapport`, `opposite_party`, `duree`, `compte_cree`, `montant`, `montant_entree`, `montant_sortie`, `balance_numeric`
- un rapprochement G2/Portal et G2/DAT avec les contrôles téléphone, devise, montant et date
- un tableau d'anomalies conservant les références non rapprochées, doublons et écarts
- un export Excel du rapport journalier
- un rapport de fidélisation mensuelle M+1 et à 90 jours, séparé par devise et type d'opération
- un export PDF court pour la Direction generale, genere localement avec Microsoft Edge, Google Chrome ou Chromium
- un export Word modifiable avec la synthèse exécutive et, en annexe paysage, le même tableau `Transactions classees` que l'écran

Le sous-onglet `Perferct_client` produit :

- une ligne de synthèse par téléphone M-PESA observé dans Turbo ou G2
- les statuts `correspondance unique`, `plusieurs clients`, `non trouvé` et `téléphone inexploitable`
- le détail des opérations observées dans Turbo/G2, avec leur source et leur devise
- un export Excel séparant la synthèse client du détail des opérations

Exemple de synthèse attendue :

```text
Devise | Synthese sur le Portail BB Digital | Montant
CDF    | DAT                                | 1 995 950
CDF    | Depot normal                       | 1 089 302
CDF    | Remboursement prets                | 104 000
CDF    | Total CDF                          | 3 189 252
USD    | DAT                                | 3 610
USD    | Depot normal                       | 1 166
USD    | Remboursement prets                | 1
USD    | Total USD                          | 4 777
```

### Exports M-PESA

Les exports Excel du module peuvent contenir :

Dans `Extrait client`, la feuille `Extrait_MPESA` reprend les filtres appliqués aux mouvements. Les autres feuilles conservent la situation complète du client sélectionné afin de préserver le contexte de contrôle.

- `G2_DAT`
- `Rapport_G2_Pivot`
- `Rapport_G2_Comptages`
- `Rapport_G2_Vertical`
- `Rapport_G2_Synthese`
- `Rapport_G2_Detail`
- `Rapport_Journalier_Pivot`
- `Rapport_Journalier_Comptages`
- `Rapport_Journalier_Vertical`
- `Rapport_Journalier_Synthese`
- `Rapport_Journalier_Detail`
- `Anomalies_G2`
- `Retention_Mensuelle`
- `Retention_Operations`
- `Retention_Detail`
- `Retention_Definitions`
- `Perfect_Clients`
- `Perfect_Operations`
- `Diagnostics`

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

Le module `Solution M-PESA` dispose aussi de ses propres exports Excel pour les rapports G2/DAT et les diagnostics de chargement.

## Structure du projet

```text
controle_interne/
|-- controle_interne.py
|-- README.md
|-- requirements.txt
|-- credit_app/
|   |-- app_loader.py
|   |-- data_schema.py
|   |-- components/
|   |   |-- preparation.py
|   |-- core.py
|   |-- cycles.py
|   |-- control_references.py
|   |-- domain.py
|   |-- ui.py
|   |-- services/
|   |   |-- data_pipeline.py
|   |   |-- mpesa_analysis.py
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
|   |   |-- solution_mpesa.py
|   |   |-- table_filters.py
|-- data/
|   |-- Rename_columns.xlsx
|   |-- Replace_values.xlsx
|-- line_list/
|-- SOP/
|-- tests/
|   |-- test_credit_domain.py
|   |-- test_mpesa_analysis.py
```

## Fichiers principaux

- application principale : [controle_interne.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/controle_interne.py>)
- logique métier : [credit_app/domain.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/domain.py>)
- schémas, alias et validation des colonnes : [credit_app/data_schema.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/data_schema.py>)
- chargement sécurisé Excel/CSV : [credit_app/app_loader.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/app_loader.py>)
- pipeline central, détection des cycles et compatibilité des compilations : [credit_app/services/data_pipeline.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/services/data_pipeline.py>)
- composant de restitution de la préparation : [credit_app/components/preparation.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/components/preparation.py>)
- référentiels métiers : [credit_app/control_references.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/control_references.py>)
- cycles et presets : [credit_app/cycles.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/cycles.py>)
- composants UI : [credit_app/ui.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/ui.py>)
- synthèse standard : [credit_app/tabs/overview.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/overview.py>)
- audit et contrôle : [credit_app/tabs/audit_control.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/audit_control.py>)
- actions CRM : [credit_app/tabs/crm_clients.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/crm_clients.py>)
- surveillance : [credit_app/tabs/surveillance.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/surveillance.py>)
- portefeuille : [credit_app/tabs/portfolio.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/portfolio.py>)
- risque : [credit_app/tabs/risk.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/risk.py>)
- qualité : [credit_app/tabs/quality.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/quality.py>)
- méthode : [credit_app/tabs/methodology.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/methodology.py>)
- solution M-PESA : [credit_app/tabs/solution_mpesa.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/tabs/solution_mpesa.py>)
- analyses M-PESA : [credit_app/services/mpesa_analysis.py](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/credit_app/services/mpesa_analysis.py>)
- skill Solution M-PESA : [skills/solution-mpesa/SKILL.md](</c:/Users/Benjamin-mupanzi/Documents/GitHub/controle_interne/skills/solution-mpesa/SKILL.md>)

## Vérification

Les tests couvrent notamment :

- la standardisation des colonnes
- la normalisation des en-têtes, les alias et les colonnes dupliquées
- les erreurs de schéma avec le fichier, les champs manquants et les champs disponibles
- le chargement CSV multi-séparateurs et la sélection des feuilles Excel
- les fichiers vides, dates invalides, montants invalides et valeurs nulles
- l'absence d'identifiant d'opération sans création de donnée artificielle
- le nettoyage de certaines valeurs métier
- les variables dérivées
- les contrôles qualité
- les watchlists par cycle
- les distributions sexe / âge
- la pyramide âge-sexe
- le cycle épargne
- le cycle CRM
- les règles de contrôle renforcées pour l’épargne et le crédit
- la solution M-PESA, le rapprochement `Receipt No = ref_no`, la priorité de classification Portal et les rapports journaliers
- les reçus G2 dupliqués, références absentes et écarts de téléphone, devise, montant ou date
- l'ordre partagé des colonnes de `Transactions classees` dans Streamlit et Word
- les exports Excel, PDF et Word G2/DAT

Commande de vérification :

```powershell
& $PYTHON -m unittest discover -s tests -v
```

Vérification ciblée Solution M-PESA :

```powershell
& $PYTHON skills/solution-mpesa/scripts/inspect_mpesa_contracts.py
& $PYTHON -m pytest tests/test_mpesa_analysis.py -q
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
