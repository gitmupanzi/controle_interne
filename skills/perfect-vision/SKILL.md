---
name: perfect-vision
description: Analyser la base Microsoft SQL Server BB_VISION_PRO et maintenir le tableau de bord Streamlit Perfect Vision, retrouver tables et colonnes dans le schéma, sélectionner ou adapter les requêtes de contrôle interne, expliquer les jointures et produire des requêtes SELECT sûres. Utiliser pour toute question ou modification sur Perfect Vision, BB_VISION_PRO, ses sous-onglets, les opérations, adhérents, comptes, épargne, crédits, HDPM, rapprochements API, indicateurs ou extractions d'audit issues des fichiers SQL du projet.
---

# Perfect Vision

Travailler à partir du schéma et du catalogue SQL réels de BB_VISION_PRO. Ne jamais inventer une table, une colonne ou une relation.

## Procédure de travail

1. Reformuler le besoin en cycle, période, population, mesure et exception recherchée.
2. Lire [references/sources.md](references/sources.md) pour localiser les sources et connaître les garde-fous.
3. Chercher d'abord une requête existante dans `data/modelisation/requetes.sql` avec `scripts/inspect_vision_sql.py --query "terme"`.
4. Vérifier chaque table et colonne dans `data/modelisation/BB_VISION_PROD.sql` avec `--table NOM_TABLE` ou `--query NOM_COLONNE`.
5. Réutiliser la requête existante si elle répond au besoin. Sinon, produire une variante minimale et expliquer les adaptations.
6. Afficher la requête complète avec `--number N`, puis vérifier séparément les colonnes techniques internes et les colonnes métier du `SELECT` final.
7. Valider les paramètres de dates, devise, seuils et statut d'annulation avant toute exécution.
8. Livrer la requête, ses hypothèses, les champs de sortie et les contrôles de cohérence.

## Règles SQL

