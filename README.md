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
- régler avant le chargement, dans `Référence et stockage`, la standardisation des colonnes, les taux de référence et les options communes d’affichage
- définir le taux d’intérêt annuel DAT utilisé par Solution M-PESA pour les intérêts estimés
- activer l’option `Afficher annotations (valeurs)` et son seuil d’affichage
- définir le taux `CDF/USD` lorsque le cycle actif l’exige

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

## Solution M-PESA / G2 / Turbo / Perfect

L’onglet `Solution M-PESA` est un module indépendant qui fonctionne par téléversement de fichiers Excel. Il analyse les entrées et sorties M-PESA G2, les écritures Portal/Turbo, les comptes d’épargne, les DAT, les crédits et les correspondances clients avec G2 et Perfect.

Convention des libellés visibles : `[Turbo]` désigne une analyse issue de `Transactions M-PESA_Turbo`, `[G2]` une analyse issue de `Transactions M-PESA_G2`, et `[Turbo + G2]` une analyse consolidée utilisant réellement les deux sources. Pour les référentiels clients, l'application emploie les noms exacts `Clients_Turbo` et `Clients_Perfect`; un client déduit des opérations est présenté comme client transactionnel et n'est pas attribué à `Clients_Turbo`. Le nom global `Solution M-PESA` reste celui du module, mais il n'est pas utilisé seul comme source d'un indicateur.

### Fichiers acceptés

L'interface demande quatre sources Turbo principales, puis propose G2 et Perfect comme contrôles facultatifs :

- `Transactions M-PESA Portal/Turbo`
  Fichier interne des écritures M-PESA, utile quand il contient notamment `customer_id`, `msisdn1`, `account_type`, `ref_no`, `description`, `dr`, `cr`, `bal_before`, `bal_after`, `currency_code` et `created_at`. Plusieurs lignes comptables peuvent appartenir à une seule opération G2.
- `Savings Account`
  Source maître Turbo des comptes d’épargne avec notamment `savings_id`, `customer_id`, `msisdn1`, `product_name`, `product_description`, `balance`, `currency_code`, `status`, `date_approved`, `maturity_date`, `created_at` et `updated_at`. La solution en extrait les comptes courants (`Open Savings` / `Current account`) et tous les DAT actifs ou historiques (`Fixed Account`). Le même emplacement multiple accepte, à défaut, les deux fichiers résumés Current et Fixed chargés ensemble.
- `Loans Account`
  Fichier Turbo des crédits, avec au minimum `loan_id` et `customer_id`; les colonnes d'encours, d'échéance et de remboursement alimentent les analyses de crédit.
- `Customers`
  Fichier client Turbo avec `msisdn1` et `created_at`. Il sert à retrouver la date de création du compte à partir du numéro de téléphone.
- `Transactions G2` (facultatif)
  Un ou plusieurs fichiers de transactions G2, avec au minimum `Receipt No`, `Currency` et `Opposite Party`. Les relevés d’entrées et de sorties peuvent être téléversés ensemble; ils sont unifiés en conservant le nom du fichier source, puis dédupliqués par `Receipt No`. `Completion Time`, `Transaction Status`, `Details`, `Reason Type` et `Balance` enrichissent l’analyse. Le montant peut être fourni dans `Transaction Amount` ou éclaté dans `Paid In` et `Withdrawn`.
- `Clients_Perfect (export 122)`
  Fichier facultatif de contrôle téléphonique avec `Phone_Prefixe`, les identifiants et le nom du client Perfect.

Les deux synthèses `Customers with Current Savings Account` et `Customers with Fixed Savings Account` n'ont plus d'emplacements séparés. Elles peuvent être sélectionnées ensemble dans `Savings Account [Turbo]` comme solution de compatibilité. Ce mode couvre seulement les comptes à solde positif et ne reconstitue ni les comptes à solde nul ni l'historique exhaustif. Si le fichier complet et les synthèses sont chargés ensemble, le fichier complet est prioritaire et les synthèses sont ignorées pour éviter tout doublon.

Tous les emplacements de téléversement M-PESA acceptent plusieurs fichiers. Le contrôle de chargement affiche le nombre et le nom des fichiers sources, puis les chevauchements sont éliminés selon la nature de la source :

