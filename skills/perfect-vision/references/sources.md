# Sources Perfect Vision

## Fichiers de référence

- Schéma SQL Server : `data/vision/BB_VISION_PRO.sql`
- Catalogue des contrôles : `data/vision/requetes.sql`
- Modélisation synthétique : `data/vision/schema_modelisation_bb_vision.md`
- Description complémentaire : `data/vision/desciption_tables_Perfect_vision.xlsx`
- Indicateurs : `data/vision/Indicateurs_perfect_vision.xlsx`

Résoudre ces chemins depuis la racine du dépôt. Depuis ce skill, la racine est `../..`.

## Tables fréquemment utilisées

- `ADHERENTS` : clients et informations d'adhésion.
- `COMPTES`, `COMPTES_ADHERENT` : comptes et rattachements clients.
- `PRODUITS_EPG` : produits d'épargne.
- `OPERATIONS`, `OPERATIONS_API` : opérations back-office et API.
- `HDPM`, `HDPM_API`, `HDPM_VIEW` : historique des mouvements.
- `DEMANDES_CREDIT`, `PRETS` : demandes et prêts.
- `DEVISES` : référentiel des devises ; les requêtes du catalogue indiquent généralement `1 = USD` et `2 = CDF`, à confirmer dans la base ciblée.

Cette liste facilite la recherche mais ne remplace pas la vérification du schéma.

## Responsabilité comptable des systèmes

| Système | Rôle de référence | Usage autorisé dans les rapprochements | Limite |
|---|---|---|---|
| Perfect Vision | Cœur métier microfinance : clients, comptes, produits, opérations, DAT, prêts, échéanciers et remboursements | Rechercher la position ou l'écriture officielle disponible dans le schéma et expliquer ses jointures | Ne pas inventer une écriture absente du schéma ou d'une requête validée |
| Transactions M-PESA_Turbo | Sous-registres opérationnels du portail : écritures, `dr`, `cr`, soldes observés, `ref_no`, comptes techniques et produits | Construire une balance auxiliaire observée, des journaux et des contrôles de mouvement | Ne pas présenter cette restitution comme une balance générale certifiée ou un compte de résultat officiel |
| Transactions M-PESA_G2 | Preuve secondaire Vodacom, statut, téléphone/nom, dates d'initiation et de finalisation | Vérifier `Receipt No = ref_no`, la devise, le montant et l'identité | Ne jamais remplacer les mouvements Turbo ou les écritures Perfect Vision par les montants G2 |

Pour analyser un écart, conserver la séparation par devise puis comparer dans cet ordre : client/téléphone, référence, produit ou compte, date, montant, statut et sens comptable. Une absence de rapprochement reste un résultat de contrôle tant que la source, le grain et le sens n'ont pas été confirmés.

## Catalogue des requêtes

Chaque contrôle de `requetes.sql` possède normalement un numéro, un nom d'export, un objectif, une lecture et un niveau d'importance. Rechercher par concept métier, table, colonne ou nom d'export. Conserver les déclarations de paramètres nécessaires à la requête sélectionnée.

Le catalogue utilise une présentation métier/export épurée :

- les CTE, sous-requêtes, jointures, filtres, agrégations et `ORDER BY` peuvent conserver des colonnes techniques non affichées;
- seules les colonnes du `SELECT` final définissent le fichier exporté;
- retirer du `SELECT` final un identifiant technique lorsqu'un code, numéro ou libellé métier équivalent est déjà présent;
- conserver les références nécessaires à l'audit : `id_client`, numéro de transaction, reçu, compte, prêt, demande ou dossier selon le cas;
- conserver au minimum les dimensions permettant d'identifier la population, la date, la devise, le montant, le statut ou motif d'exception et la référence source;
- ne pas réintroduire automatiquement toutes les colonnes intermédiaires dans la projection finale.

Utiliser `scripts/inspect_vision_sql.py --number N` pour relire une requête complète et contrôler son `SELECT` final. La requête 144 illustre ce contrat : elle affiche la date de situation, l'identité et le téléphone du client, la devise, le montant et les dates du DAT, sa durée, sa validation et son statut, tout en gardant le calcul du solde et de l'encours dans les CTE et le tri.

Paramètres courants :

- `@date_debut`, `@date_fin`
- `@seuil_5k_usd_cdf`, `@seuil_10k_usd_cdf`
- `@id_devise_reporting`

Les seuils à zéro ou les devises à `NULL` sont des valeurs à configurer, pas des hypothèses validées.

## Vérifications avant livraison

1. Toutes les tables et colonnes existent dans le schéma.
2. Les clés de jointure sont justifiées.
3. La période inclut exactement les dates attendues.
4. Les montants restent séparés par devise.
5. Les annulations, suppressions ou statuts métier sont traités explicitement.
6. Le niveau de granularité de sortie correspond à l'objectif du contrôle.
7. Le `SELECT` final ne contient que les colonnes importantes pour l'export, sans supprimer les colonnes techniques nécessaires aux calculs internes.