- Produire des requêtes sûres pour la production : lectures `SELECT`, CTE, sous-requêtes, `UNION ALL`, agrégations, variables `DECLARE` et filtres.
- Pour les requêtes lourdes, les tables temporaires locales `#...` sont autorisées afin d'accélérer l'exécution, à condition qu'elles soient créées uniquement dans la session SQL, alimentées depuis des `SELECT`, indexées seulement localement si nécessaire, puis supprimées en fin de requête. Cette optimisation touche `tempdb`, jamais les tables métiers de `BB_VISION_PROD`.
- Dans `data/modelisation/requetes.sql`, ne jamais utiliser d'instruction modifiant les données métiers ou les objets permanents : pas de `CREATE TABLE` permanent, `ALTER`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT`, `MERGE`, ni `DROP` d'objet permanent. `DROP TABLE IF EXISTS #...`, `SELECT ... INTO #...` et `CREATE INDEX ... ON #...` sont acceptés uniquement pour des tables temporaires locales de performance.
- Ne jamais exécuter les instructions `CREATE DATABASE`, `ALTER`, `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT` du fichier de schéma.
- Qualifier les objets avec `dbo.` et conserver les noms exacts du schéma.
- Utiliser des bornes de dates explicites. Pour les colonnes datetime, préférer `>= @date_debut AND < DATEADD(day, 1, @date_fin)`.
- Ne jamais additionner CDF et USD. Grouper par `ID_DEVISE` ou filtrer la devise demandée.
- Pour les requêtes paramétrées avec `@id_devise_reporting`, appliquer la convention suivante : une valeur précise filtre une seule devise; `@id_devise_reporting = NULL` signifie toutes les devises disponibles, mais toujours avec une ligne, un groupe ou un détail par devise. Ne jamais utiliser `NULL` pour produire un total monétaire multi-devises.
- Quand `@id_devise_reporting = NULL`, appliquer les seuils LBC-FT par devise : USD avec les seuils nominaux `5000` et `10000`, CDF avec les équivalents calculés directement à partir de `@taux_usd_cdf`. Si une autre devise apparaît, la traiter comme une devise distincte et documenter l'hypothèse de seuil.
- Ne pas déclarer de variables séparées pour les seuils équivalents CDF : déclarer uniquement `@taux_usd_cdf` en `decimal(19,6)`, puis calculer dans la requête `5000 * @taux_usd_cdf` et `10000 * @taux_usd_cdf` en `decimal`, jamais en `float`. Cela évite les erreurs de cohérence lorsque le taux de reporting change.
- Si un reporting consolidé en CDF est demandé, ajouter `@convertir_affichage_cdf bit` comme option d'affichage. Ne jamais remplacer les colonnes sources `montant`, `volume`, `solde` ou `encours` : conserver la devise d'origine, puis ajouter des colonnes explicites comme `montant_equivalent_cdf`, `volume_equivalent_cdf`, `devise_affichage`, `montant_affichage`, `volume_affichage` et `taux_usd_cdf_applique`.
- Pour les analyses de dépôts client, utiliser la définition métier complète `DEPO + VERS + MOB_DEPO` : `DEPO` = dépôt guichet/back-office, `VERS` = versement banque au bénéfice du client, `MOB_DEPO` = dépôt mobile/API. Garder les lignes Mobile Banking limitées à `MOB_DEPO/MOB_RETR` afin de ne pas mélanger versement banque et canal mobile.
- Pour les requêtes volumineuses sur les mouvements, filtrer d'abord `dbo.HDPM` / `dbo.HDPM_API` par `DATE_OPERATION`, `ID_DEVISE` et, si possible, `ID_TYPE_OPERATION`, puis joindre `dbo.OPERATIONS` / `dbo.OPERATIONS_API` pour vérifier `ANNULE`. Éviter de partir de `OPERATIONS` puis de rejoindre toute `HDPM` lorsque l'objectif porte sur les montants comptables.
- Pour le canevas `REPORTING_FIN_MENSUEL DES IMF ACTUALISE JUIN 2026.xlsx`, utiliser les lignes LBC-FT suivantes : 13 total opérations, 14 opérations en espèces, 15 total encours de crédits, 16 crédits à la consommation, 17 crédits bâtiments et travaux publics / immobiliers, 18 crédits aux miniers, 19 crédits aux PPE, 20 crédits aux sociétés d'assurance, 21 crédits aux cabinets d'avocats, 22 crédits aux OBNL (ONG/ASBL), 23 crédits aux MPME, 24 crédits garantis par le DAT, 25 total dépôts, 26 à 33 dépôts par segment, 35 à 50 portefeuille client par segment, 53 dépôt >= 10k USD, 54 retrait >= 10k USD, 55 dépôt >= 5k et < 10k USD, 56 retrait >= 5k et < 10k USD, 57 à 123 opérations par segment et seuils, 124 crédits remboursés anticipativement, 126 total alertes générées, 127 total alertes traitées, 128 alertes espèces >= 10k, 129 alertes traitées espèces >= 10k, 130 opérations suspectes/atypiques, 132 mobile banking, 133 Bank to Wallet, 134 Wallet to Bank, 135 à 140 canaux internet/agents/POS lorsqu'une source validée existe, 142 déclarations automatiques, 143 DOS, 145 gels des avoirs, 146 transactions refusées pour sanctions et 148 localisation. Si une rubrique d'analyse n'existe pas dans le canevas, mettre `ligne_reporting = NULL` ou `statut_couverture = NON_COUVERT` plutôt que produire un chiffre non justifié.
- Pour les lignes LBC-FT par segment client, partir de `dbo.HDPM` / `dbo.HDPM_API`, joindre `dbo.COMPTES_ADHERENT` puis `dbo.extra_clients_view`. Les segments issus de libellés (`PPE`, minier, immobilier, MPME, OBNL, EME, bureaux de change, restauration, jeux, SPA, non-résident, commerçant, exploitant/négociant) doivent rester `PARTIEL` tant que la Conformité n'a pas validé la nomenclature officielle et les champs de référence. Les lignes de canaux non présents dans le schéma (`internet banking`, `agent banking`, `POS`) doivent rester `NON_COUVERT`.
- Pour les lignes crédit 15 à 24 du canevas LBC-FT, calculer le stock à `@date_fin` par devise avec `dbo.extra_credits_view` et `dbo.fct_perf_extra_encours(@date_fin, id_pret)`. Ne jamais filtrer uniquement sur `date_decaissement`, car cette colonne peut être vide dans `BB_VISION_PROD`; utiliser une date de référence `COALESCE(date_decaissement, date_effet, date_debut_cycle, date_demande)`. Dédoublonner ensuite par `id_pret` avec le cycle le plus récent afin d'éviter de compter plusieurs cycles du même prêt. Les lignes fondées sur des libellés de produit, objet de financement, secteur, typologie client ou profession doivent être marquées `PARTIEL` tant que la Conformité n'a pas validé la nomenclature officielle. La ligne 24 peut utiliser `DOSSIERS_CREDIT.MNT_EPG_OBLIGATOIRE` comme approximation des crédits garantis par DAT, avec une mention explicite de cette limite.
- Les requêtes conformité qui alimentent un canevas réglementaire doivent exposer une colonne de traçabilité comme `regle_alimentation`, `operations_incluses`, `origine_donnee` ou `commentaire`, afin que chaque `ligne_reporting` indique clairement les tables sources, les types d'opérations, les seuils appliqués et les limites de couverture. Une ligne sans traçabilité métier est considérée incomplète.
- Pour les analyses operationnelles du cycle credit, exposer `PAR60` des qu'une requete expose `PAR30` et `PAR90`. Le suivi minimum attendu est `PAR1`, `PAR30`, `PAR60`, `PAR90` et, si disponible, `PAR180`, toujours calcule sur l'encours actif et separe par devise.
- Distinguer les sources back-office et API avant de les réunir avec `UNION ALL`.
- Éviter `NOLOCK` pour les contrôles nécessitant une image cohérente, sauf demande explicite et risque documenté.
- Signaler toute jointure incertaine et la confirmer dans le schéma ou dans une requête existante.
- Ne jamais remplacer les colonnes nécessaires aux CTE, jointures, filtres, agrégations ou tris uniquement pour alléger l'export.
- Éviter `SELECT *` dans la projection finale et afficher seulement les colonnes utiles à la décision et au contrôle.

