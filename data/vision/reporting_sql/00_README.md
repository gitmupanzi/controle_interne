# BB_VISION_REPORTING

Kit SQL de demarrage pour construire une couche de reporting durable au-dessus de Perfect Vision.

## Objectif

Ce dossier prepare une base `BB_VISION_REPORTING` separee de la base operationnelle `BB_VISION_PRO`.

Le but est de faire lire Power BI sur des tables propres, stables et indexees, au lieu de lancer directement les longues requetes du catalogue `data/vision/requetes.sql` contre la base Perfect Vision.

## Ordre d'execution recommande

1. `01_create_database_and_schemas.sql`
2. `02_create_dimensions.sql`
3. `03_create_facts.sql`
4. `04_create_etl_control.sql`
5. `05_load_dimensions.sql`
6. `06_create_powerbi_views.sql`
7. `07_quality_checks.sql`
8. `08_create_indexes.sql`
9. `09_load_facts_todo.sql`

## Sources de reference

- Schema source : `data/vision/BB_VISION_PRO.sql`
- Catalogue metier : `data/vision/requetes.sql`
- Projet Power BI : `data/vision/power-bi`

## Convention

- Schema `rpt` : tables physiques du data mart.
- Schema `ctl` : suivi des chargements et rapprochements.
- Schema `pbi` : vues exposees a Power BI avec des noms de colonnes proches du modele actuel.

## Etat du kit

Ce premier kit cree la structure cible et les controles de base. Les chargements de faits doivent etre alimentes progressivement a partir des requetes de reference :

- Credit : 96 a 109, 145 a 147
- Epargne : 103, 110, 113, 144
- Conformite : 156
- Clients : 157

Ne pas brancher la production directement tant que les procedures de chargement et les rapprochements KPI ne sont pas valides sur `BB_VISION_PRO_TEST`.
