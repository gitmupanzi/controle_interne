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
4. Vérifier chaque table et colonne dans `data/modelisation/BB_VISION_PRO.sql` avec `--table NOM_TABLE` ou `--query NOM_COLONNE`.
5. Réutiliser la requête existante si elle répond au besoin. Sinon, produire une variante minimale et expliquer les adaptations.
6. Afficher la requête complète avec `--number N`, puis vérifier séparément les colonnes techniques internes et les colonnes métier du `SELECT` final.
7. Valider les paramètres de dates, devise, seuils et statut d'annulation avant toute exécution.
8. Livrer la requête, ses hypothèses, les champs de sortie et les contrôles de cohérence.

## Règles SQL

- Produire des requêtes en lecture seule (`SELECT`, CTE, tables temporaires locales si nécessaires).
- Ne jamais exécuter les instructions `CREATE DATABASE`, `ALTER`, `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT` du fichier de schéma.
- Qualifier les objets avec `dbo.` et conserver les noms exacts du schéma.
- Utiliser des bornes de dates explicites. Pour les colonnes datetime, préférer `>= @date_debut AND < DATEADD(day, 1, @date_fin)`.
- Ne jamais additionner CDF et USD. Grouper par `ID_DEVISE` ou filtrer la devise demandée.
- Pour les requêtes paramétrées avec `@id_devise_reporting`, appliquer la convention suivante : une valeur précise filtre une seule devise; `@id_devise_reporting = NULL` signifie toutes les devises disponibles, mais toujours avec une ligne, un groupe ou un détail par devise. Ne jamais utiliser `NULL` pour produire un total monétaire multi-devises.
- Quand `@id_devise_reporting = NULL`, appliquer les seuils LBC-FT par devise : USD avec les seuils nominaux `5000` et `10000`, CDF avec `@seuil_5k_usd_cdf` et `@seuil_10k_usd_cdf`. Si une autre devise apparaît, la traiter comme une devise distincte et documenter l'hypothèse de seuil.
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
- Identifier chaque bloc exporté par le libellé métier `analyse` et son grain par `type_element`. Lire `analyse_source` et `type_ligne` uniquement comme anciens alias pendant la transition des fichiers historiques. Ne jamais faire dépendre Q156 d'une vue ou du résultat enregistré d'une autre requête : recopier ou factoriser la logique dans ses propres CTE ou tables temporaires locales.
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