- Transactions Turbo : `id`, ou à défaut la combinaison référence, compte, client, devise, `dr`, `cr` et date;
- `Savings Account` : `savings_id`, puis client, devise, type de compte, produit et dates propres au type de compte, en conservant la version la plus récente; la source complète prime sur les vues Current/Fixed;
- crédits : `loan_id`, avec priorité à la version la plus récente;
- `Clients_Turbo` : `customer_id`, ou téléphone et date de création lorsque l'identifiant n'est pas fourni;
- `Clients_Perfect` : `id_client`, puis les identifiants de repli documentés.

La logique des transactions Turbo reste comptable et distincte de G2 : sur la ligne `MPESA ACCOUNT`, `dr` représente une sortie M-PESA et `cr` une entrée M-PESA. Les lignes techniques partageant le même `ref_no` sont regroupées pour le rapprochement G2/DAT; elles ne sont pas interprétées avec les règles G2 `Paid In`/`Withdrawn`.

Le fichier `Transactions M-PESA_G2` est facultatif pour ouvrir le sous-onglet `G2 / DAT`. En son absence, le mode `[Turbo]` reconstruit uniquement les opérations démontrables dans `Transactions M-PESA_Turbo` : dépôt normal, DAT et remboursement regroupés par `ref_no`, puis retraits `Retrait Vers M-Pesa` regroupés par `reference_id + created_at`. `created_at` fournit alors la date et l'heure. Le mode ne fabrique ni nom G2, ni statut G2, ni solde G2, ni date d'initiation/finalisation G2; les contrôles croisés G2/Turbo sont affichés comme `Non applicable - Turbo seul`. Lorsqu'il est chargé, G2 reste la source de son propre relevé de contrôle, mais Portal Turbo demeure la source financière principale de la Solution M_PESA.

Les relevés G2 peuvent commencer directement par `Receipt No., Completion Time, Initiation Time, Details, Transaction Status, Currency, Paid In, Withdrawn, Balance, Reason Type, Opposite Party, Linked Transaction ID`. Les exports organisation bruts contenant cinq lignes descriptives avant ces en-têtes restent acceptés : la vraie ligne d'en-tête est détectée automatiquement par fichier avant l'unification des comptes 1441 et 15558.

Avec les fichiers du 17 juillet 2026, `Savings Account` contient 80 791 lignes : 77 084 comptes courants et 3 707 DAT. Les 1 214 DAT à solde positif correspondent exactement aux 1 214 lignes de l'export DAT résumé; les 2 493 autres DAT, à solde nul, restent conservés comme historique au lieu d'être perdus.

### Règles de rapprochement

L’application construit une seule ligne analytique par `Receipt No`. Un reçu dupliqué est signalé et n’est jamais compté deux fois.

Le rapprochement principal suit ces règles :

- `Receipt No = ref_no` est la clé prioritaire entre G2 et le Portal/Turbo.
- Les différentes écritures comptables d’un même `ref_no` sont regroupées sans être comptées comme plusieurs opérations clients.
- Pour une sortie G2 `BisouBisouB2C` dont le reçu est absent de `ref_no`, le rapprochement secondaire est autorisé uniquement avec une opération Turbo `Retrait Vers M-Pesa` ayant le même téléphone, la même devise, le même montant et un écart horaire maximal de 120 minutes. L'opération Turbo est distinguée par `reference_id + created_at`, car `reference_id` seul identifie le compte d'épargne et peut être réutilisé.
- Pour les entrées rapprochées, `FIXED SAVINGS` ou `Depot Bloque` classe l’opération en `DAT`; `NORMAL SAVINGS` ou `Epargne depot` en `Depot normal`; les comptes ou descriptions de prêt en `Remboursement prets`.
- Sans référence Portal retrouvée, `Details`, `Reason Type`, le sens et les règles G2 servent de repli.
- `Paid In` non nul classe le flux en `Entree`; `Withdrawn` non nul le classe en `Sortie`. Le signe de `Transaction Amount` est utilisé comme repli dans l’ancien format.
- Les sorties `BisouBisouB2C` sont classées en `Paiement client B2C` et les demandes de prêt en `Demande de credit`.
- Une sortie B2C rapprochée à `Retrait Vers M-Pesa` reçoit aussi le libellé de contrôle `Retrait epargne vers M-PESA` sans modifier sa classification G2.
- `Super Transaction` est classé en `Operation interne Bisou`; son rapprochement client est `Non applicable - operation interne`, et une sortie n’est jamais utilisée comme candidate DAT.

