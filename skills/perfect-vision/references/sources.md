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

## Catalogue des requêtes

Chaque contrôle de `requetes.sql` possède normalement un numéro, un nom d'export, un objectif, une lecture et un niveau d'importance. Rechercher par concept métier, table, colonne ou nom d'export. Conserver les déclarations de paramètres nécessaires à la requête sélectionnée.

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