## Projection métier des exports

- Considérer `data/modelisation/requetes.sql` comme le catalogue métier/export épuré de référence.
- Simplifier uniquement le `SELECT` final; conserver les calculs et identifiants techniques nécessaires en amont.
- Garder les références auditables : client, transaction, reçu, compte, prêt, demande ou dossier selon le contrôle.
- Préférer les codes, numéros et libellés métier aux identifiants techniques redondants. Conserver un identifiant technique seulement s'il est la seule clé exploitable pour la revue.
- Vérifier que les colonnes finales suffisent pour identifier la population, comprendre l'anomalie, mesurer le montant, connaître la devise, dater le fait et retrouver la pièce source.

## Contrat du cycle conformité

- Considérer la requête 156 comme l'unique fichier d'entrée du cycle conformité. Elle doit reprendre, avec une logique SQL autonome, les analyses 38, 39, 48, 57 et 149 à 155.
- Identifier chaque bloc exporté par le libellé métier `analyse` et son grain par `type_element`. Lire `analyse_source` et `type_ligne` uniquement comme anciens alias pendant la transition des fichiers historiques. Ne jamais faire dépendre Q156 d'une vue ou du résultat enregistré d'une autre requête : recopier ou factoriser la logique dans ses propres CTE, sous-requêtes ou tables temporaires locales `#...` lorsque le volume impose une optimisation.
- Employer `rubrique` comme libellé canonique de l'élément analysé et `nombre` comme mesure canonique de comptage. Lire `type_alerte`, `controle` et `nombre_anomalies` uniquement comme anciens alias pendant la transition des fichiers historiques.
- La projection finale de Q156 est destinée à un utilisateur métier : regrouper les dates techniques dans `date_evenement`, exposer `code_client` plutôt qu'un identifiant interne redondant, utiliser `numero_operation` pour la référence d'opération, retirer `id_devise` lorsque `devise` est présent et regrouper les drapeaux booléens dans `indicateurs`.
- Pour les autres requêtes, appliquer la même règle au `SELECT` final : retirer un identifiant technique seulement lorsqu'un code, numéro ou libellé métier permet la même traçabilité. Ne jamais supprimer une clé qui est le seul moyen de retrouver la pièce source.
- Conserver un grain exploitable : une ligne par alerte, déclaration, profil, sanction, réactivation ou contrôle ; une ligne par groupe client-jour-devise pour le fractionnement ; une ligne par mois-point de service-devise pour les gros mouvements ; une ligne par rubrique-devise pour les synthèses.
- Mapper les mesures sans mélanger les devises : `montant` porte le montant de l'élément ou le maximum unitaire, `volume` porte le cumul du groupe, et `nombre` porte le nombre d'éléments. Documenter ce mapping dans `commentaire` lorsqu'un bloc agrégé l'utilise.
- Pour toute modification de Q156 ou des onglets conformité, exécuter le va-et-vient complet : tester Q156 sur SQL Server, exporter le XLSX, le téléverser dans Streamlit, puis contrôler les onglets `Conformité`, `Surveillance`, `Portefeuille`, `Risques` et `Qualité`.
- Vérifier que les anciens XLSX restent lisibles grâce aux alias de repli, sans réintroduire ces alias dans les nouveaux exports.

## Invariants du tableau de bord Streamlit