Chaque opération Turbo retrouvée fait ensuite l’objet de quatre contrôles indépendants : téléphone, devise, montant et date. La date de création compare d'abord `Initiation Time` G2 à `created_at` Turbo; `Completion Time` représente la finalisation G2 et permet de calculer le délai de traitement. Si `Initiation Time` manque, `Completion Time` sert de repli explicite. Une différence absolue supérieure à 60 minutes devient un `Ecart de date`, même le même jour, et apparaît dans `Afficher les anomalies [G2]`. Un passage de date inférieur ou égal à 60 minutes reste conforme et les deux dates sont conservées dans `Observation`. La fenêtre de 120 minutes reste uniquement utilisée pour rechercher une sortie B2C candidate. Le résultat devient `Rapproche exact`, `Rapproche avec ecart`, `Non rapproche` ou `Non applicable - operation interne`. Les reçus dupliqués, statuts non terminés, références absentes, écarts et opérations non classées restent visibles dans les anomalies.

Les statuts G2 sont normalisés en `Completed`, `Declined`, `Cancelled`, `Expired`, `Pending`, `Non renseigne` ou `Autre`. Seules les transactions explicitement `Completed` alimentent les montants, tendances, fidélisation, contrôles DAT et analyses Perfect. Les autres statuts restent visibles dans la répartition des statuts, le détail et les anomalies. Un ancien export entièrement dépourvu de statut reste compatible; dans un fichier moderne où au moins un statut est renseigné, une ligne sans statut est réservée au contrôle.

Pour les informations client :

