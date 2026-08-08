# KPI, DAX et validation

## Catalogue KPI

Le dossier `data/kpi_perfect/documentation` contient :

- `KPI_CATALOGUE.md`
- `VALIDATION_RESULTS.md`
- `DATA_GAPS.md`
- `MIGRATION_STATUS.md`
- `NEXT_STEPS_POWER_BI.md`

Ces fichiers sont la base de documentation pour les KPI Power BI.

## Exemples de familles de mesures

| Famille | Exemples |
|---|---|
| Crédit | prêts actifs, encours, décaissements, top encours |
| Risque | PAR 30, PAR 60, PAR 90, provisions |
| Épargne | soldes, mobilisation, comptes |
| Clients | clients actifs, nouveaux clients, rétention |
| Conformité | alertes, dossiers incomplets, contrôles |

## Validation

Chaque KPI publié doit préciser :

- mesure DAX ;
- table TMDL ;
- table ou vue reporting ;
- requête SQL ou règle métier d'origine ;
- devise ;
- période ;
- résultat de rapprochement avec SQL.

!!! warning "Attention"
    Un KPI affiché dans Power BI ne doit pas être considéré comme certifié tant que son rapprochement avec la source SQL n'est pas documenté.
