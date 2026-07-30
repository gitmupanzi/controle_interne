# BB_VISION_REPORTING

Kit SQL de demarrage pour construire une couche de reporting durable au-dessus de Perfect Vision.

## Objectif

Ce dossier prepare une base `BB_VISION_REPORTING` separee de la base operationnelle `BB_VISION_PRO`.

Le but est de faire lire Power BI sur des tables propres, stables et indexees, au lieu de lancer directement les longues requetes du catalogue `data/vision/requetes.sql` contre la base Perfect Vision.

### Data Mart

Un data mart (magasin de donnees thematique ou sous-ensemble analytique.) est une petite base de donnees organisee pour l'analyse d'un domaine precis.

Dans ce projet, `BB_VISION_REPORTING` est le data mart de controle interne. Il ne remplace pas Perfect Vision.
Il sert plutot a preparer des donnees propres pour les analyses Power BI, par exemple :

- credit ;
- epargne ;
- clients ;
- conformite ;
- surveillance financiere.

Image simple : Perfect Vision est la base de travail quotidienne, tandis que le data mart est la vitrine propre
destinee aux analyses et tableaux de bord.

### ETL

Un ETL (`Extract, Transform, Load` : extraire, transformer, charger) est le processus qui permet de prendre les donnees dans une source, de les nettoyer ou restructurer, puis de les charger dans une base de reporting.

Dans ce projet :

1. `Extract` / extraire : lire les donnees dans `BB_VISION_PRO_TEST` ou plus tard dans `BB_VISION_PRO` ;
2. `Transform` / transformer : appliquer les regles metier des requetes autonomes, par exemple la requete 156 ;
3. `Load` / charger : inserer le resultat propre dans les tables `rpt.*`.

Image simple : l'ETL est l'atelier qui prend les donnees brutes de Perfect Vision et les transforme en donnees
pretes pour Power BI.

### Fact Table

Une table de faits (`Fact Table`) contient les donnees mesurables ou observables. Elle porte souvent des montants, des nombres,
des soldes, des volumes ou des indicateurs.

Dans ce projet, les tables qui commencent par `f_` sont des tables de faits.

Exemples :

- `rpt.f_conformite` : faits et signaux du cycle conformite ;
- `rpt.f_clients` : indicateurs par client et par devise ;
- `rpt.f_credit_portefeuille` : montants et volumes du portefeuille credit ;
- `rpt.f_epargne_soldes` : soldes et indicateurs epargne.

### Dimension Table

Une table de dimension (`Dimension Table`) sert a decrire les faits. Elle permet de filtrer, regrouper ou presenter les donnees.

Dans ce projet, les tables qui commencent par `d_` sont des dimensions.

Exemples :

- `rpt.d_date` : calendrier ;
- `rpt.d_devise` : USD, CDF, etc. ;
- `rpt.d_agence` : agences ou points de service ;
- `rpt.d_client` : informations descriptives des clients.

Image simple : la table de faits donne les chiffres, la table de dimension explique comment lire ces chiffres.

### KPI

Un KPI (`Key Performance Indicator` :indicateur cle de performance) est un indicateur important que l'on suit regulierement pour piloter une activite ou un risque.

Dans ce projet, les KPI peuvent etre par exemple :

- nombre de clients actifs ;
- encours de credit ;
- portefeuille a risque ;
- volume de depots ;
- nombre d'alertes LBC-FT ;
- nombre de comptes dormants ;
- montant des remboursements attendus.

### Batch

Un batch (lot de traitement ou lot de chargement) correspond a une execution d'un chargement de donnees.

Exemple : si on charge les donnees du 01/06/2026 au 30/06/2026, ce chargement recoit un numero de batch.
Ce numero permet de savoir :

- quand le chargement a ete fait ;
- quelle periode a ete chargee ;
- quelle devise a ete chargee ;
- si le chargement a reussi ou echoue ;
- quelles donnees appartiennent a ce chargement.

Dans ce projet, le suivi des batchs est stocke dans le schema `ctl`.

### Staging

Le staging (zone de preparation temporaire) est une zone intermediaire utilisee lorsque les donnees doivent etre preparees avant d'etre integrees
dans les tables finales.

Dans ce projet, le schema `stg` sert a cette preparation. Power BI ne doit pas lire `stg`.

## Ordre d'execution recommande

1. `01_create_database_and_schemas.sql`
2. `02_create_dimensions.sql`
3. `03_create_facts.sql`
4. `04_create_etl_control.sql`
5. `05_load_dimensions.sql`
6. `06_create_powerbi_views.sql`
7. `07_quality_checks.sql`
8. `08_create_indexes.sql`
9. `09_load_facts_conformite_clients.sql`
10. `10_run_monthly_load.sql`

## Sources de reference

- Schema source : `data/vision/BB_VISION_PRO.sql`
- Catalogue metier : `data/vision/requetes.sql`
- Projet Power BI : `data/vision/power-bi`

## Convention