- `Opposite Party` fournit le téléphone et le nom G2; le numéro est normalisé au format `243...`.
- `Nom_client` enrichit les rapports Turbo lorsque G2 est disponible.
- `Extrait client` fonctionne avec Transactions M-PESA_Turbo seul : recherche par `customer_id` ou téléphone, mouvements, synthèse, filtres et exports restent disponibles. Portal Turbo est la source financière principale. G2 est facultatif et sert uniquement à compléter le nom et à afficher un contrôle des opérations liées au client sélectionné; ses montants, dates et soldes ne remplacent jamais Turbo.
- Dans l'extrait écran et Word, la colonne `Description` reprend les libellés `description` du portail Turbo pour toutes les écritures de l'opération. Le téléphone et le nom G2 peuvent être ajoutés après ce libellé, mais `Details` et `Reason Type` G2 ne remplacent jamais la description Turbo.
- Dans l'extrait officiel, les flux sont présentés du point de vue de Bisou Bisou : les dépôts et remboursements sont des entrées sur le compte `1441`; les décaissements et sorties sont affectés au compte `15558`. La colonne `Compte` du tableau conserve cette affectation ligne par ligne.
- L'en-tête Word affiche `Devise` et non `Compte`. Trois exports sont disponibles lorsque les deux devises existent : `CDF`, `USD` et `ALL`. Le document `ALL` conserve une synthèse et un cumul distincts pour chaque devise. Le Word officiel ne porte aucun suffixe `[Turbo]`; sans solde d'ouverture, la colonne reste nommée `Cumul net` sans reprendre l'ancien avertissement.
- Le filtre des types d'opération sélectionne par défaut les dépôts, les retraits `Retrait Vers M-Pesa`, les décaissements de crédit et les remboursements de crédit. Un retrait sans `ref_no` est compté une seule fois par `customer_id + devise + created_at + reference_id`, malgré ses deux écritures miroir Turbo.
- Le Word Turbo seul est nommé `extrait_compte_<customer_id>_<telephone>_<devise>_<debut>_<fin>.docx`. Lorsque G2 est chargé, `Nom_client` est inséré entre l'identifiant et le téléphone; G2 n'est jamais utilisé pour recalculer les entrées ou les sorties.
- Dans le titre du Word, le nom client est affiché seulement lorsqu'il est disponible. Sans nom, le titre devient directement `Extrait de compte - <telephone> - <devise>` et n'affiche pas `NON DISPONIBLE`.
- L'Extrait client construit aussi un parcours financier au grain `customer_id + devise + created_at + ref_no`. Quand `ref_no` manque, l'horodatage et les comptes Turbo réunissent les écritures d'un décaissement, d'un remboursement ou d'un transfert interne sans les compter plusieurs fois.
- Le bloc `Remboursements observés [Turbo]` retient uniquement les événements de remboursement présents dans Transactions M-PESA_Turbo et correspondant aux filtres actifs. Il restitue la date, la référence, la devise, le montant payé, le principal remboursé, les intérêts, les pénalités et le mode observé. Les décaissements, la dette créée et les positions de crédit ne sont plus affichés dans l'Extrait client, ses Word, PDF ou son classeur client.
- Les mouvements `Retrait Compte Bloque` sans ligne `MPESA ACCOUNT` sont conservés dans `Mouvements internes épargne / DAT [Turbo]`; ils ne sont pas ajoutés aux entrées 1441 ou aux sorties 15558 de l'extrait officiel.
- Le bloc `DAT en cours et échéances à venir [Turbo]` utilise les comptes `FIXED SAVINGS` à solde positif dans `Savings Account`. Il affiche le DAT, la durée, la souscription, l'échéance, les jours restants, la devise, le capital bloqué, le taux annuel, l'intérêt estimé, le capital avec intérêt estimé et la situation `En cours`, `Échéance proche`, `Échéance aujourd'hui` ou `Échu à rembourser`.
- La situation DAT est datée depuis l'instantané `Savings Account`, puis à défaut depuis la dernière transaction Turbo du client; G2 n'intervient jamais dans ce calcul. Le taux DAT par défaut reste 11 %. L'intérêt est une estimation de préparation et non une écriture comptable. Les intérêts des DAT déjà dénoués ne sont plus affichés dans l'Extrait client.
- Les remboursements utilisent les filtres de devise, période, référence et type d'opération de l'extrait. Les DAT en cours sont un contexte de position : ils sont filtrés par client et devise, mais restent indépendants de la période transactionnelle. Dans le Word client, `Détail des transactions` reste présent et le pied de page indique `Solution Bisou Bisou Digital`.
- `Compte créer` provient d’abord de `Clients.created_at`, puis de l’épargne courante et enfin du DAT.
- `Phone_Prefixe` rapproche les clients transactionnels Turbo/G2 avec `Clients_Perfect`. La présence est contrôlée séparément dans G2, Turbo et `Clients_Perfect` afin de produire l'intersection stricte des trois systèmes. Un numéro partagé par plusieurs fiches est agrégé avant la jointure afin de ne pas multiplier les opérations.

Au premier téléversement, tous les sous-onglets M-PESA sont construits afin de former un tableau de bord immédiatement disponible. Une modification des fichiers déclenche une reconstruction complète volontaire; les interactions suivantes restent locales au sous-onglet grâce aux fragments Streamlit. La lecture Excel rapide, la préparation, le rapprochement G2, l'extrait client et les analyses lourdes sont mis en cache avec une empreinte compacte du contenu des fichiers, de la période et du client. La solution ne bascule pas vers un calcul limité au seul onglet sélectionné.

La norme visuelle de navigation s'applique aussi aux sous-sous-onglets de `Finance Turbo`, `Perfect_client` et `G2 / DAT` : barre sobre avec espacement régulier, onglet actif bleu arrondi et souligné en rouge, survol discret, focus clavier visible et défilement horizontal sur petit écran. Chaque barre imbriquée utilise un conteneur Streamlit identifié afin que son style reste indépendant de la barre principale.

Dans tous les sous-onglets de Solution M-PESA, un tableau non vide d'anomalies, d'alertes, d'écarts ou d'éléments à vérifier est précédé d'une bannière rouge. Le tableau reste volontairement sans coloration afin de préserver sa lisibilité; l'absence de signal est confirmée en vert.

