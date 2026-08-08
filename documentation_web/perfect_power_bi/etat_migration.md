# État de migration Power BI

État constaté le 1er août 2026 sur `CDBBIMFL065`.

## Déjà matérialisé dans `BB_VISION_REPORTING`

| Table Power BI | Objet reporting | Source métier | Lignes juin 2026 | État |
|---|---|---:|---:|---|
| `F_Conformite` | `rpt.f_conformite` | Q156 | 50 666 | Migré |
| `F_Clients` | `rpt.f_clients` | Q157 | 17 507 | Migré |
| `F_Credit_PAR_Detail` | `rpt.f_credit_par_detail` | Q96 | 1 172 | Migré, rapprochement SQL réussi |
| `F_Credit_Portefeuille` | `rpt.f_credit_portefeuille` | Q97 | 12 | Migré, rapprochement SQL réussi |
| `F_Credit_Decaissements` | `rpt.f_credit_decaissements` | Q99 | 12 | Migré, rapprochement SQL réussi |
| `F_Credit_Echeances_Futures` | `rpt.f_credit_echeances_futures` | Q100 | 92 | Migré, rapprochement SQL réussi |
| `F_Epargne_Soldes` | `rpt.f_epargne_soldes` | Q103 | 934 | Migré, rapprochement SQL réussi |
| `F_Credit_Top_Encours` | `rpt.f_credit_top_encours` | Q98 | 50 | Migré, validation SQL réussie |
| `F_Credit_Retention` | `rpt.f_credit_retention` | Q101 | 5 | Migré, validation SQL réussie |
| `F_Credit_Vintage` | `rpt.f_credit_vintage` | Q102 | 9 | Migré, validation SQL réussie |
| `F_Credit_Tranches` | `rpt.f_credit_tranches` | Q104 | 29 | Migré, validation SQL réussie |
| `F_Credit_Concentration` | `rpt.f_credit_concentration` | Q105 | 12 | Migré, validation SQL réussie |
| `F_Credit_Couverture` | `rpt.f_credit_couverture` | Q106 | 1 172 | Migré, validation SQL réussie |
| `F_Credit_Provisions_Detail` | `rpt.f_credit_provisions_detail` | Q107 | 879 | Migré, validation SQL réussie |
| `F_Credit_Duree` | `rpt.f_credit_duree` | Q108 | 1 172 | Migré, validation SQL réussie |
| `F_Credit_Tendance_PAR` | `rpt.f_credit_tendance_par` | Q109 | 12 | Migré, validation SQL réussie |

Les seize partitions Power Query ci-dessus utilisent `pBaseReporting` et la navigation `Sql.Database` vers `rpt.*`.
Les anciens noms de colonnes attendus par le modèle Power BI sont maintenus par `Table.RenameColumns` afin de ne pas casser les visuels.

## Dépendances temporaires vers `BB_VISION_PRO_TEST`

Aucune partition Power BI active du périmètre actuel ne dépend encore de `pBaseDonnees` ou de `Value.NativeQuery`.
Les requêtes Perfect Vision restent utilisées côté SQL Server uniquement dans les procédures ETL contrôlées de `BB_VISION_REPORTING`.

## Objets SQL opérationnels

- `rpt.load_f_conformite` ;
- `rpt.load_f_clients` ;
- `rpt.load_f_credit_core` ;
- `rpt.load_f_credit_flows` ;
- `rpt.load_f_epargne_soldes` ;
- `rpt.load_f_credit_analytics` ;
- `rpt.load_all_facts`, étendue aux lots Conformité, Clients, Crédit cœur, Flux crédit, Épargne soldes et Crédit analytique ;
- `ctl.start_batch` et `ctl.end_batch` ;
- vues `pbi.*` déjà créées pour les faits prévus.

## Faits encore vides

Aucun fait prévu dans le périmètre Power BI actuel n'est vide après le batch 26.

## Modèle et pages

- 20 tables TMDL, dont `_Mesures` ;
- 91 mesures DAX après ajout des KPI PAR7, PAR60, PAR180, arriérés, crédits en retard, décaissements, échéances futures et ratios crédits/dépôts CDF/USD ;
- 76 mesures sont actuellement référencées par au moins un visuel PBIR ;
- 9 pages existantes : Paramétrage, Direction, Clients, Crédit, Risque crédit, Prévisions crédit, Épargne, Conformité et Surveillance ;
- relations Date, Devise et Agence déjà présentes pour les faits crédit migrés.

La page `Risque crédit` contient maintenant les cartes prioritaires compactes `PAR 7`, `PAR 30` et `PAR 60`.
Elles complètent les KPI déjà visibles : clients exposés au PAR, arriéré total, concentration top 10 %, exposition non couverte,
principaux encours par client, encours/PAR 30+ par tranche et prêts à investiguer.

La page `Direction` a été enrichie dans le PBIR avec les KPI `Clients actifs`, `Prêts décaissés`,
`Clients épargne`, `Comptes épargne`, `Ratio crédits/dépôts CDF/USD`, `Alertes` et
`Dernière date disponible`. Les deux graphiques inférieurs ont été redimensionnés afin d'ajouter les blocs
`Ratio crédits/dépôts` et `Alertes et actualisation` sans chevauchement.

## Prochaine étape recommandée

Actualiser Power BI Desktop et contrôler visuellement les pages `Crédit`, `Risque crédit`, `Prévisions crédit`,
`Direction` et `Épargne`. Ensuite, passer à l'optimisation : index, durée de rafraîchissement, passerelle, puis sécurité RLS.

La feuille de route opérationnelle est détaillée dans [Prochaines étapes Power BI](prochaines_etapes.md).