La base `BB_VISION_REPORTING` est organisee en plusieurs schemas pour separer clairement les responsabilites.
Cette separation est importante : elle evite que Power BI lise directement les tables Perfect Vision, elle facilite
les controles, et elle permet de faire evoluer le modele sans casser les rapports deja construits.

### Schema `rpt` : tables physiques du data mart

Le schema `rpt` contient les vraies tables de reporting, c'est-a-dire les donnees deja preparees pour l'analyse.

Exemples :

- `rpt.f_conformite`
- `rpt.f_clients`
- `rpt.f_credit_portefeuille`
- `rpt.f_epargne_soldes`
- `rpt.d_date`
- `rpt.d_devise`

Ces tables sont alimentees par des procedures de chargement construites a partir des requetes autonomes de
`data/vision/requetes.sql`.

Regle de gestion :

- une table `rpt.f_*` correspond a un sujet analytique stable ;
- les colonnes techniques de Perfect Vision ne doivent pas etre exposees inutilement ;
- les montants ne doivent jamais melanger plusieurs devises ;
- chaque chargement doit enregistrer `batch_id` et `loaded_at` pour garder une piste d'audit ;
- si une periode est rechargee, les anciennes lignes de cette meme periode/devise doivent etre remplacees proprement.

En pratique, `rpt` est le coeur du systeme miroir/reporting.

### Schema `pbi` : vues exposees a Power BI

Le schema `pbi` contient uniquement des vues destinees a Power BI.

Pour un nouveau modele, Power BI peut se connecter prioritairement aux objets `pbi.*`, et non directement a la base
Perfect Vision.

Exception validee pour le PBIP actuel : les tables `F_Conformite` et `F_Clients` lisent directement `rpt.f_conformite`
et `rpt.f_clients`. Cette exception est volontaire, car le modele TMDL existant attend des noms de colonnes techniques
comme `date_debut`, `type_element`, `code_client` ou `nombre_comptes`. Les vues `pbi.*` exposent des noms plus lisibles
en francais, parfois accentues, ce qui peut obliger a remapper beaucoup de colonnes dans Power BI.

Pourquoi passer par `pbi` ?

- garder des noms de colonnes lisibles pour les utilisateurs ;
- proteger Power BI contre les changements internes des tables `rpt` ;
- pouvoir renommer, masquer ou reformater une colonne sans toucher au chargement ;
- garder un point d'entree propre pour le modele semantique Power BI.

Exemples :

- `pbi.F_Conformite` lit `rpt.f_conformite` ;
- `pbi.F_Clients` lit `rpt.f_clients` ;
- `pbi.D_Date` lit `rpt.d_date` ;
- `pbi.D_Devise` lit `rpt.d_devise`.

Regle de gestion :

- Power BI lit `pbi.*` ;
- ou Power BI lit `rpt.*` lorsque le modele existant attend les noms techniques de la table de faits ;
- les vues `pbi.*` ne doivent pas contenir de logique metier lourde ;
- la logique metier doit rester dans les requetes/procedures de chargement qui alimentent `rpt.*` ;
- les vues servent surtout a exposer un modele lisible, stable et compatible avec le tableau de bord.

### Schema `ctl` : controle, tracabilite et rapprochements

Le schema `ctl` sert a suivre les chargements et a documenter la qualite des donnees.

Il contient notamment :

- les lots de chargement ;
- les messages de succes ou d'erreur ;
- les periodes chargees ;
- la devise chargee, si un filtre devise a ete applique ;
- les rapprochements entre les resultats SQL et les indicateurs Power BI.

Exemples :

- `ctl.etl_batch`
- `ctl.etl_table_log`
- `ctl.kpi_reconciliation`
- `ctl.start_batch`
- `ctl.end_batch`

Regle de gestion :

- tout chargement important doit creer un lot dans `ctl.etl_batch` ;
- les erreurs doivent etre conservees au lieu d'etre seulement affichees dans SSMS ;
- les KPI importants doivent etre rapproches entre SQL et Power BI avant validation ;
- ce schema permet de savoir quand, comment et sur quelle periode les donnees ont ete chargees.

En pratique, `ctl` est la boite noire du reporting : il permet d'expliquer ce qui s'est passe.

### Schema `stg` : zone temporaire de preparation

Le schema `stg` est reserve aux donnees intermediaires.

Il peut servir lorsque le chargement devient trop complexe pour etre insere directement dans `rpt`.
Par exemple, on peut d'abord stocker un resultat brut de requete, controler les doublons ou les colonnes obligatoires,
puis inserer seulement les donnees propres dans `rpt`.

Regle de gestion :

- `stg` ne doit pas etre utilise par Power BI ;
- les tables `stg` peuvent etre videes et rechargees ;
- les donnees finales doivent toujours finir dans `rpt` ;
- `stg` sert a preparer, pas a publier.

### Parcours normal de la donnee

Le flux cible est le suivant :