Dans `Contrôle des données`, le tableau `Anomalies Transactions [Turbo]` affiche en première position une colonne épinglée `Raison de l'anomalie`. Elle précise chaque règle déclenchée et réunit les motifs lorsqu'une même écriture cumule plusieurs anomalies. Les filtres `statut` et `controle` s'appliquent à la synthèse et à cette liste; lorsque `controle` est filtré, seuls les motifs sélectionnés restent affichés. La valeur de chaque contrôle correspond au nombre de lignes Turbo détaillables. Pour les écritures répétées, le nombre de groupes reste indiqué dans la colonne `detail`.

### Restitutions disponibles

Le sous-onglet principal `Finance Turbo` réunit le pilotage financier et la comptabilité observée avec une période et un filtre de devises communs. Ses six volets sont `Vue direction`, `Flux et activité`, `Crédit, épargne et DAT`, `Balances et journaux`, `Risques et contrôles` et `Export`. Le volet `Balances et journaux` construit notamment les analyses financières observables directement dans Transactions M-PESA_Turbo :

- une synthèse séparée par devise avec écritures, clients, opérations, débits, crédits et taux de symétrie
- une balance par client enrichie du nom G2 sans reprendre les montants G2
- une balance auxiliaire des positions `NORMAL SAVINGS`, `FIXED SAVINGS` et `PRINCIPLE`
- une balance des mouvements par type de compte Turbo
- un journal des opérations regroupées par `ref_no`, puis par client, devise et horodatage lorsque la référence manque
- le journal brut des écritures, les opérations à vérifier et le contrôle de variation `bal_before` / `bal_after`
- les flux du compte `MPESA ACCOUNT`, avec le sens Bisou Bisou documenté
- les intérêts, pénalités, parts Bisou et parts Voda présentés séparément pour éviter le double comptage
- les positions des instantanés Current Savings, Fixed Savings et Loans, affichées à part de la balance journalière
- la couverture des noms G2 et du rapprochement direct `Receipt No = ref_no`

Cette restitution est une balance observée des sous-registres Turbo. Sans plan comptable complet et soldes d'ouverture officiels, elle n'est pas présentée comme une balance générale certifiée, un bilan ou un compte de résultat officiel. CDF et USD ne sont jamais additionnés.

#### Cas de validation comptable du 16 juillet 2026

Le test de référence utilise les exports produits le 17 juillet pour la journée clôturée du 16 juillet 2026. Transactions M-PESA_Turbo reste l'unique source des mouvements; G2 enrichit les noms et vérifie les références. Le périmètre contient 549 écritures Turbo, 75 clients et 135 opérations regroupées.

| Devise | Écritures | Clients | Opérations | Débits | Crédits | Symétriques | À revoir | Variations de solde conformes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CDF | 231 | 28 | 48 | 2 359 892,00 | 2 269 330,00 | 39 / 48 (81,25 %) | 9 | 98,2684 % |
| USD | 318 | 50 | 87 | 9 318,68 | 9 258,01 | 67 / 87 (77,0115 %) | 20 | 96,2264 % |

Avec les relevés G2 d'entrées 1441 et de sorties 15558, le contrôle comptable direct `Receipt No = ref_no` retrouve 35 références CDF sur 49 transactions G2 terminées (71,4286 %) et 50 références USD sur 83 (60,2410 %). Les sorties B2C peuvent en plus être rapprochées par téléphone, devise, montant et heure; elles ne sont pas comptées comme rapprochements directs. La couverture des noms clients Turbo est de 100 % en CDF et 98 % en USD. Les 29 opérations non symétriques et les 16 lignes dont la variation de solde est à revoir sont des signaux de contrôle : Turbo peut décrire plusieurs couches comptables d'une même opération, donc ces cas ne sont pas automatiquement des erreurs.

Les instantanés de référence, distincts de la balance journalière, donnent 89 157 002,34 CDF de dépôts face à 77 461 721,46 CDF de crédits (86,8824 %) et 203 049,44 USD de dépôts face à 30 555,78 USD de crédits (15,0484 %). Les intérêts, pénalités, parts Bisou et parts Voda restent affichés séparément afin d'éviter un double comptage.