- Pour toute période utilisateur, afficher deux `st.date_input` distincts intitulés exactement `Date de début` et `Date de fin`, au format `DD/MM/YYYY`. Ne jamais utiliser un `st.date_input` initialisé avec un tuple ou une liste comme sélecteur de plage. Employer deux clés stables distinctes, valider `date_debut <= date_fin` et appliquer des bornes inclusives.
- Conserver les analyses détaillées de Perfect Vision dans des `st.tabs`. Perfect Vision constitue un tableau de bord complet : calculer tous les sous-onglets ensemble au chargement initial afin qu'ils soient ensuite immédiatement consultables.
- Ne jamais remplacer ces `st.tabs` par une navigation conditionnelle qui calcule uniquement l'onglet sélectionné. Cette optimisation à la demande est réservée aux modules dont le fonctionnement métier l'autorise, pas à Perfect Vision.
- Améliorer les performances avec `st.cache_data` sur la lecture, la normalisation et les calculs déterministes coûteux. Invalider naturellement le cache lorsque le fichier, la feuille, les paramètres ou les filtres changent; ne pas mettre en cache un rendu Streamlit susceptible de devenir obsolète.
- Vérifier après toute modification que l'ouverture initiale alimente tous les sous-onglets et que le passage d'un onglet déjà chargé à un autre ne déclenche pas un nouveau calcul Python.

## Frontière avec la comptabilité Turbo

- Considérer Perfect Vision comme le cœur métier microfinance et la source à interroger pour les comptes, prêts, échéanciers, remboursements, DAT et écritures officielles disponibles dans son schéma.
- Traiter `mtt_encours` comme une colonne contextuelle : dans les rapports crédit, elle représente l'encours crédit et se normalise en `solde_final`; dans les rapports d'encours épargnant contenant notamment `num_compte`, `libelle_compte`, `produit` et `mtt_encours`, elle représente le solde du compte épargne et se normalise en `solde_compte`. Ne jamais imposer une seule règle globale qui bloque ou fausse l'autre cycle.
- Considérer le volet `Balances et journaux` de `Finance Turbo` dans Solution M-PESA comme une restitution de contrôle des sous-registres opérationnels Turbo. Il produit des balances et positions observées, mais ne remplace pas une balance générale, un bilan ou un compte de résultat validé dans Perfect Vision.
- Utiliser G2 uniquement comme preuve secondaire du canal M-PESA, complément de nom et contrôle `Receipt No = ref_no`; ne jamais reprendre ses montants dans une balance Turbo ou Perfect.
- En cas d'écart Turbo–Perfect Vision, rapprocher par client, téléphone normalisé, devise, référence, produit et date, puis documenter le sens comptable de chaque système avant de conclure. Ne jamais additionner CDF et USD.
- Lire [references/sources.md](references/sources.md) pour la matrice de responsabilité entre Perfect Vision, Turbo et G2.
- Pour transposer une requête Perfect Vision de niveau 9 ou 10 vers les volets de pilotage de `Finance Turbo`, vérifier d'abord que les quatre exports Turbo portent le grain et les champs nécessaires. Adapter les remboursements, évolutions dépôts/crédits, nouveaux crédits, encours, concentration, PAR simplifié, dépôts fréquents, tranches de dépôts, comptes inactifs, DAT sans crédit actif et crédit–épargne disponible. Ne pas copier comme exacts les échéanciers, provisions, garanties ou retards de versement lorsqu'un plan d'amortissement ou un champ métier manque.
- Dans cette transposition, Transactions M-PESA_Turbo fournit les flux, Loans Account les positions de crédit, Savings Account les positions d'épargne/DAT et Customers le référentiel. G2 reste hors des calculs et sert seulement à l'identité et au rapprochement secondaire.

## Norme visuelle commune des onglets

- Conserver une barre d'onglets sobre et professionnelle.
- Afficher l'onglet actif en bleu avec un soulignement rouge.
- Appliquer un survol discret et rendre la navigation au clavier clairement visible.
- Permettre le défilement horizontal des onglets sur les petits écrans.

## Utilitaire de recherche

```powershell
python skills/perfect-vision/scripts/inspect_vision_sql.py --list-queries
python skills/perfect-vision/scripts/inspect_vision_sql.py --query "crédit sans garantie"
python skills/perfect-vision/scripts/inspect_vision_sql.py --number 144
python skills/perfect-vision/scripts/inspect_vision_sql.py --table PRETS
python skills/perfect-vision/scripts/export_vision_query.py --query 156 --date-start 2026-06-01 --date-end 2026-06-30
```

Charger seulement les extraits pertinents : le schéma complet dépasse 3 Mo.

## Format de réponse

Fournir, selon le besoin : objectif du contrôle, sources utilisées, paramètres, SQL prêt à relire, clés de jointure, interprétation des résultats, limites et tests de cohérence. Ne présenter aucun résultat comme observé si la requête n'a pas été exécutée.