```text
BB_VISION_PRO_TEST / BB_VISION_PRO
        |
        |  requetes autonomes ou procedures de chargement
        v
stg.*   optionnel, si preparation necessaire
        |
        v
rpt.*   tables physiques controlees et historisables
        |
        v
pbi.*   vues lisibles pour Power BI
        |
        v
Power BI
```

Regle simple a retenir :

- Perfect Vision reste la source operationnelle ;
- `rpt` stocke les donnees analytiques propres ;
- `pbi` expose les donnees a Power BI ;
- `ctl` explique et controle les chargements ;
- `stg` sert seulement de zone de passage.

## Etat du kit

Ce premier kit cree la structure cible et les controles de base. Les premiers chargements reels disponibles sont :

- Conformite : requete 156 vers `rpt.f_conformite`
- Clients : requete 157 vers `rpt.f_clients`

Les autres chargements de faits doivent etre alimentes progressivement a partir des requetes de reference :

- Credit : 96 a 109, 145 a 147
- Epargne : 103, 110, 113, 144
- Conformite : 156, deja amorcee dans `09_load_facts_conformite_clients.sql`
- Clients : 157, deja amorcee dans `09_load_facts_conformite_clients.sql`

Ne pas brancher la production directement tant que les procedures de chargement et les rapprochements KPI ne sont pas valides sur `BB_VISION_PRO_TEST`.

## Exemple de chargement valide sur la base locale

Apres execution des scripts de creation, le chargement prioritaire Conformite + Clients peut etre lance avec :

```sql
10_run_monthly_load.sql
```

Ce script contient les parametres de periode en haut du fichier. Il suffit de modifier :

```sql
DECLARE @date_debut date = '2026-06-01';
DECLARE @date_fin   date = '2026-06-30';
```

Le coeur du chargement est :

```sql
EXEC rpt.load_all_facts
    @source_database = N'BB_VISION_PRO_TEST',
    @date_debut = '2026-06-01',
    @date_fin = '2026-06-30',
    @id_devise_reporting = NULL;
```

Avec `@id_devise_reporting = NULL`, les donnees Clients sont chargees devise par devise pour eviter une demande
memoire trop elevee dans SQL Server.

Sur le test local de juin 2026, le chargement a produit :

- `rpt.f_conformite` : 50 666 lignes ;
- `rpt.f_clients` : 17 507 lignes ;
- total du lot : 68 173 lignes.

Les messages du type `La valeur NULL est eliminee par un agregat` sont des avertissements SQL Server lies aux
aggregations. Ils ne bloquent pas le chargement.

## Connexion Power BI validee

Le projet PBIP `data/vision/power-bi/IMF BB Tableau de bord.pbip` a ete adapte pour consommer les premieres tables
materialisees de `BB_VISION_REPORTING`.

Parametres Power BI :

- `pServeur = "CDBBIMFL065"`
- `pBaseDonnees = "BB_VISION_PRO_TEST"` : conserve pour les tables credit/epargne non encore materialisees.
- `pBaseReporting = "BB_VISION_REPORTING"` : utilise par les tables deja migrees vers le data mart.
- `pDateDebut = #date(2026, 6, 1)`
- `pDateFin = #date(2026, 6, 30)`

Tables Power BI deja migrees :

- `F_Conformite` lit `BB_VISION_REPORTING.rpt.f_conformite`.
- `F_Clients` lit `BB_VISION_REPORTING.rpt.f_clients`.

Regle Power Query retenue :

- utiliser `Sql.Database(pServeur, pBaseReporting, ...)` ;
- naviguer vers la table avec `Source{[Schema="rpt", Item="f_conformite"]}[Data]` ou `Source{[Schema="rpt", Item="f_clients"]}[Data]` ;
- filtrer la periode avec `Table.SelectRows(..., each [date_debut] = pDateDebut and [date_fin] = pDateFin)` ;
- eviter `Value.NativeQuery` pour ces tables materialisees ;
- ne pas placer `SET NOCOUNT ON`, `DECLARE` ou des dates converties en texte dans une requete Power Query native.

Pourquoi cette regle ?

Power BI peut encapsuler une requete native SQL. Dans ce cas, des instructions comme `SET NOCOUNT ON` ou des dates
fabriquees sous forme de chaine peuvent provoquer :

- `Syntaxe incorrecte vers le mot cle SET` ;
- `Syntaxe incorrecte vers ')'` ;
- `Echec de la conversion de la date et/ou de l'heure a partir d'une chaine de caracteres`.

La navigation Power Query evite ces erreurs et laisse Power BI manipuler les dates comme de vraies valeurs Date.

Resultat valide sur juin 2026 :

- `F_Conformite` : 50 666 lignes chargees dans Power BI ;
- `F_Clients` : 17 507 lignes chargees dans Power BI.

Apres chaque rechargement mensuel :

1. Executer `10_run_monthly_load.sql` dans SSMS.
2. Ouvrir le PBIP dans Power BI Desktop.
3. Cliquer sur `Accueil > Actualiser`.
4. Verifier les pages `Clients`, `Conformite` et `Surveillance`.