Pour les DAT dénoués le 16 juillet 2026, `Savings Account` porte 9 intérêts client positifs : 4 en CDF pour 918,27 CDF et 5 en USD pour 33,87 USD. Les intérêts Vodacom correspondants valent respectivement 250,44 CDF et 9,24 USD. Aucune de ces neuf lignes ne possède une écriture de dénouement détaillée dans l'export Transactions Turbo; elles sont donc signalées comme constatées dans `Savings Account`, sans incidence sur le solde M-PESA.

Le sous-onglet `DAT` utilise `Savings Account` pour afficher immédiatement les comptes à solde positif déjà échus et ceux arrivant à terme dans les 30 prochains jours. L'horizon est réglable de 1 à 90 jours. La liste conserve le compte `savings_id`, le client, le téléphone, le produit, les dates, les jours restants, le capital, l'intérêt estimé et le capital plus intérêt. Le taux annuel DAT Bisou Bisou vaut 11 % par défaut dans la barre latérale; l'intérêt simple est estimé entre `date_approved` et `maturity_date`. Tous les montants restent séparés par devise et constituent une préparation au remboursement, pas une écriture comptable officielle.

Le sous-onglet `Detail des credits` rapproche `Loans Account` avec les comptes courants de `Savings Account`. Il utilise d'abord `savings_account_id` contre `id` ou `savings_id`; lorsque cet identifiant est vide, il déduit `savings_id` uniquement si `customer_id + currency_code` identifie un compte courant unique. La vue consolidée présente, au grain client x devise, les prêts, remboursements, encours, principal, intérêts, pénalités, épargne courante et DAT positifs. Les absences, ambiguïtés et incohérences de téléphone, client ou devise sont conservées dans un tableau de contrôle et un export Excel à quatre feuilles. Les positions sont juxtaposées sans compensation comptable et l'épargne n'est pas assimilée à une garantie.

Sur les fichiers du 17 juillet 2026, les 2 213 lignes de `Loans Account` ont toutes `savings_account_id` vide. Le repli client x devise rapproche 1 740 crédits CDF sur 1 740 et 472 crédits USD sur 473; un crédit USD sans compte courant correspondant reste à revoir. L'épargne courante et les DAT sont comptés une seule fois par client et devise, même lorsqu'un client possède plusieurs prêts.

Les volets de pilotage de `Finance Turbo` centralisent sur une période les analyses de microfinance et de contrôle démontrables depuis le portail Turbo :

- flux d'entrées et sorties, dépôts d'épargne, dépôts DAT, retraits, remboursements et décaissements, avec évolution par jour, semaine ou mois;
- remboursements observés avec principal, intérêts, pénalités, mode et contrôle des écritures miroir;
- nouveaux crédits : rapprochement global par devise entre les décaissements Transactions Turbo et les comptes créés dans Loans Account;
- encours, retards, PAR simplifié 1/7/30 jours, PAR par tranche et concentration du portefeuille;
- activité d'épargne par client, dépôts fréquents, tranches de dépôts, DAT proches de l'échéance, DAT sans crédit actif et vue crédit–épargne sans compensation;
- concentration des transactions, transactions importantes, fractionnement potentiel, activité inhabituelle comparée aux 90 jours précédents, mouvements sur comptes inactifs et qualité des téléphones Clients_Turbo.

Turbo constitue l'unique source des montants, soldes, crédits, DAT, remboursements et alertes du cockpit. G2 peut enrichir un nom et fournir une preuve de rapprochement dans les autres sous-onglets, mais n'intervient dans aucun calcul financier du pilotage. Les montants CDF et USD sont toujours séparés.

La période utilise deux bornes inclusives. La dernière journée complète est proposée par défaut si l'extraction la plus récente s'arrête avant 18 h. Le PAR reste vide si l'encours ou l'échéance nécessaire n'est pas fiable; faute de plan d'amortissement détaillé, il est explicitement simplifié depuis `due_date`. Une alerte indique un dossier à revoir et ne constitue pas une preuve de fraude.

Le moteur adapte les contrôles Perfect Vision prioritaires qui sont réellement transposables à Turbo : remboursement des crédits, évolution dépôts/crédits, nouveaux crédits, encours, concentration, PAR par tranche, dépôts fréquents, comptes inactifs et couverture crédit–épargne. Les contrôles exigeant un tableau d'amortissement, des garanties, des provisions ou un plan comptable complet ne sont pas présentés comme calculés.

Les 96 188 lignes de l'export réel sont consolidées une seule fois en événements métier, d'abord par `ref_no`, puis par `customer_id + devise + created_at` lorsque la référence manque. Le journal consolidé, le rapport de pilotage, la comptabilité observée et le rapprochement crédit–épargne sont mis en cache séparément; les six volets de `Finance Turbo` sont tous construits au chargement et un changement de volet ne relance pas l'analyse.

Test de référence du 16 juillet 2026 : 135 événements consolidés, dont 48 CDF et 87 USD. Les remboursements observés valent 284 910 CDF et 194,54 USD; les nouveaux crédits décaissés valent 122 200 CDF et 99 USD. Les décaissements se rapprochent exactement des comptes de crédit créés dans la période pour les deux devises. Ces résultats proviennent uniquement de Turbo.

Le sous-onglet `G2 / DAT` produit, depuis G2 lorsqu'il est chargé ou depuis le mode de repli Turbo documenté ci-dessus :

- une analyse des transactions terminees par date et sur les 24 heures, avec separation par devise et par sens; les jours et heures sans activite sont affiches a zero
- les indicateurs de volume total, moyenne quotidienne, date la plus active, jour de semaine le plus actif (`Lundi` a `Dimanche`) et heure la plus active sur le perimetre filtre
- un filtre combiné sur la date et l'heure de `Completion Time` en mode G2 ou `created_at` en mode Turbo seul, puis sur le sens : entrées, sorties ou tous les flux; la dernière journée complète est proposée et les heures `00:00:00` / `23:59:59` la conservent en entier
- une synthèse des entrées, sorties, volumes et soldes nets par devise
- une répartition des statuts G2 par devise et fichier source lorsque G2 est disponible; en mode Turbo seul, les opérations sont explicitement libellées `Comptabilisee Turbo` sans inférer un statut G2
- une ventilation par type d'opération incluant les paiements B2C et demandes de crédit
- une synthèse verticale par devise : `Devise`, `Synthese sur le Portail BB Digital`, `Montant`
- un tableau unique `Transactions`, trié par devise puis date décroissante, avec les colonnes :
  `date`, `receipt_no`, `currency_code`, `details_rapport`, `opposite_party`, `duree`, `compte_cree`, `montant`, `montant_entree`, `montant_sortie`, `balance_numeric`
- un rapprochement G2/Portal et G2/DAT avec les contrôles téléphone, devise, montant et date lorsque G2 est chargé; en mode Turbo seul, un contrôle interne Turbo/DAT sans faux rapprochement G2
- un tableau d'anomalies conservant les références non rapprochées, doublons et écarts
- un export Excel du rapport journalier
- un rapport de fidélisation mensuelle M+1 et à 90 jours, séparé par devise et type d'opération
- un export Word modifiable avec `Synthese des flux G2 par devise` ou `Synthese des flux Turbo par devise` selon la source effective, la synthèse exécutive et, en annexe paysage, le même tableau `Transactions` que l'écran
- dans ce Word, `Activite`, les flux, les principales opérations, la fréquence temporelle, la fidélisation et l'annexe sont recalculés sur le filtre actif de date, heure et sens; seules les transactions `Completed` alimentent ces analyses, tandis que les autres statuts restent comptés comme lignes de contrôle

Le sous-onglet `Perfect_client` produit trois populations inclusives au grain d'un téléphone normalisé :

- `Clients_Perfect x G2` : fiches `Clients_Perfect` dont `Phone_Prefixe` est observé dans G2
- `Clients_Perfect x Turbo` : fiches `Clients_Perfect` dont `Phone_Prefixe` est observé dans au moins une source Turbo
- `Clients_Perfect x Turbo x G2` : intersection stricte `Clients_Perfect`–Turbo–G2
- une ligne de synthèse par téléphone, avec toutes les identités Perfect partageant éventuellement ce numéro
- les indicateurs `présent dans Turbo`, `présent dans G2`, `présent dans Perfect` et `présent dans les 3 systèmes`
- une présence Turbo confirmée dès que le téléphone est observé dans une source Turbo, une présence G2 confirmée depuis `Opposite Party`, et une présence Perfect confirmée par `Phone_Prefixe`
- les statuts `correspondance unique`, `plusieurs clients`, `non trouvé` et `téléphone inexploitable`
- le détail des opérations observées dans Turbo/G2, avec leur source et leur devise
- un export Excel séparant les clients des trois systèmes, la population générale et le détail des opérations

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

Les exports Excel sont volontairement limités aux feuilles importantes pour réduire le temps de génération.

Dans `Extrait client`, le classeur contient les feuilles utiles parmi `Synthese`, `Extrait_Turbo`, `Parcours_Turbo`, `DAT_En_Cours`, `Remboursements_Turbo`, `Comportement_Turbo`, `Mouvements_Internes`, `Controles_Client_Turbo`, `DAT_Final`, `G2_DAT` et `Diagnostics`. Il n'ajoute plus `Credit_Client_Turbo`, `Positions_Turbo`, `Interets_DAT_Echus` ni `Credits`. `G2_DAT` est facultative et limitée au client sélectionné.

Dans `G2 / DAT`, le classeur contient `Rapport_Journalier_Comptages`, `Rapport_Journalier_Synthese`, `Statuts_G2`, `Rapport_Journalier_Detail`, `Anomalies_G2`, `G2_DAT`, `Retention_Mensuelle` et `Retention_Detail`.

Le classeur G2/DAT ajoute `Transactions_Jour`, `Transactions_Jour_Semaine`, `Transactions_Heure` et `Transactions_Jour_Heure` pour reutiliser les volumes temporels hors de l'application.

Dans `Perfect_client`, le classeur contient `Clients_Perfect_G2`, `Clients_Perfect_Turbo` et `Clients_Perfect_Turbo_G2`. L'export des forts DAT conserve uniquement `Forts_DAT` et `Portefeuille_DAT`.

Dans le volet `Export` de `Finance Turbo`, l'Excel de pilotage est généré seulement sur demande. Il contient les feuilles utiles parmi `Flux_Synthese_Turbo`, `Flux_Evolution_Turbo`, `Remboursements_Synthese`, `Remboursements_Pilotage`, `Nouveaux_Credits_Synthese`, `Nouveaux_Credits_Turbo`, `Pilotage_Credit_Turbo`, `Credits_Risque_Turbo`, `PAR_Tranches_Turbo`, `Concentration_Credit`, `Activite_Epargne_Clients`, `Depots_Frequents_Hebdo`, `Tranches_Depots_Turbo`, `Concentration_Transactions`, `Alertes_Turbo`, `Mouvements_Comptes_Inactifs`, `DAT_Sans_Credit_Actif`, `Credit_Epargne_Disponible`, `Echeances_DAT_Turbo`, `Qualite_Clients_Turbo`, `Definitions_Pilotage` et `Sources_Pilotage`. Aucune feuille G2 ne fournit de montant.

Dans le même volet `Export`, l'Excel comptable reste un téléchargement distinct et contient exactement `Compta_Synthese_Turbo`, `Balance_Clients_Turbo`, `Positions_Clients_Turbo`, `Balance_Comptes_Turbo`, `Journal_Operations_Turbo`, `Journal_Ecritures_Turbo`, `Controles_Operations_Turbo`, `Controles_Soldes_Turbo`, `Flux_MPESA_Turbo`, `Produits_Financiers_Turbo`, `Positions_Portefeuille_Turbo` et `Controle_G2_Turbo`. Les onze premières feuilles restent exclusivement Turbo; la dernière trace le contrôle secondaire G2.

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
- l'ordre partagé des colonnes de `Transactions` dans Streamlit et Word
- les exports Excel ciblés et Word G2/DAT

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
